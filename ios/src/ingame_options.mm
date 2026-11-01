// NFSMW Recompiled - the options menu while playing (iOS)
//
// Opened in menus and pause screens (game_state.cpp: battery::InMenu), where
// the game already waits: with the gear at the top right, or L3+R3 on a
// controller. A sheet over the game with the launcher's graphics settings
// (launcher.h: Rows), saved to the same Documents/settings.json.
//
// Most apply at once, through their cvars:
//   - render resolution and MetalFX: native_renderer.mm reads them again
//     (NativeSettingsChanged), as for 0.75x when hot;
//   - FXAA, shadow map drawing size, car reflections (rate and size): read
//     every frame;
//   - the HUD's size and positions, post-processing: game_scene_size.cpp,
//     every frame;
//   - all four fps caps, 30 fps when warm, 30 fps in menus, 0.75x when hot:
//     battery.mm (ChooseCap, SettingsChanged).
// Performance profiles also apply live, through performance::Choose.
// The Extra Options too (all but the Old Bridge barrier): the game reads them
// where it uses them, and the values in its data are written again
// (nfsmw_extra_options_tunables). Effects such as traffic or race limits show
// from the next race.
// The rest wait for the next launch: MSAA and what Battery mode reads once
// (anisotropic filtering, shadow quality...). Documents/extra_args.txt is
// not read here: a setting changed here wins over it until the next launch.
//
// While the sheet is up the game gets no controller or touch-pad input
// (BlocksGameInput, the input system's active callback in game_app.cpp),
// and after it closes none until every controller button is released, so the
// press that closed it does not reach the game. The controller works the
// sheet: D-pad up/down to choose a row, left/right (or A) to change it, B or
// L3+R3 to close.

#import <GameController/GameController.h>
#import <UIKit/UIKit.h>

#include <atomic>
#include <map>
#include <set>
#include <string>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "battery.h"
#include "performance_profile.h"
#include "ingame_options.h"
#include "launcher.h"
#include "hud_editor.h"
#include "touch_controls.h"

extern "C" void NativeSettingsChanged();  // native_renderer.mm
extern "C" void nfsmw_extra_options_tunables() __attribute__((weak));  // game_extra_options.cpp (USA)
extern "C" void nfsmw_heat_step_request(int32_t steps) __attribute__((weak));  // same
extern "C" void nfsmw_toggle_auto_drive() __attribute__((weak));               // same
extern "C" void nfsmw_reset_car_request() __attribute__((weak));               // same
extern "C" void nfsmw_open_debug_car_customize() __attribute__((weak));        // same
extern "C" void nfsmw_keyboard_reload() __attribute__((weak));                 // keyboard_prompts.mm
extern "C" void nfsmw_teleport_request(int32_t landmark) __attribute__((weak));  // same
extern "C" int32_t nfsmw_landmark_count() __attribute__((weak));               // same
extern "C" const char* nfsmw_landmark(int32_t i, const char** area) __attribute__((weak));

