// Directly imported/adapted from victorgbd/NFSMW-Recompiled-Mobile,
// commit d534be88edf5bcd362445c84e5b79c61e29571e7 (GPL-3.0).
// Original Android LAN implementation and this C++ adaptation: victorgbd.
// Local integration/Darwin changes are recorded in docs/TECHNICAL.md.
// El servidor de salas de EA de la LAN de la app de iOS (servidor_ea.h): el ServidorEa.java de la
// app de Android, que es a su vez el ea_server.py de nfsmw-server-lan (version del commit 9ebeb11,
// 2026-10-16). Un cambio de protocolo hay que hacerlo en los tres. El protocolo y lo que costo cada
// mensaje estan en el README de ese proyecto y en docs/diario/red-y-privilegios.md; aqui solo lo que
// cambia al pasarlo a C++:
//  - Un hilo por conexion y un candado (recursivo, como el synchronized de Java) para todo lo que
//    toca salas, partidas y sesiones. Las respuestas se escriben dentro del candado, asi que en cada
//    socket salen en el mismo orden que en Java y en Python.
//  - Las sesiones, salas y partidas van en shared_ptr: en Java una sesion que se fue sigue en la
//    lista de alguna partida vieja hasta que el recolector la quita, y escribirle no hace nada.
//  - Las estadisticas (stats.json, races.jsonl) con nlohmann::ordered_json, que viene con el SDK
//    (inja): el mismo formato y el mismo orden de claves que el json de Python.
// Es C++ y POSIX sin nada de Apple: se puede compilar y probar en Linux (prueba_servidor_ea.py).

#include "red_lan.h"
#include "servidor_ea.h"
#include "pc_gateway.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <cerrno>
#include <chrono>
#include <climits>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include <nlohmann/json.hpp>

#ifndef SO_NOSIGPIPE
#define SO_NOSIGPIPE 0  // Linux, para las pruebas: alli no hay, y el SIGPIPE se ignora en la prueba
#endif

namespace nfsmw::servidor {

namespace {

constexpr int PUERTO_DIRECTORIO = 30960;
constexpr int PUERTO_SALAS = 10901;
// No es de EA: la app pregunta aqui si un gamertag esta libre (y busca servidores, por UDP).
constexpr int PUERTO_GAMERTAG = red::PUERTO_APP;
// Lo que un gamertag comprobado queda apartado para el telefono que pregunto.
constexpr auto APARTADO = std::chrono::minutes(10);
constexpr long REGISTRO_MAX = 4L << 20;
// Lo que espera un accept o la busqueda antes de mirar si hay que parar.
constexpr int VUELTA_MS = 500;

using Reloj = std::chrono::steady_clock;

// Un mapa ordenado de clave = valor, como el LinkedHashMap de Java: poner una clave que ya esta
// cambia su valor sin moverla.
using Campos = std::vector<std::pair<std::string, std::string>>;

const std::string* Buscar(const Campos& f, const std::string& clave) {
  for (const auto& [k, v] : f) {
    if (k == clave) return &v;
  }
  return nullptr;
}
std::string Valor(const Campos& f, const std::string& clave, const std::string& porDefecto) {
  const std::string* v = Buscar(f, clave);
  return v ? *v : porDefecto;
}
void Poner(Campos& f, const std::string& clave, std::string valor) {
  for (auto& [k, v] : f) {
    if (k == clave) {
      v = std::move(valor);
      return;
    }
  }
  f.emplace_back(clave, std::move(valor));
}
bool Vacio(const std::string* s) { return !s || s->empty(); }
// Lo que pondria Java al escribir un valor que puede no estar: "null".
std::string ONull(const std::string* s) { return s ? *s : "null"; }

std::string Recortar(const std::string& s) {
  const auto a = s.find_first_not_of(" \t\r\n");
  if (a == std::string::npos) return "";
  return s.substr(a, s.find_last_not_of(" \t\r\n") - a + 1);
}

// Integer.parseInt: entero con signo, entero de 32 bits y nada mas.
std::optional<int> Numero(const std::string& s) {
  if (s.empty()) return std::nullopt;
  errno = 0;
  char* fin = nullptr;
  const long v = std::strtol(s.c_str(), &fin, 10);
  if (errno || *fin || fin == s.c_str() || v < INT_MIN || v > INT_MAX || std::isspace((unsigned char)s[0])) {
    return std::nullopt;
  }
  return int(v);
}
int Entero(const std::string* s, int porDefecto) {
  if (Vacio(s)) return porDefecto;
  return Numero(Recortar(*s)).value_or(porDefecto);
}

std::string Minusculas(std::string s) {
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return char(std::tolower(c)); });
  return s;
}

std::string Hex(const uint8_t* b, size_t n) {
  static const char* const cifras = "0123456789abcdef";
  std::string s;
  for (size_t i = 0; i < n; ++i) {
    s += cifras[b[i] >> 4];
    s += cifras[b[i] & 15];
  }
  return s;
}

std::string AzarHex() {
  uint8_t b[16];
  arc4random_buf(b, sizeof(b));
  return Hex(b, sizeof(b));
}

std::string Ahora(const char* formato) {
  const std::time_t t = std::time(nullptr);
  std::tm local{};
  localtime_r(&t, &local);
  char b[64];
  std::strftime(b, sizeof(b), formato, &local);
  return b;
}
// yyyy.MM.dd-HH:mm:ss, el formato de fechas del protocolo.
std::string Fecha() { return Ahora("%Y.%m.%d-%H:%M:%S"); }
// HH:mm:ss.SSS, la del registro.
std::string Hora() {
  const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                      std::chrono::system_clock::now().time_since_epoch()).count() % 1000;
  char b[8];
  std::snprintf(b, sizeof(b), ".%03d", int(ms));
  return Ahora("%H:%M:%S") + b;
}

// urllib.parse.unquote: los %XX y nada mas (un '+' se queda, que en base64 cuenta). Como en Java,
// un %XX al final del todo no se cambia.
std::string Desescapar(const std::string& s) {
  if (s.find('%') == std::string::npos) return s;
  std::string b;
  for (size_t i = 0; i < s.size(); ++i) {
    if (s[i] == '%' && i + 2 < s.size() && std::isxdigit((unsigned char)s[i + 1]) && std::isxdigit((unsigned char)s[i + 2])) {
      b += char(std::strtol(s.substr(i + 1, 2).c_str(), nullptr, 16));
      i += 2;
    } else {
      b += s[i];
    }
  }
  return b;
}

// Base64.getDecoder(): sin relleno vale; nullopt si no es base64.
std::optional<std::vector<uint8_t>> Base64(const std::string& s) {
  auto valor = [](char c) -> int {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
  };
  std::vector<uint8_t> d;
  uint32_t acumulado = 0;
  int bits = 0, cifras = 0;
  size_t i = 0;
  for (; i < s.size() && s[i] != '='; ++i) {
    const int v = valor(s[i]);
    if (v < 0) return std::nullopt;
    acumulado = (acumulado << 6) | uint32_t(v);
    bits += 6;
    ++cifras;
    if (bits >= 8) {
      bits -= 8;
      d.push_back(uint8_t(acumulado >> bits));
    }
  }
  if (cifras % 4 == 1) return std::nullopt;
  // El relleno: solo el que toca, y al final.
  size_t relleno = 0;
  for (; i < s.size(); ++i) {
    if (s[i] != '=') return std::nullopt;
    ++relleno;
  }
  if (relleno && (cifras + relleno) % 4 != 0) return std::nullopt;
  return d;
}

// Cabecera de 12 bytes (orden, subcodigo, largo) y CLAVE=valor\n... con un 0 al final.
using Mensaje = std::vector<uint8_t>;
Mensaje Crear(const std::string& orden, const Campos& campos, const char* sub = nullptr) {
  std::string cuerpo;
  for (const auto& [k, v] : campos) cuerpo += k + "=" + v + "\n";
  const size_t largo = 12 + cuerpo.size() + 1;
  Mensaje m(largo, 0);
  std::memcpy(m.data(), orden.data(), std::min<size_t>(4, orden.size()));
  if (sub) std::memcpy(m.data() + 4, sub, 4);
  m[8] = uint8_t(largo >> 24);
  m[9] = uint8_t(largo >> 16);
  m[10] = uint8_t(largo >> 8);
  m[11] = uint8_t(largo);
  std::memcpy(m.data() + 12, cuerpo.data(), cuerpo.size());
  return m;
}

Campos LeerCampos(const uint8_t* b, size_t desde, size_t hasta) {
  while (hasta > desde && b[hasta - 1] == 0) --hasta;
  const std::string texto(reinterpret_cast<const char*>(b) + desde, hasta - desde);
  Campos campos;
  size_t inicio = 0;
  while (true) {
    const size_t salto = texto.find('\n', inicio);
    const std::string linea = texto.substr(inicio, salto == std::string::npos ? std::string::npos : salto - inicio);
    const size_t igual = linea.find('=');
    if (igual != std::string::npos) Poner(campos, linea.substr(0, igual), linea.substr(igual + 1));
    if (salto == std::string::npos) break;
    inicio = salto + 1;
  }
  return campos;
}

