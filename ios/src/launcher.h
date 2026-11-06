// NFSMW Recompiled - the pre-launch screen on iOS (launcher.mm)

#pragma once

#ifdef __OBJC__
#import <Foundation/Foundation.h>
@class UIViewController;
#endif

#include <filesystem>
#include <set>
#include <utility>
#include <string>
#include <vector>

namespace nfsmw::launcher {

// The app's Documents/ folder (LiveContainer's redirected one, inside it).
std::filesystem::path Documents();
// The keyboard's menu key set from settings.json (keyboard_context.cpp).
std::string MenuKeyBinds();
std::string DrivingKeyBinds();
std::string ActionKeyBinds();

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
// The same rows grouped as the launcher shows them: its tab, its section
// title, in the launcher's order (keys not in the list left out).
struct MenuGroup {
  NSString* tab;
  NSString* title;
  std::vector<MenuRow> rows;
};
std::vector<MenuGroup> Groups(NSArray<NSString*>* keys);
// The settings also shown while playing (the launcher's kInGame flag), in its
// order; those of them shown only with the native renderer; and the cvars
// those settings set that apply at once (the rest wait for the next launch).
NSArray<NSString*>* InGameKeys();
bool InGameNeedsNative(NSString* key);
const std::set<std::string>& LiveCvars();
// The launcher's Keyboard controls list (both sets), for the in-game options.
// A hardware key's name as the key lists write it ("1", "Return"...).
NSString* KeyNameForHID(long usage);
UIViewController* MakeKeyBindsEditor(NSMutableDictionary<NSString*, NSString*>* settings, void (^save)(void));
NSMutableDictionary<NSString*, NSString*>* ReadSettings(const std::filesystem::path& documents);
void WriteSettings(const std::filesystem::path& documents, NSDictionary<NSString*, NSString*>* settings);
// A setting's value as the game gets it (Battery mode's when it sets it).
NSString* SettingValue(NSDictionary<NSString*, NSString*>* settings, NSString* key);
// Battery mode is on and sets this one.
bool SetByBatteryMode(NSDictionary<NSString*, NSString*>* settings, NSString* key);
// A HUD size/position setting while Custom HUD is off (the game's value used).
bool HudLocked(NSDictionary<NSString*, NSString*>* settings, NSString* key);
// The game's arguments for these settings (as SettingsArguments).
std::vector<std::string> ArgumentsFor(NSDictionary<NSString*, NSString*>* settings);
#endif

}  // namespace nfsmw::launcher
