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
#include <cstdint>

#include <rex/cvar.h>

#include "display_rate.h"

REXCVAR_DEFINE_INT32(nfsmw_frame_ticks, 2, "Game",
                     "Game frame time: 2 one display period per frame (smooth motion), 0 the game's own "
                     "(uneven)");

extern "C" double nfsmw_frame_ticks(double ticks, double milliseconds, double rate, double wait, double clamp) {
  (void)rate, (void)wait, (void)clamp;
  if (REXCVAR_GET(nfsmw_frame_ticks) != 2 || !(milliseconds > 0) || milliseconds >= 250) return ticks;
  uint64_t vblank_ns = 0, period_ns = 0;
  nfsmw::display::LatestVblank(vblank_ns, period_ns);
  const double period = period_ns ? double(period_ns) / 1e6 : 1000.0 / 60.0;
  static double debt = 0;  // real time not yet given to the game (ms); the main loop's thread only
  debt += milliseconds - period;
  double give = period;
  while (debt > period * 0.75 && give < period * 4) {  // refreshes missed: catch up
    give += period;
    debt -= period;
  }
  if (debt < -2 * period || debt > 4 * period) debt = 0;  // far off (loading): resync
  return ticks * (give / milliseconds);
}
