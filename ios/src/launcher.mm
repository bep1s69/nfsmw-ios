// NFSMW Recompiled - the pre-launch screen on iOS
//
// The iOS counterpart of Android's SetupActivity + Ajustes
// (android/app/src/main/java/io/github/nfsmwrecomp/): the same sections, the
// same options and texts, for what exists on iOS. Not here, and why:
//   - GPU driver import, GPU turbo, thread affinity: Android only. iOS gets
//     its own two performance switches instead (thread QoS, async submits).
//   - The native engine's options (render resolution, fps limit, shadows,
//     reflections, filters, AAudio): that engine is not part of the iOS port.
//   - App language: the iOS app is English only.
//   - The gamertag: with a custom one the game asked to sign in to Xbox Live,
//     and saying yes froze it. The SDK's default profile stays.
//   - Tilt steering and the touch layout editor: tilt only acts while driving,
//     and only the native engine can tell when that is (on Android's Xenos
//     engine it never turns on); both come later.
//
// It runs before the game: main() calls Run(), which puts a UIKit window up
// and spins the main run loop until Play is tapped (the way SDL shows its own
// message boxes on iOS), then takes the window down. The game's SDL window is
// created after that.
//
// Settings live in Documents/settings.json (string values), saved on every
// change, so they can be read and edited from the Files app too.

#import <UIKit/UIKit.h>

#include <algorithm>
#include <cctype>
#include <cmath>
#include <functional>
#include <regex>
#include <system_error>
#include <unordered_map>

#include "launcher.h"
#include "touch_controls.h"
#include "save_manager.h"
#include <dlfcn.h>
#include <mach-o/loader.h>

namespace fs = std::filesystem;

namespace {

// ---------------------------------------------------------------------------
//  The options
// ---------------------------------------------------------------------------
enum class Type { kSwitch, kChoice, kText, kLink };  // kLink: a row that opens a screen

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
};

struct Section {
  NSString* title;
  NSString* footer;
  std::vector<Option> options;
  int tab = 0;  // Tabs(): which tab shows it
};

// The launcher's tabs (a segmented control at the top).
enum Tab { kTabGame, kTabGraphics, kTabControls, kTabAudio, kTabAdvanced, kTabCount };
NSArray<NSString*>* TabTitles() {
  return @[ @"Game", @"Graphics", @"Controls", @"Audio", @"Advanced" ];
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

bool EmulatorOnly(NSString* key) {
  static NSSet* keys = [NSSet setWithArray:@[
    @"scaling", @"async_submits", @"one_pass", @"edram_fsi", @"widen_kb", @"occlusion", @"exposure",
    @"memexport", @"pages", @"mvk_profiling"
  ]];
  return [keys containsObject:key];
}
bool NativeOnly(NSString* key) {
  static NSSet* keys = [NSSet setWithArray:@[ @"no_vulkan", @"async_pipelines" ]];
  return [keys containsObject:key];
}

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
  NSString* standard;
};

const std::vector<KeyBind>& KeyBinds() {
  static const std::vector<KeyBind> binds = {
      {@"keybind_right_trigger", @"Accelerate", @"RT", @"Up,W"},
      {@"keybind_left_trigger", @"Brake / reverse", @"LT", @"Down,S"},
      {@"keybind_lstick_left", @"Steer left", @"left stick", @"Left,A"},
      {@"keybind_lstick_right", @"Steer right", @"left stick", @"Right,D"},
      {@"keybind_lstick_up", @"Menu up", @"left stick", @"Up,W"},
      {@"keybind_lstick_down", @"Menu down", @"left stick", @"Down,S"},
      {@"keybind_a", @"Accept / handbrake", @"A", @"Return,Space"},
      {@"keybind_b", @"Back / nitrous", @"B", @"Backspace,Alt"},
      {@"keybind_x", @"Speedbreaker", @"X", @"X"},
      {@"keybind_y", @"Y (map, details)", @"Y", @"Tab"},
      {@"keybind_rstick_up", @"Shift up", @"right stick", @"Shift"},
      {@"keybind_rstick_down", @"Shift down", @"right stick", @"Control"},
      {@"keybind_left_shoulder", @"Look back", @"LB", @"C"},
      {@"keybind_right_shoulder", @"Change camera", @"RB", @"V"},
      {@"keybind_back", @"Reset car", @"Back", @"R"},
      {@"keybind_start", @"Pause / start", @"Start", @"Escape,P"},
      {@"keybind_dpad_up", @"D-pad up", @"D-pad", @"I"},
      {@"keybind_dpad_down", @"D-pad down", @"D-pad", @"K"},
      {@"keybind_dpad_left", @"D-pad left", @"D-pad", @"J"},
      {@"keybind_dpad_right", @"D-pad right", @"D-pad", @"L"},
      {@"keybind_rstick_left", @"Right stick left", @"right stick", @""},
      {@"keybind_rstick_right", @"Right stick right", @"right stick", @""},
      {@"keybind_lstick_press", @"Left stick click", @"L3", @""},
      {@"keybind_rstick_press", @"Right stick click", @"R3", @""},
      {@"keybind_guide", @"Guide", @"Guide", @""},
  };
  return binds;
}

NSString* KeyBindValue(NSDictionary<NSString*, NSString*>* s, const KeyBind& b) {
  NSString* v = s[[@"kb_" stringByAppendingString:b.setting]];
  return v ?: b.standard;
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
  const CGSize n = UIScreen.mainScreen.nativeBounds.size;
  return CGSizeMake(std::max(n.width, n.height), std::min(n.width, n.height));
}

// "auto": the shape closest to the screen's.
NSString* AutoAspect() {
  const CGSize px = ScreenPixels();
  const double r = px.width / px.height;
  return r >= 2.0 ? @"wide" : r <= 1.45 ? @"4:3" : @"16:9";
}

