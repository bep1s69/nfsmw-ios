#!/usr/bin/env python3
"""
Test switch: a small Vulkan shared-memory buffer, for measuring memory while
the native renderer draws everything.

    python3 tools/ios/patch_ios_small_shared_memory.py            apply
    python3 tools/ios/patch_ios_small_shared_memory.py --status
    python3 tools/ios/patch_ios_small_shared_memory.py --revert

Touches src/graphics/vulkan/shared_memory.cpp and command_processor.cpp.


WHY
===

With the native renderer drawing from the first frame (nothing for the
emulated renderer), the graphics footprint still jumps by ~630 MiB within a
second of the native renderer starting. Suspect: Vulkan's 512 MB
shared-memory buffer (MoltenVK, non-sparse) made resident by the little
work Vulkan still submits (swaps, occlusion queries). With
--ios_shared_memory_mb=N (N > 0) the buffer is only N MB, and the shared
memory descriptors point inside it. ONLY with the native renderer drawing
everything: an emulated draw would read past it.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

SM = "src/graphics/vulkan/shared_memory.cpp"
CP = "src/graphics/vulkan/command_processor.cpp"

SIZE_ANCHOR = '''    buffer_create_info.flags &= ~sparse_flags;
    if (dfn.vkCreateBuffer(device, &buffer_create_info, nullptr, &buffer_) != VK_SUCCESS) {
'''
SIZE_NEW = '''    buffer_create_info.flags &= ~sparse_flags;
    // LOCAL PATCH - iOS (tools/ios/patch_ios_small_shared_memory.py).
    if (REXCVAR_GET(ios_shared_memory_mb) > 0) {
      buffer_create_info.size = VkDeviceSize(REXCVAR_GET(ios_shared_memory_mb)) << 20;
      REXGPU_INFO("Shared memory: test buffer of {} MB only (ios_shared_memory_mb)",
                  REXCVAR_GET(ios_shared_memory_mb));
    }
    if (dfn.vkCreateBuffer(device, &buffer_create_info, nullptr, &buffer_) != VK_SUCCESS) {
'''

CVAR_ANCHOR = '''#include <rex/graphics/vulkan/shared_memory.h>
'''
CVAR_NEW = '''#include <rex/graphics/vulkan/shared_memory.h>
// LOCAL PATCH - iOS (tools/ios/patch_ios_small_shared_memory.py).
REXCVAR_DEFINE_INT32(ios_shared_memory_mb, 0, "GPU",
                     "iOS test: Vulkan shared-memory buffer of this many MB (0: the full 512)");
'''

DESC_ANCHOR = '''    shared_memory_descriptor_buffer_info.offset = shared_memory_binding_range * i;
    shared_memory_descriptor_buffer_info.range = shared_memory_binding_range;
'''
DESC_NEW = '''    shared_memory_descriptor_buffer_info.offset = shared_memory_binding_range * i;
    shared_memory_descriptor_buffer_info.range = shared_memory_binding_range;
    // LOCAL PATCH - iOS (tools/ios/patch_ios_small_shared_memory.py): inside
    // a small test buffer.
    if (REXCVAR_GET(ios_shared_memory_mb) > 0) {
      shared_memory_descriptor_buffer_info.offset = 0;
      shared_memory_descriptor_buffer_info.range =
          std::min<VkDeviceSize>(shared_memory_binding_range, VkDeviceSize(REXCVAR_GET(ios_shared_memory_mb)) << 20);
    }
'''
DECL_ANCHOR = '''#include <rex/graphics/vulkan/command_processor.h>
'''
DECL_NEW = '''#include <rex/graphics/vulkan/command_processor.h>
REXCVAR_DECLARE(int32_t, ios_shared_memory_mb);  // LOCAL PATCH - iOS (patch_ios_small_shared_memory.py)
'''

BLOCKS = [
    (SM, "the ios_shared_memory_mb cvar", CVAR_ANCHOR, CVAR_NEW),
    (SM, "a small buffer on request", SIZE_ANCHOR, SIZE_NEW),
    (CP, "the cvar declared", DECL_ANCHOR, DECL_NEW),
    (CP, "descriptors inside the small buffer", DESC_ANCHOR, DESC_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_small_shared_memory", BLOCKS))
