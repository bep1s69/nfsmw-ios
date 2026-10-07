#!/usr/bin/env python3
"""
The "unknown register" check on every GPU register write becomes a table
lookup.

    python3 tools/ios/patch_ios_register_check.py            apply
    python3 tools/ios/patch_ios_register_check.py --status
    python3 tools/ios/patch_ios_register_check.py --revert

Touches src/graphics/command_processor.cpp.


WHAT A CPU PROFILE SHOWED
=========================

Instruments' Time Profiler, 15 s of a police chase on an iPad Pro M4, attached
to the running game (xctrace record --attach): the "GPU Commands" thread was
busy ~80 % of the time, and in chases it is what limits the frame rate (4,000-
5,000 draws a frame). 7.4 % of that thread was RegisterFile::GetRegisterInfo,
called from CommandProcessor::WriteRegister on EVERY register write:

    if (!regs.GetRegisterInfo(index)) {
      REXGPU_DEBUG("GPU: Write to unknown register ...");
    }

GetRegisterInfo is a switch over the whole register table where each case has
a function-local static (so a thread-safe initialisation guard to check), only
to print a debug line. Now the set of known registers is worked out once, the
first time, into a table of RegisterFile::kRegisterCount flags; each write is
one array read. The debug line is the same.

Also: CommandProcessor::IsReadbackMemexportEnabled, called on every draw,
looked a cvar up by name (rex::cvar::HasNonDefaultValue) each time: 2.3 % of
the thread. Whether that cvar was given is fixed at start: looked up once.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/command_processor.cpp"

ANCHOR = '''  const_cast<volatile uint32_t&>(regs.values[index]) = value;
  if (!regs.GetRegisterInfo(index)) {
'''
NEW = '''  const_cast<volatile uint32_t&>(regs.values[index]) = value;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: which registers are known, worked out once instead of
  // a switch on every write (tools/ios/patch_ios_register_check.py).
  static const std::vector<bool> ios_known_registers = [] {
    std::vector<bool> known(RegisterFile::kRegisterCount);
    for (uint32_t i = 0; i < RegisterFile::kRegisterCount; ++i) {
      known[i] = RegisterFile::GetRegisterInfo(i) != nullptr;
    }
    return known;
  }();
  if (index >= RegisterFile::kRegisterCount || !ios_known_registers[index]) {
#else
  if (!regs.GetRegisterInfo(index)) {
#endif
'''

MEMEXPORT_ANCHOR = '''  if (legacy_readback_memexport_cvar_name_ &&
      rex::cvar::HasNonDefaultValue(legacy_readback_memexport_cvar_name_)) {
'''
MEMEXPORT_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: whether the legacy cvar was given is decided at start;
  // looking it up by name on every draw was 2.3 % of the GPU thread
  // (tools/ios/patch_ios_register_check.py).
  static const bool ios_legacy_given =
      legacy_readback_memexport_cvar_name_ &&
      rex::cvar::HasNonDefaultValue(legacy_readback_memexport_cvar_name_);
  if (ios_legacy_given) {
#else
  if (legacy_readback_memexport_cvar_name_ &&
      rex::cvar::HasNonDefaultValue(legacy_readback_memexport_cvar_name_)) {
#endif
'''

BLOCKS = [
    (F, "known registers from a table", ANCHOR, NEW),
    (F, "the legacy memexport cvar looked up once", MEMEXPORT_ANCHOR, MEMEXPORT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_register_check", BLOCKS))
