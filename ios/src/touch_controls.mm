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
// Steering in the DRIVE layout (ios_touch_steering): a dynamic joystick under
// the thumb in the bottom-left quarter (fading out on release), the fixed
// circle, or two buttons.
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

#include "native_renderer.h"

#include "battery.h"
#include "touch_controls.h"

REXCVAR_DEFINE_BOOL(ios_touch_auto_layout, true, "Input",
                    "Touch controls: the DRIVE layout while driving, the PAD layout in menus and pause "
                    "screens, switched by themselves");
REXCVAR_DEFINE_STRING(ios_touch_steering, "dynamic", "Input",
                      "Touch controls, DRIVE layout: how to steer. dynamic: a joystick wherever the "
                      "thumb lands in the bottom-left quarter, fading out when it lifts; fixed: the "
                      "steering circle in its place; buttons: two buttons, left and right");
REXCVAR_DEFINE_DOUBLE(ios_touch_idle_opacity, 0.35, "Input",
                      "Touch controls, DRIVE layout: their opacity after 3 s without a touch, as a "
                      "share of the chosen opacity (1 = no dimming)");
REXCVAR_DEFINE_BOOL(ios_touch_menu_gestures, true, "Input",
                    "Touch controls in menus and pause screens (with ios_touch_auto_layout): no "
                    "overlay; a swipe pushes the left stick that way, a tap presses A, a two-finger "
                    "tap B. The PAD pill brings the full gamepad back until the next layout change");
REXCVAR_DEFINE_BOOL(ios_touch_native, true, "Input",
                    "Touch controls drawn into the game's frame with the native renderer. Off: a "
                    "UIKit layer over the game, whose redraws delay the game's frame by a refresh");

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

// nfsmw::touch::SetDriveContext, from the game's thread.
std::atomic<int> g_drive_context{0};

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
  float left_x = 0;         // buttons that push the left stick left/right (steering buttons)
  // The dynamic steering joystick: it takes a touch anywhere in `zone`,
  // comes up under the thumb and fades out once it lifts.
  bool dynamic = false;
  CGRect zone = CGRectZero;
  // State.
  bool pressed = false;
  CGPoint knob{0, 0};  // sticks: -1..1
  int dpad_bits = 0;
  float fade = 0;  // dynamic joystick after release: 1 shown .. 0 gone

  bool Contains(CGPoint p) const {
    if (dynamic) {
      return CGRectContainsPoint(zone, p);
    }
    return Distance(p) <= 1;
  }

  // How far p is from the control, 1 at the edge of what it takes: more
  // than it draws, for thumbs (touches between two controls go to the
  // nearer, controlAt).
  CGFloat Distance(CGPoint p) const {
    if (kind == Kind::kRectButton || kind == Kind::kTrigger) {
      const CGFloat slack = 18;
      return std::max(std::fabs(p.x - center.x) / (size.width * 0.5 + slack),
                      std::fabs(p.y - center.y) / (size.height * 0.5 + slack));
    }
    const CGFloat r = kind == Kind::kStick ? radius * 1.4 : radius * 1.45 + 6;
    return std::hypot(p.x - center.x, p.y - center.y) / r;
  }

  // What it covers on screen (with its outline and label), for redrawing
  // only what changed.
  CGRect Bounds() const {
    const bool round = kind == Kind::kStick || kind == Kind::kRoundButton;
    const CGFloat w = round ? radius * 2 : size.width, h = round ? radius * 2 : size.height;
    return CGRectInset(CGRectMake(center.x - w / 2, center.y - h / 2, w, h), -6, -6);
  }

  // Its look: pressed, where the knob is, which D-pad arrows; and for the
  // dynamic joystick where it is and how faded.
  uint64_t Look() const {
    uint64_t look = uint64_t(pressed) | uint64_t(dpad_bits & 0xFFFF) << 1 |
                    uint64_t(uint16_t(int16_t(knob.x * 1000))) << 17 |
                    uint64_t(uint16_t(int16_t(knob.y * 1000))) << 33;
    if (dynamic) {
      look ^= (uint64_t(uint16_t(center.x)) << 7 | uint64_t(uint16_t(center.y)) << 29 |
               uint64_t(uint8_t(fade * 255)) << 49) * 0x9E3779B97F4A7C15ull;
    }
    return look;
  }

  // Drawn at all: the dynamic joystick only while held or fading out.
  bool Shown() const { return !dynamic || pressed || fade > 0; }
};

}  // namespace

