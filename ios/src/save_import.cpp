// NFSMW Recompiled - unpacking downloaded saves (see save_import.h).

#include "save_import.h"

#include <zlib.h>

#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <queue>
#include <string>
#include <vector>

#include <rex/filesystem/devices/stfs_container_device.h>
#include <rex/filesystem/entry.h>
#include <rex/filesystem/file.h>

namespace fs = std::filesystem;
using rex::X_STATUS;

namespace nfsmw::saves {
namespace {

std::vector<uint8_t> ReadAll(const fs::path& p) {
  std::ifstream in(p, std::ios::binary);
  return std::vector<uint8_t>(std::istreambuf_iterator<char>(in), {});
}

bool WriteAll(const fs::path& p, const uint8_t* data, size_t n) {
  std::error_code ec;
  fs::create_directories(p.parent_path(), ec);
  std::ofstream out(p, std::ios::binary);
  out.write(reinterpret_cast<const char*>(data), std::streamsize(n));
  return bool(out);
}

// A path from an archive kept inside out_dir (no absolute paths or "..").
bool Inside(const std::string& name) {
  if (name.empty() || name[0] == '/' || name[0] == '\\') return false;
  for (const auto& part : fs::path(name)) {
    if (part == "..") return false;
  }
  return true;
}

}  // namespace

// ZIP: the end record gives the central directory; each of its entries points
// at a local header, after which the data is stored (0) or deflated (8).
bool Unzip(const fs::path& zip, const fs::path& out_dir) {
  const std::vector<uint8_t> d = ReadAll(zip);
  auto u16 = [&](size_t at) { return uint32_t(d[at]) | uint32_t(d[at + 1]) << 8; };
  auto u32 = [&](size_t at) { return u16(at) | u16(at + 2) << 16; };
  if (d.size() < 22) return false;
  size_t end = d.size() - 22;
  const size_t stop = d.size() > 22 + 0xFFFF ? d.size() - 22 - 0xFFFF : 0;
  while (u32(end) != 0x06054B50) {
    if (end == stop) return false;
    --end;
  }
  const uint32_t count = u16(end + 10);
  size_t at = u32(end + 16);
  int written = 0;
  for (uint32_t i = 0; i < count; ++i) {
    if (at + 46 > d.size() || u32(at) != 0x02014B50) return false;
    const uint32_t method = u16(at + 10), packed = u32(at + 20), size = u32(at + 24);
    const uint32_t name_len = u16(at + 28), extra_len = u16(at + 30), comment_len = u16(at + 32);
    const size_t local = u32(at + 42);
    if (at + 46 + name_len > d.size()) return false;
    const std::string name(reinterpret_cast<const char*>(&d[at + 46]), name_len);
    at += 46 + name_len + extra_len + comment_len;
    if (name.back() == '/' || !Inside(name) || name.rfind("__MACOSX/", 0) == 0) continue;
    if (local + 30 > d.size() || u32(local) != 0x04034B50) return false;
    const size_t data = local + 30 + u16(local + 26) + u16(local + 28);
    if (data + packed > d.size()) return false;
    std::vector<uint8_t> out(size);
    if (method == 0 && packed == size) {
      std::memcpy(out.data(), &d[data], size);
    } else if (method == 8) {
      z_stream z{};
      if (inflateInit2(&z, -MAX_WBITS) != Z_OK) return false;
      z.next_in = const_cast<Bytef*>(&d[data]);
      z.avail_in = packed;
      z.next_out = out.data();
      z.avail_out = size;
      const int r = inflate(&z, Z_FINISH);
      inflateEnd(&z);
      if (r != Z_STREAM_END || z.total_out != size) return false;
    } else {
      continue;  // another compression: not from Files or a usual zip tool
    }
    if (!WriteAll(out_dir / name, out.data(), out.size())) return false;
    ++written;
  }
  return written > 0;
}

bool IsStfs(const fs::path& file) {
  char magic[4] = {};
  if (FILE* f = fopen(file.c_str(), "rb")) {
    fread(magic, 1, 4, f);
    fclose(f);
  }
  return !memcmp(magic, "CON ", 4) || !memcmp(magic, "LIVE", 4) || !memcmp(magic, "PIRS", 4);
}

bool ExtractStfs(const fs::path& package, const fs::path& out_dir) {
  namespace vfs = rex::filesystem;
  vfs::StfsContainerDevice device("", package);
  if (!device.Initialize()) return false;
  std::queue<vfs::Entry*> queue;
  if (vfs::Entry* root = device.ResolvePath("/")) queue.push(root);
  int written = 0;
  while (!queue.empty()) {
    vfs::Entry* entry = queue.front();
    queue.pop();
    for (auto& child : entry->children()) queue.push(child.get());
    if (entry->attributes() & vfs::kFileAttributeDirectory) continue;
    const std::string path = entry->path();
    if (!Inside(path)) continue;
    vfs::File* in = nullptr;
    if (entry->Open(vfs::FileAccess::kFileReadData, &in) != X_STATUS_SUCCESS) continue;
    std::vector<uint8_t> data(entry->size());
    size_t got = 0;
    const bool ok = in->ReadSync(std::span<uint8_t>(data), 0, &got) == X_STATUS_SUCCESS && got == data.size();
    in->Destroy();
    if (!ok || !WriteAll(out_dir / path, data.data(), data.size())) return false;
    ++written;
  }
  return written > 0;
}

}  // namespace nfsmw::saves
