#!/usr/bin/env python3
"""Actual prepared metadata/lookup sites vs pre-trial Record preparation.

No GPU execution. Validation/decoding/index/state/ownership code is guarded
byte-for-byte separately. --benchmark times only preparation on the host.
"""
from pathlib import Path
import subprocess
import tempfile
import sys
ROOT=Path(__file__).resolve().parents[2]

def function(s,signature):
    start=s.index(signature);at=s.index('{',start);end=at+1;depth=1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]

def normalize_prepared_record(s):
    # Only the audited metadata/lookup changes may differ. Content validation,
    # decoding, index handling, diagnostics, ownership and state stay original.
    edits=[
      ('    PreparedGeometry* prepared=PreparedGeometryFor(in,layout,inputs_it->second,lo,d.vertex_count,frame.vertex_diagnostics);\n',''),
      ('      auto* description=prepared ? &prepared->inputs[input_index] : nullptr;\n',''),
      ('      if (description) {\n        f=description->fetch;valid_fetch=true;\n      } else if (layout) {','      if (layout) {'),
      ('        if (!description) for (int i = 0; i < 4; ++i) {','        for (int i = 0; i < 4; ++i) {'),
      ('      if (description) {std::copy_n(description->remap,4,remap);remapped=description->remapped;}\n',''),
      ('description ? description->base : in.up_vertices ?','in.up_vertices ?'),
      ('description ? description->first : (size_t(lo)','(size_t(lo)'),
      ('description ? description->motion_term : uint64_t(uintptr_t(base)','uint64_t(uintptr_t(base)'),
      ('description ? description->range : size_t(d.vertex_count)','size_t(d.vertex_count)'),
      ('''      CacheEntry<FloatArray>* entry=description ? description->entry : nullptr;
      if(entry)++frame.vertex_diagnostics.prepared_lookups_saved;
      else {entry=&AttributeEntryFor(description ? description->key : akey,frame.vertex_diagnostics);if(description)description->entry=entry;}
      CacheEntry<FloatArray>& acached=*entry;''','      CacheEntry<FloatArray>& acached = AttributeEntryFor(akey, frame.vertex_diagnostics);'),
    ]
    for new,old in edits:
        assert s.count(new)==1,new
        s=s.replace(new,old)
    return s