NSString* NativeScaleTitle() {
  return [NSString stringWithFormat:@"Native · %.0fp (this screen)", ScreenPixels().height];
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

const std::vector<Section>& Sections() {
  static const std::vector<Section> sections = {
      {@"Game", nil,
       {
           {@"black_edition", Type::kSwitch, @"Black Edition content",
            @"The Black Edition extras that exist in the Xbox 360 game, like the Porsche 911 "
            @"GT2 and the Corvette C6.R.",
            @"true"},
       }, kTabGame},
      {@"Saves", nil,
       {
           {@"saves", Type::kLink, @"Save manager",
            @"Your careers with their progress; backups, restore, export and import; and a copy "
            @"in an iCloud Drive folder, kept in sync between your devices.",
            @""},
       }, kTabGame},
      {@"Extra Options", @"Features of the PC mod Extra Options (nfsmods.xyz/mod/43), ported to the Xbox 360 "
       @"game.",
       {
           {@"marker_count", Type::kChoice, @"Markers after beating a rival",
            @"How many of the six markers you pick after beating a Blacklist rival. The game's "
            @"is 2.",
            @"2",
            {{@"1", @"1"}, {@"2", @"2"}, {@"3", @"3"}, {@"4", @"4"}, {@"5", @"5"}, {@"6", @"6"}}},
           {@"car_limit", Type::kChoice, @"Cars you can buy",
            @"How many cars you can buy at the car lot. Blacklist and bonus cars do not count. "
            @"The game's is 10.",
            @"10",
            {{@"10", @"10"}, {@"12", @"12"}, {@"15", @"15"}, {@"18", @"18"}, {@"20", @"20"},
             {@"25", @"25"}}},
           {@"sim_120", Type::kSwitch, @"120 Hz simulation (experimental)",
            @"The game moves its world 60 times a second at any frame rate. On, 120 times: for "
            @"the 120 fps cap. Under test; turn it off if the game runs too fast or too slow.",
            @"false"},
           {@"skip_movies", Type::kSwitch, @"Skip movies",
            @"Skips the game's movies, as Extra Options' SkipMovies: the EA logo and intro go "
            @"straight to \"press start\". The story movies of the career are skipped too.",
            @"false"},
           {@"old_bridge", Type::kSwitch, @"Open the road to the Old Bridge",
            @"Removes the barrier that closes the road to the Old Bridge.",
            @"false"},
       }, kTabGame},
      {@"Renderer", nil,
       {
           {@"native_renderer", Type::kSwitch, @"Native Metal renderer",
            @"Draws the game with its own shaders translated to Metal, instead of emulating the "
            @"Xbox 360's GPU: much faster, sharper settings possible (Render resolution). Movies "
            @"included. Off: the emulated renderer for everything. "
            @"Needs the native shaders in this build (without them the emulated one is used).",
            @"true"},
           {@"no_vulkan", Type::kSwitch, @"No emulated renderer (no Vulkan)",
            @"With the native Metal renderer on: Vulkan and MoltenVK are not started at all "
            @"(less memory, faster start). The native renderer draws everything, movies "
            @"included. Off: Vulkan runs alongside, as before.",
            @"true"},
           {@"async_pipelines", Type::kSwitch, @"Compile pipelines in the background",
            @"Native renderer: the first time a new kind of draw appears, it is compiled in the "
            @"background and that object is missing for a few frames, instead of a hitch of up to "
            @"~70 ms. Pipelines from earlier sessions are compiled at startup either way.",
            @"true"},
       }, kTabGraphics},
      {@"Display", nil,
       {
           {@"aspect", Type::kChoice, @"Screen shape",
            @"The shape of the game's picture. Fit this screen: 19.5:9 on iPhone, 4:3 on iPad, "
            @"16:9 elsewhere. 16:9 is the Xbox 360's own; on other screens it has black bars "
            @"(or see Stretch). 4:3 is the game's own mode for 4:3 TVs, with its own field of "
            @"view and HUD.",
            @"auto",
            {{@"Fit this screen", @"auto"}, {@"16:9 (Xbox 360)", @"16:9"}, {@"4:3", @"4:3"},
             {@"19.5:9", @"wide"}}},
           {@"scale", Type::kChoice, @"Render resolution",
            ScaleSummary(),
            @"1",
            {{@"1x · 720p (Xbox 360)", @"1"}, {@"1.25x · 900p", @"1.25"}, {@"1.5x · 1080p", @"1.5"},
             {@"1.75x · 1260p", @"1.75"}, {@"2x · 1440p", @"2"}, {NativeScaleTitle(), @"native"}}},
           {@"fps_cap", Type::kChoice, @"Frame rate cap",
            @"30 saves battery and heat. 60 is the game's own. 40 and 120 are experimental: "
            @"they run the console's screen refresh at 120 Hz, which the game was not made "
            @"for, so some things may run too fast.",
            @"60",
            {{@"30", @"30"}, {@"40 (experimental)", @"40"}, {@"60", @"60"},
             {@"120 (experimental)", @"120"}}},
           {@"stretch", Type::kSwitch, @"Stretch to full screen",
            @"Off: the Xbox 360's 16:9 image, with black bars. On: fills the screen, but "
            @"distorts the image.",
            @"false"},
           {@"show_fps", Type::kSwitch, @"Show FPS",
            @"Corner counter: frames per second and milliseconds per frame.", @"false"},
       }, kTabGraphics},
      {@"Graphics", nil,
       {
           {@"antialiasing", Type::kChoice, @"Anti-aliasing",
            @"Smooths jagged edges. MSAA is the game's own: the finest and the most expensive "
            @"(it also turns off the single-pass scene). FXAA is a filter over the final "
            @"image: much cheaper, but a little softer.",
            @"off",
            {{@"Off", @"off"},
             {@"MSAA 2x", @"msaa2"},
             {@"MSAA 4x", @"msaa4"},
             {@"FXAA", @"fxaa"},
             {@"FXAA high", @"fxaa_high"}}},
           {@"anisotropic", Type::kChoice, @"Anisotropic filtering",
            @"Sharper textures seen at an angle, like the road in the distance.", @"3",
            {{@"Off", @"0"}, {@"2x", @"2"}, {@"4x", @"3"}, {@"16x", @"5"}}},
           {@"shadow_size", Type::kChoice, @"Shadow quality",
            @"Size of the shadow map, drawn and copied every frame. Lower: more fps where the GPU "
            @"is the limit, softer shadow edges. The Xbox 360's is High.",
            @"1600",
            {{@"High (1600, Xbox 360)", @"1600"}, {@"Medium (1280)", @"1280"},
             {@"Low (1024)", @"1024"}, {@"Very low (768)", @"768"}}},
           {@"postprocessing", Type::kSwitch, @"Post-processing",
            @"The original game's color filter and blur. Off: less GPU work, but it no longer "
            @"looks like the original.",
            @"true"},
           {@"scaling", Type::kChoice, @"Scaling to the screen",
            @"How the game image is taken to the screen size. FSR: sharper upscaling. CAS: "
            @"sharpening only.",
            @"bilinear",
            {{@"Bilinear", @"bilinear"}, {@"AMD FSR 1.0", @"fsr"}, {@"AMD CAS", @"cas"}}},
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
            @""},
       }, kTabControls},
      {@"Keyboard", nil,
       {
           {@"keyboard", Type::kSwitch, @"Keyboard controls",
            @"Play with a hardware keyboard (Magic Keyboard, Bluetooth or USB): its keys act as "
            @"the controller, together with the touch controls and any gamepad.",
            @"true"},
           {@"keyboard_bindings", Type::kLink, @"Customize keyboard controls",
            @"Which key does what. PC-style by default: arrows or WASD to drive, Space handbrake, "
            @"Alt nitrous, Shift and Ctrl to change gear, Return to accept, Backspace to go back, "
            @"Esc to pause.",
            @""},
       }, kTabControls},
      {@"Audio", nil,
       {
           {@"audio_starve_reset", Type::kSwitch, @"Audio stream reset",
            @"When a sound stream runs out of data, drop what it had decoded but not yet played "
            @"(Xenia Canary's fix for stale sounds in NFS). Leave it on: off, music cuts out. "
            @"Only for testing.",
            @"true"},
       }, kTabAudio},
      {@"Performance", @"To test what each thing costs on your device. The defaults are the recommended ones.",
       {
           {@"thread_qos", Type::kSwitch, @"Top thread priority",
            @"Runs the game's main thread and the GPU command thread at the highest priority, "
            @"on the performance cores.",
            @"true"},
           {@"iso_stream", Type::kSwitch, @"Read the ISO in pieces",
            @"Reads the disc image as the game needs it instead of mapping all 7.8 GB into "
            @"memory. Used automatically when mapping fails (devices with less address space); "
            @"on, it is used always, for testing.",
            @"false"},
       }, kTabAdvanced},
      {@"Emulated renderer", @"Only for the emulated (Vulkan) renderer: greyed out while the native Metal renderer "
       @"draws the game.",
       {
           {@"async_submits", Type::kSwitch, @"Asynchronous GPU submission",
            @"MoltenVK encodes the GPU work on its own thread, so the game does not wait for "
            @"it. Off made menus and races several fps slower.",
            @"true"},
           {@"one_pass", Type::kSwitch, @"Single-pass scene",
            @"Draws the scene once instead of in three strips: ~30 % fewer draws and about "
            @"+25-45 % fps in races. Not available with MSAA.",
            @"true"},
           {@"edram_fsi", Type::kSwitch, @"EDRAM in the pixel shader (experimental)",
            @"Another way to emulate the Xbox 360's EDRAM. Ignored if the GPU does not support "
            @"it.",
            @"false"},
           {@"widen_kb", Type::kChoice, @"CPU write invalidation (experimental)",
            @"How much memory around a CPU write is refreshed for the GPU. Smaller: less copying, "
            @"more faults on the game's threads. For measuring.",
            @"256",
            {{@"256 KB (SDK)", @"256"}, {@"64 KB", @"64"}, {@"16 KB", @"16"}, {@"4 KB", @"4"}}},
           {@"occlusion", Type::kSwitch, @"Occlusion queries",
            @"Sun flares and lights. Makes the game wait for the GPU. Off currently hangs at "
            @"boot on iOS.",
            @"true"},
           {@"exposure", Type::kSwitch, @"Accurate exposure",
            @"Reads the image back from the GPU every frame. Without it the image looks "
            @"washed out.",
            @"true"},
           {@"memexport", Type::kSwitch, @"Memexport readback",
            @"Memory coherence for what the shaders write. May cost performance.", @"true"},
           {@"pages", Type::kSwitch, @"Refresh GPU-written pages",
            @"Memory coherence. May cost performance.", @"true"},
           {@"mvk_profiling", Type::kSwitch, @"MoltenVK profiling",
            @"MoltenVK's own timings, in the log every 300 frames. Only for measuring.",
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
           {@"gpu_capture", Type::kSwitch, @"GPU frame capture button",
            @"A CAPTURE button in the top-right corner of the game. A tap saves the GPU work of "
            @"about two frames to Documents/captures, to open in Xcode on a Mac. Only for "
            @"measuring: captures are large.",
            @"false"},
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
  return s;
}

void SaveSettings(const fs::path& docs, NSDictionary<NSString*, NSString*>* s) {
  NSData* data = [NSJSONSerialization
      dataWithJSONObject:s
                 options:NSJSONWritingPrettyPrinted | NSJSONWritingSortedKeys
                   error:nil];
  [data writeToFile:SettingsPath(docs) atomically:YES];
}

bool On(NSDictionary<NSString*, NSString*>* s, NSString* key);

NSString* Value(NSDictionary<NSString*, NSString*>* s, NSString* key) {
  NSString* v = s[key];
  if (v && [key isEqualToString:@"aspect"]) {  // older settings files: the video modes themselves
    if ([v isEqualToString:@"1024x768"] || [v isEqualToString:@"640x480"]) return @"4:3";
    if ([v isEqualToString:@"1560x720"]) return @"wide";
  }
  if (v) {
    return v;
  }
  // The render resolution's default: 1.5x with the native renderer (almost as
  // sharp as the screen on a phone, at about half the GPU work of 2x), 1x
  // without it.
  if ([key isEqualToString:@"scale"]) {
    return On(s, @"native_renderer") ? @"1.5" : @"1";
  }
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
  a.push_back("--black_edition=" + b(On(s, @"black_edition")));
  a.push_back("--nfsmw_marker_count=" + str(@"marker_count"));
  a.push_back("--nfsmw_purchased_car_limit=" + str(@"car_limit"));
  a.push_back("--nfsmw_remove_old_bridge_barrier=" + b(On(s, @"old_bridge")));
  a.push_back(std::string("--nfsmw_sim_rate=") + (On(s, @"sim_120") ? "120" : "60"));
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
  NSString* const aspect = ResolvedAspect(s);
  // 4:3: the game's HD 4:3 mode, its scene drawn at 960x720 (not 640x480).
  if ([aspect isEqualToString:@"4:3"]) {
    a.push_back("--resolution=1024x768");
    a.push_back("--nfsmw_sd_scene_720=true");
  }
  // Wider than 16:9: the scene is one wide strip, which needs the single pass.
  const bool wide = [aspect isEqualToString:@"wide"];
  if (wide) {
    a.push_back("--resolution=1560x720");
    a.push_back("--nfsmw_wide_scene_width=1560");
  }
  a.push_back("--present_letterbox=" + b(!On(s, @"stretch")));
  a.push_back("--ios_show_fps=" + b(On(s, @"show_fps")));
  a.push_back("--ios_touch_controls=" + b(On(s, @"touch_controls")));
  a.push_back("--mnk_mode=" + b(On(s, @"keyboard")));
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
  a.push_back("--anisotropic_override=" + str(@"anisotropic"));
  // With the native renderer the scale is its own: the emulated renderer only
  // draws what the native one does not (videos) and stays at 1x. Scaled, it
  // allocates its scaled resolve buffer whole (512 MB x scale^2: MoltenVK has
  // no sparse buffers), 2 GB at 2x that nothing used.
  if (On(s, @"native_renderer")) {
    a.push_back("--resolution_scale=1");
    a.push_back("--nfsmw_native_resolution_scale=" + str(@"scale"));
  } else {
    a.push_back("--resolution_scale=" + std::to_string(whole_scale));
  }
  a.push_back("--ios_thread_qos=" + b(On(s, @"thread_qos")));
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
  a.push_back("--ios_gpu_capture=" + b(On(s, @"gpu_capture")));
  return a;
}

NSString* FileSize(const fs::path& p) {
  std::error_code ec;
  const auto bytes = fs::file_size(p, ec);
  return ec ? @"?" : [NSByteCountFormatter stringFromByteCount:(long long)bytes
                                                    countStyle:NSByteCountFormatterCountStyleFile];
}

// ---------------------------------------------------------------------------
//  Achievements
// ---------------------------------------------------------------------------
// The list comes from the game itself (achievements_export.cpp writes
// Documents/achievements/list.json and icons/ when the game starts); what is
// unlocked, from the SDK's own file, Documents/data/achievements/<title>.toml:
//
//   [unlocked.<id>]
//   filetime = <Windows FILETIME>
struct Achievement {
  uint32_t id = 0;
  NSString* name = @"";
  NSString* description = @"";
  NSString* locked_description = @"";
  uint32_t gamerscore = 0;
  NSString* icon = nil;  // full path, or nil
  bool unlocked = false;
  uint64_t filetime = 0;
};

struct Achievements {
  bool loaded = false;  // false until the game has run once
  std::vector<Achievement> list;
  size_t unlocked = 0;
  uint32_t gamerscore = 0, gamerscore_total = 0;
};

Achievements LoadAchievements(const fs::path& docs) {
  Achievements out;
  const fs::path dir = docs / "achievements";
  NSData* data = [NSData dataWithContentsOfFile:@((dir / "list.json").c_str())];
  NSDictionary* json = data ? [NSJSONSerialization JSONObjectWithData:data options:0 error:nil]
                            : nil;
  NSArray* items = [json isKindOfClass:NSDictionary.class] ? json[@"achievements"] : nil;
  if (![items isKindOfClass:NSArray.class]) {
    return out;
  }
  out.loaded = true;

  // What is unlocked: "[unlocked.<id>]" then "filetime = <n>".
  std::unordered_map<uint32_t, uint64_t> unlocked;
  NSString* title = [json[@"title_id"] isKindOfClass:NSString.class] ? json[@"title_id"] : @"";
  NSString* toml = [NSString
      stringWithContentsOfFile:@((docs / "data" / "achievements" / (std::string(title.UTF8String) + ".toml")).c_str())
                      encoding:NSUTF8StringEncoding
                         error:nil];
  uint32_t current = 0;
  bool in_entry = false;
  for (NSString* raw in [toml componentsSeparatedByCharactersInSet:NSCharacterSet.newlineCharacterSet]) {
    NSString* line = [raw stringByTrimmingCharactersInSet:NSCharacterSet.whitespaceCharacterSet];
    if ([line hasPrefix:@"[unlocked."] && [line hasSuffix:@"]"]) {
      current = uint32_t([[line substringWithRange:NSMakeRange(10, line.length - 11)] longLongValue]);
      in_entry = true;
      unlocked[current] = 0;
    } else if (in_entry && [line hasPrefix:@"filetime"]) {
      NSRange eq = [line rangeOfString:@"="];
      if (eq.location != NSNotFound) {
        unlocked[current] = strtoull([line substringFromIndex:eq.location + 1].UTF8String, nullptr, 10);
      }
    }
  }

  for (NSDictionary* item in items) {
    if (![item isKindOfClass:NSDictionary.class]) {
      continue;
    }
    Achievement a;
    a.id = [item[@"id"] unsignedIntValue];
    a.name = item[@"name"] ?: @"";
    a.description = item[@"description"] ?: @"";
    a.locked_description = item[@"locked_description"] ?: @"";
    a.gamerscore = [item[@"gamerscore"] unsignedIntValue];
    NSString* icon = item[@"icon"];
    if (icon.length) {
      a.icon = @((dir / icon.UTF8String).c_str());
    }
    auto u = unlocked.find(a.id);
    a.unlocked = u != unlocked.end();
    a.filetime = a.unlocked ? u->second : 0;
    out.unlocked += a.unlocked;
    out.gamerscore += a.unlocked ? a.gamerscore : 0;
    out.gamerscore_total += a.gamerscore;
    out.list.push_back(a);
  }
  return out;
}

NSString* AchievementSummary(const Achievements& a) {
  return [NSString stringWithFormat:@"%zu of %zu unlocked · %u of %u G", a.unlocked,
                                    a.list.size(), a.gamerscore, a.gamerscore_total];
}

}  // namespace

// ---------------------------------------------------------------------------
//  The achievement list
// ---------------------------------------------------------------------------
@interface NFSAchievementsController : UITableViewController
- (instancetype)initWithAchievements:(Achievements)achievements;
@end

@implementation NFSAchievementsController {
  Achievements _a;
  NSCache<NSString*, UIImage*>* _icons;
}

- (instancetype)initWithAchievements:(Achievements)achievements {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _a = std::move(achievements);
    _icons = [[NSCache alloc] init];
    self.title = @"Achievements";
  }
  return self;
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(_a.list.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  return AchievementSummary(_a);
}

- (UIImage*)iconFor:(const Achievement&)a {
  if (!a.icon) {
    return [UIImage systemImageNamed:@"trophy"];
  }
  UIImage* image = [_icons objectForKey:a.icon];
  if (!image) {
    image = [UIImage imageWithContentsOfFile:a.icon] ?: [UIImage systemImageNamed:@"trophy"];
    [_icons setObject:image forKey:a.icon];
  }
  return image;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const Achievement& a = _a.list[size_t(ip.row)];
  UITableViewCell* cell = [tableView dequeueReusableCellWithIdentifier:@"a"]
                              ?: [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                                        reuseIdentifier:@"a"];
  cell.selectionStyle = UITableViewCellSelectionStyleNone;
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.text = a.name;
  c.textProperties.font = [UIFont preferredFontForTextStyle:UIFontTextStyleHeadline];
  NSString* text = a.unlocked || a.locked_description.length == 0 ? a.description
                                                                  : a.locked_description;
  NSString* status = @"Locked";
  if (a.unlocked) {
    status = @"Unlocked";
    if (a.filetime > 116444736000000000ULL) {
      NSDate* when = [NSDate dateWithTimeIntervalSince1970:double(a.filetime - 116444736000000000ULL) / 1e7];
      status = [@"Unlocked " stringByAppendingString:
                                 [NSDateFormatter localizedStringFromDate:when
                                                                dateStyle:NSDateFormatterMediumStyle
                                                                timeStyle:NSDateFormatterShortStyle]];
    }
  }
  c.secondaryText = [NSString stringWithFormat:@"%@\n%u G · %@", text, a.gamerscore, status];
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  c.textToSecondaryTextVerticalPadding = 4;
  c.image = [self iconFor:a];
  c.imageProperties.maximumSize = CGSizeMake(56, 56);
  c.imageProperties.reservedLayoutSize = CGSizeMake(56, 56);
  c.imageProperties.cornerRadius = 6;
  c.imageToTextPadding = 14;
  cell.contentConfiguration = c;
  // Locked: dimmed, as on the console.
  cell.contentView.alpha = a.unlocked ? 1.0 : 0.45;
  cell.accessoryType = a.unlocked ? UITableViewCellAccessoryCheckmark : UITableViewCellAccessoryNone;
  return cell;
}

@end

// ---------------------------------------------------------------------------
//  The screen
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
//  Keyboard controls: the editor
// ---------------------------------------------------------------------------
// "Press a key": takes the next key from a hardware keyboard (UIPress), shown
// as a sheet; Cancel (or a tap outside) leaves the binding as it was.
@interface NFSKeyCaptureController : UIViewController
- (instancetype)initWithPrompt:(NSString*)prompt done:(void (^)(NSString* key))done;
@end

@implementation NFSKeyCaptureController {
  NSString* _prompt;
  void (^_done)(NSString*);
  UILabel* _hint;
}

- (instancetype)initWithPrompt:(NSString*)prompt done:(void (^)(NSString*))done {
  if ((self = [super initWithNibName:nil bundle:nil])) {
    _prompt = prompt;
    _done = done;
    self.modalPresentationStyle = UIModalPresentationFormSheet;
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = UIColor.systemBackgroundColor;
  UILabel* title = [[UILabel alloc] init];
  title.text = _prompt;
  title.font = [UIFont preferredFontForTextStyle:UIFontTextStyleTitle2];
  title.numberOfLines = 0;
  title.textAlignment = NSTextAlignmentCenter;
  _hint = [[UILabel alloc] init];
  _hint.text = @"Press a key on the keyboard.";
  _hint.textColor = UIColor.secondaryLabelColor;
  _hint.numberOfLines = 0;
  _hint.textAlignment = NSTextAlignmentCenter;
  UIButton* cancel = [UIButton buttonWithType:UIButtonTypeSystem];
  [cancel setTitle:@"Cancel" forState:UIControlStateNormal];
  [cancel addAction:[UIAction actionWithHandler:^(UIAction*) {
            [self dismissViewControllerAnimated:YES completion:nil];
          }]
      forControlEvents:UIControlEventTouchUpInside];
  UIStackView* stack = [[UIStackView alloc] initWithArrangedSubviews:@[ title, _hint, cancel ]];
  stack.axis = UILayoutConstraintAxisVertical;
  stack.spacing = 16;
  stack.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:stack];
  [NSLayoutConstraint activateConstraints:@[
    [stack.centerXAnchor constraintEqualToAnchor:self.view.centerXAnchor],
    [stack.centerYAnchor constraintEqualToAnchor:self.view.centerYAnchor],
    [stack.leadingAnchor constraintGreaterThanOrEqualToAnchor:self.view.leadingAnchor constant:24],
  ]];
}

- (BOOL)canBecomeFirstResponder {
  return YES;
}

- (void)viewDidAppear:(BOOL)animated {
  [super viewDidAppear:animated];
  [self becomeFirstResponder];
}

- (void)pressesBegan:(NSSet<UIPress*>*)presses withEvent:(UIPressesEvent*)event {
  for (UIPress* press in presses) {
    if (!press.key) continue;
    NSString* name = KeyName(press.key.keyCode);
    if (!name) {
      _hint.text = @"That key cannot be used. Press another one.";
      continue;
    }
    void (^done)(NSString*) = _done;
    [self dismissViewControllerAnimated:YES completion:^{
      done(name);
    }];
    return;
  }
  [super pressesBegan:presses withEvent:event];
}

@end

// The list of actions and their keys. Tapping one: replace its key, add a
// second one, clear it or put the default back.
@interface NFSKeyBindsController : UITableViewController
- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings
                            save:(void (^)(void))save;
@end

@implementation NFSKeyBindsController {
  NSMutableDictionary<NSString*, NSString*>* _settings;
  void (^_save)(void);
}

- (instancetype)initWithSettings:(NSMutableDictionary<NSString*, NSString*>*)settings
                            save:(void (^)(void))save {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _settings = settings;
    _save = save;
    self.title = @"Keyboard controls";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:@"Defaults"
                                       style:UIBarButtonItemStylePlain
                                      target:self
                                      action:@selector(confirmDefaults)];
}

- (void)setValue:(NSString*)value forBind:(const KeyBind&)b {
  NSString* key = [@"kb_" stringByAppendingString:b.setting];
  if ([value isEqualToString:b.standard]) {
    [_settings removeObjectForKey:key];
  } else {
    _settings[key] = value;
  }
  _save();
  [self.tableView reloadData];
}

- (void)confirmDefaults {
  UIAlertController* alert =
      [UIAlertController alertControllerWithTitle:@"Default keys for everything?"
                                          message:nil
                                   preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Defaults"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            for (const KeyBind& b : KeyBinds()) {
                                              [self->_settings removeObjectForKey:[@"kb_" stringByAppendingString:b.setting]];
                                            }
                                            self->_save();
                                            [self.tableView reloadData];
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(KeyBinds().size());
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  return @"Each action presses a controller input (shown in grey), so the game behaves as with a "
         @"gamepad. One key can do several things (Up accelerates in a race and moves up in the "
         @"menus). Shift, Ctrl and Alt work on their own.";
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const KeyBind& b = KeyBinds()[size_t(ip.row)];
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleValue1
                                                 reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.valueCellConfiguration;
  c.text = b.action;
  c.secondaryText = KeysForDisplay(KeyBindValue(_settings, b));
  cell.contentConfiguration = c;
  UILabel* pad = [[UILabel alloc] init];
  pad.text = b.pad;
  pad.font = [UIFont preferredFontForTextStyle:UIFontTextStyleCaption1];
  pad.textColor = UIColor.tertiaryLabelColor;
  [pad sizeToFit];
  cell.accessoryView = pad;
  return cell;
}

- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  const KeyBind b = KeyBinds()[size_t(ip.row)];
  NSString* current = KeyBindValue(_settings, b);
  UIAlertController* sheet =
      [UIAlertController alertControllerWithTitle:b.action
                                          message:[NSString stringWithFormat:@"Now: %@", KeysForDisplay(current)]
                                   preferredStyle:UIAlertControllerStyleActionSheet];
  auto capture = [self, b](bool add, NSString* current) {
    NFSKeyCaptureController* cap = [[NFSKeyCaptureController alloc]
        initWithPrompt:b.action
                  done:^(NSString* key) {
                    NSString* value = key;
                    if (add && current.length) {
                      NSArray* parts = [current componentsSeparatedByString:@","];
                      value = [parts containsObject:key] ? current : [current stringByAppendingFormat:@",%@", key];
                    }
                    [self setValue:value forBind:b];
                  }];
    [self presentViewController:cap animated:YES completion:nil];
  };
  [sheet addAction:[UIAlertAction actionWithTitle:@"Set a key…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) { capture(false, current); }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Add another key…"
                                            style:UIAlertActionStyleDefault
                                          handler:^(UIAlertAction*) { capture(true, current); }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"No key"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) { [self setValue:@"" forBind:b]; }]];
  [sheet addAction:[UIAlertAction
                       actionWithTitle:[NSString stringWithFormat:@"Default (%@)", KeysForDisplay(b.standard)]
                                 style:UIAlertActionStyleDefault
                               handler:^(UIAlertAction*) { [self setValue:b.standard forBind:b]; }]];
  [sheet addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  // On iPad an action sheet needs an anchor: the row.
  sheet.popoverPresentationController.sourceView = [tableView cellForRowAtIndexPath:ip];
  sheet.popoverPresentationController.sourceRect = [tableView cellForRowAtIndexPath:ip].bounds;
  [self presentViewController:sheet animated:YES completion:nil];
}

@end

// The launcher's navigation: portrait on iPhone, any orientation on iPad
// (the game itself is landscape only: SDL_IOS_ORIENTATIONS in ios_main).
@interface NFSLauncherNavigation : UINavigationController
@end

@implementation NFSLauncherNavigation
- (UIInterfaceOrientationMask)supportedInterfaceOrientations {
  if (self.presentedViewController && !self.presentedViewController.isBeingDismissed) {
    return self.presentedViewController.supportedInterfaceOrientations;  // e.g. the touch editor: landscape
  }
  return UIDevice.currentDevice.userInterfaceIdiom == UIUserInterfaceIdiomPad ? UIInterfaceOrientationMaskAll
                                                                              : UIInterfaceOrientationMaskPortrait;
}
@end

@interface NFSLauncherController : UITableViewController <UITextFieldDelegate>
- (instancetype)initWithDocuments:(fs::path)docs done:(std::function<void(fs::path)>)done;
@end

@implementation NFSLauncherController {
  fs::path _docs;
  std::function<void(fs::path)> _done;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  std::vector<fs::path> _isos;
  NSString* _isoName;  // the chosen one's file name
  NSInteger _tab;      // Tab
  int _savesAttention;  // saves newer in iCloud or changed on both sides
  std::vector<size_t> _visible;  // the Sections() shown on this tab
}

- (instancetype)initWithDocuments:(fs::path)docs done:(std::function<void(fs::path)>)done {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _docs = docs;
    _done = std::move(done);
    _settings = LoadSettings(docs);
    self.title = @"NFSMW Recompiled";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:@"Play"
                                       style:UIBarButtonItemStyleDone
                                      target:self
                                      action:@selector(play)];
  self.navigationItem.leftBarButtonItem =
      [[UIBarButtonItem alloc] initWithTitle:@"Reset"
                                       style:UIBarButtonItemStylePlain
                                      target:self
                                      action:@selector(confirmReset)];
  self.tableView.keyboardDismissMode = UIScrollViewKeyboardDismissModeOnDrag;
  // The tabs.
  UISegmentedControl* tabs = [[UISegmentedControl alloc] initWithItems:TabTitles()];
  _tab = [NSUserDefaults.standardUserDefaults integerForKey:@"nfsmw.launcher.tab"];
  if (_tab < 0 || _tab >= kTabCount) _tab = kTabGame;
  tabs.selectedSegmentIndex = _tab;
  [tabs addAction:[UIAction actionWithHandler:^(UIAction*) {
          self->_tab = tabs.selectedSegmentIndex;
          [NSUserDefaults.standardUserDefaults setInteger:self->_tab forKey:@"nfsmw.launcher.tab"];
          [self reloadTab];
        }]
      forControlEvents:UIControlEventValueChanged];
  UIView* header = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 320, 52)];
  tabs.translatesAutoresizingMaskIntoConstraints = NO;
  [header addSubview:tabs];
  [NSLayoutConstraint activateConstraints:@[
    [tabs.leadingAnchor constraintEqualToAnchor:header.layoutMarginsGuide.leadingAnchor],
    [tabs.trailingAnchor constraintEqualToAnchor:header.layoutMarginsGuide.trailingAnchor],
    [tabs.centerYAnchor constraintEqualToAnchor:header.centerYAnchor],
  ]];
  self.tableView.tableHeaderView = header;
  // About: version and build, so a report names the exact build.
  UILabel* about = [[UILabel alloc] initWithFrame:CGRectMake(0, 0, 320, 56)];
  about.text = AboutText();
  about.numberOfLines = 0;
  about.textAlignment = NSTextAlignmentCenter;
  about.font = [UIFont systemFontOfSize:12];
  about.textColor = UIColor.tertiaryLabelColor;
  self.tableView.tableFooterView = about;
  // Saves: a backup of what changed, and changes from this device to iCloud.
  _savesAttention = nfsmw::saves::AutoSync(_docs);
  [self reloadTab];
  [self rescan];
  // Back from the Files app (an ISO copied in): look again.
  [NSNotificationCenter.defaultCenter addObserver:self
                                         selector:@selector(rescan)
                                             name:UIApplicationDidBecomeActiveNotification
                                           object:nil];
}

