// NFSMW Recompiled (iOS) - look around the car with the mouse (free look)
//
// NFSMW has no look-around input while driving (its camera actions are
// change, look back, pull back; the right stick's up/down shifts gear), so
// mouse look moves the camera itself, as the PC Widescreen Fix's FreeLook
// does: it wraps eCreateLookAtMatrix(out, from, to, up) where
// CubicCameraMover::Update (the chase camera) calls it, and moves `from`
// (the eye) around `to` (the car).
//
// Found (November 2): on PC the Widescreen Fix's pattern lands in
// CubicCameraMover::Update (0x47D3C0, from its vtable) at the call 0x47DCBC
// to eCreateLookAtMatrix 0x6CF0A0. The USA Update is sub_82171DE8: the only
// function loading all five of the PC Update's float constants (65, 15,
// 5.333, 4, 1.5); its call after `sth r8,196(r7)` (the PC's word at +0xC4)
// is bl sub_8243CBF0 with r3 out, r4 from, r5 to, r6 up, returning to
// 0x821725E4, as the PC's push order. The camera view (PC +0x9C, set from
// +0x98) is +172 here (`lwz r4,168(r31)` / `stw r4,172(r31)`), the PC's
// +0xA4 is +180, so look-behind (PC +0xA1) is +177. Free look only in the
// two chase views (2, 3) and not looking back, as the Widescreen Fix.
//
// The mouse deltas come from keyboard_prompts.mm (GameController's mouse,
// chained after SDL's handler); the pointer is locked by the SDK's own mouse
// mode (mnk_mouse, its stick part at sensitivity 0) while driving.
//
// Right stick (dev133/dev134, Stefan, Nov 16): a physical controller's right
// stick points the same camera while driving: the camera looks at the car
// from the side the stick points to (up behind, toward you the front, left
// the car's right side) and is back behind the car the moment it is let
// go (dev133 turned it at a rate and eased back; Stefan wanted this). The game's XInputGetState wrapper sub_8262D6B8 (r3 user, r4 state;
// it branches to XamInputGetState) is wrapped: while driving and not in a
// drag race, the right stick is read there and taken out of the state the
// game sees, so its up/down no longer shifts gear. In a drag race, in menus,
// with the option off, or while a touch SHIFT button holds the right stick,
// the state goes to the game untouched (shifting as before).

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "nfsmw_pch.h"

#include "battery.h"
#include "touch_controls.h"

REXCVAR_DEFINE_BOOL(nfsmw_mouse_look, true, "Input", "Turn the chase camera with the mouse while driving");
REXCVAR_DEFINE_DOUBLE(nfsmw_mouse_look_speed, 1.0, "Input", "Mouse look speed (1 = 0.15 degrees per mouse count)");
REXCVAR_DEFINE_BOOL(nfsmw_mouse_look_invert, true, "Input", "Mouse look: moving the mouse up looks down");
REXCVAR_DEFINE_BOOL(nfsmw_stick_look, true, "Input",
                    "Turn the chase camera with the controller's right stick while driving (not in drag races, "
                    "where it shifts gear)");

namespace {

std::atomic<float> mouse_x{0}, mouse_y{0};
std::atomic<float> stick_x{0}, stick_y{0};  // right stick, -1..1, past its dead zone
float yaw_offset = 0, pitch_offset = 0;  // degrees, game thread
bool last_input_stick = false;
std::chrono::steady_clock::time_point last_input, last_call;
float last_to[3] = {};

constexpr float kDeg = 3.14159265f / 180.0f;
constexpr uint32_t kCubicReturn = 0x821725E4;

float LoadF(uint8_t* base, uint32_t a) {
  const uint32_t b = REX_LOAD_U32(a);
  float f;
  std::memcpy(&f, &b, 4);
  return f;
}
void StoreF(uint8_t* base, uint32_t a, float f) {
  uint32_t b;
  std::memcpy(&b, &f, 4);
  REX_STORE_U32(a, b);
}

}  // namespace

// dev135 (Stefan, Nov 16): the rear-view mirror's picture follows the main
// camera's direction (it samples the environment cube backwards from the
// view), so looking at the front showed what is ahead in it. While the free
// look is turned more than 20 degrees away from behind the car, the mirror
// (frame and picture) is hidden (game_scene_size.cpp, native_renderer.mm).
std::atomic<bool> g_look_hides_mirror{false};
extern "C" bool nfsmw_look_hides_mirror() { return g_look_hides_mirror.load(std::memory_order_relaxed); }

extern "C" void nfsmw_look_mouse(float dx, float dy) {
  mouse_x.store(mouse_x.load(std::memory_order_relaxed) + dx, std::memory_order_relaxed);
  mouse_y.store(mouse_y.load(std::memory_order_relaxed) + dy, std::memory_order_relaxed);
}

