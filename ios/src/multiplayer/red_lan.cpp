// Directly imported/adapted from victorgbd/NFSMW-Recompiled-Mobile,
// commit d534be88edf5bcd362445c84e5b79c61e29571e7 (GPL-3.0).
// Original Android LAN implementation and this C++ adaptation: victorgbd.
// Local integration/Darwin changes are recorded in docs/TECHNICAL.md.
// La red de la LAN del lanzador de iOS (red_lan.h).

#include "red_lan.h"

#include <arpa/inet.h>
#include <fcntl.h>
#include <ifaddrs.h>
#include <net/if.h>
#include <netdb.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <functional>
#include <cctype>
#include <chrono>
#include <cstring>
#include <regex>
#include <set>
#include <sstream>
#include <thread>

#ifndef SO_NOSIGPIPE
#define SO_NOSIGPIPE 0  // Linux, para las pruebas: alli no hay, y el SIGPIPE se ignora en la prueba
#endif

namespace nfsmw::red {

namespace {

constexpr int PLAZO_GAMERTAG_MS = 2000;
constexpr const char* PREGUNTA = "NFSMW_DISCOVER";
constexpr const char* RESPUESTA = "NFSMW_SERVER";
constexpr int PLAZO_BUSQUEDA_MS = 1500;
// Cuando se repite el broadcast, en ms desde el principio.
constexpr int RONDAS_MS[] = {0, 300, 700};
// Lo que se sigue escuchando tras la ultima pregunta a la /24, si acaba tarde.
constexpr int ULTIMA_MS = 400;
// Por si enviar se atasca: la busqueda nunca pasa de aqui.
constexpr int MAXIMO_MS = 5000;
// Las preguntas a IP sin nadie esperan al ARP: con el bufer normal, la /24 tarda en salir.
constexpr int BUFER_ENVIO = 1 << 20;

std::string Minusculas(std::string s) {
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return char(std::tolower(c)); });
  return s;
}

std::string Recortar(const std::string& s) {
  const auto a = s.find_first_not_of(" \t\r\n");
  if (a == std::string::npos) return "";
  const auto b = s.find_last_not_of(" \t\r\n");
  return s.substr(a, b - a + 1);
}

// 10/8, 172.16/12 y 192.168/16 (InetAddress.isSiteLocalAddress), en orden de host.
bool EsLocal(uint32_t ip) {
  return (ip >> 24) == 10 || (ip >> 20) == ((172u << 4) | 1) || (ip >> 16) == ((192u << 8) | 168);
}

std::string Texto(uint32_t ip_host) {
  in_addr a{};
  a.s_addr = htonl(ip_host);
  char b[INET_ADDRSTRLEN] = {};
  inet_ntop(AF_INET, &a, b, sizeof(b));
  return b;
}

void SinSigpipe(int s) {
  int uno = 1;
  setsockopt(s, SOL_SOCKET, SO_NOSIGPIPE, &uno, sizeof(uno));
}

// Las IPv4 de este telefono en redes locales (propias) y a donde preguntar: el broadcast de cada red
// y 255.255.255.255 (difusion) y, en redes /24 o menores, cada IP (red). En orden de host.
void Destinos(std::vector<uint32_t>& propias, std::vector<uint32_t>& difusion, std::vector<uint32_t>& red) {
  ifaddrs* lista = nullptr;
  if (getifaddrs(&lista) != 0) return;
  for (ifaddrs* i = lista; i; i = i->ifa_next) {
    if (!i->ifa_addr || i->ifa_addr->sa_family != AF_INET || !(i->ifa_flags & IFF_UP) ||
        (i->ifa_flags & IFF_LOOPBACK) || PuntosInterfaz(i->ifa_name) < 0) {
      continue;
    }
    const uint32_t ip = ntohl(reinterpret_cast<sockaddr_in*>(i->ifa_addr)->sin_addr.s_addr);
    if (!EsLocal(ip)) continue;
    propias.push_back(ip);
    if ((i->ifa_flags & IFF_BROADCAST) && i->ifa_broadaddr && i->ifa_broadaddr->sa_family == AF_INET) {
      difusion.push_back(ntohl(reinterpret_cast<sockaddr_in*>(i->ifa_broadaddr)->sin_addr.s_addr));
    }
    if (!i->ifa_netmask) continue;
    uint32_t mascara = ntohl(reinterpret_cast<sockaddr_in*>(i->ifa_netmask)->sin_addr.s_addr);
    const int prefijo = __builtin_popcount(mascara);
    if (prefijo > 30) continue;
    // Keep scans bounded even on a broad LAN; manual address supports peers
    // outside this device's /24 without scanning thousands of other machines.
    if (prefijo < 24) mascara = 0xFFFFFF00u;
    const uint32_t base = ip & mascara;
    for (uint32_t h = base + 1; h < (base | ~mascara); ++h) {
      if (h != ip) red.push_back(h);
    }
  }
  freeifaddrs(lista);
  if (!propias.empty()) difusion.push_back(0xFFFFFFFFu);
}

