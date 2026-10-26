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
//
// --ios_display_match_cap (default false since IPA51): ask for exactly the cap's
// rate at 30, 40 and 60 (30 Hz, 40 Hz, 60 Hz) instead of 60 / 120 / 60. In Low
// Power Mode iOS ran the 40 cap at 60 Hz and the iPhone's drain halved
// (docs/TECHNICAL.md), but IPA50 at 40 got iOS's 60 Hz pattern and the same
// drain as 120 Hz, and 40 fps on 60 Hz is less even. The guest vblank still
// runs at 60 (30 cap) or 120 (40 cap): each refresh is published as that many
// evenly spaced ones, so the
// plugin's lock keeps its interval and stays on the display's phase.

#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>

#include <dlfcn.h>

#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdint>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"
#include "lifecycle.h"

REXCVAR_DEFINE_BOOL(ios_display_match_cap, false, "GPU",
                    "iOS: ask the display for exactly the frame rate cap's refresh rate at 30, 40 "
                    "and 60 fps (instead of 60 / 120 / 60)");

namespace {
std::atomic<int> current_cap{60};
std::atomic<int> asked_hz{60};
}  // namespace

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
      // The guest vblank's rate at the 30, 40 and 60 caps: 60, 120 and 60 Hz.
      const int cap = current_cap.load(std::memory_order_relaxed);
      const double guest_hz = cap == 40 ? 120.0 : cap == 30 || cap == 60 ? 60.0 : 0.0;
      const long split = guest_hz > 0 ? std::lround(period * guest_hz) : 1;
      publish(uint64_t(link.timestamp * 1e9), uint64_t(period * 1e9) / uint64_t(std::max(split, 1L)));
    }
  }
  // The rate iOS actually gives, when it changes (held for 30 refreshes).
  static int shown_hz = 0, seen_hz = 0, seen_count = 0, lines = 0;
  const double period = link.targetTimestamp - link.timestamp;
  const int hz = period > 0 ? int(std::lround(1.0 / period)) : 0;
  seen_count = hz == seen_hz ? seen_count + 1 : 0;
  seen_hz = hz;
  if (hz && seen_count == 30 && hz != shown_hz && lines++ < 40) {
    shown_hz = hz;
    REXLOG_INFO("[display] refresh now {} Hz (asked {} Hz, cap {})", hz, asked_hz.load(),
                current_cap.load());
  }
}
@end

namespace nfsmw::display {

void RequestRateForCap(int fps_cap) {
  static CADisplayLink* link = nil;
  static NFSDisplayRate* target = nil;
  const bool high = fps_cap == 40 || fps_cap == 120;
  const bool match = REXCVAR_GET(ios_display_match_cap) && (fps_cap == 30 || fps_cap == 40 || fps_cap == 60);
  const float preferred = match ? float(fps_cap) : high ? 120.0f : 60.0f;
  current_cap.store(fps_cap);
  asked_hz.store(int(preferred));
  if (!link) {
    target = [[NFSDisplayRate alloc] init];
    link = [CADisplayLink displayLinkWithTarget:target selector:@selector(tick:)];
    [link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
  }
  link.preferredFrameRateRange =
      match ? CAFrameRateRangeMake(preferred, preferred, preferred)
            : CAFrameRateRangeMake(high ? 80.0f : 30.0f, preferred, preferred);
  REXLOG_INFO("[display] cap {} fps: asking for {:.0f} Hz{} (screen max {} Hz)", fps_cap, preferred,
              match ? ", the cap's rate" : "", int(UIScreen.mainScreen.maximumFramesPerSecond));
}

bool MatchesCap() { return REXCVAR_GET(ios_display_match_cap); }

}  // namespace nfsmw::display
