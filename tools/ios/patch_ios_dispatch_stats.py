#!/usr/bin/env python3
"""
Diagnostic: every 5 s the log lists the compute dispatches by the function
that recorded them, with their thread group counts.

    python3 tools/ios/patch_ios_dispatch_stats.py            apply
    python3 tools/ios/patch_ios_dispatch_stats.py --status
    python3 tools/ios/patch_ios_dispatch_stats.py --revert

Touches include/rex/graphics/vulkan/deferred_command_buffer.h and
src/graphics/vulkan/deferred_command_buffer.cpp. Cvar ios_dispatch_stats (off by
default: turn on to measure).


WHY
===

A Metal System Trace in a race at ~95 fps: compute dispatches were 23 % of
the GPU's time, ~62 a frame, with no labels (resolves, texture loads, EDRAM
clears and transfers all look the same). DeferredCommandBuffer::CmdVkDispatch
is inline in each of the ~9 places that dispatch; it now calls a function
that is never inlined, whose return address is therefore in the function that
dispatched. The log names it with dladdr and gives its offset in the GPU
plugin, for atos if the name is not exported:

  [ios-dispatch] 5 s: N dispatches
  [ios-dispatch]   n  groups G  Function (librexgpu-xenos.dylib+0xOFFSET)
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

H = "include/rex/graphics/vulkan/deferred_command_buffer.h"
CPP = "src/graphics/vulkan/deferred_command_buffer.cpp"

H_DECL_ANCHOR = '''namespace rex::graphics::vulkan {

class VulkanCommandProcessor;
'''
H_DECL_NEW = '''namespace rex::graphics::vulkan {

class VulkanCommandProcessor;

#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: compute dispatch statistics (tools/ios/patch_ios_dispatch_stats.py).
void IosCountDispatch(uint64_t groups);
#endif
'''

H_CALL_ANCHOR = '''  void CmdVkDispatch(uint32_t group_count_x, uint32_t group_count_y, uint32_t group_count_z) {
'''
H_CALL_NEW = '''  void CmdVkDispatch(uint32_t group_count_x, uint32_t group_count_y, uint32_t group_count_z) {
#if REX_PLATFORM_IOS
    IosCountDispatch(uint64_t(group_count_x) * group_count_y * group_count_z);
#endif
'''

CPP_ANCHOR = '''namespace rex::graphics::vulkan {
'''
CPP_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: compute dispatch statistics (tools/ios/patch_ios_dispatch_stats.py).
#include <dlfcn.h>
#include <chrono>
#include <unordered_map>
#include <vector>
#include <rex/logging.h>
REXCVAR_DEFINE_BOOL(ios_dispatch_stats, false, "GPU",
                    "iOS: log compute dispatches by the function that recorded them, every 5 s");
#endif

namespace rex::graphics::vulkan {

#if REX_PLATFORM_IOS
// Never inlined: the return address is in the function whose inline
// CmdVkDispatch called this. Command processor thread only.
__attribute__((noinline)) void IosCountDispatch(uint64_t groups) {
  if (!REXCVAR_GET(ios_dispatch_stats)) {
    return;
  }
  struct Site {
    uint32_t count = 0;
    uint64_t groups = 0;
  };
  static std::unordered_map<const void*, Site> sites;
  static uint32_t total = 0;
  static auto since = std::chrono::steady_clock::now();
  const void* caller = __builtin_extract_return_addr(__builtin_return_address(0));
  Site& site = sites[caller];
  ++site.count;
  site.groups += groups;
  ++total;
  const auto now = std::chrono::steady_clock::now();
  if (now - since < std::chrono::seconds(5)) {
    return;
  }
  // Grouped by function (several return addresses can be in one).
  struct Function {
    uint32_t count = 0;
    uint64_t groups = 0;
    std::string where;
  };
  std::unordered_map<std::string, Function> functions;
  for (const auto& [address, s] : sites) {
    Dl_info info = {};
    std::string name = "?";
    uintptr_t offset = 0;
    if (dladdr(address, &info) && info.dli_fbase) {
      offset = uintptr_t(address) - uintptr_t(info.dli_fbase);
      name = info.dli_sname ? info.dli_sname : "?";
    }
    const char* file = info.dli_fname ? std::strrchr(info.dli_fname, '/') : nullptr;
    Function& f = functions[name];
    f.count += s.count;
    f.groups += s.groups;
    if (f.where.empty()) {
      f.where = fmt::format("{}+0x{:X}", file ? file + 1 : "?", offset);
    }
  }
  std::vector<std::pair<std::string, Function>> sorted(functions.begin(), functions.end());
  std::sort(sorted.begin(), sorted.end(),
            [](const auto& a, const auto& b) { return a.second.count > b.second.count; });
  REXGPU_INFO("[ios-dispatch] 5 s: {} dispatches", total);
  for (const auto& [name, f] : sorted) {
    REXGPU_INFO("[ios-dispatch]   {:6d}  groups {:9d}  {} ({})", f.count, f.groups,
                name.substr(0, 100), f.where);
  }
  sites.clear();
  total = 0;
  since = now;
}
#endif
'''

BLOCKS = [
    (H, "declare the counter", H_DECL_ANCHOR, H_DECL_NEW),
    (H, "count each dispatch", H_CALL_ANCHOR, H_CALL_NEW),
    (CPP, "the counter", CPP_ANCHOR, CPP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_dispatch_stats", BLOCKS))
