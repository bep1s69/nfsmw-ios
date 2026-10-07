#!/usr/bin/env python3
"""
The copies of guest memory into the upload buffers are done by two worker
threads, in parallel with the command processor; it waits for them only just
before submitting.

    python3 tools/ios/patch_ios_async_copies.py            apply
    python3 tools/ios/patch_ios_async_copies.py --status
    python3 tools/ios/patch_ios_async_copies.py --revert

Touches src/graphics/vulkan/shared_memory.cpp,
src/graphics/vulkan/command_processor.cpp and src/graphics/shared_memory.cpp. Apply after
patch_ios_paint_suspend.py. Cvar ios_async_upload_copies (on).


WHY
===

The heaviest stretch of a 2-lap race (4:3 HD, 120 fps cap) ran at ~75 fps
with the GPU waiting 0.1 ms a frame: the command processor alone took ~13 ms
a frame for ~3,000 draws. A CPU profile of that thread: 26 % in one memcpy,
VulkanSharedMemory::UploadRanges copying guest memory (the game's dynamic
vertex and index data) into upload buffers; most of PrimitiveProcessor's time
is that same copy, for index data. patch_ios_shared_stats.py measured the
volume: 3-4 GB every 5 s asked for by the draws (each asks for a whole vertex
buffer), 1.6-2.4x that copied in whole 16 KB pages. Copying exactly the bytes
asked for would at most halve it; the data itself has to go.

But nothing needs the copied bytes until the GPU runs the submission. So the
command processor now only queues each copy (destination, source, size) and
goes on recording; two worker threads copy, and before vkQueueSubmit the
command processor waits for the queue to be empty, copying from it itself
while it waits. The pages are protected (MakeRangeValid) before the copy is
queued, as before, so a CPU write after that still faults and invalidates
them; the only difference is that a copy may take data written a moment
after the draw was recorded instead of at that instant. The game writes its
dynamic buffers as rings, reusing a region only frames later, so in practice
the bytes are the same.

Copies under 2 KB are still done in place (queueing would cost more).

Second version, after a profile of the first in the same stretch: memmove
fell from 26 % to 2 % of the command processor, but it stayed saturated:
condition_variable::notify_one (a wake-up system call per queued copy) took
8.5 % and re-protecting the pages (mprotect, before each copy) 12.5 %. Now
the workers are woken once per UploadRanges call and only if one sleeps.
Moving the protection to the workers as well was tried and was worse (61-70
fps where it had been 68-78): mprotect serialises on the address space map,
so the workers' protections slowed the game's threads and the command
processor waited longer for them. The protection stays on the command
processor.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

SM = "src/graphics/vulkan/shared_memory.cpp"
CP = "src/graphics/vulkan/command_processor.cpp"

SM_TOP_ANCHOR = '''#include <rex/graphics/vulkan/shared_memory.h>
'''
SM_TOP_NEW = '''#include <rex/graphics/vulkan/shared_memory.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: upload copies on worker threads
// (tools/ios/patch_ios_async_copies.py).
#include <pthread.h>
#include <atomic>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <thread>
REXCVAR_DEFINE_BOOL(ios_async_upload_copies, true, "GPU",
                    "iOS: copy guest memory into the upload buffers on worker threads, waited "
                    "for just before each submission");
namespace rex::graphics::vulkan {
namespace {
struct IosCopy {
  void* dst;
  const void* src;
  size_t size;
  rex::memory::Memory* memory;  // protect [protect_start, +size) first, if set
  uint32_t protect_start;
};
class IosCopyPool {
 public:
  // Queued; Kick() wakes the workers once a batch is in.
  void Push(const IosCopy& job) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (threads_.empty()) {
      Start();
    }
    jobs_.push_back(job);
    ++pending_;
  }
  void Kick() {
    bool wake;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      wake = sleeping_ != 0 && !jobs_.empty();
    }
    if (wake) {
      cv_.notify_all();
    }
  }
  // Until every queued copy is done; copies from the queue meanwhile.
  void Wait() {
    while (pending_.load(std::memory_order_acquire)) {
      IosCopy job;
      if (Pop(job)) {
        Run(job);
      } else {
        std::this_thread::yield();
      }
    }
  }

 private:
  void Start() {
    for (int i = 0; i < 2; ++i) {
      threads_.emplace_back([this] {
        pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
        pthread_setname_np("NFSMW upload copies");
        for (;;) {
          IosCopy job;
          {
            std::unique_lock<std::mutex> lock(mutex_);
            ++sleeping_;
            cv_.wait(lock, [this] { return !jobs_.empty(); });
            --sleeping_;
            job = jobs_.front();
            jobs_.pop_front();
          }
          Run(job);
        }
      });
      threads_.back().detach();
    }
  }
  bool Pop(IosCopy& job) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (jobs_.empty()) {
      return false;
    }
    job = jobs_.front();
    jobs_.pop_front();
    return true;
  }
  void Run(const IosCopy& job) {
    if (job.memory) {
      job.memory->EnablePhysicalMemoryAccessCallbacks(job.protect_start, uint32_t(job.size), true,
                                                      false);
    }
    std::memcpy(job.dst, job.src, job.size);
    pending_.fetch_sub(1, std::memory_order_release);
  }
  std::mutex mutex_;
  std::condition_variable cv_;
  std::deque<IosCopy> jobs_;
  std::vector<std::thread> threads_;
  uint32_t sleeping_ = 0;
  std::atomic<uint32_t> pending_{0};
};
IosCopyPool& IosCopies() {
  static IosCopyPool* pool = new IosCopyPool();  // never destroyed: detached workers
  return *pool;
}
}  // namespace
// Before a submission: every queued copy into the upload buffers is done.
void IosWaitUploadCopies() { IosCopies().Wait(); }
}  // namespace rex::graphics::vulkan
#endif
'''

SM_COPY_ANCHOR = '''      MakeRangeValid(upload_range_start << page_size_log2(), uint32_t(upload_buffer_size), false);
      std::memcpy(upload_buffer_mapping,
                  memory().TranslatePhysical(upload_range_start << page_size_log2()),
                  upload_buffer_size);
'''
SM_COPY_NEW = '''#if REX_PLATFORM_IOS
      // LOCAL PATCH - iOS: the copy on a worker thread, done before the
      // submission (tools/ios/patch_ios_async_copies.py).
      if (REXCVAR_GET(ios_async_upload_copies) && upload_buffer_size >= 2048) {
        MakeRangeValid(upload_range_start << page_size_log2(), uint32_t(upload_buffer_size), false);
        IosCopies().Push({upload_buffer_mapping,
                          memory().TranslatePhysical(upload_range_start << page_size_log2()),
                          size_t(upload_buffer_size), nullptr, 0});
      } else {
        MakeRangeValid(upload_range_start << page_size_log2(), uint32_t(upload_buffer_size),
                       false);
        std::memcpy(upload_buffer_mapping,
                    memory().TranslatePhysical(upload_range_start << page_size_log2()),
                    upload_buffer_size);
      }
#else
      MakeRangeValid(upload_range_start << page_size_log2(), uint32_t(upload_buffer_size), false);
      std::memcpy(upload_buffer_mapping,
                  memory().TranslatePhysical(upload_range_start << page_size_log2()),
                  upload_buffer_size);
#endif
'''

SM_KICK_ANCHOR = '''  if (!upload_regions_.empty()) {
    assert_true(upload_buffer_previous != VK_NULL_HANDLE);
    command_buffer.CmdVkCopyBuffer(upload_buffer_previous, buffer_,
                                   uint32_t(upload_regions_.size()), upload_regions_.data());
    upload_regions_.clear();
  }
'''
SM_KICK_NEW = SM_KICK_ANCHOR + '''#if REX_PLATFORM_IOS
  IosCopies().Kick();  // LOCAL PATCH - iOS: one wake-up for this call's copies
#endif
'''

COMMON = "src/graphics/shared_memory.cpp"
COMMON_FLAG_ANCHOR = '''namespace rex::graphics {
'''
COMMON_FLAG_NEW = '''namespace rex::graphics {

#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: set while VulkanSharedMemory queues an upload whose
// worker protects the pages itself (tools/ios/patch_ios_async_copies.py).
thread_local bool ios_defer_protect = false;
#endif
'''
COMMON_PROTECT_ANCHOR = '''  if (memory_invalidation_callback_handle_) {
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: hot pages stay unprotected (patch_ios_hot_pages.py).
'''
COMMON_PROTECT_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the upload's worker protects (patch_ios_async_copies.py).
  if (ios_defer_protect) {
    return;
  }
#endif
  if (memory_invalidation_callback_handle_) {
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: hot pages stay unprotected (patch_ios_hot_pages.py).
'''

CP_DECL_ANCHOR = '''#include <rex/ui/vulkan/presenter.h>
#include <rex/ui/vulkan/util.h>
'''
CP_DECL_NEW = '''#include <rex/ui/vulkan/presenter.h>
#include <rex/ui/vulkan/util.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: upload copies on worker threads (shared_memory.cpp,
// tools/ios/patch_ios_async_copies.py).
namespace rex::graphics::vulkan {
void IosWaitUploadCopies();
}  // namespace rex::graphics::vulkan
#endif
'''

CP_WAIT_ANCHOR = '''    VkResult submit_result;
    {
#if REX_PLATFORM_IOS
      nfsmw_ios_gpu_gate();  // LOCAL PATCH - iOS, before taking the queue
#endif
'''
CP_WAIT_NEW = '''#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: the upload copies this submission reads are done
    // (tools/ios/patch_ios_async_copies.py).
    IosWaitUploadCopies();
#endif
    VkResult submit_result;
    {
#if REX_PLATFORM_IOS
      nfsmw_ios_gpu_gate();  // LOCAL PATCH - iOS, before taking the queue
#endif
'''

BLOCKS = [
    (SM, "the copy workers", SM_TOP_ANCHOR, SM_TOP_NEW),
    (SM, "protection and copy queued", SM_COPY_ANCHOR, SM_COPY_NEW),
    (SM, "one wake-up per call", SM_KICK_ANCHOR, SM_KICK_NEW),
    (CP, "declare the wait", CP_DECL_ANCHOR, CP_DECL_NEW),
    (CP, "wait for the copies before submitting", CP_WAIT_ANCHOR, CP_WAIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_async_copies", BLOCKS))
