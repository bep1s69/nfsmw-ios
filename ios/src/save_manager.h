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

// After the game writes a save (game_pool.cpp hears of it): AutoSync of
// <HOME>/Documents three seconds after the last write, off the game's threads,
// so a save reaches iCloud without waiting for the next launch.
void SyncAfterGameSave();

}  // namespace nfsmw::saves
