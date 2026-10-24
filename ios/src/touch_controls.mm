// NFSMW Recompiled - on-screen touch controls on iOS
//
// A basic version of Android's TouchControllerView
// (android/app/src/main/java/io/github/nfsmwrecomp/TouchControllerView.java):
// the same controls in the same default places, feeding the game through the
// same SDL virtual gamepad as Android (TouchControllerBridge.setState in
// android_main.cpp: 15 buttons and 6 axes, only what changed is sent).
//
// Two layouts, switched with the DRIVE/PAD pill next to HIDE/TOUCH (the
// choice is remembered):
//   - PAD: the full gamepad above, for menus and anything else;
//   - DRIVE: a layout for driving, from a sketch by the player: a horizontal
//     steering circle, shift buttons, nitrous, look back and a small D-pad
//     on the left; speedbreaker,
//     handbrake and tall brake/accelerate pads on the right; camera at the
//     top and reset at the bottom. Which pad button each action presses is in
//     the kDrive* table below.
//
// The layout also switches by itself (cvar ios_touch_auto_layout): to DRIVE
// when driving starts, to PAD when a menu or a pause screen comes up
// (game_state.cpp tells; battery::InMenu), checked 5 times a second. The pill
// still switches by hand until the next change.
//
// Not here yet, and on Android: tilt steering.
//
// Also here: the FPS counter (InstallFpsCounter), Android's GameActivity one.
//
// What it does:
//   - left stick, right stick, D-pad, A/B/X/Y, LB/RB, LT/RT, BACK/START,
//     L3/R3, multitouch (a finger keeps the control it started on);
//   - a light haptic tap on button presses;
//   - a HIDE/TOUCH pill at the top centre; and with a physical controller
//     connected the controls hide themselves. A tap anywhere brings them back.
//
// UIKit and SDL's joystick functions both run on the main thread here (it is
// SDL's thread on iOS), so no locking is needed.

#import <GameController/GameController.h>
#import <UIKit/UIKit.h>

#include <SDL3/SDL_joystick.h>

#include <dlfcn.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "battery.h"
#include "touch_controls.h"

REXCVAR_DEFINE_BOOL(ios_touch_auto_layout, true, "Input",
                    "Touch controls: the DRIVE layout while driving, the PAD layout in menus and pause "
                    "screens, switched by themselves");

extern "C" void NativeRequestDump();  // native_renderer.mm

namespace {

// SDL gamepad button indices, as bits (the same as TouchControllerView.java).
constexpr int kA = 1 << 0, kB = 1 << 1, kX = 1 << 2, kY = 1 << 3;
constexpr int kBack = 1 << 4, kStart = 1 << 6, kL3 = 1 << 7, kR3 = 1 << 8;
constexpr int kLB = 1 << 9, kRB = 1 << 10;
constexpr int kUp = 1 << 11, kDown = 1 << 12, kLeft = 1 << 13, kRight = 1 << 14;

constexpr int kButtons = 15;
constexpr int kAxes = 6;

// DRIVE layout: which pad input each driving action uses, from the game's
// own controls screen (control type 1). Accelerate and brake are the triggers
// (RT, LT); shifting is the right stick, up and down (see kDriveShift*).
constexpr int kDriveHandbrake = kA;     // E-brake
constexpr int kDriveNitrous = kB;
constexpr int kDriveSpeedbreaker = kX;
constexpr int kDriveCamera = kRB;       // Change camera
constexpr int kDriveReset = kBack;      // Reset car
constexpr int kDrivePause = kStart;
constexpr int kDriveLookBack = kLB;
constexpr float kDriveShiftUp = -1.0f;  // right stick Y, SDL: negative is up
constexpr float kDriveShiftDown = 1.0f;

// ---------------------------------------------------------------------------
//  The SDL virtual gamepad (the same as android_main.cpp)
// ---------------------------------------------------------------------------
SDL_Joystick* g_pad = nullptr;
int g_buttons = 0;
Sint16 g_axes[kAxes] = {};

// Keyboard controls (the SDK's mnk_mode, set by the launcher).
bool KeyboardControlsOn() { return rex::cvar::Query<bool>("mnk_mode"); }

Sint16 AxisToS16(float v) { return Sint16(std::clamp(v, -1.0f, 1.0f) * 32767.0f); }
Sint16 TriggerToS16(float v) { return Sint16(std::clamp(v, 0.0f, 1.0f) * 65535.0f - 32768.0f); }

void SetPadState(int buttons, float lx, float ly, float rx, float ry, float lt, float rt) {
  if (!g_pad) {
    SDL_VirtualJoystickDesc desc;
    SDL_INIT_INTERFACE(&desc);
    desc.type = SDL_JOYSTICK_TYPE_GAMEPAD;
    desc.naxes = kAxes;
    desc.nbuttons = kButtons;
    desc.nhats = 0;
    desc.name = "NFSMW touch controls";
    const SDL_JoystickID id = SDL_AttachVirtualJoystick(&desc);
    if (id != 0) {
      g_pad = SDL_OpenJoystick(id);
    }
    if (!g_pad) {
      REXLOG_ERROR("[touch] could not create the virtual gamepad: {}", SDL_GetError());
      return;
    }
    REXLOG_INFO("[touch] virtual gamepad created");
  }
  const int changed = buttons ^ g_buttons;
  for (int i = 0; i < kButtons; ++i) {
    if (changed & (1 << i)) {
      SDL_SetJoystickVirtualButton(g_pad, i, (buttons & (1 << i)) != 0);
    }
  }
  g_buttons = buttons;
  const Sint16 axes[kAxes] = {AxisToS16(lx), AxisToS16(ly), AxisToS16(rx),
                              AxisToS16(ry), TriggerToS16(lt), TriggerToS16(rt)};
  for (int i = 0; i < kAxes; ++i) {
    if (axes[i] != g_axes[i]) {
      SDL_SetJoystickVirtualAxis(g_pad, i, axes[i]);
      g_axes[i] = axes[i];
    }
  }
}

// ---------------------------------------------------------------------------
//  The controls
// ---------------------------------------------------------------------------
enum class Kind { kStick, kRoundButton, kRectButton, kTrigger, kDpad };

struct Control {
  Kind kind;
  NSString* label;
  CGPoint center;
  CGFloat radius;  // round controls
  CGSize size;     // rectangular controls
  int bit = 0;     // buttons
  int axis = -1;   // sticks: 0 left, 1 right; triggers: 0 LT, 1 RT
  bool horizontal = false;  // sticks: left/right only (the steering circle)
  float right_y = 0;        // buttons that push the right stick up/down (shifting)
  // State.
  bool pressed = false;
  CGPoint knob{0, 0};  // sticks: -1..1
  int dpad_bits = 0;

