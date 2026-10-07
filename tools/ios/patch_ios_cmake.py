#!/usr/bin/env python3
"""
What the SDK's CMake has to do differently when building for iOS.

    python3 tools/ios/patch_ios_cmake.py            apply
    python3 tools/ios/patch_ios_cmake.py --status
    python3 tools/ios/patch_ios_cmake.py --revert

Touches CMakeLists.txt and thirdparty/CMakeLists.txt.

With CMAKE_SYSTEM_NAME=iOS, CMake sets both APPLE and IOS. Almost everything
under APPLE applies (SDL with Metal, the OBJC languages), except:

  - The Vulkan loader and MoltenVK from the submodules. On macOS they are
    built and placed next to the executable. Not on iOS: the desktop loader is
    pointless (no ICDs to choose from, MoltenVK is the only driver), and
    MoltenVK builds with its own Xcode project, not add_subdirectory. The app
    ships the MoltenVK.xcframework from Khronos' release of the SAME version
    the submodule pins (v1.4.1), downloaded by tools/ios/prepare_sdk.py and
    packaged by ios/CMakeLists.txt.

  - REX_PLATFORM_IOS=1 on the compiler command line, like the SDK already does
    with REX_PLATFORM_MAC=1. platform.h defines it too (patch_ios_platform),
    but some files test it before including platform.h (memory_posix.cpp).
    And iOS gets its own output folder, out/ios-arm64, apart from macOS's.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

MVK_ANCHOR = '''    if(APPLE)
        # Build the loader and MoltenVK revisions shipped by the pinned SDK.
'''
MVK_NEW = '''    # LOCAL PATCH - iOS: neither the loader nor MoltenVK from the submodules;
    # the app ships the MoltenVK.xcframework of the same version
    # (tools/ios/prepare_sdk.py).
    if(APPLE AND NOT IOS)
        # Build the loader and MoltenVK revisions shipped by the pinned SDK.
'''

DEF_ANCHOR = '''        set(REX_PLATFORM "mac-${REX_TARGET_PROCESSOR}")
    endif()
    add_compile_definitions(REX_PLATFORM_MAC=1)
'''
DEF_NEW = '''        set(REX_PLATFORM "mac-${REX_TARGET_PROCESSOR}")
    endif()
    add_compile_definitions(REX_PLATFORM_MAC=1)
    # LOCAL PATCH - iOS: REX_PLATFORM_IOS from the command line too, like
    # REX_PLATFORM_MAC. Some files test it BEFORE including rex/platform.h
    # (memory_posix.cpp), and there only what CMake sets exists. Plus its own
    # output folder (out/ios-arm64), apart from macOS's.
    if(IOS)
        add_compile_definitions(REX_PLATFORM_IOS=1)
        set(REX_PLATFORM "ios-${REX_TARGET_PROCESSOR}")
    endif()
'''

BLOCKS = [
    ("thirdparty/CMakeLists.txt", "no loader or MoltenVK from the submodules", MVK_ANCHOR,
     MVK_NEW),
    ("CMakeLists.txt", "REX_PLATFORM_IOS=1 and platform ios-arm64", DEF_ANCHOR, DEF_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cmake", BLOCKS))
