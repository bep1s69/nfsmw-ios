// NFSMW Recompiled - the Objective-C side of the probe (see probe_apple.h)

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <UIKit/UIKit.h>

#include <mach/mach.h>
#include <os/proc.h>

#include <SDL3/SDL_properties.h>
#include <SDL3/SDL_video.h>
#include <fmt/format.h>

#include "probe_apple.h"

namespace nfsmw::apple {

namespace {

std::string Gb(uint64_t bytes) { return fmt::format("{:.2f} GB", bytes / 1073741824.0); }

}  // namespace

std::vector<std::string> SystemInfo() {
  std::vector<std::string> l;
  NSProcessInfo* p = NSProcessInfo.processInfo;
  l.push_back(fmt::format("iOS {}", p.operatingSystemVersionString.UTF8String));
  l.push_back(fmt::format("Device RAM: {}", Gb(p.physicalMemory)));
  // What is left before iOS kills the app (jetsam). The
  // increased-memory-limit entitlement raises it.
  l.push_back(fmt::format("Memory available to the app: {}", Gb(os_proc_available_memory())));
  task_vm_info_data_t vm{};
  mach_msg_type_number_t n = TASK_VM_INFO_COUNT;
  if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&vm), &n) ==
      KERN_SUCCESS) {
    // The address-space ceiling. The SDK reserves ~4.5 GB contiguous.
    l.push_back(fmt::format("Address space: 0x{:X} - 0x{:X} ({})", vm.min_address,
                            vm.max_address, Gb(vm.max_address - vm.min_address)));
  }
  return l;
}

std::vector<std::string> MetalInfo() {
  std::vector<std::string> l;
  id<MTLDevice> mtl = MTLCreateSystemDefaultDevice();
  if (!mtl) {
    l.push_back("Metal: no device");
    return l;
  }
  l.push_back(fmt::format("Metal: {}", mtl.name.UTF8String));
  l.push_back(fmt::format("Metal: BC (supportsBCTextureCompression) = {}",
                          mtl.supportsBCTextureCompression ? "yes" : "NO"));
  l.push_back(fmt::format("Metal: Apple9 family = {}",
                          [mtl supportsFamily:MTLGPUFamilyApple9] ? "yes" : "no"));
  l.push_back(fmt::format("Metal: recommended GPU working set = {}",
                          Gb(mtl.recommendedMaxWorkingSetSize)));
  return l;
}

void ShowText(SDL_Window* window, const std::string& text) {
  UIWindow* uiwindow = (__bridge UIWindow*)SDL_GetPointerProperty(
      SDL_GetWindowProperties(window), SDL_PROP_WINDOW_UIKIT_WINDOW_POINTER, nullptr);
  UIView* root = uiwindow.rootViewController.view;
  if (!root) {
    return;
  }
  UITextView* view = [[UITextView alloc] initWithFrame:root.bounds];
  view.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
  view.editable = NO;
  view.backgroundColor = UIColor.blackColor;
  view.textColor = UIColor.whiteColor;
  view.font = [UIFont monospacedSystemFontOfSize:12 weight:UIFontWeightRegular];
  view.textContainerInset = UIEdgeInsetsMake(24, 48, 24, 48);
  view.text = [NSString stringWithUTF8String:text.c_str()];
  [root addSubview:view];
}

}  // namespace nfsmw::apple