namespace {

std::atomic<bool> sheet_open{false};
NSString* const kHeatStep = @"heat_step";  // the Change heat row (not a setting)
NSString* const kAutoDrive = @"auto_drive";  // the Auto drive row (not a setting)
NSString* const kResetCar = @"reset_car";    // Reset car (not a setting)
NSString* const kTeleport = @"teleport";     // Teleport, a menu of places (not a setting)
NSString* const kDebugCustomize = @"debug_customize";  // Debug car customize (not a setting)
// Rows of the Actions tab: buttons (title, value) instead of a setting.
bool ActionRow(NSString* key) {
  return [key isEqualToString:kHeatStep] || [key isEqualToString:kAutoDrive] ||
         [key isEqualToString:kResetCar] || [key isEqualToString:kTeleport] ||
         [key isEqualToString:kDebugCustomize];
}
NSString* const kActionsTab = @"Actions";   // rows that do something now
NSInteger last_tab = 0;                     // the sheet's tab last time, while the game runs
std::atomic<bool> wait_release{false};  // closed: until the controller's buttons are up

NSArray<NSString*>* Keys() {
  return @[ @"scale", @"metalfx_mode", @"fps_cap", @"performance_mode", @"antialiasing", @"shadow_scale", @"reflection_rate",
            @"reflection_size", @"auto_cap", @"menu_cap", @"heat_scale", @"battery_mode", @"postprocessing", @"motion_blur", @"hud_custom",
            @"touch_steering", @"touch_idle_opacity", @"touch_menu_invert", @"touch_menu_empty_accept", @"touch_menu_two_finger_back", @"mouse_look_speed", @"mouse_look_invert", @"touch_look", @"touch_look_speed",
            // Extra Options (all live except the Old Bridge barrier, set when the world loads)
            @"infinite_nos", @"infinite_speedbreaker", @"sb_recharge_time", @"sb_recharge_speed", @"sb_mass",
            @"no_cops", @"show_non_pursuit_cops", @"heat_override", @"heat_min", @"heat_max", @"speeding_limit",
            @"excessive_speeding_limit", @"reckless_driving_limit", @"marker_count", @"car_limit",
            @"impound_strikes", @"impound_strikes_max", @"skip_movies", @"game_speed", @"unlock_all_things",
            @"skip_career_intro", @"world_animation_speed", @"nos_trail_repeat", @"no_rev_limiter", @"laps_min", @"laps_max",
            @"opponents_min", @"opponents_max", @"random_laps_max", @"random_opponents_max", @"traffic_low",
            @"traffic_medium", @"traffic_high", @"always_rain", @"rain_amount", @"rain_intensity", @"rain_drop_size",
            @"rain_crossing", @"rain_fall_speed", @"rain_gravity", @"road_reflection" ];
}

// The settings that only the native renderer has (left out without it).
bool NativeOnlyKey(NSString* key) {
  static NSSet* keys = [NSSet setWithArray:@[ @"scale", @"metalfx_mode", @"shadow_scale", @"reflection_rate",
                                              @"reflection_size", @"heat_scale", @"battery_mode" ]];
  return [keys containsObject:key];
}

// The cvars set while playing (the cap: battery::ChooseCap).
const std::set<std::string>& LiveFlags() {
  static const std::set<std::string> flags = {
      "nfsmw_native_resolution_scale", "nfsmw_native_metalfx",  "nfsmw_native_fxaa",
      "nfsmw_native_shadow_scale",     "nfsmw_native_half_rate_reflections", "nfsmw_native_scale_reflections",
      "nfsmw_battery_auto_cap",        "nfsmw_menu_cap",        "nfsmw_heat_scale",
      "nfsmw_sin_posprocesado",        "nfsmw_motion_blur",
      "nfsmw_hud_scale",               "nfsmw_hud_safe_zone",   "nfsmw_hud_left_x",      "nfsmw_hud_left_y",
      "nfsmw_hud_right_x",             "nfsmw_hud_right_y",     "nfsmw_hud_race_x",
      "nfsmw_hud_race_y",              "nfsmw_hud_layout",      "ios_touch_steering",
      "ios_touch_idle_opacity", "ios_touch_menu_invert", "ios_touch_menu_empty_accept", "ios_touch_menu_two_finger_back", "nfsmw_mouse_look_speed", "nfsmw_mouse_look_invert", "ios_touch_look", "ios_touch_look_speed",
      // Extra Options: read where the game uses them (game_extra_options.cpp);
      // the values in the game's data are written again by
      // nfsmw_extra_options_tunables().
      "nfsmw_infinite_nos", "nfsmw_infinite_speedbreaker", "nfsmw_sb_recharge_time", "nfsmw_sb_recharge_speed",
      "nfsmw_sb_mass", "nfsmw_no_cops", "nfsmw_show_non_pursuit_cops", "nfsmw_heat_override", "nfsmw_heat_min",
      "nfsmw_heat_max", "nfsmw_speeding_limit", "nfsmw_excessive_speeding_limit", "nfsmw_reckless_driving_limit",
      "nfsmw_marker_count", "nfsmw_purchased_car_limit", "nfsmw_impound_strikes", "nfsmw_impound_strikes_max",
      "nfsmw_skip_movies", "nfsmw_game_speed", "nfsmw_unlock_all_things", "nfsmw_skip_career_intro",
      "nfsmw_world_animation_speed", "nfsmw_nos_trail_repeat", "nfsmw_no_rev_limiter", "nfsmw_laps_min", "nfsmw_laps_max", "nfsmw_opponents_min",
      "nfsmw_opponents_max", "nfsmw_random_laps_max", "nfsmw_random_opponents_max", "nfsmw_traffic_low",
      "nfsmw_traffic_medium", "nfsmw_traffic_high", "nfsmw_always_rain", "nfsmw_rain_amount",
      "nfsmw_rain_intensity", "nfsmw_rain_drop_size", "nfsmw_rain_crossing", "nfsmw_rain_fall_speed",
      "nfsmw_rain_gravity", "nfsmw_road_reflection"};
  return flags;
}

bool LiveCap(NSString* fps) {
  return [fps isEqualToString:@"30"] || [fps isEqualToString:@"40"] ||
         [fps isEqualToString:@"60"] || [fps isEqualToString:@"120"];
}

std::pair<std::string, std::string> Split(const std::string& arg) {
  const size_t eq = arg.find('=');
  const size_t start = arg.rfind("--", 0) == 0 ? 2 : 0;
  if (eq == std::string::npos) return {arg.substr(start), "true"};
  return {arg.substr(start, eq - start), arg.substr(eq + 1)};
}

bool ControllerPressed(GCExtendedGamepad* p) {
  return p.buttonA.pressed || p.buttonB.pressed || p.buttonX.pressed || p.buttonY.pressed ||
         p.leftShoulder.pressed || p.rightShoulder.pressed || p.leftTrigger.pressed || p.rightTrigger.pressed ||
         p.leftThumbstickButton.pressed || p.rightThumbstickButton.pressed || p.dpad.up.pressed ||
         p.dpad.down.pressed || p.dpad.left.pressed || p.dpad.right.pressed || p.buttonMenu.pressed ||
         p.buttonOptions.pressed;
}

UIWindow* GameWindow() {
  UIWindow* window = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    if ([scene isKindOfClass:UIWindowScene.class] && ((UIWindowScene*)scene).screen == UIScreen.mainScreen) {
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if (w.isKeyWindow || !window) window = w;
      }
    }
  }
  return window;
}

}  // namespace

