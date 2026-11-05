#!/usr/bin/env python3
"""
Fewer host wake-ups on threads outside the frame path (November 6, dev89):

1. Alertable sleeps (`rex::thread::AlertableSleep`) sleep the whole remaining
   time on a per-thread word that QueueUserCallback (APCs) bumps and wakes,
   instead of 1 ms slices. Cvar `ios_alertable_wait` (true; false = slices).
2. An XMA kick that was decoded inline no longer wakes the XMA worker for an
   empty sweep. Cvar `ios_xma_kick_wake` (false; true = wake it as before).
3. With `ios_multi_wait=true`, a multi-object wait sleeps on a word of its own
   that only its own objects bump, not the process-wide sequence. Cvar
   `ios_multi_wait_own` (true; false = the dev60 global sequence).
   `[multi-wait] 10 s: N waits, S sleeps, O overflowed` when on.
4. Census only: `ios_timer_census` (false) logs the guest's SetTimer due
   times/periods every 10 s (`[timer-census]`).

    python3 tools/ios/patch_ios_wake_cuts.py            apply
    python3 tools/ios/patch_ios_wake_cuts.py --status
    python3 tools/ios/patch_ios_wake_cuts.py --revert

Touches src/core/threading_posix.cpp (after patch_ios_multi_wait.py),
src/audio/xma_decoder.cpp and src/system/xtimer.cpp.


WHY
===

dev88 iPhone System Trace (docs/TECHNICAL.md "November 6: wake-up sources
outside D3D"): the game's 5 ms and 10 ms alertable sleeps woke 5-10 times
each (~1,780/s on two guest threads); the XMA worker woke ~1,500/s after
kicks it had nothing left to do for; the audio worker woke ~930/s for ~188
audio permits/s (global multi-wait sequence); TimerQueue ~1,240/s from two
guest threads re-arming one-shot timers (due times unknown, hence the census).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

TP = "src/core/threading_posix.cpp"
XMA = "src/audio/xma_decoder.cpp"
XT = "src/system/xtimer.cpp"

# --- threading_posix.cpp -------------------------------------------------

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_multi_wait, false, "Kernel",'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py).
REXCVAR_DEFINE_BOOL(ios_alertable_wait, true, "Kernel",
                    "iOS: alertable sleeps wait the whole time and wake on a queued callback "
                    "instead of 1 ms slices (restart required)");
REXCVAR_DEFINE_BOOL(ios_multi_wait_own, true, "Kernel",
                    "iOS: with ios_multi_wait, each multi-object wait sleeps on its own word, "
                    "bumped only by its own objects (restart required)");
''' + CVAR_ANCHOR

SLEEP_ANCHOR = '''SleepResult AlertableSleep(std::chrono::microseconds duration) {
  alertable_state_ = true;
  auto deadline = std::chrono::steady_clock::now() + duration;
  while (true) {
'''
SLEEP_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): the current thread's
// callback word (defined after PosixCondition<Thread>), nullptr if none.
std::atomic<uint32_t>* IosCurrentApcWord();

SleepResult AlertableSleep(std::chrono::microseconds duration) {
  alertable_state_ = true;
  auto deadline = std::chrono::steady_clock::now() + duration;
#if defined(__APPLE__)
  // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): sleep the whole
  // remaining time; QueueUserCallback bumps and wakes the word.
  static const bool ios_alertable_wait = REXCVAR_GET(ios_alertable_wait);
  if (std::atomic<uint32_t>* ios_word = ios_alertable_wait ? IosCurrentApcWord() : nullptr) {
    while (true) {
      const uint32_t ios_seen = ios_word->load(std::memory_order_seq_cst);
      if (DispatchCurrentThreadUserCallback()) {
        alertable_state_ = false;
        return SleepResult::kAlerted;
      }
      auto now = std::chrono::steady_clock::now();
      if (now >= deadline) {
        alertable_state_ = false;
        return SleepResult::kSuccess;
      }
      const uint64_t ns =
          uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(deadline - now).count());
      if (ns > 0) {
        os_sync_wait_on_address_with_timeout(ios_word, ios_seen, sizeof(uint32_t),
                                             OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                             OS_CLOCK_MACH_ABSOLUTE_TIME, ns);
      }
    }
  }
#endif
  while (true) {
'''

QUEUE_ANCHOR = '''      user_callbacks_.push_back(std::move(callback));
      has_pending_user_callbacks_.store(true, std::memory_order_release);
    }
'''
QUEUE_NEW = QUEUE_ANCHOR + '''#if defined(__APPLE__)
    // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): wake an alertable
    // sleep of this thread.
    ios_apc_word.fetch_add(1, std::memory_order_seq_cst);
    os_sync_wake_by_address_all(&ios_apc_word, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
'''

MEMBER_ANCHOR = '''  std::deque<std::function<void()>> user_callbacks_;
  std::atomic<bool> has_pending_user_callbacks_{false};
'''
MEMBER_NEW = MEMBER_ANCHOR + '''
 public:
  // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): bumped per queued
  // callback; alertable sleeps wait on it.
  std::atomic<uint32_t> ios_apc_word{0};

 private:
'''

CURRENT_ANCHOR = '''bool DispatchCurrentThreadUserCallback() {
  if (!current_thread_condition_) {
    Thread::GetCurrentThread();
  }
  return current_thread_condition_ && current_thread_condition_->DispatchQueuedUserCallbacks();
}
'''
CURRENT_NEW = CURRENT_ANCHOR + '''
// LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py).
std::atomic<uint32_t>* IosCurrentApcWord() {
  if (!current_thread_condition_) {
    Thread::GetCurrentThread();
  }
  return current_thread_condition_ ? &current_thread_condition_->ios_apc_word : nullptr;
}
'''

NOTIFY_ANCHOR = '''  std::atomic<uint32_t> ios_multi_waiters{0};
  void IosMultiNotify() {
    if (ios_multi_waiters.load(std::memory_order_seq_cst) != 0) {
      IosMultiWake();
    }
  }
'''
NOTIFY_NEW = '''  std::atomic<uint32_t> ios_multi_waiters{0};
  // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): words of the
  // multi-object waits registered on this object (ios_multi_wait_own).
  static constexpr int kIosOwnSlots = 4;
  std::atomic<std::atomic<uint32_t>*> ios_own_words[kIosOwnSlots] = {};
  void IosMultiNotify() {
    if (ios_multi_waiters.load(std::memory_order_seq_cst) != 0) {
      IosMultiWake();
    }
    for (auto& slot : ios_own_words) {
      if (std::atomic<uint32_t>* w = slot.load(std::memory_order_seq_cst)) {
        w->fetch_add(1, std::memory_order_seq_cst);
#if defined(__APPLE__)
        os_sync_wake_by_address_all(w, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
      }
    }
  }
'''

REG_ANCHOR = '''    struct IosRegistration {
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
'''
REG_NEW = '''    // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): with
    // ios_multi_wait_own the wait registers a word of its own (from a pool
    // that is never freed; two threads sharing one only wake each other) in
    // a free slot of every object; no free slot = 1 ms cap for this wait.
    struct IosRegistration {
      std::vector<PosixConditionBase*>& handles;
      const bool on;
      std::atomic<uint32_t>* word = nullptr;
      bool overflow = false;
      IosRegistration(std::vector<PosixConditionBase*>& h, bool o) : handles(h), on(o) {
        if (!on) return;
        static const bool own = REXCVAR_GET(ios_multi_wait_own);
        if (!own) {
          for (auto* handle : handles) handle->ios_multi_waiters.fetch_add(1, std::memory_order_seq_cst);
          return;
        }
        static std::atomic<uint32_t> pool[256];
        static std::atomic<uint32_t> next{0};
        thread_local std::atomic<uint32_t>* mine =
            &pool[next.fetch_add(1, std::memory_order_relaxed) % 256];
        word = mine;
        for (auto* handle : handles) {
          bool placed = false;
          for (auto& slot : handle->ios_own_words) {
            std::atomic<uint32_t>* expected = nullptr;
            if (slot.compare_exchange_strong(expected, word, std::memory_order_seq_cst)) {
              placed = true;
              break;
            }
          }
          if (!placed) overflow = true;
        }
        IosOwnStats(overflow);
      }
      ~IosRegistration() {
        if (!on) return;
        if (!word) {
          for (auto* handle : handles) handle->ios_multi_waiters.fetch_sub(1, std::memory_order_seq_cst);
          return;
        }
        for (auto* handle : handles) {
          for (auto& slot : handle->ios_own_words) {
            std::atomic<uint32_t>* expected = word;
            if (slot.compare_exchange_strong(expected, nullptr, std::memory_order_seq_cst)) break;
          }
        }
      }
      // waits, overflowed waits, and sleeps, logged every 10 s.
      static std::atomic<uint64_t>& Sleeps() {
        static std::atomic<uint64_t> s{0};
        return s;
      }
      static void IosOwnStats(bool overflowed) {
        static std::atomic<uint64_t> waits{0}, overflows{0};
        static std::atomic<int64_t> since{0};
        ++waits;
        if (overflowed) ++overflows;
        const int64_t now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                                   std::chrono::steady_clock::now().time_since_epoch())
                                   .count();
        int64_t s = since.load();
        if (!s) {
          since.compare_exchange_strong(s, now_ms);
        } else if (now_ms - s >= 10000 && since.compare_exchange_strong(s, now_ms)) {
          REXLOG_INFO("[multi-wait] 10 s: {} waits, {} sleeps, {} overflowed (own words)",
                      waits.exchange(0), Sleeps().exchange(0), overflows.exchange(0));
        }
      }
    } ios_registration{handles, IosMultiWaitOn()};
'''

SEEN_ANCHOR = '''      const uint32_t ios_seen = ios_multi_seq.load(std::memory_order_seq_cst);
'''
SEEN_NEW = '''      // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): own word if any.
      const uint32_t ios_seen = ios_registration.word
                                    ? ios_registration.word->load(std::memory_order_seq_cst)
                                    : ios_multi_seq.load(std::memory_order_seq_cst);
'''

WAIT_ANCHOR = '''        const auto cap = std::chrono::steady_clock::duration(std::chrono::milliseconds(20));
        const uint64_t ns = uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                         timeout == std::chrono::milliseconds::max() ? cap
                                                                                     : std::min(left, cap))
                                         .count());
        if (ns > 0) {
          os_sync_wait_on_address_with_timeout(&ios_multi_seq, ios_seen, sizeof(uint32_t),
'''
WAIT_NEW = '''        // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): own word, 1 ms
        // cap if an object had no free slot.
        const auto cap = std::chrono::steady_clock::duration(
            std::chrono::milliseconds(ios_registration.overflow ? 1 : 20));
        const uint64_t ns = uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                                         timeout == std::chrono::milliseconds::max() ? cap
                                                                                     : std::min(left, cap))
                                         .count());
        std::atomic<uint32_t>* ios_wait_word =
            ios_registration.word ? ios_registration.word : &ios_multi_seq;
        if (ios_registration.word) IosRegistration::Sleeps().fetch_add(1, std::memory_order_relaxed);
        if (ns > 0) {
          os_sync_wait_on_address_with_timeout(ios_wait_word, ios_seen, sizeof(uint32_t),
'''

# --- xma_decoder.cpp -----------------------------------------------------

XCVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ffmpeg_verbose, false, "Audio", "Verbose FFmpeg output (debug and above)");
'''
XCVAR_NEW = XCVAR_ANCHOR + '''// LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py).
REXCVAR_DEFINE_BOOL(ios_xma_kick_wake, false, "Audio",
                    "iOS: wake the XMA worker after a kick was decoded inline (the old "
                    "behaviour; false skips that empty sweep)");
'''

KICK_ANCHOR = '''        if (context.Work()) {
          context.SignalWorkDone();
        }
      }
    }
    work_event_->Set();
  } else if (r >= XmaRegister::Context0Lock && r <= XmaRegister::Context9Lock) {'''
KICK_NEW = '''        if (context.Work()) {
          context.SignalWorkDone();
        }
      }
    }
    // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): every kicked
    // context ran inline above (Work() clears its enable bit), so the worker
    // would only sweep and sleep again.
    static const bool ios_kick_wake = [] {
      const bool on = REXCVAR_GET(ios_xma_kick_wake);
      REXLOG_INFO("[xma] worker wake after inline kick decode: {} (ios_xma_kick_wake)",
                  on ? "on" : "off");
      return on;
    }();
    if (ios_kick_wake) {
      work_event_->Set();
    }
  } else if (r >= XmaRegister::Context0Lock && r <= XmaRegister::Context9Lock) {'''

# --- xtimer.cpp ----------------------------------------------------------

TINC_ANCHOR = '''#include <rex/system/xtimer.h>
'''
TINC_NEW = TINC_ANCHOR + '''// LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): timer census.
#include <rex/cvar.h>
#include <atomic>
#include <map>
#include <mutex>
#include <utility>
REXCVAR_DEFINE_BOOL(ios_timer_census, false, "Kernel",
                    "iOS: log the guest's SetTimer due times and periods every 10 s "
                    "(logging only)");
'''

TSET_ANCHOR = '''  period_ms = chrono::Clock::ScaleGuestDurationMillis(period_ms);
  WinSystemClock::time_point due_tp;
'''
TSET_NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_wake_cuts.py): census of the
  // requested due time (100 ns units, negative = relative) and period.
  static const bool ios_census = REXCVAR_GET(ios_timer_census);
  if (ios_census) {
    static std::mutex m;
    static std::map<std::pair<int64_t, uint32_t>, uint64_t> seen;
    static int64_t since = 0;
    const int64_t now_ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                               std::chrono::steady_clock::now().time_since_epoch())
                               .count();
    std::lock_guard<std::mutex> lock(m);
    ++seen[{due_time < 0 ? due_time : 1, period_ms}];
    if (!since) {
      since = now_ms;
    } else if (now_ms - since >= 10000) {
      std::string line;
      uint64_t total = 0;
      for (auto& [k, n] : seen) {
        total += n;
        line += fmt::format(" | due {} ({:.3f} ms) period {} ms x{}",
                            k.first == 1 ? std::string("absolute") : std::to_string(k.first),
                            k.first == 1 ? 0.0 : -k.first / 10000.0, k.second, n);
      }
      REXLOG_INFO("[timer-census] 10 s: {} SetTimer calls ({:.0f}/s){}", total,
                  total * 1000.0 / double(now_ms - since), line);
      seen.clear();
      since = now_ms;
    }
  }
''' + TSET_ANCHOR

BLOCKS = [
    (TP, "alertable-wait and own-word cvars", CVAR_ANCHOR, CVAR_NEW),
    (TP, "alertable sleep waits on the callback word", SLEEP_ANCHOR, SLEEP_NEW),
    (TP, "queued callback wakes the word", QUEUE_ANCHOR, QUEUE_NEW),
    (TP, "per-thread callback word", MEMBER_ANCHOR, MEMBER_NEW),
    (TP, "current thread's callback word", CURRENT_ANCHOR, CURRENT_NEW),
    (TP, "objects wake their own multi-waiters", NOTIFY_ANCHOR, NOTIFY_NEW),
    (TP, "multi-wait registers its own word", REG_ANCHOR, REG_NEW),
    (TP, "multi-wait reads its own word", SEEN_ANCHOR, SEEN_NEW),
    (TP, "multi-wait sleeps on its own word", WAIT_ANCHOR, WAIT_NEW),
    (XMA, "ios_xma_kick_wake cvar", XCVAR_ANCHOR, XCVAR_NEW),
    (XMA, "no worker wake after an inline kick decode", KICK_ANCHOR, KICK_NEW),
    (XT, "timer census cvar", TINC_ANCHOR, TINC_NEW),
    (XT, "timer census", TSET_ANCHOR, TSET_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_wake_cuts", BLOCKS))
