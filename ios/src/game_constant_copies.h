// USA sub_82699100: short float-constant copies before command submission.
// Included after the generated PPC definitions. Keep the original loops as
// fallback; integer conversions and dirty-mask updates remain generated code.
#pragma once

#include <cstdint>

bool& FLAGS_nfsmw_native_constant_copies_storage_();

namespace nfsmw::constants {

inline bool OrdinaryRange(uint32_t address, uint32_t size) {
  // Exclude MMIO, wrapping ranges and physical aliases. Comparing guest
  // addresses for overlap is sufficient only in the ordinary virtual range.
  const uint64_t end = uint64_t(address) + size;
  return end <= 0xA0000000ull &&
         (end <= 0x7F000000ull || address >= 0x80000000u);
}

inline bool Overlaps(uint32_t a, uint32_t size_a, uint32_t b, uint32_t size_b) {
  return uint64_t(a) < uint64_t(b) + size_b &&
         uint64_t(b) < uint64_t(a) + size_a;
}

template <bool Pixel>
inline bool TryCopy(PPCContext& ctx, uint8_t* base, PPCCRRegister& cr6,
                    uint32_t& ea) {
  const uint32_t sp = ctx.r1.u32;
  if (!OrdinaryRange(sp, 448)) return false;
  const uint32_t descriptor = REX_LOAD_U32(sp + 80);
  if (!OrdinaryRange(descriptor, 16) || Overlaps(descriptor, 16, sp, 448)) return false;
  const uint32_t limit = (REX_LOAD_U32(descriptor + (Pixel ? 8 : 4)) >> 10) & 3;
  const uint32_t first = ctx.r10.u32;
  if (first > limit || REX_LOAD_U32(sp + 88) != first) return false;
  const uint32_t source_base = Pixel ? REX_LOAD_U32(sp + 236) : ctx.r9.u32;
  const uint32_t dest_base = REX_LOAD_U32(sp + (Pixel ? 244 : 248));
  const uint32_t source = (source_base & ~15u) + first * 16;
  const uint32_t dest = (dest_base & ~15u) + first * 16;
  const uint32_t bytes = (limit - first + 1) * 16;
  if (!OrdinaryRange(source, bytes) || !OrdinaryRange(dest, bytes) ||
      Overlaps(source, bytes, sp, 448) || Overlaps(dest, bytes, sp, 448) ||
      Overlaps(dest, bytes, descriptor, 16)) return false;

  // These are guest-to-guest byte copies. The two inverse SIMD shuffles
  // cancel for memory output, but the last loaded PPC vector stays visible.
  // Keep each load before its store, including when source and dest overlap.
  // OrdinaryRange validated the entire span, so physical-address adjustment
  // is zero throughout; do not repeat guest-address dispatch per vector.
  simde__m128i last{};
  for (uint32_t offset = 0; offset < bytes; offset += 16) {
    last = simde_mm_load_si128(reinterpret_cast<const simde__m128i*>(base + source + offset));
    simde_mm_store_si128(reinterpret_cast<simde__m128i*>(base + dest + offset), last);
  }
  simde_mm_store_si128(reinterpret_cast<simde__m128i*>(ctx.v0.u8),
      simde_mm_shuffle_epi8(last, simde_mm_load_si128(
          reinterpret_cast<const simde__m128i*>(VectorMaskL))));
  ctx.r11.u64 = descriptor;
  ctx.r10.u64 = limit + 1;
  if constexpr (Pixel) ctx.r9.u64 = limit;
  else ctx.r8.u64 = limit;
  REX_STORE_U32(sp + 88, limit + 1);
  cr6.compare<uint32_t>(limit + 1, limit, ctx.xer);
  ea = dest + bytes - 16;
  return true;
}

}  // namespace nfsmw::constants
