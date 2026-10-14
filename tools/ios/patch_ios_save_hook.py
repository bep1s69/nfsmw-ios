#!/usr/bin/env python3
"""
Tell the app when the game creates or opens a save.

    python3 tools/ios/patch_ios_save_hook.py            apply
    python3 tools/ios/patch_ios_save_hook.py --status
    python3 tools/ios/patch_ios_save_hook.py --revert

Touches src/kernel/xam/xam_content.cpp. Needs patch_ios_save_log first (it
goes right after its log line).

The SDK exports a function pointer, rex_ios_save_event, that the app sets
(ios/src/game_pool.cpp). Every save the game creates (to write it) or opens
(to read it) calls it with the save's file name and whether it was created.
The larger record pool keeps its extra entries outside the game's own data,
so they are not in the save file: the app writes them next to it when the
game saves, and puts them back when that save's data is loaded (cars of a
career saved with Black Edition on came back invisible).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/kernel/xam/xam_content.cpp"

CALL_ANCHOR = '''                                                         : "nothing done",
                uint32_t(result));
'''
CALL_NEW = '''                                                         : "nothing done",
                uint32_t(result));
    // LOCAL PATCH - iOS: the app hears of it (tools/ios/patch_ios_save_hook.py).
    if (rex_ios_save_event && result == 0 && disposition != kDispositionState::Unknown) {
      rex_ios_save_event(content_data.file_name().c_str(), disposition == kDispositionState::Create);
    }
'''

INCLUDE_ANCHOR = '''enum class kDispositionState : uint32_t { Unknown = 0, Create = 1, Open = 2 };
'''
INCLUDE_NEW = '''// LOCAL PATCH - iOS: set by the app; called when the game creates (true) or
// opens (false) a save, with its file name (tools/ios/patch_ios_save_hook.py).
extern "C" __attribute__((visibility("default"))) void (*rex_ios_save_event)(const char* name,
                                                                              bool created) = nullptr;

enum class kDispositionState : uint32_t { Unknown = 0, Create = 1, Open = 2 };
'''

BLOCKS = [
    (FILE, "the save hook pointer", INCLUDE_ANCHOR, INCLUDE_NEW),
    (FILE, "the save hook called", CALL_ANCHOR, CALL_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_save_hook", BLOCKS))
