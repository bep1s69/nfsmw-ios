// NFSMW Recompiled - even frame time for the game's world (D-005, 0.4.2)
//
// The game's main loop (sub_823B0008) times each frame with the clock and
// steps the world and camera by that time. Nothing paces the loop to the
// display: it runs until the GPU queue pushes back, so its frames came at
// 13.5 / 19.5 ms alternating, with 30-45 ms stalls and quick catch-up frames
// (Oct 28, IPA122), while the screen showed one frame per refresh. The world
// stepped 2x, 0 in stretches (camera log): a judder with every frame on time,
// worst at places seen for the first time and after a device restart.
//
// tools/ios/patch_game_frame_ticks.py passes the frame's time through
// nfsmw_frame_ticks before the loop runs the frame. With nfsmw_frame_ticks 2
// (default) each frame gets one display period (16.67 ms at 60 Hz), or more
// when real time has run over 3/4 of a period ahead (frames missed on screen
// too); far off (loading) it resyncs. The loop itself is not slowed.
// At the 30 cap, driving uses two guest vblanks per world frame (33.33 ms).
// Catch-up retains roughly 66.67 ms at every guest rate, including 120 Hz.
// IPA124: camera judder 113-197 per ~900 frames -> 3 in 6120 (iPad), 0 in
// 4080 (iPhone). 0: the game's own time.

#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <string>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"
#include "world_step_limit.h"
#include "frame_clock_policy.h"
#include "battery.h"

REXCVAR_DEFINE_INT32(nfsmw_frame_ticks, 2, "Game",
                     "Game frame time: 2 one display period per frame (smooth motion), 0 the game's own "
                     "(uneven)");
REXCVAR_DEFINE_BOOL(nfsmw_frame_ticks_log, false, "Game",
                    "Diagnostic: buffer 60 world updates and log raw/given time, quantum, debt, "
                    "engine accumulator/clamp/output and host gap");

namespace {
// Main-loop thread only. Record numbers per update; format only once per
// batch. The result is returned verbatim, including the original bypasses.
double TraceTicks(double result, double ticks, double milliseconds, double period,
                  double debt, bool resync, int mode, double rate, double wait, double clamp) {
  if (!REXCVAR_GET(nfsmw_frame_ticks_log)) return result;
  using Clock = std::chrono::steady_clock;
  static Clock::time_point last;
  const auto now = Clock::now();
  const double wall = last.time_since_epoch().count() ?
      std::chrono::duration<double, std::milli>(now - last).count() : 0;
  last = now;
  static std::array<std::array<double, 6>, 60> samples;
  static size_t count = 0;
  static uint64_t total = 0;
  static int lines = 160;  // at most four minutes of updates at 40 fps
  const double given = ticks != 0 ? milliseconds * (result / ticks) : milliseconds;
  samples[count++] = {milliseconds, given, period, debt, wall, resync ? 1.0 : 0.0};
  ++total;
  if (count == samples.size()) {
    if (lines-- > 0) {
      std::string values;
      for (const auto& sample : samples) {
        values += fmt::format(" {:.3f}/{:.3f}/{:.4f}/{:.3f}/{:.3f}/{:.0f}",
                              sample[0], sample[1], sample[2], sample[3], sample[4], sample[5]);
      }
      REXLOG_INFO("[world-clock] updates {}-{}, mode {}, rate {}, wait {}, clamp {} | "
                  "raw/given/quantum/debt/host-gap(ms)/resync:{}",
                  total - samples.size() + 1, total, mode, rate, wait, clamp, values);
    }
    count = 0;
  }
  return result;
}
}  // namespace

// Restore the original elapsed-time allowance, not the shared simulation step.
// The generated hook runs before the clamp; diagnostics see the effective limit.
extern "C" double nfsmw_world_step_limit(double limit, double step,
    uint32_t flag) {
  return nfsmw::WorldStepLimit(limit, step, flag);
}

