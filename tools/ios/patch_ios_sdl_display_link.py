#!/usr/bin/env python3
"""
No idle 80-120 Hz display link from SDL's view controller (iOS).

    python3 tools/ios/patch_ios_sdl_display_link.py            apply
    python3 tools/ios/patch_ios_sdl_display_link.py --status
    python3 tools/ios/patch_ios_sdl_display_link.py --revert

Touches thirdparty/sdl3/src/video/uikit/SDL_uikitviewcontroller.m.


WHY
===

A log of two laps at the 30 and 60 caps on an iPhone (A19, 120 Hz screen):
frames came exactly 30 and 60 a second, yet never one on the cap's grid.
The gaps between shown frames were 25 / 37.5 / 37.5 ms at 30 and
12.5 / 12.5 / 25 ms at 60: the screen ran at 80 Hz, where neither cap fits
(judder), and above the 60 Hz that ios/src/display_rate.mm asks for.

SDL's view controller, on screens over 60 Hz, makes a CADisplayLink in its
init with a range of (2/3 x max, max, max): 80-120 Hz on a 120 Hz iPhone.
It only runs SDL's animation callback, which this app never sets
(SDL_SetiOSAnimationCallback; startAnimation makes a link of its own then,
without stopping this one). So it does nothing but hold the screen at
80 Hz or more and wake the main thread 80-120 times a second, whatever the
cap: display power and judder for nothing.

The link is no longer made in init. The app's own link (display_rate.mm)
alone sets the screen's rate: 60 Hz at the 30 and 60 caps, 120 Hz at 40 and
120.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "thirdparty/sdl3/src/video/uikit/SDL_uikitviewcontroller.m"

LINK_ANCHOR = '''        if (@available(iOS 15.0, tvOS 15.0, *)) {
            const SDL_DisplayMode *mode = SDL_GetDesktopDisplayMode(SDL_GetPrimaryDisplay());
            if (mode && mode->refresh_rate > 60.0f) {
                int frame_rate = (int)mode->refresh_rate;
                displayLink = [CADisplayLink displayLinkWithTarget:self selector:@selector(doLoop:)];
                displayLink.preferredFrameRateRange = CAFrameRateRangeMake((frame_rate * 2) / 3, frame_rate, frame_rate);
                [displayLink addToRunLoop:NSRunLoop.currentRunLoop forMode:NSDefaultRunLoopMode];
            }
        }
'''
LINK_NEW = '''        // LOCAL PATCH - iOS: no idle 80-120 Hz display link: it held the
        // screen at 80 Hz or more whatever the app asked for, and this app
        // sets no animation callback (tools/ios/patch_ios_sdl_display_link.py).
#if 0
        if (@available(iOS 15.0, tvOS 15.0, *)) {
            const SDL_DisplayMode *mode = SDL_GetDesktopDisplayMode(SDL_GetPrimaryDisplay());
            if (mode && mode->refresh_rate > 60.0f) {
                int frame_rate = (int)mode->refresh_rate;
                displayLink = [CADisplayLink displayLinkWithTarget:self selector:@selector(doLoop:)];
                displayLink.preferredFrameRateRange = CAFrameRateRangeMake((frame_rate * 2) / 3, frame_rate, frame_rate);
                [displayLink addToRunLoop:NSRunLoop.currentRunLoop forMode:NSDefaultRunLoopMode];
            }
        }
#endif
'''

BLOCKS = [
    (F, "no idle display link in init", LINK_ANCHOR, LINK_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_sdl_display_link", BLOCKS))
