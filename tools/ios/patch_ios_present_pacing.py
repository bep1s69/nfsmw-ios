#!/usr/bin/env python3
"""
Even frame pacing at the 30 and 40 fps caps: each frame is presented with a
target time, one frame interval after the previous one.

    python3 tools/ios/patch_ios_present_pacing.py            apply
    python3 tools/ios/patch_ios_present_pacing.py --status
    python3 tools/ios/patch_ios_present_pacing.py --revert

Touches src/ui/vulkan/vulkan_device.cpp and src/ui/vulkan/vulkan_presenter.cpp
(the runtime). Works with patch_ios_fps_cap.py: the cvar ios_fps_cap is
defined here, because the presenter is in the runtime and cannot see the GPU
plugin's cvars; the plugin declares it.


WHY
===

At the 30 and 40 caps the log showed perfectly even guest frames (exactly
40.0 frames and 40.0 presents a second), yet the picture looked choppy. The
frames were handed to the display with no target time, so each was shown at
whatever refresh came next after it arrived: small jitter turned some frames
into 1 refresh and others into 3 (at 30 on 60 Hz), and 40 on a 60 Hz display
can only alternate 1 and 2 refreshes.

MoltenVK implements VK_GOOGLE_display_timing with Metal's presentAtTime:, so
a frame can carry the time it should appear. Here, at the 30 and 40 caps,
each present asks for one interval (33.3 or 25 ms) after the previous target:
the targets stay on an even grid, never earlier than now, and the grid starts
again from now if a frame is more than one interval late. A target is never
more than a quarter interval ahead of now: the first version let the grid run
ahead, so a frame ready early waited up to a whole interval for its slot, and
the 30 cap felt laggy. The clock is
mach_absolute_time in nanoseconds, the one CACurrentMediaTime (and so
presentAtTime:) uses.

The display's own rate is the app's side: ios/src/display_rate.mm asks iOS
for 120 Hz at the 40 and 120 caps (ProMotion), where 40 fps is exactly 3
refreshes.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

DEV = "src/ui/vulkan/vulkan_device.cpp"
PRES = "src/ui/vulkan/vulkan_presenter.cpp"

DEV_GLOBAL_ANCHOR = '''#include <rex/ui/vulkan/device.h>
'''
DEV_GLOBAL_NEW = '''#include <rex/ui/vulkan/device.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: VK_GOOGLE_display_timing enabled on the device, for the
// presenter's pacing (tools/ios/patch_ios_present_pacing.py).
bool ios_vk_google_display_timing = false;
#endif
'''

DEV_REQUEST_ANCHOR = '''  std::vector<const char*> enabled_extensions;
'''
DEV_REQUEST_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: ask for VK_GOOGLE_display_timing (MoltenVK: presentAtTime:).
  ::ios_vk_google_display_timing = false;
  requested_extensions.emplace("VK_GOOGLE_display_timing", &::ios_vk_google_display_timing);
#endif
  std::vector<const char*> enabled_extensions;
'''

PRES_TOP_ANCHOR = '''#include <rex/ui/vulkan/util.h>
'''
PRES_TOP_NEW = '''#include <rex/ui/vulkan/util.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: the frame rate cap, and presentation paced by it
// (tools/ios/patch_ios_present_pacing.py, patch_ios_fps_cap.py).
#include <mach/mach_time.h>
#include <rex/cvar.h>
REXCVAR_DEFINE_INT32(ios_fps_cap, 60, "GPU",
                     "iOS: frame rate cap: 30, 40, 60 (the game's) or 120. 40 and 120 run the "
                     "guest vblank at 120 Hz (experimental)");
extern bool ios_vk_google_display_timing;  // vulkan_device.cpp
namespace {
uint64_t IosNowNs() {
  static mach_timebase_info_data_t timebase = {};
  if (!timebase.denom) {
    mach_timebase_info(&timebase);
  }
  return mach_absolute_time() * timebase.numer / timebase.denom;
}
}  // namespace
#endif
'''

PRESENT_ANCHOR = '''  present_info.pResults = nullptr;
  VkResult present_result;
'''
PRESENT_NEW = '''  present_info.pResults = nullptr;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: at the 30 and 40 caps, each frame asks to appear one
  // interval after the previous one (tools/ios/patch_ios_present_pacing.py).
  VkPresentTimeGOOGLE ios_present_time = {};
  VkPresentTimesInfoGOOGLE ios_present_times = {};
  {
    const int32_t cap = REXCVAR_GET(ios_fps_cap);
    const uint64_t interval = cap == 30 ? 33333333ull : cap == 40 ? 25000000ull : 0;
    static uint64_t ios_last_target = 0;
    static uint32_t ios_present_id = 0;
    if (interval && ::ios_vk_google_display_timing) {
      const uint64_t now = IosNowNs();
      uint64_t grid = ios_last_target + interval;
      if (!ios_last_target || now > grid + interval) {
        grid = now;  // more than a frame late: start the grid again
      } else if (grid > now + interval / 4) {
        // Never more than a quarter interval ahead: a frame that is ready
        // early would otherwise wait up to a whole interval for its slot
        // (input lag at the 30 cap).
        grid = now + interval / 4;
      }
      ios_last_target = grid;
      ios_present_time.presentID = ++ios_present_id;
      ios_present_time.desiredPresentTime = grid > now ? grid : now;
      ios_present_times.sType = VK_STRUCTURE_TYPE_PRESENT_TIMES_INFO_GOOGLE;
      ios_present_times.swapchainCount = 1;
      ios_present_times.pTimes = &ios_present_time;
      present_info.pNext = &ios_present_times;
    } else {
      ios_last_target = 0;
    }
  }
#endif
  VkResult present_result;
'''

BLOCKS = [
    (DEV, "the display timing flag", DEV_GLOBAL_ANCHOR, DEV_GLOBAL_NEW),
    (DEV, "request VK_GOOGLE_display_timing", DEV_REQUEST_ANCHOR, DEV_REQUEST_NEW),
    (PRES, "ios_fps_cap and the clock", PRES_TOP_ANCHOR, PRES_TOP_NEW),
    (PRES, "a target time on each present", PRESENT_ANCHOR, PRESENT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_present_pacing", BLOCKS))
