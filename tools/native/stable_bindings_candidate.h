// Parked G2 candidate: complete preparation cost gate failed.
// Host tests only; not connected to the game renderer.
// Only post-validation Attribute collection is reusable. Each original owner
// Capture must have completed before Add; no validation outcome is cached.
#pragma once
#include "native_frame_storage.h"
#include <array>
#include <new>
#include <deque>
#include <memory_resource>
#include <span>
#include <vector>

namespace nfsmw {
template<class Attribute,size_t Limit=512> class StableBindings {
 public:
  struct Bundle {
    std::pmr::vector<Attribute> attributes;
    std::array<uint8_t,32> locations;
    bool indexed=true;
    explicit Bundle(std::pmr::memory_resource* resource):attributes(resource){locations.fill(255);}
    void Index(){
      for(size_t i=0;i<attributes.size();++i){
        if(attributes[i].location>=locations.size()){indexed=false;return;}
        locations[attributes[i].location]=uint8_t(i); // same LAST matching location
      }
    }
    const Attribute* Find(uint32_t location)const{
      if(indexed && location<locations.size()){
        auto at=locations[location];return at==255?nullptr:&attributes[at];
      }
      const Attribute* found=nullptr;
      for(const auto& a:attributes)if(a.location==location)found=&a;
      return found;
    }
  };
  struct Hint {
    uint64_t generation=0,blocked_generation=0;
    const Bundle* bundle=nullptr;
  };
  explicit StableBindings(std::pmr::memory_resource* resource=std::pmr::get_default_resource()):bundles_(resource){}
  StableBindings(const StableBindings&)=delete;
  StableBindings& operator=(const StableBindings&)=delete;
  // Opaque prepared-slot address is only a selector, never validation. Slot
  // reuse can at worst force full per-attribute mismatch/fallback below.
  Hint* Select(const void* key){
    if(!key)return nullptr;
    uint64_t hash=uintptr_t(key);hash^=hash>>30;hash*=0xbf58476d1ce4e5b9ULL;hash^=hash>>27;
    for(size_t i=0;i<8;++i){auto& slot=index_[(hash+i)&(index_.size()-1)];
      if(slot.key==key)return &slot.hint;
      if(!slot.key){slot.key=key;return &slot.hint;}
    }
    ++capacity;return nullptr;
  }
  uint64_t hits=0,builds=0,changes=0,bypasses=0,capacity=0,allocation_fallbacks=0;
  size_t size() const{return bundles_.size();}
  class Collect {
   public:
    Collect(const Collect&)=delete;
    Collect& operator=(const Collect&)=delete;
    Collect(StableBindings* cache,Hint* hint,std::pmr::vector<Attribute>& out,
            size_t expected,bool stable):cache_(cache),hint_(hint),out_(out),expected_(expected){
      if(!cache_ || !hint_ || !stable || expected<6 || expected>16 ||
         hint_->blocked_generation==cache_->generation_){
        if(cache_)++cache_->bypasses;cache_=nullptr;return;
      }
      // A stale hint may point into a dead frame. Check unique epoch first.
      if(hint_->generation==cache_->generation_ && hint_->bundle){
        if(hint_->bundle->attributes.size()==expected)prior_=hint_->bundle;
        else{++cache_->changes;Block();}
      }
    }
    bool Reusing() const{return prior_!=nullptr;}
    const Bundle* PublishedBundle()const{return published_;}
    void Add(Attribute&& a,bool stable){
      if(!cache_){out_.push_back(std::move(a));return;}
      if(!stable || a.fresh){Fallback();out_.push_back(std::move(a));return;}
      if(prior_){
        if(seen_<prior_->attributes.size()){
          const auto& old=prior_->attributes[seen_];
          if(old.location==a.location && old.integer==a.integer && !old.fresh &&
             old.values.get()==a.values.get()){
            ++seen_;return; // both versions already retained by THIS frame
          }
        }
        Fallback();out_.push_back(std::move(a));return;
      }
      out_.push_back(std::move(a));++seen_;
    }
    std::span<const Attribute> Finish(){
      if(!cache_)return out_;
      if(seen_!=expected_){Fallback();return out_;}
      if(prior_){++cache_->hits;published_=prior_;return prior_->attributes;}
      if(cache_->bundles_.size()==Limit){++cache_->capacity;Block();return out_;}
      // Moving is delayed until deque allocation succeeds. Allocation failure
      // must leave the complete original draw list available as fallback.
      try{cache_->bundles_.emplace_back(out_.get_allocator().resource());}
      catch(const std::bad_alloc&){++cache_->allocation_fallbacks;Block();return out_;}
      auto& bundle=cache_->bundles_.back();
      bundle.attributes.swap(out_); // equal allocators; no allocations/throw after ownership transfer
      bundle.Index();published_=&bundle;
      ++cache_->builds;
      *hint_={cache_->generation_,0,&bundle};return bundle.attributes;
    }
   private:
    void Block(){hint_->blocked_generation=cache_->generation_;cache_=nullptr;prior_=nullptr;}
    void Fallback(){
      if(prior_){
        out_.reserve(expected_);
        for(size_t i=0;i<seen_;++i)out_.push_back(prior_->attributes[i]);
      }
      ++cache_->changes;Block();
    }
    StableBindings* cache_;
    Hint* hint_;
    std::pmr::vector<Attribute>& out_;
    const Bundle* prior_=nullptr;
    const Bundle* published_=nullptr;
    size_t expected_,seen_=0;
  };
 private:
  struct Index {const void* key=nullptr;Hint hint;};
  std::array<Index,512> index_{};
  const uint64_t generation_=NextOwnerGeneration();
  std::pmr::deque<Bundle> bundles_;
};
} // namespace nfsmw
