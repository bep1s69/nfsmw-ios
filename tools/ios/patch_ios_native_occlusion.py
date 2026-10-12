#!/usr/bin/env python3
"""
While the native Metal renderer draws the game, it also answers the game's
occlusion queries (the sun glare).

    python3 tools/ios/patch_ios_native_occlusion.py            apply
    python3 tools/ios/patch_ios_native_occlusion.py --status
    python3 tools/ios/patch_ios_native_occlusion.py --revert

Touches src/graphics/vulkan/command_processor.cpp (the GPU plugin) and
src/ui/vulkan/vulkan_presenter.cpp (the runtime, where the hook lives, as
the other native-renderer hooks do). Builds on patch_ios_native_only.py and
patch_ios_occlusion_async.py.


WHY
===

NFSMW decides how bright the sun glare is from an occlusion query: how many
of the sun's pixels pass the depth test. With the native renderer showing
the game, the emulated renderer skips its draws (patch_ios_native_only.py),
so the Vulkan query around the sun's draw counted nothing the game drew and
the glare shone through buildings and trees.


HOW
===

A hook, rex_native_occlusion_hook, set by the native renderer. While
rex_native_draws_only is set, each ZPD event (query begin or end) goes to it
instead of to the Vulkan query: on a begin it marks the draws that follow,
which it counts with a Metal visibility result; on an end it gives back the
last count it has for that query (the result arrives when the GPU finishes
the frame, so the game sees it a frame or two late, as with
ios_async_occlusion), which is written to guest memory here.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CP = "src/graphics/vulkan/command_processor.cpp"
PRES = "src/ui/vulkan/vulkan_presenter.cpp"

DEF_ANCHOR = '''std::atomic<void (*)()> rex_native_swap_hook{nullptr};
'''
DEF_NEW = '''std::atomic<void (*)()> rex_native_swap_hook{nullptr};
// LOCAL PATCH - iOS: the native renderer's occlusion queries
// (tools/ios/patch_ios_native_occlusion.py).
std::atomic<bool (*)(uint32_t, bool, uint64_t*)> rex_native_occlusion_hook{nullptr};
'''

FLAG_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_async_occlusion, true, "GPU",
                    "iOS: answer occlusion queries with the previous result instead of making "
                    "the CPU wait for the GPU (one forced wait per frame in NFSMW)");
#endif
'''
FLAG_NEW = '''REXCVAR_DEFINE_BOOL(ios_async_occlusion, true, "GPU",
                    "iOS: answer occlusion queries with the previous result instead of making "
                    "the CPU wait for the GPU (one forced wait per frame in NFSMW)");
#endif
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: while the native Metal renderer draws the game, it counts
// the occlusion queries' samples (tools/ios/patch_ios_native_occlusion.py).
// The hook: (sample count address, query end, count out) -> handled; on an
// end, the count to give the game. Defined in the runtime.
#include <atomic>
extern std::atomic<bool> rex_native_draws_only;
extern std::atomic<bool (*)(uint32_t, bool, uint64_t*)> rex_native_occlusion_hook;
#endif
'''

ZPD_ANCHOR = '''  bool is_end = is_end_via_z_pass || is_end_via_z_fail;

  if (!is_end) {
    if (active_occlusion_query_.valid &&
'''
ZPD_NEW = '''  bool is_end = is_end_via_z_pass || is_end_via_z_fail;

#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the native renderer draws, so it counts
  // (tools/ios/patch_ios_native_occlusion.py).
  if (auto* native_query = rex_native_occlusion_hook.load(std::memory_order_relaxed);
      native_query && rex_native_draws_only.load(std::memory_order_relaxed)) {
    if (active_occlusion_query_.valid) {
      // Begun before the native renderer took over: ended cleanly (its count
      // is overwritten below), so the Vulkan queries stay usable.
      EndGuestOcclusionQuery(active_occlusion_query_.sample_count_address);
    }
    uint64_t samples = 0;
    if (native_query(sample_count_addr, is_end, &samples)) {
      if (is_end) {
        WriteGuestOcclusionResult(sample_count_addr, samples);
      }
      return true;
    }
  }
#endif

  if (!is_end) {
    if (active_occlusion_query_.valid &&
'''

BLOCKS = [
    (PRES, "the occlusion hook, in the runtime", DEF_ANCHOR, DEF_NEW),
    (CP, "the occlusion hook's declaration", FLAG_ANCHOR, FLAG_NEW),
    (CP, "ZPD events to the native renderer", ZPD_ANCHOR, ZPD_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_native_occlusion", BLOCKS))
