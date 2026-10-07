// NFSMW Recompiled - startup trace on iOS (see boot_trace.cpp)

#pragma once

#include <string>

namespace nfsmw::boot {

// Opens (appends to) the trace file and installs the crash hooks. Call first.
void Open(const std::string& path);

// One line, written and handed to the kernel at once: it survives a crash or
// a hang right after it.
void Trace(const std::string& line);

// Off: Trace writes nothing more (the launcher's Logging switch).
void SetEnabled(bool enabled);

}  // namespace nfsmw::boot
