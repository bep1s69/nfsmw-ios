// NFSMW Recompiled (iOS) - menus and pause screens told from driving
//
// For the 30 fps cap in menus (battery.mm) and the touch controls' own
// switch between the PAD and DRIVE layouts (touch_controls.mm). USA edition
// addresses.
//
// THE GAME FLOW STATE
//
// TheGameFlowManager is at 0x82A39AB8 (BeginGameFlowLoadingFrontEnd,
// sub_823B4428, writes its single function and the name "LoadingFrontEnd"
// there). Its word at +32 is CurrentGameFlowState, with the PC's values
// (1 loading the frontend, 2 unloading it, 3 in the frontend, 4 loading a
// region, 5 loading a track, 6 racing, 7 unloading the track, 8 unloading the
// region): 81 readers compare it with 3 or 6, and the GameFlowManager's
// functions write 1-9 (sub_823B3C00 writes 6). "Racing" is any time in the
// world, free roam included.
//
// MENUS IN THE WORLD
//
// In the world, the pause menu and the screens like it are frontend packages
// pushed over the HUD. The game asks cFEng (its pointer at 0x82A2C5C4)
// whether one is up with sub_82284D70, IsPackagePushed(cFEng, name): EPause
// (its event, sub_8238E0B8) pushes "Pause_Main.fng" only if that says no.
// Here the same question is asked for the packages below, which stop the
// driving (pause, its sub-screens, the post-race screens, dialogs, the map).
// Short overlays that come while driving (SMS messages, fades, the race's
// title, EA_Trax.fng: the song's name at the start of a race) are not in it.
//
// WHEN
//
// After GameFlowManager::Service (sub_823B4158), which the main loop calls
// once a frame on the game's thread, whatever the state: the guest function
// is called there with the game's own context, as game_scene_size.cpp calls
// FindObject. Changes go to battery::SetInMenu and are logged ("[game]").

#include <cstdint>
#include <string>

#include "nfsmw_pch.h"

#include <rex/logging.h>

#include "battery.h"

