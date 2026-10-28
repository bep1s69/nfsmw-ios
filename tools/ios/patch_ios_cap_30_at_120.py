#!/usr/bin/env python3
"""
The 30 fps cap also when the guest vblank runs at 120 Hz (iOS).

    python3 tools/ios/patch_ios_cap_30_at_120.py            apply
    python3 tools/ios/patch_ios_cap_30_at_120.py --status
    python3 tools/ios/patch_ios_cap_30_at_120.py --revert

Touches src/graphics/command_processor.cpp and src/graphics/graphics_system.cpp.

The guest vblank's rate is chosen when its thread starts: 120 Hz when the
game starts at the 40 (or 120) cap. "30 fps in menus" and "30 fps when warm"
(ios/src/battery.mm) now also work at the 40 cap (0.4.2, Stefan): they set the
cap to 30 while playing, and the cap counted 2 vblanks a frame, 60 fps at
120 Hz. The thread now records its rate, and the 30 cap counts 4 vblanks at
120 Hz.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CP = "src/graphics/command_processor.cpp"
GS = "src/graphics/graphics_system.cpp"

CP_ANCHOR = '''  const uint32_t vblanks = cap == 30 ? 2u : cap == 40 ? 3u : 1u;'''
CP_NEW = '''  // LOCAL PATCH - iOS (patch_ios_cap_30_at_120.py): 30 at a 120 Hz vblank too.
  const bool vblank_120 = nfsmw_vblank_120.load(std::memory_order_relaxed);
  const uint32_t vblanks = cap == 30 ? (vblank_120 ? 4u : 2u) : cap == 40 ? 3u : 1u;'''

CP_DECL_ANCHOR = '''// LOCAL PATCH - iOS: the frame rate cap (tools/ios/patch_ios_fps_cap.py).
// Called just before a swap is handled: not before N vblanks have passed since'''
CP_DECL_NEW = '''// LOCAL PATCH - iOS (patch_ios_cap_30_at_120.py): the guest vblank runs at
// 120 Hz (set by GraphicsSystem's vblank thread when it starts, in the runtime).
extern "C" std::atomic<bool> nfsmw_vblank_120;
''' + CP_DECL_ANCHOR

GS_ANCHOR = '''        if (REXCVAR_GET(ios_fps_cap) == 40 || REXCVAR_GET(ios_fps_cap) == 120) {
          refresh_rate_hz = 120.0;
        }'''
GS_NEW = '''        if (REXCVAR_GET(ios_fps_cap) == 40 || REXCVAR_GET(ios_fps_cap) == 120) {
          refresh_rate_hz = 120.0;
          nfsmw_vblank_120.store(true);  // LOCAL PATCH - iOS (patch_ios_cap_30_at_120.py)
        }'''

GS_DECL_ANCHOR = '''REXCVAR_DECLARE(int32_t, ios_fps_cap);
'''
GS_DECL_NEW = '''REXCVAR_DECLARE(int32_t, ios_fps_cap);
// LOCAL PATCH - iOS (patch_ios_cap_30_at_120.py): the guest vblank runs at
// 120 Hz; read by the GPU plugin's frame rate cap.
extern "C" __attribute__((visibility("default"))) std::atomic<bool> nfsmw_vblank_120{false};
'''

BLOCKS = [
    (CP, "vblank-rate flag", CP_DECL_ANCHOR, CP_DECL_NEW),
    (CP, "30 cap counts 4 vblanks at 120 Hz", CP_ANCHOR, CP_NEW),
    (GS, "vblank-rate flag declared", GS_DECL_ANCHOR, GS_DECL_NEW),
    (GS, "vblank thread records 120 Hz", GS_ANCHOR, GS_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cap_30_at_120", BLOCKS))
