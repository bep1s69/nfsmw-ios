#!/usr/bin/env python3
"""
Waits on several objects at once (WaitAny/WaitAll, e.g. the audio worker)
sleep until one of their objects is signalled instead of polling every 1 ms
(cvar ios_multi_wait, default false since dev61: dev60 showed no battery change;
kept for CPU-overhead work).

    python3 tools/ios/patch_ios_multi_wait.py            apply
    python3 tools/ios/patch_ios_multi_wait.py --status
    python3 tools/ios/patch_ios_multi_wait.py --revert

Touches src/core/threading_posix.cpp.


WHY
===

November 4 (docs/TECHNICAL.md), dev50 iPad System Trace: the audio worker
(AudioSystem::WorkerThreadMain, WaitAny over its client semaphores and the
shutdown event) woke ~825 times a second in PosixConditionBase::WaitMultiple,
which checks the objects and sleeps min(remaining, 1 ms) in a loop.

HOW
===

A multi-wait registers itself on each of its objects (ios_multi_waiters) and
sleeps on one global sequence. Every state change that can satisfy a wait
(Event set, Semaphore release, Mutant release, Timer signal, thread exit)
bumps the sequence and wakes it, but only when that object has a multi-waiter,
so single-object waits and unrelated objects add no wake-ups. The sequence is
read before the objects are checked, so a signal between the check and the
sleep makes the sleep return at once. 20 ms safety cap per sleep.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/core/threading_posix.cpp"

INC_ANCHOR = "#include <rex/thread/timer_queue.h>\n"
INC_NEW = INC_ANCHOR + """// LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)
#include <rex/cvar.h>
#if defined(__APPLE__)
#include <os/os_sync_wait_on_address.h>
#endif
REXCVAR_DEFINE_BOOL(ios_multi_wait, false, "Kernel",
                    "iOS: waits on several objects sleep until one is signalled instead of 1 ms "
                    "polling (restart required)");
