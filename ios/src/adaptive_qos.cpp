// Adaptive QoS (--ios_adaptive_qos, default false): the game's main thread and
// the GPU command thread at Utility QoS (efficiency cores, cheaper clocks) while
// frames arrive on time, back to User Initiated as soon as they do not.
//
// Utility QoS for those two threads cut the iPad Pro M4's estimated drain by a
// quarter at 1.5x / 60 (docs/TECHNICAL.md, October 21), but an iPhone 17 Pro
// (4 efficiency cores) could not hold 60 that way. Here the GPU command thread
// watches the time between swaps: 2 late frames (over 1.2x the cap's interval)
// in the last 120 switch both threads to User Initiated for a hold time, then they
// try Utility again. A retry that fails within 10 s doubles the hold (20 s up to
// 240 s); 60 s on Utility resets it. Each thread can only set its own QoS: the
// command thread at its swap (NativeSwap), the main thread in the game's
// deferred-call runner (sub_823C8290, called from its main loop).
//
// --ios_adaptive_qos_workers (default true): User Initiated also covers the other
// guest threads (Utility through --ios_utility_qos_guest) and the native render
// queue. The October 24 pursuit trace (docs/TECHNICAL.md) had main on the
// performance cores waiting on a guest worker left at Utility on the efficiency
// cores and preempted most of each 80 ms gap. Those threads cannot be asked to
// set their own QoS, so the command thread starts an override on each one
// (pthread_override_qos_class_start_np) and ends it on the way back to Utility.
//
// The boost is tunable: --ios_adaptive_qos_level (user_initiated or default),
// the longest hold --ios_adaptive_qos_max_hold (seconds) and
// --ios_adaptive_qos_workers_count (the busiest guest threads by CPU time; 0
// raises all of them). The defaults are IPA48's (user_initiated, 240 s, all),
// the boost proven in pursuits; IPA49's Default / 20 s / 3 saved no battery on
// the iPhone (docs/TECHNICAL.md, October 24). --ios_adaptive_qos_ipa48=true
// forces the IPA48 values over Extra Args.

#include <pthread.h>
#include <pthread/qos.h>
#include <mach/mach.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

#include <rex/cvar.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(ios_adaptive_qos, false, "Kernel",
                    "Experiment: main and GPU command threads at Utility QoS while frames are on time "
                    "(restart required)");
REXCVAR_DEFINE_BOOL(ios_adaptive_qos_workers, true, "Kernel",
                    "Adaptive QoS: User Initiated also raises the other guest threads and the "
                    "native render queue (restart required)");
REXCVAR_DEFINE_STRING(ios_adaptive_qos_level, "user_initiated", "Kernel",
                      "Adaptive QoS: the class of a boost, default or user_initiated (restart required)");
REXCVAR_DEFINE_INT32(ios_adaptive_qos_max_hold, 240, "Kernel",
                     "Adaptive QoS: longest boost in seconds; IPA49 tried 20 (restart required)");
REXCVAR_DEFINE_INT32(ios_adaptive_qos_workers_count, 0, "Kernel",
                     "Adaptive QoS: how many guest threads a boost raises, busiest first by CPU time; "
                     "0 raises all (restart required)");
REXCVAR_DEFINE_BOOL(ios_adaptive_qos_ipa48, false, "Kernel",
                    "Adaptive QoS: the IPA48 boost (user_initiated, 240 s, all guest threads); "
                    "overrides the three settings above (restart required)");

