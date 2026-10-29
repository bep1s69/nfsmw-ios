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
//   - the 30/60 fps cap, 30 fps when warm, 30 fps in menus, 0.75x when hot:
//     battery.mm (ChooseCap, SettingsChanged).
// The rest wait for the next launch, and the sheet says so: 40/120 fps (or
// from them: they change the console's screen refresh and the threads'
// priorities at launch), MSAA, and what Battery mode sets that is read once
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
#include "ingame_options.h"
#include "launcher.h"
#include "hud_editor.h"

extern "C" void NativeSettingsChanged();  // native_renderer.mm

namespace {

std::atomic<bool> sheet_open{false};
std::atomic<bool> wait_release{false};  // closed: until the controller's buttons are up

NSArray<NSString*>* Keys() {
  return @[ @"scale", @"metalfx_mode", @"fps_cap", @"antialiasing", @"shadow_scale", @"reflection_rate",
            @"reflection_size", @"auto_cap", @"menu_cap", @"heat_scale", @"battery_mode", @"postprocessing", @"motion_blur", @"hud_custom",
            @"touch_steering", @"touch_idle_opacity" ];
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
      "ios_touch_idle_opacity"};
  return flags;
}

bool LiveCap(NSString* fps) { return [fps isEqualToString:@"30"] || [fps isEqualToString:@"60"]; }

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
- (void)close;
@end

@implementation NFSInGameOptions {
  std::filesystem::path _docs;
  NSMutableDictionary<NSString*, NSString*>* _settings;
  NSDictionary<NSString*, NSString*>* _launched;  // as the game started
  std::vector<nfsmw::launcher::MenuRow> _rows;
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
    for (auto& r : nfsmw::launcher::Rows(Keys())) {
      if (native || !NativeOnlyKey(r.key)) _rows.push_back(r);
    }
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
  self.navigationItem.leftBarButtonItem = [[UIBarButtonItem alloc] initWithTitle:@"Customize HUD"
                                                                           style:UIBarButtonItemStylePlain
                                                                          target:self
                                                                          action:@selector(customizeHud)];
  [self updateHudButton];
}

- (void)updateHudButton {
  self.navigationItem.leftBarButtonItem.enabled =
      [nfsmw::launcher::SettingValue(_settings, @"hud_custom") isEqualToString:@"true"];
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
    if (LiveFlags().count(name) || (live_cap && name == "ios_fps_cap")) continue;
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
  NSString* fps = nfsmw::launcher::SettingValue(_settings, @"fps_cap");
  if (LiveCap(fps) && LiveCap(nfsmw::launcher::SettingValue(_launched, @"fps_cap"))) {
    nfsmw::battery::ChooseCap(fps.intValue);
  }
  nfsmw::battery::SettingsChanged();
}

- (void)set:(NSString*)key to:(NSString*)value {
  _settings[key] = value;
  [self apply];
  [self updateHudButton];
  [self.tableView reloadData];
  [self showFocus];
}

- (BOOL)locked:(const nfsmw::launcher::MenuRow&)r {
  return nfsmw::launcher::SetByBatteryMode(_settings, r.key) || nfsmw::launcher::HudLocked(_settings, r.key);
}

- (NSInteger)tableView:(UITableView*)tableView numberOfRowsInSection:(NSInteger)section {
  return NSInteger(_rows.size());
}

- (NSString*)tableView:(UITableView*)tableView titleForFooterInSection:(NSInteger)section {
  NSString* text = @"Changes apply at once and are saved for the next launch too.";
  if ([self anythingWaits]) {
    text = [text stringByAppendingString:@" Those marked \"next launch\" (and some that Battery mode sets) "
                                         @"take effect the next time the game starts."];
  }
  if (GCController.current) {
    text = [text stringByAppendingString:@"\nController: D-pad to choose and change, B or L3+R3 to close."];
  }
  return text;
}

- (UITableViewCell*)tableView:(UITableView*)tableView cellForRowAtIndexPath:(NSIndexPath*)ip {
  const nfsmw::launcher::MenuRow& r = _rows[size_t(ip.row)];
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
  if (_focus < 0 || _focus >= NSInteger(_rows.size())) return;
  NSIndexPath* ip = [NSIndexPath indexPathForRow:_focus inSection:0];
  [self.tableView selectRowAtIndexPath:ip animated:NO scrollPosition:UITableViewScrollPositionNone];
  [self.tableView scrollToRowAtIndexPath:ip atScrollPosition:UITableViewScrollPositionNone animated:YES];
}

// One step of the controller (each press once).
- (void)controllerUp:(BOOL)up down:(BOOL)down left:(BOOL)left right:(BOOL)right a:(BOOL)a {
  const NSInteger n = NSInteger(_rows.size());
  if (n == 0) return;
  if (_focus < 0) {
    _focus = 0;
  } else if (up || down) {
    _focus = (_focus + (down ? 1 : n - 1)) % n;
  } else if (left || right || a) {
    const nfsmw::launcher::MenuRow& r = _rows[size_t(_focus)];
    if ([self locked:r]) return;
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
  BOOL _combo, _up, _down, _left, _right, _a, _b;  // last state, for presses
}

- (instancetype)initInWindow:(UIWindow*)window {
  if ((self = [super init])) {
    UIButtonConfiguration* bc = UIButtonConfiguration.grayButtonConfiguration;
    bc.image = [UIImage systemImageNamed:@"gearshape.fill"];
    bc.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
    _gear = [UIButton buttonWithConfiguration:bc
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
  if ((b && !_b) || pressed_combo) {
    [sheet close];
  } else if ((up && !_up) || (down && !_down) || (left && !_left) || (right && !_right) || (a && !_a)) {
    [sheet controllerUp:up && !_up down:down && !_down left:left && !_left right:right && !_right a:a && !_a];
  }
  _up = up, _down = down, _left = left, _right = right, _a = a, _b = b;
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
