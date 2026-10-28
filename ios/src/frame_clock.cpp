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

#include <mach/mach_time.h>
#include <pthread.h>

#include <algorithm>
#include <atomic>
#include <cstdint>

#include <rex/chrono/clock.h>
#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"

REXCVAR_DEFINE_INT32(nfsmw_frame_clock_ms, 0, "Game",
                     "Experimental: the game's main-thread clock reads up to this many ms after a "
                     "vblank read the vblank's time, so each frame advances exactly one vblank "
                     "(0: off)");

namespace nfsmw::frame_clock {
namespace {

thread_local bool on_main = false;
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

uint64_t Filter(uint64_t ticks) {
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
    rex::chrono::Clock::set_guest_tick_filter(&Filter);
    if (REXCVAR_GET(nfsmw_frame_clock_ms) > 0) {
      REXLOG_INFO("[frame-clock] on: main thread {:x}, reads up to {} ms after a vblank read its time", self,
                  REXCVAR_GET(nfsmw_frame_clock_ms));
    }
  }
}

}  // namespace nfsmw::frame_clock
