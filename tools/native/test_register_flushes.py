#!/usr/bin/env python3
"""C1 gate: actual outer flush + emitters, existing app/SDK bridge.

Actual app hooks run against guest/ABI stand-ins. --benchmark uses optimized host code,
seven alternating trials; it cannot establish device CPU or energy savings.
"""
from test_register_batch_bridge import program, ROOT, SDK
from test_register_batches import emitter
from pathlib import Path
import subprocess
import tempfile
import sys
import re

program=program[:program.index('int main(int argc')]
for name in ['sub_825A2968','sub_825A3EC8']:
    program=program.replace(f'extern \"C\" void __imp__{name}(PPCContext&,uint8_t*){{}}','')
# The old isolated-emitter fixture's no-op saves are insufficient when the
# real outer routine holds r30/r31 across calls. Model the ABI stack saves.
for low in (25,26):
    save=''.join(f'Store64(base,c.r1.u32-{8*(33-i)},c.r{i}.u64);' for i in range(low,32))
    restore=''.join(f'c.r{i}.u64=Load64(base,c.r1.u32-{8*(33-i)});' for i in range(low,32))
    program=re.sub(r'static void __savegprlr_'+str(low)+r'\([^\n]+',
        f'static void __savegprlr_{low}(PPCContext& c,uint8_t* base){{Store(base,c.r1.u32-8,uint32_t(c.r12.u64));{save}}}',program)
    program=re.sub(r'static void __restgprlr_'+str(low)+r'\([^\n]+',
        f'static void __restgprlr_{low}(PPCContext& c,uint8_t* base){{c.lr=Load(base,c.r1.u32-8);{restore}}}',program)
# Helpers are explicit foreign-operation stand-ins, not asserted shader proofs.
program+=r'''
unsigned foreign_calls=0;
static void Foreign(PPCContext& c,uint8_t* base,uint32_t marker) {
  ++foreign_calls;auto device=c.r3.u32;uint32_t last=Load(base,device);
  Store(base,last+4,0xC0001000);Store(base,last+8,marker);Store(base,device,last+8);
  // Prefix may dirty state/sources; collection must happen after it.
  Store(base,device+11532,Load(base,device+11532)^marker);
}
static void sub_825A2B88(PPCContext& c,uint8_t* b){Foreign(c,b,0x565458);}
static void sub_825A38F8(PPCContext& c,uint8_t* b){Foreign(c,b,0x534844);}
'''
program+=emitter('nfsmw_recomp.18.cpp','sub_825A2968')
outer=emitter('nfsmw_recomp.85.cpp','sub_825A3EC8')
# Fail closed if regeneration introduces an unmodelled helper inside the suffix.
assert re.findall(r'^\s*(sub_[0-9A-F]+)\(ctx, base\);',outer,re.M)==[
    'sub_825A2B88','sub_825A38F8','sub_825A28A8','sub_825A28A8',
    'sub_825A2A60','sub_825A2A60','sub_825A2968',*(['sub_825A28A8']*6)]

