// LAN room presentation only; original networking/Android adaptation credits
// remain in game_lan.cpp and servidor_ea.cpp. USA edition.
#include "nfsmw_pch.h"
#include "../boot_trace.h"
#include <atomic>
#include <rex/cvar.h>
REXCVAR_DECLARE(bool, red_lan);
extern "C" void __imp__sub_82545A88(PPCContext &__restrict ctx, uint8_t *base);
extern "C" void __imp__sub_82544A78(PPCContext &__restrict ctx, uint8_t *base);
namespace {
void RefreshCount(uint8_t* base, uint32_t room) {
  if (!REXCVAR_GET(red_lan) || !room) return;
  // The original member-change callback receives the room model in r5.
  // Its slot0 list is +360; native ListCount8281BB60 reads list+24.
  // Room record starts at+372: I+0, S/capacity+32, C/player count+36.
  const uint32_t list = REX_LOAD_U32(room + 360);
  const uint32_t capacity = REX_LOAD_U32(room + 404);
  if (!list || !REX_LOAD_U32(room + 372) || capacity < 1 || capacity > 4) return;
  const uint32_t actual = REX_LOAD_U32(list + 24);
  const uint32_t previous = REX_LOAD_U32(room + 408);
  if (actual > capacity || actual == previous) return;
  // A host's create response has C=1 even after +usm inserts guests. The
  // native room callback passes that record to the frontend unchanged. Sync
  // it to real parsed members, never connection/ready flags.
  REX_STORE_U32(room + 408, actual);
  static std::atomic<unsigned> traces{0};
  if (traces.fetch_add(1) < 12)
    nfsmw::boot::Trace("[lan-roster] room player count " + std::to_string(previous) +
                       " -> " + std::to_string(actual) + " from native member list");
}
}
extern "C" REX_FUNC(sub_82545A88) {
  RefreshCount(base, ctx.r5.u32);
  __imp__sub_82545A88(ctx, base);
}
extern "C" REX_FUNC(sub_82544A78) {
  // Also cover stale room metadata arriving after the member callback.
  RefreshCount(base, ctx.r3.u32);
  __imp__sub_82544A78(ctx, base);
}
