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
void Packet(bool receive, const uint8_t *packet, uint32_t size) {
  // Existing kernel logging truncates at96bytes; car/setup messages are longer.
  // Bound both packet count and size. Header is normalized to guest order here.
  if (size <= 32 || size > 2048)
    return;
  static std::atomic<unsigned> rxData{0}, txData{0};
  if ((receive ? rxData : txData).fetch_add(1) >= 32)
    return;
  constexpr char digits[] = "0123456789ABCDEF";
  std::string hex;
  hex.reserve(size * 2);
  for (uint32_t i = 0; i < size; ++i) {
    hex += digits[packet[i] >> 4];
    hex += digits[packet[i] & 15];
  }
  nfsmw::boot::Trace(std::string("[pc-packet] ") + (receive ? "RX" : "TX") +
                     " guest bytes=" + std::to_string(size) + " hex=" + hex);
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
  const uint32_t ip = REX_LOAD_U32(ctx.r7.u32 + 4);
  const uint32_t command = REX_LOAD_U32(copy);
  if (command == 1) nfsmw::pc::NoteInit(ip, false);
  if (command >= 1 && command <= (nfsmw::pc::Hosting(ip) ? 5u : 3u)) {
    const uint32_t localId = REX_LOAD_U32(copy + 4);
    nfsmw::pc::SetLocalRaceId(ip, localId);
    if (nfsmw::pc::HasRaceId(ip))
      REX_STORE_U32(copy + 4, nfsmw::pc::RaceId(ip));
  }
  Packet(false, base + copy, size);
  Header(base + copy);
  ctx.r4.u64 = copy;
  __imp__sub_8282A4F0(ctx, base);
  ctx.r1.u64 = savedStack;
  Trace(false, size);
}
extern "C" REX_FUNC(sub_8282A5A0) {
  const uint32_t buffer = ctx.r4.u32, capacity = ctx.r5.u32, peer = ctx.r7.u32;
  const uint32_t caller = uint32_t(ctx.lr), reference = ctx.r31.u32, socket = ctx.r3.u32;
  const bool comm = CommCaller(caller);
  // This DirtySock API returns only after dequeuing a completed datagram;
  // unlike WSARecvFrom, no pending asynchronous buffer remains at this point.
  __imp__sub_8282A5A0(ctx, base);
  if (comm && buffer && ctx.r3.s32 >= 8 && ctx.r3.u32 <= capacity &&
      ctx.r3.u32 <= 2048 && PcEndpoint(base, peer)) {
    Header(base + buffer);
    const uint32_t ip = REX_LOAD_U32(peer + 4);
    const uint32_t command = REX_LOAD_U32(buffer);
    const uint32_t id = REX_LOAD_U32(buffer + 4);
    // A PC that sends INIT first makes this device its listener, whether this
    // device hosts the lobby or is another guest in it.
    if (command == 1) nfsmw::pc::NoteInit(ip, true);
    const bool listener = nfsmw::pc::Hosting(ip);
    // Original PC850A13–3F emits opcode5 with its listener's connection ID.
    // Xbox's connecting CommUDP uses its own ID to match replies at8289CB3C.
    if (command == (listener ? 1u : 5u)) {
      const bool changed = !nfsmw::pc::HasRaceId(ip) || nfsmw::pc::RaceId(ip) != id;
      nfsmw::pc::ObserveRaceId(ip, id);
      if (changed) nfsmw::boot::Trace("[pc-udp] PC connection ID learned");
    }
    // USA8289C4D8 returns into the CommUDP listener selection loop. Its r31
    // is the current reference: +128 socket, +148 state3/listening, +152 ID.
    // The first INIT must already carry that ID to pass8289C590/C61C. Waiting
    // for an outgoing reply to learn it is circular: rejected INITs get none.
    if (listener && command == 1 && caller == 0x8289C4D8 &&
        reference && !(reference & 3) && REX_LOAD_U32(reference + 128) == socket &&
        REX_LOAD_U32(reference + 148) == 3) {
      const uint32_t localId = REX_LOAD_U32(reference + 152);
      const bool changed = !nfsmw::pc::HasLocalRaceId(ip) || nfsmw::pc::LocalRaceId(ip) != localId;
      nfsmw::pc::SetLocalRaceId(ip, localId);
      if (changed) nfsmw::boot::Trace("[pc-udp] host listener ID captured before INIT matching");
    }
    if (command >= 1 && command <= 5 && nfsmw::pc::HasRaceId(ip) &&
        nfsmw::pc::HasLocalRaceId(ip) && id == nfsmw::pc::RaceId(ip))
      REX_STORE_U32(buffer + 4, nfsmw::pc::LocalRaceId(ip));
    Packet(true, base + buffer, ctx.r3.u32);
    Trace(true, ctx.r3.u32);
  }
}
