#!/usr/bin/env python3
"""
Only small resolves are read back to guest memory (exposure and the like);
large ones (full-screen effects) are not copied back every frame.

    python3 tools/ios/patch_ios_readback_limit.py            apply
    python3 tools/ios/patch_ios_readback_limit.py --status
    python3 tools/ios/patch_ios_readback_limit.py --revert

Touches src/graphics/vulkan/command_processor.cpp.


WHAT A CPU PROFILE SHOWED
=========================

Instruments' Time Profiler in a police chase on an iPad Pro M4:
VulkanCommandProcessor::IssueCopy_ReadbackResolvePath was 15 % of the GPU
thread, nearly all of it one memcpy. With readback_resolve=fast (the app's
"Accurate exposure", on), EVERY resolve (the GPU copying a render target out
of EDRAM) is also copied back into guest memory, a frame late, so the CPU can
read it. In a chase that includes full-screen effects: megabytes a frame.

The CPU needs a few of those: the exposure (the game reads the scene's
brightness from a tiny downsampled target to set the next frames' exposure;
without it the image looks washed out). Full-screen images it does not read.


THE CHANGE
==========

A resolve larger than ios_readback_max_kb (default 256 KB; a 1280x720 image is
~3.6 MB, a luminance target a few KB) is not read back: the function returns
right after the resolve, so neither the GPU copy to the readback buffer nor
the memcpy happen. The resolve itself (into the GPU's copy of guest memory,
which textures read) is untouched. 0 = read everything back, as before.

Every 5 s the log says how many resolves were read back and how many skipped,
and the largest of each, so the threshold can be checked.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/vulkan/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
'''
CVAR_NEW = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_readback_limit.py).
REXCVAR_DEFINE_INT32(ios_readback_max_kb, 256, "GPU",
                     "iOS: resolves larger than this (KB) are not read back to guest memory; "
                     "0 = read back everything");
#endif
'''

LIMIT_ANCHOR = '''  ReadbackResolveMode readback_mode = GetReadbackResolveMode(REXCVAR_GET(vulkan_readback_resolve));
  if (readback_mode == ReadbackResolveMode::kDisabled) {
    return true;
  }
'''
LIMIT_NEW = '''  ReadbackResolveMode readback_mode = GetReadbackResolveMode(REXCVAR_GET(vulkan_readback_resolve));
  if (readback_mode == ReadbackResolveMode::kDisabled) {
    return true;
  }
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: only small resolves go back to guest memory
  // (tools/ios/patch_ios_readback_limit.py).
  {
    static uint64_t kept = 0, skipped = 0;
    static uint32_t kept_max = 0, skipped_max = 0;
    static auto since = std::chrono::steady_clock::now();
    const uint32_t limit = uint32_t(std::max(0, REXCVAR_GET(ios_readback_max_kb))) * 1024u;
    const bool skip = limit && written_length > limit;
    if (skip) {
      ++skipped;
      skipped_max = std::max(skipped_max, written_length);
    } else {
      ++kept;
      kept_max = std::max(kept_max, written_length);
    }
    const auto now = std::chrono::steady_clock::now();
    if (now - since >= std::chrono::seconds(5)) {
      REXGPU_INFO("[ios-readback] 5 s: {} resolves read back (largest {} KB), {} skipped "
                  "(largest {} KB, limit {} KB)",
                  kept, kept_max >> 10, skipped, skipped_max >> 10, limit >> 10);
      kept = skipped = 0;
      kept_max = skipped_max = 0;
      since = now;
    }
    if (skip) {
      return true;
    }
  }
#endif
'''

BLOCKS = [
    (F, "the ios_readback_max_kb cvar", CVAR_ANCHOR, CVAR_NEW),
    (F, "skip reading back large resolves", LIMIT_ANCHOR, LIMIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_readback_limit", BLOCKS))