namespace {

std::atomic<int> mode{-1};  // 0 Utility, 1 boosted
using Clock = std::chrono::steady_clock;

struct Boost {
  qos_class_t qos;
  const char* name;
  double max_hold_s;
  int workers;  // 0: all
};

const Boost& Settings() {
  static const Boost boost = [] {
    if (REXCVAR_GET(ios_adaptive_qos_ipa48)) return Boost{QOS_CLASS_USER_INITIATED, "User Initiated", 240.0, 0};
    const bool user_initiated = REXCVAR_GET(ios_adaptive_qos_level) == "user_initiated";
    return Boost{user_initiated ? QOS_CLASS_USER_INITIATED : QOS_CLASS_DEFAULT,
                 user_initiated ? "User Initiated" : "Default",
                 double(std::clamp<int32_t>(REXCVAR_GET(ios_adaptive_qos_max_hold), 5, 240)),
                 std::max<int32_t>(REXCVAR_GET(ios_adaptive_qos_workers_count), 0)};
  }();
  return boost;
}

void Apply(int m, int& applied) {
  if (m < 0 || m == applied) return;
  pthread_set_qos_class_self_np(m == 0 ? QOS_CLASS_UTILITY : Settings().qos, 0);
  applied = m;
}

bool WorkersOn() {
  static const bool on = REXCVAR_GET(ios_adaptive_qos_workers);
  return on;
}

// Guest threads keep their default names ("XThreadDF1B (F8000010)"; the main
// thread is "Main XThread", which follows the mode itself).
std::vector<pthread_override_t> overrides;

void RaiseGuestThreads(bool raise) {
  for (pthread_override_t o : overrides) pthread_override_qos_class_end_np(o);
  overrides.clear();
  if (!raise) return;
  thread_act_array_t threads = nullptr;
  mach_msg_type_number_t count = 0;
  if (task_threads(mach_task_self(), &threads, &count) != KERN_SUCCESS) return;
  // (CPU time since the previous boost, thread), busiest first.
  static std::vector<std::pair<uint64_t, uint64_t>> last_us;  // (thread id, CPU time)
  std::vector<std::pair<uint64_t, uint64_t>> now_us;
  std::vector<std::pair<uint64_t, pthread_t>> guests;
  for (mach_msg_type_number_t i = 0; i < count; ++i) {
    pthread_t thread = pthread_from_mach_thread_np(threads[i]);
    char name[64] = {};
    thread_identifier_info_data_t id = {};
    thread_basic_info_data_t basic = {};
    mach_msg_type_number_t n = THREAD_IDENTIFIER_INFO_COUNT, b = THREAD_BASIC_INFO_COUNT;
    if (thread && pthread_getname_np(thread, name, sizeof(name)) == 0 && std::strncmp(name, "XThread", 7) == 0 &&
        thread_info(threads[i], THREAD_IDENTIFIER_INFO, thread_info_t(&id), &n) == KERN_SUCCESS &&
        thread_info(threads[i], THREAD_BASIC_INFO, thread_info_t(&basic), &b) == KERN_SUCCESS) {
      const uint64_t us = uint64_t(basic.user_time.seconds + basic.system_time.seconds) * 1000000 +
                          basic.user_time.microseconds + basic.system_time.microseconds;
      uint64_t before = 0;
      for (const auto& [tid, t] : last_us) {
        if (tid == id.thread_id) before = t;
      }
      now_us.push_back({id.thread_id, us});
      guests.push_back({us - std::min(us, before), thread});
    }
    mach_port_deallocate(mach_task_self(), threads[i]);
  }
  vm_deallocate(mach_task_self(), vm_address_t(threads), count * sizeof(thread_act_t));
  last_us.swap(now_us);
  std::sort(guests.begin(), guests.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
  const size_t limit = Settings().workers ? size_t(Settings().workers) : guests.size();
  for (size_t i = 0; i < guests.size() && i < limit; ++i) {
    if (pthread_override_t o = pthread_override_qos_class_start_np(guests[i].second, Settings().qos, 0)) {
      overrides.push_back(o);
    }
  }
}

}  // namespace

namespace nfsmw::adaptive_qos {

bool Enabled() {
  static const bool on = REXCVAR_GET(ios_adaptive_qos) && !rex::cvar::Query<bool>("ios_utility_qos");
  return on;
}

// For the native render queue: submit this frame at the boost's class (0 when not boosted).
qos_class_t WorkersRaised() {
  return Enabled() && WorkersOn() && mode.load(std::memory_order_relaxed) == 1 ? Settings().qos
                                                                               : QOS_CLASS_UNSPECIFIED;
}

// On the GPU command thread, once per swap.
void OnSwap(double interval_ms) {
  if (!Enabled()) return;
  static int applied = -1;
  static bool late[120] = {};
  static int at = 0, late_count = 0;
  static Clock::time_point hold_until, eco_since = Clock::now();
  static double hold_s = 20.0;
  static int lines = 0;
  const auto now = Clock::now();
  int m = mode.load(std::memory_order_relaxed);
  if (m < 0) {
    m = 0;
    mode.store(0, std::memory_order_relaxed);
    REXLOG_INFO("[adaptive-qos] on: main and GPU command threads start at Utility; guest workers and render queue {}",
                WorkersOn() ? "follow the mode" : "stay at Utility");
    REXLOG_INFO("[adaptive-qos] boost: {} QoS, holds up to {:.0f} s, {} guest threads{}", Settings().name,
                Settings().max_hold_s,
                Settings().workers ? fmt::format("the {} busiest", Settings().workers) : std::string("all"),
                REXCVAR_GET(ios_adaptive_qos_ipa48) ? " (IPA48 settings)" : "");
  }
  const int32_t cap = std::max<int32_t>(rex::cvar::Query<int32_t>("ios_fps_cap"), 1);
  const double budget = 1000.0 / cap;
  const bool is_late = interval_ms > budget * 1.2 && interval_ms < 250.0;  // not loading stalls
  late_count += int(is_late) - int(late[at]);
  late[at] = is_late;
  at = (at + 1) % 120;
  if (m == 0 && late_count >= 2) {
    const double eco_s = std::chrono::duration<double>(now - eco_since).count();
    hold_s = eco_s < 10.0 ? std::min(hold_s * 2.0, Settings().max_hold_s) : eco_s > 60.0 ? 20.0 : hold_s;
    hold_s = std::min(hold_s, Settings().max_hold_s);
    hold_until = now + std::chrono::milliseconds(int64_t(hold_s * 1000));
    m = 1;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] {} for {:.0f} s ({} late frames of 120, {:.0f} s on Utility)", Settings().name, hold_s, late_count, eco_s);
  } else if (m == 1 && now >= hold_until) {
    m = 0;
    eco_since = now;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] back to Utility");
  }
  if (m != mode.load(std::memory_order_relaxed)) {
    std::fill(std::begin(late), std::end(late), false);
    late_count = 0;
    mode.store(m, std::memory_order_relaxed);
    if (WorkersOn()) {
      RaiseGuestThreads(m == 1);
      if (m == 1 && lines < 60) REXLOG_INFO("[adaptive-qos] {} guest threads and the render queue raised", overrides.size());
    }
  }
  Apply(m, applied);
}

