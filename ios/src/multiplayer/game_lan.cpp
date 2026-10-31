// Adapted directly from victorgbd's nativo/app/src/nfsmw_red_sonda.cpp,
// d534be88edf5bcd362445c84e5b79c61e29571e7 (GPL-3.0).
// Original Android LAN implementation and adaptation credited in CHANGELOG.md.
// USA Socket address-map function is sub_828298E0, PAL sub_82829AD0.
#include "nfsmw_pch.h"
#include <rex/cvar.h>
REXCVAR_DECLARE(bool, red_lan);
extern "C" void __imp__sub_828298E0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_828298E0) {
  // Keep service loopback -> EA replacement mapping, but let the original
  // CommUDP race sockets talk straight to the other phone's LAN address.
  if (REXCVAR_GET(red_lan) && ctx.r4.u32 && REX_LOAD_U8(ctx.r4.u32 + 4) != 127) {
    ctx.r3.u64 = ctx.r4.u64;
    return;
  }
  __imp__sub_828298E0(ctx, base);
}
