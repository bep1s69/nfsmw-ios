#!/usr/bin/env python3
"""
A frame rate cap: 30, 40, 60 (the game's own) or 120 fps.

    python3 tools/ios/patch_ios_fps_cap.py            apply
    python3 tools/ios/patch_ios_fps_cap.py --status
    python3 tools/ios/patch_ios_fps_cap.py --revert

Touches src/graphics/command_processor.cpp and src/graphics/graphics_system.cpp.
Builds on tools/parche_vblank.py (the vblank counter, nfsmw_vblank_seq) and
patch_ios_vblank_grid.py.


HOW
===

The game flips on the guest vblank, which "GPU VSync" emulates at 60 Hz. The
cap counts in vblanks, so frames stay on the vblank rhythm and are evenly
spaced:

    cap  vblank   vblanks per frame
     30   60 Hz   2
     60   60 Hz   1   (no wait: as before)
     40  120 Hz   3
    120  120 Hz   1

The wait is just before the command processor handles a swap: the frame is
not presented until N vblanks after the previous one was. A frame that is
already slower than that does not wait at all (so a 30 cap with a 20 ms frame
is 30, not 20). Holding the command processor back holds the game back too,
so the CPU and GPU idle the rest of the time: that is the battery and heat
saving.

40 and 120 run the guest vblank at 120 Hz. The game was made for a 60 Hz
vblank; if it counts time in vblanks anywhere, things may run fast there. They
are marked experimental in the pre-launch screen.

Cvar ios_fps_cap (30, 40, 60, 120), default 60, defined in the runtime by
patch_ios_present_pacing.py (the presenter needs it too), declared here.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CP = "src/graphics/command_processor.cpp"
GS = "src/graphics/graphics_system.cpp"

CVAR_ANCHOR = '''REXCVAR_DECLARE(bool, ios_thread_qos);
#endif
'''
CVAR_NEW = '''REXCVAR_DECLARE(bool, ios_thread_qos);
// LOCAL PATCH - iOS: the frame rate cap (tools/ios/patch_ios_fps_cap.py).
// Defined in the runtime, in vulkan_presenter.cpp (patch_ios_present_pacing.py),
// which paces presentation by it too and cannot see the GPU plugin's cvars.
REXCVAR_DECLARE(int32_t, ios_fps_cap);
#endif
'''

CAP_ANCHOR = '''#else
  rex::thread::Sleep(tope);
#endif
}

void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
'''
CAP_NEW = '''#else
  rex::thread::Sleep(tope);
#endif
}

#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: the frame rate cap (tools/ios/patch_ios_fps_cap.py).
// Called just before a swap is handled: not before N vblanks have passed since
// the previous swap. A late frame does not wait.
static void IosCapBeforeSwap() {
  static uint32_t last_swap_vblank = 0;
  static bool have_last = false;
  const int32_t cap = REXCVAR_GET(ios_fps_cap);
  const uint32_t vblanks = cap == 30 ? 2u : cap == 40 ? 3u : 1u;
  if (vblanks > 1 && have_last) {
    const uint32_t target = last_swap_vblank + vblanks;
    // A bounded number of waits: never stall the GPU thread if vblanks stop.
    for (int i = 0; i < 8 &&
                    int32_t(nfsmw_vblank_seq.load(std::memory_order_acquire) - target) < 0;
         ++i) {
      NfsmwEsperarVblank(std::chrono::milliseconds(50));
    }
  }
  last_swap_vblank = nfsmw_vblank_seq.load(std::memory_order_acquire);
  have_last = true;
}
#endif

void CommandProcessor::WriteRegister(uint32_t index, uint32_t value) {
'''

SWAP_ANCHOR = '''  reader->AdvanceRead((count - 4) * sizeof(uint32_t));

  IssueSwap(frontbuffer_ptr, frontbuffer_width, frontbuffer_height);
'''
SWAP_NEW = '''  reader->AdvanceRead((count - 4) * sizeof(uint32_t));

#if REX_PLATFORM_IOS
  IosCapBeforeSwap();  // LOCAL PATCH - iOS: the frame rate cap
#endif
  IssueSwap(frontbuffer_ptr, frontbuffer_width, frontbuffer_height);
'''

GS_DECL_ANCHOR = '''#include <rex/cvar.h>
'''
GS_DECL_NEW = '''#include <rex/cvar.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: defined in command_processor.cpp (patch_ios_fps_cap.py).
// Here, at file scope: inside the namespace it would name another cvar.
REXCVAR_DECLARE(int32_t, ios_fps_cap);
#endif
'''

GS_RATE_ANCHOR = '''        double refresh_rate_hz = std::max(1.0, double(float(video_mode.refresh_rate)));
'''
GS_RATE_NEW = '''        double refresh_rate_hz = std::max(1.0, double(float(video_mode.refresh_rate)));
#if REX_PLATFORM_IOS
        // LOCAL PATCH - iOS: 40 and 120 fps caps need a 120 Hz guest vblank
        // (tools/ios/patch_ios_fps_cap.py).
        if (REXCVAR_GET(ios_fps_cap) == 40 || REXCVAR_GET(ios_fps_cap) == 120) {
          refresh_rate_hz = 120.0;
        }
#endif
'''

BLOCKS = [
    (CP, "the ios_fps_cap cvar", CVAR_ANCHOR, CVAR_NEW),
    (CP, "the cap: N vblanks between swaps", CAP_ANCHOR, CAP_NEW),
    (CP, "apply the cap before each swap", SWAP_ANCHOR, SWAP_NEW),
    (GS, "declare ios_fps_cap", GS_DECL_ANCHOR, GS_DECL_NEW),
    (GS, "a 120 Hz vblank for 40 and 120", GS_RATE_ANCHOR, GS_RATE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_fps_cap", BLOCKS))
