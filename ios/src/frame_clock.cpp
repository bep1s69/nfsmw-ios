// NFSMW Recompiled - the frame-step clock (experimental, D-005)
//
// At 60 fps the game world judders while every frame is shown 16.7 ms apart
// (iPhone, Oct 28; iPad, Oct 26-27): the motion inside the frames is uneven.
// The game reads the clock on its main thread (mftb, KeQueryPerformanceCounter)
// and those reads jitter by about a millisecond around the vblank they follow,
// so each frame's step is a little longer or shorter than 1/60 s.
//
// With nfsmw_frame_clock_ms > 0, the main thread's reads that come less than
// that many ms after a guest vblank read the vblank's own time: each frame
// then advances by exactly one vblank (16.67 ms at the 60 cap). Later reads
// run on the real clock (waits that poll the clock keep working); a thread's
// reads never go backwards. Other threads (audio, workers) are untouched.
// The grid is the display refresh the guest vblank is locked to
// (display_rate.mm). The SDK hook: tools/ios/patch_ios_frame_clock.py.
//
// Every 300 vblanks the main thread's reads are logged by how long after
// the vblank they came: `[frame-clock]`.
//
// That snap could not work (IPA113): the main loop reads the clock about 3
// times a frame at every point of it, and its phase drifts against the
// vblank. Version 2, nfsmw_frame_clock_swap: on the main loop thread and the
// thread that swaps, the clock advances by whole refresh periods at each
// swap (as many as really passed, normally one) and runs on the real clock
// in between, held just short of the next period. A read at the same point
// of every frame then steps by exactly one period. Waits that poll the clock
// still finish: past two periods without a swap (loading) it runs again,
// one period behind until the next swap catches up.

#include <mach/mach_time.h>
#include <pthread.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>

#include <rex/chrono/clock.h>
#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"

REXCVAR_DEFINE_INT32(nfsmw_frame_clock_ms, 0, "Game",
                     "Experimental: the game's main-thread clock reads up to this many ms after a "
                     "vblank read the vblank's time, so each frame advances exactly one vblank "
                     "(0: off)");

REXCVAR_DEFINE_BOOL(nfsmw_frame_clock_hold, false, "Game",
                    "Experimental, with nfsmw_frame_clock_swap: the clock stands still within a frame "
                    "(each frame reads its swap's time; runs again after two periods without a swap)");
REXCVAR_DEFINE_BOOL(nfsmw_frame_clock_swap, false, "Game",
                    "Experimental: on the game's main loop and swap threads the clock advances one "
                    "refresh period per swap (even steps at 60 fps)");

