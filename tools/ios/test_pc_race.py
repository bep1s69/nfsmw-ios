#!/usr/bin/env python3
"""Compile actual PC-only factory diagnostics; verify original result unchanged."""
from pathlib import Path
import subprocess
import tempfile
root=Path(__file__).resolve().parents[2]
prefix=r'''
#pragma once
#include <cstdint>
#include <cassert>
#include <string>
#include <unordered_map>
#include <vector>
struct Reg {union{uint64_t u64=0;uint32_t u32;};};
struct PPCContext{Reg r3,r4,r20,r22;uint64_t lr=0;};
#define REX_FUNC(n) void n(PPCContext&ctx,uint8_t*base)
extern std::unordered_map<uint32_t,uint32_t> words;
#define REX_LOAD_U32(a) words[uint32_t(a)]
'''
test=r'''
#include "nfsmw_pch.h"
std::unordered_map<uint32_t,uint32_t> words;
bool pc=true;uint32_t result=0;int originals=0;std::vector<std::string> logs;
namespace nfsmw::pc{bool Active(){return ::pc;}}
namespace nfsmw::boot{void Trace(const std::string&s){logs.push_back(s);}}
extern "C" REX_FUNC(__imp__sub_8212BFB8){++originals;ctx.r3.u64=result;ctx.r4.u64=0;}
extern "C" REX_FUNC(sub_8212BFB8);
PPCContext C(){PPCContext c;c.r3.u64=0x1000;c.r4.u64=0x2000;c.r22.u64=0x3000;c.lr=0x82474944;return c;}
int main(){
 words[0x1000]=0x12345678;words[0x2000]=11;words[0x2004]=22;words[0x2008]=33;
 words[0x3000+4432]=0x3f0888cd;
 // A registered factory whose callback returns null, versus missing registration.
 words[0x82c5e444]=0x4000;words[0x4000]=0x12345678;words[0x4004]=0x82111111;
 auto c=C();sub_8212BFB8(c,nullptr);assert(c.r3.u32==0 && originals==1);
 assert(logs.size()==2 && logs[0].find("callback=82111111")!=std::string::npos && logs[1].find("result=00000000")!=std::string::npos);
 logs.clear();words[0x4000]=0x87654321;c=C();sub_8212BFB8(c,nullptr);
 assert(c.r3.u32==0 && logs[0].find("match=00000000")!=std::string::npos);
 logs.clear();words[0x4000]=0x12345678;result=0x12340000;c=C();sub_8212BFB8(c,nullptr);
 assert(c.r3.u32==result && logs[1].find("result=12340000")!=std::string::npos);
 logs.clear();pc=false;c=C();sub_8212BFB8(c,nullptr);assert(c.r3.u32==result && logs.empty());
 pc=true;c=C();c.lr=0x82500000;sub_8212BFB8(c,nullptr);assert(logs.empty());
 logs.clear();for(int i=0;i<20;++i){c=C();sub_8212BFB8(c,nullptr);}
 assert(logs.size()==10); // 3 earlier traced calls + 5 remaining, cap8 total
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-pc-race-') as d:
 p=Path(d);(p/'nfsmw_pch.h').write_text(prefix);(p/'test.cpp').write_text(test)
 subprocess.run(['clang++','-std=c++23','-O1','-fsanitize=address,undefined','-I'+str(p),str(p/'test.cpp'),str(root/'ios/src/multiplayer/game_pc_race.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
 print('PASS: actual factory diagnostics distinguish missing registration/null callback result, preserve original results and mode/callsite bypass, cap output. No crash fixed.')
