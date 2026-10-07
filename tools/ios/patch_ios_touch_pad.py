#!/usr/bin/env python3
"""
The touch controls' gamepad never takes a player slot: it always plays as
player 1, together with whatever real controller is connected.

    python3 tools/ios/patch_ios_touch_pad.py            apply
    python3 tools/ios/patch_ios_touch_pad.py --status
    python3 tools/ios/patch_ios_touch_pad.py --revert

Touches src/input/sdl/sdl_input_driver.cpp.


WHAT HAPPENED
=============

The touch controls (ios/src/touch_controls.mm) feed the game through an SDL
virtual gamepad, "NFSMW touch controls", attached as soon as the game's window
is up. The SDK gives each real pad a player slot in connection order. On an
iPad with an Xbox controller, the virtual pad sometimes connected first: it
became player 1 and the Xbox controller player 2.

Player 2 has no signed-in profile (the SDK signs in only player 1). Playing
with the controller, NFSMW asked player 2 to sign in to Xbox Live, and
creating a career alias softlocked at "Do you want to save the alias?": there
was no profile to save it for. With only the touch pad (an iPhone), or with
the controller connecting first, all was well.

The SDK already has the idea this needs: "synthetic" devices (keyboard and
mouse emulation) never take a slot and always feed player 1
(SlotAssignment::OnDevicesChanged). The touch pad is one of those: an
emulation, on the same screen as the player. So the SDL driver now reports it
as synthetic, and the real controller is player 1 however they connect.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/input/sdl/sdl_input_driver.cpp"

ANCHOR = '''    info.guid = guid_text;
    info.synthetic = false;
    out.push_back(info);
'''
NEW = '''    info.guid = guid_text;
    info.synthetic = false;
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: the touch controls' virtual pad plays as player 1 and
    // never takes a slot from a real controller (tools/ios/patch_ios_touch_pad.py).
    if (info.name == "NFSMW touch controls") {
      info.synthetic = true;
    }
#endif
    out.push_back(info);
'''

BLOCKS = [
    (F, "the touch pad is a synthetic device", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_touch_pad", BLOCKS))
