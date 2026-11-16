// NFSMW Recompiled (iOS) - the game's UI textures upscaled ahead of time
//
// Sharp HUD (dev161, Stefan): instead of upscaling each menu / HUD texture
// the first time it is drawn, every texture of the game's UI texture packs is
// read from the player's own disc image before the game starts, decoded as
// the native renderer decodes it (untiled, byte-swapped level 0: its content
// hash is the renderer's key), upscaled by the network (hud_upscale.mm) and
// kept on disk. While playing, a texture with a prepared copy just loads it.
//
// The disc: XDVDFS (XGD2) with NFS/ZDIR.BIN (24-byte entries: bStringHash of
// the upper-case path, archive, sector, global sector, size, checksum) over
// NFS/ZZDATA0-9.BIN; .LZC files are JDLZ-compressed; texture packs are chunk
// 0xB3300000 with the pack's name (0x33310001), texture infos (0x33310004,
// 124 bytes each), their Xenos format words (0x33310005, 32 bytes each) and
// the pixel data (0x33320003, from the next 4 KB boundary of the file). All
// verified on the USA disc (November 16; tools prototype in the session).

#include "ui_texture_prep.h"

#import <Foundation/Foundation.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <memory>
#include <cstdio>
#include <cstring>
#include <map>
#include <string>
#include <vector>

#include <rex/logging.h>

#include "hud_upscale.h"