namespace nfsmw::frame_clock {
namespace {

thread_local bool on_main = false;
thread_local bool on_swap = false;
thread_local bool raw = false;  // OnSwap reading the real clock
thread_local uint64_t last_returned = 0;

uint64_t MachNs() {
  static const mach_timebase_info_data_t tb = [] {
    mach_timebase_info_data_t t{};
    mach_timebase_info(&t);
    return t;
  }();
  return mach_absolute_time() * tb.numer / tb.denom;
}

// Reads by time after the vblank: <1, 1-2, 2-4, 4-8, 8-12, 12+ ms.
uint32_t bins[6] = {};
uint32_t snapped = 0;
uint64_t window_vblank = 0;
uint32_t window_count = 0;
int lines = 60;

// Version 2's state, written at each swap: the virtual and real clocks then
// (guest ticks) and the period. The swap thread writes, two threads read.
std::atomic<uint64_t> swap_virtual{0}, swap_real{0}, swap_period{0};
uint32_t steps_hist[4] = {};  // periods per swap: 1, 2, 3, more
uint32_t swaps = 0;

uint64_t PeriodTicks() {
  uint64_t vblank_ns = 0, period_ns = 0;
  nfsmw::display::LatestVblank(vblank_ns, period_ns);
  if (!period_ns) period_ns = 16666667;
  return uint64_t(double(period_ns) * double(rex::chrono::Clock::guest_tick_frequency()) *
                  rex::chrono::Clock::guest_time_scalar() / 1e9);
}

uint64_t SwapClock(uint64_t ticks) {
  const uint64_t base_real = swap_real.load(std::memory_order_acquire);
  const uint64_t base_virtual = swap_virtual.load(std::memory_order_relaxed);
  const uint64_t period = swap_period.load(std::memory_order_relaxed);
  if (!base_real || !period || ticks < base_real) return std::max(ticks, last_returned);
  const uint64_t since = ticks - base_real;
  uint64_t result;
  if (since < period) {
    // v3 (nfsmw_frame_clock_hold): the camera log (IPA117) showed the game's
    // camera turning 2x, 0, 2x, 0 in stretches: a fixed 1/60 step counted
    // from the clock, with reads inside the frame on either side of a step.
    result = REXCVAR_GET(nfsmw_frame_clock_hold) ? base_virtual : base_virtual + since;
  } else if (since < 2 * period) {
    result = base_virtual + period - 1;  // held until the swap
  } else {
    result = base_virtual + since - period;  // no swap for a while: the clock runs again
  }
  result = std::max(result, last_returned);
  last_returned = result;
  return result;
}

uint64_t Filter(uint64_t ticks) {
  if (raw) return ticks;
  if ((on_main || on_swap) && REXCVAR_GET(nfsmw_frame_clock_swap)) return SwapClock(ticks);
  if (!on_main) return ticks;
  const int32_t ms = REXCVAR_GET(nfsmw_frame_clock_ms);
  if (ms <= 0) return ticks;
  uint64_t vblank_ns = 0, period_ns = 0;
  nfsmw::display::LatestVblank(vblank_ns, period_ns);
  const uint64_t now = MachNs();
  if (!vblank_ns || !period_ns || now < vblank_ns || now - vblank_ns > 250000000ull) return ticks;
  const uint64_t latest = vblank_ns + ((now - vblank_ns) / period_ns) * period_ns;
  const uint64_t after = now - latest;
  const double after_ms = double(after) / 1e6;
  ++bins[after_ms < 1 ? 0 : after_ms < 2 ? 1 : after_ms < 4 ? 2 : after_ms < 8 ? 3 : after_ms < 12 ? 4 : 5];
  if (latest != window_vblank) {
    window_vblank = latest;
    if (++window_count >= 300) {
      if (lines > 0) {
        --lines;
        REXLOG_INFO("[frame-clock] {} ms: main-thread reads over 300 vblanks by time after the vblank: "
                    "<1 ms {}, 1-2 {}, 2-4 {}, 4-8 {}, 8-12 {}, 12+ {}; {} read the vblank's time",
                    ms, bins[0], bins[1], bins[2], bins[3], bins[4], bins[5], snapped);
      }
      std::fill(std::begin(bins), std::end(bins), 0);
      snapped = 0;
      window_count = 0;
    }
  }
  uint64_t result = ticks;
  if (after < uint64_t(ms) * 1000000ull) {
    const double ticks_per_ns = double(rex::chrono::Clock::guest_tick_frequency()) *
                                rex::chrono::Clock::guest_time_scalar() / 1e9;
    const uint64_t back = uint64_t(double(after) * ticks_per_ns);
    result = ticks > back ? ticks - back : ticks;
    ++snapped;
  }
  result = std::max(result, last_returned);
  last_returned = result;
  return result;
}

}  // namespace

// At each frame's swap (native_renderer.mm, on the thread that swaps).
void OnSwap() {
  if (!REXCVAR_GET(nfsmw_frame_clock_swap)) return;
  if (!on_swap) {
    on_swap = true;
    rex::chrono::Clock::set_guest_tick_filter(&Filter);
    REXLOG_INFO("[frame-clock] v2 on: one refresh period per swap (main loop and swap threads)");
  }
  raw = true;
  const uint64_t now = rex::chrono::Clock::QueryGuestTickCount();
  raw = false;
  const uint64_t period = PeriodTicks();
  const uint64_t base_real = swap_real.load(std::memory_order_relaxed);
  uint64_t next_virtual;
  if (!base_real || now < base_real || !period) {
    next_virtual = now;
  } else {
    const uint64_t steps = std::max<uint64_t>(1, (now - base_real + period / 2) / period);
    ++steps_hist[std::min<uint64_t>(steps, 4) - 1];
    const uint64_t old_virtual = swap_virtual.load(std::memory_order_relaxed);
    // Never behind what was handed out (a frame over two periods ran the clock).
    const uint64_t since = now - base_real;
    const uint64_t handed = since < 2 * period ? old_virtual + std::min(since, period - 1)
                                               : old_virtual + since - period;
    next_virtual = std::max(old_virtual + steps * period, handed + 1);
    if (++swaps >= 300) {
      static int said = 60;
      if (said-- > 0) {
        REXLOG_INFO("[frame-clock] v2: last 300 swaps advanced 1 period {}, 2 {}, 3 {}, more {}; "
                    "virtual clock {:.1f} ms behind the real one",
                    steps_hist[0], steps_hist[1], steps_hist[2], steps_hist[3],
                    double(int64_t(now) - int64_t(next_virtual)) * 1000.0 /
                        (double(rex::chrono::Clock::guest_tick_frequency()) *
                         rex::chrono::Clock::guest_time_scalar()));
      }
      std::fill(std::begin(steps_hist), std::end(steps_hist), 0);
      swaps = 0;
    }
  }
  swap_virtual.store(next_virtual, std::memory_order_relaxed);
  swap_period.store(period, std::memory_order_relaxed);
  swap_real.store(now, std::memory_order_release);
}

// The game's main thread, once per loop (adaptive_qos.cpp's deferred-call
// hook): the first thread to call it is the main thread.
void OnMainLoop() {
  thread_local int8_t checked = 0;
  if (checked) return;
  checked = 1;
  static std::atomic<uint64_t> owner{0};
  uint64_t self = 0;
  pthread_threadid_np(nullptr, &self);
  uint64_t expected = 0;
  if (owner.compare_exchange_strong(expected, self) || expected == self) {
    on_main = true;
    if (REXCVAR_GET(nfsmw_frame_clock_ms) > 0 || REXCVAR_GET(nfsmw_frame_clock_swap)) {
      rex::chrono::Clock::set_guest_tick_filter(&Filter);
    }
    if (REXCVAR_GET(nfsmw_frame_clock_ms) > 0) {
      REXLOG_INFO("[frame-clock] on: main thread {:x}, reads up to {} ms after a vblank read its time", self,
                  REXCVAR_GET(nfsmw_frame_clock_ms));
    }
  }
}

}  // namespace nfsmw::frame_clock

