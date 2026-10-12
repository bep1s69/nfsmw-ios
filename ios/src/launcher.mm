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
#include <functional>
#include <regex>
#include <system_error>
#include <unordered_map>

#include "launcher.h"

namespace fs = std::filesystem;

namespace {

// ---------------------------------------------------------------------------
//  The options
// ---------------------------------------------------------------------------
enum class Type { kSwitch, kChoice, kText };

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
};

// What the game uses when an option has never been changed: the iOS port's
// current defaults (ios_main.mm), which are Android's except where noted.
const std::vector<Section>& Sections() {
  static const std::vector<Section> sections = {
      {@"Game", nil,
       {
           {@"black_edition", Type::kSwitch, @"Black Edition content",
            @"The Black Edition extras that exist in the Xbox 360 game, like the Porsche 911 "
            @"GT2 and the Corvette C6.R.",
            @"true"},
       }},
      {@"Extra Options",
       @"Features of the PC mod Extra Options (nfsmods.xyz/mod/43), ported to the Xbox 360 "
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
       }},
      {@"Display", nil,
       {
           {@"retina", Type::kChoice, @"Resolution",
            @"Size of the final image on screen. Auto: one pixel per point on large screens "
            @"(iPad), every pixel on small ones (iPhone). Points is lighter and has the least "
            @"input lag; Retina is the sharpest.",
            @"auto",
            {{@"Auto", @"auto"}, {@"Retina", @"true"}, {@"Points", @"false"}}},
           {@"fps_cap", Type::kChoice, @"Frame rate cap",
            @"30 saves battery and heat. 60 is the game's own. 40 and 120 are experimental: "
            @"they run the console's screen refresh at 120 Hz, which the game was not made "
            @"for, so some things may run too fast.",
            @"60",
            {{@"30", @"30"}, {@"40 (experimental)", @"40"}, {@"60", @"60"},
             {@"120 (experimental)", @"120"}}},
           {@"aspect", Type::kChoice, @"Aspect ratio (experimental)",
            @"The video mode the game is told the console has. 4:3 is the game's own mode for "
            @"4:3 TVs, with its own field of view and HUD. The game draws its 4:3 scene at "
            @"640×480; see Sharper 4:3 scene below.",
            @"16:9",
            {{@"16:9", @"16:9"}, {@"4:3 HD (1024×768)", @"1024x768"},
             {@"4:3 SD (640×480)", @"640x480"}, {@"19.5:9 (1560×720)", @"1560x720"}}},
           {@"sd_720", Type::kSwitch, @"Sharper 4:3 scene (experimental)",
            @"At 4:3, the game draws its scene at 960×720 instead of 640×480 (without its "
            @"2x MSAA). Use it with Internal resolution 1x.",
            @"true"},
           {@"stretch", Type::kSwitch, @"Stretch to full screen",
            @"Off: the Xbox 360's 16:9 image, with black bars. On: fills the screen, but "
            @"distorts the image.",
            @"false"},
           {@"show_fps", Type::kSwitch, @"Show FPS",
            @"Corner counter: frames per second and milliseconds per frame.", @"false"},
       }},
      {@"Touch controls", nil,
       {
           {@"touch_controls", Type::kSwitch, @"Touch controls",
            @"On-screen gamepad. It hides itself while a physical controller is connected; "
            @"a tap brings it back.",
            @"true"},
       }},
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
           {@"scaling", Type::kChoice, @"Scaling to the screen",
            @"How the game image is taken to the screen size. FSR: sharper upscaling. CAS: "
            @"sharpening only.",
            @"bilinear",
            {{@"Bilinear", @"bilinear"}, {@"AMD FSR 1.0", @"fsr"}, {@"AMD CAS", @"cas"}}},
           {@"postprocessing", Type::kSwitch, @"Post-processing",
            @"The original game's color filter and blur. Off: less GPU work, but it no longer "
            @"looks like the original.",
            @"true"},
           {@"anisotropic", Type::kChoice, @"Anisotropic filtering",
            @"Sharper textures seen at an angle, like the road in the distance.", @"3",
            {{@"Off", @"0"}, {@"2x", @"2"}, {@"4x", @"3"}, {@"16x", @"5"}}},
           {@"scale", Type::kChoice, @"Internal resolution",
            @"2x renders at 2560×1440: sharper, but much heavier. 1x is recommended.", @"1",
            {{@"1x", @"1"}, {@"2x", @"2"}}},
       }},
      {@"Performance", nil,
       {
           {@"thread_qos", Type::kSwitch, @"Top thread priority",
            @"Runs the game's main thread and the GPU command thread at the highest priority, "
            @"on the performance cores.",
            @"true"},
           {@"async_submits", Type::kSwitch, @"Asynchronous GPU submission",
            @"MoltenVK encodes the GPU work on its own thread, so the game does not wait for "
            @"it. Off made menus and races several fps slower.",
            @"true"},
       }},
      {@"Advanced",
       @"To test what each thing costs on your device. The defaults are the recommended ones.",
       {
           {@"one_pass", Type::kSwitch, @"Single-pass scene",
            @"Draws the scene once instead of in three strips: ~30 % fewer draws and about "
            @"+25-45 % fps in races. Not available with MSAA.",
            @"true"},
           {@"edram_fsi", Type::kSwitch, @"EDRAM in the pixel shader (experimental)",
            @"Another way to emulate the Xbox 360's EDRAM. Ignored if the GPU does not support "
            @"it.",
            @"false"},
           {@"shadow_size", Type::kChoice, @"Shadow quality",
            @"Size of the shadow map, drawn and copied every frame. Lower: more fps where the GPU "
            @"is the limit, softer shadow edges. The Xbox 360's is High.",
            @"1600",
            {{@"High (1600, Xbox 360)", @"1600"}, {@"Medium (1280)", @"1280"},
             {@"Low (1024)", @"1024"}, {@"Very low (768)", @"768"}}},
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
           {@"native_renderer", Type::kSwitch, @"Native Metal renderer (experimental)",
            @"Draws the game with its own shaders translated to Metal instead of the emulated "
            @"Xbox 360 GPU, shown over it. In development: needs the native shaders in this build.",
            @"false"},
           {@"async_pipelines", Type::kSwitch, @"Compile pipelines in the background",
            @"Native renderer: the first time a new kind of draw appears, it is compiled in the "
            @"background and that object is missing for a few frames, instead of a hitch of up to "
            @"~70 ms. Pipelines from earlier sessions are compiled at startup either way.",
            @"true"},
           {@"iso_stream", Type::kSwitch, @"Read the ISO in pieces",
            @"Reads the disc image as the game needs it instead of mapping all 7.8 GB into "
            @"memory. Used automatically when mapping fails (devices with less address space); "
            @"on, it is used always, for testing.",
            @"false"},
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
           {@"mvk_profiling", Type::kSwitch, @"MoltenVK profiling",
            @"MoltenVK's own timings, in the log every 300 frames. Only for measuring.",
            @"false"},
       }},
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

