#pragma once
#include <algorithm>
#include <cmath>

namespace nfsmw {
inline double WorldFramePeriod(double guest_period, int cap, bool driving) {
  // At 30 fps the guest vblank still runs at 60 Hz. World frames consume
  // two vblanks; using one allowed alternating half/full-and-half motion.
  return cap == 30 && driving ? guest_period * 2 : guest_period;
}
struct WorldClockStep { double given; bool resync; };
inline WorldClockStep AdvanceWorldClock(double& debt, double elapsed, double period) {
  // Preserve four original 60 Hz periods of catch-up time at every cap.
  // Count whole quanta to avoid floating-point boundary overshoot.
  const int max_steps = std::max(1, int(std::floor((1000.0 / 15) / period + .001)));
  debt += elapsed - period;
  int steps = 1;
  while (debt > period * .75 && steps < max_steps) {
    ++steps;
    debt -= period;
  }
  const bool resync = debt < -2 * period || debt > max_steps * period;
  if (resync) debt = 0;
  return {steps * period, resync};
}
}  // namespace nfsmw
