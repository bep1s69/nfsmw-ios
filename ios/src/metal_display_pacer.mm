#import <QuartzCore/CAMetalDisplayLink.h>
#import <QuartzCore/CAAnimation.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <condition_variable>
#include <mutex>
#include <rex/cvar.h>
#include <rex/logging.h>
#include "metal_display_pacer.h"
#include "managed_frame_slots.h"
#include "battery.h"

REXCVAR_DEFINE_BOOL(nfsmw_native_metal_display_40, false, "GPU",
                    "Experiment: system Metal display-link drawables and timestamps at 40 fps "
                    "(restart required; primary display only)");

namespace {
std::mutex mutex;
std::condition_variable changed;
CAMetalLayer* attached = nil;             // under mutex
CAMetalDisplayLinkUpdate* pending = nil;  // one retained update at most
bool owns = false, active = true;
uint64_t generation = 0;
uint64_t guest_timestamp_ns = 0, guest_period_ns = 0;
double previous_target = 0;
nfsmw::ManagedFrameSlots world_slots;
uint64_t assigned_frames = 0;  // diagnostic sequence, under mutex; monotonic across restarts
unsigned frames = 0;
CAMetalDisplayLink* metal_link = nil;           // main thread only
bool Enabled() {
  static const bool enabled = REXCVAR_GET(nfsmw_native_metal_display_40);
  return enabled;
}
}  // namespace

@interface NFSMetalPacerDelegate : NSObject <CAMetalDisplayLinkDelegate>
@end
@implementation NFSMetalPacerDelegate
- (void)metalDisplayLink:(CAMetalDisplayLink*)sender needsUpdate:(CAMetalDisplayLinkUpdate*)update {
  if (sender != metal_link) return;
  // A menu cap may change between the ordinary display tick and this one.
  if (rex::cvar::Query<int32_t>("ios_fps_cap") != 40) {
    nfsmw::metal_pacer::Tick();
    return;
  }
  std::lock_guard<std::mutex> lock(mutex);
  if (!owns || !active) return;
  // Use the display link's system timestamp spacing, not callback arrival
  // jitter or integer subdivision of CADisplayLink (which may run at 80 Hz).
  // A missed callback spans several 25 ms slots; normalize it before /3.
  const double target = update.targetPresentationTimestamp;
  double cadence = .025;
  if (previous_target > 0 && target > previous_target) {
    const double gap = target - previous_target;
    cadence = gap / std::max(1.0, std::round(gap / .025));
  }
  previous_target = target;
  if (cadence >= .020 && cadence <= .030) {
    const double period = cadence / 3;
    const double now = CACurrentMediaTime();
    const double latest = target - std::ceil(std::max(0.0, target - now) / period) * period;
    guest_period_ns = uint64_t(std::llround(period * 1e9));
    guest_timestamp_ns = uint64_t(std::llround(latest * 1e9));
  }
  pending = update;  // replace an unused update; never queue stale frames
  changed.notify_all();
  static double last = 0;
  static uint32_t count = 0;
  if (++count % 120 == 0) {
    REXLOG_INFO("[metal-display-40] callback gap {:.2f} ms, target {:.2f} ms ahead, guest grid {:.4f} ms",
                last > 0 ? (CACurrentMediaTime() - last) * 1000 : 0,
                (update.targetPresentationTimestamp - CACurrentMediaTime()) * 1000,
                double(guest_period_ns) / 1e6);
  }
  last = CACurrentMediaTime();
}
@end

