#!/usr/bin/env python3
"""
SDL's game window on the phone's own scene, never on an external display's.

    python3 tools/ios/patch_ios_sdl_scene.py            apply
    python3 tools/ios/patch_ios_sdl_scene.py --status
    python3 tools/ios/patch_ios_sdl_scene.py --revert

Touches thirdparty/sdl3/src/video/uikit/SDL_uikitvideo.m and
SDL_uikitappdelegate.m.

With AirPlay mirroring (or HDMI) the app has a second window scene, the
external display's. UIKit_GetActiveWindowScene took the first foreground one
it found, so SDL's window could land on the TV: the TV showed the game, the
phone kept the launcher. Scenes on another screen than the phone's are now
skipped (their session role is not enough: under LiveContainer, mirroring) (the external display gets its own window from the native
renderer).

SDL's app delegate answered every scene session with its own scene delegate,
whatever its role. iOS 17-26 offer an external display (HDMI, USB-C, AirPlay)
to the app delegate as a session of the external display role: SDL's delegate
took it, put its launch window on the TV and called main() a second time,
inside the first (the second launcher window launcher.mm hides afterwards).
It now answers only for the application role; for other roles it returns the
configuration UIKit made from Info.plist's scene manifest, which names the
app's own delegate for the external display (ios/src/external_display.mm).
Without a manifest entry that configuration has no delegate and iOS mirrors
the phone. iOS 27 offers an external display only to a registered scene
accessory and does not ask the app delegate. +nfsmwOtherRolesFromInfoPlist
lets the app see that this patch is in (its log says when it is not).
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
            if ([scene isKindOfClass:[UIWindowScene class]] && ((UIWindowScene *)scene).screen == [UIScreen mainScreen]) {
                [connectedScenes addObject:scene];
            }
        }

        // First, try to find an active foreground scene
'''

DELEGATE = "thirdparty/sdl3/src/video/uikit/SDL_uikitappdelegate.m"

DELEGATE_ANCHOR = '''    // This doesn't appear to be called, but it needs to be implemented to signal that we support the UIScene life cycle
    UISceneConfiguration *config = [[UISceneConfiguration alloc] initWithName:@"SDLSceneConfiguration" sessionRole:connectingSceneSession.role];
'''
DELEGATE_NEW = '''    // LOCAL PATCH - iOS: the application role only. An external display's
    // session (iOS 17-26) gets the configuration from Info.plist's scene
    // manifest: the app's own delegate, or none (mirroring). SDL's delegate
    // on it called main() again (tools/ios/patch_ios_sdl_scene.py).
    if (![connectingSceneSession.role isEqualToString:UIWindowSceneSessionRoleApplication]) {
        return connectingSceneSession.configuration;
    }
    // This doesn't appear to be called, but it needs to be implemented to signal that we support the UIScene life cycle
    UISceneConfiguration *config = [[UISceneConfiguration alloc] initWithName:@"SDLSceneConfiguration" sessionRole:connectingSceneSession.role];
'''

MARKER_ANCHOR = '''+ (NSString *)getSceneDelegateClassName
{
    return @"SDLUIKitSceneDelegate";
}
'''
MARKER_NEW = '''+ (NSString *)getSceneDelegateClassName
{
    return @"SDLUIKitSceneDelegate";
}

// LOCAL PATCH - iOS: the app's check that scene roles other than the
// application's come from Info.plist (tools/ios/patch_ios_sdl_scene.py).
+ (BOOL)nfsmwOtherRolesFromInfoPlist
{
    return YES;
}
'''

BLOCKS = [
    (FILE, "phone scenes only", ANCHOR, NEW),
    (DELEGATE, "app delegate: other roles from Info.plist", DELEGATE_ANCHOR, DELEGATE_NEW),
    (DELEGATE, "app delegate: patch marker", MARKER_ANCHOR, MARKER_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_sdl_scene", BLOCKS))
