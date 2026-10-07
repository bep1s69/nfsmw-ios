// NFSMW Recompiled - the pre-launch screen on iOS (launcher.mm)

#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace nfsmw::launcher {

// The app's Documents/ folder (LiveContainer's redirected one, inside it).
std::filesystem::path Documents();

// The ISOs in Documents/, alphabetically.
std::vector<std::filesystem::path> FindIsos(const std::filesystem::path& documents);

// Shows the settings and the Play button, and returns when Play is tapped:
// the ISO to play. Settings are saved to Documents/settings.json as they
// change. Call on the main thread, before the game's SDL window exists.
std::filesystem::path Run(const std::filesystem::path& documents);

// The game's arguments for the saved settings ("--name=value" each). They
// replace the defaults with the same name; Documents/extra_args.txt comes
// after them and wins.
std::vector<std::string> SettingsArguments(const std::filesystem::path& documents);

}  // namespace nfsmw::launcher