extern "C" void __imp__sub_8243CBF0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_8243CBF0) {
  if (ctx.lr != kCubicReturn) {
    __imp__sub_8243CBF0(ctx, base);
    return;
  }
  const auto now = std::chrono::steady_clock::now();
  const float dx = mouse_x.exchange(0), dy = mouse_y.exchange(0);
  const uint32_t mover = ctx.r31.u32, from = ctx.r4.u32, to = ctx.r5.u32;
  const uint32_t view = REX_LOAD_U32(mover + 172);
  const bool behind = REX_LOAD_U8(mover + 177) != 0;
  const float tx = LoadF(base, to), ty = LoadF(base, to + 4), tz = LoadF(base, to + 8);
  // A new race or view, or the car put somewhere else: back behind the car.
  const bool restart = now - last_call > std::chrono::milliseconds(250) ||
                       std::hypot(tx - last_to[0], ty - last_to[1]) > 20.0f;
  last_call = now;
  last_to[0] = tx, last_to[1] = ty, last_to[2] = tz;
  const bool mouse_on = REXCVAR_GET(nfsmw_mouse_look), stick_on = REXCVAR_GET(nfsmw_stick_look);
  if (restart || (!mouse_on && !stick_on) || behind || (view != 2 && view != 3)) {
    yaw_offset = pitch_offset = 0;
    g_look_hides_mirror.store(false, std::memory_order_relaxed);
    __imp__sub_8243CBF0(ctx, base);
    return;
  }
  const bool invert = REXCVAR_GET(nfsmw_mouse_look_invert);
  const float sx = stick_on ? stick_x.load(std::memory_order_relaxed) : 0.0f;
  const float sy = stick_on ? stick_y.load(std::memory_order_relaxed) : 0.0f;
  if (mouse_on && (dx != 0 || dy != 0)) {
    const float speed = 0.15f * float(REXCVAR_GET(nfsmw_mouse_look_speed));
    last_input = now;
    last_input_stick = false;
    yaw_offset -= dx * speed;
    pitch_offset += (invert ? -dy : dy) * speed;
    pitch_offset = std::clamp(pitch_offset, -20.0f, 60.0f);
    yaw_offset = std::remainder(yaw_offset, 360.0f);
  } else if (sx != 0 || sy != 0) {
    // dev134: the camera points where the stick points (up: behind, as
    // normal; toward you: the front; left: the car's right side; right: its
    // left side), at once, at the normal height.
    last_input = now;
    last_input_stick = true;
    yaw_offset = std::atan2(-sx, sy) / kDeg;
    pitch_offset = 0;
  } else if (last_input_stick) {
    // Stick let go: straight back behind the car.
    yaw_offset = pitch_offset = 0;
    last_input_stick = false;
  } else if (now - last_input > std::chrono::milliseconds(1500)) {
    // Idle: back behind the car over about half a second.
    yaw_offset *= 0.9f;
    pitch_offset *= 0.9f;
    if (std::fabs(yaw_offset) < 0.05f && std::fabs(pitch_offset) < 0.05f) yaw_offset = pitch_offset = 0;
  }
  g_look_hides_mirror.store(std::fabs(yaw_offset) > 20.0f, std::memory_order_relaxed);
  if (yaw_offset != 0 || pitch_offset != 0) {
    const float fx = LoadF(base, from) - tx, fy = LoadF(base, from + 4) - ty, fz = LoadF(base, from + 8) - tz;
    const float dist = std::sqrt(fx * fx + fy * fy + fz * fz);
    const float yaw = std::atan2(fy, fx) + yaw_offset * kDeg;
    const float pitch = std::clamp(std::atan2(fz, std::hypot(fx, fy)) + pitch_offset * kDeg, -1.39626f, 1.39626f);
    StoreF(base, from, tx + dist * std::cos(pitch) * std::cos(yaw));
    StoreF(base, from + 4, ty + dist * std::cos(pitch) * std::sin(yaw));
    StoreF(base, from + 8, tz + dist * std::sin(pitch));
  }
  __imp__sub_8243CBF0(ctx, base);
}