- (void)dealloc {
  [NSNotificationCenter.defaultCenter removeObserver:self];
}

- (void)reloadTab {
  _visible.clear();
  for (size_t i = 0; i < Sections().size(); ++i) {
    if (Sections()[i].tab == _tab) _visible.push_back(i);
  }
  [self.tableView reloadData];
}

// The first sections of the Game tab are the ISO and the achievements.
- (NSInteger)fixedSections {
  return _tab == kTabGame ? 2 : 0;
}

- (const Section&)sectionAt:(NSInteger)section {
  return Sections()[_visible[size_t(section - [self fixedSections])]];
}

- (void)rescan {
  _isos = nfsmw::launcher::FindIsos(_docs);
  NSString* chosen = _settings[@"iso"];
  _isoName = nil;
  for (const fs::path& p : _isos) {
    NSString* name = [NSString stringWithUTF8String:p.filename().c_str()];
    if (!_isoName || [name isEqualToString:chosen]) {
      _isoName = name;
    }
  }
  self.navigationItem.rightBarButtonItem.enabled = _isoName != nil;
  [self.tableView reloadData];
}

- (void)set:(NSString*)key to:(NSString*)value {
  _settings[key] = value;
  SaveSettings(_docs, _settings);
}

- (void)play {
  [self.view endEditing:YES];
  for (const fs::path& p : _isos) {
    if ([_isoName isEqualToString:[NSString stringWithUTF8String:p.filename().c_str()]]) {
      _done(p);
      return;
    }
  }
}

