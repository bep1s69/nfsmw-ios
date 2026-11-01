#!/usr/bin/env python3
"""Actual USA name lookup + LAN count repair, using real parsed-list semantics.
Generated proprietary implementation stays in the private temporary fixture.
"""
from pathlib import Path
import subprocess,tempfile
root=Path(__file__).resolve().parents[2]
s=(root/'ios/generated/default/nfsmw_recomp.1.cpp').read_text()
a=s.index('DEFINE_REX_FUNC(sub_82544A78)');b=s.index('\nDEFINE_REX_FUNC(',a+1)
original=s[a:b].replace('DEFINE_REX_FUNC(sub_82544A78)','extern "C" REX_FUNC(__imp__sub_82544A78)')
cb=(root/'ios/generated/default/nfsmw_recomp.130.cpp').read_text();a=cb.index('DEFINE_REX_FUNC(sub_82545A88)');b=cb.index('\nDEFINE_REX_FUNC(',a+1)
original+=cb[a:b].replace('DEFINE_REX_FUNC(sub_82545A88)','extern "C" REX_FUNC(__imp__sub_82545A88)')
prefix=r'''
#pragma once
#include <cstdint>
#include <cstring>
#include <cassert>
#include <string>
#include <vector>
struct Reg{union{uint64_t u64=0;int64_t s64;uint32_t u32;int32_t s32;};};
struct CR{bool eq=false,lt=false,gt=false;template<class T>void compare(T a,T b,int){eq=a==b;lt=a<b;gt=a>b;}};
struct PPCContext{
'''+''.join('Reg r%d;'%i for i in range(32))+r'''
 Reg ctr;uint64_t lr=0;int xer=0;
};
using PPCCRRegister=CR;
#define REX_CALL_INDIRECT_FUNC(a) Observe(ctx,base)
void Observe(PPCContext&,uint8_t*);
#define REX_FUNC_PROLOGUE()
#define REX_FUNC(n) void n(PPCContext&ctx,uint8_t*base)
#define REXCVAR_DECLARE(t,n) extern t n
#define REXCVAR_GET(n) (n)
inline uint32_t Load(uint8_t*b,uint32_t a){assert(a+4<=65536);uint32_t v;memcpy(&v,b+a,4);return __builtin_bswap32(v);}
inline void Store(uint8_t*b,uint32_t a,uint32_t v){assert(a+4<=65536);v=__builtin_bswap32(v);memcpy(b+a,&v,4);}
#define REX_LOAD_U32(a) Load(base,a)
#define REX_STORE_U32(a,v) Store(base,a,v)
#define REX_LOAD_U64(a) ((uint64_t(Load(base,a))<<32)|Load(base,(a)+4))
#define REX_STORE_U64(a,v) do{Store(base,a,uint64_t(v)>>32);Store(base,(a)+4,uint32_t(v));}while(0)
'''
test=r'''
#include "nfsmw_pch.h"
bool red_lan=true;std::vector<std::string> logs;
namespace nfsmw::boot{void Trace(const std::string&s){logs.push_back(s);}}
void sub_8281BB70(PPCContext&ctx,uint8_t*base){
 auto list=ctx.r3.u32,index=ctx.r4.u32;
 ctx.r3.u64=index<Load(base,list+24)?Load(base,list+32+4*index):0;
}
void sub_8215D7B8(PPCContext&ctx,uint8_t*base){ctx.r3.s64=strcmp((char*)base+ctx.r3.u32,(char*)base+ctx.r4.u32);}
extern "C" REX_FUNC(sub_82544A78);
extern "C" REX_FUNC(sub_82545A88);
int callbacks=0;uint32_t seenCount=0;
void Observe(PPCContext&ctx,uint8_t*base){++callbacks;seenCount=Load(base,ctx.r4.u32+36);ctx.r3.u64=77;}
'''
main=r'''
int main(){
 uint8_t memory[65536]{};auto*base=memory;uint32_t room=0x1000,list=0x2000;
 Store(base,room+360,list);Store(base,room+372,1001);Store(base,room+404,4);Store(base,room+408,1);
 Store(base,list+24,2);Store(base,list+32,0x3000);Store(base,list+36,0x3100);
 strcpy((char*)base+room+388,"Host");strcpy((char*)base+0x3004,"Host");strcpy((char*)base+0x3104,"Guest");
 auto context=[&](){PPCContext c;c.r1.u64=0xe000;c.r3.u64=room;c.r4.u64=0;c.r5.u64=room;return c;};
 Store(base,room+364,0x82500000);
 // Native callback passes stale C=1 to frontend despite two parsed members.
 auto c=context();__imp__sub_82545A88(c,base);assert(seenCount==1);
 // Direct indexed lookup can find Guest even with stale metadata; name text is valid.
 c=context();c.r4.u64=1;__imp__sub_82544A78(c,base);assert(c.r3.u32==0x3100 && Load(base,room+408)==1);
 c=context();sub_82544A78(c,base);assert(c.r3.u32==0x3000 && Load(base,room+408)==2);
 c=context();c.r4.u64=1;sub_82544A78(c,base);assert(c.r3.u32==0x3100);
 // Original callback sees repaired count before notifying the frontend.
 Store(base,room+408,1);c=context();sub_82545A88(c,base);
 assert(callbacks==2 && seenCount==2 && c.r3.u32==77);
 // Guest leaves: list contains only host, no stale or invented opponent.
 Store(base,list+24,1);c=context();c.r4.u64=1;sub_82544A78(c,base);assert(c.r3.u32==0 && Load(base,room+408)==1);
 // Offline and invalid/capacity-inconsistent models remain untouched.
 Store(base,list+24,2);red_lan=false;c=context();sub_82544A78(c,base);assert(Load(base,room+408)==1);
 red_lan=true;Store(base,list+24,5);c=context();sub_82544A78(c,base);assert(Load(base,room+408)==1);
 Store(base,list+24,2);Store(base,room+372,0);c=context();sub_82544A78(c,base);assert(Load(base,room+408)==1);
 assert(!logs.empty());
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-roster-') as d:
 p=Path(d);(p/'rex').mkdir();(p/'rex/cvar.h').write_text('');(p/'nfsmw_pch.h').write_text(prefix)
 (p/'test.cpp').write_text(test+original+main)
 subprocess.run(['clang++','-std=c++23','-O1','-fsanitize=address,undefined','-I'+str(p),str(p/'test.cpp'),str(root/'ios/src/multiplayer/game_lan_roster.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
print('PASS: actual USA callback forwards stale C=1 despite parsed Guest; LAN repair forwards C=2 and original indexed lookup returns Guest; leave/offline/invalid-count paths pass. Actual frontend rendering untested.')
