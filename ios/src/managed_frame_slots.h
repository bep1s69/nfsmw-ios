// Bookkeeping for world time lost when managed 40 fps output slots are skipped.
// Caller supplies synchronization. No wall-clock/renderer dependencies here.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace nfsmw {
class ManagedFrameSlots {
 public:
  void Reset() { last_target_ = 0; driving_ = false; pending_ = 0; remainder_ = 0; }

  void Assign(double target, double period, bool driving) {
    if (!std::isfinite(target) || !std::isfinite(period) || target <= 0 ||
        period < .020 || period > .030) {
      Reset();
      return;
    }
    if (!driving) {
      pending_ = 0;
      remainder_ = 0;
    } else if (driving_ && last_target_ > 0) {
      const double gap = target - last_target_;
      // A long discontinuity is loading/lifecycle, not gameplay debt.
      // Normal missed callbacks/frames advance by whole system slots.
      if (gap <= 0 || gap >= period * 10) { pending_ = 0; remainder_ = 0; }
      else {
        // Do not round individual intervals: a 1.5-slot / .5-slot phase
        // adjustment is two frames, not a missed frame. Carry the fraction.
        remainder_ += gap / period - 1;
        if (remainder_ >= 1 - 1e-6) {
          const auto missed = uint32_t(std::floor(remainder_ + 1e-6));
          pending_ = std::min(12u, pending_ + missed);
          remainder_ -= missed;
        }
      }
    }
    last_target_ = target;
    driving_ = driving;
  }

  uint32_t Take(uint32_t maximum) {
    const uint32_t taken = std::min(pending_, maximum);
    pending_ -= taken;
    return taken;
  }
  uint32_t Pending() const { return pending_; }

 private:
  double last_target_ = 0;
  bool driving_ = false;
  uint32_t pending_ = 0;
  double remainder_ = 0;
};
}  // namespace nfsmw
