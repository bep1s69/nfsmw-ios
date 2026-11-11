// Recording-thread-only metadata cache. No decoded data or GPU ownership.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace nfsmw {
template<class Key,class Description,size_t Sets=1024> class PreparedGeometryCache {
  static_assert(Sets && !(Sets&(Sets-1)));
  struct Slot {Key key;Description description;uint64_t generation=0;bool ready=false;};
  struct Set {Slot ways[2];unsigned replace=0;};
  std::array<Set,Sets> sets_;
  uint64_t generation_=1;
 public:
  template<class Matches> Description* Find(const Key& key,uint64_t hash,Matches&& matches) {
    auto& set=sets_[hash&(Sets-1)];
    for(unsigned i=0;i<2;++i) {
      auto& slot=set.ways[i];
      // Test generation BEFORE reading descriptions containing borrowed nodes.
      if(slot.generation==generation_ && slot.ready && slot.key==key && matches(slot.description)) {
        set.replace=i^1;return &slot.description;
      }
    }
    return nullptr;
  }
  // A one-off mesh takes the reference path. Prepare metadata only after the
  // same identity returns to this set; avoids rebuilding large cold records.
  bool Admit(const Key& key,uint64_t hash) {
    auto& set=sets_[hash&(Sets-1)];
    for(unsigned i=0;i<2;++i) {
      auto& slot=set.ways[i];
      if(slot.generation==generation_ && !slot.ready && slot.key==key) {
        set.replace=i;return true;
      }
    }
    auto& slot=set.ways[set.replace];slot.key=key;slot.ready=false;
    slot.generation=generation_;set.replace^=1;return false;
  }
  // Fill cannot fail: caller checks eligibility before replacement. Fill must
  // initialize every field the matcher/reader uses, including null node handles.
  template<class Fill> Description& Replace(const Key& key,uint64_t hash,Fill&& fill) {
    auto& set=sets_[hash&(Sets-1)];auto& slot=set.ways[set.replace];
    slot.generation=0;fill(slot.description);slot.key=key;
    slot.ready=true;slot.generation=generation_;set.replace^=1;return slot.description;
  }
  void Invalidate() {
    if(generation_==std::numeric_limits<uint64_t>::max()) {
      for(auto& set:sets_)for(auto& slot:set.ways)slot.generation=0;
      generation_=1;
    } else ++generation_;
  }
};
} // namespace nfsmw