// The main loop's tick count (tools/ios/patch_game_frame_ticks.py): sub_823B0008
// runs each frame with (int)(elapsed * rate), truncated, throwing the rest
// away. Logged every 300 frames: elapsed * rate by band, and the constants.
// nfsmw_frame_ticks 1: the remainder is carried to the next frame, so the
// ticks add up to the time that passed (an even 1 a frame at a steady 60).
REXCVAR_DEFINE_INT32(nfsmw_frame_ticks, 1, "Game",
                     "Main loop tick count: 0 the game's (truncated, remainder lost), 1 the remainder "
                     "carried to the next frame");
extern "C" double nfsmw_frame_ticks(double ticks, double seconds, double rate, double wait, double clamp) {
  static double carry = 0;
  static uint32_t bands[8] = {}, frames = 0, results[4] = {};
  static int lines = 120;
  static bool said = false;
  if (!said) {
    said = true;
    REXLOG_INFO("[frame-ticks] main loop: rate {:.4f} ticks/s, waits for over {:.6f} s, clamps at {:.6f} s; mode {}",
                rate, wait, clamp, REXCVAR_GET(nfsmw_frame_ticks));
  }
  const double t = ticks;
  ++bands[t < 0.5 ? 0 : t < 0.9 ? 1 : t < 1.0 ? 2 : t < 1.1 ? 3 : t < 1.5 ? 4 : t < 1.9 ? 5 : t < 2.1 ? 6 : 7];
  double out = ticks;
  if (REXCVAR_GET(nfsmw_frame_ticks) == 1) {
    const double sum = ticks + carry;
    const double whole = std::floor(sum + 1e-6);
    carry = std::clamp(sum - whole, 0.0, 0.999);
    out = whole;
  } else {
    carry = 0;
  }
  ++results[std::min(3, std::max(0, int(out)))];
  if (++frames >= 300) {
    if (lines-- > 0) {
      REXLOG_INFO("[frame-ticks] 300 frames: elapsed x rate <0.5 {}, 0.5-0.9 {}, 0.9-1.0 {}, 1.0-1.1 {}, 1.1-1.5 {}, "
                  "1.5-1.9 {}, 1.9-2.1 {}, 2.1+ {} | ticks run 0: {}, 1: {}, 2: {}, 3+: {} (mode {})",
                  bands[0], bands[1], bands[2], bands[3], bands[4], bands[5], bands[6], bands[7], results[0],
                  results[1], results[2], results[3], REXCVAR_GET(nfsmw_frame_ticks));
    }
    std::fill(std::begin(bands), std::end(bands), 0);
    std::fill(std::begin(results), std::end(results), 0);
    frames = 0;
  }
  (void)seconds;
  return out;
}

// The render hand-off (tools/ios/patch_game_render_handoff.py): in gameplay
// the game hands each frame to its render thread, which draws it while the
// main loop already updates the next one. With this on, gameplay frames take
// the game's own single-threaded path (drawn on the main loop thread), so the
// drawing cannot see the next frame's camera. Read once (restart required).
REXCVAR_DEFINE_BOOL(nfsmw_render_single_thread, false, "Game",
                    "Experimental: gameplay frames drawn on the game's main loop thread instead of "
                    "handed to its render thread (restart required)");
extern "C" bool nfsmw_render_single_thread() {
  static const bool on = [] {
    const bool v = REXCVAR_GET(nfsmw_render_single_thread);
    REXLOG_INFO("[render-handoff] gameplay frames {}", v ? "drawn on the main loop thread (single-threaded)"
                                                          : "handed to the render thread (the game's)");
    return v;
  }();
  return on;
}

