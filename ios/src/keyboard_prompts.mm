// NFSMW Recompiled (iOS) - keyboard key prompts over the menu's button hints
//
// The Xbox 360 game draws controller icons (A, B, X, Y, LB...) as its hints;
// neither its disc nor the PC's has art for most keys (the PC has 11 key
// textures and writes the rest as text; BACKLOG, November 1). So while the
// keyboard is the last thing used, each hint icon gets a key cap drawn over
// it with the menu key that presses it (keyboard_context.cpp's menu set).
//
// Last device wins (Stefan, November 1): a key press shows the caps, a
// controller button or a touch hides them. Polled 20 times a second on the
// main thread (GCKeyboard / GCController state, the touch count of
// touch_controls.mm), so nothing else's input handler is replaced.
//
// The hints come from the touch scan (game_scene_size.cpp,
// nfsmw_menu_hints_list), in the packages' units: 480 tall from the middle of
// the screen (measured on the dev15 screenshots; the menu taps use 480 / 0.92).

#import <GameController/GameController.h>
#import <UIKit/UIKit.h>

#include <atomic>
#include <mutex>
#include <string>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "app_scene.h"
#include "battery.h"
#include "keyboard_context.h"
#include "launcher.h"
#include "menu_touch_policy.h"
#include "touch_controls.h"

REXCVAR_DECLARE(bool, mnk_mode);

extern "C" void nfsmw_look_mouse(float dx, float dy) __attribute__((weak));  // camera_look.cpp
extern "C" void nfsmw_showcase_zoom(float factor) __attribute__((weak));  // same
extern "C" void nfsmw_reset_car_request() __attribute__((weak));        // game_extra_options.cpp
extern "C" void nfsmw_toggle_auto_drive() __attribute__((weak));        // same
extern "C" void nfsmw_heat_step_request(int32_t steps) __attribute__((weak));  // same

