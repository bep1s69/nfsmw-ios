// CPU-side ownership only. Borrowed draw handles never outlive their frame.
#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <limits>
#include <deque>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

namespace nfsmw {
inline constexpr size_t kNoFrameSlot=std::numeric_limits<size_t>::max();
inline uint64_t NextOwnerGeneration() {
  static std::atomic<uint64_t> generation{0};
  return generation.fetch_add(1,std::memory_order_relaxed)+1;
}
template<class T> struct FrameOwnerHint {
  uint64_t generation=0;
  const std::shared_ptr<T>* owner=nullptr;
  size_t slot=kNoFrameSlot;
};
template<class T> class FrameRef {
 public:
  FrameRef() = default;
  template<class U> FrameRef(const std::shared_ptr<U>& p) : owned_(p) {}
  template<class U> FrameRef& operator=(const std::shared_ptr<U>& p) {
    owned_ = p; borrowed_ = nullptr; raw_or_slot_ = 0; return *this;
  }
  T* get() const { return borrowed_ ? borrowed_->get() : raw_or_slot_ ? reinterpret_cast<T*>(raw_or_slot_) : owned_.get(); }
  T* operator->() const { return get(); }
  T& operator*() const { return *get(); }
  explicit operator bool() const { return get() != nullptr; }
  const std::shared_ptr<T>& Owner() const { return borrowed_ ? *borrowed_ : owned_; }
  size_t Slot() const { return borrowed_ ? size_t(raw_or_slot_) : kNoFrameSlot; }
  void Borrow(const std::shared_ptr<T>& owner,size_t slot=kNoFrameSlot) {
    owned_.reset(); borrowed_ = &owner; raw_or_slot_ = slot;
  }
  void BorrowRaw(T* p) { owned_.reset(); borrowed_ = nullptr; raw_or_slot_ = reinterpret_cast<uintptr_t>(p); }
 private:
  std::shared_ptr<T> owned_;
  const std::shared_ptr<T>* borrowed_ = nullptr;
  // A borrowed owner and a raw slab pointer are mutually exclusive. Reuse
  // this word for the owner ordinal without growing every Draw/Attribute.
  uintptr_t raw_or_slot_ = 0;
};

template<class T> class FrameOwners {
 public:
  FrameOwners() = default;
  FrameOwners(const FrameOwners&) = delete;
  FrameOwners& operator=(const FrameOwners&) = delete;
  FrameRef<T> Capture(const std::shared_ptr<T>& owner,FrameOwnerHint<T>* hint=nullptr) {
    FrameRef<T> ref;
    if (!owner) return ref;
    // Never dereference a stale hint until its unique table generation matches.
    if (hint && hint->generation==generation_ && hint->owner && hint->owner->get()==owner.get()) {
      ++hint_hits;
      ref.Borrow(*hint->owner,hint->slot); return ref;
    }
    ++lookups;
    auto [it, added] = index_.try_emplace(owner.get(), owners_.size());
    if (added) owners_.push_back(owner);
    const size_t slot=it->second;
    ref.Borrow(owners_[slot],slot);
    if (hint) *hint={generation_,&owners_[slot],slot};
    return ref;
  }
  void Pin(FrameRef<T>& ref) {
    if (ref.Owner()) ref=Capture(ref.Owner());
  }
  void Clear() { owners_.clear(); index_.clear(); generation_=NextOwnerGeneration(); hint_hits=lookups=0; }
  size_t size() const { return owners_.size(); }
  uint64_t hint_hits=0,lookups=0;
 private:
  std::deque<std::shared_ptr<T>> owners_; // references survive insertion
  std::unordered_map<const T*, size_t> index_;
  uint64_t generation_=NextOwnerGeneration();
};

template<class T, size_t PerBlock = 64, size_t MaxItems = 4096>
class FrameBlocks {
 public:
  T* Next() {
    if (used_ == MaxItems) return nullptr;
    const size_t b = used_ / PerBlock;
    if (b == blocks_.size()) blocks_.emplace_back(new T[PerBlock]);
    return &blocks_[b][used_++ % PerBlock];
  }
  void Reset() { used_ = 0; }
  size_t bytes() const { return blocks_.size() * PerBlock * sizeof(T); }
  size_t used() const { return used_; }
 private:
  std::vector<std::unique_ptr<T[]>> blocks_;
  size_t used_ = 0;
};

// Only acquisition/release is locked. No per-draw locks. An epoch change drops
// idle storage; a checked-out frame keeps its storage until its last owner dies.
template<class T, size_t Limit = 3> class FrameStoragePool {
 public:
  void Purge(unsigned epoch) {
    std::lock_guard lock(mutex_);
    if (epoch_ != epoch) { live_ -= free_.size(); free_.clear(); epoch_ = epoch; }
  }
  std::shared_ptr<T> Take(unsigned epoch) {
    std::lock_guard lock(mutex_);
    if (epoch_ != epoch) { live_ -= free_.size(); free_.clear(); epoch_ = epoch; }
    std::unique_ptr<T> item;
    if (!free_.empty()) { item = std::move(free_.back()); free_.pop_back(); }
    else if (live_ < Limit) { item = std::make_unique<T>(); ++live_; }
    else return {};
    return std::shared_ptr<T>(item.release(), [this, epoch](T* p) {
      p->Reset();
      std::unique_ptr<T> returned(p);
      std::lock_guard lock(mutex_);
      if (epoch == epoch_) free_.push_back(std::move(returned));
      else --live_;
    });
  }
 private:
  std::mutex mutex_;
  std::vector<std::unique_ptr<T>> free_;
  size_t live_ = 0;
  unsigned epoch_ = 0;
};
} // namespace nfsmw
