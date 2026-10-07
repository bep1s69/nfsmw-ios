#!/usr/bin/env python3
"""
At the 30 and 40 fps caps the UI thread's idle repaint waits 1/10 s, so it
never presents a duplicate frame just before a game frame.

    python3 tools/ios/patch_ios_ui_tick_cap.py            apply
    python3 tools/ios/patch_ios_ui_tick_cap.py --status
    python3 tools/ios/patch_ios_ui_tick_cap.py --revert

Touches src/ui/presenter.cpp. Builds on patch_ios_ui_tick.py (the idle
repaint, cvar ios_ui_repaint_hz, 30 by default) and needs ios_fps_cap
(patch_ios_present_pacing.py, same library).


WHY
===

With the guest vblank locked to the display (patch_ios_vblank_display.py) the
30 cap looked the least smooth of all, and the log said why: 37-44 presents a
second for 30 game frames. The UI thread repaints on its own when no game
frame came for 1/ios_ui_repaint_hz s, i.e. 1/30 s: at a 30 fps cap that is
exactly the time between frames, so the idle repaint kept winning the race
against the next frame. The repeat took a display refresh and the real frame
went out one refresh late.

At the 30 and 40 caps the idle repaint now waits at least 1/10 s. Game frames
are still presented at once (they force a paint); the idle repaint is still
there for overlays and paused screens.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/ui/presenter.cpp"

DECL_ANCHOR = '''REXCVAR_DEFINE_INT32(ios_ui_repaint_hz, 30, "UI",
'''
DECL_NEW = '''// LOCAL PATCH - iOS: the frame rate cap, defined in vulkan_presenter.cpp
// (tools/ios/patch_ios_ui_tick_cap.py).
REXCVAR_DECLARE(int32_t, ios_fps_cap);
REXCVAR_DEFINE_INT32(ios_ui_repaint_hz, 30, "UI",
'''

HZ_ANCHOR = '''    const int32_t hz = std::clamp<int32_t>(REXCVAR_GET(ios_ui_repaint_hz), 1, 240);
'''
HZ_NEW = '''    int32_t hz = std::clamp<int32_t>(REXCVAR_GET(ios_ui_repaint_hz), 1, 240);
    // LOCAL PATCH - iOS: at the 30 and 40 caps, never race a game frame
    // (tools/ios/patch_ios_ui_tick_cap.py).
    if (REXCVAR_GET(ios_fps_cap) == 30 || REXCVAR_GET(ios_fps_cap) == 40) {
      hz = std::min<int32_t>(hz, 10);
    }
'''

BLOCKS = [
    (F, "declare ios_fps_cap", DECL_ANCHOR, DECL_NEW),
    (F, "idle repaint at most 10 Hz at the 30 and 40 caps", HZ_ANCHOR, HZ_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_ui_tick_cap", BLOCKS))
