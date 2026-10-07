#!/usr/bin/env python3
"""
Let the rexglue CLI write the game's decrypted, decompressed image to a file.

    python3 tools/ios/patch_ios_dump_image.py            apply
    python3 tools/ios/patch_ios_dump_image.py --status
    python3 tools/ios/patch_ios_dump_image.py --revert

Touches src/codegen/project_recompiler.cpp (the host CLI only; nothing that runs
on the device).

    NFSMW_DUMP_IMAGE=/path/image.bin rexglue codegen <manifest>

loads default.xex as the codegen always does, writes the image as mapped at
its base address (0x82000000 for NFSMW) and exits before any analysis, so
nothing is generated and ios/generated/ is left alone.

What for: the game's code is in the generated C++, but its data (strings,
tables, constants) is not. Porting PC mods like Extra Options means finding
the Xbox 360 code that matches each PC address, and the game's own strings
are the way in (tools/ios/find_image.py).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/codegen/project_recompiler.cpp"

INCLUDE_ANCHOR = '''#include "template_registry_internal.h"
'''
INCLUDE_NEW = '''#include "template_registry_internal.h"

// LOCAL PATCH - iOS tooling: NFSMW_DUMP_IMAGE (tools/ios/patch_ios_dump_image.py).
#include <cstdio>
#include <cstdlib>
#include <rex/system/xmemory.h>
'''

DUMP_ANCHOR = '''  auto entry_display_name = std::filesystem::path(targeted[0].config.filePath).filename().string();
'''
DUMP_NEW = '''  // LOCAL PATCH - iOS tooling: write the loaded image and stop, before any
  // analysis or output (tools/ios/patch_ios_dump_image.py).
  if (const char* dump = std::getenv("NFSMW_DUMP_IMAGE")) {
    auto* xex = runtime->kernel_state()->GetExecutableModule()->xex_module();
    const uint32_t base = xex->base_address();
    const uint32_t size = xex->image_size();
    const void* data = runtime->kernel_state()->memory()->TranslateVirtual(base);
    FILE* out = std::fopen(dump, "wb");
    const bool ok = out && data && std::fwrite(data, 1, size, out) == size;
    if (out) {
      std::fclose(out);
    }
    std::fprintf(stderr, "NFSMW_DUMP_IMAGE: %s: base 0x%08X, %u bytes -> %s\\n",
                 ok ? "written" : "FAILED", base, size, dump);
    std::exit(ok ? 0 : 1);
  }

  auto entry_display_name = std::filesystem::path(targeted[0].config.filePath).filename().string();
'''

BLOCKS = [
    (F, "includes for the image dump", INCLUDE_ANCHOR, INCLUDE_NEW),
    (F, "NFSMW_DUMP_IMAGE", DUMP_ANCHOR, DUMP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_dump_image", BLOCKS))
