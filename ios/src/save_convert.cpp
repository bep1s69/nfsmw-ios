// NFSMW Recompiled - converting a PC save to the Xbox 360 layout (see
// save_convert.h).
//
// The PC v1.3 save (63,596 bytes, "20CM") and the Xbox 360 one (62,688 bytes,
// "MC02") hold the same structures; the Xbox stores every 2- and 4-byte value
// big-endian, packs the Lua table bitfields the other way round, fills unused
// bytes with 0xAA instead of 0xCD, and has its own options block and tail. The
// field map comes from sprintstate/nfs-mw-save-editor (GPL-3.0,
// core/switch_format.py, which reads Xbox 360 saves of the Switch port of the
// same recompilation), extended here to the whole FEPlayerCarDB (all 200 car
// records and 75 customizations; FEPlayerCarDB layout from the dbalatoni13/nfsmw
// decompilation) and checked against the order the Xbox 360 loader reads
// the file (sub_822C2998, sub_822C3A60). Parts with no known map (the
// options block 0x5B41-, the end of the tail) are taken
// from an Xbox 360 save of this device, the template.

#include "save_convert.h"

#include <algorithm>
#include <array>
#include <cstring>
#include <functional>
#include <map>
#include <utility>

#include <CommonCrypto/CommonDigest.h>

namespace nfsmw::saves {
namespace {

constexpr size_t kPcSize = 0xF86C;
constexpr size_t kXboxSize = 0xF4E0;
constexpr size_t kGameStart = 0x34;
constexpr size_t kGameSize = 0x4000;

using Bytes = std::vector<uint8_t>;

void Reverse(uint8_t* p, size_t n) {
  for (size_t i = 0; i < n / 2; ++i) std::swap(p[i], p[n - 1 - i]);
}

uint32_t U32(const uint8_t* p, bool big) {
  return big ? uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]
             : uint32_t(p[3]) << 24 | uint32_t(p[2]) << 16 | uint32_t(p[1]) << 8 | p[0];
}

uint16_t U16(const uint8_t* p, bool big) { return big ? uint16_t(p[0] << 8 | p[1]) : uint16_t(p[1] << 8 | p[0]); }

void Put32(uint8_t* p, uint32_t v, bool big) {
  for (int i = 0; i < 4; ++i) p[i] = uint8_t(v >> (big ? 24 - 8 * i : 8 * i));
}

void Md5(const uint8_t* p, size_t n, uint8_t out[16]) {
  CC_MD5_CTX c;
  CC_MD5_Init(&c);
  CC_MD5_Update(&c, p, CC_LONG(n));
  CC_MD5_Final(out, &c);
}

// EA's CRC32 (poly 0x04C11DB7, MSB first, seeded with the first word).
uint32_t EaCrc32(const uint8_t* p, size_t n) {
  static const auto table = [] {
    std::array<uint32_t, 256> t{};
    for (uint32_t i = 0; i < 256; ++i) {
      uint32_t c = i << 24;
      for (int k = 0; k < 8; ++k) c = (c & 0x80000000u) ? (c << 1) ^ 0x04C11DB7u : c << 1;
      t[i] = c;
    }
    return t;
  }();
  if (n < 4) return 0;
  uint32_t crc = ~(uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3]);
  for (size_t i = 4; i < n; ++i) crc = ((crc << 8) | p[i]) ^ table[crc >> 24];
  return ~crc;
}

// The header's sizes and checksums, and the trailing MD5 of [0x34, end-16).
void Repair(Bytes& b, bool big) {
  Put32(&b[4], uint32_t(b.size()), big);
  Md5(&b[0x34], b.size() - 0x34 - 16, &b[b.size() - 16]);
  Put32(&b[0x10], EaCrc32(&b[0x1C], 8), big);
  Put32(&b[0x14], EaCrc32(&b[0x24], b.size() - 0x24), big);
  Put32(&b[0x18], EaCrc32(&b[0], 0x18), big);
}

// A persistent activity's Lua table: entries alternate key and value; each
// starts with a byte of flags (kind 4 bits, boolean, packed, key, valid; in
// that order from the top bit on the Xbox, from the bottom on PC). Numbers
// (kind 3) carry 4 bytes, or 1 when packed; identifiers (kind 4) run to a zero
// byte, but packed ones may contain zeros, so the one complete parse is
// searched for.
struct LuaFlags {
  int kind, boolean, packed, key, valid;
};

