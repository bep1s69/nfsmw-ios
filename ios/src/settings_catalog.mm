// NFSMW Recompiled - the launcher's settings catalogue (see settings_catalog.h)

#include "app_scene.h"
#import <UIKit/UIKit.h>
#include <algorithm>
#include <cctype>
#include <cmath>
#include <functional>
#include <regex>
#include <system_error>
#include <unordered_map>
#include <dlfcn.h>
#include <mach-o/loader.h>

#include "settings_catalog.h"
#include "launcher.h"

namespace nfsmw::catalog {




NSArray<NSString*>* TabTitles() {
  return @[ @"Play", @"Display", @"Battery", @"Graphics", @"HUD & Controls", @"Gameplay", @"Audio", @"Advanced" ];
}

// The choices 0, 10, ... 100 (traffic density).
std::vector<Choice> Percent(NSString* game) {
  std::vector<Choice> c;
  for (int i = 0; i <= 100; i += 10) {
    NSString* v = [NSString stringWithFormat:@"%d", i];
    c.push_back({[v isEqualToString:game] ? [v stringByAppendingString:@" (game)"] : v, v});
  }
  return c;
}

// Settings only the emulated (Vulkan) renderer uses: greyed out while the
// native Metal renderer draws the game. And the reverse.
// "NFSMW Recompiled 0.2.0 · build 1A2B3C4D": the app's version and its
// executable's UUID (the same one the log names), for tester reports.
NSString* AboutText() {
  NSString* version = [NSBundle.mainBundle objectForInfoDictionaryKey:@"CFBundleShortVersionString"] ?: @"?";
  NSString* build = @"?";
  // This executable's header (under LiveContainer, image 0 is LiveContainer).
  Dl_info info = {};
  dladdr(reinterpret_cast<const void*>(&AboutText), &info);
  const auto* header = reinterpret_cast<const mach_header_64*>(info.dli_fbase);
  if (header) {
    const auto* cmd = reinterpret_cast<const load_command*>(header + 1);
    for (uint32_t i = 0; i < header->ncmds; ++i) {
      if (cmd->cmd == LC_UUID) {
        const uint8_t* u = reinterpret_cast<const uuid_command*>(cmd)->uuid;
        build = [NSString stringWithFormat:@"%02X%02X%02X%02X", u[0], u[1], u[2], u[3]];
        break;
      }
      cmd = reinterpret_cast<const load_command*>(reinterpret_cast<const uint8_t*>(cmd) + cmd->cmdsize);
    }
  }
  return [NSString stringWithFormat:@"NFSMW Recompiled %@ · build %@", version, build];
}

bool HasFlag(NSString* key, unsigned flag) {
  const Option* o = FindOption(key);
  return o && (o->flags & flag);
}
bool EmulatorOnly(NSString* key) { return HasFlag(key, kEmulatedOnly); }
bool NativeOnly(NSString* key) { return HasFlag(key, kNativeOnly); }


// Two sets (0.6, Stefan: context-aware keys): the game switches between them
// when a menu comes up or goes (keyboard_context.cpp). Driving follows the
// PC's keys; in menus Return accepts and Escape goes back, as on PC.
const std::vector<KeyBind>& KeyBinds() {
  static const std::vector<KeyBind> binds = {
      {@"keybind_right_trigger", @"Accelerate", @"RT", @"Up,W", @"RBracket"},
      {@"keybind_left_trigger", @"Brake / reverse", @"LT", @"Down,S", @"LBracket"},
      {@"keybind_lstick_left", @"Steer left / menu left", @"left stick", @"Left,A", @"Left"},
      {@"keybind_lstick_right", @"Steer right / menu right", @"left stick", @"Right,D", @"Right"},
      {@"keybind_lstick_up", @"Menu up", @"left stick", @"", @"Up"},
      {@"keybind_lstick_down", @"Menu down", @"left stick", @"", @"Down"},
      {@"keybind_a", @"Handbrake / accept", @"A", @"Space", @"Return,Space,NumpadEnter"},
      {@"keybind_b", @"Nitrous / back", @"B", @"Alt", @"Escape,Backspace"},
      {@"keybind_x", @"Speedbreaker", @"X", @"X", @"X"},
      {@"keybind_y", @"Y (map, details)", @"Y", @"Tab", @"Tab"},
      // Menus: WASD is the right stick (Stefan: arrows alone move in menus),
      // which turns the camera in Showcase and moves the world map's cursor.
      {@"keybind_rstick_up", @"Shift up / camera up", @"right stick", @"Shift", @"W"},
      {@"keybind_rstick_down", @"Shift down / camera down", @"right stick", @"Control", @"S"},
      {@"keybind_left_shoulder", @"Look back / previous tab", @"LB", @"C", @"Q,PageUp"},
      {@"keybind_right_shoulder", @"Change camera / next tab", @"RB", @"V", @"E,PageDown"},
      {@"keybind_back", @"Reset car", @"Back", @"R", @"R"},
      {@"keybind_start", @"Pause / start", @"Start", @"Escape,P", @"P"},
      // The D-pad in free roam (touch_controls.mm's ENTER/MAP/SMS/LIST): the
      // PC's keys for them (Stefan: B for the Blacklist).
      {@"keybind_dpad_up", @"Enter shop / engage event", @"D-pad up", @"Return,I", @"I"},
      {@"keybind_dpad_down", @"Blacklist", @"D-pad down", @"B,K", @"K"},
      {@"keybind_dpad_left", @"World map", @"D-pad left", @"M,J", @"J"},
      {@"keybind_dpad_right", @"SMS messages", @"D-pad right", @"T,L", @"L"},
      {@"keybind_rstick_left", @"Camera left", @"right stick", @"", @"A"},
      {@"keybind_rstick_right", @"Camera right", @"right stick", @"", @"D"},
      {@"keybind_lstick_press", @"Left stick click", @"L3", @"", @""},
      {@"keybind_rstick_press", @"Right stick click", @"R3", @"", @""},
      {@"keybind_guide", @"Guide", @"Guide", @"", @""},
  };
  return binds;
}

// Actions of the in-game options' Actions tab on keys of their own, while
// driving (keyboard_prompts.mm; Stefan, November 2: number keys). Same
// storage as the binds ("kb_<setting>"); `pad` is shown as "action".
const std::vector<KeyBind>& ActionBinds() {
  static const std::vector<KeyBind> binds = {
      {@"action_reset_car", @"Reset car", @"action", @"1", @""},
      {@"action_auto_drive", @"Auto drive", @"action", @"2", @""},
      {@"action_heat_down", @"Heat -1", @"action", @"3", @""},
      {@"action_heat_up", @"Heat +1", @"action", @"4", @""},
  };
  return binds;
}

// "kb_<setting>" (driving) or "kbm_<setting>" (menus) in settings.json.
NSString* KeyBindKey(const KeyBind& b, bool menu) {
  return [(menu ? @"kbm_" : @"kb_") stringByAppendingString:b.setting];
}

NSString* KeyBindValue(NSDictionary<NSString*, NSString*>* s, const KeyBind& b, bool menu) {
  NSString* v = s[KeyBindKey(b, menu)];
  return v ?: (menu ? b.menu_standard : b.standard);
}


// A key, as the SDK names it, from a hardware keyboard press (UIKey).
NSString* KeyName(UIKeyboardHIDUsage usage) {
  if (usage >= UIKeyboardHIDUsageKeyboardA && usage <= UIKeyboardHIDUsageKeyboardZ) {
    return [NSString stringWithFormat:@"%c", char('A' + (usage - UIKeyboardHIDUsageKeyboardA))];
  }
  if (usage >= UIKeyboardHIDUsageKeyboard1 && usage <= UIKeyboardHIDUsageKeyboard9) {
    return [NSString stringWithFormat:@"%c", char('1' + (usage - UIKeyboardHIDUsageKeyboard1))];
  }
  if (usage >= UIKeyboardHIDUsageKeyboardF1 && usage <= UIKeyboardHIDUsageKeyboardF12) {
    return [NSString stringWithFormat:@"F%d", int(usage - UIKeyboardHIDUsageKeyboardF1) + 1];
  }
  if (usage >= UIKeyboardHIDUsageKeypad1 && usage <= UIKeyboardHIDUsageKeypad9) {
    return [NSString stringWithFormat:@"Numpad%d", int(usage - UIKeyboardHIDUsageKeypad1) + 1];
  }
  switch (usage) {
    case UIKeyboardHIDUsageKeyboard0: return @"0";
    case UIKeyboardHIDUsageKeypad0: return @"Numpad0";
    case UIKeyboardHIDUsageKeyboardReturnOrEnter: return @"Return";
    case UIKeyboardHIDUsageKeypadEnter: return @"NumpadEnter";
    case UIKeyboardHIDUsageKeyboardEscape: return @"Escape";
    case UIKeyboardHIDUsageKeyboardDeleteOrBackspace: return @"Backspace";
    case UIKeyboardHIDUsageKeyboardTab: return @"Tab";
    case UIKeyboardHIDUsageKeyboardSpacebar: return @"Space";
    case UIKeyboardHIDUsageKeyboardHyphen: return @"Minus";
    case UIKeyboardHIDUsageKeyboardEqualSign: return @"Plus";
    case UIKeyboardHIDUsageKeyboardOpenBracket: return @"LBracket";
    case UIKeyboardHIDUsageKeyboardCloseBracket: return @"RBracket";
    case UIKeyboardHIDUsageKeyboardBackslash: return @"Backslash";
    case UIKeyboardHIDUsageKeyboardSemicolon: return @"Semicolon";
    case UIKeyboardHIDUsageKeyboardQuote: return @"Quote";
    case UIKeyboardHIDUsageKeyboardGraveAccentAndTilde: return @"Backtick";
    case UIKeyboardHIDUsageKeyboardComma: return @"Comma";
    case UIKeyboardHIDUsageKeyboardPeriod: return @"Period";
    case UIKeyboardHIDUsageKeyboardSlash: return @"Slash";
    case UIKeyboardHIDUsageKeyboardCapsLock: return @"CapsLock";
    case UIKeyboardHIDUsageKeyboardInsert: return @"Insert";
    case UIKeyboardHIDUsageKeyboardHome: return @"Home";
    case UIKeyboardHIDUsageKeyboardPageUp: return @"PageUp";
    case UIKeyboardHIDUsageKeyboardDeleteForward: return @"Delete";
    case UIKeyboardHIDUsageKeyboardEnd: return @"End";
    case UIKeyboardHIDUsageKeyboardPageDown: return @"PageDown";
    case UIKeyboardHIDUsageKeyboardRightArrow: return @"Right";
    case UIKeyboardHIDUsageKeyboardLeftArrow: return @"Left";
    case UIKeyboardHIDUsageKeyboardDownArrow: return @"Down";
    case UIKeyboardHIDUsageKeyboardUpArrow: return @"Up";
    case UIKeyboardHIDUsageKeyboardLeftShift:
    case UIKeyboardHIDUsageKeyboardRightShift: return @"Shift";
    case UIKeyboardHIDUsageKeyboardLeftControl:
    case UIKeyboardHIDUsageKeyboardRightControl: return @"Control";
    case UIKeyboardHIDUsageKeyboardLeftAlt:
    case UIKeyboardHIDUsageKeyboardRightAlt: return @"Alt";
    default: return nil;  // Cmd and keys the driver has no name for
  }
}

// For display: "Up, W" -> "Up or W"; "Control" -> "Ctrl"; nothing -> "—".
NSString* KeysForDisplay(NSString* value) {
  NSMutableArray<NSString*>* keys = [NSMutableArray array];
  for (NSString* k in [value componentsSeparatedByString:@","]) {
    NSString* t = [k stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
    if (t.length) [keys addObject:[t isEqualToString:@"Control"] ? @"Ctrl" : [t isEqualToString:@"Escape"] ? @"Esc" : t];
  }
  return keys.count ? [keys componentsJoinedByString:@" or "] : @"—";
}

// The screen in landscape, in pixels (long side, short side).
CGSize ScreenPixels() {
  const CGSize n = nfsmw::AppScreen().nativeBounds.size;
  return CGSizeMake(std::max(n.width, n.height), std::min(n.width, n.height));
}

// "auto": the shape closest to the screen's.
NSString* AutoAspect() {
  const CGSize px = ScreenPixels();
  const double r = px.width / px.height;
  // Wider than 16:9: a scene of this screen's own shape (FitSceneWidth).
  // Narrower: the game's 4:3 mode, the only narrower one it has.
  return r > 16.0 / 9.0 + 0.02 ? @"wide" : r < 1.6 ? @"4:3" : @"16:9";
}

// Fit this screen, wider than 16:9: the scene as wide as the screen's shape
// at 720 high, in steps of 8 (1560 on a 2868x1320 iPhone).
int FitSceneWidth() {
  const CGSize px = ScreenPixels();
  const int w = int(std::lround(720.0 * px.width / px.height / 8.0)) * 8;
  return std::clamp(w, 1288, 2400);
}

// The game's scene for a shape ("16:9", "4:3", "wide"), in 1x pixels.
CGSize SceneSize(NSString* aspect) {
  if ([aspect isEqualToString:@"wide"]) return CGSizeMake(FitSceneWidth(), 720);
  if ([aspect isEqualToString:@"4:3"]) return CGSizeMake(960, 720);
  return CGSizeMake(1280, 720);
}

NSString* NativeScaleTitle() {
  return [NSString stringWithFormat:@"Native · %.0fp (this screen)", ScreenPixels().height];
}


// A render resolution's title with the pixels it draws on this device, in
// the shape in use: "1x · 1560×720 (Xbox 360)", "Native · 2868×1320".
NSString* ScaleChoiceTitle(NSString* value, NSDictionary<NSString*, NSString*>* s) {
  const CGSize scene = SceneSize(ResolvedAspect(s));
  const CGSize px = ScreenPixels();
  const bool native = [value isEqualToString:@"native"];
  const double k = native ? std::min(px.width / scene.width, px.height / scene.height) : value.doubleValue;
  const long w = std::lround(scene.width * k / 2.0) * 2, h = std::lround(scene.height * k / 2.0) * 2;
  if (native) return [NSString stringWithFormat:@"Native · %ld×%ld (this screen)", w, h];
  return [NSString stringWithFormat:@"%@x · %ld×%ld%@", value, w, h,
                                    [value isEqualToString:@"1"] ? @" (Xbox 360)" : @""];
}

// A choice's title as shown (the render resolutions depend on the device and shape).
NSString* ChoiceTitle(NSString* key, const Choice& c, NSDictionary<NSString*, NSString*>* s) {
  return [key isEqualToString:@"scale"] ? ScaleChoiceTitle(c.value, s) : c.title;
}

NSString* ScaleSummary() {
  const CGSize px = ScreenPixels();
  return [NSString stringWithFormat:
      @"How many pixels the game is drawn with: 1x is the Xbox 360's 720p. Native draws as many as "
      @"this screen shows (%.0f pixels high, about %.2fx), no more and no less. Higher is sharper and "
      @"heavier: with the native renderer, 1.5x costs about half of 2x. Without it, the emulated "
      @"renderer rounds to 1x or 2x.",
      px.height, px.height / 720.0];
}

bool SupportsHighFrameRates() {
  // Screen capability, not its temporary refresh rate under Low Power Mode.
  return nfsmw::AppScreen().maximumFramesPerSecond >= 120;
}

std::vector<Choice> FrameRateChoices() {
  if (SupportsHighFrameRates()) return {{@"30", @"30"}, {@"40", @"40"},
                                       {@"60", @"60"}, {@"120", @"120"}};
  return {{@"30", @"30"}, {@"60", @"60"}};
}

const std::vector<Section>& Sections() {
  static const std::vector<Section> sections = {
      {@"Setup", nil, {
           {@"setup_again", Type::kLink, @"Set up again", @"Open first-launch setup.", @""},
       }, kTabGame},
      {@"Saves", nil,
       {
           {@"saves", Type::kLink, @"Save manager",
            @"Your careers with their progress; backups, restore, export and import; and a copy "
            @"in an iCloud Drive folder, kept in sync between your devices.",
            @""},
       }, kTabGame},
      {@"Multiplayer", @"Play on the same Wi-Fi with another iPhone, iPad or Android device.",
       {
           {@"multiplayer_setup", Type::kLink, @"Host or join a game",
            @"Find nearby hosts, check your connection and launch multiplayer.", @""},
       }, kTabGame},
      {@"Career", @"Features of the PC mod Extra Options (nfsmods.xyz/mod/43), ported to the Xbox 360 "
       @"game.",
       {
           {@"marker_count", Type::kChoice, @"Markers after beating a rival",
            @"How many of the six markers you pick after beating a Blacklist rival. The game's "
            @"is 2.",
            @"2",
            {{@"1", @"1"}, {@"2", @"2"}, {@"3", @"3"}, {@"4", @"4"}, {@"5", @"5"}, {@"6", @"6"}}, kInGame, "nfsmw_marker_count"},
           {@"car_limit", Type::kChoice, @"Cars you can buy",
            @"How many cars you can buy at the car lot. Blacklist and bonus cars do not count. "
            @"The game's is 10.",
            @"10",
            {{@"10", @"10"}, {@"12", @"12"}, {@"15", @"15"}, {@"18", @"18"}, {@"20", @"20"},
             {@"25", @"25"}}, kInGame, "nfsmw_purchased_car_limit"},
           {@"no_rev_limiter", Type::kSwitch, @"No rev limiter",
            @"The engine revs past the red line instead of bouncing off it, as Extra Options' "
            @"NoRevLimiter.",
            @"false", {}, kInGame, "nfsmw_no_rev_limiter"},
           {@"showcase_unlimited", Type::kSwitch, @"Unlimited showcase camera",
            @"In Showcase the camera turns all the way round and zooms without its limits, as "
            @"Extra Options' GarageRotate / GarageZoom.",
            @"false", {}, kInGame, "nfsmw_showcase_unlimited"},
           {@"unlock_all_things", Type::kSwitch, @"Unlock everything",
            @"All cars, parts and events unlocked, as Extra Options' UnlockAllThings. Your "
            @"career's progress is not changed; turning it off locks them again.",
            @"false", {}, kInGame, "nfsmw_unlock_all_things"},
           {@"skip_career_intro", Type::kSwitch, @"Skip the career intro",
            @"A new career starts without the intro races, as Extra Options' SkipCareerIntro.",
            @"false", {}, kInGame, "nfsmw_skip_career_intro"},
           {@"skip_movies", Type::kSwitch, @"Skip movies",
            @"Skips the game's movies, as Extra Options' SkipMovies: the EA logo and intro go "
            @"straight to \"press start\". The story movies of the career are skipped too.",
            @"false", {}, kInGame, "nfsmw_skip_movies"},
           {@"old_bridge", Type::kSwitch, @"Open the road to the Old Bridge",
            @"Removes the barrier that closes the road to the Old Bridge.",
            @"false"},
           {@"impound_strikes", Type::kChoice, @"Impound strikes of a new car",
            @"How many times a car you buy can be busted before it is impounded. Cars you "
            @"already have keep theirs. The game's is 3.",
            @"3",
            {{@"3 (game)", @"3"}, {@"4", @"4"}, {@"5", @"5"}, {@"10", @"10"}}, kInGame, "nfsmw_impound_strikes"},
           {@"impound_strikes_max", Type::kChoice, @"Most impound strikes",
            @"The most strikes a car can reach with impound markers. The game's is 5.",
            @"5",
            {{@"5 (game)", @"5"}, {@"10", @"10"}, {@"20", @"20"}}, kInGame, "nfsmw_impound_strikes_max"},
       }, kTabExtras},
      {@"Speedbreaker", nil,
       {
           {@"infinite_speedbreaker", Type::kSwitch, @"Infinite Speedbreaker",
            @"The Speedbreaker never runs out (from the Xbox 360 prototype's debug menu).",
            @"false", {}, kInGame, "nfsmw_infinite_speedbreaker"},
           {@"infinite_nos", Type::kSwitch, @"Infinite nitrous",
            @"Nitrous never runs out (from the Xbox 360 prototype's debug menu). May apply to "
            @"opponents too.",
            @"false", {}, kInGame, "nfsmw_infinite_nos"},
           {@"sb_recharge_time", Type::kChoice, @"Refill time",
            @"How long the Speedbreaker takes to fill up again. The game's is 25 seconds.",
            @"25",
            {{@"10 s", @"10"}, {@"15 s", @"15"}, {@"25 s (game)", @"25"}, {@"40 s", @"40"}}, kInGame, "nfsmw_sb_recharge_time"},
           {@"sb_recharge_speed", Type::kChoice, @"Refill speed",
            @"How fast you must drive for the Speedbreaker to fill up. The game's is 100.",
            @"100",
            {{@"Any speed", @"0"}, {@"50", @"50"}, {@"75", @"75"}, {@"100 (game)", @"100"}}, kInGame, "nfsmw_sb_recharge_speed"},
           {@"sb_mass", Type::kChoice, @"Weight while slowed",
            @"How much heavier your car is during the Speedbreaker, for ramming. The game's "
            @"is 2x.",
            @"2",
            {{@"1x", @"1"}, {@"2x (game)", @"2"}, {@"3x", @"3"}, {@"5x", @"5"}}, kInGame, "nfsmw_sb_mass"},
       }, kTabExtras},
      {@"Police", nil,
       {
           {@"no_cops", Type::kSwitch, @"No cops",
            @"No police anywhere (from the Xbox 360 prototype's debug menu). Pursuit events and "
            @"Blacklist milestones that need cops cannot be finished.",
            @"false", {}, kInGame, "nfsmw_no_cops"},
           {@"show_non_pursuit_cops", Type::kSwitch, @"Show all cops on the minimap",
            @"Also shows cops that are not chasing you, as Extra Options' ShowNonPursuitCops.",
            @"false", {}, kInGame, "nfsmw_show_non_pursuit_cops"},
           {@"heat_override", Type::kSwitch, @"Heat level override",
            @"Every event normally limits how high (and how low) the heat can go, often well "
            @"below 5. On: Lowest heat and Highest heat below replace those limits everywhere, "
            @"as Extra Options' HeatLevelOverride. Needed to raise the heat above an event's own "
            @"limit, also with Change heat in the in-game menu.",
            @"false", {}, kInGame, "nfsmw_heat_override"},
           {@"heat_min", Type::kChoice, @"Lowest heat", @"With the override on: the heat never drops "
            @"below this. Above 5 is experimental.",
            @"1",
            {{@"1", @"1"}, {@"2", @"2"}, {@"3", @"3"}, {@"4", @"4"}, {@"5", @"5"},
             {@"6", @"6"}, {@"7", @"7"}, {@"8", @"8"}, {@"9", @"9"}, {@"10", @"10"}}, kInGame, "nfsmw_heat_min"},
           {@"heat_max", Type::kChoice, @"Highest heat",
            @"With the override on: the heat never goes above this. The game's is 5; 6 to 10 "
            @"are experimental (more cops on PC; untested on the Xbox 360 game).",
            @"5",
            {{@"1", @"1"}, {@"2", @"2"}, {@"3", @"3"}, {@"4", @"4"}, {@"5 (game)", @"5"},
             {@"6", @"6"}, {@"7", @"7"}, {@"8", @"8"}, {@"9", @"9"}, {@"10", @"10"}}, kInGame, "nfsmw_heat_max"},
           {@"speeding_limit", Type::kChoice, @"Speeding",
            @"The speed at which the police can give you a Speeding infraction. The game's is "
            @"241 km/h (150 mph).",
            @"67",
            {{@"180 km/h", @"50"}, {@"241 km/h (game)", @"67"}, {@"290 km/h", @"80.5"},
             {@"Never", @"1000"}}, kInGame, "nfsmw_speeding_limit"},
           {@"excessive_speeding_limit", Type::kChoice, @"Excessive speeding",
            @"The speed for an Excessive Speeding infraction. The game's is 290 km/h (180 mph).",
            @"80.5",
            {{@"241 km/h", @"67"}, {@"290 km/h (game)", @"80.5"}, {@"322 km/h", @"89.4"},
             {@"Never", @"1000"}}, kInGame, "nfsmw_excessive_speeding_limit"},
           {@"reckless_driving_limit", Type::kChoice, @"Reckless driving",
            @"The speed for a Reckless Driving infraction. The game's is 322 km/h (200 mph).",
            @"89.4",
            {{@"290 km/h", @"80.5"}, {@"322 km/h (game)", @"89.4"}, {@"360 km/h", @"100"},
             {@"Never", @"1000"}}, kInGame, "nfsmw_reckless_driving_limit"},
       }, kTabExtras},
      {@"Quick Race", nil,
       {
           {@"laps_max", Type::kChoice, @"Most laps",
            @"The most laps you can pick for a circuit, lap knockout or tollbooth race. The game's "
            @"is 8.",
            @"8",
            {{@"8 (game)", @"8"}, {@"10", @"10"}, {@"15", @"15"}, {@"20", @"20"}, {@"30", @"30"},
             {@"50", @"50"}, {@"99", @"99"}}, kInGame, "nfsmw_laps_max"},
           {@"opponents_max", Type::kChoice, @"Most opponents (experimental)",
            @"The most opponents you can pick. The game's is 3. On PC the 4th and later can get "
            @"odd cars; more cars on the road also cost speed and memory.",
            @"3",
            {{@"3 (game)", @"3"}, {@"4", @"4"}, {@"5", @"5"}, {@"6", @"6"}}, kInGame, "nfsmw_opponents_max"},
           {@"laps_min", Type::kChoice, @"Fewest laps",
            @"The fewest laps you can pick. The game's is 1.",
            @"1",
            {{@"1 (game)", @"1"}, {@"2", @"2"}, {@"3", @"3"}, {@"5", @"5"}}, kInGame, "nfsmw_laps_min"},
           {@"opponents_min", Type::kChoice, @"Fewest opponents",
            @"The fewest opponents you can pick. The game's is 1.",
            @"1",
            {{@"1 (game)", @"1"}, {@"2", @"2"}, {@"3", @"3"}}, kInGame, "nfsmw_opponents_min"},
           {@"random_laps_max", Type::kChoice, @"Random race: most laps",
            @"The most laps a random circuit race can get. The game's is 5.",
            @"5",
            {{@"5 (game)", @"5"}, {@"8", @"8"}, {@"10", @"10"}, {@"20", @"20"}}, kInGame, "nfsmw_random_laps_max"},
           {@"random_opponents_max", Type::kChoice, @"Random race: most opponents (experimental)",
            @"The most opponents a random race can get. The game's is 3; more as in Most opponents.",
            @"3",
            {{@"3 (game)", @"3"}, {@"4", @"4"}, {@"5", @"5"}, {@"6", @"6"}}, kInGame, "nfsmw_random_opponents_max"},
           {@"world_animation_speed", Type::kChoice, @"World animation speed",
            @"How fast the world's animations run, as Extra Options' WorldAnimationSpeed. The game's is 45.",
            @"45",
            {{@"Slow (20)", @"20"}, {@"45 (game)", @"45"}, {@"Fast (90)", @"90"}}, kInGame, "nfsmw_world_animation_speed"},
           {@"nos_trail_repeat", Type::kChoice, @"Nitrous trail length",
            @"How long the nitrous flame trail is, as Extra Options' NosTrailRepeatCount. The game's is 8.",
            @"8",
            {{@"4", @"4"}, {@"8 (game)", @"8"}, {@"16", @"16"}, {@"32", @"32"}}, kInGame, "nfsmw_nos_trail_repeat"},
           {@"game_speed", Type::kChoice, @"Game speed (experimental)",
            @"Makes the whole game run slower or faster, as Extra Options' GameSpeed. The game's is 1x.",
            @"1",
            {{@"0.5x", @"0.5"}, {@"0.75x", @"0.75"}, {@"1x (game)", @"1"}, {@"1.25x", @"1.25"},
             {@"1.5x", @"1.5"}, {@"2x", @"2"}}, kInGame, "nfsmw_game_speed"},
           {@"traffic_low", Type::kChoice, @"Traffic at Low", @"How much traffic the Low setting means.",
            @"10", Percent(@"10"), kInGame, "nfsmw_traffic_low"},
           {@"traffic_medium", Type::kChoice, @"Traffic at Medium",
            @"How much traffic the Medium setting means.", @"30", Percent(@"30"), kInGame, "nfsmw_traffic_medium"},
           {@"traffic_high", Type::kChoice, @"Traffic at High",
            @"How much traffic the High setting means. 100 is bumper to bumper.", @"50", Percent(@"50"), kInGame, "nfsmw_traffic_high"},
       }, kTabExtras},
      {@"Weather", nil,
       {
           {@"always_rain", Type::kSwitch, @"Always rain",
            @"Rain everywhere, all the time (the game rains only in a few places).",
            @"false", {}, kInGame, "nfsmw_always_rain"},
           {@"rain_amount", Type::kChoice, @"Rain amount", @"How much rain falls.", @"1",
            {{@"0.5x", @"0.5"}, {@"1x (game)", @"1"}, {@"1.5x", @"1.5"}, {@"2x", @"2"}, {@"3x", @"3"}}, kInGame, "nfsmw_rain_amount"},
           {@"rain_intensity", Type::kChoice, @"Rain intensity", @"How heavy the rain looks.", @"0.45",
            {{@"Light", @"0.25"}, {@"Game", @"0.45"}, {@"Heavy", @"0.7"}, {@"Storm", @"1"}}, kInGame, "nfsmw_rain_intensity"},
           {@"rain_drop_size", Type::kChoice, @"Drop size", @"The size of the falling drops.", @"0.01",
            {{@"Small", @"0.005"}, {@"Game", @"0.01"}, {@"Large", @"0.02"}}, kInGame, "nfsmw_rain_drop_size"},
           {@"rain_crossing", Type::kChoice, @"Rain drift", @"How much the rain drifts sideways.", @"0.02",
            {{@"None", @"0"}, {@"Game", @"0.02"}, {@"Windy", @"0.05"}, {@"Gale", @"0.1"}}, kInGame, "nfsmw_rain_crossing"},
           {@"rain_fall_speed", Type::kChoice, @"Rain fall speed", @"How fast the drops fall.", @"0.03",
            {{@"Slow", @"0.015"}, {@"Game", @"0.03"}, {@"Fast", @"0.06"}}, kInGame, "nfsmw_rain_fall_speed"},
           {@"rain_gravity", Type::kChoice, @"Rain gravity", @"How strongly the drops are pulled down.", @"0.35",
            {{@"Light", @"0.2"}, {@"Game", @"0.35"}, {@"Heavy", @"0.6"}}, kInGame, "nfsmw_rain_gravity"},
           {@"road_reflection", Type::kChoice, @"Wet road reflection",
            @"How much the road reflects in the rain.", @"1",
            {{@"Off", @"0"}, {@"0.5x", @"0.5"}, {@"1x (game)", @"1"}, {@"1.5x", @"1.5"}, {@"2x", @"2"}}, kInGame, "nfsmw_road_reflection"},
       }, kTabExtras},
      {@"Renderer", nil,
       {
           {@"async_pipelines", Type::kSwitch, @"Compile pipelines in the background",
            @"Native renderer: the first time a new kind of draw appears, it is compiled in the "
            @"background and that object is missing for a few frames, instead of a hitch of up to "
            @"~70 ms. Pipelines from earlier sessions are compiled at startup either way.",
            @"true", {}, kNativeOnly},
       }, kTabGraphics},
      {@"Display", nil,
       {
           {@"aspect", Type::kChoice, @"Screen shape",
            @"The shape of the game's picture. Fit this screen: this device's own shape, edge to "
            @"edge (on a screen narrower than 16:9, such as an iPad, the game's 4:3 mode, the "
            @"closest it has). 16:9 is the Xbox 360's own; on other screens it has black bars.",
            @"auto",
            {{@"Fit this screen", @"auto"}, {@"16:9 (Xbox 360)", @"16:9"}}},
           {@"scale", Type::kChoice, @"Render resolution",
            ScaleSummary(),
            @"1",
            {{@"0.85x · 612p", @"0.85"}, {@"1x · 720p (Xbox 360)", @"1"}, {@"1.25x · 900p", @"1.25"}, {@"1.5x · 1080p", @"1.5"},
             {@"1.75x · 1260p", @"1.75"}, {@"2x · 1440p", @"2"},
             {NativeScaleTitle(), @"native"}}, kInGame | kInGameNative, "nfsmw_native_resolution_scale"},
           {@"fps_cap", Type::kChoice, @"Frame rate cap",
            @"30 saves battery and heat. Higher caps make motion smoother when the game "
            @"can keep up. 40 and 120 are available on 120 Hz displays.",
            @"60", FrameRateChoices(), kInGame},
           {@"show_fps", Type::kSwitch, @"Show FPS",
            @"Corner counter: frames per second and milliseconds per frame.", @"false"},
       }, kTabDisplay},
      {@"Battery", nil, {
           {@"preset", Type::kLink, @"Look and performance", @"Choose a starting point for graphics and battery life.", @""},
           {@"auto_cap", Type::kSwitch, @"30 fps when warm or on Low Power",
            @"At the 40 and 60 caps: 30 fps while Low Power Mode is on or the phone is warm, back "
            @"once it is off and cool again.",
            @"false", {}, kInGame, "nfsmw_battery_auto_cap"},
           {@"menu_cap", Type::kSwitch, @"30 fps in menus and pause",
            @"At the 40 and 60 caps: 30 fps in menus, pause screens and loading, which redraw much "
            @"the same picture; back as soon as driving starts.",
            @"false", {}, kInGame, "nfsmw_menu_cap"},
           {@"heat_scale", Type::kSwitch, @"0.75x when hot",
            @"Native renderer: the render resolution drops to 0.75x while the phone is hot (iOS "
            @"thermal state \"serious\") and goes back to the one chosen once it has cooled down.",
            @"false", {}, kInGame | kInGameNative | kNativeOnly, "nfsmw_heat_scale"},
           {@"performance_mode", Type::kChoice, @"Performance",
            @"Which CPU cores the game's threads ask for. Eco: the efficient ones always (the "
            @"default with Battery mode on), for battery life over smoothness. Balanced: the "
            @"efficient ones in menus and loading, the fast ones while driving (iPads with 6 or "
            @"more efficient cores keep their original, tested setting). Max: always the "
            @"fast ones, for the steadiest frame rate. Sound and the screen's timing keep their "
            @"own priority in every mode. iOS takes this as a hint, not a fixed choice of cores.",
            @"balanced",
            {{@"Eco", @"eco"}, {@"Balanced", @"balanced"}, {@"Max", @"max"}}, kInGame},
       }, kTabBattery},
      {@"HUD", @"Also in the options while playing (the gear in pause screens, or L3+R3), where "
               @"they apply at once: the HUD shows them as soon as driving starts again.",
       {
           {@"hud_custom", Type::kSwitch, @"Custom HUD",
            @"Off: the game's own HUD size and layout. On: the layout from Customize HUD applies.",
            @"false", {}, kInGame, "nfsmw_hud_scale,nfsmw_hud_safe_zone,nfsmw_hud_left_x,nfsmw_hud_left_y,nfsmw_hud_right_x,nfsmw_hud_right_y,nfsmw_hud_race_x,nfsmw_hud_race_y,nfsmw_hud_layout"},
           {@"hud_editor", Type::kLink, @"Customize HUD",
            @"Move each part of the HUD by hand, change its size, and set the HUD's overall size and "
            @"safe zone. Race / free roam and pursuit each have a tab.",
            @"", {}, kInGame},
       }, kTabControls},
      {@"Graphics", nil,
       {
           {@"antialiasing", Type::kChoice, @"Anti-aliasing",
            @"Smooths jagged edges. MSAA is the finest and the most expensive (with the native "
            @"renderer at every screen shape; without it, the game's own, not at 19.5:9). FXAA is "
            @"a filter over the final image: much cheaper, but a little softer.",
            @"off",
            {{@"Off", @"off"},
             {@"MSAA 2x", @"msaa2"},
             {@"MSAA 4x", @"msaa4"},
             {@"FXAA", @"fxaa"},
             {@"FXAA high", @"fxaa_high"}}, kInGame, "nfsmw_native_fxaa"},
           {@"anisotropic", Type::kChoice, @"Anisotropic filtering",
            @"Sharper textures seen at an angle, like the road in the distance.", @"3",
            {{@"Off", @"0"}, {@"2x", @"2"}, {@"4x", @"3"}, {@"16x", @"5"}}},
           {@"shadow_size", Type::kChoice, @"Shadow quality",
            @"Size of the shadow map, drawn and copied every frame. Lower: more fps where the GPU "
            @"is the limit, softer shadow edges. The Xbox 360's is High.",
            @"1600",
            {{@"High (1600, Xbox 360)", @"1600"}, {@"Medium (1280)", @"1280"},
             {@"Low (1024)", @"1024"}, {@"Very low (768)", @"768"}}},
           {@"shadow_scale", Type::kChoice, @"Shadow map drawing size",
            @"Native renderer: the shadow map drawn at the size above or at half of it. Half: "
            @"less GPU work, softer and blockier shadows.",
            @"1",
            {{@"Full", @"1"}, {@"Half", @"0.5"}}, kInGame | kInGameNative | kNativeOnly, "nfsmw_native_shadow_scale"},
           {@"reflection_rate", Type::kChoice, @"Car reflections",
            @"Choose how often each car reflection face updates. Half rate gives 15 updates per second "
            @"at 30 fps or 20 at 40 fps.",
            @"full",
            {{@"Every frame", @"full"}, {@"Half each frame", @"half"}}, kInGame | kInGameNative | kNativeOnly, "nfsmw_native_half_rate_reflections"},
           {@"reflection_size", Type::kChoice, @"Reflection and mirror resolution",
            @"Native renderer: the environment reflected on the cars and shown in the rear-view "
            @"mirror, drawn at the Xbox 360's size or scaled with the render resolution. 1x: "
            @"~1 ms less GPU work a frame above 1x, a softer mirror.",
            @"1x",
            {{@"1x (Xbox 360)", @"1x"}, {@"Render resolution", @"scaled"}}, kInGame | kInGameNative | kNativeOnly, "nfsmw_native_scale_reflections"},
           {@"postprocessing", Type::kSwitch, @"Post-processing",
            @"The original game's color filter and blur. Off: less GPU work, but it no longer "
            @"looks like the original.",
            @"true", {}, kInGame, "nfsmw_sin_posprocesado"},
           {@"motion_blur", Type::kSwitch, @"Motion blur",
            @"The original game's blur at speed. Off: the picture stays sharp when driving fast.",
            @"true", {}, kInGame, "nfsmw_motion_blur"},
       }, kTabGraphics},
      {@"Touch controls", nil,
       {
           {@"touch_controls", Type::kSwitch, @"Touch controls",
            @"On-screen gamepad. It hides itself while a physical controller is connected; "
            @"a tap brings it back.",
            @"true"},
           {@"touch_layout", Type::kLink, @"Customize touch controls",
            @"Move and resize the on-screen buttons and sticks (both the Pad and the Drive "
            @"layouts), and set their size and opacity.",
            @"", {}, kInGame},
           {@"touch_steering", Type::kChoice, @"Steering",
            @"Drive layout. Dynamic: a joystick comes up wherever your thumb lands in the bottom-left "
            @"quarter of the screen and fades out when you lift it. Fixed: the steering circle stays "
            @"in its place. Buttons: one button for left, one for right.",
            @"dynamic",
            {{@"Dynamic joystick", @"dynamic"}, {@"Fixed joystick", @"fixed"}, {@"Two buttons", @"buttons"}}, kInGame, "ios_touch_steering"},
           {@"touch_idle_opacity", Type::kChoice, @"Dim when not touched",
            @"Drive layout: after 3 seconds without a touch the controls fade to this share of their "
            @"opacity, so they hide less of the road. Any touch brings them back.",
            @"0.35",
            {{@"Off", @"1"}, {@"Half", @"0.5"}, {@"Low", @"0.35"}, {@"Very low", @"0.2"}}, kInGame, "ios_touch_idle_opacity"},
           {@"touch_menu_gestures", Type::kSwitch, @"Swipe and tap in menus",
            @"With layouts switching by themselves: no buttons in menus and pause screens. Swipe to "
            @"move (the left stick that way), tap to accept (A), tap with two fingers to go back (B). "
            @"The PAD button brings the full gamepad back for that menu.",
            @"true"},
           {@"touch_menu_empty_accept", Type::kSwitch, @"Tap and swipe anywhere",
            @"Tap empty space to accept (A) and swipe anywhere to navigate. Turn off to tap "
            @"visible controls and start swipes only inside recognised scrollable areas.", @"false", {}, kInGame, "ios_touch_menu_empty_accept"},
           {@"touch_menu_two_finger_back", Type::kSwitch, @"Two-finger tap to go back",
            @"Tap with two fingers in menus to press Back (B). Independent of tap and swipe anywhere.", @"true", {}, kInGame, "ios_touch_menu_two_finger_back"},
           {@"touch_menu_invert", Type::kSwitch, @"Invert menu swipes",
            @"Reverse the direction used to navigate menus. "
            @"World-map cursor dragging is unchanged.", @"true", {}, kInGame, "ios_touch_menu_invert"},
           {@"touch_look", Type::kSwitch, @"Swipe to look around",
            @"Drive layout: swipe on the screen where there is no control to turn the chase camera "
            @"around the car (free look). It swings back behind the car when you let go.",
            @"true", {}, kInGame, "ios_touch_look"},
           {@"touch_look_speed", Type::kChoice, @"Swipe look speed", @"How far a swipe turns the camera.",
            @"1",
            {{@"Slow", @"0.5"}, {@"Normal", @"1"}, {@"Fast", @"1.5"}, {@"Very fast", @"2.5"}}, kInGame, "ios_touch_look_speed"},
           {@"touch_auto_layout", Type::kSwitch, @"Switch layouts by themselves",
            @"The Drive layout while driving, the Pad layout in menus and pause screens. The "
            @"DRIVE/PAD button still switches by hand.",
            @"true"},
       }, kTabControls},
      {@"Keyboard", nil,
       {
           {@"keyboard", Type::kSwitch, @"Keyboard controls",
            @"Play with a hardware keyboard (Magic Keyboard, Bluetooth or USB): its keys act as "
            @"the controller, together with the touch controls and any gamepad.",
            @"true"},
           {@"mouse_look", Type::kSwitch, @"Mouse look",
            @"With keyboard controls: the mouse or trackpad turns the chase camera around the car "
            @"while driving (the pointer is locked then, free in menus). It swings back behind the "
            @"car when you stop.",
            @"true"},
           {@"mouse_look_speed", Type::kChoice, @"Mouse look speed", @"How far the camera turns per mouse movement.",
            @"1",
            {{@"Slow", @"0.5"}, {@"Normal", @"1"}, {@"Fast", @"1.5"}, {@"Very fast", @"2.5"}}, kInGame, "nfsmw_mouse_look_speed"},
           {@"mouse_look_invert", Type::kSwitch, @"Invert mouse look",
            @"On (default, Stefan: more natural for free look): moving the mouse up looks down at "
            @"the car.",
            @"true", {}, kInGame, "nfsmw_mouse_look_invert"},
           {@"keyboard_bindings", Type::kLink, @"Customize keyboard controls",
            @"Which key does what. PC-style by default: arrows or WASD to drive, Space handbrake, "
            @"Alt nitrous, Shift and Ctrl to change gear, Return to accept, Backspace to go back, "
            @"Esc to pause.",
            @"", {}, kInGame},
       }, kTabControls},
      {@"Audio", nil,
       {
           {@"audio_silent_mode", Type::kSwitch, @"Play sound in silent mode",
            @"Off: the game is quiet when the phone's silent switch is on, like most iOS games. "
            @"On: the game's sound plays anyway.",
            @"false"},
           {@"audio_mix_others", Type::kSwitch, @"Keep other music playing",
            @"Let music from another app continue alongside the game. You can lower the game's "
            @"music volume separately in its audio settings. Applies when launching the game.", @"false"},
           {@"audio_starve_reset", Type::kSwitch, @"Audio stream reset",
            @"When a sound stream runs out of data, drop what it had decoded but not yet played "
            @"(Xenia Canary's fix for stale sounds in NFS). Leave it on: off, music cuts out. "
            @"Only for testing.",
            @"true"},
       }, kTabAudio},
      {@"Performance", @"To test what each thing costs on your device. The defaults are the recommended ones.",
       {
           {@"iso_stream", Type::kSwitch, @"Read the ISO in pieces",
            @"Reads the disc image as the game needs it instead of mapping all 7.8 GB into "
            @"memory. Used automatically when mapping fails (devices with less address space); "
            @"on, it is used always, for testing.",
            @"false"},
       }, kTabAdvanced},
      {@"Diagnostics", nil,
       {
           {@"logging", Type::kSwitch, @"Logging",
            @"Writes Documents/logs/nfsmw.log and boot.txt. Off when just playing; on (and "
            @"send the log) when testing something.",
            @"true"},
           {@"detailed_log", Type::kSwitch, @"Detailed log",
            @"log_level=debug. It tanks the fps: only for diagnosing problems.", @"false"},
           {@"gpu_capture", Type::kSwitch, @"GPU frame capture (experimental)",
            @"Adds a red CAPTURE button. Saves a native frame to Documents/captures for Xcode. "
            @"Capture support slows rendering and may cause graphics problems; turn off and restart "
            @"the app after testing.", @"false"},
           {@"cost_probe", Type::kSwitch, @"GPU cost per shader",
            @"Native renderer: once a second, one of the most used pixel shaders is left out of a "
            @"frame (it may flicker) and the log says how much GPU time that saved.",
            @"false", {}, kNativeOnly},
           {@"motion_debug", Type::kSwitch, @"Show motion vectors",
            @"Native renderer: the scene's motion instead of the picture. Grey: still; red: "
            @"moving right; green: moving down; darker: the other way.",
            @"false", {}, kNativeOnly},
           {@"heat_scale_test", Type::kSwitch, @"Test 0.75x when hot",
            @"Native renderer, with \"0.75x when hot\" on (or Battery mode): acts as if the phone "
            @"were hot for 30 s of every minute, to see the resolution switch. The log says when.",
            @"false", {}, kNativeOnly},
           {@"extra_args", Type::kText, @"Extra arguments",
            @"Options for testing, passed to the game at launch, separated by spaces, e.g. "
            @"--nfsmw_hud_watch=true. They win over these settings and Documents/extra_args.txt.",
            @""},
       }, kTabAdvanced},
  };
  return sections;
}

const Option* FindOption(NSString* key) {
  for (const Section& s : Sections()) {
    for (const Option& o : s.options) {
      if ([o.key isEqualToString:key]) {
        return &o;
      }
    }
  }
  return nullptr;
}

bool GamertagValid(NSString* g) {
  static const std::regex re("[A-Za-z][A-Za-z0-9 ]{0,14}");
  return g.length == 0 || std::regex_match(std::string(g.UTF8String), re);
}

// ---------------------------------------------------------------------------
//  Documents/settings.json
// ---------------------------------------------------------------------------
NSString* SettingsPath(const fs::path& docs) {
  return [NSString stringWithUTF8String:(docs / "settings.json").c_str()];
}

NSMutableDictionary<NSString*, NSString*>* LoadSettings(const fs::path& docs) {
  NSMutableDictionary<NSString*, NSString*>* s = [NSMutableDictionary dictionary];
  NSData* data = [NSData dataWithContentsOfFile:SettingsPath(docs)];
  id json = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil] : nil;
  if ([json isKindOfClass:NSDictionary.class]) {
    for (id key in json) {
      id value = json[key];
      if ([key isKindOfClass:NSString.class]) {
        // Accept true/false and numbers too, for hand-edited files.
        if ([value isKindOfClass:NSString.class]) {
          s[key] = value;
        } else if (value == (id)kCFBooleanTrue || value == (id)kCFBooleanFalse) {
          s[key] = [value boolValue] ? @"true" : @"false";
        } else if ([value isKindOfClass:NSNumber.class]) {
          s[key] = [value stringValue];
        }
      }
    }
  }
  // Retire temporary stress selections saved by the 0.5.1 test builds.
  if (s[@"scale"] && ![s[@"scale"] isEqualToString:@"native"] &&
      [s[@"scale"] doubleValue] > 2.0) s[@"scale"] = @"1";
  if ([s[@"battery_mode"] isEqualToString:@"true"]) {
    // Read all legacy effective values before removing the override.
    NSMutableDictionary* effective = [NSMutableDictionary dictionary];
    for (const auto& section : Sections()) {
      for (const auto& option : section.options) {
        if (NSString* value = BatteryValue(option.key)) effective[option.key] = value;
      }
    }
    effective[@"fps_cap"] = [s[@"fps_cap"] isEqualToString:@"40"] && SupportsHighFrameRates() ? @"40" : @"30";
    effective[@"performance_mode"] = s[@"performance_mode"] ?: @"eco";
    [s addEntriesFromDictionary:effective];
  }
  [s removeObjectForKey:@"battery_mode"];
  return s;
}

void SaveSettings(const fs::path& docs, NSDictionary<NSString*, NSString*>* s) {
  NSData* data = [NSJSONSerialization
      dataWithJSONObject:s
                 options:NSJSONWritingPrettyPrinted | NSJSONWritingSortedKeys
                   error:nil];
  [data writeToFile:SettingsPath(docs) atomically:YES];
}


// Longest battery starts with the former Battery mode overrides.
NSString* BatteryValue(NSString* key) {
  static NSDictionary<NSString*, NSString*>* values = @{
    @"scale" : @"0.85",
    @"antialiasing" : @"fxaa",
    @"anisotropic" : @"3",
    @"shadow_size" : @"1600",
    @"postprocessing" : @"true",
    @"motion_blur" : @"true",
    @"shadow_scale" : @"0.5",
    @"reflection_rate" : @"half",
    @"reflection_size" : @"1x",
    @"auto_cap" : @"true",
    @"menu_cap" : @"true",
    @"heat_scale" : @"true",
  };
  return values[key];
}

// The HUD settings that Custom HUD switches on (0.4.2, Stefan: a master
// switch, so a player who never touches them gets the game's own HUD), with
// the game's values used while it is off.
NSArray<NSString*>* PresetNames() {
  return @[@"Longest battery", @"Balanced", @"Best looking"];
}

static NSDictionary<NSString*, NSString*>* QualityOverrides() {
  return @{@"scale": @"native", @"antialiasing": @"msaa4", @"anisotropic": @"5",
           @"reflection_size": @"scaled", @"performance_mode": @"max",
           @"fps_cap": UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad &&
                        SupportsHighFrameRates() ? @"120" : @"60"};
}

static bool PresetOption(NSString* key) {
  return BatteryValue(key) || [key isEqualToString:@"fps_cap"] ||
         [key isEqualToString:@"performance_mode"];
}

static NSString* PresetValue(const Option& option, NSInteger preset, NSString* fps, NSString* reflection) {
  if (preset == 0) {
    if ([option.key isEqualToString:@"fps_cap"]) return fps;
    if ([option.key isEqualToString:@"performance_mode"]) return @"eco";
    if ([option.key isEqualToString:@"reflection_rate"]) return reflection;
    return BatteryValue(option.key);
  }
  if (preset == 2) {
    NSString* value = QualityOverrides()[option.key];
    if (value) return value;
  }
  return option.default_value;
}

void ApplyPreset(NSMutableDictionary<NSString*, NSString*>* settings, NSInteger preset,
                 NSString* fps, NSString* reflection) {
  if (preset < 0 || preset >= NSInteger(PresetNames().count)) return;
  fps = SupportsHighFrameRates() && [fps isEqualToString:@"40"] ? @"40" : @"30";
  reflection = [reflection isEqualToString:@"full"] ? @"full" : @"half";
  for (const auto& section : Sections()) {
    for (const auto& option : section.options) {
      if (PresetOption(option.key)) settings[option.key] = PresetValue(option, preset, fps, reflection);
    }
  }
}

NSString* PresetName(NSDictionary<NSString*, NSString*>* settings) {
  NSString* fps = Value(settings, @"fps_cap");
  NSString* reflection = Value(settings, @"reflection_rate");
  for (NSInteger preset = 0; preset < NSInteger(PresetNames().count); ++preset) {
    if (preset == 0 && !([fps isEqualToString:@"30"] ||
                        (SupportsHighFrameRates() && [fps isEqualToString:@"40"]))) continue;
    bool matches = true;
    for (const auto& section : Sections()) {
      for (const auto& option : section.options) {
        if (PresetOption(option.key) &&
            ![Value(settings, option.key) isEqualToString:PresetValue(option, preset, fps, reflection)]) {
          matches = false;
        }
      }
    }
    if (matches) return PresetNames()[preset];
  }
  return @"Custom";
}

void ApplyInputSetup(NSMutableDictionary<NSString*, NSString*>* settings, NSInteger input,
                     NSString* steering) {
  if (input < 0) return;
  settings[@"touch_controls"] = input == 2 ? @"false" : @"true";
  settings[@"keyboard"] = input == 2 ? @"true" : @"false";
  settings[@"mouse_look"] = input == 2 ? @"true" : @"false";
  if (input == 0 && steering) settings[@"touch_steering"] = steering;
}

NSString* HudDefault(NSString* key) {
  static NSDictionary<NSString*, NSString*>* values = @{
    @"hud_scale" : @"1.00",
    @"hud_safe_zone" : @"1.00",
    @"hud_left_x" : @"0",
    @"hud_left_y" : @"0",
    @"hud_right_x" : @"0",
    @"hud_right_y" : @"0",
    @"hud_race_x" : @"0",
    @"hud_race_y" : @"0",
    @"hud_layout" : @"",
  };
  return values[key];
}

// The old (emulated, Vulkan) renderer's settings, removed from the menus on
// November 6 (Stefan): the native Metal renderer always draws, and these keep
// the values they had by default, whatever an older settings.json says.
// Extra arguments can still change the cvars for tests.
NSString* RetiredValue(NSString* key) {
  static NSDictionary<NSString*, NSString*>* values = @{
    @"native_renderer" : @"true", @"no_vulkan" : @"true", @"scaling" : @"bilinear",
    @"async_submits" : @"true",   @"one_pass" : @"true",  @"edram_fsi" : @"false",
    @"widen_kb" : @"256",         @"occlusion" : @"true", @"exposure" : @"true",
    @"memexport" : @"true",       @"pages" : @"true",     @"mvk_profiling" : @"false",
  };
  return values[key];
}

NSString* Value(NSDictionary<NSString*, NSString*>* s, NSString* key) {
  if (NSString* retired = RetiredValue(key)) return retired;
  if (NSString* game = HudDefault(key); game && ![s[@"hud_custom"] isEqualToString:@"true"]) {
    return game;
  }
  NSString* v = s[key];
  if ([key isEqualToString:@"fps_cap"] && !SupportsHighFrameRates() &&
      ([v isEqualToString:@"40"] || [v isEqualToString:@"120"])) v = @"60";
  if (!v.length && HudDefault(key)) return HudDefault(key);  // no row of its own (the HUD editor's)
  if (v && [key isEqualToString:@"aspect"]) {  // older settings files: the video modes themselves
    // 0.6.0: only Fit this screen and 16:9; the 4:3 and 19.5:9 choices are Fit.
    if (![v isEqualToString:@"16:9"]) return @"auto";
  }
  if (v) {
    return v;
  }
  // The render resolution's default: 1x (the Xbox 360's 720p) with either
  // renderer: on a phone screen it is hard to tell from 1.5x, at about half
  // the GPU work.
  if ([key isEqualToString:@"lan_mode"]) return @"off";
  const Option* o = FindOption(key);
  return o ? o->default_value : @"";
}

bool On(NSDictionary<NSString*, NSString*>* s, NSString* key) {
  return [Value(s, key) isEqualToString:@"true"];
}

// The shape in use: "16:9", "4:3" or "wide" ("auto" resolved for this screen).
NSString* ResolvedAspect(NSDictionary<NSString*, NSString*>* s) {
  NSString* aspect = Value(s, @"aspect");
  return [aspect isEqualToString:@"auto"] ? AutoAspect() : aspect;
}


bool Msaa(NSDictionary<NSString*, NSString*>* s) {
  return [Value(s, @"antialiasing") hasPrefix:@"msaa"];
}

// The same translation as Ajustes.argumentos() on Android.
std::vector<std::string> Arguments(NSDictionary<NSString*, NSString*>* s) {
  auto b = [](bool v) { return std::string(v ? "true" : "false"); };
  auto str = [&](NSString* key) { return std::string(Value(s, key).UTF8String); };
  std::vector<std::string> a;
  // Black Edition content is always on: there is no switch for it any more.
  a.push_back("--black_edition=true");
  a.push_back("--nfsmw_marker_count=" + str(@"marker_count"));
  a.push_back("--nfsmw_purchased_car_limit=" + str(@"car_limit"));
  a.push_back("--nfsmw_remove_old_bridge_barrier=" + b(On(s, @"old_bridge")));
  a.push_back("--nfsmw_laps_max=" + str(@"laps_max"));
  a.push_back("--nfsmw_opponents_max=" + str(@"opponents_max"));
  a.push_back("--nfsmw_laps_min=" + str(@"laps_min"));
  a.push_back("--nfsmw_opponents_min=" + str(@"opponents_min"));
  a.push_back("--nfsmw_random_laps_max=" + str(@"random_laps_max"));
  a.push_back("--nfsmw_random_opponents_max=" + str(@"random_opponents_max"));
  a.push_back("--nfsmw_game_speed=" + str(@"game_speed"));
  a.push_back("--nfsmw_world_animation_speed=" + str(@"world_animation_speed"));
  a.push_back("--nfsmw_nos_trail_repeat=" + str(@"nos_trail_repeat"));
  a.push_back("--nfsmw_unlock_all_things=" + b(On(s, @"unlock_all_things")));
  a.push_back("--nfsmw_no_rev_limiter=" + b(On(s, @"no_rev_limiter")));
  a.push_back("--nfsmw_showcase_unlimited=" + b(On(s, @"showcase_unlimited")));
  a.push_back("--nfsmw_skip_career_intro=" + b(On(s, @"skip_career_intro")));
  a.push_back("--nfsmw_traffic_low=" + str(@"traffic_low"));
  a.push_back("--nfsmw_traffic_medium=" + str(@"traffic_medium"));
  a.push_back("--nfsmw_traffic_high=" + str(@"traffic_high"));
  a.push_back("--nfsmw_always_rain=" + b(On(s, @"always_rain")));
  a.push_back("--nfsmw_rain_amount=" + str(@"rain_amount"));
  a.push_back("--nfsmw_rain_intensity=" + str(@"rain_intensity"));
  a.push_back("--nfsmw_rain_drop_size=" + str(@"rain_drop_size"));
  a.push_back("--nfsmw_rain_crossing=" + str(@"rain_crossing"));
  a.push_back("--nfsmw_rain_fall_speed=" + str(@"rain_fall_speed"));
  a.push_back("--nfsmw_rain_gravity=" + str(@"rain_gravity"));
  a.push_back("--nfsmw_road_reflection=" + str(@"road_reflection"));
  a.push_back("--nfsmw_impound_strikes=" + str(@"impound_strikes"));
  a.push_back("--nfsmw_impound_strikes_max=" + str(@"impound_strikes_max"));
  a.push_back("--nfsmw_sb_recharge_time=" + str(@"sb_recharge_time"));
  a.push_back("--nfsmw_sb_recharge_speed=" + str(@"sb_recharge_speed"));
  a.push_back("--nfsmw_sb_mass=" + str(@"sb_mass"));
  a.push_back("--nfsmw_heat_override=" + b(On(s, @"heat_override")));
  a.push_back("--nfsmw_no_cops=" + b(On(s, @"no_cops")));
  a.push_back("--nfsmw_show_non_pursuit_cops=" + b(On(s, @"show_non_pursuit_cops")));
  a.push_back("--nfsmw_infinite_nos=" + b(On(s, @"infinite_nos")));
  a.push_back("--nfsmw_infinite_speedbreaker=" + b(On(s, @"infinite_speedbreaker")));
  a.push_back("--nfsmw_heat_min=" + str(@"heat_min"));
  a.push_back("--nfsmw_heat_max=" + str(@"heat_max"));
  a.push_back("--nfsmw_speeding_limit=" + str(@"speeding_limit"));
  a.push_back("--nfsmw_excessive_speeding_limit=" + str(@"excessive_speeding_limit"));
  a.push_back("--nfsmw_reckless_driving_limit=" + str(@"reckless_driving_limit"));
  // 120 Hz simulation at every cap (0.4.3; its Advanced switch removed). At
  // 40 a 25 ms frame is 1.5 of the game's 1/60 s world steps (frames
  // alternated 1 and 2 steps, camera log, Oct 28). At 60 the first ~15 s of
  // a pursuit moved the world on 2 of 3 frames, which 120 Hz removes (iPad
  // camera logs, Oct 29). --nfsmw_sim_rate=60 in Extra Args for tests.
  a.push_back("--nfsmw_sim_rate=120");
  // The render scale: the native renderer's own (fractions, or the screen's
  // "native"); the emulated renderer only has whole steps (1x or 2x).
  NSString* scale = Value(s, @"scale");
  const double scale_value = [scale isEqualToString:@"native"] ? ScreenPixels().height / 720.0 : scale.doubleValue;
  // Whole steps for the emulated renderer: 1.5x and below are 1x.
  const int whole_scale = std::clamp(int(scale_value + 0.25), 1, 2);
  // The final image: every screen pixel once the game is drawn above 1x; else
  // the old automatic choice (points on large screens). Not shown any more;
  // ios_retina still works from extra_args.txt.
  a.push_back(std::string("--ios_retina=") + (scale_value > 1.0 ? "true" : "auto"));
  a.push_back("--ios_fps_cap=" + str(@"fps_cap"));
  a.push_back("--nfsmw_battery_auto_cap=" + b(On(s, @"auto_cap")));
  a.push_back("--nfsmw_menu_cap=" + b(On(s, @"menu_cap")));
  NSString* const aspect = ResolvedAspect(s);
  // 4:3: the game's HD 4:3 mode, its scene drawn at 960x720 (not 640x480).
  if ([aspect isEqualToString:@"4:3"]) {
    a.push_back("--resolution=1024x768");
    a.push_back("--nfsmw_sd_scene_720=true");
  }
  // Wider than 16:9: the scene is one wide strip, which needs the single pass.
  const bool wide = [aspect isEqualToString:@"wide"];
  if (wide) {
    const int width = FitSceneWidth();
    a.push_back("--resolution=" + std::to_string(width) + "x720");
    a.push_back("--nfsmw_wide_scene_width=" + std::to_string(width));
  }
  a.push_back("--ios_show_fps=" + b(On(s, @"show_fps")));
  a.push_back("--nfsmw_performance_mode=" + str(@"performance_mode"));
  a.push_back(std::string("--nfsmw_performance_source=") +
              (s[@"performance_mode"].length ? "setting"
                                                              : "default"));
  a.push_back("--nfsmw_hud_scale=" + str(@"hud_scale"));
  a.push_back("--nfsmw_hud_safe_zone=" + str(@"hud_safe_zone"));
  // The HUD editor's layout (it replaced the per-side offsets of 0.4.2).
  // Never empty: "--nfsmw_hud_layout=" took the next argument as its value
  // (IPA158 log, Custom HUD off: "[hud] layout: --ios_gpu_capture=false").
  a.push_back("--nfsmw_hud_layout=" + (str(@"hud_layout").empty() ? std::string("none") : str(@"hud_layout")));
  a.push_back("--ios_gpu_capture=" + b(On(s, @"gpu_capture")));
  a.push_back("--ios_touch_controls=" + b(On(s, @"touch_controls")));
  a.push_back("--ios_touch_auto_layout=" + b(On(s, @"touch_auto_layout")));
  a.push_back("--ios_touch_steering=" + str(@"touch_steering"));
  a.push_back("--ios_touch_menu_gestures=" + b(On(s, @"touch_menu_gestures")));
  a.push_back("--ios_touch_menu_empty_accept=" + b(On(s, @"touch_menu_empty_accept")));
  a.push_back("--ios_touch_menu_two_finger_back=" + b(On(s, @"touch_menu_two_finger_back")));
  a.push_back("--ios_touch_menu_invert=" + b(On(s, @"touch_menu_invert")));
  a.push_back("--ios_touch_idle_opacity=" + str(@"touch_idle_opacity"));
  a.push_back("--ios_touch_look=" + b(On(s, @"touch_look")));
  a.push_back("--ios_touch_look_speed=" + str(@"touch_look_speed"));
  a.push_back("--mnk_mode=" + b(On(s, @"keyboard")));
  // Mouse look (camera_look.cpp): the SDK's mouse mode only locks the pointer;
  // its right-stick part is off (patch_ios_mouse_axes.py).
  a.push_back("--mnk_mouse=" + b(On(s, @"keyboard") && On(s, @"mouse_look")));
  a.push_back("--mnk_mouse_x=false");
  a.push_back("--mnk_mouse_y=false");
  a.push_back("--nfsmw_mouse_look=" + b(On(s, @"mouse_look")));
  a.push_back("--nfsmw_mouse_look_speed=" + str(@"mouse_look_speed"));
  a.push_back("--nfsmw_mouse_look_invert=" + b(On(s, @"mouse_look_invert")));
  for (const KeyBind& kb : KeyBinds()) {
    a.push_back(std::string("--") + kb.setting.UTF8String + "=" + KeyBindValue(s, kb).UTF8String);
  }
  NSString* aa = Value(s, @"antialiasing");
  const bool msaa = Msaa(s);
  a.push_back("--gpu_sin_msaa=" + b(!msaa));
  a.push_back(std::string("--gpu_msaa_muestras=") + ([aa isEqualToString:@"msaa2"] ? "2" : "4"));
  a.push_back(std::string("--swap_post_effect=") +
              ([aa isEqualToString:@"fxaa"]        ? "fxaa"
               : [aa isEqualToString:@"fxaa_high"] ? "fxaa_extreme"
                                                   : "none"));
  a.push_back("--present_effect=" + str(@"scaling"));
  a.push_back("--nfsmw_sin_posprocesado=" + b(!On(s, @"postprocessing")));
  a.push_back("--nfsmw_motion_blur=" + b(On(s, @"motion_blur")));
  a.push_back("--anisotropic_override=" + str(@"anisotropic"));
  // With the native renderer the scale is its own: the emulated renderer only
  // draws what the native one does not (videos) and stays at 1x. Scaled, it
  // allocates its scaled resolve buffer whole (512 MB x scale^2: MoltenVK has
  // no sparse buffers), 2 GB at 2x that nothing used.
  if (On(s, @"native_renderer")) {
    a.push_back("--resolution_scale=1");
    a.push_back("--nfsmw_native_resolution_scale=" + str(@"scale"));
    a.push_back("--nfsmw_native_half_rate_reflections=" + b([Value(s, @"reflection_rate") isEqualToString:@"half"]));
    a.push_back("--nfsmw_native_shadow_scale=" + str(@"shadow_scale"));
    a.push_back("--nfsmw_native_scale_reflections=" + b([Value(s, @"reflection_size") isEqualToString:@"scaled"]));
    // MetalFX removed from the launcher in dev75 (Stefan, Nov 5): on the iPhone 17
    // Pro Max 1x + MetalFX to the screen drew 43.4 %/h vs 33.9 at native (60 fps).
    // The renderer path stays for diagnostics via --nfsmw_native_metalfx (default off).
    a.push_back("--nfsmw_native_motion_debug=" + b(On(s, @"motion_debug")));
    a.push_back("--nfsmw_native_cost_probe=" + b(On(s, @"cost_probe")));
    a.push_back("--nfsmw_heat_scale=" + b(On(s, @"heat_scale")));
    a.push_back("--nfsmw_heat_scale_test=" + b(On(s, @"heat_scale_test")));
    // FXAA in the native renderer (the emulated one's is swap_post_effect).
    NSString* aa_mode = Value(s, @"antialiasing");
    a.push_back(std::string("--nfsmw_native_fxaa=") +
                ([aa_mode isEqualToString:@"fxaa"]        ? "normal"
                 : [aa_mode isEqualToString:@"fxaa_high"] ? "high"
                                                          : "off"));
    // MSAA in the native renderer also where the game draws without (19.5:9).
    a.push_back(std::string("--nfsmw_native_force_msaa=") +
                ([aa_mode isEqualToString:@"msaa4"] ? "4" : [aa_mode isEqualToString:@"msaa2"] ? "2" : "0"));
  } else {
    a.push_back("--resolution_scale=" + std::to_string(whole_scale));
  }
  a.push_back("--ios_thread_qos=false");  // accepted for older argument files; promotion is retired
  a.push_back("--ios_async_submits=" + b(On(s, @"async_submits")));
  // The single pass is the game's mode without anti-aliasing: not with MSAA.
  a.push_back("--nfsmw_render_sin_mosaico=" + b(wide || (On(s, @"one_pass") && !msaa)));
  a.push_back(std::string("--render_target_path_vulkan=") + (On(s, @"edram_fsi") ? "fsi" : "fbo"));
  a.push_back("--occlusion_query_enable=" + b(On(s, @"occlusion")));
  a.push_back("--ios_invalidation_widen_kb=" + str(@"widen_kb"));
  a.push_back("--nfsmw_shadow_map_size=" + str(@"shadow_size"));
  a.push_back(std::string("--readback_resolve=") + (On(s, @"exposure") ? "fast" : "none"));
  a.push_back("--readback_memexport=" + b(On(s, @"memexport")));
  a.push_back("--clear_memory_page_state=" + b(On(s, @"pages")));
  a.push_back("--ios_iso_stream=" + b(On(s, @"iso_stream")));
  a.push_back("--ios_xma_starve_reset=" + b(On(s, @"audio_starve_reset")));
  NSString* lanMode = Value(s, @"lan_mode");
  const bool lan = [lanMode isEqualToString:@"auto"] || [lanMode isEqualToString:@"join"] ||
                   [lanMode isEqualToString:@"host"] || [lanMode isEqualToString:@"host_pc"];
  a.push_back(std::string("--red_lan=") + b(lan));
  a.push_back(std::string("--red_live=") + b(lan));
  a.push_back(std::string("--grant_user_privileges=") + b(lan));
  if (lan) {
    NSString* endpoint = s[@"lan_resolved_ip"] ?: @"";
    // Automatic LAN and PC hosts go through the in-app relay on 127.0.0.1.
    const bool pc = ([s[@"lan_pc"] isEqualToString:@"true"] && [lanMode isEqualToString:@"join"]) ||
                    [lanMode isEqualToString:@"auto"];
    a.push_back("--red_dns=" + (pc ? std::string("127.0.0.1") : std::string(endpoint.UTF8String)));
    const std::string own = std::string((s[@"lan_own_ip"] ?: @"").UTF8String);
    if (!own.empty()) a.push_back("--red_ip=" + own);
    NSString* name = Value(s, @"lan_gamertag");
    if (name.length && GamertagValid(name)) a.push_back("--user_gamertag=" + std::string(name.UTF8String));
    a.push_back("--red_registro=true");
  }
  a.push_back("--ios_audio_mix_others=" + b(On(s, @"audio_mix_others")));
  a.push_back("--ios_audio_silent_mode=" + b(On(s, @"audio_silent_mode")));
  a.push_back("--nfsmw_native_present=" + b(On(s, @"native_renderer")));
  // No Vulkan at all when the native renderer draws everything
  // (tools/ios/patch_ios_native_backend.py).
  if (On(s, @"native_renderer") && On(s, @"no_vulkan")) {
    a.push_back("--gpu_backend=native");
  }
  a.push_back("--nfsmw_skip_movies=" + b(On(s, @"skip_movies")));
  a.push_back("--nfsmw_native_async_pipelines=" + b(On(s, @"async_pipelines")));
  a.push_back(std::string("--log_level=") +
              (!On(s, @"logging") ? "off" : On(s, @"detailed_log") ? "debug" : "info"));
  a.push_back("--ios_mvk_performance=" + b(On(s, @"mvk_profiling")));
  return a;
}

}  // namespace nfsmw::catalog
