#!/usr/bin/env python3
"""Host-only actual full descriptor-loop differential and cost gate.

Extracts the original and currently patched USA loops without editing codegen.
No game integration or performance claim follows from a passing host fixture.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ios'))
import patch_game_constant_copies as patch
import patch_game_constant_descriptors as descriptors

SITES = {
    '826991D8': ('Vertex', '965bf79981ceb0b3c67897d2ef412adb61bcf2052666c3287d43480f667125ef'),
    '8269933C': ('Pixel', '7a676ee8ea9391e754f6fb8f1990079de1e7e95d7030a7a4b9485add9f7d0a98'),
}

HARNESS = r'''
#include <rex/ppc/context.h>
#include <rex/ppc/intrinsics.h>
#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>
#define REX_RAW_ADDR(x) (base+uint32_t(x))
#define REX_LOAD_U32(x) __builtin_bswap32(*(volatile uint32_t*)REX_RAW_ADDR(x))
#ifdef INJECT_STORES
static uint32_t inject_descriptor=0,inject_index=0;
static inline void Store32(uint8_t* base,uint32_t at,uint32_t value) {
  *(volatile uint32_t*)(base+at)=__builtin_bswap32(value);
  if(inject_descriptor && at==0x458 && value==4) {
    auto* p=reinterpret_cast<volatile uint32_t*>(base+inject_descriptor);
    *p=__builtin_bswap32((__builtin_bswap32(*p)&~1023u)|inject_index);
    inject_descriptor=0;
  }
}
#define REX_STORE_U32(x,y) Store32(base,uint32_t(x),uint32_t(y))
#else
#define REX_STORE_U32(x,y) (*(volatile uint32_t*)REX_RAW_ADDR(x)=__builtin_bswap32(uint32_t(y)))
#endif
#define REX_LOAD_U64(x) __builtin_bswap64(*(volatile uint64_t*)REX_RAW_ADDR(x))
#define REX_STORE_U64(x,y) (*(volatile uint64_t*)REX_RAW_ADDR(x)=__builtin_bswap64(uint64_t(y)))
#include "@HEADER@"
@REFERENCES@
struct State {
  PPCContext ctx;
  PPCCRRegister cr;
  PPCRegister temp;
  uint32_t ea;
  std::vector<uint8_t> memory;
};
static std::mt19937 bits(0x82699100);
static void Put(State& s,uint32_t at,uint32_t value) {
  auto* base=s.memory.data();REX_STORE_U32(at,value);
}
static uint32_t Get(State& s,uint32_t at) {
  auto* base=s.memory.data();return REX_LOAD_U32(at);
}
static State Fixture(bool pixel,unsigned descriptors,unsigned vectors,int mode=0) {
  State s;
  auto fill=[](auto& value) {
    auto* p=reinterpret_cast<uint8_t*>(&value);
    for(size_t i=0;i<sizeof(value);++i)p[i]=uint8_t(bits());
  };
  fill(s.ctx);fill(s.cr);fill(s.temp);s.ea=bits();
  s.memory.resize(128*1024);
  for(size_t i=0;i<s.memory.size();i+=4) {
    uint32_t v=bits();std::memcpy(s.memory.data()+i,&v,4);
  }
  constexpr uint32_t sp=0x400,desc=0x2000,bindings=0x3000,bank=0x10000;
  uint32_t src=mode==4?sp:0x4000;
  if(mode>=1 && mode<=3)src=bank+(pixel?376:120)*16+(mode-2)*16;
  if(mode==5)src+=8; // unsupported unaligned source base, valid original path
  s.ctx.r1.u64=sp;s.ctx.r11.u64=desc;s.ctx.r18.u64=0x8000000000000000ull;
  s.ctx.r21.u64=bank;s.ctx.r23.u64=bindings;s.ctx.r24.u64=src;
  s.ctx.xer.ca=1;
  Put(s,sp+80,desc);Put(s,sp+92,desc+descriptors*16);
  Put(s,sp+96,bindings);Put(s,sp+100,src);Put(s,sp+120,bank);
  for(unsigned i=0;i<std::max(1u,descriptors);++i) {
    unsigned index=i*4%252,slot=i%64;
    unsigned count=vectors?vectors:1+i%4;
    Put(s,desc+i*16,(bits()&0x3ffffu)|(slot<<18));
    uint32_t flags=(bits()&0xfffff000u)|index|((count-1)<<10);
    Put(s,desc+i*16+(pixel?8:4),flags);
    uint32_t selection=(mode>=1 && mode<=3)?index:i%64*4;
    if(mode==4)selection=i%4; // source from safe stack span, never a destination
    Put(s,bindings+slot*8+4,(bits()&0xffff0000u)|selection);
  }
  return s;
}
template<bool Pixel,int Arm> __attribute__((noinline)) static void Invoke(State& s) {
  if constexpr(Arm==2) {
    if(nfsmw::constants::candidate::Run<Pixel>(s.ctx,s.memory.data(),s.cr,s.ea,s.temp))return;
  }
  if constexpr(Pixel) {
    if constexpr(Arm==0)OriginalPixel(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    else CurrentPixel(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
  } else {
    if constexpr(Arm==0)OriginalVertex(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
    else CurrentVertex(s.ctx,s.memory.data(),s.cr,s.ea,s.temp);
  }
}
static void Same(const State& a,const State& b) {
  if(std::memcmp(&a.ctx,&b.ctx,sizeof(PPCContext))) {
    auto* x=reinterpret_cast<const uint8_t*>(&a.ctx);
    auto* y=reinterpret_cast<const uint8_t*>(&b.ctx);
    for(size_t i=0;i<sizeof(PPCContext);++i)if(x[i]!=y[i]) {
      std::fprintf(stderr,"context mismatch byte %zu: %02x/%02x\n",i,x[i],y[i]);break;
    }
    assert(false);
  }
  assert(std::memcmp(&a.cr,&b.cr,sizeof(PPCCRRegister))==0);
  assert(a.temp.u64==b.temp.u64 && a.ea==b.ea && a.memory==b.memory);
}
template<bool Pixel> static void Equal(const State& seed,int expected=-1,int dirty_index=-1) {
  State a=seed,b=seed,c=seed;
  auto inject=[&] {
#ifdef INJECT_STORES
    inject_descriptor=dirty_index<0?0:0x2000+(Pixel?8:4);inject_index=uint32_t(dirty_index);
#endif
  };
  inject();Invoke<Pixel,0>(a);inject();Invoke<Pixel,1>(b);inject();
  const bool complete=nfsmw::constants::candidate::Run<Pixel>(c.ctx,c.memory.data(),c.cr,c.ea,c.temp);
  if(expected>=0)assert(complete==bool(expected));
  if(!complete)Invoke<Pixel,1>(c);
  Same(a,b);Same(b,c);
}
template<bool Pixel> static void Reject(const State& seed) {
  State s=seed;
  assert(!nfsmw::constants::candidate::Run<Pixel>(s.ctx,s.memory.data(),s.cr,s.ea,s.temp));
  Same(seed,s);
}
template<bool Pixel> static void Tests(size_t& comparisons,size_t& rejections) {
  for(unsigned n:{1u,2u,4u,8u,16u,32u,64u})
    for(unsigned vectors:{0u,1u,2u,3u,4u})
      for(int mode=0;mode<=5;++mode)
        for(unsigned repeat=0;repeat<8;++repeat) {
          Equal<Pixel>(Fixture(Pixel,n,vectors,mode),mode<=3);++comparisons;
        }
  // Every constant index and vector width, including dirty-word crossings and
  // beyond supported 256 constants: latter must execute the exact fallback.
  for(unsigned index=0;index<1024;++index) {
    auto s=Fixture(Pixel,1,1+index%4);
    uint32_t word=Get(s,0x2000+(Pixel?8:4));
    Put(s,0x2000+(Pixel?8:4),(word&~1023u)|index);
    Equal<Pixel>(s,index+1+index%4<=256);++comparisons;
  }
  for(unsigned n:{0u,65u}) {Equal<Pixel>(Fixture(Pixel,n,4));++comparisons;}
  // First two descriptors complete before a supported-memory/unsupported-index
  // failure. Verify resumption, not restart, against the full original body.
  auto late=Fixture(Pixel,4,4);
  Put(late,0x2020+(Pixel?8:4),(Get(late,0x2020+(Pixel?8:4))&~1023u)|256);
  auto prefix=late;
  assert(!nfsmw::constants::candidate::Run<Pixel>(prefix.ctx,prefix.memory.data(),prefix.cr,prefix.ea,prefix.temp));
  assert(prefix.ctx.r11.u64==0x2020 && Get(prefix,0x450)==0x2020);
  Equal<Pixel>(late);++comparisons;
  // A destination changes the lookup table used by subsequent descriptors.
  // The candidate must reload those selections rather than cache a whole run.
  auto lookup_alias=Fixture(Pixel,4,4);
  uint32_t table=0x10000+(Pixel?376:120)*16;
  Put(lookup_alias,0x460,table);lookup_alias.ctx.r23.u64=table;
  for(unsigned i=0;i<64;++i)Put(lookup_alias,table+i*8+4,i%4);
  std::fill(lookup_alias.memory.begin()+0x4000,lookup_alias.memory.begin()+0x5000,0);
  Equal<Pixel>(lookup_alias,1);++comparisons;
  auto dirty_alias=Fixture(Pixel,4,4);
  Put(dirty_alias,0x460,0x10010);dirty_alias.ctx.r23.u64=0x10010;
  for(unsigned i=0;i<64;++i)Put(dirty_alias,0x10010+i*8+4,0);
  Put(dirty_alias,0x10010,0);Put(dirty_alias,0x10014,0);
  Put(dirty_alias,0x10018,0);Put(dirty_alias,0x1001c,0);
  Equal<Pixel>(dirty_alias,1);++comparisons;
  auto descriptor_source=Fixture(Pixel,4,4);
  Put(descriptor_source,0x464,0x2000);descriptor_source.ctx.r24.u64=0x2000;
  Equal<Pixel>(descriptor_source,1);++comparisons;
#ifdef INJECT_STORES
  // Change only dirty-state index after the completed copy: retain the later
  // descriptor observation, including the PPC >63 shift behavior.
  for(int index:{0,255,513,1023}) {
    Equal<Pixel>(Fixture(Pixel,1,4),1,index);++comparisons;
  }
#endif
  auto seed=Fixture(Pixel,4,4);
  auto reject=[&](auto change) {auto s=seed;change(s);Reject<Pixel>(s);++rejections;};
  reject([](State& s){s.ctx.r1.u64=0xA0000000;});
  reject([](State& s){s.ctx.r18.u64=1;});
  reject([](State& s){s.ctx.r11.u64|=1ull<<40;});
  reject([](State& s){Put(s,0x450,0x2010);});
  reject([](State& s){Put(s,0x45c,0x2001);});
  reject([](State& s){Put(s,0x45c,0x1ff0);});
  reject([](State& s){s.ctx.r21.u64+=16;});
  reject([](State& s){Put(s,0x460,0xA0000000);s.ctx.r23.u64=0xA0000000;});
  reject([](State& s){Put(s,0x464,0xA0000000);s.ctx.r24.u64=0xA0000000;});
  reject([](State& s){Put(s,0x478,0xfffffff0);s.ctx.r21.u64=0xfffffff0;});
  reject([](State& s){Put(s,0x478,0x400);s.ctx.r21.u64=0x400;});
  reject([](State& s){Put(s,0x478,0x2000);s.ctx.r21.u64=0x2000;});
  reject([](State& s){
    uint32_t bank=0x2000-(Pixel?376:120)*16;
    Put(s,0x478,bank);s.ctx.r21.u64=bank;
  });
}
template<bool Pixel,int Arm> static uint64_t Bench(State& s,unsigned count) {
  uint64_t sum=0;
  for(unsigned i=0;i<count;++i) {
    s.ctx.r11.u64=0x2000;Put(s,0x450,0x2000);
    Invoke<Pixel,Arm>(s);
    sum+=s.ea^s.ctx.r10.u64;
    asm volatile("" : : "r"(&s) : "memory");
  }
  return sum;
}
template<bool Pixel> static void Cost(unsigned iterations) {
  for(unsigned n:{1u,4u,16u,64u})for(unsigned vectors:{0u,4u})for(int mode:{0,4,6}) {
    // mode6 rejects after a real completed prefix, all guard/fallback work timed.
    State seed=Fixture(Pixel,n,vectors,mode==6?0:mode);
    if(mode==6)Put(seed,0x2000+(n/2)*16+(Pixel?8:4),
      (Get(seed,0x2000+(n/2)*16+(Pixel?8:4))&~1023u)|256);
    for(unsigned trial=0;trial<7;++trial) {
      double ns[3]{};uint64_t sums[3]{};
      for(unsigned order=0;order<3;++order) {
        unsigned arm=(order+trial)%3;State s=seed;
        auto a=std::chrono::steady_clock::now();
        sums[arm]=arm==0?Bench<Pixel,0>(s,iterations):arm==1?Bench<Pixel,1>(s,iterations):Bench<Pixel,2>(s,iterations);
        ns[arm]=std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-a).count()/iterations;
      }
      assert(sums[0]==sums[1] && sums[1]==sums[2]);
      std::printf("COST %s n=%u vectors=%u mode=%d trial=%u original=%.3f current=%.3f candidate=%.3f checksum=%llu\n",
        Pixel?"PS":"VS",n,vectors,mode,trial,ns[0],ns[1],ns[2],(unsigned long long)sums[0]);
    }
  }
}
template<bool Pixel,int Arm> static uint64_t BenchPool(std::vector<State>& pool,unsigned count) {
  uint64_t sum=0;
  for(unsigned i=0;i<count;++i) {
    State& s=pool[i&31];
    s.ctx.r11.u64=0x2000;Put(s,0x450,0x2000);
    Invoke<Pixel,Arm>(s);
    sum+=s.ea^s.ctx.r10.u64;
    asm volatile("" : : "r"(&s) : "memory");
  }
  return sum;
}
template<bool Pixel> static void RotatingCost(unsigned iterations) {
  for(unsigned n:{1u,4u,16u,64u})for(unsigned vectors:{0u,4u}) {
    std::vector<State> seed;
    for(unsigned i=0;i<32;++i)seed.push_back(Fixture(Pixel,n,vectors));
    for(unsigned trial=0;trial<7;++trial) {
      double ns[3]{};uint64_t sums[3]{};
      for(unsigned order=0;order<3;++order) {
        unsigned arm=(order+trial)%3;auto pool=seed;
        auto a=std::chrono::steady_clock::now();
        sums[arm]=arm==0?BenchPool<Pixel,0>(pool,iterations):
          arm==1?BenchPool<Pixel,1>(pool,iterations):BenchPool<Pixel,2>(pool,iterations);
        ns[arm]=std::chrono::duration<double,std::nano>(std::chrono::steady_clock::now()-a).count()/iterations;
      }
      assert(sums[0]==sums[1] && sums[1]==sums[2]);
      std::printf("ROTATE %s n=%u vectors=%u mode=0 trial=%u original=%.3f current=%.3f candidate=%.3f checksum=%llu\n",
        Pixel?"PS":"VS",n,vectors,trial,ns[0],ns[1],ns[2],(unsigned long long)sums[0]);
    }
  }
}
int main(int argc,char**) {
  size_t comparisons=0,rejections=0;
  Tests<false>(comparisons,rejections);Tests<true>(comparisons,rejections);
  std::printf("PASS %zu three-arm full-loop comparisons; %zu unchanged rejections; late-prefix resumption\n",comparisons,rejections);
  if(argc>1){Cost<false>(30000);Cost<true>(30000);RotatingCost<false>(30000);RotatingCost<true>(30000);}
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sdk', type=Path, default=ROOT.parent / 'rexglue-sdk-ios')
    ap.add_argument('--benchmark', action='store_true')
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    matches = [p for p in patch.GENERATED.glob('*.cpp')
               if 'DEFINE_REX_FUNC(sub_82699100) {' in p.read_text()]
    assert len(matches) == 1
    original = patch.original_text(descriptors.original_text(matches[0].read_text()))
    current = patch.transform(original)
    references = []
    for label, (name, digest) in SITES.items():
        for arm, source in [('Original', original), ('Current', current)]:
            a = source.index(f'loc_{label}:\n')
            end = f'\tif (cr6.lt) goto loc_{label};\n'
            b = source.index(end, a) + len(end)
            body = source[a:b]
            if arm == 'Original':
                assert hashlib.sha256(body.encode()).hexdigest() == digest, 'full generated run changed'
            references.append(f'__attribute__((noinline)) void {arm}{name}(PPCContext& ctx, uint8_t* base, PPCCRRegister& cr6, uint32_t& ea, PPCRegister& temp) {{\n const bool native_constant_copies=true;\n{body}\n}}')
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.output / 'full-descriptor-fixture.cpp'
    source.write_text(HARNESS.replace('@HEADER@', str(ROOT / 'tools/native/constant_descriptor_candidate.h'))
                      .replace('@REFERENCES@', '\n'.join(references)))
    exe = args.output / ('benchmark' if args.benchmark else 'sanitized')
    flags = ['-O2'] if args.benchmark else ['-O1', '-DINJECT_STORES', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
    command = ['xcrun', 'clang++', '-std=c++23', '-Wno-asm-operand-widths', *flags,
               '-I', str(args.sdk / 'include'), '-I', str(args.sdk / 'thirdparty/simde'),
               str(source), '-o', str(exe)]
    subprocess.run(command, check=True)
    subprocess.run([str(exe)] + (['benchmark'] if args.benchmark else []), check=True)


if __name__ == '__main__':
    main()
