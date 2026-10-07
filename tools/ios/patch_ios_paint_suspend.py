#!/usr/bin/env python3
"""
While the app is paused (another app on screen) no GPU work is submitted: the
UI thread paints nothing, and the GPU emulation's submissions wait. The
window's surface stays.

    python3 tools/ios/patch_ios_paint_suspend.py            apply
    python3 tools/ios/patch_ios_paint_suspend.py --status
    python3 tools/ios/patch_ios_paint_suspend.py --revert

Touches src/ui/presenter.cpp, src/ui/vulkan/vulkan_presenter.cpp and
src/graphics/vulkan/command_processor.cpp. Used by ios/src/game_app.cpp
(through ios/src/lifecycle.mm).


WHY
===

iOS refuses GPU work from an app in the background: going to the home screen
in a race could end in VK_ERROR_DEVICE_LOST ("Insufficient Permission").

The UI thread paints on its own (the idle repaint, the last guest frames). The
first answer took the window's surface away while paused, as on Android. On
iOS that made a new Metal view at every return (it could end up over the
touch controls, came back portrait once) and a paint requested in between left
the presenter's request flag set forever (patch_ios_surface_reattach.py). So
the surface stays, and while nfsmw_ios_suspend_paints(true) is in effect
PaintFromUIThread does nothing but clear that flag: the first guest frame after
nfsmw_ios_suspend_paints(false) asks for a paint again as usual.

The GPU emulation was paused with GraphicsSystem::Pause(), which suspends the
command processor's thread with a race: the thread signals "paused" and only
then suspends itself. A quick resume in between was lost and the thread stayed
suspended for good (the game froze); and once, 4 s after a pause, the thread
was still submitting and the device was lost. Instead, while paused, every
vkQueueSubmit off the main thread (the command processor's, and the guest
output refresh's) waits in nfsmw_ios_gpu_gate() until the app is active
again. It waits BEFORE taking the queue, and never on the main thread (which
is the one that resumes), so nothing the main thread needs is held. The
thread is never suspended: game_app.cpp no longer calls Pause().
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/ui/presenter.cpp"
VP = "src/ui/vulkan/vulkan_presenter.cpp"
CP = "src/graphics/vulkan/command_processor.cpp"

TOP_ANCHOR = '''void Presenter::PaintFromUIThread(bool force_paint) {
'''
TOP_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: no GPU work while the app is paused
// (tools/ios/patch_ios_paint_suspend.py).
namespace {
std::atomic<bool> ios_paints_suspended{false};
std::mutex ios_gate_mutex;
std::condition_variable ios_gate_cv;
}  // namespace
extern "C" __attribute__((visibility("default"))) void nfsmw_ios_suspend_paints(bool suspend) {
  {
    std::lock_guard<std::mutex> lock(ios_gate_mutex);
    ios_paints_suspended.store(suspend, std::memory_order_release);
  }
  ios_gate_cv.notify_all();
}
// Before a GPU submission: waits while the app is paused (never on the main
// thread, which is the one that resumes).
extern "C" __attribute__((visibility("default"))) void nfsmw_ios_gpu_gate() {
  if (!ios_paints_suspended.load(std::memory_order_acquire) || pthread_main_np()) {
    return;
  }
  std::unique_lock<std::mutex> lock(ios_gate_mutex);
  ios_gate_cv.wait(lock, [] { return !ios_paints_suspended.load(std::memory_order_acquire); });
}
#endif

void Presenter::PaintFromUIThread(bool force_paint) {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: no GPU work while paused; the request flag is cleared
  // so the next request after resuming goes through.
  if (ios_paints_suspended.load(std::memory_order_acquire)) {
    ui_thread_paint_requested_.store(false, std::memory_order_relaxed);
    return;
  }
#endif
'''

INCLUDE_ANCHOR = '''#include <mutex>
'''
INCLUDE_NEW = '''#include <mutex>
#if REX_PLATFORM_IOS
#include <pthread.h>  // LOCAL PATCH - iOS: pthread_main_np (patch_ios_paint_suspend.py)
#endif
'''

GATE_DECL = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: GPU submissions wait while the app is paused
// (presenter.cpp, tools/ios/patch_ios_paint_suspend.py).
extern "C" void nfsmw_ios_gpu_gate();
#endif
'''

VP_DECL_ANCHOR = '''#include <rex/ui/vulkan/util.h>
'''

VP_SUBMIT_ANCHOR = '''      VkResult submit_result;
      {
        const VulkanDevice::Queue::Acquisition queue_acquisition =
            vulkan_device_->AcquireQueue(vulkan_device_->queue_family_graphics_compute(), 0);
        submit_result =
            dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence_acqusition.fence());
'''
VP_SUBMIT_NEW = '''      VkResult submit_result;
      {
#if REX_PLATFORM_IOS
        nfsmw_ios_gpu_gate();  // LOCAL PATCH - iOS, before taking the queue
#endif
        const VulkanDevice::Queue::Acquisition queue_acquisition =
            vulkan_device_->AcquireQueue(vulkan_device_->queue_family_graphics_compute(), 0);
        submit_result =
            dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence_acqusition.fence());
'''

CP_DECL_ANCHOR = '''#include <rex/ui/vulkan/presenter.h>
#include <rex/ui/vulkan/util.h>
'''

CP_SUBMIT_ANCHOR = '''    VkResult submit_result;
    {
      const auto ios_queue_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
'''
CP_SUBMIT_NEW = '''    VkResult submit_result;
    {
#if REX_PLATFORM_IOS
      nfsmw_ios_gpu_gate();  // LOCAL PATCH - iOS, before taking the queue
#endif
      const auto ios_queue_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
'''

BLOCKS = [
    (F, "pthread_main_np", INCLUDE_ANCHOR, INCLUDE_NEW),
    (F, "suspend the UI thread's paints, and the GPU gate", TOP_ANCHOR, TOP_NEW),
    (VP, "declare the GPU gate", VP_DECL_ANCHOR, VP_DECL_ANCHOR + GATE_DECL),
    (VP, "the guest output refresh waits at the gate", VP_SUBMIT_ANCHOR, VP_SUBMIT_NEW),
    (CP, "declare the GPU gate", CP_DECL_ANCHOR, CP_DECL_ANCHOR + GATE_DECL),
    (CP, "the command processor's submissions wait at the gate", CP_SUBMIT_ANCHOR,
     CP_SUBMIT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_paint_suspend", BLOCKS))
