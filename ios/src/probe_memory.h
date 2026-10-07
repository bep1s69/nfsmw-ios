// NFSMW Recompiled - guest memory diagnostics for the probe (probe_memory.cpp)

#pragma once

#include <string>
#include <vector>

// Repeats, step by step, how the SDK backs the ~4.5 GB guest memory, plus the
// Mach memory entry alternative. One report line per result, with errno.
std::vector<std::string> GuestMemoryDiagnostics();