// ---------------------------------------------------------------------------
//  The sheet
// ---------------------------------------------------------------------------
@interface NFSInGameOptions : UITableViewController <UIAdaptivePresentationControllerDelegate>
- (void)controllerUp:(BOOL)up down:(BOOL)down left:(BOOL)left right:(BOOL)right a:(BOOL)a;
- (void)controllerTab:(NSInteger)step;
- (void)close;
@end

@implementation NFSInGameOptions {
  std::filesystem::path _docs;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  NSDictionary<NSString*, NSString*>* _launched;  // as the game started
  std::vector<nfsmw::launcher::MenuGroup> _groups;  // every tab's
  NSArray<NSString*>* _tabs;                         // their tab titles, in order
  NSInteger _tab;                                    // the tab shown
  std::vector<size_t> _visible;                      // _groups on that tab
  UISegmentedControl* _tabControl;
  NSInteger _focus;  // the controller's row, -1 until it is used
}

- (instancetype)init {
  if ((self = [super initWithStyle:UITableViewStyleInsetGrouped])) {
    _docs = nfsmw::launcher::Documents();
    _settings = nfsmw::launcher::ReadSettings(_docs);
    static NSDictionary<NSString*, NSString*>* launched;
    if (!launched) launched = [_settings copy];  // the first opening: nothing changed yet
    _launched = launched;
    const bool native = [nfsmw::launcher::SettingValue(_settings, @"native_renderer") isEqualToString:@"true"];
    for (auto& g : nfsmw::launcher::Groups(Keys())) {
      std::erase_if(g.rows, [&](const auto& r) { return !native && NativeOnlyKey(r.key); });
      if (!g.rows.empty()) _groups.push_back(std::move(g));
    }
    // Actions: not settings (nothing saved), things done to the game now.
    if (nfsmw_heat_step_request) {
      _groups.push_back({kActionsTab, @"Pursuit",
                         {{kHeatStep, @"Change heat",
                           @"One heat level down (−) or up (+) in the pursuit you are in. The event's own "
                           @"limits still apply unless Heat level override is on.",
                           false,
                           {{@"−", @"-1"}, {@"+", @"1"}}}}});
    }
    if (nfsmw_toggle_auto_drive && nfsmw_reset_car_request && nfsmw_teleport_request) {
      std::vector<std::pair<NSString*, NSString*>> places;  // "Area/Name", index
      for (int32_t i = 0; i < nfsmw_landmark_count(); ++i) {
        const char* area = "";
        const char* name = nfsmw_landmark(i, &area);
        places.emplace_back([NSString stringWithFormat:@"%s/%s", area, name], [NSString stringWithFormat:@"%d", i]);
      }
      _groups.push_back({kActionsTab, @"Driving",
                         {{kResetCar, @"Reset car",
                           @"Puts your car back on its wheels where it is (stuck or upside down), as the "
                           @"prototype's Flip Car.",
                           false,
                           {{@"Reset", @"1"}}},
                          {kTeleport, @"Teleport",
                           @"Moves your car to a place in the city, from the prototype's debug menu "
                           @"(Extra Options' hot positions do the same on PC). Free roam only.",
                           false,
                           places},
                          {kAutoDrive, @"Auto drive",
                           @"The AI drives your car until you press it again, as Extra Options' AutoDrive "
                           @"hotkey (the prototype's Toggle AI Control).",
                           false,
                           {{@"Toggle", @"1"}}}}});
    }
    // Debug car customize: off (dev11 still crashed from a Customize screen:
    // the debug screen takes its car from elsewhere; TECHNICAL, November 2).
    if ((false)) {
      _groups.push_back({kActionsTab, @"Garage",
                         {{kDebugCustomize, @"Debug car customize",
                           @"Opens the developers' car customize screen (every part, paint and vinyl), as "
                           @"Extra Options' ShowDebugCarCustomize. Only from the Customize screen of a "
                           @"car (safehouse or car lot): anywhere else nothing happens.",
                           false,
                           {{@"Open", @"1"}}}}});
    }
    NSMutableArray<NSString*>* tabs = [NSMutableArray array];
    for (const auto& g : _groups) {
      if (![tabs containsObject:g.tab]) [tabs addObject:g.tab];
    }
    _tabs = tabs;
    _focus = -1;
    [self showTab:std::min<NSInteger>(last_tab, NSInteger(_tabs.count) - 1)];
    _focus = -1;
    self.title = @"Options";
  }
  return self;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.navigationItem.rightBarButtonItem =
      [[UIBarButtonItem alloc] initWithBarButtonSystemItem:UIBarButtonSystemItemDone
                                                    target:self
                                                    action:@selector(close)];
  // The HUD editor (the launcher's Customize HUD), while Custom HUD is on.
  // And the touch controls' editor (Stefan, Oct 29).
  self.navigationItem.leftBarButtonItems = @[
    [[UIBarButtonItem alloc] initWithTitle:@"Customize HUD"
                                     style:UIBarButtonItemStylePlain
                                    target:self
                                    action:@selector(customizeHud)],
    [[UIBarButtonItem alloc] initWithTitle:@"Touch controls"
                                     style:UIBarButtonItemStylePlain
                                    target:self
                                    action:@selector(customizeTouch)],
    // The keyboard's keys (both sets), applied at once (Stefan, November 2).
    [[UIBarButtonItem alloc] initWithTitle:@"Keyboard"
                                     style:UIBarButtonItemStylePlain
                                    target:self
                                    action:@selector(customizeKeyboard)]
  ];
  _tabControl = [[UISegmentedControl alloc] initWithItems:_tabs];
  _tabControl.selectedSegmentIndex = _tab;
  [_tabControl addAction:[UIAction actionWithHandler:^(UIAction*) {
                  [self showTab:self->_tabControl.selectedSegmentIndex];
                }]
        forControlEvents:UIControlEventValueChanged];
  UIView* header = [[UIView alloc] initWithFrame:CGRectMake(0, 0, 0, 52)];
  _tabControl.translatesAutoresizingMaskIntoConstraints = NO;
  [header addSubview:_tabControl];
  [NSLayoutConstraint activateConstraints:@[
    [_tabControl.centerXAnchor constraintEqualToAnchor:header.centerXAnchor],
    [_tabControl.centerYAnchor constraintEqualToAnchor:header.centerYAnchor],
    [_tabControl.leadingAnchor constraintGreaterThanOrEqualToAnchor:header.leadingAnchor constant:16]
  ]];
  self.tableView.tableHeaderView = header;
  [self updateHudButton];
}

