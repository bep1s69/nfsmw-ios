#!/usr/bin/env python3
"""Validate extracted target-reference lookup against the original map operation.

Targets here are CPU stand-ins with mutable fields and resource ownership. This
checks lookup identity/lifetime, not Metal rendering. --benchmark runs alternating
host trials with the real launch-switch path; timings are not device energy.
"""
import argparse
import pathlib
import re
import statistics
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = r'''
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <map>
#include <memory>
#include <random>
#include <string>
#include <string_view>
#include <vector>
bool g_enabled;
#define REXCVAR_GET(name) g_enabled
struct Target {
  uint32_t pitch=0,height=0,format=0,draws=0;
  bool used=false,clear_color=false;
  std::shared_ptr<int> color;
};
@PRODUCTION@
size_t checks=0;
Target& Check(std::map<std::string,Target>& map,TargetLookupCache& cache,const std::string& key,bool enabled) {
  const bool existed=map.contains(key);const auto count=map.size();
  auto& got=cache.Find(map,key,enabled);
  assert(map.size()==count+!existed);
  assert(map.contains(key) && &got==&map.at(key));
  ++checks;return got;
}
void Edges() {
  const bool enabled=TargetLookupEnabled();std::map<std::string,Target> map;
  TargetLookupCache cache;
  const std::vector<std::string> keys={"", "000_960_0_d5e4_s1", "000_960_0_d5e4_s2", "001_960_0_d5e4_s1",
    "000_961_0_d5e4_s1", "000_960_1_d5e4_s1", "000_960_0_d5e5_s1", "000_960_0_d5e4_s1+001",
    std::string("abc\0x",5),std::string("abc\0y",5),std::string(150,'x'),std::string(149,'x')+'y'};
  for(const auto& key:keys) {
    auto* ptr=&Check(map,cache,key,enabled);
    assert(&Check(map,cache,std::string(key),enabled)==ptr);
    std::string temporary=key;Check(map,cache,temporary,enabled);temporary.assign(300,'z');
    assert(&Check(map,cache,key,enabled)==ptr);
    // Insert many unrelated entries: tree rotations must not stale pointers.
    for(unsigned i=0;i<300;++i)map["insert_"+std::to_string(i)].height=i;
    assert(&Check(map,cache,key,enabled)==ptr);
    auto resource=std::make_shared<int>(42);std::weak_ptr<int> weak=resource;
    ptr->color=resource;resource.reset();assert(!weak.expired());
    ptr->pitch=1440;ptr->height=1080;ptr->format=2;ptr->used=true;
    auto& live=Check(map,cache,key,enabled);
    assert(live.pitch==1440 && live.height==1080 && live.format==2 && live.used && live.color && *live.color==42);
    // Resize/rebind in place, as the renderer does. Cache owns no resource copy.
    *ptr=Target{};assert(weak.expired());ptr->pitch=960;ptr->color=std::make_shared<int>(17);
    assert(&Check(map,cache,key,enabled)==ptr && Check(map,cache,key,enabled).pitch==960);
  }
  // Primary and MRT operations may alias, and resolve-like writes are live.
  TargetLookupCache setup,draw;
  auto& primary=Check(map,setup,keys[1],enabled);primary.draws=10;
  auto& secondary=map[keys[1]];secondary.draws+=3;
  assert(Check(map,draw,keys[1],enabled).draws==13);
  map[keys[1]].clear_color=true;
  assert(Check(map,draw,keys[1],enabled).clear_color);
  assert(&Check(map,setup,keys[2],enabled)!=&primary);
  // New frame/traversal gets a new cache, including when a map is replaced.
  {TargetLookupCache next;Check(map,next,keys[1],enabled);}
  map.clear();
  {TargetLookupCache next;assert(Check(map,next,keys[1],enabled).draws==0);}
  std::puts("PASS exact full strings (including empty/NUL/long), temporary keys, map insertion, live resize/rebind, resource ownership, MRT aliases and traversal reset");
}
void Randomized() {
  const bool enabled=TargetLookupEnabled();std::mt19937 rng(0x54415247);
  std::map<std::string,Target> map,reference;
  for(unsigned frame=0;frame<2000;++frame) {
    // The previous traversal's caches have already been destroyed.
    if(frame%37==0){map.clear();reference.clear();}
    TargetLookupCache setup,draw;
    std::vector<std::string> keys;
    for(unsigned i=0;i<120;++i)keys.push_back("target_"+std::to_string((i/8+frame)%31));
    if(frame%3==0)std::shuffle(keys.begin(),keys.end(),rng);
    for(const auto& key:keys) {
      auto& got=Check(map,setup,key,enabled);auto& expected=reference[key];
      ++got.draws;++expected.draws;got.pitch=expected.pitch=rng()%2048;
      // Additional MRT map insertion between cached primary references.
      if(rng()%5==0){map["mrt_"+key].format=3;reference["mrt_"+key].format=3;}
    }
    for(const auto& key:keys) {
      auto& got=Check(map,draw,key,enabled);auto& expected=reference[key];
      assert(got.draws==expected.draws && got.pitch==expected.pitch && got.format==expected.format);
      got.clear_color=expected.clear_color=(rng()%7==0);
      if(rng()%11==0) {map[key].height=1024;reference[key].height=1024;}
      assert(Check(map,draw,key,enabled).height==reference[key].height);
    }
    assert(map.size()==reference.size());auto a=map.begin();auto b=reference.begin();
    for(;a!=map.end();++a,++b)assert(a->first==b->first && a->second.draws==b->second.draws &&
      a->second.pitch==b->second.pitch && a->second.height==b->second.height &&
      a->second.format==b->second.format && a->second.clear_color==b->second.clear_color);
  }
  std::printf("PASS 2000 frames of two traversals, mutations, interleaved MRT inserts and frame-boundary reset; %zu checks\n",checks);
}
template<bool Helper>
__attribute__((noinline)) uint64_t Timed(std::map<std::string,Target>& map,const std::vector<std::string>& keys) {
  const bool enabled=TargetLookupEnabled();uint64_t checksum=0;
  for(unsigned frame=0;frame<1000;++frame)for(unsigned pass=0;pass<2;++pass) {
    TargetLookupCache cache;
    for(const auto& key:keys) {
      Target& t=Helper?cache.Find(map,key,enabled):map[key];
      checksum+=t.pitch;++t.draws;
    }
  }
  return checksum;
}
void Benchmark(bool original,std::string_view layout) {
  const unsigned count=layout=="many-targets"?256:12;
  const unsigned run=layout=="one-target"?2400:layout=="short-runs"?4:
                     layout=="alternating" || layout=="many-targets"?1:50;
  std::vector<std::string> names,keys;
  std::map<std::string,Target> map;
  for(unsigned i=0;i<count;++i){auto name="000_960_0_d"+std::to_string(100+i)+"_s1";
    if(layout=="long-keys")name+=std::string(120,'x');
    names.push_back(name);map[name].pitch=960+i;}
  for(unsigned i=0;i<2400;++i)keys.push_back(names[(i/run)%count]);
  if(original)Timed<false>(map,keys);else Timed<true>(map,keys);
  const auto start=std::chrono::steady_clock::now();
  const auto checksum=original?Timed<false>(map,keys):Timed<true>(map,keys);
  const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
  uint64_t draws=0;for(const auto& [key,t]:map)draws+=t.draws;
  std::printf("HOST %s: %.3f ms; checksum %llu; draws %llu; entries %zu\n",layout.data(),ms,
    (unsigned long long)checksum,(unsigned long long)draws,map.size());
}
int main(int argc,char** argv) {
  g_enabled=argc>1 && std::string_view(argv[1])=="on";
  if(argc>2){Benchmark(std::string_view(argv[1])=="original",argv[2]);return 0;}
  Edges();Randomized();
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    source = (ROOT / 'ios/src/native_renderer.mm').read_text()
    begin = source.index('struct TargetLookupCache {')
    end = source.index('// Depth resolves:', begin)
    helper = source[begin:end]
    # Guard the two intended integration sites and independent cache lifetime.
    for snippet in [
        'const bool reuse_target_lookup = TargetLookupEnabled();',
        'TargetLookupCache setup_target_lookup;\n    for (const Draw& d : frame->draws)',
        'Target& t = setup_target_lookup.Find(targets, key, reuse_target_lookup);',
        'TargetLookupCache draw_target_lookup;\n    for (size_t position = 0;',
        'Target& t = draw_target_lookup.Find(targets, tk, reuse_target_lookup);',
        'Target* t1 = d.second_target ? &targets[tk1] : nullptr;',
    ]:
        assert snippet in source, snippet
    with tempfile.TemporaryDirectory(prefix='nfsmw-target-lookup-') as temp:
        path = pathlib.Path(temp)
        cpp, exe = path / 'test.cpp', path / 'test'
        cpp.write_text(HARNESS.replace('@PRODUCTION@', helper))
        for options in [['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'], ['-O3']]:
            subprocess.run(['xcrun', 'clang++', '-std=c++20', *options, str(cpp), '-o', str(exe)], check=True)
            for arm in ['off', 'on']:
                print(f'CHECK {options[0]} {arm}', flush=True)
                subprocess.run([str(exe), arm], check=True)
        if args.benchmark:
            for layout in ['one-target', 'runs', 'short-runs', 'alternating', 'many-targets', 'long-keys']:
                times = {arm: [] for arm in ['original', 'off', 'on']}
                identity = None
                for trial in range(7):
                    order = ['original', 'off', 'on'] if trial % 2 == 0 else ['on', 'off', 'original']
                    for arm in order:
                        output = subprocess.check_output([str(exe), arm, layout], text=True)
                        print(f'TRIAL {trial} {arm} {output}', end='', flush=True)
                        m = re.search(r': ([\d.]+) ms; checksum (\d+); draws (\d+); entries (\d+)', output)
                        assert m, output
                        got = m.group(2, 3, 4)
                        if identity is None:
                            identity = got
                        assert got == identity, (layout, arm, got, identity)
                        times[arm].append(float(m[1]))
                print(f'MEDIAN {layout}: ' + ', '.join(f'{a} {statistics.median(v):.3f} ms' for a, v in times.items()) +
                      f'; matching checksum/draws/entries {identity}', flush=True)


if __name__ == '__main__':
    main()
