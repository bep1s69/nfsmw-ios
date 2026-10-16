// USA sub_82453768: scalar float transfers between vector operations.
#pragma once

#include <cstdint>

bool& FLAGS_nfsmw_native_transform_copies_storage_();

namespace nfsmw::transforms {

inline bool OrdinaryRange(uint32_t address, uint32_t size) {
  const uint64_t end = uint64_t(address) + size;
  return end <= 0xA0000000ull &&
         (end <= 0x7F000000ull || address >= 0x80000000u);
}

inline bool NormalOrZero(uint32_t bits) {
  const uint32_t magnitude = bits & 0x7FFFFFFFu;
  return magnitude == 0 ||
         (magnitude >= 0x00800000u && magnitude < 0x7F800000u);
}

// Exact binary32 -> binary64 representation for normal numbers and signed
// zero. No FP instruction, rounding, exception flags or host flush mode change.
inline uint64_t WidenNormalOrZero(uint32_t bits) {
  const uint64_t sign = uint64_t(bits & 0x80000000u) << 32;
  const uint32_t magnitude = bits & 0x7FFFFFFFu;
  return sign | (magnitude == 0 ? 0 :
      (uint64_t(magnitude) << 29) + (uint64_t(896) << 52));
}

template <unsigned Count>
inline bool TryCopy(PPCContext& ctx, uint8_t* base, PPCRegister& temp,
                    bool& flush_disabled) {
  static_assert(Count == 1 || Count == 3);
  const uint32_t source = ctx.r11.u32 + (Count == 1 ? 12344u : 0u);
  const uint32_t dest = ctx.r1.u32 + (Count == 1 ? 92u : 80u);
  if (((source | dest) & 3u) != 0 ||
      !OrdinaryRange(source, Count * 4) ||
      !OrdinaryRange(dest, Count * 4)) return false;

  // Both original sequences load every source before any destination store.
  // Preserve that order, including overlap, and read each word exactly once.
  // Device/MMIO/physical aliases retain the original inline sequence.
  const uint32_t first = REX_LOAD_U32(source);
  uint32_t second = 0, third = 0;
  if constexpr (Count == 3) {
    second = REX_LOAD_U32(source + 4);
    third = REX_LOAD_U32(source + 8);
  }
  const bool exact = NormalOrZero(first) &&
      (Count == 1 || (NormalOrZero(second) && NormalOrZero(third)));
  flush_disabled = !exact;
  if (exact) {
    ctx.f0.u64 = WidenNormalOrZero(first);
    if constexpr (Count == 3) {
      ctx.f13.u64 = WidenNormalOrZero(second);
      ctx.f12.u64 = WidenNormalOrZero(third);
    }
    temp.u32 = first;
    REX_STORE_U32(dest, temp.u32);
    if constexpr (Count == 3) {
      temp.u32 = second;
      REX_STORE_U32(dest + 4, temp.u32);
      temp.u32 = third;
      REX_STORE_U32(dest + 8, temp.u32);
    }
  } else {
    // Reuse the already loaded words; exceptional inputs must not cause a
    // second read. Keep the generated conversions for NaNs/Inf/subnormals.
    ctx.fpscr.disableFlushModeUnconditional();
    temp.u32 = first;
    ctx.f0.f64 = double(temp.f32);
    if constexpr (Count == 3) {
      temp.u32 = second;
      ctx.f13.f64 = double(temp.f32);
      temp.u32 = third;
      ctx.f12.f64 = double(temp.f32);
    }
    temp.f32 = float(ctx.f0.f64);
    REX_STORE_U32(dest, temp.u32);
    if constexpr (Count == 3) {
      temp.f32 = float(ctx.f13.f64);
      REX_STORE_U32(dest + 4, temp.u32);
      temp.f32 = float(ctx.f12.f64);
      REX_STORE_U32(dest + 8, temp.u32);
    }
  }
  return true;
}

}  // namespace nfsmw::transforms
