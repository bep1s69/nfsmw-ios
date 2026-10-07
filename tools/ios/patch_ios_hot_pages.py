#!/usr/bin/env python3
"""
"Hot" pages: guest memory the CPU keeps rewriting is no longer protected; it
counts as never valid, so each use uploads its current contents.

    python3 tools/ios/patch_ios_hot_pages.py            apply
    python3 tools/ios/patch_ios_hot_pages.py --status
    python3 tools/ios/patch_ios_hot_pages.py --revert

Touches src/graphics/shared_memory.cpp. Apply after patch_ios_shared_stats.py.
Cvar ios_hot_pages: OFF. Tried on, in a race on an iPhone: the CPU write faults
fell from ~100,000 to ~1,000 every 5 s, but the GPU took 70-75 ms a frame
(12-14 fps): every draw uploaded its hot pages again, ~1,500 small copies a
frame, all hoisted to the start of their render pass (where several uploads
of one page in one pass also all land before the pass's first draw). Needs
uploads that are not per draw before it can be on.


WHY
===

patch_ios_shared_stats.py, in a race: 37,000-180,000 CPU write faults every
5 s (100-450 a frame) and 4-8 GB uploaded, whatever the widening (256, 64 or
16 KB). The game fills its dynamic buffers piece by piece while drawing from
them: a write faults, the page is invalidated, a draw uploads it and protects
it again, the next piece written into the same page faults again. Each fault
stops a game thread (a signal, the handler, an mprotect); each upload
protects again (11 % of the GPU command thread).

A page that faults 4 times within a second becomes hot: it stays unprotected
and is never marked valid, so every request uploads it (the uploads that
happened anyway) and no write to it faults again. Pages a watch covers (a
texture's data) never become hot, and become normal again, valid and
protected, when a watch is placed on them; a GPU write (a resolve) makes them
normal too. So whatever is cached from guest memory is still invalidated by
CPU writes exactly as before.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/shared_memory.cpp"

TOP_ANCHOR = '''namespace rex::graphics {
'''
TOP_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: hot pages (tools/ios/patch_ios_hot_pages.py).
#include <vector>
REXCVAR_DEFINE_BOOL(ios_hot_pages, false, "GPU",
                    "iOS: pages the CPU keeps rewriting stay unprotected and are uploaded on "
                    "every use instead of faulting on every write");
namespace {
// Under the shared memory's global lock. One shared memory.
std::vector<uint8_t> ios_page_faults;  // faults in the current second, per page
std::vector<uint64_t> ios_hot;         // hot pages, one bit each, 64 per block
std::chrono::steady_clock::time_point ios_faults_since = std::chrono::steady_clock::now();
uint64_t ios_hot_count = 0, ios_hot_cooled = 0;
inline uint64_t IosHotBlock(uint32_t block) {
  return block < ios_hot.size() ? ios_hot[block] : 0;
}
}  // namespace
#endif

namespace rex::graphics {
'''

FAULT_ANCHOR = '''  ios_shared_faults.fetch_add(1, std::memory_order_relaxed);
#endif
'''
FAULT_NEW = '''  ios_shared_faults.fetch_add(1, std::memory_order_relaxed);
#endif
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: pages written again and again become hot
  // (tools/ios/patch_ios_hot_pages.py).
  if (REXCVAR_GET(ios_hot_pages)) {
    const uint32_t page_count = kBufferSize >> page_size_log2_;
    if (ios_page_faults.size() != page_count) {
      ios_page_faults.assign(page_count, 0);
      ios_hot.assign((page_count + 63) >> 6, 0);
    }
    const auto now = std::chrono::steady_clock::now();
    if (now - ios_faults_since >= std::chrono::seconds(1)) {
      std::fill(ios_page_faults.begin(), ios_page_faults.end(), uint8_t(0));
      ios_faults_since = now;
    }
    const uint32_t written_first = physical_address_start >> page_size_log2_;
    const uint32_t written_last = physical_address_last >> page_size_log2_;
    for (uint32_t page = written_first; page <= written_last && page < page_count; ++page) {
      uint8_t& faults = ios_page_faults[page];
      if (faults < 255) {
        ++faults;
      }
      if (faults < 4 || (ios_hot[page >> 6] >> (page & 63)) & 1) {
        continue;
      }
      // Not if anything watches it (a texture's data).
      bool watched = false;
      const uint32_t bucket = (page << page_size_log2_) >> kWatchBucketSizeLog2;
      for (const WatchNode* node = watch_buckets_[bucket]; node && !watched;
           node = node->bucket_node_next) {
        watched = page >= node->range->page_first && page <= node->range->page_last;
      }
      if (!watched) {
        ios_hot[page >> 6] |= uint64_t(1) << (page & 63);
        ++ios_hot_count;
      }
    }
  }
#endif
'''

SCAN_ANCHOR = '''        uint64_t block_valid = system_page_flags_valid_[i];
'''
SCAN_NEW = '''        uint64_t block_valid = system_page_flags_valid_[i];
#if REX_PLATFORM_IOS
        block_valid &= ~IosHotBlock(i);  // LOCAL PATCH - iOS: hot pages are never valid
#endif
'''

VALID_ANCHOR = '''      system_page_flags_valid_[i] |= valid_bits;
'''
VALID_NEW = '''#if REX_PLATFORM_IOS
      valid_bits &= ~IosHotBlock(i);  // LOCAL PATCH - iOS: hot pages are never valid
#endif
      system_page_flags_valid_[i] |= valid_bits;
'''

PROTECT_ANCHOR = '''  if (memory_invalidation_callback_handle_) {
    memory().EnablePhysicalMemoryAccessCallbacks(
        valid_page_first << page_size_log2_,
        (valid_page_last - valid_page_first + 1) << page_size_log2_, true, false);
  }
}
'''
PROTECT_NEW = '''  if (memory_invalidation_callback_handle_) {
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: hot pages stay unprotected (patch_ios_hot_pages.py).
    bool any_hot = false;
    for (uint32_t b = valid_block_first; b <= valid_block_last && !any_hot; ++b) {
      any_hot = IosHotBlock(b) != 0;
    }
    if (any_hot) {
      uint32_t run_first = UINT32_MAX;
      for (uint32_t page = valid_page_first; page <= valid_page_last + 1; ++page) {
        const bool hot =
            page > valid_page_last || ((IosHotBlock(page >> 6) >> (page & 63)) & 1);
        if (!hot && run_first == UINT32_MAX) {
          run_first = page;
        } else if (hot && run_first != UINT32_MAX) {
          memory().EnablePhysicalMemoryAccessCallbacks(
              run_first << page_size_log2_, (page - run_first) << page_size_log2_, true, false);
          run_first = UINT32_MAX;
        }
      }
      return;
    }
#endif
    memory().EnablePhysicalMemoryAccessCallbacks(
        valid_page_first << page_size_log2_,
        (valid_page_last - valid_page_first + 1) << page_size_log2_, true, false);
  }
}
'''

WATCH_ANCHOR = '''  return reinterpret_cast<WatchHandle>(range);
'''
WATCH_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: a watched page is not hot: valid (its contents were
  // just uploaded for whoever watches it) and protected again
  // (tools/ios/patch_ios_hot_pages.py).
  {
    bool any_hot = false;
    for (uint32_t page = watch_page_first; page <= watch_page_last; ++page) {
      if (page >> 6 < ios_hot.size() && (ios_hot[page >> 6] >> (page & 63)) & 1) {
        ios_hot[page >> 6] &= ~(uint64_t(1) << (page & 63));
        any_hot = true;
        ++ios_hot_cooled;
      }
    }
    if (any_hot) {
      // Not under the global lock: protecting takes the memory's lock, which
      // the fault handler takes before this one.
      global_lock.unlock();
      MakeRangeValid(watch_page_first << page_size_log2_,
                     (watch_page_last - watch_page_first + 1) << page_size_log2_, false);
    }
  }
#endif
  return reinterpret_cast<WatchHandle>(range);
'''

GPU_ANCHOR = '''  MakeRangeValid(start, length, true);
'''
GPU_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: GPU-written pages are not hot (patch_ios_hot_pages.py).
  {
    auto global_lock = global_critical_region_.Acquire();
    for (uint32_t page = page_first; page <= page_last; ++page) {
      if (page >> 6 < ios_hot.size()) {
        ios_hot[page >> 6] &= ~(uint64_t(1) << (page & 63));
      }
    }
  }
#endif
  MakeRangeValid(start, length, true);
'''

LOG_ANCHOR = '''                  ios_shared_requests, double(ios_shared_requested_bytes) / (1024.0 * 1024.0));
'''
LOG_NEW = '''                  ios_shared_requests, double(ios_shared_requested_bytes) / (1024.0 * 1024.0));
      {
        uint64_t hot_now = 0;
        for (uint64_t block : ios_hot) {
          hot_now += __builtin_popcountll(block);
        }
        REXGPU_INFO("[ios-shared]   hot pages: {} now, {} made hot, {} back to normal (total)",
                    hot_now, ios_hot_count, ios_hot_cooled);
      }
'''

BLOCKS = [
    (F, "the cvar and the hot page bits", TOP_ANCHOR, TOP_NEW),
    (F, "pages written again and again become hot", FAULT_ANCHOR, FAULT_NEW),
    (F, "hot pages are uploaded on every request", SCAN_ANCHOR, SCAN_NEW),
    (F, "hot pages are never marked valid", VALID_ANCHOR, VALID_NEW),
    (F, "hot pages are not protected", PROTECT_ANCHOR, PROTECT_NEW),
    (F, "a watched page is not hot", WATCH_ANCHOR, WATCH_NEW),
    (F, "a GPU-written page is not hot", GPU_ANCHOR, GPU_NEW),
    (F, "hot pages in the log", LOG_ANCHOR, LOG_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_hot_pages", BLOCKS))
