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

#include <algorithm>
#include <atomic>
#include <cstring>
#include <cstdint>
#include <string_view>

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

REXCVAR_DEFINE_INT32(nfsmw_marker_count, 2, "Game",
                     "Markers you pick after beating a Blacklist rival (1-6; the game's is 2)");
REXCVAR_DEFINE_INT32(nfsmw_purchased_car_limit, 10, "Game",
                     "Cars you can buy at the car lot (1-25; the game's is 10)");
REXCVAR_DEFINE_BOOL(nfsmw_remove_old_bridge_barrier, false, "Game",
                    "Remove the barrier that closes the road to the Old Bridge");
REXCVAR_DEFINE_INT32(nfsmw_sim_rate, 60, "Game",
                     "Gameplay simulation rate in Hz: 60 (the game's) or 120 (experimental, "
                     "for the 120 fps cap)");
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
      return;
    }
    const uint8_t first = 'T', eighth = ' ';
    const bool ok = PatchGuestBytes(kSceneryGroupDoor, &first, 1) &&
                    PatchGuestBytes(kSceneryGroupDoor + 7, &eighth, 1);
    REXLOG_INFO("[extra-options] old bridge barrier: {}", ok ? "removed" : "COULD NOT PATCH");
  }
}
