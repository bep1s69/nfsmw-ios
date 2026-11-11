#!/usr/bin/env python3
"""G2 bounded path against actual COMPLETE Record vertex section.

Reference/experiment run original fetching, content validation, memo, decoding
and per-input Capture. Only list reserve/emission/final collection differs.
Index range is supplied; index/state/Metal/texture bodies are not executed.
Real fetch parsing/layout cache, memo, decoder and MotionMix are included.
Synthetic float32 layouts; little-endian swap/mapping/logging stand-ins.
The candidate is parked after a mixed/negative complete cost gate.
"""
from pathlib import Path
import subprocess,tempfile,sys
import test_prepared_geometry as prep
ROOT=Path(__file__).resolve().parents[2]
CPP=r'''
struct Frame;
struct Storage {
 nfsmw::FrameOwners<FloatArray> attributes{true};
};
using BundleCache=nfsmw::StableBindings<Attribute>;
struct Result {Draw draw;std::span<const Attribute> view;uint64_t geometry;const BundleCache::Bundle* bundle;};
struct Frame {
 Storage storage;
 nfsmw::DrawArena attribute_arena{true,0};
 std::optional<BundleCache> bundles;
 std::vector<Result> draws;
 VertexDiagnostics vertex_diagnostics;
 size_t attribute_lists=0,attribute_hint_bytes=0,skipped_other=0,from_arguments=0,reuse_attempts=0;
 bool candidate,bundle_disabled=false;
 explicit Frame(bool c):candidate(c){}
};
struct Store {std::unordered_map<uint64_t,std::vector<VertexInput>> inputs;}store;

namespace fmt {template<class... T>std::string format(const char* s,T&&...){return s;}}
void Note(Frame&,const std::string&){}
namespace write_watch {bool Clean(uint32_t,size_t){return false;}void Arm(uint32_t,size_t){}}
using FastClock=std::chrono::steady_clock;
bool timed_draw=false;
bool Stable(const PreparedGeometry* p){
 if(!p || p->count<6 || p->count>16)return false;
 for(unsigned i=0;i<p->count;++i)if(!p->inputs[i].entry || !p->inputs[i].entry->value || p->inputs[i].entry->dynamic)return false;
 return true;
}
BundleCache* CacheFor(Frame& f,PreparedGeometry* p){
 if(!f.candidate || f.bundle_disabled || !Stable(p))return nullptr;
 if(!f.bundles)try{f.bundles.emplace();}catch(const std::bad_alloc&){f.bundle_disabled=true;return nullptr;}return &*f.bundles;
}
@RECORDS@
struct Case {
 uint32_t regs[0x6000]{},code[96]{};std::vector<VertexInput> inputs;CachedFetchLayout layout;NfsmwNativeDraw in{};
 unsigned lo=0,count=8;
 explicit Case(unsigned n=6){in.regs=regs;in.vs_key=123;in.vs_microcode_hash=456;in.vs_dwords=n*6;in.vs_microcode=code;in.initiator=4;
  for(unsigned i=0;i<n;++i){inputs.push_back({i*2,0u,i,0x688,int32_t(i)});
   layout.inputs.push_back({VFetch{i/3,i*4,16,38,0x688,false,false},true});}
  Retarget(0);
 }
 void Retarget(unsigned mesh){for(auto& item:layout.inputs){auto slot=item.fetch.slot;
   regs[kFetchBase+slot*2]=0x1000+mesh*4096+slot*1024;regs[kFetchBase+slot*2+1]=16384<<2;}}
 void Install(){
  for(size_t i=0;i<inputs.size();++i){const auto& f=layout.inputs[i].fetch;auto* w=code+inputs[i].address*3;
   w[0]=(uint32_t(i)<<12)|(1u<<19)|((f.slot/3)<<20)|((f.slot%3)<<25);
   w[1]=(f.format<<16)|f.swizzle|(uint32_t(f.is_signed)<<12)|(uint32_t(f.integer)<<13);
   w[2]=(f.offset<<8)|f.stride;
  }
  store.inputs[in.vs_key]=inputs;
 }
};
struct Signature {unsigned skipped;std::vector<uint64_t> data;bool operator==(const Signature&)const=default;};
Signature Summarize(const Frame& f){Signature s{unsigned(f.skipped_other),{}};
 for(const auto& r:f.draws){s.data.push_back(r.geometry);s.data.push_back(r.view.size());
  for(unsigned location=0;location<40;++location){const Attribute* found=nullptr;
   for(const auto& a:r.view)if(a.location==location)found=&a;
   if(r.bundle)assert(found==r.bundle->Find(location));
  }
  for(auto& a:r.view){s.data.push_back(a.location);s.data.push_back(a.integer);s.data.push_back(a.fresh);s.data.push_back(a.values.Slot());
   s.data.push_back(a.values?a.values->size():0);if(a.values)for(float v:*a.values){uint32_t u;std::memcpy(&u,&v,4);s.data.push_back(u);}}}
 s.data.push_back(f.storage.attributes.size());s.data.push_back(f.storage.attributes.lookups);s.data.push_back(f.storage.attributes.hint_hits);
 return s;}
void Reset(){InvalidatePreparedGeometry();attribute_lookup.Clear();attribute_cache.clear();fetch_layout_cache.clear();store.inputs.clear();frame_counter=((frame_counter>>16)+1)*65536+100;}
Signature Scenario(unsigned mode){Reset();std::memset(physical,0,64<<20);Case c(9);c.inputs[2].usage=2;c.inputs[3].swizzle=0x680;Frame f(mode==2);bool candidate=mode!=0;
 for(unsigned i=0;i<3000;++i){
  if(i%71==0)c.Retarget(i%16);
  if(i%97==0){c.lo=(i/97)%4;c.count=1+(i/97)%16;}
  if(i%53==0){ // known source write: actual fingerprint/decode/dynamic path
   physical[0x1000]^=uint8_t(i|1);}
  if(i%211==0){++c.in.vs_microcode_hash;c.layout.inputs[4].fetch.offset=(i/211)%2?4:16;}
  c.Install();
  if(candidate)Candidate(f,c.in,c.lo,c.count);else Reference(f,c.in,c.lo,c.count);
  if(i%103==0)++frame_counter;
 }
 // Shader/metadata known; invalid format at a LATER input triggers actual
 // early return after earlier captures. No partial draw/bundle publication.
 c.layout.inputs[8].fetch.format=63;++c.in.vs_microcode_hash;c.Install();
 if(candidate)Candidate(f,c.in,c.lo,c.count);else Reference(f,c.in,c.lo,c.count);
 assert(f.skipped_other && f.draws.size()==3000);
 if(mode==2)assert(f.bundles && f.bundles->hits>0 && f.bundles->size()<=512);
 if(mode==2)assert(size_t(std::count_if(f.draws.begin(),f.draws.end(),[](const auto& r){return r.bundle!=nullptr;}))==f.bundles->hits+f.bundles->builds);
 // Erase source cache nodes AFTER sweep invalidation. Published lists keep
 // their frame owners and data; source storage can subsequently change.
 InvalidatePreparedGeometry();attribute_lookup.Clear();attribute_cache.clear();
 return Summarize(f);
}
struct FaultResource:std::pmr::memory_resource {
 bool fail=false;
 void* do_allocate(size_t n,size_t a)override{if(fail)throw std::bad_alloc();return std::pmr::new_delete_resource()->allocate(n,a);}
 void do_deallocate(void* p,size_t n,size_t a)override{std::pmr::new_delete_resource()->deallocate(p,n,a);}
 bool do_is_equal(const std::pmr::memory_resource& r)const noexcept override{return this==&r;}
};
Signature LateFailure(unsigned mode){
 Reset();std::memset(physical,0,64<<20);Case c(9);Frame f(mode==2);
 for(unsigned i=6;i<9;++i)c.layout.inputs[i].fetch.offset=262146+(i-6)*4;
 c.Install();auto record=[&]{if(mode)Candidate(f,c.in,c.lo,c.count);else Reference(f,c.in,c.lo,c.count);};
 for(unsigned i=0;i<16;++i)record();
 c.regs[kFetchBase+2*2+1]=1<<2; // shrink ONLY the later stream; decoded key is unchanged
 for(unsigned i=0;i<16;++i)record();
 auto before=f.draws.size(),attempts=f.reuse_attempts;
 auto hits=f.bundles?f.bundles->hits:0,builds=f.bundles?f.bundles->builds:0;
 physical[0x1000+2*1024]^=1; // memo OFF forces actual late decoder/bounds rejection
 record();assert(f.draws.size()==before && f.skipped_other==1);
 if(mode==2){assert(f.reuse_attempts==attempts+1);assert(f.bundles->hits==hits && f.bundles->builds==builds);}
 return Summarize(f);
}
void HeaderEdges(){
 nfsmw::DrawArena arena(true,0);nfsmw::FrameOwners<FloatArray> owners(true);
 auto value=std::make_shared<FloatArray>(16,1.f);
 using Small=nfsmw::StableBindings<Attribute,2>;Small cache;
 auto fill=[&](void* key,unsigned count=6,bool stable=true){
  std::pmr::vector<Attribute> out(arena.Resource());auto* h=cache.Select(key);
  Small::Collect c(&cache,h,out,count,stable);if(!c.Reusing())out.reserve(count);
  for(unsigned i=0;i<count;++i){Attribute a;a.location=i;a.integer=false;a.values=owners.Capture(value);c.Add(std::move(a),stable);}
  auto view=c.Finish();assert(view.size()==count);return std::vector<Attribute>(view.begin(),view.end());};
 auto first=fill(reinterpret_cast<void*>(1));fill(reinterpret_cast<void*>(1));assert(cache.hits==1);
 // Key reused for a different descriptor/input count must never return old tail.
 fill(reinterpret_cast<void*>(1),7);fill(reinterpret_cast<void*>(2));fill(reinterpret_cast<void*>(3));
 assert(cache.size()==2 && cache.capacity>0);assert(first[0].values.get()==value.get());
 Small::Hint stale;{Small old;std::pmr::vector<Attribute> out(arena.Resource());Small::Collect c(&old,&stale,out,6,true);
 for(unsigned i=0;i<6;++i){Attribute a;a.location=i;a.integer=false;a.values=owners.Capture(value);c.Add(std::move(a),true);}c.Finish();}
 stale.bundle=reinterpret_cast<const Small::Bundle*>(uintptr_t(1));Small next;
 std::pmr::vector<Attribute> out(arena.Resource());Small::Collect c(&next,&stale,out,6,true);assert(!c.Reusing());
 // A mismatch after a matching prefix must preserve OLD earlier versions.
 Small prefix;Small::Hint h;
 std::pmr::vector<Attribute> original(arena.Resource());Small::Collect warm(&prefix,&h,original,6,true);
 for(unsigned i=0;i<6;++i){Attribute a;a.location=i==5?2:i;a.integer=false;a.values=owners.Capture(value);warm.Add(std::move(a),true);}auto old=warm.Finish();assert(warm.PublishedBundle()->Find(2)==&old[5]);
 auto replacement=std::make_shared<FloatArray>(16,2.f);
 std::pmr::vector<Attribute> changed(arena.Resource());Small::Collect update(&prefix,&h,changed,6,true);assert(update.Reusing());
 for(unsigned i=0;i<6;++i){Attribute a;a.location=i;a.integer=false;a.fresh=i==2;
   a.values=owners.Capture(i<2?value:replacement);update.Add(std::move(a),i<4);}
 auto result=update.Finish();assert(result.size()==6 && result[2].fresh);
 for(unsigned i=0;i<6;++i){assert((*old[i].values)[0]==1.f);assert((*result[i].values)[0]==(i<2?1.f:2.f));}
 // Throw in deque growth, after the original list is complete: no lost list.
 FaultResource fault;nfsmw::StableBindings<Attribute,512> constrained(&fault);fault.fail=true;
 for(unsigned j=0;j<512 && !constrained.allocation_fallbacks;++j){
   nfsmw::StableBindings<Attribute,512>::Hint hint;std::pmr::vector<Attribute> list(arena.Resource());
   nfsmw::StableBindings<Attribute,512>::Collect collect(&constrained,&hint,list,6,true);
   for(unsigned i=0;i<6;++i){Attribute a;a.location=i;a.integer=false;a.values=owners.Capture(value);collect.Add(std::move(a),true);}
   auto v=collect.Finish();assert(v.size()==6 && v[5].values.get()==value.get());
 }
 assert(constrained.allocation_fallbacks==1);
 Small wide;Small::Hint wide_hint;std::pmr::vector<Attribute> wide_list(arena.Resource());
 Small::Collect wide_collect(&wide,&wide_hint,wide_list,6,true);
 for(unsigned i=0;i<6;++i){Attribute a;a.location=i==5?37:i;a.integer=false;a.values=owners.Capture(value);wide_collect.Add(std::move(a),true);}
 auto wide_view=wide_collect.Finish();auto* wide_bundle=wide_collect.PublishedBundle();
 assert(wide_bundle->Find(37)==&wide_view[5] && wide_bundle->Find(63)==nullptr);
 Small selectors;unsigned rejected=0;
 for(uintptr_t i=1;i<4096;++i)if(!selectors.Select(reinterpret_cast<void*>(i*16)))++rejected;
 assert(rejected && selectors.capacity==rejected && selectors.size()==0);
 std::puts("PASS bounded capacity/selector collisions, reused-key width, stale epochs, prefix/version/fresh/dynamic fallback and allocation failure retention");
}
void Benchmark(){
 for(unsigned attrs:{1u,4u,6u,9u})for(unsigned meshes:{32u,512u,8192u})for(bool changing:{false,true})for(unsigned active:(attrs>=6?std::vector<unsigned>{attrs,1}:std::vector<unsigned>{attrs})){
  std::vector<double> times[3];uint64_t hits=0,changes=0,builds=0;size_t draws=0;
  for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<3;++arm){unsigned mode=(trial+arm)%3;bool candidate=mode!=0;
   Reset();std::memset(physical,0,64<<20);Case c(attrs);c.Install();auto start=std::chrono::steady_clock::now();draws=0;hits=changes=builds=0;
   for(unsigned start=0;start<20000;start+=3000){
    ++frame_counter;Frame f(mode==2);
    for(unsigned i=start;i<std::min(start+3000,20000u);++i){c.Retarget(i%meshes);
     if(changing)physical[0x1000+(i%meshes)*4096]^=uint8_t(1);
     if(candidate)Candidate(f,c.in,c.lo,c.count);else Reference(f,c.in,c.lo,c.count);
    }
    // Reference search versus immutable-bundle location index. Index creation
    // and fallback searches are included; GPU/Metal calls remain unexecuted.
    uintptr_t check=0;
    for(auto& r:f.draws)for(unsigned l=0;l<active;++l){const Attribute* found=nullptr;
     if(r.bundle)found=r.bundle->Find(l);else for(auto& a:r.view)if(a.location==l)found=&a;
     if(found)check^=uintptr_t(found->values.get());}
    for(auto& r:f.draws)check^=r.geometry;
    asm volatile(""::"r"(check):"memory");draws+=f.draws.size();
    if(candidate && f.bundles){hits+=f.bundles->hits;changes+=f.bundles->changes;builds+=f.bundles->builds;}
   } // complete frame teardown timed
   times[mode].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
  }
  for(auto& t:times)std::sort(t.begin(),t.end());
  std::printf("RECORD %u inputs/%u active/%u meshes/%s: reference %.3f / path OFF %.3f / bounded stable ON %.3f ms per%zu; hits %llu changes %llu builds %llu (actual vertex section, 3000draw frame boundaries, not GPU/power)\n",attrs,active,meshes,changing?"writes":"stable",times[0][3],times[1][3],times[2][3],draws,hits,changes,builds);
 }
}
int main(int argc,char**){memo_enabled=argc==1;enabled=true;std::printf("CONFIG fingerprint memo %s\n",memo_enabled?"on":"off");std::vector<uint8_t> memory(64<<20);physical=memory.data();
 auto a=Scenario(0);auto off=Scenario(1);auto b=Scenario(2);assert(a==b && a==off);
 if(!memo_enabled){auto x=LateFailure(0);assert(x==LateFailure(1) && x==LateFailure(2));}
 HeaderEdges();
 std::puts("PASS actual full vertex-section differential: 3000 historical draws, actual fingerprint/decoder/memo, owner order/stats, source writes/layout/range changes, late failure, eviction retention");
 @BENCHMARK@
 delete prepared_geometry;
}
'''

