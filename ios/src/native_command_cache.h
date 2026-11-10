// ObjC++ Metal command storage. All mutation is on the serial render queue;
// only completion changes busy. No resource is replaced while busy on GPU.
#pragma once
#import <Metal/Metal.h>
#include "native_command_key.h"
#include <algorithm>
#include <atomic>
#include <bit>
#include <cstring>
#include <unordered_map>
#include <vector>

namespace nfsmw::commands {
constexpr size_t kMaxDraws = 8192, kPushStride = 256;
constexpr size_t kPinBudget = 96 * 1024 * 1024, kMaxHeap = 2 * 1024 * 1024;
struct Stats {
  uint64_t hits=0, builds=0, submitted=0, runs=0, singles=0, budget=0;
};
struct Context {
  std::atomic<bool> busy{false};
  id<MTLIndirectCommandBuffer> icb = nil;
  id<MTLBuffer> push = nil, heaps[5] = {};
  struct Entry { NativeCommandKey key; bool valid=false, used=false; };
  struct Pin { id<MTLBuffer> buffer; size_t refs; };
  std::vector<Entry> entries;
  std::unordered_map<uintptr_t, Pin> pins;
  size_t pin_bytes=0;
  unsigned epoch=0;
  Stats stats;

  void Clear() {
    icb=nil; entries.clear(); pins.clear(); pin_bytes=0;
    push=nil;
    for(auto& h:heaps) h=nil;
  }
  void Unpin(uintptr_t p) {
    if (!p) return;
    auto it=pins.find(p);
    if (--it->second.refs==0) { pin_bytes-=it->second.buffer.length; pins.erase(it); }
  }
  void Reset(size_t i) {
    auto& e=entries[i];
    if (!e.valid) return;
    [[icb indirectRenderCommandAtIndex:i] reset];
    for(auto p:e.key.buffers) Unpin(p);
    Unpin(e.key.index_buffer);
    e.valid=false;
  }
  void ResetCommands() { for(size_t i=0;i<entries.size();++i) Reset(i); }
  void FinishFrame() {
    // Non-eligible/direct slots must not pin abandoned geometry indefinitely.
    // Flush runs first. These entries are absent from this frame's ICB uses.
    for(size_t i=0;i<entries.size();++i) if (!entries[i].used) Reset(i);
  }
  bool Begin(id<MTLDevice> device, size_t count, unsigned current_epoch) {
    stats={};
    if (epoch!=current_epoch) { Clear(); epoch=current_epoch; }
    if (!count || count>kMaxDraws) return false;
    if (entries.size()<count) {
      size_t capacity=std::bit_ceil(std::max(count,size_t(256)));
      MTLIndirectCommandBufferDescriptor* d=[MTLIndirectCommandBufferDescriptor new];
      d.commandTypes=MTLIndirectCommandTypeDrawIndexed;
      d.inheritBuffers=NO; d.inheritPipelineState=YES;
      d.maxVertexBufferBindCount=31; d.maxFragmentBufferBindCount=9;
      id<MTLIndirectCommandBuffer> next=[device newIndirectCommandBufferWithDescriptor:d
                              maxCommandCount:capacity options:MTLResourceStorageModeShared];
      id<MTLBuffer> next_push=[device newBufferWithLength:capacity*kPushStride options:MTLResourceStorageModeShared];
      if (!next || !next_push) return false;
      Clear(); icb=next; push=next_push; entries.resize(capacity);
    }
    for(size_t i=count;i<entries.size();++i) Reset(i);
    for(size_t i=0;i<count;++i) entries[i].used=false;
    return true;
  }
  id<MTLBuffer> Heap(id<MTLDevice> device, size_t n, size_t bytes) {
    if (bytes>kMaxHeap) return nil;
    if (heaps[n].length<bytes) {
      id<MTLBuffer> next=[device newBufferWithLength:std::bit_ceil(std::max(bytes,size_t(256)))
                                            options:MTLResourceStorageModeShared];
      if (!next) return nil;
      ResetCommands(); heaps[n]=next;
    }
    std::memset(heaps[n].contents,0,heaps[n].length);
    return heaps[n];
  }
  bool Store(size_t i, const NativeCommandKey& key) {
    auto& e=entries[i];
    if (e.valid && e.key==key) { e.used=true; ++stats.hits; return true; }
    // Check budget before mutating the old entry. Buffer arguments are held
    // strongly by the caller until this method pins them.
    size_t added=0;
    std::array<uintptr_t,32> unique{};
    size_t n=0;
    auto check=[&](uintptr_t p) {
      if (!p || pins.count(p) || std::find(unique.begin(),unique.begin()+n,p)!=unique.begin()+n) return;
      unique[n++]=p;
      added+=[(__bridge id<MTLBuffer>)(void*)p length];
    };
    for(auto p:key.buffers) check(p);
    check(key.index_buffer);
    if (pin_bytes+added>kPinBudget) { ++stats.budget; return false; }
    Reset(i);
    auto pin=[&](uintptr_t p) {
      if (!p) return;
      auto [it,inserted]=pins.try_emplace(p,Pin{(__bridge id<MTLBuffer>)(void*)p,0});
      if (inserted) pin_bytes+=it->second.buffer.length;
      ++it->second.refs;
    };
    for(auto p:key.buffers) pin(p);
    pin(key.index_buffer);
    id<MTLIndirectRenderCommand> cmd=[icb indirectRenderCommandAtIndex:i];
    for(size_t b=0;b<key.buffers.size();++b) if (key.buffers[b]) {
      id<MTLBuffer> buffer=(__bridge id<MTLBuffer>)(void*)key.buffers[b];
      [cmd setVertexBuffer:buffer offset:key.offsets[b] atIndex:b];
      if (b<5 || b==8) [cmd setFragmentBuffer:buffer offset:key.offsets[b] atIndex:b];
    }
    [cmd drawIndexedPrimitives:MTLPrimitiveType(key.primitive) indexCount:key.count indexType:MTLIndexTypeUInt32
             indexBuffer:(__bridge id<MTLBuffer>)(void*)key.index_buffer indexBufferOffset:key.index_offset
             instanceCount:1 baseVertex:0 baseInstance:0];
    e.key=key; e.valid=true; e.used=true; ++stats.builds;
    return true;
  }
};

struct Lease {
  Lease() = default;
  Lease(const Lease&) = delete;
  Lease& operator=(const Lease&) = delete;
  Context* context=nullptr;
  bool submitted=false;
  ~Lease() { if (context && !submitted) context->busy.store(false,std::memory_order_release); }
};
inline std::array<Context,3>& Pool() {
  static auto* contexts=new std::array<Context,3>;
  return *contexts;
}
inline void PurgeIdle(unsigned epoch) {
  for(auto& c:Pool()) {
    bool idle=false;
    if (!c.busy.compare_exchange_strong(idle,true,std::memory_order_acquire)) continue;
    if (c.epoch!=epoch) { c.Clear(); c.epoch=epoch; }
    c.busy.store(false,std::memory_order_release);
  }
}
inline Context* Acquire(id<MTLDevice> device,size_t count,unsigned epoch) {
  // Process lifetime; callbacks can outlive normal static teardown.
  for(auto& c:Pool()) {
    bool idle=false;
    if (!c.busy.compare_exchange_strong(idle,true,std::memory_order_acquire)) continue;
    if (c.Begin(device,count,epoch)) return &c;
    c.busy.store(false,std::memory_order_release);
  }
  return nullptr;
}

// Encoder-local pointer set without per-resource node allocations. Context
// pins, not this set, own resources. Zero is never a valid resource address.
class ResourceDeclarations {
 public:
  void Clear() { std::fill(slots_.begin(),slots_.end(),0); used_=0; }
  bool Insert(uintptr_t p) {
    if (!p) return false;
    if (slots_.empty()) Grow();
    size_t at=Find(p);
    if (slots_[at]==p) return false;
    if (used_*2>=slots_.size()) { Grow(); at=Find(p); }
    slots_[at]=p; ++used_; return true;
  }
 private:
  size_t Find(uintptr_t p) const {
    uintptr_t h=p>>4;
    h^=h>>17; h*=uintptr_t(0x9E3779B97F4A7C15ull); h^=h>>32;
    size_t at=h&(slots_.size()-1);
    while(slots_[at] && slots_[at]!=p) at=(at+1)&(slots_.size()-1);
    return at;
  }
  void Grow() {
    auto old=std::move(slots_);
    slots_.assign(old.empty() ? 64 : old.size()*2,0);
    for(auto p:old) if(p) slots_[Find(p)]=p;
  }
  std::vector<uintptr_t> slots_;
  size_t used_=0;
};

// The caller flushes BEFORE each inherited-state mutation, resolve or direct
// draw. Own buffer bindings mean parent buffer updates cannot change this run.
struct Batch {
  Context* context=nullptr;
  id<MTLRenderCommandEncoder> encoder=nil;
  CommandRun run;
  std::vector<__unsafe_unretained id<MTLResource>> resources;
  bool incremental_resources=true;
  // Keep the last encoder alive so a later encoder cannot reuse its address
  // and inherit the old declaration set. Context pins still own all buffers
  // until GPU completion; this changes no resource ownership.
  id<MTLRenderCommandEncoder> residency_encoder=nil;
  ResourceDeclarations declared;
  std::array<uintptr_t,32> last_resource{};
  uint64_t resource_calls=0, resource_entries=0;
  bool Flush() {
    if (!run.count) return false;
    resources.clear();
    if (incremental_resources) {
      if (residency_encoder!=encoder) {
        residency_encoder=encoder;
        declared.Clear(); last_resource.fill(0);
      }
      auto add=[&](uintptr_t p) {
        if (declared.Insert(p))
          resources.push_back((__bridge id<MTLResource>)(void*)p);
      };
      add(reinterpret_cast<uintptr_t>((__bridge void*)context->icb));
      for(size_t i=run.first;i<run.first+run.count;++i) {
        const auto& key=context->entries[i].key;
        for(size_t b=0;b<key.buffers.size();++b) {
          const auto p=key.buffers[b];
          // Common descriptor heaps/push storage usually stay in the same
          // slots: skip even the set lookup when the binding is unchanged.
          if (p!=last_resource[b]) { add(p); last_resource[b]=p; }
        }
        if (key.index_buffer!=last_resource[31]) {
          add(key.index_buffer); last_resource[31]=key.index_buffer;
        }
      }
    } else {
      resources.push_back(context->icb);
      for(size_t i=run.first;i<run.first+run.count;++i) {
        const auto& key=context->entries[i].key;
        for(auto p:key.buffers) if(p) resources.push_back((__bridge id<MTLResource>)(void*)p);
        resources.push_back((__bridge id<MTLResource>)(void*)key.index_buffer);
      }
      std::sort(resources.begin(),resources.end(),[](id a,id b){return reinterpret_cast<uintptr_t>((__bridge void*)a)<reinterpret_cast<uintptr_t>((__bridge void*)b);});
      resources.erase(std::unique(resources.begin(),resources.end()),resources.end());
    }
    if (!resources.empty()) {
      [encoder useResources:resources.data() count:resources.size() usage:MTLResourceUsageRead
                     stages:MTLRenderStageVertex|MTLRenderStageFragment];
      ++resource_calls; resource_entries+=resources.size();
    }
    if (run.count == 1) {
      const auto& key=context->entries[run.first].key;
      for(size_t b=0;b<key.buffers.size();++b) if(key.buffers[b]) {
        id<MTLBuffer> buffer=(__bridge id<MTLBuffer>)(void*)key.buffers[b];
        [encoder setVertexBuffer:buffer offset:key.offsets[b] atIndex:b];
        if (b<5 || b==8) [encoder setFragmentBuffer:buffer offset:key.offsets[b] atIndex:b];
      }
      [encoder drawIndexedPrimitives:MTLPrimitiveType(key.primitive) indexCount:key.count
             indexType:MTLIndexTypeUInt32 indexBuffer:(__bridge id<MTLBuffer>)(void*)key.index_buffer
             indexBufferOffset:key.index_offset];
      ++context->stats.singles;
    } else {
      [encoder executeCommandsInBuffer:context->icb withRange:NSMakeRange(run.first,run.count)];
      context->stats.submitted+=run.count; ++context->stats.runs;
    }
    run.Clear(); encoder=nil;
    return true;
  }
  void Add(size_t slot,id<MTLRenderCommandEncoder> enc) {
    if (run.count && (encoder!=enc || !run.Adjacent(slot))) Flush();
    encoder=enc; run.Add(slot);
  }
};
} // namespace nfsmw::commands
