// NFSMW Recompiled - the game's achievement list, for the pre-launch screen

#pragma once

#include <filesystem>

namespace nfsmw::achievements {

// Writes the achievements the SDK loaded from the game's XEX (names,
// descriptions, gamerscore, icons) to Documents/achievements/: list.json and
// icons/<image id>.png. The pre-launch screen reads them, plus the SDK's own
// unlock file (Documents/data/achievements/<title id>.toml). Call once the
// XEX is loaded (OnPostSetup).
void Export(const std::filesystem::path& documents);

}  // namespace nfsmw::achievements