namespace {

std::atomic<bool> wanted{false};

// ACTION KEYS (launcher ActionBinds: 1 reset car, 2 auto drive, 3/4 heat
// -1/+1 by default), only while driving. Polled with the prompts' timer:
// GameController's keyChangedHandler is SDL's (SDL_uikitevents.m), and
// replacing it took every key away from the game (dev21, Stefan).
std::vector<std::pair<GCKeyCode, std::string>> action_codes;  // key -> action
std::vector<bool> action_down;

void LoadActionKeys() {
  NSMutableDictionary<NSString*, NSString*>* map = [NSMutableDictionary dictionary];
  const std::string list = nfsmw::launcher::ActionKeyBinds();
  for (NSString* item in [[NSString stringWithUTF8String:list.c_str()] componentsSeparatedByString:@";"]) {
    NSArray<NSString*>* kv = [item componentsSeparatedByString:@"="];
    if (kv.count != 2) continue;
    for (NSString* key in [kv[1] componentsSeparatedByString:@","]) {
      if (key.length) map[key] = kv[0];
    }
  }
  action_codes.clear();
  for (long code = 4; code <= 231; ++code) {  // the HID keyboard page
    NSString* action = map[nfsmw::launcher::KeyNameForHID(code)];
    if (action) action_codes.emplace_back(GCKeyCode(code), action.UTF8String);
  }
  action_down.assign(action_codes.size(), false);
}

void RunAction(const std::string& action) {
  REXLOG_INFO("[keyboard] action key: {}", action);
  if (action == "action_reset_car" && nfsmw_reset_car_request) nfsmw_reset_car_request();
  if (action == "action_auto_drive" && nfsmw_toggle_auto_drive) nfsmw_toggle_auto_drive();
  if (action == "action_heat_down" && nfsmw_heat_step_request) nfsmw_heat_step_request(-1);
  if (action == "action_heat_up" && nfsmw_heat_step_request) nfsmw_heat_step_request(1);
}

// MOUSE LOOK (camera_look.cpp): GameController's mouse handler is SDL's too
// (SDL_uikitevents.m OnGCMouseConnected), so ours is chained after it, never
// in its place; SDL sets it again on a reconnect, so it is chained again
// shortly after each one.
void ChainMouse(GCMouse* mouse) {
  GCMouseInput* input = mouse.mouseInput;
  if (!input || !nfsmw_look_mouse) return;
  static void* chained = nullptr;  // the handler we installed last
  GCMouseMoved current = input.mouseMovedHandler;
  if (current && (__bridge void*)current == chained) return;
  GCMouseMoved ours = ^(GCMouseInput* in, float dx, float dy) {
    if (current) current(in, dx, dy);
    // Showcase's left-drag needs nothing here: iPadOS delivers mouse clicks
    // and drags as touches, which turn the car already (touch_controls.mm);
    // adding the deltas too would turn it twice.
    if (nfsmw::battery::InMenu() == 0) nfsmw_look_mouse(dx, dy);
  };
  input.mouseMovedHandler = ours;
  chained = (__bridge void*)input.mouseMovedHandler;
  // The wheel zooms in Showcase; SDL's scroll handler is kept and called first.
  GCControllerDirectionPad* scroll = input.scroll;
  GCControllerDirectionPadValueChangedHandler scroll_current = scroll.valueChangedHandler;
  scroll.valueChangedHandler = ^(GCControllerDirectionPad* pad, float x, float y) {
    if (scroll_current) scroll_current(pad, x, y);
    if (nfsmw::touch::ShowcaseUp() && nfsmw_showcase_zoom && y != 0) nfsmw_showcase_zoom(y > 0 ? 0.92f : 1.08f);
  };
  REXLOG_INFO("[keyboard] mouse look attached{}", current ? " (after SDL's handler)" : "");
}

void WatchMice() {
  for (GCMouse* m in GCMouse.mice) ChainMouse(m);
  [NSNotificationCenter.defaultCenter addObserverForName:GCMouseDidConnectNotification
                                                  object:nil
                                                   queue:NSOperationQueue.mainQueue
                                              usingBlock:^(NSNotification* n) {
                                                GCMouse* m = n.object;
                                                // After SDL's own observer set its handler.
                                                dispatch_after(dispatch_time(DISPATCH_TIME_NOW, NSEC_PER_SEC / 2),
                                                               dispatch_get_main_queue(), ^{ ChainMouse(m); });
                                              }];
}

void PollActionKeys(GCKeyboardInput* input) {
  for (size_t i = 0; i < action_codes.size(); ++i) {
    const bool down = input && [input buttonForKeyCode:action_codes[i].first].pressed;
    if (down && !action_down[i] && nfsmw::battery::InMenu() == 0) RunAction(action_codes[i].second);
    action_down[i] = down;
  }
}
std::mutex hints_mutex;
std::vector<float> hints;  // 5 floats each
int hints_serial = 0;

// A hint's button bits -> the bind that presses it in menus.
const char* BindFor(int button) {
  using namespace nfsmw::menu_touch;
  switch (button) {
    case 1: return "keybind_a";
    case 2: return "keybind_b";
    case 4: return "keybind_x";
    case 8: return "keybind_y";
    case 1 << 6: return "keybind_start";
    case 1 << 9: return "keybind_left_shoulder";
    case 1 << 10: return "keybind_right_shoulder";
    case LT: return "keybind_left_trigger";
    case RT: return "keybind_right_trigger";
    case Left: return "keybind_lstick_left";
    case Right: return "keybind_lstick_right";
    case Up: return "keybind_lstick_up";
    case Down: return "keybind_lstick_down";
    default: return nullptr;
  }
}

NSString* Caption(const std::string& key) {
  static NSDictionary<NSString*, NSString*>* names = @{
    @"Return" : @"↵", @"Escape" : @"Esc", @"Backspace" : @"⌫", @"Space" : @"␣", @"Tab" : @"⇥",
    @"Shift" : @"⇧", @"Alt" : @"⌥",
    @"Left" : @"←", @"Right" : @"→", @"Up" : @"↑", @"Down" : @"↓", @"LBracket" : @"[",
    @"RBracket" : @"]", @"PageUp" : @"PgUp", @"PageDown" : @"PgDn", @"Control" : @"⌃",
    @"NumpadEnter" : @"↵", @"Minus" : @"-", @"Plus" : @"=", @"Comma" : @",",
    @"Period" : @".", @"Slash" : @"/", @"Backslash" : @"\\", @"Semicolon" : @";", @"Quote" : @"'",
  };
  NSString* k = [NSString stringWithUTF8String:key.c_str()];
  return names[k] ?: k;
}

bool AnyPadPressed(GCExtendedGamepad* p) {
  return p.buttonA.pressed || p.buttonB.pressed || p.buttonX.pressed || p.buttonY.pressed ||
         p.leftShoulder.pressed || p.rightShoulder.pressed || p.leftTrigger.pressed || p.rightTrigger.pressed ||
         p.dpad.up.pressed || p.dpad.down.pressed || p.dpad.left.pressed || p.dpad.right.pressed ||
         p.buttonMenu.pressed || fabsf(p.leftThumbstick.xAxis.value) > 0.5f ||
         fabsf(p.leftThumbstick.yAxis.value) > 0.5f;
}

}  // namespace

