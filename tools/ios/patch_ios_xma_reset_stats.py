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

BLOCKS = [
    (FILE, "includes", INC_ANCHOR, INC_NEW),
    (FILE, "resets once a second", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_reset_stats", BLOCKS))