namespace nfsmw::metal_pacer {
namespace {
// Called on main with mutex held. Invalidate before releasing ownership:
// no new nextDrawable caller can overlap a live Metal display link.
void Stop() {
  if (metal_link) {
    [metal_link invalidate];
    metal_link.delegate = nil;
    metal_link = nil;
    REXLOG_INFO("[metal-display-40] stopped; legacy presentation available");
  }
  owns = false;
  pending = nil;
  guest_timestamp_ns = guest_period_ns = 0;
  previous_target = 0;
  world_slots.Reset();
  ++generation;
  changed.notify_all();
}
}  // namespace

void Attach(CAMetalLayer* layer) {
  if (!Enabled()) return;
  {
    std::lock_guard<std::mutex> lock(mutex);
    Stop();
    attached = layer;
  }
  Tick();
}

void SetActive(bool value) {
  if (!Enabled()) return;
  {
    std::lock_guard<std::mutex> lock(mutex);
    active = value;
    if (!value) Stop();  // wake renderer BEFORE lifecycle pauses guest threads
  }
  if (value) Tick();
}

void Tick() {
  if (!Enabled()) return;
  std::lock_guard<std::mutex> lock(mutex);
  const bool want = active && attached && rex::cvar::Query<int32_t>("ios_fps_cap") == 40;
  if (!want) {
    if (owns) Stop();
    return;
  }
  if (owns || frames != 0) return;  // retry next tick; never block main
  static NFSMetalPacerDelegate* delegate = [NFSMetalPacerDelegate new];
  metal_link = [[CAMetalDisplayLink alloc] initWithMetalLayer:attached];
  metal_link.delegate = delegate;
  metal_link.preferredFrameRateRange = CAFrameRateRangeMake(40, 40, 40);
  metal_link.preferredFrameLatency = 2;
  pending = nil;
  guest_timestamp_ns = guest_period_ns = 0;
  previous_target = 0;
  world_slots.Reset();
  ++generation;
  owns = true;
  [metal_link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
  REXLOG_INFO("[metal-display-40] started: 40 callbacks/s requested, latency 2; "
              "plain present when scheduled, system timing, guest vblank unchanged");
}

bool GuestGrid(uint64_t& timestamp_ns, uint64_t& period_ns) {
  if (!Enabled()) return false;
  std::lock_guard<std::mutex> lock(mutex);
  if (!owns || !active || !guest_period_ns ||
      rex::cvar::Query<int32_t>("ios_fps_cap") != 40) return false;
  timestamp_ns = guest_timestamp_ns;
  period_ns = guest_period_ns;
  return true;
}

uint32_t TakeMissedSlots(uint32_t maximum) {
  if (!Enabled()) return 0;
  std::lock_guard<std::mutex> lock(mutex);
  if (!maximum || !owns || !active || nfsmw::battery::InMenu() != 0 ||
      rex::cvar::Query<int32_t>("ios_fps_cap") != 40) {
    world_slots.Reset();
    return 0;
  }
  return world_slots.Take(maximum);
}

uint64_t AssignedFrames() {
  std::lock_guard<std::mutex> lock(mutex);
  return assigned_frames;
}

Frame::Frame(CAMetalLayer* layer) {
  if (!Enabled() || !layer) return;
  const auto start = std::chrono::steady_clock::now();
  std::unique_lock<std::mutex> lock(mutex);
  if (layer != attached) return;
  registered_ = true;
  ++frames;
  managed = owns;
  generation_ = generation;
  if (!managed) return;
  const auto deadline = start + std::chrono::milliseconds(100);
  while (owns && active && generation == generation_ &&
         rex::cvar::Query<int32_t>("ios_fps_cap") == 40) {
    if (pending) {
      if (pending.targetTimestamp > CACurrentMediaTime() + .001) {
        drawable = pending.drawable;
        presentation_time = pending.targetPresentationTimestamp;
        present_deadline = pending.targetTimestamp;
        // Count skipped assigned system slots, not raw main-loop stalls:
        // queued frames can still present evenly while the main loop catches up.
        world_slots.Assign(presentation_time, double(guest_period_ns * 3) / 1e9,
                           nfsmw::battery::InMenu() == 0);
        ++assigned_frames;
        pending = nil;
        break;
      }
      pending = nil;
    }
    if (changed.wait_until(lock, deadline) == std::cv_status::timeout) {
      static int lines = 12;
      if (lines-- > 0) REXLOG_WARN("[metal-display-40] no drawable callback in 100 ms; frame not presented");
      break;  // keep ownership: NEVER call nextDrawable as a timeout fallback
    }
  }
  wait_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
  static uint32_t acquisitions = 0;
  static double total_wait = 0, longest_wait = 0;
  total_wait += wait_ms;
  longest_wait = std::max(longest_wait, wait_ms);
  if (++acquisitions % 300 == 0) {
    REXLOG_INFO("[metal-display-40] drawable wait avg {:.2f} ms, max {:.2f} ms (300 frames)",
                total_wait / 300, longest_wait);
    total_wait = longest_wait = 0;
  }
}

Frame::~Frame() {
  if (!registered_) return;
  // Release the update's drawable before allowing a new owner to start.
  drawable = nil;
  std::lock_guard<std::mutex> lock(mutex);
  --frames;
}

bool Frame::Current() const {
  if (!managed) return true;
  std::lock_guard<std::mutex> lock(mutex);
  return owns && active && generation == generation_ &&
         rex::cvar::Query<int32_t>("ios_fps_cap") == 40;
}

void Scheduled(double deadline) {
  // Scheduling callback: compare actual scheduling time with targetTimestamp,
  // not the later estimated targetPresentationTimestamp.
  static std::mutex stats_mutex;
  std::lock_guard<std::mutex> lock(stats_mutex);
  static uint32_t count = 0, late = 0;
  static double worst = 0;
  const double after_ms = (CACurrentMediaTime() - deadline) * 1000;
  if (after_ms > 0) ++late;
  worst = std::max(worst, after_ms);
  if (++count % 300 == 0) {
    REXLOG_INFO("[metal-display-40] {} of 300 buffers scheduled after present deadline, worst {:.2f} ms",
                late, worst);
    late = 0;
    worst = 0;
  }
}

void Presented(double target, double shown) {
  // Metal may invoke these concurrently. Log actual system-target misses,
  // without tripping the legacy atTime watchdog used by the 30 fps path.
  static std::mutex stats_mutex;
  static uint32_t count = 0, missed = 0;
  static double worst = 0;
  std::lock_guard<std::mutex> lock(stats_mutex);
  const double delta = (shown - target) * 1000;
  if (shown <= 0 || std::fabs(delta) > 4) ++missed;
  if (shown > 0) worst = std::max(worst, std::fabs(delta));
  if (++count % 300 == 0) {
    REXLOG_INFO("[metal-display-40] {} of 300 presentations >4 ms from system target or dropped, "
                "worst {:.2f} ms", missed, worst);
    missed = 0;
    worst = 0;
  }
}
}  // namespace nfsmw::metal_pacer