  bool Contains(CGPoint p) const {
    if (kind == Kind::kRectButton || kind == Kind::kTrigger) {
      // A little slack around the rectangle, easier to hit with a thumb.
      return std::fabs(p.x - center.x) <= size.width * 0.5 + 8 &&
             std::fabs(p.y - center.y) <= size.height * 0.5 + 8;
    }
    // Sticks take touches a bit beyond their ring.
    const CGFloat r = kind == Kind::kStick ? radius * 1.35 : radius * 1.15;
    return std::hypot(p.x - center.x, p.y - center.y) <= r;
  }

  // What it covers on screen (with its outline and label), for redrawing
  // only what changed.
  CGRect Bounds() const {
    const bool round = kind == Kind::kStick || kind == Kind::kRoundButton;
    const CGFloat w = round ? radius * 2 : size.width, h = round ? radius * 2 : size.height;
    return CGRectInset(CGRectMake(center.x - w / 2, center.y - h / 2, w, h), -6, -6);
  }

  // Its look: pressed, where the knob is, which D-pad arrows.
  uint64_t Look() const {
    return uint64_t(pressed) | uint64_t(dpad_bits & 0xFFFF) << 1 |
           uint64_t(uint16_t(int16_t(knob.x * 1000))) << 17 | uint64_t(uint16_t(int16_t(knob.y * 1000))) << 33;
  }
};

}  // namespace

@interface NFSTouchView : UIView
- (void)followGame;
@end

@implementation NFSTouchView {
  std::vector<Control> _controls;
  std::vector<uint64_t> _drawnLook;  // each control's look when last drawn
  NSMapTable<UITouch*, NSNumber*>* _owners;  // touch -> control index
  CGRect _toggle;
  CGRect _modeToggle;  // DRIVE/PAD
  CGRect _snap;        // SNAP (nfsmw_native_dump_manual): a renderer snapshot; empty when off
  BOOL _driving;
  BOOL _controlsVisible;
  UIImpactFeedbackGenerator* _haptic;
  // The layout editor (launcher: Customize touch controls): touches move
  // controls instead of pressing them.
  BOOL _editing;
  int _selected;
  CGPoint _grab;  // the finger's offset from the selected control's centre
}

// The player's layout (NSUserDefaults, set in the editor): per control
// (layout.name) its centre as fractions of the view and a size factor; and
// the size of all controls and their opacity.
static NSString* const kLayoutKey = @"nfsmw.touch.layout";

static NSString* ControlIdent(BOOL driving, const Control& c) {
  NSString* name = c.label.length ? [c.label stringByReplacingOccurrencesOfString:@"\n" withString:@" "]
                                  : (c.kind == Kind::kDpad ? @"DPAD" : @"STEER");
  return [NSString stringWithFormat:@"%@.%@", driving ? @"drive" : @"pad", name];
}

static CGFloat TouchSize() {
  const double v = [NSUserDefaults.standardUserDefaults doubleForKey:@"nfsmw.touch.size"];
  return v > 0 ? CGFloat(v) : 1.0;
}

static CGFloat TouchOpacity() {
  NSNumber* v = [NSUserDefaults.standardUserDefaults objectForKey:@"nfsmw.touch.opacity"];
  return v ? CGFloat(std::clamp(v.doubleValue, 0.15, 1.0)) : 1.0;
}

- (instancetype)initWithFrame:(CGRect)frame {
  if ((self = [super initWithFrame:frame])) {
    self.backgroundColor = UIColor.clearColor;
    self.opaque = NO;
    self.multipleTouchEnabled = YES;
    self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _owners = [NSMapTable strongToStrongObjectsMapTable];
    // Hidden while a gamepad, or a keyboard with keyboard controls on, is
    // connected (a tap brings them back).
    _controlsVisible = !GCController.current && !(KeyboardControlsOn() && GCKeyboard.coalescedKeyboard);
    _driving = [NSUserDefaults.standardUserDefaults boolForKey:@"nfsmw.touch.driving"];
    _haptic = [[UIImpactFeedbackGenerator alloc] initWithStyle:UIImpactFeedbackStyleLight];
    _selected = -1;
    self.alpha = TouchOpacity();
    // The drawing is recorded here and rasterized on Core Animation's own
    // thread, not on the main thread (~10 ms a second while driving).
    self.layer.drawsAsynchronously = YES;
    NSNotificationCenter* nc = NSNotificationCenter.defaultCenter;
    [nc addObserver:self
           selector:@selector(controllerConnected:)
               name:GCControllerDidConnectNotification
             object:nil];
    [nc addObserver:self
           selector:@selector(controllerDisconnected:)
               name:GCControllerDidDisconnectNotification
             object:nil];
    if (KeyboardControlsOn()) {
      [nc addObserver:self
             selector:@selector(controllerConnected:)
                 name:GCKeyboardDidConnectNotification
               object:nil];
      [nc addObserver:self
             selector:@selector(controllerDisconnected:)
                 name:GCKeyboardDidDisconnectNotification
               object:nil];
    }
  }
  return self;
}