namespace nfsmw::ui_texture_prep {
namespace {

constexpr uint64_t kGameOffset = 0xFD90000;  // XGD2
constexpr int kVersion = 4;  // 2: soft art (glows), 3: photos, no longer through the network                  // bump to prepare everything again

struct Disc {
  FILE* f = nullptr;
  std::map<std::string, std::pair<uint32_t, uint32_t>> nfs;  // name -> sector, size
  std::vector<uint8_t> zdir;
  bool Read(uint64_t offset, void* out, size_t n) {
    return fseeko(f, off_t(offset), SEEK_SET) == 0 && fread(out, 1, n, f) == n;
  }
  std::vector<uint8_t> Bytes(uint64_t offset, size_t n) {
    std::vector<uint8_t> b(n);
    if (!Read(offset, b.data(), n)) b.clear();
    return b;
  }
};

uint16_t U16(const uint8_t* p) { return uint16_t(p[0] | p[1] << 8); }
uint32_t U32(const uint8_t* p) { return uint32_t(p[0] | p[1] << 8 | p[2] << 16 | uint32_t(p[3]) << 24); }

std::map<std::string, std::pair<uint32_t, uint32_t>> Directory(Disc& d, uint32_t sector, uint32_t size) {
  std::map<std::string, std::pair<uint32_t, uint32_t>> out;
  const std::vector<uint8_t> data = d.Bytes(kGameOffset + uint64_t(sector) * 2048, size);
  std::vector<size_t> todo{0};
  while (!todo.empty()) {
    const size_t o = todo.back() * 4;
    todo.pop_back();
    if (o + 14 > data.size()) continue;
    const uint16_t left = U16(&data[o]), right = U16(&data[o + 2]);
    if (left == 0xFFFF) continue;
    const uint8_t nl = data[o + 13];
    if (o + 14 + nl > data.size()) continue;
    std::string name(reinterpret_cast<const char*>(&data[o + 14]), nl);
    std::transform(name.begin(), name.end(), name.begin(), ::toupper);
    out[name] = {U32(&data[o + 4]), U32(&data[o + 8])};
    if (left) todo.push_back(left);
    if (right) todo.push_back(right);
  }
  return out;
}

bool Open(Disc& d, const std::string& iso) {
  d.f = fopen(iso.c_str(), "rb");
  if (!d.f) return false;
  char magic[20];
  if (!d.Read(kGameOffset + 32 * 2048, magic, 20) || std::memcmp(magic, "MICROSOFT*XBOX*MEDIA", 20) != 0) return false;
  uint8_t root[8];
  if (!d.Read(kGameOffset + 32 * 2048 + 20, root, 8)) return false;
  const auto top = Directory(d, U32(root), U32(root + 4));
  auto nfs = top.find("NFS");
  if (nfs == top.end()) return false;
  d.nfs = Directory(d, nfs->second.first, nfs->second.second);
  auto zdir = d.nfs.find("ZDIR.BIN");
  if (zdir == d.nfs.end()) return false;
  d.zdir = d.Bytes(kGameOffset + uint64_t(zdir->second.first) * 2048, zdir->second.second);
  return !d.zdir.empty();
}

uint32_t BStringHash(const std::string& path) {
  uint32_t h = 0xFFFFFFFF;
  for (char c : path) h = h * 33 + uint8_t(::toupper(uint8_t(c)));
  return h;
}

std::vector<uint8_t> File(Disc& d, const std::string& path) {
  const uint32_t h = BStringHash(path);
  for (size_t i = 0; i + 24 <= d.zdir.size(); i += 24) {
    if (U32(&d.zdir[i]) != h) continue;
    const uint32_t archive = U32(&d.zdir[i + 4]), sector = U32(&d.zdir[i + 8]), size = U32(&d.zdir[i + 16]);
    auto a = d.nfs.find("ZZDATA" + std::to_string(archive) + ".BIN");
    if (a == d.nfs.end()) return {};
    return d.Bytes(kGameOffset + uint64_t(a->second.first) * 2048 + uint64_t(sector) * 2048, size);
  }
  return {};
}

std::vector<uint8_t> Jdlz(const std::vector<uint8_t>& in) {
  if (in.size() < 16 || std::memcmp(in.data(), "JDLZ", 4) != 0) return in;
  const uint32_t usize = U32(&in[8]);
  std::vector<uint8_t> out(usize);
  uint32_t f1 = 1, f2 = 1;
  size_t i = 16, o = 0;
  while (i < in.size() && o < usize) {
    if (f1 == 1) f1 = in[i++] | 0x100;
    if (f2 == 1 && i < in.size()) f2 = in[i++] | 0x100;
    if (f1 & 1) {
      if (i + 1 >= in.size()) break;
      uint32_t length, t;
      if (f2 & 1) {
        length = (in[i + 1] | ((in[i] & 0xF0) << 4)) + 3;
        t = (in[i] & 0x0F) + 1;
      } else {
        t = (in[i + 1] | ((in[i] & 0xE0) << 3)) + 17;
        length = (in[i] & 0x1F) + 3;
      }
      i += 2;
      if (t > o) break;
      for (uint32_t k = 0; k < length && o < usize; ++k, ++o) out[o] = out[o - t];
      f2 >>= 1;
    } else {
      out[o++] = in[i++];
    }
    f1 >>= 1;
  }
  out.resize(o);
  return out;
}

// The native renderer's TiledOffset2D (rexglue GetTiledOffset2D).
int32_t Tiled(int32_t x, int32_t y, uint32_t pitch, uint32_t log2) {
  pitch = (pitch + 31) & ~31u;
  int32_t macro = ((x >> 5) + (y >> 5) * int32_t(pitch >> 5)) << (log2 + 7);
  int32_t micro = ((x & 7) + ((y & 0xE) << 2)) << log2;
  int32_t offset = macro + ((micro & ~0xF) << 1) + (micro & 0xF) + ((y & 1) << 4);
  return ((offset & ~0x1FF) << 3) + ((y & 16) << 7) + ((offset & 0x1C0) << 2) +
         (((((y & 8) >> 2) + (x >> 3)) & 3) << 6) + (offset & 0x3F);
}

struct Info {
  uint32_t width, height, format, endian, tiled, place, size;
};

// Level 0 as the renderer decodes it: blocks in rows, byte-swapped.
bool Linear(const uint8_t* data, size_t avail, const Info& t, std::vector<uint8_t>& out, uint32_t& bytes,
            uint32_t& block) {
  switch (t.format) {
    case 0x12: block = 4, bytes = 8; break;   // DXT1
    case 0x13: block = 4, bytes = 16; break;  // DXT2/3
    case 0x14: block = 4, bytes = 16; break;  // DXT4/5
    case 0x06: block = 1, bytes = 4; break;   // 8_8_8_8
    default: return false;
  }
  const uint32_t bw = (t.width + block - 1) / block, bh = (t.height + block - 1) / block;
  const uint32_t log2 = __builtin_ctz(bytes);
  out.assign(size_t(bw) * bh * bytes, 0);
  for (uint32_t by = 0; by < bh; ++by) {
    for (uint32_t bx = 0; bx < bw; ++bx) {
      const size_t so = t.tiled ? size_t(Tiled(int32_t(bx), int32_t(by), bw, log2)) : (size_t(by) * bw + bx) * bytes;
      if (so + bytes > avail) return false;
      const uint8_t* s = data + so;
      uint8_t* d = &out[(size_t(by) * bw + bx) * bytes];
      // As the renderer's copy_blocks: 16-bit pairs swapped for k8in16 (and
      // 2-byte formats), else 32-bit words by the endianness.
      if (bytes == 2 || t.endian == 1) {
        for (uint32_t i = 0; i < bytes; i += 2) d[i] = s[i + 1], d[i + 1] = s[i];
      } else {
        for (uint32_t i = 0; i < bytes; i += 4) {
          if (t.endian == 2) d[i] = s[i + 3], d[i + 1] = s[i + 2], d[i + 2] = s[i + 1], d[i + 3] = s[i];
          else if (t.endian == 3) d[i] = s[i + 2], d[i + 1] = s[i + 3], d[i + 2] = s[i], d[i + 3] = s[i + 1];
          else std::memcpy(d + i, s + i, 4);
        }
      }
    }
  }
  return true;
}

void Rgb565(uint16_t v, int c[3]) {
  c[0] = ((v >> 11) & 31) * 255 / 31, c[1] = ((v >> 5) & 63) * 255 / 63, c[2] = (v & 31) * 255 / 31;
}

// RGBA8 of a decoded level 0 (for the network; not the key).
void Rgba(const std::vector<uint8_t>& lin, const Info& t, std::vector<uint8_t>& out) {
  const uint32_t w = t.width, h = t.height;
  out.assign(size_t(w) * h * 4, 255);
  if (t.format == 0x06) {
    std::memcpy(out.data(), lin.data(), std::min(out.size(), lin.size()));
    return;
  }
  const uint32_t bw = (w + 3) / 4, bh = (h + 3) / 4, bytes = t.format == 0x12 ? 8 : 16;
  for (uint32_t by = 0; by < bh; ++by) {
    for (uint32_t bx = 0; bx < bw; ++bx) {
      const uint8_t* b = &lin[(size_t(by) * bw + bx) * bytes];
      const uint8_t* cb = t.format == 0x12 ? b : b + 8;
      const uint16_t c0 = U16(cb), c1 = U16(cb + 2);
      const uint32_t bits = U32(cb + 4);
      int p[4][4];
      Rgb565(c0, p[0]);
      Rgb565(c1, p[1]);
      const bool three = t.format == 0x12 && c0 <= c1;
      for (int k = 0; k < 3; ++k) {
        p[2][k] = three ? (p[0][k] + p[1][k]) / 2 : (2 * p[0][k] + p[1][k]) / 3;
        p[3][k] = three ? 0 : (p[0][k] + 2 * p[1][k]) / 3;
      }
      p[0][3] = p[1][3] = p[2][3] = 255;
      p[3][3] = three ? 0 : 255;
      uint8_t alpha[16];
      for (int i = 0; i < 16; ++i) alpha[i] = 255;
      if (t.format == 0x13) {
        for (int i = 0; i < 16; ++i) alpha[i] = uint8_t(((b[i / 2] >> (4 * (i & 1))) & 15) * 17);
      } else if (t.format == 0x14) {
        const int a0 = b[0], a1 = b[1];
        uint64_t ab = 0;
        for (int i = 0; i < 6; ++i) ab |= uint64_t(b[2 + i]) << (8 * i);
        int pal[8] = {a0, a1};
        if (a0 > a1) for (int i = 0; i < 6; ++i) pal[2 + i] = ((6 - i) * a0 + (i + 1) * a1) / 7;
        else {
          for (int i = 0; i < 4; ++i) pal[2 + i] = ((4 - i) * a0 + (i + 1) * a1) / 5;
          pal[6] = 0, pal[7] = 255;
        }
        for (int i = 0; i < 16; ++i) alpha[i] = uint8_t(pal[(ab >> (3 * i)) & 7]);
      }
      for (int i = 0; i < 16; ++i) {
        const uint32_t x = bx * 4 + (i & 3), y = by * 4 + (i >> 2);
        if (x >= w || y >= h) continue;
        const int k = (bits >> (2 * i)) & 3;
        uint8_t* o = &out[(size_t(y) * w + x) * 4];
        o[0] = uint8_t(p[k][0]), o[1] = uint8_t(p[k][1]), o[2] = uint8_t(p[k][2]);
        o[3] = t.format == 0x12 ? uint8_t(p[k][3]) : alpha[i];
      }
    }
  }
}

struct Chunk {
  uint32_t id;
  size_t at, size;  // payload
};
void Find(const std::vector<uint8_t>& d, size_t o, size_t end, uint32_t want, std::vector<Chunk>& out) {
  while (o + 8 <= end) {
    const uint32_t id = U32(&d[o]), size = U32(&d[o + 4]);
    if (o + 8 + size > end) break;
    if (id == want) out.push_back({id, o + 8, size});
    if ((id & 0x80000000u) && size) Find(d, o + 8, o + 8 + size, want, out);
    o += 8 + size;
  }
}

// The UI's packs (file, and which of its texture packs).
struct Pack {
  const char* file;
  const char* tpk;  // part of the texture pack's name
};
const Pack kPacks[] = {
    {"FRONTEND\\FRONTB.LZC", "FrontEndTextures"},
    {"GLOBAL\\HUDTEXRACE.BIN", "HudTextures"},
    {"GLOBAL\\HUDTEXTURESPHOTOFINISH.BIN", "HudTextures"},
    {"GLOBAL\\INGAMEA.BUN", "HudTexturesGlobal"},
    {"GLOBAL\\GLOBALA.BUN", "GlobalMessageTextures"},
    {"LANGUAGES\\LANGUAGETEXTURES.BIN", "LanguageTextures"},
    {"GLOBAL\\HUDS_CUSTOM_00.BIN", "HUDS_Custom"},
};

NSURL* DoneMarker() {
  NSURL* any = nfsmw::hud_upscale::PreparedFile(0, 0, 0);
  return [[any URLByDeletingLastPathComponent] URLByAppendingPathComponent:[NSString stringWithFormat:@"done_v%d", kVersion]];
}

}  // namespace

bool Needed() {
  return nfsmw::hud_upscale::ModelPresent() &&
         ![NSFileManager.defaultManager fileExistsAtPath:DoneMarker().path];
}

void Run(const std::string& iso, const std::function<void(uint32_t, uint32_t)>& progress) {
  Disc disc;
  if (!Open(disc, iso)) {
    REXLOG_WARN("[ui-prep] {}: not a readable Xbox 360 disc image", iso);
    if (disc.f) fclose(disc.f);
    return;
  }
  // Gather first (for the progress bar's total).
  struct Item {
    std::vector<uint8_t>* file;
    Info info;
    size_t base;
  };
  std::vector<std::unique_ptr<std::vector<uint8_t>>> files;
  std::vector<Item> items;
  for (const Pack& pack : kPacks) {
    auto data = std::make_unique<std::vector<uint8_t>>(Jdlz(File(disc, pack.file)));
    if (data->empty()) {
      REXLOG_INFO("[ui-prep] {}: not on this disc", pack.file);
      continue;
    }
    const std::vector<uint8_t>& d = *data;
    std::vector<Chunk> tpks;
    Find(d, 0, d.size(), 0xB3300000, tpks);
    size_t here = 0;
    for (const Chunk& tp : tpks) {
      std::vector<Chunk> head, infos, formats, pixels;
      Find(d, tp.at, tp.at + tp.size, 0x33310001, head);
      Find(d, tp.at, tp.at + tp.size, 0x33310004, infos);
      Find(d, tp.at, tp.at + tp.size, 0x33310005, formats);
      Find(d, tp.at, tp.at + tp.size, 0x33320003, pixels);
      if (head.empty() || infos.empty() || formats.empty() || pixels.empty()) continue;
      const std::string name(reinterpret_cast<const char*>(&d[head[0].at + 0x20]),
                             strnlen(reinterpret_cast<const char*>(&d[head[0].at + 0x20]), 0x40));
      if (name.find(pack.tpk) == std::string::npos) continue;
      const size_t base = (pixels[0].at + 0xFFF) & ~size_t(0xFFF);
      const size_t n = std::min(infos[0].size / 124, formats[0].size / 32);
      for (size_t k = 0; k < n; ++k) {
        const uint8_t* e = &d[infos[0].at + k * 124];
        const uint32_t fmt = U32(&d[formats[0].at + k * 32 + 20]);
        Info t{U16(e + 68), U16(e + 70), fmt & 0x3F, (fmt >> 6) & 3, (fmt >> 8) & 1, U32(e + 48), U32(e + 56)};
        if (t.width < 8 || t.height < 8 || t.width > 1024 || t.height > 1024) continue;
        items.push_back({data.get(), t, base});
        ++here;
      }
    }
    REXLOG_INFO("[ui-prep] {}: {} textures", pack.file, here);
    files.push_back(std::move(data));
  }
  fclose(disc.f);
  const uint32_t total = uint32_t(items.size());
  uint32_t done = 0, made = 0, kept = 0, skipped = 0;
  const auto t0 = std::chrono::steady_clock::now();
  for (const Item& it : items) {
    @autoreleasepool {
      std::vector<uint8_t> lin, rgba, up;
      uint32_t bytes = 0, block = 1;
      const size_t at = it.base + it.info.place;
      if (at < it.file->size() &&
          Linear(it.file->data() + at, it.file->size() - at, it.info, lin, bytes, block)) {
        const uint64_t hash = nfsmw::hud_upscale::ContentHash(lin.data(), lin.size());
        NSURL* file = nfsmw::hud_upscale::PreparedFile(hash, it.info.width, it.info.height);
        if ([NSFileManager.defaultManager fileExistsAtPath:file.path]) {
          ++kept;
        } else {
          Rgba(lin, it.info, rgba);
          if (nfsmw::hud_upscale::UpscaleRgba(rgba, it.info.width, it.info.height, up)) {
            nfsmw::hud_upscale::SavePngFile(file, it.info.width * 2, it.info.height * 2, up);
            ++made;
          } else {
            ++skipped;
          }
        }
      } else {
        ++skipped;
      }
      progress(++done, total);
    }
  }
  [@"done" writeToURL:DoneMarker() atomically:YES encoding:NSUTF8StringEncoding error:nil];
  REXLOG_INFO("[ui-prep] {} textures: {} upscaled, {} already there, {} skipped, {:.1f} s", total, made, kept, skipped,
              std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());
}

}  // namespace nfsmw::ui_texture_prep
