// Experimental 40 fps primary-display drawable delivery. Off by default.
#pragma once

#import <QuartzCore/CAMetalLayer.h>
#include <cstdint>

namespace nfsmw::metal_pacer {
// Main thread. Tick never waits for the renderer.
void Attach(CAMetalLayer* layer);
void Tick();
void SetActive(bool active);
// Virtual 120 Hz grid derived from the managed 40 fps system cadence.
// Avoid integer subdivision of a separate display link running at 80 Hz.
// Same mach_absolute_time clock as CACurrentMediaTime, nanoseconds.
bool GuestGrid(uint64_t& timestamp_ns, uint64_t& period_ns);
// Consume skipped output slots for bounded world catch-up; maximum=0 resets.
uint32_t TakeMissedSlots(uint32_t maximum);

// A render-queue frame lease. Legacy frames are counted too, so the main
// thread starts display-link ownership only between nextDrawable users.
class Frame {
 public:
  explicit Frame(CAMetalLayer* layer);
  ~Frame();
  Frame(const Frame&) = delete;
  Frame& operator=(const Frame&) = delete;
  bool Current() const;
  bool managed = false;
  id<CAMetalDrawable> drawable = nil;
  double presentation_time = 0;  // estimated display time; diagnostics only
  double present_deadline = 0;  // deadline to commit and call plain present
  double wait_ms = 0;
 private:
  bool registered_ = false;
  uint64_t generation_ = 0;
};
void Scheduled(double deadline);
void Presented(double target, double shown);
}  // namespace nfsmw::metal_pacer
