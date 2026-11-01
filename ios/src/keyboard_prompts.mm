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
// nfsmw_menu_hints_list), in the packages' units: 480 / 0.92 tall from the
// middle of the screen, as menu taps (touch_controls.mm).

#import <GameController/GameController.h>
#import <UIKit/UIKit.h>

#include <atomic>
#include <mutex>
#include <string>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "battery.h"
#include "keyboard_context.h"
#include "menu_touch_policy.h"
#include "touch_controls.h"

REXCVAR_DECLARE(bool, mnk_mode);

namespace {

std::atomic<bool> wanted{false};
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
    @"Return" : @"Enter", @"Escape" : @"Esc", @"Backspace" : @"⌫", @"Space" : @"Space",
    @"Left" : @"←", @"Right" : @"→", @"Up" : @"↑", @"Down" : @"↓", @"LBracket" : @"[",
    @"RBracket" : @"]", @"PageUp" : @"PgUp", @"PageDown" : @"PgDn", @"Control" : @"Ctrl",
    @"NumpadEnter" : @"Enter", @"Minus" : @"-", @"Plus" : @"=", @"Comma" : @",",
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
  const CGFloat s = h * 0.92 / 480.0;
  for (size_t i = 0; i + 5 <= now.size(); i += 5) {
    const char* bind = BindFor(int(now[i + 4]));
    if (!bind) continue;
    const std::string k = nfsmw::keyboard::MenuKey(bind);
    if (k.empty()) continue;
    UILabel* cap = [[UILabel alloc] init];
    cap.text = Caption(k);
    cap.textAlignment = NSTextAlignmentCenter;
    cap.font = [UIFont systemFontOfSize:MAX(10, now[i + 3] * 2 * s * 0.55) weight:UIFontWeightSemibold];
    cap.adjustsFontSizeToFitWidth = YES;
    cap.minimumScaleFactor = 0.5;
    cap.textColor = UIColor.blackColor;
    cap.backgroundColor = [UIColor colorWithWhite:0.92 alpha:1];
    cap.layer.cornerRadius = 4;
    cap.layer.borderColor = [UIColor colorWithWhite:0.4 alpha:1].CGColor;
    cap.layer.borderWidth = 1;
    cap.clipsToBounds = YES;
    const CGFloat ch = MAX(14, now[i + 3] * 2 * s);
    const CGFloat cw = MAX(ch, [cap.text sizeWithAttributes:@{NSFontAttributeName : cap.font}].width + 8);
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
    if ([scene isKindOfClass:UIWindowScene.class]) {
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if (w.isKeyWindow || !window) window = w;
      }
    }
  }
  if (!window) return;
  prompts = [[NFSKeyPrompts alloc] initWithFrame:window.bounds];
  [window addSubview:prompts];
  REXLOG_INFO("[keyboard] key prompts installed");
}
