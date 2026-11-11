#!/usr/bin/env python3
"""Differential ownership/lifetime and allocation checks on the production index."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#include "native_frame_storage.h"
#include <cassert>
#include <cstdlib>
#include <cstdio>
#include <new>
#include <random>
#include <chrono>
static bool count_allocations=false;
static size_t allocations=0;
void* operator new(size_t bytes) {
  if(count_allocations) ++allocations;
  if(void* p=std::malloc(bytes ? bytes : 1)) return p;
  throw std::bad_alloc();
}
void* operator new[](size_t bytes) {return ::operator new(bytes);}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,size_t) noexcept {std::free(p);}
void operator delete[](void* p,size_t) noexcept {std::free(p);}
using Owners=nfsmw::FrameOwners<const int>;
static size_t hash_pointer(uintptr_t x) {
  x^=x>>30; x*=0xbf58476d1ce4e5b9ULL;
  x^=x>>27; x*=0x94d049bb133111ebULL;
  return x^(x>>31);
}
static void Collisions() {
  nfsmw::FrameOwnerIndex<const int> index;
  std::vector<const int*> keys;
  // Deliberately force the same initial bucket across all growth to1024slots.
  // These opaque test identities are never dereferenced by the index.
  for(uintptr_t x=16;keys.size()<400;x+=16)
    if((hash_pointer(x)&1023)==0) keys.push_back(reinterpret_cast<const int*>(x));
  for(int round=0;round<3;++round) {
    for(size_t i=0;i<keys.size();++i) assert(index.FindOrInsert(keys[i],i)==i);
    for(size_t i=0;i<keys.size();++i) assert(index.FindOrInsert(keys[i],99999)==i);
    size_t bytes=index.bytes();index.Clear();assert(index.bytes()==bytes);
  }
}
static void Differential() {
  Owners reference(false),flat(true),other(true);
  std::vector<std::shared_ptr<const int>> cache;
  std::vector<nfsmw::FrameOwnerHint<const int>> a(128),b(128);
  for(int i=0;i<128;++i)cache.push_back(std::make_shared<const int>(i));
  std::mt19937 rng(121);
  for(int frame=0;frame<80;++frame) {
    std::vector<nfsmw::FrameRef<const int>> saved;
    std::vector<std::shared_ptr<const int>> expected;
    for(int i=0;i<4000;++i) {
      size_t k=rng()%cache.size();
      if(i%17==0)cache[k]=std::make_shared<const int>(i);
      auto x=reference.Capture(cache[k],&a[k]),y=flat.Capture(cache[k],&b[k]);
      assert(x.get()==y.get() && x.Slot()==y.Slot() && *x==*y);
      saved.push_back(y);expected.push_back(cache[k]);
      if(i%11==0) { // another frame/table invalidates this cache entry's hint
        auto z=other.Capture(cache[k],&b[k]);assert(z.get()==cache[k].get());
      }
    }
    for(size_t i=0;i<saved.size();++i)assert(saved[i].get()==expected[i].get());
    assert(reference.size()==flat.size());
    // Hints for the flat arm were shared with 'other', so counters may differ.
    assert(!flat.Capture({}) && !reference.Capture({}));
    reference.Clear();flat.Clear();other.Clear();
    for(auto& hint:b)hint.owner=reinterpret_cast<const std::shared_ptr<const int>*>(uintptr_t(1));
    assert(flat.size()==0 && flat.lookups==0 && flat.hint_hits==0);
  }
}
static void Lifetimes() {
  Owners owners(true);nfsmw::FrameOwnerHint<const int> hint;
  auto value=std::make_shared<const int>(7);std::weak_ptr<const int> weak=value;
  auto first=owners.Capture(value,&hint);auto copy=first;
  for(int i=0;i<12000;++i)owners.Capture(std::make_shared<const int>(i));
  value.reset();assert(*copy==7 && !weak.expired());
  owners.Clear();assert(weak.expired()); // flat table must not keep owners alive
  hint.owner=reinterpret_cast<const std::shared_ptr<const int>*>(uintptr_t(1));
  value=std::make_shared<const int>(8);assert(*owners.Capture(value,&hint)==8);
  alignas(Owners) unsigned char table_bytes[sizeof(Owners)];
  auto* table=new(table_bytes) Owners(true);table->Capture(value,&hint);
  auto generation=hint.generation;table->~Owners();
  table=new(table_bytes) Owners(true);assert(*table->Capture(value,&hint)==8);
  assert(hint.generation!=generation);table->~Owners();
  // Reuse precisely the same payload address after Clear (new shared control block).
  alignas(int) unsigned char payload[sizeof(int)];
  auto make=[&](int n) {auto* p=new(payload) int(n);return std::shared_ptr<const int>(p,[](const int*){});};
  auto old=make(19);owners.Capture(old,&hint);old.reset();owners.Clear();
  auto replacement=make(20);auto ref=owners.Capture(replacement,&hint);
  assert(*ref==20 && ref.Slot()==0);
}
struct Storage {
  Owners owners{true};
  void Reset(){owners.Clear();}
};
static void Pool() {
  nfsmw::FrameStoragePool<Storage,2> pool;
  auto a=pool.Take(0),b=pool.Take(0);assert(a&&b&&!pool.Take(0));
  auto value=std::make_shared<const int>(91);std::weak_ptr<const int> weak=value;
  auto ref=a->owners.Capture(value);value.reset();
  b.reset();pool.Purge(1);assert(*ref==91 && !weak.expired());
  b=pool.Take(1);assert(b&&!pool.Take(1));
  a.reset();assert(weak.expired()); // checked-out old epoch releases and is discarded
  assert(pool.Take(1));
  auto p=b.get();b.reset();b=pool.Take(1);assert(b.get()==p&&b->owners.size()==0);
}
static size_t Count(bool flat,bool report=true,double* elapsed=nullptr) {
  Owners owners(flat);
  std::vector<std::shared_ptr<const int>> cache;
  for(int i=0;i<4096;++i)cache.push_back(std::make_shared<const int>(i));
  for(auto& p:cache)owners.Capture(p);owners.Clear(); // grow/warm both arms
  size_t bytes=owners.flat_index_bytes();allocations=0;count_allocations=true;
  auto begin=std::chrono::steady_clock::now();
  for(int frame=0;frame<30;++frame) {
    for(size_t i=0;i<cache.size();++i) {
      auto ref=owners.Capture(cache[i]);assert(ref.Slot()==i);
      auto duplicate=owners.Capture(cache[i]);assert(duplicate.Slot()==i);
    }
    owners.Clear();
  }
  count_allocations=false;
  if(elapsed)*elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
  if(flat)assert(owners.flat_index_bytes()==bytes);
  if(report)std::printf("%s: %zu heap allocations across 30 warmed 4096-owner frames; %zu retained flat-index bytes\n",
              flat?"reusable":"reference",allocations,bytes);
  return allocations;
}
int main(int argc,char**) {
  static_assert(sizeof(nfsmw::FrameRef<const int>)==32);
  Collisions();Differential();Lifetimes();Pool();
  auto reference=Count(false),flat=Count(true);assert(flat*10<reference);
  if(argc>1) {
    std::vector<double> a,b;
    for(int i=0;i<7;++i) {
      double x,y;
      if(i%2) {Count(true,false,&y);Count(false,false,&x);}
      else {Count(false,false,&x);Count(true,false,&y);}
      a.push_back(x);b.push_back(y);
    }
    std::sort(a.begin(),a.end());std::sort(b.begin(),b.end());
    std::printf("Host only, seven alternating-order trials: reference median %.3f ms, reusable median %.3f ms (not device CPU/energy)\n",a[3],b[3]);
  }
}
'''
benchmark='--benchmark' in sys.argv
with tempfile.TemporaryDirectory(prefix='nfsmw-owner-index-') as tmp:
    path, exe = Path(tmp)/'test.cpp', Path(tmp)/'test'
    path.write_text(CODE)
    options=['-O2'] if benchmark else ['-O1','-g','-fsanitize=address,undefined']
    subprocess.run(['clang++','-std=c++20',*options,
                    '-fno-omit-frame-pointer','-I',str(ROOT/'ios/src'),str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe),*(['benchmark'] if benchmark else [])],check=True)

source=(ROOT/'ios/src/native_renderer.mm').read_text()
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_owner_index, true,' in source
for role in ['constant_owners','attributes','indices']:
    assert role+'{NativeOwnerIndex()}' in source
# Keep ownership index independent of GPU encoding, geometry and validation.
baseline=subprocess.check_output(['git','show','1f925f3:ios/src/native_renderer.mm'],cwd=ROOT,text=True)
start='void Record(Frame& frame, const NfsmwNativeDraw& in) {'
end='// --- Drawing a recorded frame with Metal'
assert source[source.index(start):source.index(end)]==baseline[baseline.index(start):baseline.index(end)]
start='    TargetLookupCache draw_target_lookup;';end='    // Resolves after the last draw'
assert source[source.index(start):source.index(end)]==baseline[baseline.index(start):baseline.index(end)]
print('PASS collisions/growth/reset, differential ordinals/data, stale hints/address reuse, immediate release/pool epochs, warmed allocations and unchanged Record/draw loop')
