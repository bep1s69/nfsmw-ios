// Uses victorgbd's original Android-compatible lobby protocol and C++ adaptation.
#include "lan_session.h"
#include "red_lan.h"
#include "servidor_ea.h"
#include "pc_gateway.h"
#include "../boot_trace.h"
#include <thread>
#include <chrono>

namespace nfsmw::lan {
Prepared Prepare(const std::string& mode, const std::string& server,
                 const std::string& gamertag, const std::filesystem::path& docs) {
  Prepared result;
  pc::Stop();
  if (mode == "off") {
    servidor::Parar();
    return result;
  }
  if (mode != "host" && mode != "join") {
    result.error = "Choose Off, Host or Join for LAN multiplayer.";
    return result;
  }
  result.hosting = mode == "host";
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
    std::error_code ec;
    std::filesystem::create_directories(docs / "data/lan_server", ec);
    if (ec) { result.error = "Cannot create the LAN server's data folder: " + ec.message(); return result; }
    std::filesystem::create_directories(docs / "logs", ec);
    bool started = false;
    // Upstream stops its listener threads at their next 500 ms poll. Switching
    // Host/Join must allow those sockets to close before rebinding the ports.
    for (int attempt = 0; attempt < 8 && !started; ++attempt) {
      if (attempt) std::this_thread::sleep_for(std::chrono::milliseconds(100));
      started = servidor::Arrancar((docs / "data/lan_server").string(), (docs / "logs").string(),
          [] {}, [gamertag] { return red::GamertagEfectivo(gamertag); }, &result.error);
    }
    if (!started) {
      result.error = "Cannot start the LAN server: " + result.error;
      return result;
    }
    result.error.clear();
  } else {
    servidor::Parar();
  }
  // Native PC hosts have no custom launcher/gamertag service on10902.
  // Detect their real directory first, including hosts with an old helper.
  if (!result.hosting && pc::Probe(result.ip)) {
    result.pc = true;
    if (!pc::Start(result.ip, [](const std::string& line) { boot::Trace(line); }, &result.error)) return result;
    return result;
  }
  const auto tag = red::ComprobarGamertag(result.ip, gamertag);
  if (tag == red::Comprobacion::kEnUso)
    result.error = "That gamertag is already in use. Choose a different name.";
  else if (tag == red::Comprobacion::kSinRespuesta)
    result.error = "The LAN server did not answer. Check its address, local-network permission and Wi-Fi connection.";
  if (!result.error.empty() && result.hosting) servidor::Parar();
  return result;
}
}
