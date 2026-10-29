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
#include <cstdio>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "nfsmw_pch.h"

#include "touch_controls.h"

#include <rex/cvar.h>
#include <rex/logging.h>

#include "battery.h"

REXCVAR_DEFINE_BOOL(nfsmw_hud_watch, false, "Game",
                    "Diagnostic: log the HUD objects whose flags change ([hud-watch]), twice a second");
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
// The Customize HUD editor's layout (hud_editor.mm, live): per element
// "name:x,y,size;..." with x, y in HUD units added to its place and size a
// factor on top of the HUD's size. Names: minimap, speedometer, race_info,
// infractions, mirror, pursuit_bar, pursuit_points.
REXCVAR_DEFINE_STRING(nfsmw_hud_layout, "", "Game", "Custom HUD layout (the Customize HUD editor's)");
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

// Set by game_state.cpp while a full-screen TV overlay is up while driving
// (IPA139's log: BUSTED_OVERLAY.fng, InGamePhotoMaster.fng at a race's end):
// drawn at the game's size, like a menu. The HUD is hidden under them.
bool g_full_size_screen = false;

float HudScale() { return nfsmw::battery::InMenu() == 0 && !g_full_size_screen ? HudScaleSetting() : 1.0f; }

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

void ReapplyHudPieces(uint8_t* base);  // below

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
  ReapplyHudPieces(base);
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
  // Its size (+56/+60: a group's scale) when an element's own size is set.
  bool scaled = false;
  float base_w = 0, base_h = 0;
  float written_w = 0, written_h = 0;
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

