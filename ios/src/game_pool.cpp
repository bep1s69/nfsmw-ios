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
//
// SAVES
//
// The game saves the table as it is in memory (36040 bytes at the profile's
// +1052, verbatim in the save file), so the overflow was never saved: a career
// saved with Black Edition on came back with the records whose entries were in
// it pointing at empty ones, and those cars drew as nothing (career only: a
// quick race builds its records afresh). Now, when the game creates a save
// (tools/ios/patch_ios_save_hook.py tells us), each table's slots and overflow
// go to Documents/save_extras/<save>.pool; when it opens one, that file is kept
// aside, and the first time the overflow of a table whose slots are exactly the
// saved ones is used (the save's data has been loaded into it), the saved
// overflow is put back.

#include <sys/stat.h>

#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <string>
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
// The SDK's save hook (tools/ios/patch_ios_save_hook.py).
extern "C" void (*rex_ios_save_event)(const char* name, bool created);

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

// --- The overflow in the saves -------------------------------------------

constexpr uint32_t kSlotBytes = kSlots * kSlotSize;
constexpr uint32_t kExtraBytes = kPoolExtra * kEntrySize;
constexpr char kMagic[8] = {'N', 'F', 'S', 'P', 'O', 'O', 'L', '1'};

struct Saved {
  std::vector<uint8_t> slots, extra;  // guest bytes as they were
};

std::mutex g_saves_mutex;
std::vector<Saved> g_pending;  // from the save opened last, not yet put back
std::string g_pending_name;
std::atomic<bool> g_have_pending{false};

uint8_t* Guest(uint32_t address) {
  return rex::system::kernel_state()->memory()->TranslateVirtual<uint8_t*>(address);
}

std::string SidecarPath(const char* name) {
  const char* home = getenv("HOME");
  std::string dir = std::string(home ? home : ".") + "/Documents/save_extras";
  mkdir(dir.c_str(), 0755);
  std::string file = name;
  for (char& c : file) {
    if (c == '/' || c == '\\') c = '_';
  }
  return dir + "/" + file + ".pool";
}

// The game created a save (to write it): every table's slots and overflow.
// Opened one (to read it): its file kept aside until its data is loaded.
void OnSaveEvent(const char* name, bool created) {
  if (!name || !*name) {
    return;
  }
  const std::string path = SidecarPath(name);
  if (created) {
    std::vector<Overflow> overflows;
    {
      std::lock_guard<std::mutex> lock(g_mutex);
      overflows = g_overflows;
    }
    if (overflows.empty()) {
      remove(path.c_str());  // nothing outside the game's own data
      return;
    }
    FILE* f = fopen((path + ".tmp").c_str(), "wb");
    if (!f) {
      REXLOG_WARN("[pool] cannot write {}", path);
      return;
    }
    const uint32_t count = uint32_t(overflows.size());
    bool ok = fwrite(kMagic, 1, sizeof(kMagic), f) == sizeof(kMagic) && fwrite(&count, 4, 1, f) == 1;
    for (const Overflow& o : overflows) {
      ok = ok && fwrite(Guest(o.table), 1, kSlotBytes, f) == kSlotBytes &&
           fwrite(Guest(o.entries), 1, kExtraBytes, f) == kExtraBytes;
    }
    ok = fclose(f) == 0 && ok;
    if (ok && rename((path + ".tmp").c_str(), path.c_str()) == 0) {
      REXLOG_INFO("[pool] save '{}': {} extra entries of {} table(s) kept beside it", name, kPoolExtra, count);
    } else {
      REXLOG_WARN("[pool] save '{}': the extra entries could not be written", name);
    }
    return;
  }
  FILE* f = fopen(path.c_str(), "rb");
  if (!f) {
    return;  // saved before this, or with nothing outside
  }
  char magic[sizeof(kMagic)] = {};
  uint32_t count = 0;
  std::vector<Saved> saved;
  if (fread(magic, 1, sizeof(magic), f) == sizeof(magic) && !memcmp(magic, kMagic, sizeof(kMagic)) &&
      fread(&count, 4, 1, f) == 1 && count < 16) {
    for (uint32_t i = 0; i < count; ++i) {
      Saved s{std::vector<uint8_t>(kSlotBytes), std::vector<uint8_t>(kExtraBytes)};
      if (fread(s.slots.data(), 1, kSlotBytes, f) != kSlotBytes ||
          fread(s.extra.data(), 1, kExtraBytes, f) != kExtraBytes) {
        saved.clear();
        break;
      }
      saved.push_back(std::move(s));
    }
  }
  fclose(f);
  std::lock_guard<std::mutex> lock(g_saves_mutex);
  g_pending = std::move(saved);
  g_pending_name = name;
  g_have_pending = !g_pending.empty();
  if (!g_pending.empty()) {
    REXLOG_INFO("[pool] save '{}': its extra entries wait for its data to be loaded", name);
  }
}

// The overflow of `table` from the save opened last, once its slots are the
// saved ones (the save's data is in it). Before any use of the overflow.
void RestoreIfLoaded(uint32_t table) {
  if (!g_have_pending.load(std::memory_order_acquire)) {
    return;
  }
  std::vector<uint8_t> extra;
  std::string name;
  {
    std::lock_guard<std::mutex> lock(g_saves_mutex);
    for (size_t i = 0; i < g_pending.size(); ++i) {
      if (!memcmp(Guest(table), g_pending[i].slots.data(), kSlotBytes)) {
        extra = std::move(g_pending[i].extra);
        g_pending.erase(g_pending.begin() + i);
        name = g_pending_name;
        break;
      }
    }
    g_have_pending = !g_pending.empty();
  }
  if (extra.empty()) {
    return;
  }
  uint8_t* base = rex::system::kernel_state()->memory()->virtual_membase();
  if (const uint32_t entries = OverflowFor(base, table)) {
    memcpy(Guest(entries), extra.data(), kExtraBytes);
    REXLOG_INFO("[pool] save '{}': extra entries of table {:08X} put back", name, table);
  }
}

struct HookSaves {
  HookSaves() { rex_ios_save_event = &OnSaveEvent; }
} g_hook_saves;

}  // namespace

// The patched sites: the address of entry `index` of `table`.
extern "C" uint32_t nfsmw_pool_entry(uint8_t* base, uint32_t table, uint32_t index) {
  if (index < kPoolOriginal || index >= kPoolTotal) {
    return table + kPoolOffset + index * kEntrySize;  // what the game did
  }
  RestoreIfLoaded(table);
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
    RestoreIfLoaded(table);
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
  RestoreIfLoaded(table);
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
