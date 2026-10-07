// NFSMW Recompiled - the display refresh rate the game asks iOS for
//
// On ProMotion displays iOS picks the refresh rate from what the app asks for;
// a Metal layer presenting on its own gets 60 Hz. A CADisplayLink with a
// preferred frame rate range is the way to ask (and its ticks feed the guest
// vblank, below). 120 Hz matters for the 40 fps cap
// (25 ms is exactly 3 refreshes at 120, but 1.5 at 60) and for 120 fps. On an
// iPhone it also needs CADisableMinimumFrameDurationOnPhone in Info.plist.
//
// Each tick also publishes the refresh's time and period to the GPU plugin
// (nfsmw_display_vsync, tools/ios/patch_ios_vblank_display.py): at the 30 and
// 40 caps the guest vblank follows the display's refresh. The timestamps are
// the display's, not when this callback ran, so main-thread delays do not
// matter. CACurrentMediaTime's clock is mach_absolute_time, as the plugin's.

#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>

#include <dlfcn.h>

#include <cstdint>

#include <rex/logging.h>

#include "display_rate.h"
#include "lifecycle.h"

@interface NFSDisplayRate : NSObject
- (void)tick:(CADisplayLink*)link;
@end

@implementation NFSDisplayRate
- (void)tick:(CADisplayLink*)link {
  nfsmw::lifecycle::OnDisplayTick();
  using Publish = void (*)(uint64_t, uint64_t);
  static Publish publish = reinterpret_cast<Publish>(dlsym(RTLD_DEFAULT, "nfsmw_display_vsync"));
  if (publish) {
    const double period = link.targetTimestamp - link.timestamp;
    if (period > 0) {
      publish(uint64_t(link.timestamp * 1e9), uint64_t(period * 1e9));
    }
  }
}
@end

namespace nfsmw::display {

void RequestRateForCap(int fps_cap) {
  static CADisplayLink* link = nil;
  static NFSDisplayRate* target = nil;
  const bool high = fps_cap == 40 || fps_cap == 120;
  const float preferred = high ? 120.0f : 60.0f;
  if (!link) {
    target = [[NFSDisplayRate alloc] init];
    link = [CADisplayLink displayLinkWithTarget:target selector:@selector(tick:)];
    [link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
  }
  link.preferredFrameRateRange =
      CAFrameRateRangeMake(high ? 80.0f : 30.0f, preferred, preferred);
  REXLOG_INFO("[display] cap {} fps: asking for {:.0f} Hz (screen max {} Hz)", fps_cap, preferred,
              int(UIScreen.mainScreen.maximumFramesPerSecond));
}

}  // namespace nfsmw::display