program+=outer.replace('sub_825A3EC8','reference_outer').replace('sub_825A28A8(ctx, base)','original_sub_825A28A8(ctx, base)').replace('sub_825A2A60(ctx, base)','original_sub_825A2A60(ctx, base)').replace('sub_825A2968(ctx, base)','original_sub_825A2968(ctx, base)')
program+=outer
program+=r'''
extern "C" void __imp__sub_825A2968(PPCContext& c,uint8_t* b){original_sub_825A2968(c,b);}
extern "C" void __imp__sub_825A3EC8(PPCContext& c,uint8_t* b){original_sub_825A3EC8(c,b);}
static void Candidate(PPCContext& c,uint8_t* b){sub_825A3EC8(c,b);}
'''
program+=outer.replace('sub_825A3EC8','c0_outer').replace('sub_825A2968(ctx, base)','original_sub_825A2968(ctx, base)')
program+=r'''
struct Decoded {
  NativeOracle cp;
  std::vector<std::pair<uint32_t,uint32_t>> operations;
};
static void Decode(Decoded& out,uint8_t* base,uint32_t first,uint32_t last) {
  for(uint32_t at=first+4;at<=last;) {
    uint32_t header=Load(base,at);at+=4;
    if(header>>30==2)continue;
    uint32_t count=((header>>16)&0x3fff)+1;
    memory::RingBuffer reader{reinterpret_cast<uint32_t*>(REX_RAW_ADDR(at)),count};
    if(header>>30==0) {
      out.operations.emplace_back(header&0x7fff,count);
      assert(out.cp.ExecutePacketType0(&reader,header));
    } else if(count==4 && Load(base,at)==kMagic) {
      uint64_t ticket=Load(base,at+8)|(uint64_t(Load(base,at+12))<<32);
      assert(Consume(ticket,+[](void* opaque,uint32_t reg,uint32_t* data,uint32_t n){
        auto& out=*static_cast<Decoded*>(opaque);out.operations.emplace_back(reg,n);out.cp.WriteRegistersFromMem(reg,data,n);
      },&out));
    } else {assert(count==1 && ((header>>8)&127)==0x10);out.operations.emplace_back(UINT32_MAX,Load(base,at));}
    at+=count*4;
  }
}
static constexpr uint32_t dev=0x1000,ring=0x100000;
static void Init(uint8_t* base,uint64_t vs,uint64_t ps,uint64_t fetch,uint64_t scalar,uint32_t alignment=0) {
  Store(base,dev,ring+alignment);Store(base,dev+4,ring+0x80000);
  Store64(base,dev+16,vs);Store64(base,dev+24,ps);
  Store64(base,dev+32,(fetch&0xffffffff00000000ull)|0xbfffC000ull);
  Store64(base,dev+40,scalar);Store64(base,dev+48,scalar|0x7ff);
}
static PPCContext Context() {
  PPCContext c{};c.r1.u32=0x80000;c.r3.u32=dev;c.lr=0x12345678;
  c.r30.u64=0x123456789abcdef0;c.r31.u64=0xfedcba9876543210;return c;
}
static void FlushDifferential() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();std::mt19937_64 rng(1234);
  for(unsigned n=0;n<300;++n)for(unsigned alignment=0;alignment<16;alignment+=4) {
    for(unsigned i=0;i<3000;++i)Store(base,dev+i*4,uint32_t(rng()));
    uint64_t mask=n==0?UINT64_MAX:n==1?0xAAAAAAAAAAAAAAAAull:n==2?0:rng();
    Init(base,mask,n<3?mask:rng(),n<3?mask:rng(),n<3?mask:rng(),alignment);
    auto reference=memory;auto old=Context(),trial=old;
    bulk=n%2;original_reference_outer(old,reference.data());Candidate(trial,base);
    Decoded a,b;Decode(a,reference.data(),ring+alignment,Load(reference.data(),dev));Decode(b,base,ring+alignment,Load(base,dev));
    assert(a.operations==b.operations);
    assert(!std::memcmp(a.cp.registers.values,b.cp.registers.values,sizeof(a.cp.registers.values)));
    assert(a.cp.side_effect_calls==b.cp.side_effect_calls);
    assert((Load(base,dev)&15)==(Load(reference.data(),dev)&15));
    // Every device byte except compressed ring pointer is identical, including
    // mask clears, prefix edits and the bool/loop CPU-visible sentinel.
    assert(!std::memcmp(base+dev+4,reference.data()+dev+4,11996));
    assert(trial.r1.u64==old.r1.u64 && trial.lr==old.lr && trial.lr==0x12345678);
    assert(trial.r30.u64==old.r30.u64 && trial.r31.u64==old.r31.u64);
    assert(stats.pending==0);
  }
  assert(stats.produced>0 && (!FlushEnabled() || stats.collected>stats.produced) && stats.consumed==stats.produced);
  std::printf("PASS C1 actual outer flush: 1200 masks/alignments, CP range/order/side effects, ABI, all device bytes; %u words/%u batches\n",unsigned(stats.words.load()),unsigned(stats.produced.load()));
}
static void Boundaries() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();
  // Ordered/repeated lower-address writes are valid and not sorted away.
  Batch b{};uint32_t raw[1024]{};assert(Append(b,UINT64_MAX,0x4900,1,raw));
  assert(Append(b,1ull<<63,0x2000,1,raw));assert(Append(b,1ull<<63,0x4900,1,raw));assert(b.Valid());
  auto saved=b;assert(!Append(b,UINT64_MAX,0x4000,16,raw));assert(!std::memcmp(&saved,&b,sizeof(b)));
  b={};assert(Append(b,0xAAAAAAAAAAAAAAAAull,0x4000,1,raw));saved=b;
  assert(!Append(b,1ull<<63,0x2000,1,raw));assert(!std::memcmp(&saved,&b,sizeof(b)));
  for(unsigned alignment=0;alignment<16;alignment+=4)for(unsigned n=0;n<80;++n) {
    uint64_t mask=(n%2?0xAAAAAAAA00000000ull:0xffffffff00000000ull);
    auto c=Context();c.r4.u64=mask;c.r5.u32=0x4800;c.r6.u32=dev+1152;
    Store(base,dev,ring+alignment);Store(base,dev+4,ring+8192);
    original_sub_825A2968(c,base);assert(Load(base,dev)==FetchEnd(ring+alignment,ring+8192,mask));
  }
  Init(base,UINT64_MAX<<60,0,0,0);Store64(base,dev+32,0);Store64(base,dev+48,0);Store64(base,dev+40,0);
  assert(!WorthCollecting(base,dev));Store64(base,dev+24,UINT64_MAX<<60);assert(WorthCollecting(base,dev));
  // Snapshot later source edits cannot change an already-owned run.
  auto snapshot=Context();snapshot.r4.u64=UINT64_MAX<<48;snapshot.r5.u32=0x4000;snapshot.r6.u32=dev+1920;snapshot.lr=0x825A3F80;
  Store(base,dev+1920,0x1234);Collector owned(base,dev);assert(owned.AddCall(snapshot,16));
  Store(base,dev+1920,0x5678);owned.Flush();Decoded saved_source;Decode(saved_source,base,ring,Load(base,dev));
  assert(saved_source.cp.registers.values[0x4000]==0x1234);
  // Unknown observer flushes the collected prefix before its original work.
  Init(base,0,0,0,0);auto c=Context();c.r4.u64=UINT64_MAX<<48;c.r5.u32=0x4000;c.r6.u32=dev+1920;c.lr=0x825A3F80;
  Collector prefix(base,dev);assert(prefix.AddCall(c,16));assert(Load(base,dev)==ring);
  c.lr=0;assert(!prefix.AddCall(c,16));assert(Load(base,dev)>ring);assert(!prefix.lease);
  Decoded out;Decode(out,base,ring,Load(base,dev));assert(out.operations.size()==1);
  // Capacity failure flushes the owned prefix and admits this call separately.
  Init(base,0,0,0,0);c=Context();c.r4.u64=UINT64_MAX;c.r5.u32=0x4000;c.r6.u32=dev+1920;c.lr=0x825A3F80;
  Collector cap(base,dev);assert(cap.AddCall(c,16));c.r5.u32=0x4400;c.r6.u32=dev+6016;c.lr=0x825A3FA4;
  assert(cap.AddCall(c,16));cap.Flush();Decoded two;Decode(two,base,ring,Load(base,dev));assert(two.operations.size()==2);
  // If the original suffix needs the segment helper, the already-collected
  // prefix is committed first, and the current original writer is called once.
  Init(base,UINT64_MAX<<48,UINT64_MAX,0,0);Store64(base,dev+48,0);Store(base,dev+4,ring+1200);
  c=Context();try{Candidate(c,base);assert(false);}catch(const Slow&){}
  Decoded before_slow;Decode(before_slow,base,ring,Load(base,dev));assert(before_slow.operations.size()==1);
  // Actual nested outer hook commits a pending parent before running either
  // its admitted inner work or a sparse inner exception, then restores TLS.
  Init(base,0,0,0,0);Store64(base,dev+48,0);c=Context();c.r4.u64=UINT64_MAX<<48;
  c.r5.u32=0x4000;c.r6.u32=dev+1920;c.lr=0x825A3F80;
  Collector parent(base,dev);assert(parent.AddCall(c,16));active=&parent;
  const uint32_t nested_dev=0x10000,nested_ring=0x120000;
  std::memcpy(base+nested_dev,base+dev,12000);Store(base,nested_dev,nested_ring);Store(base,nested_dev+4,nested_ring+8192);
  Store64(base,nested_dev+16,UINT64_MAX<<60);Store64(base,nested_dev+24,UINT64_MAX<<60);
  auto nested=Context();nested.r3.u32=nested_dev;Candidate(nested,base);
  assert(active==&parent && !parent.lease);Decoded inner;Decode(inner,base,nested_ring,Load(base,nested_dev));
  assert(inner.operations.size()>=2);
  Store64(base,nested_dev+16,1ull<<63);Store64(base,nested_dev+24,0);Store(base,nested_dev+4,Load(base,nested_dev)+4);
  nested=Context();nested.r3.u32=nested_dev;
  try{Candidate(nested,base);assert(false);}catch(const Slow&){}
  assert(active==&parent);active=nullptr;Decoded outer_prefix;Decode(outer_prefix,base,ring,Load(base,dev));
  assert(outer_prefix.operations.size()==1 && stats.pending==0);
  // Refused source/ring aliases do not modify guest bytes or skip a write.
  Init(base,0,0,0,0);c=Context();c.r4.u64=UINT64_MAX<<48;c.r5.u32=0x4000;c.r6.u32=dev+1920;c.lr=0x825A3F80;
  Store(base,dev,dev+64);auto untouched=memory;Collector alias(base,dev);
  assert(!alias.AddCall(c,16));assert(memory==untouched);
  // Backend/missing-consumer gates must retain the complete original stream.
  for(unsigned gate=0;gate<3;++gate) {
    Init(base,UINT64_MAX<<60,UINT64_MAX<<60,UINT64_MAX<<60,UINT64_MAX);
    auto reference=memory;auto old=Context();c=old;
    original_reference_outer(old,reference.data());auto before=stats.flushes.load();
    if(gate==0)native_mode=false;
    if(gate==1)flag_gpu_backend="vulkan";
    if(gate==2)rex_native_register_batch_hook=nullptr;
    Candidate(c,base);
    native_mode=true;flag_gpu_backend="native";rex_native_register_batch_hook=&Consume;
    assert(memory==reference && stats.flushes==before);
  }
  // Exhausted pool: no skipped state, the full actual flush remains original.
  std::vector<Batches::Reservation> leases;for(unsigned i=0;i<2048;++i){auto l=Storage()->Reserve();assert(l);leases.push_back(std::move(l));}
  Init(base,UINT64_MAX<<60,UINT64_MAX<<60,0,UINT64_MAX);c=Context();auto reference=memory;auto old=c;
  original_reference_outer(old,reference.data());Candidate(c,base);
  assert(Load(base,dev)==Load(reference.data(),dev));leases.clear();assert(stats.pending==0);
  assert(active==nullptr);
  std::puts("PASS C1 ordered/repeated runs, untouched capacity rejection, fetch alignment, prefix/unknown/segment/capacity barriers nested/exception TLS, aliases and pool exhaustion");
}
static void HighAliasFlush() {
  constexpr size_t bytes=0x100002000ull;
  auto* base=static_cast<uint8_t*>(mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));assert(base!=MAP_FAILED);
  const uint32_t device=0xE0001000,first=0xE1000000;
  for(unsigned i=0;i<3000;++i)Store(base,device+i*4,i+17);
  Store(base,device,first);Store(base,device+4,first+8192);
  Store64(base,device+16,UINT64_MAX<<60);Store64(base,device+24,UINT64_MAX<<60);
  Store64(base,device+32,UINT64_MAX<<60);Store64(base,device+40,0);Store64(base,device+48,0);
  auto c=Context();c.r3.u32=device;Candidate(c,base);NativeOracle cp;
  Replay(cp,base,first,Load(base,device));
  for(unsigned i=0;i<64;++i){assert(cp.registers.values[0x4000+i]==1920/4+i+17);assert(cp.registers.values[0x4400+i]==6016/4+i+17);}
  for(unsigned i=0;i<24;++i)assert(cp.registers.values[0x4800+i]==1152/4+i+17);
  assert(Load64(base,device+16)==0 && Load64(base,device+24)==0 && Load64(base,device+32)==0 && !stats.pending);
  // A raw source crossing the high-physical skew must stay original.
  c=Context();c.r3.u32=0xE0000000u-1920-64;c.r6.u32=c.r3.u32+1920;c.r4.u64=UINT64_MAX<<48;c.r5.u32=0x4000;c.lr=0x825A3F80;
  Collector crossing(base,c.r3.u32);assert(!crossing.AddCall(c,16));
  munmap(base,bytes);std::puts("PASS C1 actual outer flush high-physical mapping and cross-skew rejection");
}
static void BenchmarkSparse() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();
  for(unsigned i=0;i<3000;++i)Store(base,dev+i*4,i+123);
  for(unsigned bits:{0u,1u,4u,16u})for(bool pair:{false,true}) {
    if(!bits && pair)continue;
    uint64_t mask=bits?UINT64_MAX<<(64-bits):0;
    std::vector<double> times[3];uint64_t tokens[3]{};
    for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<3;++arm) {
      unsigned mode=(trial+arm)%3;NativeOracle cp;auto c=Context();
      auto start=std::chrono::steady_clock::now();auto before=stats.produced.load();
      for(unsigned i=0;i<10000;++i) {
        Store(base,dev,ring);Store(base,dev+4,ring+0x80000);
        Store64(base,dev+16,mask);Store64(base,dev+24,pair?mask:0);
        Store64(base,dev+32,0);Store64(base,dev+40,0);Store64(base,dev+48,0);
        if(mode==0)original_reference_outer(c,base);
        else if(mode==1)original_c0_outer(c,base);else Candidate(c,base);
        cp.side_effect_calls.clear();Replay(cp,base,ring,Load(base,dev));
        c.r3.u32=dev;asm volatile("" : : "r"(cp.registers.values) : "memory");
      }
      tokens[mode]=stats.produced.load()-before;
      times[mode].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
    }
    for(auto& t:times)std::sort(t.begin(),t.end());
    std::printf("Host sparse %u ALU words, %u banks: original %.3f / C0 %.3f / C1+C0 %.3f ms per10000; tokens %llu/%llu/%llu (host only)\n",bits*16,pair?2:1,times[0][3],times[1][3],times[2][3],tokens[0],tokens[1],tokens[2]);
  }
}
static void BenchmarkAggregate() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();
  for(unsigned i=0;i<3000;++i)Store(base,dev+i*4,i+123);
  for(unsigned bits:{1u,4u,8u,16u,32u,64u}) {
    uint64_t mask=UINT64_MAX<<(64-bits);std::vector<double> times[3];unsigned bytes[3]{};
    for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<3;++arm) {
      unsigned mode=(trial+arm)%3;NativeOracle cp;auto c=Context();
      auto start=std::chrono::steady_clock::now();
      for(unsigned i=0;i<10000;++i) {
        // Both ALU banks, four fetch groups and the normal scalar state banks.
        Init(base,mask,mask,UINT64_MAX<<60,0x8888888888888888ull);
        if(mode==0)original_reference_outer(c,base);
        else if(mode==1)original_c0_outer(c,base);else Candidate(c,base);
        bytes[mode]=Load(base,dev)-ring;cp.side_effect_calls.clear();Replay(cp,base,ring,Load(base,dev));
        c.r3.u32=dev;asm volatile("" : : "r"(cp.registers.values) : "memory");
      }
      times[mode].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
    }
    for(auto& t:times)std::sort(t.begin(),t.end());
    std::printf("Host aggregate %u ALU words/bank + fetch/scalars: original %.3f / C0 %.3f / C1 %.3f ms per10000; ring bytes %u/%u/%u (host only, no energy proof)\n",bits*16,times[0][3],times[1][3],times[2][3],bytes[0],bytes[1],bytes[2]);
  }
}
int main(int argc,char** argv){bool on=argc==1 || std::string_view(argv[1])=="c0-off";flag_nfsmw_native_register_flushes=on;flag_nfsmw_native_register_batches=argc==1 || std::string_view(argv[1])!="c0-off";FlushDifferential();if(on){Boundaries();HighAliasFlush();if(argc==1){@BENCHMARK@}}else {assert(stats.flushes==0 && stats.collected==0);std::puts("PASS C1 disabled outer route retains C0");}}
'''
benchmark='--benchmark' in sys.argv
program=program.replace('@BENCHMARK@','BenchmarkSparse();BenchmarkAggregate();' if benchmark else '')
with tempfile.TemporaryDirectory(prefix='nfsmw-flush-candidate-') as tmp:
    path,exe=Path(tmp)/'test.cpp',Path(tmp)/'test';path.write_text(program)
    options=['-O2'] if benchmark else ['-O1','-g','-fsanitize=address,undefined']
    subprocess.run(['clang++','-std=c++20',*options,'-fno-omit-frame-pointer',
        '-I',str(ROOT/'ios/src'),'-I',str(ROOT/'tools/native'),'-I',str(SDK/'thirdparty/simde'),
        str(path),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
    subprocess.run([str(exe),'off'],check=True)
    if not benchmark:subprocess.run([str(exe),'c0-off'],check=True)