// The layout to the game's state, when it changes (ios_touch_auto_layout).
- (void)followGame {
  __weak NFSTouchView* weak = self;
  [NSTimer scheduledTimerWithTimeInterval:0.2
                                  repeats:YES
                                    block:^(NSTimer* timer) {
                                      NFSTouchView* view = weak;
                                      if (!view) {
                                        [timer invalidate];
                                        return;
                                      }
                                      [view gameStateTick];
                                    }];
}

- (void)gameStateTick {
  static int last = -1;
  const int in_menu = nfsmw::battery::InMenu();
  if (in_menu == last || in_menu < 0 || _editing) return;
  last = in_menu;
  const BOOL driving = in_menu == 0;
  if (driving == _driving) return;
  [self releaseAll];  // nothing stays pressed from the other layout
  _driving = driving;
  [self setNeedsLayout];
  REXLOG_INFO("[touch] {} layout", driving ? "DRIVE" : "PAD");
}

- (void)controllerConnected:(NSNotification*)note {
  [self setControlsVisible:NO];
}

- (void)controllerDisconnected:(NSNotification*)note {
  if (GCController.controllers.count == 0 && !(KeyboardControlsOn() && GCKeyboard.coalescedKeyboard)) {
    [self setControlsVisible:YES];
  }
}

- (void)setControlsVisible:(BOOL)visible {
  _controlsVisible = visible;
  if (!visible) {
    [self releaseAll];
  }
  [self setNeedsDisplay];
}

// The default layout of TouchControllerView.buildControls: positions in
// fractions of the view, sizes in 'unit', 1/16 of the width or 1/9 of the
// height, whichever is smaller.
- (void)layoutSubviews {
  [super layoutSubviews];
  const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
  const CGFloat unit = std::min(w / 16.0, h / 9.0);
  const CGFloat stick = unit * 0.78, button = unit * 0.38;
  const CGFloat shoulderW = unit * 1.25, shoulderH = unit * 0.55;
  auto P = [&](CGFloat fx, CGFloat fy) { return CGPointMake(w * fx, h * fy); };
  [self setNeedsDisplay];  // a new layout: everything redrawn once
  _drawnLook.clear();
  _controls.clear();
  _toggle = CGRectMake(w * .5 - unit * .9, h * .02, unit * 1.8, unit * .5);
  _modeToggle = CGRectOffset(_toggle, -(_toggle.size.width + unit * .3), 0);
  static const bool snap = rex::cvar::Query<bool>("nfsmw_native_dump_manual");
  _snap = snap ? CGRectOffset(_toggle, _toggle.size.width + unit * .3, 0) : CGRectZero;
  if (_driving) {
    [self layoutDriving:w height:h unit:unit];
    [self releaseAll];
    return;
  }
  auto round = [&](NSString* l, CGPoint c, CGFloat r, int bit) {
    Control k{Kind::kRoundButton, l, c, r};
    k.bit = bit;
    _controls.push_back(k);
  };
  auto rect = [&](Kind kind, NSString* l, CGPoint c, CGSize s, int bit, int axis) {
    Control k{kind, l, c, 0, s};
    k.bit = bit;
    k.axis = axis;
    _controls.push_back(k);
  };
  Control ls{Kind::kStick, @"L", P(.16, .73), stick};
  ls.axis = 0;
  Control rs{Kind::kStick, @"R", P(.67, .77), stick};
  rs.axis = 1;
  _controls.push_back(ls);
  _controls.push_back(rs);
  Control dpad{Kind::kDpad, @"", P(.32, .72), unit * 0.98};
  _controls.push_back(dpad);
  const CGPoint face = P(.85, .68);
  round(@"A", CGPointMake(face.x, face.y + unit * .68), button, kA);
  round(@"B", CGPointMake(face.x + unit * .68, face.y), button, kB);
  round(@"X", CGPointMake(face.x - unit * .68, face.y), button, kX);
  round(@"Y", CGPointMake(face.x, face.y - unit * .68), button, kY);
  rect(Kind::kTrigger, @"LT", P(.07, .10), CGSizeMake(shoulderW, shoulderH), 0, 0);
  rect(Kind::kRectButton, @"LB", P(.20, .10), CGSizeMake(shoulderW, shoulderH), kLB, -1);
  rect(Kind::kRectButton, @"RB", P(.80, .10), CGSizeMake(shoulderW, shoulderH), kRB, -1);
  rect(Kind::kTrigger, @"RT", P(.93, .10), CGSizeMake(shoulderW, shoulderH), 0, 1);
  rect(Kind::kRectButton, @"BACK", P(.44, .79), CGSizeMake(unit * .82, unit * .45), kBack, -1);
  rect(Kind::kRectButton, @"START", P(.55, .79), CGSizeMake(unit * .92, unit * .45), kStart, -1);
  round(@"L3", P(.07, .48), button * .82, kL3);
  round(@"R3", P(.73, .48), button * .82, kR3);
  [self applyCustomLayout];
  [self releaseAll];
}

// The player's sizes and positions over the default layout.
- (void)applyCustomLayout {
  const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
  if (w <= 0 || h <= 0) return;
  NSDictionary* layout = [NSUserDefaults.standardUserDefaults dictionaryForKey:kLayoutKey];
  const CGFloat all = TouchSize();
  for (Control& c : _controls) {
    CGFloat scale = all;
    NSArray* v = layout[ControlIdent(_driving, c)];
    if (v.count == 3) {
      c.center = CGPointMake(w * [v[0] doubleValue], h * [v[1] doubleValue]);
      scale *= CGFloat([v[2] doubleValue]);
    }
    c.radius *= scale;
    c.size = CGSizeMake(c.size.width * scale, c.size.height * scale);
  }
  self.alpha = _editing ? 1.0 : TouchOpacity();
}

- (void)saveControl:(const Control&)c scale:(CGFloat)scale {
  const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
  NSMutableDictionary* layout =
      [[NSUserDefaults.standardUserDefaults dictionaryForKey:kLayoutKey] mutableCopy] ?: [NSMutableDictionary dictionary];
  layout[ControlIdent(_driving, c)] = @[ @(c.center.x / w), @(c.center.y / h), @(scale) ];
  [NSUserDefaults.standardUserDefaults setObject:layout forKey:kLayoutKey];
}