@interface NFSTouchView : UIView
- (void)followGame;
@end

@implementation NFSTouchView {
  std::vector<Control> _controls;
  std::vector<uint64_t> _drawnLook;  // each control's look when last drawn
  std::vector<CGRect> _drawnBounds;  // and where it was (the dynamic joystick moves)
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
  NSString* _steering;  // ios_touch_steering the layout was made with
  int _context;         // g_drive_context the layout was made with
  NSTimer* _fadeTimer;  // the dynamic joystick fading out
  // Dimmed after 3 s without a touch while driving (ios_touch_idle_opacity).
  NSTimeInterval _lastTouch;
  CGFloat _dim;         // 1 full .. ios_touch_idle_opacity
  CGFloat _dimTarget;
  NSTimer* _dimTimer;
  // Menus without the overlay (ios_touch_menu_gestures): one gesture at a
  // time, from its first finger down to the last one up.
  BOOL _gestures;
  BOOL _padOverride;  // the PAD pill: the full gamepad in this menu
  CGPoint _gStart;
  NSTimeInterval _gTime;
  BOOL _gSwiping;
  int _gFingers;   // the most fingers down at once
  int _gDown;      // fingers down now
  CGRect _steerZone;    // editor: where the dynamic joystick works, outlined
  int _selected;
  CGPoint _grab;  // the finger's offset from the selected control's centre
  // Drawn into the native frame (ios_touch_native, IPA111): the picture kept
  // here, redrawn where it changed, at most once per run loop turn.
  BOOL _nativeMode;
  BOOL _drawingNative;
  BOOL _nativeQueued;
  CGRect _nativeDirty;
  std::vector<uint8_t> _nativePixels;
  int _nativeW, _nativeH;
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

// The editor runs from the launcher, before the game sets the cvar: the
// launcher hands it the setting (MakeLayoutEditor).
static NSString* g_editor_steering = @"dynamic";

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
    _dim = _dimTarget = 1;
    _lastTouch = NSDate.timeIntervalSinceReferenceDate;
    self.alpha = TouchOpacity();
    // The drawing is recorded here and rasterized on Core Animation's own
    // thread, not on the main thread (~10 ms a second while driving).
    self.layer.drawsAsynchronously = YES;
    _nativeDirty = CGRectNull;
    // Native drawing starts and stops with the native layer (checked twice a
    // second, as the FPS counter does).
    __weak NFSTouchView* weak = self;
    [NSTimer scheduledTimerWithTimeInterval:0.5
                                    repeats:YES
                                      block:^(NSTimer* timer) {
                                        NFSTouchView* view = weak;
                                        if (!view) {
                                          [timer invalidate];
                                          return;
                                        }
                                        [view syncNativeMode];
                                        [view syncSteering];
                                        [view syncDim];
                                      }];
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
  _padOverride = NO;
  [self setNeedsLayout];
  REXLOG_INFO("[touch] {} layout", driving ? "DRIVE" : "PAD");
}

- (NSString*)steeringMode {
  if (_editing) return g_editor_steering;
  return [NSString stringWithUTF8String:REXCVAR_GET(ios_touch_steering).c_str()];
}

// The steering choice changed in the options while playing, or the HUD
// shows a circle or a race: a new layout.
- (void)syncSteering {
  if (_driving && !_editing && g_drive_context.load() != _context) {
    [self releaseAll];
    [self setNeedsLayout];
    return;
  }
  if (_driving && _steering && ![_steering isEqualToString:[self steeringMode]]) {
    REXLOG_INFO("[touch] steering: {}", [self steeringMode].UTF8String);
    [self setNeedsLayout];
  }
}

