// NFSMW Recompiled - the display refresh rate the game asks iOS for

#pragma once

namespace nfsmw::display {

// Tells iOS which refresh rate suits the frame rate cap (ProMotion): 120 Hz
// for the 40 and 120 caps (40 fps is exactly 3 refreshes), 60 Hz otherwise.
// Main thread.
void RequestRateForCap(int fps_cap);

// --ios_display_match_cap: the display follows cap changes (Battery mode's 30).
bool MatchesCap();

}  // namespace nfsmw::display
