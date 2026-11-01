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
struct PPCContext{Reg r1,r3,r4,r5,r7,r8,r31;uint64_t lr=0;};
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
namespace nfsmw::pc{
uint32_t remoteId=0,localId=0;
bool host=false,remoteKnown=false,localKnown=false;
bool Hosting(){return host;}
bool HasRaceId(uint32_t){return remoteKnown;}
bool HasLocalRaceId(uint32_t){return localKnown;}
bool IsRacePeer(uint32_t ip){return ::pc && ip==0xc0a801ca;}
void ObserveRaceId(uint32_t,uint32_t id){remoteId=id;remoteKnown=true;}
uint32_t RaceId(uint32_t){return remoteId;}
void SetLocalRaceId(uint32_t,uint32_t id){localId=id;localKnown=true;}
uint32_t LocalRaceId(uint32_t){return localId;}
}
std::vector<std::string> logs;
namespace nfsmw::boot {void Trace(const std::string&s) {logs.push_back(s);}}
std::vector<uint8_t> sent;
int result=8;
uint8_t packet[64]={5,0,0,0,0xc5,0xb9,0x64,0xc6,0xde,0xad,0xbe,0xef};
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
 const uint8_t rx[]={0,0,0,5,0,0,0,0,0xde,0xad,0xbe,0xef};
 assert(memcmp(mem+0x2000,rx,12)==0 && c.r3.s32==12);
 assert(nfsmw::pc::remoteId==0xc664b9c5);
 // A subsequent INIT keeps the game's local ID zero but requests PC's ID on wire.
 memcpy(mem+0x2000,original,12);c=context();result=12;sub_8282A4F0(c,base);
 const uint8_t mapped[]={1,0,0,0,0xc5,0xb9,0x64,0xc6,0xde,0xad,0xbe,0xef};
 assert(sent==std::vector<uint8_t>(mapped,mapped+12) && memcmp(mem+0x2000,original,12)==0);
 // Established DATA acknowledgements are sequence numbers, never mapped IDs.
 const uint8_t data[]={0x10,0,0,1,0xc6,0x64,0xb9,0xc5,0xde,0xad,0xbe,0xef};
 memcpy(mem+0x2000,data,12);c=context();sub_8282A4F0(c,base);
 assert(sent[4]==0xc5 && sent[5]==0xb9 && sent[6]==0x64 && sent[7]==0xc6);
 memcpy(mem+0x2000,rx,12);
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
 red_lan=true;pc=true;Store32(base,0x104,0xc0a801ca);mem[0x103]=0x4a;
 // Captured reverse-host failure: PC INIT4749E364 arrives before any TX.
 // Capture local listener ID from exact original receive callsite immediately.
 nfsmw::pc::host=true;nfsmw::pc::remoteKnown=false;nfsmw::pc::localKnown=false;
 packet[0]=1;packet[4]=0x64;packet[5]=0xe3;packet[6]=0x49;packet[7]=0x47;
 Store32(base,0x3080,0xf8000128);Store32(base,0x3094,3);Store32(base,0x3098,0);
 c=context();c.lr=0x8289c4d8;c.r31.u64=0x3000;c.r3.u64=0xf8000128;result=8;
 sub_8282A5A0(c,base);
 assert(nfsmw::pc::localKnown && nfsmw::pc::localId==0 && nfsmw::pc::remoteId==0x4749e364);
 assert(Load32(base,0x2000)==1 && Load32(base,0x2004)==0); // original listener match now succeeds
 Store32(base,0x2000,5);Store32(base,0x2004,0);c=context();result=8;sub_8282A4F0(c,base);
 assert(sent[4]==0x64 && sent[5]==0xe3 && sent[6]==0x49 && sent[7]==0x47);
 // Wrong state/socket/callsite must not sample another reference's listener ID.
 for(int skip=0;skip<3;++skip) {
  nfsmw::pc::localKnown=false;Store32(base,0x3094,skip==0?4:3);
  c=context();c.lr=skip==2?0x8289c7b4:0x8289c4d8;c.r31.u64=0x3000;c.r3.u64=skip==1?99:0xf8000128;
  sub_8282A5A0(c,base);assert(!nfsmw::pc::localKnown && Load32(base,0x2004)==0x4749e364);
 }
 // Reverse role: original PC initiates with ID zero. Zero is a known ID.
 nfsmw::pc::host=true;nfsmw::pc::remoteKnown=false;nfsmw::pc::localKnown=false;
 packet[0]=1;memset(packet+4,0,4);result=12;c=context();sub_8282A5A0(c,base);
 assert(nfsmw::pc::remoteKnown && nfsmw::pc::remoteId==0);
 Store32(base,0x2000,5);Store32(base,0x2004,0x12345678);
 c=context();sub_8282A4F0(c,base);
 assert(sent[0]==5 && sent[4]==0 && sent[5]==0 && sent[6]==0 && sent[7]==0);
 assert(Load32(base,0x2004)==0x12345678 && nfsmw::pc::localId==0x12345678);
 c=context();sub_8282A5A0(c,base);assert(Load32(base,0x2004)==0x12345678);
 nfsmw::pc::host=false;packet[0]=5;packet[4]=0xc5;packet[5]=0xb9;packet[6]=0x64;packet[7]=0xc6;
 logs.clear();memcpy(mem+0x2000,original,12);mem[0x2027]=0xa5;
 for(int i=0;i<40;++i){c=context();c.r5.u64=40;result=40;sub_8282A4F0(c,base);}
 assert(std::count_if(logs.begin(),logs.end(),[](auto&s){return s.find("[pc-packet] TX")==0;})==32);
 auto record=std::find_if(logs.begin(),logs.end(),[](auto&s){return s.find("[pc-packet] TX")==0;});
 assert(record!=logs.end() && record->ends_with("A5") && sent[39]==0xa5);
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-udp-') as d:
 p=Path(d);(p/'rex').mkdir();(p/'rex/cvar.h').write_text('')
 (p/'nfsmw_pch.h').write_text(prefix);(p/'test.cpp').write_text(test)
 subprocess.run(['clang++','-std=c++23','-O1','-fsanitize=address,undefined','-I'+str(p),'-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/game_pc_udp.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
 print('PASS: actual UDP hooks translate captured PC header words, preserve payload/caller buffer/return/stack; LAN-off/mobile/voice/other-port/short/error paths unchanged. No real PC handshake/race tested.')
