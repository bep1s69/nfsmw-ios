#!/usr/bin/env python3
"""Live guest vblank transitions for 30/40/60/120; apply LAST after pacing patches.

Earlier patch status may report superseded blocks absent (also true before
this patch). Exact anchors, transactional writes and --revert via patch_engine.
"""
import sys
from patch_engine import run
GS = 'src/graphics/graphics_system.cpp'
CP = 'src/graphics/command_processor.cpp'
RATE = '''            const int32_t cap = REXCVAR_GET(ios_fps_cap);
'''
LIVE = RATE + '''            // LOCAL PATCH - iOS: live FPS groups (patch_ios_live_fps.py).
            static int32_t ios_previous_cap = -1;
            const double requested_hz = cap == 40 || cap == 120 ? 120.0 : 60.0;
            if (ios_previous_cap != cap) {
              ios_previous_cap = cap;
              refresh_rate_hz = requested_hz;
              vsync_interval_ticks = std::max(uint64_t(1),
                  uint64_t(double(guest_tick_frequency) / refresh_rate_hz));
              last_frame_time = chrono::Clock::QueryGuestTickCount();
              ios_last_fired_ns = IosMachNs();
              ios_locked_said = false;
              nfsmw_vblank_120.store(refresh_rate_hz == 120.0, std::memory_order_release);
              if (REXCVAR_GET(ios_vblank_realtime)) {
                mach_timebase_info_data_t tb;
                mach_timebase_info(&tb);
                thread_time_constraint_policy_data_t policy;
                policy.period = uint32_t(1e9 / refresh_rate_hz * tb.denom / tb.numer);
                policy.computation = uint32_t(1e6 * tb.denom / tb.numer);
                policy.constraint = uint32_t(2e6 * tb.denom / tb.numer);
                policy.preemptible = 1;
                const auto kr = thread_policy_set(pthread_mach_thread_np(pthread_self()),
                    THREAD_TIME_CONSTRAINT_POLICY, reinterpret_cast<thread_policy_t>(&policy),
                    THREAD_TIME_CONSTRAINT_POLICY_COUNT);
                REXGPU_INFO("[live-fps] cap {}, guest {:.0f} Hz, real-time policy {}",
                            cap, refresh_rate_hz, kr == KERN_SUCCESS ? "set" : "FAILED");
              }
            }
'''
HISTORY = '''  const bool vblank_120 = nfsmw_vblank_120.load(std::memory_order_relaxed);
'''
RESET = HISTORY + '''  // LOCAL PATCH - iOS: drop the previous cap's swap phase.
  static int32_t previous_cap = -1;
  static bool previous_high = false;
  if (previous_cap != cap || previous_high != vblank_120) {
    have_last = false;
    previous_cap = cap;
    previous_high = vblank_120;
  }
'''
WAIT = '''    for (int i = 0; i < 8 &&
                    int32_t(nfsmw_vblank_seq.load(std::memory_order_acquire) - target) < 0;
'''
NEW_WAIT = '''    for (int i = 0; i < 8 && REXCVAR_GET(ios_fps_cap) == cap &&
                    nfsmw_vblank_120.load(std::memory_order_acquire) == vblank_120 &&
                    int32_t(nfsmw_vblank_seq.load(std::memory_order_acquire) - target) < 0;
'''
BLOCKS = [(GS, 'runtime guest rate and phase', RATE, LIVE),
          (CP, 'swap phase reset', HISTORY, RESET),
          (CP, 'interrupt stale cap wait', WAIT, NEW_WAIT)]
if __name__ == '__main__':
    sys.exit(run('ios_live_fps', BLOCKS))
