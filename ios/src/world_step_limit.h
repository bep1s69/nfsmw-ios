// Keep the original catch-up duration with 120 Hz substeps.
#pragma once
#include <cmath>
#include <cstdint>

namespace nfsmw {
inline double WorldStepLimit(double limit, double step, uint32_t flag) {
  // A zero flag selects a separate 20 ms budget unit, which must stay intact.
  if (flag == 0 || step != double(1.0f / 120.0f) ||
      !std::isfinite(limit) || limit <= 0)
    return limit;
  // Original budget: multiplier * 1/60 s. The shared constant now contains
  // 1/120 s. Doubling this local cap restores duration without changing the
  // multiplier, simulation frequency, accumulator, or supplied frame time.
  return double(float(limit * 2.0));
}
}  // namespace nfsmw
