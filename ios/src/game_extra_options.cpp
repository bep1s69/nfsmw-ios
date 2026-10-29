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
// Always rain: the PC mod sets a flag the 360 build does not have where it
// was. Here the rain intensity at a point (sub_824FB818: the scripted
// override at 0x82A2D6A0 if set, SetChanceOfRain's, else the weather
// regions') is 1 while the setting is on.
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
REXCVAR_DEFINE_DOUBLE(nfsmw_road_reflection, 1.0, "Game",
                      "How much the wet road reflects (the game's is 1)");
REXCVAR_DEFINE_INT32(nfsmw_shadow_map_size, 1600, "Game",
                     "Width and height of the car shadow map (512-1600; the Xbox 360's is 1600, "
                     "the most that fits in its 10 MB EDRAM)");

namespace {

int32_t Setting(int32_t value, int32_t lo, int32_t hi, const char* what,
                std::atomic<bool>& logged) {
  const int32_t n = std::clamp(value, lo, hi);
  if (!logged.exchange(true)) {
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

}  // namespace

extern "C" int32_t nfsmw_markers_to_pick() {
  static std::atomic<bool> logged{false};
  return Setting(REXCVAR_GET(nfsmw_marker_count), 1, 6, "markers to pick after a rival", logged);
}

extern "C" int32_t nfsmw_purchased_car_limit() {
  static std::atomic<bool> logged{false};
  return Setting(REXCVAR_GET(nfsmw_purchased_car_limit), 1, 25, "cars you can buy", logged);
}

// The shadow map's size, read where the game creates it (sub_82454C18,
// tools/ios/patch_game_extra_options.py). Smaller: less drawing, resolving and
// texture reloading every frame, blurrier shadow edges.
extern "C" int32_t nfsmw_shadow_map_size() {
  static std::atomic<bool> logged{false};
  return Setting(REXCVAR_GET(nfsmw_shadow_map_size), 512, 1600, "shadow map size", logged) & ~7;
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
  // The rain's tunables (see RAIN above): only when they still hold the
  // game's defaults (the right table in this build).
  {
    struct Tunable {
      uint32_t address;
      float game;
      double value;
      const char* name;
    };
    const Tunable rain[] = {
        {0x828F9D20, 1.0f, REXCVAR_GET(nfsmw_rain_amount), "amount"},
        {0x828F9DA0, 0.45f, REXCVAR_GET(nfsmw_rain_intensity), "intensity"},
        {0x828F9D9C, 0.01f, REXCVAR_GET(nfsmw_rain_drop_size), "drop size"},
        {0x828F9E44, 1.0f, REXCVAR_GET(nfsmw_road_reflection), "road reflection"},
    };
    auto* memory = rex::system::kernel_state()->memory();
    auto bits_of = [](float v) {
      uint32_t b;
      std::memcpy(&b, &v, 4);
      return b;
    };
    auto guest_bits = [&](uint32_t address) {
      const auto* p = memory->TranslateVirtual<const uint8_t*>(address);
      return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | uint32_t(p[3]);
    };
    bool table_ok = true;
    for (const Tunable& t : rain) {
      table_ok &= guest_bits(t.address) == bits_of(t.game);
    }
    if (!table_ok) {
      REXLOG_WARN("[extra-options] rain: the tunables are not where expected; not touched");
    } else {
      for (const Tunable& t : rain) {
        const float v = float(t.value);
        if (v == t.game) continue;
        const uint32_t b = bits_of(v);
        const uint8_t be[4] = {uint8_t(b >> 24), uint8_t(b >> 16), uint8_t(b >> 8), uint8_t(b)};
        const bool ok = PatchGuestBytes(t.address, be, 4);
        REXLOG_INFO("[extra-options] rain {}: {:.3f}{}", t.name, v, ok ? "" : " (COULD NOT PATCH)");
      }
    }
    if (REXCVAR_GET(nfsmw_always_rain)) {
      REXLOG_INFO("[extra-options] always rain: on");
    }
  }
}

extern "C" int32_t nfsmw_laps_min() { return 1; }

extern "C" int32_t nfsmw_laps_max() {
  static std::atomic<bool> logged{false};
  return Setting(REXCVAR_GET(nfsmw_laps_max), 1, 127, "most Quick Race laps", logged);
}

extern "C" int32_t nfsmw_opponents_min() { return 1; }

extern "C" int32_t nfsmw_opponents_max() {
  static std::atomic<bool> logged{false};
  return Setting(REXCVAR_GET(nfsmw_opponents_max), 1, 6, "most Quick Race opponents", logged);
}

extern "C" int32_t nfsmw_traffic_density(int32_t level) {
  static std::atomic<bool> logged[3];
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
