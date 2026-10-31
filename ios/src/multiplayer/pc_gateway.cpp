// Native PC LAN adaptation. Protocol evidence/credits: docs/TECHNICAL.md.
// Uses the original PC server unchanged; Xbox persona and offline-LAN stats
// differences are handled locally. Never rewrites peer/race payloads.
#include "pc_gateway.h"
#include <algorithm>
#include <arpa/inet.h>
#include <atomic>
#include <chrono>
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
int Connect(const std::string &ip) {
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0)
    return -1;
  Options(fd);
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons(9900);
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
  void Run(const std::shared_ptr<Client> &c) {
    int remote = Connect(ip), local = c->local;
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
          ok = Send(remote, wire);
        } else {
          if (command == "@dir" && wire.substr(4, 4) == std::string(4, '\0')) {
            body = Put(Put(body, "ADDR", "127.0.0.1"), "PORT", "30960");
            wire = Frame(command, body);
            Log("PC directory routed through in-app adapter");
          }
          ok = Send(local, wire);
          if (command == "pers")
            Log("PC persona response received");
          if (command == "+uss" || command == "+ust")
            Log("PC room N=" + Field(body, "N") +
                " params=" + Field(body, "P"));
          if (wire.substr(4, 4) == "badc")
            Log("PC does not support command " + command);
        }
      }
      if (!ok)
        break;
    }
    {
      std::lock_guard<std::mutex> l(c->mutex);
      if (c->remote >= 0)
        close(c->remote);
      close(c->local);
      c->remote = c->local = -1;
    }
    c->done = true;
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
    Log("ready: loopback adapter -> " + ip + ":9900");
    return true;
  }
};
std::mutex gatewayMutex;
std::unique_ptr<Gateway> gateway;
} // namespace
bool Probe(const std::string &ip) {
  int fd = Connect(ip);
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
  return Field(body, "PORT") == "9900" &&
         inet_pton(AF_INET, Field(body, "ADDR").c_str(), &address) == 1;
}
void Stop() {
  std::lock_guard<std::mutex> lock(gatewayMutex);
  gateway.reset();
}
bool Start(const std::string &ip,
           std::function<void(const std::string &)> trace, std::string *error) {
  std::lock_guard<std::mutex> lock(gatewayMutex);
  gateway.reset();
  for (int i = 0; i < 8; ++i) {
    auto g = std::make_unique<Gateway>();
    g->ip = ip;
    g->trace = trace;
    if (g->Begin()) {
      gateway = std::move(g);
      return true;
    }
    g.reset();
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  if (error)
    *error = "Cannot start the PC LAN adapter on this device. Return to the "
             "launcher and retry.";
  return false;
}
} // namespace nfsmw::pc
