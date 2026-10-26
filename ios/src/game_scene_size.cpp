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
//   - the two sides moved by nfsmw_hud_left_x/y and nfsmw_hud_right_x/y, in
//     the same hook as the wide scene: the groups' x and y (object+44 -> +28,
//     +32), and the minimap with them as the game moves it (sub_8229C020):
//     its +184/+188, its children's x/y, and the map picture's offset
//     (0x82A2C60C x, 0x82A2C610 y, both read where the map is drawn).

#include <cstdint>
#include <cstring>

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
// driving, and the left (minimap, heat) and right (speedometer, nitrous)
// sides moved, in HUD units (640 across at 4:3; y down).
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_scale, 1.0, "Game", "HUD size while driving (1 = the game's)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_left_x, 0.0, "Game", "Minimap side of the HUD moved right by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_left_y, 0.0, "Game", "Minimap side of the HUD moved down by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_right_x, 0.0, "Game", "Speedometer side of the HUD moved right by (HUD units)");
REXCVAR_DEFINE_DOUBLE(nfsmw_hud_right_y, 0.0, "Game", "Speedometer side of the HUD moved down by (HUD units)");
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

// nfsmw_hud_scale while driving (menus keep the game's size), else 1.
float HudScale() {
  const double scale = REXCVAR_GET(nfsmw_hud_scale);
  return scale >= 0.5 && scale <= 1.5 && nfsmw::battery::InMenu() == 0 ? float(scale) : 1.0f;
}

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

// Where the middles of the two sides are, from the middle of the screen, in
// HUD units before the matrix (left side; the right is the mirror image):
// measured on Stefan's Oct 26 screenshots, 221 x 138 at 4:3 (the 4:3 layout),
// 120 more across at 16:9 (the game's widescreen layout). The size scales
// about the middle of the screen; the sides are moved by as much again, so
// each grows or shrinks about its own middle and keeps its margins.
constexpr float kSideX = 221.0f, kSideY = 138.0f, kWideSideX = 120.0f;

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
  const uint32_t data = REX_LOAD_U32(object + 44);
  if (!data) {
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
      const uint32_t data = child ? REX_LOAD_U32(child + 44) : 0;
      if (data) {
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

uint32_t FindObject(PPCContext& ctx, uint8_t* base, uint32_t package, uint32_t hash) {
  ctx.r3.u64 = package;
  ctx.r4.u64 = hash;
  sub_8227FD58(ctx, base);
  return ctx.r3.u32;
}

}  // namespace

// The HUD's update (sub_822AA6D0, every frame while there is a HUD): the
// sides out for a wide scene, and the player's own HUD positions
// (nfsmw_hud_left_x/y, nfsmw_hud_right_x/y, in HUD units: 640 across at 4:3).
extern "C" REX_FUNC(sub_822AA6D0) {
  const uint32_t hud = ctx.r3.u32;
  const uint8_t was_wide = hud ? REX_LOAD_U8(hud + 816) : 0;
  __imp__sub_822AA6D0(ctx, base);
  if (!hud) {
    return;
  }
  const uint32_t width = WideWidth();
  const float extra = width && REX_LOAD_U8(hud + 816) ? ExtraHudOffset(width) : 0.0f;
  // The game's own middle of a side (g), where it should be drawn (g + the
  // offset), and what to add for that through a matrix scaled by s:
  // s * (g + d) = g + offset.
  const float s = HudScale();
  const float gx = kSideX + (REX_LOAD_U8(hud + 816) ? kWideSideX : 0.0f);
  auto d = [s](float g, float offset) { return (g + offset) / s - g; };
  const float lx = d(-gx, float(REXCVAR_GET(nfsmw_hud_left_x)) - extra);
  const float ly = d(kSideY, float(REXCVAR_GET(nfsmw_hud_left_y)));
  const float rx = d(gx, float(REXCVAR_GET(nfsmw_hud_right_x)) + extra);
  const float ry = d(kSideY, float(REXCVAR_GET(nfsmw_hud_right_y)));
  if (lx == 0 && ly == 0 && rx == 0 && ry == 0 && !g_left.object && !g_right.object && !g_minimap.object) {
    return;  // nothing to move, and nothing moved
  }
  const PPCContext saved = ctx;
  const uint32_t package = REX_LOAD_U32(hud + 36);
  if (package) {
    const uint32_t left = FindObject(ctx, base, package, kLeftGroup);
    const uint32_t right = FindObject(ctx, base, package, kRightGroup);
    static uint32_t said_left = 0, said_right = 0;
    if (left != said_left || right != said_right) {
      said_left = left;
      said_right = right;
      REXLOG_INFO("[hud] left group {:08X} by {:.0f},{:.0f}; right group {:08X} by {:.0f},{:.0f} (wide {:.0f})",
                  left, lx, ly, right, rx, ry, extra);
    }
    static uint32_t dumped = 0;
    if (right && right != dumped) {  // its layout, to find the race position/progress pieces
      dumped = right;
      const uint32_t data = REX_LOAD_U32(right + 44);
      for (uint32_t o = 0; o < 0x80; o += 0x20) {
        REXLOG_INFO("[hud] right group +{:02X}: {:08X} {:08X} {:08X} {:08X} {:08X} {:08X} {:08X} {:08X}", o,
                    REX_LOAD_U32(right + o), REX_LOAD_U32(right + o + 4), REX_LOAD_U32(right + o + 8),
                    REX_LOAD_U32(right + o + 12), REX_LOAD_U32(right + o + 16), REX_LOAD_U32(right + o + 20),
                    REX_LOAD_U32(right + o + 24), REX_LOAD_U32(right + o + 28));
      }
      if (data) {
        REXLOG_INFO("[hud] right group data pos {:.1f},{:.1f} size {:.2f},{:.2f}", LoadF(base, data + 28),
                    LoadF(base, data + 32), LoadF(base, data + 56), LoadF(base, data + 60));
      }
    }
    MoveGroup(base, left, lx, ly, g_left);
    MoveGroup(base, right, rx, ry, g_right);
  }
  ctx = saved;
  MoveMinimap(base, REX_LOAD_U32(hud + 800), lx, ly, REX_LOAD_U8(hud + 816) != was_wide);
}
