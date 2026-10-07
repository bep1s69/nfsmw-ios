// NFSMW Recompiled - a Metal GPU frame capture, from a button in the game

#pragma once

namespace nfsmw::gpu_capture {

// Puts a CAPTURE button in the top-right corner of the game's window. A tap
// records the GPU work of about two frames to
// Documents/captures/<date-time>.gputrace, to open in Xcode on a Mac (Metal
// debugger: per-pass GPU time, memory traffic, shaders). Needs
// MTL_CAPTURE_ENABLED=1 in the environment before Metal's device is created
// (ios_main.mm sets it when --ios_gpu_capture is on). Main thread.
void InstallButton();

}  // namespace nfsmw::gpu_capture
