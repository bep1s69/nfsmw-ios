#!/usr/bin/env python3
"""Differential against actual generated USA emitters; no GPU/guest execution."""
from pathlib import Path
import subprocess
import tempfile
import re

ROOT=Path(__file__).resolve().parents[2]
SDK=ROOT.parent/'nfsmw-multiplayer-sdk'
def emitter(file,name):
    text=(ROOT/'ios/generated/default'/file).read_text()
    start=text.index('DEFINE_REX_FUNC('+name+') {')
    end=text.find('\nDEFINE_REX_FUNC(',start+1)
    return text[start:end if end>=0 else len(text)]
def function(text,signature):
    start=text.index(signature);pos=text.index('{',start);end=pos+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]

CODE=r'''
#include "native_register_batch.h"
#include <simde/x86/ssse3.h>
#include <cassert>
#include <vector>
#include <random>
#include <thread>
#include <mutex>
#include <deque>
#include <cstdio>
#include <stdexcept>
#include <string_view>
using namespace nfsmw::register_batch;
union PPCRegister {uint64_t u64;int64_t s64;uint32_t u32;int32_t s32;uint8_t u8;};
struct Xer {bool ca=false;};
struct PPCCRRegister {bool lt=false,gt=false,eq=false;
  template<class T,class A,class B> void compare(A a,B b,const Xer&) {lt=T(a)<T(b);gt=T(a)>T(b);eq=T(a)==T(b);}};
struct alignas(16) Vec {uint8_t u8[16];};
struct PPCContext { @REGISTERS@ @VECTORS@ Xer xer;uint64_t lr;};
alignas(16) uint8_t VectorMaskL[]={15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0};
static size_t HostOffset(uint32_t at){return size_t(at)+(at>=0xE0000000u?0x1000:0);}
static uint32_t Load(uint8_t* base,uint32_t at){uint32_t n;std::memcpy(&n,base+HostOffset(at),4);return __builtin_bswap32(n);}
static void Store(uint8_t* base,uint32_t at,uint32_t n){n=__builtin_bswap32(n);std::memcpy(base+HostOffset(at),&n,4);}
#define REX_LOAD_U32(at) Load(base,at)
#define REX_STORE_U32(at,n) Store(base,at,n)
#define REX_RAW_ADDR(at) (base+HostOffset(at))
#define REX_FUNC_PROLOGUE()
#define DEFINE_REX_FUNC(name) void name(PPCContext& ctx,uint8_t* base)
static void __savegprlr_25(PPCContext&,uint8_t*){}
static void __savegprlr_26(PPCContext&,uint8_t*){}
static void __restgprlr_25(PPCContext& c,uint8_t*){c.lr=c.r12.u64;}
static void __restgprlr_26(PPCContext& c,uint8_t*){c.lr=c.r12.u64;}
struct Slow{};
static void sub_825A27F0(PPCContext&,uint8_t*){throw Slow{};}
@EMITTERS@
namespace memory {
struct RingBuffer {
  uint32_t* data;size_t count,at=0;
  size_t read_count(){return (count-at)*4;}
  template<class T>T ReadAndSwap(){assert(at<count);return T(__builtin_bswap32(data[at++]));}
};
inline void copy_and_swap(uint32_t* to,uint32_t* from,size_t count){for(size_t i=0;i<count;++i)to[i]=__builtin_bswap32(from[i]);}
}
constexpr uint32_t XE_GPU_REG_SHADER_CONSTANT_000_X=0x4000,XE_GPU_REG_SHADER_CONSTANT_511_W=0x47ff;
constexpr uint32_t XE_GPU_REG_SHADER_CONSTANT_FETCH_00_0=0x4800,XE_GPU_REG_SHADER_CONSTANT_FETCH_31_5=0x48bf;
constexpr uint32_t XE_GPU_REG_SHADER_CONSTANT_BOOL_000_031=0x4900,XE_GPU_REG_SHADER_CONSTANT_LOOP_31=0x4927;
bool bulk=true;
bool Flag(std::string_view name){if(name=="ios_native_bulk_constants")return bulk;assert(name=="ios_type0_ranges");return true;}
#define REXCVAR_GET(n) Flag(#n)
#define REX_PLATFORM_IOS 1
#define REXGPU_ERROR(...) assert(false)
struct OracleCP {
  struct Registers {uint32_t values[0x6000]{};} registers;
  Registers* register_file_=&registers;
  std::vector<std::pair<uint32_t,uint32_t>> side_effect_calls;
  void WriteRegister(uint32_t reg,uint32_t value){registers.values[reg]=value;side_effect_calls.emplace_back(reg,value);}
  virtual void WriteRegistersFromMem(uint32_t reg,uint32_t* data,uint32_t count){for(unsigned i=0;i<count;++i)WriteRegister(reg+i,__builtin_bswap32(data[i]));}
  void WriteRegisterRangeFromRing(memory::RingBuffer* ring,uint32_t reg,uint32_t count){WriteRegistersFromMem(reg,ring->data+ring->at,count);ring->at+=count;}
  bool ExecutePacketType0(memory::RingBuffer* reader,uint32_t packet);
};
@TYPE0@
struct NativeOracle : OracleCP {
  uint64_t constant_ranges_=0,constant_words_=0,bulk_ranges_=0,bulk_words_=0,fallback_ranges_=0,fallback_words_=0;
  @NATIVE_RANGE@
};
static void Differential() {
  std::vector<uint8_t> memory(2<<20);auto* base=memory.data();
  std::mt19937_64 rng(122);const uint32_t dev=0x1000,source=0x4000,ring=0x100000,limit=0x180000;
  for(uint32_t group:{1u,16u})for(unsigned n=0;n<260;++n)for(unsigned alignment=0;alignment<16;alignment+=4) {
    uint64_t mask=n==0?UINT64_MAX:n==1?1:n==2?(1ull<<63):n==3?0xAAAAAAAAAAAAAAAAull:rng();
    for(unsigned i=0;i<1024;++i)Store(base,source+i*4,uint32_t(rng()));
    auto* raw=reinterpret_cast<const uint32_t*>(base+source);
    Batch batch{};assert(Build(batch,mask,group==1?0x2300:0x4000,group,{raw,1024})&&batch.Valid());
    const auto snapshot=batch;
    PPCContext ctx{};ctx.r1.u32=0x80000;ctx.r3.u32=dev;ctx.r4.u64=mask;ctx.r5.u32=group==1?0x2300:0x4000;ctx.r6.u32=source;
    const uint32_t last=ring+alignment;Store(base,dev,last);Store(base,dev+4,limit);
    if(group==1)sub_825A28A8(ctx,base);else sub_825A2A60(ctx,base);
    uint32_t end=Load(base,dev);
    assert(end==OriginalEnd(last,limit,mask,group));
    // Only the proved fast path: save/restore and slow segment helper are
    // stand-ins; actual generated scalar + VMX copy/packet body executes.
    assert(ctx.r3.u32==dev);
    std::vector<std::pair<uint32_t,uint32_t>> decoded,expected;
    NativeOracle old_cp,new_cp;bulk=n%2;
    for(uint32_t at=last+4;at<=end;) {
      uint32_t header=Load(base,at);at+=4;
      if(header>>30==2)continue;
      assert(header>>30==0 && !(header&0x8000));
      uint32_t count=((header>>16)&0x3fff)+1,reg=header&0x7fff;
      memory::RingBuffer reader{reinterpret_cast<uint32_t*>(base+at),count};
      assert(old_cp.ExecutePacketType0(&reader,header));
      for(uint32_t i=0;i<count;++i,at+=4)decoded.emplace_back(reg+i,Load(base,at));
    }
    for(unsigned i=0;i<batch.run_count;++i) {
      auto r=batch.runs[i];for(unsigned j=0;j<r.count;++j)
        expected.emplace_back(r.reg+j,__builtin_bswap32(batch.words[r.offset+j]));
      new_cp.WriteRegistersFromMem(r.reg,batch.words.data()+r.offset,r.count);
    }
    assert(decoded==expected);
    assert(!std::memcmp(old_cp.registers.values,new_cp.registers.values,sizeof(old_cp.registers.values)));
    assert(old_cp.side_effect_calls==new_cp.side_effect_calls);
    std::memset(base+source,0,4096);assert(std::memcmp(&snapshot,&batch,sizeof(batch))==0);
    uint32_t token_end=TokenEnd(last,end);
    if(batch.word_count>=16)assert(token_end && token_end<=end && (token_end&15)==(end&15));
    // Force original slow helper at its first run: admission must reject.
    assert(!OriginalEnd(last,last+4,mask,group));
    ctx={};ctx.r1.u32=0x80000;ctx.r3.u32=dev;ctx.r4.u64=mask;ctx.r5.u32=group==1?0x2300:0x4000;ctx.r6.u32=source;
    Store(base,dev,last);Store(base,dev+4,last+4);
    try{if(group==1)sub_825A28A8(ctx,base);else sub_825A2A60(ctx,base);assert(false);}catch(const Slow&){}
  }
  Batch batch{};batch.word_count=17;auto before=batch;
  uint32_t source_words[1024]{};
  assert(!Build(batch,0,0x4000,16,source_words));
  assert(!Build(batch,1,0x4000,16,{source_words,1023}));
  assert(!Build(batch,1,0x5fff,1,source_words));
  assert(!Build(batch,1,0x4000,4,source_words));
  assert(!std::memcmp(&before,&batch,sizeof(batch)));
}
static void Ownership() {
  Pool<2> pool;uint32_t source[64];for(unsigned i=0;i<64;++i)source[i]=i;
  auto a=pool.Reserve(),b=pool.Reserve();assert(a&&b&&!pool.Reserve());
  assert(!a.Publish()); // unbuilt/reused storage cannot be published
  assert(Build(a.Data(),UINT64_MAX,0x4000,1,source));
  uint64_t token=a.Publish();assert(token);std::fill(std::begin(source),std::end(source),999u);
  unsigned writes=0;assert(pool.Consume(token,[&](auto reg,auto* words,auto count){assert(reg==0x4000&&count==64&&words[63]==63);++writes;}));
  assert(writes==1&&!pool.Consume(token,[](auto,auto*,auto){assert(false);}));
  auto c=pool.Reserve();assert(c&&!c.Publish());
  assert(!pool.Consume(token,[](auto,auto*,auto){assert(false);})); // ABA after same slot reused
  assert(Build(c.Data(),UINT64_MAX,0x4000,1,source));auto next=c.Publish();assert(next!=token);
  try {pool.Consume(next,[](auto,auto*,auto){throw std::runtime_error("fixture");});assert(false);}catch(const std::runtime_error&){}
  assert(pool.Reserve()); // consumer unwinding still returns slot
  Pool<2> exhausted(UINT64_MAX);assert(!exhausted.Reserve());
  assert(!pool.Consume(0,[](auto,auto*,auto){}));
}
static void Concurrent() {
  Pool<16> pool;std::mutex mutex;std::deque<uint64_t> queue;std::atomic<unsigned> done=0;
  std::vector<unsigned> seen(4000);std::atomic<unsigned> blocked=0;
  auto producer=[&](unsigned p){
    for(unsigned i=0;i<2000;++i) {
      uint32_t words[64];std::fill(std::begin(words),std::end(words),p*2000+i);
      for(;;){auto lease=pool.Reserve();if(!lease){++blocked;std::this_thread::yield();continue;}
        assert(Build(lease.Data(),UINT64_MAX,0x4000,1,words));auto token=lease.Publish();assert(token);
        {std::lock_guard lock(mutex);queue.push_back(token);}break;}
      std::fill(std::begin(words),std::end(words),999999u);
    }++done;
  };
  std::thread a(producer,0),b(producer,1);
  unsigned consumed=0;
  while(consumed<4000) {
    uint64_t token=0;{std::lock_guard lock(mutex);if(!queue.empty()){token=queue.front();queue.pop_front();}}
    if(!token){std::this_thread::yield();continue;}
    assert(pool.Consume(token,[&](auto reg,auto* words,auto count){
      assert(reg==0x4000&&count==64&&words[0]<seen.size());
      for(unsigned j=0;j<count;++j)assert(words[j]==words[0]);++seen[words[0]];
    }));++consumed;
  }
  a.join();b.join();assert(done==2);for(auto n:seen)assert(n==1);
}
int main(){Differential();Ownership();Concurrent();std::puts("PASS actual scalar/VMX emitters: masks/alignment/data/order, owned copies, bounds/slow-path admission, cancellation/exhaustion/ABA and concurrent publication/consumption");}
'''
CODE=CODE.replace('@REGISTERS@',' '.join('PPCRegister r'+str(i)+';' for i in range(32)))
CODE=CODE.replace('@VECTORS@',' '.join('Vec v'+str(i)+';' for i in range(32)))
CODE=CODE.replace('@EMITTERS@',emitter('nfsmw_recomp.56.cpp','sub_825A28A8')+'\n'+emitter('nfsmw_recomp.22.cpp','sub_825A2A60'))
CODE=CODE.replace('@TYPE0@',function((SDK/'src/graphics/command_processor.cpp').read_text(),'bool CommandProcessor::ExecutePacketType0(').replace('CommandProcessor::','OracleCP::'))
CODE=CODE.replace('@NATIVE_RANGE@',function((SDK/'src/graphics/plugin_main.cpp').read_text(),'void WriteRegistersFromMem(').replace('CommandProcessor::','OracleCP::'))
def verify_sites():
    flush=emitter('nfsmw_recomp.85.cpp','sub_825A3EC8')
    found={};reg=offset=lr=None
    for line in flush.splitlines():
        m=re.search(r'// li r5,(\d+)',line)
        if m:reg=int(m[1])
        m=re.search(r'// addi r6,r31,(\d+)',line)
        if m:offset=int(m[1])
        m=re.search(r'ctx.lr = 0x([0-9A-F]+)',line)
        if m:lr=int(m[1],16)
        for name,group in [('sub_825A28A8',1),('sub_825A2A60',16)]:
            if name+'(ctx, base)' in line:found[lr]=(reg,offset,group)
    header=(ROOT/'ios/src/native_register_batch.h').read_text()
    sites=re.findall(r'\{(0x[0-9A-F]+),(0x[0-9A-F]+),(\d+),(\d+),(\d+)\}',header)
    assert len(sites)==10 and len(found)==10
    for pc,base,offset,words,group in sites:
        assert found[int(pc,16)]==(int(base,16),int(offset),int(group))

if __name__=='__main__':
    verify_sites()
    with tempfile.TemporaryDirectory(prefix='nfsmw-register-batch-') as tmp:
        path,exe=Path(tmp)/'test.cpp',Path(tmp)/'test';path.write_text(CODE)
        subprocess.run(['clang++','-std=c++20','-O1','-g','-fsanitize=address,undefined',
            '-fno-omit-frame-pointer','-I',str(ROOT/'ios/src'),'-I',str(SDK/'thirdparty/simde'),
            str(path),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
