// Native PC LAN adaptation. Protocol evidence/credits: docs/TECHNICAL.md.
// Uses the original PC server unchanged; Xbox persona and offline-LAN stats
// differences are handled locally. Never rewrites peer/race payloads.
#include "pc_gateway.h"
#include <algorithm>
#include <arpa/inet.h>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <memory>
#include <mutex>
#include <poll.h>
#include <sys/socket.h>
#include <thread>
#include <unistd.h>
#include <vector>
namespace nfsmw::pc {
namespace {
enum Role { kUnknown, kListener, kConnector };
struct Peer {
  uint32_t ip = 0, remote = 0, local = 0;
  bool remoteKnown = false, localKnown = false;
  Role role = kUnknown;
};
constexpr size_t kMaxPeers = 3;
std::mutex peersMutex;
std::vector<Peer> peers;
// Lock-free fast path for every non-PC datagram.
std::atomic<size_t> peerCount{0};
std::atomic<bool> hosting{false};
Peer *Find(uint32_t ipv4) {
  for (auto &p : peers)
    if (ipv4 && p.ip == ipv4)
      return &p;
  return nullptr;
}
void ResetPeers() {
  std::lock_guard<std::mutex> l(peersMutex);
  peers.clear();
  peerCount = 0;
}
template <class F> auto WithPeer(uint32_t ipv4, F f) {
  std::lock_guard<std::mutex> l(peersMutex);
  return f(Find(ipv4));
}
} // namespace
bool IsRacePeer(uint32_t ipv4) {
  return peerCount.load() && WithPeer(ipv4, [](Peer *p) { return p != nullptr; });
}
bool Active() { return peerCount.load() != 0; }
bool Hosting() { return hosting.load(); }
bool Hosting(uint32_t ipv4) {
  return WithPeer(ipv4, [](Peer *p) { return p && p->role == kListener; });
}
void NoteInit(uint32_t ipv4, bool received) {
  WithPeer(ipv4, [received](Peer *p) {
    if (p && p->role == kUnknown)
      p->role = received ? kListener : kConnector;
    return 0;
  });
}
void StartHosting() {
  ResetPeers();
  hosting = true;
}
bool SetHostingPeer(uint32_t ipv4) {
  if (!Hosting() || !ipv4) return false;
  std::lock_guard<std::mutex> l(peersMutex);
  if (Find(ipv4)) return true;
  if (peers.size() >= kMaxPeers) return false;
  // PC guests of this host always open CommUDP towards it.
  peers.push_back({ipv4, 0, 0, false, false, kListener});
  peerCount = peers.size();
  return true;
}
void SetGuestPeers(const std::vector<uint32_t> &list) {
  hosting = false;
  std::lock_guard<std::mutex> l(peersMutex);
  std::vector<Peer> next;
  for (uint32_t ip : list) {
    if (!ip || next.size() >= kMaxPeers) continue;
    if (auto *p = Find(ip)) next.push_back(*p);
    else next.push_back({ip});
  }
  peers = std::move(next);
  peerCount = peers.size();
}
std::vector<uint32_t> Peers() {
  std::lock_guard<std::mutex> l(peersMutex);
  std::vector<uint32_t> out;
  for (auto &p : peers) out.push_back(p.ip);
  return out;
}
bool HasRaceId(uint32_t ipv4) {
  return WithPeer(ipv4, [](Peer *p) { return p && p->remoteKnown; });
}
bool HasLocalRaceId(uint32_t ipv4) {
  return WithPeer(ipv4, [](Peer *p) { return p && p->localKnown; });
}
void ObserveRaceId(uint32_t ipv4, uint32_t id) {
  WithPeer(ipv4, [id](Peer *p) {
    if (p) { p->remote = id; p->remoteKnown = true; }
    return 0;
  });
}
uint32_t RaceId(uint32_t ipv4) {
  return WithPeer(ipv4, [](Peer *p) { return p ? p->remote : 0u; });
}
void SetLocalRaceId(uint32_t ipv4, uint32_t id) {
  WithPeer(ipv4, [id](Peer *p) {
    if (p) { p->local = id; p->localKnown = true; }
    return 0;
  });
}
uint32_t LocalRaceId(uint32_t ipv4) {
  return WithPeer(ipv4, [](Peer *p) { return p ? p->local : 0u; });
}

std::string Field(const std::string &body, const std::string &key) {
  size_t at = 0;
  while (at < body.size()) {
    size_t end = body.find_first_of("\n\t\0", at, 3);
    if (end == std::string::npos)
      end = body.size();
    if (body.compare(at, key.size() + 1, key + "=") == 0)
      return body.substr(at + key.size() + 1, end - at - key.size() - 1);
    at = end + 1;
  }
  return {};
}
std::string Put(std::string body, const std::string &key,
                const std::string &value) {
  while (!body.empty() && body.back() == '\0')
    body.pop_back();
  size_t at = 0;
  while (at < body.size()) {
    size_t end = body.find_first_of("\n\t", at);
    if (end == std::string::npos)
      end = body.size();
    if (body.compare(at, key.size() + 1, key + "=") == 0) {
      body.replace(at, end - at, key + "=" + value);
      return body;
    }
    at = end + 1;
  }
  if (!body.empty() && body.back() != '\n' && body.back() != '\t')
    body += '\n';
  return body + key + "=" + value;
}
std::string Frame(const std::string &command, const std::string &body,
                  const std::string &subtype) {
  if (command.size() != 4 || subtype.size() != 4)
    return {};
  std::string out = command + subtype + std::string(4, '\0') + body;
  if (out.size() == 12 || out.back() != '\0')
    out += '\0';
  uint32_t size = htonl(uint32_t(out.size()));
  std::memcpy(out.data() + 8, &size, 4);
  return out;
}
std::string AdaptRoom(const std::string &body) {
  // PC room captured in preview6: P=V%3d192359%0a... . The original Xbox
  // sub_82546178 rejects that value before initiating QoS (expects192641).
  // Restrict the alias to this observed build; preserve unknown versions and
  // every other field, especially description/addresses and Binary7 payloads.
  auto params = Field(body, "P");
  std::string lower = params;
  std::transform(
      lower.begin(), lower.end(), lower.begin(), [](unsigned char c) {
        return c >= 'A' && c <= 'Z' ? char(c + ('a' - 'A')) : char(c);
      });
  size_t at = 0;
  while ((at = lower.find("v%3d192359", at)) != std::string::npos) {
    const size_t end = at + 10;
    bool start = at == 0 || (at >= 3 && lower.substr(at - 3, 3) == "%0a");
    bool finish = end == params.size() || lower.substr(end, 3) == "%0a" ||
                  lower.substr(end, 6) == "%0d%0a";
    if (start && finish) {
      params.replace(at + 4, 6, "192641");
      return Put(body, "P", params);
    }
    at = end;
  }
  return body;
}
namespace {
// Independently implemented from the actual USA decoder sub_82826978:
// three separately padded Binary7 blocks, XNADDR36, XNKEY16, XNKID8.
std::string Binary7(const std::string &raw) {
  std::string out;
  uint32_t buffer = 0;
  int bits = 0;
  for (unsigned char b : raw) {
    buffer |= uint32_t(b) << bits;
    bits += 8;
    while (bits >= 7) {
      out += char(0x80 | (buffer & 0x7f));
      buffer >>= 7;
      bits -= 7;
    }
  }
  if (bits)
    out += char(0x80 | buffer);
  return out;
}
std::string Address(const std::string &ip) {
  in_addr a{};
  if (inet_pton(AF_INET, ip.c_str(), &a) != 1)
    return {};
  uint32_t host = ntohl(a.s_addr);
  if (!(host >> 24) || (host >> 24) == 127 || (host >> 24) >= 224)
    return {};
  std::string addr(36, '\0');
  std::memcpy(addr.data(), &a.s_addr, 4);
  const unsigned char *b = reinterpret_cast<const unsigned char *>(&a.s_addr);
  addr[10] = 0;
  addr[11] = 0x1d;
  addr[12] = char(0xd8);
  addr[13] = char(b[1]);
  addr[14] = char(b[2]);
  addr[15] = char(b[3]);
  return addr;
}
std::string Machine(const std::string &ip) {
  auto addr = Address(ip);
  if (addr.empty())
    return {};
  char uid[24];
  const auto *b = reinterpret_cast<const unsigned char *>(addr.data());
  snprintf(uid, sizeof(uid), "$00090000%02x%02x%02x%02x^", b[0], b[1], b[2],
           b[3]);
  return std::string(uid) + Binary7(addr);
}
bool PcMachine(const std::string &value) {
  // Never replace existing Xbox/Xenon machine blobs, or unknown encodings.
  if (value.empty())
    return true;
  if (value.size() != 9 || value[0] != '$')
    return false;
  return std::all_of(value.begin() + 1, value.end(), [](unsigned char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
           (c >= 'A' && c <= 'F');
  });
}
} // namespace
std::string AdaptLogin(const std::string &body, const std::string &sourceIp) {
  auto machine = Field(body, "MADDR");
  if (machine.size() < 19 || machine[0] != '$' || machine[17] != '^')
    return body;
  if (!std::all_of(machine.begin() + 1, machine.begin() + 17,
                   [](unsigned char c) {
                     return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
                            (c >= 'A' && c <= 'F');
                   }))
    return body;
  auto addr = Address(sourceIp);
  if (addr.empty())
    return body;
  const auto *b = reinterpret_cast<const unsigned char *>(addr.data());
  char text[12];
  // PC virtual machine addresses are the little-endian IPv4 integer, as
  // observed in the unmodified PC host's D/MA fields ($ca01a8c0 for .202).
  snprintf(text, sizeof(text), "$%02x%02x%02x%02x", b[3], b[2], b[1], b[0]);
  return Put(body, "MADDR", text);
}
std::string AdaptUser(const std::string &body) {
  if (!PcMachine(Field(body, "MA")))
    return body;
  auto machine = Machine(Field(body, "A"));
  return machine.empty() ? body : Put(body, "MA", machine);
}
std::string AdaptGame(const std::string &body) {
  auto out = body;
  std::string hostAddress;
  for (int i = 0; i < 4; ++i) {
    auto n = std::to_string(i);
    auto ip = Field(body, "ADDR" + n);
    if (Field(body, "OPPO" + n) == Field(body, "HOST") &&
        !Field(body, "HOST").empty())
      hostAddress = Address(ip);
    if (PcMachine(Field(body, "MADDR" + n))) {
      auto machine = Machine(ip);
      if (!machine.empty())
        out = Put(out, "MADDR" + n, machine);
    }
  }
  if (!Field(body, "SESS").empty() || hostAddress.empty() ||
      Field(body, "IDENT").empty())
    return out;
  // Local LAN identity only: the original PC doesn't implement Xbox Live
  // sessions/keys. The existing SDK LAN path doesn't use Xbox encryption.
  // Stable across lobby updates; no real Xbox service credentials generated.
  uint64_t hash = 14695981039346656037ull;
  for (unsigned char c : hostAddress + Field(body, "IDENT")) {
    hash ^= c;
    hash *= 1099511628211ull;
  }
  std::string id(8, '\0'), key(16, '\0'), nonce(8, '\0');
  for (int i = 0; i < 8; ++i)
    id[i] = char(hash >> (i * 8));
  id[0] = char(static_cast<unsigned char>(id[0]) | 0x80);
  for (int i = 0; i < 16; ++i)
    key[i] = char(static_cast<unsigned char>(id[i % 8]) ^ (0x5a + i));
  for (int i = 0; i < 8; ++i)
    nonce[i] = char(static_cast<unsigned char>(id[i]) ^ 0xa5);
  out =
      Put(out, "SESS", "$" + Binary7(hostAddress) + Binary7(key) + Binary7(id));
  if (Field(body, "PLATPARAMS").empty())
    out = Put(out, "PLATPARAMS", Binary7(nonce));
  return out;
}
std::string HostLogin(const std::string &body, const std::string &ip) {
  auto machine = Machine(ip);
  return machine.empty() ? body : Put(body, "MADDR", machine);
}
namespace {
std::string PcAddress(const std::string &ip) {
  auto address = Address(ip);
  if (address.empty()) return {};
  auto b = reinterpret_cast<const unsigned char *>(address.data());
  char text[12];
  snprintf(text, sizeof(text), "$%02x%02x%02x%02x", b[3], b[2], b[1], b[0]);
  return text;
}

}
std::string HostReply(const std::string &command, const std::string &body, const std::string &hostIp) {
  auto out = body;
  if (command == "@dir") return Put(out, "PORT", "9900");
  if (command == "+uss" || command == "+ust" || command == "ujoi" ||
      command == "ucre" || command == "uadm") {
    auto params = Field(body, "P");
    // Reverse only the known Xbox build token, with field boundaries.
    for (size_t at = 0; (at = params.find("V%3d192641", at)) != std::string::npos; ++at) {
      const auto end = at + 10;
      if ((at == 0 || params.substr(at - std::min(at, size_t(3)), 3) == "%0a") &&
          (end == params.size() || params.substr(end, 3) == "%0a")) {
        params.replace(at + 4, 6, "192359"); break;
      }
    }
    out = Put(out, "P", params);
    auto d = Field(body, "D");
    // Room description is the Xbox host XUID; PC expects an IPv4 machine address.
    if (d.size() == 17 && d[0] == '$') {
      auto pc = PcAddress(hostIp);
      if (!pc.empty()) out = Put(out, "D", pc);
    }
  }
  if (command == "+who" || command == "+usr") {
    auto ma = PcAddress(Field(body, "A"));
    if (!ma.empty()) out = Put(out, "MA", ma);
  }
  if (!Field(body, "IDENT").empty() && (command == "+gam" || command == "+mgm" || command == "+ses" ||
      command == "gcre" || command == "gjoi" || command == "gset" || command == "gget")) {
    for (int i = 0; i < 4; ++i) {
      auto n = std::to_string(i);
      auto ma = PcAddress(Field(body, "ADDR" + n));
      if (!ma.empty()) out = Put(out, "MADDR" + n, ma);
    }
    out = Put(Put(out, "SESS", ""), "PLATPARAMS", "");
  }
  return out;
}
std::string Advertisement(const std::string &name, unsigned players, uint32_t session) {
  std::string packet(384, '\0');
  packet.replace(0, 5, "gEA\x03\x05", 5);
  for (int i = 0; i < 3; ++i) packet[5+i] = char(session >> (i*8));
  packet.replace(8, 7, "NFSMWNA");
  packet.replace(40, std::min(name.size(), size_t(11)), name.substr(0, 11));
  auto count = "9900|" + std::to_string(std::min(players, 4u));
  packet.replace(72, count.size(), count);
  const std::string caps = "TCP:~1:1024\tUDP:~1:1024";
  packet.replace(258, caps.size(), caps);
  return packet;
}
std::string LocalStats(const std::string &name) {
  // Original PC LAN has no Xbox 'user' history endpoint. New local LAN
  // identity starts with empty history, same schema as the mobile host.
  std::string zeros = "0";
  for (int i = 1; i < 44; ++i)
    zeros += ",0";
  return Frame("user",
               "PERS=" + name + "\nSTAT=" + zeros + "\nLWSTAT=" + zeros +
                   "\nLMSTAT=" + zeros +
                   "\nLGAME=0\nLAST=2005.11.15-00:00:00\nEXPR=1072566000");
}
namespace {
void Options(int fd) {
#ifdef SO_NOSIGPIPE
  int one = 1;
  setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one));
#endif
  timeval timeout{2, 0};
  setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));
  setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout));
}
int Connect(const std::string &ip, int port = 9900) {
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0)
    return -1;
  Options(fd);
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons(uint16_t(port));
  if (inet_pton(AF_INET, ip.c_str(), &a.sin_addr) != 1) {
    close(fd);
    return -1;
  }
  int flags = fcntl(fd, F_GETFL, 0);
  fcntl(fd, F_SETFL, flags | O_NONBLOCK);
  int result = connect(fd, reinterpret_cast<sockaddr *>(&a), sizeof(a));
  if (result != 0) {
    pollfd p{fd, POLLOUT, 0};
    int e = 0;
    socklen_t n = sizeof(e);
    if (poll(&p, 1, 800) != 1 ||
        getsockopt(fd, SOL_SOCKET, SO_ERROR, &e, &n) != 0 || e) {
      close(fd);
      return -1;
    }
  }
  fcntl(fd, F_SETFL, flags);
  return fd;
}
bool Send(int fd, const std::string &data) {
  size_t at = 0;
  while (at < data.size()) {
    ssize_t n = send(fd, data.data() + at, data.size() - at, 0);
    if (n <= 0)
      return false;
    at += size_t(n);
  }
  return true;
}
bool Read(int fd, std::string &data, size_t count) {
  while (data.size() < count) {
    char b[4096];
    ssize_t n = recv(fd, b, std::min(sizeof(b), count - data.size()), 0);
    if (n <= 0)
      return false;
    data.append(b, size_t(n));
  }
  return true;
}
bool Receive(int fd, std::string &wire) {
  wire.clear();
  if (!Read(fd, wire, 12))
    return false;
  uint32_t n;
  std::memcpy(&n, wire.data() + 8, 4);
  n = ntohl(n);
  return n >= 12 && n <= 65536 && Read(fd, wire, n);
}
struct Client {
  int local = -1, remote = -1;
  std::mutex mutex;
  std::thread thread;
  std::atomic<bool> done{false};
};
class Gateway {
public:
  std::atomic<bool> quit{false};
  int listener = -1;
  std::thread acceptor;
  std::string ip;
  std::function<Route()> decide;
  std::function<void(const std::string &)> trace;
  std::vector<std::shared_ptr<Client>> clients;
  void Log(const std::string &s) {
    if (trace)
      trace("[pc-lan] " + s);
  }
  ~Gateway() {
    quit = true;
    if (listener >= 0)
      shutdown(listener, SHUT_RDWR);
    if (acceptor.joinable())
      acceptor.join();
    if (listener >= 0)
      close(listener);
    for (auto &c : clients) {
      std::lock_guard<std::mutex> l(c->mutex);
      if (c->local >= 0)
        shutdown(c->local, SHUT_RDWR);
      if (c->remote >= 0)
        shutdown(c->remote, SHUT_RDWR);
    }
    for (auto &c : clients)
      if (c->thread.joinable())
        c->thread.join();
  }
  void Finish(const std::shared_ptr<Client> &c) {
    {
      std::lock_guard<std::mutex> l(c->mutex);
      if (c->remote >= 0)
        close(c->remote);
      close(c->local);
      c->remote = c->local = -1;
    }
    c->done = true;
  }
  // Mobile lobby: its @dir reply already names the host's LAN lobby port,
  // which the game then reaches directly. Relay the bytes unchanged.
  void Pipe(const std::shared_ptr<Client> &c, const std::string &target) {
    int remote = Connect(target, 30960), local = c->local;
    {
      std::lock_guard<std::mutex> l(c->mutex);
      c->remote = remote;
    }
    if (remote < 0)
      Log("cannot reach lobby directory " + target + ":30960");
    char b[16384];
    while (remote >= 0 && !quit) {
      pollfd f[2] = {{local, POLLIN, 0}, {remote, POLLIN, 0}};
      int ready = poll(f, 2, 100);
      if (ready < 0)
        break;
      if (!ready)
        continue;
      bool ok = true;
      for (int side = 0; side < 2 && ok; ++side) {
        if (!f[side].revents)
          continue;
        ssize_t n = recv(f[side].fd, b, sizeof(b), 0);
        ok = n > 0 && Send(side ? local : remote, std::string(b, size_t(n)));
      }
      if (!ok)
        break;
    }
    Finish(c);
  }
  void Run(const std::shared_ptr<Client> &c) {
    Route route{ip, true};
    if (decide)
      route = decide();
    if (route.ip.empty()) {
      Log("no lobby available for this sign-in");
      Finish(c);
      return;
    }
    if (!route.pc) {
      Pipe(c, route.ip);
      return;
    }
    int remote = Connect(route.ip), local = c->local;
    {
      std::lock_guard<std::mutex> l(c->mutex);
      c->remote = remote;
    }
    std::string name, own;
    if (remote >= 0) {
      sockaddr_in a{};
      socklen_t n = sizeof(a);
      if (getsockname(remote, reinterpret_cast<sockaddr *>(&a), &n) == 0) {
        char text[INET_ADDRSTRLEN];
        if (inet_ntop(AF_INET, &a.sin_addr, text, sizeof(text)))
          own = text;
      }
    }
    while (remote >= 0 && !quit) {
      pollfd f[2] = {{local, POLLIN, 0}, {remote, POLLIN, 0}};
      int ready = poll(f, 2, 100);
      if (ready < 0)
        break;
      if (!ready)
        continue;
      bool ok = true;
      for (int side = 0; side < 2 && ok; ++side) {
        if (!f[side].revents)
          continue;
        std::string wire;
        if (!Receive(f[side].fd, wire)) {
          ok = false;
          break;
        }
        std::string command = wire.substr(0, 4), body = wire.substr(12);
        if (side == 0) {
          if (command == "auth")
            name = Field(body, "GTAG");
          // The game's connection is loopback; the PC must receive the real
          // source address of our backend socket, never127.0.0.1.
          if (command == "addr" && !own.empty())
            wire = Frame(command, Put(body, "ADDR", own));
          if (command == "pers" && Field(body, "PERS").empty()) {
            auto persona = Field(body, "GTAG");
            if (persona.empty())
              persona = name;
            if (!persona.empty()) {
              wire = Frame(command, Put(body, "PERS", persona));
              Log("added PC persona field");
            }
          }
          if ((command == "auth" || command == "pers") && !own.empty()) {
            auto loginBody = wire.substr(12);
            auto adapted = AdaptLogin(loginBody, own);
            if (adapted != loginBody) {
              wire = Frame(command, adapted, wire.substr(4, 4));
              Log("adapted local machine address for PC peers");
            }
          }
          if (command == "user") {
            auto persona = Field(body, "PERS");
            if (persona.empty())
              persona = name;
            ok = Send(local, LocalStats(persona));
            Log("supplied empty local LAN history (PC has no Xbox user "
                "endpoint)");
            continue;
          }
          if (command == "usea")
            Log("PC room search NAME=" + Field(body, "NAME") + " flags=" +
                Field(body, "CUSTFLAGS") + " mask=" + Field(body, "CUSTMASK"));
          if (command == "ujoi" || command == "gjoi" || command == "gget" ||
              command == "gset")
            Log("client " + command + " NAME=" + Field(body, "NAME") +
                " room=" + Field(body, "ROOM") +
                " ident=" + Field(body, "IDENT"));
          ok = Send(remote, wire);
        } else {
          if (command == "@dir" && wire.substr(4, 4) == std::string(4, '\0')) {
            body = Put(Put(body, "ADDR", "127.0.0.1"), "PORT", "30960");
            wire = Frame(command, body);
            Log("PC directory routed through in-app adapter");
          }
          if (command == "+uss" || command == "+ust" || command == "ujoi" ||
              command == "ucre" || command == "uadm") {
            auto adapted = AdaptRoom(body);
            if (adapted != body) {
              Log("aliased PC room build 192359 to Xbox room build 192641; "
                  "race compatibility unverified");
              body = std::move(adapted);
              wire = Frame(command, body, wire.substr(4, 4));
            }
          }
          if (command == "gjoi" || command == "gget" || command == "gset" ||
              command == "gcre" || command == "+mgm" || command == "+ses") {
            auto adapted = AdaptGame(body);
            if (adapted != body) {
              bool sessionAdded = Field(body, "SESS").empty() &&
                                  !Field(adapted, "SESS").empty();
              body = std::move(adapted);
              wire = Frame(command, body, wire.substr(4, 4));
              Log(sessionAdded ? "constructed local Xbox LAN session for PC "
                                 "host; peer connection unverified"
                               : "adapted PC game peer addresses");
            }
          }
          if (command == "onln" || command == "+who" || command == "+usr") {
            auto adapted = AdaptUser(body);
            if (adapted != body) {
              body = std::move(adapted);
              wire = Frame(command, body, wire.substr(4, 4));
              Log("adapted PC presence peer address");
            }
          }
          ok = Send(local, wire);
          if (command == "pers")
            Log("PC persona response received");
          if (command == "+uss" || command == "+ust")
            Log("PC room N=" + Field(body, "N") +
                " params=" + Field(body, "P"));
          if (command == "ujoi" || command == "gjoi" || command == "gget" ||
              command == "gset" || command == "+mgm" || command == "+ses")
            Log("PC " + command + " NAME=" + Field(body, "NAME") + " HOST=" +
                Field(body, "HOST") + " COUNT=" + Field(body, "COUNT") +
                " SESS_bytes=" + std::to_string(Field(body, "SESS").size()) +
                " PLATPARAMS_bytes=" +
                std::to_string(Field(body, "PLATPARAMS").size()));
          if (wire.substr(4, 4) != std::string(4, '\0'))
            Log("PC response " + command + " subtype=" + wire.substr(4, 4));
          if (wire.substr(4, 4) == "badc")
            Log("PC does not support command " + command);
        }
      }
      if (!ok)
        break;
    }
    Finish(c);
  }
  bool Begin() {
    listener = socket(AF_INET, SOCK_STREAM, 0);
    if (listener < 0)
      return false;
    Options(listener);
    int one = 1;
    setsockopt(listener, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons(30960);
    if (bind(listener, reinterpret_cast<sockaddr *>(&a), sizeof(a)) != 0 ||
        listen(listener, 4) != 0)
      return false;
    acceptor = std::thread([this] {
      while (!quit) {
        pollfd p{listener, POLLIN, 0};
        if (poll(&p, 1, 100) != 1)
          continue;
        int fd = accept(listener, nullptr, nullptr);
        if (fd < 0)
          continue;
        Options(fd);
        clients.erase(std::remove_if(clients.begin(), clients.end(),
                                     [](auto &c) {
                                       if (!c->done)
                                         return false;
                                       if (c->thread.joinable())
                                         c->thread.join();
                                       return true;
                                     }),
                      clients.end());
        if (clients.size() >= 8) {
          close(fd);
          continue;
        }
        auto c = std::make_shared<Client>();
        c->local = fd;
        clients.push_back(c);
        c->thread = std::thread([this, c] { Run(c); });
      }
    });
    Log(decide ? "ready: automatic lobby relay on 127.0.0.1:30960"
               : "ready: loopback adapter -> " + ip + ":9900");
    return true;
  }
};
std::mutex gatewayMutex;
std::unique_ptr<Gateway> gateway;
} // namespace
namespace {
bool ProbeDirectory(const std::string &ip, int port) {
  int fd = Connect(ip, port);
  if (fd < 0)
    return false;
  bool sent =
      Send(fd, Frame("@tic", "RC4+MD5-V2") +
                   Frame("@dir",
                         "REGN=NA\nCLST=192641\nNETV=0\nPROD=nfs-xbox-2006"));
  std::string wire;
  bool read = sent && Receive(fd, wire);
  close(fd);
  if (!read || wire.substr(0, 8) != std::string("@dir\0\0\0\0", 8))
    return false;
  in_addr address{};
  auto body = wire.substr(12);
  return Field(body, "PORT") == (port == 9900 ? "9900" : "10901") &&
         inet_pton(AF_INET, Field(body, "ADDR").c_str(), &address) == 1;
}
bool Launch(std::unique_ptr<Gateway> g) {
  for (int i = 0; i < 8; ++i) {
    if (g->Begin()) {
      gateway = std::move(g);
      return true;
    }
    auto next = std::make_unique<Gateway>();
    next->ip = g->ip;
    next->decide = g->decide;
    next->trace = g->trace;
    g = std::move(next);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  return false;
}
} // namespace
bool Probe(const std::string &ip) { return ProbeDirectory(ip, 9900); }
bool ProbeMobile(const std::string &ip) { return ProbeDirectory(ip, 30960); }
void Stop() {
  std::lock_guard<std::mutex> lock(gatewayMutex);
  ResetPeers();
  hosting = false;
  gateway.reset();
}
bool Start(const std::string &ip,
           std::function<void(const std::string &)> trace, std::string *error) {
  std::lock_guard<std::mutex> lock(gatewayMutex);
  ResetPeers();
  hosting = false;
  gateway.reset();
  auto g = std::make_unique<Gateway>();
  g->ip = ip;
  g->trace = trace;
  if (Launch(std::move(g))) {
    in_addr a{};
    if (inet_pton(AF_INET, ip.c_str(), &a) == 1) {
      std::lock_guard<std::mutex> l(peersMutex);
      // This device opens CommUDP towards the PC host's listener.
      peers = {{ntohl(a.s_addr), 0, 0, false, false, kConnector}};
      peerCount = 1;
    }
    return true;
  }
  if (error)
    *error = "Cannot start the PC LAN adapter on this device. Return to the "
             "launcher and retry.";
  return false;
}
bool StartAuto(std::function<Route()> decide,
               std::function<void(const std::string &)> trace,
               std::string *error) {
  std::lock_guard<std::mutex> lock(gatewayMutex);
  ResetPeers();
  hosting = false;
  gateway.reset();
  auto g = std::make_unique<Gateway>();
  g->decide = std::move(decide);
  g->trace = trace;
  if (Launch(std::move(g)))
    return true;
  if (error)
    *error = "Cannot start the LAN relay on this device. Return to the "
             "launcher and retry.";
  return false;
}
} // namespace nfsmw::pc
