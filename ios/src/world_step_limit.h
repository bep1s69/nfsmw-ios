// Keep the original catch-up duration when managed 40 uses 120 Hz substeps.
#pragma once
#include <cmath>
#include <cstdint>

namespace nfsmw {
inline double WorldStepLimit(double limit, double step, uint32_t flag,
    bool main_loop, bool managed, int menu, int cap, int frame_ticks) {
  // Only the measured main-loop driving path is covered by this experiment.
  // A zero flag selects a separate 20 ms budget unit, which must stay intact.
  if (!managed || menu != 0 || cap != 40 || frame_ticks != 2 ||
      !main_loop || flag == 0 || step != double(1.0f / 120.0f) ||
      !std::isfinite(limit) || limit <= 0)
    return limit;
  // Original budget: multiplier * 1/60 s. The shared constant now contains
  // 1/120 s. Doubling this local cap restores duration without changing the
  // multiplier, simulation frequency, accumulator, or supplied frame time.
  return double(float(limit * 2.0));
}
}  // namespace nfsmw