// Editor: the selected control's own size factor (1 = default).
- (CGFloat)scaleOf:(const Control&)c {
  NSArray* v = [NSUserDefaults.standardUserDefaults dictionaryForKey:kLayoutKey][ControlIdent(_driving, c)];
  return v.count == 3 ? CGFloat([v[2] doubleValue]) : 1.0;
}

- (void)setEditing:(BOOL)editing driving:(BOOL)driving {
  _editing = editing;
  _driving = driving;
  _controlsVisible = YES;
  _selected = -1;
  [self setNeedsLayout];
}

- (void)resizeSelected:(CGFloat)factor {
  if (_selected < 0 || size_t(_selected) >= _controls.size()) return;
  const Control& c = _controls[size_t(_selected)];
  const CGFloat scale = std::clamp([self scaleOf:c] * factor, 0.5, 2.0);
  [self saveControl:c scale:scale];
  const int keep = _selected;
  [self setNeedsLayout];
  [self layoutIfNeeded];
  _selected = keep;
  [self setNeedsDisplay];
}

// The DRIVE layout (positions as fractions of the view, from the sketch).
- (void)layoutDriving:(CGFloat)w height:(CGFloat)h unit:(CGFloat)unit {
  auto P = [&](CGFloat fx, CGFloat fy) { return CGPointMake(w * fx, h * fy); };
  auto round = [&](NSString* l, CGPoint c, CGFloat r, int bit) {
    Control k{Kind::kRoundButton, l, c, r};
    k.bit = bit;
    _controls.push_back(k);
  };
  Control steer{Kind::kStick, @"", P(.115, .78), unit * 1.15};
  steer.axis = 0;
  steer.horizontal = true;
  _controls.push_back(steer);
  auto shift = [&](NSString* l, CGPoint c, float y) {
    Control k{Kind::kRoundButton, l, c, unit * .42};
    k.right_y = y;
    _controls.push_back(k);
  };
  shift(@"DOWN", P(.075, .52), kDriveShiftDown);
  shift(@"UP", P(.165, .52), kDriveShiftUp);
  round(@"NOS", P(.235, .86), unit * .5, kDriveNitrous);
  round(@"LOOK\nBACK", P(.235, .62), unit * .42, kDriveLookBack);
  round(@"SPEED\nBREAKER", P(.765, .58), unit * .8, kDriveSpeedbreaker);
  round(@"HAND\nBRAKE", P(.9, .58), unit * .8, kDriveHandbrake);
  Control brake{Kind::kTrigger, @"BRAKE", P(.765, .84), 0, CGSizeMake(unit * 1.05, unit * 1.75)};
  brake.axis = 0;
  _controls.push_back(brake);
  Control accel{Kind::kTrigger, @"GAS", P(.9, .84), 0, CGSizeMake(unit * 1.05, unit * 1.75)};
  accel.axis = 1;
  _controls.push_back(accel);
  round(@"CAM", P(.455, .17), unit * .36, kDriveCamera);
  round(@"PAUSE", P(.545, .17), unit * .36, kDrivePause);
  round(@"RESET", P(.5, .86), unit * .36, kDriveReset);
  // The D-pad, for what free roam puts on it (shops and safehouses, the
  // Blacklist, the map, messages) and for menus.
  Control dpad{Kind::kDpad, @"", P(.11, .27), unit * .72};
  _controls.push_back(dpad);
  [self applyCustomLayout];
}

// Touches go to the game's own view where there is nothing of ours.
- (UIView*)hitTest:(CGPoint)p withEvent:(UIEvent*)event {
  if (_editing) {
    return [super hitTest:p withEvent:event] ? self : nil;
  }
  if (!_controlsVisible) {
    return self;  // any tap brings the controls back
  }
  if (CGRectContainsPoint(_toggle, p) || CGRectContainsPoint(_modeToggle, p) || CGRectContainsPoint(_snap, p)) {
    return self;
  }
  for (const Control& c : _controls) {
    if (c.Contains(p)) {
      return self;
    }
  }
  return nil;
}

- (int)controlAt:(CGPoint)p {
  for (size_t i = 0; i < _controls.size(); ++i) {
    if (_controls[i].Contains(p)) {
      return int(i);
    }
  }
  return -1;
}

- (void)updateControl:(Control&)c at:(CGPoint)p {
  switch (c.kind) {
    case Kind::kStick: {
      CGFloat dx = (p.x - c.center.x) / c.radius,
              dy = c.horizontal ? 0 : (p.y - c.center.y) / c.radius;
      const CGFloat len = std::hypot(dx, dy);
      if (len > 1) {
        dx /= len;
        dy /= len;
      }
      c.knob = CGPointMake(dx, dy);
      break;
    }
    case Kind::kDpad: {
      const CGFloat dx = p.x - c.center.x, dy = p.y - c.center.y;
      int bits = 0;
      // A dead zone in the middle, and diagonals within +-22.5 degrees.
      if (std::hypot(dx, dy) > c.radius * 0.2) {
        const CGFloat a = std::atan2(dy, dx) * 180.0 / M_PI;  // 0 = right, 90 = down
        if (a > -67.5 && a < 67.5) bits |= kRight;
        if (a > 112.5 || a < -112.5) bits |= kLeft;
        if (a > 22.5 && a < 157.5) bits |= kDown;
        if (a < -22.5 && a > -157.5) bits |= kUp;
      }
      c.dpad_bits = bits;
      break;
    }
    default:
      break;
  }
}

