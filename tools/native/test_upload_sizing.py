#!/usr/bin/env python3
"""Compare extracted upload sizing with the original source under host ARC.

Uses production Draw/Attribute layouts and both current switch arms. Tests
exact budgets, traversal counts, input preservation and aligned upload bounds.
--benchmark measures synthetic host frames, not device rendering or energy.
"""
import argparse
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILE = 'ios/src/native_renderer.mm'
REFERENCE = '03da344'


def structure(source, name):
    start = source.index('struct ' + name + ' {')
    return source[start:source.index('\n};', start) + 3]


def sizing(source):
    start = source.index('    struct UploadedConstants {')
    return source[start:source.index('    // Every byte read from it', start)]


HARNESS = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <memory>
#include <memory_resource>
#include <random>
#include <string_view>
#include <vector>
using FloatArray = std::vector<float>;
@TYPES@
struct Frame { std::vector<Draw> draws; };
struct CountedDraws {
 const std::vector<Draw>& values;
 mutable size_t starts=0,visits=0;
 struct Iterator {
  std::vector<Draw>::const_iterator it;
  size_t* visits;
  const Draw& operator*() const { return *it; }
  Iterator& operator++() { ++it;++*visits;return *this; }
  bool operator!=(const Iterator& b) const { return it!=b.it; }
 };
 Iterator begin() const { ++starts;return {values.begin(),&visits}; }
 Iterator end() const { return {values.end(),&visits}; }
};
struct CountedFrame { CountedDraws draws; };
template<class F> __attribute__((noinline)) size_t Reference(const F* frame,bool) {
 @REFERENCE@
 return total;
}
template<class F> __attribute__((noinline)) size_t Candidate(const F* frame,bool fused_upload_sizing) {
 @CURRENT@
 return total;
}
// Independent worst-case upload simulation: every shared-data set changes,
// and all fresh arrays are consumed. Real encoding may skip some of them.
size_t UploadBound(const Frame& f) {
 size_t used=0;
 auto put=[&](size_t bytes) { used=((used+255)&~size_t(255))+bytes; };
 struct Stage { const void* bank=nullptr;uint16_t first=0,end=0; } stages[3];
 auto stage=[&](int k,const void* bank,std::pair<uint16_t,uint16_t> range) {
  if(range.first>=range.second)return;
  auto& last=stages[k];
  if(bank==last.bank && last.first<=range.first && last.end>=range.second)return;
  put(size_t(range.second-range.first)*16);
  last={bank,range.first,range.second};
 };
 for(const auto& d:f.draws) {
  stage(0,d.vs_constants.get(),d.vs_range);
  stage(1,d.ps_constants.get(),d.ps_range);
  if(d.previous_vs_constants)stage(2,d.previous_vs_constants.get(),d.vs_range);
  put(1024);
  for(const auto& a:d.attributes)if(a.fresh && a.values)put(a.values->size()*4);
  if(d.indices_fresh)put(d.index_count()*4);
 }
 return used;
}
// Exact relevant input representation, including values and identity of the
// shared arrays; no uninitialized render-state padding is inspected.
std::vector<uint64_t> Describe(const Frame& f) {
 std::vector<uint64_t> out;
 for(const auto& d:f.draws) {
  out.insert(out.end(),{uintptr_t(d.vs_constants.get()),uintptr_t(d.ps_constants.get()),
   uintptr_t(d.previous_vs_constants.get()),d.vs_range.first,d.vs_range.second,
   d.ps_range.first,d.ps_range.second,uintptr_t(d.indices.get()),d.indices_fresh});
  if(d.indices)for(auto i:*d.indices)out.push_back(i);
  for(const auto& a:d.attributes) {
   out.insert(out.end(),{a.location,a.integer,a.fresh,uintptr_t(a.values.get())});
   if(a.values)for(auto x:*a.values)out.push_back(uint64_t(x));
  }
 }
 return out;
}
size_t checks=0;
size_t Check(const Frame& f) {
 auto before=Describe(f);size_t expected=Reference(&f,false);
 assert(Candidate(&f,false)==expected && Candidate(&f,true)==expected);
 assert(UploadBound(f)<=expected && std::max<size_t>(expected,256)>=UploadBound(f));
 for(bool fused:{false,true}) {
  CountedFrame c{{f.draws}};
  assert(Candidate(&c,fused)==expected);
  assert(c.draws.starts==(fused?1u:2u));
  assert(c.draws.visits==f.draws.size()*(fused?1u:2u));
 }
 assert(Describe(f)==before);++checks;return expected;
}
Draw& Add(Frame& f) { return f.draws.emplace_back(std::pmr::get_default_resource()); }
void Edges() {
 Frame empty;assert(Check(empty)==0);
 auto a=std::make_shared<ConstantBank>(),b=std::make_shared<ConstantBank>();
 auto array=std::make_shared<FloatArray>(17,3.f);
 for(bool fresh:{false,true})for(bool indices:{false,true})for(bool previous:{false,true}) {
  Frame f;auto& d=Add(f);d.vs_constants=a;d.ps_constants=b;
  d.vs_range={1,3};d.ps_range={8,9};if(previous)d.previous_vs_constants=a;
  d.indices_fresh=fresh;
  if(indices)d.indices=std::make_shared<const std::vector<uint32_t>>(std::initializer_list<uint32_t>{0,1,2});
  d.attributes.push_back({0,false,array,fresh});
  d.attributes.push_back({1,false,nullptr,true});
  d.attributes.push_back({2,true,std::make_shared<FloatArray>(),true});
  size_t expected=288+272+1280+256+(previous?288:0)+(fresh?256+(indices?12:0)+68+256:0);
  assert(Check(f)==expected);
 }
 Frame ranges;
 for(auto r:{std::pair<uint16_t,uint16_t>{0,256},{4,8},{8,8},{200,4},{0,256},{0,257},{256,257},{0,0}}) {
  auto& d=Add(ranges);d.vs_constants=a;d.ps_constants=a;d.previous_vs_constants=a;
  d.vs_range=r;d.ps_range=r;d.indices_fresh=false;
 }
 assert(Check(ranges)==3*(4096+256)+3*(4112+256)+8*1280);
 Frame nulls;Add(nulls);Check(nulls);
}
std::mt19937 rng(0x4e46534d);
std::vector<std::shared_ptr<ConstantBank>> banks;
std::vector<std::shared_ptr<FloatArray>> arrays;
std::vector<std::shared_ptr<const std::vector<uint32_t>>> indices;
void Pools() {
 for(int i=0;i<32;++i)banks.push_back(std::make_shared<ConstantBank>());
 for(size_t size:{0u,1u,4u,16u,64u,256u,1024u})arrays.push_back(std::make_shared<FloatArray>(size,2.f));
 for(size_t size:{0u,1u,3u,127u,1024u})indices.push_back(std::make_shared<const std::vector<uint32_t>>(size,7));
}
Frame Generate(size_t count,unsigned fresh_percent,bool edges) {
 Frame f;f.draws.reserve(count);
 for(size_t i=0;i<count;++i) {
  auto& d=Add(f);d.vs_constants=banks[(i/8)%banks.size()];d.ps_constants=banks[(i/5)%banks.size()];
  d.vs_range={0,64};d.ps_range={4,32};
  if(rng()%4==0)d.previous_vs_constants=banks[rng()%banks.size()];
  if(edges) {
   d.vs_range={uint16_t(rng()%258),uint16_t(rng()%258)};
   d.ps_range={uint16_t(rng()%258),uint16_t(rng()%258)};
   if(rng()%8==0)d.vs_constants.reset();
   if(rng()%8==0)d.ps_constants.reset();
  }
  if(rng()%8)d.indices=indices[rng()%indices.size()];
  d.indices_fresh=rng()%100<fresh_percent;
  size_t n=edges?rng()%17:8;
  for(size_t j=0;j<n;++j)d.attributes.push_back({uint32_t(j),bool(rng()%2),rng()%8?arrays[rng()%arrays.size()]:nullptr,rng()%100<fresh_percent});
 }
 return f;
}
void Benchmark() {
 volatile size_t checksum=0;
 for(unsigned fresh:{0u,20u,100u}) {
  auto f=Generate(2700,fresh,false);Check(f);
  for(unsigned i=0;i<64;++i) {
   asm volatile("" : : "r"(&f) : "memory");
   checksum=checksum+Reference(&f,false)+Candidate(&f,false)+Candidate(&f,true);
  }
  for(unsigned trial=0;trial<7;++trial) {
   double times[3]{};
   for(unsigned o=0;o<3;++o) {
    unsigned arm=(o+trial)%3;constexpr unsigned loops=2000;
    auto start=std::chrono::steady_clock::now();
    for(unsigned i=0;i<loops;++i) {
     asm volatile("" : : "r"(&f) : "memory");
     size_t n=arm==0?Reference(&f,false):Candidate(&f,arm==2);
     checksum=checksum+n;
    }
    times[arm]=std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-start).count()/loops;
   }
   std::printf("BENCH 2700 draws fresh %u%% trial %u original %.0f ns, current OFF %.0f ns, fused ON %.0f ns\n",fresh,trial,times[0],times[1],times[2]);
  }
 }
 std::printf("checksum %zu\n",size_t(checksum));
}
int main(int argc,char**) {
 @autoreleasepool {
  Edges();Pools();for(unsigned i=0;i<2000;++i)Check(Generate(rng()%129,rng()%101,true));
  std::printf("PASS %zu frames: original/current OFF/fused budgets, traversal counts, input preservation, aligned upload bounds; sizeof(Draw)=%zu\n",checks,sizeof(Draw));
  if(argc>1)Benchmark();
 }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    source = (ROOT / FILE).read_text()
    original = subprocess.check_output(['git', 'show', f'{REFERENCE}:{FILE}'], cwd=ROOT, text=True)
    types = '\n'.join(structure(source, name) for name in ['Attribute', 'ConstantBank', 'Draw'])
    harness = HARNESS.replace('@TYPES@', types).replace('@REFERENCE@', sizing(original)).replace('@CURRENT@', sizing(source))
    with tempfile.TemporaryDirectory(prefix='nfsmw-upload-sizing-') as temp:
        temp = pathlib.Path(temp)
        path = temp / 'test.mm'
        path.write_text(harness)
        exe = temp / 'test'
        flags = ['-O3'] if args.benchmark else ['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        subprocess.run(['xcrun', 'clang++', '-std=c++23', '-fobjc-arc', *flags, str(path), '-framework', 'Foundation', '-framework', 'Metal', '-o', str(exe)], check=True)
        subprocess.run([str(exe)] + (['benchmark'] if args.benchmark else []), check=True)


if __name__ == '__main__':
    main()