LuaFlags PcFlags(uint8_t v) {
  return {v & 15, (v >> 4) & 1, (v >> 5) & 1, (v >> 6) & 1, (v >> 7) & 1};
}

uint8_t XboxByte(const LuaFlags& f) {
  return uint8_t(f.kind << 4 | f.boolean << 3 | f.packed << 2 | f.key << 1 | f.valid);
}

bool LuaTable(uint8_t* t, size_t size) {
  using Path = std::vector<std::pair<size_t, int>>;  // (position, kind)
  struct Result {
    int count = 0;  // complete parses found (0, 1 or 2 = ambiguous)
    Path path;
  };
  std::map<std::pair<size_t, bool>, Result> memo;
  std::function<Result(size_t, bool)> walk = [&](size_t pos, bool expect_key) -> Result {
    if (pos >= size) return {};
    auto it = memo.find({pos, expect_key});
    if (it != memo.end()) return it->second;
    Result r;
    const LuaFlags f = PcFlags(t[pos]);
    if (!f.valid) {
      if (t[pos] == 0 && pos + 1 == size && expect_key) r.count = 1;
    } else if (bool(f.key) == expect_key && (f.kind == 1 || f.kind == 3 || f.kind == 4)) {
      std::vector<size_t> after;
      if (f.kind == 4) {
        for (size_t i = pos + 1; i < size; ++i) {
          if (t[i] != 0) continue;
          after.push_back(i + 1);
          if (!f.packed) break;
        }
      } else {
        after.push_back(pos + 1 + (f.kind == 3 ? (f.packed ? 1 : 4) : 0));
      }
      for (size_t next : after) {
        const Result tail = walk(next, !expect_key);
        if (!tail.count) continue;
        const size_t len = tail.path.size() + 1;
        if (r.count && len < r.path.size()) continue;  // prefer the longest
        if (r.count && len > r.path.size()) r.count = 0;
        if (!r.count) {
          r.path = {{pos, f.kind}};
          r.path.insert(r.path.end(), tail.path.begin(), tail.path.end());
        }
        r.count = std::min(2, r.count + tail.count);
      }
    }
    memo[{pos, expect_key}] = r;
    return r;
  };
  const Result r = walk(0, true);
  if (r.count != 1) return false;
  for (const auto& [pos, kind] : r.path) {
    const LuaFlags f = PcFlags(t[pos]);
    t[pos] = XboxByte(f);
    if (kind == 3 && !f.packed) Reverse(&t[pos + 1], 4);
  }
  return true;
}

// The 16 KiB gameplay section (0x34-0x4034, its own MD5 first).
bool GameSection(uint8_t* g) {
  if (std::memcmp(g + 16, "Game", 4) != 0) return false;
  uint32_t h[11];
  for (int i = 0; i < 11; ++i) h[i] = U32(g + 16 + 4 * i, false);
  const uint32_t version = h[1], persistent = h[2], timers = h[3], types = h[4], milestones = h[5],
                 traps = h[6], gates = h[7], hiding_bits = h[8], bin_bytes = h[9], sms = h[10];
  if (version != 8 || persistent > 256 || timers > 64 || types > 128 || milestones > 256 || traps > 128) {
    return false;
  }
  for (size_t p = 16; p < 60; p += 4) Reverse(g + p, 4);
  auto fits = [&](size_t pos, size_t n) { return pos <= kGameSize && n <= kGameSize - pos; };
  size_t pos = 0x80;
  for (uint32_t i = 0; i < persistent; ++i) {
    if (!fits(pos, 16)) return false;
    const uint32_t size = U32(g + pos + 4, false);
    if (size < 8) return false;
    const size_t record = (8 + size + 15) & ~size_t(15);
    const uint16_t table = U16(g + pos + 14, false);
    if (!fits(pos, record) || table != size - 8) return false;
    for (auto [rel, width] : {std::pair{0, 4}, {4, 4}, {8, 4}, {12, 2}, {14, 2}}) Reverse(g + pos + rel, width);
    if (table && !LuaTable(g + pos + 16, table)) return false;
    pos += record;
  }
  auto align = [](size_t v) { return (v + 7) & ~size_t(7); };
  if (!fits(pos, timers * 32)) return false;
  for (uint32_t i = 0; i < timers; ++i, pos += 32) {
    Reverse(g + pos, 4);      // interval
    Reverse(g + pos + 8, 4);  // elapsed
  }
  pos = align(pos);
  if (!fits(pos, types * 16)) return false;
  for (uint32_t i = 0; i < types; ++i, pos += 16) {
    for (int rel = 0; rel < 16; rel += 4) Reverse(g + pos + rel, 4);
  }
  pos = align(pos);
  if (!fits(pos, milestones * 20)) return false;
  for (uint32_t i = 0; i < milestones; ++i, pos += 20) {
    for (auto [rel, width] : {std::pair{0, 4}, {4, 4}, {10, 2}, {12, 4}, {16, 4}}) Reverse(g + pos + rel, width);
  }
  pos = align(pos);
  if (!fits(pos, traps * 20)) return false;
  for (uint32_t i = 0; i < traps; ++i, pos += 20) {
    for (auto [rel, width] : {std::pair{0, 2}, {2, 2}, {4, 4}, {8, 4}, {12, 4}, {16, 4}}) Reverse(g + pos + rel, width);
  }
  pos = align(pos);
  if (!fits(pos, gates * 4)) return false;
  for (uint32_t i = 0; i < gates; ++i, pos += 4) Reverse(g + pos, 4);
  pos = align(pos);
  const size_t hiding = (hiding_bits + 7) / 8;
  if (hiding % 4 || !fits(pos, hiding)) return false;
  for (size_t rel = 0; rel < hiding; rel += 4) Reverse(g + pos + rel, 4);
  pos = align(pos + hiding);
  if (bin_bytes < 4 || !fits(pos, bin_bytes)) return false;
  if (bin_bytes != 4 + U32(g + pos, false) * 8) return false;
  Reverse(g + pos, 4);
  for (size_t rel = 4; rel < bin_bytes; rel += 2) Reverse(g + pos + rel, 2);
  pos = align(pos + bin_bytes);
  if (!fits(pos, sms * 4)) return false;
  for (uint32_t i = 0; i < sms; ++i, pos += 4) Reverse(g + pos, 4);
  pos = align(pos);
  if (!fits(pos, 32)) return false;
  Reverse(g + pos + 8, 4);  // free-roam marker keys
  Reverse(g + pos + 24, 4);
  Md5(g + 16, kGameSize - 16, g);
  return true;
}

