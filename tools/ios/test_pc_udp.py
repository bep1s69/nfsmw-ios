#!/usr/bin/env python3
"""Compile actual USA PC UDP hooks with bounded guest memory and capture stubs.

Checks captured header conversion at the DirtySock boundary, not a real PC race.
"""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
prefix=r'''
#pragma once
#include <cstdint>
#include <cassert>
#include <algorithm>
#include <string>
#include <vector>
#include <cstring>
struct Reg {union{uint64_t u64=0;int64_t s64;uint32_t u32;int32_t s32;};};
struct PPCContext{Reg r1,r3,r4,r5,r7,r8;uint64_t lr=0;};
#define REX_FUNC(n) void n(PPCContext&ctx,uint8_t*base)
#define REXCVAR_DECLARE(t,n) extern t n
#define REXCVAR_GET(n) (n)
inline uint32_t Load32(uint8_t*b,uint32_t a){assert(a+4<=65536);uint32_t v;memcpy(&v,b+a,4);return __builtin_bswap32(v);}
inline uint16_t Load16(uint8_t*b,uint32_t a){assert(a+2<=65536);return (b[a]<<8)|b[a+1];}
inline void Store32(uint8_t*b,uint32_t a,uint32_t v){assert(a+4<=65536);v=__builtin_bswap32(v);memcpy(b+a,&v,4);}
#define REX_LOAD_U32(a) Load32(base,a)
#define REX_LOAD_U16(a) Load16(base,a)
#define REX_STORE_U32(a,v) Store32(base,a,v)
'''
test=r'''
#include "nfsmw_pch.h"
#include "pc_gateway.h"
bool red_lan=true,pc=true;
namespace nfsmw::pc{bool IsRacePeer(uint32_t ip){return ::pc && ip==0xc0a801ca;}}
namespace nfsmw::boot {void Trace(const std::string&) {}}
std::vector<uint8_t> sent;
int result=8;
const uint8_t packet[]={5,0,0,0,0xc5,0xb9,0x64,0xc6,0xde,0xad,0xbe,0xef};
extern "C" REX_FUNC(sub_8282A4F0);
extern "C" REX_FUNC(sub_8282A5A0);
extern "C" REX_FUNC(__imp__sub_8282A4F0){
 assert(ctx.r4.u32+ctx.r5.u32<=65536);
 sent.assign(base+ctx.r4.u32,base+ctx.r4.u32+ctx.r5.u32);
 ctx.r3.s64=result;ctx.r4.u64=0; // volatile argument registers may be clobbered
}
extern "C" REX_FUNC(__imp__sub_8282A5A0){
 if(result>0)memcpy(base+ctx.r4.u32,packet,result);
 ctx.r3.s64=result;ctx.r4.u64=0;ctx.r5.u64=0;ctx.r7.u64=0;
}
int main(){
 uint8_t mem[65536]{};auto*base=mem;
 mem[0x102]=0x0e;mem[0x103]=0x4a;Store32(base,0x104,0xc0a801ca);
 const uint8_t original[]={0,0,0,1,0,0,0,0,0xde,0xad,0xbe,0xef};
 memcpy(mem+0x2000,original,12);
 auto context=[](){PPCContext c;c.r1.u64=0xe000;c.r4.u64=0x2000;c.r5.u64=12;c.r7.u64=0x100;c.lr=0x8289c7b4;return c;};
 auto c=context();sub_8282A4F0(c,base);
 assert(c.r1.u32==0xe000 && c.r3.s32==8);
 const uint8_t expected[]={1,0,0,0,0,0,0,0,0xde,0xad,0xbe,0xef};
 assert(sent==std::vector<uint8_t>(expected,expected+12));
 assert(memcmp(mem+0x2000,original,12)==0); // caller buffer untouched, retries safe
 c=context();result=-1;sub_8282A4F0(c,base);assert(c.r1.u32==0xe000 && c.r3.s32==-1);
 result=12;c=context();sub_8282A5A0(c,base);
 const uint8_t rx[]={0,0,0,5,0xc6,0x64,0xb9,0xc5,0xde,0xad,0xbe,0xef};
 assert(memcmp(mem+0x2000,rx,12)==0 && c.r3.s32==12);
 result=-1;c=context();sub_8282A5A0(c,base);assert(c.r3.s32==-1 && memcmp(mem+0x2000,rx,12)==0);
 for(int skip=0;skip<6;++skip){
  red_lan=true;pc=true;Store32(base,0x104,0xc0a801ca);mem[0x103]=0x4a;
  c=context();
  if(skip==0)red_lan=false;
  if(skip==1)pc=false;
  if(skip==2)Store32(base,0x104,0xc0a801cd); // mobile peer
  if(skip==3)mem[0x103]=0x4b; // other UDP port
  if(skip==4)c.lr=0x82500000; // voice/non-CommUDP caller
  if(skip==5)c.r5.u64=4; // too short
  memcpy(mem+0x2000,original,12);result=skip==5?4:12;
  sub_8282A4F0(c,base);assert(memcmp(sent.data(),original,result)==0 && c.r1.u32==0xe000);
  c=context();if(skip==4)c.lr=0x82500000;if(skip==5)c.r5.u64=4;
  sub_8282A5A0(c,base);assert(memcmp(mem+0x2000,packet,result)==0);
 }
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-udp-') as d:
 p=Path(d);(p/'rex').mkdir();(p/'rex/cvar.h').write_text('')
 (p/'nfsmw_pch.h').write_text(prefix);(p/'test.cpp').write_text(test)
 subprocess.run(['clang++','-std=c++23','-O1','-fsanitize=address,undefined','-I'+str(p),'-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/game_pc_udp.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
 print('PASS: actual UDP hooks translate captured PC header words, preserve payload/caller buffer/return/stack; LAN-off/mobile/voice/other-port/short/error paths unchanged. No real PC handshake/race tested.')
