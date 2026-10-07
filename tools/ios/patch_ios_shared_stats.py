#!/usr/bin/env python3
"""
How much the CPU's writes cost the GPU emulation, and a setting for how far a
CPU write's invalidation is widened.

    python3 tools/ios/patch_ios_shared_stats.py            apply
    python3 tools/ios/patch_ios_shared_stats.py --status
    python3 tools/ios/patch_ios_shared_stats.py --revert

Touches src/graphics/shared_memory.cpp. Cvars ios_shared_stats (off by default: turn on to measure) and
ios_invalidation_widen_kb (256, the SDK's). Apply after
patch_ios_narrow_invalidation.py.


WHY
===

A CPU profile of the GPU command thread in a race: 26 % copying guest memory
into the GPU's copy (VulkanSharedMemory::UploadRanges, a memcpy) and 11 %
protecting the pages again afterwards (mprotect): the game writes its
per-frame data, the write faults, the pages are uploaded and protected again.

The copies cannot go: the GPU runs 1-3 frames behind the command processor,
which tells the game a frame is done when it records it, so the game reuses
its buffers while the GPU still has to read them; it reads a copy taken at
record time. But how much is copied can change: a CPU write invalidates up to
256 KB around it (patch_ios_narrow_invalidation.py stops that only at watched
ranges), all of which is uploaded again when next used. Narrower means fewer
bytes copied but more faults on the game's threads; which is better has to be
measured.

  [ios-shared] 5 s: F CPU write faults, P pages invalidated, U MB uploaded
                    in R uploads (widening K KB)

ios_invalidation_widen_kb: 4, 16, 64 or 256; the widening stays within the
aligned block of that size around the written pages.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/shared_memory.cpp"

CVAR_ANCHOR = '''#include <rex/memory.h>

namespace rex::graphics {
'''
CVAR_NEW = '''#include <rex/memory.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_shared_stats.py).
#include <atomic>
#include <chrono>
#include <rex/cvar.h>
#include <rex/logging.h>
REXCVAR_DEFINE_BOOL(ios_shared_stats, false, "GPU",
                    "iOS: log CPU write faults, invalidated pages and uploads every 5 s");
REXCVAR_DEFINE_INT32(ios_invalidation_widen_kb, 256, "GPU",
                     "iOS: how far a CPU write's invalidation is widened (4, 16, 64 or 256 KB)");
namespace {
std::atomic<uint64_t> ios_shared_faults{0}, ios_shared_pages_invalidated{0};
uint64_t ios_shared_upload_pages = 0, ios_shared_uploads = 0;  // command processor only
std::chrono::steady_clock::time_point ios_shared_since = std::chrono::steady_clock::now();
}  // namespace
#endif

namespace rex::graphics {
'''

WIDEN_ANCHOR = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the widening stops at watched ranges the write does not
  // touch (tools/ios/patch_ios_narrow_invalidation.py).
'''
WIDEN_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the widening stays within an aligned block of
  // ios_invalidation_widen_kb, and the faults are counted
  // (tools/ios/patch_ios_shared_stats.py).
  if (!exact_range) {
    const int32_t kb = REXCVAR_GET(ios_invalidation_widen_kb);
    const uint32_t pages =
        std::clamp<uint32_t>(uint32_t(std::max(kb, 4)) << 10 >> page_size_log2_, 1, 64);
    const uint32_t written_first = physical_address_start >> page_size_log2_;
    const uint32_t written_last = physical_address_last >> page_size_log2_;
    page_first = std::max(page_first, written_first & ~(pages - 1));
    page_last = std::min(page_last, written_last | (pages - 1));
  }
  ios_shared_faults.fetch_add(1, std::memory_order_relaxed);
#endif
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the widening stops at watched ranges the write does not
  // touch (tools/ios/patch_ios_narrow_invalidation.py).
'''

COUNT_ANCHOR = '''  FireWatches(page_first, page_last, false);

  return std::make_pair(page_first << page_size_log2_, (page_last - page_first + 1)
                                                           << page_size_log2_);
'''
COUNT_NEW = '''  FireWatches(page_first, page_last, false);
#if REX_PLATFORM_IOS
  ios_shared_pages_invalidated.fetch_add(page_last - page_first + 1,
                                         std::memory_order_relaxed);  // LOCAL PATCH - iOS
#endif

  return std::make_pair(page_first << page_size_log2_, (page_last - page_first + 1)
                                                           << page_size_log2_);
'''

UPLOAD_ANCHOR = '''  const bool nfsmw_subido = upload_ranges_.empty() || UploadRanges(upload_ranges_);
'''
UPLOAD_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: upload statistics (tools/ios/patch_ios_shared_stats.py).
  if (REXCVAR_GET(ios_shared_stats)) {
    for (const auto& r : upload_ranges_) {
      ios_shared_upload_pages += r.second;
    }
    ios_shared_uploads += upload_ranges_.size();
    const auto now = std::chrono::steady_clock::now();
    if (now - ios_shared_since >= std::chrono::seconds(5)) {
      REXGPU_INFO("[ios-shared] 5 s: {} CPU write faults, {} pages invalidated, {:.1f} MB "
                  "uploaded in {} uploads (widening {} KB)",
                  ios_shared_faults.exchange(0), ios_shared_pages_invalidated.exchange(0),
                  double(ios_shared_upload_pages << page_size_log2_) / (1024.0 * 1024.0),
                  ios_shared_uploads, REXCVAR_GET(ios_invalidation_widen_kb));
      ios_shared_upload_pages = 0;
      ios_shared_uploads = 0;
      ios_shared_since = now;
    }
  }
#endif
  const bool nfsmw_subido = upload_ranges_.empty() || UploadRanges(upload_ranges_);
'''

BLOCKS = [
    (F, "the cvars and counters", CVAR_ANCHOR, CVAR_NEW),
    (F, "limit the widening, count the faults", WIDEN_ANCHOR, WIDEN_NEW),
    (F, "count the invalidated pages", COUNT_ANCHOR, COUNT_NEW),
    (F, "count the uploads and log", UPLOAD_ANCHOR, UPLOAD_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_shared_stats", BLOCKS))
