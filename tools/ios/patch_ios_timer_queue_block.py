#!/usr/bin/env python3
"""
The SDK's timer thread sleeps between timers instead of spinning.

    python3 tools/ios/patch_ios_timer_queue_block.py            apply
    python3 tools/ios/patch_ios_timer_queue_block.py --status
    python3 tools/ios/patch_ios_timer_queue_block.py --revert

Touches src/core/timer_queue.cpp.


WHY
===

A Time Profiler capture at the 30 fps cap (iPhone, 2026-10-13) showed
rex::thread::TimerQueue busy ~14 ms of every second in cthread_yield,
sysconf and short sleeps: disruptorplus' spin_wait_strategy waiting for the
next timer or a new one by yielding in a loop, all the time, at any frame
rate. blocking_wait_strategy waits on a condition variable until the next
timer is due (or a new one is queued) and the CPU can rest.

An empty queue waits at most a second at a time (a time_point::max deadline
on a condition variable can overflow into a busy loop).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/core/timer_queue.cpp"

INC_ANCHOR = '''#include <disruptorplus/spin_wait_strategy.hpp>
'''
INC_NEW = '''#include <disruptorplus/spin_wait_strategy.hpp>
#include <disruptorplus/blocking_wait_strategy.hpp>  // LOCAL PATCH - iOS (patch_ios_timer_queue_block.py)
'''

TYPES_ANCHOR = '''  dp::spin_wait_strategy wait_strategy_;
  dp::multi_threaded_claim_strategy<dp::spin_wait_strategy> claim_strategy_;
  dp::sequence_barrier<dp::spin_wait_strategy> consumed_;
'''
TYPES_NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_timer_queue_block.py): blocking,
  // not spinning (the thread yielded in a loop all the time).
  dp::blocking_wait_strategy wait_strategy_;
  dp::multi_threaded_claim_strategy<dp::blocking_wait_strategy> claim_strategy_;
  dp::sequence_barrier<dp::blocking_wait_strategy> consumed_;
'''

WAIT_ANCHOR = '''        dp::sequence_t available = claim_strategy_.wait_until_published(
            next_sequence, next_sequence - 1,
            wait_queue_.empty() ? clock::time_point::max() : wait_queue_.front()->due_);
'''
WAIT_NEW = '''        // LOCAL PATCH - iOS: an empty queue waits a second at a time (a
        // time_point::max deadline can overflow in a condition variable).
        dp::sequence_t available = claim_strategy_.wait_until_published(
            next_sequence, next_sequence - 1,
            wait_queue_.empty() ? clock::now() + std::chrono::seconds(1) : wait_queue_.front()->due_);
'''

HDR = "thirdparty/disruptorplus/include/disruptorplus/blocking_wait_strategy.hpp"
# disruptorplus passes the predicate before the time to wait_until/wait_for
# (std::condition_variable takes the time first): it never compiled for a
# timed wait until now.
CV_UNTIL_ANCHOR = '''                m_cv.wait_until(
                    lock,
                    [&]() -> bool {
                        result = minimum_sequence_after(sequence, count, sequences);
                        return difference(result, sequence) >= 0;
                    },
                    timeoutTime);
'''
CV_UNTIL_NEW = '''                m_cv.wait_until(  // LOCAL PATCH - iOS: time before predicate
                    lock,
                    timeoutTime,
                    [&]() -> bool {
                        result = minimum_sequence_after(sequence, count, sequences);
                        return difference(result, sequence) >= 0;
                    });
'''
CV_FOR_ANCHOR = '''                m_cv.wait_for(
                    lock,
                    [&]() -> bool {
                        result = minimum_sequence_after(sequence, count, sequences);
                        return difference(result, sequence) >= 0;
                    },
                    timeout);
'''
CV_FOR_NEW = '''                m_cv.wait_for(  // LOCAL PATCH - iOS: time before predicate
                    lock,
                    timeout,
                    [&]() -> bool {
                        result = minimum_sequence_after(sequence, count, sequences);
                        return difference(result, sequence) >= 0;
                    });
'''

BLOCKS = [
    (HDR, "condition variable waits: time before predicate", CV_UNTIL_ANCHOR, CV_UNTIL_NEW),
    (HDR, "condition variable timed wait: time before predicate", CV_FOR_ANCHOR, CV_FOR_NEW),
    (FILE, "blocking_wait_strategy included", INC_ANCHOR, INC_NEW),
    (FILE, "blocking, not spinning", TYPES_ANCHOR, TYPES_NEW),
    (FILE, "bounded wait on an empty queue", WAIT_ANCHOR, WAIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_timer_queue_block", BLOCKS))