// Como Map.toString de Java, para el registro.
std::string Texto(const Campos& c) {
  std::string s = "{";
  for (size_t i = 0; i < c.size(); ++i) {
    if (i) s += ", ";
    s += c[i].first + "=" + c[i].second;
  }
  return s + "}";
}

std::string Ip(const sockaddr_in& a) {
  char b[INET_ADDRSTRLEN] = {};
  inet_ntop(AF_INET, &a.sin_addr, b, sizeof(b));
  return b;
}

using Json = nlohmann::ordered_json;

// Los textos del protocolo son bytes (ISO-8859-1): lo que no sea UTF-8 sale como U+FFFD en vez de
// romper el volcado.
std::string Volcar(const Json& j, int sangria = -1) { return j.dump(sangria, ' ', false, Json::error_handler_t::replace); }

long long Cifra(const Json& v) { return v.is_number() ? v.get<long long>() : 0; }

void CrearCarpeta(const std::string& ruta) {
  std::error_code ec;
  std::filesystem::create_directories(ruta, ec);
}

// ---------------------------------------------------------------------------------------------
//  Estado
// ---------------------------------------------------------------------------------------------

struct Partida;

// Lo que el servidor sabe de un jugador conectado.
struct Sesion {
  int fd = -1;
  int puerto = 0;
  bool pc = false;
  std::string ip;
  // La IP de este telefono por la que ha llegado (la que se le da en @dir).
  std::string ipLocal;
  int id = 0;
  std::string nombreCuenta = "USER";
  std::string persona;
  std::optional<int> sala;
  std::shared_ptr<Partida> partida;
  std::string maddr;
  std::string opparam;
  std::string auxi;
  // Lo pone auth: hasta entonces el nombre es solo el de relleno.
  bool autenticado = false;
  // Conjuntos a los que esta apuntado: nombre de la sala -> ranura (0..4).
  std::vector<std::pair<std::string, int>> conjuntos;
  // El socket ha muerto o se cerro: no se le escribe mas.
  bool roto = false;

  // persona o name, como en el de Python.
  std::string nombre() const { return !persona.empty() ? persona : nombreCuenta; }

  // Se llama con el candado del servidor. Si el socket ha muerto, su hilo lo cerrara.
  void escribir(const Mensaje& original) {
    if (roto) return;
    Mensaje translated;
    if (pc && original.size() >= 12) {
      const std::string command(original.begin(), original.begin()+4);
      const std::string body(original.begin()+12, original.end());
      const auto frame = nfsmw::pc::Frame(command, nfsmw::pc::HostReply(command, body, ipLocal),
          std::string(original.begin()+4, original.begin()+8));
      translated.assign(frame.begin(), frame.end());
    }
    const auto& m = pc ? translated : original;
    size_t hecho = 0;
    while (hecho < m.size()) {
      const ssize_t n = send(fd, m.data() + hecho, m.size() - hecho, 0);
      if (n < 0 && errno == EINTR) continue;
      if (n <= 0) {
        roto = true;
        shutdown(fd, SHUT_RDWR);
        return;
      }
      hecho += size_t(n);
    }
  }

  const int* conjunto(const std::string& sala) const {
    for (const auto& [n, r] : conjuntos) {
      if (n == sala) return &r;
    }
    return nullptr;
  }
  void quitarRanura(int ranura) {
    conjuntos.erase(std::remove_if(conjuntos.begin(), conjuntos.end(), [&](const auto& c) { return c.second == ranura; }),
                    conjuntos.end());
  }
  void apuntar(const std::string& sala, int ranura) {
    for (auto& [n, r] : conjuntos) {
      if (n == sala) {
        r = ranura;
        return;
      }
    }
    conjuntos.emplace_back(sala, ranura);
  }
};
using SesionP = std::shared_ptr<Sesion>;

struct Sala {
  int id = 0;
  // I T SF CF O S C N D P, como texto.
  Campos f;
  // No se manda: la sesion duena. El nombre de "O" no basta si dos telefonos van con el mismo
  // gamertag.
  Sesion* dueno = nullptr;
};

struct Partida {
  // IDENT NAME HOST PARAMS ... y lo que mande el anfitrion en gset.
  Campos f;
  std::vector<SesionP> jugadores;
};

struct Apartado {
  std::string ip;
  Reloj::time_point fin;
};

// Estadisticas y clasificaciones, en stats.json con el mismo formato que el de Python (se puede
// copiar de uno a otro). Lo que lee el juego y de donde sale cada numero: la clase Stats de
// ea_server.py y su README.
class Estadisticas {
 public:
  static constexpr int LARGO = 44;
  static constexpr int MODOS = 3;
  static constexpr int PRIMER_MODO = 8;
  static constexpr int POR_MODO = 12;
  static constexpr int PUNTOS_POR_PUESTO = 10;

  // Parametro M de la sala (2 = circuito) -> bloque de STAT. Solo se sabe el circuito; el resto, al
  // primero.
  static std::optional<int> BloqueModo(int modo) { return modo == 2 ? std::optional<int>(0) : std::nullopt; }

  explicit Estadisticas(std::string carpeta) : carpeta_(std::move(carpeta)), ruta_(carpeta_ + "/stats.json") {
    try {
      std::ifstream f(ruta_);
      jugadores_ = Json::parse(f).at("players");
    } catch (const std::exception&) {
      jugadores_ = Json::object();
    }
    if (!jugadores_.is_object()) jugadores_ = Json::object();
  }

  // RESU: {jugadores, indice de quien lo manda, indice, puesto, indice, puesto...}.
  static std::vector<int> LeerResultados(const std::vector<uint8_t>& d, std::string* error) {
    if (d.size() < 8 || d[0] != 3) {
      *error = "unknown results version";
      return {};
    }
    const int n = d[1];
    std::vector<int> r(2 + 2 * size_t(n));
    r[0] = n;
    r[1] = d[3];
    size_t o = 8;
    for (int i = 0; i < n; ++i) {
      if (o + 51 > d.size()) {
        *error = "results cut short";
        return {};
      }
      r[2 + 2 * size_t(i)] = d[o];
      r[3 + 2 * size_t(i)] = d[o + 1];
      o += 51 + d[o + 50];
    }
    return r;
  }

  void sumar(const std::string& nombre, int jugadores, int puesto, int modo, bool clasificatoria) {
    Json& p = jugador(nombre);
    Json& st = p["stat"];
    const int bloque = PRIMER_MODO + POR_MODO * BloqueModo(modo).value_or(0);
    const bool gano = puesto == 1;
    if (int(st.size()) <= bloque + 4) return;
    st[size_t(bloque)] = Cifra(st[size_t(bloque)]) + (long long)(jugadores - puesto + 1) * PUNTOS_POR_PUESTO;
    const size_t i = size_t(bloque + (gano ? 1 : 2) + (clasificatoria ? 0 : 2));
    st[i] = Cifra(st[i]) + 1;
    p["last_game"] = (long long)std::time(nullptr);
    guardar();
  }

  Campos personales(const std::string& nombre) {
    Json& p = jugador(nombre);
    guardar();
    return {{"STAT", Texto(p["stat"])},
            {"LWSTAT", Texto(p["week"]["stat"])},
            {"LMSTAT", Texto(p["month"]["stat"])},
            {"LGAME", std::to_string(Cifra(p["last_game"]))}};
  }

  struct Fila {
    int puesto = 0;
    std::string nombre;
    long long puntos = 0;
    long long victorias = 0;
    std::vector<long long> fila;
  };

  // Todos los que han corrido, el mejor primero.
  std::vector<Fila> clasificacion() const {
    std::vector<Fila> filas;
    for (const auto& [clave, p] : jugadores_.items()) {
      if (!p.is_object() || !p.contains("stat") || !p["stat"].is_array()) continue;
      const Json& st = p["stat"];
      auto en = [&st](int i) -> long long { return i < int(st.size()) ? Cifra(st[size_t(i)]) : 0; };
      long long puntos = 0, ganadas = 0, perdidas = 0;
      for (int m = 0; m < MODOS; ++m) {
        const int b = PRIMER_MODO + POR_MODO * m;
        puntos += en(b);
        ganadas += en(b + 1) + en(b + 3);
        perdidas += en(b + 2) + en(b + 4);
      }
      if (ganadas + perdidas > 0) {
        const std::string nombre = p.contains("name") && p["name"].is_string() ? p["name"].get<std::string>() : "";
        filas.push_back({0, nombre, puntos, ganadas, {0, ganadas, perdidas, 0, 0, 0, puntos}});
      }
    }
    std::stable_sort(filas.begin(), filas.end(), [](const Fila& a, const Fila& b) {
      if (a.puntos != b.puntos) return a.puntos > b.puntos;
      if (a.victorias != b.victorias) return a.victorias > b.victorias;
      return Minusculas(a.nombre) < Minusculas(b.nombre);
    });
    for (size_t i = 0; i < filas.size(); ++i) filas[i].puesto = int(i) + 1;
    return filas;
  }

  static std::string Texto(const std::vector<long long>& valores) {
    std::string s;
    char b[32];
    for (size_t i = 0; i < valores.size(); ++i) {
      if (i) s += ',';
      const long long v = valores[i];
      std::snprintf(b, sizeof(b), v < 0 ? "-%llx" : "%llx", (unsigned long long)(v < 0 ? -v : v));
      s += b;
    }
    return s;
  }

