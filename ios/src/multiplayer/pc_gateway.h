#pragma once
#include <cstdint>
#include <functional>
#include <string>
#include <vector>
namespace nfsmw::pc {
// Probe the original PC LAN directory on TCP9900 (no account/login mutation).
// Native PC race peers, at most three. IPv4 uses guest/network numeric order
// (e.g. 0xc0a801ca). Each peer keeps its own CommUDP connection IDs and role.
bool IsRacePeer(uint32_t ipv4);
bool Active();
// This device's lobby accepts native PC guests.
bool Hosting();
// This device is the CommUDP listener for that PC (the PC sent INIT first).
bool Hosting(uint32_t ipv4);
// First INIT decides the role for peers whose role is not fixed yet.
void NoteInit(uint32_t ipv4, bool received);
void StartHosting();
bool SetHostingPeer(uint32_t ipv4);
// Guest of a mobile or PC host: replace the PC peer list, keeping the IDs of
// peers that stay. Roles of new peers are learned from their first INIT.
void SetGuestPeers(const std::vector<uint32_t> &ipv4);
std::vector<uint32_t> Peers();
bool HasRaceId(uint32_t ipv4);
bool HasLocalRaceId(uint32_t ipv4);
void ObserveRaceId(uint32_t ipv4, uint32_t connectionId);
uint32_t RaceId(uint32_t ipv4);
void SetLocalRaceId(uint32_t ipv4, uint32_t connectionId);
uint32_t LocalRaceId(uint32_t ipv4);
// Probe the original PC LAN directory on TCP9900 (no account/login mutation).
bool Probe(const std::string &ip);
// Mobile (iOS/Android) lobby directory on TCP30960.
bool ProbeMobile(const std::string &ip);
// In-app loopback adapter. Only PC control traffic uses this path; races stay
// peer to peer. No PC-side helper or modification is required.
bool Start(const std::string &ip,
           std::function<void(const std::string &)> trace, std::string *error);
// Automatic LAN: the game's directory always connects to 127.0.0.1:30960.
// decide() runs on each new connection and returns the lobby to use: a mobile
// directory (pc=false, relayed byte for byte) or a native PC (adapted).
struct Route {
  std::string ip;
  bool pc = false;
};
bool StartAuto(std::function<Route()> decide,
               std::function<void(const std::string &)> trace,
               std::string *error);
void Stop();
// Pure frame transformations, exposed for protocol regression tests.
std::string Field(const std::string &body, const std::string &key);
std::string Put(std::string body, const std::string &key,
                const std::string &value);
std::string Frame(const std::string &command, const std::string &body,
                  const std::string &subtype = std::string(4, '\0'));
// Translate only the observed PC room build tag for the Xbox room parser.
// This does not establish session/race compatibility.
std::string AdaptRoom(const std::string &body);
// PC-only local Xbox session/address envelopes; no peer/race payload rewrite.
std::string AdaptGame(const std::string &body);
std::string AdaptLogin(const std::string &body, const std::string &sourceIp);
std::string AdaptUser(const std::string &body);
std::string HostLogin(const std::string &body, const std::string &ip);
std::string HostReply(const std::string &command, const std::string &body, const std::string &hostIp);
std::string Advertisement(const std::string &name, unsigned players, uint32_t session);
std::string LocalStats(const std::string &name);
} // namespace nfsmw::pc
