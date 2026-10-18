#!/usr/bin/env python3
"""Differential-check the extracted ready lookup and actual Get/Finish methods.

Foundation stand-ins replace Metal compilation; original methods come from Git
8623510. --benchmark times ready hits/misses with the real launch-switch path.
This does not execute shaders or measure device energy.
"""
import argparse
import pathlib
import re
import statistics
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
REFERENCE = '8623510'


def method(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


HARNESS = r'''
#import <Foundation/Foundation.h>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <random>
#include <string>
#include <string_view>
#include <unordered_map>
#include <unordered_set>
#include <vector>
@protocol MTLRenderPipelineState @end
@protocol MTLDevice @end
@protocol MTLFunction @end
bool g_enabled;
#define REXCVAR_GET(name) g_enabled
#define REXLOG_WARN(...) ((void)0)
@KEY_AND_LOOKUP@
@interface FakePSO : NSObject<MTLRenderPipelineState> { @public uint64_t token; }
@end
@implementation FakePSO @end
@interface FixturePipelineDescriptor : NSObject { @public PipelineKey key; }
@end
@implementation FixturePipelineDescriptor @end
using ReadyMap=std::unordered_map<PipelineKey,id<MTLRenderPipelineState>,PipelineKeyHash>;
ReadyMap pool;
id<MTLRenderPipelineState> Pso(const PipelineKey& key) {
  auto& p=pool[key];if(!p){FakePSO* x=[FakePSO new];x->token=PipelineKeyHash{}(key);p=x;}return p;
}
FixturePipelineDescriptor* PipelineDescriptor(const PipelineKey& key,id<MTLFunction>,id<MTLFunction>) {
  if(key.motion==0xfefefefe)return nil;
  auto* d=[FixturePipelineDescriptor new];d->key=key;return d;
}
unsigned* makes;
struct Archive {
 id<MTLRenderPipelineState> Make(id<MTLDevice>,FixturePipelineDescriptor* d,NSError**) {
  assert(makes);++*makes;
  if(d->key.format==0xf00)return nil;
  if(d->key.format==0xf01)@throw [NSException exceptionWithName:@"fixture" reason:@"compile exception" userInfo:nil];
  return Pso(d->key);
 }
} pipeline_archive;
struct State {
 ReadyMap ready_;
 std::unordered_set<PipelineKey,PipelineKeyHash> failed_,demanded_,known_;
 bool keys_dirty_=false;uint32_t failures_logged_=0,draws_waiting_=0;
 unsigned make_calls=0;
 struct Job {PipelineKey key;bool warm;};std::vector<Job> jobs;
 void Start(id<MTLDevice>,const PipelineKey& key,FixturePipelineDescriptor* desc,bool warm) {
  assert(desc && desc->key==key);jobs.push_back({key,warm});
 }
 @FINISH@
};
struct Candidate : State {
 PipelineLookupCache<id<MTLRenderPipelineState>> ready_lookup_;
 @CANDIDATE_GET@
};
struct Reference : State {
 @REFERENCE_GET@
};
PipelineKey Key(unsigned i) {return {0x1000u+i,0x2000u+i%17,i%5,i%3,15,0,0,0,1,false,0};}
size_t checks=0;
void Equal(const Candidate& a,const Reference& b) {
 assert(a.ready_.size()==b.ready_.size() && a.failed_==b.failed_ && a.demanded_==b.demanded_ && a.known_==b.known_);
 assert(a.keys_dirty_==b.keys_dirty_ && a.failures_logged_==b.failures_logged_ &&
        a.draws_waiting_==b.draws_waiting_ && a.make_calls==b.make_calls && a.jobs.size()==b.jobs.size());
 for(const auto& [k,p]:a.ready_)assert(b.ready_.at(k)==p);
 for(size_t i=0;i<a.jobs.size();++i)assert(a.jobs[i].key==b.jobs[i].key && a.jobs[i].warm==b.jobs[i].warm);
}
id<MTLRenderPipelineState> Check(Candidate& a,Reference& b,const PipelineKey& k,bool async,bool failed_in=false) {
 bool af=failed_in,bf=failed_in;makes=&a.make_calls;
 id<MTLRenderPipelineState> ap=a.Get(nil,k,nil,nil,async,&af,PipelineLookupEnabled());
 makes=&b.make_calls;id<MTLRenderPipelineState> bp=b.Get(nil,k,nil,nil,async,&bf);
 assert(ap==bp && af==bf);Equal(a,b);++checks;return ap;
}
void Complete(Candidate& a,Reference& b,const PipelineKey& k,id<MTLRenderPipelineState> p,bool warm) {
 a.Finish(k,p,warm,"fixture");b.Finish(k,p,warm,"fixture");Equal(a,b);
}
void Identity() {
 Candidate a;Reference b;auto k=Key(0);
 auto first=Check(a,b,k,false);assert(first && Check(a,b,k,false)==first);
 for(unsigned field=0;field<11;++field) {
  auto c=k;
  switch(field){case 0:++c.vs;break;case 1:++c.ps;break;case 2:++c.blend;break;case 3:++c.blend1;break;
   case 4:++c.mask;break;case 5:++c.format;break;case 6:++c.format1;break;case 7:++c.alpha_spec;break;
   case 8:++c.sample_count;break;case 9:c.alpha_to_coverage=!c.alpha_to_coverage;break;case 10:++c.motion;break;}
  assert(!(c==k));assert(Check(a,b,c,false)!=first);assert(Check(a,b,c,false));assert(Check(a,b,k,false)==first);
 }
 // A ready hit leaves the caller's failed value untouched, exactly as before.
 Check(a,b,k,false,true);
 // Force bucket chains; inserting/rehashing cannot invalidate a borrowed node.
 a.ready_.max_load_factor(10000);b.ready_.max_load_factor(10000);
 a.ready_.rehash(1);b.ready_.rehash(1);
 for(unsigned i=100;i<500;++i){Complete(a,b,Key(i),Pso(Key(i)),false);Check(a,b,Key(i),false);}
 Check(a,b,k,false);auto* entry=a.ready_lookup_.entry;
 a.ready_.rehash(8192);b.ready_.rehash(8192);
 Check(a,b,k,false);if(PipelineLookupEnabled())assert(a.ready_lookup_.entry==entry);
 std::puts("PASS all 11 identity fields, collisions, insertion/rehash, stable ready nodes and failed-output preservation");
}
void Transitions() {
 Candidate a;Reference b;auto old=Key(1);Check(a,b,old,false);
 auto pending=Key(2);assert(!Check(a,b,pending,true));assert(!Check(a,b,pending,true,true));
 assert(a.jobs.size()==1);Check(a,b,old,false);
 // Warm failure is retryable; demand completion eventually publishes readiness.
 Complete(a,b,pending,nil,true);assert(!Check(a,b,pending,true));
 Complete(a,b,pending,Pso(pending),false);assert(Check(a,b,pending,true)==Pso(pending));
 // Duplicate completion keeps the first PSO even if the new result differs/fails.
 Complete(a,b,pending,Pso(Key(1000)),true);Complete(a,b,pending,nil,false);
 assert(Check(a,b,pending,false)==Pso(pending));
 for(uint32_t format:{0xf00u,0xf01u}){auto fail=Key(format);fail.format=format;
  assert(!Check(a,b,fail,false));assert(!Check(a,b,fail,false));Check(a,b,pending,false);}
 auto absent=Key(4);absent.motion=0xfefefefe;assert(!Check(a,b,absent,true));assert(!Check(a,b,absent,true));
 auto demand_fail=Key(5);assert(!Check(a,b,demand_fail,true));Complete(a,b,demand_fail,nil,false);
 assert(!Check(a,b,demand_fail,true));Complete(a,b,demand_fail,Pso(demand_fail),true);
 assert(Check(a,b,demand_fail,true)==Pso(demand_fail)); // ready takes precedence over old failure set
 std::puts("PASS actual Get/Finish sync success/failure/exception, missing descriptor, pending demand, warm retry, ready publication and duplicate completion");
}
void Ownership() {
 __weak id weak=nil;
 ReadyMap ready;PipelineLookupCache<id<MTLRenderPipelineState>> cache;auto k=Key(9);
 @autoreleasepool {id p=[FakePSO new];weak=p;ready[k]=p;cache.Find(ready,k,true);}
 assert(weak!=nil);ready.clear();assert(weak==nil);
 // No lookup after this test-only erase: production ready_ never erases.
 std::puts("PASS borrowed-node cache does not retain a second PSO owner");
}
void Randomized() {
 Candidate a;Reference b;std::mt19937 rng(0x50534f);
 for(unsigned frame=0;frame<500;++frame) {
  for(unsigned draw=0;draw<120;++draw) {
   auto k=Key((draw/8+frame)%47);if(draw%17==0)k=Key(rng()%100);
   Check(a,b,k,true,rng()%19==0);
   if(draw%31==0)Complete(a,b,k,Pso(k),rng()%2);
  }
  auto jobs=a.jobs;for(const auto& j:jobs)if(!a.ready_.contains(j.key))Complete(a,b,j.key,Pso(j.key),j.warm);
  if(frame%13==0){a.ready_.rehash(256+(frame%5)*256);b.ready_.rehash(256+(frame%5)*256);}
 }
 std::printf("PASS 500 frames / 60000 randomized requests with completion, warm races, misses and ready hits; %zu checks\n",checks);
}
template<bool Fast>
__attribute__((noinline)) uint64_t Timed(Candidate& a,Reference& b,const std::vector<PipelineKey>& keys) {
 uint64_t sum=0;
 for(unsigned frame=0;frame<2000;++frame) {
  const bool enabled=Fast?PipelineLookupEnabled():false;
  for(const auto& k:keys) {
   bool failed=false;id<MTLRenderPipelineState> p;
   if constexpr(Fast){makes=&a.make_calls;p=a.Get(nil,k,nil,nil,false,&failed,enabled);}
   else {makes=&b.make_calls;p=b.Get(nil,k,nil,nil,false,&failed);}
   assert(p && !failed);sum+=((FakePSO*)p)->token;
  }
 }
 return sum;
}
void Benchmark(bool original,std::string_view layout) {
 Candidate a;Reference b;std::vector<PipelineKey> keys;
 const unsigned count=layout=="many-pipelines"?256:12;
 const unsigned run=layout=="one-pipeline"?2400:layout=="short-runs"?4:
                    layout=="alternating" || layout=="many-pipelines" || layout=="late-mismatch"?1:50;
 for(unsigned i=0;i<2400;++i){unsigned n=(i/run)%count;auto k=Key(n);
  if(layout=="late-mismatch"){k=Key(0);k.alpha_spec=n;}
  keys.push_back(k);a.ready_[k]=Pso(k);b.ready_[k]=Pso(k);
 }
 if(original)Timed<false>(a,b,keys);else Timed<true>(a,b,keys);
 auto start=std::chrono::steady_clock::now();auto sum=original?Timed<false>(a,b,keys):Timed<true>(a,b,keys);
 auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
 assert(a.make_calls==0 && b.make_calls==0 && a.jobs.empty() && b.jobs.empty());
 std::printf("HOST %s: %.3f ms; checksum %llu; ready %zu; compiles %u\n",layout.data(),ms,
  (unsigned long long)sum,a.ready_.size(),a.make_calls+b.make_calls);
}
int main(int argc,char** argv) {@autoreleasepool {
 g_enabled=argc>1 && std::string_view(argv[1])=="on";
 if(argc>2){Benchmark(std::string_view(argv[1])=="original",argv[2]);return 0;}
 Identity();Transitions();Ownership();Randomized();
}return 0;}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--benchmark', action='store_true')
    args = parser.parse_args()
    source = (ROOT / 'ios/src/native_renderer.mm').read_text()
    baseline = subprocess.check_output(['git', 'show', f'{REFERENCE}:ios/src/native_renderer.mm'], cwd=ROOT, text=True)
    get = method(source, 'id<MTLRenderPipelineState> Get(')
    old_get = method(baseline, 'id<MTLRenderPipelineState> Get(')
    finish = method(source, 'void Finish(const PipelineKey& k,')
    assert finish == method(baseline, 'void Finish(const PipelineKey& k,')
    # Protect the entire miss path, actual collection and PSO creation policy.
    miss = '    if (failed_.count(k)) {'
    assert get[get.index(miss):] == old_get[old_get.index(miss):]
    assert method(source, 'void Collect()') == method(baseline, 'void Collect()')
    assert source.count('pipeline_cache.Get(') == 1
    assert 'async_pipelines, &pipeline_failed,\n                                                       reuse_pipeline_lookup)' in source
    assert 'const bool reuse_pipeline_lookup = PipelineLookupEnabled();' in source
    key_and_lookup = source[source.index('struct PipelineKey {'):source.index('// Motion vectors (in the viewport')]
    text = HARNESS.replace('@KEY_AND_LOOKUP@', key_and_lookup).replace('@FINISH@', finish)
    text = text.replace('@CANDIDATE_GET@', get).replace('@REFERENCE_GET@', old_get)
    text = text.replace('MTLRenderPipelineDescriptor', 'FixturePipelineDescriptor')
    with tempfile.TemporaryDirectory(prefix='nfsmw-pipeline-lookup-') as temp:
        path = pathlib.Path(temp)
        cpp, exe = path / 'test.mm', path / 'test'
        cpp.write_text(text)
        for options in [['-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'], ['-O3']]:
            subprocess.run(['xcrun', 'clang++', '-std=c++20', '-fobjc-arc', '-framework', 'Foundation', *options,
                            str(cpp), '-o', str(exe)], check=True)
            for arm in ['off', 'on']:
                print(f'CHECK {options[0]} {arm}', flush=True)
                subprocess.run([str(exe), arm], check=True)
        if args.benchmark:
            for layout in ['one-pipeline', 'runs', 'short-runs', 'alternating', 'many-pipelines', 'late-mismatch']:
                times = {a: [] for a in ['original', 'off', 'on']}
                identity = None
                for trial in range(7):
                    order = ['original', 'off', 'on'] if trial % 2 == 0 else ['on', 'off', 'original']
                    for arm in order:
                        output = subprocess.check_output([str(exe), arm, layout], text=True)
                        print(f'TRIAL {trial} {arm} {output}', end='', flush=True)
                        m = re.search(r': ([\d.]+) ms; checksum (\d+); ready (\d+); compiles (\d+)', output)
                        assert m, output
                        got = m.group(2, 3, 4)
                        if identity is None:
                            identity = got
                        assert got == identity, (layout, arm, got, identity)
                        times[arm].append(float(m[1]))
                print(f'MEDIAN {layout}: ' + ', '.join(f'{a} {statistics.median(v):.3f} ms' for a, v in times.items()) +
                      f'; matching checksum/ready/compiles {identity}', flush=True)


if __name__ == '__main__':
    main()