 private:
  static std::string Texto(const Json& a) {
    std::vector<long long> v;
    if (a.is_array()) {
      for (const auto& x : a) v.push_back(Cifra(x));
    }
    return Texto(v);
  }

  Json& jugador(const std::string& nombre) {
    const std::string clave = Minusculas(Recortar(nombre));
    if (!jugadores_.contains(clave) || !jugadores_[clave].is_object()) {
      jugadores_[clave] = {{"name", Recortar(nombre)},
                           {"stat", Json(std::vector<long long>(LARGO, 0))},
                           {"week", nullptr},
                           {"month", nullptr},
                           {"last_game", 0}};
    }
    Json& p = jugadores_[clave];
    if (!p.contains("stat") || !p["stat"].is_array()) p["stat"] = std::vector<long long>(LARGO, 0);
    // Empieza otra semana / mes: como estaban entonces.
    const std::pair<const char*, std::string> periodos[] = {{"week", Ahora("%G-W%V")}, {"month", Ahora("%Y-%m")}};
    for (const auto& [periodo, ident] : periodos) {
      if (!p.contains(periodo) || !p[periodo].is_object() || p[periodo].value("id", "") != ident) {
        p[periodo] = {{"id", ident}, {"stat", p["stat"]}};
      }
    }
    return p;
  }

  void guardar() {
    CrearCarpeta(carpeta_);
    const std::string tmp = carpeta_ + "/stats.tmp";
    {
      std::ofstream f(tmp, std::ios::binary | std::ios::trunc);
      if (!f) return;
      f << Volcar(Json{{"players", jugadores_}}, 1);
      if (!f) return;
    }
    std::rename(tmp.c_str(), ruta_.c_str());
  }

  std::string carpeta_;
  std::string ruta_;
  Json jugadores_;
};

// ---------------------------------------------------------------------------------------------
//  El servidor
// ---------------------------------------------------------------------------------------------

class Servidor : public std::enable_shared_from_this<Servidor> {
 public:
  Servidor(std::string datos, const std::string& logs, std::function<void()> alCambiar, std::function<std::string()> nombre, std::string pcIp = {})
      : pcIp_(std::move(pcIp)), datos_(std::move(datos)), alCambiar_(std::move(alCambiar)), nombre_(std::move(nombre)), estadisticas_(datos_) {
    CrearCarpeta(datos_);
    CrearCarpeta(logs);
    const std::string f = logs + "/servidor_lan.log";
    // Cada mensaje va al registro: que no crezca sin fin en el telefono.
    struct stat datosRegistro {};
    const bool seguir = stat(f.c_str(), &datosRegistro) != 0 || datosRegistro.st_size < REGISTRO_MAX;
    registro_ = std::fopen(f.c_str(), seguir ? "a" : "w");
  }

  ~Servidor() {
    if (registro_) std::fclose(registro_);
  }

  // Abre los cuatro puertos (falla si alguno esta cogido) y empieza a atender.
  bool arrancar(std::string* error) {
    log("============================================================");
    for (int puerto : {PUERTO_DIRECTORIO, PUERTO_SALAS, PUERTO_GAMERTAG, 9900}) {
      if (puerto == 9900 && pcIp_.empty()) continue;
      const int s = abrir(SOCK_STREAM, puerto, error);
      if (s < 0) {
        parar();
        return false;
      }
      escuchas_.push_back(s);
      auto yo = shared_from_this();
      std::thread([yo, s, puerto] { yo->aceptar(s, puerto); }).detach();
    }
    if (!pcIp_.empty()) {
      anuncio_ = socket(AF_INET, SOCK_DGRAM, 0);
      int one = 1;
      sockaddr_in source{}; source.sin_family = AF_INET;
      inet_pton(AF_INET, pcIp_.c_str(), &source.sin_addr);
      if (anuncio_ < 0 || setsockopt(anuncio_, SOL_SOCKET, SO_BROADCAST, &one, sizeof(one)) != 0 ||
          bind(anuncio_, reinterpret_cast<sockaddr*>(&source), sizeof(source)) != 0) {
        *error = "PC LAN announcement: " + std::string(strerror(errno));
        if (anuncio_ >= 0) close(anuncio_);
        anuncio_ = -1; parar(); return false;
      }
      auto yo = shared_from_this();
      std::thread([yo] { yo->anunciarPC(); }).detach();
    }
    busqueda_ = abrir(SOCK_DGRAM, PUERTO_GAMERTAG, error);
    if (busqueda_ < 0) {
      parar();
      return false;
    }
    auto yo = shared_from_this();
    std::thread([yo] { yo->contestarBusquedas(); }).detach();
    // El servidor de salas manda ~png cada poco; sin trafico, el cliente da la conexion por muerta a
    // los 60 s y vuelve al menu.
    std::thread([yo] { yo->latidos(); }).detach();
    log("EA server: directory " + std::to_string(PUERTO_DIRECTORIO) + ", lobby " + std::to_string(PUERTO_SALAS) +
        ", gamertag check " + std::to_string(PUERTO_GAMERTAG) + ", LAN search " + std::to_string(PUERTO_GAMERTAG) + "/udp");
    return true;
  }

  void parar() {
    if (parado_.exchange(true)) return;
    {
      std::lock_guard<std::mutex> l(mutexLatido_);
      latido_.notify_all();
      anuncioWake_.notify_all();
    }
    // Los accept y la busqueda lo ven en su siguiente vuelta y cierran su socket.
    {
      std::lock_guard<std::recursive_mutex> l(candado_);
      for (const auto& s : sesiones_) {
        if (!s->roto) shutdown(s->fd, SHUT_RDWR);
      }
    }
    log("stopped");
  }

  bool parado() const { return parado_; }

  // Un socket de escucha o el de la busqueda fallo sin que nadie parase el servidor: lo normal en iOS
  // es que la app se congelase en segundo plano y el sistema le anulase los sockets ("Socket is not
  // connected"). Se para entero, para que EnMarcha() lo diga y Revivir() lo vuelva a abrir.
  void caer(const std::string& porque) {
    if (parado_) return;
    log(porque + ": the server is down; it restarts when the app comes back");
    parar();
  }

  // Jugadores dentro de Xbox Live (conectados al servidor de salas y autenticados).
  int jugadores() {
    std::lock_guard<std::recursive_mutex> l(candado_);
    int n = 0;
    for (const auto& s : sesiones_) {
      if ((s->puerto == PUERTO_SALAS || s->pc) && s->autenticado) ++n;
    }
    return n;
  }

 private:
  // ---- Conexiones