NSString* Value(NSDictionary<NSString*, NSString*>* s, NSString* key) {
  NSString* v = s[key];
  if (v) {
    return v;
  }
  const Option* o = FindOption(key);
  return o ? o->default_value : @"";
}

bool On(NSDictionary<NSString*, NSString*>* s, NSString* key) {
  return [Value(s, key) isEqualToString:@"true"];
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
  a.push_back("--ios_retina=" + str(@"retina"));
  a.push_back("--ios_fps_cap=" + str(@"fps_cap"));
  if (![Value(s, @"aspect") isEqualToString:@"16:9"]) {
    a.push_back("--resolution=" + str(@"aspect"));
    a.push_back("--nfsmw_sd_scene_720=" + b(On(s, @"sd_720")));
  }
  // Wider than 16:9: the scene is one wide strip, which needs the single pass.
  const bool wide = [Value(s, @"aspect") isEqualToString:@"1560x720"];
  if (wide) {
    a.push_back("--nfsmw_wide_scene_width=1560");
  }
  a.push_back("--present_letterbox=" + b(!On(s, @"stretch")));
  a.push_back("--ios_show_fps=" + b(On(s, @"show_fps")));
  a.push_back("--ios_touch_controls=" + b(On(s, @"touch_controls")));
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
    a.push_back("--resolution_scale=" + str(@"scale"));
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
  a.push_back("--nfsmw_native_present=" + b(On(s, @"native_renderer")));
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
@interface NFSLauncherController : UITableViewController <UITextFieldDelegate>
- (instancetype)initWithDocuments:(fs::path)docs done:(std::function<void(fs::path)>)done;
@end

@implementation NFSLauncherController {
  fs::path _docs;
  std::function<void(fs::path)> _done;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  std::vector<fs::path> _isos;
  NSString* _isoName;  // the chosen one's file name
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

// Section 0 is the ISO, 1 the achievements; the rest are Sections().
static constexpr NSInteger kFixedSections = 2;

- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return NSInteger(Sections().size()) + kFixedSections;
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  if (section == 0) {
    return std::max<NSInteger>(1, NSInteger(_isos.size()));
  }
  if (section == 1) {
    return 1;
  }
  return NSInteger(Sections()[size_t(section - kFixedSections)].options.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  return section == 0   ? @"ISO"
         : section == 1 ? @"Achievements"
                        : Sections()[size_t(section - kFixedSections)].title;
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  if (section == 0) {
    return _isos.empty()
               ? @"Copy your USA ISO into this app's folder (Files app › On My iPhone/iPad › "
                 @"NFSMW, or LiveContainer's folder for it). This screen looks again when you "
                 @"come back."
               : (_isos.size() > 1 ? @"Tap the one to play." : nil);
  }
  if (section == 1) {
    return nil;
  }
  if (section == NSInteger(Sections().size()) + kFixedSections - 1) {
    NSString* f = Sections().back().footer;
    return [f stringByAppendingString:
                  @"\n\nDocuments/extra_args.txt, if present, is applied after these settings "
                  @"and wins."];
  }
  return Sections()[size_t(section - kFixedSections)].footer;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                                 reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  c.textToSecondaryTextVerticalPadding = 4;

  if (ip.section == 0) {
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

  if (ip.section == 1) {
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

  const Option& o = Sections()[size_t(ip.section - kFixedSections)].options[size_t(ip.row)];
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
      //    otherwise off with MSAA (it does not exist with it);
      //  - the sharper 4:3 scene: only does something at 4:3.
      NSString* aspect = Value(_settings, @"aspect");
      const bool wide = [aspect isEqualToString:@"1560x720"];
      const bool four_three = [aspect isEqualToString:@"1024x768"] ||
                              [aspect isEqualToString:@"640x480"];
      bool locked = false;
      bool on = [value isEqualToString:@"true"];
      if ([key isEqualToString:@"one_pass"] && (wide || Msaa(_settings))) {
        locked = true;
        on = wide;
      } else if ([key isEqualToString:@"sd_720"] && !four_three) {
        locked = true;
      }
      sw.on = on;
      sw.enabled = !locked;
      cell.contentView.alpha = locked ? 0.45 : 1.0;
      [sw addAction:[UIAction actionWithHandler:^(UIAction*) {
            [self set:key to:sw.on ? @"true" : @"false"];
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
      cell.accessoryView = button;
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
  if (ip.section == 1) {
    Achievements a = LoadAchievements(_docs);
    if (a.loaded) {
      [self.navigationController
          pushViewController:[[NFSAchievementsController alloc] initWithAchievements:std::move(a)]
                    animated:YES];
    }
    return;
  }
  if (ip.section == 0 && size_t(ip.row) < _isos.size()) {
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
  UINavigationController* nav = [[UINavigationController alloc] initWithRootViewController:root];
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
  return chosen;
}

std::vector<std::string> SettingsArguments(const fs::path& documents) {
  return Arguments(LoadSettings(documents));
}

}  // namespace nfsmw::launcher