// On the game's main thread (the first thread to call it), once per loop.
// The owner is settled once per thread: the game calls this hundreds of
// thousands of times a second in pursuits, and the compare-exchange on every
// call cost ~8 ms/s on the iPhone (IPA63 profile).
void OnMainLoop() {
  if (!Enabled()) return;
  static std::atomic<uint64_t> owner{0};
  thread_local int applied = -1;
  thread_local int8_t is_owner = -1;  // -1 not checked yet
  if (is_owner < 0) {
    uint64_t self = 0;
    pthread_threadid_np(nullptr, &self);
    uint64_t expected = 0;
    if (owner.compare_exchange_strong(expected, self)) {
      REXLOG_INFO("[adaptive-qos] main loop thread {:x} follows the mode", self);
    }
    is_owner = expected == 0 || expected == self;
  }
  if (!is_owner) return;
  Apply(mode.load(std::memory_order_relaxed), applied);
}

}  // namespace nfsmw::adaptive_qos

// The game's deferred-call runner, from its main loop (see
// tools/ios/patch_game_deferred_queue.py): the main thread's QoS, then the original.
extern "C" void __imp__sub_823C8290(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_823C8290) {
  nfsmw::adaptive_qos::OnMainLoop();
  __imp__sub_823C8290(ctx, base);
}
