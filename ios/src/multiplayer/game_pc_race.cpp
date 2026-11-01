// USA PC cross-play race-loader diagnostics. No gameplay/result changes.
#include "../boot_trace.h"
#include "nfsmw_pch.h"
#include "pc_gateway.h"
#include <atomic>
#include <cstdio>
extern "C" void __imp__sub_8212BFB8(PPCContext &__restrict ctx, uint8_t *base);
extern "C" REX_FUNC(sub_8212BFB8) {
  // Only the factory call whose result was dereferenced at82474944. Other
  // constructors and all non-PC modes retain the original path without reads.
  if (!nfsmw::pc::Active() || uint32_t(ctx.lr) != 0x82474944) {
    __imp__sub_8212BFB8(ctx, base);
    return;
  }
  static std::atomic<unsigned> count{0};
  if (count.fetch_add(1) >= 8) {
    __imp__sub_8212BFB8(ctx, base);
    return;
  }
  const uint32_t key = REX_LOAD_U32(ctx.r3.u32);
  const uint32_t args = ctx.r4.u32;
  const uint32_t p0 = REX_LOAD_U32(args), p1 = REX_LOAD_U32(args + 4),
                 p2 = REX_LOAD_U32(args + 8);
  // Registry traversed by the actual factory, immutable after registration.
  constexpr uint32_t registry = uint32_t(int64_t(-32058) * 65536 - 7100);
  static_assert(registry == 0x82C5E444);
  uint32_t entry = REX_LOAD_U32(registry), match = 0, callback = 0, walked = 0;
  while (entry && walked++ < 256) {
    if (REX_LOAD_U32(entry) == key) {
      match = entry;
      callback = REX_LOAD_U32(entry + 4);
      break;
    }
    entry = REX_LOAD_U32(entry + 8);
  }
  char line[320];
  snprintf(
      line, sizeof(line),
      "[pc-race] factory caller=82474944 key=%08X match=%08X callback=%08X "
      "walked=%u args=%08X,%08X,%08X participant=%08X local=%u car_record=%08X",
      key, match, callback, walked, p0, p1, p2, ctx.r22.u32, ctx.r20.u32,
      REX_LOAD_U32(ctx.r22.u32 + 4432));
  nfsmw::boot::Trace(line);
  __imp__sub_8212BFB8(ctx, base);
  snprintf(line, sizeof(line), "[pc-race] factory key=%08X result=%08X", key,
           ctx.r3.u32);
  nfsmw::boot::Trace(line);
  // Leave the original result intact. A fabricated object or skipped callback
  // would hide the failure and could break later simulation in both games.
}