@interface NFSKeyPrompts : UIView
@end

@implementation NFSKeyPrompts {
  NSTimer* _timer;
  int _shownSerial;
  int _lastTouches;
  BOOL _keyboardLast;
  BOOL _keyWasDown;
}

- (instancetype)initWithFrame:(CGRect)frame {
  if ((self = [super initWithFrame:frame])) {
    self.userInteractionEnabled = NO;
    self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _shownSerial = -1;
    _lastTouches = nfsmw::touch::TouchesSoFar();
    __weak NFSKeyPrompts* weak = self;
    _timer = [NSTimer scheduledTimerWithTimeInterval:0.05 repeats:YES block:^(NSTimer*) { [weak tick]; }];
  }
  return self;
}

- (void)tick {
  if (!REXCVAR_GET(mnk_mode)) return;
  const BOOL key = GCKeyboard.coalescedKeyboard.keyboardInput.anyKeyPressed;
  nfsmw::keyboard::SetAnyKeyDown(key);
  PollActionKeys(GCKeyboard.coalescedKeyboard.keyboardInput);
  // Diagnostics (dev14): the first key presses as GameController sees them.
  static int key_lines = 40;
  if (key && !_keyWasDown && key_lines > 0) {
    GCKeyboardInput* input = GCKeyboard.coalescedKeyboard.keyboardInput;
    NSMutableArray* down = [NSMutableArray array];
    for (GCControllerButtonInput* b in input.buttons.allValues) {
      if (b.pressed) [down addObject:b.localizedName ?: @"?"];
    }
    --key_lines;
    REXLOG_INFO("[keyboard] key down: {}", [[down componentsJoinedByString:@", "] UTF8String]);
  }
  _keyWasDown = key;
  GCExtendedGamepad* pad = GCController.current.extendedGamepad;
  const int touches = nfsmw::touch::TouchesSoFar();
  const BOOL was = _keyboardLast;
  if (key) _keyboardLast = YES;
  if ((pad && AnyPadPressed(pad)) || touches != _lastTouches) _keyboardLast = NO;
  _lastTouches = touches;
  if (_keyboardLast != was) REXLOG_INFO("[keyboard] prompts {}", _keyboardLast ? "on" : "off");
  const bool menu = nfsmw::battery::InMenu() == 1;
  wanted.store(_keyboardLast && menu);
  if (!wanted) {
    if (self.subviews.count) {
      for (UIView* v in self.subviews.copy) [v removeFromSuperview];
      _shownSerial = -1;
    }
    return;
  }
  std::vector<float> now;
  int serial;
  {
    std::lock_guard lock(hints_mutex);
    now = hints;
    serial = hints_serial;
  }
  if (serial == _shownSerial) return;
  _shownSerial = serial;
  for (UIView* v in self.subviews.copy) [v removeFromSuperview];
  const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
  // 480 units tall: the caps over the hint bar landed 9% too close to the
  // middle with the menu taps' 0.92 (dev15 screenshots, Stefan, November 2).
  const CGFloat s = h / 480.0;
  for (size_t i = 0; i + 5 <= now.size(); i += 5) {
    const char* bind = BindFor(int(now[i + 4]));
    if (!bind) continue;
    const std::string k = nfsmw::keyboard::MenuKey(bind);
    if (k.empty()) continue;
    // Styled as the game's own hint icons (dev16/17 caps were too big and
    // out of place, Stefan): a dark disc (a pill for "Esc") with the hints'
    // cream outline and glyph, the size of the icon's ring (about 72% of
    // its drawn quad, which has a margin), keys as symbols so most fit in
    // a circle (↵ Enter, ⇥ Tab, ⌫ Backspace).
    const CGFloat ring = MAX(11, now[i + 3] * 2 * s * 0.72);
    UIColor* cream = [UIColor colorWithRed:0.91 green:0.88 blue:0.78 alpha:1];
    UILabel* cap = [[UILabel alloc] init];
    cap.text = Caption(k);
    cap.textAlignment = NSTextAlignmentCenter;
    UIFont* font = [UIFont fontWithName:@"AvenirNextCondensed-Heavy" size:ring * 0.62];
    cap.font = font ?: [UIFont systemFontOfSize:ring * 0.6 weight:UIFontWeightHeavy];
    cap.adjustsFontSizeToFitWidth = YES;
    cap.minimumScaleFactor = 0.5;
    cap.textColor = cream;
    cap.backgroundColor = [UIColor colorWithWhite:0.05 alpha:0.9];
    cap.layer.cornerRadius = ring / 2;
    cap.layer.borderColor = cream.CGColor;
    cap.layer.borderWidth = MAX(1, ring * 0.08);
    cap.clipsToBounds = YES;
    const CGFloat ch = ring;
    const CGFloat cw = MIN(ring * 2, MAX(ch, [cap.text sizeWithAttributes:@{NSFontAttributeName : cap.font}].width + ring * 0.45));
    cap.frame = CGRectMake(w / 2 + now[i] * s - cw / 2, h / 2 + now[i + 1] * s - ch / 2, cw, ch);
    [self addSubview:cap];
  }
}

