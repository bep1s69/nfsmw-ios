// NFSMW Recompiled (iOS) - EA SND's mixer CPU budget does not drop sounds
//
// USA edition addresses. Ported from SpeedBreaker v0.1.8
// (github.com/SpeedBreakerProject/speedbreaker, runtime/apu/ea_cpu_budget.cpp,
// GPL-3.0), which runs the same USA disc.
//
// THE BUG
//
// The engine sound fades or goes quiet mid-race and only comes back at the next
// gear change. EA SND times its own mixer thread with mftb: once per 256-sample
// block, sub_82601528 averages the busy time of the last 3 blocks and compares
// it with 90 % of a block. When it is over, it calls sub_82601788 (f1 = how far
// over, r3 = mixer+68), which expels the lowest-priority voices (sub_826016B8
// picks one, sub_825D04B8 stops it) until the excess is covered. Those voices
// are gone for good: the engine, turbo and skid loops only start again when the
// game restarts them, on a gear change. On the Xbox 360 the budget measured real
// mixing cost; here one late wake of the mixer thread by the OS (~14 ms on a
// single block) trips it while the mix itself costs ~2 % of a block.
//
// THE FIX
//
// sub_82601788 does nothing, and logs at most once a minute that EA would have
// dropped voices. Cvar nfsmw_ea_cpu_budget (off) calls the original, for an A/B.
// Checked in our generated code: sub_82601528 calls sub_82601788, which calls
// sub_826016B8 and sub_825D04B8, as in SpeedBreaker.

#include <chrono>
#include <cstdint>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_ea_cpu_budget, false, "Juego",
                    "Let EA SND drop voices when its mixer thread runs late (the original "
                    "behaviour: the engine sound can go quiet until the next gear change)");

extern "C" void __imp__sub_82601788(PPCContext& __restrict ctx, uint8_t* base);

extern "C" REX_FUNC(sub_82601788) {
  if (REXCVAR_GET(nfsmw_ea_cpu_budget)) {
    __imp__sub_82601788(ctx, base);
    return;
  }
  // Called on the mixer thread only.
  static uint64_t skipped = 0;
  static auto last_log = std::chrono::steady_clock::time_point{};
  ++skipped;
  const auto now = std::chrono::steady_clock::now();
  if (last_log == std::chrono::steady_clock::time_point{} || now - last_log >= std::chrono::minutes(1)) {
    REXLOG_INFO("[ea-budget] EA SND would have dropped voices ({} times so far, {:.3f} over)",
                skipped, ctx.f1.f64);
    last_log = now;
  }
}
