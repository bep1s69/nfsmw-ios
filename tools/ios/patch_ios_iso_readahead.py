#!/usr/bin/env python3
"""
Read-ahead on the mapped ISO, and who waits on disc reads (iOS).

    python3 tools/ios/patch_ios_iso_readahead.py            apply
    python3 tools/ios/patch_ios_iso_readahead.py --status
    python3 tools/ios/patch_ios_iso_readahead.py --revert

Touches src/filesystem/devices/disc_image_file.cpp.


WHY
===

The 60 fps judder (D-005): every frame is new and shown on time, yet the
motion is uneven; an area gets smoother the more it is driven, also after
relaunching, and after a device restart even leaving the safehouse "felt like
30 fps" (Stefan, Oct 28). What survives a relaunch and not a restart is
iOS' file cache. The ISO is mapped: a disc read is a memcpy from the mapping,
and the first read of a stretch page-faults it in from flash on the reading
(game) thread. Now:
- ios_iso_readahead_mb (default 16): after each read, the next that many MB
  of the image are advised (madvise MADV_WILLNEED), so the kernel reads them
  in ahead of the game, in the background;
- every 5 s, `[iso-read]` per thread: reads, KiB, ms spent reading, slowest.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/filesystem/devices/disc_image_file.cpp"

INC_ANCHOR = '''#include <algorithm>

namespace rex::filesystem {
'''
INC_NEW = '''#include <algorithm>
// LOCAL PATCH - iOS (tools/ios/patch_ios_iso_readahead.py)
#include <pthread.h>
#include <sys/mman.h>
#include <unistd.h>
#include <chrono>
#include <map>
#include <mutex>
#include <string>
#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_INT32(ios_iso_readahead_mb, 16, "Filesystem",
                     "iOS: after each disc read, ask the kernel to read this many MB of the "
                     "image ahead into memory (0: off)");

namespace {
// Per thread, since the last line: reads, bytes, time, slowest.
struct IosReadStats {
  uint32_t reads = 0;
  uint64_t bytes = 0;
  double ms = 0, slowest = 0;
};
void IosCountRead(size_t bytes, double ms) {
  static std::mutex m;
  static std::map<std::string, IosReadStats> by_thread;
  static auto since = std::chrono::steady_clock::now();
  static int lines = 400;
  char name[64] = {};
  pthread_getname_np(pthread_self(), name, sizeof(name));
  std::lock_guard<std::mutex> lock(m);
  auto& s = by_thread[name[0] ? name : "?"];
  ++s.reads;
  s.bytes += bytes;
  s.ms += ms;
  s.slowest = std::max(s.slowest, ms);
  const auto now = std::chrono::steady_clock::now();
  if (now - since >= std::chrono::seconds(5)) {
    std::string text;
    for (const auto& [thread, t] : by_thread) {
      text += " | " + thread + ": " + std::to_string(t.reads) + " reads, " + std::to_string(t.bytes >> 10) +
              " KiB, " + std::to_string(int(t.ms * 10) / 10.0).substr(0, 6) + " ms, slowest " +
              std::to_string(int(t.slowest * 10) / 10.0).substr(0, 5) + " ms";
    }
    if (lines-- > 0) REXLOG_INFO("[iso-read] 5 s (read-ahead {} MB){}", REXCVAR_GET(ios_iso_readahead_mb), text);
    by_thread.clear();
    since = now;
  }
}
}  // namespace

namespace rex::filesystem {
'''

READ_ANCHOR = '''  std::memcpy(buffer.data(), entry_->mmap()->data() + real_offset, real_length);
  *out_bytes_read = real_length;
  return X_STATUS_SUCCESS;
}
'''
READ_NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_iso_readahead.py): timed, then
  // the next stretch of the image advised.
  const auto ios_start = std::chrono::steady_clock::now();
  std::memcpy(buffer.data(), entry_->mmap()->data() + real_offset, real_length);
  IosCountRead(real_length,
               std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - ios_start).count());
  if (const int32_t ahead_mb = REXCVAR_GET(ios_iso_readahead_mb); ahead_mb > 0) {
    static const size_t page = size_t(getpagesize());
    const size_t map_size = entry_->mmap()->size();
    const size_t from = (real_offset + real_length) & ~(page - 1);
    const size_t to = std::min(map_size, from + size_t(ahead_mb) * 1024 * 1024);
    // Again only when the reads have used up half of the stretch advised
    // last time for this file (streams read in small pieces).
    static std::mutex advised_mutex;
    static std::map<const void*, size_t> advised_end;
    bool advise = false;
    {
      std::lock_guard<std::mutex> lock(advised_mutex);
      size_t& end = advised_end[entry_];
      if (to > from && (from >= end || from + (to - from) / 2 > end || from + size_t(ahead_mb) * 1024 * 1024 < end)) {
        end = to;
        advise = true;
      }
    }
    if (advise) {
      madvise(const_cast<uint8_t*>(entry_->mmap()->data()) + from, to - from, MADV_WILLNEED);
    }
  }
  *out_bytes_read = real_length;
  return X_STATUS_SUCCESS;
}
'''

BLOCKS = [
    (FILE, "read-ahead includes, cvar and stats", INC_ANCHOR, INC_NEW),
    (FILE, "timed read and read-ahead", READ_ANCHOR, READ_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_iso_readahead", BLOCKS))
