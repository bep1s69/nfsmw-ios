// Integration of victorgbd's Android LAN implementation and C++ iOS adaptation.
#pragma once
#include <filesystem>
#include <string>
namespace nfsmw::lan {
struct Prepared {
  std::string ip;
  std::string error;
  bool hosting = false;
};
// Blocking network work: run on a background queue before launching the game.
Prepared Prepare(const std::string& mode, const std::string& server,
                 const std::string& gamertag, const std::filesystem::path& documents);
}
