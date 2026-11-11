#!/usr/bin/env python3
"""Host-only G2 experiment using actual renderer types. No production changes.

Inputs model outputs AFTER original validation. Timings include bundle matching,
ownership/list creation, draw append, active-input lookup and frame teardown;
exclude common validation/decoding, mesh-identity selection, shaders, GPU and power.
Mesh identity is supplied by the experiment; production admission/capacity and
the failure-before-publication path remain unimplemented. A result here alone
never authorizes skipping validation or claiming whole Record/battery gains.
"""
from pathlib import Path
import subprocess
import tempfile
import sys
import test_draw_arena as arena

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#include <chrono>
#include <array>
#include <span>
#include <random>
// Stable decoded outputs supplied by the unchanged validator, including metadata.
struct Validated { std::shared_ptr<FloatArray> value; uint32_t location; bool integer, fresh; };
struct Bundle {
  std::pmr::vector<Attribute> attributes;
  std::array<uint8_t,32> by_location;
  explicit Bundle(std::pmr::memory_resource* r):attributes(r){by_location.fill(255);}
};
struct BoundDraw {const Bundle* bundle=nullptr; uint16_t fresh=0;};
struct Experiment {
  // Both prototype and reference use ACTUAL Draw/Frame/Attribute/FrameOwners.
  nfsmw::FrameOwners<FloatArray> owners{true};
  Frame frame{true,0,0};
  std::deque<Bundle> bundles;
  std::vector<const Bundle*> last;
  std::vector<BoundDraw> bound;
  std::vector<nfsmw::FrameOwnerHint<FloatArray>> hints;
  uint64_t hits=0,misses=0;
  explicit Experiment(unsigned meshes):last(meshes),hints(meshes*16){}
  BoundDraw Bind(unsigned mesh,std::span<const Validated> inputs,bool capture_each) {
    assert(inputs.size()<=16);
    // The conservative arm retains CURRENT production capture timing/cost.
    // Production would collect these handles at each original validation site.
    std::array<nfsmw::FrameRef<FloatArray>,16> snapshots;
    if(capture_each)for(size_t i=0;i<inputs.size();++i)
      snapshots[i]=owners.Capture(inputs[i].value,&hints[mesh*16+i]);
    auto* prior=last.at(mesh);bool same=prior && prior->attributes.size()==inputs.size();
    uint16_t fresh=0;
    for(size_t i=0;i<inputs.size();++i){
      const auto& in=inputs[i];assert(in.location<32);
      if(in.fresh)fresh|=uint16_t(1u<<i);
      if(same){const auto& a=prior->attributes[i];
        if(a.values.get()!=(capture_each?snapshots[i].get():in.value.get()) || a.location!=in.location || a.integer!=in.integer)same=false;
      }
    }
    if(same){++hits;return {prior,fresh};}
    ++misses;bundles.emplace_back(frame.attribute_arena.Resource());auto& b=bundles.back();
    b.attributes.reserve(inputs.size());
    for(size_t i=0;i<inputs.size();++i){
      const auto& in=inputs[i];Attribute a;a.location=in.location;a.integer=in.integer;
      a.values=capture_each?snapshots[i]:owners.Capture(in.value,&hints[mesh*16+i]);
      b.attributes.push_back(std::move(a));b.by_location[in.location]=uint8_t(i); // original LAST match wins
    }
    last[mesh]=&b;return {&b,fresh};
  }
  void Add(unsigned mesh,std::span<const Validated> inputs,unsigned mode){
    Draw d(frame.attribute_arena.Resource());
    if(mode)bound.push_back(Bind(mesh,inputs,mode==2));
    else {
      d.attributes.reserve(inputs.size());
      for(size_t i=0;i<inputs.size();++i){const auto& in=inputs[i];Attribute a;
        a.location=in.location;a.integer=in.integer;a.fresh=in.fresh;
        a.values=owners.Capture(in.value,&hints[mesh*16+i]);d.attributes.push_back(std::move(a));}
    }
    frame.draws.push_back(std::move(d));
  }
  // Simulates renderer's active-location selection with actual attribute views.
  const Attribute* Get(size_t draw,uint32_t location,bool compact) const {
    if(compact){auto* b=bound[draw].bundle;auto i=b->by_location[location];
      return i==255?nullptr:&b->attributes[i];}
    const Attribute* found=nullptr;
    for(const auto& a:frame.draws[draw].attributes)if(a.location==location)found=&a;
    return found;
  }
  bool Fresh(size_t draw,const Attribute* a,bool compact) const {
    return compact?bool(bound[draw].fresh&(1u<<size_t(a-bound[draw].bundle->attributes.data()))):a->fresh;
  }
};
using Inputs=std::vector<Validated>;
Inputs MakeInputs(unsigned n,unsigned seed){Inputs in;for(unsigned i=0;i<n;++i){
 in.push_back({std::make_shared<FloatArray>(16,float(seed+i)),i,bool(i&1),false});}return in;}