extern "C" void __imp__sub_823B4158(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void sub_82284D70(PPCContext& __restrict ctx, uint8_t* base);

namespace {

constexpr uint32_t kGameFlowState = 0x82A39AB8 + 32;
constexpr uint32_t kFeng = 0x82A2C5C4;  // cFEng*
constexpr uint32_t kRacing = 6;

// The packages that mean "not driving" while in the world. Their names are
// copied into guest memory once (IsPackagePushed takes a guest string).
const char* const kMenuPackages[] = {
    "Pause_Main.fng",          "Pause_Options.fng",          "Pause_Controller.fng",
    "Pause_Performance_Tuning.fng", "X360_Pause.fng",        "InGameRaceSheet.fng",
    "InGameMilestones.fng",    "InGameBounty.fng",           "InGameRivalBio.fng",
    "InGameRivalChallenge.fng", "InGameReputationOverview.fng", "InGame_MC_Main.fng",
    "InGameDialog.fng",        "InGameAnyMovie.fng",         "WS_InGameAnyMovie.fng",
    "InGameAnyTutorial.fng",   "PostRace_Results.fng",       "PostRace_Pursuit.fng",
    "PostRace_MilestoneRewards.fng", "PostBusted.fng",       "GameOver.fng",
    "GameWon.fng",             "WorldMapMain.fng",           "EngageEventDialog.fng",
    "ControllerUnplugged.fng", "Loading.fng",                "WS_Loading.fng",
    "SixDaysLater.fng",
};
constexpr int kMenuCount = int(sizeof(kMenuPackages) / sizeof(kMenuPackages[0]));

// Full-screen fades while in the world (the black loading screen before a
// race is FadeScreen.fng, IPA79): not menus (the driving goes on under them,
// and the touch controls keep their layout). It stays pushed once it has
// come (IPA79: no "gone" in a whole race), so only its coming is told to
// game_scene_size.cpp, which holds the HUD's size back for a moment as it
// would shrink the black screen too.
const char* const kFadePackages[] = {"FadeScreen.fng", "FadeScreenNoLoadingBar.fng", "BLACK_BACKGROUND.fng",
                                     "BLACK_FADE_OUT.fng"};
constexpr int kFadeCount = int(sizeof(kFadePackages) / sizeof(kFadePackages[0]));

const char* StateName(uint32_t s) {
  switch (s) {
    case 0: return "none";
    case 1: return "loading the frontend";
    case 2: return "unloading the frontend";
    case 3: return "in the frontend";
    case 4: return "loading a region";
    case 5: return "loading a track";
    case 6: return "in the world";
    case 7: return "unloading the track";
    case 8: return "unloading the region";
  }
  return "other";
}

// The names in guest memory: a block of the game's heap would need its
// allocator; the names go in the guest stack's unused space below r1 instead,
// written before each call (the callee's frame starts below them).
uint32_t PutName(PPCContext& ctx, uint8_t* base, const char* name, uint32_t at) {
  const size_t n = std::char_traits<char>::length(name) + 1;
  for (size_t i = 0; i < n; ++i) REX_STORE_U8(at + uint32_t(i), uint8_t(name[i]));
  return at;
}

// The first of these packages up, or -1.
int PushedPackage(PPCContext& ctx, uint8_t* base, const char* const* packages, int count) {
  const uint32_t feng = REX_LOAD_U32(kFeng);
  if (!feng) return -1;
  const PPCContext saved = ctx;
  // 512 bytes below the stack pointer for the name, the callee's frame below
  // that: r1 moved down past them for the call.
  const uint32_t name_at = saved.r1.u32 - 512;
  int found = -1;
  for (int i = 0; i < count && found < 0; ++i) {
    ctx = saved;
    ctx.r1.u64 = name_at - 64;
    ctx.r3.u64 = feng;
    ctx.r4.u64 = PutName(ctx, base, packages[i], name_at);
    sub_82284D70(ctx, base);
    if (ctx.r3.u8) found = i;
  }
  ctx = saved;
  return found;
}

}  // namespace

// Counts the world's starts and the fades' coming (kFadePackages); read by
// game_scene_size.cpp on the game's thread.
extern "C" {
uint32_t nfsmw_world_fades = 0;
}
namespace {
bool fade_up = false;
}

extern "C" REX_FUNC(sub_823B4158) {
  __imp__sub_823B4158(ctx, base);
  static uint32_t last_state = ~0u;
  static int last_menu = -2;
  const uint32_t state = REX_LOAD_U32(kGameFlowState);
  const int menu = state == kRacing ? PushedPackage(ctx, base, kMenuPackages, kMenuCount) : -1;
  const int fade = state == kRacing && menu < 0 ? PushedPackage(ctx, base, kFadePackages, kFadeCount) : -1;
  if ((state == kRacing) != (last_state == kRacing) || (fade >= 0 && !fade_up)) ++nfsmw_world_fades;
  // Under a menu the fades are not asked about: kept as they were.
  if ((menu < 0 || state != kRacing) && (fade >= 0) != fade_up) {
    fade_up = fade >= 0;
    static int fade_lines = 40;
    if (fade_lines-- > 0) REXLOG_INFO("[game] fade {}", fade >= 0 ? kFadePackages[fade] : "gone");
  }
  if (state == last_state && menu == last_menu) return;
  static int lines_left = 400;  // in case something flickers every frame
  const bool log = lines_left-- > 0;
  const bool driving = state == kRacing && menu < 0;
  const bool was_driving = last_state == kRacing && last_menu < 0;
  if (log && state != last_state) {
    REXLOG_INFO("[game] game flow state {} ({})", state, StateName(state));
  }
  if (log && (driving != was_driving || menu != last_menu)) {
    if (driving) {
      REXLOG_INFO("[game] driving");
    } else if (menu >= 0) {
      REXLOG_INFO("[game] menu: {}", kMenuPackages[menu]);
    } else if (was_driving || last_state == ~0u) {
      REXLOG_INFO("[game] menu: {}", StateName(state));
    }
  }
  last_state = state;
  last_menu = menu;
  nfsmw::battery::SetInMenu(!driving);
}
