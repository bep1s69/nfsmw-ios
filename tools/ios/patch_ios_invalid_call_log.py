#!/usr/bin/env python3
"""
More to go on when the game calls a function that does not exist.

    python3 tools/ios/patch_ios_invalid_call_log.py            apply
    python3 tools/ios/patch_ios_invalid_call_log.py --status
    python3 tools/ios/patch_ios_invalid_call_log.py --revert

Touches src/system/function_dispatcher.cpp.


WHY
===

Since 2026-10-12 the game sometimes dies right after leaving the safehouse
with "[FATAL] Call to invalid or unregistered function at guest address
0x00000000": an indirect call through a null pointer. The line names only
the target (0), not who called it. The trap now also logs the guest link
register, the stack pointer, r3-r5 and a walk of the guest stack's back
chain (saved return addresses), so the caller can be found in the
recompiled code.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/system/function_dispatcher.cpp"

TRAP_ANCHOR = '''static void InvalidFunctionTrap(PPCContext& ctx, uint8_t* /*base*/) {
  REX_FATAL("Call to invalid or unregistered function at guest address 0x{:08X}",
            ctx.last_indirect_target);
}
'''
TRAP_NEW = '''static void InvalidFunctionTrap(PPCContext& ctx, uint8_t* base) {
  // LOCAL PATCH - iOS (tools/ios/patch_ios_invalid_call_log.py): who called.
  if (base) {
    auto read32 = [&](uint32_t a) {
      uint32_t v;
      std::memcpy(&v, base + a, 4);
      return __builtin_bswap32(v);
    };
    std::string chain;
    uint32_t sp = ctx.r1.u32;
    for (int i = 0; i < 16 && sp >= 0x70000000u && sp < 0x80000000u && (sp & 3) == 0; ++i) {
      const uint32_t up = read32(sp);
      if (up <= sp || up - sp > 0x40000 || up >= 0x80000000u) break;
      chain += fmt::format(" <- 0x{:08X}", read32(up - 8));
      sp = up;
    }
    REXLOG_ERROR("[invalid-call] lr=0x{:08X} r1=0x{:08X} r3=0x{:08X} r4=0x{:08X} r5=0x{:08X} "
                 "ctr=0x{:08X} | stack{}",
                 uint32_t(ctx.lr), ctx.r1.u32, ctx.r3.u32, ctx.r4.u32, ctx.r5.u32, ctx.ctr.u32, chain);
  }
  REX_FATAL("Call to invalid or unregistered function at guest address 0x{:08X}",
            ctx.last_indirect_target);
}
'''

INC_ANCHOR = '''#include <rex/assert.h>
'''
INC_NEW = '''#include <rex/assert.h>
#include <cstring>  // LOCAL PATCH - iOS (tools/ios/patch_ios_invalid_call_log.py)
#include <string>
'''

BLOCKS = [
    (FILE, "includes", INC_ANCHOR, INC_NEW),
    (FILE, "the trap logs the caller", TRAP_ANCHOR, TRAP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_invalid_call_log", BLOCKS))
