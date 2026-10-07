#!/usr/bin/env python3
"""
Choose whether the screen layer runs at the display's full pixel density.

    python3 tools/ios/patch_ios_retina.py            apply
    python3 tools/ios/patch_ios_retina.py --status
    python3 tools/ios/patch_ios_retina.py --revert

Touches src/ui/window_sdl.cpp.

The SDK creates its SDL window with SDL_WINDOW_HIGH_PIXEL_DENSITY, so on iOS
the CAMetalLayer is at the screen's native pixels: 2752x2064 on an iPad Pro
M4, 5.7 million pixels painted for a game image of 1280x720 (0.9 million).
Without the flag the layer is at point resolution, still larger than the
game's image, and iOS scales it to the screen: 1600x1200 on that iPad as it
was set up (Display Zoom "More Space": 2752/1600 = the "contents scale 1.7"
MoltenVK logs), 1376x1032 with the default zoom.

In a heavy race on that iPad each UI paint took 25-28 ms, almost all of it
not acquire or present: very likely waiting for the GPU. A cvar to compare,
from Documents/extra_args.txt, without rebuilding:

    --ios_retina=true     (or false, or auto)

Default "auto": point resolution only where the screen's points are at least
1280x720, the game's own image, so nothing is lost; full density otherwise.
On that iPad the paint's cost did not change (it was all inside vkQueueSubmit
either way, see ios/src/ios_main.mm, ios_async_submits), but input felt more
direct at point resolution. On an iPhone 17 Pro Max the points are 956x440:
smaller than the game's image, so there "auto" means full density (a plain
"off" default made the phone's picture soft). --ios_retina=true or false
forces it; with a higher internal resolution (resolution_scale) the full
density will matter.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

W = "src/ui/window_sdl.cpp"

CVAR_ANCHOR = '''namespace rex::ui {

namespace {
'''
CVAR_NEW = '''// LOCAL PATCH - iOS: the screen layer at full pixel density or at points
// (tools/ios/patch_ios_retina.py).
#if REX_PLATFORM_IOS
REXCVAR_DEFINE_STRING(ios_retina, "auto", "Display",
                      "iOS: paint the screen at its full pixel density (true), at point "
                      "resolution (false), or auto: points where they are at least the game's "
                      "1280x720, full density otherwise");
#endif

namespace rex::ui {

namespace {
'''

FLAGS_ANCHOR = '''  SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY | SDL_WINDOW_HIDDEN;
'''
FLAGS_NEW = '''  SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY | SDL_WINDOW_HIDDEN;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: without it, the CAMetalLayer is at point resolution.
  {
    const std::string retina = REXCVAR_GET(ios_retina);
    bool full_density = retina == "true" || retina == "on" || retina == "1";
    if (retina != "false" && retina != "off" && retina != "0" && !full_density) {
      // auto: SDL's display bounds on iOS are in points.
      SDL_Rect bounds{};
      full_density = !SDL_GetDisplayBounds(SDL_GetPrimaryDisplay(), &bounds) ||
                     std::max(bounds.w, bounds.h) < 1280 || std::min(bounds.w, bounds.h) < 720;
      REXLOG_INFO("WindowSDL: ios_retina auto: screen {}x{} points -> {}", bounds.w, bounds.h,
                  full_density ? "full density" : "point resolution");
    }
    if (!full_density) {
      flags &= ~SDL_WindowFlags(SDL_WINDOW_HIGH_PIXEL_DENSITY);
    }
  }
#endif
'''

BLOCKS = [
    (W, "the ios_retina cvar", CVAR_ANCHOR, CVAR_NEW),
    (W, "drop high pixel density when off", FLAGS_ANCHOR, FLAGS_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_retina", BLOCKS))