@end

namespace nfsmw::keyboard {

bool PromptsWanted() { return wanted.load(std::memory_order_relaxed); }

void SetHints(const float* h, int n) {
  std::lock_guard lock(hints_mutex);
  std::vector<float> next(h, h + 5 * n);
  if (next == hints) return;
  hints = std::move(next);
  ++hints_serial;
}

}  // namespace nfsmw::keyboard

extern "C" void nfsmw_keyboard_install_prompts() {
  static NFSKeyPrompts* prompts;
  if (prompts) return;
  UIWindow* window = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    // The app's own scene: not an external display's (external_display.mm).
    if (nfsmw::IsAppScene(scene)) {
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if (nfsmw::IsHelperWindow(w)) continue;
        if (w.isKeyWindow || !window) window = w;
      }
    }
  }
  if (!window) return;
  nfsmw::keyboard::SetMenuList(nfsmw::launcher::MenuKeyBinds());
  LoadActionKeys();
  WatchMice();
  prompts = [[NFSKeyPrompts alloc] initWithFrame:window.bounds];
  [window addSubview:prompts];
  REXLOG_INFO("[keyboard] key prompts installed");
}

// The in-game options' keyboard editor saved: both sets again, applied now.
extern "C" void nfsmw_keyboard_reload() {
  LoadActionKeys();
  nfsmw::keyboard::Reload(nfsmw::launcher::DrivingKeyBinds(), nfsmw::launcher::MenuKeyBinds());
}
