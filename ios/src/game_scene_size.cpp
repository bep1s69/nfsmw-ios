// NFSMW Recompiled - the size of the game's scene: 4:3 and wider than 16:9
//
// 4:3 (nfsmw_sd_scene_720)
// ========================
//
// At 4:3 the game takes its SD path: mode 0 of the renderer's anti-aliasing
// table, one 640x480 strip with 2x MSAA, scaled up to the screen
// (render_probe.cpp showed it). Here, with the cvar on, mode 0 becomes one
// 960x720 strip without MSAA: 720 lines like the HD modes, at 1x internal
// resolution (the scaled-resolution path made 4:3 at 2x run at ~40 fps).
//
// USA addresses:
//   sub_824581A8  the renderer's constructor: builds the mode table (layout in
//                 render_targets.cpp: +4 strips, +28 width, +52 height, +76
//                 MSAA, +100+64*mode the strip rectangles). Mode 0's entry is
//                 rewritten after it, before the render target sets are
//                 registered from the table.
//   sub_824585E0  sets the mode (r4) and the four render-size words at
//                 0x82A2CF68 (width, height, width, height; 640/480 for mode 0).
//                 After it, for mode 0, 960/720.
//   sub_82440D80  the HUD's title-safe matrix. In SD it scales by 576/width and
//                 448/height of the screen-size pair (0x82A2CF70/74): 0.9 at
//                 640x480, but 0.6 at 960x720, which shrank the HUD to the
//                 middle of the screen (and put the mirror's frame away from
//                 its picture). It runs with that pair at 640x480.
// EDRAM: 960x720 color + depth at 4 bytes each is 5.3 MB of the 10 MB; with
// 2x MSAA it would not fit, so mode 0 loses its MSAA.
//
// Wider than 16:9 (nfsmw_wide_scene_width, e.g. 1560 for 19.5:9)
// ===============================================================
//
// The video mode is 1560x720 (the launcher's --resolution). The game takes its
// HD path (width >= 1280) but has 1280 written in: the HD modes 2-5 of the
// table (1280x736 one strip, or 3 strips of 1280x256 with 4x MSAA) and the
// render-size words, which sub_82440188 (XGetVideoMode's caller) and
// sub_82441828 (switching between modes 2-4 while running) set to 1280.
//   - the constructor's hook makes modes 2-5 one strip without MSAA, the
//     surface 1600x736 (EDRAM: 9.4 MB, it fits only without MSAA), the strip
//     rectangle 0,0,width,720;
//   - nfsmw_scene_size_fixup, called by render_targets.cpp after every mode
//     choice and every render target bind, turns 1280 in the words into the
//     width. Those two functions are hooked there already, so this is a call
//     instead of a second hook.
//   - the HUD: sub_82440D80 builds the HUD's matrix and hands it to
//     sub_82453768 (r4 = the matrix, row-major floats). In HD it scales x by
//     0.75 of y, (4:3)/(16:9), whatever the width: at 1560 the HUD came out
//     22 % wider. The x scale is multiplied by 1280/width there, so the HUD
//     keeps its shapes (in the middle 16:9 of the screen).
//   - then the HUD out to the edges, as the PC Widescreen Fix does.
//     sub_822AA6D0 (the HUD's widescreen switch, FEngHud::SetWideScreenMode on
//     PC) sends the HUD package the widescreen message and moves the minimap
//     (sub_8229C020) by -120 FE units: the 16:9 layout is the 4:3 one with
//     the sides 120 units out. Wider, the sides go out by more:
//     120 * (aspect - 16/9) / (16/9 - 4/3), 105 at 1560x720. After it:
//       - the left and right groups of the package (hashes 0x1603009E and
//         0x5D0101F1, found with sub_8227FD58, FindObject(package, hash)) are
//         moved by that much, at every call: their x is object+44 -> +28,
//         and if the package's own script moved them since, that is the new
//         base;
//       - when it has just switched the minimap to widescreen, the minimap
//         and its pivot (0x82A2C60C) go out by the same, the way the game
//         moved them (the minimap's +184 and its children's x).

