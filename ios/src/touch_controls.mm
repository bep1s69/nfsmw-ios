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
//     steering circle, shift buttons, nitrous and look back on the left; speedbreaker,
//     handbrake and tall brake/accelerate pads on the right; camera at the
//     top and reset at the bottom. Which pad button each action presses is in
//     the kDrive* table below.
//
// Not here yet, and on Android: the layout editor (with size/opacity), tilt
// steering and switching layouts by itself with the part of the game (that
// needs the game's state; on Android only the native engine could tell).
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

#include <rex/logging.h>

#include "touch_controls.h"

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
};

}  // namespace

@interface NFSTouchView : UIView
@end

@implementation NFSTouchView {
  std::vector<Control> _controls;
  NSMapTable<UITouch*, NSNumber*>* _owners;  // touch -> control index
  CGRect _toggle;
  CGRect _modeToggle;  // DRIVE/PAD
  BOOL _driving;
  BOOL _controlsVisible;
  UIImpactFeedbackGenerator* _haptic;
}

- (instancetype)initWithFrame:(CGRect)frame {
  if ((self = [super initWithFrame:frame])) {
    self.backgroundColor = UIColor.clearColor;
    self.opaque = NO;
    self.multipleTouchEnabled = YES;
    self.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    _owners = [NSMapTable strongToStrongObjectsMapTable];
    _controlsVisible = !GCController.current;
    _driving = [NSUserDefaults.standardUserDefaults boolForKey:@"nfsmw.touch.driving"];
    _haptic = [[UIImpactFeedbackGenerator alloc] initWithStyle:UIImpactFeedbackStyleLight];
    NSNotificationCenter* nc = NSNotificationCenter.defaultCenter;
    [nc addObserver:self
           selector:@selector(controllerConnected:)
               name:GCControllerDidConnectNotification
             object:nil];
    [nc addObserver:self
           selector:@selector(controllerDisconnected:)
               name:GCControllerDidDisconnectNotification
             object:nil];
  }
  return self;
}

- (void)controllerConnected:(NSNotification*)note {
  [self setControlsVisible:NO];
}

- (void)controllerDisconnected:(NSNotification*)note {
  if (GCController.controllers.count == 0) {
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
  _controls.clear();
  _toggle = CGRectMake(w * .5 - unit * .9, h * .02, unit * 1.8, unit * .5);
  _modeToggle = CGRectOffset(_toggle, -(_toggle.size.width + unit * .3), 0);
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
  [self releaseAll];
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
}

// Touches go to the game's own view where there is nothing of ours.
- (UIView*)hitTest:(CGPoint)p withEvent:(UIEvent*)event {
  if (!_controlsVisible) {
    return self;  // any tap brings the controls back
  }
  if (CGRectContainsPoint(_toggle, p) || CGRectContainsPoint(_modeToggle, p)) {
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
  SetPadState(buttons, axes[0], axes[1], axes[2], axes[3], triggers[0], triggers[1]);
  [self setNeedsDisplay];
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

  for (const Control& c : _controls) {
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
    if ([scene isKindOfClass:UIWindowScene.class]) {
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

namespace nfsmw::touch {

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
  installed = true;
  REXLOG_INFO("[touch] touch controls on screen ({} x {} points)",
              int(window.bounds.size.width), int(window.bounds.size.height));
}

}  // namespace nfsmw::touch
