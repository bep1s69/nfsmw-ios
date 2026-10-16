#!/usr/bin/env python3
"""Exercise extracted GPU-buffer cache, upload and sweep code under host ARC.

Metal buffers/arena are host-memory fixtures; no GPU work is submitted.
--benchmark times the extracted front lookup with controlled pointer layouts,
not a replay of device addresses or a device performance/energy measurement.
"""
import argparse
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

HARNESS = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <memory>
#include <new>
#include <string_view>
#include <unordered_map>
#include <vector>
bool g_hash_enabled=false,g_stats_enabled=false;
bool Flag(std::string_view name) { return name=="nfsmw_native_gpu_lookup_hash" ? g_hash_enabled : g_stats_enabled; }
#define REXCVAR_GET(name) Flag(#name)
@interface HostBuffer : NSObject {
  std::vector<uint8_t> storage;
}
- (instancetype)initWithSize:(size_t)size;
- (void*)contents;
@end
@implementation HostBuffer
- (instancetype)initWithSize:(size_t)size { if((self=[super init])) storage.resize(size); return self; }
- (void*)contents { return storage.data(); }
@end
@GPU_BUFFER@
struct HostArena {
 struct Allocation { id<MTLBuffer> buffer; size_t size; bool live; };
 std::vector<Allocation> allocations;
 bool fail_next=false;
 size_t attempts=0,releases=0,trims=0;
 bool Allocate(id<MTLDevice>,size_t size,uint32_t& chunk,__strong id<MTLBuffer>& buffer,size_t& offset) {
  ++attempts;
  if(fail_next) { fail_next=false;return false; }
  chunk=uint32_t(allocations.size());offset=32;
  buffer=(id<MTLBuffer>)[[HostBuffer alloc] initWithSize:size+offset];
  allocations.push_back({buffer,size,true});return true;
 }
 void Release(uint32_t chunk,size_t offset,size_t size) {
  assert(chunk<allocations.size() && offset==32 && allocations[chunk].live && allocations[chunk].size==size);
  allocations[chunk].live=false;allocations[chunk].buffer=nil;++releases;
 }
 void Trim() { ++trims; }
} buffer_arena;
std::unordered_map<const void*,GpuBuffer> gpu_buffers;
uint64_t gpu_frame=1;
uint32_t gpu_submission_frame=1;
std::atomic<uint32_t> gpu_frames_done{0};
uint32_t frame_new_buffers=0;
uint64_t geometry_upload_arrays=0,geometry_upload_bytes=0;
@PRODUCTION@
GpuBuffer* FrontOnly(const void* pointer) {
 struct Pointer { const void* p;const void* get() const {return p;} }values{pointer};
 @FRONT@
 return slot.entry;
}
using Values=std::vector<float>;
void Reset() {
 for(auto& slot:gpu_buffer_slots)slot={};
 gpu_buffers.clear();buffer_arena={};gpu_buffer_lookup_stats={};
 gpu_frame=1;gpu_submission_frame=1;gpu_frames_done=0;
 frame_new_buffers=0;geometry_upload_arrays=geometry_upload_bytes=0;
}
void CheckCounts() {
 const auto& s=gpu_buffer_lookup_stats;
 assert(s.empty_misses+s.collisions==s.existing_entries+s.new_entries);
 if(!g_stats_enabled)assert(s.hits+s.empty_misses+s.collisions+s.existing_entries+s.new_entries==0);
}
id<MTLBuffer> Lookup(const std::shared_ptr<Values>& values) {
 size_t offset=999;
 auto buffer=GpuBufferFor(nil,values,offset);
 assert(buffer && offset==32);
 assert(std::memcmp(static_cast<uint8_t*>(buffer.contents)+offset,values->data(),values->size()*4)==0);
 assert(gpu_buffers.at(values.get()).keep.get()==values.get());
 assert(gpu_buffers.at(values.get()).last_used==gpu_frame);
 assert(gpu_buffers.at(values.get()).last_submission==gpu_submission_frame);
 CheckCounts();return buffer;
}
void SelectorChecks() {
 constexpr uintptr_t base=0x7000000000ull;
 std::array<bool,4096> seen{};
 for(unsigned i=0;i<4096;++i) {
  auto index=GpuBufferSlotIndex(reinterpret_cast<const void*>(base+i*16));
  assert(index<4096 && !seen[index]);seen[index]=true;
  if(!g_hash_enabled)assert(index==i);
 }
 for(unsigned i=0;i<64;++i)assert(GpuBufferSlotIndex(reinterpret_cast<const void*>(uint64_t(1)<<i))<4096);
 assert((GpuBufferSlotIndex(reinterpret_cast<const void*>(base))!=
         GpuBufferSlotIndex(reinterpret_cast<const void*>(base+65536)))==g_hash_enabled);
}
std::pair<std::shared_ptr<Values>,std::shared_ptr<Values>> Collision() {
 std::array<std::shared_ptr<Values>,4096> first{};
 for(unsigned i=0;i<=4096;++i) {
  auto value=std::make_shared<Values>(4,float(i+1));
  auto index=GpuBufferSlotIndex(value.get());
  if(first[index])return {first[index],value};
  first[index]=std::move(value);
 }
 std::abort();
}
void CollisionRehashAndSweep() {
 Reset();auto [a,b]=Collision();
 const auto* key_a=a.get();const auto* key_b=b.get();
 const auto slot=GpuBufferSlotIndex(key_a);assert(slot==GpuBufferSlotIndex(key_b));
 gpu_submission_frame=10;auto first=Lookup(a);
 assert(Lookup(a)==first && buffer_arena.attempts==1);
 auto* node_a=&gpu_buffers.at(key_a);
 gpu_submission_frame=11;Lookup(b);
 assert(Lookup(a)==first && &gpu_buffers.at(key_a)==node_a && buffer_arena.attempts==2);
 gpu_buffers.reserve(20000);
 assert(&gpu_buffers.at(key_a)==node_a && Lookup(a)==first);
 // Leave the colliding newer submission in the slot before erasing the older one.
 gpu_submission_frame=12;Lookup(b);
 auto survivor=std::make_shared<Values>(4,99.f);
 while(GpuBufferSlotIndex(survivor.get())==slot)survivor=std::make_shared<Values>(4,98.f);
 gpu_frame=600;gpu_submission_frame=20;auto survivor_buffer=Lookup(survivor);
 std::weak_ptr<Values> weak_a=a,weak_b=b;a.reset();b.reset();
 gpu_frame=640;gpu_frames_done=10;SweepGpu();
 assert(gpu_buffers.size()==3 && buffer_arena.releases==0 && !weak_a.expired() && !weak_b.expired());
 gpu_frames_done=11;SweepGpu();
 assert(gpu_buffers.size()==2 && buffer_arena.releases==1 && weak_a.expired() && !weak_b.expired());
 assert(gpu_buffer_slots[slot].key==key_b && gpu_buffer_slots[slot].entry==&gpu_buffers.at(key_b));
 gpu_frame=704;gpu_frames_done=12;SweepGpu();
 assert(gpu_buffers.size()==1 && buffer_arena.releases==2 && weak_b.expired());
 assert(gpu_buffer_slots[slot].key==nullptr && gpu_buffer_slots[slot].entry==nullptr);
 assert(Lookup(survivor)==survivor_buffer);
}
void RetryAndPointerReuse() {
 Reset();auto value=std::make_shared<Values>(4,7.f);
 buffer_arena.fail_next=true;size_t offset=99;
 assert(!GpuBufferFor(nil,value,offset) && offset==0 && gpu_buffers.size()==1);
 assert(!gpu_buffers.at(value.get()).keep && geometry_upload_arrays==0);
 Lookup(value);assert(buffer_arena.attempts==2 && geometry_upload_arrays==1);
 CheckCounts();
 Reset();
 alignas(Values) std::byte storage[sizeof(Values)];
 auto make=[&](float number) {
  auto* p=std::construct_at(reinterpret_cast<Values*>(storage),4,number);
  return std::shared_ptr<Values>(p,[](Values* q){std::destroy_at(q);});
 };
 auto old=make(1.f);const auto* old_key=old.get();std::weak_ptr<Values> weak=old;
 gpu_submission_frame=4;Lookup(old);old.reset();
 gpu_frame=640;gpu_frames_done=3;SweepGpu();assert(!weak.expired());
 gpu_frames_done=4;SweepGpu();assert(weak.expired() && gpu_buffers.empty());
 auto replacement=make(9.f);assert(replacement.get()==old_key);
 Lookup(replacement);assert(buffer_arena.attempts==2 && geometry_upload_arrays==2);
 // Clear the cached owner before this stack storage is destroyed.
 Reset();replacement.reset();
}
void Benchmark() {
 for(unsigned regions : {1u,4u,16u}) {
  Reset();std::vector<const void*> keys;
  const unsigned per_region=regions==16?256:1024;
  for(unsigned region=0;region<regions;++region)for(unsigned i=0;i<per_region;++i)
   keys.push_back(reinterpret_cast<const void*>(0x7000000000ull+uint64_t(region)*65536+i*48+16));
  for(auto key:keys)gpu_buffers.try_emplace(key);
  for(int warm=0;warm<4;++warm)for(auto key:keys)FrontOnly(key);
  for(int round=0;round<3;++round) {
   gpu_buffer_lookup_stats={};
   auto start=std::chrono::steady_clock::now();
   uintptr_t checksum=0;
   constexpr unsigned repeats=512;
   for(unsigned rep=0;rep<repeats;++rep)for(auto key:keys) {
    auto* entry=FrontOnly(key);checksum+=uintptr_t(entry);
    asm volatile(""::"r"(entry):"memory");
   }
   auto stop=std::chrono::steady_clock::now();size_t occupied=0;
   for(const auto& slot:gpu_buffer_slots)occupied+=slot.key!=nullptr;
   const auto& s=gpu_buffer_lookup_stats;const auto calls=uint64_t(repeats)*keys.size();
   std::printf("layout %u regions/%zu keys: %.2f ns/lookup, %zu occupied, %.2f%% hits (stats %s), checksum %zu\n",
      regions,keys.size(),std::chrono::duration<double,std::nano>(stop-start).count()/calls,
      occupied,100.*s.hits/calls,g_stats_enabled?"on":"off",size_t(checksum));
  }
 }
 Reset();
}
int main(int argc,char** argv) {
 g_hash_enabled=std::string_view(argv[1])=="on";g_stats_enabled=std::string_view(argv[2])=="on";
 @autoreleasepool {
  SelectorChecks();CollisionRehashAndSweep();RetryAndPointerReuse();Reset();
  std::printf("PASS actual GPU-buffer lookup/sweep, selector %s, counters %s: collisions, rehash, completion gates, invalidation, ownership, retries, same-address reuse\n",argv[1],argv[2]);
  if(argc>3)Benchmark();
 }
}
'''


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--benchmark',action='store_true')
    args=ap.parse_args()
    s=(ROOT/'ios/src/native_renderer.mm').read_text()
    a=s.index('struct GpuBuffer {');b=s.index('\n};',a)+3
    gpu_buffer=s[a:b]
    a=s.index('struct GpuBufferSlot {');b=s.index('// The on-screen layer',a)
    production=s[a:b]
    a=production.index('  GpuBufferSlot& slot =');b=production.index('  GpuBuffer& g = *slot.entry;',a)
    source=HARNESS.replace('@GPU_BUFFER@',gpu_buffer).replace('@PRODUCTION@',production).replace('@FRONT@',production[a:b])
    with tempfile.TemporaryDirectory(prefix='nfsmw-gpu-lookup-') as temp:
        temp=pathlib.Path(temp);path=temp/'test.mm';path.write_text(source);exe=temp/'test'
        flags=['-O3'] if args.benchmark else ['-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(['xcrun','clang++','-std=c++23','-fobjc-arc',*flags,str(path),'-framework','Foundation','-framework','Metal','-o',str(exe)],check=True)
        for mode in ('off','on'):
            for stats in (('on',) if args.benchmark else ('off','on')):
                subprocess.run([str(exe),mode,stats]+(['benchmark'] if args.benchmark else []),check=True)


if __name__=='__main__':
    main()
