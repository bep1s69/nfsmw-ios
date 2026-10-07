// NFSMW Recompiled - the Objective-C side of the probe (probe_apple.mm)
//
// The probe (probe.cpp) is C++: vulkan.hpp does not compile as Objective-C++
// with ARC (the CAMetalLayer* in VkMetalSurfaceCreateInfoEXT becomes a strong
// pointer and the struct stops being trivial). What it needs from UIKit and
// Metal lives here, behind C++ functions.

#pragma once

#include <string>
#include <vector>

struct SDL_Window;

namespace nfsmw::apple {

// iOS version, RAM, memory iOS lets the app use and the process address
// space. One report line per item.
std::vector<std::string> SystemInfo();

// What Metal says about the GPU, without going through MoltenVK (BC included).
std::vector<std::string> MetalInfo();

// The text, full screen, on top of the SDL window.
void ShowText(SDL_Window* window, const std::string& text);

}  // namespace nfsmw::apple