// As MoveGroup, and scaled by es about (ax, ay) (in the object's parent's
// units, before the move): position a + d + (p - a) * es, size times es
// (a group's size is the scale of what it holds). es 1: MoveGroup's result,
// and a size left by an earlier es put back.
void MoveScaled(uint8_t* base, uint32_t object, float dx, float dy, float es, float ax, float ay, Moved& moved) {
  const uint32_t data = Plausible(object) ? REX_LOAD_U32(object + 44) : 0;
  if (!Plausible(data)) return;
  const float w = LoadF(base, data + 56), h = LoadF(base, data + 60);
  const bool same = moved.object == object;
  MoveGroup(base, object, dx, dy, moved);  // its base found, written as for es 1
  if (es == 1.0f && !(same && moved.scaled)) {
    moved.scaled = false;
    return;
  }
  if (!same || !moved.scaled || w != moved.written_w || h != moved.written_h) {
    moved.base_w = w;  // new, or the game sized it since
    moved.base_h = h;
  }
  moved.scaled = es != 1.0f;
  moved.written_x = ax + dx + (moved.base_x - ax) * es;
  moved.written_y = ay + dy + (moved.base_y - ay) * es;
  moved.written_w = moved.base_w * es;
  moved.written_h = moved.base_h * es;
  StoreF(base, data + 28, moved.written_x);
  StoreF(base, data + 32, moved.written_y);
  if (moved.written_w != w) StoreF(base, data + 56, moved.written_w);
  if (moved.written_h != h) StoreF(base, data + 60, moved.written_h);
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

// Diagnostic (nfsmw_hud_watch): the HUD's objects whose flags change,
// twice a second, to find what shows in free roam, races, pursuits and
// event circles (touch controls' context buttons).
void WatchObjects(uint8_t* base, uint32_t first, int depth, int& budget,
                  std::unordered_map<uint32_t, uint32_t>& seen, int& logged) {
  for (uint32_t o = first; Plausible(o) && budget > 0; o = REX_LOAD_U32(o + 4)) {
    if (REX_LOAD_U32(o) == kListVtable) break;
    --budget;
    const uint32_t type = REX_LOAD_U32(o + 0x18), flags = REX_LOAD_U32(o + 0x1C);
    auto [it, added] = seen.emplace(o, flags);
    if (!added && it->second != flags && logged < 60) {
      ++logged;
      const uint32_t data = REX_LOAD_U32(o + 0x2C);
      float x = 0, y = 0;
      if (Plausible(data)) x = LoadF(base, data + 28), y = LoadF(base, data + 32);
      REXLOG_INFO("[hud-watch] {:08X} hash {:08X} type {} depth {} flags {:08X} -> {:08X} pos {:.0f},{:.0f}", o,
                  REX_LOAD_U32(o + 0x10), type, depth, it->second, flags, x, y);
    }
    it->second = flags;
    if (type == 5 && REX_LOAD_U32(o + 0x5C) == kListVtable && REX_LOAD_U32(o + 0x60) < 200 && depth < 8) {
      WatchObjects(base, REX_LOAD_U32(o + 0x64), depth + 1, budget, seen, logged);
    }
  }
}

void WatchTree(uint8_t* base, uint32_t object) {
  static std::unordered_map<uint32_t, uint32_t> seen;
  static uint32_t first_seen = 0;
  uint32_t first = object;
  for (int i = 0; i < 1000; ++i) {
    const uint32_t prev = REX_LOAD_U32(first + 8);
    if (!Plausible(prev) || REX_LOAD_U32(prev) == kListVtable) break;
    first = prev;
  }
  if (first != first_seen) {
    seen.clear();
    first_seen = first;
    REXLOG_INFO("[hud-watch] new HUD tree from {:08X}", first);
  }
  int budget = 1500, logged = 0;
  WatchObjects(base, first, 0, budget, seen, logged);
}

// What the HUD shows, for the touch controls' D-pad buttons (IPA154's
// [hud-watch] log, Oct 29): the prompt over the road in an event, shop or
// safehouse circle (3B1B624A, and its D-pad picture 0A729B1B), and the
// race's position markers on the left (4FDDD64C-4FDDD64F, one shown in a
// race, none in free roam). Shown: flag 0x00800000 (43800000 shown,
// 40000000 / 42000000 hidden).
constexpr uint32_t kShown = 0x00800000;

void ScanContext(uint8_t* base, uint32_t first, int depth, int& budget, int& bits) {
  for (uint32_t o = first; Plausible(o) && budget > 0; o = REX_LOAD_U32(o + 4)) {
    if (REX_LOAD_U32(o) == kListVtable) break;
    --budget;
    const uint32_t hash = REX_LOAD_U32(o + 0x10), type = REX_LOAD_U32(o + 0x18);
    const bool shown = (REX_LOAD_U32(o + 0x1C) & kShown) != 0;
    if (shown && (hash == 0x3B1B624A || hash == 0x0A729B1B)) bits |= nfsmw::touch::kInCircle;
    if (shown && hash >= 0x4FDDD64C && hash <= 0x4FDDD64F) bits |= nfsmw::touch::kInRace;
    if (type == 5 && REX_LOAD_U32(o + 0x5C) == kListVtable && REX_LOAD_U32(o + 0x60) < 200 && depth < 8) {
      ScanContext(base, REX_LOAD_U32(o + 0x64), depth + 1, budget, bits);
    }
  }
}

void UpdateDriveContext(uint8_t* base, uint32_t object) {
  uint32_t first = object;
  for (int i = 0; i < 1000; ++i) {
    const uint32_t prev = REX_LOAD_U32(first + 8);
    if (!Plausible(prev) || REX_LOAD_U32(prev) == kListVtable) break;
    first = prev;
  }
  int budget = 1500, bits = 0;
  ScanContext(base, first, 0, budget, bits);
  static int last = -1;
  if (bits != last) {
    last = bits;
    REXLOG_INFO("[hud] drive context: {}{}", bits & nfsmw::touch::kInRace ? "race" : "free roam",
                bits & nfsmw::touch::kInCircle ? ", in a circle" : "");
  }
  nfsmw::touch::SetDriveContext(bits);
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

enum Element { kMinimap, kSpeedometer, kRaceInfo, kTopLeft, kTopCentre, kBottomCentre, kPursuitPoints, kElements };
// The layout's names for them (nfsmw_hud_layout).
constexpr const char* kElementNames[kElements] = {"minimap", "speedometer", "race_info", "infractions",
                                                  "mirror", "pursuit_bar", "pursuit_points"};

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
// "PURSUIT CTS" (kPursuitPoints) keeps the speedometer's corner: by default
// they move together (IPA142).
constexpr Corner kCorners[] = {{-1, 215}, {1, 215}, {1, -213}, {-1, -213}, {0, -220}, {0, 215}, {1, 215}};
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
  // A group the game places itself every frame (IPA142: the infraction
  // list's rows, which flashed between the two places): its children are
  // moved instead, which the game leaves alone.
  bool by_children;
  uint32_t parents[2];  // the groups it is in (0: none), for its parent's place
};
std::vector<Piece> g_pieces;
std::unordered_map<uint32_t, Moved> g_child_moved;

float X(uint8_t* base, uint32_t object);
float Y(uint8_t* base, uint32_t object);
float g_anchor[kElements][2] = {};  // each element's corner (HUD units from the middle), as last laid out
float g_size[kElements] = {1, 1, 1, 1, 1, 1, 1};  // each element's own size

// A piece moved by (dx, dy) and scaled by its element's own size about the
// element's corner.
void MovePiece(uint8_t* base, Piece& p, float dx, float dy) {
  const float es = g_size[p.element];
  float px = 0, py = 0;  // where its parent's units start
  for (uint32_t g : p.parents) {
    if (g) px += X(base, g), py += Y(base, g);
  }
  const float ax = g_anchor[p.element][0] - px, ay = g_anchor[p.element][1] - py;
  if (!p.by_children) {
    MoveScaled(base, p.object, dx, dy, es, ax, ay, p.moved);
    return;
  }
  const float cx = ax - X(base, p.object), cy = ay - Y(base, p.object);
  int n = 0;
  for (uint32_t c = REX_LOAD_U32(p.object + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
       c = REX_LOAD_U32(c + 4), ++n) {
    MoveScaled(base, c, dx, dy, es, cx, cy, g_child_moved[c]);
  }
}
float g_layout[kElements][3] = {};  // nfsmw_hud_layout: x, y, own size

// nfsmw_hud_layout read again when it changes. The minimap's and the
// mirror's own size are left at 1: their pictures are drawn apart from
// their pieces (MoveMinimap, the native renderer's mirror).
void ReadLayout() {
  static std::string read = "-";
  const std::string now = REXCVAR_GET(nfsmw_hud_layout);
  if (now == read) return;
  read = now;
  for (int e = 0; e < kElements; ++e) g_layout[e][0] = g_layout[e][1] = 0, g_size[e] = 1.0f;
  size_t at = 0;
  while (at < now.size()) {
    size_t end = now.find(';', at);
    if (end == std::string::npos) end = now.size();
    const std::string item = now.substr(at, end - at);
    at = end + 1;
    const size_t colon = item.find(':');
    if (colon == std::string::npos) continue;
    float x = 0, y = 0, es = 1;
    if (std::sscanf(item.c_str() + colon + 1, "%f,%f,%f", &x, &y, &es) < 2) continue;
    for (int e = 0; e < kElements; ++e) {
      if (item.compare(0, colon, kElementNames[e]) != 0) continue;
      g_layout[e][0] = std::clamp(x, -600.0f, 600.0f);
      g_layout[e][1] = std::clamp(y, -400.0f, 400.0f);
      g_size[e] = e == kMinimap || e == kTopCentre ? 1.0f : std::clamp(es, 0.5f, 2.0f);
    }
  }
  REXLOG_INFO("[hud] layout: {}", now.empty() ? "(none)" : now);
}

float g_offset[kElements][2] = {};  // each element's offset, as last written
bool g_pieces_moved = false;  // by the HUD's update this frame
uint32_t g_pieces_package = 0;

float Y(uint8_t* base, uint32_t object) {
  const uint32_t data = Plausible(object) ? REX_LOAD_U32(object + 44) : 0;
  return Plausible(data) ? LoadF(base, data + 32) : 0.0f;
}

float X(uint8_t* base, uint32_t object) {
  const uint32_t data = Plausible(object) ? REX_LOAD_U32(object + 44) : 0;
  return Plausible(data) ? LoadF(base, data + 28) : 0.0f;
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
// the minimap's at 105-139. The three rows at the right's middle (-32, 2,
// 38: "PURSUIT CTS" and the rows above it) sit just above the speedometer
// at size 1 (IPA141, Stefan's 100% screenshot): they go with it (they went
// with the race info until IPA141 and floated mid-screen at 70%).
constexpr float kBottom = 60.0f;
// Left where the game puts them: the prompt over the road in an event,
// shop or safehouse circle (its icon and its group with the spinning ring),
// in the left group but drawn at the top middle. As top-left pieces they
// went with the infractions (Stefan, IPA154: moved 100 units down with his
// infractions, the ring flashing between there and lower still).
bool NotAPiece(uint32_t hash) { return hash == 0x3B1B624A || hash == 0x3345911D; }

void AddPieces(uint8_t* base, uint32_t outer, uint32_t group, float y0, Element below, int above, int middle) {
  if (!Plausible(group) || REX_LOAD_U32(group + 0x5C) != kListVtable) return;
  int n = 0;
  for (uint32_t c = REX_LOAD_U32(group + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
       c = REX_LOAD_U32(c + 4), ++n) {
    if (NotAPiece(REX_LOAD_U32(c + 0x10))) continue;
    const float y = y0 + AnchorY(base, c, 0);
    const int e = y > kBottom ? int(below) : y < -kBottom ? above : middle;
    if (e >= 0) g_pieces.push_back({c, Element(e), {}, REX_LOAD_U32(c + 0x10), REX_LOAD_U32(c), false, {outer, group}});
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
  float user[kElements][2] = {
      {float(REXCVAR_GET(nfsmw_hud_left_x)), float(REXCVAR_GET(nfsmw_hud_left_y))},
      {float(REXCVAR_GET(nfsmw_hud_right_x)), float(REXCVAR_GET(nfsmw_hud_right_y))},
      {float(REXCVAR_GET(nfsmw_hud_race_x)), float(REXCVAR_GET(nfsmw_hud_race_y))},
      {0, 0}, {0, 0}, {0, 0}, {0, 0}};
  ReadLayout();
  for (int e = 0; e < kElements; ++e) {
    user[e][0] += g_layout[e][0];
    user[e][1] += g_layout[e][1];
  }
  const double safe = REXCVAR_GET(nfsmw_hud_safe_zone);
  const float k = safe >= 0.5 && safe <= 1.5 ? float(safe) : 1.0f;
  // The setting, not HudScale(): the pieces' offsets must not change when a
  // pause screen comes and goes. Pieces the game does not redraw keep the
  // position they had when last laid out (IPA75: the still parts, such as
  // the dial's face and the minimap's ring, kept the offsets of the pause
  // screen's size 1 and came out where the matrix alone put them).
  const float s = HudScaleSetting();
  const float gx = kSideX + (REX_LOAD_U8(hud + 816) ? kWideSideX : 0.0f);
  float (&offset)[kElements][2] = g_offset;
  static bool active = false;  // anything set or moved since the start
  for (int e = 0; e < kElements; ++e) {
    const float x = kCorners[e].side * (gx + kHalfWidth + extra), y = kCorners[e].y;
    offset[e][0] = (k * x + user[e][0]) / s - x;
    offset[e][1] = (k * y + user[e][1]) / s - y;
    g_anchor[e][0] = x;
    g_anchor[e][1] = y;
    active = active || std::abs(offset[e][0]) > 0.01f || std::abs(offset[e][1]) > 0.01f || g_size[e] != 1.0f;
  }
  const uint32_t package = REX_LOAD_U32(hud + 36);
  static int watch_tick = 0;
  // Four times a second: the touch controls' context, and the diagnostic.
  if (package && ++watch_tick % 15 == 0) {
    const PPCContext saved_watch = ctx;
    const uint32_t right = FindObject(ctx, base, package, kRightGroup);
    ctx = saved_watch;
    if (right) {
      UpdateDriveContext(base, right);
      if (REXCVAR_GET(nfsmw_hud_watch)) WatchTree(base, right);
    }
  }
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
      g_child_moved.clear();
      const uint32_t left_outer = FindObject(ctx, base, package, kLeftOuter);
      const uint32_t right_inner = FindObject(ctx, base, package, kRightInner);
      AddPieces(base, left_outer, left, Y(base, left_outer) + Y(base, left), kMinimap, kTopLeft, kTopLeft);
      AddPieces(base, right, right_inner, Y(base, right) + Y(base, right_inner), kSpeedometer, kRaceInfo,
                kPursuitPoints);
      const uint32_t middle = FindObject(ctx, base, package, kMiddleGroup);
      AddPieces(base, 0, middle, Y(base, middle), kBottomCentre, kTopCentre, -1);
      int counts[kElements] = {};
      for (const Piece& p : g_pieces) ++counts[p.element];
      REXLOG_INFO("[hud] package {:08X}: left group {:08X}, right group {:08X} ({:08X}); pieces: minimap {}, "
                  "speedometer {}, race info {}, top left {}, top centre {}, bottom centre {}, pursuit points {} (wide {:.0f})",
                  package, left, right, right_inner, counts[kMinimap], counts[kSpeedometer], counts[kRaceInfo],
                  counts[kTopLeft], counts[kTopCentre], counts[kBottomCentre], counts[kPursuitPoints], extra);
    }
    if (dump && right) {  // once per HUD package
      dumped_package = package;
      DumpTree(base, right);
    }
    MoveGroup(base, left, -extra, 0, g_left);
    MoveGroup(base, right, extra, 0, g_right);
    for (Piece& p : g_pieces) {
      MovePiece(base, p, offset[p.element][0], offset[p.element][1]);
    }
    g_pieces_moved = true;
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

// Once the HUD's matrix is built for drawing: a piece that the game placed
// again after the HUD's update (IPA141, Stefan: the infraction list's
// lines, slid in every frame while they show, were drawn where the game
// puts them, scaled about the middle of the screen, away from their badge in
// the corner) is moved again. IPA142: moved here, the list's rows flashed
// between both places (the game also places them at other times), so a
// group placed by the game is given back to it and its children are moved
// from then on (by_children). A piece the game did not touch reads what was
// written and is left. Logged once per piece, 20 lines at most.
void ReapplyHudPieces(uint8_t* base) {
  if (!g_pieces_moved) return;
  g_pieces_moved = false;
  static int lines = 20;
  for (Piece& p : g_pieces) {
    if (REX_LOAD_U32(p.object + 0x10) != p.hash || REX_LOAD_U32(p.object) != p.vtable) return;  // freed
    const uint32_t data = REX_LOAD_U32(p.object + 44);
    if (!Plausible(data)) continue;
    const float x = LoadF(base, data + 28), y = LoadF(base, data + 32);
    if (p.by_children || p.moved.object != p.object || (x == p.moved.written_x && y == p.moved.written_y)) continue;
    // Only the top left's (IPA143, iPhone: given to the game, the
    // busted/evade bar's group kept its marker unmoved, off the bottom).
    const bool group = p.element == kTopLeft && REX_LOAD_U32(p.object + 0x18) == 5 &&
                       REX_LOAD_U32(p.object + 0x5C) == kListVtable;
    if (lines > 0) {
      --lines;
      REXLOG_INFO("[hud] piece {:08X} placed again by the game ({:.1f},{:.1f}): {}", p.hash, x, y,
                  group ? "its children moved from now on" : "moved after it");
    }
    if (group) {
      p.by_children = true;  // its own position stays the game's
      p.moved = {};
      MovePiece(base, p, g_offset[p.element][0], g_offset[p.element][1]);
    } else {
      MovePiece(base, p, g_offset[p.element][0], g_offset[p.element][1]);
    }
  }
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
float g_fit_grow = 1.0f;  // sizes also multiplied by this (fades: see below)

void Fit(uint8_t* base, uint32_t object, float sx, float sy, bool only_position) {
  const uint32_t data = REX_LOAD_U32(object + 44);
  if (!Plausible(data)) return;
  const uint32_t at[4] = {data + 28, data + 32, data + 56, data + 60};
  float now[4];
  for (int i = 0; i < 4; ++i) now[i] = LoadF(base, at[i]);
  auto [it, added] = g_fitted.try_emplace(object);
  Fitted& f = it->second;
  if (added || std::memcmp(now, f.written, sizeof(now)) != 0) std::memcpy(f.base, now, sizeof(now));
  for (int i = 0; i < 4; ++i) {
    f.written[i] = i >= 2 && only_position ? f.base[i] : f.base[i] / (i % 2 ? sy : sx) * (i >= 2 ? g_fit_grow : 1.0f);
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
bool FitWide(uint8_t* base, uint32_t object, float sx, float sy, int depth) {
  const uint32_t type = REX_LOAD_U32(object + 0x18), data = REX_LOAD_U32(object + 44);
  if (type == 1 || type == 9) {  // 9: InGameBackground.fng's pictures
    if (!Plausible(data) || std::abs(LoadF(base, data + 56)) < 400.0f) return false;
    Fit(base, object, sx, sy, false);
    g_fade_alpha = std::max(g_fade_alpha, REX_LOAD_U32(data + 12));  // FEColor b, g, r, a
    return true;
  }
  if (type != 5 || depth >= 4 || REX_LOAD_U32(object + 0x5C) != kListVtable) return false;
  bool any = false;
  int n = 0;
  for (uint32_t c = REX_LOAD_U32(object + 0x64); Plausible(c) && REX_LOAD_U32(c) != kListVtable && n < 200;
       c = REX_LOAD_U32(c + 4), ++n) {
    any = FitWide(base, c, sx, sy, depth + 1) || any;
  }
  if (any) Fit(base, object, sx, sy, true);
  return any;
}

}  // namespace

// A full-screen fade package that is up (game_state.cpp, every frame while
// one is pushed in the world): the black loading screen before a race is
// drawn through the HUD's matrix too, and at a smaller HUD size the picture
// bled through at its top and bottom (IPA78). Its full-screen images (400
// units wide or more: the black screen) are drawn as at size 1. The
// package's object list is found by its list header (vtable 0x82080030,
// count, first), logged once. IPA143 (Stefan, iPhone): the loading screen
// and the asphalt picture behind the post-race screens let the game show on
// all four sides: in HD the matrix keeps the title-safe 0.92 and, on a wide
// scene, x is narrowed by 1280/width. Those are taken out too. IPA144: still
// a thin edge (the 1200x650 images are not quite enough there), so they are
// drawn 10% larger. Called in every game state and under menus (driving: the
// HUD's size is in the matrix). IPA144 also fitted InGameBackground.fng,
// which broke the pause menu (it is that menu's dimmed panels too): left out.
// The matrix's scale beyond a full-size, full-width picture: the HUD's size
// (driving only), the title-safe scale kept (HD 0.92, SD only with
// nfsmw_hud_title_safe) and, in x, the wide scene's 1280/width.
void FullScreenScale(uint8_t* base, bool driving, float& sx, float& sy) {
  float safe_x, safe_y;
  HudSafeScale(base, safe_x, safe_y);  // 1 in HD (kept there), the SD scale
  const bool hd = REX_LOAD_U8(0x828F4A8F) != 0;
  const float hd_safe = LoadF(base, kHdSafeScale);
  const bool kept = hd || REXCVAR_GET(nfsmw_hud_title_safe);
  const float keep_x = !kept ? 1.0f : hd ? (hd_safe > 0.75f && hd_safe <= 1.0f ? hd_safe : 1.0f) : safe_x;
  const float keep_y = !kept ? 1.0f : hd ? keep_x : safe_y;
  const uint32_t width = WideWidth();
  const float s = driving ? HudScaleSetting() : 1.0f;
  sx = s * keep_x * (width ? 1280.0f / float(width) : 1.0f);
  sy = s * keep_y;
}

// InGameBackground.fng: the asphalt picture behind the post-race screens and
// the pause menu's dimmed backdrop (IPA145, Stefan: on the iPhone it covered
// only the middle). IPA144 fitted its wide images one by one and the
// narrower side pieces (254 of 1018 units) were left: dark bands. Its
// top-level groups are scaled instead (a group's size is its scale: the
// backdrop's is 1 x 2), so the pieces stay together.
extern "C" void nfsmw_hud_fit_backdrop(uint8_t* base, uint32_t package, bool driving) {
  if (!Plausible(package)) return;
  float sx, sy;
  FullScreenScale(base, driving, sx, sy);
  uint32_t at = 0;
  int n = 0;
  for (uint32_t o = FirstObject(base, package, at); Plausible(o) && REX_LOAD_U32(o) != kListVtable && n < 300;
       o = REX_LOAD_U32(o + 4), ++n) {
    if (REX_LOAD_U32(o + 0x18) == 5) Fit(base, o, sx, sy, false);
  }
}

// A package's objects logged once (two overlays up at once took turns and
// were logged every frame: 5 MB logs in minutes, IPA154).
static bool FirstTime(uint32_t package) {
  static std::unordered_set<uint32_t> said;
  return said.size() < 256 && said.insert(package).second;
}

extern "C" void nfsmw_hud_fit_fade(uint8_t* base, uint32_t package, bool driving) {
  if (!Plausible(package)) {  // none up
    g_fade_opaque = false;
    return;
  }
  uint32_t at = 0;
  const uint32_t first = FirstObject(base, package, at);
  if (FirstTime(package)) {
    REXLOG_INFO("[hud] fade package {:08X}: objects list at +{:X}, first {:08X}", package, at, first);
    int budget = 60;
    if (first) DumpObjects(base, first, 0, budget);
  }
  g_fade_alpha = 0;
  float sx, sy;
  FullScreenScale(base, driving, sx, sy);
  int n = 0;
  g_fit_grow = 1.1f;
  for (uint32_t o = first; Plausible(o) && REX_LOAD_U32(o) != kListVtable && n < 300; o = REX_LOAD_U32(o + 4), ++n) {
    FitWide(base, o, sx, sy, 0);
  }
  g_fit_grow = 1.0f;
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
// driving: the HUD's size is in the matrix (IPA146, Stefan: under the pause
// menu the song box was left moved for the smaller size, at full size and
// off the screen; there it goes back to the game's place).
extern "C" void nfsmw_hud_fit_overlay(uint8_t* base, uint32_t package, bool driving) {
  if (!Plausible(package)) return;
  uint32_t at = 0;
  const uint32_t first = FirstObject(base, package, at);
  if (FirstTime(package)) {
    REXLOG_INFO("[hud] overlay package {:08X}: objects list at +{:X}, first {:08X}", package, at, first);
    int budget = 60;
    if (first) DumpObjects(base, first, 0, budget);
  }
  const double safe = REXCVAR_GET(nfsmw_hud_safe_zone);
  const float k = safe >= 0.5 && safe <= 1.5 ? float(safe) : 1.0f;
  const float s = driving ? HudScaleSetting() : 1.0f;
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

extern "C" void nfsmw_hud_full_size(bool on) {
  if (on != g_full_size_screen) REXLOG_INFO("[hud] full-screen overlay {}", on ? "up: HUD size 1" : "gone");
  g_full_size_screen = on;
}

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
