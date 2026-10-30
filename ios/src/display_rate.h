// NFSMW Recompiled - the display refresh rate the game asks iOS for

#pragma once

#include <cstdint>

namespace nfsmw::display {

// Tells iOS which refresh rate suits the frame rate cap (ProMotion): 120 Hz
// for the 40 and 120 caps (40 fps is exactly 3 refreshes), 60 Hz otherwise.
// Main thread.
void RequestRateForCap(int fps_cap);

// --ios_display_match_cap: the display follows cap changes (Battery mode's 30).
bool MatchesCap();

// The guest vblank's grid as last published (mach_absolute_time ns): a
// refresh time and the period; 0, 0 before the first. Any thread.
void LatestVblank(uint64_t& time_ns, uint64_t& period_ns);

// Full 40 fps frame duration while the experimental Metal link owns the
// primary display; 0 on the legacy paths. Any thread, no lock.
uint64_t ManagedFramePeriodNs();
// At most maximum skipped managed output slots; 0 resets debt/history.
uint32_t TakeManagedMissedSlots(uint32_t maximum);
uint64_t ManagedAssignedFrames();  // diagnostic render-assignment sequence

}  // namespace nfsmw::display