#include <cstdint>
#include <cstring>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_sd_scene_720, false, "Game",
                    "4:3 (SD) scene at 960x720 without MSAA instead of 640x480 with 2x MSAA "
                    "(experimental)")
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);
// The HUD's title-safe shrink (sub_82440D80): the 360 draws the HUD smaller,
// about the middle of the screen, to stay inside a TV's safe area: in SD by
// 576/640 x 448/480, in HD by the constant at kHdSafeScale. A phone or tablet
// shows the whole picture, and the PS2 version draws its HUD at full size
// (its margins measured at 4:3: ours were 0.9 x 0.933 of them). Off: as the
// PS2's, in SD (4:3) only: in HD (16:9 and wider, 0.92) the full-size HUD
// came too close to the edges of a 19.5:9 iPhone.
REXCVAR_DEFINE_BOOL(nfsmw_hud_title_safe, false, "Game",
                    "Shrink the HUD into the TV title-safe area like the Xbox 360 (off: full size, like the PS2)");
REXCVAR_DEFINE_INT32(nfsmw_wide_scene_width, 0, "Game",
                     "Scene width for video modes wider than 16:9 (e.g. 1560 for 19.5:9); 0 = "
                     "the game's 1280 (experimental)")
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

extern "C" void __imp__sub_824581A8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_824585E0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82440D80(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82453768(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822AA6D0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void sub_8227FD58(PPCContext& __restrict ctx, uint8_t* base);

namespace {

constexpr uint32_t kWidth = 960;
constexpr uint32_t kHeight = 720;
constexpr uint32_t kRenderSize = 0x82A2CF68;
// sub_82440D80's constants: SD 576 and 448 (the safe area in pixels), HD the
// safe scale (x and y), then x's 4:3/16:9.
constexpr uint32_t kSdSafeWidth = 0x820B0660;
constexpr uint32_t kSdSafeHeight = 0x820B065C;
constexpr uint32_t kHdSafeScale = 0x820B0664;
constexpr uint32_t kHdAspect = 0x82062DC4;

// The wide scene's width, or 0. Only wider than 1280 and up to 1600 (EDRAM).
float LoadF(uint8_t* base, uint32_t address) {
  const uint32_t bits = REX_LOAD_U32(address);
  float v;
  std::memcpy(&v, &bits, sizeof(v));
  return v;
}

void StoreF(uint8_t* base, uint32_t address, float v) {
  uint32_t bits;
  std::memcpy(&bits, &v, sizeof(bits));
  REX_STORE_U32(address, bits);
}

// Set while sub_82440D80 runs: its call to sub_82453768 hands on the HUD's matrix.
thread_local bool g_hud_matrix = false;

uint32_t WideWidth() {
  const int32_t w = REXCVAR_GET(nfsmw_wide_scene_width);
  return (w > 1280 && w <= 1600) ? uint32_t(w) & ~7u : 0;
}

void WidenTable(uint8_t* base, uint32_t renderer, uint32_t width) {
  const uint32_t rect2 = renderer + 100 + 64 * 2;
  if (REX_LOAD_U32(renderer + 4 + 8) != 1 || REX_LOAD_U32(renderer + 28 + 8) != 1280 ||
      REX_LOAD_U32(rect2 + 8) != 1280 || REX_LOAD_U32(rect2 + 12) != 720) {
    REXLOG_WARN("[wide-scene] mode 2 is not the 1280x736 strip expected: left as it is");
    return;
  }
  for (uint32_t m = 2; m < 6; ++m) {
    const uint32_t rect = renderer + 100 + 64 * m;
    REX_STORE_U32(renderer + 4 + 4 * m, 1);
    REX_STORE_U32(renderer + 28 + 4 * m, 1600);
    REX_STORE_U32(renderer + 52 + 4 * m, 736);
    REX_STORE_U32(renderer + 76 + 4 * m, 0);
    REX_STORE_U32(rect, 0);
    REX_STORE_U32(rect + 4, 0);
    REX_STORE_U32(rect + 8, width);
    REX_STORE_U32(rect + 12, 720);
  }
  REXLOG_INFO("[wide-scene] modes 2-5: one {}x720 strip without MSAA", width);
}

}  // namespace

// Called by render_targets.cpp (weak there) after the game chooses a mode and
// at every render target bind: 1280 in the render-size words becomes the wide
// width.
extern "C" void nfsmw_scene_size_fixup(uint8_t* base) {
  const uint32_t width = WideWidth();
  if (!width) {
    return;
  }
  for (uint32_t i : {0u, 2u}) {
    if (REX_LOAD_U32(kRenderSize + 4 * i) == 1280) {
      REX_STORE_U32(kRenderSize + 4 * i, width);
    }
  }
}

extern "C" REX_FUNC(sub_824581A8) {
  const uint32_t renderer = ctx.r3.u32;
  __imp__sub_824581A8(ctx, base);
  if (!renderer) {
    return;
  }
  if (const uint32_t width = WideWidth()) {
    WidenTable(base, renderer, width);
  }
  if (!REXCVAR_GET(nfsmw_sd_scene_720)) {
    return;
  }
  // Only the table as analyzed: mode 0 one 640x480 strip, rect 0,0,640,480.
  const uint32_t rect = renderer + 100;
  if (REX_LOAD_U32(renderer + 4) != 1 || REX_LOAD_U32(renderer + 28) != 640 ||
      REX_LOAD_U32(renderer + 52) != 480 || REX_LOAD_U32(rect + 8) != 640 ||
      REX_LOAD_U32(rect + 12) != 480) {
    REXLOG_WARN("[sd-scene] mode 0 is not the 640x480 strip expected: left as it is");
    return;
  }
  REX_STORE_U32(renderer + 28, kWidth);
  REX_STORE_U32(renderer + 52, kHeight);
  REX_STORE_U32(renderer + 76, 0);
  REX_STORE_U32(rect + 8, kWidth);
  REX_STORE_U32(rect + 12, kHeight);
  REXLOG_INFO("[sd-scene] mode 0: one {}x{} strip without MSAA", kWidth, kHeight);
}

extern "C" REX_FUNC(sub_824585E0) {
  const uint32_t renderer = ctx.r3.u32;
  __imp__sub_824585E0(ctx, base);
  if (REXCVAR_GET(nfsmw_sd_scene_720) && renderer && REX_LOAD_U32(renderer) == 0 &&
      REX_LOAD_U32(kRenderSize) == 640) {
    REX_STORE_U32(kRenderSize, kWidth);
    REX_STORE_U32(kRenderSize + 4, kHeight);
    REX_STORE_U32(kRenderSize + 8, kWidth);
    REX_STORE_U32(kRenderSize + 12, kHeight);
  }
}

extern "C" REX_FUNC(sub_82440D80) {
  const bool sd_720 = REXCVAR_GET(nfsmw_sd_scene_720) && REX_LOAD_U32(kRenderSize + 8) == kWidth &&
                      REX_LOAD_U32(kRenderSize + 12) == kHeight;
  if (sd_720) {
    REX_STORE_U32(kRenderSize + 8, 640);
    REX_STORE_U32(kRenderSize + 12, 480);
  }
  g_hud_matrix = true;
  __imp__sub_82440D80(ctx, base);
  g_hud_matrix = false;
  if (sd_720) {
    REX_STORE_U32(kRenderSize + 8, kWidth);
    REX_STORE_U32(kRenderSize + 12, kHeight);
  }
}

// The HUD's safe-area scale (x, y) in the matrix sub_82440D80 is making:
// SD 576/width x 448/height of the pair it read, HD the constant. 1 when the
// values are not the expected ones (left as they are).
void HudSafeScale(uint8_t* base, float& x, float& y) {
  x = y = 1.0f;
  const bool hd = REX_LOAD_U8(0x828F4A8F) != 0;  // the branch sub_82440D80 takes
  if (hd) {
    const float k = LoadF(base, kHdSafeScale);
    if (k > 0.75f && k < 1.0f) x = y = k;
  } else {
    const float w = float(REX_LOAD_U32(kRenderSize + 8)), h = float(REX_LOAD_U32(kRenderSize + 12));
    const float sw = LoadF(base, kSdSafeWidth), sh = LoadF(base, kSdSafeHeight);
    if (w > 0 && h > 0 && sw > 0.75f * w && sw < w && sh > 0.75f * h && sh < h) {
      x = sw / w;
      y = sh / h;
    }
  }
  static bool said = false;
  if (!said) {
    said = true;
    REXLOG_INFO("[hud] {} title-safe scale {:.3f} x {:.3f} (HD constant {:.3f}, aspect {:.3f}; SD {:.0f}x{:.0f}): {}",
                hd ? "HD" : "SD", x, y, LoadF(base, kHdSafeScale), LoadF(base, kHdAspect),
                LoadF(base, kSdSafeWidth), LoadF(base, kSdSafeHeight),
                REXCVAR_GET(nfsmw_hud_title_safe) || hd ? "kept" : "removed");
  }
  if (hd) x = y = 1.0f;  // kept in HD (see nfsmw_hud_title_safe)
}

extern "C" REX_FUNC(sub_82453768) {
  if (g_hud_matrix && ctx.r4.u32) {
    const uint32_t m = ctx.r4.u32;
    float sx = LoadF(base, m), sy = LoadF(base, m + 20);
    if (const uint32_t width = WideWidth()) sx *= 1280.0f / float(width);
    float safe_x, safe_y;
    HudSafeScale(base, safe_x, safe_y);
    if (!REXCVAR_GET(nfsmw_hud_title_safe)) {
      sx /= safe_x;
      sy /= safe_y;
    }
    StoreF(base, m, sx);
    StoreF(base, m + 20, sy);
  }
  __imp__sub_82453768(ctx, base);
}

namespace {

constexpr uint32_t kLeftGroup = 0x1603009E;
constexpr uint32_t kRightGroup = 0x5D0101F1;
constexpr uint32_t kMinimapPivotX = 0x82A2C60C;

// HUD units the sides go out beyond the game's own 16:9 layout.
float ExtraHudOffset(uint32_t width) {
  const float aspect = float(width) / 720.0f;
  return 120.0f * (aspect - 16.0f / 9.0f) / (16.0f / 9.0f - 4.0f / 3.0f);
}

// One group: the x the game (or its script) last gave it, and what was written.
struct Moved {
  uint32_t object = 0;
  float written = 0;
};
Moved g_left, g_right;

void MoveGroup(uint8_t* base, uint32_t object, float offset, Moved& moved) {
  if (!object) {
    return;
  }
  const uint32_t data = REX_LOAD_U32(object + 44);
  if (!data) {
    return;
  }
  const float x = LoadF(base, data + 28);
  if (moved.object == object && x == moved.written) {
    return;  // already moved, and nothing moved it since
  }
  moved.object = object;
  moved.written = x + offset;
  StoreF(base, data + 28, moved.written);
}

uint32_t FindObject(PPCContext& ctx, uint8_t* base, uint32_t package, uint32_t hash) {
  ctx.r3.u64 = package;
  ctx.r4.u64 = hash;
  sub_8227FD58(ctx, base);
  return ctx.r3.u32;
}

}  // namespace

extern "C" REX_FUNC(sub_822AA6D0) {
  const uint32_t hud = ctx.r3.u32;
  const uint8_t was_wide = hud ? REX_LOAD_U8(hud + 816) : 0;
  __imp__sub_822AA6D0(ctx, base);
  const uint32_t width = WideWidth();
  if (!width || !hud || !REX_LOAD_U8(hud + 816)) {
    return;
  }
  const float extra = ExtraHudOffset(width);
  const PPCContext saved = ctx;
  const uint32_t package = REX_LOAD_U32(hud + 36);
  if (package) {
    const uint32_t left = FindObject(ctx, base, package, kLeftGroup);
    const uint32_t right = FindObject(ctx, base, package, kRightGroup);
    static bool said = false;
    if (!said) {
      said = true;
      REXLOG_INFO("[wide-scene] HUD out by {:.0f} units: left group {:08X}, right group {:08X}",
                  extra, left, right);
    }
    MoveGroup(base, left, -extra, g_left);
    MoveGroup(base, right, extra, g_right);
  }
  ctx = saved;
  // The minimap, once, when the game has just moved it for widescreen.
  const uint32_t minimap = REX_LOAD_U32(hud + 800);
  if (!was_wide && minimap) {
    StoreF(base, minimap + 184, LoadF(base, minimap + 184) - extra);
    for (uint32_t off : {60u, 64u, 68u, 72u, 144u}) {
      const uint32_t child = REX_LOAD_U32(minimap + off);
      const uint32_t data = child ? REX_LOAD_U32(child + 44) : 0;
      if (data) {
        StoreF(base, data + 28, LoadF(base, data + 28) - extra);
      }
    }
    StoreF(base, kMinimapPivotX, LoadF(base, kMinimapPivotX) - extra);
  }
}
