// NFSMW Recompiled (iOS) - a larger record pool, so Black Edition content fits.
// USA edition addresses.
//
// THE PROBLEM
//
// The game keeps records in a table: 200 slots of 20 bytes, each pointing (by
// a byte index at slot+16) into a pool of 75 entries of 408 bytes, built into
// the same object at table+4000. Right after the pool, at table+34600, comes
// other data, so the pool cannot grow in place.
//
// With Black Edition content on (--black_edition), loading the global data
// creates 84 records: the pool runs out, sub_822CB458 drops the last ones
// without a word, and starting the career looks one of them up and freezes
// (see ios/README.md).
//
// THE FIX
//
// The first 75 entries stay where they are. Entries 75 to kPoolTotal-1 live
// in an overflow block allocated on the guest heap, one per table.
//
//   - tools/ios/patch_game_pool.py edits the generated code: the 31 places
//     that turn an index into an entry address call nfsmw_pool_entry()
//     instead, their "index <= 75" checks become "index <= kPoolTotal-1", and
//     sub_822CBC00 resets the overflow right after its inline reset of the 75.
//     That script reads kPoolTotal from this file.
//   - The functions here replace the ones that walk the pool by pointer:
//     init (sub_822C9220), allocate (sub_822C9570), any free (sub_822C9538),
//     reset (sub_822CB9F0) and the "room for one more?" check (sub_82584050).
//     Each runs the original first, so the first 75 behave exactly as before,
//     and only then looks at the overflow.

#include <cstdint>
#include <mutex>
#include <vector>

#include "nfsmw_pch.h"

#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

