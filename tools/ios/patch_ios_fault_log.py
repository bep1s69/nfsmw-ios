#!/usr/bin/env python3
"""
Stop a repeating guest fault from flooding the log.

    python3 tools/ios/patch_ios_fault_log.py            apply
    python3 tools/ios/patch_ios_fault_log.py --status
    python3 tools/ios/patch_ios_fault_log.py --revert

Touches src/system/xmemory.cpp.


WHAT HAPPENED
=============

Starting the career on an iPad M4 froze the game (the menu music kept
playing). One guest thread was reading through a null pointer, null + 0x14,
over and over: the same thread, the same registers, ~1,500 times a second.
Each time, Memory::AccessViolationCallback logged "Unhandled guest access
violation" plus parche_diagnostico's 5-line dump of the thread. That wrote
~100 MB of log in under 4 seconds, and the log's rotation threw away the
moment the fault STARTED, which is the one part that mattered.

This keeps the log useful without hiding anything:

  - the same fault (same guest address, same host thread) back to back is
    logged in full only the first 3 times;
  - after that, one short line at 10, 100, 1,000, ... repeats, with the count;
  - a different fault is logged in full again.

What the callback does with the fault (return false) does not change.


A NOTE ON ONE BLOCK
===================

The closing brace goes right after parche_diagnostico's dump, inside the text
that patch inserted. As with patch_ios_waits, that is safe only because
tools/ios/prepare_sdk.py applies the project patches once.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/system/xmemory.cpp"

OPEN_ANCHOR = '''  if (!heap || heap->heap_type() != memory::HeapType::kGuestPhysical) {
    REXSYS_ERROR(
        "Unhandled guest access violation: {} of guest 0x{:08X} (host 0x{:016X}) on thread 0x{:X}",
'''
OPEN_NEW = '''  if (!heap || heap->heap_type() != memory::HeapType::kGuestPhysical) {
    // LOCAL PATCH - iOS: the same fault back to back is logged in full only
    // the first 3 times, then one line at 10, 100, 1000... repeats
    // (tools/ios/patch_ios_fault_log.py). A stuck guest thread logged ~1,500
    // a second, and the rotation lost the moment it started.
    static std::mutex ios_fault_mutex;
    static uint32_t ios_fault_address = 0;
    static uint32_t ios_fault_thread = 0;
    static uint64_t ios_fault_count = 0;
    bool ios_log_in_full = true;
    {
      std::lock_guard<std::mutex> ios_lock(ios_fault_mutex);
      const uint32_t thread_id = rex::thread::current_thread_id();
      if (virtual_address == ios_fault_address && thread_id == ios_fault_thread) {
        ++ios_fault_count;
      } else {
        ios_fault_address = virtual_address;
        ios_fault_thread = thread_id;
        ios_fault_count = 1;
      }
      if (ios_fault_count > 3) {
        ios_log_in_full = false;
        uint64_t power = 10;
        while (power < ios_fault_count) {
          power *= 10;
        }
        if (power == ios_fault_count) {
          REXSYS_ERROR("Unhandled guest access violation: {} of guest 0x{:08X} on thread 0x{:X}, "
                       "repeated {} times in a row",
                       is_write ? "write" : "read", virtual_address, thread_id, ios_fault_count);
        }
      }
    }
    if (ios_log_in_full) {
    REXSYS_ERROR(
        "Unhandled guest access violation: {} of guest 0x{:08X} (host 0x{:016X}) on thread 0x{:X}",
'''

CLOSE_ANCHOR = '''    // ======================= fin del parche local ==========================

    return false;
  }
'''
CLOSE_NEW = '''    // ======================= fin del parche local ==========================
    }  // LOCAL PATCH - iOS: if (ios_log_in_full)

    return false;
  }
'''

BLOCKS = [
    (F, "log a repeating fault only now and then", OPEN_ANCHOR, OPEN_NEW),
    (F, "close the full-log block", CLOSE_ANCHOR, CLOSE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_fault_log", BLOCKS))