PREFIX=r'''
#include "native_prepared_geometry.h"
#include "baseline_prepared_geometry.h"
#include "native_frame_storage.h"
#include "native_renderer.h"
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <iterator>
#include <map>
#include <memory>
#include <new>
#include <random>
#include <set>
#include <string>
#include <string_view>
#include <type_traits>
#include <unordered_map>
#include <vector>
using FloatArray=std::vector<float>;
bool enabled=true;
int Flag(std::string_view name){
  if(name=="nfsmw_native_prepared_geometry")return enabled;
  if(name=="nfsmw_native_attribute_lookup_sets_log2")return 14;
  assert(name=="nfsmw_native_attribute_lookup" || name=="nfsmw_native_attribute_bulk_compare");return true;
}
#define REXCVAR_GET(name) Flag(#name)
#define REXLOG_INFO(...)
constexpr uint64_t kPurgeIdleFrames=30;
bool purge=false;
struct PurgeSeen{bool Take(){return std::exchange(purge,false);}};
uint64_t frame_counter=0;
constexpr unsigned kFetchBase=0x4800;
uint8_t* physical;
const uint8_t* Physical(uint32_t at){return physical+(at&0x1fffffff);}
struct Memory {template<class T>T TranslateVirtual(uint32_t at){return reinterpret_cast<T>(physical+at);}};
Memory* Mem(){static Memory m;return &m;}
namespace xenos {enum class Endian:unsigned{};}
struct Attribute{unsigned location;bool integer;};
'''
TAIL=r'''
// Captured observable preparation outputs, independent of cache storage layout.
struct CapturedInput {
 VFetch fetch;uint32_t location,buffer,size_bytes;bool integer,remapped;int remap[4];
 const uint8_t* base;AttributeKey key;size_t first,range;uint64_t motion_term;CacheEntry<FloatArray>* entry;
};
struct Frame{VertexDiagnostics vertex_diagnostics;};
struct Draw{uint32_t vertex_count;};
@REFERENCE_CAPTURE@
@LIVE_CAPTURE@
@BASELINE_CAPTURE@
void Equal(const CapturedInput& a,const CapturedInput& b){
 assert(a.fetch.slot==b.fetch.slot && a.fetch.offset==b.fetch.offset && a.fetch.stride==b.fetch.stride);
 assert(a.fetch.format==b.fetch.format && a.fetch.swizzle==b.fetch.swizzle && a.fetch.is_signed==b.fetch.is_signed && a.fetch.integer==b.fetch.integer);
 assert(a.key==b.key && a.entry==b.entry && a.base==b.base && a.location==b.location);
 assert(a.buffer==b.buffer && a.size_bytes==b.size_bytes && a.integer==b.integer);
 assert(a.remapped==b.remapped && !std::memcmp(a.remap,b.remap,sizeof(a.remap)));
 assert(a.first==b.first && a.range==b.range && a.motion_term==b.motion_term);
}
struct Case {
 uint32_t regs[0x6000]{};std::vector<VertexInput> inputs;CachedFetchLayout layout;NfsmwNativeDraw in{};
 uint32_t lo=0,count=128;
 explicit Case(unsigned n=6){
  in.regs=regs;in.vs_key=123;in.vs_microcode_hash=456;in.vs_dwords=90;in.initiator=4;
  for(unsigned i=0;i<n;++i){
   inputs.push_back({i*2,i==2?2u:0u,i,0x688,int32_t(i)});
   layout.inputs.push_back({VFetch{i/3,i*2,16,6,0x688,false,false},true});
   regs[kFetchBase+(i/3)*2]=0x1000;regs[kFetchBase+(i/3)*2+1]=(16384<<2)|2;
  }
 }
 void Retarget(unsigned mesh){for(unsigned i=0;i<inputs.size();++i)regs[kFetchBase+layout.inputs[i].fetch.slot*2]=0x1000+mesh*4096;}
};
Frame frame;
void Check(Case& c){
 auto* p=PreparedGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics);
 auto* baseline=BaselineGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics);
 if(p)assert(enabled && p->count==c.inputs.size());else if(!enabled)assert(!p);
 for(unsigned i=0;i<c.inputs.size();++i){
  auto live=LiveCapture(p?&p->inputs[i]:nullptr,c.in,c.inputs[i],c.layout.inputs[i].fetch,c.lo,c.count,frame);
  auto old=ReferenceCapture(nullptr,c.in,c.inputs[i],c.layout.inputs[i].fetch,c.lo,c.count,frame);Equal(live,old);
  Equal(BaselineCapture(baseline?&baseline->inputs[i]:nullptr,c.in,c.inputs[i],c.layout.inputs[i].fetch,c.lo,c.count,frame),old);
 }
}
void Differential(){
 Case c;std::mt19937 rng(124);unsigned cases=0;
 for(unsigned n=0;n<30000;++n){
  if(n%97==0){InvalidatePreparedGeometry();InvalidateBaselineGeometry();attribute_lookup.Clear();attribute_cache.clear();}
  if(n%11==0){++c.in.vs_microcode_hash;auto& f=c.layout.inputs[n%c.inputs.size()].fetch;
   f.stride=1+rng()%64;f.offset=rng()%32;f.format=rng()%64;f.swizzle=rng()%4096;f.integer=rng()%2;f.is_signed=rng()%2;}
  if(n%13==0)c.in.vs_key=rng()%8;
  if(n%19==0){++c.in.vs_microcode_hash;auto& input=c.inputs[n%c.inputs.size()];
   input.usage=rng()%4;input.location=rng()%32;input.swizzle=rng()%4096;}
  if(n%17==0)c.in.vs_dwords=30+rng()%90;
  if(n%7==0){c.lo=rng()%64;c.count=1+rng()%1024;}
  if(n%5==0)c.Retarget(rng()%256);
  if(n%3==0)c.regs[kFetchBase+1]=((1+rng()%16384)<<2)|(rng()%4);
  Check(c);Check(c);Check(c);cases+=3;
 }
 if(enabled)assert(frame.vertex_diagnostics.prepared_lookups_saved>0);
 std::printf("PASS %u actual Record preparation comparisons per dev124/compact against original; keys, addresses, endian, remap, ranges, node identity and motion mixing\n",cases);
}
void Boundaries(){
 Case c;auto get=[&]{return PreparedGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics);};
 InvalidatePreparedGeometry();InvalidateBaselineGeometry();attribute_lookup.Clear();attribute_cache.clear();
 assert(!get());auto* p=get();assert(p && attribute_cache.empty()); // no eager side effects for later inputs
 Check(c);p=get();assert(p && p->inputs[0].entry);
 auto* node=p->inputs[0].entry;node->value=std::make_shared<FloatArray>(8,1.f);
 nfsmw::FrameOwners<FloatArray> owners;auto before=owners.Capture(node->value,&node->frame_owner);
 // A descriptor cache hit must expose CURRENT decoded version/dynamic flags,
 // never cache last frame's value or validation result.
 node->value=std::make_shared<FloatArray>(8,2.f);node->dynamic=true;node->fingerprint=999;
 assert(get()->inputs[0].entry==node && get()->inputs[0].entry->dynamic);
 auto after=owners.Capture(node->value,&node->frame_owner);assert((*before)[0]==1 && (*after)[0]==2);
 auto old_base=physical;std::vector<uint8_t> other(2<<20);physical=other.data();
 get();auto* moved=get();assert(moved && moved->inputs[0].base!=old_base+0x1000);Check(c);physical=old_base;
 // Real sweep must invalidate before deleting all borrowed idle nodes. Old
 // FrameOwners continue retaining earlier versions through eviction.
 // The historical cache shares the fixture map; its production sweep is not installed here.
 frame_counter=1024;purge=true;InvalidateBaselineGeometry();SweepAttributeCache();assert(attribute_cache.empty());Check(c);
 assert((*before)[0]==1 && (*after)[0]==2);
 // High guest physical aliases must keep the SDK's masked host mapping.
 c.regs[kFetchBase]^=0xA0000000u;Check(c);Check(c);Check(c);
 // Exact collision matching and generation: poison the borrowed handle, then
 // invalidate. Matcher may never inspect stale metadata after that point.
 using Table=nfsmw::PreparedGeometryCache<unsigned,uintptr_t,1>;Table table;
 table.Replace(1,0,[](auto& d){d=1;});table.Invalidate();
 assert(!table.Find(1,0,[](auto){assert(false);return true;}));
 Table probation;
 assert(!probation.Admit(1,0) && !probation.Admit(2,0));
 assert(!probation.Find(1,0,[](auto){assert(false);return true;}));
 assert(probation.Admit(1,0));probation.Replace(1,0,[](auto& d){d=11;});
 assert(probation.Admit(2,0));probation.Replace(2,0,[](auto& d){d=22;});
 assert(*probation.Find(1,0,[](auto){return true;})==11);
 assert(*probation.Find(2,0,[](auto){return true;})==22);
 for(unsigned i=0;i<100;++i)table.Replace(i,0,[&](auto& d){d=i;});
 assert(!table.Find(1,0,[](auto){return true;}));assert(*table.Find(99,0,[](auto){return true;})==99);
 // Unsupported and exceptional draw paths don't even acquire descriptors.
 auto bypass=[&]{auto misses=frame.vertex_diagnostics.prepared_misses;assert(!get());assert(frame.vertex_diagnostics.prepared_misses==misses);};
 c.in.up_vertices=1;bypass();c.in.up_vertices=0;c.in.inline_draw=1;bypass();c.in.inline_draw=0;
 c.in.from_arguments=1;bypass();c.in.from_arguments=0;c.in.initiator=8;bypass();c.in.initiator=4;
 c.in.vs_microcode_hash=0;bypass();c.in.vs_microcode_hash=456;
 c.layout.inputs[0].valid=false;bypass();c.layout.inputs[0].valid=true;
 c.layout.inputs[0].fetch.slot=96;bypass();c.layout.inputs[0].fetch.slot=0;
 assert(!PreparedGeometryFor(c.in,nullptr,c.inputs,c.lo,c.count,frame.vertex_diagnostics));
 for(unsigned n:{0u,1u,2u,3u}){Case tiny(n);assert(!PreparedGeometryFor(tiny.in,&tiny.layout,tiny.inputs,0,128,frame.vertex_diagnostics));}
 Case mismatch; mismatch.layout.inputs.pop_back();assert(!PreparedGeometryFor(mismatch.in,&mismatch.layout,mismatch.inputs,0,128,frame.vertex_diagnostics));
 Case large(17);assert(!PreparedGeometryFor(large.in,&large.layout,large.inputs,0,128,frame.vertex_diagnostics));
 std::puts("PASS lazy nodes, mutable versions/dynamic flags, physical-base change, real sweep/purge, frame lifetime, collisions, generations and exceptional fallback");
}
void BindingMutations(){
 for(bool unique:{false,true}) {
  Case c(unique?16:6);
  const unsigned slots[]={0,1,2,31,32,63,64,65,94,95,7,11,17,23,43,83};
  if(unique)for(unsigned i=0;i<c.inputs.size();++i){
   c.layout.inputs[i].fetch.slot=slots[i];c.regs[kFetchBase+2*slots[i]]=0x1000;
   c.regs[kFetchBase+2*slots[i]+1]=(16384<<2)|2;
  }
  InvalidatePreparedGeometry();InvalidateBaselineGeometry();
  auto get=[&]{return PreparedGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics);};
  Check(c);Check(c);Check(c);auto* p=get();assert(p);
  assert(p->binding_count==(unique?16:2));
  for(unsigned i=0;i<p->binding_count;++i)for(unsigned word=0;word<2;++word){
   const auto index=kFetchBase+p->bindings[i].index+word;
   auto hits=frame.vertex_diagnostics.prepared_hits;
   c.regs[index]^=word?4u:4096u;
   get();assert(frame.vertex_diagnostics.prepared_hits==hits); // every used word rejects, even non-anchor
   Check(c);Check(c);Check(c);p=get();assert(p);
  }
  auto hits=frame.vertex_diagnostics.prepared_hits;
  c.regs[kFetchBase+2*90]^=4096;assert(get()); // unused pair must not invalidate
  assert(frame.vertex_diagnostics.prepared_hits==hits+1);
  Check(c);
 }
 std::puts("PASS both words of every unique used binding, duplicates, slots63/64/95, unused binding stability against dev124 and original");
}
void MatchingBenchmark(){
 for(bool unique:{false,true})for(unsigned meshes:{32u,512u,2048u}){
  Case c(9);if(unique)for(unsigned a=0;a<9;++a){
   c.layout.inputs[a].fetch.slot=a;c.regs[kFetchBase+2*a]=0x1000;c.regs[kFetchBase+2*a+1]=(16384<<2)|2;
  }
  std::vector<double> times[2];uint64_t hits[2]={};
  for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<2;++arm){
   bool compact=(trial+arm)%2;
   InvalidatePreparedGeometry();InvalidateBaselineGeometry();frame={};
   auto start=std::chrono::steady_clock::now();
   for(unsigned i=0;i<400000;++i){
    c.Retarget(i%meshes);
    void* p=compact?static_cast<void*>(PreparedGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics)):
                    static_cast<void*>(BaselineGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics));
    asm volatile(""::"r"(p):"memory");
   }
   times[compact].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
   hits[compact]=frame.vertex_diagnostics.prepared_hits;
  }
  for(auto& t:times)std::sort(t.begin(),t.end());assert(hits[0]==hits[1]);
  std::printf("MATCH 9 inputs/%u %s bindings/%u meshes: dev124 %.3f / compact %.3f ms per400000, hits %llu (host matching/fill only)\n",unique?9:3,unique?"unique":"shared",meshes,times[0][3],times[1][3],hits[0]);
 }
}
void Benchmark(){
 for(unsigned attrs:{1u,3u,4u,6u,9u})for(unsigned meshes:{32u,512u,2048u,8192u}){
  Case c(attrs);std::vector<double> times[3];uint64_t avoided=0;uint64_t checksum=0;
  for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<3;++arm){
   unsigned candidate=(trial+arm)%3;InvalidatePreparedGeometry();InvalidateBaselineGeometry();attribute_lookup.Clear();attribute_cache.clear();
   frame={};const unsigned calls=40000;auto start=std::chrono::steady_clock::now();
   for(unsigned i=0;i<calls;++i){
    c.Retarget(i%meshes);auto* p=candidate==2?PreparedGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics):nullptr;
    auto* baseline=candidate==1?BaselineGeometryFor(c.in,&c.layout,c.inputs,c.lo,c.count,frame.vertex_diagnostics):nullptr;
    for(unsigned a=0;a<attrs;++a){
     auto value=candidate==2?LiveCapture(p?&p->inputs[a]:nullptr,c.in,c.inputs[a],c.layout.inputs[a].fetch,c.lo,c.count,frame):
         candidate==1?BaselineCapture(baseline?&baseline->inputs[a]:nullptr,c.in,c.inputs[a],c.layout.inputs[a].fetch,c.lo,c.count,frame):
                           ReferenceCapture(nullptr,c.in,c.inputs[a],c.layout.inputs[a].fetch,c.lo,c.count,frame);
     checksum+=uintptr_t(value.entry)&255;asm volatile(""::"r"(value.entry):"memory");
    }
   }
   times[candidate].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
   if(candidate==2)avoided=frame.vertex_diagnostics.prepared_lookups_saved;
  }
  for(auto& t:times)std::sort(t.begin(),t.end());
  std::printf("HOST %u inputs/%u meshes: reference %.3f / dev124 %.3f / compact %.3f ms per40000, avoided %llu of %u lookups, checksum %llu (not device CPU/energy)\n",attrs,meshes,times[0][3],times[1][3],times[2][3],avoided,40000*attrs,checksum);
 }
}
int main(int argc,char**){enabled=argc==1;std::vector<uint8_t> memory(64<<20);physical=memory.data();
 Differential();if(enabled){Boundaries();BindingMutations();@BENCHMARK@}else assert(!prepared_geometry && !baseline_geometry);
 delete prepared_geometry;delete baseline_geometry;
 std::printf("Table bound %zu KiB, switch %s\n",sizeof(PreparedGeometryTable)/1024,enabled?"on":"off");
}
'''

