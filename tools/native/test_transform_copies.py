#!/usr/bin/env python3
"""Compare actual generated scalar regions and guards using the SDK context.

ASan/UBSan by default; --benchmark uses -O3 and times both extracted regions.
Run on an ARM64 Mac after codegen. No generated files are changed by this test.
"""
import argparse
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ios'))
import patch_game_transform_copies as patch

HARNESS = r'''
#include <rex/ppc/context.h>
#include <rex/ppc/intrinsics.h>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <random>
#include <vector>
struct Access { uint32_t address, value; bool store; bool operator==(const Access&) const = default; };
std::vector<Access> accesses;
bool trace_accesses = true;
uint32_t Load(uint8_t* base, uint32_t address) {
  auto value = __builtin_bswap32(*(volatile uint32_t*)(base + address));
#ifndef BENCHMARK
  if (trace_accesses) accesses.push_back({address, value, false});
#endif
  return value;
}
void Store(uint8_t* base, uint32_t address, uint32_t value) {
#ifndef BENCHMARK
  if (trace_accesses) accesses.push_back({address, value, true});
#endif
  *(volatile uint32_t*)(base + address) = __builtin_bswap32(value);
}
#define REX_RAW_ADDR(x) (base + uint32_t(x))
#define REX_LOAD_U32(x) Load(base, uint32_t(x))
#define REX_STORE_U32(x,y) Store(base, uint32_t(x), uint32_t(y))
#include "@HEADER@"
@REGIONS@
struct alignas(64) State {
  PPCContext ctx;
  PPCRegister temp;
  uint32_t ea;
  alignas(16) std::array<uint8_t, 16384> memory;
};
uint64_t ReadFPCR() { uint64_t v; asm volatile("mrs %0, fpcr":"=r"(v)); return v; }
uint64_t ReadFPSR() { uint64_t v; asm volatile("mrs %0, fpsr":"=r"(v)); return v; }
void WriteFPCR(uint64_t v) { asm volatile("msr fpcr, %0"::"r"(v):"memory"); }
void WriteFPSR(uint64_t v) { asm volatile("msr fpsr, %0"::"r"(v):"memory"); }
static std::mt19937 rng(82453768);
State Fixture(unsigned count, const std::array<uint32_t,3>& bits, int overlap) {
  State s;
  auto* p=reinterpret_cast<uint8_t*>(&s);
  for(size_t i=0;i<sizeof(s);++i)p[i]=uint8_t(rng());
  s.ctx.r1.u64=1024; s.ctx.r11.u64=count==1?uint32_t(4096-12344):4096;
  s.ctx.r9.u64=2048;s.ctx.r7.u64=2080;s.ctx.r4.u64=2112;
  // Keep the interleaved integer->vector conversion finite/exact.
  for(unsigned i=0;i<4;++i)s.ctx.v6.u32[i]=i+1;
  const uint32_t dest=1024+(count==1?92:80);
  uint32_t source=4096;
  if(overlap!=100)source=uint32_t(int(dest)+overlap*4);
  s.ctx.r11.u32=source-(count==1?12344u:0u);
  for(unsigned i=0;i<count;++i) {
    uint32_t v=__builtin_bswap32(bits[i]);std::memcpy(s.memory.data()+source+i*4,&v,4);
  }
  return s;
}
size_t tests=0;
template<unsigned Count> void Equal(const State& original, uint64_t control, uint64_t status) {
  State ref=original,on=original,off=original;
  ref.ctx.fpscr.csr=on.ctx.fpscr.csr=off.ctx.fpscr.csr=uint32_t(control);
  WriteFPCR(control);WriteFPSR(status);accesses.clear();
  if constexpr(Count==1) Reference1(ref.ctx,ref.memory.data(),ref.temp,ref.ea,false);
  else Reference3(ref.ctx,ref.memory.data(),ref.temp,ref.ea,false);
  auto ref_accesses=accesses;
  const uint64_t ref_control=ReadFPCR(),ref_status=ReadFPSR();
  for(bool enabled : {false,true}) {
    auto& got=enabled?on:off;
    WriteFPCR(control);WriteFPSR(status);accesses.clear();
    if constexpr(Count==1) Candidate1(got.ctx,got.memory.data(),got.temp,got.ea,enabled);
    else Candidate3(got.ctx,got.memory.data(),got.temp,got.ea,enabled);
    assert(std::memcmp(&ref.ctx,&got.ctx,sizeof(PPCContext))==0);
    assert(ref.temp.u64==got.temp.u64 && ref.ea==got.ea && ref.memory==got.memory);
    assert(ReadFPCR()==ref_control && ReadFPSR()==ref_status);
    assert(accesses==ref_accesses);
  }
  ++tests;
}
template<unsigned Count> __attribute__((noinline)) uint64_t Bench(State& s, bool enabled, unsigned n) {
  uint64_t sum=0;
  for(unsigned i=0;i<n;++i) {
    // Reload the input pointer overwritten by the first region's GPR work.
    s.ctx.r11.u32=Count==1?uint32_t(4096-12344):4096;
    s.ctx.r4.u64=2112;
    if(enabled) {
      if constexpr(Count==1) Candidate1(s.ctx,s.memory.data(),s.temp,s.ea,true);
      else Candidate3(s.ctx,s.memory.data(),s.temp,s.ea,true);
    } else {
      if constexpr(Count==1) Reference1(s.ctx,s.memory.data(),s.temp,s.ea,false);
      else Reference3(s.ctx,s.memory.data(),s.temp,s.ea,false);
    }
    sum+=s.temp.u32+s.ctx.f0.u64;
    asm volatile(""::"r"(&s):"memory");
  }
  return sum;
}
template<unsigned Count> void Benchmark(uint64_t control) {
  trace_accesses=false;
  auto s=Fixture(Count,{0x3f800000,0xbfaaaaab,0x00800001},100);
  WriteFPCR(control); s.ctx.fpscr.csr=uint32_t(control);
  for(int round=0;round<5;++round) {
    // Alternate order to reduce systematic warm-up bias.
    double ns[2]{};uint64_t sums[2]{};
    for(int step=0;step<2;++step) {
      bool enabled=bool(step^(round&1));
      auto a=std::chrono::steady_clock::now();
      sums[enabled]=Bench<Count>(s,enabled,2000000);
      auto b=std::chrono::steady_clock::now();
      ns[enabled]=std::chrono::duration<double,std::nano>(b-a).count()/2000000;
    }
    assert(sums[0]==sums[1]);
    std::printf("%u floats + surrounding generated operations: original %.2f ns, on %.2f ns\n",Count,ns[0],ns[1]);
  }
}
int main(int argc,char**) {
  const auto saved_control=ReadFPCR(), saved_status=ReadFPSR();
  const uint64_t base_control=(saved_control & ~uint64_t((3u<<22)|0x9f00u|(1u<<25))) | (1u<<24)|(1u<<19);
  const std::array<uint32_t,24> edge={0,0x80000000,1,0x80000001,0x007fffff,0x807fffff,
    0x00800000,0x80800000,0x00800001,0x3f800000,0xbf800000,0x3fffffff,0x7f7fffff,0xff7fffff,
    0x7f800000,0xff800000,0x7fc00000,0xffc00000,0x7f800001,0xff800001,0x7fffffff,0xffffffff,0x3eaaaaab,0x33800000};
  for(unsigned round=0;round<4;++round) for(unsigned dn=0;dn<2;++dn) {
    const uint64_t control=base_control|(uint64_t(round)<<22)|(uint64_t(dn)<<25);
    for(uint64_t status : {uint64_t(0),uint64_t(0x0800009f)}) {
      for(auto a:edge) for(int overlap : {100,-2,-1,0,1,2}) {
        Equal<1>(Fixture(1,{a,0,0},overlap),control,status);
        for(auto b:edge)Equal<3>(Fixture(3,{a,b,edge[(a^b)%edge.size()]},overlap),control,status);
      }
      for(unsigned exponent=1;exponent<255;++exponent) for(uint32_t mantissa : {0u,1u,0x3fffffu,0x7fffffu}) {
        for(uint32_t sign : {0u,0x80000000u}) {
          auto v=sign|(exponent<<23)|mantissa;
          Equal<1>(Fixture(1,{v,0,0},100),control,status);
        }
      }
      for(int i=0;i<1000;++i) {
        std::array<uint32_t,3> v={rng(),rng(),rng()};
        Equal<1>(Fixture(1,v,100),control,status);
        Equal<3>(Fixture(3,v,100),control,status);
      }
    }
  }
  // Rejected ranges must not touch memory, context, temp or the output flag.
  for(unsigned count : {1u,3u})for(uint32_t bad : {0x7f000000u,0x9ffffffcu,0xa0000000u,0xc0000000u,0xe0000000u,0xfffffffcu,4097u}) {
    if(count==1 && (bad==0x9ffffffcu || bad==0xfffffffcu)) continue; // one word does not cross the boundary
    for(bool bad_source : {false,true}) {
      auto s=Fixture(count,{0x3f800000,0,0},100);
      if(bad_source)s.ctx.r11.u32=bad-(count==1?12344u:0u);
      else s.ctx.r1.u32=bad-(count==1?92u:80u);
      auto before=s;bool disabled=true;accesses.clear();
      bool got=count==1 ? nfsmw::transforms::TryCopy<1>(s.ctx,s.memory.data(),s.temp,disabled) :
                         nfsmw::transforms::TryCopy<3>(s.ctx,s.memory.data(),s.temp,disabled);
      assert(!got && disabled && accesses.empty() && std::memcmp(&s,&before,sizeof(s))==0);
    }
  }
  WriteFPCR(saved_control);WriteFPSR(saved_status);
  std::printf("PASS %zu differential regions, both switch arms; full context/temp/ea/memory, ordered scalar accesses, FPCR and FPSR\n",tests);
  if(argc>1) { Benchmark<1>(base_control);Benchmark<3>(base_control); }
  WriteFPCR(saved_control);WriteFPSR(saved_status);
}
'''