void Preguntar(int s, const std::vector<uint32_t>& destinos, const std::atomic<bool>& parar) {
  static const std::string pregunta = std::string(PREGUNTA) + "\n";
  for (uint32_t d : destinos) {
    if (parar.load()) return;
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(PUERTO_APP);
    a.sin_addr.s_addr = htonl(d);
    // Un destino sin ruta (o el broadcast, que iOS no deja sin su permiso de multicast): los demas
    // siguen.
    sendto(s, pregunta.data(), pregunta.size(), 0, reinterpret_cast<sockaddr*>(&a), sizeof(a));
  }
}

std::optional<Encontrado> Leer(const char* datos, size_t n, uint32_t de) {
  std::istringstream lineas(std::string(datos, n));
  std::string l;
  if (!std::getline(lineas, l) || Recortar(l) != RESPUESTA) return std::nullopt;
  Encontrado e;
  e.ip = Texto(de);
  while (std::getline(lineas, l)) {
    if (l.rfind("NAME=", 0) == 0) {
      e.nombre = Recortar(l.substr(5));
    } else if (l.rfind("PLAYERS=", 0) == 0) {
      e.jugadores = std::max(0, std::atoi(Recortar(l.substr(8)).c_str()));
    }
  }
  return e;
}

}  // namespace

bool IpValida(const std::string& ip) {
  int partes = 0;
  size_t desde = 0;
  while (true) {
    const size_t punto = ip.find('.', desde);
    const std::string parte = ip.substr(desde, punto == std::string::npos ? std::string::npos : punto - desde);
    if (parte.empty() || parte.size() > 3 || !std::all_of(parte.begin(), parte.end(), [](unsigned char c) { return std::isdigit(c) != 0; }) ||
        std::atoi(parte.c_str()) > 255) {
      return false;
    }
    ++partes;
    if (punto == std::string::npos) break;
    desde = punto + 1;
  }
  return partes == 4;
}

bool DireccionValida(const std::string& d) {
  if (d.empty() || d.size() > 253) return false;
  if (d.find_first_not_of("0123456789.") == std::string::npos) return IpValida(d);
  static const std::regex nombre("[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*",
                                 std::regex::icase);
  return std::regex_match(d, nombre);
}

std::string ResolverIpv4(const std::string& direccion) {
  if (IpValida(direccion)) return direccion;
  addrinfo pista{};
  pista.ai_family = AF_INET;
  pista.ai_socktype = SOCK_STREAM;
  addrinfo* r = nullptr;
  if (getaddrinfo(direccion.c_str(), nullptr, &pista, &r) != 0 || !r) return "";
  const uint32_t ip = ntohl(reinterpret_cast<sockaddr_in*>(r->ai_addr)->sin_addr.s_addr);
  freeaddrinfo(r);
  return Texto(ip);
}

std::string GamertagEfectivo(const std::string& gamertag) {
  const std::string g = Recortar(gamertag);
  return g.empty() ? "User" : g;
}

Comprobacion ComprobarGamertag(const std::string& ip, const std::string& gamertag) {
  sockaddr_in a{};
  a.sin_family = AF_INET;
  a.sin_port = htons(PUERTO_APP);
  if (inet_pton(AF_INET, ip.c_str(), &a.sin_addr) != 1) return Comprobacion::kSinRespuesta;
  const int s = socket(AF_INET, SOCK_STREAM, 0);
  if (s < 0) return Comprobacion::kSinRespuesta;
  SinSigpipe(s);
  // Conectar con plazo: sin bloquear, y se espera a que se pueda escribir.
  const int banderas = fcntl(s, F_GETFL, 0);
  fcntl(s, F_SETFL, banderas | O_NONBLOCK);
  bool conectado = connect(s, reinterpret_cast<sockaddr*>(&a), sizeof(a)) == 0;
  if (!conectado && errno == EINPROGRESS) {
    pollfd p{s, POLLOUT, 0};
    int error = 0;
    socklen_t largo = sizeof(error);
    conectado = poll(&p, 1, PLAZO_GAMERTAG_MS) == 1 && getsockopt(s, SOL_SOCKET, SO_ERROR, &error, &largo) == 0 &&
                error == 0;
  }
  Comprobacion r = Comprobacion::kSinRespuesta;
  if (conectado) {
    fcntl(s, F_SETFL, banderas);
    timeval plazo{PLAZO_GAMERTAG_MS / 1000, 0};
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &plazo, sizeof(plazo));
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, &plazo, sizeof(plazo));
    const std::string linea = "GAMERTAG " + GamertagEfectivo(gamertag) + "\n";
    if (send(s, linea.data(), linea.size(), 0) == ssize_t(linea.size())) {
      std::string respuesta;
      char c;
      while (respuesta.size() < 64 && recv(s, &c, 1, 0) == 1 && c != '\n') respuesta += c;
      respuesta = Recortar(respuesta);
      // Un servidor sin esta comprobacion (version vieja) cierra o no contesta: no se sabe.
      if (respuesta == "FREE") r = Comprobacion::kLibre;
      if (respuesta == "IN_USE") r = Comprobacion::kEnUso;
    }
  }
  close(s);
  return r;
}

