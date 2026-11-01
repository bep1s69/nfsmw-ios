#!/usr/bin/env python3
"""Exercise the actual generated USA room validator without a game/network.

Requires local, ignored generated code. Dependency stubs isolate the version
filter and report reaching QoS; they do not emulate a PC connection or race.
No proprietary generated source is copied into the repository.
"""
from pathlib import Path
import subprocess
import tempfile
root = Path(__file__).resolve().parents[2]
source = root / 'ios/generated/default/nfsmw_recomp.119.cpp'
s = source.read_text()
start = s.index('DEFINE_REX_FUNC(sub_82546178)')
end = s.index('\nDEFINE_REX_FUNC(', start + 1)
validator = s[start:end]
prefix = r'''
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
'''
prefix += ''.join('PPCRegister r%d;\n' % i for i in range(32))
prefix += r'''
PPCRegister ctr;uint64_t lr=0;XER xer;
};
std::unordered_map<uint32_t,uint32_t> words;
std::unordered_map<uint32_t,uint64_t> doubles;
std::unordered_map<uint32_t,uint8_t> bytes;
#define REX_FUNC_PROLOGUE()
#define DEFINE_REX_FUNC(n) void n(PPCContext& ctx,uint8_t*base)
#define REX_LOAD_U32(a) words[uint32_t(a)]
#define REX_LOAD_U8(a) bytes[uint32_t(a)]
#define REX_STORE_U32(a,v) (words[uint32_t(a)]=(v))
#define REX_STORE_U64(a,v) (doubles[uint32_t(a)]=(v))
#define REX_STORE_U8(a,v) (bytes[uint32_t(a)]=(v))
int version=0,qos=0;
void __savegprlr_25(PPCContext&,uint8_t*){}
void __restgprlr_25(PPCContext&,uint8_t*){}
void sub_82542C18(PPCContext&c,uint8_t*){c.r3.u64=0x10000;}
void sub_828157A0(PPCContext&,uint8_t*){}
void sub_82815DD0(PPCContext&c,uint8_t*){c.r3.u64=version;}
void sub_825551E8(PPCContext&c,uint8_t*){words[c.r3.u32]=0x20000;words[0x10000+348]=0x20000;}
void sub_82555030(PPCContext&c,uint8_t*){words[c.r3.u32]=0x40000;bytes[c.r3.u32+4]=1;}
void sub_8253B560(PPCContext&c,uint8_t*){c.r3.u64=0x10000;}
void sub_82824C58(PPCContext&c,uint8_t*){++qos;c.r3.u64=16;}
'''
test = r'''
bool validate(int v){words.clear();bytes.clear();doubles.clear();version=v;qos=0;PPCContext c;c.r1.u64=0x80000;c.r5.u64=0x30000;sub_82546178(c,nullptr);return c.r3.u32==1;}
int main(){
 assert(!validate(192359) && qos==0);
 assert(validate(192641) && qos==1);
 auto room=nfsmw::pc::AdaptRoom("P=V%3d192359%0aP%3d1%0a");
 auto p=nfsmw::pc::Field(room,"P");
 assert(validate(std::stoi(p.substr(4,6))) && qos==1);
 assert(!validate(194010) && qos==0);
 std::cout<<"PASS: actual USA sub_82546178 rejects captured PC192359 before QoS; PC adapter alias reaches QoS/acceptance; unknown version still rejected. No session/race emulation.\n";
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-room-') as d:
    p=Path(d)
    (p/'test.cpp').write_text(prefix+validator+test)
    subprocess.run(['clang++','-std=c++23','-O1','-pthread','-fsanitize=address,undefined','-I'+str(root/'ios/src/multiplayer'),str(p/'test.cpp'),str(root/'ios/src/multiplayer/pc_gateway.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
