#!/usr/bin/env python3
"""
SDL's game window on the phone's own scene, never on an external display's.

    python3 tools/ios/patch_ios_sdl_scene.py            apply
    python3 tools/ios/patch_ios_sdl_scene.py --status
    python3 tools/ios/patch_ios_sdl_scene.py --revert

Touches thirdparty/sdl3/src/video/uikit/SDL_uikitvideo.m.

With AirPlay mirroring (or HDMI) the app has a second window scene, the
external display's. UIKit_GetActiveWindowScene took the first foreground one
it found, so SDL's window could land on the TV: the TV showed the game, the
phone kept the launcher. Scenes whose session role is not Application are
now skipped (the external display gets its own window from the native
renderer).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "thirdparty/sdl3/src/video/uikit/SDL_uikitvideo.m"

ANCHOR = '''        NSSet<UIScene *> *connectedScenes = [UIApplication sharedApplication].connectedScenes;

        // First, try to find an active foreground scene
'''
NEW = '''        // LOCAL PATCH - iOS: only the phone's own scenes, never an external
        // display's (tools/ios/patch_ios_sdl_scene.py).
        NSMutableSet<UIScene *> *connectedScenes = [NSMutableSet set];
        for (UIScene *scene in [UIApplication sharedApplication].connectedScenes) {
            if ([scene.session.role isEqualToString:UIWindowSceneSessionRoleApplication]) {
                [connectedScenes addObject:scene];
            }
        }

        // First, try to find an active foreground scene
'''

BLOCKS = [(FILE, "phone scenes only", ANCHOR, NEW)]

if __name__ == "__main__":
    sys.exit(run("ios_sdl_scene", BLOCKS))