- (void)confirmReset {
  UIAlertController* alert =
      [UIAlertController alertControllerWithTitle:@"Reset all settings?"
                                          message:@"Every option goes back to its default. "
                                                  @"Your saves are not touched."
                                   preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel"
                                            style:UIAlertActionStyleCancel
                                          handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Reset"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            NSString* iso = self->_settings[@"iso"];
                                            [self->_settings removeAllObjects];
                                            if (iso) {
                                              self->_settings[@"iso"] = iso;
                                            }
                                            SaveSettings(self->_docs, self->_settings);
                                            [self.tableView reloadData];
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

// On the Game tab, section 0 is the ISO, 1 the achievements; the rest are
// this tab's Sections().
- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return NSInteger(_visible.size()) + [self fixedSections];
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  if (fixed && section == 0) {
    return std::max<NSInteger>(1, NSInteger(_isos.size()));
  }
  if (fixed && section == 1) {
    return 1;
  }
  return NSInteger([self sectionAt:section].options.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  return fixed && section == 0   ? @"ISO"
         : fixed && section == 1 ? @"Achievements"
                                 : [self sectionAt:section].title;
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  const NSInteger fixed = [self fixedSections];
  if (fixed && section == 0) {
    return _isos.empty()
               ? @"Copy your USA ISO into this app's folder (Files app › On My iPhone/iPad › "
                 @"NFSMW, or LiveContainer's folder for it). This screen looks again when you "
                 @"come back."
               : (_isos.size() > 1 ? @"Tap the one to play." : nil);
  }
  if (fixed && section == 1) {
    return nil;
  }
  if (_tab == kTabAdvanced && section == NSInteger(_visible.size()) - 1) {
    NSString* f = [self sectionAt:section].footer ?: @"";
    return [f stringByAppendingString:
                  @"Documents/extra_args.txt, if present, is applied after these settings "
                  @"and wins."];
  }
  return [self sectionAt:section].footer;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                                 reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  c.textToSecondaryTextVerticalPadding = 4;

  const NSInteger fixed = [self fixedSections];
  if (fixed && ip.section == 0) {
    if (_isos.empty()) {
      c.text = @"No ISO found";
      c.textProperties.color = UIColor.systemOrangeColor;
      cell.selectionStyle = UITableViewCellSelectionStyleNone;
    } else {
      const fs::path& p = _isos[size_t(ip.row)];
      NSString* name = [NSString stringWithUTF8String:p.filename().c_str()];
      c.text = name;
      c.secondaryText = FileSize(p);
      cell.accessoryType = [name isEqualToString:_isoName] ? UITableViewCellAccessoryCheckmark
                                                           : UITableViewCellAccessoryNone;
    }
    cell.contentConfiguration = c;
    return cell;
  }

  if (fixed && ip.section == 1) {
    const Achievements a = LoadAchievements(_docs);
    c.image = [UIImage systemImageNamed:@"trophy.fill"];
    c.imageProperties.tintColor = UIColor.systemYellowColor;
    c.text = a.loaded ? AchievementSummary(a) : @"No list yet";
    c.secondaryText = a.loaded ? nil
                               : @"Start the game once: it brings the list of achievements "
                                 @"with it, and this shows it from then on.";
    cell.accessoryType = a.loaded ? UITableViewCellAccessoryDisclosureIndicator
                                  : UITableViewCellAccessoryNone;
    cell.selectionStyle = a.loaded ? UITableViewCellSelectionStyleDefault
                                   : UITableViewCellSelectionStyleNone;
    cell.contentConfiguration = c;
    return cell;
  }

  const Option& o = [self sectionAt:ip.section].options[size_t(ip.row)];
  if ([o.key isEqualToString:@"saves"] && _savesAttention) {
    c.text = o.title;
    c.secondaryText = [NSString stringWithFormat:@"%d save(s) newer in iCloud or changed on two devices: "
                                                 @"open to choose which to keep.",
                                                 _savesAttention];
    c.secondaryTextProperties.color = UIColor.systemOrangeColor;
    cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
    cell.contentConfiguration = c;
    return cell;
  }
  // Greyed out: what only the emulated renderer uses while the native one
  // draws, and the native renderer's own settings while it is off.
  const bool native = On(_settings, @"native_renderer");
  const bool inactive = (native && EmulatorOnly(o.key)) || (!native && NativeOnly(o.key));
  c.text = o.title;
  c.secondaryText = o.summary;
  cell.selectionStyle = UITableViewCellSelectionStyleNone;
  NSString* key = o.key;
  NSString* value = Value(_settings, key);

  switch (o.type) {
    case Type::kSwitch: {
      UISwitch* sw = [[UISwitch alloc] init];
      // Settings another one decides, shown greyed out:
      //  - the single pass: always on at 19.5:9 (the wide scene is one strip),
      //    otherwise off with MSAA (it does not exist with it).
      const bool wide = [ResolvedAspect(_settings) isEqualToString:@"wide"];
      bool locked = false;
      bool on = [value isEqualToString:@"true"];
      if ([key isEqualToString:@"one_pass"] && (wide || Msaa(_settings))) {
        locked = true;
        on = wide;
      }
      locked = locked || inactive;
      sw.on = on;
      sw.enabled = !locked;
      cell.contentView.alpha = locked ? 0.45 : 1.0;
      [sw addAction:[UIAction actionWithHandler:^(UIAction*) {
            [self set:key to:sw.on ? @"true" : @"false"];
            // The native renderer greys other settings out (or back in).
            if ([key isEqualToString:@"native_renderer"]) [self.tableView reloadData];
          }]
          forControlEvents:UIControlEventValueChanged];
      cell.accessoryView = sw;
      break;
    }
    case Type::kChoice: {
      NSMutableArray<UIMenuElement*>* items = [NSMutableArray array];
      for (const Choice& ch : o.choices) {
        NSString* v = ch.value;
        UIAction* item = [UIAction actionWithTitle:ch.title
                                             image:nil
                                        identifier:nil
                                           handler:^(UIAction*) {
                                             [self set:key to:v];
                                             // Anti-aliasing and the aspect ratio
                                             // lock other settings.
                                             [self.tableView reloadData];
                                           }];
        item.state = [v isEqualToString:value] ? UIMenuElementStateOn : UIMenuElementStateOff;
        [items addObject:item];
      }
      UIButtonConfiguration* bc = UIButtonConfiguration.tintedButtonConfiguration;
      bc.indicator = UIButtonConfigurationIndicatorPopup;
      UIButton* button = [UIButton buttonWithConfiguration:bc primaryAction:nil];
      button.menu = [UIMenu menuWithChildren:items];
      button.showsMenuAsPrimaryAction = YES;
      button.changesSelectionAsPrimaryAction = YES;
      [button sizeToFit];
      button.enabled = !inactive;
      cell.contentView.alpha = inactive ? 0.45 : 1.0;
      cell.accessoryView = button;
      break;
    }
    case Type::kLink: {
      cell.accessoryType = UITableViewCellAccessoryDisclosureIndicator;
      cell.selectionStyle = UITableViewCellSelectionStyleDefault;
      break;
    }
    case Type::kText: {
      UITextField* field = [[UITextField alloc] initWithFrame:CGRectMake(0, 0, 170, 34)];
      field.borderStyle = UITextBorderStyleRoundedRect;
      field.placeholder = @"User";
      field.text = value;
      field.autocorrectionType = UITextAutocorrectionTypeNo;
      field.autocapitalizationType = UITextAutocapitalizationTypeNone;
      field.spellCheckingType = UITextSpellCheckingTypeNo;
      field.smartQuotesType = UITextSmartQuotesTypeNo;
      field.returnKeyType = UIReturnKeyDone;
      field.delegate = self;
      [field addAction:[UIAction actionWithHandler:^(UIAction*) {
               // Saved as typed, but only while it is valid for Xbox 360.
               const bool valid = GamertagValid(field.text);
               field.textColor = valid ? UIColor.labelColor : UIColor.systemRedColor;
               if (valid) {
                 [self set:key to:field.text];
               }
             }]
          forControlEvents:UIControlEventEditingChanged];
      cell.accessoryView = field;
      break;
    }
  }
  cell.contentConfiguration = c;
  return cell;
}

- (BOOL)textFieldShouldReturn:(UITextField*)field {
  [field resignFirstResponder];
  return YES;
}

- (void)tableView:(UITableView*)tableView didSelectRowAtIndexPath:(NSIndexPath*)ip {
  [tableView deselectRowAtIndexPath:ip animated:YES];
  const NSInteger fixed = [self fixedSections];
  if (fixed && ip.section == 1) {
    Achievements a = LoadAchievements(_docs);
    if (a.loaded) {
      [self.navigationController
          pushViewController:[[NFSAchievementsController alloc] initWithAchievements:std::move(a)]
                    animated:YES];
    }
    return;
  }
  if (ip.section >= fixed) {
    const Option& o = [self sectionAt:ip.section].options[size_t(ip.row)];
    if (o.type == Type::kLink && [o.key isEqualToString:@"saves"]) {
      [self.navigationController pushViewController:nfsmw::saves::MakeSaveManager(_docs) animated:YES];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"touch_layout"]) {
      [self presentViewController:nfsmw::touch::MakeLayoutEditor() animated:YES completion:nil];
      return;
    }
    if (o.type == Type::kLink && [o.key isEqualToString:@"keyboard_bindings"]) {
      NFSKeyBindsController* editor =
          [[NFSKeyBindsController alloc] initWithSettings:_settings
                                                     save:^{
                                                       SaveSettings(self->_docs, self->_settings);
                                                     }];
      [self.navigationController pushViewController:editor animated:YES];
    }
    return;
  }
  if (fixed && ip.section == 0 && size_t(ip.row) < _isos.size()) {
    _isoName = [NSString stringWithUTF8String:_isos[size_t(ip.row)].filename().c_str()];
    [self set:@"iso" to:_isoName];
    [tableView reloadSections:[NSIndexSet indexSetWithIndex:0]
             withRowAnimation:UITableViewRowAnimationNone];
  }
}

@end

// ---------------------------------------------------------------------------
//  The API
// ---------------------------------------------------------------------------
namespace nfsmw::launcher {

fs::path Documents() {
  NSArray<NSString*>* paths =
      NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);
  return fs::path(paths.firstObject.UTF8String);
}

std::vector<fs::path> FindIsos(const fs::path& documents) {
  std::vector<fs::path> isos;
  std::error_code ec;
  for (const auto& e : fs::directory_iterator(documents, ec)) {
    std::string ext = e.path().extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (e.is_regular_file(ec) && ext == ".iso") {
      isos.push_back(e.path());
    }
  }
  std::sort(isos.begin(), isos.end());
  return isos;
}

fs::path Run(const fs::path& documents) {
  bool finished = false;
  fs::path chosen;
  NFSLauncherController* root =
      [[NFSLauncherController alloc] initWithDocuments:documents
                                                  done:[&](fs::path iso) {
                                                    chosen = iso;
                                                    finished = true;
                                                  }];
  UINavigationController* nav = [[NFSLauncherNavigation alloc] initWithRootViewController:root];
  nav.navigationBar.prefersLargeTitles = YES;

  UIWindowScene* scene = nil;
  for (UIScene* s in UIApplication.sharedApplication.connectedScenes) {
    if ([s isKindOfClass:UIWindowScene.class]) {
      scene = (UIWindowScene*)s;
      break;
    }
  }
  UIWindow* window = scene ? [[UIWindow alloc] initWithWindowScene:scene]
                           : [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
  window.overrideUserInterfaceStyle = UIUserInterfaceStyleDark;
  window.windowLevel = UIWindowLevelNormal + 1;  // over SDL's launch screen
  window.rootViewController = nav;
  [window makeKeyAndVisible];

  while (!finished) {
    @autoreleasepool {
      [NSRunLoop.currentRunLoop runMode:NSDefaultRunLoopMode beforeDate:NSDate.distantFuture];
    }
  }

  window.hidden = YES;
  window.rootViewController = nil;
  window = nil;
  // Back to landscape for the game: the launcher may have left the scene in
  // portrait, and iOS only re-evaluates orientations when asked.
  if (scene) {
    for (UIWindow* w in scene.windows) {
      [w.rootViewController setNeedsUpdateOfSupportedInterfaceOrientations];
    }
    UIWindowSceneGeometryPreferencesIOS* prefs = [[UIWindowSceneGeometryPreferencesIOS alloc]
        initWithInterfaceOrientations:UIInterfaceOrientationMaskLandscape];
    [scene requestGeometryUpdateWithPreferences:prefs errorHandler:nil];
  }
  return chosen;
}

std::vector<std::string> SettingsArguments(const fs::path& documents) {
  return Arguments(LoadSettings(documents));
}

}  // namespace nfsmw::launcher
