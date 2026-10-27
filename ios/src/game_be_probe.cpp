// NFSMW Recompiled (iOS) - TEMPORARY probe for BACKLOG D-007: the Black
// Edition Challenge Series event (19.9.70, the Camaro one) does not show with
// Black Edition on. USA edition addresses.
//
// sub_822EAA60(r3 = event key) says whether an event is available: 99.1.1 is
// always hidden; 21.1.1, 21.2.1, 21.2.2 and 19.9.70 need the Black Edition
// flag (byte 0x82A2CE06); 19.8.31 needs a profile check. This logs each
// distinct (key, caller, result) once, so opening the Challenge Series menu
// shows whether the game asks about 19.9.70 at all and what it gets.
// Remove once D-007 is understood.

#include <cstdint>
#include <mutex>
#include <set>
#include <tuple>

#include "nfsmw_pch.h"

#include <rex/logging.h>

extern "C" void __imp__sub_822EAA60(PPCContext& __restrict ctx, uint8_t* base);

namespace {

// Jenkins hashes (init 0xABCDEF00) of the event IDs that sub_822EAA60 checks.
const char* KnownEvent(uint32_t key) {
  switch (key) {
    case 0xE2C06E4Bu: return "99.1.1";
    case 0x1FDF6AFDu: return "21.1.1";
    case 0x40608EE5u: return "21.2.1";
    case 0x068305F0u: return "21.2.2";
    case 0xFE87E90Bu: return "19.9.70";
    case 0xB8EF8863u: return "19.8.31";
    default: return "";
  }
}

std::mutex g_mutex;
std::set<std::tuple<uint32_t, uint32_t, uint32_t>> g_seen;
uint64_t g_calls = 0;

}  // namespace

extern "C" REX_FUNC(sub_822EAA60) {
  const uint32_t key = ctx.r3.u32;
  const uint32_t caller = uint32_t(ctx.lr);
  __imp__sub_822EAA60(ctx, base);
  const uint32_t result = ctx.r3.u32 & 0xFF;
  std::lock_guard<std::mutex> lock(g_mutex);
  ++g_calls;
  if (g_seen.emplace(key, caller, result).second) {
    REXLOG_INFO("[be-probe] event {:08X} {} from {:08X} -> {} (flag {}, call {})", key,
                KnownEvent(key), caller, result,
                REX_LOAD_U8(0x82A2CE06u), g_calls);
  }
}
