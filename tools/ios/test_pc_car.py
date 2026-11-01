#!/usr/bin/env python3
"""Compile actual PC native-car serializer hooks against captured ID/field map."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
prefix=r'''
#pragma once
#include <cstdint>
#include <cassert>
#include <cstring>
#include <string>
#include <vector>
struct Reg{union{uint64_t u64=0;uint32_t u32;};};
struct PPCContext{Reg r3,r4,r5,r30,r31;uint64_t lr=0;};
#define REX_FUNC(n) void n(PPCContext&ctx,uint8_t*base)
#define REX_LOAD_U8(a) base[uint32_t(a)]
#define REX_STORE_U8(a,v) (base[uint32_t(a)]=(v))
'''
test=r'''
#include "nfsmw_pch.h"
#include "pc_car_layout.h"
bool active=true;std::vector<uint8_t> incoming,outgoing;std::vector<std::string> logs;
namespace nfsmw::pc{bool Active(){return active;}}
namespace nfsmw::boot{void Trace(const std::string&s){logs.push_back(s);}}
extern "C" REX_FUNC(sub_82538320);
extern "C" REX_FUNC(sub_825380E8);
extern "C" REX_FUNC(__imp__sub_82538320){memcpy(base+ctx.r4.u32,incoming.data(),incoming.size());ctx.r3.u64=incoming.size();ctx.r4.u64=0;}
extern "C" REX_FUNC(__imp__sub_825380E8){outgoing.push_back(uint8_t(ctx.r4.u32));ctx.r4.u64=0;}
int main(){
 uint8_t mem[8192]{};PPCContext c;
 // Actual PC remote car ID packet/failed participant3F0888CD -> localCD88083F.
 incoming={0x3f,0x08,0x88,0xcd};c.r4.u64=1024;c.lr=0x824d54b4;sub_82538320(c,mem);
 const uint8_t valid[]={0xcd,0x88,0x08,0x3f};assert(c.r3.u32==4 && memcmp(mem+1024,valid,4)==0);
 for(int i=0;i<4;++i){c.r30.u64=1024;c.r31.u64=i;c.r4.u64=valid[i];c.r5.u64=8;c.lr=0x824d5704;sub_825380E8(c,mem);}
 assert(outgoing==incoming && memcmp(mem+1024,valid,4)==0);
 // Typed customization fields: shorts/float/preset, byte handle and pad untouched.
 incoming.assign(408,0);incoming[0]=0x34;incoming[1]=0x12;
 incoming[0x116]=0xcd;incoming[0x117]=0xaa;
 incoming[0x11a]=0x80;incoming[0x11b]=0x3f; // PC float1.0
 incoming[0x190]=0x44;incoming[0x191]=0x33;incoming[0x192]=0x22;incoming[0x193]=0x11;
 incoming[0x194]=0xab;incoming[0x195]=0xcd;incoming[0x196]=0xcd;incoming[0x197]=0xcd;
 c.r4.u64=2048;c.lr=0x824d54fc;sub_82538320(c,mem);
 assert(c.r3.u32==408 && mem[2048]==0x12 && mem[2049]==0x34);
 assert(mem[2048+0x118]==0x3f && mem[2048+0x119]==0x80 && mem[2048+0x11a]==0 && mem[2048+0x11b]==0);
 assert(mem[2048+0x190]==0x11 && mem[2048+0x193]==0x44);
 assert(mem[2048+0x116]==0xcd && mem[2048+0x117]==0xaa && mem[2048+0x194]==0xab && mem[2048+0x197]==0xcd);
 auto before=std::vector<uint8_t>(mem+2048,mem+2456);outgoing.clear();
 for(int i=0;i<408;++i){c.r30.u64=2048;c.r31.u64=i;c.r4.u64=mem[2048+i];c.r5.u64=8;c.lr=0x824d574c;sub_825380E8(c,mem);}
 assert(outgoing==incoming && before==std::vector<uint8_t>(mem+2048,mem+2456));
 for(int i=0;i<408;++i)assert(nfsmw::pc::CarByte(nfsmw::pc::CarByte(i,408),408)==i);
 // Off/other raw fields/bit widths cannot affect mobile or numeric bit writers.
 active=false;incoming={1,2,3,4};c.r4.u64=1024;c.lr=0x824d54b4;sub_82538320(c,mem);assert(mem[1024]==1);
 active=true;c.r4.u64=1024;c.lr=0x824d5444;sub_82538320(c,mem);assert(mem[1024]==1);
 for(auto lr:{0x824d5704u,0x824d574cu,0x82500000u}){c.lr=lr;c.r5.u64=16;c.r4.u64=0xab;sub_825380E8(c,mem);assert(outgoing.back()==0xab);}
 incoming={9,8};c.r4.u64=1024;c.lr=0x824d54b4;sub_82538320(c,mem);assert(c.r3.u32==2 && mem[1024]==9 && mem[1025]==8 && logs.back().find("unexpected")!=std::string::npos);
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-car-') as d:
 p=Path(d);(p/'nfsmw_pch.h').write_text(prefix);(p/'test.cpp').write_text(test)
 subprocess.run(['clang++','-std=c++23','-O1','-fsanitize=address,undefined','-I'+str(p),'-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/game_pc_car.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
 print('PASS: actual car serializer hooks repair captured record ID both ways, typed short/float/preset customization fields and byte/padding preservation; roundtrip/caller buffer/off/other fields unchanged. Race/device result untested.')
