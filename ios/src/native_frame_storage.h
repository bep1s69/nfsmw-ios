// CPU-side ownership only. Borrowed draw handles never outlive their frame.
#pragma once
#include <array>
#include <algorithm>
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

// Identity lookup only: keys never own or dereference the payload. Clearing
// retains the contiguous allocation, not any shared owners from the frame.
template<class T> class FrameOwnerIndex {
 public:
  size_t FindOrInsert(const T* key, size_t ordinal) {
    if (slots_.empty()) Grow(64);
    size_t at=Hash(key)&(slots_.size()-1);
    while (slots_[at].key) {
      if (slots_[at].key==key) return slots_[at].ordinal;
      at=(at+1)&(slots_.size()-1);
    }
    if (used_>=slots_.size()/2) {
      Grow(slots_.size()*2);
      at=Hash(key)&(slots_.size()-1);
      while (slots_[at].key) at=(at+1)&(slots_.size()-1);
    }
    slots_[at]={key,ordinal}; ++used_;
    return ordinal;
  }
  void Clear() { std::fill(slots_.begin(),slots_.end(),Slot{}); used_=0; }
  size_t bytes() const { return slots_.capacity()*sizeof(Slot); }
 private:
  struct Slot { const T* key=nullptr; size_t ordinal=0; };
  // Mix the whole pointer: decoded arrays have aligned, often adjacent
  // addresses. The lookup must not cluster on their zero alignment bits.
  static size_t Hash(const T* key) {
    uint64_t x=reinterpret_cast<uintptr_t>(key);
    x^=x>>30; x*=0xbf58476d1ce4e5b9ULL;
    x^=x>>27; x*=0x94d049bb133111ebULL;
    return size_t(x^(x>>31));
  }
  void Grow(size_t count) {
    std::vector<Slot> next(count);
    for (const auto& slot:slots_) if (slot.key) {
      size_t at=Hash(slot.key)&(count-1);
      while (next[at].key) at=(at+1)&(count-1);
      next[at]=slot;
    }
    slots_.swap(next);
  }
  std::vector<Slot> slots_;
  size_t used_=0;
};

template<class T> class FrameOwners {
 public:
  explicit FrameOwners(bool reusable_index=false) : reusable_index_(reusable_index) {}
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
    size_t slot;
    if (reusable_index_) slot=flat_index_.FindOrInsert(owner.get(),owners_.size());
    else slot=index_.try_emplace(owner.get(),owners_.size()).first->second;
    if (slot==owners_.size()) owners_.push_back(owner);
    ref.Borrow(owners_[slot],slot);
    if (hint) *hint={generation_,&owners_[slot],slot};
    return ref;
  }
  void Pin(FrameRef<T>& ref) {
    if (ref.Owner()) ref=Capture(ref.Owner());
  }
  void Clear() {
    owners_.clear();
    if (reusable_index_) flat_index_.Clear(); else index_.clear();
    generation_=NextOwnerGeneration(); hint_hits=lookups=0;
  }
  size_t size() const { return owners_.size(); }
  size_t flat_index_bytes() const { return flat_index_.bytes(); }
  uint64_t hint_hits=0,lookups=0;
 private:
  std::deque<std::shared_ptr<T>> owners_; // references survive insertion
  std::unordered_map<const T*, size_t> index_;
  FrameOwnerIndex<T> flat_index_;
  const bool reusable_index_;
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