  // En IPv4: con el comodin de IPv6 las IP de los clientes saldrian como ::ffff:a.b.c.d y no casarian
  // con las del juego.
  int abrir(int tipo, int puerto, std::string* error) {
    const int s = socket(AF_INET, tipo, 0);
    if (s < 0) {
      *error = std::string("socket: ") + std::strerror(errno);
      return -1;
    }
    int uno = 1;
    setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &uno, sizeof(uno));
    sockaddr_in a{};
    a.sin_family = AF_INET;
    a.sin_port = htons(uint16_t(puerto));
    a.sin_addr.s_addr = htonl(INADDR_ANY);
    if (bind(s, reinterpret_cast<sockaddr*>(&a), sizeof(a)) != 0 || (tipo == SOCK_STREAM && listen(s, 16) != 0)) {
      *error = std::to_string(puerto) + ": " + std::strerror(errno);
      close(s);
      return -1;
    }
    return s;
  }

  // Espera a que haya algo que leer en `s`, mirando cada poco si hay que parar.
  bool esperar(int s) {
    while (!parado_) {
      pollfd p{s, POLLIN, 0};
      const int n = poll(&p, 1, VUELTA_MS);
      if (n > 0) return true;
      if (n < 0 && errno != EINTR) return false;
    }
    return false;
  }

  void aceptar(int escucha, int puerto) {
    while (esperar(escucha)) {
      sockaddr_in de{};
      socklen_t largo = sizeof(de);
      const int s = accept(escucha, reinterpret_cast<sockaddr*>(&de), &largo);
      if (s < 0) {
        if (errno == EINTR || errno == ECONNABORTED) continue;
        caer("[" + std::to_string(puerto) + "] accept: " + std::strerror(errno));
        break;
      }
      int uno = 1;
      setsockopt(s, SOL_SOCKET, SO_NOSIGPIPE, &uno, sizeof(uno));
      auto yo = shared_from_this();
      std::thread([yo, s, puerto] {
        if (puerto == PUERTO_GAMERTAG) {
          yo->comprobarGamertag(s);
        } else {
          yo->atender(s, puerto);
        }
      }).detach();
    }
    caer("[" + std::to_string(puerto) + "] poll: " + std::strerror(errno));  // nada si se paro a proposito
    close(escucha);
  }

  void atender(int fd, int puerto) {
    int uno = 1;
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &uno, sizeof(uno));
    // Las respuestas se escriben con el candado: que un cliente que no lee no lo retenga sin fin.
    timeval plazo{10, 0};
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &plazo, sizeof(plazo));
    auto ses = std::make_shared<Sesion>();
    ses->fd = fd;
    ses->puerto = puerto;
    ses->pc = puerto == 9900;
    sockaddr_in otro{}, propio{};
    socklen_t largo = sizeof(otro);
    getpeername(fd, reinterpret_cast<sockaddr*>(&otro), &largo);
    largo = sizeof(propio);
    getsockname(fd, reinterpret_cast<sockaddr*>(&propio), &largo);
    ses->ip = Ip(otro);
    ses->ipLocal = Ip(propio);
    // PC-only mode exposes mobile control ports only to this phone's game.
    if (!pcIp_.empty() && !ses->pc && ses->ip != pcIp_ && ses->ip != "127.0.0.1") {
      log("[pc-host] rejected mobile guest " + ses->ip); close(fd); return;
    }
    ses->id = ++cuentaSesiones_;
    const std::string p = "[" + std::to_string(puerto) + "]";
    const std::string par = ses->ip + ":" + std::to_string(ntohs(otro.sin_port));
    {
      std::lock_guard<std::recursive_mutex> l(candado_);
      sesiones_.push_back(ses);
    }
    log(p + " connection from " + par);
    std::vector<uint8_t> buffer;
    std::vector<uint8_t> trozo(65536);
    while (true) {
      const ssize_t n = recv(fd, trozo.data(), trozo.size(), 0);
      if (n < 0 && errno == EINTR) continue;
      if (n <= 0) {
        if (n < 0 && !parado_) log(p + " " + std::strerror(errno));
        break;
      }
      buffer.insert(buffer.end(), trozo.begin(), trozo.begin() + n);
      while (buffer.size() >= 12) {
        const uint64_t largoMensaje = uint64_t(buffer[8]) << 24 | uint64_t(buffer[9]) << 16 | uint64_t(buffer[10]) << 8 | buffer[11];
        if (largoMensaje < 12 || largoMensaje > (1u << 20)) {
          log(p + " impossible length " + std::to_string(largoMensaje) + ": " + Hex(buffer.data(), std::min<size_t>(32, buffer.size())));
          buffer.clear();
          break;
        }
        if (buffer.size() < largoMensaje) break;
        const std::string orden(buffer.begin(), buffer.begin() + 4);
        const std::string sub = Hex(&buffer[4], 4);
        Campos campos = LeerCampos(buffer.data(), 12, size_t(largoMensaje));
        if (ses->pc && (orden == "auth" || orden == "pers")) {
          in_addr address{}; inet_pton(AF_INET, ses->ip.c_str(), &address);
          if (!nfsmw::pc::SetHostingPeer(ntohl(address.s_addr))) {
            log("[pc-host] only one PC peer per experimental hosting session");
            shutdown(fd, SHUT_RDWR); break;
          }
          const std::string body(buffer.begin()+12, buffer.begin()+std::ptrdiff_t(largoMensaje));
          const auto adapted = nfsmw::pc::HostLogin(body, ses->ip);
          campos = LeerCampos(reinterpret_cast<const uint8_t*>(adapted.data()), 0, adapted.size());
        }
        buffer.erase(buffer.begin(), buffer.begin() + std::ptrdiff_t(largoMensaje));
        log(p + " <- " + orden + " sub=" + sub + " " + Texto(campos));
        std::lock_guard<std::recursive_mutex> l(candado_);
        std::vector<Mensaje> respuestas;
        if (!responder(ses, orden, campos, respuestas)) log(p + "    (unhandled command: replying empty)");
        for (const auto& r : respuestas) {
          log(p + " -> " + std::string(r.begin(), r.begin() + 4) + " " + Texto(LeerCampos(r.data(), 12, r.size())));
          ses->escribir(r);
        }
      }
    }
    bool eraJugador;
    {
      std::lock_guard<std::recursive_mutex> l(candado_);
      eraJugador = ses->autenticado && (puerto == PUERTO_SALAS || ses->pc);
      olvidar(ses);
      sesiones_.erase(std::remove(sesiones_.begin(), sesiones_.end(), ses), sesiones_.end());
      // Nadie mas le escribe: el descriptor se puede cerrar (y reutilizar).
      ses->roto = true;
    }
    log(p + " " + par + " closed");
    close(fd);
    if (eraJugador) alCambiar_();
  }

  void anunciarPC() {
    const uint32_t identity = arc4random();
    sockaddr_in target{}; target.sin_family = AF_INET;
    target.sin_port = htons(9999); target.sin_addr.s_addr = htonl(INADDR_BROADCAST);
    log("[pc-host] native discovery UDP9999; directory/lobby TCP9900; source " + pcIp_);
    std::mutex mutex;
    std::unique_lock<std::mutex> wait(mutex);
    bool reported = false;
    while (!parado_) {
      const auto packet = nfsmw::pc::Advertisement(nombre_(), unsigned(jugadores()), identity);
      if (sendto(anuncio_, packet.data(), packet.size(), 0,
          reinterpret_cast<sockaddr*>(&target), sizeof(target)) < 0 && !reported) {
        log("[pc-host] announcement failed: " + std::string(strerror(errno)));
        reported = true;
      }
      anuncioWake_.wait_for(wait, std::chrono::seconds(3), [this] { return parado_.load(); });
    }
    close(anuncio_);
  }

  void latidos() {
    std::unique_lock<std::mutex> espera(mutexLatido_);
    while (!parado_) {
      latido_.wait_for(espera, std::chrono::seconds(20), [this] { return parado_.load(); });
      if (parado_) break;
      const Mensaje m = Crear("~png", {{"REF", Fecha()}, {"TIME", "2"}});
      std::lock_guard<std::recursive_mutex> l(candado_);
      for (const auto& s : sesiones_) {
        if ((s->puerto == PUERTO_SALAS || s->pc)) s->escribir(m);
      }
    }
  }

  // La pregunta de la app: una linea "GAMERTAG <nombre>" y otra de vuelta, "FREE" o "IN_USE". Un
  // FREE aparta el nombre para el que pregunta (ver apartar), para que a dos telefonos no se les
  // diga a la vez que esta libre.
  void comprobarGamertag(int fd) {
    sockaddr_in otro{};
    socklen_t largo = sizeof(otro);
    getpeername(fd, reinterpret_cast<sockaddr*>(&otro), &largo);
    const std::string ip = Ip(otro);
    timeval plazo{5, 0};
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &plazo, sizeof(plazo));
    std::string linea;
    char c;
    bool leida = false;
    while (linea.size() < 512) {
      const ssize_t n = recv(fd, &c, 1, 0);
      if (n < 0 && errno == EINTR) continue;
      if (n < 0) break;  // plazo: sin respuesta
      if (n == 0 || c == '\n') {
        leida = true;
        break;
      }
      linea += c;
    }
    if (leida || linea.size() >= 512) {
      linea = Recortar(linea);
      const size_t espacio = linea.find(' ');
      const std::string orden = espacio == std::string::npos ? linea : linea.substr(0, espacio);
      const std::string gamertag = espacio == std::string::npos ? "" : Recortar(linea.substr(espacio + 1));
      std::string respuesta;
      if (orden != "GAMERTAG" || gamertag.empty()) {
        respuesta = "ERROR";
      } else {
        std::optional<std::string> otroIp;
        {
          std::lock_guard<std::recursive_mutex> l(candado_);
          otroIp = quienUsa(gamertag, ip);
          if (!otroIp) apartar(gamertag, ip);
        }
        respuesta = otroIp ? "IN_USE" : "FREE";
        log("[" + std::to_string(PUERTO_GAMERTAG) + "] " + ip + " asks about '" + gamertag + "': " + respuesta +
            (otroIp ? " (" + *otroIp + ")" : " (held for it)"));
      }
      respuesta += "\n";
      send(fd, respuesta.data(), respuesta.size(), 0);
    }
    close(fd);
  }

  // La busqueda de servidores de la app (red_lan.cpp, BuscadorServidores en Android): a cada
  // pregunta, nombre y jugadores.
  void contestarBusquedas() {
    uint8_t buf[512];
    // Cada busqueda llega varias veces (broadcast y directa, tres rondas): al registro, una vez por
    // IP cada 10 s.
    std::map<std::string, Reloj::time_point> anotadas;
    const std::string pregunta = "NFSMW_DISCOVER";
    while (esperar(busqueda_)) {
      sockaddr_in de{};
      socklen_t largo = sizeof(de);
      const ssize_t n = recvfrom(busqueda_, buf, sizeof(buf), 0, reinterpret_cast<sockaddr*>(&de), &largo);
      if (n < 0) {
        if (errno == EINTR) continue;
        caer("[" + std::to_string(PUERTO_GAMERTAG) + "/udp] " + std::strerror(errno));
        break;
      }
      if (size_t(n) < pregunta.size() || std::memcmp(buf, pregunta.data(), pregunta.size()) != 0) continue;
      if (!pcIp_.empty()) continue; // PC-only hosting is advertised by native UDP9999.
      const std::string nombre = nombre_();
      const int j = jugadores();
      const std::string r = "NFSMW_SERVER\nNAME=" + nombre + "\nPLAYERS=" + std::to_string(j) + "\n";
      if (sendto(busqueda_, r.data(), r.size(), 0, reinterpret_cast<sockaddr*>(&de), largo) < 0) continue;
      const std::string ip = Ip(de);
      const auto ahora = Reloj::now();
      if (auto a = anotadas.find(ip); a != anotadas.end() && ahora - a->second < std::chrono::seconds(10)) continue;
      anotadas[ip] = ahora;
      log("[" + std::to_string(PUERTO_GAMERTAG) + "/udp] search from " + ip + ": answered '" + nombre + "', " +
          std::to_string(j) + " players");
    }
    caer("[" + std::to_string(PUERTO_GAMERTAG) + "/udp] poll: " + std::strerror(errno));
    close(busqueda_);
  }

  // ---- Mensajes

  // Lo que se contesta a cada orden; false si no se conoce (se contesta vacio).
  bool responder(const SesionP& ses, const std::string& orden, const Campos& f, std::vector<Mensaje>& r) {
    std::string nombre = orden.substr(orden.find_first_not_of("@~") == std::string::npos ? orden.size()
                                                                                         : orden.find_first_not_of("@~"));
    std::replace(nombre.begin(), nombre.end(), ' ', '_');
    if (ses->pc && (nombre == "gcre" || nombre == "ucre")) {
      r.push_back(Crear(orden, {}, "perm")); return true;
    }
    if (nombre == "dir") dir(*ses, r);
    else if (nombre == "tic") {}   // ofrece cifrar; sin respuesta sigue en claro
    else if (nombre == "addr") {}  // el cliente dice su IP y puerto; sin respuesta
    else if (nombre == "png") {}   // la respuesta a nuestro ping: no se contesta
    else if (nombre == "skey") r.push_back(Crear("skey", {{"SKEY", "$51ba8aee64ddfacae5baefa6bf61e009"}}));
    else if (nombre == "news") news(*ses, r);
    else if (nombre == "sele") sele(ses, f, r);
    else if (nombre == "user") user(*ses, f, r);
    else if (nombre == "snap") snap(*ses, f, r);
    else if (nombre == "rank") rank(*ses, f, r);
    else if (nombre == "usea") usea(*ses, f, r);
    else if (nombre == "gcre") gcre(ses, f, r);
    else if (nombre == "gjoi") gjoi(ses, f, r);
    else if (nombre == "gset") gset(ses, f, r);
    else if (nombre == "glea") { dejarPartida(ses); r.push_back(Crear("glea", {})); }
    else if (nombre == "gdel") { dejarPartida(ses); r.push_back(Crear("gdel", {})); }
    else if (nombre == "gsta") gsta(*ses, r);
    else if (nombre == "ujoi") ujoi(ses, f, r);
    else if (nombre == "udel") udel(ses, f, r);
    else if (nombre == "ulea") ulea(ses, r);
    else if (nombre == "mesg") mesg(ses, f, r);
    else if (nombre == "uadm") uadm(*ses, f, r);
    else if (nombre == "ucre") ucre(ses, f, r);
    else if (nombre == "auxi") auxi(ses, f, r);
    else if (nombre == "auth") auth(*ses, f, r);
    else if (nombre == "pers") pers(*ses, f, r);
    else {
      r.push_back(Crear(orden, {}));
      return false;
    }
    return true;
  }

  void dir(const Sesion& ses, std::vector<Mensaje>& r) {
    r.push_back(Crear("@dir", {{"ADDR", ses.ipLocal},
                               {"PORT", std::to_string(PUERTO_SALAS)},
                               {"SESS", std::to_string(1000000000 + int(arc4random_uniform(1000000000)))},
                               {"MASK", AzarHex()}}));
  }

  void news(const Sesion& ses, std::vector<Mensaje>& r) {
    r.push_back(Crear("news", {{"BUDDY_SERVER", ses.ipLocal},
                               {"BUDDY_PORT", "10899"},
                               {"TOSAC_URL", ""},
                               {"TOSA_URL", ""},
                               {"TOS_URL", ""}}));
  }

  void sele(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Lo mismo que pide ("si, todo eso") y su propio registro (+who).
    r.push_back(Crear("sele", f));
    r.push_back(registroUsuario(*ses, "+who"));
    // USERSETk=<sala>: se apunta en la ranura k a los miembros de esa sala (el que se une lo manda
    // antes de ujoi): la sala (+ust) y cada miembro (+usm).
    for (const auto& [clave, valor] : f) {
      if (clave.rfind("USERSET", 0) != 0 || clave.size() == 7 ||
          clave.find_first_not_of("0123456789", 7) != std::string::npos) {
        continue;
      }
      const auto numero = Numero(clave.substr(7));
      if (!numero) continue;  // en Java, un numero que no cabe en un int rompe la conexion
      const int ranura = *numero;
      ses->quitarRanura(ranura);
      if (valor.empty()) continue;
      ses->apuntar(valor, ranura);
      if (Sala* sala = salaPorNombre(valor)) {
        r.push_back(Crear("+ust", registroSala(*sala)));
        for (const auto& m : miembros(*sala)) r.push_back(registroMiembro(*m, ranura, false));
      }
    }
  }

  // -- conjuntos de usuarios (las "salas" de ucre/ujoi/ulea/usea) --------------------------------
  // La sala de juego es la lista de miembros del conjunto en la ranura 0, y solo se llena con '+usm'
  // (S ranura, I, N, F, G, X). El miembro 0 es uno mismo: sin su propia entrada la lista sale vacia.

  Sala* salaPorNombre(const std::string& nombre) {
    for (auto& [id, s] : salas_) {
      if (Valor(s->f, "N", "") == nombre) return s.get();
    }
    return nullptr;
  }

  std::vector<SesionP> miembros(const Sala& sala) {
    std::vector<SesionP> l;
    for (const auto& o : sesiones_) {
      if (o->sala && *o->sala == sala.id) l.push_back(o);
    }
    return l;
  }

  static std::string Ident(const Sesion& ses) { return ses.partida ? Valor(ses.partida->f, "IDENT", "null") : "0"; }

  Mensaje registroMiembro(const Sesion& ses, int ranura, bool quitar) {
    if (quitar) return Crear("+usm", {{"S", std::to_string(ranura)}, {"I", std::to_string(ses.id)}});
    return Crear("+usm", {{"S", std::to_string(ranura)},
                          {"I", std::to_string(ses.id)},
                          {"N", ses.nombre()},
                          {"F", "U"},
                          {"G", Ident(ses)},
                          {"X", ses.auxi}});
  }

  // '+usm' de `ses` a los apuntados a `sala`; la copia de `pide` se devuelve en `r`.
  void avisarConjunto(const Sala& sala, const Sesion& ses, const Sesion* pide, bool quitar, std::vector<Mensaje>* r) {
    const std::string nombre = Valor(sala.f, "N", "");
    for (const auto& o : sesiones_) {
      const int* ranura = o->conjunto(nombre);
      if (!ranura) continue;
      const Mensaje m = registroMiembro(ses, *ranura, quitar);
      if (o.get() == pide) {
        if (r) r->push_back(m);
      } else {
        o->escribir(m);
      }
    }
  }

  void olvidar(const SesionP& ses) {
    dejarPartida(ses);
    // Su nombre le sigue apartado un rato, para que nadie lo coja nada mas salir de Xbox Live.
    if (ses->autenticado) apartar(ses->nombre(), ses->ip);
    if (ses->sala) {
      if (auto s = salas_.find(*ses->sala); s != salas_.end()) avisarConjunto(*s->second, *ses, ses.get(), true, nullptr);
    }
    std::vector<int> suyas;
    for (const auto& [id, s] : salas_) {
      if (s->dueno == ses.get()) suyas.push_back(id);
    }
    for (int id : suyas) {
      if (auto s = salas_.find(id); s != salas_.end()) borrarSala(id, *ses);
    }
  }

  // Borra una sala: los que siguen en ella salen (y sus apuntados se enteran).
  void borrarSala(int id, Sesion& dueno) {
    auto s = salas_.find(id);
    if (s == salas_.end()) return;
    const std::unique_ptr<Sala> sala = std::move(s->second);
    for (const auto& m : miembros(*sala)) {
      if (m.get() != &dueno) {
        avisarConjunto(*sala, *m, nullptr, true, nullptr);
        m->sala.reset();
      }
    }
    if (dueno.sala && *dueno.sala == sala->id) dueno.sala.reset();
    salas_.erase(s);
    log("   room " + std::to_string(sala->id) + " (" + Valor(sala->f, "N", "null") + ") of " + Valor(sala->f, "O", "null") +
        " deleted");
  }

  void user(const Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    const std::string* pers = Buscar(f, "PERS");
    const std::string nombre = pers ? *pers : ses.nombre();
    Campos reg = {{"PERS", nombre}, {"LAST", "2005.11.15-00:00:00"}, {"EXPR", "1072566000"}};
    for (auto& [k, v] : estadisticas_.personales(nombre)) Poner(reg, k, v);
    r.push_back(Crear("user", reg));
  }

  void snap(const Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Clasificacion: CHAN (donde pone el juego las filas), INDEX, START/RANGE o FIND=$. La respuesta
    // repite CHAN y dice en RANGE cuantas '+snp' siguen.
    std::vector<Estadisticas::Fila> filas = estadisticas_.clasificacion();
    if (!Vacio(Buscar(f, "FIND"))) {
      const std::string yo = Minusculas(ses.nombre());
      filas.erase(std::remove_if(filas.begin(), filas.end(), [&](const auto& fila) { return Minusculas(fila.nombre) != yo; }),
                  filas.end());
    } else {
      const int inicio = Entero(Buscar(f, "START"), 0);
      const int cuantas = Entero(Buscar(f, "RANGE"), 100);
      const size_t desde = std::min<size_t>(size_t(std::max(inicio, 0)), filas.size());
      const size_t hasta = std::min<size_t>(filas.size(), desde + size_t(std::max(cuantas, 0)));
      filas = std::vector<Estadisticas::Fila>(filas.begin() + std::ptrdiff_t(desde), filas.begin() + std::ptrdiff_t(hasta));
    }
    const std::string* chan = Buscar(f, "CHAN");
    const std::string* start = Buscar(f, "START");
    r.push_back(Crear("snap", {{"CHAN", chan ? *chan : "0"}, {"START", start ? *start : "0"}, {"RANGE", std::to_string(filas.size())}}));
    for (const auto& fila : filas) {
      r.push_back(Crear("+snp", {{"N", fila.nombre},
                                 {"R", std::to_string(fila.puesto)},
                                 {"P", std::to_string(fila.puntos)},
                                 {"O", "0"},
                                 {"S", Estadisticas::Texto(fila.fila)}}));
    }
  }

  void rank(const Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Resultados de una carrera de cada jugador al acabar: REPT quien, RESU los resultados (base64 en
    // URL). Su propio puesto va a sus estadisticas.
    const std::string nombre = !Vacio(Buscar(f, "REPT")) ? *Buscar(f, "REPT") : ses.nombre();
    const auto [modo, clasificatoria] = ajustesCarrera(ses);
    std::string resu = Desescapar(Valor(f, "RESU", ""));
    resu.erase(std::remove_if(resu.begin(), resu.end(),
                              [](unsigned char c) { return !(std::isalnum(c) || c == '+' || c == '/' || c == '='); }),
               resu.end());
    const std::vector<uint8_t> d = Base64(resu).value_or(std::vector<uint8_t>());
    std::optional<int> contado;
    std::string error;
    const std::vector<int> res = Estadisticas::LeerResultados(d, &error);
    if (!error.empty()) {
      log("   rank from " + nombre + ": " + error);
    } else {
      const int jugadores = res[0];
      const int quien = res[1];
      for (size_t i = 2; i + 1 < res.size(); i += 2) {
        if (res[i] == quien && res[i + 1] != 0) {
          estadisticas_.sumar(nombre, jugadores, res[i + 1], modo, clasificatoria);
          contado = res[i + 1];
          if (!Estadisticas::BloqueModo(modo)) {
            log("   race mode M=" + std::to_string(modo) + " not mapped to a STAT block yet: counted in the first one");
          }
          break;
        }
      }
    }
    log("   rank: " + nombre + " finished " + (contado ? std::to_string(*contado) : "null") + " of the race (M=" +
        std::to_string(modo) + ", ranked=" + (clasificatoria ? "True" : "False") + ")");
    Json campos = Json::object();
    for (const auto& [k, v] : f) campos[k] = v;
    const Json linea = {{"time", Ahora("%Y-%m-%dT%H:%M:%S")},
                        {"from", nombre},
                        {"fields", campos},
                        {"results", Hex(d.data(), d.size())},
                        {"mode", modo},
                        {"ranked", clasificatoria},
                        {"counted", contado ? Json(*contado) : Json(nullptr)}};
    if (FILE* carreras = std::fopen((datos_ + "/races.jsonl").c_str(), "a")) {
      const std::string texto = Volcar(linea) + "\n";
      std::fwrite(texto.data(), 1, texto.size(), carreras);
      std::fclose(carreras);
    } else {
      log("   races.jsonl: " + std::string(std::strerror(errno)));
    }
    r.push_back(Crear("rank", {}));
  }

  // {modo M, si es clasificatoria} de los PARAMS de la sala de `ses` (V=... P=1 L=3 M=2).
  std::pair<int, bool> ajustesCarrera(const Sesion& ses) {
    const Sala* sala = nullptr;
    if (ses.sala) {
      if (auto s = salas_.find(*ses.sala); s != salas_.end()) sala = s->second.get();
    }
    Campos params;
    const std::string texto = Desescapar(sala ? Valor(sala->f, "P", "") : "");
    size_t inicio = 0;
    while (true) {
      size_t salto = texto.find_first_of("\r\n", inicio);
      const std::string linea = texto.substr(inicio, salto == std::string::npos ? std::string::npos : salto - inicio);
      const size_t igual = linea.find('=');
      Poner(params, Recortar(igual == std::string::npos ? linea : linea.substr(0, igual)),
            igual == std::string::npos ? "" : Recortar(linea.substr(igual + 1)));
      if (salto == std::string::npos) break;
      // \r\n cuenta como uno.
      if (texto[salto] == '\r' && salto + 1 < texto.size() && texto[salto + 1] == '\n') ++salto;
      inicio = salto + 1;
    }
    const int modo = Numero(Valor(params, "M", "2")).value_or(2);
    return {modo, Valor(params, "P", "1") == "1"};
  }

  void usea(const Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Busqueda de salas (la de Partida rapida): COUNT, y cada una en un '+uss'.
    std::vector<const Sala*> otras;
    for (const auto& [id, s] : salas_) {
      if (s->dueno != &ses) otras.push_back(s.get());
    }
    const std::string* start = Buscar(f, "START");
    r.push_back(Crear("usea", {{"START", start ? *start : "0"}, {"COUNT", std::to_string(otras.size())}}));
    for (const Sala* s : otras) r.push_back(Crear("+uss", registroSala(*s)));
  }

  // -- partidas (la carrera dentro de una sala) ---------------------------------------------------

  Campos registroPartida(const Partida& p, const Sesion& mira) {
    auto v = [&p](const char* k) { return ONull(Buscar(p.f, k)); };
    Campos f = {{"IDENT", v("IDENT")},
                {"NAME", v("NAME")},
                {"SELF", mira.nombre()},
                {"HOST", v("HOST")},
                {"PARAMS", v("PARAMS")},
                {"PLATPARAMS", v("PLATPARAMS")},
                {"ROOM", v("ROOM")},
                {"CUSTFLAGS", v("CUSTFLAGS")},
                {"SYSFLAGS", v("SYSFLAGS")},
                {"COUNT", std::to_string(p.jugadores.size())},
                {"PRIV", "0"},
                {"MINSIZE", v("MINSIZE")},
                {"MAXSIZE", v("MAXSIZE")},
                {"NUMPART", "1"},
                {"PARTSIZE0", v("MAXSIZE")},
                {"PARTPARAMS0", ""},
                {"SEED", v("SEED")},
                {"WHEN", v("WHEN")},
                {"AUTH", ""},
                {"SESS", Valor(p.f, "SESS", "")}};
    for (size_t i = 0; i < p.jugadores.size(); ++i) {
      const Sesion& j = *p.jugadores[i];
      const std::string n = std::to_string(i);
      Poner(f, "OPPO" + n, j.nombre());
      Poner(f, "OPID" + n, std::to_string(j.id));
      Poner(f, "ADDR" + n, j.ip);
      Poner(f, "LADDR" + n, j.ip);
      Poner(f, "MADDR" + n, j.maddr);
      Poner(f, "OPPART" + n, "0");
      Poner(f, "OPPARAM" + n, j.opparam);
      Poner(f, "OPFLAG" + n, "0");
      Poner(f, "PRES" + n, "0");
    }
    return f;
  }

  // El registro de la partida a todos sus jugadores (menos uno).
  void avisar(const Partida& p, const std::string& orden, const Sesion* salvo) {
    for (const auto& j : p.jugadores) {
      if (j.get() == salvo) continue;
      log("   " + orden + " -> " + j->nombre() + " (COUNT=" + std::to_string(p.jugadores.size()) + ")");
      j->escribir(Crear(orden, registroPartida(p, *j)));
    }
  }

  std::shared_ptr<Partida> partidaPorNombre(const std::string& nombre) {
    for (const auto& [n, p] : partidas_) {
      if (n == nombre) return p;
    }
    return nullptr;
  }

  void gcre(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    const std::string yo = ses->nombre();
    ++siguienteId_;
    auto p = std::make_shared<Partida>();
    const std::string* nombre = Buscar(f, "NAME");
    p->f = {{"IDENT", std::to_string(siguienteId_)},
            {"NAME", nombre ? *nombre : yo},
            {"HOST", yo},
            {"PARAMS", Valor(f, "PARAMS", "")},
            {"PLATPARAMS", Valor(f, "PLATPARAMS", "")},
            {"ROOM", std::to_string(ses->sala && *ses->sala != 0 ? *ses->sala : 0)},
            {"CUSTFLAGS", Valor(f, "CUSTFLAGS", "0")},
            {"SYSFLAGS", Valor(f, "SYSFLAGS", "0")},
            {"MINSIZE", Valor(f, "MINSIZE", "2")},
            {"MAXSIZE", Valor(f, "MAXSIZE", "4")},
            {"SEED", std::to_string(1 + arc4random_uniform(INT_MAX - 1))},
            {"WHEN", Fecha()}};
    p->jugadores.push_back(ses);
    // partidas.put: la de ese nombre se cambia en su sitio.
    const std::string clave = Valor(p->f, "NAME", "");
    bool puesta = false;
    for (auto& [n, vieja] : partidas_) {
      if (n == clave) {
        vieja = p;
        puesta = true;
      }
    }
    if (!puesta) partidas_.emplace_back(clave, p);
    ses->partida = p;
    // Despues, su registro con G = esta partida.
    r.push_back(Crear("gcre", registroPartida(*p, *ses)));
    r.push_back(registroUsuario(*ses, "+who"));
  }

  void gjoi(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    auto p = partidaPorNombre(Valor(f, "NAME", ""));
    if (!p) {
      log("   gjoi: no game '" + ONull(Buscar(f, "NAME")) + "'");
      r.push_back(Crear("gjoi", {}, "nfnd"));
      return;
    }
    if (std::find(p->jugadores.begin(), p->jugadores.end(), ses) == p->jugadores.end()) p->jugadores.push_back(ses);
    ses->partida = p;
    avisar(*p, "+mgm", ses.get());
    // Solo el registro: el que se une conecta con el SESS de este registro. '+ses' es para cuando el
    // anfitrion arranca (gsta).
    r.push_back(Crear("gjoi", registroPartida(*p, *ses)));
    r.push_back(registroUsuario(*ses, "+who"));
  }

  void gset(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    auto p = ses->partida;
    if (!p) {
      r.push_back(Crear("gset", {}));
      return;
    }
    // Se guarda todo lo que manda el anfitrion; ojo con SESS, su sesion de Xbox codificada ("$..."):
    // el que se une solo conecta si empieza por '$'.
    for (const auto& [k, v] : f) {
      if (k != "NAME") Poner(p->f, k, v);
    }
    avisar(*p, "+mgm", ses.get());
    r.push_back(Crear("gset", registroPartida(*p, *ses)));
  }

  void dejarPartida(const SesionP& ses) {
    auto p = ses->partida;
    if (!p) return;
    p->jugadores.erase(std::remove(p->jugadores.begin(), p->jugadores.end(), ses), p->jugadores.end());
    ses->partida.reset();
    if (p->jugadores.empty() || Valor(p->f, "HOST", "") == ses->nombre()) {
      const std::string nombre = Valor(p->f, "NAME", "");
      partidas_.erase(std::remove_if(partidas_.begin(), partidas_.end(), [&](const auto& e) { return e.first == nombre; }),
                      partidas_.end());
      for (const auto& j : p->jugadores) j->partida.reset();
      log("   game " + nombre + " closed");
    } else {
      avisar(*p, "+mgm", nullptr);
    }
  }

  void gsta(const Sesion& ses, std::vector<Mensaje>& r) {
    // El anfitrion arranca: '+ses' con el registro (y su SESS) a todos.
    if (ses.partida) avisar(*ses.partida, "+ses", nullptr);
    r.push_back(Crear("gsta", {}));
  }

  Sala* buscarSala(const Campos& f) {
    for (const char* clave : {"I", "IDENT", "ROOM"}) {
      const std::string* v = Buscar(f, clave);
      if (!v) continue;
      const std::string sinMenos = v->substr(std::min(v->find_first_not_of('-'), v->size()));
      if (sinMenos.empty() || sinMenos.find_first_not_of("0123456789") != std::string::npos) continue;
      if (const auto id = Numero(*v)) {
        if (auto s = salas_.find(*id); s != salas_.end()) return s->second.get();
      }
    }
    const std::string* nombre = !Vacio(Buscar(f, "NAME")) ? Buscar(f, "NAME") : Buscar(f, "N");
    if (!nombre) return nullptr;
    for (auto& [id, s] : salas_) {
      if (Valor(s->f, "N", "") == *nombre || Valor(s->f, "O", "") == *nombre) return s.get();
    }
    return nullptr;
  }

  void ujoi(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    Sala* sala = buscarSala(f);
    if (!sala) {
      log("   ujoi: can't find the room for " + Texto(f));
      r.push_back(Crear("ujoi", {}, "nfnd"));
      return;
    }
    Poner(sala->f, "C", std::to_string(Entero(Buscar(sala->f, "C"), 0) + 1));
    ses->sala = sala->id;
    // Los que ya estan reciben el '+usr' del que entra y el que entra el de cada uno: con ese
    // registro (LA, MA) el anfitrion le da de alta en la conexion entre pares.
    r.push_back(Crear("ujoi", registroSala(*sala)));
    for (const auto& otro : sesiones_) {
      if (otro != ses && otro->sala && *otro->sala == sala->id) {
        log("   +usr " + ses->nombre() + " -> " + otro->nombre());
        otro->escribir(registroUsuario(*ses, "+usr"));
        r.push_back(registroUsuario(*otro, "+usr"));
      }
    }
    r.push_back(registroUsuario(*ses, "+usr"));
    avisarConjunto(*sala, *ses, ses.get(), false, &r);
  }

  void udel(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    // El dueno borra su sala (tras gdel al salir de "Crear partida").
    Sala* sala = salaPorNombre(Valor(f, "NAME", ""));
    if (!sala && ses->sala) {
      if (auto s = salas_.find(*ses->sala); s != salas_.end()) sala = s->second.get();
    }
    if (sala && sala->dueno == ses.get()) borrarSala(sala->id, *ses);
    r.push_back(Crear("udel", {}));
  }

  void ulea(const SesionP& ses, std::vector<Mensaje>& r) {
    Sala* sala = nullptr;
    if (ses->sala) {
      if (auto s = salas_.find(*ses->sala); s != salas_.end()) sala = s->second.get();
    }
    if (sala && Entero(Buscar(sala->f, "C"), 0) > 1) Poner(sala->f, "C", std::to_string(Entero(Buscar(sala->f, "C"), 0) - 1));
    ses->sala.reset();
    r.push_back(Crear("ulea", {}));
    if (sala) avisarConjunto(*sala, *ses, ses.get(), true, &r);
  }

  void mesg(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Mensaje a la partida (al unirse, TEXT=42 ATTR=EGS: el "estoy aqui" que hace que el anfitrion
    // le de de alta). Los demas lo reciben como '+msg'.
    std::vector<SesionP> destinos;
    if (ses->partida) {
      for (const auto& j : ses->partida->jugadores) {
        if (j != ses) destinos.push_back(j);
      }
    }
    if (destinos.empty() && ses->sala) {
      for (const auto& o : sesiones_) {
        if (o != ses && o->sala && *o->sala == *ses->sala) destinos.push_back(o);
      }
    }
    for (const auto& j : destinos) {
      log("   +msg " + ses->nombre() + " -> " + j->nombre() + ": " + ONull(Buscar(f, "TEXT")) + " " + ONull(Buscar(f, "ATTR")));
      j->escribir(Crear("+msg", {{"N", ses->nombre()}, {"T", Valor(f, "TEXT", "")}, {"F", Valor(f, "ATTR", "")}}));
    }
    r.push_back(Crear("mesg", {}));
  }

  void uadm(const Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    // El anfitrion cambia su sala (parametros, banderas).
    Sala* sala = nullptr;
    if (ses.sala) {
      if (auto s = salas_.find(*ses.sala); s != salas_.end()) sala = s->second.get();
    }
    if (!sala) {
      r.push_back(Crear("uadm", {}));
      return;
    }
    Poner(sala->f, "N", Valor(f, "NAME", Valor(sala->f, "N", "")));
    Poner(sala->f, "D", Valor(f, "DESC", Valor(sala->f, "D", "")));
    Poner(sala->f, "P", Valor(f, "PARAMS", Valor(sala->f, "P", "")));
    Poner(sala->f, "CF", Valor(f, "CUSTFLAGS", Valor(sala->f, "CF", "")));
    r.push_back(Crear("uadm", registroSala(*sala)));
  }

  // Las claves que lee el juego (sub_82825B28, en orden): I T SF CF O S C N D P.
  static Campos registroSala(const Sala& sala) {
    Campos m;
    for (const char* k : {"I", "T", "SF", "CF", "O", "S", "C", "N", "D", "P"}) m.emplace_back(k, ONull(Buscar(sala.f, k)));
    return m;
  }

  void ucre(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Crear sala ("Crear partida"); despues el juego manda gcre. Una por jugador.
    std::vector<int> viejas;
    for (const auto& [id, s] : salas_) {
      if (s->dueno == ses.get()) viejas.push_back(id);
    }
    for (int id : viejas) borrarSala(id, *ses);
    ++siguienteId_;
    auto sala = std::make_unique<Sala>();
    sala->id = siguienteId_;
    sala->dueno = ses.get();
    sala->f = {{"I", std::to_string(sala->id)},
               {"T", Valor(f, "TYPE", "0")},
               {"SF", Valor(f, "SYSFLAGS", "")},
               {"CF", Valor(f, "CUSTFLAGS", "")},
               {"O", ses->nombre()},
               {"S", Valor(f, "SIZE", "4")},
               {"C", "1"},
               {"N", Valor(f, "NAME", "")},
               {"D", ""},
               {"P", Valor(f, "PARAMS", "")}};
    Sala& puesta = *sala;
    salas_[sala->id] = std::move(sala);
    ses->sala = puesta.id;
    // El dueno es miembro y no manda 'sele USERSET0': se le da la ranura 0.
    ses->quitarRanura(0);
    ses->apuntar(Valor(puesta.f, "N", ""), 0);
    r.push_back(Crear("ucre", registroSala(puesta)));
    r.push_back(registroUsuario(*ses, "+usr"));
    r.push_back(registroMiembro(*ses, 0, false));
  }

  void auxi(const SesionP& ses, const Campos& f, std::vector<Mensaje>& r) {
    // Su texto auxiliar (su estado en la sala): se guarda, se devuelve y va un '+usr' nuevo a todos
    // los de su sala, el incluido.
    ses->auxi = Valor(f, "TEXT", "");
    r.push_back(Crear("auxi", f));
    if (!ses->sala) return;
    for (const auto& otro : sesiones_) {
      if (otro != ses && otro->sala && *otro->sala == *ses->sala) otro->escribir(registroUsuario(*ses, "+usr"));
    }
    r.push_back(registroUsuario(*ses, "+usr"));
    if (auto s = salas_.find(*ses->sala); s != salas_.end()) avisarConjunto(*s->second, *ses, ses.get(), false, &r);
  }

  // +who / +usr: G (su partida; 0 = ninguna) y MA (sin el, ConnApi sin XUID).
  static Mensaje registroUsuario(const Sesion& ses, const std::string& orden) {
    return Crear(orden, {{"I", std::to_string(ses.id)},
                         {"M", ses.nombreCuenta},
                         {"N", ses.nombre()},
                         {"MA", ses.maddr},
                         {"A", ses.ip},
                         {"LA", ses.ip},
                         {"G", Ident(ses)},
                         {"P", "1"},
                         {"F", "U"},
                         {"LO", "esES"},
                         {"PRES", "1"},
                         {"X", ses.auxi}});
  }

  void auth(Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    ses.nombreCuenta = !Vacio(Buscar(f, "NAME")) ? *Buscar(f, "NAME") : !Vacio(Buscar(f, "GTAG")) ? *Buscar(f, "GTAG") : ses.nombreCuenta;
    ses.maddr = Valor(f, "MADDR", ses.maddr);
    const bool antes = ses.autenticado;
    ses.autenticado = true;
    if (const auto otro = quienUsa(ses.nombreCuenta, ses.ip)) {
      log("   warning: gamertag '" + ses.nombreCuenta + "' already in use by " + *otro);
    }
    r.push_back(Crear("auth", {{"NAME", ses.nombreCuenta},
                               {"ADDR", ses.ip},
                               {"PERSONAS", ses.nombreCuenta},
                               {"LOC", "esES"},
                               {"MAIL", "lan@lan"},
                               {"SPAM", "NN"},
                               {"TOS", "1"},
                               {"SINCE", "2005.11.15-00:00:00"},
                               {"LAST", "2005.11.15-00:00:00"}}));
    if (!antes && (ses.puerto == PUERTO_SALAS || ses.pc)) alCambiar_();
  }

  void pers(Sesion& ses, const Campos& f, std::vector<Mensaje>& r) {
    ses.persona = !Vacio(Buscar(f, "PERS")) ? *Buscar(f, "PERS") : !Vacio(Buscar(f, "GTAG")) ? *Buscar(f, "GTAG") : ses.nombreCuenta;
    ses.maddr = Valor(f, "MADDR", ses.maddr);
    r.push_back(Crear("pers", {{"PERS", ses.persona},
                               {"LKEY", AzarHex()},
                               {"LOC", "esES"},
                               {"A", ses.ip},
                               {"LA", ses.ip},
                               {"IDLE", "600000"}}));
  }

  // La IP de otro aparato que tiene ahora este gamertag (conectado o apartado); nada si esta libre.
  std::optional<std::string> quienUsa(const std::string& gamertag, const std::string& ip) {
    const std::string buscado = Minusculas(Recortar(gamertag));
    for (const auto& o : sesiones_) {
      if (o->ip == ip || !o->autenticado) continue;
      if (Minusculas(o->nombreCuenta) == buscado || (!o->persona.empty() && Minusculas(o->persona) == buscado)) return o->ip;
    }
    for (const auto& [nombre, a] : apartados_) {
      if (nombre == buscado && a.ip != ip && a.fin > Reloj::now()) return a.ip;
    }
    return std::nullopt;
  }

  // Aparta `gamertag` para `ip` unos minutos; lo que tuviera apartado esa IP se suelta.
  void apartar(const std::string& gamertag, const std::string& ip) {
    const auto ahora = Reloj::now();
    apartados_.erase(std::remove_if(apartados_.begin(), apartados_.end(),
                                    [&](const auto& a) { return a.second.ip == ip || a.second.fin <= ahora; }),
                     apartados_.end());
    const std::string clave = Minusculas(Recortar(gamertag));
    apartados_.erase(std::remove_if(apartados_.begin(), apartados_.end(), [&](const auto& a) { return a.first == clave; }),
                     apartados_.end());
    apartados_.emplace_back(clave, Apartado{ip, ahora + APARTADO});
  }

  void log(const std::string& texto) {
    std::lock_guard<std::mutex> l(mutexRegistro_);
    if (!registro_) return;
    const std::string linea = Hora() + " " + texto + "\n";
    std::fwrite(linea.data(), 1, linea.size(), registro_);
    std::fflush(registro_);
  }

  std::string pcIp_;
  int anuncio_ = -1;
  std::condition_variable anuncioWake_;
  std::string datos_;
  std::function<void()> alCambiar_;
  std::function<std::string()> nombre_;
  Estadisticas estadisticas_;
  std::FILE* registro_ = nullptr;
  std::mutex mutexRegistro_;
  std::vector<int> escuchas_;
  int busqueda_ = -1;
  std::atomic<bool> parado_{false};
  std::mutex mutexLatido_;
  std::condition_variable latido_;

  std::recursive_mutex candado_;
  std::map<int, std::unique_ptr<Sala>> salas_;
  std::vector<std::pair<std::string, std::shared_ptr<Partida>>> partidas_;
  std::vector<SesionP> sesiones_;
  int siguienteId_ = 1000;
  // Gamertags apartados: nombre en minusculas -> (IP, fin). Uno por IP.
  std::vector<std::pair<std::string, Apartado>> apartados_;
  static inline std::atomic<int> cuentaSesiones_{0};
};

std::mutex g_mutex;
std::shared_ptr<Servidor> g_servidor;
// Lo que se le paso a Arrancar, para Revivir; g_quiere: arrancado y sin Parar() desde entonces.
bool g_quiere = false;
std::string g_datos, g_logs, g_pcIp;
std::function<void()> g_alCambiar;
std::function<std::string()> g_nombre;

}  // namespace

