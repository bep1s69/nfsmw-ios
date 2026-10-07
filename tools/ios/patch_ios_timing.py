#!/usr/bin/env python3
"""
Where the "swap" time goes on iOS: a line in the log every 5 s.

    python3 tools/ios/patch_ios_timing.py            apply
    python3 tools/ios/patch_ios_timing.py --status
    python3 tools/ios/patch_ios_timing.py --revert

Touches src/ui/presenter.cpp, src/ui/vulkan/vulkan_presenter.cpp and
src/graphics/vulkan/command_processor.cpp.


WHY
===

The first race on an iPad M4 (17-25 fps) had parche_tiempos' breakdown at
40.7 ms per frame = draws 7.2 + swap 19.7 + rest 13.8, with the command
processor (CP) never idle and never waiting for the GPU. "swap" is
VulkanCommandProcessor::IssueSwap from presenter->RefreshGuestOutput() to the
end, and only ~5 ms of it is vkQueueSubmit. The rest is inside the presenter,
and there are two very different possibilities:

  - the presenter's paint mode is kGuestOutputThreadImmediately: then the CP
    thread ITSELF paints and presents (Presenter::PaintAndPresent), which on
    iOS means waiting in vkAcquireNextImageKHR for a CAMetalLayer drawable,
    paced by the display. The emulation would wait for the screen every frame;
  - or the UI thread paints (kUIThreadOnRequest), and the time is somewhere
    else.

This times each piece, per guest frame, averaged over 5 s:

    [ios-swap] per guest frame: refresh N ms (CP: gamma pass + submit) |
               CP paints N/s, N ms each | UI paints N/s, N ms each |
               acquire N ms, present N ms (per paint)

It is a handful of clock reads per frame: cheap enough to leave in.


SECOND ROUND: WHO WAITS FOR WHAT
================================

With patch_ios_ui_tick the swap fell from ~15 ms to ~1.5 ms in a race, but in
a heavier race (3,700-4,000 draws) it was back at 15-16 ms, with each UI paint
taking 25-28 ms of which acquire and present were ~0.01 ms. Two more timers:

  - paint GPU wait: PaintAndPresentImpl first waits for an EARLIER paint to
    finish on the GPU (AwaitSubmissionCompletion). With MoltenVK's single
    queue, a paint runs on the GPU after the game's own work, so this is,
    roughly, how far behind the GPU is;
  - CP queue wait: how long the command processor waits for the queue lock
    before its vkQueueSubmit (parche_tiempos' "vkQueueSubmit" only times the
    call itself).


THIRD ROUND: INSIDE THE PAINT
=============================

The second round answered "is it the GPU?" with no: in a race each paint took
15-16 ms while waiting 0.00 ms for the GPU, and the CP waited 7-8 ms per frame
for the queue lock. So the paint spends ~15 ms somewhere else. It is timed by
stage:

  - consume: ConsumeGuestOutput, a mutex the CP also takes;
  - UI: ExecuteUIDrawersFromUIThread (ImGui);
  - queue wait and submit: the lock, then vkQueueSubmit (MoltenVK turns the
    Vulkan commands into Metal work here);
  - the rest of the paint (recording the guest output passes) is what remains.


A NOTE ON ONE BLOCK
===================

The vkQueuePresentKHR call sits inside parche_cola_presentar's block, so the
timing goes there too. As with patch_ios_waits, that is safe only because
tools/ios/prepare_sdk.py applies the project patches once.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

P = "src/ui/presenter.cpp"
VP = "src/ui/vulkan/vulkan_presenter.cpp"

# ---------------------------------------------------------------------------
#  src/ui/presenter.cpp: the counters, the timer and the report
# ---------------------------------------------------------------------------
# Above PaintFromUIThread, the first function that uses the counters.
COUNTERS_ANCHOR = '''void Presenter::PaintFromUIThread(bool force_paint) {
'''
COUNTERS_NEW = '''// LOCAL PATCH - iOS: where the swap time goes (tools/ios/patch_ios_timing.py).
// The acquire/present counters are also used by vulkan_presenter.cpp.
namespace ios_timing {
std::atomic<uint64_t> g_refresh_ns{0};
std::atomic<uint64_t> g_frames{0};
std::atomic<uint64_t> g_cp_paint_ns{0};
std::atomic<uint64_t> g_cp_paints{0};
std::atomic<uint64_t> g_ui_paint_ns{0};
std::atomic<uint64_t> g_ui_paints{0};
std::atomic<uint64_t> g_acquire_ns{0};
std::atomic<uint64_t> g_present_ns{0};
std::atomic<uint64_t> g_paint_gpu_wait_ns{0};
std::atomic<uint64_t> g_paint_consume_ns{0};
std::atomic<uint64_t> g_paint_ui_ns{0};
std::atomic<uint64_t> g_paint_queue_wait_ns{0};
std::atomic<uint64_t> g_paint_submit_ns{0};
// Added to by the command processor, in the GPU plugin.
__attribute__((visibility("default"))) std::atomic<uint64_t> g_cp_queue_wait_ns{0};

void Add(std::atomic<uint64_t>& to, std::chrono::steady_clock::time_point since) {
  to.fetch_add(uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                            std::chrono::steady_clock::now() - since)
                            .count()),
               std::memory_order_relaxed);
}

// Called once per guest frame (end of RefreshGuestOutput): every 5 s, one
// line with the averages, and the counters back to zero.
static void Report() {
  static std::chrono::steady_clock::time_point last = std::chrono::steady_clock::now();
  const auto now = std::chrono::steady_clock::now();
  const double seconds = std::chrono::duration<double>(now - last).count();
  if (seconds < 5.0) {
    return;
  }
  last = now;
  const double frames = double(std::max<uint64_t>(1, g_frames.exchange(0)));
  const uint64_t cp_paints = g_cp_paints.exchange(0);
  const uint64_t ui_paints = g_ui_paints.exchange(0);
  const uint64_t paints = std::max<uint64_t>(1, cp_paints + ui_paints);
  auto ms = [](std::atomic<uint64_t>& v, double per) { return double(v.exchange(0)) / 1e6 / per; };
  const double refresh = ms(g_refresh_ns, frames);
  const double cp_each = ms(g_cp_paint_ns, double(std::max<uint64_t>(1, cp_paints)));
  const double ui_each = ms(g_ui_paint_ns, double(std::max<uint64_t>(1, ui_paints)));
  const double acquire = ms(g_acquire_ns, double(paints));
  const double present = ms(g_present_ns, double(paints));
  const double paint_gpu_wait = ms(g_paint_gpu_wait_ns, double(paints));
  const double cp_queue_wait = ms(g_cp_queue_wait_ns, frames);
  const double consume = ms(g_paint_consume_ns, double(paints));
  const double ui = ms(g_paint_ui_ns, double(paints));
  const double paint_queue_wait = ms(g_paint_queue_wait_ns, double(paints));
  const double paint_submit = ms(g_paint_submit_ns, double(paints));
  REXLOG_INFO(
      "[ios-swap] per guest frame ({:.0f} in {:.1f} s): refresh {:.2f} ms (CP: gamma pass + "
      "submit) | CP paints {:.1f}/s, {:.2f} ms each | UI paints {:.1f}/s, {:.2f} ms each | "
      "per paint: GPU wait {:.2f}, consume {:.2f}, acquire {:.2f}, UI {:.2f}, queue wait {:.2f}, "
      "submit {:.2f}, present {:.2f} ms | CP waiting for the queue {:.2f} ms",
      frames, seconds, refresh, double(cp_paints) / seconds, cp_each,
      double(ui_paints) / seconds, ui_each, paint_gpu_wait, consume, acquire, ui,
      paint_queue_wait, paint_submit, present, cp_queue_wait);
}
}  // namespace ios_timing

void Presenter::PaintFromUIThread(bool force_paint) {
'''

REFRESH_ANCHOR = '''  if (is_active) {
    if (!RefreshGuestOutputImpl(guest_output_mailbox_writable_, frontbuffer_width,
                                frontbuffer_height, refresher, writable_properties.is_8bpc)) {
'''
REFRESH_NEW = '''  ios_timing::g_frames.fetch_add(1, std::memory_order_relaxed);  // LOCAL PATCH - iOS
  if (is_active) {
    const auto ios_refresh_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
    const bool ios_refreshed = RefreshGuestOutputImpl(
        guest_output_mailbox_writable_, frontbuffer_width, frontbuffer_height, refresher,
        writable_properties.is_8bpc);
    ios_timing::Add(ios_timing::g_refresh_ns, ios_refresh_start);
    if (!ios_refreshed) {
'''

CP_PAINT_ANCHOR = '''          paint_result = PaintAndPresent(false);
'''
CP_PAINT_NEW = '''          // LOCAL PATCH - iOS: the CP thread paints and presents itself.
          const auto ios_paint_start = std::chrono::steady_clock::now();
          paint_result = PaintAndPresent(false);
          ios_timing::Add(ios_timing::g_cp_paint_ns, ios_paint_start);
          ios_timing::g_cp_paints.fetch_add(1, std::memory_order_relaxed);
'''

UI_PAINT_ANCHOR = '''      paint_result = PaintAndPresent(draw_ui);
'''
UI_PAINT_NEW = '''      // LOCAL PATCH - iOS: the UI thread paints and presents.
      const auto ios_paint_start = std::chrono::steady_clock::now();
      paint_result = PaintAndPresent(draw_ui);
      ios_timing::Add(ios_timing::g_ui_paint_ns, ios_paint_start);
      ios_timing::g_ui_paints.fetch_add(1, std::memory_order_relaxed);
'''

REPORT_ANCHOR = '''      host_gpu_loss_callback_(false, false);
    }
  }

  return is_active;
}
'''
REPORT_NEW = '''      host_gpu_loss_callback_(false, false);
    }
  }

  ios_timing::Report();  // LOCAL PATCH - iOS
  return is_active;
}
'''

# ---------------------------------------------------------------------------
#  src/ui/vulkan/vulkan_presenter.cpp: acquire and present
# ---------------------------------------------------------------------------
# Before the file's namespaces open: everything after this sits inside
# rex::ui::vulkan (the shader #includes even inside a namespace of their own),
# from where ios_timing:: resolves to rex::ui::ios_timing.
DECL_ANCHOR = '''namespace rex {
namespace ui {
namespace vulkan {
'''
DECL_NEW = '''// LOCAL PATCH - iOS: timing of acquire and present (presenter.cpp,
// tools/ios/patch_ios_timing.py).
#include <atomic>
#include <chrono>
namespace rex::ui::ios_timing {
extern std::atomic<uint64_t> g_acquire_ns;
extern std::atomic<uint64_t> g_present_ns;
extern std::atomic<uint64_t> g_paint_gpu_wait_ns;
extern std::atomic<uint64_t> g_paint_consume_ns;
extern std::atomic<uint64_t> g_paint_ui_ns;
extern std::atomic<uint64_t> g_paint_queue_wait_ns;
extern std::atomic<uint64_t> g_paint_submit_ns;
void Add(std::atomic<uint64_t>& to, std::chrono::steady_clock::time_point since);
}  // namespace rex::ui::ios_timing

namespace rex {
namespace ui {
namespace vulkan {
'''

ACQUIRE_ANCHOR = '''  VkResult acquire_result =
      dfn.vkAcquireNextImageKHR(device, paint_context_.swapchain, UINT64_MAX, acquire_semaphore,
                                VK_NULL_HANDLE, &swapchain_image_index);
'''
ACQUIRE_NEW = '''  const auto ios_acquire_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
  VkResult acquire_result =
      dfn.vkAcquireNextImageKHR(device, paint_context_.swapchain, UINT64_MAX, acquire_semaphore,
                                VK_NULL_HANDLE, &swapchain_image_index);
  ios_timing::Add(ios_timing::g_acquire_ns, ios_acquire_start);
'''

PRESENT_ANCHOR = '''    present_result = dfn.vkQueuePresentKHR(queue_acquisition.queue(), &present_info);
'''
PRESENT_NEW = '''    const auto ios_present_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
    present_result = dfn.vkQueuePresentKHR(queue_acquisition.queue(), &present_info);
    ios_timing::Add(ios_timing::g_present_ns, ios_present_start);
'''

CHRONO_ANCHOR = '''#include <atomic>
#include <cctype>
'''
CHRONO_NEW = '''#include <atomic>
#include <cctype>
#include <chrono>  // LOCAL PATCH - iOS (tools/ios/patch_ios_timing.py)
'''

PAINT_WAIT_ANCHOR = '''  if (current_paint_submission_index >= paint_submission_count) {
    paint_context_.submission_tracker.AwaitSubmissionCompletion(current_paint_submission_index -
                                                                paint_submission_count);
  }
'''
PAINT_WAIT_NEW = '''  if (current_paint_submission_index >= paint_submission_count) {
    const auto ios_wait_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
    paint_context_.submission_tracker.AwaitSubmissionCompletion(current_paint_submission_index -
                                                                paint_submission_count);
    ios_timing::Add(ios_timing::g_paint_gpu_wait_ns, ios_wait_start);
  }
'''

CONSUME_ANCHOR = '''    std::unique_lock<std::mutex> guest_output_consumer_lock(ConsumeGuestOutput(
        guest_output_mailbox_index, &guest_output_properties, &guest_output_paint_config));
'''
CONSUME_NEW = '''    const auto ios_consume_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
    std::unique_lock<std::mutex> guest_output_consumer_lock(ConsumeGuestOutput(
        guest_output_mailbox_index, &guest_output_properties, &guest_output_paint_config));
    ios_timing::Add(ios_timing::g_paint_consume_ns, ios_consume_start);
'''

UI_ANCHOR = '''    ExecuteUIDrawersFromUIThread(ui_draw_context);
'''
UI_NEW = '''    const auto ios_ui_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
    ExecuteUIDrawersFromUIThread(ui_draw_context);
    ios_timing::Add(ios_timing::g_paint_ui_ns, ios_ui_start);
'''

SUBMIT_ANCHOR = '''    VkResult submit_result;
    {
      const VulkanDevice::Queue::Acquisition queue_acquisition =
          vulkan_device_->AcquireQueue(vulkan_device_->queue_family_graphics_compute(), 0);
      submit_result =
          dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence_acqusition.fence());
      if (ui_fence_acquisition.fence() != VK_NULL_HANDLE && submit_result == VK_SUCCESS) {
        if (dfn.vkQueueSubmit(queue_acquisition.queue(), 0, nullptr,
                              ui_fence_acquisition.fence()) != VK_SUCCESS) {
          ui_fence_acquisition.SubmissionSucceededSignalFailed();
        }
      }
    }
'''
SUBMIT_NEW = '''    VkResult submit_result;
    {
      const auto ios_queue_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
      const VulkanDevice::Queue::Acquisition queue_acquisition =
          vulkan_device_->AcquireQueue(vulkan_device_->queue_family_graphics_compute(), 0);
      ios_timing::Add(ios_timing::g_paint_queue_wait_ns, ios_queue_start);
      const auto ios_submit_start = std::chrono::steady_clock::now();
      submit_result =
          dfn.vkQueueSubmit(queue_acquisition.queue(), 1, &submit_info, fence_acqusition.fence());
      if (ui_fence_acquisition.fence() != VK_NULL_HANDLE && submit_result == VK_SUCCESS) {
        if (dfn.vkQueueSubmit(queue_acquisition.queue(), 0, nullptr,
                              ui_fence_acquisition.fence()) != VK_SUCCESS) {
          ui_fence_acquisition.SubmissionSucceededSignalFailed();
        }
      }
      ios_timing::Add(ios_timing::g_paint_submit_ns, ios_submit_start);
    }
'''

CP = "src/graphics/vulkan/command_processor.cpp"

CP_DECL_ANCHOR = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
'''
CP_DECL_NEW = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
// LOCAL PATCH - iOS: the CP's wait for the queue lock, reported by
// presenter.cpp (tools/ios/patch_ios_timing.py).
namespace rex::ui::ios_timing {
extern std::atomic<uint64_t> g_cp_queue_wait_ns;
}  // namespace rex::ui::ios_timing
'''

CP_QUEUE_ANCHOR = '''    VkResult submit_result;
    {
      ui::vulkan::VulkanDevice::Queue::Acquisition queue_acquisition =
          vulkan_device->AcquireQueue(vulkan_device->queue_family_graphics_compute(), 0);
'''
CP_QUEUE_NEW = '''    VkResult submit_result;
    {
      const auto ios_queue_start = std::chrono::steady_clock::now();  // LOCAL PATCH - iOS
      ui::vulkan::VulkanDevice::Queue::Acquisition queue_acquisition =
          vulkan_device->AcquireQueue(vulkan_device->queue_family_graphics_compute(), 0);
      rex::ui::ios_timing::g_cp_queue_wait_ns.fetch_add(
          uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(
                       std::chrono::steady_clock::now() - ios_queue_start)
                       .count()),
          std::memory_order_relaxed);
'''

BLOCKS = [
    (P, "include <chrono>", CHRONO_ANCHOR, CHRONO_NEW),
    (P, "counters, timer and report", COUNTERS_ANCHOR, COUNTERS_NEW),
    (P, "time the CP's refresh (gamma + submit)", REFRESH_ANCHOR, REFRESH_NEW),
    (P, "time CP-thread painting", CP_PAINT_ANCHOR, CP_PAINT_NEW),
    (P, "time UI-thread painting", UI_PAINT_ANCHOR, UI_PAINT_NEW),
    (P, "report every 5 s", REPORT_ANCHOR, REPORT_NEW),
    (VP, "declare the counters", DECL_ANCHOR, DECL_NEW),
    (VP, "time vkAcquireNextImageKHR", ACQUIRE_ANCHOR, ACQUIRE_NEW),
    (VP, "time vkQueuePresentKHR", PRESENT_ANCHOR, PRESENT_NEW),
    (VP, "time the paint's wait for the GPU", PAINT_WAIT_ANCHOR, PAINT_WAIT_NEW),
    (VP, "time ConsumeGuestOutput", CONSUME_ANCHOR, CONSUME_NEW),
    (VP, "time the UI drawers", UI_ANCHOR, UI_NEW),
    (VP, "time the paint's queue wait and submit", SUBMIT_ANCHOR, SUBMIT_NEW),
    (CP, "declare the CP queue-wait counter", CP_DECL_ANCHOR, CP_DECL_NEW),
    (CP, "time the CP's wait for the queue", CP_QUEUE_ANCHOR, CP_QUEUE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_timing", BLOCKS))
