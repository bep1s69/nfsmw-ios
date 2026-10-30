#!/usr/bin/env python3
"""Compile actual FE hint walker against bounded fake guest memory and gesture policy."""
import pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[2]
s=(root/'ios/src/game_scene_size.cpp').read_text()
walker=s.split('// MENU_TOUCH_HINTS_BEGIN:',1)[1].split('\n',1)[1].split('// MENU_TOUCH_HINTS_END',1)[0]
prefix=r'''
#include "menu_touch_policy.h"
#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <string>
#include <unordered_map>
#include <vector>
#include <utility>
std::unordered_map<uint32_t,uint32_t> words;
std::unordered_map<uint32_t,float> floats;
#define REX_LOAD_U32(a) words[uint32_t(a)]
bool Plausible(uint32_t a) { return a>=0x10000 && a<0x80000000; }
float LoadF(uint8_t*,uint32_t a) { return floats[a]; }
constexpr uint32_t kListVtable=0x82080030,kShown=0x00800000;
void Object(uint32_t o,uint32_t type,float x,float y,float w,float h,uint32_t hash=0,uint32_t texture=0) {
 words[o+0x18]=type;words[o+0x1c]=kShown;words[o+0x10]=hash;words[o+0x24]=texture;
 words[o+0x2c]=o+0x800; floats[o+0x800+28]=x;floats[o+0x800+32]=y;
 floats[o+0x800+56]=w;floats[o+0x800+60]=h;
}
'''
test=r'''
int main() {
 using namespace nfsmw::menu_touch;
 static_assert(Hash("CROSS")==0x02959349);
 assert(Direction(20,0,false)==Right && Direction(20,0,true)==Left);
 assert(Direction(0,-20,false)==Up && Direction(0,-20,true)==Down);
 assert(Direction(5,5,false)==0);
 DragRepeat drag;
 assert(drag.Buttons(10,Right)==Right);
 assert(drag.Buttons(10.2,Right)==0);
 assert(drag.Buttons(10.36,Right)==Right);
 assert(drag.Buttons(10.45,Right)==0);
 assert(drag.Buttons(13.72,Left)==Left); // direction changes immediately
 drag.Reset();assert(drag.Buttons(20,0)==0);
 // Root group with FIVE children: old code skipped hints in this shape.
 Object(0x10000,5,100,10,2,.5);
 words[0x10000+0x5c]=kListVtable;words[0x10000+0x60]=5;words[0x10000+0x64]=0x20000;
 Object(0x20000,2,0,0,1,1);words[0x20000+4]=0x30000;
 Object(0x30000,1,10,20,30,30,0,Hash("CROSS"));words[0x30000+4]=0x40000;
 Object(0x40000,1,100,20,30,30,0,Hash("L2"));words[0x40000+4]=0x50000;
 Object(0x50000,1,200,20,30,30,Hash("RIGHT_ARROW_7"));words[0x50000+4]=0x60000;
 Object(0x60000,1,300,20,30,30,0,Hash("CIRCLE"));words[0x60000+0x1c]=0; // hidden
 std::vector<Hint> hints;int budget=2000;
 FindHints(nullptr,0x10000,0,0,1,1,0,false,0,hints,budget);
 assert(hints.size()==3);
 assert(hints[0].x==120 && hints[0].y==20); // independent group x/y scales
 assert(HintAt(hints,120,20)->button==1);
 assert(HintAt(hints,190,20)->button==1); // text beside A also taps A
 assert(HintAt(hints,300,20)->button==LT);
 assert(HintAt(hints,365,20)->button==LT); // trigger hint text is tappable too // icon without companion text
 assert(HintAt(hints,500,20)->button==Right);
 assert(HintAt(hints,700,20)==nullptr); // hidden Y cannot activate
 assert(ButtonOfTexture(Hash("R2"))==RT);
 assert(ButtonOfObject(0xD1CDA594)==LT && ButtonOfObject(0x9345E4A7)==RT);
 // Standalone face icon, mirrored generic arrow, unknown compact icon.
 Object(0x70000,1,-30,20,30,30,0,Hash("SQUARE"));words[0x70000+4]=0x71000;
 Object(0x71000,1,30,20,-32,32,0,Hash("ARROW"));words[0x71000+4]=0x72000;
 Object(0x72000,1,120,20,30,30,0,12345);
 hints.clear();budget=2000;FindHints(nullptr,0x70000,0,0,1,1,0,false,0,hints,budget);
 assert(HintAt(hints,-30,20)->button==4);
 assert(HintAt(hints,30,20)->button==Left);
 assert(HintAt(hints,120,20)->button==0); // unknown not guessed as A
 // Corrupt sibling cycle must stop at the shared budget.
 words[0x72000+4]=0x70000;hints.clear();budget=10;
 FindHints(nullptr,0x70000,0,0,1,1,0,false,0,hints,budget);assert(budget==0);
 // A hidden parent excludes all descendants.
 words[0x10000+0x1c]=0;hints.clear();budget=2000;
 FindHints(nullptr,0x10000,0,0,1,1,0,false,0,hints,budget);assert(hints.empty());
 puts("PASS: gesture direction/repeat; actual FE walker nested/standalone/trigger/arrow/label/hidden/cycle cases");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=pathlib.Path(t);(p/'test.cpp').write_text(prefix+walker+test)
 subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I',str(root/'ios/src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