- (void)touchesBegan:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
  if (_editing) {
    const CGPoint p = [touches.anyObject locationInView:self];
    _selected = [self controlAt:p];
    if (_selected >= 0) {
      const Control& c = _controls[size_t(_selected)];
      _grab = CGPointMake(p.x - c.center.x, p.y - c.center.y);
      [_haptic impactOccurred];
    }
    [self setNeedsDisplay];
    return;
  }
  if (!_controlsVisible) {
    [self setControlsVisible:YES];
    return;
  }
  bool haptic = false;
  for (UITouch* t in touches) {
    const CGPoint p = [t locationInView:self];
    if (CGRectContainsPoint(_toggle, p)) {
      [self setControlsVisible:NO];
      return;
    }
    if (CGRectContainsPoint(_snap, p)) {
      NativeRequestDump();
      REXLOG_INFO("[touch] snapshot requested");
      [_haptic impactOccurred];
      return;
    }
    if (CGRectContainsPoint(_modeToggle, p)) {
      _driving = !_driving;
      [NSUserDefaults.standardUserDefaults setBool:_driving forKey:@"nfsmw.touch.driving"];
      [_haptic impactOccurred];
      [self setNeedsLayout];
      return;
    }
    const int i = [self controlAt:p];
    if (i < 0) {
      continue;
    }
    [_owners setObject:@(i) forKey:t];
    Control& c = _controls[size_t(i)];
    c.pressed = true;
    [self updateControl:c at:p];
    haptic = haptic || c.kind == Kind::kRoundButton || c.kind == Kind::kRectButton;
  }
  if (haptic) {
    [_haptic impactOccurred];
  }
  [self sendState];
}

- (void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
  if (_editing) {
    if (_selected >= 0) {
      Control& c = _controls[size_t(_selected)];
      const CGPoint p = [touches.anyObject locationInView:self];
      const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
      c.center = CGPointMake(std::clamp(p.x - _grab.x, 0.0, w), std::clamp(p.y - _grab.y, 0.0, h));
      [self setNeedsDisplay];
    }
    return;
  }
  for (UITouch* t in touches) {
    NSNumber* owner = [_owners objectForKey:t];
    if (owner) {
      [self updateControl:_controls[owner.unsignedIntegerValue] at:[t locationInView:self]];
    }
  }
  [self sendState];
}

- (void)endTouches:(NSSet<UITouch*>*)touches {
  for (UITouch* t in touches) {
    NSNumber* owner = [_owners objectForKey:t];
    if (!owner) {
      continue;
    }
    [_owners removeObjectForKey:t];
    Control& c = _controls[owner.unsignedIntegerValue];
    // Another finger may still hold the same control.
    bool still_held = false;
    for (UITouch* other in _owners) {
      if ([_owners objectForKey:other].unsignedIntegerValue == owner.unsignedIntegerValue) {
        still_held = true;
      }
    }
    if (!still_held) {
      c.pressed = false;
      c.knob = CGPointZero;
      c.dpad_bits = 0;
    }
  }
  [self sendState];
}

- (void)touchesEnded:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
  if (_editing) {
    if (_selected >= 0) {
      const Control& c = _controls[size_t(_selected)];
      [self saveControl:c scale:[self scaleOf:c]];
    }
    return;
  }
  [self endTouches:touches];
}

- (void)touchesCancelled:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
  [self endTouches:touches];
}

- (void)releaseAll {
  [_owners removeAllObjects];
  for (Control& c : _controls) {
    c.pressed = false;
    c.knob = CGPointZero;
    c.dpad_bits = 0;
  }
  [self sendState];
}

- (void)sendState {
  int buttons = 0;
  float axes[4] = {}, triggers[2] = {};
  for (const Control& c : _controls) {
    switch (c.kind) {
      case Kind::kStick:
        axes[c.axis * 2] = float(c.knob.x);
        axes[c.axis * 2 + 1] = float(c.knob.y);
        break;
      case Kind::kTrigger:
        triggers[c.axis] = c.pressed ? 1.0f : 0.0f;
        break;
      case Kind::kDpad:
        buttons |= c.dpad_bits;
        break;
      default:
        if (c.pressed) {
          buttons |= c.bit;
          if (c.right_y != 0) {
            axes[3] = c.right_y;
          }
        }
        break;
    }
  }
  if (!_editing) {
    SetPadState(buttons, axes[0], axes[1], axes[2], axes[3], triggers[0], triggers[1]);
  }
  // Redraw only the controls whose look changed (a moving finger used to
  // redraw the whole screen-sized overlay at every move: ~0.1 of a core).
  if (_drawnLook.size() != _controls.size()) {
    _drawnLook.assign(_controls.size(), ~uint64_t(0));
  }
  CGRect dirty = CGRectNull;
  for (size_t i = 0; i < _controls.size(); ++i) {
    const uint64_t look = _controls[i].Look();
    if (look != _drawnLook[i]) {
      _drawnLook[i] = look;
      dirty = CGRectUnion(dirty, _controls[i].Bounds());
    }
  }
  if (!CGRectIsNull(dirty)) {
    [self setNeedsDisplayInRect:dirty];
  }
}

// ---------------------------------------------------------------------------
//  Drawing: translucent dark fills with a light outline, like Android's.
// ---------------------------------------------------------------------------
- (void)drawLabel:(NSString*)text at:(CGPoint)p size:(CGFloat)size {
  [self drawLabel:text at:p size:size fit:CGFLOAT_MAX];
}

