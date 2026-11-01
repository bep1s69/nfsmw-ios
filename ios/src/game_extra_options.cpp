// NFSMW Recompiled (iOS) - Extra Options features, ported from the PC mod
// (https://github.com/ExOptsTeam/NFSMWExOpts) to the Xbox 360 code. USA
// edition addresses.
//
// The mod patches PC addresses; each feature's Xbox 360 counterpart was found
// again. Edits to the generated code: tools/ios/patch_game_extra_options.py.
//
// SELECTABLE MARKER COUNT (Extra Options: Gameplay > SelectableMarkerCount)
//
// After beating a Blacklist rival the game shows six markers and lets you
// pick 2. On PC the mod changes that 2 in four instructions; on the Xbox 360
// the same four are (found by tracing the screen the game opens after a
// rival race, then the code that fills it in):
//
//   sub_82586768  cmpwi r3,2 / bge   no more picks once the limit is reached
//   sub_82586768  cmpwi r3,2 / blt   the selection is done at the limit
//   sub_82586E78  subfic r6,r30,2    "picks left" on screen
//   sub_82586E78  subfic r6,r11,2    the same, second label
//
// (sub_82586E28 counts the markers picked so far.) They read
// nfsmw_markers_to_pick(). 1 to 6: the screen has six markers, as the mod's
// own range.
//
// PURCHASED CAR LIMIT (Extra Options: Gameplay > PurchasedCarLimit)
//
// The car lot lets you buy 10 cars (Blacklist and bonus cars do not count).
// On PC the mod writes limit-1 at 0x7C1A77. On the Xbox 360 the car lot
// screen (Car_Select.fng, class built by sub_825644E0) checks it once, in
// sub_82564B88:
//
//   bl sub_822CA1A8       the cars bought (a flag test over the 200 car slots)
//   cmpwi r3,10 / blt     room for one more
//
// sub_822CA1A8 has no other caller. That compare reads
// nfsmw_purchased_car_limit(). 1 to 25, the mod's range.
//
// REMOVE OLD BRIDGE BARRIER (Extra Options: Gameplay > RemoveOldBridgeBarrier)
//
// The barrier on the road to the Old Bridge is the scenery group
// "SCENERY_GROUP_DOOR". The game looks it up by the hash of that name; the
// mod changes two letters of the string (0x8B2810 'T', 0x8B2817 ' ' on PC) so
// the lookup finds nothing and the barrier is never switched on. On the Xbox
// 360 the string is at 0x82087AC4, hashed at runtime by sub_823B3980 and
// sub_824763D0 (the compiler put the first letter, 'S', in the code as a
// constant, so on the 360 it is the second edit, '_' -> ' ' at +7, that does
// it; both are written, as the mod does). The string is in read-only data:
// the page is made writable for the two bytes and put back.

