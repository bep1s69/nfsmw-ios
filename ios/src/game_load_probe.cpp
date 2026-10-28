// NFSMW Recompiled (iOS) - TEMPORARY probe: why a career save is "damaged"
// (GitHub issue 8, BACKLOG D-010). Logs the save loader's inputs and its two
// failure points. Remove once the cause is known.
//
// sub_822C3A60(profile r3, buffer r4, size r5, r6, mode r7) returns 0 when
//   - the word after the gameplay section (mode 0: where sub_822C2998 stopped;
//     else buffer+16+23033) differs from word +8 of the object at 0x82A2C684,
//   - or sub_822C3718 returns 0.

#include <cstdint>

#include "nfsmw_pch.h"

#include <rex/logging.h>

extern "C" void __imp__sub_822C3A60(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822C2998(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822C3718(PPCContext& __restrict ctx, uint8_t* base);

namespace {
uint32_t g_end = 0;  // where sub_822C2998 stopped, last call
}

extern "C" REX_FUNC(sub_822C2998) {
  const uint32_t from = ctx.r4.u32;
  __imp__sub_822C2998(ctx, base);
  g_end = ctx.r3.u32;
  REXLOG_INFO("[load-probe] gameplay read from {:08X} to {:08X} ({} bytes)", from, g_end,
              g_end - from);
}

extern "C" REX_FUNC(sub_822C3718) {
  const uint32_t lr = uint32_t(ctx.lr);
  __imp__sub_822C3718(ctx, base);
  REXLOG_INFO("[load-probe] sub_822C3718 (from {:08X}) -> {}", lr, ctx.r3.u32 & 0xFF);
}

extern "C" REX_FUNC(sub_822C3A60) {
  const uint32_t lr = uint32_t(ctx.lr);
  const uint32_t buffer = ctx.r4.u32, size = ctx.r5.u32, r6 = ctx.r6.u32, mode = ctx.r7.u32;
  g_end = 0;
  REXLOG_INFO("[load-probe] load (from {:08X}) buffer {:08X} size {} r6 {:08X} mode {} | first {:08X} {:08X}",
              lr, buffer, size, r6, mode, REX_LOAD_U32(buffer), REX_LOAD_U32(buffer + 4));
  __imp__sub_822C3A60(ctx, base);
  const uint32_t where = mode == 0 ? g_end : buffer + 16 + 23033;
  const uint32_t object = REX_LOAD_U32(0x82A2C684u);
  const uint32_t saved = where ? (uint32_t(REX_LOAD_U8(where)) << 24 | uint32_t(REX_LOAD_U8(where + 1)) << 16 |
                                  uint32_t(REX_LOAD_U8(where + 2)) << 8 | REX_LOAD_U8(where + 3))
                               : 0;
  const uint32_t expected = object ? REX_LOAD_U32(object + 8) : 0;
  REXLOG_INFO("[load-probe] load -> {} | word at {:08X} (buffer+{}) = {:08X}, game expects {:08X} ({})",
              ctx.r3.u32, where, where - buffer, saved, expected, saved == expected ? "same" : "DIFFERENT");
}
