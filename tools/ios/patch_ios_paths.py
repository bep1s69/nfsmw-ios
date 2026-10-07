#!/usr/bin/env python3
"""
Where the SDK looks for its libraries on iOS: the GPU plugin and MoltenVK.

    python3 tools/ios/patch_ios_paths.py            apply
    python3 tools/ios/patch_ios_paths.py --status
    python3 tools/ios/patch_ios_paths.py --revert

Touches two SDK files:
    src/core/filesystem_posix.cpp     GetExecutableFolder() on iOS
    src/ui/vulkan/vulkan_instance.cpp MoltenVK.framework as the first candidate


THE PROBLEM: LIVECONTAINER
==========================

The SDK looks for the GPU plugin (librexgpu-xenos.dylib) in
GetExecutableFolder(), which on Apple is the folder of _NSGetExecutablePath().
In a normal app that is the .app. But the app runs inside LiveContainer, which
loads the app's executable INTO ITS OWN PROCESS: _NSGetExecutablePath()
returns LiveContainer's executable, and the plugin would be looked for in ITS
bundle.

Same problem as Android, where /proc/self/exe is app_process, and the same fix
as android_main.cpp (CarpetaDeLasLibrerias): ask dladdr() where THIS library
is loaded. This function lives in librexruntime.dylib, which sits in
<app>.app/Frameworks/, and librexgpu-xenos.dylib and MoltenVK.framework are
right there too (see ios/CMakeLists.txt). So GetExecutableFolder() becomes
that folder, and the plugin loader finds the plugin with no further changes.
It works the same without LiveContainer.

Anything else that uses GetExecutableFolder() (looking for an ISO next to the
executable, say) will look in Frameworks/ and find nothing; on iOS the app
always passes explicit paths (--game_data_root, --user_data_root).


MOLTENVK
========

On macOS the SDK looks for a Vulkan loader (libvulkan) or libMoltenVK.dylib in
an installed Vulkan SDK. On iOS nothing is installed: MoltenVK ships inside the
app as MoltenVK.framework and is loader and driver at once (it exports
vkGetInstanceProcAddr). It goes first in the list, by absolute path.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

# ---------------------------------------------------------------------------
#  src/core/filesystem_posix.cpp
# ---------------------------------------------------------------------------
DLFCN_ANCHOR = '''#if defined(__APPLE__)
#include <mach-o/dyld.h>
#endif
'''
DLFCN_NEW = '''#if defined(__APPLE__)
#include <mach-o/dyld.h>
#endif
// LOCAL PATCH - iOS: GetExecutableFolder() through dladdr (see below).
// Unconditional: rex/platform.h is not included yet here (REX_PLATFORM_IOS
// would read 0), and dlfcn.h exists on every POSIX system.
#include <dlfcn.h>
'''

FOLDER_ANCHOR = '''std::filesystem::path GetExecutableFolder() {
#if REX_PLATFORM_ANDROID
'''
FOLDER_NEW = '''std::filesystem::path GetExecutableFolder() {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the folder of THIS library (<app>.app/Frameworks), not
  // the executable's. Inside LiveContainer the process executable is
  // LiveContainer's, not the app's. librexgpu-xenos.dylib and
  // MoltenVK.framework are there too (ios/CMakeLists.txt).
  Dl_info info{};
  if (dladdr(reinterpret_cast<const void*>(&GetExecutableFolder), &info) && info.dli_fname) {
    return std::filesystem::path(info.dli_fname).parent_path();
  }
#endif
#if REX_PLATFORM_ANDROID
'''

# ---------------------------------------------------------------------------
#  src/ui/vulkan/vulkan_instance.cpp
# ---------------------------------------------------------------------------
# After parche_turnip's block, not before it: Turnip anchors on the
# vulkan_moltenvk.h include. With this block between that include and
# Turnip's, re-running the Android patches made Turnip miss its own block and
# insert it again, then this one did too: both ended up duplicated.
INCLUDE_ANCHOR = '''#if REX_PLATFORM_ANDROID && defined(REX_HAS_ADRENOTOOLS)
#include <dlfcn.h>
#include <adrenotools/driver.h>
#endif
'''
INCLUDE_NEW = '''#if REX_PLATFORM_ANDROID && defined(REX_HAS_ADRENOTOOLS)
#include <dlfcn.h>
#include <adrenotools/driver.h>
#endif
// LOCAL PATCH - iOS: GetExecutableFolder()
#if REX_PLATFORM_IOS
#include <rex/filesystem.h>
#endif
'''

MVK_ANCHOR = '''  std::vector<std::filesystem::path> loader_candidates = macos_runtime_paths.loader_candidates;
'''
MVK_NEW = '''  std::vector<std::filesystem::path> loader_candidates = macos_runtime_paths.loader_candidates;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: MoltenVK ships inside the app, next to librexruntime
  // (GetExecutableFolder() is <app>.app/Frameworks on iOS). Before anything.
  loader_candidates.insert(loader_candidates.begin(),
                           rex::filesystem::GetExecutableFolder() / "MoltenVK.framework" /
                               "MoltenVK");
#endif
'''

BLOCKS = [
    ("src/core/filesystem_posix.cpp", "include dlfcn.h", DLFCN_ANCHOR, DLFCN_NEW),
    ("src/core/filesystem_posix.cpp", "GetExecutableFolder() is Frameworks/", FOLDER_ANCHOR,
     FOLDER_NEW),
    ("src/ui/vulkan/vulkan_instance.cpp", "include rex/filesystem.h", INCLUDE_ANCHOR,
     INCLUDE_NEW),
    ("src/ui/vulkan/vulkan_instance.cpp", "MoltenVK.framework first", MVK_ANCHOR, MVK_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_paths", BLOCKS))