static bool ArrancarModo(const std::string& datos, const std::string& logs, std::function<void()> alCambiar,
              std::function<std::string()> nombre, const std::string& pcIp, std::string* error) {
  std::lock_guard<std::mutex> l(g_mutex);
  if (g_servidor && !g_servidor->parado()) return true;
  auto s = std::make_shared<Servidor>(datos, logs, alCambiar, nombre, pcIp);
  std::string motivo;
  if (!s->arrancar(&motivo)) {
    if (error) *error = motivo;
    return false;
  }
  g_servidor = s;
  g_quiere = true;
  g_pcIp = pcIp;
  g_datos = datos;
  g_logs = logs;
  g_alCambiar = std::move(alCambiar);
  g_nombre = std::move(nombre);
  return true;
}

bool Arrancar(const std::string& datos, const std::string& logs, std::function<void()> changed,
              std::function<std::string()> name, std::string* error) {
  return ArrancarModo(datos, logs, changed, name, "", error);
}
bool ArrancarPC(const std::string& datos, const std::string& logs, std::function<void()> changed,
                std::function<std::string()> name, const std::string& ip, std::string* error) {
  return ArrancarModo(datos, logs, changed, name, ip, error);
}
bool Revivir(std::string* error) {
  // Los sockets del que cayo los cierran sus hilos en su siguiente vuelta (VUELTA_MS); hasta entonces
  // los puertos siguen cogidos. Unos cuantos intentos, sin el candado durante la espera.
  for (int intento = 0; intento < 8; ++intento) {
    {
      std::lock_guard<std::mutex> l(g_mutex);
      if (!g_quiere) return false;
      if (g_servidor && !g_servidor->parado()) return true;
      auto s = std::make_shared<Servidor>(g_datos, g_logs, g_alCambiar, g_nombre, g_pcIp);
      std::string motivo;
      if (s->arrancar(&motivo)) {
        g_servidor = s;
        return true;
      }
      if (error) *error = motivo;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(VUELTA_MS));
  }
  return false;
}

void Parar() {
  std::lock_guard<std::mutex> l(g_mutex);
  g_quiere = false;
  if (g_servidor) {
    // Sus hilos lo retienen hasta que acaban.
    g_servidor->parar();
    g_servidor.reset();
  }
}

bool EnMarcha() {
  std::lock_guard<std::mutex> l(g_mutex);
  return g_servidor && !g_servidor->parado();
}

int Jugadores() {
  std::shared_ptr<Servidor> s;
  {
    std::lock_guard<std::mutex> l(g_mutex);
    s = g_servidor;
  }
  return s ? s->jugadores() : 0;
}

}  // namespace nfsmw::servidor
