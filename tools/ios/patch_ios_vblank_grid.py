#!/usr/bin/env python3
"""
The guest vblank keeps an exact 60 Hz: a wake-up that comes a little late is
made up, instead of pushing every later vblank back.

    python3 tools/ios/patch_ios_vblank_grid.py            apply
    python3 tools/ios/patch_ios_vblank_grid.py --status
    python3 tools/ios/patch_ios_vblank_grid.py --revert

Touches src/graphics/graphics_system.cpp. Builds on tools/parche_vblank.py
(Android), applied first by prepare_sdk.py.


WHY
===

The menus topped out at 57-58 fps on an iPad Pro M4, with the GPU nearly
idle, and so did the fastest moments of a race. The "GPU VSync" thread marks
the guest's vblank every 16.67 ms (60 Hz) and the game, double-buffered, flips
on it, so the vblank rate is the frame rate's ceiling.

parche_vblank makes the thread sleep until the next vblank is due and then
re-anchors the grid on the moment it actually woke:

    last_frame_time = current_time;

That is on purpose for a frame that is really late (it sets the new rhythm
instead of the game losing a whole vblank). But a sleep on iOS always wakes a
little late, 0.3-1 ms, and re-anchoring keeps that delay: each vblank is
counted from the late one before it, ~17.2 ms apart, 58 Hz.

Now, if the wake-up is at most kCatchUpMs late, the grid moves by exactly one
interval (the next vblank comes that much sooner, and the average stays at
60 Hz). Later than that, it re-anchors as before. Cvar ios_vblank_catch_up,
default on; false gives back parche_vblank's behaviour.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/graphics_system.cpp"

CVAR_ANCHOR = '''void NfsmwAvisarVblank();
'''
CVAR_NEW = '''void NfsmwAvisarVblank();
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: the vblank grid makes up small wake-up delays
// (tools/ios/patch_ios_vblank_grid.py).
REXCVAR_DEFINE_BOOL(ios_vblank_catch_up, true, "GPU",
                    "iOS: make up the vblank thread's small wake-up delays, so the guest "
                    "vblank stays at 60 Hz instead of ~58");
#endif
'''

GRID_ANCHOR = '''            last_frame_time = current_time;
            marcado = true;
'''
GRID_NEW = '''#if REX_PLATFORM_IOS
            // LOCAL PATCH - iOS: up to 2 ms late is the sleep waking late, not
            // a late frame: keep the grid (the next vblank comes that much
            // sooner). Later than that, re-anchor as before.
            const uint64_t ios_catch_up_ticks = guest_tick_frequency / 500;  // 2 ms
            if (REXCVAR_GET(ios_vblank_catch_up) &&
                current_time - last_frame_time < interval_ticks + ios_catch_up_ticks) {
              last_frame_time += interval_ticks;
            } else {
              last_frame_time = current_time;
            }
#else
            last_frame_time = current_time;
#endif
            marcado = true;
'''

BLOCKS = [
    (F, "the ios_vblank_catch_up cvar", CVAR_ANCHOR, CVAR_NEW),
    (F, "keep the vblank grid", GRID_ANCHOR, GRID_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_vblank_grid", BLOCKS))
