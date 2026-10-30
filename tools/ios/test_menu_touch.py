#!/usr/bin/env python3
"""Compile actual FE hint walker against bounded fake guest memory and gesture policy."""
import pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[2]
s=(root/'ios/src/game_scene_size.cpp').read_text()
walker=s.split('// MENU_TOUCH_HINTS_BEGIN:',1)[1].split('\n',1)[1].split('// MENU_TOUCH_HINTS_END',1)[0]
popup=s.split('// MENU_TOUCH_POPUP_BEGIN',1)[1].split('// MENU_TOUCH_POPUP_END',1)[0]
prefix=r'''
#include "menu_touch_policy.h"
#include <algorithm>
#include <cassert>
#include <chrono>
#define REXLOG_INFO(...) ((void)0)
#include <cmath>
#include <cstdio>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#include <utility>
std::unordered_map<uint32_t,uint32_t> words;
std::unordered_map<uint32_t,float> floats;
#define REX_LOAD_U32(a) words[uint32_t(a)]
bool Plausible(uint32_t a) { return a>=0x10000 && a<0x80000000; }
float LoadF(uint8_t*,uint32_t a) { return floats[a]; }
constexpr uint32_t kListVtable=0x82080030;
void Object(uint32_t o,uint32_t type,float x,float y,float w,float h,uint32_t hash=0,uint32_t texture=0) {
 words[o+0x18]=type;words[o+0x1c]=0x42000000; // real visible flags lacking the HUD-only bit
 words[o+0x10]=hash;words[o+0x24]=texture;
 words[o+0x2c]=o+0x800; floats[o+0x800+28]=x;floats[o+0x800+32]=y;
 floats[o+0x800+56]=w;floats[o+0x800+60]=h;
}
'''
popup_prefix=r'''
struct MenuPackage {
 uint32_t address;std::string name;std::vector<Hint> hints;
 std::vector<MenuNode> nodes;std::vector<FocusFrame> frames;
};
'''
test=r'''
int main() {
 using namespace nfsmw::menu_touch;
 assert(TapAction(0,true)==1 && TapAction(0,false)==0);
 assert(TapAction(8,true)==8 && TapAction(8,false)==8);
 assert(TapAction(-1,true)==0 && TapAction(-1,false)==0);
 // Two-finger B is separate from blank-tap policy; a B hint is always valid.
 assert(TapAction(2,false)==2);
 assert(BackAction(2,true)==2 && BackAction(2,false)==0 && BackAction(1,true)==0);
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
 Object(0x60000,1,300,20,30,30,0,Hash("CIRCLE"));words[0x60000+0x1c]=0x47C00000; // hidden
 std::vector<Hint> hints;int budget=2000;
 FindHints(nullptr,0x10000,0,0,1,1,0,false,0,hints,budget);
 assert(hints.size()==3); // old HUD-only visibility test rejected this root
 // The guest show/hide methods use bit26, not bit23 from HUD context.
 static_assert(kMenuHidden == 0x04000000);

 assert(hints[0].x==120 && hints[0].y==20); // independent group x/y scales
 assert(HintAt(hints,120,20)->button==1);
 assert(HintAt(hints,190,20)->button==1); // text beside A also taps A
 assert(HintAt(hints,300,20)->button==LT);
 assert(HintAt(hints,365,20)->button==LT); // trigger hint text is tappable too // icon without companion text
 assert(HintAt(hints,500,20)->button==Right);
 assert(HintAt(hints,700,20)==nullptr); // hidden Y cannot activate
 assert(ButtonOfTexture(Hash("R2"))==RT);
 assert(ButtonOfTexture(Hash("L1"))==LT && ButtonOfTexture(Hash("R1"))==RT);
 assert(ButtonOfTexture(Hash("LB"))==(1<<9) && ButtonOfTexture(Hash("RB"))==(1<<10));
 assert(ButtonOfObject(0x0603C1D1)==Left && ButtonOfObject(0x6126AB37)==Right && ButtonOfObject(0xC6EAC384)==Right);
 assert(ButtonOfObject(0xD1CDA594)==LT && ButtonOfObject(0x9345E4A7)==RT);
 // Standalone face icon, mirrored generic arrow, unknown compact icon.
 Object(0x70000,1,-30,20,30,30,0,Hash("SQUARE"));words[0x70000+4]=0x71000;
 Object(0x71000,9,30,20,-32,32,0,Hash("ARROW"));words[0x71000+4]=0x72000;
 Object(0x72000,1,120,20,30,30,0,12345);
 hints.clear();budget=2000;FindHints(nullptr,0x70000,0,0,1,1,0,false,0,hints,budget);
 assert(HintAt(hints,-30,20)->button==4);
 assert(HintAt(hints,30,20)->button==Left);
 assert(HintAt(hints,120,20)->button==0); // unknown not guessed as A
 // Corrupt sibling cycle must stop at the shared budget.
 words[0x72000+4]=0x70000;hints.clear();budget=10;
 FindHints(nullptr,0x70000,0,0,1,1,0,false,0,hints,budget);assert(budget==0);
 // A hidden parent excludes all descendants.
 words[0x10000+0x1c]=0x04000000;hints.clear();budget=2000;
 FindHints(nullptr,0x10000,0,0,1,1,0,false,0,hints,budget);assert(hints.empty());
 // Real test6 focus-frame corners, grouped independently of nearby unknown icon.
 std::vector<MenuNode> nodes;
 Object(0x80000,5,100,10,2,.5);
 words[0x80000+0x5c]=kListVtable;words[0x80000+0x60]=4;words[0x80000+0x64]=0x81000;
 for (int i=0;i<4;++i) {
   uint32_t o=0x81000+i*0x1000;
   Object(o,1,i%2?20:-20,i/2?40:-40,9,9,0,0x6FB79A55);
   words[o+4]=i==3?0:o+0x1000;
 }
 hints.clear();budget=2000;
 FindHints(nullptr,0x80000,0,0,1,1,0,false,0,hints,budget,&nodes);
 auto frames=FocusFrames(nodes);
 assert(frames.size()==1 && frames[0].rect.Contains(100,10));
 assert(!frames[0].rect.Contains(160,10));
 assert(ScrollAt(nodes,hints,frames,100,10,false));
 assert(!ScrollAt(nodes,hints,frames,-300,-150,false));
 // Incomplete/hidden highlight cannot turn empty space into an accept target.
 words[0x84000+0x1c]=kMenuHidden;nodes.clear();hints.clear();budget=2000;
 FindHints(nullptr,0x80000,0,0,1,1,0,false,0,hints,budget,&nodes);
 assert(FocusFrames(nodes).empty());
 // Live carousel arrows create a band; areas away from the band stay inert.
 hints={{1,0,-30,150,20,20,Left,false},{2,0,280,150,20,20,Right,false}};
 assert(ScrollAt({},hints,{},160,150,false));
 assert(!ScrollAt({},hints,{},160,20,false));
 // World map canvas from zoom/category controls; legend stays outside it.
 hints.push_back({3,0,-245,169,20,20,LT,false});
 hints.push_back({4,0,23,169,20,20,RT,false});
 hints.push_back({5,0,44,-184,20,20,Left,false});
 assert(ScrollAt({},hints,{},-100,0,true));
 assert(!ScrollAt({},hints,{},200,0,true));
 // Popup choices are wide images; a hidden choice never enters the snapshot.
 nodes={{0x90000,1,0xB8A7C6CC,0,1,2,82,154,32},
        {0x91000,1,0xB8A7C6CD,0,1,167,82,154,32}};
 auto choices=DialogChoices(nodes);assert(choices.size()==2);
 assert(NodeRect(choices[1]).Contains(180,80));
 assert(!NodeRect(choices[0]).Contains(180,80));
 // Popup: choose an unselected button, then accept only its observed highlight.
 MenuPackage pkg{17,"InGameDialog.fng",{},nodes,{{1,NodeRect(nodes[0])}}};
 assert(PopupAction(pkg,100,167,82)==(SelectChoice|Right));
 assert(PopupAction(pkg,100,167,82)==WaitForChoice);
 popup.started-=std::chrono::milliseconds(200);
 pkg.frames={{1,NodeRect(nodes[1])}};
 assert(PopupAction(pkg,100,167,82)==WaitForChoice);
 assert(PopupAction(pkg,100,167,82)==1);
 pkg.frames={{1,NodeRect(nodes[0])}};
 assert(PopupAction(pkg,101,167,82)==(SelectChoice|Right));
 popup.started-=std::chrono::milliseconds(900);
 assert(PopupAction(pkg,101,167,82)==-1); // no guessed accept after failed move
 assert(PopupAction(pkg,102,2,82)==1); // selected choice accepts directly
 assert(PopupAction(pkg,103,-200,-150)==-1); // blank modal never falls through
 assert(PopupAction(pkg,104,167,82)==(SelectChoice|Right));
 ++pkg.address;assert(PopupAction(pkg,104,167,82)==-1); // package replaced
 pkg.frames.clear();assert(PopupAction(pkg,105,167,82)==-1);
 // Three visible choices: verify the intermediate focus before a second step.
 pkg.address=17;pkg.nodes.push_back({0x92000,1,0xB8A7C6CE,0,1,-163,82,154,32});
 pkg.frames={{1,NodeRect(pkg.nodes[2])}};
 assert(PopupAction(pkg,106,167,82)==(SelectChoice|Right));
 pkg.frames={{1,NodeRect(pkg.nodes[0])}};
 popup.last_move-=std::chrono::milliseconds(230);
 assert(PopupAction(pkg,106,167,82)==(SelectChoice|Right));
 assert(PopupAction(pkg,106,167,82)==WaitForChoice); // no repeat until focus moves
 puts("PASS: gesture direction/repeat; actual FE walker nested/standalone/trigger/arrow/label/hidden/cycle cases");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=pathlib.Path(t);(p/'test.cpp').write_text(prefix+walker+popup_prefix+popup+test)
 subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I',str(root/'ios/src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
