#!/usr/bin/env python3
"""
Keep looping XMA streams out of the "ran out of input" reset (GitHub issue 15).

    python3 tools/ios/patch_ios_xma_starve_loops.py            apply
    python3 tools/ios/patch_ios_xma_starve_loops.py --status
    python3 tools/ios/patch_ios_xma_starve_loops.py --revert

Touches src/audio/xma_context.cpp. Builds on patch_ios_xma_starve_switch.py.


WHY
===

The Volkswagen Golf's engine sound cut out about once a second (iPad Pro M5,
iPhone 17 Pro Max, 0.5.2 and dev91). The host output had no gaps; turning the
launcher's "Audio stream reset" off made the cut go away (Stefan, November 6).
The reset (Xenia Canary's NFS stall-detector fix) drops decoded output the
game has not read yet whenever a context starts Work() without valid input.
It cannot simply go: it keeps one-shot streams from replaying a stale stretch,
and a 60 ms grace cut the menu songs (October 13). Guess under test: the
engine is a stream the game set to loop (loop_count > 0); those keep their
output. ios_xma_starve_keep_loops turns this off; "[xma] starve" lines every
5 s count resets and kept loops, to check the guess.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_xma_starve_reset, true, "Audio",
'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_loops.py).
REXCVAR_DEFINE_BOOL(ios_xma_starve_keep_loops, true, "Audio",
                    "iOS: the ran-out-of-input reset leaves looping streams alone "
                    "(the Golf's engine cut out once a second, issue 15)");
REXCVAR_DEFINE_BOOL(ios_xma_starve_reset, true, "Audio",
'''

RESET_ANCHOR = '''    if (REXCVAR_GET(ios_xma_starve_reset) && stalled &&
        data.output_buffer_write_offset != data.output_buffer_read_offset) {
'''
RESET_NEW = '''    // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_loops.py): a looping
    // stream keeps its output; counted with the resets every 5 s.
    const bool ios_pending = data.output_buffer_write_offset != data.output_buffer_read_offset;
    const bool ios_keep_loop = REXCVAR_GET(ios_xma_starve_keep_loops) && data.loop_count > 0;
    if (REXCVAR_GET(ios_xma_starve_reset) && stalled && ios_pending) {
      static std::atomic<uint32_t> ios_resets{0}, ios_kept{0};
      static std::atomic<int64_t> ios_since{0};
      ++(ios_keep_loop ? ios_kept : ios_resets);
      const int64_t now_s = std::chrono::duration_cast<std::chrono::seconds>(
          std::chrono::steady_clock::now().time_since_epoch()).count();
      int64_t last = ios_since.load();
      if (last == 0) ios_since.compare_exchange_strong(last, now_s);
      else if (now_s - last >= 5 && ios_since.compare_exchange_strong(last, now_s)) {
        REXLOG_INFO("[xma] starve 5 s: {} resets, {} looping streams kept", ios_resets.exchange(0),
                    ios_kept.exchange(0));
      }
    }
    if (REXCVAR_GET(ios_xma_starve_reset) && stalled && ios_pending && !ios_keep_loop) {
'''

BLOCKS = [
    (FILE, "the ios_xma_starve_keep_loops cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "looping streams kept out of the reset", RESET_ANCHOR, RESET_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_starve_loops", BLOCKS))
