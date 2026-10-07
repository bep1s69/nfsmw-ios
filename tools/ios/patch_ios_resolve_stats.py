#!/usr/bin/env python3
"""
Diagnostic: every 5 s the log lists the kinds of resolve that cost the most
EDRAM dumping (copying host render targets into the EDRAM buffer before the
resolve shader reads it), with their size, destination and render targets.

    python3 tools/ios/patch_ios_resolve_stats.py            apply
    python3 tools/ios/patch_ios_resolve_stats.py --status
    python3 tools/ios/patch_ios_resolve_stats.py --revert

Touches src/graphics/vulkan/render_target_cache.cpp. Cvar ios_resolve_stats
(off: turn on to measure).


WHY
===

patch_ios_dispatch_stats.py in a race: DumpRenderTargets dispatched ~68,000
thread groups a frame. A group is 8x16 samples, so ~8.7 million samples a
frame went into the EDRAM buffer: about 12 times a 960x720 screen, far more
than the ~20 resolves a frame should need even with the 1600x1600 shadow map.
Before writing the SDK's unfinished direct resolve (TryResolveCopyDirectly is
a stub that always dumps), this says which resolves dump what:

  [ios-resolve] 5 s: N resolves, G dump groups (S M samples)
  [ios-resolve]   n x  WxH -> D KB  dump: format pitch msaa, rectangles: G groups
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/vulkan/render_target_cache.cpp"

TOP_ANCHOR = '''namespace rex::graphics::vulkan {
'''
TOP_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: resolve statistics (tools/ios/patch_ios_resolve_stats.py).
#include <chrono>
#include <map>
#include <string>
#include <vector>
#include <rex/cvar.h>
REXCVAR_DEFINE_BOOL(ios_resolve_stats, true, "GPU",
                    "iOS: log the kinds of resolve that cost the most EDRAM dumping, every 5 s");
namespace {
struct IosResolveKind {
  uint32_t count = 0;
  uint64_t groups = 0;
};
std::map<std::string, IosResolveKind> ios_resolve_kinds;  // command processor only
std::string ios_resolve_current;                           // the resolve being dumped
uint32_t ios_resolve_total = 0;
uint64_t ios_resolve_groups = 0;
std::chrono::steady_clock::time_point ios_resolve_since = std::chrono::steady_clock::now();
void IosResolveLog() {
  const auto now = std::chrono::steady_clock::now();
  if (now - ios_resolve_since < std::chrono::seconds(5)) {
    return;
  }
  REXGPU_INFO("[ios-resolve] 5 s: {} resolves, {} dump groups ({:.1f} M samples)",
              ios_resolve_total, ios_resolve_groups, double(ios_resolve_groups) * 128 / 1e6);
  std::vector<std::pair<std::string, IosResolveKind>> sorted(ios_resolve_kinds.begin(),
                                                             ios_resolve_kinds.end());
  std::sort(sorted.begin(), sorted.end(),
            [](const auto& a, const auto& b) { return a.second.groups > b.second.groups; });
  for (size_t i = 0; i < sorted.size() && i < 14; ++i) {
    REXGPU_INFO("[ios-resolve]   {:5d} x  {}: {} groups", sorted[i].second.count,
                sorted[i].first, sorted[i].second.groups);
  }
  ios_resolve_kinds.clear();
  ios_resolve_total = 0;
  ios_resolve_groups = 0;
  ios_resolve_since = now;
}
}  // namespace
#endif

namespace rex::graphics::vulkan {
'''

RESOLVE_ANCHOR = '''  // Nothing to copy/clear.
  if (!resolve_info.coordinate_info.width_div_8 || !resolve_info.height_div_8) {
    return true;
  }
'''
RESOLVE_NEW = '''  // Nothing to copy/clear.
  if (!resolve_info.coordinate_info.width_div_8 || !resolve_info.height_div_8) {
    return true;
  }
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: resolve statistics (tools/ios/patch_ios_resolve_stats.py).
  if (REXCVAR_GET(ios_resolve_stats)) {
    ios_resolve_current = fmt::format(
        "{}x{} -> {} KB", resolve_info.coordinate_info.width_div_8 * 8,
        resolve_info.height_div_8 * 8, resolve_info.copy_dest_extent_length >> 10);
    ++ios_resolve_total;
  }
#endif
'''

DUMP_ANCHOR = '''    MarkEdramBufferModified();
  }
  return all_pipelines_available;
}
'''
DUMP_NEW = '''    MarkEdramBufferModified();
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: resolve statistics (tools/ios/patch_ios_resolve_stats.py).
    if (REXCVAR_GET(ios_resolve_stats)) {
      uint64_t groups = 0;
      for (uint32_t i = 0; i < dispatch_count; ++i) {
        groups += uint64_t((draw_resolution_scale_x() *
                                (xenos::kEdramTileWidthSamples >> uint32_t(rt_key.Is64bpp())) *
                                dispatches[i].width_tiles +
                            (kDumpSamplesPerGroupX - 1)) /
                           kDumpSamplesPerGroupX) *
                  ((draw_resolution_scale_y() * xenos::kEdramTileHeightSamples *
                        dispatches[i].height_tiles +
                    (kDumpSamplesPerGroupY - 1)) /
                   kDumpSamplesPerGroupY);
      }
      const std::string kind =
          fmt::format("{} | dump {} {} pitch {}t msaa {} base {} rows {}", ios_resolve_current,
                      rt_key.is_depth ? "depth" : "color", rt_key.GetFormatName(),
                      uint32_t(rt_key.GetPitchTiles()), uint32_t(rt_key.msaa_samples),
                      uint32_t(rt_key.base_tiles), uint32_t(rectangle.rows));
      IosResolveKind& k = ios_resolve_kinds[kind];
      ++k.count;
      k.groups += groups;
      ios_resolve_groups += groups;
    }
#endif
  }
#if REX_PLATFORM_IOS
  if (REXCVAR_GET(ios_resolve_stats)) {
    IosResolveLog();
  }
#endif
  return all_pipelines_available;
}
'''

BLOCKS = [
    (F, "the statistics", TOP_ANCHOR, TOP_NEW),
    (F, "name the resolve", RESOLVE_ANCHOR, RESOLVE_NEW),
    (F, "count each dump", DUMP_ANCHOR, DUMP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_resolve_stats", BLOCKS))
