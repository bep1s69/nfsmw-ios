#!/usr/bin/env python3
"""
SDL's video driver on iOS: uikit, not cocoa.

    python3 tools/ios/patch_ios_sdl.py            apply
    python3 tools/ios/patch_ios_sdl.py --status
    python3 tools/ios/patch_ios_sdl.py --revert

Touches src/ui/windowed_app_context_sdl.cpp.

On Apple the SDK forces SDL's video driver to "cocoa" (macOS' desktop driver,
which provides the CAMetalLayer). REX_PLATFORM_MAC is also 1 on iOS, so the
game asked for cocoa there too, and on the first run on an iPad M4:

    SDL_InitSubSystem(SDL_INIT_VIDEO) failed: cocoa not available
    Could not initialize the SDL context

The app then returned from main, and on iOS SDL keeps its window up when that
happens: a black screen, forever, with no game line in the log
(ios/src/boot_trace.cpp is what found it). The Vulkan probe never hit this
because it does not set the hint.

SDL's iOS driver is "uikit"; it also hands out a CAMetalLayer through
SDL_Metal_CreateView, which is what the SDK's macOS path uses
(window_sdl.cpp), so nothing else changes. The video_driver cvar still wins
when set.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

ANCHOR = '''#if REX_PLATFORM_MAC
  // macOS presents via a CAMetalLayer surface obtained from the Cocoa driver.
  if (requested_driver.empty()) {
    requested_driver = "cocoa";
  }
#endif
'''
NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: SDL's iOS driver is uikit; cocoa does not exist there
  // ("cocoa not available"). It hands out a CAMetalLayer the same way
  // (tools/ios/patch_ios_sdl.py).
  if (requested_driver.empty()) {
    requested_driver = "uikit";
  }
#elif REX_PLATFORM_MAC
  // macOS presents via a CAMetalLayer surface obtained from the Cocoa driver.
  if (requested_driver.empty()) {
    requested_driver = "cocoa";
  }
#endif
'''

BLOCKS = [
    ("src/ui/windowed_app_context_sdl.cpp", "uikit video driver on iOS", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_sdl", BLOCKS))