//
// SKIP MOVIES (Extra Options: Main > SkipMovies)
//
// The game keeps its debug setting SKIPMOVIES (read from a debug config by
// sub_82538C10; 0 on retail) in the word at 0x82A2CE1C. Set, the movie screen
// (sub_82282F18, the message that starts a movie: "%sMOVIES\%s%s%s%s" is
// built next door, in sub_82282E80) reports the movie finished at once
// instead of playing it: the EA logo, the intro and the attract movie are
// skipped and the game goes straight on to "press start". Two other places
// read it (sub_822BBA98, sub_824792D8). On PC the mod writes 1 to the same
// variable (0x926144). Here its three readers see it set while the setting is
// on (the variable itself is left as it is).
//
// QUICK RACE LAPS AND OPPONENTS (Extra Options: LapControllers,
// OpponentControllers)
//
// The PC mod rewrites the limits of the Quick Race options screen's lap and
// opponent selectors. On the 360 each is one function of the options screen
// (the ones that take the left/right button hashes 0x9120409E and
// 0xB5971BF1):
//
//   sub_82561430  laps: below 1 -> 8, above 8 -> 1 (the byte at +32 of the
//                 race type's 24-byte options, in the options at 0x82A2C684)
//   sub_82560C78  opponents: below 1 -> 4 - players, above it -> 1 (+35)
//
// Their limits read nfsmw_laps_min/max() and nfsmw_opponents_min/max(). The
// race itself takes the count as it is (sub_822C4FB8 hands it to the race's
// attributes; no clamp after it was found). More than 3 opponents: on PC the
// 4th and later get odd cars; experimental.
//
// TRAFFIC DENSITY (Extra Options: TrafficControllers)
//
// sub_822C4FB8 turns the race's traffic level (1-3, the options' byte +10)
// into the density the race attribute gets: 10, 30, 50 (the PC mod's three
// bytes at 0x56DD96-0x56DD9E are the same table). They read
// nfsmw_traffic_density(level).
//
// RAIN (Extra Options: Weather)
//
// The rain's tunables are a table of floats in .data, in the PC layout (the
// mod's 0x904A14..0x904B38 are 0x828F9D20..0x828F9E44 here, found by their
// default values 0.02, 0.03, 0.35 in a row): amount (1.0), crossing (0.02),
// fall speed (0.03), gravity (0.35), drop size (0.01), intensity (0.45),
// road reflection (1.0). Written at boot.
//
// Crossing (0.02, PC 0x904A24), fall speed (0.03, 0x904A28) and gravity
// (0.35, 0x904A2C) are 0x828F9D30..0x828F9D38 here (the same offset from the
// table's start as on PC; November 1).
//
// Always rain: the PC mod sets a flag the 360 build does not have where it
// was. Here the rain intensity at a point (sub_824FB818: the scripted
// override at 0x82A2D6A0 if set, SetChanceOfRain's, else the weather
// regions') is 1 while the setting is on.
//
// SPEEDBREAKER (Extra Options: Gameplay > SBRechargeTime,
// SBRechargeSpeedLimit, SBMassMultiplier)
//
// The mod writes three floats in a row in .data (0x901AE4: 25, 100, 2); the
// same three are at 0x828FB8D4 here, the only place they appear in a row.
// Written at boot.
//
// INFRACTION SPEEDS (Extra Options: Pursuit > SpeedingLimit,
// ExcessiveSpeedingLimit, RecklessDrivingLimit)
//
// In m/s, three floats in .rdata, in the PC order (0x8A380C: excessive 80.5,
// speeding 67, reckless 89.4): 0x82061CC4 here, the only match. Written at
// boot (read-only data, made writable for it).
//
// IMPOUND STRIKES (Extra Options: Gameplay > ImpoundStrikesCount,
// MaximumImpoundStrikesCount)
//
// A new car's record (sub_822C9610, FEPlayerCarDB::CreateNewCareerRecord:
// the first free one of 25 records of 56 bytes) is filled in by sub_822CE7D8,
// which sets its strikes byte (+2) to 3, as the PC's 0x580DA7. It is wrapped
// below and the byte rewritten. The most strikes a car can reach
// (g_MaximumMaximumTimesBusted, 5; PC 0x8F4314 after the float 0.25) is the
// word after 0.25 at 0x828FF1FC here. Written at boot.
//
// HEAT LEVEL OVERRIDE (Extra Options: Pursuit > HeatLevelOverride,
// MinimumHeatLevel, MaximumHeatLevel)
//
// The pursuit's heat is clamped to a minimum and maximum (floats at +220 and
// +224 of its object, set per event). On PC the mod writes its own two there
// just before the clamp (0x443DC3: after the 0-14 clamp of an index, then
// fld/fdiv/fadd, mov edx,[esi+E0], mov eax,[esi+DC]). On the 360 the same
// clamp is in sub_82117950 (the 0-14 clamp, then lfs 220(r31), lfs
// 224(r31)); nfsmw_heat_override() writes them first while the setting is on.
// The in-game options' Heat +1 / -1 (0.6) add to the new heat just before
// that clamp (f31 there; nfsmw_heat_step, tools/ios/patch_game_extra_options.py),
// so the event's limits still apply (the override widens them). The clamped
// value goes to r17's virtual +8, the same call the prototype's debug menu
// Set Heat makes (callback 0x822A45E8 there).
//
// Only that clamp: the PC mod also raises the maximum heat in menus and in
// SetHeatLevel (to 10), not ported, so heat above 5 is experimental.
//
// GAME SPEED (Extra Options: Gameplay > GameSpeed)
//
// The PC mod writes the float at 0x901B1C (1.0). It is 0x828FB90C here: same
// neighbours (1.0 then a NaN two words on, after seven zeros), and the code
// that uses it is the PC's: sub_82472F38 loads it first thing and skips its
// work when it is 1.0. sub_82538C10 (the debug config reader) and
// sub_824402B8 also write it, so instead of a write at boot sub_82472F38 is
// wrapped below and sees the game's value times the setting while it runs.
//
// RANDOM QUICK RACE (Extra Options: LapControllers/OpponentControllers >
// RandomRace)
//
// PC 0x56DCB0 fills a random race's options: opponents rand(3)+1, laps
// rand(5)+1 for a circuit, the opponents for a lap knockout, 1 otherwise; the
// mod changes the 3 and the 5 (0x56DCC1, 0x56DCE9). The 360's is
// sub_822C4E68 (the same xorshift with 0x1D872B41, stores to +7 and +4 of the
// options in r4, race type in r5), with the divisions inlined, so it is
// wrapped below and +7/+4 drawn again with the settings' ranges when they
// differ from the game's.
//
// DEBUG FLAGS FROM THE XBOX 360 PROTOTYPE (no PC mod setting)
//
// The October 2005 PAL milestone build (NfsMWEuropeGerMilestone.exe, debug
// menu) registers each menu switch with the address of its variable (widget
// +0x14 name, +0x24 variable). The code that reads those variables was
// matched to the USA build by instruction sequence (the same compiler; most
// functions identical) and the variable read at the same instruction there:
//
//   Infinite NOS            proto 0x82A81DFF, read in 0x82459C98
//                           -> USA 0x82A2CE71, read in sub_82424988 (skips
//                              the NOS use when set)
//   Infinite RaceBreaker    proto 0x82A82238, 0x824A15F0
//                           -> USA 0x82A2D1C6, sub_8246C188 (skips the drain)
//   Show Non-Pursuit Cops   proto 0x82A8153A, 0x822C2E90
//                           -> USA 0x82A2C5FA, sub_8229B840
//   No Cops                 proto: a toggle of the word 0x82A80C4C (non-zero
//                           = no cops)
//                           -> USA 0x82A2BD94; sub_8249D808 is "cops
//                              enabled" (word == 0), sub_820EC5B0 sets it from
//                              a message, readers sub_820EB6A8, sub_824A2DD8,
//                              sub_824A22B0
//
// The retail game still reads all of them; only the menu that set them is
// gone. The three bytes have no writer in the USA code; the cops word is
// written by the game (race start, messages). Each reader is wrapped below
// and sets its variable first while the setting is on.
//
#include <algorithm>
#include <atomic>
#include <cstring>
#include <cstdint>
#include <string_view>

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_INT32(nfsmw_marker_count, 2, "Game",
                     "Markers you pick after beating a Blacklist rival (1-6; the game's is 2)");
