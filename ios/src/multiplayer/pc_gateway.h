#pragma once
#include <cstdint>
#include <functional>
#include <string>
namespace nfsmw::pc {
// Probe the original PC LAN directory on TCP9900 (no account/login mutation).
// True only while the native PC adapter is active, for its selected PC IPv4.
// IPv4 uses guest/network numeric order (e.g. 0xc0a801ca).
bool IsRacePeer(uint32_t ipv4);
bool Active();
bool Hosting();
void StartHosting();
bool SetHostingPeer(uint32_t ipv4);
bool HasRaceId(uint32_t ipv4);
bool HasLocalRaceId(uint32_t ipv4);
void ObserveRaceId(uint32_t ipv4, uint32_t connectionId);
uint32_t RaceId(uint32_t ipv4);
void SetLocalRaceId(uint32_t ipv4, uint32_t connectionId);
uint32_t LocalRaceId(uint32_t ipv4);
bool Probe(const std::string &ip);
// In-app loopback adapter. Only PC control traffic uses this path; races stay
// peer to peer. No PC-side helper or modification is required.
bool Start(const std::string &ip,
           std::function<void(const std::string &)> trace, std::string *error);
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
