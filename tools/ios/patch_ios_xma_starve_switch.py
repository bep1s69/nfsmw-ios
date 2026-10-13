#!/usr/bin/env python3
"""
A switch for the XMA "ran out of input" reset (patch_ios_xma_canary.py).

    python3 tools/ios/patch_ios_xma_starve_switch.py            apply
    python3 tools/ios/patch_ios_xma_starve_switch.py --status
    python3 tools/ios/patch_ios_xma_starve_switch.py --revert

Touches src/audio/xma_context.cpp. Builds on patch_ios_xma_canary.py.


WHY
===

When a context starts Work() with no valid input but decoded output the game
has not read yet, the Canary reset sets the write offset back to the read
offset: that output is dropped. Police radio chatter is streamed in pieces;
when the next piece is late, the end of the current line may be cut (the user
hears the chatter cut out). The cvar ios_xma_starve_reset (launcher: Audio
stream reset) turns the reset off, to compare in the same build.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"
HDR = "include/rex/audio/xma/context.h"

CVAR_ANCHOR = '''#include <rex/stream.h>
'''
CVAR_NEW = '''#include <rex/stream.h>
#include <rex/cvar.h>  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_switch.py)

// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_switch.py).
REXCVAR_DEFINE_BOOL(ios_xma_starve_reset, true, "Audio",
                    "iOS: a stream that runs out of input drops the output the game has not "
                    "read yet (Xenia Canary's NFS stall detector fix)");
'''

RESET_ANCHOR = '''    if (data.output_buffer_write_offset != data.output_buffer_read_offset) {
      data.output_buffer_write_offset = data.output_buffer_read_offset;
'''

GRACE_CVAR_ANCHOR = CVAR_NEW
GRACE_CVAR_NEW = CVAR_NEW + '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_switch.py): the reset
// only once the game has stopped reading for this long; while it still reads,
// the decoded output plays out (0: at once, as Xenia Canary).
REXCVAR_DEFINE_INT32(ios_xma_starve_grace_ms, 0, "Audio",
                     "iOS: starved of input, reset a stream only after the game has not read "
                     "its output for this many ms (0: at once)");
'''

RESET_NEW = '''    // LOCAL PATCH - iOS: not while the game is still reading what was
    // decoded (streamed speech lost its ends: police radio chatter cut out).
    // The read offset unchanged for ios_xma_starve_grace_ms: it has stopped.
    bool stalled = true;
    const int32_t grace_ms = REXCVAR_GET(ios_xma_starve_grace_ms);
    if (grace_ms > 0) {
      const auto now = std::chrono::steady_clock::now();
      if (!ios_starve_seen_ || data.output_buffer_read_offset != ios_starve_read_offset_) {
        ios_starve_seen_ = true;
        ios_starve_read_offset_ = data.output_buffer_read_offset;
        ios_starve_since_ = now;
      }
      stalled = now - ios_starve_since_ >= std::chrono::milliseconds(grace_ms);
    }
    if (REXCVAR_GET(ios_xma_starve_reset) && stalled &&
        data.output_buffer_write_offset != data.output_buffer_read_offset) {
      ios_starve_seen_ = false;
      data.output_buffer_write_offset = data.output_buffer_read_offset;
'''

FED_ANCHOR = '''  if (initial_data.IsAnyInputBufferValid()) {
    data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;
  } else {
'''
FED_NEW = '''  if (initial_data.IsAnyInputBufferValid()) {
    data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;
    ios_starve_seen_ = false;  // LOCAL PATCH - iOS: fed again
  } else {
'''

HDR_ANCHOR = '''  bool carry_valid_ = false;
  uint8_t pending_output_limit_ = 0;
  uint8_t pending_start_skip_ = 0;
};
'''
HDR_NEW = '''  bool carry_valid_ = false;
  uint8_t pending_output_limit_ = 0;
  uint8_t pending_start_skip_ = 0;

  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_switch.py): starved of
  // input, since when the game's read offset has not moved.
  bool ios_starve_seen_ = false;
  uint32_t ios_starve_read_offset_ = 0;
  std::chrono::steady_clock::time_point ios_starve_since_{};
};
'''

INC_ANCHOR = '''#include <atomic>
#include <mutex>
'''
INC_NEW = '''#include <atomic>
#include <chrono>  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_switch.py)
#include <mutex>
'''

BLOCKS = [
    (FILE, "the ios_xma_starve_reset cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "the reset only while it is on, once the game stopped reading", RESET_ANCHOR, RESET_NEW),
    (HDR, "<chrono>", INC_ANCHOR, INC_NEW),
    (HDR, "the stall timer members", HDR_ANCHOR, HDR_NEW),
    (FILE, "the ios_xma_starve_grace_ms cvar", GRACE_CVAR_ANCHOR, GRACE_CVAR_NEW),
    (FILE, "the stall timer cleared when fed", FED_ANCHOR, FED_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_starve_switch", BLOCKS))
