// NFSMW Recompiled (iOS) - a job's waiter that cannot miss the job's end
//
// USA edition addresses.
//
// THE HANG
//
// A black-screen hang at boot (2026-10-13, nfsmw_boot_hang.log): the loader
// thread waited for a job it had queued, the worker that ran it waited for
// more work, and nothing moved again. The semaphore trace showed why, within
// 12 microseconds: the loader signalled the worker (R 0xF8000044), the worker
// woke, ran the job and went back to sleep (w/W 0xF8000044), and only then did
// the loader start waiting for "done" (W 0xF800004C), which had already been
// signalled to nobody.
//
// sub_8261D610 is that wait: WaitForJob(job, deadline). It reads the job's
// result word (job+4) and, while it is 0, takes the worker's lock (+156) and
// waits on its "done" condition (+200). The worker (sub_8261EA18) writes the
// result and broadcasts "done" without that lock, so a job that ends between
// the read and the wait is never seen: the broadcast finds no waiter and
// nothing comes again. On the Xbox 360 the gap is a few instructions; here a
// worker on another core finishes small jobs inside it.
//
// THE FIX
//
// The same function, but with an endless deadline (-1) each wait ends after
// 2 ms and the result word is read again, as the original loop already does
// after every wake. The condition's timed wait is the game's own (sub_8262C600
// takes an absolute deadline: its tick, sub_8262E428, plus 10000, plus the
// milliseconds). A job that ends normally still wakes the waiter at once; only
// the lost wake-up now costs 2 ms instead of the game. A finite deadline from
// the caller is left to the original.

#include <cstdint>

#include "nfsmw_pch.h"

extern "C" void __imp__sub_8261D610(PPCContext& __restrict ctx, uint8_t* base);
extern "C" void sub_8261ADE8(PPCContext& __restrict ctx, uint8_t* base);  // lock (with a timeout)
extern "C" void sub_8262BD18(PPCContext& __restrict ctx, uint8_t* base);  // condition wait
extern "C" void sub_8262E428(PPCContext& __restrict ctx, uint8_t* base);  // tick (ms)
extern "C" void __imp__RtlLeaveCriticalSection(PPCContext& __restrict ctx, uint8_t* base);

namespace {
constexpr uint32_t kSettings = 0x82A2D9E8;   // its +16: the shared worker, for jobs that name none
constexpr uint32_t kLockTimeout = 0x82033308;
constexpr uint32_t kRetryMs = 2;
}  // namespace

extern "C" REX_FUNC(sub_8261D610) {
  const uint32_t job = ctx.r3.u32, deadline = ctx.r4.u32;
  if (REX_LOAD_U32(deadline) != 0xFFFFFFFFu) {
    __imp__sub_8261D610(ctx, base);
    return;
  }
  uint32_t worker = REX_LOAD_U32(job + 64);
  if (REX_LOAD_U8(worker + 6)) {
    worker = REX_LOAD_U32(REX_LOAD_U32(kSettings) + 16);
  }
  // A frame of its own for the short deadline the wait reads.
  const uint32_t caller_sp = ctx.r1.u32, frame = caller_sp - 64, short_deadline = frame + 32;
  REX_STORE_U32(frame, caller_sp);
  ctx.r1.u32 = frame;
  const uint32_t lock = worker + 156, done = worker + 200;
  while (REX_LOAD_U32(job + 4) == 0) {
    ctx.r3.u64 = lock;
    ctx.r4.u64 = kLockTimeout;
    ctx.lr = 0x8261D674;
    sub_8261ADE8(ctx, base);
    ctx.lr = 0x8261D684;
    sub_8262E428(ctx, base);
    REX_STORE_U32(short_deadline, ctx.r3.u32 + 10000 + kRetryMs);
    ctx.r3.u64 = done;
    ctx.r4.u64 = lock;
    ctx.r5.u64 = short_deadline;
    sub_8262BD18(ctx, base);
    REX_STORE_U32(lock + 32, REX_LOAD_U32(lock + 32) - 1);
    ctx.r3.u64 = lock;
    ctx.lr = 0x8261D698;
    __imp__RtlLeaveCriticalSection(ctx, base);
  }
  ctx.r1.u32 = caller_sp;
  ctx.r3.u64 = REX_LOAD_U32(job + 4);
}
