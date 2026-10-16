#pragma once

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <iterator>
#include <map>
#include <utility>
#include <vector>

namespace nfsmw {
// Render-thread-only bookkeeping. Call Release only after the last GPU use.
class ArenaRanges {
  using SizeIndex = std::multimap<size_t, std::pair<uint32_t, size_t>>;
  struct Range {
    size_t size;
    SizeIndex::iterator by_size;
  };
  using Offsets = std::map<size_t, Range>;
  SizeIndex sizes_;
  std::vector<Offsets> chunks_;

  void Insert(uint32_t chunk, size_t offset, size_t size) {
    auto index = sizes_.emplace(size, std::make_pair(chunk, offset));
    chunks_[chunk].emplace(offset, Range{size, index});
  }
  void Erase(uint32_t chunk, Offsets::iterator range) {
    sizes_.erase(range->second.by_size);
    chunks_[chunk].erase(range);
  }

 public:
  ArenaRanges() = default;
  ArenaRanges(const ArenaRanges&) = delete;
  ArenaRanges& operator=(const ArenaRanges&) = delete;

  void AddChunk(uint32_t chunk, size_t size) {
    if (chunks_.size() <= chunk) chunks_.resize(size_t(chunk) + 1);
    assert(chunks_[chunk].empty());
    Insert(chunk, 0, size);
  }
  bool Allocate(size_t size, uint32_t& chunk, size_t& offset) {
    auto found = sizes_.lower_bound(size);
    if (found == sizes_.end()) return false;
    const size_t available = found->first;
    chunk = found->second.first;
    offset = found->second.second;
    Erase(chunk, chunks_[chunk].find(offset));
    if (available > size) Insert(chunk, offset + size, available - size);
    return true;
  }
  void Release(uint32_t chunk, size_t offset, size_t size) {
    auto& ranges = chunks_[chunk];
    auto next = ranges.lower_bound(offset);
    assert(next == ranges.end() || offset + size <= next->first);
    if (next != ranges.begin()) {
      auto previous = std::prev(next);
      assert(previous->first + previous->second.size <= offset);
      if (previous->first + previous->second.size == offset) {
        offset = previous->first;
        size += previous->second.size;
        Erase(chunk, previous);
      }
    }
    if (next != ranges.end() && offset + size == next->first) {
      size += next->second.size;
      Erase(chunk, next);
    }
    Insert(chunk, offset, size);
  }
  void RemoveEmptyChunk(uint32_t chunk, size_t size) {
    auto& ranges = chunks_[chunk];
    assert(ranges.size() == 1 && ranges.begin()->first == 0 && ranges.begin()->second.size == size);
    Erase(chunk, ranges.begin());
  }
};
}  // namespace nfsmw
