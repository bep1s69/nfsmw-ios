// Integration of victorgbd's Android LAN implementation and C++ iOS adaptation.
#pragma once
#include <filesystem>
#include <string>
namespace nfsmw::lan {
struct Prepared {
  std::string ip;
  std::string error;
  std::string own_ip;
  bool hosting = false;
  bool pc = false;
};
// mode: "auto" (the game's sign-in picks a nearby lobby or hosts one, for
// phones and native PCs alike), "join" (manual address), "host", "host_pc".
// Blocking network work: run on a background queue before launching the game.
Prepared Prepare(const std::string& mode, const std::string& server,
                 const std::string& gamertag, const std::filesystem::path& documents);
}
