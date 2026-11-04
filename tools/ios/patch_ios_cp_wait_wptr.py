#!/usr/bin/env python3
"""
The command processor's WAIT_REG_MEM also wakes when the game submits more
commands, not only at the vblank or after its 1 ms lap (cvar
ios_cp_wait_wptr, default true; false = the vblank-only wait as before), and
counts how its waits end ("[cp-wait-wake]" every 10 s).

    python3 tools/ios/patch_ios_cp_wait_wptr.py            apply
    python3 tools/ios/patch_ios_cp_wait_wptr.py --status
    python3 tools/ios/patch_ios_cp_wait_wptr.py --revert

Touches src/graphics/command_processor.cpp.


WHY
===

November 4 (docs/TECHNICAL.md), dev57 iPad census: every WAIT_REG_MEM lap is
the same wait, memory word 0x1FCA5004 (endian 2) == 0 while it reads 1,
~580-840 laps a second, each ended by the 1 ms cap: the CP waits for the
game's CPU side to clear that word. The CPU side most likely clears it around
its next submission (a write of CP_RB_WPTR); waking the wait on those writes
lets the CP re-check then instead of up to 1 ms later. An early wake only
costs a re-check; the 1 ms lap stays as the safety net.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/graphics/command_processor.cpp"

CVAR_ANCHOR = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_census.py).
REXCVAR_DEFINE_BOOL(ios_cp_wait_census, false, "GPU",'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py).
REXCVAR_DEFINE_BOOL(ios_cp_wait_wptr, true, "GPU",
                    "iOS: WAIT_REG_MEM also wakes when the game submits commands (false: vblank "
                    "or its 1 ms lap only)");
''' + CVAR_ANCHOR

SEQ_ANCHOR = '''void CommandProcessor::UpdateWritePointer(uint32_t value) {
  write_ptr_index_ = value;
  write_ptr_index_event_->Set();
}
'''
SEQ_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py): one sequence the
// WAIT_REG_MEM wait sleeps on, bumped by every vblank and every submission.
std::atomic<uint32_t> ios_cp_wake_seq{0};
static void IosCpWake() {
  ios_cp_wake_seq.fetch_add(1, std::memory_order_release);
#if defined(__APPLE__)
  os_sync_wake_by_address_all(&ios_cp_wake_seq, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
}
static void IosCpWaitWake(uint32_t seen, std::chrono::milliseconds cap) {
  static uint64_t waits = 0, woken = 0, timeouts = 0;
  static auto since = std::chrono::steady_clock::now();
  ++waits;
#if defined(__APPLE__)
  if (cap.count() > 0) {
    const int r = os_sync_wait_on_address_with_timeout(&ios_cp_wake_seq, seen, sizeof(uint32_t),
                                                       OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                                       OS_CLOCK_MACH_ABSOLUTE_TIME,
                                                       uint64_t(cap.count()) * 1000000ull);
    if (r < 0 && errno == ETIMEDOUT) {
      ++timeouts;
    } else {
      ++woken;
    }
  }
#else
  rex::thread::Sleep(cap);
#endif
  const auto now = std::chrono::steady_clock::now();
  if (now - since >= std::chrono::seconds(10)) {
    REXGPU_INFO("[cp-wait-wake] 10 s: {} WAIT_REG_MEM waits, {} woken (vblank or submission), {} "
                "timed out", waits, woken, timeouts);
    waits = woken = timeouts = 0;
    since = now;
  }
}

void CommandProcessor::UpdateWritePointer(uint32_t value) {
  write_ptr_index_ = value;
  write_ptr_index_event_->Set();
  IosCpWake();  // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py)
}
'''

VB_ANCHOR = '''  // LOCAL PATCH - iOS
  nfsmw_vblank_seq.fetch_add(1, std::memory_order_release);
  os_sync_wake_by_address_all(&nfsmw_vblank_seq, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
'''
VB_NEW = VB_ANCHOR + '''  IosCpWake();  // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py)
'''

LOOP_ANCHOR = '''  do {
    uint32_t value = 0;
    if (is_memory) {'''
LOOP_NEW = '''  do {
    // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py): the sequence
    // before the check, so a wake between the check and the wait is not lost.
    const uint32_t ios_seq_seen = ios_cp_wake_seq.load(std::memory_order_acquire);
    uint32_t value = 0;
    if (is_memory) {'''

WAIT_ANCHOR = '''          NfsmwEsperarVblank(std::chrono::milliseconds(wait / 0x100));
'''
WAIT_NEW = '''          // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_wptr.py)
          if (REXCVAR_GET(ios_cp_wait_wptr)) {
            IosCpWaitWake(ios_seq_seen, std::chrono::milliseconds(wait / 0x100));
          } else {
            NfsmwEsperarVblank(std::chrono::milliseconds(wait / 0x100));
          }
'''

INC_ANCHOR = "#include <tuple>  // LOCAL PATCH - iOS (patch_ios_cp_wait_census.py)\n"
INC_NEW = INC_ANCHOR + "#include <cerrno>  // LOCAL PATCH - iOS (patch_ios_cp_wait_wptr.py)\n"

BLOCKS = [
    (FILE, "<cerrno>", INC_ANCHOR, INC_NEW),
    (FILE, "the ios_cp_wait_wptr cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "the wake sequence, bumped by submissions", SEQ_ANCHOR, SEQ_NEW),
    (FILE, "the wake sequence, bumped by vblanks", VB_ANCHOR, VB_NEW),
    (FILE, "the sequence read before the check", LOOP_ANCHOR, LOOP_NEW),
    (FILE, "the wait on the sequence", WAIT_ANCHOR, WAIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cp_wait_wptr", BLOCKS))