def region(function, site):
    count, start, _, resume = site
    a = function.index(start)
    # The candidate's guard begins immediately before the lfs comment.
    if patch.MARK in function:
        a = function.rindex('\ttransform_flush_disabled = true;', 0, a)
    b = function.index('\n', function.index('ctx.fpscr.enableFlushModeUnconditional();', function.index(resume))) + 1
    # Include the first following vector arithmetic operation, exercising mode restoration.
    b = function.index('\n', b) + 1
    return function[a:b]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--benchmark', action='store_true')
    ap.add_argument('--sdk', type=pathlib.Path, default=ROOT.parent/'rexglue-sdk-ios')
    args = ap.parse_args()
    matches = [p for p in patch.GENERATED.glob('*.cpp') if 'DEFINE_REX_FUNC(sub_82453768) {' in p.read_text()]
    assert len(matches)==1
    original = patch.original_text(matches[0].read_text())
    candidate = patch.transform(original)
    assert patch.original_text(candidate)==original
    regions=[]
    for name,text in [('Reference',original),('Candidate',candidate)]:
        a,b=patch.bounds(text)
        for site in patch.SITES:
            body=region(text[a:b],site)
            regions.append(f'__attribute__((noinline)) void {name}{site[0]}(PPCContext& ctx, uint8_t* base, PPCRegister& temp, uint32_t& ea, bool native_transform_copies) {{ bool transform_flush_disabled=true;\n{body}\n}}')
    with tempfile.TemporaryDirectory(prefix='nfsmw-transform-copies-') as temp:
        temp=pathlib.Path(temp)
        fixture=temp/'generated';fixture.mkdir();file=fixture/'test.cpp';file.write_text(original)
        command=[sys.executable,str(pathlib.Path(patch.__file__)),'--dir',str(fixture)]
        for options in ([],[],['--status'],['--revert'],['--revert']):
            subprocess.run(command+options,check=True,capture_output=True)
        assert file.read_text()==original
        for damaged in [original[:patch.bounds(original)[0]] + original[patch.bounds(original)[0]:].replace('ctx.f0.f64 = double(temp.f32);','ctx.f0.f64 = 0;',1),
                        candidate.replace('if (transform_flush_disabled) ctx.fpscr.enableFlushModeUnconditional();','ctx.fpscr.enableFlushModeUnconditional();',1),
                        original+'\n'+original]:
            file.write_text(damaged)
            assert subprocess.run(command,capture_output=True).returncode!=0
            assert file.read_text()==damaged
        print('PASS patch apply/idempotence/status/revert and failure atomicity',flush=True)
        source=temp/'test.cpp'
        source.write_text(HARNESS.replace('@HEADER@',str(ROOT/'ios/src/game_transform_copies.h')).replace('@REGIONS@','\n'.join(regions)))
        exe=temp/'test'
        flags=['-O3','-DBENCHMARK'] if args.benchmark else ['-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        subprocess.run(['xcrun','clang++','-std=c++23','-Wno-asm-operand-widths',*flags,
                        '-I',str(args.sdk/'include'),'-I',str(args.sdk/'thirdparty/simde'),str(source),'-o',str(exe)],check=True)
        subprocess.run([str(exe)]+(['benchmark'] if args.benchmark else []),check=True)


if __name__=='__main__':
    main()
