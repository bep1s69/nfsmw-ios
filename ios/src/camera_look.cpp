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

#include <mach/mach.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "nfsmw_pch.h"

#include "battery.h"
#include "touch_controls.h"

REXCVAR_DEFINE_BOOL(nfsmw_fov_probe, false, "Input", "Diagnostics: log fields that look like the camera's field of view as they change");
REXCVAR_DEFINE_BOOL(nfsmw_look_fixed_orbit, true, "Input", "Free look: the camera orbits the car fixed in the car's frame (not the chase camera's spring)");
REXCVAR_DEFINE_BOOL(nfsmw_look_probe, false, "Input", "Diagnostics: log where the car's matrix is (free look)");
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
  // dev175 diagnostic: the field of view (Stefan: with the camera fixed to
  // the car, it still moves with gear shifts and acceleration: likely the
  // game's speed zoom). Every 0.5 s while driving, the first-level objects
  // the mover points to (and the mover) are compared with the previous
  // sample; fields that changed and look like a field of view (u16 binary
  // angle 9000-19000 = 50-104 degrees, or a float 40-110 degrees or
  // 0.7-1.9 radians) are logged with their old and new values.
  if (REXCVAR_GET(nfsmw_fov_probe) && (view == 2 || view == 3)) {
    static auto next_fov = now;
    static int fov_lines = 0;
    static std::vector<std::pair<uint32_t, std::vector<uint8_t>>> prev;
    if (now >= next_fov && fov_lines < 80) {
      next_fov = now + std::chrono::milliseconds(500);
      auto rd = [&](uint32_t a, uint8_t* out, size_t n) {
        vm_size_t got = 0;
        return vm_read_overwrite(mach_task_self(), vm_address_t(base + a), n, vm_address_t(out), &got) ==
                   KERN_SUCCESS && got == n;
      };
      std::vector<uint32_t> objs{mover};
      uint8_t mv[0x400];
      if (rd(mover, mv, sizeof(mv)))
        for (uint32_t o = 0; o < sizeof(mv); o += 4) {
          const uint32_t p1 = uint32_t(mv[o]) << 24 | uint32_t(mv[o + 1]) << 16 | uint32_t(mv[o + 2]) << 8 | mv[o + 3];
          if (p1 >= 0x40000000u && p1 < 0xC0000000u && std::find(objs.begin(), objs.end(), p1) == objs.end() &&
              objs.size() < 40)
            objs.push_back(p1);
        }
      std::string changed;
      std::vector<std::pair<uint32_t, std::vector<uint8_t>>> cur;
      for (uint32_t ob : objs) {
        std::vector<uint8_t> b(0x600);
        if (!rd(ob, b.data(), b.size())) continue;
        for (const auto& [pa, pb] : prev) {
          if (pa != ob) continue;
          for (uint32_t k = 0; k + 4 <= b.size(); k += 2) {
            const uint16_t a16 = uint16_t(pb[k] << 8 | pb[k + 1]), b16 = uint16_t(b[k] << 8 | b[k + 1]);
            if (a16 != b16 && a16 >= 9000 && a16 <= 19000 && b16 >= 9000 && b16 <= 19000 && changed.size() < 900)
              changed += fmt::format(" [{:08x}+{:x} u16 {}->{}]", ob, k, a16, b16);
            if (k % 4) continue;
            const uint32_t av = uint32_t(pb[k]) << 24 | uint32_t(pb[k + 1]) << 16 | uint32_t(pb[k + 2]) << 8 | pb[k + 3];
            const uint32_t bv = uint32_t(b[k]) << 24 | uint32_t(b[k + 1]) << 16 | uint32_t(b[k + 2]) << 8 | b[k + 3];
            float af, bf;
            std::memcpy(&af, &av, 4);
            std::memcpy(&bf, &bv, 4);
            const bool deg = af > 40 && af < 110 && bf > 40 && bf < 110;
            const bool rad = af > 0.7f && af < 1.9f && bf > 0.7f && bf < 1.9f;
            if (av != bv && (deg || rad) && std::fabs(af - bf) < 0.25f * af && changed.size() < 900)
              changed += fmt::format(" [{:08x}+{:x} f {:.4f}->{:.4f}]", ob, k, af, bf);
          }
        }
        cur.emplace_back(ob, std::move(b));
      }
      prev = std::move(cur);
      if (!changed.empty()) {
        ++fov_lines;
        REXLOG_INFO("[fov-probe] mover {:08x}:{}", mover, changed);
      }
    }
  }
  // dev172 diagnostic (fixed free look): the car's position and matrix.
  // dev171 (14 Pro Max log): the mover holds the look-at point at +0x140
  // and its pointers within 64 MB only led back into itself. Now every
  // guest pointer in the mover (two levels deep) is read safely
  // (vm_read_overwrite: an unmapped page is an error, not a crash) and
  // searched for a position within 10 units of the look-at point with three
  // unit-length rows before it.
  if (REXCVAR_GET(nfsmw_look_probe) && (view == 2 || view == 3)) {
    static auto next = now;
    static int lines = 0;
    if (now >= next && lines < 40) {
      next = now + std::chrono::seconds(3);
      auto read = [&](uint32_t a, uint8_t* out, size_t n) {
        vm_size_t got = 0;
        return vm_read_overwrite(mach_task_self(), vm_address_t(base + a), n, vm_address_t(out), &got) ==
                   KERN_SUCCESS && got == n;
      };
      auto be32 = [](const uint8_t* p) { return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]; };
      auto f32 = [&](const uint8_t* p) { const uint32_t v = be32(p); float f; std::memcpy(&f, &v, 4); return f; };
      auto unit = [&](const uint8_t* p) {
        const float x = f32(p), y = f32(p + 4), z = f32(p + 8), l = std::sqrt(x * x + y * y + z * z);
        return std::isfinite(l) && std::fabs(l - 1.0f) < 0.02f;
      };
      std::string found;
      std::vector<uint32_t> seen;
      auto scan = [&](uint32_t obj, const std::string& path) {
        uint8_t buf[0x600];
        if (!read(obj, buf, sizeof(buf))) return false;
        for (uint32_t k = 0; k + 12 <= sizeof(buf); k += 4) {
          const float x = f32(buf + k), y = f32(buf + k + 4), z = f32(buf + k + 8);
          if (!std::isfinite(x) || std::fabs(x - tx) > 10 || std::fabs(y - ty) > 10 || std::fabs(z - tz) > 10) continue;
          const bool matrix = k >= 48 && unit(buf + k - 48) && unit(buf + k - 32) && unit(buf + k - 16);
          if (found.size() < 900)
            found += fmt::format(" [{}+{:x}{} ({:.2f},{:.2f},{:.2f})]", path, k, matrix ? " MATRIX" : "", x, y, z);
        }
        return true;
      };
      uint8_t mv[0x400];
      if (read(mover, mv, sizeof(mv))) {
        for (uint32_t o = 0; o < sizeof(mv); o += 4) {
          const uint32_t p1 = be32(mv + o);
          if (p1 < 0x40000000u || p1 >= 0xC0000000u || std::find(seen.begin(), seen.end(), p1) != seen.end()) continue;
          if (p1 >= mover && p1 < mover + 0x400) continue;  // itself
          seen.push_back(p1);
          if (!scan(p1, fmt::format("+{:x}", o))) continue;
          uint8_t ob[0x100];
          if (!read(p1, ob, sizeof(ob))) continue;
          for (uint32_t o2 = 0; o2 < sizeof(ob); o2 += 4) {
            const uint32_t p2 = be32(ob + o2);
            if (p2 < 0x40000000u || p2 >= 0xC0000000u || std::find(seen.begin(), seen.end(), p2) != seen.end()) continue;
            seen.push_back(p2);
            if (seen.size() > 600) break;
            scan(p2, fmt::format("+{:x}>+{:x}", o, o2));
          }
        }
      }
      ++lines;
      REXLOG_INFO("[look-probe] to ({:.2f},{:.2f},{:.2f}) mover {:08x}:{}", tx, ty, tz, mover,
                  found.empty() ? " none" : found);
    }
  }
  // A new race or view, or the car put somewhere else: back behind the car.
  const bool restart = now - last_call > std::chrono::milliseconds(250) ||
                       std::hypot(tx - last_to[0], ty - last_to[1]) > 20.0f;
  const float dt = std::min(std::chrono::duration<float>(now - last_call).count(), 0.1f);
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
  } else if (sx != 0 || sy != 0 || last_input_stick) {
    // dev134: the camera points where the stick points (up: behind, as
    // normal; toward you: the front; left: the car's right side; right: its
    // left side), at the normal height, back behind the car on release.
    // dev138 (Stefan: choppy): it follows that angle with a 50 ms time
    // constant instead of jumping to it every frame (stick wobble and the
    // game's input steps showed as jerks); within half a degree it is there.
    const bool held = sx != 0 || sy != 0;
    const float target = held ? std::atan2(-sx, sy) / kDeg : 0.0f;
    const float step = std::remainder(target - yaw_offset, 360.0f);
    // dev166 (Stefan): looking back (stick down, within 30 degrees of
    // straight back) is instant, both ways, like a look-back button; left
    // and right keep the easing.
    static bool looking_back = false;
    const bool back_now = held && std::fabs(target) > 150.0f;
    // Only the moment it enters the back zone (and the release from it)
    // snaps; moving the stick within it eases like the rest (dev168,
    // Stefan: dev166 snapped every frame there: jittery).
    const bool snap = (back_now && !looking_back) || (looking_back && !back_now && !held);
    looking_back = back_now;
    yaw_offset = snap || std::fabs(step) < 0.5f ? target : yaw_offset + step * (1.0f - std::exp(-dt / 0.05f));
    yaw_offset = std::remainder(yaw_offset, 360.0f);
    pitch_offset = 0;
    last_input = now;
    last_input_stick = held || yaw_offset != 0;
  } else if (now - last_input > std::chrono::milliseconds(1500)) {
    // Idle: back behind the car over about half a second.
    yaw_offset *= 0.9f;
    pitch_offset *= 0.9f;
    if (std::fabs(yaw_offset) < 0.05f && std::fabs(pitch_offset) < 0.05f) yaw_offset = pitch_offset = 0;
  }
  g_look_hides_mirror.store(std::fabs(yaw_offset) > 20.0f, std::memory_order_relaxed);
  // dev173 (fixed free look, Stefan): the car's own matrix, found by the
  // dev172 probe at [mover+0x250]+0x24 (three rows of 16 bytes, position at
  // +0x54, about 0.5 below the look-at point). While not looking, where the
  // chase camera sits in the car's frame (behind, above) and the look-at
  // point's height are averaged; while looking, the eye orbits the car at
  // those, turned about the car's up axis: no spring with acceleration or
  // gear shifts, and it tilts with the car on slopes.
  {
    static float rest_back = 0, rest_up = 0, rest_target_up = 0;
    bool ok = false;
    float cp[3], ax[3][3];
    // The car's matrix: found by a search like the dev172 probe's and kept
    // (dev177: in a Challenge Series pursuit the dev176 path, mover+0x250 ->
    // +0x4, did not hold and the free look fell back to the sprung camera).
    // Paths: mover+o1 -> object (+o2 -> object) with a position within 10
    // of the look-at point at +k and three unit rows before it.
    if (REXCVAR_GET(nfsmw_look_fixed_orbit)) {
      static uint32_t path_mover = 0, o1 = 0x250, o2 = 4, kpos = 0x54;
      static bool two = true;
      static auto next_search = now;
      auto rd = [&](uint32_t a, uint8_t* out, size_t n) {
        vm_size_t got = 0;
        return a >= 0x40000000u && a < 0xC0000000u &&
               vm_read_overwrite(mach_task_self(), vm_address_t(base + a), n, vm_address_t(out), &got) ==
                   KERN_SUCCESS && got == n;
      };
      auto be = [](const uint8_t* q) { return uint32_t(q[0]) << 24 | uint32_t(q[1]) << 16 | uint32_t(q[2]) << 8 | q[3]; };
      auto fl = [&](const uint8_t* q) { const uint32_t v = be(q); float x; std::memcpy(&x, &v, 4); return x; };
      auto matrix_at = [&](const uint8_t* q, bool fill) {  // q points at the position; rows 48..16 bytes before
        const float px = fl(q), py = fl(q + 4), pz = fl(q + 8);
        if (!std::isfinite(px) || std::fabs(px - tx) > 10 || std::fabs(py - ty) > 10 || std::fabs(pz - tz) > 10)
          return false;
        float r[3][3];
        for (int i = 0; i < 3; ++i) {
          for (int c = 0; c < 3; ++c) r[i][c] = fl(q - 48 + i * 16 + c * 4);
          const float l = std::sqrt(r[i][0] * r[i][0] + r[i][1] * r[i][1] + r[i][2] * r[i][2]);
          if (!std::isfinite(l) || std::fabs(l - 1.0f) > 0.02f) return false;
        }
        if (fill) {
          std::memcpy(ax, r, sizeof(r));
          cp[0] = px, cp[1] = py, cp[2] = pz;
        }
        return true;
      };
      auto try_path = [&](uint32_t m, uint32_t a1, uint32_t a2, bool second, uint32_t k) {
        uint8_t q[4];
        if (!rd(m + a1, q, 4)) return false;
        uint32_t obj = be(q);
        if (second) {
          if (!rd(obj + a2, q, 4)) return false;
          obj = be(q);
        }
        uint8_t mm[64];
        return k >= 48 && rd(obj + k - 48, mm, sizeof(mm)) && matrix_at(mm + 48, true);
      };
      ok = path_mover == mover && try_path(mover, o1, o2, two, kpos);
      if (!ok && (path_mover != mover || now >= next_search)) {
        next_search = now + std::chrono::seconds(3);
        uint8_t mv[0x400];
        bool found = false;
        if (rd(mover, mv, sizeof(mv))) {
          for (uint32_t a1 = 0; a1 < sizeof(mv) && !found; a1 += 4) {
            const uint32_t p1 = be(mv + a1);
            if (p1 >= mover && p1 < mover + 0x400) continue;
            uint8_t ob[0x600];
            if (!rd(p1, ob, sizeof(ob))) continue;
            for (uint32_t k = 48; k + 12 <= sizeof(ob) && !found; k += 4)
              if (matrix_at(ob + k, false)) found = true, o1 = a1, two = false, kpos = k;
            for (uint32_t a2 = 0; a2 < 0x100 && !found; a2 += 4) {
              const uint32_t p2 = be(ob + a2);
              uint8_t o2b[0x600];
              if (!rd(p2, o2b, sizeof(o2b))) continue;
              for (uint32_t k = 48; k + 12 <= sizeof(o2b) && !found; k += 4)
                if (matrix_at(o2b + k, false)) found = true, o1 = a1, o2 = a2, two = true, kpos = k;
            }
          }
        }
        if (found) {
          path_mover = mover;
          ok = try_path(mover, o1, o2, two, kpos);
          REXLOG_INFO("[look] car matrix: mover+{:x}{} +{:x} ({})", o1, two ? fmt::format(" > +{:x}", o2) : "", kpos,
                      ok ? "ok" : "not confirmed");
        } else {
          static int misses = 0;
          if (misses++ < 10) REXLOG_INFO("[look] car matrix not found (mover {:08x})", mover);
        }
      }
    }
    if (ok) {
      // Up: the row with the largest world z; forward: of the other two, the
      // one along the chase camera's view (eye to look-at), signed.
      int up = 0;
      for (int r = 1; r < 3; ++r)
        if (std::fabs(ax[r][2]) > std::fabs(ax[up][2])) up = r;
      float U[3] = {ax[up][0], ax[up][1], ax[up][2]};
      if (U[2] < 0) U[0] = -U[0], U[1] = -U[1], U[2] = -U[2];
      const float ex = LoadF(base, from), ey = LoadF(base, from + 4), ez = LoadF(base, from + 8);
      const float vx = tx - ex, vy = ty - ey, vz = tz - ez;
      int fw = up == 0 ? 1 : 0;
      const int other = 3 - up - fw;
      auto dotv = [&](int r) { return ax[r][0] * vx + ax[r][1] * vy + ax[r][2] * vz; };
      if (std::fabs(dotv(other)) > std::fabs(dotv(fw))) fw = other;
      float F[3] = {ax[fw][0], ax[fw][1], ax[fw][2]};
      if (dotv(fw) < 0) F[0] = -F[0], F[1] = -F[1], F[2] = -F[2];
      const float rx = ex - cp[0], ry = ey - cp[1], rz = ez - cp[2];
      if (yaw_offset == 0 && pitch_offset == 0) {
        const float back = -(rx * F[0] + ry * F[1] + rz * F[2]), upv = rx * U[0] + ry * U[1] + rz * U[2];
        const float tup = (tx - cp[0]) * U[0] + (ty - cp[1]) * U[1] + (tz - cp[2]) * U[2];
        if (back > 0.5f && back < 40.0f && std::fabs(upv) < 20.0f) {
          const float k = rest_back == 0 ? 1.0f : 1.0f - std::exp(-dt / 1.0f);
          rest_back += (back - rest_back) * k;
          rest_up += (upv - rest_up) * k;
          rest_target_up += (tup - rest_target_up) * k;
        }
      } else if (rest_back > 0) {
        static int said = 0;
        if (said++ == 0)
          REXLOG_INFO("[look] fixed to the car: {:.2f} behind, {:.2f} up, look-at {:.2f} up", rest_back, rest_up,
                      rest_target_up);
        // Behind the car (-F) turned by the yaw about U (Rodrigues), plus height.
        const float a = yaw_offset * kDeg, c = std::cos(a), sn = std::sin(a);
        const float bx = -F[0], by = -F[1], bz = -F[2];
        const float cx = U[1] * bz - U[2] * by, cy = U[2] * bx - U[0] * bz, cz = U[0] * by - U[1] * bx;
        const float d = U[0] * bx + U[1] * by + U[2] * bz;
        const float hx = bx * c + cx * sn + U[0] * d * (1 - c), hy = by * c + cy * sn + U[1] * d * (1 - c),
                    hz = bz * c + cz * sn + U[2] * d * (1 - c);
        const float px = cp[0] + U[0] * rest_target_up, py = cp[1] + U[1] * rest_target_up,
                    pz = cp[2] + U[2] * rest_target_up;
        // `to` may be the mover's own (sprung) target: restored after the
        // call so its spring is not disturbed.
        const float otx = tx, oty = ty, otz = tz;
        StoreF(base, to, px);
        StoreF(base, to + 4, py);
        StoreF(base, to + 8, pz);
        StoreF(base, from, cp[0] + hx * rest_back + U[0] * rest_up);
        StoreF(base, from + 4, cp[1] + hy * rest_back + U[1] * rest_up);
        StoreF(base, from + 8, cp[2] + hz * rest_back + U[2] * rest_up);
        __imp__sub_8243CBF0(ctx, base);
        StoreF(base, to, otx);
        StoreF(base, to + 4, oty);
        StoreF(base, to + 8, otz);
        return;
      }
    }
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