// Tabs as the launcher's (Extras, Graphics, Controls) plus Actions; groups
// as its sections. Controller: L1/R1 change the tab.
- (void)showTab:(NSInteger)tab {
  if (_tabs.count == 0) return;
  _tab = (tab + NSInteger(_tabs.count)) % NSInteger(_tabs.count);
  last_tab = _tab;
  _visible.clear();
  for (size_t i = 0; i < _groups.size(); ++i) {
    if ([_groups[i].tab isEqualToString:_tabs[size_t(_tab)]]) _visible.push_back(i);
  }
  _tabControl.selectedSegmentIndex = _tab;
  _focus = _focus < 0 ? -1 : 0;
  [self.tableView reloadData];
  [self showFocus];
}

- (const nfsmw::launcher::MenuRow&)rowAt:(NSIndexPath*)ip {
  return _groups[_visible[size_t(ip.section)]].rows[size_t(ip.row)];
}

// The controller's row (counted over the tab's groups) as an index path.
- (NSIndexPath*)focusPath {
  NSInteger n = _focus;
  for (size_t s = 0; s < _visible.size(); ++s) {
    const NSInteger rows = NSInteger(_groups[_visible[s]].rows.size());
    if (n < rows) return [NSIndexPath indexPathForRow:n inSection:NSInteger(s)];
    n -= rows;
  }
  return nil;
}

- (NSInteger)rowCount {
  NSInteger n = 0;
  for (size_t i : _visible) n += NSInteger(_groups[i].rows.size());
  return n;
}

- (void)updateHudButton {
  self.navigationItem.leftBarButtonItem.enabled =
      [nfsmw::launcher::SettingValue(_settings, @"hud_custom") isEqualToString:@"true"];
}

