// NFSMW Recompiled - the launcher's settings catalogue (settings_catalog.mm)
//
// Every setting the launcher and the in-game options show (Sections()), what
// each one is (OptionFlag), its value with Battery mode and Custom HUD rules
// (Value), the screen shape and resolution titles, the keyboard bind tables,
// settings.json and the game arguments (Arguments). No UI here: launcher.mm
// and ingame_options.mm (through launcher.h) draw it. Split out of
// launcher.mm on November 6 (docs/MENU_REDESIGN.md, step 2).

#pragma once

#import <UIKit/UIKit.h>

#include <filesystem>
#include <string>
#include <vector>

namespace nfsmw::catalog {

namespace fs = std::filesystem;

// ---------------------------------------------------------------------------
//  The options
// ---------------------------------------------------------------------------
enum class Type { kSwitch, kChoice, kText, kLink };  // kLink: a row that opens a screen

// What each setting is, kept on the setting itself so the launcher and the
// in-game options (ingame_options.mm, through launcher.h) read one source.
enum OptionFlag : unsigned {
  kInGame = 1u << 0,         // also in the options while playing
  kInGameNative = 1u << 1,   // ...but only with the native renderer
  kNativeOnly = 1u << 2,     // greyed out in the launcher without the native renderer
  kEmulatedOnly = 1u << 3,   // greyed out in the launcher with the native renderer
};

struct Choice {
  NSString* title;
  NSString* value;
};

struct Option {
  NSString* key;
  Type type;
  NSString* title;
  NSString* summary;
  NSString* default_value;  // switches: @"true" / @"false"
  std::vector<Choice> choices = {};
  unsigned flags = 0;          // OptionFlag
  const char* live = nullptr;  // in game: the cvars that apply at once ("a,b"); the rest wait for the next launch
};

struct Section {
  NSString* title;
  NSString* footer;
  std::vector<Option> options;
  int tab = 0;  // Tabs(): which tab shows it
};

// The launcher's tabs (a segmented control at the top).
enum Tab { kTabGame, kTabExtras, kTabGraphics, kTabControls, kTabAudio, kTabAdvanced, kTabCount };

// What the game uses when an option has never been changed: the iOS port's
// current defaults (ios_main.mm), which are Android's except where noted.
// ---------------------------------------------------------------------------
//  Keyboard controls
// ---------------------------------------------------------------------------
// The SDK's keyboard driver (mnk_mode) presses the controller's inputs from
// the keys in its keybind_* settings: a comma-separated list of key names
// (rex/ui/keybinds.cpp: "A", "Up", "Space", "Shift", "Return"...), optionally
// "Shift+X". The launcher keeps each one as "kb_<setting>"; unset, the
// default below. The defaults follow the PC version's way of playing.
struct KeyBind {
  NSString* setting;  // the SDK's cvar
  NSString* action;   // what it does in NFSMW
  NSString* pad;      // the controller input it presses
  NSString* standard;       // the key(s) while driving
  NSString* menu_standard;  // the key(s) in menus and pause screens (0.6)
};

NSArray<NSString*>* TabTitles();
std::vector<Choice> Percent(NSString* game);
NSString* AboutText();
bool HasFlag(NSString* key, unsigned flag);
bool EmulatorOnly(NSString* key);
bool NativeOnly(NSString* key);
const std::vector<KeyBind>& KeyBinds();
const std::vector<KeyBind>& ActionBinds();
NSString* KeyBindKey(const KeyBind& b, bool menu = false);
NSString* KeyBindValue(NSDictionary<NSString*, NSString*>* s, const KeyBind& b, bool menu = false);
NSString* KeyName(UIKeyboardHIDUsage usage);
NSString* KeysForDisplay(NSString* value);
CGSize ScreenPixels();
NSString* AutoAspect();
int FitSceneWidth();
CGSize SceneSize(NSString* aspect);
NSString* NativeScaleTitle();
NSString* ScaleChoiceTitle(NSString* value, NSDictionary<NSString*, NSString*>* s);
NSString* ChoiceTitle(NSString* key, const Choice& c, NSDictionary<NSString*, NSString*>* s);
NSString* ScaleSummary();
bool SupportsHighFrameRates();
std::vector<Choice> FrameRateChoices();
const std::vector<Section>& Sections();
const Option* FindOption(NSString* key);
bool GamertagValid(NSString* g);
NSString* SettingsPath(const fs::path& docs);
NSMutableDictionary<NSString*, NSString*>* LoadSettings(const fs::path& docs);
void SaveSettings(const fs::path& docs, NSDictionary<NSString*, NSString*>* s);
NSString* BatteryValue(NSString* key);
NSString* HudDefault(NSString* key);
NSString* Value(NSDictionary<NSString*, NSString*>* s, NSString* key);
bool On(NSDictionary<NSString*, NSString*>* s, NSString* key);
NSString* ResolvedAspect(NSDictionary<NSString*, NSString*>* s);
bool Msaa(NSDictionary<NSString*, NSString*>* s);
std::vector<std::string> Arguments(NSDictionary<NSString*, NSString*>* s);

}  // namespace nfsmw::catalog