REXCVAR_DEFINE_INT32(nfsmw_purchased_car_limit, 10, "Game",
                     "Cars you can buy at the car lot (1-25; the game's is 10)");
REXCVAR_DEFINE_BOOL(nfsmw_remove_old_bridge_barrier, false, "Game",
                    "Remove the barrier that closes the road to the Old Bridge");
// 120 by default in IPA94-100 against the judder at 60 fps; back to 60 in
// IPA101: Stefan found it did not fix the judder (docs/TECHNICAL.md, Oct 27).
// 120 again from IPA167: at 60 the world moved on 2 of 3 frames for the
// first ~15 s of a pursuit (camera logs, Oct 29). The launcher passes 120.
REXCVAR_DEFINE_INT32(nfsmw_sim_rate, 120, "Game",
                     "Gameplay simulation rate in Hz: 60 (the game's) or 120 (smoother at 60 fps, "
                     "needed for the 120 fps cap)");
REXCVAR_DEFINE_BOOL(nfsmw_skip_movies, false, "Game",
                    "Skip the game's movies (EA logo, intro, attract and story movies), as Extra Options' "
                    "SkipMovies");
REXCVAR_DEFINE_INT32(nfsmw_laps_max, 8, "Game",
                     "Most laps you can pick for a Quick Race (1-127; the game's is 8)");
REXCVAR_DEFINE_INT32(nfsmw_opponents_max, 3, "Game",
                     "Most opponents you can pick for a Quick Race (1-6; the game's is 3)");
REXCVAR_DEFINE_INT32(nfsmw_traffic_low, 10, "Game", "Traffic density at Low (0-100; the game's is 10)");
REXCVAR_DEFINE_INT32(nfsmw_traffic_medium, 30, "Game", "Traffic density at Medium (0-100; the game's is 30)");
REXCVAR_DEFINE_INT32(nfsmw_traffic_high, 50, "Game", "Traffic density at High (0-100; the game's is 50)");
REXCVAR_DEFINE_BOOL(nfsmw_always_rain, false, "Game", "Rain everywhere, all the time");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_amount, 1.0, "Game", "How much rain falls (the game's is 1)");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_intensity, 0.45, "Game", "Rain intensity (the game's is 0.45)");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_drop_size, 0.01, "Game", "Size of the falling drops (the game's is 0.01)");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_crossing, 0.02, "Game", "Sideways drift of the rain (the game's is 0.02)");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_fall_speed, 0.03, "Game", "How fast the rain falls (the game's is 0.03)");
REXCVAR_DEFINE_DOUBLE(nfsmw_rain_gravity, 0.35, "Game", "Gravity on the rain drops (the game's is 0.35)");
REXCVAR_DEFINE_DOUBLE(nfsmw_game_speed, 1.0, "Game",
                      "Game speed multiplier, as Extra Options' GameSpeed (0.25-4; the game's is 1)");