// A label no wider than `fit`: a long word on a small button is made smaller.
- (void)drawLabel:(NSString*)text at:(CGPoint)p size:(CGFloat)size fit:(CGFloat)fit {
  NSMutableParagraphStyle* centered = [[NSMutableParagraphStyle alloc] init];
  centered.alignment = NSTextAlignmentCenter;
  // Two-line labels ("SPEED\nBREAKER") a little smaller.
  const bool two_lines = [text containsString:@"\n"];
  NSDictionary* attrs = @{
    NSFontAttributeName : [UIFont boldSystemFontOfSize:two_lines ? size * 0.55 : size],
    NSForegroundColorAttributeName : [UIColor colorWithWhite:1 alpha:0.85],
    NSParagraphStyleAttributeName : centered
  };
  CGSize s = [text boundingRectWithSize:CGSizeMake(CGFLOAT_MAX, CGFLOAT_MAX)
                                options:NSStringDrawingUsesLineFragmentOrigin
                             attributes:attrs
                                context:nil]
                 .size;
  if (s.width > fit && fit > 0) {
    const CGFloat k = fit / s.width;
    UIFont* font = attrs[NSFontAttributeName];
    NSMutableDictionary* smaller = [attrs mutableCopy];
    smaller[NSFontAttributeName] = [font fontWithSize:font.pointSize * k];
    attrs = smaller;
    s = [text boundingRectWithSize:CGSizeMake(CGFLOAT_MAX, CGFLOAT_MAX)
                           options:NSStringDrawingUsesLineFragmentOrigin
                        attributes:attrs
                           context:nil]
            .size;
  }
  [text drawInRect:CGRectMake(p.x - s.width / 2, p.y - s.height / 2, s.width, s.height)
      withAttributes:attrs];
}

- (void)drawRect:(CGRect)dirty {
  UIColor* fill = [UIColor colorWithWhite:0.05 alpha:0.40];
  UIColor* pressed = [UIColor colorWithRed:0.44 green:0.45 blue:0.20 alpha:0.75];
  UIColor* stroke = [UIColor colorWithWhite:1 alpha:0.55];

  if (_editing) {
    // The editor: the selected control outlined.
    if (_selected >= 0 && size_t(_selected) < _controls.size()) {
      UIBezierPath* sel = [UIBezierPath bezierPathWithRoundedRect:_controls[size_t(_selected)].Bounds()
                                                    cornerRadius:10];
      [[UIColor systemYellowColor] setStroke];
      sel.lineWidth = 3;
      [sel stroke];
    }
  } else {
  // The HIDE/TOUCH pill.
  UIBezierPath* pill = [UIBezierPath bezierPathWithRoundedRect:_toggle
                                                  cornerRadius:_toggle.size.height / 2];
  [fill setFill];
  [pill fill];
  [stroke setStroke];
  pill.lineWidth = 1;
  [pill stroke];
  [self drawLabel:(_controlsVisible ? @"HIDE" : @"TOUCH")
               at:CGPointMake(CGRectGetMidX(_toggle), CGRectGetMidY(_toggle))
             size:_toggle.size.height * 0.42];
  if (!_controlsVisible) {
    return;
  }

  // The DRIVE/PAD pill: names the layout a tap switches to.
  UIBezierPath* mode = [UIBezierPath bezierPathWithRoundedRect:_modeToggle
                                                  cornerRadius:_modeToggle.size.height / 2];
  [fill setFill];
  [mode fill];
  [stroke setStroke];
  mode.lineWidth = 1;
  [mode stroke];
  [self drawLabel:(_driving ? @"PAD" : @"DRIVE")
               at:CGPointMake(CGRectGetMidX(_modeToggle), CGRectGetMidY(_modeToggle))
             size:_modeToggle.size.height * 0.42];
  if (!CGRectIsEmpty(_snap)) {
    UIBezierPath* snap = [UIBezierPath bezierPathWithRoundedRect:_snap cornerRadius:_snap.size.height / 2];
    [fill setFill];
    [snap fill];
    [stroke setStroke];
    snap.lineWidth = 1;
    [snap stroke];
    [self drawLabel:@"SNAP"
                 at:CGPointMake(CGRectGetMidX(_snap), CGRectGetMidY(_snap))
               size:_snap.size.height * 0.42];
  }
  }

  for (const Control& c : _controls) {
    if (!CGRectIntersectsRect(c.Bounds(), dirty)) continue;  // not in the part being redrawn
    switch (c.kind) {
      case Kind::kStick: {
        UIBezierPath* ring = [UIBezierPath
            bezierPathWithOvalInRect:CGRectInset(CGRectMake(c.center.x, c.center.y, 0, 0),
                                                 -c.radius, -c.radius)];
        [fill setFill];
        [ring fill];
        [stroke setStroke];
        ring.lineWidth = 1.5;
        [ring stroke];
        const CGFloat kr = c.radius * 0.45;
        const CGPoint k = CGPointMake(c.center.x + c.knob.x * c.radius * 0.6,
                                      c.center.y + c.knob.y * c.radius * 0.6);
        UIBezierPath* knob =
            [UIBezierPath bezierPathWithOvalInRect:CGRectMake(k.x - kr, k.y - kr, kr * 2, kr * 2)];
        [(c.pressed ? pressed : [UIColor colorWithWhite:0.3 alpha:0.6]) setFill];
        [knob fill];
        [stroke setStroke];
        [knob stroke];
        break;
      }
      case Kind::kDpad: {
        const CGFloat arm = c.radius * 0.36, len = c.radius;
        const struct {
          int bit;
          CGRect r;
          NSString* l;
        } arms[] = {
            {kUp, CGRectMake(c.center.x - arm, c.center.y - len, arm * 2, len - arm), @"▲"},
            {kDown, CGRectMake(c.center.x - arm, c.center.y + arm, arm * 2, len - arm), @"▼"},
            {kLeft, CGRectMake(c.center.x - len, c.center.y - arm, len - arm, arm * 2), @"◀"},
            {kRight, CGRectMake(c.center.x + arm, c.center.y - arm, len - arm, arm * 2), @"▶"},
        };
        for (const auto& a : arms) {
          UIBezierPath* path = [UIBezierPath bezierPathWithRoundedRect:a.r cornerRadius:4];
          [((c.dpad_bits & a.bit) ? pressed : fill) setFill];
          [path fill];
          [stroke setStroke];
          [path stroke];
          [self drawLabel:a.l
                       at:CGPointMake(CGRectGetMidX(a.r), CGRectGetMidY(a.r))
                     size:arm * 0.8];
        }
        break;
      }
      case Kind::kRoundButton: {
        UIBezierPath* path = [UIBezierPath
            bezierPathWithOvalInRect:CGRectInset(CGRectMake(c.center.x, c.center.y, 0, 0),
                                                 -c.radius, -c.radius)];
        [(c.pressed ? pressed : fill) setFill];
        [path fill];
        [stroke setStroke];
        path.lineWidth = 1.5;
        [path stroke];
        [self drawLabel:c.label at:c.center size:c.radius * 0.8 fit:c.radius * 1.6];
        break;
      }
      case Kind::kRectButton:
      case Kind::kTrigger: {
        const CGRect r = CGRectMake(c.center.x - c.size.width / 2, c.center.y - c.size.height / 2,
                                    c.size.width, c.size.height);
        UIBezierPath* path = [UIBezierPath bezierPathWithRoundedRect:r
                                                        cornerRadius:std::min(c.size.width, c.size.height) * 0.3];
        [(c.pressed ? pressed : fill) setFill];
        [path fill];
        [stroke setStroke];
        path.lineWidth = 1.5;
        [path stroke];
        [self drawLabel:c.label
                     at:c.center
                   size:std::min(c.size.width, c.size.height) * 0.38
                    fit:c.size.width * 0.85];
        break;
      }
    }
  }
}