// Dimmed after 3 s without a touch in the DRIVE layout; back at once on a
// touch. Eased over ~0.3 s (the whole overlay redrawn 10 times).
- (void)syncDim {
  const CGFloat idle = CGFloat(std::clamp(REXCVAR_GET(ios_touch_idle_opacity), 0.1, 1.0));
  const bool resting = _driving && !_editing && _owners.count == 0 &&
                       NSDate.timeIntervalSinceReferenceDate - _lastTouch > 3.0;
  [self dimTo:resting ? idle : 1];
}

- (void)dimTo:(CGFloat)target {
  if (target == _dimTarget) return;
  _dimTarget = target;
  if (_dimTimer) return;
  __weak NFSTouchView* weak = self;
  _dimTimer = [NSTimer scheduledTimerWithTimeInterval:1.0 / 30
                                              repeats:YES
                                                block:^(NSTimer* timer) {
                                                  [weak dimTick:timer];
                                                }];
}

- (void)dimTick:(NSTimer*)timer {
  const CGFloat step = 0.07;
  _dim = _dim < _dimTarget ? std::min(_dimTarget, _dim + step * 2) : std::max(_dimTarget, _dim - step);
  if (_dim == _dimTarget) {
    [timer invalidate];
    if (_dimTimer == timer) _dimTimer = nil;
  }
  self.alpha = _editing ? 1.0 : TouchOpacity() * _dim;
  [self setNeedsDisplay];
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
  _drawnBounds.clear();
  _controls.clear();
  [_fadeTimer invalidate];
  _fadeTimer = nil;
  _steerZone = CGRectZero;
  _toggle = CGRectMake(w * .5 - unit * .9, h * .02, unit * 1.8, unit * .5);
  _modeToggle = CGRectOffset(_toggle, -(_toggle.size.width + unit * .3), 0);
  static const bool snap = rex::cvar::Query<bool>("nfsmw_native_dump_manual");
  _snap = snap ? CGRectOffset(_toggle, _toggle.size.width + unit * .3, 0) : CGRectZero;
  if (_driving) {
    _gestures = NO;
    [self layoutDriving:w height:h unit:unit];
    [self releaseAll];
    return;
  }
  static const bool gestures =
      rex::cvar::Query<bool>("ios_touch_menu_gestures") && rex::cvar::Query<bool>("ios_touch_auto_layout");
  _gestures = gestures && !_editing && !_padOverride;
  if (_gestures) {
    _gDown = 0;
    [self releaseAll];
    return;  // nothing drawn but the pills
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
  self.alpha = _editing ? 1.0 : TouchOpacity() * _dim;
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
  // Steering (ios_touch_steering): the circle where it is, the same
  // circle under the thumb anywhere in the bottom-left quarter (not in the
  // editor: it has no place of its own), or two buttons.
  _steering = [self steeringMode];
  if ([_steering isEqualToString:@"buttons"]) {
    Control left{Kind::kRoundButton, @"◀", P(.06, .80), unit * .55};
    left.left_x = -1;
    _controls.push_back(left);
    Control right{Kind::kRoundButton, @"▶", P(.16, .80), unit * .55};
    right.left_x = 1;
    _controls.push_back(right);
  } else if ([_steering isEqualToString:@"fixed"]) {
    Control steer{Kind::kStick, @"", P(.115, .78), unit * 1.15};
    steer.axis = 0;
    steer.horizontal = true;
    _controls.push_back(steer);
  } else {
    _steerZone = CGRectMake(0, h * .5, w * .5, h * .5);
  }
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
  // What the game puts on the D-pad while driving (its controls screen):
  // up enters a shop or engages an event, left the world map, right the
  // SMS messages, down the Blacklist (or the race's / pursuit's details).
  // One button each, around where the D-pad was.
  // Each only when it does something (the HUD tells, SetDriveContext):
  // ENTER in a circle, MAP and SMS outside races; LIST always (the
  // Blacklist, or the race's / pursuit's details). The editor shows all.
  _context = g_drive_context.load();
  const bool all = _editing;
  const CGPoint pad = P(.11, .27);
  const CGFloat off = unit * .62, r = unit * .36;
  if (all || (_context & nfsmw::touch::kInCircle)) round(@"ENTER", CGPointMake(pad.x, pad.y - off), r, kUp);
  if (all || !(_context & nfsmw::touch::kInRace)) {
    round(@"MAP", CGPointMake(pad.x - off, pad.y), r, kLeft);
    round(@"SMS", CGPointMake(pad.x + off, pad.y), r, kRight);
  }
  round(@"LIST", CGPointMake(pad.x, pad.y + off), r, kDown);
  [self applyCustomLayout];
  // Last, so the buttons inside its zone (nitrous, look back) come first.
  if (!CGRectIsEmpty(_steerZone) && !_editing) {
    Control steer{Kind::kStick, @"", P(.115, .78), unit * 1.15 * TouchSize()};
    steer.axis = 0;
    steer.horizontal = true;
    steer.dynamic = true;
    steer.zone = _steerZone;
    _controls.push_back(steer);
  }
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
  if (_gestures) {
    // The whole screen, but what is over the game besides us (the options
    // gear) keeps its touches.
    for (UIView* v in self.superview.subviews) {
      if (v == self || v.hidden || v.alpha < 0.01 || !v.userInteractionEnabled ||
          CGRectEqualToRect(v.frame, self.superview.bounds))
        continue;
      if ([v hitTest:[self convertPoint:p toView:v] withEvent:event]) return nil;
    }
    return self;
  }
  for (const Control& c : _controls) {
    if (c.Contains(p)) {
      return self;
    }
  }
  return nil;
}

// The nearest control that takes p; the dynamic joystick only where no
// other does.
- (int)controlAt:(CGPoint)p {
  int best = -1, zone = -1;
  CGFloat nearest = 1;
  for (size_t i = 0; i < _controls.size(); ++i) {
    const Control& c = _controls[i];
    if (c.dynamic) {
      if (c.Contains(p)) zone = int(i);
      continue;
    }
    const CGFloat d = c.Distance(p);
    if (d <= nearest) {
      nearest = d;
      best = int(i);
    }
  }
  return best >= 0 ? best : zone;
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
  _lastTouch = NSDate.timeIntervalSinceReferenceDate;
  [self dimTo:1];
  if (_gestures) {
    bool on_pill = false;
    for (UITouch* t in touches) {
      const CGPoint p = [t locationInView:self];
      on_pill = on_pill || CGRectContainsPoint(_toggle, p) || CGRectContainsPoint(_modeToggle, p) ||
                CGRectContainsPoint(_snap, p);
    }
    if (!on_pill) {
      [self gestureBegan:touches];
      return;
    }
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
    if (CGRectContainsPoint(_modeToggle, p) && _gestures) {
      _padOverride = YES;  // the full gamepad, until the next layout change
      [_haptic impactOccurred];
      [self setNeedsLayout];
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
    if (c.dynamic && !c.pressed) {
      // Under the thumb, whole on screen.
      const CGFloat w = self.bounds.size.width, h = self.bounds.size.height;
      c.center = CGPointMake(std::clamp(p.x, c.radius, w - c.radius), std::clamp(p.y, c.radius, h - c.radius));
      c.fade = 0;
    }
    c.pressed = true;
    if (_driving && c.bit & (kUp | kDown | kLeft | kRight)) {
      REXLOG_INFO("[touch] {}", c.label.UTF8String);  // marks the [hud-watch] log
    }
    [self updateControl:c at:p];
    haptic = haptic || c.kind == Kind::kRoundButton || c.kind == Kind::kRectButton;
  }
  if (haptic) {
    [_haptic impactOccurred];
  }
  [self sendState];
}

// ---------------------------------------------------------------------------
//  Menus: swipe and tap (as on Android)
// ---------------------------------------------------------------------------
- (void)gestureBegan:(NSSet<UITouch*>*)touches {
  if (_gDown == 0) {
    _gStart = [touches.anyObject locationInView:self];
    _gTime = NSDate.timeIntervalSinceReferenceDate;
    _gSwiping = NO;
    _gFingers = 0;
  }
  _gDown += int(touches.count);
  _gFingers = std::max(_gFingers, _gDown);
}

// The first finger's way from where it went down: past 14 points the left
// stick goes that way (the larger of across and down, so a menu moves one
// way), all the way at 40.
- (void)gestureMoved:(UITouch*)touch {
  if (_gFingers > 1) return;
  const CGPoint p = [touch locationInView:self];
  const CGFloat dx = p.x - _gStart.x, dy = p.y - _gStart.y;
  const CGFloat d = std::hypot(dx, dy);
  if (d < 14 && !_gSwiping) return;
  _gSwiping = YES;
  const float k = float(std::clamp((d - 8) / 32, 0.0, 1.0));
  const bool across = std::fabs(dx) >= std::fabs(dy);
  SetPadState(0, across ? (dx > 0 ? k : -k) : 0, across ? 0 : (dy > 0 ? k : -k), 0, 0, 0, 0);
}

- (void)gestureEnded:(NSSet<UITouch*>*)touches {
  _gDown = std::max(0, _gDown - int(touches.count));
  if (_gDown > 0) return;
  SetPadState(0, 0, 0, 0, 0, 0, 0);
  // A tap: short and still. One finger A, two B.
  if (_gSwiping || NSDate.timeIntervalSinceReferenceDate - _gTime > 0.4) return;
  const int button = _gFingers >= 2 ? kB : kA;
  REXLOG_INFO("[touch] menu tap: {}", button == kB ? "B" : "A");
  [_haptic impactOccurred];
  SetPadState(button, 0, 0, 0, 0, 0, 0);
  dispatch_after(dispatch_time(DISPATCH_TIME_NOW, int64_t(0.1 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
    if (g_buttons == button) SetPadState(0, 0, 0, 0, 0, 0, 0);
  });
}

- (void)touchesMoved:(NSSet<UITouch*>*)touches withEvent:(UIEvent*)event {
  if (_gestures && !_editing) {
    [self gestureMoved:touches.anyObject];
    return;
  }
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
  _lastTouch = NSDate.timeIntervalSinceReferenceDate;
  if (_gestures) {
    [self gestureEnded:touches];
    return;
  }
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
      if (c.dynamic) {
        c.fade = 1;
        [self startFade];
      }
    }
  }
  [self sendState];
}

// The dynamic joystick fades out in a quarter of a second.
- (void)startFade {
  if (_fadeTimer) return;
  __weak NFSTouchView* weak = self;
  _fadeTimer = [NSTimer scheduledTimerWithTimeInterval:1.0 / 30
                                               repeats:YES
                                                 block:^(NSTimer* timer) {
                                                   [weak fadeTick:timer];
                                                 }];
}

- (void)fadeTick:(NSTimer*)timer {
  bool fading = false;
  for (Control& c : _controls) {
    if (c.dynamic && !c.pressed && c.fade > 0) {
      c.fade = std::max(0.0f, c.fade - 1.0f / (0.25f * 30));
      fading = fading || c.fade > 0;
    }
  }
  if (!fading) {
    [timer invalidate];
    if (_fadeTimer == timer) _fadeTimer = nil;
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
    c.fade = 0;
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
          axes[0] += c.left_x;  // both steering buttons held: straight
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
    _drawnBounds.assign(_controls.size(), CGRectNull);
  }
  CGRect dirty = CGRectNull;
  for (size_t i = 0; i < _controls.size(); ++i) {
    const uint64_t look = _controls[i].Look();
    if (look != _drawnLook[i]) {
      _drawnLook[i] = look;
      // Where it was too: the dynamic joystick moves.
      dirty = CGRectUnion(dirty, CGRectUnion(_drawnBounds[i], _controls[i].Bounds()));
      _drawnBounds[i] = _controls[i].Bounds();
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

// The DRIVE layout's buttons drawn as symbols (SF Symbols, iOS 18); a label
// without one stays text.
static NSString* SymbolFor(NSString* label) {
  static NSDictionary<NSString*, NSString*>* symbols = @{
    @"NOS" : @"flame.fill",
    @"LOOK\nBACK" : @"eye.fill",
    @"SPEED\nBREAKER" : @"stopwatch.fill",
    @"HAND\nBRAKE" : @"exclamationmark.brakesignal",
    @"GAS" : @"pedal.accelerator.fill",
    @"BRAKE" : @"pedal.brake.fill",
    @"CAM" : @"camera.fill",
    @"PAUSE" : @"pause.fill",
    @"RESET" : @"arrow.counterclockwise",
    @"ENTER" : @"flag.checkered",
    @"MAP" : @"map.fill",
    @"SMS" : @"message.fill",
    @"LIST" : @"list.number",
    @"UP" : @"chevron.up",
    @"DOWN" : @"chevron.down",
    @"◀" : @"arrowtriangle.left.fill",
    @"▶" : @"arrowtriangle.right.fill",
  };
  return symbols[label];
}

// A control's label: its symbol in the DRIVE layout, `size` points tall,
// or the text.
- (void)drawIcon:(NSString*)label at:(CGPoint)p size:(CGFloat)size fit:(CGFloat)fit {
  NSString* name = _driving ? SymbolFor(label) : nil;
  UIImage* image = nil;
  if (name) {
    UIImageSymbolConfiguration* config =
        [UIImageSymbolConfiguration configurationWithPointSize:size weight:UIImageSymbolWeightSemibold];
    image = [[UIImage systemImageNamed:name withConfiguration:config]
        imageWithTintColor:[UIColor colorWithWhite:1 alpha:0.9]
             renderingMode:UIImageRenderingModeAlwaysOriginal];
  }
  if (!image) {
    [self drawLabel:label at:p size:size * 0.88 fit:fit];
    return;
  }
  CGSize s = image.size;
  if (s.width > fit) s = CGSizeMake(fit, s.height * fit / s.width);
  [image drawInRect:CGRectMake(p.x - s.width / 2, p.y - s.height / 2, s.width, s.height)];
}

// With the native renderer the controls are drawn into the game's frame: a
// redraw of this view's layer delayed the game's frame of that refresh by one
// refresh (33 ms spikes while steering, Oct 28 donut traces), as the FPS
// label did (IPA86-88). The view stays for the touches; its own layer is left
// empty and untouched.
- (BOOL)wantsNative {
  static const bool on = rex::cvar::Query<bool>("ios_touch_native");
  return on && !_editing && nfsmw_native_overlay_active();
}

- (void)syncNativeMode {
  const BOOL want = [self wantsNative];
  if (want == _nativeMode) return;
  _nativeMode = want;
  REXLOG_INFO("[touch] drawn {}", want ? "into the native frame" : "by UIKit");
  if (want) {
    _nativePixels.clear();  // a full picture first
    [self queueNative:self.bounds];
  } else {
    nfsmw_native_set_touch_overlay(nullptr, 0, 0, 0, 0, 0, 0);
  }
  [super setNeedsDisplay];  // the layer: emptied, or drawn again
}

- (void)setNeedsDisplay {
  [self setNeedsDisplayInRect:self.bounds];
}

- (void)setNeedsDisplayInRect:(CGRect)rect {
  if (_nativeMode != [self wantsNative]) [self syncNativeMode];
  if (_nativeMode) {
    [self queueNative:rect];
    return;
  }
  [super setNeedsDisplayInRect:rect];
}

- (void)queueNative:(CGRect)rect {
  _nativeDirty = CGRectUnion(_nativeDirty, rect);
  if (_nativeQueued) return;
  _nativeQueued = YES;
  __weak NFSTouchView* weak = self;
  dispatch_async(dispatch_get_main_queue(), ^{
    [weak drawNative];
  });
}

- (void)drawNative {
  _nativeQueued = NO;
  CGRect dirty = _nativeDirty;
  _nativeDirty = CGRectNull;
  if (!_nativeMode) return;
  const CGRect bounds = self.bounds;
  const CGFloat scale = UIScreen.mainScreen.scale;
  const int w = int(std::ceil(bounds.size.width * scale)), h = int(std::ceil(bounds.size.height * scale));
  if (w <= 0 || h <= 0) return;
  if (int(_nativePixels.size()) != w * h * 4 || _nativeW != w || _nativeH != h) {
    _nativePixels.assign(size_t(w) * size_t(h) * 4, 0);
    _nativeW = w;
    _nativeH = h;
    dirty = bounds;
  }
  dirty = CGRectIntersection(dirty, bounds);
  if (CGRectIsEmpty(dirty)) return;
  // Whole pixels around the rectangle, then back to points.
  const int px = int(std::floor(dirty.origin.x * scale)), py = int(std::floor(dirty.origin.y * scale));
  const int pw = std::min(w, int(std::ceil(CGRectGetMaxX(dirty) * scale))) - px;
  const int ph = std::min(h, int(std::ceil(CGRectGetMaxY(dirty) * scale))) - py;
  if (pw <= 0 || ph <= 0) return;
  dirty = CGRectMake(px / scale, py / scale, pw / scale, ph / scale);
  CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
  CGContextRef context =
      CGBitmapContextCreate(_nativePixels.data(), size_t(w), size_t(h), 8, size_t(w) * 4, space,
                            kCGImageAlphaPremultipliedFirst | kCGBitmapByteOrder32Little);  // BGRA
  CGColorSpaceRelease(space);
  if (!context) return;
  // UIKit's top-left origin, in points.
  CGContextTranslateCTM(context, 0, h);
  CGContextScaleCTM(context, scale, -scale);
  CGContextClearRect(context, dirty);
  CGContextClipToRect(context, dirty);
  // The view's opacity, which its layer would have applied.
  CGContextSetAlpha(context, self.alpha);
  CGContextBeginTransparencyLayer(context, nullptr);
  UIGraphicsPushContext(context);
  _drawingNative = YES;
  [self drawRect:dirty];
  _drawingNative = NO;
  UIGraphicsPopContext();
  CGContextEndTransparencyLayer(context);
  CGContextRelease(context);
  nfsmw_native_set_touch_overlay(_nativePixels.data(), w, h, px, py, pw, ph);
}

- (void)drawRect:(CGRect)dirty {
  if (_nativeMode && !_drawingNative) return;  // drawn into the native frame instead
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
    // The dynamic joystick's zone: it has no place to move.
    if (!CGRectIsEmpty(_steerZone)) {
      UIBezierPath* zone = [UIBezierPath bezierPathWithRoundedRect:CGRectInset(_steerZone, 6, 6) cornerRadius:12];
      const CGFloat dash[] = {8, 6};
      [zone setLineDash:dash count:2 phase:0];
      zone.lineWidth = 1.5;
      [stroke setStroke];
      [zone stroke];
      [self drawLabel:@"STEERING\nthumb anywhere here"
                   at:CGPointMake(CGRectGetMidX(_steerZone), CGRectGetMidY(_steerZone))
                 size:_steerZone.size.height * 0.16];
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
  [self drawLabel:(_driving || _gestures ? @"PAD" : @"DRIVE")
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
    if (!CGRectIntersectsRect(c.Bounds(), dirty) || !c.Shown()) continue;  // not in the part being redrawn
    switch (c.kind) {
      case Kind::kStick: {
        CGContextRef context = UIGraphicsGetCurrentContext();
        CGContextSaveGState(context);
        if (!c.pressed && c.dynamic) CGContextSetAlpha(context, c.fade);
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
        CGContextRestoreGState(context);
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
        [self drawIcon:c.label at:c.center size:c.radius * 0.9 fit:c.radius * 1.4];
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
        [self drawIcon:c.label
                    at:c.center
                  size:std::min(c.size.width, c.size.height) * 0.45
                   fit:c.size.width * 0.75];
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
  NSString* text = fps < 0 ? @"-- fps"
                   : ms > 0 ? [NSString stringWithFormat:@"%.0f fps · %.1f ms", fps, ms]
                            : [NSString stringWithFormat:@"%.0f fps", fps];
  if ([self drawIntoNativeFrame:text]) {
    return;  // the label itself is left alone (hidden)
  }
  self.text = text;
  [self layoutInSuperview];
}

// With the native renderer the counter is drawn into the game's frame
// (IPA88): as a label over the game's layer, each text change delayed the
// game's frame of that refresh by one 120 Hz refresh (a 25 + 8 ms stutter
// pair twice a second, IPA86 logs). The label stays, hidden and untouched.
- (bool)drawIntoNativeFrame:(NSString*)text {
  static NSString* drawn = nil;
  const bool native = nfsmw_native_overlay_active();
  if (self.hidden != native) {
    self.hidden = native;
    if (!native) {
      nfsmw_native_set_fps_overlay(nullptr, 0, 0, 0, 0, 0, 0);
      drawn = nil;
    }
  }
  UIView* parent = self.superview;
  if (!native || !parent) {
    return false;
  }
  if ([text isEqualToString:drawn]) {
    return true;
  }
  drawn = text;
  const CGSize size = [text sizeWithAttributes:@{NSFontAttributeName : self.font}];
  const UIEdgeInsets safe = parent.safeAreaInsets;
  const CGRect frame = CGRectMake(safe.left + 8, safe.top + 6, std::ceil(size.width) + 16,
                                  std::ceil(size.height) + 6);
  const CGRect bounds = parent.bounds;
  const int drawable_w = nfsmw_native_drawable_width();
  // IPA89 drew it at the frame's resolution: blurrier than IPA88's screen
  // scale (Stefan), so the screen's scale again, with the frame's as a floor.
  const CGFloat scale = std::max(UIScreen.mainScreen.scale,
                                 drawable_w > 0 ? CGFloat(drawable_w) / bounds.size.width : 0.0);
  const int w = int(std::ceil(frame.size.width * scale)), h = int(std::ceil(frame.size.height * scale));
  if (w <= 0 || h <= 0 || bounds.size.width <= 0 || bounds.size.height <= 0) {
    return true;
  }
  std::vector<uint8_t> pixels(size_t(w) * size_t(h) * 4, 0);
  CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
  CGContextRef context =
      CGBitmapContextCreate(pixels.data(), size_t(w), size_t(h), 8, size_t(w) * 4, space,
                            kCGImageAlphaPremultipliedFirst | kCGBitmapByteOrder32Little);  // BGRA
  CGColorSpaceRelease(space);
  if (!context) {
    return true;
  }
  // UIKit's top-left origin, in points.
  CGContextTranslateCTM(context, 0, h);
  CGContextScaleCTM(context, scale, -scale);
  CGContextSetRGBFillColor(context, 0.08, 0.08, 0.08, 1.0);
  CGContextFillRect(context, CGRectMake(0, 0, frame.size.width, frame.size.height));
  UIGraphicsPushContext(context);
  NSMutableParagraphStyle* centered = [NSMutableParagraphStyle new];
  centered.alignment = NSTextAlignmentCenter;
  [text drawInRect:CGRectMake(0, (frame.size.height - size.height) * 0.5, frame.size.width, size.height)
         withAttributes:@{
           NSFontAttributeName : self.font,
           NSForegroundColorAttributeName : UIColor.whiteColor,
           NSParagraphStyleAttributeName : centered
         }];
  UIGraphicsPopContext();
  CGContextRelease(context);
  nfsmw_native_set_fps_overlay(pixels.data(), w, h, float(frame.origin.x / bounds.size.width),
                               float(frame.origin.y / bounds.size.height),
                               float(frame.size.width / bounds.size.width),
                               float(frame.size.height / bounds.size.height));
  return true;
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

UIViewController* MakeLayoutEditor(NSString* steering) {
  g_editor_steering = steering.length ? steering : @"dynamic";
  NFSTouchLayoutEditor* editor = [[NFSTouchLayoutEditor alloc] init];
  editor.modalPresentationStyle = UIModalPresentationFullScreen;
  return editor;
}

void SetDriveContext(int bits) { g_drive_context.store(bits); }

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
