#!/usr/bin/env python3
"""
Keyboard controls: Shift, Ctrl and Alt as keys of their own.

    python3 tools/ios/patch_ios_mnk_modifiers.py            apply
    python3 tools/ios/patch_ios_mnk_modifiers.py --status
    python3 tools/ios/patch_ios_mnk_modifiers.py --revert

Touches src/input/mnk/mnk_input_driver.cpp.

The SDK's keyboard driver matched modifiers EXACTLY: "Up" was silent while
Shift was held, and a bind of a bare "Shift" could never fire (holding it
makes the live mask non-zero). That was to let the D-pad share the arrows
("Shift+Up"). NFSMW's PC-style layout uses Shift and Ctrl to change gear and
Alt for nitrous, held WHILE steering with the arrows. So a bind needs the
modifiers it names, and ignores the others: "Up" works with Shift held, "Shift"
alone fires, "Shift+Up" still needs Shift.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

ANCHOR = '''  uint8_t want = TakeModifiers(token);
  if (want != live_mods) {
    return false;
  }
'''
NEW = '''  uint8_t want = TakeModifiers(token);
  // LOCAL PATCH - iOS: the modifiers a bind names must be held; the others are
  // ignored, so bare Shift/Ctrl/Alt binds fire and do not mute the rest
  // (tools/ios/patch_ios_mnk_modifiers.py).
  if ((live_mods & want) != want) {
    return false;
  }
'''

BLOCKS = [
    ("src/input/mnk/mnk_input_driver.cpp", "modifiers held, others ignored", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_mnk_modifiers", BLOCKS))