static std::optional<std::vector<Encontrado>> BuscarPorUdp(
    const std::function<void(const std::string&)>& trace) {
  std::vector<uint32_t> propias, difusion, red;
  Destinos(propias, difusion, red);
  if (trace) {
    std::string addresses;
    for (auto ip : propias) addresses += Texto(ip) + " ";
    trace("[lan-discovery] own=" + addresses + " direct_targets=" + std::to_string(red.size()));
  }
  if (propias.empty()) return std::nullopt;
  std::vector<Encontrado> encontrados;
  const int s = socket(AF_INET, SOCK_DGRAM, 0);
  if (s < 0) return encontrados;
  // Bind explicitly before sending: reply handling does not depend on a
  // successful broadcast auto-binding the socket on iOS.
  sockaddr_in local{};
#if defined(__APPLE__)
  local.sin_len = sizeof(local);
#endif
  local.sin_family = AF_INET;
  if (bind(s, reinterpret_cast<sockaddr*>(&local), sizeof(local)) != 0) {
    if (trace) trace("[lan-discovery] UDP bind failed errno=" + std::to_string(errno));
    close(s); return encontrados;
  }
#if defined(__APPLE__)
  // Custom broadcast needs a restricted entitlement in LiveContainer. Keep
  // this socket unicast-only; TCP directories provide the portable fallback.
  difusion.clear();
#endif
  fcntl(s, F_SETFL, fcntl(s, F_GETFL, 0) | O_NONBLOCK);
  int uno = 1;
  setsockopt(s, SOL_SOCKET, SO_BROADCAST, &uno, sizeof(uno));
  int bufer = BUFER_ENVIO;
  setsockopt(s, SOL_SOCKET, SO_SNDBUF, &bufer, sizeof(bufer));

  using reloj = std::chrono::steady_clock;
  const auto inicio = reloj::now();
  auto pasado = [&] {
    return int(std::chrono::duration_cast<std::chrono::milliseconds>(reloj::now() - inicio).count());
  };
  // Las preguntas, en sus hilos (enviar puede bloquear), y las respuestas aqui mientras tanto.
  std::atomic<bool> parar{false}, rondasHechas{false}, barridoHecho{false};
  std::thread rondas([&] {
    for (int espera : RONDAS_MS) {
      const int falta = espera - pasado();
      if (falta > 0) std::this_thread::sleep_for(std::chrono::milliseconds(falta));
      Preguntar(s, difusion, parar);
    }
    rondasHechas = true;
  });
  std::thread barrido([&] {
    Preguntar(s, red, parar);
    barridoHecho = true;
  });

  std::set<std::string> vistas;
  int finEnvio = -1;
  int received = 0, rejected = 0, receiveError = 0;
  char buf[512];
  while (true) {
    const int ahora = pasado();
    if (finEnvio < 0 && rondasHechas && barridoHecho) finEnvio = ahora;
    const int plazo = finEnvio < 0 ? MAXIMO_MS : std::min(MAXIMO_MS, std::max(PLAZO_BUSQUEDA_MS, finEnvio + ULTIMA_MS));
    if (ahora >= plazo) break;
    pollfd p{s, POLLIN, 0};
    if (poll(&p, 1, std::max(1, std::min(100, plazo - ahora))) != 1) continue;
    sockaddr_in de{};
    socklen_t largo = sizeof(de);
    const ssize_t n = recvfrom(s, buf, sizeof(buf), 0, reinterpret_cast<sockaddr*>(&de), &largo);
    if (n <= 0) { if (n < 0) receiveError = errno; continue; }
    ++received;
    const uint32_t ip = ntohl(de.sin_addr.s_addr);
    if (std::find(propias.begin(), propias.end(), ip) != propias.end()) continue;
    if (auto e = Leer(buf, size_t(n), ip); e && vistas.insert(e->ip).second) encontrados.push_back(*e);
    else ++rejected;
  }
  parar = true;
  rondas.join();
  barrido.join();
  close(s);
  if (trace) trace("[lan-discovery] UDP received=" + std::to_string(received) +
      " rejected=" + std::to_string(rejected) + " hosts=" + std::to_string(encontrados.size()) +
      " last_recv_errno=" + std::to_string(receiveError));
  return encontrados;
}

