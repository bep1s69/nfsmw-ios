#!/usr/bin/env python3
"""Actual app hooks + SDK NOP/type0/range methods, with guest/ABI stand-ins."""
from test_register_batches import CODE, ROOT, SDK, function
from pathlib import Path
import os
import subprocess
import sys
import tempfile
sys.path.insert(0,str(ROOT/'tools/ios'))
from patch_ios_register_batches import BLOCKS

originals={name:(SDK/name).read_text() for name,_,_,_ in BLOCKS}
for name,_,before,after in reversed(BLOCKS):
    if after in originals[name]:originals[name]=originals[name].replace(after,before)
with tempfile.TemporaryDirectory(prefix='nfsmw-register-patch-') as tmp:
    root=Path(tmp)
    for name,text in originals.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    env=dict(os.environ,NFSMW_SDK=tmp)
    command=[sys.executable,str(ROOT/'tools/ios/patch_ios_register_batches.py')]
    subprocess.run(command,env=env,check=True)
    patched={name:(root/name).read_text() for name in originals}
    subprocess.run(command,env=env,check=True)
    assert patched=={name:(root/name).read_text() for name in originals}
    subprocess.run(command+['--revert'],env=env,check=True)
    assert originals=={name:(root/name).read_text() for name in originals}

program=CODE.replace('#define DEFINE_REX_FUNC(name) void name(', '#define DEFINE_REX_FUNC(name) void original_##name(')
for name in ['sub_825A28A8','sub_825A2A60']:
    program=program.replace(name+'(ctx,base)', 'original_'+name+'(ctx,base)')
program=program.replace('size_t read_count(){','void AdvanceRead(size_t bytes){at+=bytes/4;assert(at<=count);}\n  size_t read_count(){')
program=program.replace('bool ExecutePacketType0(memory::RingBuffer* reader,uint32_t packet);',
    'bool ExecutePacketType0(memory::RingBuffer* reader,uint32_t packet);\n  bool ExecutePacketType3_NOP(memory::RingBuffer*,uint32_t,uint32_t);')
program=program[:program.index('int main(){')]
program+=r'''
#include <chrono>
#include <sys/mman.h>
#undef REXCVAR_GET
#undef REXGPU_ERROR
#define REXCVAR_GET(n) flag_##n
#define REXCVAR_DEFINE_BOOL(...)
#define REXCVAR_DECLARE(...)
#define REXLOG_INFO(...)
#define REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)
bool flag_nfsmw_native_register_batches=true;
bool flag_nfsmw_native_register_flushes=false;
extern "C" void __imp__sub_825A2968(PPCContext&,uint8_t*);
extern "C" void __imp__sub_825A3EC8(PPCContext&,uint8_t*);
std::string flag_gpu_backend="native";
bool native_mode=true;
extern "C" bool nfsmw_native_cp_mode(){return native_mode;}
unsigned fallback_calls=0,errors=0;
#define REXGPU_ERROR(...) (++errors)
extern "C" void __imp__sub_825A28A8(PPCContext& c,uint8_t* b){++fallback_calls;original_sub_825A28A8(c,b);}
extern "C" void __imp__sub_825A2A60(PPCContext& c,uint8_t* b){++fallback_calls;original_sub_825A2A60(c,b);}
'''
live=(ROOT/'ios/src/native_register_batches.cpp').read_text()
live='\n'.join(line for line in live.splitlines() if not any(x in line for x in
    ['#include "nfsmw_pch.h"','#include <rex/cvar.h>','#include <rex/logging.h>']))
program+=live+r'''
std::atomic<RexNativeRegisterBatch> rex_native_register_batch_hook{&Consume};
std::atomic<uint32_t> rex_native_draw_marker{0};
'''
# Isolated bridge does not invoke these new outer/fetch entries. C1's fixture
# replaces the stubs with actual generated bodies.
program+=r'''
extern "C" void __imp__sub_825A2968(PPCContext&,uint8_t*){}
extern "C" void __imp__sub_825A3EC8(PPCContext&,uint8_t*){}
'''
program+=function(patched['src/graphics/command_processor.cpp'],
    'bool CommandProcessor::ExecutePacketType3_NOP(').replace('CommandProcessor','OracleCP')