"""

BASE_ANCHOR = """class PosixConditionBase {
 public:
"""
BASE_NEW = """// LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py): the sequence every
// multi-object wait sleeps on.
static std::atomic<uint32_t> ios_multi_seq{0};
static void IosMultiWake() {
  ios_multi_seq.fetch_add(1, std::memory_order_seq_cst);
#if defined(__APPLE__)
  os_sync_wake_by_address_all(&ios_multi_seq, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
}
static bool IosMultiWaitOn() {
  static const bool on = REXCVAR_GET(ios_multi_wait);
  return on;
}

""" + BASE_ANCHOR + """  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py): multi-object
  // waits registered on this object; a state change wakes them.
  std::atomic<uint32_t> ios_multi_waiters{0};
  void IosMultiNotify() {
    if (ios_multi_waiters.load(std::memory_order_seq_cst) != 0) {
      IosMultiWake();
    }
  }

"""

REG_ANCHOR = """    auto start_time = std::chrono::steady_clock::now();
    auto end_time = (timeout == std::chrono::milliseconds::max())
                        ? std::chrono::steady_clock::time_point::max()
                        : start_time + timeout;

    while (true) {
      size_t first_signaled = std::numeric_limits<size_t>::max();"""
REG_NEW = """    auto start_time = std::chrono::steady_clock::now();
    auto end_time = (timeout == std::chrono::milliseconds::max())
                        ? std::chrono::steady_clock::time_point::max()
                        : start_time + timeout;

    // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py): registered on
    // every object for the whole wait.
    struct IosRegistration {
      std::vector<PosixConditionBase*>& handles;
      const bool on;
      IosRegistration(std::vector<PosixConditionBase*>& h, bool o) : handles(h), on(o) {
        if (on) {
          for (auto* handle : handles) handle->ios_multi_waiters.fetch_add(1, std::memory_order_seq_cst);
        }
      }
      ~IosRegistration() {
        if (on) {
          for (auto* handle : handles) handle->ios_multi_waiters.fetch_sub(1, std::memory_order_seq_cst);
        }
      }
    } ios_registration{handles, IosMultiWaitOn()};

    while (true) {
      // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py): before the check.
      const uint32_t ios_seen = ios_multi_seq.load(std::memory_order_seq_cst);
      size_t first_signaled = std::numeric_limits<size_t>::max();"""

SLEEP_ANCHOR = """      if (timeout == std::chrono::milliseconds::max()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      } else {"""
SLEEP_NEW = """#if defined(__APPLE__)
      // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py): sleep until an
      // object changes (or the time is up), 20 ms safety cap.
      if (ios_registration.on) {
        const auto left = end_time - now;
        const auto cap = std::chrono::steady_clock::duration(std::chrono::milliseconds(20));
        const uint64_t ns = uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                         timeout == std::chrono::milliseconds::max() ? cap
                                                                                     : std::min(left, cap))
                                         .count());
        if (ns > 0) {
          os_sync_wait_on_address_with_timeout(&ios_multi_seq, ios_seen, sizeof(uint32_t),
                                               OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                               OS_CLOCK_MACH_ABSOLUTE_TIME, ns);
        }
        continue;
      }
#endif
""" + SLEEP_ANCHOR

EVENT_ANCHOR = """  bool Signal() override {
    auto lock = std::unique_lock<std::mutex>(mutex_);
    signal_ = true;
    cond_.notify_all();
    return true;
  }"""
EVENT_NEW = """  bool Signal() override {
    auto lock = std::unique_lock<std::mutex>(mutex_);
    signal_ = true;
    cond_.notify_all();
    IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)
    return true;
  }"""

SEM_ANCHOR = """    count_ += release_count;
    cond_.notify_all();
    return true;"""
SEM_NEW = """    count_ += release_count;
    cond_.notify_all();
    IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)
    return true;"""

MUT_ANCHOR = """      if (count_ == 0) {
        cond_.notify_all();
      }"""
MUT_NEW = """      if (count_ == 0) {
        cond_.notify_all();
        IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)
      }"""

TIMER_ANCHOR = """  bool Signal() override {
    std::lock_guard<std::mutex> lock(mutex_);
    signal_ = true;
    cond_.notify_all();
    return true;
  }"""
TIMER_NEW = """  bool Signal() override {
    std::lock_guard<std::mutex> lock(mutex_);
    signal_ = true;
    cond_.notify_all();
    IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)
    return true;
  }"""

EXIT_ANCHOR = """      exit_code_ = exit_code;
      signaled_ = true;
      cond_.notify_all();"""
EXIT_NEW = EXIT_ANCHOR + """
      IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)"""

EXIT2_ANCHOR = """    thread->handle_.signaled_ = true;
    thread->handle_.cond_.notify_all();"""
EXIT2_NEW = EXIT2_ANCHOR + """
    thread->handle_.IosMultiNotify();  // LOCAL PATCH - iOS (tools/ios/patch_ios_multi_wait.py)"""

BLOCKS = [
    (FILE, "includes and the ios_multi_wait cvar", INC_ANCHOR, INC_NEW),
    (FILE, "the multi-wait sequence and per-object registration", BASE_ANCHOR, BASE_NEW),
    (FILE, "registration and the sequence read", REG_ANCHOR, REG_NEW),
    (FILE, "sleep on the sequence", SLEEP_ANCHOR, SLEEP_NEW),
    (FILE, "Event set notifies", EVENT_ANCHOR, EVENT_NEW),
    (FILE, "Semaphore release notifies", SEM_ANCHOR, SEM_NEW),
    (FILE, "Mutant release notifies", MUT_ANCHOR, MUT_NEW),
    (FILE, "Timer signal notifies", TIMER_ANCHOR, TIMER_NEW),
    (FILE, "thread exit notifies", EXIT_ANCHOR, EXIT_NEW),
    (FILE, "thread exit (other path) notifies", EXIT2_ANCHOR, EXIT2_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_multi_wait", BLOCKS))