def capture(record,name,description_type="PreparedGeometryInput"):
    a=record.index('      const uint32_t* fc =');b=record.index('      acached.last_used =',a)
    body=record[a:b]
    return f'''CapturedInput {name}({description_type}* description,const NfsmwNativeDraw& in,
        const VertexInput& input,const VFetch& original_fetch,uint32_t lo,uint32_t count,Frame& frame) {{
      const VFetch f=description ? description->fetch : original_fetch;
      Draw d{{count}};uint64_t geometry=123;const uint32_t* regs=in.regs;
{body}
      CapturedInput out{{}};out.fetch=f;out.location=a.location;out.integer=a.integer;
      out.buffer=buffer;out.size_bytes=size_bytes;out.remapped=remapped;std::copy_n(remap,4,out.remap);
      out.base=base;out.key=akey;out.first=first;out.range=range;out.motion_term=geometry;out.entry=&acached;return out;
    }}'''

def main():
    source=(ROOT/'ios/src/native_renderer.mm').read_text()
    reference=subprocess.check_output(['git','show','1bbb88b:ios/src/native_renderer.mm'],cwd=ROOT,text=True)
    old=function(reference,'void Record(');new=function(source,'void Record(')
    assert normalize_prepared_record(new)==old,'Production validation/index/decoding/ownership/state changed'
    for signature in ['uint64_t Fingerprint(', 'uint64_t IndexFingerprint(', 'bool ParseVFetch(',
                      'bool DecodeElement(', 'bool ResolveVertexFetch(', 'const CachedFetchLayout* FetchLayoutFor(']:
        assert function(source,signature)==function(reference,signature),signature
    baseline=subprocess.check_output(['git','show','9140567:ios/src/native_renderer.mm'],cwd=ROOT,text=True)
    baseline_header=subprocess.check_output(['git','show','9140567:ios/src/native_prepared_geometry.h'],cwd=ROOT,text=True).replace('PreparedGeometryCache','BaselineGeometryCache')
    program=PREFIX
    for signature in ['struct VertexInput {','struct VertexDiagnostics {']:
        program+=function(source,signature)+';\n'
    program+=source[source.index('uint64_t Fingerprint('):source.index('// Guest memory write watch:')]
    program+=source[source.index('template <typename Map>\nvoid Sweep('):source.index('std::unordered_map<FetchKey, CacheEntry<Texture>')]
    program+=source[source.index('struct AttributeKey {'):source.index("// A draw's indices as the renderer draws them")]
    program+=function(source,'struct VFetch {')+';\n'
    program+=source[source.index('struct CachedVertexFetch {'):source.index('// Recording-thread only. Shader objects')]
    program+=function(source,'inline uint64_t MotionMix(')+'\n'
    program+=source[source.index('// A description owns only immutable preparation results.'):source.index('// Draw-reuse census (nfsmw_native_reuse_census')]
    baseline_helpers=baseline[baseline.index('// A description owns only immutable preparation results.'):baseline.index('// Draw-reuse census (nfsmw_native_reuse_census')]
    program+=baseline_helpers.replace('PreparedGeometry','BaselineGeometry').replace('PrepareGeometryInput','PrepareBaselineInput').replace('kPreparedInputs','kBaselineInputs').replace('prepared_geometry','baseline_geometry').replace('nfsmw_native_baseline_geometry','nfsmw_native_prepared_geometry')
    program+=TAIL.replace('@REFERENCE_CAPTURE@',capture(old,'ReferenceCapture')).replace('@LIVE_CAPTURE@',capture(new,'LiveCapture')).replace('@BASELINE_CAPTURE@',capture(function(baseline,'void Record('),'BaselineCapture','BaselineGeometryInput'))
    benchmark='--benchmark' in sys.argv;program=program.replace('@BENCHMARK@','Benchmark();MatchingBenchmark();' if benchmark else '')
    with tempfile.TemporaryDirectory(prefix='nfsmw-prepared-geometry-') as tmp:
        path,exe=Path(tmp)/'test.cpp',Path(tmp)/'test';path.write_text(program)
        (Path(tmp)/'baseline_prepared_geometry.h').write_text(baseline_header)
        options=['-O2'] if benchmark else ['-O1','-g','-fsanitize=address,undefined']
        subprocess.run(['clang++','-std=c++20',*options,'-I',str(ROOT/'ios/src'),'-I',tmp,str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True);subprocess.run([str(exe),'off'],check=True)
    print('PASS complete Record guard: only preparation/lookup edits; original validation, decoding, indices, draw state and ownership unchanged')

if __name__=='__main__':main()
