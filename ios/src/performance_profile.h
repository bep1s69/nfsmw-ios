#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace nfsmw::performance {
// Pure policy shared by startup argument expansion and live selection.
struct Policy {
  bool main_utility, guest_utility, adaptive, original, render_utility, background;
};
inline Policy Resolve(int mode, int efficiency_cores, int cap) {
  const bool eco = mode == 0, max = mode == 2;
  // Balanced with 6+ efficiency cores (M-series iPads): main and GPU command
  // threads at Utility below the 120 cap (efficiency cores, no boost). dev51
  // (Nov 3) had dropped this because frames missed refreshes on the
  // efficiency cores; with the frame hand-off no longer polling (dev55) the
  // iPad runs it smoothly (Nov 4 dev61 run Q: 24.0 vs ~28 %/h boosted, Stefan:
  // no stutters), so it is back (dev62). Phones keep the driving boost.
  const bool tablet = !eco && !max && efficiency_cores >= 6;
  // Tablet Balanced at the 30/40 caps: the Utility threads at Background QoS
  // (lower efficiency-core clocks; Nov 4 dev64: 12.6 %/h at a smooth 40, vs
  // 15.6 %/h with drops at 60), dev65.
  return {eco || (tablet && cap <= 60), !max,
          !eco && !max && (!tablet || cap > 60), tablet, !max, tablet && cap > 0 && cap <= 40};
}
inline unsigned Encode(const Policy& p) {
  return unsigned(p.main_utility) | (unsigned(p.guest_utility)<<1) |
         (unsigned(p.adaptive)<<2) | (unsigned(p.original)<<3) | (unsigned(p.render_utility)<<4) |
         (unsigned(p.background)<<5);
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
