// Uses victorgbd's original Android-compatible lobby protocol and C++ adaptation.
#include "lan_session.h"
#include "red_lan.h"
#include "servidor_ea.h"
#include "pc_gateway.h"
#include "../boot_trace.h"
#include <arpa/inet.h>
#include <atomic>
#include <cstdlib>
#include <mutex>
#include <optional>
#include <thread>
#include <chrono>

namespace nfsmw::lan {
namespace {
using Clock = std::chrono::steady_clock;
void Log(const std::string& s) { boot::Trace("[lan-auto] " + s); }
uint32_t Number(const std::string& ip) {
  in_addr a{};
  return inet_pton(AF_INET, ip.c_str(), &a) == 1 ? ntohl(a.s_addr) : 0;
}
bool StartServer(const std::string& own, const std::string& gamertag,
                 const std::filesystem::path& docs, bool pc, std::string* error) {
  std::error_code ec;
  std::filesystem::create_directories(docs / "data/lan_server", ec);
  if (ec) { *error = "Cannot create the LAN server's data folder: " + ec.message(); return false; }
  std::filesystem::create_directories(docs / "logs", ec);
  // Upstream stops its listener threads at their next 500 ms poll. Switching
  // Host/Join must allow those sockets to close before rebinding the ports.
  for (int attempt = 0; attempt < 8; ++attempt) {
    if (attempt) std::this_thread::sleep_for(std::chrono::milliseconds(100));
    auto name = [gamertag] { return red::GamertagEfectivo(gamertag); };
    if (pc ? servidor::ArrancarPC((docs / "data/lan_server").string(), (docs / "logs").string(),
                                  [] {}, name, own, error)
           : servidor::Arrancar((docs / "data/lan_server").string(), (docs / "logs").string(),
                                [] {}, name, error)) {
      error->clear();
      return true;
    }
  }
  *error = "Cannot start the LAN server: " + *error;
  return false;
}
// Automatic LAN state. decide() runs on relay threads; one decision at a time.
struct Auto {
  std::mutex mutex;
  std::string gamertag;
  std::filesystem::path docs;
  pc::Route route;
  Clock::time_point when{};
  std::atomic<bool> polling{false};
  std::thread poll;
  void StopPoll() {
    polling = false;
    if (poll.joinable()) poll.join();
  }
  // iOS host tells its guests which room members are native PCs.
  void StartPoll(const std::string& host) {
    StopPoll();
    polling = true;
    poll = std::thread([this, host] {
      std::vector<uint32_t> last;
      bool first = true;
      while (polling) {
        auto list = red::PcPeers(host);
        pc::SetGuestPeers(list);
        if (first || list != last) Log("PC peers in host room: " + std::to_string(list.size()));
        last = list; first = false;
        for (int i = 0; i < 10 && polling; ++i) std::this_thread::sleep_for(std::chrono::milliseconds(100));
      }
    });
  }
  std::optional<red::Encontrado> Pick(const std::vector<red::Encontrado>& found) {
    // Prefer a mobile lobby (phones and PCs can join it), lowest address
    // first so every device makes the same choice.
    std::optional<red::Encontrado> best;
    for (const auto& h : found) {
      if (!Number(h.ip)) continue;
      if (!best || (best->pc && !h.pc) || (best->pc == h.pc && Number(h.ip) < Number(best->ip))) best = h;
    }
    return best;
  }
  pc::Route Join(const red::Encontrado& host) {
    servidor::Parar();
    if (host.pc) {
      pc::SetGuestPeers({Number(host.ip)});
      Log("joining PC lobby " + host.ip);
    } else {
      pc::SetGuestPeers({});
      if (red::ComprobarGamertag(host.ip, gamertag) == red::Comprobacion::kEnUso)
        Log("player name already used in " + host.ip + "; joining anyway");
      StartPoll(host.ip);
      Log("joining mobile lobby " + host.ip);
    }
    return {host.ip, host.pc};
  }
  pc::Route Decide() {
    std::lock_guard<std::mutex> lock(mutex);
    const auto now = Clock::now();
    // Follow-up connections of one sign-in (a PC lobby reconnects through
    // the relay right after its directory reply) keep the same lobby.
    if (!route.ip.empty() && now - when < std::chrono::seconds(20)) {
      when = now;
      return route;
    }
    const std::string own = red::IpLocal();
    if (!red::IpValida(own)) {
      Log("no Wi-Fi or hotspot address");
      return route = {};
    }
    // Never drop players who are already in this device's lobby.
    if (route.ip == own && servidor::EnMarcha() && servidor::Jugadores() > 0) {
      Log("still hosting " + std::to_string(servidor::Jugadores()) + " players");
      when = now;
      return route;
    }
    StopPoll();
    Log("sign-in: looking for a nearby lobby");
    auto found = red::BuscarServidores([](const std::string& line) { boot::Trace(line); }, true);
    if (auto host = found ? Pick(*found) : std::nullopt) {
      route = Join(*host);
      when = Clock::now();
      return route;
    }
    std::string error;
    if (!servidor::EnMarcha()) {
      pc::StartHosting();
      if (!StartServer(own, gamertag, docs, true, &error)) {
        Log(error);
        return route = {};
      }
    }
    Log("no lobby found; hosting for phones and PCs at " + own);
    // Two devices signing in together may both host. Look again once this
    // lobby is visible; the higher address joins the lower one.
    std::this_thread::sleep_for(std::chrono::milliseconds(300 + arc4random_uniform(700)));
    found = red::BuscarServidores({}, true);
    if (auto rival = found ? Pick(*found) : std::nullopt;
        rival && !rival->pc && Number(rival->ip) < Number(own) && servidor::Jugadores() == 0) {
      Log("another device started hosting at the same time");
      route = Join(*rival);
    } else {
      route = {own, false};
    }
    when = Clock::now();
    return route;
  }
};
Auto& State() {
  static Auto* state = new Auto;  // relay threads may outlive static destruction
  return *state;
}
}  // namespace

Prepared Prepare(const std::string& mode, const std::string& server,
                 const std::string& gamertag, const std::filesystem::path& docs) {
  Prepared result;
  // Launch rechecks preflight; retain a PC already connected in the launcher.
  const bool keepPcHost = mode == "host_pc" && pc::Hosting() && servidor::EnMarcha();
  if (!keepPcHost) pc::Stop();
  State().StopPoll();  // relay threads (and so decide()) have finished
  if (mode == "off") {
    servidor::Parar();
    return result;
  }
  if (mode == "auto") {
    servidor::Parar();
    auto& state = State();
    {
      std::lock_guard<std::mutex> lock(state.mutex);
      state.gamertag = gamertag;
      state.docs = docs;
      state.route = {};
    }
    result.own_ip = red::IpLocal();
    if (!red::IpValida(result.own_ip)) {
      result.error = "Connect to Wi-Fi or a local hotspot before playing on LAN.";
      return result;
    }
    result.ip = "127.0.0.1";
    pc::StartAuto([] { return State().Decide(); },
                  [](const std::string& line) { boot::Trace(line); }, &result.error);
    return result;
  }
  if (mode != "host" && mode != "host_pc" && mode != "join") {
    result.error = "Choose Off, Automatic or Join for LAN multiplayer.";
    return result;
  }
  result.hosting = mode == "host" || mode == "host_pc";
  if (mode == "host_pc" && !keepPcHost) pc::StartHosting();
  if (!result.hosting && !red::DireccionValida(server)) {
    result.error = "Enter a complete IPv4 address or local hostname for the LAN server.";
    return result;
  }
  result.ip = result.hosting ? red::IpLocal() : red::ResolverIpv4(server);
  if (!red::IpValida(result.ip) || result.ip.rfind("127.", 0) == 0 || result.ip == "0.0.0.0") {
    result.error = result.hosting ? "Connect to Wi-Fi or a local hotspot before hosting."
                                 : "Enter the LAN server's IPv4 address or local hostname.";
    return result;
  }
  result.own_ip = result.hosting ? result.ip : red::IpHacia(result.ip);
  if (!result.hosting && result.ip == result.own_ip) {
    result.error = "That is this device's address. Choose Host here, or join the address shown on the OTHER device.";
    return result;
  }
  if (result.hosting) {
    if (!StartServer(result.ip, gamertag, docs, mode == "host_pc", &result.error)) return result;
  } else {
    servidor::Parar();
  }
  // Native PC hosts have no custom launcher/gamertag service on10902. iOS
  // hosts also answer the PC directory port, so check the mobile one first.
  if (!result.hosting && !pc::ProbeMobile(result.ip) && pc::Probe(result.ip)) {
    result.pc = true;
    if (!pc::Start(result.ip, [](const std::string& line) { boot::Trace(line); }, &result.error)) return result;
    return result;
  }
  const auto tag = red::ComprobarGamertag(result.ip, gamertag);
  if (tag == red::Comprobacion::kEnUso)
    result.error = "That gamertag is already in use. Choose a different name.";
  else if (tag == red::Comprobacion::kSinRespuesta)
    result.error = "The LAN server did not answer. Check its address, local-network permission and Wi-Fi connection.";
  if (!result.error.empty() && result.hosting) { servidor::Parar(); pc::Stop(); }
  return result;
}
}
