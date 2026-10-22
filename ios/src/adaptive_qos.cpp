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

#include <pthread.h>
#include <pthread/qos.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>

#include <rex/cvar.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(ios_adaptive_qos, false, "Kernel",
                    "Experiment: main and GPU command threads at Utility QoS while frames are on time "
                    "(restart required)");

namespace {

std::atomic<int> mode{-1};  // 0 Utility, 1 User Initiated
using Clock = std::chrono::steady_clock;

void Apply(int m, int& applied) {
  if (m < 0 || m == applied) return;
  pthread_set_qos_class_self_np(m == 0 ? QOS_CLASS_UTILITY : QOS_CLASS_USER_INITIATED, 0);
  applied = m;
}

}  // namespace

namespace nfsmw::adaptive_qos {

bool Enabled() {
  static const bool on = REXCVAR_GET(ios_adaptive_qos) && !rex::cvar::Query<bool>("ios_utility_qos");
  return on;
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
    REXLOG_INFO("[adaptive-qos] on: main and GPU command threads start at Utility");
  }
  const int32_t cap = std::max<int32_t>(rex::cvar::Query<int32_t>("ios_fps_cap"), 1);
  const double budget = 1000.0 / cap;
  const bool is_late = interval_ms > budget * 1.2 && interval_ms < 250.0;  // not loading stalls
  late_count += int(is_late) - int(late[at]);
  late[at] = is_late;
  at = (at + 1) % 120;
  if (m == 0 && late_count >= 2) {
    const double eco_s = std::chrono::duration<double>(now - eco_since).count();
    hold_s = eco_s < 10.0 ? std::min(hold_s * 2.0, 240.0) : eco_s > 60.0 ? 20.0 : hold_s;
    hold_until = now + std::chrono::milliseconds(int64_t(hold_s * 1000));
    m = 1;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] User Initiated for {:.0f} s ({} late frames of 120, {:.0f} s on Utility)", hold_s, late_count, eco_s);
  } else if (m == 1 && now >= hold_until) {
    m = 0;
    eco_since = now;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] back to Utility");
  }
  if (m != mode.load(std::memory_order_relaxed)) {
    std::fill(std::begin(late), std::end(late), false);
    late_count = 0;
    mode.store(m, std::memory_order_relaxed);
  }
  Apply(m, applied);
}

// On the game's main thread (the first thread to call it), once per loop.
void OnMainLoop() {
  if (!Enabled()) return;
  static std::atomic<uint64_t> owner{0};
  thread_local int applied = -1;
  uint64_t self = 0;
  pthread_threadid_np(nullptr, &self);
  uint64_t expected = 0;
  if (owner.compare_exchange_strong(expected, self)) {
    REXLOG_INFO("[adaptive-qos] main loop thread {:x} follows the mode", self);
  } else if (expected != self) {
    return;
  }
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
