#!/usr/bin/env python3
"""Decode PC adapter envelopes using the actual generated USA session decoder.

Requires ignored generated sources. No real network/peer/race emulation.
"""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
functions=[]
for file,name in [('6','82826978'),('130','82826890')]:
 s=(root/('ios/generated/default/nfsmw_recomp.'+file+'.cpp')).read_text()
 a=s.index('DEFINE_REX_FUNC(sub_'+name+')')
 functions.append(s[a:s.index('\nDEFINE_REX_FUNC',a+1)])
prefix=r'''
#include "pc_gateway.h"
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <unordered_map>
struct PPCRegister { union {uint64_t u64=0; int64_t s64;uint32_t u32;int32_t s32;uint8_t u8;int8_t s8;};};
struct XER{uint32_t ca=0;};
struct PPCCRRegister{bool eq=false,lt=false,gt=false;template<class T>void compare(T a,T b,XER){eq=a==b;lt=a<b;gt=a>b;}};
struct PPCContext {
PPCRegister r0;
PPCRegister r1;
PPCRegister r2;
PPCRegister r3;
PPCRegister r4;
PPCRegister r5;
PPCRegister r6;
PPCRegister r7;
PPCRegister r8;
PPCRegister r9;
PPCRegister r10;
PPCRegister r11;
PPCRegister r12;
PPCRegister r13;
PPCRegister r14;
PPCRegister r15;
PPCRegister r16;
PPCRegister r17;
PPCRegister r18;
PPCRegister r19;
PPCRegister r20;
PPCRegister r21;
PPCRegister r22;
PPCRegister r23;
PPCRegister r24;
PPCRegister r25;
PPCRegister r26;
PPCRegister r27;
PPCRegister r28;
PPCRegister r29;
PPCRegister r30;
PPCRegister r31;
PPCRegister ctr;uint64_t lr=0;XER xer;
};
uint8_t mem[0x10000]{};
#define REX_FUNC_PROLOGUE()
#define DEFINE_REX_FUNC(n) void n(PPCContext& ctx,uint8_t*base)
#define REX_LOAD_U8(a) mem[uint32_t(a)]
#define REX_STORE_U8(a,v) (mem[uint32_t(a)]=(v))
'''

test=r'''
std::string game="IDENT=1\tHOST=TKM\tCOUNT=2\tOPPO0=TKM\tADDR0=192.168.1.202\tMADDR0=$ca01a8c0\tOPPO1=bep1s\tADDR1=192.168.1.205\tMADDR1=$cd01a8c0";
int main(){
 using namespace nfsmw::pc;
 assert(Field(AdaptLogin("GTAG=Guest\tMADDR=$00090000c0a801cd^binary", "192.168.1.205"), "MADDR")=="$cd01a8c0");
 assert(AdaptLogin("MADDR=$unknown", "192.168.1.205")=="MADDR=$unknown");
 assert(AdaptLogin("MADDR=$00090000c0a801cd^binary", "127.0.0.1")=="MADDR=$00090000c0a801cd^binary");
 assert(AdaptLogin("MADDR=$gggggggggggggggg^binary", "192.168.1.205")=="MADDR=$gggggggggggggggg^binary");
 auto adapted=AdaptGame(game);auto sess=Field(adapted,"SESS");
 assert(sess.size()==72 && sess[0]=='$');
 memcpy(mem+0x1000,sess.c_str(),sess.size()+1);
 PPCContext ctx;ctx.r3.u64=0x2000;ctx.r4.u64=0x1000;sub_82826978(ctx,nullptr);
 const uint8_t expected[]={192,168,1,202};assert(memcmp(mem+0x2008,expected,4)==0);
 assert(mem[0x2012]==0 && mem[0x2013]==0x1d && mem[0x2014]==0xd8);
 assert(mem[0x2015]==168 && mem[0x2016]==1 && mem[0x2017]==202);
 assert(mem[0x2000]&0x80);
 for(int i=0;i<16;++i)assert(mem[0x202c+i]==uint8_t(mem[0x2000+(i%8)]^(0x5a+i)));
 assert(Field(AdaptGame(Put(game,"PARAMS","track-update")),"SESS")==sess);
 assert(Field(AdaptGame(Put(game,"IDENT","2")),"SESS")!=sess);
 assert(Field(AdaptGame(Put(game,"SESS","$existing")),"SESS")=="$existing");
 assert(Field(AdaptGame("IDENT=1\tHOST=Unknown\tADDR0=127.0.0.1"),"SESS").empty());
 assert(AdaptUser("N=Host\tA=127.0.0.1")=="N=Host\tA=127.0.0.1");
 auto machine=Field(adapted,"MADDR0");assert(machine.substr(0,18)=="$00090000c0a801ca^");
 auto caret=machine.find('^');memcpy(mem+0x3000,machine.c_str()+caret+1,machine.size()-caret);
 ctx={};ctx.r3.u64=0x4000;ctx.r4.u64=36;ctx.r5.u64=0x3000;sub_82826890(ctx,nullptr);
 assert(memcmp(mem+0x4000,expected,4)==0);
 assert(Field(AdaptUser("N=TKM\tA=192.168.1.202\tMA=$ca01a8c0"),"MA")==machine);
 auto original=Put(game,"MADDR0",machine);assert(Field(AdaptGame(original),"MADDR0")==machine);
 assert(Field(AdaptUser("N=TKM\tA=192.168.1.202\tMA=$unknown"),"MA")=="$unknown");
 std::cout<<"PASS: actual USA session/address decoders read PC host IP/MAC/key/ID; stable updates, distinct games, existing sessions and unknown machine blobs preserved; invalid host rejected. No real peer/race emulation.\n";
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-session-') as d:
 p=Path(d);(p/'test.cpp').write_text(prefix+''.join(functions)+test)
 subprocess.run(['clang++','-std=c++23','-O1','-pthread','-fsanitize=address,undefined','-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/pc_gateway.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
