// NFSMW Recompiled (iOS) - the game's render thread waits for queued work
// instead of spinning (see tools/ios/patch_game_queue_wait.py).
//
// dev215 (Stefan, Nov 17: hold 60 fps on the iPhone's efficiency cores; with
// the reflection cuts Low lasted 40 s): the render thread's loop called the
// deferred-call runner again and again with 0 pending entries while the
// world thread was still queueing the frame (Nov 16 profile: ~13 % of that
// thread, sub_823C8290 + its register save/restore + the loop). On the four
// efficiency cores that spin competes with the threads doing the work.
#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_queue_wait, true, "Kernel",
                    "dev215: the game's render thread sleeps (woken by the next queued entry, at most 250 us) "
                    "while its deferred-call queue is empty, instead of spinning");

namespace {
std::mutex lock;
std::condition_variable cv;
std::atomic<uint32_t> published{0};
std::atomic<int> waiting{0};
std::atomic<uint64_t> waits{0}, woken{0};
}  // namespace

extern "C" void nfsmw_queue_wake() {
  published.fetch_add(1, std::memory_order_release);
  if (waiting.load(std::memory_order_acquire)) {
    std::lock_guard<std::mutex> g(lock);
    cv.notify_one();
  }
}

extern "C" void nfsmw_queue_wait(uint8_t* base, uint32_t queue) {
  static const bool on = REXCVAR_GET(nfsmw_queue_wait);
  if (!on || !queue) return;
  const uint32_t seen = published.load(std::memory_order_acquire);
  // Something already queued since the runner looked: no wait.
  if (REX_LOAD_U32(queue + 0) != REX_LOAD_U32(queue + 4)) return;
  waiting.fetch_add(1, std::memory_order_acq_rel);
  bool got = false;
  {
    std::unique_lock<std::mutex> g(lock);
    got = cv.wait_for(g, std::chrono::microseconds(250),
                      [&] { return published.load(std::memory_order_acquire) != seen; });
  }
  waiting.fetch_sub(1, std::memory_order_acq_rel);
  woken.fetch_add(got, std::memory_order_relaxed);
  const uint64_t n = waits.fetch_add(1, std::memory_order_relaxed) + 1;
  if (n % 100000 == 0)
    REXLOG_INFO("[queue-wait] {} waits, {} woken by a new entry (the rest after 250 us)", n,
                woken.load(std::memory_order_relaxed));
}
