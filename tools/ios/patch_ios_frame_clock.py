#!/usr/bin/env python3
"""
A hook on the guest clock, for the app's frame-step clock (iOS).

    python3 tools/ios/patch_ios_frame_clock.py            apply
    python3 tools/ios/patch_ios_frame_clock.py --status
    python3 tools/ios/patch_ios_frame_clock.py --revert

Touches include/rex/chrono/clock.h and src/core/clock.cpp.


WHY
===

At 60 fps the game world judders with every frame shown 16.7 ms apart
(D-005; Oct 28 iPhone logs): the motion inside the frames is uneven. The
game reads the clock (mftb, KeQueryPerformanceCounter) on its main thread,
and those reads jitter by about a millisecond around the vblank they follow.
ios/src/frame_clock.cpp (cvar nfsmw_frame_clock_ms, 0 = off) snaps the main
thread's reads shortly after a vblank to that vblank, so each frame advances
by exactly one vblank. This only adds the hook; with no filter set nothing
changes.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

HEADER = "include/rex/chrono/clock.h"
SOURCE = "src/core/clock.cpp"

H_ANCHOR = '''  static uint64_t QueryGuestTickCount();
'''
H_NEW = '''  static uint64_t QueryGuestTickCount();
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS (tools/ios/patch_ios_frame_clock.py): when set, every
  // guest tick count read goes through it (the app's frame-step clock).
  static void set_guest_tick_filter(uint64_t (*filter)(uint64_t));
#endif
'''

C_ANCHOR = '''uint64_t Clock::QueryGuestTickCount() {
  auto guest_tick_count = UpdateGuestClock();
  return guest_tick_count;
}
'''
C_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_frame_clock.py).
static std::atomic<uint64_t (*)(uint64_t)> ios_guest_tick_filter{nullptr};

void Clock::set_guest_tick_filter(uint64_t (*filter)(uint64_t)) {
  ios_guest_tick_filter.store(filter, std::memory_order_release);
}
#endif

uint64_t Clock::QueryGuestTickCount() {
  auto guest_tick_count = UpdateGuestClock();
#if REX_PLATFORM_IOS
  if (auto filter = ios_guest_tick_filter.load(std::memory_order_acquire)) {
    return filter(guest_tick_count);
  }
#endif
  return guest_tick_count;
}
'''

INC_ANCHOR = '''#include <algorithm>
#include <limits>
'''
INC_NEW = '''#include <algorithm>
#include <atomic>  // LOCAL PATCH - iOS (patch_ios_frame_clock.py)
#include <limits>
'''

BLOCKS = [
    (HEADER, "guest tick filter declared", H_ANCHOR, H_NEW),
    (SOURCE, "atomic included", INC_ANCHOR, INC_NEW),
    (SOURCE, "guest tick filter", C_ANCHOR, C_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_frame_clock", BLOCKS))
