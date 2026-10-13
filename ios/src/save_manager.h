// NFSMW Recompiled - the save manager (save_manager.mm): the game's saves
// listed with their progress, backups, export/import, and a copy in an
// iCloud Drive folder with its sync state.

#pragma once

#include <filesystem>

#ifdef __OBJC__
@class UIViewController;

namespace nfsmw::saves {

// The screen (pushed from the launcher's Game tab).
UIViewController* MakeSaveManager(const std::filesystem::path& documents);

}  // namespace nfsmw::saves
#endif

namespace nfsmw::saves {

// At launcher start: a backup of each save that changed since its last one,
// and saves changed only on this device copied to the iCloud Drive folder.
// Never overwrites a local save. Returns how many saves need the player's
// attention (newer in iCloud, or changed on both sides).
int AutoSync(const std::filesystem::path& documents);

}  // namespace nfsmw::saves
