#!/usr/bin/env python3
"""
A guest thread's first stack frame starts a little below the top of its
stack, over zeros, instead of exactly at the guard page.

    python3 tools/ios/patch_ios_stack_top.py            apply
    python3 tools/ios/patch_ios_stack_top.py --status
    python3 tools/ios/patch_ios_stack_top.py --revert

Touches src/system/xthread.cpp.

The freezes after leaving the safehouse (and on the freeway, in tollbooth
races): the game kept running underneath (music, controls), the picture
stopped. Both logs of 2026-10-14 show the main thread inside its job loop
(823C82F8) reading guest 0x70190000 a million times: "Unhandled guest access
violation: read of guest 0x70190000". The main thread's stack is
0x70150000-0x70190000 and it started with r1 = 0x70190000: the SDK puts the
first frame exactly at the top, so the first frame's back-chain points at the
guard page just above. Anything that follows the back-chain to its end (a
stack walk) reads that guard page, and the fault handler retried the read
forever.

Now every guest thread starts 256 bytes below the top, and those bytes are
zero: the back-chain ends in a 0 inside the stack, as walks expect. The stack
limits the game sees (PCR stack base/end) are unchanged.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/system/xthread.cpp"

ANCHOR = '''  thread_state_ =
      std::make_unique<runtime::ThreadState>(thread_id_, stack_base_, pcr_address_, memory());
'''
NEW = '''  // LOCAL PATCH - iOS: the first frame 256 bytes below the stack's top, over
  // zeros, so the back-chain ends inside the stack instead of at the guard
  // page above it (a stack walk read it forever: the "safehouse" freeze;
  // tools/ios/patch_ios_stack_top.py).
  constexpr uint32_t kIosStackTop = 0x100;
  if (stack_base_) {
    memory()->Fill(stack_base_ - kIosStackTop, kIosStackTop, 0);
  }
  thread_state_ = std::make_unique<runtime::ThreadState>(
      thread_id_, stack_base_ ? stack_base_ - kIosStackTop : 0, pcr_address_, memory());
'''

BLOCKS = [
    (FILE, "first frame below the stack's top", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_stack_top", BLOCKS))
