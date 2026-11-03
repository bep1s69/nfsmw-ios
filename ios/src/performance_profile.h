#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace nfsmw::performance {
// Pure policy shared by startup argument expansion and live selection.
struct Policy {
  bool main_utility, guest_utility, adaptive, original, render_utility;
};
inline Policy Resolve(int mode, int efficiency_cores, int cap) {
  const bool eco = mode == 0, max = mode == 2;
  // Balanced with 6+ efficiency cores (M-series iPads) kept the main and GPU
  // command threads at Utility below the 120 cap until dev51: the System
  // Trace (Nov 3) had both 100% on the efficiency cores, the same frame work
  // taking ~1.9x the core time, and frames missing refreshes. Now Balanced is
  // the same on every device (boosted while driving).
  (void)efficiency_cores;
  const bool tablet = false;
  return {eco || (tablet && cap <= 60), !max,
          !eco && !max && (!tablet || cap > 60), tablet, !max};
}
inline unsigned Encode(const Policy& p) {
  return unsigned(p.main_utility) | (unsigned(p.guest_utility)<<1) |
         (unsigned(p.adaptive)<<2) | (unsigned(p.original)<<3) | (unsigned(p.render_utility)<<4);
}
inline unsigned WithOverrides(unsigned defaults, unsigned mask, unsigned values) {
  return (defaults & ~mask) | (values & mask);
}
// Called before defaults are inserted and after the cvar parser, respectively.
void CaptureOverrides(const std::vector<std::string>& args, int efficiency_cores);
void Initialize();
void Choose(const std::string& name);
// Work items, not replacement queues; serial order is preserved.
unsigned RenderQos();
unsigned PipelineQos();
}  // namespace nfsmw::performance