extern "C" void __imp__sub_822C9220(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822C9538(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822C9570(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822CB9F0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82584050(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void sub_822CAE48(PPCContext& __restrict ctx, uint8_t* base);

namespace {

// The total number of entries, the original 75 included. The index is a byte
// and 255 means "none", so at most 255. tools/ios/patch_game_pool.py reads it.
constexpr uint32_t kPoolTotal = 150;
constexpr uint32_t kPoolOriginal = 75;
constexpr uint32_t kPoolExtra = kPoolTotal - kPoolOriginal;
constexpr uint32_t kEntrySize = 408;
constexpr uint32_t kPoolOffset = 4000;  // from the table
constexpr uint32_t kIndexOffset = 404;  // the entry's own index; 255 = free
constexpr uint32_t kSlots = 200;
constexpr uint32_t kSlotSize = 20;
static_assert(kPoolTotal <= 255, "the index is a byte, and 255 means none");

struct Overflow {
  uint32_t table;
  uint32_t entries;  // guest address of entry 75
};

std::mutex g_mutex;
std::vector<Overflow> g_overflows;

// What sub_822C9220 leaves in an entry: 139 halfwords of -1, then zeros, and
// the index byte at 255 (free).
void InitEntry(uint8_t* base, uint32_t entry) {
  for (uint32_t i = 0; i < 139; ++i) {
    REX_STORE_U16(entry + i * 2, 0xFFFF);
  }
  for (uint32_t off = 278; off < kEntrySize; ++off) {
    REX_STORE_U8(entry + off, 0);
  }
  REX_STORE_U8(entry + kIndexOffset, 0xFF);
}

uint32_t ExtraEntry(uint32_t entries, uint32_t index) {
  return entries + (index - kPoolOriginal) * kEntrySize;
}

// The table's overflow block, allocated (all entries free) the first time.
// 0 only if the guest heap is out of memory.
uint32_t OverflowFor(uint8_t* base, uint32_t table) {
  std::lock_guard<std::mutex> lock(g_mutex);
  for (const Overflow& o : g_overflows) {
    if (o.table == table) {
      return o.entries;
    }
  }
  auto* memory = rex::system::kernel_state()->memory();
  const uint32_t entries = memory->SystemHeapAlloc(kPoolExtra * kEntrySize);
  if (entries == 0) {
    REXLOG_ERROR("[pool] no guest memory for {} more entries of table {:08X}; "
                 "it stays at {}", kPoolExtra, table, kPoolOriginal);
    return 0;
  }
  for (uint32_t i = kPoolOriginal; i < kPoolTotal; ++i) {
    InitEntry(base, ExtraEntry(entries, i));
  }
  g_overflows.push_back({table, entries});
  REXLOG_INFO("[pool] table {:08X}: {} entries ({} more at {:08X})", table, kPoolTotal,
              kPoolExtra, entries);
  return entries;
}

bool OverflowHasFree(uint8_t* base, uint32_t entries) {
  for (uint32_t i = kPoolOriginal; i < kPoolTotal; ++i) {
    if (REX_LOAD_U8(ExtraEntry(entries, i) + kIndexOffset) == 0xFF) {
      return true;
    }
  }
  return false;
}

}  // namespace

// The patched sites: the address of entry `index` of `table`.
extern "C" uint32_t nfsmw_pool_entry(uint8_t* base, uint32_t table, uint32_t index) {
  if (index < kPoolOriginal || index >= kPoolTotal) {
    return table + kPoolOffset + index * kEntrySize;  // what the game did
  }
  const uint32_t entries = OverflowFor(base, table);
  return entries ? ExtraEntry(entries, index) : 0;
}

// Every entry free again: what sub_822CB9F0 and sub_822CBC00 do to the 75.
extern "C" void nfsmw_pool_reset(uint8_t* base, uint32_t table) {
  if (const uint32_t entries = OverflowFor(base, table)) {
    for (uint32_t i = kPoolOriginal; i < kPoolTotal; ++i) {
      REX_STORE_U8(ExtraEntry(entries, i) + kIndexOffset, 0xFF);
    }
  }
}

// Init of the table (r3), returns it.
extern "C" REX_FUNC(sub_822C9220) {
  const uint32_t table = ctx.r3.u32;
  __imp__sub_822C9220(ctx, base);
  if (const uint32_t entries = OverflowFor(base, table)) {
    for (uint32_t i = kPoolOriginal; i < kPoolTotal; ++i) {
      InitEntry(base, ExtraEntry(entries, i));
    }
  }
}

// Reset: every entry free.
extern "C" REX_FUNC(sub_822CB9F0) {
  const uint32_t table = ctx.r3.u32;
  __imp__sub_822CB9F0(ctx, base);
  nfsmw_pool_reset(base, table);
}

// Is any entry free? 1 or 0.
extern "C" REX_FUNC(sub_822C9538) {
  const uint32_t table = ctx.r3.u32;
  __imp__sub_822C9538(ctx, base);
  if (ctx.r3.u32 == 0) {
    const uint32_t entries = OverflowFor(base, table);
    ctx.r3.u64 = (entries && OverflowHasFree(base, entries)) ? 1 : 0;
  }
}

// Allocate a free entry: the address, or 0. The same initialization the
// original does, and the index written to the entry's own byte.
extern "C" REX_FUNC(sub_822C9570) {
  const uint32_t table = ctx.r3.u32;
  __imp__sub_822C9570(ctx, base);
  if (ctx.r3.u32 != 0) {
    return;
  }
  const uint32_t entries = OverflowFor(base, table);
  for (uint32_t i = kPoolOriginal; entries && i < kPoolTotal; ++i) {
    const uint32_t entry = ExtraEntry(entries, i);
    if (REX_LOAD_U8(entry + kIndexOffset) == 0xFF) {
      InitEntry(base, entry);
      REX_STORE_U8(entry + kIndexOffset, uint8_t(i));
      ctx.r3.u64 = entry;
      return;
    }
  }
  static bool logged = false;
  if (!logged) {
    logged = true;
    REXLOG_WARN("[pool] table {:08X}: all {} entries in use", table, kPoolTotal);
  }
}

// Room for one more record? 1 if fewer than 20 of kind 0xF0004 exist
// (sub_822CAE48), an entry is free and a slot is free; else 0. Only the
// "entry free" part needs the overflow, so: if the original says no while the
// 75 are full, decide again with the overflow counted.
extern "C" REX_FUNC(sub_82584050) {
  __imp__sub_82584050(ctx, base);
  if (ctx.r3.u32 != 0) {
    return;
  }
  // r31 = *(*(0x82A2C684) + 16) + 1052, as the original computes it.
  const uint32_t manager = REX_LOAD_U32(0x82A2C684);
  const uint32_t table = REX_LOAD_U32(manager + 16) + 1052;
  for (uint32_t i = 0; i < kPoolOriginal; ++i) {
    if (REX_LOAD_U8(table + kPoolOffset + i * kEntrySize + kIndexOffset) == 0xFF) {
      return;  // an original entry was free: the "no" came from elsewhere
    }
  }
  const uint32_t entries = OverflowFor(base, table);
  if (!entries || !OverflowHasFree(base, entries)) {
    return;
  }
  bool slot_free = false;
  for (uint32_t i = 0; i < kSlots && !slot_free; ++i) {
    slot_free = REX_LOAD_U32(table + i * kSlotSize) == 0xFFFFFFFF;
  }
  if (!slot_free) {
    return;
  }
  ctx.r3.u64 = table;
  ctx.r4.u64 = 0x000F0004;
  ctx.lr = 0x82584080;
  sub_822CAE48(ctx, base);
  ctx.r3.u64 = (int32_t(ctx.r3.u32) < 20) ? 1 : 0;
}
