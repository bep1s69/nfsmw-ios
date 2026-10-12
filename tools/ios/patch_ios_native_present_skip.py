#!/usr/bin/env python3
"""
While the native renderer shows the game, the emulated renderer does not
refresh or present its own (hidden) output.

    python3 tools/ios/patch_ios_native_present_skip.py            apply
    python3 tools/ios/patch_ios_native_present_skip.py --status
    python3 tools/ios/patch_ios_native_present_skip.py --revert

Touches src/ui/presenter.cpp. Builds on patch_ios_native_only.py (the flag
rex_native_draws_only, defined in src/ui/vulkan/vulkan_presenter.cpp).

patch_ios_native_only.py skips the emulated renderer's draws, but every guest
frame still went through RefreshGuestOutput: a full-screen gamma pass on the
command processor, then the UI thread painting and presenting a 2868x1320
image (~55 per second) under the native layer, where nobody sees it. GPU,
memory bandwidth and compositor work for nothing (the log's "[ios-swap] UI
paints 55/s"). With the flag set, the refresh is skipped as if it had failed
(the last image stays, unshown); FMVs clear the flag and it resumes.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/ui/presenter.cpp"

ANCHOR_DECL = '''#include <pthread.h>  // LOCAL PATCH - iOS: pthread_main_np (patch_ios_paint_suspend.py)
'''
NEW_DECL = '''#include <pthread.h>  // LOCAL PATCH - iOS: pthread_main_np (patch_ios_paint_suspend.py)

// LOCAL PATCH - iOS: set while the native renderer shows the game
// (vulkan_presenter.cpp; tools/ios/patch_ios_native_present_skip.py).
extern std::atomic<bool> rex_native_draws_only;
'''

ANCHOR = '''  bool is_active = writable_properties.IsActive();
  ios_timing::g_frames.fetch_add(1, std::memory_order_relaxed);  // LOCAL PATCH - iOS
'''
NEW = '''  bool is_active = writable_properties.IsActive();
  ios_timing::g_frames.fetch_add(1, std::memory_order_relaxed);  // LOCAL PATCH - iOS
  // LOCAL PATCH - iOS: the native renderer shows the game: no gamma pass, no
  // paint, no present of this hidden output (patch_ios_native_present_skip.py).
  if (rex_native_draws_only.load(std::memory_order_relaxed)) {
    return false;
  }
'''

BLOCKS = [
    (FILE, "declare the native flag", ANCHOR_DECL, NEW_DECL),
    (FILE, "skip the refresh while native shows", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_native_present_skip", BLOCKS))