REXCVAR_DEFINE_INT32(nfsmw_laps_min, 1, "Game", "Fewest laps you can pick for a Quick Race (1-127; the game's is 1)");
REXCVAR_DEFINE_INT32(nfsmw_opponents_min, 1, "Game",
                     "Fewest opponents you can pick for a Quick Race (1-6; the game's is 1)");
REXCVAR_DEFINE_INT32(nfsmw_random_laps_max, 5, "Game",
                     "Most laps of a random Quick Race circuit (1-127; the game's is 5)");
REXCVAR_DEFINE_INT32(nfsmw_random_opponents_max, 3, "Game",
                     "Most opponents of a random Quick Race (1-6; the game's is 3)");
REXCVAR_DEFINE_DOUBLE(nfsmw_road_reflection, 1.0, "Game",
                      "How much the wet road reflects (the game's is 1)");
REXCVAR_DEFINE_DOUBLE(nfsmw_sb_recharge_time, 25.0, "Game",
                      "Seconds the Speedbreaker takes to refill (the game's is 25)");
REXCVAR_DEFINE_DOUBLE(nfsmw_sb_recharge_speed, 100.0, "Game",
                      "Speed above which the Speedbreaker refills (the game's is 100)");
REXCVAR_DEFINE_DOUBLE(nfsmw_sb_mass, 2.0, "Game",
                      "Your car's mass multiplier during Speedbreaker (the game's is 2)");
REXCVAR_DEFINE_DOUBLE(nfsmw_speeding_limit, 67.0, "Game",
                      "Speed in m/s for the Speeding infraction (the game's is 67)");
REXCVAR_DEFINE_DOUBLE(nfsmw_excessive_speeding_limit, 80.5, "Game",
                      "Speed in m/s for the Excessive Speeding infraction (the game's is 80.5)");
REXCVAR_DEFINE_DOUBLE(nfsmw_reckless_driving_limit, 89.4, "Game",
                      "Speed in m/s for the Reckless Driving infraction (the game's is 89.4)");
REXCVAR_DEFINE_INT32(nfsmw_impound_strikes, 3, "Game",
                     "Impound strikes a newly bought car has (1-127; the game's is 3)");
REXCVAR_DEFINE_INT32(nfsmw_impound_strikes_max, 5, "Game",
                     "Most impound strikes a car can reach with markers (1-127; the game's is 5)");
REXCVAR_DEFINE_BOOL(nfsmw_heat_override, false, "Game",
                    "Force the pursuit heat between nfsmw_heat_min and nfsmw_heat_max in every event");
REXCVAR_DEFINE_INT32(nfsmw_heat_min, 1, "Game", "Lowest heat level with the override (1-10)");
REXCVAR_DEFINE_INT32(nfsmw_heat_max, 5, "Game",
                     "Highest heat level with the override (1-10; above 5 is experimental)");
REXCVAR_DEFINE_BOOL(nfsmw_infinite_nos, false, "Game", "Nitrous never runs out (prototype debug menu)");
REXCVAR_DEFINE_BOOL(nfsmw_infinite_speedbreaker, false, "Game",
                    "Speedbreaker never runs out (prototype debug menu)");
REXCVAR_DEFINE_BOOL(nfsmw_no_cops, false, "Game", "No police anywhere (prototype debug menu)");
REXCVAR_DEFINE_BOOL(nfsmw_show_non_pursuit_cops, false, "Game",
                    "Show cops that are not chasing you on the minimap, as Extra Options' "
                    "ShowNonPursuitCops");
REXCVAR_DEFINE_INT32(nfsmw_shadow_map_size, 1600, "Game",
                     "Width and height of the car shadow map (512-1600; the Xbox 360's is 1600, "
                     "the most that fits in its 10 MB EDRAM)");