def main():
    s=(ROOT/'ios/src/native_renderer.mm').read_text()
    prefix='#import <Foundation/Foundation.h>\n#import <Metal/Metal.h>\n#include "native_draw_arena.h"\n#include "stable_bindings_candidate.h"\n#include <optional>\n#include <chrono>\n#include <cmath>\n'
    attrs=s[s.index('template <typename T>\nstruct DefaultInitAllocator'):s.index('// --- Residency')]
    prefix+=prep.PREFIX.replace('#include "baseline_prepared_geometry.h"','').replace('using FloatArray=std::vector<float>;',attrs).replace('struct Attribute{unsigned location;bool integer;};','')
    prefix=prefix.replace('bool enabled=true;','bool enabled=true;bool memo_enabled=true;')
    prefix=prefix.replace('  assert(name=="nfsmw_native_attribute_lookup" || name=="nfsmw_native_attribute_bulk_compare");return true;', '  if(name=="nfsmw_native_fingerprint_memo")return memo_enabled;return name=="nfsmw_native_attribute_lookup" || name=="nfsmw_native_attribute_bulk_compare" || name=="nfsmw_native_vfetch_cache";')
    sdk=Path('/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk/include/rex/graphics/xenos.h').read_text()
    sig='enum class VertexFormat';pos=sdk.index(sig);end=sdk.index('};',pos)+2
    prefix+='namespace xenos {\n'+sdk[pos:end]+'''\nuint32_t GpuSwap(uint32_t v,Endian e){assert(unsigned(e)==0);return v;}\n}\n'''
    for signature in ['uint32_t LoadLE32(', 'float AsFloat(', 'struct VertexInput {','struct VertexDiagnostics {','struct ConstantBank {','struct Draw {']:
        prefix+=prep.function(s,signature)+(';' if signature.startswith('struct') else '')+'\n'
    prefix+=s[s.index('uint64_t Fingerprint('):s.index('// Guest memory write watch:')]
    prefix+=s[s.index('template <typename Map>\nvoid Sweep('):s.index('std::unordered_map<FetchKey, CacheEntry<Texture>')]
    prefix+=s[s.index('struct AttributeKey {'):s.index("// A draw's indices as the renderer draws them")]
    prefix+=s[s.index('struct VFetch {'):s.index('// --- Textures',s.index('struct VFetch {'))]
    prefix+=s[s.index('struct CachedVertexFetch {'):s.index('// Recording-thread only. Shader objects')]
    prefix+=prep.function(s,'inline uint64_t MotionMix(')+'\n'
    prefix+=prep.function(s,'bool ResolveVertexFetch(')+'\n'
    prefix+=s[s.index('// Recording-thread only. Shader objects'):s.index('// A description owns only immutable preparation results.')]
    prefix+=s[s.index('// A description owns only immutable preparation results.'):s.index('// Draw-reuse census (nfsmw_native_reuse_census')]
    body=s[s.index('  // Vertex inputs.',s.index('void Record(')):s.index('\n  if (!index_hit)',s.index('void Record('))]
    candidate=body.replace('      if (frame.attribute_arena.Enabled()) d.attributes.reserve(inputs_it->second.size());\n','')
    line='    PreparedGeometry* prepared=PreparedGeometryFor(in,layout,inputs_it->second,lo,d.vertex_count,frame.vertex_diagnostics);\n'
    assert candidate.count(line)==1
    candidate=candidate.replace(line,line+'''    auto* cache=CacheFor(frame,prepared);
    BundleCache::Collect collection(cache,cache?cache->Select(prepared):nullptr,d.attributes,inputs_it->second.size(),cache!=nullptr);
    if(collection.Reusing())++frame.reuse_attempts;
    if(frame.attribute_arena.Enabled() && !collection.Reusing())d.attributes.reserve(inputs_it->second.size());
''')
    assert candidate.count('d.attributes.push_back(std::move(a));')==3
    candidate=candidate.replace('d.attributes.push_back(std::move(a));','collection.Add(std::move(a),!acached.dynamic);')
    at=candidate.rfind('    }\n  }');assert at>=0
    candidate=candidate[:at]+candidate[at:].replace('    }\n  }','    }\n    view=collection.Finish();bundle=collection.PublishedBundle();\n  }',1)
    # Prove every validation, memo, decode, Capture and failure statement is
    # untouched. Only reserve/emission/final ownership collection may differ.
    recovered=candidate
    begin=recovered.index(line)+len(line)
    end=recovered.index('    for (size_t input_index',begin)
    recovered=recovered[:begin]+recovered[end:]
    recovered=recovered.replace('collection.Add(std::move(a),!acached.dynamic);','d.attributes.push_back(std::move(a));')
    recovered=recovered.replace('    view=collection.Finish();bundle=collection.PublishedBundle();\n','')
    anchor='      frame.attribute_hint_bytes += inputs_it->second.size() * sizeof(Attribute);\n'
    assert recovered.count(anchor)==1
    recovered=recovered.replace(anchor,anchor+'      if (frame.attribute_arena.Enabled()) d.attributes.reserve(inputs_it->second.size());\n')
    assert recovered==body,'Unexpected change outside collection'
    assert candidate.count('geometry_storage->attributes.Capture')==body.count('geometry_storage->attributes.Capture')==3
    records=''
    for name,code in [('Reference',body),('Candidate',candidate)]:
        records+=f'''void {name}(Frame& frame,const NfsmwNativeDraw& in,uint32_t lo,uint32_t count) {{
 Draw d(frame.attribute_arena.Resource());d.vertex_count=count;d.vs_key=in.vs_key;d.ps_key=in.ps_key;
 d.surface_info=d.color_info=d.depth_info=d.depth_control=d.blend_control=d.color_mask=d.color_control=d.vte=0;
 d.alpha_ref=0;d.window_offset_x=d.window_offset_y=0;d.window_offset_enable=false;
 std::fill_n(d.textures,16,-1);std::fill_n(d.viewport,6,0.f);std::fill_n(d.scissor,4,0);
 auto* geometry_storage=&frame.storage;const uint32_t* regs=in.regs;bool record_memo=true;
 const uint32_t hi=lo+count-1,prim=in.initiator&0x3f;
 struct {{uint64_t base;uint32_t count,offset,flags;}}ikey{{uint64_t(in.index_base),count,lo,in.initiator}};
 std::span<const Attribute> view;const BundleCache::Bundle* bundle=nullptr;
{code}
 if(view.empty())view=d.attributes;
 frame.draws.push_back({{std::move(d),view,geometry,bundle}});
}}\n'''
    program=prefix+CPP.replace('@RECORDS@',records).replace('@BENCHMARK@','Benchmark();' if '--benchmark' in sys.argv else '')
    with tempfile.TemporaryDirectory(prefix='nfsmw-stable-record-') as tmp:
        path,exe=Path(tmp)/'test.mm',Path(tmp)/'test';path.write_text(program)
        opts=['-O2'] if '--benchmark' in sys.argv else ['-O1','-g','-fsanitize=address,undefined']
        subprocess.run(['xcrun','clang++','-std=c++20',*opts,'-fobjc-arc','-I',str(ROOT/'ios/src'),'-I',str(ROOT/'tools/native'),'-framework','Foundation','-framework','Metal',str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        subprocess.run([str(exe),'memo-off'],check=True)
if __name__=='__main__':main()
