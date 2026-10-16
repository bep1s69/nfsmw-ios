// Shader interfaces are immutable after startup. Missing or malformed
// metadata must preserve all texture slots, never infer that a shader is empty.
#pragma once

#include <charconv>
#include <cstdint>
#include <optional>
#include <sstream>
#include <string>
#include <string_view>
#include <unordered_map>

namespace nfsmw {
class TextureMasks {
 public:
  bool Load(std::string_view text) {
    Clear();
    std::istringstream input{std::string(text)};
    std::string line;
    if (!std::getline(input, line) || line != "nfsmw-texture-masks-v1") return false;
    std::unordered_map<uint64_t, uint16_t> staged[2];
    while (std::getline(input, line)) {
      if (line.empty()) continue;
      std::istringstream row(line);
      std::string name, bits, extra;
      if (!(row >> name >> bits) || (row >> extra) || name.size() != 19 ||
          (name.substr(0, 3) != "vs_" && name.substr(0, 3) != "ps_") || bits.size() != 8) return false;
      uint64_t key = 0;
      uint32_t mask = 0;
      auto k = std::from_chars(name.data() + 3, name.data() + name.size(), key, 16);
      auto m = std::from_chars(bits.data(), bits.data() + bits.size(), mask, 16);
      if (k.ec != std::errc{} || k.ptr != name.data() + name.size() ||
          m.ec != std::errc{} || m.ptr != bits.data() + bits.size() || mask > 0xFFFF ||
          !staged[name[0] == 'p'].emplace(key, uint16_t(mask)).second) return false;
    }
    masks_[0] = std::move(staged[0]);
    masks_[1] = std::move(staged[1]);
    return Size() != 0;
  }

  void SetInternal(bool pixel, uint64_t key, uint16_t mask) {
    masks_[pixel][key] = mask;
    cached_[pixel].valid = false;
  }
  std::optional<uint16_t> ForDraw(uint64_t vs, uint64_t ps) const {
    const auto vertex = Lookup(false, vs), pixel = Lookup(true, ps);
    if (!vertex || !pixel) return std::nullopt;
    return uint16_t(*vertex | *pixel);
  }
  size_t Size() const { return masks_[0].size() + masks_[1].size(); }

 private:
  struct Cached {
    bool valid = false;
    uint64_t key = 0;
    std::optional<uint16_t> value;
  };
  void Clear() {
    masks_[0].clear(); masks_[1].clear();
    cached_[0] = {}; cached_[1] = {};
  }
  std::optional<uint16_t> Lookup(bool pixel, uint64_t key) const {
    Cached& c = cached_[pixel];
    if (!c.valid || c.key != key) {
      const auto it = masks_[pixel].find(key);
      c = {true, key, it == masks_[pixel].end() ? std::nullopt : std::optional<uint16_t>(it->second)};
    }
    return c.value;
  }
  std::unordered_map<uint64_t, uint16_t> masks_[2];
  // Record's caches, like the existing shader-function and fetch-layout
  // caches, are used only by the selected recording thread.
  mutable Cached cached_[2];
};
}  // namespace nfsmw