namespace {

int32_t Setting(int32_t value, int32_t lo, int32_t hi, const char* what,
                std::atomic<int32_t>& logged) {
  const int32_t n = std::clamp(value, lo, hi);
  if (logged.exchange(n) != n) {
    REXLOG_INFO("[extra-options] {}: {}", what, n);
  }
  return n;
}

// Writes `bytes` into guest memory that may be read-only (the XEX's .rdata),
// restoring the protection afterwards.
bool PatchGuestBytes(uint32_t address, const uint8_t* bytes, uint32_t count) {
  auto* kernel = rex::system::kernel_state();
  auto* memory = kernel ? kernel->memory() : nullptr;
  auto* heap = memory ? memory->LookupHeap(address) : nullptr;
  if (!heap) {
    return false;
  }
  const uint32_t page = heap->page_size();
  const uint32_t start = address & ~(page - 1);
  const uint32_t size = ((address + count - start) + page - 1) & ~(page - 1);
  uint32_t old_protect = 0;
  if (!heap->Protect(start, size,
                     rex::memory::kMemoryProtectRead | rex::memory::kMemoryProtectWrite,
                     &old_protect)) {
    return false;
  }
  auto* host = memory->TranslateVirtual<uint8_t*>(address);
  std::copy(bytes, bytes + count, host);
  heap->Protect(start, size, old_protect);
  return true;
}

uint32_t GuestWord(uint32_t address) {
  const auto* p = rex::system::kernel_state()->memory()->TranslateVirtual<const uint8_t*>(address);
  return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | uint32_t(p[3]);
}

bool PatchGuestWord(uint32_t address, uint32_t value) {
  const uint8_t be[4] = {uint8_t(value >> 24), uint8_t(value >> 16), uint8_t(value >> 8),
                         uint8_t(value)};
  return PatchGuestBytes(address, be, 4);
}

uint32_t FloatBits(float v) {
  uint32_t b;
  std::memcpy(&b, &v, 4);
  return b;
}

struct FloatTunable {
  uint32_t address;
  float game;
  double value;
  const char* name;
};

// Writes a group of floats. The first time only when all of them still hold
// the game's values (the right place in this build); from then on, again
// whenever the in-game options change them.
template <size_t N>
void PatchFloats(const char* group, int& state, const FloatTunable (&table)[N]) {
  if (state == 0) {
    state = 1;
    for (const FloatTunable& t : table) {
      if (GuestWord(t.address) != FloatBits(t.game)) {
        REXLOG_WARN("[extra-options] {}: the values are not where expected; not touched", group);
        state = -1;
        break;
      }
    }
  }
  if (state < 0) return;
  for (const FloatTunable& t : table) {
    const float v = float(t.value);
    if (GuestWord(t.address) == FloatBits(v)) continue;
    const bool ok = PatchGuestWord(t.address, FloatBits(v));
    REXLOG_INFO("[extra-options] {} {}: {:.3f}{}", group, t.name, v, ok ? "" : " (COULD NOT PATCH)");
  }
}

}  // namespace

extern "C" int32_t nfsmw_markers_to_pick() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_marker_count), 1, 6, "markers to pick after a rival", logged);
}

extern "C" int32_t nfsmw_purchased_car_limit() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_purchased_car_limit), 1, 25, "cars you can buy", logged);
}

// The shadow map's size, read where the game creates it (sub_82454C18,
// tools/ios/patch_game_extra_options.py). Smaller: less drawing, resolving and
// texture reloading every frame, blurrier shadow edges.
extern "C" int32_t nfsmw_shadow_map_size() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_shadow_map_size), 512, 1600, "shadow map size", logged) & ~7;
}

