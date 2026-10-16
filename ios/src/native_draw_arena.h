// CPU storage for one recorded frame's small attribute lists. The Frame must
// declare this before its draw list so all attribute objects die before it.
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <memory_resource>

namespace nfsmw {
class DrawArena {
 public:
  static constexpr size_t kMaxInitialBytes = 4 * 1024 * 1024;
  static constexpr size_t kMaxDrawHint = 8192;
  struct Statistics {
    uint64_t allocations = 0;
    uint64_t allocated_bytes = 0;
    uint64_t live_bytes = 0;
    uint64_t peak_bytes = 0;
  };

 private:
  class Heap final : public std::pmr::memory_resource {
   public:
    explicit Heap(std::pmr::memory_resource* upstream) : upstream_(upstream) {}
    Statistics stats;

   private:
    void* do_allocate(size_t bytes, size_t alignment) override {
      void* memory = upstream_->allocate(bytes, alignment);
      ++stats.allocations;
      stats.allocated_bytes += bytes;
      stats.live_bytes += bytes;
      stats.peak_bytes = std::max(stats.peak_bytes, stats.live_bytes);
      return memory;
    }
    void do_deallocate(void* memory, size_t bytes, size_t alignment) override {
      upstream_->deallocate(memory, bytes, alignment);
      stats.live_bytes -= bytes;
    }
    bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override {
      return this == &other;
    }
    std::pmr::memory_resource* upstream_;
  };

  // Reverse destruction order: pool releases its blocks before heap dies.
  Heap heap_;
  std::pmr::monotonic_buffer_resource pool_;
  const bool enabled_;

 public:
  DrawArena(bool enabled, size_t previous_attribute_bytes,
            std::pmr::memory_resource* upstream = std::pmr::new_delete_resource())
      : heap_(upstream),
        pool_(std::clamp(previous_attribute_bytes, size_t(4096), kMaxInitialBytes), &heap_),
        enabled_(enabled) {}
  DrawArena(const DrawArena&) = delete;
  DrawArena& operator=(const DrawArena&) = delete;
  DrawArena(DrawArena&&) = delete;
  DrawArena& operator=(DrawArena&&) = delete;

  bool Enabled() const { return enabled_; }
  std::pmr::memory_resource* Resource() {
    if (enabled_) return &pool_;
    return &heap_;
  }
  Statistics Stats() const { return heap_.stats; }
};
}  // namespace nfsmw
