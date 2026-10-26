// NFSMW Recompiled - game functions replaced on iOS
//
// The iOS copy of android/app/src/main/cpp/ganchos.cpp: the same hooks, at the
// same (PAL Spain) addresses, translated to the edition being built by
// tools/ediciones/ediciones.py exactly like the Android ones (ios/CMakeLists.txt).
// Only two things differ:
//
//   - the wait is os_sync_wait_on_address_with_timeout (iOS 17.4+) instead of
//     the Linux futex. The CP wakes it with os_sync_wake_by_address_all, which
//     tools/ios/patch_ios_waits.py adds next to the futex wake on Linux.
//   - the switch to turn the wait off is the NFSMW_RING_WAIT=0 environment
//     variable instead of the Android debug.nfsmw.espera_anillo property.
//
// The generated functions are weak symbols that jump to __imp__sub_X (see
// DEFINE_REX_FUNC in nfsmw_pch.h; on Darwin, a weak symbol with a tail call).
// Defining sub_X here with strong linkage replaces it, and __imp__sub_X is still
// the original.
//
// WAITING FOR SPACE IN THE COMMAND RING (sub_825A5D18)
//
// When the GPU command ring is full, the game's D3D waits for the command
// processor (CP) to advance its read pointer. It does so by SPINNING:
// sub_82597690 and sub_82597380 re-read the pointer over and over, calling
// sub_825A5D18, the hang watchdog, on every lap (it returns 0 if the pointer has
// not moved for 2 s). On the Xbox 360 that was cheap. Here the CP is the
// bottleneck and publishes the pointer only twice per frame: on Android the
// game's render thread spent the whole frame at 100 % on a prime core, heating
// the phone into thermal throttling.
//
// The hook: if the pointer has not moved since the last lap, sleep on the
// CP's sequence counter (nfsmw_cp_rptr_seq, from tools/parche_espera_anillo.py)
// until it publishes a new one, capped at half a frame of the current fps cap
// (12.5 ms at 40, 8.3 at 60, 4.2 at 120; IPA52 used 8, before that 1), or at
// --ios_ring_wait_ms when that is set above 0. Without that counter (an SDK without the patch) nothing changes. The CP
// bumps the counter every time it publishes the read pointer, so the cap is only
// a safety net: in the October 24 iPhone pursuit trace the main thread made ~709
// of these waits a second and only ~103 ended with a wake, the rest timed out
// after 1 ms while the CP sat in its vblank wait. "[ring-wait]" counts them.
//
// Only for the two ring-space loops, recognised by their return address. The
// other watchdog users wait on fences the CP writes mid-stream, and waiting
// here would add latency to them.
//
// NO POST-PROCESSING (sub_822246F0 and sub_82224380)
//
// The "Disable Post Processing" Xenia patch for this game (game-patches,
// 454107D9, by illusion): the only two reads of the global byte 0x828F48B2
// -lbz at 0x82224710 and 0x8222442C- read 0 instead. Here, without touching the
// generated code: while those two functions run the byte is 0, and it is
// restored on return. Cvar nfsmw_sin_posprocesado, off by default.
//
// That byte only picks the visual treatment's "branching" technique over the
// plain one ("visualtreatment_branching" / "visualtreatment", 0x82075510 /
// 0x8207552C; sub_822241A0 decides whether the branch is needed, e.g. for
// motion blur), so with it the colour filter, bloom and vignette stayed
// (Stefan, Oct 26: the switch did nothing he could see). The frame's post
// chain is run by sub_82442310 (which also draws the HUD, sub_82440D80): the
// byte at +9 of its argument (the view's "post-processing on") gates the
// bloom chain (sub_82224C00) and the visual treatment (sub_822246F0, r4 =
// 1); without it the function takes its other path, which puts the scene on
// the screen as it is. game_scene_size.cpp (USA addresses, not translated
// by tools/ediciones) makes that byte read 0 while the function runs.

#include <dlfcn.h>
#include <os/os_sync_wait_on_address.h>

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <cstring>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_INT32(ios_ring_wait_ms, 0, "Juego",
                     "iOS: longest sleep of the ring-space wait before re-reading the CP's read "
                     "pointer, in ms; 0 = half a frame of the fps cap (1 before October 24)");
REXCVAR_DEFINE_BOOL(nfsmw_sin_posprocesado, false, "Juego",
                    "Remove post-processing: colour filter, bloom and blur. Less GPU work, but the "
                    "game loses its look");