// The values in the game's data (rain, Speedbreaker, infraction speeds, most
// impound strikes): at boot and again from the in-game options
// (ingame_options.mm), which set the cvars first. Main thread; the game reads
// each value where it uses it, so a change shows from then on.
extern "C" void nfsmw_extra_options_tunables() {
  // The rain's tunables (see RAIN above): only when they still hold the
  // game's defaults (the right table in this build).
  static int rain_state = 0, sb_state = 0, infraction_state = 0, strikes_state = 0;
  PatchFloats("rain", rain_state, {
      {0x828F9D20, 1.0f, REXCVAR_GET(nfsmw_rain_amount), "amount"},
      {0x828F9DA0, 0.45f, REXCVAR_GET(nfsmw_rain_intensity), "intensity"},
      {0x828F9D9C, 0.01f, REXCVAR_GET(nfsmw_rain_drop_size), "drop size"},
      {0x828F9D30, 0.02f, REXCVAR_GET(nfsmw_rain_crossing), "crossing"},
      {0x828F9D34, 0.03f, REXCVAR_GET(nfsmw_rain_fall_speed), "fall speed"},
      {0x828F9D38, 0.35f, REXCVAR_GET(nfsmw_rain_gravity), "gravity"},
      {0x828F9E44, 1.0f, REXCVAR_GET(nfsmw_road_reflection), "road reflection"},
  });
  if (REXCVAR_GET(nfsmw_always_rain)) {
    REXLOG_INFO("[extra-options] always rain: on");
  }
  // SPEEDBREAKER and INFRACTION SPEEDS above.
  PatchFloats("speedbreaker", sb_state, {
      {0x828FB8D4, 25.0f, REXCVAR_GET(nfsmw_sb_recharge_time), "recharge time"},
      {0x828FB8D8, 100.0f, REXCVAR_GET(nfsmw_sb_recharge_speed), "recharge speed"},
      {0x828FB8DC, 2.0f, REXCVAR_GET(nfsmw_sb_mass), "mass"},
  });
  PatchFloats("infraction", infraction_state, {
      {0x82061CC4, 80.5f, REXCVAR_GET(nfsmw_excessive_speeding_limit), "excessive speeding"},
      {0x82061CC8, 67.0f, REXCVAR_GET(nfsmw_speeding_limit), "speeding"},
      {0x82061CCC, 89.4f, REXCVAR_GET(nfsmw_reckless_driving_limit), "reckless driving"},
  });
  // IMPOUND STRIKES above: the maximum, after the float 0.25.
  {
    constexpr uint32_t kQuarter = 0x828FF1F8, kMaxStrikes = 0x828FF1FC;
    const int32_t max = std::clamp(REXCVAR_GET(nfsmw_impound_strikes_max), 1, 127);
    if (strikes_state == 0) {
      strikes_state = GuestWord(kQuarter) == FloatBits(0.25f) && GuestWord(kMaxStrikes) == 5 ? 1 : -1;
      if (strikes_state < 0) REXLOG_WARN("[extra-options] most impound strikes: not where expected; not touched");
    }
    if (strikes_state > 0 && GuestWord(kMaxStrikes) != uint32_t(max)) {
      const bool ok = PatchGuestWord(kMaxStrikes, uint32_t(max));
      REXLOG_INFO("[extra-options] most impound strikes: {}{}", max, ok ? "" : " (COULD NOT PATCH)");
    }
  }
}

// The data patches, once the XEX is loaded and before the game reads them
// (IosNfsmwApp::OnPostSetup). Weakly referenced there: this file is only in
// the USA build.
extern "C" void nfsmw_extra_options_apply() {
  // Simulation rate (the PC Widescreen Fix's SimRate). NFSMW steps its
  // gameplay by a fixed 1/60 s whatever the frame rate: at 120 fps the world
  // still moved 60 times a second. On PC SimRate rewrites five code sites;
  // on the 360 those read one shared read-only 1/60 (0x820AFDD0, 21
  // functions), and World_Service's timestep variable starts at 1/60
  // (0x828F85AC, .data). Both become 1/rate. Experimental: the shared
  // constant may also be used for things that should stay at 1/60.
  if (const int32_t rate = REXCVAR_GET(nfsmw_sim_rate); rate == 120) {
    constexpr uint32_t kSharedStep = 0x820AFDD0;
    constexpr uint32_t kWorldStep = 0x828F85AC;
    auto* memory = rex::system::kernel_state()->memory();
    const auto* shared = memory->TranslateVirtual<const uint8_t*>(kSharedStep);
    const uint8_t sixtieth[4] = {0x3C, 0x88, 0x88, 0x89};  // 1/60, big-endian
    if (!std::equal(sixtieth, sixtieth + 4, shared)) {
      REXLOG_WARN("[extra-options] sim rate: 0x{:08X} is not 1/60; not touched", kSharedStep);
    } else {
      const float step = 1.0f / float(rate);
      uint32_t bits;
      std::memcpy(&bits, &step, 4);
      const uint8_t be[4] = {uint8_t(bits >> 24), uint8_t(bits >> 16), uint8_t(bits >> 8),
                             uint8_t(bits)};
      const bool ok = PatchGuestBytes(kSharedStep, be, 4) && PatchGuestBytes(kWorldStep, be, 4);
      REXLOG_INFO("[extra-options] sim rate: {} Hz {}", rate, ok ? "set" : "COULD NOT PATCH");
    }
  }
  if (REXCVAR_GET(nfsmw_remove_old_bridge_barrier)) {
    constexpr uint32_t kSceneryGroupDoor = 0x82087AC4;  // "SCENERY_GROUP_DOOR"
    auto* memory = rex::system::kernel_state()->memory();
    const auto* name = memory->TranslateVirtual<const char*>(kSceneryGroupDoor);
    if (std::string_view(name, 18) != "SCENERY_GROUP_DOOR") {
      REXLOG_WARN("[extra-options] old bridge barrier: 0x{:08X} is not SCENERY_GROUP_DOOR; "
                  "not touched", kSceneryGroupDoor);
    } else {
      const uint8_t first = 'T', eighth = ' ';
      const bool ok = PatchGuestBytes(kSceneryGroupDoor, &first, 1) &&
                      PatchGuestBytes(kSceneryGroupDoor + 7, &eighth, 1);
      REXLOG_INFO("[extra-options] old bridge barrier: {}", ok ? "removed" : "COULD NOT PATCH");
    }
  }
  nfsmw_extra_options_tunables();
}

