// NFSMW Recompiled (iOS) - the frame hand-off waits sleep until the hand-off
//
// USA edition addresses. Edits to the generated code:
// tools/ios/patch_game_handoff_wait.py.
//
// THE WAITS
//
// The game hands each gameplay frame from its main loop to its render thread
// through one word, 0x82A2CF40 (Oct 28, TECHNICAL "Render hand-off found"):
// the main loop sets it to 1 (sub_82441EF0), the render thread waits while it
// is 0, draws, and sets it back to 0 (sub_82441B60); the main loop waits while
// it is 1 (sub_82441DB0). Both waits call Sleep(0) (sub_8262D790) in a loop,
// which the SDK turns into a 100 us host sleep: ~6,900 wake-ups a second on
// the two frame threads on the iPad (dev50 System Trace, Nov 4), each doing
// ~2 us of work. A fixed 400 us sleep cut whole-device drain by 4.4 %/h
// (dev54 probe), but any fixed length depends on the device's speed.
//
// THE FIX
//
// Each wait sleeps on the word itself (os_sync_wait_on_address) and both
// writers wake it right after their store, so a waiter runs again as soon as
// the hand-off happens, on any device. A store that lands between the
// waiter's read and its sleep makes the kernel's compare fail and the wait
// return at once. A writer not covered here (none found: the only stores to
// that address are these two) still ends a wait after
// nfsmw_handoff_wait_us, a safety net, never a lost frame.

#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <os/os_sync_wait_on_address.h>
#include <rex/cvar.h>
#include <rex/logging.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(nfsmw_handoff_wait, true, "Game",
                    "Frame hand-off waits sleep until the other thread changes the hand-off word "
                    "(false: the game's Sleep(0) polling; restart required)");
REXCVAR_DEFINE_INT32(nfsmw_handoff_wait_us, 2000, "Game",
                     "Safety-net timeout of one frame hand-off wait in microseconds (100-50000)");

namespace {
constexpr uint32_t kHandoffWord = 0x82A2CF40;

std::atomic<uint64_t> waits{0}, timeouts{0}, wakes{0};
std::atomic<int64_t> since_ms{0};

int64_t NowMs() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

void Report() {
  const int64_t now = NowMs();
  int64_t since = since_ms.load(std::memory_order_relaxed);
  if (since == 0) {
    since_ms.compare_exchange_strong(since, now);
    return;
  }
  if (now - since < 10000 || !since_ms.compare_exchange_strong(since, now)) {
    return;
  }
  const uint64_t w = waits.exchange(0), t = timeouts.exchange(0), k = wakes.exchange(0);
  REXLOG_INFO("[handoff-wait] 10 s: {} waits ({:.0f}/s), {} timed out, {} wakes sent", w,
              w * 1000.0 / double(now - since), t, k);
}
}  // namespace

// Called in place of the Sleep(0) of a hand-off wait loop. Returns false when
// off, and the caller then sleeps as the game did. The loop reads the word
// again afterwards, as it always did.
extern "C" bool nfsmw_handoff_wait(uint8_t* base, uint32_t waiting_value) {
  static const bool on = REXCVAR_GET(nfsmw_handoff_wait);
  if (!on) {
    return false;
  }
  static const bool said = [] {
    REXLOG_INFO("[handoff-wait] on: frame hand-off waits sleep on 0x{:08X} (safety net {} us)",
                kHandoffWord, REXCVAR_GET(nfsmw_handoff_wait_us));
    return true;
  }();
  (void)said;
  static const uint64_t timeout_ns =
      uint64_t(std::clamp<int32_t>(REXCVAR_GET(nfsmw_handoff_wait_us), 100, 50000)) * 1000;
  // Guest memory is big-endian: compare the word's raw bytes.
  void* word = base + kHandoffWord;
  const uint32_t raw = __builtin_bswap32(waiting_value);
  const int woke = os_sync_wait_on_address_with_timeout(word, raw, sizeof(uint32_t),
                                                        OS_SYNC_WAIT_ON_ADDRESS_NONE,
                                                        OS_CLOCK_MACH_ABSOLUTE_TIME, timeout_ns);
  waits.fetch_add(1, std::memory_order_relaxed);
  if (woke < 0 && errno == ETIMEDOUT) {
    timeouts.fetch_add(1, std::memory_order_relaxed);
  }
  Report();
  return true;
}

// Called right after each of the game's stores to the hand-off word.
extern "C" void nfsmw_handoff_wake(uint8_t* base) {
  static const bool on = REXCVAR_GET(nfsmw_handoff_wait);
  if (!on) {
    return;
  }
  os_sync_wake_by_address_all(base + kHandoffWord, sizeof(uint32_t), OS_SYNC_WAKE_BY_ADDRESS_NONE);
  wakes.fetch_add(1, std::memory_order_relaxed);
}
