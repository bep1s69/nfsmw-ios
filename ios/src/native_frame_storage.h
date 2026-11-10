// CPU-side ownership only. Borrowed draw handles never outlive their frame.
#pragma once
#include <array>
#include <deque>
#include <memory>
#include <mutex>
#include <unordered_map>
#include <vector>

namespace nfsmw {
template<class T> class FrameRef {
 public:
  FrameRef() = default;
  template<class U> FrameRef(const std::shared_ptr<U>& p) : owned_(p) {}
  template<class U> FrameRef& operator=(const std::shared_ptr<U>& p) {
    owned_ = p; borrowed_ = nullptr; raw_ = nullptr; return *this;
  }
  T* get() const { return raw_ ? raw_ : Owner().get(); }
  T* operator->() const { return get(); }
  T& operator*() const { return *get(); }
  explicit operator bool() const { return get() != nullptr; }
  const std::shared_ptr<T>& Owner() const { return borrowed_ ? *borrowed_ : owned_; }
  void Borrow(const std::shared_ptr<T>& owner) { owned_.reset(); raw_ = nullptr; borrowed_ = &owner; }
  void BorrowRaw(T* p) { owned_.reset(); borrowed_ = nullptr; raw_ = p; }
 private:
  std::shared_ptr<T> owned_;
  const std::shared_ptr<T>* borrowed_ = nullptr;
  T* raw_ = nullptr;
};

template<class T> class FrameOwners {
 public:
  void Pin(FrameRef<T>& ref) {
    if (!ref) return;
    auto [it, added] = index_.try_emplace(ref.get(), owners_.size());
    if (added) owners_.push_back(ref.Owner());
    ref.Borrow(owners_[it->second]);
  }
  void Clear() { owners_.clear(); index_.clear(); }
  size_t size() const { return owners_.size(); }
 private:
  std::deque<std::shared_ptr<T>> owners_; // references survive insertion
  std::unordered_map<const T*, size_t> index_;
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