// Before the pursuit's heat clamp (see HEAT LEVEL OVERRIDE above).
extern "C" void nfsmw_heat_override(uint32_t object, uint8_t* base) {
  if (!REXCVAR_GET(nfsmw_heat_override)) {
    return;
  }
  static std::atomic<int32_t> logged_min{INT32_MIN}, logged_max{INT32_MIN};
  const int32_t lo = Setting(REXCVAR_GET(nfsmw_heat_min), 1, 10, "heat override minimum", logged_min);
  const int32_t hi = std::max(lo, Setting(REXCVAR_GET(nfsmw_heat_max), 1, 10, "heat override maximum", logged_max));
  REX_STORE_U32(object + 220, FloatBits(float(lo)));
  REX_STORE_U32(object + 224, FloatBits(float(hi)));
}

// Heat +1 / -1 from the in-game options (see HEAT LEVEL OVERRIDE above):
// asked for on the main thread, added once the next time a pursuit's heat
// is updated.
namespace {
std::atomic<int32_t> heat_steps{0};
}  // namespace

extern "C" void nfsmw_heat_step_request(int32_t steps) {
  heat_steps.fetch_add(steps);
  REXLOG_INFO("[extra-options] heat {:+d} asked for", steps);
}

extern "C" double nfsmw_heat_step(double heat) {
  const int32_t steps = heat_steps.exchange(0);
  if (steps == 0) return heat;
  REXLOG_INFO("[extra-options] heat {:.2f} {:+d} (then the event's limits)", heat, steps);
  return heat + steps;
}

// A new car's record (see IMPOUND STRIKES above). A leaf: r3 is still the
// record afterwards.
extern "C" void __imp__sub_822CE7D8(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_822CE7D8) {
  __imp__sub_822CE7D8(ctx, base);
  static std::atomic<int32_t> logged{INT32_MIN};
  const int32_t strikes = Setting(REXCVAR_GET(nfsmw_impound_strikes), 1, 127, "impound strikes of a new car", logged);
  if (strikes != 3) {
    REX_STORE_U8(ctx.r3.u32 + 2, uint8_t(strikes));
  }
}

extern "C" int32_t nfsmw_laps_max();
extern "C" int32_t nfsmw_opponents_max();

extern "C" int32_t nfsmw_laps_min() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_laps_min), 1, std::max(1, nfsmw_laps_max()), "fewest Quick Race laps", logged);
}

extern "C" int32_t nfsmw_laps_max() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_laps_max), 1, 127, "most Quick Race laps", logged);
}

extern "C" int32_t nfsmw_opponents_min() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_opponents_min), 1, std::max(1, nfsmw_opponents_max()),
                 "fewest Quick Race opponents", logged);
}

extern "C" int32_t nfsmw_opponents_max() {
  static std::atomic<int32_t> logged{INT32_MIN};
  return Setting(REXCVAR_GET(nfsmw_opponents_max), 1, 6, "most Quick Race opponents", logged);
}

extern "C" int32_t nfsmw_traffic_density(int32_t level) {
  static std::atomic<int32_t> logged[3] = {INT32_MIN, INT32_MIN, INT32_MIN};
  switch (level) {
    case 1: return Setting(REXCVAR_GET(nfsmw_traffic_low), 0, 100, "traffic at Low", logged[0]);
    case 2: return Setting(REXCVAR_GET(nfsmw_traffic_medium), 0, 100, "traffic at Medium", logged[1]);
    default: return Setting(REXCVAR_GET(nfsmw_traffic_high), 0, 100, "traffic at High", logged[2]);
  }
}

// The rain intensity at a point (see RAIN above).
extern "C" void __imp__sub_824FB818(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_824FB818) {
  __imp__sub_824FB818(ctx, base);
  if (REXCVAR_GET(nfsmw_always_rain)) {
    ctx.f1.f64 = 1.0;
  }
}

extern "C" int32_t nfsmw_skip_movies() {
  const bool skip = REXCVAR_GET(nfsmw_skip_movies);
  static std::atomic<bool> logged{false};
  if (!logged.exchange(true)) {
    REXLOG_INFO("[extra-options] skip movies: {}", skip ? "on" : "off");
  }
  return skip ? 1 : 0;
}

