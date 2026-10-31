// USA PC player-setup serialization. Translate raw native car fields at their
// actual bitstream boundaries, not guessed offsets in compressed UDP packets.
#include "../boot_trace.h"
#include "nfsmw_pch.h"
#include "pc_car_layout.h"
#include "pc_gateway.h"
extern "C" void __imp__sub_825380E8(PPCContext &__restrict ctx, uint8_t *base);
extern "C" void __imp__sub_82538320(PPCContext &__restrict ctx, uint8_t *base);
extern "C" REX_FUNC(sub_825380E8) {
  if (nfsmw::pc::Active() && ctx.r5.u32 == 8) {
    size_t size = uint32_t(ctx.lr) == 0x824D5704   ? 4
                  : uint32_t(ctx.lr) == 0x824D574C ? 408
                                                   : 0;
    if (size && ctx.r31.u32 < size) {
      // Original loop reads bytes r30[index], emits8bits. Select the native
      // opposite-endian field byte without changing the saved car record.
      ctx.r4.u64 =
          REX_LOAD_U8(ctx.r30.u32 + nfsmw::pc::CarByte(ctx.r31.u32, size));
    }
  }
  __imp__sub_825380E8(ctx, base);
}
extern "C" REX_FUNC(sub_82538320) {
  const uint32_t dest = ctx.r4.u32;
  const size_t size = nfsmw::pc::Active()
                          ? (uint32_t(ctx.lr) == 0x824D54B4   ? 4
                             : uint32_t(ctx.lr) == 0x824D54FC ? 408
                                                              : 0)
                          : 0;
  __imp__sub_82538320(ctx, base);
  if (!size)
    return;
  // Original returns the byte-array's declared size. Never convert beyond
  // an observed complete field; keep the original result for callers.
  if (ctx.r3.u32 != size) {
    nfsmw::boot::Trace(
        "[pc-car] unexpected setup field length=" + std::to_string(ctx.r3.u32) +
        " expected=" + std::to_string(size));
    return;
  }
  for (size_t i = 0; i < size; ++i) {
    auto other = nfsmw::pc::CarByte(i, size);
    if (i < other) {
      auto byte = REX_LOAD_U8(dest + i);
      REX_STORE_U8(dest + i, REX_LOAD_U8(dest + other));
      REX_STORE_U8(dest + other, byte);
    }
  }
  nfsmw::boot::Trace("[pc-car] converted received native car field bytes=" +
                     std::to_string(size));
}
