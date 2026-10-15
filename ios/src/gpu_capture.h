// NFSMW Recompiled - a Metal GPU frame capture, from a button in the game

#pragma once

#ifdef __OBJC__
@protocol MTLCommandQueue;
#endif

namespace nfsmw::gpu_capture {

// Puts a CAPTURE button in the top-right corner of the game's window. A tap
// requests one complete native frame (a timed device capture for Vulkan) to
// Documents/captures/<date-time>.gputrace, to open in Xcode on a Mac (Metal
// debugger: per-pass GPU time, memory traffic, shaders). Needs
// MTL_CAPTURE_ENABLED=1 in the environment before Metal's device is created
// (ios_main.mm sets it when --ios_gpu_capture is on). Main thread.
void InstallButton();

#ifdef __OBJC__
// Renderer queue only: begin before creating the frame's command buffers,
// end after committing them. Returns true only for a button-requested capture.
bool BeginNativeFrame(id<MTLCommandQueue> queue);
void EndNativeFrame();
#endif

}  // namespace nfsmw::gpu_capture
