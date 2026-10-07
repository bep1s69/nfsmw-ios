#!/usr/bin/env python3
"""
REX_PLATFORM_IOS: tell iOS apart from macOS inside the SDK.

    python3 tools/ios/patch_ios_platform.py            apply
    python3 tools/ios/patch_ios_platform.py --status
    python3 tools/ios/patch_ios_platform.py --revert

Touches include/rex/platform.h.

On iOS TARGET_OS_MAC is also 1 (it means "any Darwin"), so the SDK already
sets REX_PLATFORM_MAC and takes the whole macOS path: CAMetalLayer, MoltenVK,
16 KB pages, the arm64 Darwin signal handler. That is what we want. But in a
few places iOS is NOT macOS (where the libraries live, no desktop windows, the
sandbox), and those need their own flag. REX_PLATFORM_IOS is a SUB-FLAG: when
it is 1, REX_PLATFORM_MAC is 1 too.

Like the other REX_PLATFORM_* it is always defined (0 or 1), so it can be used
in #if and static_assert. patch_ios_cmake.py also sets it on the compiler
command line, for files that test it before including platform.h.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FLAG_ANCHOR = '''#if defined(TARGET_OS_MAC) && TARGET_OS_MAC
#define REX_PLATFORM_MAC 1
'''
FLAG_NEW = '''#if defined(TARGET_OS_MAC) && TARGET_OS_MAC
#define REX_PLATFORM_MAC 1
// LOCAL PATCH - iOS: sub-flag of REX_PLATFORM_MAC (TARGET_OS_MAC is 1 on iOS
// too). For the few things where iOS is not macOS.
#if defined(TARGET_OS_IOS) && TARGET_OS_IOS
#define REX_PLATFORM_IOS 1
#endif
'''

ZERO_ANCHOR = '''#ifndef REX_PLATFORM_MAC
#define REX_PLATFORM_MAC 0
#endif
'''
ZERO_NEW = '''#ifndef REX_PLATFORM_MAC
#define REX_PLATFORM_MAC 0
#endif
// LOCAL PATCH - iOS
#ifndef REX_PLATFORM_IOS
#define REX_PLATFORM_IOS 0
#endif
'''

BLOCKS = [
    ("include/rex/platform.h", "define REX_PLATFORM_IOS", FLAG_ANCHOR, FLAG_NEW),
    ("include/rex/platform.h", "REX_PLATFORM_IOS is 0 elsewhere", ZERO_ANCHOR, ZERO_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_platform", BLOCKS))