// Unicast fallback for iOS/LiveContainer environments where discovery replies
// do not reach the UDP socket. Query the existing Aries directory; Android and
// Python hosts already support it. No new server protocol or account reservation.
static std::vector<Encontrado> BuscarPorTcp(const std::vector<uint32_t>& targets,
                                           const std::function<void(const std::string&)>& trace) {
  using Clock = std::chrono::steady_clock;
  struct Probe {
    int fd;
    uint32_t ip;
    Clock::time_point deadline;
    bool connected = false;
    size_t written = 0;
    std::vector<uint8_t> received;
  };
  const auto deadline = Clock::now() + std::chrono::seconds(4);
  constexpr size_t kConcurrent = 32;
  constexpr int kDirectoryPort = 30960;
  std::vector<Probe> active;
  std::vector<Encontrado> hosts;
  size_t next = 0, attempts = 0, connected = 0;
  int lastError = 0;
  const std::string body = std::string("PROD=nfs-xbox-2006\n") + '\0';
  std::vector<uint8_t> request(12 + body.size(), 0);
  std::memcpy(request.data(), "@dir", 4);
  const uint32_t length = uint32_t(request.size());
  request[8] = uint8_t(length >> 24); request[9] = uint8_t(length >> 16);
  request[10] = uint8_t(length >> 8); request[11] = uint8_t(length);
  std::memcpy(request.data() + 12, body.data(), body.size());
  auto closeProbe = [](Probe& p) { if (p.fd >= 0) close(p.fd); p.fd = -1; };
  while ((next < targets.size() || !active.empty()) && Clock::now() < deadline) {
    while (active.size() < kConcurrent && next < targets.size()) {
      uint32_t ip = targets[next++];
      int s = socket(AF_INET, SOCK_STREAM, 0);
      if (s < 0) { lastError = errno; continue; }
      ++attempts;
      SinSigpipe(s);
      if (fcntl(s, F_SETFL, fcntl(s, F_GETFL, 0) | O_NONBLOCK) != 0) {
        lastError = errno; close(s); continue;
      }
      sockaddr_in to{};
#if defined(__APPLE__)
      to.sin_len = sizeof(to);
#endif
      to.sin_family = AF_INET; to.sin_port = htons(kDirectoryPort); to.sin_addr.s_addr = htonl(ip);
      int result = connect(s, reinterpret_cast<sockaddr*>(&to), sizeof(to));
      if (result != 0 && errno != EINPROGRESS) { lastError = errno; close(s); continue; }
      active.push_back({s, ip, Clock::now() + std::chrono::milliseconds(350)});
    }
    std::vector<pollfd> polls;
    for (auto& p : active) polls.push_back({p.fd, short(p.written == request.size() ? POLLIN : POLLOUT), 0});
    if (polls.empty()) continue;
    int count = poll(polls.data(), polls.size(), 25);
    if (count < 0 && errno != EINTR) { lastError = errno; break; }
    for (size_t i = 0; i < active.size(); ++i) {
      auto& p = active[i];
      if (Clock::now() >= p.deadline) { closeProbe(p); continue; }
      if (!polls[i].revents) continue;
      if (polls[i].revents & POLLNVAL) { closeProbe(p); continue; }
      if (!p.connected) {
        int error = 0; socklen_t size = sizeof(error);
        if (getsockopt(p.fd, SOL_SOCKET, SO_ERROR, &error, &size) != 0 || error != 0) {
          lastError = error ? error : errno; closeProbe(p); continue;
        }
        p.connected = true; ++connected;
      }
      if (p.written < request.size()) {
        ssize_t n = send(p.fd, request.data() + p.written, request.size() - p.written, 0);
        if (n > 0) p.written += size_t(n);
        else if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
          lastError = errno; closeProbe(p); continue;
        }
      }
      if (p.written != request.size()) continue;
      uint8_t buf[4096];
      ssize_t n = recv(p.fd, buf, sizeof(buf), 0);
      if (n > 0) p.received.insert(p.received.end(), buf, buf + n);
      else if (n == 0) { closeProbe(p); continue; }
      else if (errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
        lastError = errno; closeProbe(p); continue;
      }
      if (p.received.size() > 4096) { closeProbe(p); continue; }
      if (p.received.size() < 12) continue;
      const auto& r = p.received;
      uint32_t size = uint32_t(r[8]) << 24 | uint32_t(r[9]) << 16 | uint32_t(r[10]) << 8 | r[11];
      if (std::memcmp(r.data(), "@dir\0\0\0\0", 8) != 0 || size < 12 || size > 4096) {
        closeProbe(p); continue;
      }
      if (r.size() < size) continue;
      std::istringstream fields(std::string(reinterpret_cast<const char*>(r.data() + 12), size - 12));
      std::string line, address; int port = 0;
      while (std::getline(fields, line)) {
        if (line.rfind("ADDR=", 0) == 0) address = Recortar(line.substr(5));
        if (line.rfind("PORT=", 0) == 0) port = std::atoi(line.substr(5).c_str());
      }
      if (port == 10901 && IpValida(address)) {
        hosts.push_back({Texto(p.ip), "LAN host", -1});
        if (trace) trace("[lan-discovery] TCP directory verified " + Texto(p.ip));
      }
      closeProbe(p);
    }
    active.erase(std::remove_if(active.begin(), active.end(), [](const Probe& p) { return p.fd < 0; }), active.end());
  }
  for (auto& p : active) closeProbe(p);
  if (trace) trace("[lan-discovery] TCP attempted=" + std::to_string(attempts) +
      " connected=" + std::to_string(connected) + " hosts=" + std::to_string(hosts.size()) +
      " last_errno=" + std::to_string(lastError));
  return hosts;
}

