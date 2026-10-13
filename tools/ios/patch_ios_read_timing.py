#!/usr/bin/env python3
"""
Slow disc reads in the log, to find what starves streamed sound.

    python3 tools/ios/patch_ios_read_timing.py            apply
    python3 tools/ios/patch_ios_read_timing.py --status
    python3 tools/ios/patch_ios_read_timing.py --revert

Touches src/kernel/xboxkrnl/xboxkrnl_io.cpp.


WHY
===

The police radio chatter cuts out in chases while CoreAudio's output is
clean and the XMA reset matches Xenia Canary's. The chatter is streamed
from D:\\Sound\\Speech\\copspeech_en.big: if its reads are slow (the ISO
mapped from flash, a page fault per new stretch), the stream runs dry.
NtReadFile now logs reads that take 8 ms or more ("[slow-read]", the first
300), and every read of a speech file once a second as a summary
("[speech-read]": count, bytes, slowest).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/kernel/xboxkrnl/xboxkrnl_io.cpp"

READ_ANCHOR = '''      uint32_t bytes_read = 0;
      result = file->Read(buffer.guest_address(), buffer_length,
                          byte_offset_ptr ? static_cast<uint64_t>(*byte_offset_ptr) : -1,
                          &bytes_read, apc_context.guest_address());
'''
READ_NEW = '''      uint32_t bytes_read = 0;
      const auto ios_read_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
      result = file->Read(buffer.guest_address(), buffer_length,
                          byte_offset_ptr ? static_cast<uint64_t>(*byte_offset_ptr) : -1,
                          &bytes_read, apc_context.guest_address());
      {
        // LOCAL PATCH - iOS (tools/ios/patch_ios_read_timing.py): slow reads,
        // and the speech stream's reads once a second.
        const auto now = std::chrono::steady_clock::now();
        const double ms = std::chrono::duration<double, std::milli>(now - ios_read_start).count();
        const std::string& path = file->path();
        static std::atomic<int> slow_lines{300};
        if (ms >= 8.0 && slow_lines.fetch_sub(1) > 0) {
          REXLOG_INFO("[slow-read] {:.1f} ms: {} bytes at {} of {}", ms, bytes_read,
                      byte_offset_ptr ? int64_t(static_cast<uint64_t>(*byte_offset_ptr)) : -1, path);
        }
        bool speech = false;
        for (size_t i = 0; i + 6 <= path.size() && !speech; ++i) {
          speech = (path[i] | 32) == 's' && (path[i + 1] | 32) == 'p' && (path[i + 2] | 32) == 'e' &&
                   (path[i + 3] | 32) == 'e' && (path[i + 4] | 32) == 'c' && (path[i + 5] | 32) == 'h';
        }
        if (speech) {
          static std::mutex m;
          static uint32_t count = 0;
          static uint64_t bytes = 0;
          static double slowest = 0, total_ms = 0;
          static auto since = now;
          std::lock_guard<std::mutex> lock(m);
          ++count;
          bytes += bytes_read;
          total_ms += ms;
          slowest = std::max(slowest, ms);
          if (now - since >= std::chrono::seconds(1)) {
            REXLOG_INFO("[speech-read] {} reads, {} KiB, {:.1f} ms in all, slowest {:.1f} ms", count,
                        bytes >> 10, total_ms, slowest);
            count = 0;
            bytes = 0;
            slowest = total_ms = 0;
            since = now;
          }
        }
      }
'''


BLOCKS = [
    (FILE, "slow and speech reads logged", READ_ANCHOR, READ_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_read_timing", BLOCKS))
