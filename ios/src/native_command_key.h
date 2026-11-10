// Exact command operands. Resource objects are separately pinned until reset.
#pragma once
#include <array>
#include <cstdint>
#include <cstddef>
namespace nfsmw {
struct NativeCommandKey {
  std::array<uintptr_t, 31> buffers;
  std::array<uint64_t, 31> offsets;
  uintptr_t index_buffer = 0;
  uint64_t index_offset = 0, count = 0;
  uint32_t primitive = 0;
  bool operator==(const NativeCommandKey&) const = default;
};
struct CommandRun {
  size_t first = 0, count = 0;
  bool Adjacent(size_t slot) const { return count && first + count == slot; }
  void Add(size_t slot) { if (!count) first = slot; ++count; }
  void Clear() { count = 0; }
};
} // namespace nfsmw
