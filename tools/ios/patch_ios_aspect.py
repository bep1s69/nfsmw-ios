#!/usr/bin/env python3
"""
Let the game see a 4:3 display.

    python3 tools/ios/patch_ios_aspect.py            apply
    python3 tools/ios/patch_ios_aspect.py --status
    python3 tools/ios/patch_ios_aspect.py --revert

Touches src/kernel/xboxkrnl/xboxkrnl_video.cpp.

The game asks the kernel what display it is on (VdQueryVideoMode,
VdQueryVideoFlags), and the SDK answers with the --resolution cvar, so
--resolution=1024x768 describes a 4:3 HD display, which the Xbox 360 offered
(and an iPad's screen is exactly 4:3). But the SDK decides "widescreen" with

    display_width * 3 >= display_height * 4

and for an exact 4:3 mode the two sides are EQUAL: 1024x768 was still
reported as widescreen. Strictly wider than 4:3 is what widescreen means, so
">" instead of ">=", in both places it is computed (VdQueryVideoFlags uses
the same VdQueryVideoMode).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

ANCHOR = '''  video_mode->is_widescreen = display_width * 3 >= display_height * 4;
'''
NEW = '''  // LOCAL PATCH - iOS: strictly wider than 4:3. With ">=" an exact 4:3 mode
  // (1024x768) was reported as widescreen (tools/ios/patch_ios_aspect.py).
  video_mode->is_widescreen = display_width * 3 > display_height * 4;
'''

BLOCKS = [
    ("src/kernel/xboxkrnl/xboxkrnl_video.cpp", "4:3 is not widescreen", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_aspect", BLOCKS))
