// HOST-ONLY feasibility candidate. Not included by the game or code generator.
// A false return can follow a completed prefix; ctx then names the next original
// descriptor. The caller must resume the current generated loop, not restart it.
#pragma once
#include <cstdint>
#include "../../ios/src/game_constant_copies.h"

namespace nfsmw::constants::candidate {
template<bool Pixel>
inline bool Run(PPCContext& ctx, uint8_t* base, PPCCRRegister& cr6,
                uint32_t& ea, PPCRegister& temp) {
  const uint32_t sp=ctx.r1.u32;
  if (!OrdinaryRange(sp,448) || (sp&15) ||
      ctx.r18.u64!=0x8000000000000000ull) return false;
  uint32_t descriptor=ctx.r11.u32;
  const uint32_t end=REX_LOAD_U32(sp+92);
  if (ctx.r11.u64!=descriptor || (descriptor&15) || end<=descriptor ||
      (end-descriptor)%16 || end-descriptor>64*16 ||
      !OrdinaryRange(descriptor,end-descriptor) ||
      Overlaps(descriptor,end-descriptor,sp,448) ||
      REX_LOAD_U32(sp+80)!=descriptor) return false;
  const uint32_t bank=REX_LOAD_U32(sp+120);
  const uint32_t bindings=REX_LOAD_U32(sp+96);
  const uint32_t source_bank=REX_LOAD_U32(sp+100);
  if (ctx.r21.u64!=bank || ctx.r23.u64!=bindings || ctx.r24.u64!=source_bank ||
      (bank&15) || (source_bank&15) || (bindings&7) ||
      !OrdinaryRange(bank,32) || Overlaps(bank,32,sp,448) ||
      Overlaps(bank,32,descriptor,end-descriptor)) return false;
  const uint32_t run_start=descriptor;
  while (descriptor<end) {
    const uint32_t word0=REX_LOAD_U32(descriptor);
    const uint32_t word=REX_LOAD_U32(descriptor+(Pixel?8:4));
    const uint32_t slot=((uint64_t(word0)<<17)|(word0>>15))&0x1fff8u;
    const uint64_t binding=uint64_t(bindings)+slot+4;
    if (binding>UINT32_MAX || !OrdinaryRange(uint32_t(binding),4)) return false;
    const uint32_t selection=REX_LOAD_U32(uint32_t(binding));
    const uint32_t index=word&1023u, limit=(word>>10)&3u, count=limit+1;
    const uint64_t source=uint64_t(source_bank)+((selection<<4)&0xffff0u);
    const uint64_t dest=uint64_t(bank)+(index+(Pixel?376u:120u))*16;
    if (index+count>256 || source>UINT32_MAX || dest>UINT32_MAX ||
        !OrdinaryRange(uint32_t(source),count*16) ||
        !OrdinaryRange(uint32_t(dest),count*16) ||
        Overlaps(uint32_t(source),count*16,sp,448) ||
        Overlaps(uint32_t(dest),count*16,sp,448) ||
        Overlaps(uint32_t(dest),count*16,run_start,end-run_start)) return false;

    REX_STORE_U32(sp+88,0);
    if constexpr(Pixel) {
      REX_STORE_U32(sp+236,uint32_t(source));
      REX_STORE_U32(sp+244,uint32_t(dest));
    } else REX_STORE_U32(sp+248,uint32_t(dest));
    simde__m128i last{};
    for (uint32_t i=0;i<count;++i) {
      last=simde_mm_load_si128(reinterpret_cast<const simde__m128i*>(base+source+i*16));
      simde_mm_store_si128(reinterpret_cast<simde__m128i*>(base+dest+i*16),last);
    }
    simde_mm_store_si128(reinterpret_cast<simde__m128i*>(ctx.v0.u8),
        simde_mm_shuffle_epi8(last,simde_mm_load_si128(
          reinterpret_cast<const simde__m128i*>(VectorMaskL))));
    ea=uint32_t(dest)+(count-1)*16;
    REX_STORE_U32(sp+88,count);
    // The current loop reloads the descriptor after its copy. Keep that read:
    // admission is not permission to freeze a later dirty-state observation.
    const uint32_t dirty_word=REX_LOAD_U32(descriptor+(Pixel?8:4));
    const uint32_t dirty_index=dirty_word&1023u, dirty_limit=(dirty_word>>10)&3u;
    descriptor+=16;
    REX_STORE_U32(sp+80,descriptor);
    // Match generated arithmetic shift and its XER carry, then OR the dirty
    // bits. The accepted r18 has 63 trailing zeros, so this shift loses none.
    const uint32_t first=dirty_index/4, shift=(dirty_index+dirty_limit)/4-first;
    const uint64_t signed_mask=UINT64_MAX<<(63-shift);
    const uint64_t old=REX_LOAD_U64(bank+(Pixel?24:16));
    const uint64_t dirty=old|((first&64)?0:(signed_mask>>(first&127)));
    REX_STORE_U64(bank+(Pixel?24:16),dirty);
    temp.u64=shift;
    cr6.compare<uint32_t>(descriptor,end,ctx.xer);
    ctx.xer.ca=0;
    ctx.r21.u64=bank; ctx.r23.u64=bindings; ctx.r24.u64=source_bank;
    ctx.r11.u64=descriptor; ctx.r10.u64=dirty;
    if constexpr(Pixel) {
      ctx.r7.u64=old; ctx.r8.u64=signed_mask; ctx.r9.u64=uint64_t(bank)+16;
    } else {
      ctx.r7.u64=old; ctx.r8.u64=dirty_limit; ctx.r9.u64=signed_mask;
    }
  }
  return true;
}
}  // namespace nfsmw::constants::candidate
