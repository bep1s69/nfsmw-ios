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
//
// The player's HUD layout (nfsmw_hud_*, live, from the options)
// ==============================================================
//
//   - size: the HUD's matrix (above) scaled by nfsmw_hud_scale while driving
//     (not in menus), about the middle of the screen; the mirror follows it
//     (nfsmw_mirror_scale_*).
//   - the minimap, the speedometer and the race info moved by
//     nfsmw_hud_left_x/y, nfsmw_hud_right_x/y and nfsmw_hud_race_x/y, in the
//     same hook as the wide scene: their pieces' x and y (object+44 -> +28,
//     +32; see Piece below), and the minimap's map as the game moves it (sub_8229C020):
//     its +184/+188, its children's x/y, and the map picture's offset
//     (0x82A2C60C x, 0x82A2C610 y, both read where the map is drawn).

#include <cstdint>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <unordered_map>
#include <vector>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

#include "battery.h"

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
// The player's HUD (live): its size about the middle of the screen while
// driving, and the minimap, the speedometer and the race info (top right)
// moved, in HUD units (640 across at 4:3; y down).
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_scale, 1.0, "Game", "HUD size while driving (1 = the game's)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_left_x, 0.0, "Game", "Minimap side of the HUD moved right by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_left_y, 0.0, "Game", "Minimap side of the HUD moved down by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_right_x, 0.0, "Game", "Speedometer side of the HUD moved right by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_right_y, 0.0, "Game", "Speedometer side of the HUD moved down by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_safe_zone, 1.0, "Game",
                      "How far out the HUD's pieces sit, from the middle of the screen (1 = the game's)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_race_x, 0.0, "Game", "Race info (top right) moved right by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_race_y, 0.0, "Game", "Race info (top right) moved down by (HUD units)");
REXCVAR_DEFINE_INT32(nfsmw_wide_scene_width, 0, "Game",
                     "Scene width for video modes wider than 16:9 (e.g. 1560 for 19.5:9); 0 = "
                     "the game's 1280 (experimental)")
    .lifecycle(rex::cvar::Lifecycle::kRequiresRestart);