void Correctness(){
 Experiment old(32),candidate(32),conservative(32);std::vector<Inputs> data;
 for(unsigned i=0;i<32;++i)data.push_back(MakeInputs(1+i%16,i));
 std::mt19937 rng(1252);unsigned draws=0;
 for(unsigned i=0;i<10000;++i){auto mesh=rng()%32;auto& in=data[mesh];
   if(i%7==0){auto& a=in[rng()%in.size()];a.value=std::make_shared<FloatArray>(16,float(i));}
   if(i%13==0){auto& a=in[rng()%in.size()];a.location=rng()%32;a.integer=!a.integer;}
   for(auto& a:in)a.fresh=bool(rng()%3==0);
   // Every success has already passed validation; failed partial input sequences
   // never call Bind/Add (not a production early-failure test).
   old.Add(mesh,in,0);candidate.Add(mesh,in,1);conservative.Add(mesh,in,2);++draws;
 }
 for(unsigned d=0;d<draws;++d)for(unsigned l=0;l<32;++l){
  auto* a=old.Get(d,l,false);auto* b=candidate.Get(d,l,true);auto* c=conservative.Get(d,l,true);assert(bool(a)==bool(b) && bool(a)==bool(c));
  if(a){assert(a->values.get()==b->values.get() && *a->values==*b->values);
    assert(a->location==b->location && a->integer==b->integer);
    assert(old.Fresh(d,a,false)==candidate.Fresh(d,b,true));
    assert(a->values.get()==c->values.get() && a->integer==c->integer);
    assert(old.Fresh(d,a,false)==conservative.Fresh(d,c,true));}}
 assert(candidate.hits>0 && candidate.misses>0);
 auto* held=candidate.bound.front().bundle;auto value=held->attributes.front().values.Owner();
 std::weak_ptr<FloatArray> weak=value;value.reset();data.clear();candidate.last.clear();
 assert(!weak.expired() && held->attributes.front().values);
 // A new frame owns independent bundles; no pointer/key crosses frame lifetime.
 {Experiment another(1);auto in=MakeInputs(6,999);another.Add(0,in,true);
  assert(another.bound[0].bundle!=held);assert(held->attributes.front().values);}
 // Same cache entry may change before a later input: preserve earlier capture.
 nfsmw::FrameOwners<FloatArray> timing(true);nfsmw::FrameOwnerHint<FloatArray> hint;
 auto cached=std::make_shared<FloatArray>(16,1.f);auto first=timing.Capture(cached,&hint);
 cached=std::make_shared<FloatArray>(16,2.f);auto second=timing.Capture(cached,&hint);
 assert((*first)[0]==1.f && (*second)[0]==2.f && first.get()!=second.get());
 std::printf("PASS %u immutable historical draws x32 locations; decoded versions, duplicate locations, integer metadata, per-draw fresh flags and independent frame lifetimes\n",draws);
}
uint64_t Consume(const Experiment& e,bool compact,unsigned attrs){uint64_t checksum=0;
 for(size_t d=0;d<e.frame.draws.size();++d)for(unsigned l=0;l<attrs;++l){
  const auto* a=e.Get(d,l,compact);if(a){checksum+=uintptr_t(a->values.get())&255;
    checksum+=a->location+e.Fresh(d,a,compact);asm volatile(""::"r"(a->values.get()):"memory");}}
 return checksum;}
