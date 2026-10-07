#!/usr/bin/env python3
"""
A CPU write invalidates the 256 KB around it only up to the nearest pages a
texture (or anything else) watches: textures next to the game's per-frame
data are no longer reloaded every frame.

    python3 tools/ios/patch_ios_narrow_invalidation.py            apply
    python3 tools/ios/patch_ios_narrow_invalidation.py --status
    python3 tools/ios/patch_ios_narrow_invalidation.py --revert

Touches src/graphics/shared_memory.cpp. Cvar ios_narrow_invalidation (on).


WHY
===

patch_ios_texture_stats.py, in a race at the 120 fps cap: 13,000-18,000
texture loads every 5 s, all reloads (~4 GB/s converted and copied again).
Part of it is the game's render-to-texture chain (resolve, then sampled), but
4,000-18,000 every 5 s were "outdated by the CPU": compressed DXT textures
reloaded about once a frame each, and the frame rate fell from ~115 to ~68
exactly when those went from 4,000 to 18,000. The game does not rewrite its
DXT textures every frame.

SharedMemory::MemoryInvalidationCallback, on a CPU write to protected memory,
widens the invalidation to the surrounding 64-page block (256 KB) unless
GPU-written data is in the way: cheaper than an access violation for every
4 KB the CPU writes. Every watch in that block fires. NFSMW writes its
per-frame data (vertices, constants) next to textures, so each such write
outdated the textures sharing its 256 KB block, every frame.

The widening now also stops at watched ranges that the write itself does not
touch: the block is cut just after the last watch entirely before the written
pages and just before the first watch entirely after them. Those pages stay
valid and protected: a later CPU write to a texture's own pages still faults
and outdates it, as it should. Plain memory around the write is still
invalidated in one go, as before.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/shared_memory.cpp"

CVAR_ANCHOR = '''std::pair<uint32_t, uint32_t> SharedMemory::MemoryInvalidationCallback(
    uint32_t physical_address_start, uint32_t length, bool exact_range) {
'''
CVAR_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_narrow_invalidation.py).
REXCVAR_DEFINE_BOOL(ios_narrow_invalidation, true, "GPU",
                    "iOS: a CPU write's widened invalidation stops at watched ranges it does "
                    "not touch (textures next to per-frame data are not reloaded every frame)");
#endif

std::pair<uint32_t, uint32_t> SharedMemory::MemoryInvalidationCallback(
    uint32_t physical_address_start, uint32_t length, bool exact_range) {
'''

NARROW_ANCHOR = '''  for (uint32_t i = block_first; i <= block_last; ++i) {
    uint64_t invalidate_bits = UINT64_MAX;
    if (i == block_first) {
      invalidate_bits &= ~((uint64_t(1) << (page_first & 63)) - 1);
    }
'''
NARROW_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the widening stops at watched ranges the write does not
  // touch (tools/ios/patch_ios_narrow_invalidation.py).
  if (!exact_range && REXCVAR_GET(ios_narrow_invalidation)) {
    const uint32_t written_first = physical_address_start >> page_size_log2_;
    const uint32_t written_last = physical_address_last >> page_size_log2_;
    const uint32_t bucket_first = (page_first << page_size_log2_) >> kWatchBucketSizeLog2;
    const uint32_t bucket_last = (page_last << page_size_log2_) >> kWatchBucketSizeLog2;
    for (uint32_t b = bucket_first; b <= bucket_last; ++b) {
      for (const WatchNode* node = watch_buckets_[b]; node; node = node->bucket_node_next) {
        const WatchRange* range = node->range;
        if (range->page_last < written_first && range->page_last >= page_first) {
          page_first = range->page_last + 1;
        } else if (range->page_first > written_last && range->page_first <= page_last) {
          page_last = range->page_first - 1;
        }
      }
    }
  }
#endif
  for (uint32_t i = block_first; i <= block_last; ++i) {
    uint64_t invalidate_bits = UINT64_MAX;
    if (i == block_first) {
      invalidate_bits &= ~((uint64_t(1) << (page_first & 63)) - 1);
    }
'''

BLOCKS = [
    (F, "the cvar", CVAR_ANCHOR, CVAR_NEW),
    (F, "stop the widening at watched ranges", NARROW_ANCHOR, NARROW_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_narrow_invalidation", BLOCKS))
