#!/usr/bin/env python3
"""Check the renderer's extracted attribute lookup, pointer lifetime and sweep.

Runs all lookup/comparison switch combinations under ASan/UBSan. --benchmark
also times several host hit/miss layouts; these are not device energy tests.
"""
import argparse
import pathlib
import re
import statistics
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

HARNESS = r'''
#include <cassert>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <memory>
#include <random>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <vector>
using FloatArray = std::vector<float>;
bool g_lookup_enabled,g_bulk_enabled;
bool Flag(std::string_view name) {
  if(name=="nfsmw_native_attribute_lookup")return g_lookup_enabled;
  assert(name=="nfsmw_native_attribute_bulk_compare");return g_bulk_enabled;
}
#define REXCVAR_GET(name) Flag(#name)
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
  // Every bit in the complete object participates. All members are unsigned
  // integers and the production representation assertions exclude padding.
  for(size_t byte=0;byte<sizeof(AttributeKey);++byte)for(unsigned bit=0;bit<8;++bit) {
    auto changed=key;
    reinterpret_cast<unsigned char*>(&changed)[byte]^=static_cast<unsigned char>(1u<<bit);
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
  std::puts("PASS all nine identity fields, all 320 key bits, forced two-way collisions, map fallback and rehash");
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
void Benchmark(std::string_view layout) {
  ClearAll();std::vector<AttributeKey> keys;
  const unsigned count=layout=="small-hit"?512:layout=="large-miss"?16384:
                       layout=="same-set" || layout=="early-miss"?32:4096;
  for(unsigned i=0;i<count;++i) {
    auto k=Key(i);
    if(layout=="same-set" || layout=="early-miss") {
      k=Key(0);k.format=i;
      if(layout=="early-miss") { k.base+=i%16;k.format=i/16; }
      assert(AttributeLookupCache::SetIndex(k)==AttributeLookupCache::SetIndex(Key(0)));
    }
    keys.push_back(k);Check(keys.back());
  }
  volatile uint64_t checksum=0;
  const unsigned frames=3686400/(3*count);
  const auto start=std::chrono::steady_clock::now();
  for(unsigned frame=0;frame<frames;++frame) {
    frame_counter=frame;
    for(unsigned pass=0;pass<3;++pass)for(const auto& k:keys) {
      auto& e=AttributeEntryFor(k,diagnostics);
      e.last_used=frame;checksum=checksum+e.last_used;
    }
  }
  const double ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
  std::printf("HOST FIXTURE %s %s: %.2f ms for %u lookups; checksum %llu; hits/misses/bypasses %llu/%llu/%llu\n",
    layout.data(),g_bulk_enabled?"bulk":"scalar",ms,frames*3*count,(unsigned long long)checksum,
    (unsigned long long)diagnostics.attribute_lookup_hits,(unsigned long long)diagnostics.attribute_lookup_misses,(unsigned long long)diagnostics.attribute_lookup_bypasses);
}
int main(int argc,char** argv) {
  g_lookup_enabled=argc>1 && std::string(argv[1])=="on";
  g_bulk_enabled=argc>2 && std::string(argv[2])=="on";
  if(argc>3){Benchmark(argv[3]);return 0;}
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
            for bulk in ['off', 'on']:
                print(f'CHECK lookup {arm}, bulk {bulk}', flush=True)
                subprocess.run([str(exe), arm, bulk], check=True)
        if args.benchmark:
            subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O3', str(cpp), '-o', str(exe)], check=True)
            # Also run correctness in the actual optimized configuration.
            for arm in ['off', 'on']:
                for bulk in ['off', 'on']:
                    subprocess.run([str(exe), arm, bulk], check=True)
            for layout in ['small-hit', 'mixed', 'large-miss', 'same-set', 'early-miss']:
                times = {'off': [], 'on': []}
                expected = None
                for trial in range(7):
                    for bulk in (['off', 'on'] if trial % 2 == 0 else ['on', 'off']):
                        output = subprocess.check_output([str(exe), 'on', bulk, layout], text=True)
                        print(f'TRIAL {trial} {output}', end='', flush=True)
                        match = re.search(r': ([\d.]+) ms.*checksum (\d+); hits/misses/bypasses (\d+/\d+/\d+)', output)
                        assert match, output
                        identity = match.group(2, 3)
                        if expected is None:
                            expected = identity
                        assert identity == expected, (layout, identity, expected)
                        times[bulk].append(float(match[1]))
                print(f'MEDIAN {layout}: scalar {statistics.median(times["off"]):.2f} ms, '
                      f'bulk {statistics.median(times["on"]):.2f} ms; matching checksum/counters {expected}', flush=True)


if __name__ == '__main__':
    main()
