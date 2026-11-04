#!/usr/bin/env python3
"""
The length of the host sleep behind the game's zero-length waits
(KeDelayExecutionThread with a timeout under 1 ms), as a cvar
(ios_delay0_us, default 100 = the SDK's behaviour), counted every 10 s
("[delay0]").

    python3 tools/ios/patch_ios_delay0.py            apply
    python3 tools/ios/patch_ios_delay0.py --status
    python3 tools/ios/patch_ios_delay0.py --revert

Touches src/system/xthread.cpp.


WHY
===

November 4 (docs/TECHNICAL.md): the dev50 iPad System Trace (Max run) has
the game main loop thread calling this sleep ~5,400 times a second from
sub_82441DB0 (waiting for the render thread to take the next frame) and the
render thread ~1,400 times a second from sub_82441B60, each a ~0.13 ms
mach_wait_until followed by ~2 us of work. A longer sleep is a probe of how
much battery those wake-ups cost; it can delay the frame hand-off by up to
the sleep length. 0 or less yields instead of sleeping.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/system/xthread.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ignore_thread_priorities, true, "Kernel",'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_delay0.py).
REXCVAR_DEFINE_INT32(ios_delay0_us, 100, "Kernel",
                     "iOS: host sleep in microseconds for the game's zero-length waits of "
                     "low-priority threads (100 = SDK behaviour, <= 0 yields; restart required)");
''' + CVAR_ANCHOR

DELAY_ANCHOR = '''    if (timeout_ms == 0) {
      if (priority_ <= rex::thread::ThreadPriority::kBelowNormal) {
        rex::thread::Sleep(std::chrono::microseconds(100));
      } else {
        rex::thread::MaybeYield();
      }
'''
DELAY_NEW = '''    if (timeout_ms == 0) {
      if (priority_ <= rex::thread::ThreadPriority::kBelowNormal) {
        // LOCAL PATCH - iOS (tools/ios/patch_ios_delay0.py): sleep length from
        // ios_delay0_us, counted every 10 s.
        static const int32_t ios_delay0_us = REXCVAR_GET(ios_delay0_us);
        static std::atomic<uint64_t> ios_delay0_count{0};
        static std::atomic<int64_t> ios_delay0_since{0};
        ios_delay0_count.fetch_add(1, std::memory_order_relaxed);
        const int64_t ios_now = std::chrono::duration_cast<std::chrono::milliseconds>(
                                    std::chrono::steady_clock::now().time_since_epoch())
                                    .count();
        int64_t ios_since = ios_delay0_since.load(std::memory_order_relaxed);
        if (ios_since == 0) {
          ios_delay0_since.compare_exchange_strong(ios_since, ios_now);
        } else if (ios_now - ios_since >= 10000 &&
                   ios_delay0_since.compare_exchange_strong(ios_since, ios_now)) {
          const uint64_t n = ios_delay0_count.exchange(0, std::memory_order_relaxed);
          REXLOG_INFO("[delay0] 10 s: {} zero-length waits ({:.0f}/s), host sleep {} us", n,
                      n * 1000.0 / double(ios_now - ios_since), ios_delay0_us);
        }
        if (ios_delay0_us > 0) {
          rex::thread::Sleep(std::chrono::microseconds(ios_delay0_us));
        } else {
          rex::thread::MaybeYield();
        }
      } else {
        rex::thread::MaybeYield();
      }
'''

BLOCKS = [
    (FILE, "the ios_delay0_us cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "configurable zero-length wait, counted", DELAY_ANCHOR, DELAY_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_delay0", BLOCKS))
