// NFSMW Recompiled - where the app's memory goes (iOS)

#pragma once

namespace nfsmw::memory {

// One "[memory]" log line: the footprint iOS counts against the app's limit,
// how much of the limit is left, and the parts of it (GPU, malloc,
// compressed).
void Report(const char* stage);

// The device's thermal state ("nominal", "fair", "serious", "critical").
const char* ThermalState();

// One "[cpu]" log line: the share of a core each of the busiest threads used
// since the last one, and the battery level.
void ReportCpu();

// Battery mode: at the 60 cap, 30 fps while Low Power Mode is on or the
// phone is warm (cvar nfsmw_battery_auto_cap), checked every 2 s.
void StartBatteryAutoCap();

// A Report and a ReportCpu every `seconds` from a thread of its own, whatever
// the renderer.
void StartPeriodicReports(int seconds);

}  // namespace nfsmw::memory
