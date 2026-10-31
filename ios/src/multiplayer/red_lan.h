// Directly imported/adapted from victorgbd/NFSMW-Recompiled-Mobile,
// commit d534be88edf5bcd362445c84e5b79c61e29571e7 (GPL-3.0).
// Original Android LAN implementation and this C++ adaptation: victorgbd.
// Local integration/Darwin changes are recorded in docs/TECHNICAL.md.
// La red de la LAN del lanzador de iOS: lo que en la app de Android hacen Ajustes (direccionValida,
// resolverIpv4), ComprobacionGamertag, BuscadorServidores y ServidorEa.ipLocal, con sockets POSIX.
// Todo lo que espera a la red bloquea: llamarlo fuera del hilo principal.

#pragma once

#include <optional>
#include <string>
#include <vector>

namespace nfsmw::red {

// El del servidor de la LAN (nfsmw-server-lan o un movil anfitrion) para la comprobacion del
// gamertag (TCP) y la busqueda de servidores (UDP). No es de EA.
constexpr int PUERTO_APP = 10902;

bool IpValida(const std::string& ip);

// Una IPv4 o un nombre de equipo ("mi-pc", "servidor.lan"). Lo que solo tiene numeros y puntos tiene
// que ser una IP entera: "10.0.0" no es un nombre.
bool DireccionValida(const std::string& direccion);

// La IPv4 de una direccion: ella misma si ya es una IP, o la que da la red para ese nombre; "" si no
// se encuentra. El juego solo entiende IPs (su red_dns contesta con ella a todos sus nombres).
std::string ResolverIpv4(const std::string& direccion);

// El nombre que el juego usara: vacio es el de fabrica (user_gamertag).
std::string GamertagEfectivo(const std::string& gamertag);

// Si el gamertag esta libre en ese servidor: "GAMERTAG <nombre>" y contesta "FREE" o "IN_USE". Un
// "FREE" lo aparta para este telefono unos minutos (10 en el servidor).
enum class Comprobacion { kLibre, kEnUso, kSinRespuesta };
Comprobacion ComprobarGamertag(const std::string& ip, const std::string& gamertag);

// Un servidor que contesto a la busqueda.
struct Encontrado {
  std::string ip;
  std::string nombre;
  int jugadores = 0;
};

// Los que contestan a "NFSMW_DISCOVER" (UDP), por orden de llegada; nullopt si este telefono no esta
// en ninguna red local. Bloquea el plazo entero, 1,5 s o algo mas.
std::optional<std::vector<Encontrado>> BuscarServidores();

// Cuanto vale una interfaz como red local, por su nombre: la Wi-Fi 3, el punto de acceso 2, otra de
// cable 1, otras 0; -1 = no es la LAN (datos moviles, VPN, AirDrop).
int PuntosInterfaz(const std::string& nombre);

// La IP de este telefono en la red local, la que tienen que poner los demas: la de la Wi-Fi o la del
// punto de acceso. "" si no hay ninguna.
std::string IpLocal();

}  // namespace nfsmw::red
