// The game's register save/restore helpers (__savegprlr_14..31,
// __restgprlr_14..31), natively. Every guest function with a stack frame calls
// one on entry and one on exit: 3.8-4.3% of app CPU in the October 19 iPad
// profile. The generated bodies compute each access's address on its own
// (with the physical-alias check) through volatile accesses, one store or load
// at a time. Here the ordinary stack case computes the host address once and
// lets the compiler pair the byte-swapped accesses; the values, offsets,
// widths and order of the stack contents are the same: rK at r1 - 8*(32-K) - 8
// as 64 bits, the 32-bit link register word (r12) at r1 - 8. Restore
// zero-extends that word into r12 and LR. An unusual stack pointer (near 0 or in
// the physical range) takes the original body.
//
// Switch: --nfsmw_native_gpr_helpers (default false; restart required).

#include <cstdint>
#include <cstring>

#include <rex/cvar.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(nfsmw_native_gpr_helpers, false, "CPU",
                    "Experiment: native guest register save/restore helpers (restart required)");

namespace {

constexpr PPCRegister PPCContext::* kGpr[32] = {
    &PPCContext::r0,  &PPCContext::r1,  &PPCContext::r2,  &PPCContext::r3,  &PPCContext::r4,  &PPCContext::r5,
    &PPCContext::r6,  &PPCContext::r7,  &PPCContext::r8,  &PPCContext::r9,  &PPCContext::r10, &PPCContext::r11,
    &PPCContext::r12, &PPCContext::r13, &PPCContext::r14, &PPCContext::r15, &PPCContext::r16, &PPCContext::r17,
    &PPCContext::r18, &PPCContext::r19, &PPCContext::r20, &PPCContext::r21, &PPCContext::r22, &PPCContext::r23,
    &PPCContext::r24, &PPCContext::r25, &PPCContext::r26, &PPCContext::r27, &PPCContext::r28, &PPCContext::r29,
    &PPCContext::r30, &PPCContext::r31};

inline bool Ordinary(uint32_t sp) { return sp >= 256u && sp < 0xE0000000u; }

template <int First>
__attribute__((always_inline)) inline void Save(PPCContext& ctx, uint8_t* base) {
  uint8_t* top = base + ctx.r1.u32;
  for (int k = First; k < 32; ++k) {
    const uint64_t v = __builtin_bswap64((ctx.*kGpr[k]).u64);
    std::memcpy(top - 8 * (32 - k) - 8, &v, 8);
  }
  const uint32_t lr = __builtin_bswap32(ctx.r12.u32);
  std::memcpy(top - 8, &lr, 4);
}

template <int First>
__attribute__((always_inline)) inline void Restore(PPCContext& ctx, uint8_t* base) {
  const uint8_t* top = base + ctx.r1.u32;
  for (int k = First; k < 32; ++k) {
    uint64_t v;
    std::memcpy(&v, top - 8 * (32 - k) - 8, 8);
    (ctx.*kGpr[k]).u64 = __builtin_bswap64(v);
  }
  uint32_t lr;
  std::memcpy(&lr, top - 8, 4);
  ctx.r12.u64 = __builtin_bswap32(lr);
  ctx.lr = ctx.r12.u64;
}

}  // namespace

#define NFSMW_GPR_HELPERS(K)                                                          \
  extern "C" void __imp____savegprlr_##K(PPCContext& __restrict ctx, uint8_t* base);  \
  extern "C" void __imp____restgprlr_##K(PPCContext& __restrict ctx, uint8_t* base);  \
  extern "C" REX_FUNC(__savegprlr_##K) {                                              \
    if (REXCVAR_GET(nfsmw_native_gpr_helpers) && Ordinary(ctx.r1.u32)) {              \
      Save<K>(ctx, base);                                                             \
      return;                                                                         \
    }                                                                                 \
    __imp____savegprlr_##K(ctx, base);                                                \
  }                                                                                   \
  extern "C" REX_FUNC(__restgprlr_##K) {                                              \
    if (REXCVAR_GET(nfsmw_native_gpr_helpers) && Ordinary(ctx.r1.u32)) {              \
      Restore<K>(ctx, base);                                                          \
      return;                                                                         \
    }                                                                                 \
    __imp____restgprlr_##K(ctx, base);                                                \
  }

NFSMW_GPR_HELPERS(14)
NFSMW_GPR_HELPERS(15)
NFSMW_GPR_HELPERS(16)
NFSMW_GPR_HELPERS(17)
NFSMW_GPR_HELPERS(18)
NFSMW_GPR_HELPERS(19)
NFSMW_GPR_HELPERS(20)
NFSMW_GPR_HELPERS(21)
NFSMW_GPR_HELPERS(22)
NFSMW_GPR_HELPERS(23)
NFSMW_GPR_HELPERS(24)
NFSMW_GPR_HELPERS(25)
NFSMW_GPR_HELPERS(26)
NFSMW_GPR_HELPERS(27)
NFSMW_GPR_HELPERS(28)
NFSMW_GPR_HELPERS(29)
NFSMW_GPR_HELPERS(30)
NFSMW_GPR_HELPERS(31)
