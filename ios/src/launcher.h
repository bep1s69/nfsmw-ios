// NFSMW Recompiled - the pre-launch screen on iOS (launcher.mm)

#pragma once

#ifdef __OBJC__
#import <Foundation/Foundation.h>
#endif

#include <filesystem>
#include <utility>
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

#ifdef __OBJC__
// The in-game options menu (ingame_options.mm) shows some of the launcher's
// own settings, with the same titles, choices and Battery mode rules, and
// saves them to the same Documents/settings.json.
struct MenuRow {
  NSString* key;
  NSString* title;
  NSString* summary;
  bool is_switch;
  std::vector<std::pair<NSString*, NSString*>> choices;  // title, value
};
// The rows for these keys, in this order (unknown keys left out).
std::vector<MenuRow> Rows(NSArray<NSString*>* keys);
NSMutableDictionary<NSString*, NSString*>* ReadSettings(const std::filesystem::path& documents);
void WriteSettings(const std::filesystem::path& documents, NSDictionary<NSString*, NSString*>* settings);
// A setting's value as the game gets it (Battery mode's when it sets it).
NSString* SettingValue(NSDictionary<NSString*, NSString*>* settings, NSString* key);
// Battery mode is on and sets this one.
bool SetByBatteryMode(NSDictionary<NSString*, NSString*>* settings, NSString* key);
// The game's arguments for these settings (as SettingsArguments).
std::vector<std::string> ArgumentsFor(NSDictionary<NSString*, NSString*>* settings);
#endif

}  // namespace nfsmw::launcher