- (void)customizeKeyboard {
  __weak NFSInGameOptions* weak = self;
  UIViewController* editor = nfsmw::launcher::MakeKeyBindsEditor(_settings, ^{
    NFSInGameOptions* me = weak;
    if (!me) return;
    nfsmw::launcher::WriteSettings(me->_docs, me->_settings);
    if (nfsmw_keyboard_reload) nfsmw_keyboard_reload();
  });
  [self.navigationController pushViewController:editor animated:YES];
}

- (void)customizeTouch {
  [self presentViewController:nfsmw::touch::MakeLayoutEditor(nfsmw::launcher::SettingValue(_settings, @"touch_steering"))
                     animated:YES
                   completion:nil];
}

- (void)customizeHud {
  [self presentViewController:nfsmw::hud::MakeEditor(_settings, ^{ [self apply]; }) animated:YES completion:nil];
}

- (void)close {
  [self.navigationController dismissViewControllerAnimated:YES completion:nil];
  [self closed];
}

- (void)closed {
  wait_release = true;
  sheet_open = false;
  REXLOG_INFO("[options] closed");
}

- (void)presentationControllerDidDismiss:(UIPresentationController*)presentationController {
  [self closed];
}

// The row's setting needs a restart to change from the value the game
// started with.
- (BOOL)waitsForLaunch:(NSString*)key {
  NSString* now = nfsmw::launcher::SettingValue(_settings, key);
  NSString* then = nfsmw::launcher::SettingValue(_launched, key);
  if ([now isEqualToString:then]) return NO;
  if ([key isEqualToString:@"fps_cap"]) return !LiveCap(now) || !LiveCap(then);
  if ([key isEqualToString:@"antialiasing"]) {
    const bool native = [nfsmw::launcher::SettingValue(_settings, @"native_renderer") isEqualToString:@"true"];
    return !native || [now hasPrefix:@"msaa"] || [then hasPrefix:@"msaa"];
  }
  return NO;
}

// Anything set at launch only that differs from then (Battery mode also
// sets some of those).
- (BOOL)anythingWaits {
  const std::vector<std::string> now = nfsmw::launcher::ArgumentsFor(_settings);
  const std::vector<std::string> then = nfsmw::launcher::ArgumentsFor(_launched);
  const bool native = [nfsmw::launcher::SettingValue(_settings, @"native_renderer") isEqualToString:@"true"];
  const bool live_cap = LiveCap(nfsmw::launcher::SettingValue(_settings, @"fps_cap")) &&
                        LiveCap(nfsmw::launcher::SettingValue(_launched, @"fps_cap"));
  std::map<std::string, std::string> before;
  for (const auto& a : then) before.insert(Split(a));
  for (const auto& a : now) {
    const auto [name, value] = Split(a);
    if (LiveFlags().count(name) || (live_cap && name == "ios_fps_cap") ||
        name == "nfsmw_performance_mode" || name == "nfsmw_performance_source") continue;
    if (native && name == "swap_post_effect") continue;  // the emulated renderer's FXAA
    if (before[name] != value) return YES;
  }
  return NO;
}

- (void)apply {
  nfsmw::launcher::WriteSettings(_docs, _settings);
  const bool native = [nfsmw::launcher::SettingValue(_settings, @"native_renderer") isEqualToString:@"true"];
  for (const auto& a : nfsmw::launcher::ArgumentsFor(_settings)) {
    const auto [name, value] = Split(a);
    if (!LiveFlags().count(name) || (!native && name.rfind("nfsmw_native_", 0) == 0)) continue;
    if (rex::cvar::GetFlagByName(name) == value) continue;
    rex::cvar::SetFlagByName(name, value);
    REXLOG_INFO("[options] {} = {}", name, value);
  }
  NativeSettingsChanged();
  if (nfsmw_extra_options_tunables) nfsmw_extra_options_tunables();
  NSString* fps = nfsmw::launcher::SettingValue(_settings, @"fps_cap");
  if (LiveCap(fps) && LiveCap(nfsmw::launcher::SettingValue(_launched, @"fps_cap"))) {
    nfsmw::battery::ChooseCap(fps.intValue);
  }
  nfsmw::battery::SettingsChanged();
}

