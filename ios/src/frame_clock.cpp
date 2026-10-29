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
// IPA124: camera judder 113-197 per ~900 frames -> 3 in 6120 (iPad), 0 in
// 4080 (iPhone). 0: the game's own time.

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <string>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"
#include "battery.h"

REXCVAR_DEFINE_INT32(nfsmw_frame_ticks, 2, "Game",
                     "Game frame time: 2 one display period per frame (smooth motion), 0 the game's own "
                     "(uneven)");
REXCVAR_DEFINE_BOOL(nfsmw_frame_ticks_log, false, "Game",
                    "Diagnostic: buffer 60 world updates and log raw/given time, quantum, debt and host gap");

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

extern "C" double nfsmw_frame_ticks(double ticks, double milliseconds, double rate, double wait, double clamp) {
  const int mode = REXCVAR_GET(nfsmw_frame_ticks);
  if (mode != 2 || !(milliseconds > 0) || milliseconds >= 250)
    return TraceTicks(ticks, ticks, milliseconds, 0, 0, false, mode, rate, wait, clamp);
  uint64_t vblank_ns = 0, period_ns = 0;
  nfsmw::display::LatestVblank(vblank_ns, period_ns);
  const double period = period_ns ? double(period_ns) / 1e6 : 1000.0 / 60.0;
  static double debt = 0;  // real time not yet given to the game (ms); the main loop's thread only
  const uint64_t managed_period_ns = nfsmw::display::ManagedFramePeriodNs();
  if (managed_period_ns && nfsmw::battery::InMenu() == 0 &&
      rex::cvar::Query<int32_t>("ios_fps_cap") == 40) {
    // The Metal link displays one game frame per 25 ms slot. The main loop
    // can still stall then catch up (log8: 3-74 ms) behind that steady output.
    // Debt corrections in 8.34 ms units made those on-time pictures move by
    // 1/2/4 simulation ticks. Give each picture one complete 40 fps step.
    // Keep menus, other caps, loading bypasses and legacy behavior intact.
    const double frame_period = double(managed_period_ns) / 1e6;
    debt = 0;
    return TraceTicks(ticks * (frame_period / milliseconds), ticks, milliseconds,
                      frame_period, debt, false, mode, rate, wait, clamp);
  }
  debt += milliseconds - period;
  double give = period;
  while (debt > period * 0.75 && give < period * 4) {  // refreshes missed: catch up
    give += period;
    debt -= period;
  }
  const bool resync = debt < -2 * period || debt > 4 * period;
  if (resync) debt = 0;  // far off (loading): resync
  return TraceTicks(ticks * (give / milliseconds), ticks, milliseconds,
                    period, debt, resync, mode, rate, wait, clamp);
}