extern "C" void __imp__sub_825A5D18(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_822246F0(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void __imp__sub_82224380(PPCContext& __restrict ctx, uint8_t* base);

namespace {

// Return addresses of the watchdog calls from the two ring-space wait loops.
constexpr uint32_t kRingWaitReturn1 = 0x82597730;  // sub_82597690
constexpr uint32_t kRingWaitReturn2 = 0x82597404;  // sub_82597380

// Offset, inside the D3D device, of the pointer to the in-memory copy of the
// CP read pointer (lwz rX,10384(r31) in both loops).
constexpr uint32_t kDeviceRptrPointer = 10384;

std::atomic<uint32_t>* RptrSequence() {
  static std::atomic<uint32_t>* const sequence = []() -> std::atomic<uint32_t>* {
    const char* off = std::getenv("NFSMW_RING_WAIT");
    if (off && std::strcmp(off, "0") == 0) {
      return nullptr;
    }
    // The plugin is in the same Frameworks/ folder; RTLD_NOLOAD finds it by
    // name only if the SDK has already loaded it, which it has by the time the
    // game draws.
    void* plugin = dlopen("@rpath/librexgpu-xenos.dylib", RTLD_NOW | RTLD_NOLOAD);
    return plugin ? static_cast<std::atomic<uint32_t>*>(dlsym(plugin, "nfsmw_cp_rptr_seq"))
                  : nullptr;
  }();
  return sequence;
}

}  // namespace

extern "C" REX_FUNC(sub_825A5D18) {
  const uint32_t ret = uint32_t(ctx.lr);
  if (ret == kRingWaitReturn1 || ret == kRingWaitReturn2) {
    if (std::atomic<uint32_t>* sequence = RptrSequence()) {
      // The sequence first, then the pointer: if the CP publishes in between,
      // the sequence has already changed and the wait returns at once.
      const uint32_t before = sequence->load(std::memory_order_acquire);
      // r3 points to the watchdog state: { device, tick, pointer seen }.
      const uint32_t state = ctx.r3.u32;
      const uint32_t device = REX_LOAD_U32(state + 0);
      const uint32_t seen = REX_LOAD_U32(state + 8);
      const uint32_t rptr = REX_LOAD_U32(REX_LOAD_U32(device + kDeviceRptrPointer));
      if (rptr == seen) {
        // The cap can change while playing (Battery mode's 30 fps), so per wait.
        const int32_t fixed_ms = REXCVAR_GET(ios_ring_wait_ms);
        const int32_t set_cap = rex::cvar::Query<int32_t>("ios_fps_cap");
        const int32_t cap = set_cap > 0 ? set_cap : 120;  // 0: uncapped
        const uint64_t timeout_ns = fixed_ms > 0
                                        ? uint64_t(std::min<int32_t>(fixed_ms, 50)) * 1000000
                                        : uint64_t(std::clamp(500.0 / cap, 1.0, 50.0) * 1e6);
        const int woke = os_sync_wait_on_address_with_timeout(sequence, before, sizeof(uint32_t),
                                                              OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                                              OS_CLOCK_MACH_ABSOLUTE_TIME, timeout_ns);
        // Counted on the game's thread that waits; logged every 10 s.
        static uint64_t waits = 0, timeouts = 0;
        static auto since = std::chrono::steady_clock::now();
        ++waits;
        timeouts += woke < 0 && errno == ETIMEDOUT;
        if (std::chrono::steady_clock::now() - since >= std::chrono::seconds(10)) {
          REXLOG_INFO("[ring-wait] 10 s: {} waits for ring space, {} timed out ({:.1f} ms cap{})",
                      waits, timeouts, timeout_ns / 1e6, fixed_ms > 0 ? "" : ", half a frame");
          waits = timeouts = 0;
          since = std::chrono::steady_clock::now();
        }
      }
    }
  }
  __imp__sub_825A5D18(ctx, base);
}

namespace {

// The global byte that turns post-processing on (lis r11,-32113 + 18610).
constexpr uint32_t kPostProcessingOn = 0x828F48B2;

template <void (*kOriginal)(PPCContext&, uint8_t*)>
void WithoutPostProcessing(PPCContext& __restrict ctx, uint8_t* base) {
  if (!REXCVAR_GET(nfsmw_sin_posprocesado)) {
    kOriginal(ctx, base);
    return;
  }
  const uint8_t before = REX_LOAD_U8(kPostProcessingOn);
  static std::atomic<int> said{0};
  if (said.fetch_add(1) < 2) {  // whether this runs at all, and what the byte was
    REXLOG_INFO("[post] no post-processing: hook runs, byte 0x828F48B2 was {}", before);
  }
  REX_STORE_U8(kPostProcessingOn, 0);
  kOriginal(ctx, base);
  REX_STORE_U8(kPostProcessingOn, before);
}

}  // namespace

extern "C" REX_FUNC(sub_822246F0) {
  WithoutPostProcessing<__imp__sub_822246F0>(ctx, base);
}

extern "C" REX_FUNC(sub_82224380) {
  WithoutPostProcessing<__imp__sub_82224380>(ctx, base);
}
