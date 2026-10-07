#!/usr/bin/env python3
"""
Type-0 packets that write a range of registers go through the bulk path
(WriteRegisterRangeFromRing), which the Vulkan command processor handles in
one copy for shader constants, instead of one WriteRegister per register.

    python3 tools/ios/patch_ios_type0_ranges.py            apply
    python3 tools/ios/patch_ios_type0_ranges.py --status
    python3 tools/ios/patch_ios_type0_ranges.py --revert

Touches src/graphics/command_processor.cpp. Cvar ios_type0_ranges (on).


WHY
===

A CPU profile of the command processor in the heaviest stretch of a race
(where it, not the GPU, sets the frame rate): ExecutePacketType0 17.8 %,
CommandProcessor::WriteRegister 10.6 % and VulkanCommandProcessor::WriteRegister
4.5 % of it on their own. NFSMW writes its shader constants with type-0
packets, hundreds of registers a draw, and each went through the full
per-register path (cvar checks, the register table, a switch, then the
constant-buffer bookkeeping).

VulkanCommandProcessor::WriteRegistersFromMem already handles a range of float,
bool/loop or fetch constants in one byte-swapped copy and one check of which
constant buffers it touches; any other range it hands back to
CommandProcessor::WriteRegistersFromMem, which calls WriteRegister for each
register exactly as before. ExecutePacketType0 now uses it for a range of 2 or
more registers (not for "write one register count times").
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/command_processor.cpp"

ANCHOR = '''  uint32_t base_index = (packet & 0x7FFF);
  uint32_t write_one_reg = (packet >> 15) & 0x1;
  for (uint32_t m = 0; m < count; m++) {
'''
NEW = '''  uint32_t base_index = (packet & 0x7FFF);
  uint32_t write_one_reg = (packet >> 15) & 0x1;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: a range in bulk, shader constants in one copy
  // (tools/ios/patch_ios_type0_ranges.py).
  if (!write_one_reg && count > 1 && REXCVAR_GET(ios_type0_ranges)) {
    WriteRegisterRangeFromRing(reader, base_index, count);
    return true;
  }
#endif
  for (uint32_t m = 0; m < count; m++) {
'''

CVAR_ANCHOR = '''bool CommandProcessor::ExecutePacketType0(memory::RingBuffer* reader, uint32_t packet) {
'''
CVAR_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_type0_ranges.py).
REXCVAR_DEFINE_BOOL(ios_type0_ranges, true, "GPU",
                    "iOS: type-0 packets write a register range in bulk (shader constants in "
                    "one copy)");
#endif
bool CommandProcessor::ExecutePacketType0(memory::RingBuffer* reader, uint32_t packet) {
'''

BLOCKS = [
    (F, "the cvar", CVAR_ANCHOR, CVAR_NEW),
    (F, "type-0 ranges in bulk", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_type0_ranges", BLOCKS))