- (void)set:(NSString*)key to:(NSString*)value {
  if ([key isEqualToString:kHeatStep]) {
    if (value.intValue != 0) nfsmw_heat_step_request(value.intValue);
    return;
  }
  if ([key isEqualToString:kAutoDrive]) {
    nfsmw_toggle_auto_drive();
    return;
  }
  if ([key isEqualToString:kResetCar]) {
    nfsmw_reset_car_request();
    return;
  }
  if ([key isEqualToString:kDebugCustomize]) {
    nfsmw_open_debug_car_customize();
    [self close];  // the screen opens under the sheet otherwise
    return;
  }
  if ([key isEqualToString:kTeleport]) {
    nfsmw_teleport_request(value.intValue);
    return;
  }
  _settings[key] = value;
  if ([key isEqualToString:@"performance_mode"] || [key isEqualToString:@"battery_mode"]) {
    nfsmw::performance::Choose(std::string(nfsmw::launcher::SettingValue(_settings, @"performance_mode").UTF8String));
  }
  [self apply];
  [self updateHudButton];
  [self.tableView reloadData];
  [self showFocus];
}

- (BOOL)locked:(const nfsmw::launcher::MenuRow&)r {
  return nfsmw::launcher::SetByBatteryMode(_settings, r.key) || nfsmw::launcher::HudLocked(_settings, r.key);
}

