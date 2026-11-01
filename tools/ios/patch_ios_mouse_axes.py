#!/usr/bin/env python3
"""
Mouse look on iPad (keyboard and mouse mode, mnk_mouse): the vertical axis can
be switched off, and the mouse is captured only while driving.

    NFSMW_SDK=<sdk> python3 tools/ios/patch_ios_mouse_axes.py            apply
    NFSMW_SDK=<sdk> python3 tools/ios/patch_ios_mouse_axes.py --status
    NFSMW_SDK=<sdk> python3 tools/ios/patch_ios_mouse_axes.py --revert

Touches src/input/mnk/mnk_input_driver.cpp.

The SDK's mouse look moves the right stick both ways. In NFSMW the right
stick's up/down changes gear while driving (the keyboard's Shift/Control),
so moving the mouse up or down shifted gears. A new cvar, mnk_mouse_y
(default true, the SDK's behaviour), leaves the vertical axis out; the iOS
launcher sets it false. The capture itself (relative mode, which SDL turns
into iPadOS pointer lock) already follows SetMouseLookActive, which the game
side calls with "driving" (ios/src/keyboard_context.cpp), so the pointer is
free in menus.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/input/mnk/mnk_input_driver.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_DOUBLE(mnk_sensitivity, 1.0, "Input", "Mouse sensitivity for right stick")
    .range(0.01, 10.0);'''
CVAR_NEW = '''REXCVAR_DEFINE_DOUBLE(mnk_sensitivity, 1.0, "Input", "Mouse sensitivity for right stick")
    .range(0.01, 10.0);
// LOCAL PATCH - iOS: each of the mouse's axes on the right stick can be left
// out; with both off, mnk_mouse only locks the pointer (the game turns its
// camera itself: ios/src/camera_look.cpp; tools/ios/patch_ios_mouse_axes.py).
REXCVAR_DEFINE_BOOL(mnk_mouse_x, true, "Input", "Mouse look moves the right stick left and right");
REXCVAR_DEFINE_BOOL(mnk_mouse_y, true, "Input", "Mouse look moves the right stick up and down");'''

AXIS_ANCHOR = '''    rx += static_cast<int32_t>(double(mouse_dx_) * sensitivity * kBaseScale);
    ry += static_cast<int32_t>(double(-mouse_dy_) * sensitivity * kBaseScale);'''
AXIS_NEW = '''    // LOCAL PATCH - iOS (patch_ios_mouse_axes.py): each axis can be left out.
    if (REXCVAR_GET(mnk_mouse_x)) rx += static_cast<int32_t>(double(mouse_dx_) * sensitivity * kBaseScale);
    if (REXCVAR_GET(mnk_mouse_y)) ry += static_cast<int32_t>(double(-mouse_dy_) * sensitivity * kBaseScale);'''

BLOCKS = [
    (F, "mnk_mouse_x / mnk_mouse_y cvars", CVAR_ANCHOR, CVAR_NEW),
    (F, "each axis behind its cvar", AXIS_ANCHOR, AXIS_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_mouse_axes", BLOCKS))
