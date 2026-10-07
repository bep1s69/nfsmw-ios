#!/usr/bin/env python3
"""
The futex waits of the project's patches, on Apple.

    python3 tools/ios/patch_ios_waits.py            apply
    python3 tools/ios/patch_ios_waits.py --status
    python3 tools/ios/patch_ios_waits.py --revert

Touches src/graphics/command_processor.cpp.

Three of the project's patches make threads sleep on a counter instead of
spinning or polling, with the Linux futex:

    parche_espera_anillo   the CP bumps nfsmw_cp_rptr_seq when it publishes its
                           read pointer; the ring-space hook (game_hooks.cpp on
                           iOS) sleeps on it. On Android: CPU ~15x lower.
    parche_anillo_bloques  the same counter, bumped while the ring drains.
    parche_vblank          the CP's flip wait sleeps until the vblank, and the
                           vblank thread until the swap, instead of Sleep(1 ms)
                           polling. That is what keeps a late frame from
                           costing a whole extra vblank.

All of it sits behind #if defined(__linux__). On Apple it compiles to the old
behaviour: no wakes at all, the vblank and swap counters are not even
incremented, and the waits fall back to plain sleeps.

Apple's public equivalent of the futex is os_sync_wait_on_address /
os_sync_wake_by_address_all (<os/os_sync_wait_on_address.h>, iOS 17.4+; the
app requires iOS 26). Same contract: sleep while the 32-bit value at an
address still equals what the caller saw, with a timeout. This adds an
#elif defined(__APPLE__) next to each Linux branch.


WHY THIS EDITS INSIDE OTHER PATCHES' BLOCKS
===========================================

The Linux code is inside the blocks those three patches inserted, so the
Apple branch has to go there too. That would break a re-run of those patches
over this tree, but tools/ios/prepare_sdk.py applies each project patch only
once (see its step 3), and its --status reports that record instead of
re-checking the Android patches' blocks.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/command_processor.cpp"

INCLUDE_ANCHOR = '''// vblank, y el hilo del vblank con el swap (tools/parche_vblank.py).
#if defined(__linux__)
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
#endif
'''
INCLUDE_NEW = '''// vblank, y el hilo del vblank con el swap (tools/parche_vblank.py).
#if defined(__linux__)
#include <linux/futex.h>
#include <sys/syscall.h>
#include <unistd.h>
#elif defined(__APPLE__)
// LOCAL PATCH - iOS: Apple's futex, os_sync_wait_on_address (iOS 17.4+), for
// every wait below (tools/ios/patch_ios_waits.py).
#include <os/os_sync_wait_on_address.h>
#endif
'''

# The read-pointer wake in the CP loop (parche_espera_anillo): 4 spaces.
RPTR_LOOP_ANCHOR = '''#if defined(__linux__)
    syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#endif
'''
RPTR_LOOP_NEW = '''#if defined(__linux__)
    syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#elif defined(__APPLE__)
    // LOCAL PATCH - iOS: wake the ring-space hook (game_hooks.cpp).
    os_sync_wake_by_address_all(&nfsmw_cp_rptr_seq, sizeof(uint32_t),
                                OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
'''

# The same wake while the ring drains (parche_anillo_bloques): 8 spaces.
RPTR_DRAIN_ANCHOR = '''#if defined(__linux__)
        syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#endif
'''
RPTR_DRAIN_NEW = '''#if defined(__linux__)
        syscall(SYS_futex, &nfsmw_cp_rptr_seq, FUTEX_WAKE_PRIVATE, INT_MAX, nullptr, nullptr, 0);
#elif defined(__APPLE__)
        // LOCAL PATCH - iOS: wake the ring-space hook (game_hooks.cpp).
        os_sync_wake_by_address_all(&nfsmw_cp_rptr_seq, sizeof(uint32_t),
                                    OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
'''

SWAP_WAKE_ANCHOR = '''void NfsmwAvisarSwap() {
#if defined(__linux__)
  nfsmw_swap_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_swap_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#endif
'''
SWAP_WAKE_NEW = '''void NfsmwAvisarSwap() {
#if defined(__linux__)
  nfsmw_swap_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_swap_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#elif defined(__APPLE__)
  // LOCAL PATCH - iOS
  nfsmw_swap_seq.fetch_add(1, std::memory_order_release);
  os_sync_wake_by_address_all(&nfsmw_swap_seq, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
'''

SWAP_WAIT_ANCHOR = '''#else
  rex::thread::Sleep(std::chrono::nanoseconds(nanos));
#endif
'''
SWAP_WAIT_NEW = '''#elif defined(__APPLE__)
  // LOCAL PATCH - iOS
  if (nanos > 0) {
    const uint32_t antes = nfsmw_swap_seq.load(std::memory_order_acquire);
    os_sync_wait_on_address_with_timeout(&nfsmw_swap_seq, antes, sizeof(uint32_t),
                                         OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                         OS_CLOCK_MACH_ABSOLUTE_TIME, uint64_t(nanos));
  }
#else
  rex::thread::Sleep(std::chrono::nanoseconds(nanos));
#endif
'''

VBLANK_WAKE_ANCHOR = '''void NfsmwAvisarVblank() {
#if defined(__linux__)
  nfsmw_vblank_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_vblank_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#endif
'''
VBLANK_WAKE_NEW = '''void NfsmwAvisarVblank() {
#if defined(__linux__)
  nfsmw_vblank_seq.fetch_add(1, std::memory_order_release);
  syscall(SYS_futex, reinterpret_cast<uint32_t*>(&nfsmw_vblank_seq), FUTEX_WAKE_PRIVATE, INT_MAX,
          nullptr, nullptr, 0);
#elif defined(__APPLE__)
  // LOCAL PATCH - iOS
  nfsmw_vblank_seq.fetch_add(1, std::memory_order_release);
  os_sync_wake_by_address_all(&nfsmw_vblank_seq, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
#endif
'''

VBLANK_WAIT_ANCHOR = '''#else
  rex::thread::Sleep(tope);
#endif
'''
VBLANK_WAIT_NEW = '''#elif defined(__APPLE__)
  // LOCAL PATCH - iOS
  if (tope.count() > 0) {
    const uint32_t antes = nfsmw_vblank_seq.load(std::memory_order_acquire);
    os_sync_wait_on_address_with_timeout(&nfsmw_vblank_seq, antes, sizeof(uint32_t),
                                         OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                         OS_CLOCK_MACH_ABSOLUTE_TIME,
                                         uint64_t(tope.count()) * 1000000ull);
  }
#else
  rex::thread::Sleep(tope);
#endif
'''

BLOCKS = [
    (F, "include os_sync_wait_on_address.h", INCLUDE_ANCHOR, INCLUDE_NEW),
    (F, "wake the ring hook (CP loop)", RPTR_LOOP_ANCHOR, RPTR_LOOP_NEW),
    (F, "wake the ring hook (ring draining)", RPTR_DRAIN_ANCHOR, RPTR_DRAIN_NEW),
    (F, "swap: count and wake", SWAP_WAKE_ANCHOR, SWAP_WAKE_NEW),
    (F, "swap: wait", SWAP_WAIT_ANCHOR, SWAP_WAIT_NEW),
    (F, "vblank: count and wake", VBLANK_WAKE_ANCHOR, VBLANK_WAKE_NEW),
    (F, "vblank: wait", VBLANK_WAIT_ANCHOR, VBLANK_WAIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_waits", BLOCKS))