std::optional<std::vector<Encontrado>> BuscarServidores(
    std::function<void(const std::string&)> trace) {
  auto found = BuscarPorUdp(trace);
  if (!found || !found->empty()) return found;
  if (trace) trace("[lan-discovery] no UDP replies accepted; checking TCP directories");
  std::vector<uint32_t> own, broadcast, targets;
  Destinos(own, broadcast, targets);
  targets.erase(std::remove_if(targets.begin(), targets.end(), [&](uint32_t ip) {
    return std::find(own.begin(), own.end(), ip) != own.end();
  }), targets.end());
  std::sort(targets.begin(), targets.end());
  targets.erase(std::unique(targets.begin(), targets.end()), targets.end());
  // Nearby addresses first, then wrap. Also bounds broader networks to a /24.
  if (!own.empty()) {
    uint32_t pivot = own.front();
    std::stable_sort(targets.begin(), targets.end(), [pivot](uint32_t a, uint32_t b) {
      return uint8_t(a - pivot) < uint8_t(b - pivot);
    });
  }
  *found = BuscarPorTcp(targets, trace);
  return found;
}

int PuntosInterfaz(const std::string& nombre) {
  const std::string n = Minusculas(nombre);
  if (n == "en0") return 3;                           // la Wi-Fi
  if (n.rfind("bridge", 0) == 0) return 2;            // el punto de acceso personal
  if (n.rfind("en", 0) == 0) return 1;                // un adaptador de cable
  for (const char* fuera : {"pdp_ip", "utun", "ipsec", "awdl", "llw", "anpi", "ap", "gif", "stf", "xhc"}) {
    if (n.rfind(fuera, 0) == 0) return -1;            // datos moviles, VPN, AirDrop...
  }
  return 0;
}

std::string IpLocal() {
  ifaddrs* lista = nullptr;
  if (getifaddrs(&lista) != 0) return "";
  std::string mejor;
  int mejorPuntos = -1;
  for (ifaddrs* i = lista; i; i = i->ifa_next) {
    if (!i->ifa_addr || i->ifa_addr->sa_family != AF_INET || !(i->ifa_flags & IFF_UP) ||
        (i->ifa_flags & IFF_LOOPBACK)) {
      continue;
    }
    const int puntos = PuntosInterfaz(i->ifa_name);
    const uint32_t ip = ntohl(reinterpret_cast<sockaddr_in*>(i->ifa_addr)->sin_addr.s_addr);
    if (puntos > mejorPuntos && EsLocal(ip)) {
      mejor = Texto(ip);
      mejorPuntos = puntos;
    }
  }
  freeifaddrs(lista);
  return mejor;
}

}  // namespace nfsmw::red