- (NSInteger)numberOfSectionsInTableView:(UITableView*)tableView {
  return NSInteger(_visible.size());
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(_groups[_visible[size_t(section)]].rows.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForHeaderInSection:(NSInteger)section {
  return _groups[_visible[size_t(section)]].title;
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  if (section + 1 < NSInteger(_visible.size())) return nil;  // under the last group only
  NSString* text = @"Changes apply at once and are saved for the next launch too.";
  if ([self anythingWaits]) {
    text = [text stringByAppendingString:@" Those marked \"next launch\" (and some that Battery mode sets) "
                                         @"take effect the next time the game starts."];
  }
  if (GCController.current) {
    text = [text stringByAppendingString:@"\nController: D-pad to choose and change, L1/R1 for the tabs, B or "
                                         @"L3+R3 to close."];
  }
  return text;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const nfsmw::launcher::MenuRow& r = [self rowAt:ip];
  UITableViewCell* cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault reuseIdentifier:nil];
  UIListContentConfiguration* c = UIListContentConfiguration.subtitleCellConfiguration;
  c.secondaryTextProperties.color = UIColor.secondaryLabelColor;
  c.secondaryTextProperties.numberOfLines = 0;
  const bool locked = [self locked:r];
  NSString* value = nfsmw::launcher::SettingValue(_settings, r.key);
  c.text = [self waitsForLaunch:r.key] ? [r.title stringByAppendingString:@" · next launch"] : r.title;
  c.secondaryText = !locked ? r.summary
                    : nfsmw::launcher::HudLocked(_settings, r.key)
                        ? [@"Turn on Custom HUD to change. " stringByAppendingString:r.summary]
                        : [@"Set by Battery mode. " stringByAppendingString:r.summary];
  cell.contentConfiguration = c;
  cell.contentView.alpha = locked ? 0.45 : 1.0;
  NSString* key = r.key;
  if ([key isEqualToString:kTeleport]) {
    // A menu of places, by area.
    NSMutableDictionary<NSString*, NSMutableArray<UIMenuElement*>*>* areas = [NSMutableDictionary dictionary];
    NSMutableArray<NSString*>* order = [NSMutableArray array];
    for (const auto& [title, v] : r.choices) {
      NSArray<NSString*>* parts = [title componentsSeparatedByString:@"/"];
      NSString* place = v;
      if (!areas[parts[0]]) {
        areas[parts[0]] = [NSMutableArray array];
        [order addObject:parts[0]];
      }
      [areas[parts[0]] addObject:[UIAction actionWithTitle:parts.lastObject
                                                     image:nil
                                                identifier:nil
                                                   handler:^(UIAction*) { [self set:key to:place]; }]];
    }
    NSMutableArray<UIMenuElement*>* menus = [NSMutableArray array];
    for (NSString* area in order) [menus addObject:[UIMenu menuWithTitle:area children:areas[area]]];
    UIButtonConfiguration* bc = UIButtonConfiguration.tintedButtonConfiguration;
    bc.title = @"Choose";
    UIButton* button = [UIButton buttonWithConfiguration:bc primaryAction:nil];
    button.menu = [UIMenu menuWithChildren:menus];
    button.showsMenuAsPrimaryAction = YES;
    [button sizeToFit];
    cell.accessoryView = button;
    return cell;
  }
  if (ActionRow(key)) {
    // Buttons, not a list: each press does it once.
    UIStackView* buttons = [[UIStackView alloc] init];
    buttons.spacing = 8;
    for (const auto& [title, v] : r.choices) {
      NSString* step = v;
      UIButtonConfiguration* bc = UIButtonConfiguration.tintedButtonConfiguration;
      bc.title = title;
      bc.contentInsets = NSDirectionalEdgeInsetsMake(6, 18, 6, 18);
      UIButton* b = [UIButton buttonWithConfiguration:bc
                                        primaryAction:[UIAction actionWithHandler:^(UIAction*) {
                                          [self set:key to:step];
                                        }]];
      [buttons addArrangedSubview:b];
    }
    const CGSize size = [buttons systemLayoutSizeFittingSize:UILayoutFittingCompressedSize];
    buttons.frame = CGRectMake(0, 0, size.width, size.height);
    cell.accessoryView = buttons;
    cell.selectionStyle = UITableViewCellSelectionStyleDefault;
    return cell;
  }
  if (r.is_switch) {
    UISwitch* sw = [[UISwitch alloc] init];
    sw.on = [value isEqualToString:@"true"];
    sw.enabled = !locked;
    [sw addAction:[UIAction actionWithHandler:^(UIAction*) {
          [self set:key to:sw.on ? @"true" : @"false"];
        }]
        forControlEvents:UIControlEventValueChanged];
    cell.accessoryView = sw;
  } else {
    NSMutableArray<UIMenuElement*>* items = [NSMutableArray array];
    for (const auto& [title, v] : r.choices) {
      NSString* choice = v;
      UIAction* item = [UIAction actionWithTitle:title
                                           image:nil
                                      identifier:nil
                                         handler:^(UIAction*) { [self set:key to:choice]; }];
      item.state = [choice isEqualToString:value] ? UIMenuElementStateOn : UIMenuElementStateOff;
      [items addObject:item];
    }
    UIButtonConfiguration* bc = UIButtonConfiguration.tintedButtonConfiguration;
    bc.indicator = UIButtonConfigurationIndicatorPopup;
    UIButton* button = [UIButton buttonWithConfiguration:bc primaryAction:nil];
    button.menu = [UIMenu menuWithChildren:items];
    button.showsMenuAsPrimaryAction = YES;
    button.changesSelectionAsPrimaryAction = YES;
    [button sizeToFit];
    button.enabled = !locked;
    cell.accessoryView = button;
  }
  cell.selectionStyle = UITableViewCellSelectionStyleDefault;
  return cell;
}

- (NSIndexPath*)tableView:(UITableView*)tableView willSelectRowAtIndexPath:(NSIndexPath*)ip {
  return nil;  // touches go to the switch or the menu
}

- (void)showFocus {
  NSIndexPath* ip = _focus < 0 ? nil : [self focusPath];
  if (!ip) return;
  [self.tableView selectRowAtIndexPath:ip animated:NO scrollPosition:UITableViewScrollPositionNone];
  [self.tableView scrollToRowAtIndexPath:ip atScrollPosition:UITableViewScrollPositionNone animated:YES];
}

// One step of the controller (each press once).
- (void)controllerTab:(NSInteger)step {
  [self showTab:_tab + step];
}

- (void)controllerUp:(BOOL)up down:(BOOL)down left:(BOOL)left right:(BOOL)right a:(BOOL)a {
  const NSInteger n = [self rowCount];
  if (n == 0) return;
  if (_focus < 0) {
    _focus = 0;
  } else if (up || down) {
    _focus = (_focus + (down ? 1 : n - 1)) % n;
  } else if (left || right || a) {
    const nfsmw::launcher::MenuRow& r = [self rowAt:[self focusPath]];
    if ([self locked:r]) return;
    if ([r.key isEqualToString:kHeatStep]) {
      if (left || right) [self set:r.key to:left ? @"-1" : @"1"];
      return;
    }
    if (ActionRow(r.key)) {
      if (a && ![r.key isEqualToString:kTeleport]) [self set:r.key to:r.choices.front().second];
      return;
    }
    NSString* value = nfsmw::launcher::SettingValue(_settings, r.key);
    if (r.is_switch) {
      [self set:r.key to:[value isEqualToString:@"true"] ? @"false" : @"true"];
      return;
    }
    const NSInteger count = NSInteger(r.choices.size());
    NSInteger i = 0;
    while (i < count && ![r.choices[size_t(i)].second isEqualToString:value]) ++i;
    i = i == count ? 0 : (i + (left ? count - 1 : 1)) % count;
    [self set:r.key to:r.choices[size_t(i)].second];
    return;
  }
  [self showFocus];
}

@end

// The navigation around the sheet: landscape, as the game.
@interface NFSInGameOptionsNavigation : UINavigationController
@end

@implementation NFSInGameOptionsNavigation
- (UIInterfaceOrientationMask)supportedInterfaceOrientations {
  return UIInterfaceOrientationMaskLandscape;
}
@end

// ---------------------------------------------------------------------------
//  The gear and the controller
// ---------------------------------------------------------------------------
@interface NFSInGameOptionsOpener : NSObject
@end

@implementation NFSInGameOptionsOpener {
  UIButton* _gear;
  __weak NFSInGameOptions* _sheet;
  NSTimer* _timer;
  BOOL _combo, _up, _down, _left, _right, _a, _b, _l1, _r1;  // last state, for presses
}

- (instancetype)initInWindow:(UIWindow*)window {
  if ((self = [super init])) {
    UIButtonConfiguration* bc = UIButtonConfiguration.grayButtonConfiguration;
    bc.image = [UIImage systemImageNamed:@"gearshape.fill"];
    bc.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
    _gear = [NFSUnfocusableButton buttonWithConfiguration:bc
                                primaryAction:[UIAction actionWithHandler:^(UIAction*) { [self open]; }]];
    _gear.translatesAutoresizingMaskIntoConstraints = NO;
    _gear.alpha = 0.8;
    _gear.hidden = YES;
    _gear.accessibilityLabel = @"Options";
    [window addSubview:_gear];
    UILayoutGuide* safe = window.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
      [_gear.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],
      [_gear.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-8],
      [_gear.widthAnchor constraintEqualToConstant:44], [_gear.heightAnchor constraintEqualToConstant:44]
    ]];
    [self schedule:0.1];
  }
  return self;
}

