// Experimental 40 fps primary-display drawable delivery. Off by default.
#pragma once

#import <QuartzCore/CAMetalLayer.h>
#include <cstdint>

namespace nfsmw::metal_pacer {
// Main thread. Tick never waits for the renderer.
void Attach(CAMetalLayer* layer);
void Tick();
void SetActive(bool active);

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
  double presentation_time = 0;
  double wait_ms = 0;
 private:
  bool registered_ = false;
  uint64_t generation_ = 0;
};
void Presented(double target, double shown);
}  // namespace nfsmw::metal_pacer