program+=r'''
static void Replay(NativeOracle& cp,uint8_t* base,uint32_t last,uint32_t end) {
  for(uint32_t at=last+4;at<=end;) {
    uint32_t header=Load(base,at);at+=4;
    if(header>>30==2)continue;
    uint32_t count=((header>>16)&0x3fff)+1;
    memory::RingBuffer reader{reinterpret_cast<uint32_t*>(REX_RAW_ADDR(at)),count};
    if(header>>30==0)assert(cp.ExecutePacketType0(&reader,header));
    else {assert(((header>>8)&127)==0x10);assert(cp.ExecutePacketType3_NOP(&reader,header,count));}
    at+=count*4;
  }
}
static void Bridge(bool off) {
  std::vector<uint8_t> mem(2<<20),reference;auto* base=mem.data();
  const uint32_t device=0x1000,ring=0x100000,limit=0x180000;
  std::mt19937_64 rng(123);
  for(const auto& site:kSites)for(unsigned n=0;n<32;++n)for(unsigned alignment=0;alignment<16;alignment+=4) {
    // Valid exact role bounds, arbitrary sparse/full dirty masks.
    unsigned bits=site.words/site.group;
    uint64_t allowed=bits==64?UINT64_MAX:UINT64_MAX<<(64-bits);
    uint64_t mask=n==0?allowed:rng()&allowed;if(!mask)mask=1ull<<63;
    for(unsigned i=0;i<site.words;++i)Store(base,device+site.offset+i*4,uint32_t(rng()));
    const uint32_t last=ring+alignment;Store(base,device,last);Store(base,device+4,limit);
    PPCContext c{};c.r1.u32=0x80000;c.r3.u32=device;c.r4.u64=mask;c.r5.u32=site.reg;c.r6.u32=device+site.offset;c.lr=site.lr;
    auto old=c;reference=mem;
    if(site.group==1)original_sub_825A28A8(old,reference.data());else original_sub_825A2A60(old,reference.data());
    unsigned before=fallback_calls;
    if(site.group==1)sub_825A28A8(c,base);else sub_825A2A60(c,base);
    assert(c.r3.u64==old.r3.u64 && c.lr==site.lr);
    if(off)assert(fallback_calls==before+1);
    NativeOracle a,b;Replay(a,reference.data(),last,Load(reference.data(),device));
    Replay(b,base,last,Load(base,device));
    assert(!std::memcmp(a.registers.values,b.registers.values,sizeof(a.registers.values)));
    assert(a.side_effect_calls==b.side_effect_calls);
    if(!off)assert((Load(base,device)&15)==(Load(reference.data(),device)&15));
  }
  if(off)return;
  assert(stats.produced.load()>0 && stats.consumed==stats.produced && stats.pending==0 && errors==0);
  PPCContext c{};c.r1.u32=0x80000;c.r3.u32=device;c.r4.u64=UINT64_MAX;c.r5.u32=0x4000;c.r6.u32=device+1920;c.lr=0x825A3F80;
  Store(base,device,ring);Store(base,device+4,limit);
  auto untouched=mem;
  auto reject=[&](PPCContext bad){assert(!Try(bad,base,16));assert(mem==untouched);};
  auto bad=c;bad.lr=0;reject(bad);bad=c;bad.r6.u32+=4;reject(bad);
  bad=c;bad.r5.u32++;reject(bad);bad=c;bad.r4.u64=0;reject(bad);
  Store(base,device+4,ring+4);untouched=mem;reject(c);Store(base,device+4,limit);untouched=mem;
  native_mode=false;reject(c);native_mode=true;
  std::vector<Batches::Reservation> leases;leases.reserve(2048);
  for(unsigned i=0;i<2048;++i){auto lease=Storage()->Reserve();assert(lease);leases.push_back(std::move(lease));}
  reject(c);leases.clear();assert(stats.pending==0);
  // Ordinary NOP, malformed version, stale and missing-hook tokens fail/skip
  // exactly as defined; no register writes from invalid native tokens.
  NativeOracle cp;uint32_t data[4];
  auto nop=[&](uint32_t magic,uint32_t version,uint64_t ticket){
    data[0]=__builtin_bswap32(magic);data[1]=__builtin_bswap32(version);
    data[2]=__builtin_bswap32(uint32_t(ticket));data[3]=__builtin_bswap32(uint32_t(ticket>>32));
    memory::RingBuffer r{data,4};return cp.ExecutePacketType3_NOP(&r,kHeader,4);
  };
  assert(nop(0,1,99));assert(!nop(kMagic,2,99));assert(!nop(kMagic,1,99));
  rex_native_register_batch_hook=nullptr;assert(!nop(kMagic,1,99));rex_native_register_batch_hook=&Consume;
  assert(cp.side_effect_calls.empty()&&errors==3);
  std::printf("PASS live bridge: %llu batches consumed; exact guest-emitter/CP register and side-effect order; untouched early fallback; malformed/stale/unavailable tokens rejected\n",stats.consumed.load());
}
static void Benchmark() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();
  for(const auto& site:kSites) {
    if(site.reg!=0x2300 && site.reg!=0x4000)continue;
    for(unsigned bits:{1u,4u,8u,16u,32u}) {
      if(bits*site.group<16)continue;
      const uint64_t mask=UINT64_MAX<<(64-bits);
      for(unsigned i=0;i<site.words;++i)Store(base,0x1000+site.offset+i*4,i);
      std::vector<double> times[2];
      for(unsigned trial=0;trial<7;++trial)for(unsigned arm=0;arm<2;++arm) {
        const unsigned native=(trial+arm)%2;
        NativeOracle cp;PPCContext c{};c.r1.u32=0x80000;
        auto start=std::chrono::steady_clock::now();
        for(unsigned i=0;i<10000;++i) {
          Store(base,0x1000,0x100000);Store(base,0x1004,0x180000);
          c.r3.u32=0x1000;c.r4.u64=mask;c.r5.u32=site.reg;c.r6.u32=0x1000+site.offset;c.lr=site.lr;
          if(native){if(site.group==1)sub_825A28A8(c,base);else sub_825A2A60(c,base);}
          else {if(site.group==1)original_sub_825A28A8(c,base);else original_sub_825A2A60(c,base);}
          cp.side_effect_calls.clear();Replay(cp,base,0x100000,Load(base,0x1000));
          asm volatile("" : : "r"(cp.registers.values) : "memory"); // retain observable writes in BOTH timed arms
        }
        times[native].push_back(std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count());
      }
      for(auto& t:times)std::sort(t.begin(),t.end());
      const bool admitted=bits*site.group>=(site.group==16?256u:32u);
      std::printf("Host only group %u / %u words: original %.3f ms, trial %.3f ms [%s] per10000 (not device CPU/energy)\n",site.group,bits*site.group,times[0][3],times[1][3],admitted?"token":"original fallback");
    }
  }
}
static void Aliases() {
  // Sparse virtual reservation, only touched pages resident. Mirror the real
  // generated ARM64 host skew without allocating a 4GiB physical fixture.
  constexpr size_t bytes=0x100002000ull;
  auto* base=static_cast<uint8_t*>(mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));
  assert(base!=MAP_FAILED);
  for(unsigned group:{1u,16u}) {
    const Site& site=group==1?kSites[0]:kSites[2];
    uint32_t device=0xE0001000,ring=0xE1000000;
    for(unsigned i=0;i<site.words;++i)Store(base,device+site.offset+i*4,i+123);
    PPCContext c{};c.r3.u32=device;c.r4.u64=group==1?UINT64_MAX<<(64-38):UINT64_MAX;
    c.r5.u32=site.reg;c.r6.u32=device+site.offset;c.lr=site.lr;
    Store(base,device,ring);Store(base,device+4,ring+8192);
    assert(Try(c,base,group));NativeOracle cp;Replay(cp,base,ring,Load(base,device));
    for(unsigned i=0;i<site.words;++i)assert(cp.registers.values[site.reg+i]==i+123);
  }
  // Role data crossing the skew discontinuity stays on original accesses.
  const Site& site=kSites[0];PPCContext c{};
  c.r3.u32=0xE0000000u-site.offset-64;c.r6.u32=c.r3.u32+site.offset;
  c.r4.u64=UINT64_MAX<<(64-32);c.r5.u32=site.reg;c.lr=site.lr;
  assert(!Try(c,base,1));assert(stats.pending==0);
  munmap(base,bytes);std::puts("PASS high-physical guest host skew and cross-boundary fallback");
}
int main(int argc,char**){flag_nfsmw_native_register_batches=argc==1;Bridge(argc>1);if(argc>1)std::puts("PASS disabled route invokes original writer exactly once");else Aliases();@BENCHMARK@}
'''
benchmark='--benchmark' in sys.argv
program=program.replace('@BENCHMARK@','if(argc==1)Benchmark();' if benchmark else '')
def main():
    with tempfile.TemporaryDirectory(prefix='nfsmw-register-bridge-') as tmp:
        path,exe=Path(tmp)/'test.cpp',Path(tmp)/'test';path.write_text(program)
        options=['-O2'] if benchmark else ['-O1','-g','-fsanitize=address,undefined']
        subprocess.run(['clang++','-std=c++20',*options,
            '-fno-omit-frame-pointer','-I',str(ROOT/'ios/src'),'-I',str(SDK/'thirdparty/simde'),
            str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
        subprocess.run([str(exe),'off'],check=True)

if __name__=='__main__':
    main()
