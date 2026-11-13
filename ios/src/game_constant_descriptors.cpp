#include "nfsmw_pch.h"
#include "game_constant_descriptors.h"
#include <rex/logging.h>
#include <chrono>
#include <mutex>

namespace nfsmw::constants::descriptors {
void Report(const Counts& counts) {
  // Only ~1/1024 complete guest invocations enter here. No shared counters,
  // TLS lookups, clocks or logging on the unsampled descriptor path.
  static std::mutex mutex;
  static Counts total;
  static uint64_t calls=0;
  static auto since=std::chrono::steady_clock::now();
  std::lock_guard lock(mutex);
  ++calls;
  for(unsigned s=0;s<2;++s) {
    auto& a=total.stage[s];const auto& b=counts.stage[s];
    a.attempts+=b.attempts;a.complete+=b.complete;a.partial+=b.partial;
    a.refused+=b.refused;a.native+=b.native;a.fallback+=b.fallback;
    a.single+=b.single;a.multiple+=b.multiple;a.invalid+=b.invalid;
  }
  const auto now=std::chrono::steady_clock::now();
  if(now-since<std::chrono::seconds(5))return;
  for(unsigned s=0;s<2;++s) {
    const auto& c=total.stage[s];
    REXLOG_INFO("[descriptor-runs] sampled {}: {} calls (~1/1024 invocations), {} runs, {} complete / {} partial / {} refused; {} native / {} fallback descriptors; {} single / {} multiple / {} invalid spans (sampled coverage, not total work)",
        s?"PS":"VS",calls,c.attempts,c.complete,c.partial,c.refused,c.native,c.fallback,c.single,c.multiple,c.invalid);
  }
  total={};calls=0;since=now;
}
}  // namespace nfsmw::constants::descriptors
