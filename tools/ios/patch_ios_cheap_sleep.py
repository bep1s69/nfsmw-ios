#!/usr/bin/env python3
"""
Short sleeps with one kernel call instead of three (iOS).

    python3 tools/ios/patch_ios_cheap_sleep.py            apply
    python3 tools/ios/patch_ios_cheap_sleep.py --status
    python3 tools/ios/patch_ios_cheap_sleep.py --revert

Touches src/core/threading_posix.cpp.


WHY
===

At the 30 fps cap (Time Profiler, iPhone, 2026-10-13) a game thread spent
~9 ms of every second in mach_msg under clock_get_time, under nanosleep,
under rex::thread::Sleep (KeDelayExecutionThread): Darwin's nanosleep reads
the calendar clock through a Mach message before and after the wait. The
game sleeps in short slices all the time. mach_wait_until() is one trap on
the monotonic clock; a zero sleep is a yield.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/core/threading_posix.cpp"

ANCHOR = '''void Sleep(std::chrono::microseconds duration) {
  timespec rqtp = DurationToTimeSpec(duration);'''
NEW = '''void Sleep(std::chrono::microseconds duration) {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS (tools/ios/patch_ios_cheap_sleep.py): one trap on the
  // monotonic clock (nanosleep reads the calendar clock via Mach messages).
  if (duration.count() <= 0) {
    sched_yield();
    return;
  }
  {
    static const mach_timebase_info_data_t timebase = [] {
      mach_timebase_info_data_t t{};
      mach_timebase_info(&t);
      return t;
    }();
    const uint64_t ns = uint64_t(duration.count()) * 1000u;
    const uint64_t ticks = ns * timebase.denom / timebase.numer;
    mach_wait_until(mach_absolute_time() + ticks);
    return;
  }
#endif
  timespec rqtp = DurationToTimeSpec(duration);'''

INC_ANCHOR = '''#include <rex/platform.h>
'''
INC_NEW = '''#include <rex/platform.h>
#if REX_PLATFORM_IOS
#include <mach/mach_time.h>  // LOCAL PATCH - iOS (patch_ios_cheap_sleep.py)
#endif
'''

BLOCKS = [
    (FILE, "mach_time included", INC_ANCHOR, INC_NEW),
    (FILE, "one-trap sleep", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cheap_sleep", BLOCKS))