@end

// ---------------------------------------------------------------------------
//  The FPS counter
// ---------------------------------------------------------------------------
// The guest's fps and ms per frame, as the GPU plugin publishes them
// (tools/parche_fps.py: nfsmw_fps_invitado / nfsmw_ms_invitado), found the way
// android_main.cpp finds them. Null until the plugin is loaded.
static std::atomic<float>* PluginCounter(const char* name) {
  return static_cast<std::atomic<float>*>(dlsym(RTLD_DEFAULT, name));
}

@interface NFSFpsLabel : UILabel
@end

@implementation NFSFpsLabel {
  NSTimer* _timer;
  std::atomic<float>* _fps;
  std::atomic<float>* _ms;
}

- (instancetype)init {
  if ((self = [super initWithFrame:CGRectZero])) {
    self.userInteractionEnabled = NO;
    self.textColor = UIColor.whiteColor;
    self.backgroundColor = [UIColor colorWithWhite:0 alpha:0.6];
    self.font = [UIFont monospacedDigitSystemFontOfSize:13 weight:UIFontWeightBold];
    self.textAlignment = NSTextAlignmentCenter;
    self.layer.cornerRadius = 6;
    self.layer.masksToBounds = YES;
    self.text = @"-- fps";
    __weak NFSFpsLabel* weak = self;
    _timer = [NSTimer scheduledTimerWithTimeInterval:0.5
                                             repeats:YES
                                               block:^(NSTimer*) {
                                                 [weak refresh];
                                               }];
  }
  return self;
}

- (void)refresh {
  if (!_fps) {
    _fps = PluginCounter("nfsmw_fps_invitado");
    _ms = PluginCounter("nfsmw_ms_invitado");
  }
  const float fps = _fps ? _fps->load(std::memory_order_relaxed) : -1.0f;
  const float ms = _ms ? _ms->load(std::memory_order_relaxed) : -1.0f;
  if (fps < 0) {
    self.text = @"-- fps";
  } else if (ms > 0) {
    self.text = [NSString stringWithFormat:@"%.0f fps · %.1f ms", fps, ms];
  } else {
    self.text = [NSString stringWithFormat:@"%.0f fps", fps];
  }
  [self layoutInSuperview];
}

- (void)layoutInSuperview {
  UIView* parent = self.superview;
  if (!parent) {
    return;
  }
  const CGSize s = [self.text sizeWithAttributes:@{NSFontAttributeName : self.font}];
  const UIEdgeInsets safe = parent.safeAreaInsets;
  self.frame = CGRectMake(safe.left + 8, safe.top + 6, std::ceil(s.width) + 16,
                          std::ceil(s.height) + 6);
}

- (void)removeFromSuperview {
  [_timer invalidate];
  [super removeFromSuperview];
}

@end

namespace {

// The game's window: SDL's UIWindow, the key window of the app's scene.
UIWindow* GameWindow() {
  UIWindow* window = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    if ([scene isKindOfClass:UIWindowScene.class] &&
        ((UIWindowScene*)scene).screen == UIScreen.mainScreen) {
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if (w.isKeyWindow || !window) {
          window = w;
        }
      }
    }
  }
  return window;
}

}  // namespace

// ---------------------------------------------------------------------------
//  The layout editor (launcher › Controls › Customize touch controls)
// ---------------------------------------------------------------------------
@interface NFSTouchView (Editing)
- (void)setEditing:(BOOL)editing driving:(BOOL)driving;
- (void)resizeSelected:(CGFloat)factor;
@end

@interface NFSTouchLayoutEditor : UIViewController
@end

@implementation NFSTouchLayoutEditor {
  NFSTouchView* _touch;
  UISegmentedControl* _mode;
  BOOL _driving;
}

- (UIInterfaceOrientationMask)supportedInterfaceOrientations {
  return UIInterfaceOrientationMaskLandscape;
}

- (BOOL)prefersStatusBarHidden {
  return YES;
}

- (UIButton*)button:(NSString*)title action:(SEL)action {
  UIButtonConfiguration* c = UIButtonConfiguration.filledButtonConfiguration;
  c.title = title;
  c.cornerStyle = UIButtonConfigurationCornerStyleCapsule;
  c.contentInsets = NSDirectionalEdgeInsetsMake(6, 12, 6, 12);
  UIButton* b = [UIButton buttonWithConfiguration:c primaryAction:nil];
  [b addTarget:self action:action forControlEvents:UIControlEventTouchUpInside];
  return b;
}

- (UIStackView*)slider:(NSString*)title value:(float)value min:(float)min max:(float)max action:(SEL)action {
  UILabel* label = [[UILabel alloc] init];
  label.text = title;
  label.textColor = UIColor.whiteColor;
  label.font = [UIFont systemFontOfSize:13 weight:UIFontWeightSemibold];
  UISlider* slider = [[UISlider alloc] init];
  slider.minimumValue = min;
  slider.maximumValue = max;
  slider.value = value;
  [slider addTarget:self action:action forControlEvents:UIControlEventValueChanged];
  [slider.widthAnchor constraintEqualToConstant:130].active = YES;
  UIStackView* row = [[UIStackView alloc] initWithArrangedSubviews:@[ label, slider ]];
  row.spacing = 8;
  row.alignment = UIStackViewAlignmentCenter;
  return row;
}

