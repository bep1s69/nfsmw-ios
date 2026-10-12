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
RESET_NEW = '''    if (REXCVAR_GET(ios_xma_starve_reset) &&
        data.output_buffer_write_offset != data.output_buffer_read_offset) {
      data.output_buffer_write_offset = data.output_buffer_read_offset;
'''

BLOCKS = [
    (FILE, "the ios_xma_starve_reset cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "the reset only while it is on", RESET_ANCHOR, RESET_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_starve_switch", BLOCKS))