// 10 times a second; 30 while the sheet is up (controller presses).
- (void)schedule:(NSTimeInterval)interval {
  if (_timer && _timer.timeInterval == interval) return;
  [_timer invalidate];
  __weak NFSInGameOptionsOpener* weak = self;
  _timer = [NSTimer scheduledTimerWithTimeInterval:interval
                                           repeats:YES
                                             block:^(NSTimer*) { [weak tick]; }];
}

- (void)open {
  if (sheet_open || nfsmw::battery::InMenu() != 1) return;
  UIViewController* top = _gear.window.rootViewController;
  while (top.presentedViewController) top = top.presentedViewController;
  if (!top) return;
  NFSInGameOptions* sheet = [[NFSInGameOptions alloc] init];
  NFSInGameOptionsNavigation* nav = [[NFSInGameOptionsNavigation alloc] initWithRootViewController:sheet];
  nav.modalPresentationStyle = UIModalPresentationFormSheet;
  nav.presentationController.delegate = sheet;
  sheet_open = true;
  _sheet = sheet;
  [top presentViewController:nav animated:YES completion:nil];
  REXLOG_INFO("[options] open");
}

- (void)tick {
  GCExtendedGamepad* pad = GCController.current.extendedGamepad;
  const BOOL combo = pad && pad.leftThumbstickButton.pressed && pad.rightThumbstickButton.pressed;
  const BOOL pressed_combo = combo && !_combo;
  _combo = combo;
  if (wait_release && !(pad && ControllerPressed(pad))) wait_release = false;
  _gear.hidden = sheet_open || nfsmw::battery::InMenu() != 1;
  if (!sheet_open) {
    [self schedule:0.1];
    if (pressed_combo) [self open];
    return;
  }
  [self schedule:1.0 / 30];
  NFSInGameOptions* sheet = _sheet;
  if (!pad || !sheet) return;
  const BOOL up = pad.dpad.up.pressed, down = pad.dpad.down.pressed;
  const BOOL left = pad.dpad.left.pressed, right = pad.dpad.right.pressed;
  const BOOL a = pad.buttonA.pressed, b = pad.buttonB.pressed;
  const BOOL l1 = pad.leftShoulder.pressed, r1 = pad.rightShoulder.pressed;
  if ((b && !_b) || pressed_combo) {
    [sheet close];
  } else if ((l1 && !_l1) || (r1 && !_r1)) {
    [sheet controllerTab:l1 && !_l1 ? -1 : 1];
  } else if ((up && !_up) || (down && !_down) || (left && !_left) || (right && !_right) || (a && !_a)) {
    [sheet controllerUp:up && !_up down:down && !_down left:left && !_left right:right && !_right a:a && !_a];
  }
  _up = up, _down = down, _left = left, _right = right, _a = a, _b = b, _l1 = l1, _r1 = r1;
}

@end

namespace nfsmw::options {

void Install() {
  static NFSInGameOptionsOpener* opener;
  if (opener) return;
  UIWindow* window = GameWindow();
  if (!window) {
    REXLOG_ERROR("[options] no window for the options button");
    return;
  }
  opener = [[NFSInGameOptionsOpener alloc] initInWindow:window];
  REXLOG_INFO("[options] gear in menus and pause screens, or L3+R3");
}

bool BlocksGameInput() { return sheet_open.load(std::memory_order_relaxed) || wait_release.load(std::memory_order_relaxed); }

}  // namespace nfsmw::options
