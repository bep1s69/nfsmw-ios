#!/usr/bin/env python3
"""
Diagnostic: every 5 s the log says how many textures were loaded, how many of
those were reloads of a texture already loaded, and why they were outdated
(the GPU wrote their memory, i.e. a resolve, or the CPU did), with the textures
reloaded most.

    python3 tools/ios/patch_ios_texture_stats.py            apply
    python3 tools/ios/patch_ios_texture_stats.py --status
    python3 tools/ios/patch_ios_texture_stats.py --revert

Touches src/graphics/pipeline/texture/cache.cpp. Cvar ios_texture_stats
(off by default: turn on to measure).


WHY
===

A Metal System Trace in a race at the 120 fps cap (~70 fps, GPU-bound, GPU
busy 72 %): besides the game's own drawing (~6 ms a frame) there were ~45
vkCmdCopyBufferToImage and ~85 compute dispatches a frame, much of it texture
loads (untiling in a compute shader, then the copy into the image). A texture
is normally loaded once and watched; ~45 a frame means something keeps
outdating them. This says what.

Lines, [ios-textures]:
  5 s: N loads (R reloads), X MB; outdated by the GPU G, by the CPU C
  top reloads: WxH fmt F @address, n times (gpu g / cpu c) ...
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/pipeline/texture/cache.cpp"

INCLUDE_ANCHOR = '''#include <algorithm>
#include <cstdint>
#include <utility>
'''
INCLUDE_NEW = '''#include <algorithm>
#include <cstdint>
#include <utility>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: texture load statistics (tools/ios/patch_ios_texture_stats.py).
#include <chrono>
#include <unordered_map>
#include <vector>
#endif
'''

STATS_ANCHOR = '''bool TextureCache::CommitPreparedTextureLoad(const PendingTextureLoad& pending_load) {
'''
STATS_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: texture load statistics (tools/ios/patch_ios_texture_stats.py).
REXCVAR_DEFINE_BOOL(ios_texture_stats, false, "GPU",
                    "iOS: log texture loads, reloads and why textures were outdated, every 5 s");
namespace {
struct IosTexStat {
  uint32_t loads = 0, by_gpu = 0, by_cpu = 0;
  uint8_t last_reason = 0;  // 1 GPU, 2 CPU
  uint32_t width = 0, height = 0, format = 0, address = 0;
};
// Under the texture cache's global lock (both the watch callback and the load).
std::unordered_map<const void*, IosTexStat> ios_tex_stats;
struct IosTexWindow {
  uint32_t loads = 0, reloads = 0, by_gpu = 0, by_cpu = 0, scaled = 0;
  uint64_t bytes = 0;
  std::unordered_map<const void*, uint32_t> reloads_of;
  std::chrono::steady_clock::time_point since = std::chrono::steady_clock::now();
} ios_tex_window;
void IosTexOutdated(const void* texture, bool by_gpu) {
  if (!REXCVAR_GET(ios_texture_stats)) {
    return;
  }
  IosTexStat& s = ios_tex_stats[texture];
  s.last_reason = by_gpu ? 1 : 2;
  (by_gpu ? s.by_gpu : s.by_cpu)++;
  (by_gpu ? ios_tex_window.by_gpu : ios_tex_window.by_cpu)++;
}
}  // namespace
#endif

bool TextureCache::CommitPreparedTextureLoad(const PendingTextureLoad& pending_load) {
'''

LOAD_ANCHOR = '''  texture.MakeUpToDateAndWatch(global_critical_region_.Acquire());
  texture.LogAction("Loaded");
'''
LOAD_NEW = '''  texture.MakeUpToDateAndWatch(global_critical_region_.Acquire());
  texture.LogAction("Loaded");
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: texture load statistics (tools/ios/patch_ios_texture_stats.py).
  if (REXCVAR_GET(ios_texture_stats)) {
    auto lock = global_critical_region_.Acquire();
    IosTexStat& s = ios_tex_stats[&texture];
    const bool reload = s.loads != 0;
    ++s.loads;
    s.width = texture_key.GetWidth();
    s.height = texture_key.GetHeight();
    s.format = uint32_t(texture_key.format);
    s.address = texture_key.base_page << 12;
    IosTexWindow& w = ios_tex_window;
    ++w.loads;
    w.reloads += reload;
    w.scaled += texture_key.scaled_resolve;
    w.bytes += (pending_load.load_base ? texture.GetGuestBaseSize() : 0) +
               (pending_load.load_mips ? texture.GetGuestMipsSize() : 0);
    if (reload) {
      ++w.reloads_of[&texture];
    }
    const auto now = std::chrono::steady_clock::now();
    if (now - w.since >= std::chrono::seconds(5)) {
      REXGPU_INFO("[ios-textures] 5 s: {} loads ({} reloads, {} scaled resolve), {:.1f} MB; "
                  "outdated by the GPU {}, by the CPU {}; {} textures known",
                  w.loads, w.reloads, w.scaled, double(w.bytes) / (1024.0 * 1024.0), w.by_gpu,
                  w.by_cpu, ios_tex_stats.size());
      std::vector<std::pair<const void*, uint32_t>> top(w.reloads_of.begin(), w.reloads_of.end());
      std::sort(top.begin(), top.end(),
                [](const auto& a, const auto& b) { return a.second > b.second; });
      for (size_t i = 0; i < top.size() && i < 8; ++i) {
        const IosTexStat& t = ios_tex_stats[top[i].first];
        REXGPU_INFO("[ios-textures]   {}x{} fmt {} @{:08X}: {} reloads (ever: gpu {}, cpu {}, "
                    "last {})",
                    t.width, t.height, t.format, t.address, top[i].second, t.by_gpu, t.by_cpu,
                    t.last_reason == 1 ? "gpu" : t.last_reason == 2 ? "cpu" : "-");
      }
      w = IosTexWindow{};
    }
  }
#endif
'''

WATCH_ANCHOR = '''  Texture& texture = *static_cast<Texture*>(context);
  texture.WatchCallback(global_lock, argument != 0);
'''
WATCH_NEW = '''  Texture& texture = *static_cast<Texture*>(context);
  texture.WatchCallback(global_lock, argument != 0);
#if REX_PLATFORM_IOS
  IosTexOutdated(&texture, invalidated_by_gpu);  // LOCAL PATCH - iOS (patch_ios_texture_stats.py)
#endif
'''

BLOCKS = [
    (F, "includes", INCLUDE_ANCHOR, INCLUDE_NEW),
    (F, "the statistics", STATS_ANCHOR, STATS_NEW),
    (F, "count each load", LOAD_ANCHOR, LOAD_NEW),
    (F, "count each outdating", WATCH_ANCHOR, WATCH_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_texture_stats", BLOCKS))
