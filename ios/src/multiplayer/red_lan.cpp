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
    const uint32_t mascara = ntohl(reinterpret_cast<sockaddr_in*>(i->ifa_netmask)->sin_addr.s_addr);
    const int prefijo = __builtin_popcount(mascara);
    if (prefijo < 24 || prefijo > 30) continue;
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

std::optional<std::vector<Encontrado>> BuscarServidores() {
  std::vector<uint32_t> propias, difusion, red;
  Destinos(propias, difusion, red);
  if (propias.empty()) return std::nullopt;
  std::vector<Encontrado> encontrados;
  const int s = socket(AF_INET, SOCK_DGRAM, 0);
  if (s < 0) return encontrados;
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
    if (n <= 0) continue;
    const uint32_t ip = ntohl(de.sin_addr.s_addr);
    if (std::find(propias.begin(), propias.end(), ip) != propias.end()) continue;
    if (auto e = Leer(buf, size_t(n), ip); e && vistas.insert(e->ip).second) encontrados.push_back(*e);
  }
  parar = true;
  rondas.join();
  barrido.join();
  close(s);
  return encontrados;
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