void Benchmark(){
 for(unsigned attrs:{1u,4u,6u,9u,16u})for(unsigned meshes:{32u,512u,8192u})for(bool changed:{false,true}){
  std::vector<Inputs> data,alternate;for(unsigned i=0;i<meshes;++i){data.push_back(MakeInputs(attrs,i));alternate.push_back(MakeInputs(attrs,i+999));}
  std::vector<double> times[3];uint64_t hits=0,misses=0,checksum=0,arm_checksum[3]={};size_t list_bytes[3]={};
  for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<3;++arm){unsigned mode=(trial+arm)%3;
    auto start=std::chrono::steady_clock::now();{
      Experiment e(meshes);constexpr unsigned draws=20000;
      for(unsigned d=0;d<draws;++d){auto mesh=d%meshes;const auto& in=changed && ((d/meshes)&1)?alternate[mesh]:data[mesh];
       // Alternate genuinely different retained decoded versions without allocator work.
       e.Add(mesh,in,mode);
      }
      const auto consumed=Consume(e,mode!=0,attrs);checksum+=consumed;arm_checksum[mode]+=consumed;
      list_bytes[mode]=e.frame.attribute_arena.Stats().peak_bytes;
      if(mode==2){hits=e.hits;misses=e.misses;}
    } // teardown IS inside timer, including extra prototype per-draw sidecar
    times[mode].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
  }
  assert(arm_checksum[0]==arm_checksum[1] && arm_checksum[0]==arm_checksum[2]);
  for(auto& t:times)std::sort(t.begin(),t.end());
  std::printf("HOST %u inputs/%u meshes/%s: original %.3f / optimistic bundle %.3f / capture-preserving bundle %.3f ms per20000 including teardown; hits %llu misses %llu arena peak original %zu / bundle %zu; checksum %llu (not validation/GPU/device/power)\n",attrs,meshes,changed?"changing versions":"stable",times[0][3],times[1][3],times[2][3],hits,misses,list_bytes[0],list_bytes[2],checksum);
 }
}
int main(){Correctness();@BENCHMARK@}
'''

def main():
    source = (ROOT / 'ios/src/native_renderer.mm').read_text()
    attrs = source[source.index('template <typename T>\nstruct DefaultInitAllocator'):source.index('// --- Residency')]
    types = source[source.index('struct ConstantBank {'):source.index('std::unique_ptr<Frame> recording;')]
    prefix = arena.HARNESS[:arena.HARNESS.index('class Probe final')]
    # Exercise actual reusable owner table; no change to production flag/default.
    prefix = prefix.replace('#define REXCVAR_GET(name) false', '#define REXCVAR_GET(name) true')
    program = (prefix.replace('@HEADER@', str(ROOT/'ios/src/native_draw_arena.h'))
               .replace('@FRAME_HEADER@', str(ROOT/'ios/src/native_frame_storage.h'))
               .replace('@ACTUAL_TYPES@', attrs+types).replace('@CONSTANT_TEST@',''))
    benchmark = '--benchmark' in sys.argv
    program += CODE.replace('@BENCHMARK@','Benchmark();' if benchmark else '')
    with tempfile.TemporaryDirectory(prefix='nfsmw-bundle-feasibility-') as tmp:
        path, exe = Path(tmp)/'test.mm', Path(tmp)/'test';path.write_text(program)
        opts = ['-O2'] if benchmark else ['-O1','-g','-fsanitize=address,undefined']
        subprocess.run(['xcrun','clang++','-std=c++20',*opts,'-fobjc-arc','-framework','Foundation','-framework','Metal',str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print('Host feasibility only: actual validation/Record/GPU execution NOT changed or exercised')

if __name__ == '__main__':main()