// GAME SPEED above: the game's value times the setting while it is used.
extern "C" void __imp__sub_82472F38(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_82472F38) {
  constexpr uint32_t kGameSpeed = 0x828FB90C;
  static std::atomic<int32_t> logged{100};
  const double factor = std::clamp(REXCVAR_GET(nfsmw_game_speed), 0.25, 4.0);
  if (logged.exchange(int32_t(factor * 100)) != int32_t(factor * 100)) {
    REXLOG_INFO("[extra-options] game speed: {:.2f}x", factor);
  }
  if (factor == 1.0) {
    __imp__sub_82472F38(ctx, base);
    return;
  }
  const uint32_t game = REX_LOAD_U32(kGameSpeed);
  float v;
  std::memcpy(&v, &game, 4);
  REX_STORE_U32(kGameSpeed, FloatBits(float(v * factor)));
  __imp__sub_82472F38(ctx, base);
  REX_STORE_U32(kGameSpeed, game);
}

// RANDOM QUICK RACE above. A leaf; r4 (the options) and r5 (the race type)
// are read before it runs.
extern "C" void __imp__sub_822C4E68(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_822C4E68) {
  const uint32_t options = ctx.r4.u32;
  const int32_t type = ctx.r5.s32;
  __imp__sub_822C4E68(ctx, base);
  static std::atomic<int32_t> logged_o{INT32_MIN}, logged_l{INT32_MIN};
  static std::atomic<uint32_t> seed{0x1D872B41};
  auto draw = [](int32_t n) {
    uint32_t v = seed.load();
    v ^= v << 13; v ^= v >> 17; v ^= v << 5;
    seed.store(v);
    return int32_t(v % uint32_t(n)) + 1;
  };
  const int32_t opponents = Setting(REXCVAR_GET(nfsmw_random_opponents_max), 1, 6, "random race opponents", logged_o);
  const int32_t laps = Setting(REXCVAR_GET(nfsmw_random_laps_max), 1, 127, "random race laps", logged_l);
  if (opponents != 3) {
    const uint8_t n = uint8_t(draw(opponents));
    REX_STORE_U8(options + 7, n);
    if (type == 3) REX_STORE_U8(options + 4, n);
  }
  if (laps != 5 && type == 1) {
    REX_STORE_U8(options + 4, uint8_t(draw(laps)));
  }
}

// DEBUG FLAGS FROM THE XBOX 360 PROTOTYPE above: each reader sets its flag
// first. The three bytes have no other writer, so they follow the setting
// both ways (it can change in the in-game options). The cops word is the
// game's own: set while the setting is on, cleared once when it is turned off.
#define NFSMW_BYTE_FLAG_READER(func, cvar, address)                          \
  extern "C" void __imp__##func(PPCContext& __restrict ctx, uint8_t* base); \
  extern "C" REX_FUNC(func) {                                                \
    REX_STORE_U8(address, REXCVAR_GET(cvar) ? 1 : 0);                        \
    __imp__##func(ctx, base);                                                \
  }
NFSMW_BYTE_FLAG_READER(sub_82424988, nfsmw_infinite_nos, 0x82A2CE71)
NFSMW_BYTE_FLAG_READER(sub_8246C188, nfsmw_infinite_speedbreaker, 0x82A2D1C6)
NFSMW_BYTE_FLAG_READER(sub_8229B840, nfsmw_show_non_pursuit_cops, 0x82A2C5FA)
#undef NFSMW_BYTE_FLAG_READER

namespace {
std::atomic<bool> cops_forced_off{false};
void NoCops(uint8_t* base) {
  if (REXCVAR_GET(nfsmw_no_cops)) {
    REX_STORE_U32(0x82A2BD94, 1);
    cops_forced_off.store(true);
  } else if (cops_forced_off.exchange(false)) {
    REX_STORE_U32(0x82A2BD94, 0);
  }
}
}  // namespace

#define NFSMW_FLAG_READER(func)                                              \
  extern "C" void __imp__##func(PPCContext& __restrict ctx, uint8_t* base); \
  extern "C" REX_FUNC(func) {                                                \
    NoCops(base);                                                            \
    __imp__##func(ctx, base);                                                \
  }
NFSMW_FLAG_READER(sub_8249D808)
NFSMW_FLAG_READER(sub_820EB6A8)
NFSMW_FLAG_READER(sub_824A2DD8)
NFSMW_FLAG_READER(sub_824A22B0)
#undef NFSMW_FLAG_READER
