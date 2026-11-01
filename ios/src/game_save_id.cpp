// NFSMW Recompiled (iOS) - careers saved under another player ID load.
//
// The career loader sub_822C3A60(profile r3, buffer r4, size r5, r6, mode r7)
// reads the gameplay section (sub_822C2998, which returns where it stopped),
// then compares the next 4 bytes, the player ID the career was saved with,
// with word +8 of the object at 0x82A2C684, this device's ID. If they differ
// it returns 0 and the game says the career "appears to be damaged" (GitHub
// issue 8: a save from another device or install). The file itself is fine.
//
// The gameplay section read is 23033 bytes for every save seen (IPA133: NAME,
// BEPPY), so the ID is at buffer+16+23033. Before the loader runs, a
// different ID there is replaced by the device's (rerunning the loader after
// a failure did not work: IPA134), and the MD5 that sub_822C3718 checks
// (buffer+16 to size-16, stored in the last 16 bytes: the file's trailing MD5)
// is computed again. The next save writes the device's ID.

#include <cstdint>

#include <CommonCrypto/CommonDigest.h>

#include "nfsmw_pch.h"

#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

extern "C" void __imp__sub_822C3A60(PPCContext& __restrict ctx, uint8_t* base);

namespace {

constexpr uint32_t kPlayerObject = 0x82A2C684u;
constexpr uint32_t kIdOffset = 16 + 23033;  // in the load buffer

uint32_t LoadBytesBE(uint8_t* base, uint32_t p) {
  return uint32_t(REX_LOAD_U8(p)) << 24 | uint32_t(REX_LOAD_U8(p + 1)) << 16 |
         uint32_t(REX_LOAD_U8(p + 2)) << 8 | REX_LOAD_U8(p + 3);
}

}  // namespace

extern "C" REX_FUNC(sub_822C3A60) {
  const uint32_t buffer = ctx.r4.u32, size = ctx.r5.u32;
  const uint32_t object = REX_LOAD_U32(kPlayerObject);
  if (ctx.r7.u32 == 0 && object != 0 && size >= kIdOffset + 4) {
    const uint32_t at = buffer + kIdOffset;
    const uint32_t saved = LoadBytesBE(base, at), device = REX_LOAD_U32(object + 8);
    if (saved != device) {
      for (int i = 0; i < 4; ++i) {
        REX_STORE_U8(at + i, uint8_t(device >> (24 - 8 * i)));
      }
      uint8_t* data = rex::system::kernel_state()->memory()->TranslateVirtual<uint8_t*>(buffer);
      CC_MD5(data + 16, CC_LONG(size - 32), data + size - 16);
      __imp__sub_822C3A60(ctx, base);
      REXLOG_INFO("[save-id] career saved with player ID {:08X}, this device has {:08X}: "
                  "loaded with the device's ID -> {}", saved, device, ctx.r3.u32);
      return;
    }
  }
  __imp__sub_822C3A60(ctx, base);
}
