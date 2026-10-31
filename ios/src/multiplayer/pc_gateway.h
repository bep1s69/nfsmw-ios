#pragma once
#include <functional>
#include <string>
namespace nfsmw::pc {
// Probe the original PC LAN directory on TCP9900 (no account/login mutation).
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
std::string LocalStats(const std::string &name);
} // namespace nfsmw::pc
