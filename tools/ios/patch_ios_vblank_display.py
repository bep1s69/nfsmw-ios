#!/usr/bin/env python3
"""
At the 30 and 40 fps caps the guest vblank follows the real display refresh
(phase-locked to CADisplayLink's timestamps) instead of a free-running timer.

    python3 tools/ios/patch_ios_vblank_display.py            apply
    python3 tools/ios/patch_ios_vblank_display.py --status
    python3 tools/ios/patch_ios_vblank_display.py --revert

Touches src/graphics/graphics_system.cpp. Works with ios/src/display_rate.mm
(which publishes the display's refresh times) and patch_ios_fps_cap.py (whose
cap counts guest vblanks).


WHY
===

At the 40 cap the game made exactly 40 frames a second, the display ran at
120 Hz, and yet every so often a frame was shown one refresh late. The guest
vblank ("GPU VSync" thread) is a timer of its own, the screen refresh is
another clock: the two drift against each other, and each time a guest vblank
crosses a refresh boundary a frame lands late. Target present times
(patch_ios_present_pacing.py) could only hide this: tight, and 30 was uneven;
loose, and 30 had input lag.

So the guest vblank now comes from the display. display_rate.mm's CADisplayLink
publishes, on every refresh, the refresh's timestamp and the period
(nfsmw_display_vsync). The vblank thread fires a guest vblank at each display
refresh, computed from those timestamps (not from when the main thread's
callback happened to run), and sleeps until the next one. The cap then counts
real refreshes: frames are made and shown in step with the screen.

At the 30 and 40 caps, where each frame has time to spare, a frame that misses
a refresh waits for the next, as on the console. October 26 (IPA86): the 60
cap locks too (cvar ios_vblank_lock_60, default on). Its free-running timer
showed the same drift: in iPad races 2-6 of every 300 frames came as a 25 ms +
8 ms pair instead of two 16.7 ms frames, a small stutter every 1-3 s that the
locked 40 cap did not have. The fps cap's rule that a late frame is shown at
once (not held to the next vblank) is unchanged. At 120 the timer stays. It locks only if the display's period is within 10 % of
the guest vblank interval (60 Hz for 30, 120 Hz for 40) and a refresh came in
the last 250 ms; otherwise, the timer. Cvar ios_vblank_from_display, default on.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/graphics_system.cpp"

TOP_ANCHOR = '''REXCVAR_DECLARE(int32_t, ios_fps_cap);
#endif
'''
TOP_NEW = '''REXCVAR_DECLARE(int32_t, ios_fps_cap);
// LOCAL PATCH - iOS: the display's refresh, published by the app's
// CADisplayLink (ios/src/display_rate.mm; tools/ios/patch_ios_vblank_display.py).
#include <atomic>
#include <cmath>
#include <mach/mach_time.h>
REXCVAR_DEFINE_BOOL(ios_vblank_from_display, true, "GPU",
                    "iOS: at the 30 and 40 fps caps, the guest vblank follows the display's "
                    "refresh instead of a timer of its own");
REXCVAR_DEFINE_BOOL(ios_vblank_lock_60, true, "GPU",
                    "iOS: at the 60 fps cap too, the guest vblank follows the display's "
                    "refresh (needs ios_vblank_from_display)");
namespace {
std::atomic<uint64_t> ios_display_vsync_ns{0};
std::atomic<uint64_t> ios_display_period_ns{0};
uint64_t IosMachNs() {
  static mach_timebase_info_data_t timebase = {};
  if (!timebase.denom) {
    mach_timebase_info(&timebase);
  }
  return mach_absolute_time() * timebase.numer / timebase.denom;
}
}  // namespace
// The app calls this (found with dlsym) on every display refresh: the
// refresh's time and the period, in mach_absolute_time nanoseconds.
extern "C" __attribute__((visibility("default"))) void nfsmw_display_vsync(uint64_t vsync_ns,
                                                                           uint64_t period_ns) {
  ios_display_period_ns.store(period_ns, std::memory_order_relaxed);
  ios_display_vsync_ns.store(vsync_ns, std::memory_order_release);
}
#endif
'''

LOOP_ANCHOR = '''        while (vsync_worker_running_) {
          uint64_t current_time = chrono::Clock::QueryGuestTickCount();
'''
LOOP_NEW = '''        while (vsync_worker_running_) {
#if REX_PLATFORM_IOS
          // LOCAL PATCH - iOS: at the 30, 40 and 60 caps, a guest vblank at
          // each display refresh (tools/ios/patch_ios_vblank_display.py).
          {
            static uint64_t ios_last_fired_ns = 0;
            static bool ios_locked_said = false;
            const int32_t cap = REXCVAR_GET(ios_fps_cap);
            const uint64_t vsync_ns = ios_display_vsync_ns.load(std::memory_order_acquire);
            const uint64_t period_ns = ios_display_period_ns.load(std::memory_order_relaxed);
            const uint64_t now_ns = IosMachNs();
            const double guest_interval_ns = 1e9 / refresh_rate_hz;
            const bool lock =
                (cap == 30 || cap == 40 || (cap == 60 && REXCVAR_GET(ios_vblank_lock_60))) &&
                REXCVAR_GET(ios_vblank_from_display) &&
                REXCVAR_GET(vsync) && vsync_ns && period_ns && now_ns >= vsync_ns &&
                now_ns - vsync_ns < 250000000ull &&
                std::fabs(double(period_ns) - guest_interval_ns) < guest_interval_ns * 0.1;
            if (lock) {
              if (!ios_locked_said) {
                ios_locked_said = true;
                REXGPU_INFO("[ios-vblank] cap {}: guest vblank locked to the display refresh "
                            "({:.2f} ms)",
                            cap, double(period_ns) / 1e6);
              }
              // The latest display refresh at or before now.
              const uint64_t latest = vsync_ns + ((now_ns - vsync_ns) / period_ns) * period_ns;
              if (latest > ios_last_fired_ns + period_ns / 2) {
                MarkVblank();
                NfsmwAvisarVblank();
                ios_last_fired_ns = latest;
                last_frame_time = chrono::Clock::QueryGuestTickCount();
                continue;
              }
              const uint64_t wake_ns = latest + period_ns;
              if (wake_ns > now_ns + 100000) {
                NfsmwEsperarSwap(int64_t(wake_ns - now_ns));
              } else {
                rex::thread::MaybeYield();
              }
              continue;
            }
          }
#endif
          uint64_t current_time = chrono::Clock::QueryGuestTickCount();
'''

BLOCKS = [
    (F, "the display refresh and the cvar", TOP_ANCHOR, TOP_NEW),
    (F, "a guest vblank at each display refresh", LOOP_ANCHOR, LOOP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_vblank_display", BLOCKS))
