#!/usr/bin/env python3
"""
The command processor's idle loop: yield a few times, not 64, before it sleeps
on its event (cvar ios_cp_idle_spins, default 4; 64 is the old behaviour), and
count it ("[cp-idle]" every 10 s).

    python3 tools/ios/patch_ios_cp_idle_wait.py            apply
    python3 tools/ios/patch_ios_cp_idle_wait.py --status
    python3 tools/ios/patch_ios_cp_idle_wait.py --revert

Touches src/graphics/command_processor.cpp.


WHY
===

October 24 pursuit System Trace on the iPhone (docs/TECHNICAL.md): the "GPU
Commands" thread made ~908 swtch_pri (sched_yield) calls a second from
MaybeYield() in WorkerThreadMain while the ring was empty, before falling back
to its 5 ms event wait. The event is set on every write of the ring's write
pointer (CP_RB_WPTR), so a short spin loses nothing: new work still wakes the
thread at once, and the yields stop keeping a performance core busy.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/graphics/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_cp_fast_runs, true, "GPU",'''
CVAR_NEW = '''REXCVAR_DEFINE_INT32(ios_cp_idle_spins, 4, "GPU",
                     "iOS: yields of the command processor's idle loop before it sleeps on its "
                     "event (64 before October 24)");
''' + CVAR_ANCHOR

LOOP_ANCHOR = '''      do {
        // If we spin around too much, revert to a "low-power" state.
        if (loop_count > 64) {
          const int wait_time_ms = 5;
          rex::thread::Wait(write_ptr_index_event_.get(), true,
                            std::chrono::milliseconds(wait_time_ms));
        }

        rex::thread::MaybeYield();
        loop_count++;
'''
LOOP_NEW = '''      // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_idle_wait.py): fewer yields
      // before the event wait, counted every 10 s.
      static const uint32_t ios_idle_spins = uint32_t(std::max(REXCVAR_GET(ios_cp_idle_spins), 0));
      static uint64_t ios_idle_yields = 0, ios_idle_waits = 0, ios_idle_stalls = 0;
      static auto ios_idle_since = std::chrono::steady_clock::now();
      ++ios_idle_stalls;
      do {
        // If we spin around too much, revert to a "low-power" state.
        if (loop_count > ios_idle_spins) {
          const int wait_time_ms = 5;
          rex::thread::Wait(write_ptr_index_event_.get(), true,
                            std::chrono::milliseconds(wait_time_ms));
          ++ios_idle_waits;
        } else {
          rex::thread::MaybeYield();
          ++ios_idle_yields;
        }
        loop_count++;
'''

LOG_ANCHOR = '''      nfsmw_cp_ocioso_ns.fetch_add(  // PARCHE LOCAL - tiempos
'''
LOG_NEW = '''      if (std::chrono::steady_clock::now() - ios_idle_since >= std::chrono::seconds(10)) {
        REXGPU_INFO("[cp-idle] 10 s: {} idle stalls, {} yields, {} event waits (spins before "
                    "waiting: {})",
                    ios_idle_stalls, ios_idle_yields, ios_idle_waits, ios_idle_spins);
        ios_idle_stalls = ios_idle_yields = ios_idle_waits = 0;
        ios_idle_since = std::chrono::steady_clock::now();
      }
''' + LOG_ANCHOR

BLOCKS = [
    (FILE, "the ios_cp_idle_spins cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "fewer idle yields, counted", LOOP_ANCHOR, LOOP_NEW),
    (FILE, "the [cp-idle] line", LOG_ANCHOR, LOG_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cp_idle_wait", BLOCKS))
