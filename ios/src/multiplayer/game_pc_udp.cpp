// PC-only CommUDP header experiment, USA edition. See TECHNICAL evidence.
// Own downstream adaptation; original mobile LAN credits in game_lan.cpp.
#include "../boot_trace.h"
#include "nfsmw_pch.h"
#include "pc_gateway.h"
#include <atomic>
#include <cstring>
#include <rex/cvar.h>
REXCVAR_DECLARE(bool, red_lan);
extern "C" void __imp__sub_8282A4F0(PPCContext &__restrict ctx, uint8_t *base);
extern "C" void __imp__sub_8282A5A0(PPCContext &__restrict ctx, uint8_t *base);
namespace {
bool CommCaller(uint32_t lr) { return lr >= 0x8289B000 && lr < 0x8289D200; }
bool PcEndpoint(uint8_t *base, uint32_t peer) {
  return REXCVAR_GET(red_lan) && peer && REX_LOAD_U16(peer + 2) == 3658 &&
         nfsmw::pc::IsRacePeer(REX_LOAD_U32(peer + 4));
}
void Header(uint8_t *bytes) {
  // Swap the two 32-bit transport fields only. Never touch the race payload.
  for (int i : {0, 4}) {
    std::swap(bytes[i], bytes[i + 3]);
    std::swap(bytes[i + 1], bytes[i + 2]);
  }
}
void Trace(bool receive, uint32_t size) {
  static std::atomic<unsigned> rx{0}, tx{0};
  if ((receive ? rx : tx).fetch_add(1) < 2)
    nfsmw::boot::Trace(
        std::string("[pc-udp] ") + (receive ? "receive" : "send") +
        " two header words translated; bytes=" + std::to_string(size));
}
} // namespace
extern "C" REX_FUNC(sub_8282A4F0) {
  const uint32_t source = ctx.r4.u32, size = ctx.r5.u32;
  if (!CommCaller(uint32_t(ctx.lr)) || !PcEndpoint(base, ctx.r7.u32) ||
      !source || size < 8 || size > 2048 || ctx.r1.u32 < size + 256) {
    __imp__sub_8282A4F0(ctx, base);
    return;
  }
  // Synchronous DirtySock send: use a private guest-stack copy so a retry or
  // another reader never sees the original packet temporarily byte-swapped.
  const uint64_t savedStack = ctx.r1.u64;
  const uint32_t frame = (size + 128 + 15) & ~15u;
  ctx.r1.u64 -= frame;
  REX_STORE_U32(ctx.r1.u32, uint32_t(savedStack));
  const uint32_t copy = ctx.r1.u32 + 128;
  std::memmove(base + copy, base + source, size);
  Header(base + copy);
  ctx.r4.u64 = copy;
  __imp__sub_8282A4F0(ctx, base);
  ctx.r1.u64 = savedStack;
  Trace(false, size);
}
extern "C" REX_FUNC(sub_8282A5A0) {
  const uint32_t buffer = ctx.r4.u32, capacity = ctx.r5.u32, peer = ctx.r7.u32;
  const bool comm = CommCaller(uint32_t(ctx.lr));
  // This DirtySock API returns only after dequeuing a completed datagram;
  // unlike WSARecvFrom, no pending asynchronous buffer remains at this point.
  __imp__sub_8282A5A0(ctx, base);
  if (comm && buffer && ctx.r3.s32 >= 8 && ctx.r3.u32 <= capacity &&
      ctx.r3.u32 <= 2048 && PcEndpoint(base, peer)) {
    Header(base + buffer);
    Trace(true, ctx.r3.u32);
  }
}
