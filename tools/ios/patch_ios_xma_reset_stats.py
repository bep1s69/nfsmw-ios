#!/usr/bin/env python3
"""
Once a second: the XMA stream resets, how many streams and how much decoded
sound they dropped.

    python3 tools/ios/patch_ios_xma_reset_stats.py            apply
    python3 tools/ios/patch_ios_xma_reset_stats.py --status
    python3 tools/ios/patch_ios_xma_reset_stats.py --revert

Touches src/audio/xma_context.cpp. Builds on patch_ios_xma_canary.py.


WHY
===

In police chases the game mixes exact silence for 245 ms at a time
(CoreAudio's "sudden drop" lines), over and over. The reset of streams run
dry (Xenia Canary's NFS stall detector fix) fires ~100-200 times a second
there. "[xma-resets]" lines put the resets on the same clock as the drops:
per second, resets, distinct contexts, decoded blocks dropped, and the
contexts with the most.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

ANCHOR = '''  StoreContextMerged(data, initial_data, context_ptr);
  return true;
}

void XmaContext::Enable() {
'''
NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py): resets of
  // streams run dry, once a second.
  if (!initial_data.IsAnyInputBufferValid() &&
      initial_data.output_buffer_write_offset != initial_data.output_buffer_read_offset &&
      data.output_buffer_write_offset == data.output_buffer_read_offset) {
    static std::mutex stats_mutex;
    static std::map<uint32_t, std::pair<uint32_t, uint32_t>> per_context;  // id -> (resets, blocks)
    static auto since = std::chrono::steady_clock::now();
    const uint32_t count = std::max<uint32_t>(initial_data.output_buffer_block_count, 1);
    const uint32_t dropped = (initial_data.output_buffer_write_offset + count -
                              initial_data.output_buffer_read_offset) % count;
    std::lock_guard<std::mutex> lock(stats_mutex);
    auto& e = per_context[id()];
    ++e.first;
    e.second += dropped;
    const auto now = std::chrono::steady_clock::now();
    if (now - since >= std::chrono::seconds(1)) {
      uint32_t resets = 0, blocks = 0;
      std::vector<std::pair<uint32_t, uint32_t>> top;  // (resets, id)
      for (const auto& [ctx, v] : per_context) {
        resets += v.first;
        blocks += v.second;
        top.push_back({v.first, ctx});
      }
      std::sort(top.rbegin(), top.rend());
      std::string most;
      for (size_t i = 0; i < top.size() && i < 6; ++i) most += fmt::format(" {}:{}", top[i].second, top[i].first);
      REXLOG_INFO("[xma-resets] {} resets on {} contexts, {} decoded blocks dropped | most:{}", resets,
                  per_context.size(), blocks, most);
      per_context.clear();
      since = now;
    }
  }

  StoreContextMerged(data, initial_data, context_ptr);
  return true;
}

void XmaContext::Enable() {
'''

INC_ANCHOR = '''#include <algorithm>
'''
INC_NEW = '''#include <algorithm>
#include <map>  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py)
#include <string>
#include <vector>
'''

WORK_ANCHOR = '''  std::lock_guard<std::mutex> lock(lock_);
  set_is_enabled(false);

  auto context_ptr = memory()->TranslateVirtual(guest_ptr());
'''
WORK_NEW = '''  std::lock_guard<std::mutex> lock(lock_);
  set_is_enabled(false);
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py): Work() time
  // and codec reopens, once a second ("[xma-work]").
  struct IosWorkTimer {
    std::chrono::steady_clock::time_point t0 = std::chrono::steady_clock::now();
    ~IosWorkTimer() {
      static std::atomic<uint64_t> works{0}, total_us{0}, max_us{0};
      static std::atomic<int64_t> since_us{0};
      const auto now = std::chrono::steady_clock::now();
      const uint64_t us = uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(now - t0).count());
      ++works;
      total_us += us;
      uint64_t m = max_us.load();
      while (us > m && !max_us.compare_exchange_weak(m, us)) {}
      const int64_t now_us = std::chrono::duration_cast<std::chrono::microseconds>(now.time_since_epoch()).count();
      int64_t s = since_us.load();
      if (!s) since_us.compare_exchange_strong(s, now_us);
      else if (now_us - s >= 1000000 && since_us.compare_exchange_strong(s, now_us)) {
        REXLOG_INFO("[xma-work] {} Work calls, {:.1f} ms in all, longest {:.2f} ms, {} codec reopens",
                    works.exchange(0), total_us.exchange(0) / 1000.0, max_us.exchange(0) / 1000.0,
                    ios_xma_codec_reopens.exchange(0));
      }
    }
  } ios_work_timer;

  auto context_ptr = memory()->TranslateVirtual(guest_ptr());
'''

REOPEN_ANCHOR = '''    if (avcodec_open2(av_context_, av_codec_, NULL) < 0) {
      REXAPU_ERROR("XmaContext: Failed to reopen FFmpeg context");
      return -1;
    }
    return 1;
'''
REOPEN_NEW = '''    if (avcodec_open2(av_context_, av_codec_, NULL) < 0) {
      REXAPU_ERROR("XmaContext: Failed to reopen FFmpeg context");
      return -1;
    }
    ++ios_xma_codec_reopens;  // LOCAL PATCH - iOS (patch_ios_xma_reset_stats.py)
    return 1;
'''

COUNTER_ANCHOR = '''const uint32_t XmaContext::kBitsPerPacketHeader;
'''
COUNTER_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py).
static std::atomic<uint64_t> ios_xma_codec_reopens{0};

const uint32_t XmaContext::kBitsPerPacketHeader;
'''

BLOCKS = [
    (FILE, "includes", INC_ANCHOR, INC_NEW),
    (FILE, "resets once a second", ANCHOR, NEW),
    (FILE, "the codec reopen counter", COUNTER_ANCHOR, COUNTER_NEW),
    (FILE, "Work() timed", WORK_ANCHOR, WORK_NEW),
    (FILE, "codec reopens counted", REOPEN_ANCHOR, REOPEN_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_reset_stats", BLOCKS))