// Diagnostic only: observe the engine's downstream accumulator, including
// time discarded after nfsmw_frame_ticks returned. Never change its result.
extern "C" void nfsmw_world_step_trace(double input, double before, double limit,
    double after, double output, int32_t ticks, uint32_t flag, uint32_t budget_bits, uint32_t caller) {
  using Clock = std::chrono::steady_clock;
  static thread_local Clock::time_point last;
  static thread_local std::array<std::array<double, 11>, 60> samples;
  static thread_local size_t count = 0;
  static thread_local uint64_t updates = 0;
  static thread_local int lines = 160;
  if (!REXCVAR_GET(nfsmw_frame_ticks_log) || nfsmw::battery::InMenu() != 0) {
    last = {};
    count = 0;
    return;
  }
  if (lines <= 0) return;
  const auto now = Clock::now();
  const double wall = last.time_since_epoch().count() ?
      std::chrono::duration<double, std::milli>(now - last).count() : 0;
  last = now;
  samples[count++] = {input * 1000, before * 1000, limit * 1000, after * 1000,
      output * 1000, double(ticks), double(flag), std::bit_cast<float>(budget_bits),
      double(nfsmw::display::ManagedAssignedFrames()), wall, double(caller)};
  ++updates;
  if (count == samples.size()) {
    std::string values;
    for (const auto& sample : samples)
      values += fmt::format(" {:.3f}/{:.3f}/{:.3f}/{:.3f}/{:.3f}/{:.0f}/{:.0f}/{:.3f}/{:.0f}/{:.3f}/{:08X}",
          sample[0], sample[1], sample[2], sample[3], sample[4],
          sample[5], sample[6], sample[7], sample[8], sample[9], uint32_t(sample[10]));
    REXLOG_INFO("[world-step] driving updates {}-{} | "
        "input/before/limit/after/output(ms)/ticks/flag/budget/render-seq/host-gap(ms)/caller:{}",
        updates - 59, updates, values);
    count = 0;
    --lines;
  }
}

extern "C" double nfsmw_frame_ticks(double ticks, double milliseconds, double rate, double wait, double clamp) {
  const int mode = REXCVAR_GET(nfsmw_frame_ticks);
  const uint64_t managed_period_ns = nfsmw::display::ManagedFramePeriodNs();
  if (mode != 2 || !(milliseconds > 0) || milliseconds >= 250) {
    if (managed_period_ns) nfsmw::display::TakeManagedMissedSlots(0);
    return TraceTicks(ticks, ticks, milliseconds, 0, 0, false, mode, rate, wait, clamp);
  }
  uint64_t vblank_ns = 0, period_ns = 0;
  nfsmw::display::LatestVblank(vblank_ns, period_ns);
  const double period = period_ns ? double(period_ns) / 1e6 : 1000.0 / 60.0;
  static double debt = 0;  // real time not yet given to the game (ms); the main loop's thread only
  if (managed_period_ns && nfsmw::battery::InMenu() == 0 &&
      rex::cvar::Query<int32_t>("ios_fps_cap") == 40) {
    // The Metal link displays one game frame per 25 ms slot. The main loop
    // can still stall then catch up (log8: 3-74 ms) behind that steady output.
    // Debt corrections in 8.34 ms units made those on-time pictures move by
    // 1/2/4 simulation ticks. Give each picture one complete 40 fps step.
    // Genuine skipped output slots need additional world time (log10), or
    // sustained GPU-limited output would run the simulation in slow motion.
    // Bound catch-up to the existing 250 ms loading threshold; retain excess debt.
    const double frame_period = double(managed_period_ns) / 1e6;
    const uint32_t missed = nfsmw::display::TakeManagedMissedSlots(9);
    const double give = frame_period * (1 + missed);
    if (REXCVAR_GET(nfsmw_frame_ticks_log)) {
      static uint32_t updates = 0, compensated = 0;
      compensated += missed;
      if (++updates % 300 == 0) {
        REXLOG_INFO("[world-missed] {} skipped output slots compensated over 300 driving updates", compensated);
        compensated = 0;
      }
    }
    debt = 0;
    return TraceTicks(ticks * (give / milliseconds), ticks, milliseconds,
                      frame_period, debt, false, mode, rate, wait, clamp);
  }
  const double world_period = nfsmw::WorldFramePeriod(period,
      rex::cvar::Query<int32_t>("ios_fps_cap"), nfsmw::battery::InMenu() == 0);
  const auto step = nfsmw::AdvanceWorldClock(debt, milliseconds, world_period);
  return TraceTicks(ticks * (step.given / milliseconds), ticks, milliseconds,
                    world_period, debt, step.resync, mode, rate, wait, clamp);
}