void Words(uint8_t* p, size_t n, size_t width) {
  for (size_t i = 0; i + width <= n; i += width) Reverse(p + i, width);
}

void Settings(uint8_t* p) {
  Reverse(p, 2);      // AdaptiveDifficulty (0x403D)
  Reverse(p + 2, 4);  // SpecialFlags
  for (size_t pos = 6; pos < 606; pos += 4) Reverse(p + pos + 2, 2);  // SMS sort order
  Reverse(p + 606, 2);
}

// The race records after the profile id (read by sub_822C2D30): a u32 count
// (at most 300) and 300 records of 16 bytes (u32 key, u32 flags, u32, u16,
// u16).
void RaceRecords(uint8_t* p) {
  Reverse(p, 4);
  for (size_t pos = 4; pos < 4 + 300 * 16; pos += 16) {
    for (auto [rel, width] : {std::pair{0, 4}, {4, 4}, {8, 4}, {12, 2}, {14, 2}}) Reverse(p + pos + rel, width);
  }
}

// FECarRecord: handle, FE key, vehicle key, filter bits; then bytes.
void CarRecords(uint8_t* p, size_t count) {
  for (size_t i = 0; i < count; ++i, p += 20) {
    for (int rel = 0; rel < 16; rel += 4) Reverse(p + rel, 4);
    if (p[18] == 0xCD && p[19] == 0xCD) p[18] = p[19] = 0xAA;
  }
}

// FECustomizationRecord (0x198): part indices (int16), physics, tunings,
// active tuning, preset (32-bit), handle byte.
void Customizations(uint8_t* p, size_t count) {
  for (size_t i = 0; i < count; ++i, p += 0x198) {
    for (int rel = 0; rel < 0x116; rel += 2) Reverse(p + rel, 2);
    if (p[0x116] == 0xCD && p[0x117] == 0xCD) p[0x116] = p[0x117] = 0xAA;
    for (int rel = 0x118; rel < 0x194; rel += 4) Reverse(p + rel, 4);
    if (p[0x195] == 0xCD && p[0x196] == 0xCD && p[0x197] == 0xCD) p[0x195] = p[0x196] = p[0x197] = 0xAA;
  }
}

