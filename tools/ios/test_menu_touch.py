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
 assert(HintAt(hints,30,20)->button==Right);
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
 // Root-level pause frame shares a texture with its outer decorative frame.
 std::vector<MenuNode> pause;
 for (auto [cx,cy]:{std::pair{81.f,-18.f},{152.f,-18.f},{81.f,43.f},{152.f,43.f},
                   {-280.f,-90.f},{280.f,-90.f},{-280.f,79.f},{280.f,79.f}})
   pause.push_back({uint32_t(pause.size()+1),0,0,0x475A90F5,1,cx,cy,32,32});
 auto pf=FocusFrames(pause);assert(pf.size()==1 && pf[0].rect.Contains(116,12));
 // Rotated car-category arrows must send Up/Down, title arrows remain Left/Right.
 std::vector<Hint> car={{0x0603C1D1,0x1A6D3D2C,-270,-197,20,20,Left,false},
                       {0xC6EAC384,0x1A6D3D2C,-276,-152,20,20,Right,false},
                       {0x0603C1D1,0x1A6D3D2C,-83,-174,20,20,Left,false},
                       {0xFEA90A33,Hash("CIRCLE"),-29,208,20,20,8,true}};
 CorrectMenuHints(car,true);
 assert(car[0].button==Up && car[1].button==Down && car[2].button==Left && car[3].button==(1<<10));
 assert(WidgetDragAt("Car_Select.fng",{},car,-193,-170)==VerticalDrag);
 assert(WidgetDragAt("Car_Select.fng",{},car,0,70)==HorizontalDrag);
 assert(WidgetDragAt("Showcase.fng",{},car,0,70)==CameraDrag);
 assert(WidgetDragAt("Showcase.fng",{},car,0,230)==NoDrag);
 std::vector<MenuNode> panel={{1,0,0,0,1,0,0,300,330}};
 assert(WidgetDragAt("MC_List.fng",panel,{},0,-60)==VerticalDrag);
 assert(WidgetDragAt("MC_List.fng",panel,{},300,-60)==NoDrag);
 panel[0].type=9;assert(WidgetDragAt("MC_List.fng",panel,{},0,-60)==VerticalDrag);
 std::vector<Hint> tracks={{1,0,-25,172,20,20,LT,false},{2,0,266,172,20,20,RT,false},
                           {3,0,-21,-171,20,20,Left,false}};
 assert(WidgetDragAt("Track_Select.fng",{},tracks,100,0)==HorizontalDrag);
 assert(WidgetDragAt("WorldMapMain.fng",{},tracks,100,0)==NoDrag); // distinct map behavior

 // Options contain repeated Left/Right columns, not rotated category arrows.
 std::vector<Hint> options;
 for (int i=1;i<=3;++i) {
   const float y=-106+24*i;
   options.push_back({Hash("LEFT_ARROW_"+std::to_string(i)),0x1A6D3D2C,38,y,20,20,Left,false});
   options.push_back({Hash("RIGHT_ARROW_"+std::to_string(i)),0x1A6D3D2C,248,y,20,20,Right,false});
 }
 CorrectMenuHints(options,false);
 assert(options[0].button==Left && options[1].button==Right && options[4].button==Left);
 std::vector<FocusFrame> option_focus={{0,{-280,-96,276,-68}}};
 auto om=BuildMenuModel("Options.fng",{},options,option_focus);
 assert(om.items.size()==3 && om.selected==Hash("LEFT_ARROW_1"));
 assert(OptionArrowAt(om,options,om.items[0],38,-82)==Left);
 assert(OptionArrowAt(om,options,om.items[0],248,-82)==Right);
 assert(OptionArrowAt(om,options,om.items[0],38,-58)==0);
 assert(ModelDragAt(om,0,-82)==MenuDrag && ModelDragAt(om,0,-58)==VerticalDrag);
 assert(ModelDragAt(om,350,-82)==NoDrag);
 assert(SelectItem(om,30,200,&om.items[2])==(SelectChoice|Down));
 assert(SelectItem(om,30,200,&om.items[2])==WaitForChoice);
 om.selected=om.items[1].key;item_selection.last_move-=std::chrono::milliseconds(230);
 assert(SelectItem(om,30,200,&om.items[2])==(SelectChoice|Down));
 om.selected=om.items[2].key;item_selection.last_move-=std::chrono::milliseconds(200);
 assert(SelectItem(om,30,200,&om.items[2])==WaitForChoice);
 assert(SelectItem(om,30,200,&om.items[2])==SelectionDone); // NEVER A on arrival
 assert(SelectItem(om,30,201,&om.items[2])==SelectionDone); // settings confirmation manual
 // Real full-width selection frame, previously rejected by the 540-unit limit.
 std::vector<MenuNode> wide;
 for (auto [cx,cy]:{std::pair{-280.f,-96.f},{276.f,-96.f},{-280.f,-68.f},{276.f,-68.f}})
   wide.push_back({uint32_t(wide.size()+1),0,0,0x6FB79A55,1,cx,cy,9,9});
 assert(FocusFrames(wide).size()==1);
 // Profile shadow text merges into one row. Selecting never loads the profile.
 std::vector<MenuNode> profiles={{50,0,0,0,1,0,0,300,300},
   {51,0,1,0,2,-130,-60,1,1},{52,0,2,0,2,-129,-59,1,1},
   {53,0,3,0,2,-130,-30,1,1}};
 auto pm=BuildMenuModel("MC_List.fng",profiles,{},{{0,{-140,-70,140,-50}}});
 assert(pm.items.size()==2 && pm.selected==51 && ItemAt(pm,0,-30)->key==53);
 assert(SelectItem(pm,40,202,&pm.items[0])==SelectionDone);
 assert(SelectItem(pm,40,203,&pm.items[1])==(SelectChoice|Down));
 pm.selected=53;item_selection.last_move-=std::chrono::milliseconds(200);
 assert(SelectItem(pm,40,203,&pm.items[1])==WaitForChoice);
 assert(SelectItem(pm,40,203,&pm.items[1])==SelectionDone);
 // Event grid includes the entire named viewport, including gaps between tiles.
 std::vector<MenuNode> grid={{70,0,Hash("ARRAY_SCROLL_REGION"),0,1,-135,70,180,150}};
 for (int i=0;i<4;++i) grid.push_back({uint32_t(71+i),0,Hash("EVENT_ICON_"+std::to_string(i+1)),0,1,
   -200.f+100*(i%2),30.f+70*(i/2),50,50});
 auto gm=BuildMenuModel("ChallengeSeries.fng",grid,{},{{1,{-225,5,-175,55}}});
 assert(gm.items.size()==4 && gm.selected==Hash("EVENT_ICON_1"));
 assert(ModelDragAt(gm,-150,65)==MenuDrag && ItemAt(gm,-150,65)==nullptr);
 assert(SelectItem(gm,50,204,&gm.items[3])==(SelectChoice|Right));
 gm.selected=gm.items[1].key;item_selection.last_move-=std::chrono::milliseconds(230);
 assert(SelectItem(gm,50,204,&gm.items[3])==WaitForChoice);
 assert(SelectItem(gm,50,204,&gm.items[3])==(SelectChoice|Down));
 gm.selected=gm.items[3].key;item_selection.last_move-=std::chrono::milliseconds(230);
 assert(SelectItem(gm,50,204,&gm.items[3])==WaitForChoice);
 assert(SelectItem(gm,50,204,&gm.items[3])==SelectionDone);
 assert(SelectItem(gm,50,205,&gm.items[3])==1); // second tap can launch
 gm.selected=gm.items[0].key;
 assert(SelectItem(gm,50,206,&gm.items[3])==(SelectChoice|Right));
 assert(SelectItem(gm,51,206,&gm.items[3])==-1); // replaced package cancels
 item_selection.began-=std::chrono::milliseconds(3000);
 assert(SelectItem(gm,50,206,&gm.items[3])==-1); // no forced accept on timeout
 grid.push_back({80,0,0x444969FD,0,5,-240,10,1,1});
 grid.push_back({81,0,0x444969FE,0,5,-240,170,1,1});
 std::vector<Hint> event_arrows;EventArrowHints(event_arrows,grid,gm);
 assert(event_arrows.size()==2 && event_arrows[0].button==Up && event_arrows[1].button==Down);
 // Rap Sheet bullet rows with white selected text, without corner frames.
 std::vector<MenuNode> rap;
 for (int i=0;i<6;++i) rap.push_back({uint32_t(90+i),0,uint32_t(100+i),0xC6AFDD7E,1,-270,28.f*i,12,12});
 // Multiple backings must not identify the last row as selected.
 for (int i=0;i<6;++i) rap.push_back({uint32_t(200+i),0,0,0,9,0,28.f*i,560,24});
 rap.push_back({99,0,0,0,2,-272,19,1,1,255,255,255,255});
 auto rm=BuildMenuModel("RapSheetMain.fng",rap,{},{});
 assert(rm.items.size()==6 && rm.selected==101 && ModelDragAt(rm,100,100)==VerticalDrag);
 auto ambiguous=rap;
 ambiguous.push_back({199,0,0,0,2,-272,47,1,1,255,255,255,255});
 assert(BuildMenuModel("RapSheetMain.fng",ambiguous,{},{}).selected==0);
 auto unselected=rap;unselected.back().blue=100;
 assert(BuildMenuModel("RapSheetMain.fng",unselected,{},{}).selected==0);
 assert(SelectItem(rm,60,207,&rm.items[1])==1); // selected row opens
 om.selected=0;assert(SelectItem(om,30,208,&om.items[0])==-1); // no observable focus, no input
 gm.selected=gm.items[0].key;
 assert(SelectItem(gm,50,209,&gm.items[3])==(SelectChoice|Right));
 gm.items[3].x+=20;
 assert(SelectItem(gm,50,209,&gm.items[3])==-1); // target moved or viewport repopulated
 // Viewport repopulation acknowledges a vertical move even if focus stays in
 // the same screen slot; selecting still never sends A.
 gm.items[3].x-=20;gm.selected=gm.items[1].key;
 assert(SelectItem(gm,50,210,&gm.items[3])==(SelectChoice|Down));
 ++gm.viewport;item_selection.last_move-=std::chrono::milliseconds(230);
 assert(SelectItem(gm,50,210,&gm.items[3])==WaitForChoice);
 assert(SelectItem(gm,50,210,&gm.items[3])==SelectionDone);
 std::vector<MenuNode> sub={{110,0,Hash("ARRAY_SCROLL_REGION"),0,1,0,0,300,200},
  {111,0,Hash("OPTION_NAME_1"),0,2,-100,-30,1,1},
  {112,0,Hash("OPTION_NAME_2"),0,2,-100,0,1,1},{113,0,0,0,2,-110,-39,1,1,255,255,255,255}};
 auto rs=BuildMenuModel("RapSheetUS.fng",sub,{},{});
 assert(rs.items.size()==2); // named subpage rows use the same label-focus rule
 assert(rs.selected==Hash("OPTION_NAME_1"));
 // Real ranking label identities, exclude the right-hand numeric ranks.
 std::vector<MenuNode> ranks={{300,0,0x21A45336,0,2,-278,-97,1,1,100,255,170,255},
   {301,0,0x21A45337,0,2,-278,-70,1,1,255,255,255,255},
   {302,0,0x7711109C,0,2,277,-71,1,1,255,255,255,255}};
 auto ranking=BuildMenuModel("RapSheetRankings.fng",ranks,{},{});
 assert(ranking.items.size()==2 && ranking.selected==0x21A45337);
 assert(ItemAt(ranking,0,-88)->key==0x21A45336);
 // Narrow profile focus need not contain the full-width row's horizontal center.
 auto narrow=BuildMenuModel("MC_List.fng",profiles,{},{{0,{-139,-61,-90,-41}}});
 assert(narrow.selected==51 && SelectItem(narrow,41,212,&narrow.items[0])==SelectionDone);
 assert(WidgetDragAt("RapSheetVD.fng",{}, {},100,100)==VerticalDrag);
 grid[1].texture=1;grid[2].texture=2;
 const auto content_a=BuildMenuModel("ChallengeSeries.fng",grid,{},{}).viewport;
 std::reverse(grid.begin(),grid.end());
 assert(BuildMenuModel("ChallengeSeries.fng",grid,{},{}).viewport==content_a);
 for (auto& node:grid) if (node.hash==Hash("EVENT_ICON_1")) node.texture=3;
 assert(BuildMenuModel("ChallengeSeries.fng",grid,{},{}).viewport!=content_a);
 assert(ShowcasePan(0)==0 && ShowcasePan(.5f)<-.8f && ShowcasePan(-.5f)>.8f);
 assert(ShowcasePan(1)==-1 && ShowcasePan(-10)==1);
 assert(CameraMotion(0)==0 && CameraMotion(.5f)>.35f && CameraMotion(-2)<-.35f);
 assert(CameraMotion(8)==1 && CameraMotion(14,14)==1);
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
 puts("PASS: FE walker, row/grid selection without auto-accept, option axes/arrows, event viewport, Rap Sheet, camera motion and popup safeguards");
}
'''
with tempfile.TemporaryDirectory() as t:
 p=pathlib.Path(t);(p/'test.cpp').write_text(prefix+walker+popup_prefix+popup+test)
 subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I',str(root/'ios/src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 subprocess.run([str(p/'test')],check=True)
