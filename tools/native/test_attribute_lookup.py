#!/usr/bin/env python3
"""Check the renderer's extracted attribute lookup, pointer lifetime and sweep.

Runs both launch-switch arms under ASan/UBSan. --benchmark also times a fixed
host workload; this is not a device performance or energy measurement.
"""
import argparse
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

HARNESS = r'''
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <memory>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>
using FloatArray = std::vector<float>;
bool g_lookup_enabled;
#define REXCVAR_GET(name) g_lookup_enabled
uint64_t frame_counter = 0;
struct VertexDiagnostics {
  uint64_t attribute_lookup_hits=0, attribute_lookup_misses=0, attribute_lookup_bypasses=0;
};
@PRODUCTION@
VertexDiagnostics diagnostics;
AttributeKey Key(unsigned i) {
  return {uintptr_t(0x7000000000ull + uint64_t(i/4)*4096), 8, i%4*2, 6, 2, 0,
          i%31, 128+i%7, 0};
}
CacheEntry<FloatArray>& Check(const AttributeKey& key) {
  auto& got=AttributeEntryFor(key,diagnostics);
  auto it=attribute_cache.find(key);
  assert(it!=attribute_cache.end() && &got==&it->second);
  // Cache entries are mutable, including on a front-cache hit.
  got.last_used=frame_counter;
  got.last_changed^=uint64_t(key.count);
  assert(it->second.last_changed==got.last_changed);
  return got;
}
void ClearAll() {
  attribute_lookup.Clear();
  attribute_cache.clear();
  diagnostics={};
}
void IdentityAndCollisionChecks() {
  ClearAll();
  auto key=Key(0);
  auto* first=&Check(key);
  assert(&Check(key)==first);
  // Exercise every key field, including low address bits omitted by the
  // cheap selector. Identical selectors must never imply identical entries.
  for(int field=0;field<9;++field) {
    auto changed=key;
    switch(field) {
      case 0:++changed.base;break;
      case 1:++changed.stride;break;
      case 2:++changed.offset;break;
      case 3:++changed.format;break;
      case 4:++changed.endian;break;
      case 5:++changed.integer;break;
      case 6:++changed.lo;break;
      case 7:++changed.count;break;
      case 8:++changed.remap;break;
    }
    assert(!(changed==key));
    assert(&Check(changed)!=first);
    assert(&Check(key)==first);
  }
  std::vector<AttributeKey> colliding;
  const size_t set=AttributeLookupCache::SetIndex(key);
  for(uint32_t format=0;format<40;++format) {
    auto k=key;k.format=format;
    assert(AttributeLookupCache::SetIndex(k)==set);
    colliding.push_back(k);
  }
  for(unsigned i=0;i<2000;++i)Check(colliding[(i*17)%colliding.size()]);
  // unordered_map rehash must preserve all pointers retained by the front.
  Check(key);auto* before=&attribute_cache.find(key)->second;
  const size_t buckets=attribute_cache.bucket_count();
  attribute_cache.reserve(buckets*8+40000);
  assert(attribute_cache.bucket_count()>buckets);
  assert(&Check(key)==before);
  std::puts("PASS all nine identity fields, forced two-way collisions, map fallback and rehash");
}
void MutationChecks() {
  ClearAll();auto key=Key(9);
  uint8_t bytes[64]={};
  auto& entry=Check(key);
  auto value=std::make_shared<FloatArray>(4,1.0f);
  entry.value=value;entry.fingerprint=Fingerprint(bytes,sizeof(bytes));
  auto* address=&entry;
  // The lookup must return the live entry, allowing the caller to reject
  // rewritten guest bytes even when the key and frame have not changed.
  bytes[0]=73;
  auto& changed=Check(key);
  assert(&changed==address && changed.fingerprint!=Fingerprint(bytes,sizeof(bytes)));
  changed.value=std::make_shared<FloatArray>(4,2.0f);
  changed.fingerprint=Fingerprint(bytes,sizeof(bytes));
  changed.watched=true;changed.dynamic=true;changed.last_false_alarm=77;
  auto& again=Check(key);
  assert(again.value!=value && again.fingerprint==Fingerprint(bytes,sizeof(bytes)));
  assert(again.watched && again.dynamic && again.last_false_alarm==77);
  assert(value->at(0)==1.0f); // independent ownership remains valid
  std::puts("PASS same-frame source mutation and live cache-entry metadata/payload updates");
}
void SweepChecks() {
  ClearAll();frame_counter=0;
  const auto old=Key(1),recent=Key(2);
  auto& obsolete=Check(old);
  obsolete.value=std::make_shared<FloatArray>(4,9.0f);
  auto retained=obsolete.value;
  std::weak_ptr<FloatArray> weak=retained;
  auto& alive=Check(recent);alive.last_used=750;
  auto* survivor=&alive;
  frame_counter=767;SweepAttributeCache();
  assert(attribute_cache.size()==2); // not a sweep boundary
  frame_counter=768;SweepAttributeCache();
  assert(attribute_cache.size()==1 && attribute_cache.find(old)==attribute_cache.end());
  assert(attribute_cache.find(recent)!=attribute_cache.end());
  auto misses=diagnostics.attribute_lookup_misses;
  assert(&Check(recent)==survivor);
  if(g_lookup_enabled)assert(diagnostics.attribute_lookup_misses==misses+1);
  assert(!weak.expired() && retained->at(0)==9.0f);
  // Reallocate an evicted key and exercise it, catching stale slot pointers
  // under ASan even if the allocator doesn't reuse the erased map node.
  auto& replacement=Check(old);
  assert(!replacement.value && replacement.fingerprint==0);
  replacement.value=std::make_shared<FloatArray>(4,3.0f);
  assert(Check(old).value->at(0)==3.0f);
  retained.reset();assert(weak.expired());
  std::puts("PASS production sweep invalidation, surviving nodes, erased/reinserted entries and retained ownership");
}
void RandomizedChecks() {
  ClearAll();std::mt19937 rng(20017);
  std::vector<AttributeKey> keys;
  for(unsigned i=0;i<12000;++i)keys.push_back(Key(i));
  for(unsigned i=0;i<90000;++i) {
    frame_counter=1024+i/64;
    if(i%64==0)SweepAttributeCache();
    auto k=keys[rng()%keys.size()];
    if(i%7==0)k.remap=rng()%8;
    if(i%11==0)k.endian=rng()%4;
    auto& e=Check(k);
    if(!e.value)e.value=std::make_shared<FloatArray>(4,float(i));
    e.fingerprint=i;
    assert(Check(k).fingerprint==i);
  }
  if(g_lookup_enabled)assert(diagnostics.attribute_lookup_hits>0 && diagnostics.attribute_lookup_misses>0 && diagnostics.attribute_lookup_bypasses==0);
  else assert(diagnostics.attribute_lookup_bypasses==180000 && diagnostics.attribute_lookup_hits==0 && diagnostics.attribute_lookup_misses==0);
  std::printf("PASS 90000 changing-key accesses with immediate reuse, insertions and periodic sweeps; hits/misses/bypasses %llu/%llu/%llu\n",
    (unsigned long long)diagnostics.attribute_lookup_hits,(unsigned long long)diagnostics.attribute_lookup_misses,(unsigned long long)diagnostics.attribute_lookup_bypasses);
}
void Benchmark() {
  ClearAll();std::vector<AttributeKey> keys;
  for(unsigned i=0;i<4096;++i){keys.push_back(Key(i));Check(keys.back());}
  volatile uint64_t checksum=0;
  const auto start=std::chrono::steady_clock::now();
  for(unsigned frame=0;frame<300;++frame) {
    frame_counter=frame;
    for(unsigned pass=0;pass<3;++pass)for(const auto& k:keys) {
      auto& e=AttributeEntryFor(k,diagnostics);
      e.last_used=frame;checksum=checksum+e.last_used;
    }
  }
  const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
  std::printf("HOST FIXTURE %s: %.2f ms for 3686400 lookups; checksum %llu; hits/misses/bypasses %llu/%llu/%llu\n",
    g_lookup_enabled?"on":"off",ms,(unsigned long long)checksum,
    (unsigned long long)diagnostics.attribute_lookup_hits,(unsigned long long)diagnostics.attribute_lookup_misses,(unsigned long long)diagnostics.attribute_lookup_bypasses);
}
int main(int argc,char** argv) {
  g_lookup_enabled=argc>1 && std::string(argv[1])=="on";
  if(argc>2){Benchmark();return 0;}
  IdentityAndCollisionChecks();MutationChecks();SweepChecks();RandomizedChecks();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    source = (ROOT / 'ios/src/native_renderer.mm').read_text()
    entries = source[source.index('uint64_t Fingerprint('):source.index('// Guest memory write watch:')]
    sweep = source[source.index('template <typename Map>\nvoid Sweep('):source.index('std::unordered_map<FetchKey, CacheEntry<Texture>')]
    lookup = source[source.index('struct AttributeKey {'):source.index("// A draw's indices as the renderer draws them")]
    with tempfile.TemporaryDirectory(prefix='nfsmw-attribute-lookup-') as temp:
        path = pathlib.Path(temp)
        cpp, exe = path / 'test.cpp', path / 'test'
        cpp.write_text(HARNESS.replace('@PRODUCTION@', entries + sweep + lookup))
        subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O1', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(cpp), '-o', str(exe)], check=True)
        for arm in ['off', 'on']:
            subprocess.run([str(exe), arm], check=True)
        if args.benchmark:
            subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O3', str(cpp), '-o', str(exe)], check=True)
            for arm in ['off', 'on']:
                subprocess.run([str(exe), arm, 'benchmark'], check=True)


if __name__ == '__main__':
    main()