// The game's XInputGetState (see the top): the right stick to the camera.
extern "C" void __imp__sub_8262D6B8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_8262D6B8) {
  const uint32_t state = ctx.r4.u32;
  __imp__sub_8262D6B8(ctx, base);
  if (ctx.r3.u32 != 0 || state == 0) return;  // no pad on this user
  if (!REXCVAR_GET(nfsmw_stick_look) || nfsmw::battery::InMenu() != 0 || nfsmw::touch::DragRace() ||
      nfsmw::touch::RightStickHeld()) {
    stick_x.store(0, std::memory_order_relaxed);
    stick_y.store(0, std::memory_order_relaxed);
    return;
  }
  // X_INPUT_STATE: packet number, buttons, triggers, LX, LY, RX (+12), RY (+14).
  float x = float(int16_t(REX_LOAD_U16(state + 12))) / 32767.0f;
  float y = float(int16_t(REX_LOAD_U16(state + 14))) / 32767.0f;
  REX_STORE_U16(state + 12, 0);
  REX_STORE_U16(state + 14, 0);
  // Radial dead zone (XInput's right-stick 8689 / 32767), rescaled to 0..1.
  const float m = std::hypot(x, y);
  constexpr float kDead = 0.265f;
  if (m < kDead) {
    x = y = 0;
  } else {
    const float k = std::min((m - kDead) / (1.0f - kDead), 1.0f) / m;
    x *= k;
    y *= k;
  }
  stick_x.store(x, std::memory_order_relaxed);
  stick_y.store(y, std::memory_order_relaxed);
}

// SHOWCASE CAMERA: direct touch control (drag turns, pinch zooms).
//
// PC: Extra Options' GarageRotate / GarageZoom patch 0x476AC3 / 0x476B04, in
// ShowcaseCameraMover::Update (0x4769E0, vtable entry 0x894E98): in its user
// mode (+0x80 == 1) it adds rate x dt x 60 to the yaw (+0x94), the elevation
// (+0x90, kept to 94.5..110) and the distance (+0x98, kept to 4.65..6.65),
// the limits skipped when the debug byte 0x926134 is set (what the mod's
// "mov al, 1" does). USA: sub_82175EF8, the only function loading those five
// constants (110, 94.5, 6.65, 4.65, 0.125); mode +144, elevation +160, yaw
// +164, distance +168, the debug byte 0x82A2CE07 (the prototype's "Car Guys
// Camera"). The touch drags and pinches are added to those fields before
// the update runs, which then keeps them in range; "Unlimited showcase
// camera" sets the debug byte for this call only.
REXCVAR_DEFINE_BOOL(nfsmw_showcase_unlimited, false, "Game",
                    "Showcase: turn all the way round and zoom without limits (Extra Options' GarageRotate/Zoom)");

//
// The update turns the camera by itself when it sees no stick (its rates
// at +312 yaw and +308 elevation), and our drags are not stick input, so it
// kept spinning clockwise under the finger (dev28, Stefan). For 6 s after a
// drag, pinch or wheel notch, those two rates are held at 0.
namespace {
std::atomic<float> showcase_yaw{0}, showcase_elevation{0}, showcase_zoom{1};
std::atomic<int64_t> showcase_touched_ms{0};
int64_t SteadyMs() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now().time_since_epoch())
      .count();
}
}  // namespace

extern "C" void nfsmw_showcase_turn(float yaw_degrees, float elevation_degrees) {
  showcase_yaw.store(showcase_yaw.load() + yaw_degrees);
  showcase_elevation.store(showcase_elevation.load() + elevation_degrees);
  showcase_touched_ms.store(SteadyMs());
}

extern "C" void nfsmw_showcase_zoom(float factor) {
  showcase_zoom.store(showcase_zoom.load() * factor);
  showcase_touched_ms.store(SteadyMs());
}

extern "C" void __imp__sub_82175EF8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_82175EF8) {
  const uint32_t mover = ctx.r3.u32;
  const float yaw = showcase_yaw.exchange(0), elevation = showcase_elevation.exchange(0);
  const float zoom = showcase_zoom.exchange(1);
  if (REX_LOAD_U32(mover + 144) == 1) {
    if (SteadyMs() - showcase_touched_ms.load() < 6000) {
      StoreF(base, mover + 312, 0.0f);  // no turning by itself under the finger
      StoreF(base, mover + 308, 0.0f);
    }
    if (yaw != 0) StoreF(base, mover + 164, LoadF(base, mover + 164) + yaw);
    if (elevation != 0) StoreF(base, mover + 160, LoadF(base, mover + 160) + elevation);
    if (zoom != 1) StoreF(base, mover + 168, LoadF(base, mover + 168) * zoom);
  }
  const bool unlimited = REXCVAR_GET(nfsmw_showcase_unlimited);
  const uint8_t flag = REX_LOAD_U8(0x82A2CE07);
  if (unlimited) REX_STORE_U8(0x82A2CE07, 1);
  __imp__sub_82175EF8(ctx, base);
  if (unlimited) REX_STORE_U8(0x82A2CE07, flag);
}