extern "C" void __imp__sub_824581A8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_824585E0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82440D80(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82453768(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822AA6D0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82442310(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822241A0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82224240(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void sub_8227FD58(PPCContext& __restrict ctx, uint8_t* base);
REXCVAR_DECLARE(bool, nfsmw_sin_posprocesado);  // game_hooks.cpp
REXCVAR_DEFINE_BOOL(nfsmw_motion_blur, true, "Juego",
                    "The game's motion blur (the visual treatment's blur at speed). Off: the "
                    "picture stays sharp at speed");

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

uint32_t LoadU(uint8_t* base, uint32_t address) { return REX_LOAD_U32(address); }

// A guest heap pointer (the HUD's objects are at 0xBE......).
bool Plausible(uint32_t a) { return a >= 0x40000000 && a < 0xF0000000 && (a & 3) == 0; }

void StoreF(uint8_t* base, uint32_t address, float v) {
  uint32_t bits;
  std::memcpy(&bits, &v, sizeof(bits));
  REX_STORE_U32(address, bits);
}

// nfsmw_hud_scale (in range, else 1).
float HudScaleSetting() {
  const double scale = REXCVAR_GET(nfsmw_hud_scale);
  return scale >= 0.5 && scale <= 1.5 ? float(scale) : 1.0f;
}

// The HUD matrix's: the setting while driving (menus keep the game's size),
// else 1.
// Whether a fade's black screen is fully up (alpha 255), logged only: IPA83
// held the HUD's size at 1 meanwhile, but FadeScreen.fng's black images keep
// alpha 255 for the whole race (hidden some other way), so the HUD stayed at
// full size.
bool g_fade_opaque = false;

float HudScale() { return nfsmw::battery::InMenu() == 0 ? HudScaleSetting() : 1.0f; }

float g_half_height_per_unit = 1.0f / 240.0f;  // the HUD drawn: see sub_82453768

// Set while sub_82440D80 runs: its call to sub_82453768 hands on the HUD's matrix.
thread_local bool g_hud_matrix = false;

}  // namespace

// How much the HUD's matrix is scaled here beyond the game's own (x, y): the
// rear-view mirror's picture is not drawn through that matrix (its quad has
// its own screen positions), so the native renderer scales it by as much,
// about the middle of the screen, to stay inside its frame.
extern "C" {
float nfsmw_mirror_scale_x = 1.0f;
float nfsmw_mirror_scale_y = 1.0f;
// And moved down by this much (of the screen's half height), with the
// mirror's frame (nfsmw_hud_*: kept at its top margin).
float nfsmw_mirror_shift_y = 0.0f;
}

namespace {

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
  static uint32_t calls = 0;  // how often it is rebuilt (nfsmw_hud_scale is read here)
  if (++calls == 1 || calls == 2 || calls == 1000) REXLOG_INFO("[hud] matrix built ({})", calls);
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
    const float game_sx = LoadF(base, m), game_sy = LoadF(base, m + 20);
    float sx = game_sx, sy = game_sy;
    if (const uint32_t width = WideWidth()) sx *= 1280.0f / float(width);
    float safe_x, safe_y;
    HudSafeScale(base, safe_x, safe_y);
    if (!REXCVAR_GET(nfsmw_hud_title_safe)) {
      sx /= safe_x;
      sy /= safe_y;
    }
    const float scale = HudScale();
    sx *= scale;
    sy *= scale;
    // Of the screen's half height per HUD unit: 240 units at full size, in HD
    // the title-safe 0.92 kept (HudSafeScale), in SD only with the cvar.
    const bool hd = REX_LOAD_U8(0x828F4A8F) != 0;
    const float kept_y = hd ? LoadF(base, kHdSafeScale) : REXCVAR_GET(nfsmw_hud_title_safe) ? safe_y : 1.0f;
    g_half_height_per_unit = (kept_y > 0.5f && kept_y <= 1.0f ? kept_y : 1.0f) * scale / 240.0f;
    StoreF(base, m, sx);
    StoreF(base, m + 20, sy);
    if (game_sx != 0 && game_sy != 0) {
      nfsmw_mirror_scale_x = sx / game_sx;
      nfsmw_mirror_scale_y = sy / game_sy;
    }
  }
  __imp__sub_82453768(ctx, base);
}


namespace {

constexpr uint32_t kLeftGroup = 0x1603009E;
constexpr uint32_t kRightGroup = 0x5D0101F1;
// The minimap picture's offset (x, y), read where the map is drawn; the
// game's widescreen switch sets x (sub_8229C020).
constexpr uint32_t kMinimapPivotX = 0x82A2C60C;
constexpr uint32_t kMinimapPivotY = 0x82A2C610;

// HUD units the sides go out beyond the game's own 16:9 layout.
float ExtraHudOffset(uint32_t width) {
  const float aspect = float(width) / 720.0f;
  return 120.0f * (aspect - 16.0f / 9.0f) / (16.0f / 9.0f - 4.0f / 3.0f);
}

// One group: the position the game (or its script) last gave it, and what
// was written over it.
struct Moved {
  uint32_t object = 0;
  float base_x = 0, base_y = 0;
  float written_x = 0, written_y = 0;
};
Moved g_left, g_right;

void MoveGroup(uint8_t* base, uint32_t object, float dx, float dy, Moved& moved) {
  if (!object) {
    return;
  }
  const uint32_t data = Plausible(object) ? REX_LOAD_U32(object + 44) : 0;
  if (!Plausible(data)) {
    return;
  }
  const float x = LoadF(base, data + 28), y = LoadF(base, data + 32);
  if (moved.object != object || x != moved.written_x || y != moved.written_y) {
    moved.object = object;  // new, or the game moved it since: its new base
    moved.base_x = x;
    moved.base_y = y;
  }
  moved.written_x = moved.base_x + dx;
  moved.written_y = moved.base_y + dy;
  if (moved.written_x != x) StoreF(base, data + 28, moved.written_x);
  if (moved.written_y != y) StoreF(base, data + 32, moved.written_y);
}

// The minimap is moved apart from the left group, as the game does it
// (sub_8229C020): the object's +184/+188, its children's positions, and the
// picture's offset. The game only adds to the object's (when it switches to
// widescreen); it sets the offset's x outright.
struct MovedMinimap {
  uint32_t object = 0;
  float x = 0, y = 0;  // added to the object and its children
  float pivot_x = 0, pivot_y = 0;  // added to the offset
  float written_px = 0, written_py = 0;
  float written_x = 0;  // the object's +184 as left here
};
MovedMinimap g_minimap;

// switched: the game has just moved it for (or back from) widescreen.
void MoveMinimap(uint8_t* base, uint32_t minimap, float dx, float dy, bool switched) {
  if (!minimap) {
    return;
  }
  MovedMinimap& m = g_minimap;
  if (m.object != minimap || (!switched && LoadF(base, minimap + 184) != m.written_x)) {
    m.object = minimap;  // a new one (perhaps at the same address)
    m.x = m.y = 0;
  }
  const float ox = dx - m.x, oy = dy - m.y;
  if (ox != 0 || oy != 0) {
    StoreF(base, minimap + 184, LoadF(base, minimap + 184) + ox);
    StoreF(base, minimap + 188, LoadF(base, minimap + 188) + oy);
    for (uint32_t off : {60u, 64u, 68u, 72u, 144u}) {
      const uint32_t child = REX_LOAD_U32(minimap + off);
      const uint32_t data = Plausible(child) ? REX_LOAD_U32(child + 44) : 0;
      if (Plausible(data)) {
        StoreF(base, data + 28, LoadF(base, data + 28) + ox);
        StoreF(base, data + 32, LoadF(base, data + 32) + oy);
      }
    }
    m.x = dx;
    m.y = dy;
  }
  m.written_x = LoadF(base, minimap + 184);
  const float px = LoadF(base, kMinimapPivotX), py = LoadF(base, kMinimapPivotY);
  if (px != m.written_px) m.pivot_x = 0;  // set again by the game
  if (py != m.written_py) m.pivot_y = 0;
  m.written_px = px + (dx - m.pivot_x);
  m.written_py = py + (dy - m.pivot_y);
  m.pivot_x = dx;
  m.pivot_y = dy;
  if (m.written_px != px) StoreF(base, kMinimapPivotX, m.written_px);
  if (m.written_py != py) StoreF(base, kMinimapPivotY, m.written_py);
}

// The HUD package's objects, once per new HUD, to find its elements: walked
// from a top-level object (the right group) to its first sibling and on.
// Layout as read in IPA71's dump: +0 vtable, +4 next, +8 prev, +0C GUID,
// +10 name hash, +18 type (5 = group), +1C flags, +2C data (+28 x, +32 y,
// +56/+60 size); a group's children list at +5C (vtable 0x82080030), +60
// count, +64 first.
constexpr uint32_t kListVtable = 0x82080030;

void DumpObjects(uint8_t* base, uint32_t first, int depth, int& budget) {
  for (uint32_t o = first; Plausible(o) && budget > 0; o = REX_LOAD_U32(o + 4)) {
    if (REX_LOAD_U32(o) == kListVtable) break;
    --budget;
    const uint32_t type = REX_LOAD_U32(o + 0x18), data = REX_LOAD_U32(o + 0x2C);
    float x = 0, y = 0, w = 0, h = 0;
    if (Plausible(data)) {
      x = LoadF(base, data + 28), y = LoadF(base, data + 32);
      w = LoadF(base, data + 56), h = LoadF(base, data + 60);
    }
    REXLOG_INFO("[hud-tree] {:>{}}{:08X} hash {:08X} type {} flags {:08X} pos {:.1f},{:.1f} size {:.2f},{:.2f}", "",
                depth * 2, o, REX_LOAD_U32(o + 0x10), type, REX_LOAD_U32(o + 0x1C), x, y, w, h);
    if (type == 5 && REX_LOAD_U32(o + 0x5C) == kListVtable && REX_LOAD_U32(o + 0x60) < 200 && depth < 8) {
      DumpObjects(base, REX_LOAD_U32(o + 0x64), depth + 1, budget);
    }
  }
}

void DumpTree(uint8_t* base, uint32_t object) {
  uint32_t first = object;
  for (int i = 0; i < 1000; ++i) {
    const uint32_t prev = REX_LOAD_U32(first + 8);
    if (!Plausible(prev) || REX_LOAD_U32(prev) == kListVtable) break;
    first = prev;
  }
  int budget = 800;
  REXLOG_INFO("[hud-tree] package objects from {:08X}:", first);
  DumpObjects(base, first, 0, budget);
}

uint32_t FindObject(PPCContext& ctx, uint8_t* base, uint32_t package, uint32_t hash) {
  ctx.r3.u64 = package;
  ctx.r4.u64 = hash;
  sub_8227FD58(ctx, base);
  return ctx.r3.u32;
}

// The HUD's elements, each moved on its own (IPA73's tree dump of the race
// HUD, Oct 26): the left group 0x1603009E (in 0x157C5B37) holds the minimap's
// rings and heat icon at the bottom and other pieces at the top; the right
// group 0x5D0101F1 holds one group, 0x5C7A5C8A, with the speedometer's pieces
// at the bottom and the race standings, laps and times at the top. Each child
// of those two inner groups is one piece: low on the screen it belongs to the
// minimap or the speedometer, higher (right side) to the race info; the top
// left ones stay. The minimap's map and icons are moved by
// MoveMinimap. Positions: HUD units from the middle of the screen, y down.
constexpr uint32_t kLeftOuter = 0x157C5B37;
constexpr uint32_t kRightInner = 0x5C7A5C8A;

enum Element { kMinimap, kSpeedometer, kRaceInfo, kTopLeft, kTopCentre, kBottomCentre, kElements };

// Each element's outer corner as the game draws it (before the 19.5:9
// extra), in HUD units from the middle of the screen, kept at its place by
// the size (IPA76: keeping the middles moved the edges): the middles x 221
// from the middle at 4:3, 120 more in the game's widescreen layout (the left
// ones at -x), y from IPA73's tree: the minimap's map and ring at 139 and
// the speedometer's dial ~141, both ~76 in radius; the race info's top
// pieces to ~-213 and ~76 past the middles. The mirror's frame (0x7FAC287B,
// two 128x87 halves at y -176): its top at -220.
struct Corner {
  float side;  // -1 left, 1 right
  float y;
};
// The middle group 0xAB9C1D4D's pieces (IPA82: the radar detector's arcs
// under the mirror did not follow it) go with the mirror at the top (its top
// edge, -220) and with the bottom edge at the bottom; those in the middle
// ("GO!", messages) stay.
constexpr Corner kCorners[] = {{-1, 215}, {1, 215}, {1, -213}, {-1, -213}, {0, -220}, {0, 215}};
constexpr uint32_t kMiddleGroup = 0xAB9C1D4D;
constexpr float kSideX = 221.0f, kWideSideX = 120.0f, kHalfWidth = 76.0f;
constexpr uint32_t kMirrorFrame = 0x7FAC287B;
constexpr float kMirrorTop = -220.0f;
Moved g_mirror;

struct Piece {
  uint32_t object;
  Element element;
  Moved moved;
  uint32_t hash, vtable;  // the object's when found: checked every frame
};
std::vector<Piece> g_pieces;
uint32_t g_pieces_package = 0;

float Y(uint8_t* base, uint32_t object) {
  const uint32_t data = Plausible(object) ? REX_LOAD_U32(object + 44) : 0;
  return Plausible(data) ? LoadF(base, data + 32) : 0.0f;
}

// Where a piece is drawn (y), from its group: its position plus the middle of
// what it holds.
float AnchorY(uint8_t* base, uint32_t object, int depth) {
  float y = Y(base, object);
  if (REX_LOAD_U32(object + 0x18) == 5 && REX_LOAD_U32(object + 0x5C) == kListVtable && depth < 8) {
    float sum = 0;
    int n = 0;
    for (uint32_t c = REX_LOAD_U32(object + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
         c = REX_LOAD_U32(c + 4)) {
      sum += AnchorY(base, c, depth + 1);
      ++n;
    }
    if (n) y += sum / float(n);
  }
  return y;
}

// The children of an inner group (at y0 from the middle of the screen) as
// pieces: low on the screen `below`, high `above`, in between `middle` (-1:
// left out). Low:
// below 60 units under the middle; the speedometer's pieces were at 83-165,
// the minimap's at 105-139, and three rows at the right's middle (-32, 2,
// 38) go with the race info.
constexpr float kBottom = 60.0f;
void AddPieces(uint8_t* base, uint32_t group, float y0, Element below, int above, int middle) {
  if (!Plausible(group) || REX_LOAD_U32(group + 0x5C) != kListVtable) return;
  int n = 0;
  for (uint32_t c = REX_LOAD_U32(group + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
       c = REX_LOAD_U32(c + 4), ++n) {
    const float y = y0 + AnchorY(base, c, 0);
    const int e = y > kBottom ? int(below) : y < -kBottom ? above : middle;
    if (e >= 0) g_pieces.push_back({c, Element(e), {}, REX_LOAD_U32(c + 0x10), REX_LOAD_U32(c)});
  }
}

}  // namespace

// The HUD's update (sub_822AA6D0, every frame while there is a HUD): the
// sides out for a wide scene (the two groups), and the player's own
// positions for the minimap, the speedometer and the race info
// (nfsmw_hud_*_x/y), on their pieces.
extern "C" REX_FUNC(sub_822AA6D0) {
  const uint32_t hud = ctx.r3.u32;
  const uint8_t was_wide = hud ? REX_LOAD_U8(hud + 816) : 0;
  // The game only changes the widescreen flag inside this call: a flag that
  // changed since the last call, or another HUD, is a new HUD (perhaps at
  // the old one's address, its minimap too: after a race or the safe house,
  // IMG_4038).
  static uint32_t last_hud = 0;
  static uint8_t last_wide = 0;
  const bool rebuilt = hud && (hud != last_hud || was_wide != last_wide);
  __imp__sub_822AA6D0(ctx, base);
  if (!hud) {
    return;
  }
  last_hud = hud;
  last_wide = REX_LOAD_U8(hud + 816);
  if (rebuilt) {
    g_minimap.object = 0;  // its minimap is new: move it again
  }
  const uint32_t width = WideWidth();
  const float extra = width && REX_LOAD_U8(hud + 816) ? ExtraHudOffset(width) : 0.0f;
  // The player's offsets, then what each element's pieces are moved by: with
  // the element's corner g (and the extra e, which the groups carry), the safe
  // zone k and the size s (the HUD's matrix scales about the middle of the
  // screen), the middle is drawn at k * (g + e) + offset:
  // s * (g + e + d) = k * (g + e) + offset. The mirror's frame alike (y).
  const float user[kElements][2] = {
      {float(REXCVAR_GET(nfsmw_hud_left_x)), float(REXCVAR_GET(nfsmw_hud_left_y))},
      {float(REXCVAR_GET(nfsmw_hud_right_x)), float(REXCVAR_GET(nfsmw_hud_right_y))},
      {float(REXCVAR_GET(nfsmw_hud_race_x)), float(REXCVAR_GET(nfsmw_hud_race_y))},
      {0, 0}, {0, 0}, {0, 0}};
  const double safe = REXCVAR_GET(nfsmw_hud_safe_zone);
  const float k = safe >= 0.5 && safe <= 1.5 ? float(safe) : 1.0f;
  // The setting, not HudScale(): the pieces' offsets must not change when a
  // pause screen comes and goes. Pieces the game does not redraw keep the
  // position they had when last laid out (IPA75: the still parts, such as
  // the dial's face and the minimap's ring, kept the offsets of the pause
  // screen's size 1 and came out where the matrix alone put them).
  const float s = HudScaleSetting();
  const float gx = kSideX + (REX_LOAD_U8(hud + 816) ? kWideSideX : 0.0f);
  float offset[kElements][2];
  static bool active = false;  // anything set or moved since the start
  for (int e = 0; e < kElements; ++e) {
    const float x = kCorners[e].side * (gx + kHalfWidth + extra), y = kCorners[e].y;
    offset[e][0] = (k * x + user[e][0]) / s - x;
    offset[e][1] = (k * y + user[e][1]) / s - y;
    active = active || std::abs(offset[e][0]) > 0.01f || std::abs(offset[e][1]) > 0.01f;
  }
  const uint32_t package = REX_LOAD_U32(hud + 36);
  static uint32_t dumped_package = 0;
  const bool dump = package && package != dumped_package;
  if (!dump && !active && extra == 0 && !g_left.object && !g_right.object) {
    return;  // nothing to move, and nothing moved
  }
  const PPCContext saved = ctx;
  if (package) {
    const uint32_t left = FindObject(ctx, base, package, kLeftGroup);
    const uint32_t right = FindObject(ctx, base, package, kRightGroup);
    // A new HUD (the race HUD after free roam's, IPA77's crash) may be built
    // where the old one was: the pieces are found again whenever the groups
    // or any piece are not the ones found (a freed piece was written to).
    static uint32_t pieces_left = 0, pieces_right = 0;
    bool stale = package != g_pieces_package || left != pieces_left || right != pieces_right;
    for (const Piece& p : g_pieces) {
      stale = stale || REX_LOAD_U32(p.object + 0x10) != p.hash || REX_LOAD_U32(p.object) != p.vtable;
    }
    if (stale) {
      g_pieces_package = package;
      pieces_left = left;
      pieces_right = right;
      g_pieces.clear();
      const uint32_t left_outer = FindObject(ctx, base, package, kLeftOuter);
      const uint32_t right_inner = FindObject(ctx, base, package, kRightInner);
      AddPieces(base, left, Y(base, left_outer) + Y(base, left), kMinimap, kTopLeft, kTopLeft);
      AddPieces(base, right_inner, Y(base, right) + Y(base, right_inner), kSpeedometer, kRaceInfo, kRaceInfo);
      const uint32_t middle = FindObject(ctx, base, package, kMiddleGroup);
      AddPieces(base, middle, Y(base, middle), kBottomCentre, kTopCentre, -1);
      int counts[kElements] = {};
      for (const Piece& p : g_pieces) ++counts[p.element];
      REXLOG_INFO("[hud] package {:08X}: left group {:08X}, right group {:08X} ({:08X}); pieces: minimap {}, "
                  "speedometer {}, race info {}, top left {}, top centre {}, bottom centre {} (wide {:.0f})",
                  package, left, right, right_inner, counts[kMinimap], counts[kSpeedometer], counts[kRaceInfo],
                  counts[kTopLeft], counts[kTopCentre], counts[kBottomCentre], extra);
    }
    if (dump && right) {  // once per HUD package
      dumped_package = package;
      DumpTree(base, right);
    }
    MoveGroup(base, left, -extra, 0, g_left);
    MoveGroup(base, right, extra, 0, g_right);
    for (Piece& p : g_pieces) {
      MoveGroup(base, p.object, offset[p.element][0], offset[p.element][1], p.moved);
    }
    const float mirror_dy = offset[kTopCentre][1];
    const uint32_t frame = active || std::abs(mirror_dy) > 0.01f ? FindObject(ctx, base, package, kMirrorFrame) : 0;
    if (frame) {
      MoveGroup(base, frame, 0, mirror_dy, g_mirror);
      nfsmw_mirror_shift_y = mirror_dy * g_half_height_per_unit;
    }
  }
  ctx = saved;
  MoveMinimap(base, REX_LOAD_U32(hud + 800), offset[kMinimap][0] - extra, offset[kMinimap][1],
              REX_LOAD_U8(hud + 816) != was_wide);
}

namespace {

// A fade package's full-screen pieces: their size and position as the game
// set them, and as written here.
struct Fitted {
  float base[4];
  float written[4];
};
std::unordered_map<uint32_t, Fitted> g_fitted;

// Position (+28, +32) and, unless only_position, size (+56, +60) of an
// object divided by s, so that through the HUD's matrix (scaled by s about
// the middle of the screen) it is drawn as without it.
void Fit(uint8_t* base, uint32_t object, float s, bool only_position) {
  const uint32_t data = REX_LOAD_U32(object + 44);
  if (!Plausible(data)) return;
  const uint32_t at[4] = {data + 28, data + 32, data + 56, data + 60};
  float now[4];
  for (int i = 0; i < 4; ++i) now[i] = LoadF(base, at[i]);
  auto [it, added] = g_fitted.try_emplace(object);
  Fitted& f = it->second;
  if (added || std::memcmp(now, f.written, sizeof(now)) != 0) std::memcpy(f.base, now, sizeof(now));
  for (int i = 0; i < 4; ++i) {
    f.written[i] = i >= 2 && only_position ? f.base[i] : f.base[i] / s;
    if (f.written[i] != now[i]) StoreF(base, at[i], f.written[i]);
  }
}

uint32_t g_fade_alpha = 0;  // the widest images' largest alpha this frame

// A package's first top-level object, by its object list's header (vtable
// 0x82080030, count, first) within its first 0x200 bytes (IPA81: at +0x44
// in FadeScreen.fng); 0 if none. at: the header's offset.
uint32_t FirstObject(uint8_t* base, uint32_t package, uint32_t& at) {
  for (uint32_t off = 0; off < 0x200; off += 4) {
    if (REX_LOAD_U32(package + off) != kListVtable) continue;
    const uint32_t count = REX_LOAD_U32(package + off + 4), head = REX_LOAD_U32(package + off + 8);
    if (count && count < 300 && Plausible(head) && REX_LOAD_U32(head) != kListVtable &&
        REX_LOAD_U32(head + 0x18) >= 1 && REX_LOAD_U32(head + 0x18) <= 20) {
      at = off;
      return head;
    }
  }
  return 0;
}

// An object's extent from its own position, groups included (images by their
// size, text as a point).
struct Box {
  float x0 = 1e9f, x1 = -1e9f, y0 = 1e9f, y1 = -1e9f;
  void Add(float ax0, float ax1, float ay0, float ay1) {
    x0 = std::min(x0, ax0), x1 = std::max(x1, ax1), y0 = std::min(y0, ay0), y1 = std::max(y1, ay1);
  }
  bool Valid() const { return x0 <= x1 && y0 <= y1; }
};

void Extent(uint8_t* base, uint32_t object, float px, float py, int depth, Box& box) {
  const uint32_t type = REX_LOAD_U32(object + 0x18), data = REX_LOAD_U32(object + 44);
  if (!Plausible(data)) return;
  if (type == 5) {
    if (depth >= 6 || REX_LOAD_U32(object + 0x5C) != kListVtable) return;
    int n = 0;
    for (uint32_t c = REX_LOAD_U32(object + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
         c = REX_LOAD_U32(c + 4), ++n) {
      Extent(base, c, px + LoadF(base, LoadU(base, c + 44) + 28), py + LoadF(base, LoadU(base, c + 44) + 32),
             depth + 1, box);
    }
  } else if (type == 2) {
    box.Add(px, px, py, py);
  } else {
    const float hw = std::abs(LoadF(base, data + 56)) / 2, hh = std::abs(LoadF(base, data + 60)) / 2;
    box.Add(px - hw, px + hw, py - hh, py + hh);
  }
}

// The full-screen images (400 units wide or more) in an object, groups
// included: the images by position and size, the groups that hold them by
// position (IPA81's log: FadeScreen.fng's black screen is two 1200x650
// images in the group 0x027FF2DC). Whether any was found.
bool FitWide(uint8_t* base, uint32_t object, float s, int depth) {
  const uint32_t type = REX_LOAD_U32(object + 0x18), data = REX_LOAD_U32(object + 44);
  if (type == 1) {
    if (!Plausible(data) || std::abs(LoadF(base, data + 56)) < 400.0f) return false;
    Fit(base, object, s, false);
    g_fade_alpha = std::max(g_fade_alpha, REX_LOAD_U32(data + 12));  // FEColor b, g, r, a
    return true;
  }
  if (type != 5 || depth >= 4 || REX_LOAD_U32(object + 0x5C) != kListVtable) return false;
  bool any = false;
  int n = 0;
  for (uint32_t c = REX_LOAD_U32(object + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
       c = REX_LOAD_U32(c + 4), ++n) {
    any = FitWide(base, c, s, depth + 1) || any;
  }
  if (any) Fit(base, object, s, true);
  return any;
}

}  // namespace

// A full-screen fade package that is up (game_state.cpp, every frame while
// one is pushed in the world): the black loading screen before a race is
// drawn through the HUD's matrix too, and at a smaller HUD size the picture
// bled through at its top and bottom (IPA78). Its full-screen images (400
// units wide or more: the black screen) are drawn as at size 1. The
// package's object list is found by its list header (vtable 0x82080030,
// count, first), logged once.
extern "C" void nfsmw_hud_fit_fade(uint8_t* base, uint32_t package) {
  if (!Plausible(package)) {  // none up
    g_fade_opaque = false;
    return;
  }
  static uint32_t said = 0;
  uint32_t at = 0;
  const uint32_t first = FirstObject(base, package, at);
  if (package != said) {
    said = package;
    REXLOG_INFO("[hud] fade package {:08X}: objects list at +{:X}, first {:08X}", package, at, first);
    int budget = 60;
    if (first) DumpObjects(base, first, 0, budget);
  }
  g_fade_alpha = 0;
  const float s = HudScaleSetting();
  int n = 0;
  for (uint32_t o = first; Plausible(o) && REX_LOAD_U32(o) != kListVtable && n < 300; o = REX_LOAD_U32(o + 4), ++n) {
    FitWide(base, o, s, 0);
  }
  const bool opaque = g_fade_alpha >= 255;
  if (opaque != g_fade_opaque) {
    g_fade_opaque = opaque;
    static int lines = 40;
    if (lines-- > 0) REXLOG_INFO("[hud] fade {:08X}: black screen {} (alpha {})", package, opaque ? "up" : "fading", g_fade_alpha);
  }
}

namespace {
std::unordered_map<uint32_t, Moved> g_overlay;
}  // namespace

// A package shown over the HUD while driving (game_state.cpp: EA_Trax.fng,
// the song's name; IPA82: it kept the size's middle, not the safe zone):
// each top-level object is moved so its outer corner (the corner of its
// extent away from the middle of the screen) keeps its place as the HUD's
// corners do: s * (a + d) = k * a.
extern "C" void nfsmw_hud_fit_overlay(uint8_t* base, uint32_t package) {
  if (!Plausible(package)) return;
  uint32_t at = 0;
  const uint32_t first = FirstObject(base, package, at);
  static uint32_t said = 0;
  if (package != said) {
    said = package;
    REXLOG_INFO("[hud] overlay package {:08X}: objects list at +{:X}, first {:08X}", package, at, first);
    int budget = 60;
    if (first) DumpObjects(base, first, 0, budget);
  }
  const double safe = REXCVAR_GET(nfsmw_hud_safe_zone);
  const float k = safe >= 0.5 && safe <= 1.5 ? float(safe) : 1.0f;
  const float s = HudScaleSetting();
  int n = 0;
  for (uint32_t o = first; Plausible(o) && REX_LOAD_U32(o) != kListVtable && n < 300; o = REX_LOAD_U32(o + 4), ++n) {
    const uint32_t data = REX_LOAD_U32(o + 44);
    if (!Plausible(data)) continue;
    Moved& m = g_overlay[o];
    const float x = LoadF(base, data + 28), y = LoadF(base, data + 32);
    const bool ours = m.object == o && x == m.written_x && y == m.written_y;
    const float bx = ours ? m.base_x : x, by = ours ? m.base_y : y;
    Box box;
    Extent(base, o, bx, by, 0, box);
    if (!box.Valid()) continue;
    const float ax = (box.x0 + box.x1) < 0 ? box.x0 : box.x1, ay = (box.y0 + box.y1) < 0 ? box.y0 : box.y1;
    MoveGroup(base, o, k * ax / s - ax, k * ay / s - ay, m);
  }
}

// Every screen up in the world, logged (D-006, IPA139: which packages the
// HUD's size reaches besides the HUD, and where their pieces are). The
// engine's pushed packages are a list at FEngine+216 (IsPackagePushed,
// sub_82284D70 -> sub_822F5A98: first at +8; a package's +4 next, +12 its
// name, +16 the name's hash). The list's names are logged when it changes,
// with the HUD's size then; each package's object tree when it comes up and
// again 180 frames later (its pieces once its script has moved them).
namespace {
struct Seen {
  uint32_t package;
  uint64_t frame;
  bool redumped;
};
std::vector<Seen> g_seen;
uint64_t g_ui_frame = 0;

std::string GuestName(uint8_t* base, uint32_t at) {
  std::string s;
  if (!Plausible(at & ~3u)) return "?";
  for (uint32_t i = 0; i < 64; ++i) {
    const uint8_t c = REX_LOAD_U8(at + i);
    if (!c) break;
    s.push_back(c >= 32 && c < 127 ? char(c) : '?');
  }
  return s;
}

void DumpPackage(uint8_t* base, uint32_t package, const char* when) {
  uint32_t at = 0;
  const uint32_t first = FirstObject(base, package, at);
  REXLOG_INFO("[ui-tree] {} {:08X} ({}), HUD size {:.2f}, menu {}:", GuestName(base, REX_LOAD_U32(package + 12)),
              package, when, HudScale(), nfsmw::battery::InMenu());
  int budget = 400;
  if (first) DumpObjects(base, first, 0, budget);
}
}  // namespace

extern "C" void nfsmw_ui_log(uint8_t* base, uint32_t engine) {
  ++g_ui_frame;
  if (!Plausible(engine)) return;
  std::vector<uint32_t> now;
  for (uint32_t p = REX_LOAD_U32(engine + 216 + 8); Plausible(p) && now.size() < 64; p = REX_LOAD_U32(p + 4)) {
    now.push_back(p);
  }
  bool changed = now.size() != g_seen.size();
  for (size_t i = 0; !changed && i < now.size(); ++i) changed = now[i] != g_seen[i].package;
  if (changed) {
    std::string names;
    std::vector<Seen> next;
    for (uint32_t p : now) {
      if (!names.empty()) names += ", ";
      names += GuestName(base, REX_LOAD_U32(p + 12));
      auto old = std::find_if(g_seen.begin(), g_seen.end(), [p](const Seen& s) { return s.package == p; });
      if (old != g_seen.end()) {
        next.push_back(*old);
      } else {
        next.push_back({p, g_ui_frame, false});
        DumpPackage(base, p, "up");
      }
    }
    g_seen = std::move(next);
    REXLOG_INFO("[ui] screens: {} (HUD size {:.2f}, menu {})", names, HudScale(), nfsmw::battery::InMenu());
  }
  for (Seen& s : g_seen) {
    if (!s.redumped && g_ui_frame - s.frame >= 180) {  // 180 frames: 3-6 s at the caps
      s.redumped = true;
      DumpPackage(base, s.package, "3 s later");
    }
  }
}

// Post-processing off (nfsmw_sin_posprocesado; game_hooks.cpp has the
// history): sub_82442310 runs the frame's post chain, and the byte at +9 of
// its argument (the view's "post-processing on") gates the bloom chain and
// the visual treatment (colour filter, vignette); it reads 0 while the
// function runs, so the game takes its path without them.
extern "C" REX_FUNC(sub_82442310) {
  const uint32_t view = ctx.r3.u32;
  if (!REXCVAR_GET(nfsmw_sin_posprocesado) || !view) {
    __imp__sub_82442310(ctx, base);
    return;
  }
  const uint8_t before = REX_LOAD_U8(view + 9);
  static int said = 0;
  if (said++ < 2) REXLOG_INFO("[post] frame without post-processing: view byte +9 was {}", before);
  REX_STORE_U8(view + 9, 0);
  __imp__sub_82442310(ctx, base);
  REX_STORE_U8(view + 9, before);
}

// Motion blur off (nfsmw_motion_blur): the visual treatment (sub_822246F0)
// blurs the picture by the view's two blur amounts, floats at +144/+148 of
// its entry in the view table 0x82C3F590 (384 bytes each, r4 = the view;
// the byte at +4 says the view is used). Two globals override them when not
// 0 (0x82A2C4E4/E8; 0 in the image). sub_822241A0 picks the
// "visualtreatment_branching" technique when either is above 0.0001, and
// sub_82224240 sets the shader's blur vector, binds the blur texture and
// sets its "blur on" bool. While those two run, the amounts read 0: the
// plain technique, the bool false, no blur texture. Inferred, not proven:
// that this is the motion blur Stefan sees (the mirror's view has none).
namespace {

constexpr uint32_t kViewTable = 0x82C3F590;
constexpr uint32_t kViewSize = 384;
constexpr uint32_t kBlurOverride = 0x82A2C4E4;

template <void (*kOriginal)(PPCContext&, uint8_t*)>
void WithoutMotionBlur(PPCContext& __restrict ctx, uint8_t* base) {
  if (REXCVAR_GET(nfsmw_motion_blur) || ctx.r4.u32 >= 8) {
    kOriginal(ctx, base);
    return;
  }
  const uint32_t view = kViewTable + ctx.r4.u32 * kViewSize;
  const uint32_t at[4] = {view + 144, view + 148, kBlurOverride, kBlurOverride + 4};
  uint32_t before[4];
  for (int i = 0; i < 4; ++i) {
    before[i] = REX_LOAD_U32(at[i]);
    REX_STORE_U32(at[i], 0);
  }
  static int said = 0;
  if (said < 4 && (before[0] | before[1])) {
    ++said;
    float x, y;
    std::memcpy(&x, &before[0], 4);
    std::memcpy(&y, &before[1], 4);
    REXLOG_INFO("[blur] motion blur off: view {} blur amounts were {:.4f}, {:.4f}", ctx.r4.u32, x, y);
  }
  kOriginal(ctx, base);
  for (int i = 0; i < 4; ++i) REX_STORE_U32(at[i], before[i]);
}

}  // namespace

extern "C" REX_FUNC(sub_822241A0) {
  WithoutMotionBlur<__imp__sub_822241A0>(ctx, base);
}

extern "C" REX_FUNC(sub_82224240) {
  WithoutMotionBlur<__imp__sub_82224240>(ctx, base);
}