- (void)viewDidLoad {
  [super viewDidLoad];
  self.view.backgroundColor = [UIColor colorWithRed:0.12 green:0.13 blue:0.16 alpha:1];
  UILabel* hint = [[UILabel alloc] init];
  hint.text = @"Drag a control to move it. Tap one, then use Smaller / Bigger to resize it.";
  hint.textColor = [UIColor colorWithWhite:1 alpha:0.6];
  hint.font = [UIFont systemFontOfSize:13];
  hint.textAlignment = NSTextAlignmentCenter;
  hint.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:hint];

  _touch = [[NFSTouchView alloc] initWithFrame:self.view.bounds];
  _touch.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  [self.view addSubview:_touch];
  _driving = [NSUserDefaults.standardUserDefaults boolForKey:@"nfsmw.touch.driving"];
  [_touch setEditing:YES driving:_driving];

  _mode = [[UISegmentedControl alloc] initWithItems:@[ @"Pad", @"Drive" ]];
  _mode.selectedSegmentIndex = _driving ? 1 : 0;
  [_mode addTarget:self action:@selector(modeChanged) forControlEvents:UIControlEventValueChanged];
  UIStackView* bar = [[UIStackView alloc] initWithArrangedSubviews:@[
    _mode, [self button:@"Smaller" action:@selector(smaller)], [self button:@"Bigger" action:@selector(bigger)],
    [self slider:@"Size" value:float(TouchSize()) min:0.6f max:1.6f action:@selector(sizeChanged:)],
    [self slider:@"Opacity" value:float(TouchOpacity()) min:0.15f max:1.0f action:@selector(opacityChanged:)],
    [self button:@"Reset" action:@selector(confirmReset)], [self button:@"Done" action:@selector(done)]
  ]];
  bar.spacing = 10;
  bar.alignment = UIStackViewAlignmentCenter;
  bar.translatesAutoresizingMaskIntoConstraints = NO;
  [self.view addSubview:bar];
  UILayoutGuide* safe = self.view.safeAreaLayoutGuide;
  [NSLayoutConstraint activateConstraints:@[
    [bar.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
    [bar.topAnchor constraintEqualToAnchor:safe.topAnchor constant:8],
    [hint.centerXAnchor constraintEqualToAnchor:safe.centerXAnchor],
    [hint.topAnchor constraintEqualToAnchor:bar.bottomAnchor constant:6],
  ]];
}

- (void)modeChanged {
  _driving = _mode.selectedSegmentIndex == 1;
  [_touch setEditing:YES driving:_driving];
}

- (void)smaller {
  [_touch resizeSelected:1.0 / 1.1];
}

- (void)bigger {
  [_touch resizeSelected:1.1];
}

- (void)sizeChanged:(UISlider*)slider {
  [NSUserDefaults.standardUserDefaults setDouble:slider.value forKey:@"nfsmw.touch.size"];
  [_touch setNeedsLayout];
}

- (void)opacityChanged:(UISlider*)slider {
  [NSUserDefaults.standardUserDefaults setDouble:slider.value forKey:@"nfsmw.touch.opacity"];
  _touch.alpha = 1.0;  // shown in full while editing; the game uses the setting
}

- (void)confirmReset {
  UIAlertController* alert = [UIAlertController alertControllerWithTitle:@"Reset the touch controls?"
                                                                 message:@"Positions, sizes and opacity go back to "
                                                                         @"the defaults, for both layouts."
                                                          preferredStyle:UIAlertControllerStyleAlert];
  [alert addAction:[UIAlertAction actionWithTitle:@"Cancel" style:UIAlertActionStyleCancel handler:nil]];
  [alert addAction:[UIAlertAction actionWithTitle:@"Reset"
                                            style:UIAlertActionStyleDestructive
                                          handler:^(UIAlertAction*) {
                                            NSUserDefaults* d = NSUserDefaults.standardUserDefaults;
                                            [d removeObjectForKey:kLayoutKey];
                                            [d removeObjectForKey:@"nfsmw.touch.size"];
                                            [d removeObjectForKey:@"nfsmw.touch.opacity"];
                                            [self dismissViewControllerAnimated:YES completion:nil];
                                          }]];
  [self presentViewController:alert animated:YES completion:nil];
}

- (void)done {
  [self dismissViewControllerAnimated:YES completion:nil];
}

@end

namespace nfsmw::touch {

UIViewController* MakeLayoutEditor() {
  NFSTouchLayoutEditor* editor = [[NFSTouchLayoutEditor alloc] init];
  editor.modalPresentationStyle = UIModalPresentationFullScreen;
  return editor;
}

void InstallFpsCounter() {
  static bool installed = false;
  UIWindow* window = installed ? nil : GameWindow();
  if (!window) {
    return;
  }
  NFSFpsLabel* label = [[NFSFpsLabel alloc] init];
  [window addSubview:label];
  [label layoutInSuperview];
  installed = true;
  REXLOG_INFO("[ios] FPS counter on screen");
}

void Install() {
  static bool installed = false;
  if (installed) {
    return;
  }
  UIWindow* window = GameWindow();
  if (!window) {
    REXLOG_ERROR("[touch] no window to put the touch controls on");
    return;
  }
  NFSTouchView* view = [[NFSTouchView alloc] initWithFrame:window.bounds];
  [window addSubview:view];
  if (REXCVAR_GET(ios_touch_auto_layout)) {
    [view followGame];
  }
  installed = true;
  REXLOG_INFO("[touch] touch controls on screen ({} x {} points)",
              int(window.bounds.size.width), int(window.bounds.size.height));
}

}  // namespace nfsmw::touch
