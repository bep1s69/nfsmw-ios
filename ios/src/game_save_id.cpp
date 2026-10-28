// NFSMW Recompiled (iOS) - careers saved under another player ID load.
//
// The career loader sub_822C3A60(profile r3, buffer r4, size r5, r6, mode r7)
// reads the gameplay section (sub_822C2998, which returns where it stopped),
// then compares the next 4 bytes, the player ID the career was saved with,
// with word +8 of the object at 0x82A2C684, this device's ID. If they differ
// it returns 0 and the game says the career "appears to be damaged" (GitHub
// issue 8: a save from another device or install). The file itself is fine.
//
// So when the loader fails and the ID differs, the device's ID is written into
// the buffer and the loader runs again. The next save writes the device's ID.

#include <cstdint>

#include "nfsmw_pch.h"

#include <rex/logging.h>

extern "C" void __imp__sub_822C3A60(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822C2998(PPCContext& __restrict ctx, uint8_t* base);

namespace {

constexpr uint32_t kPlayerObject = 0x82A2C684u;
uint32_t g_gameplay_end = 0;  // where sub_822C2998 stopped, last call

uint32_t LoadBytesBE(uint8_t* base, uint32_t p) {
  return uint32_t(REX_LOAD_U8(p)) << 24 | uint32_t(REX_LOAD_U8(p + 1)) << 16 |
         uint32_t(REX_LOAD_U8(p + 2)) << 8 | REX_LOAD_U8(p + 3);
}

}  // namespace

extern "C" REX_FUNC(sub_822C2998) {
  __imp__sub_822C2998(ctx, base);
  g_gameplay_end = ctx.r3.u32;
}

extern "C" REX_FUNC(sub_822C3A60) {
  const PPCContext entry = ctx;
  g_gameplay_end = 0;
  __imp__sub_822C3A60(ctx, base);
  const uint32_t buffer = entry.r4.u32, size = entry.r5.u32;
  const uint32_t at = g_gameplay_end;
  const uint32_t object = REX_LOAD_U32(kPlayerObject);
  if (ctx.r3.u32 != 0 || entry.r7.u32 != 0 || object == 0 || at < buffer || at + 4 > buffer + size) {
    return;
  }
  const uint32_t saved = LoadBytesBE(base, at), device = REX_LOAD_U32(object + 8);
  if (saved == device) {
    return;
  }
  for (int i = 0; i < 4; ++i) {
    REX_STORE_U8(at + i, uint8_t(device >> (24 - 8 * i)));
  }
  ctx = entry;
  __imp__sub_822C3A60(ctx, base);
  REXLOG_INFO("[save-id] career saved with player ID {:08X}, this device has {:08X}: "
              "loaded with the device's ID -> {}", saved, device, ctx.r3.u32);
}
