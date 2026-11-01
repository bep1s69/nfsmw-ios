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

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(nfsmw_mouse_look, true, "Input", "Turn the chase camera with the mouse while driving");
REXCVAR_DEFINE_DOUBLE(nfsmw_mouse_look_speed, 1.0, "Input", "Mouse look speed (1 = 0.15 degrees per mouse count)");
REXCVAR_DEFINE_BOOL(nfsmw_mouse_look_invert, false, "Input", "Mouse look: moving the mouse up looks down");

namespace {

std::atomic<float> mouse_x{0}, mouse_y{0};
float yaw_offset = 0, pitch_offset = 0;  // degrees, game thread
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
  if (restart || !REXCVAR_GET(nfsmw_mouse_look) || behind || (view != 2 && view != 3)) {
    yaw_offset = pitch_offset = 0;
    __imp__sub_8243CBF0(ctx, base);
    return;
  }
  const float speed = 0.15f * float(REXCVAR_GET(nfsmw_mouse_look_speed));
  if (dx != 0 || dy != 0) {
    last_input = now;
    yaw_offset -= dx * speed;
    pitch_offset += (REXCVAR_GET(nfsmw_mouse_look_invert) ? -dy : dy) * speed;
    pitch_offset = std::clamp(pitch_offset, -20.0f, 60.0f);
    yaw_offset = std::remainder(yaw_offset, 360.0f);
  } else if (now - last_input > std::chrono::milliseconds(1500)) {
    // Idle: back behind the car over about half a second.
    yaw_offset *= 0.9f;
    pitch_offset *= 0.9f;
    if (std::fabs(yaw_offset) < 0.05f && std::fabs(pitch_offset) < 0.05f) yaw_offset = pitch_offset = 0;
  }
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
