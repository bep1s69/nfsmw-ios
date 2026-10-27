#!/usr/bin/env python3
"""
The thread that fires the guest vblank ("GPU VSync") gets Mach real-time
priority (cvar ios_vblank_realtime, default on).

    python3 tools/ios/patch_ios_vblank_realtime.py            apply
    python3 tools/ios/patch_ios_vblank_realtime.py --status
    python3 tools/ios/patch_ios_vblank_realtime.py --revert

Touches src/graphics/graphics_system.cpp. Ported from SpeedBreaker v0.1.4
(github.com/SpeedBreakerProject/speedbreaker, runtime/video/vblank_timer.cpp,
GPL-3.0), which runs the same USA disc: on macOS that thread woke up to 9 ms
late, and every late wake is a late guest vblank, so a frame starts late.

The thread only runs the guest vblank interrupt and sleeps, so it asks for
very little: thread_time_constraint_policy with period = the guest vblank
interval (16.7 ms, 8.3 ms at the 40 and 120 caps), computation 1 ms,
constraint 2 ms, preemptible. Here the thread also ran at Utility QoS with the
other guest threads (patch_ios_utility_qos.py, ios_utility_qos_guest); the
real-time policy replaces that for this one thread. Logged once:
"[ios-vblank] real-time priority".
"""
import sys
from patch_engine import run

F = "src/graphics/graphics_system.cpp"

TOP_ANCHOR = "#include <rex/cvar.h>\n"
TOP_NEW = '''#include <rex/cvar.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: real-time priority for the guest vblank thread
// (tools/ios/patch_ios_vblank_realtime.py; from SpeedBreaker v0.1.4).
#include <mach/mach.h>
#include <mach/mach_time.h>
#include <mach/thread_policy.h>
#include <pthread.h>
REXCVAR_DEFINE_BOOL(ios_vblank_realtime, true, "GPU",
                    "iOS: Mach real-time priority for the thread that fires the guest vblank "
                    "(restart required)");
#endif
'''

LOOP_ANCHOR = '''        uint64_t guest_tick_frequency = chrono::Clock::guest_tick_frequency();
        uint64_t vsync_interval_ticks ='''
LOOP_NEW = '''#if REX_PLATFORM_IOS
        // LOCAL PATCH - iOS: real-time priority (tools/ios/patch_ios_vblank_realtime.py).
        if (REXCVAR_GET(ios_vblank_realtime)) {
          mach_timebase_info_data_t tb;
          mach_timebase_info(&tb);
          const auto abs = [&](double ns) { return uint32_t(ns * tb.denom / tb.numer); };
          thread_time_constraint_policy_data_t policy;
          policy.period = abs(1e9 / refresh_rate_hz);
          policy.computation = abs(1e6);
          policy.constraint = abs(2e6);
          policy.preemptible = 1;
          const kern_return_t kr =
              thread_policy_set(pthread_mach_thread_np(pthread_self()), THREAD_TIME_CONSTRAINT_POLICY,
                                reinterpret_cast<thread_policy_t>(&policy),
                                THREAD_TIME_CONSTRAINT_POLICY_COUNT);
          REXGPU_INFO("[ios-vblank] real-time priority ({:.2f} ms period): {}",
                      1e3 / refresh_rate_hz, kr == KERN_SUCCESS ? "set" : "FAILED");
        }
#endif
        uint64_t guest_tick_frequency = chrono::Clock::guest_tick_frequency();
        uint64_t vsync_interval_ticks ='''

BLOCKS = [
    (F, "the cvar and Mach headers", TOP_ANCHOR, TOP_NEW),
    (F, "real-time policy at the vblank thread's start", LOOP_ANCHOR, LOOP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_vblank_realtime", BLOCKS))