// FECareerRecord (0x38): handle, impound bytes, heat, bounty, then u16 counts
// and infractions.
void CareerRecords(uint8_t* p, size_t count) {
  for (size_t i = 0; i < count; ++i, p += 0x38) {
    for (int rel : {1, 10, 11}) {
      if (p[rel] == 0xCD) p[rel] = 0xAA;
    }
    Reverse(p + 12, 4);
    Reverse(p + 16, 4);
    for (int rel = 20; rel < 56; rel += 2) Reverse(p + rel, 2);
  }
}

}  // namespace

bool IsPcSave(const uint8_t* data, size_t size) {
  return size == kPcSize && std::memcmp(data, "20CM", 4) == 0 && U32(data + 4, false) == kPcSize;
}

bool IsXboxSave(const uint8_t* data, size_t size) {
  return size == kXboxSize && std::memcmp(data, "MC02", 4) == 0 && U32(data + 4, true) == kXboxSize &&
         U32(data + 0x1C, true) == 0x10D;
}

std::vector<uint8_t> ConvertPcSave(const std::vector<uint8_t>& pc, const std::vector<uint8_t>& xbox_template,
                                   std::string* error) {
  auto fail = [&](const char* why) {
    if (error) *error = why;
    return std::vector<uint8_t>{};
  };
  if (!IsPcSave(pc.data(), pc.size())) return fail("not a PC v1.3 save (63,596 bytes, 20CM)");
  if (!IsXboxSave(xbox_template.data(), xbox_template.size())) return fail("no usable Xbox 360 save as a template");
  if (U32(&pc[0x1C], false) != 0x10D) return fail("unsupported PC save version");
  Bytes out(xbox_template);
  // PC offset, Xbox offset, length; converted in place in `out`.
  auto copy = [&](size_t from, size_t to, size_t n) {
    std::memcpy(&out[to], &pc[from], n);
    return &out[to];
  };
  if (!GameSection(copy(0x34, 0x34, kGameSize))) return fail("the career section could not be read");
  Words(copy(0x4034, 0x4034, 4), 4, 4);
  copy(0x4038, 0x4038, 1);
  Words(copy(0x4039, 0x4039, 4), 4, 4);  // cash
  Settings(copy(0x403D, 0x403D, 608));
  // From here the order the game's loader reads (sub_822C2998, then
  // sub_822C3A60): profile id, race records, 57 unlock records of bytes,
  // 63 x 12 bytes of 32-bit values.
  copy(0x429D, 0x429D, 16);  // profile id (text)
  RaceRecords(copy(0x42AD, 0x42AD, 4 + 300 * 16));
  copy(0x5571, 0x5571, 57 * 8);
  Words(copy(0x5739, 0x5739, 63 * 12), 63 * 12, 4);
  // 0x5A2D: a word the loader compares with one the game holds at run time
  // (the load is refused when they differ): the template's stays.
  copy(0x5A31, 0x5A31, 32);  // alias and bytes
  // 240 bytes: 30 records {u32, byte, 3 pad}.
  for (size_t i = 0; i < 30; ++i) {
    uint8_t* r = copy(0x5A51 + 8 * i, 0x5A51 + 8 * i, 8);
    Reverse(r, 4);
    for (int k = 5; k < 8; ++k) {
      if (r[k] == 0xCD) r[k] = 0xAA;
    }
  }
  // Then 140 bytes of options on the Xbox (132 on PC): the template's. Then
  // the car database (FEPlayerCarDB, 36,040 bytes).
  CarRecords(copy(0x5BC5, 0x5BCD, 200 * 20), 200);
  Customizations(copy(0x6B65, 0x6B6D, 75 * 0x198), 75);
  CareerRecords(copy(0xE2ED, 0xE2F5, 25 * 0x38), 25);
  {
    uint8_t* h = copy(0xE865, 0xE86D, 40);  // sold-car history
    Reverse(h, 4);
    Words(h + 4, 36, 2);
  }
  // After the car database (sub_822C3A60): a byte, 3032 bytes of career
  // stats (32-bit values from offset 1, with five 56-byte rival records at
  // 0xA2D that start with a 12-byte "MW-..." name), then the current car's
  // handle for each of 11 game modes. The rest (read by sub_822C6880) differs
  // between the two and stays the template's.
  {
    uint8_t* t = copy(0xE88D, 0xE895, 1 + 3032 + 44);
    for (size_t pos = 1; pos + 4 <= 1 + 3032 + 44; pos += 4) {
      const bool name = pos >= 0xA2D && pos < 0xA2D + 5 * 56 && (pos - 0xA2D) % 56 < 12;
      if (!name) Reverse(t + pos, 4);
    }
  }
  Repair(out, true);
  return out;
}

}  // namespace nfsmw::saves
