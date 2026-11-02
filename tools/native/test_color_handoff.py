#!/usr/bin/env python3
"""Check the colour handoff's image ownership against the actual GpuPool on the host.

The production GpuPool/FrameDoneOnGpu text is compiled with ARC and ASan/UBSan
over a real Metal device (no game, no rendering). The harness replays the
handoff sequence of RenderFrame (target image leased from the pool, handed to
its resolve, the same address overwritten later in the frame, target resizes)
with randomized GPU completion lag, and checks that an image still owned by
the target, a kept resolve or an unfinished frame is never handed out again,
that the per-kind bound holds and that residency changes are not duplicated.
It mirrors the renderer's sequence; it does not run the renderer itself.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SDK = Path("/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk")
HARNESS = r'''
#define FMT_HEADER_ONLY
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <fmt/format.h>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdio>
#include <deque>
#include <map>
#include <random>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>
namespace residency {
std::map<const void*, int> resident;
size_t adds = 0, removes = 0;
void Add(id o) { if (!o) return; ++adds; assert(++resident[(__bridge const void*)o] == 1); }
void Remove(id o) { if (!o) return; ++removes; assert(--resident[(__bridge const void*)o] == 0); }
}  // namespace residency
static id<MTLTexture> NewTexture(id<MTLDevice> device, MTLTextureDescriptor* d, const char*) {
  return [device newTextureWithDescriptor:d];
}
@POOL@
static uint32_t Most(NSUInteger w, NSUInteger h) {  // as handoff_most
  return uint32_t(std::min<uint64_t>(4, (uint64_t(128) << 20) / std::max<uint64_t>(uint64_t(w) * h * 4, 1)));
}
static MTLTextureDescriptor* Desc(id<MTLDevice>, NSUInteger w, NSUInteger h, MTLTextureUsage usage) {
  MTLTextureDescriptor* d = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                              width:w height:h mipmapped:NO];
  d.usage = usage;
  d.storageMode = MTLStorageModePrivate;
  return d;
}
int main() {
  @autoreleasepool {
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    assert(device);
    std::mt19937 rng(7);
    const MTLTextureUsage target_usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead |
                                         MTLTextureUsagePixelFormatView;
    const MTLTextureUsage post_usage = MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView;
    const NSUInteger widths[] = {286, 240, 160};  // small images: same protocol, quick on the host
    NSUInteger w = widths[0], h = 132;
    id<MTLTexture> color = gpu_pool.Texture(device, Desc(device, w, h, target_usage), 0, Most(w, h));
    bool pooled = true;
    size_t standalone = 0, adopted = 0;
    assert(color);
    std::unordered_map<uint32_t, id<MTLTexture>> kept;   // kept_resolves
    std::map<uint32_t, std::vector<id>> in_flight;       // each frame's encoded images
    uint64_t handoffs = 0, misses = 0, overwrites = 0, resizes = 0;
    uint32_t most_live = 0;
    const uint32_t frames = 20000;
    for (uint32_t number = 1; number <= frames; ++number) {
      gpu_pool.Reclaim(number);
      if (rng() % 97 == 0) {  // another size: the target's image back to the pool after this frame
        if (pooled) gpu_pool.Retire(color, number); else residency::Remove(color);
        w = widths[rng() % 3];
        color = gpu_pool.Texture(device, Desc(device, w, h, target_usage), 0, Most(w, h));
        pooled = color != nil;
        if (!color) {  // the pool has its most of the kind: made on its own, as with the setting off
          color = NewTexture(device, Desc(device, w, h, target_usage), "");
          residency::Add(color);
          ++standalone;
        }
        ++resizes;
      } else if (!pooled) {  // the same size next frame: adopted when the pool has room, never remade
        pooled = gpu_pool.Adopt(color, Most(w, h));
        adopted += pooled;
      }
      auto& refs = in_flight[number];
      refs.push_back(color);  // the scene's passes draw into it
      auto owned = [&](id o) {
        if (o == color) return true;
        for (auto& [a, k] : kept) if (k == o) return true;
        for (auto& [f, list] : in_flight)
          for (id r : list) if (r == o) return true;
        return false;
      };
      MTLTextureDescriptor* nd = Desc(device, w, h, target_usage);
      id<MTLTexture> next = pooled ? gpu_pool.Texture(device, nd, 0, Most(w, h)) : nil;
      id<MTLTexture> dest;
      if (next) {
        assert(!owned(next));
        dest = color;
        color = next;
        ++handoffs;
      } else {
        dest = gpu_pool.Texture(device, Desc(device, w, h, post_usage));  // the normal copy's
        assert(!owned(dest));
        ++misses;
      }
      const std::string kind = fmt::format("t {} {} {}x{}x{} {} {} {}", uint64_t(nd.textureType), uint64_t(nd.pixelFormat),
                                           nd.width, nd.height, nd.depth, uint64_t(nd.usage), uint64_t(nd.storageMode), 0);
      assert(gpu_pool.live[kind] <= Most(w, h));
      most_live = std::max(most_live, gpu_pool.live[kind]);
      refs.push_back(dest);
      if (auto old = kept.find(0x09689000); old != kept.end() && old->second != dest) gpu_pool.Retire(old->second, number);
      kept[0x09689000] = dest;
      // The post resolve to the same address later in the frame.
      if (rng() % 8) {
        id<MTLTexture> post = gpu_pool.Texture(device, Desc(device, w, h, post_usage));
        assert(!owned(post));
        refs.push_back(post);
        gpu_pool.Retire(kept[0x09689000], number);
        kept[0x09689000] = post;
        ++overwrites;
      }
      // The GPU finishes frames in order, behind the encoding.
      const uint32_t lag = rng() % 10 ? 1 + rng() % 3 : 1 + rng() % 16;  // mostly 1-3, at times 16
      if (number > lag) {
        FrameDoneOnGpu(number - lag);
        in_flight.erase(in_flight.begin(), in_flight.upper_bound(gpu_frames_done.load()));
      }
    }
    for (auto& [k, n] : gpu_pool.live) assert(n <= 64);
    // Every pool object resident exactly once; nothing else made resident.
    size_t resident = 0;
    for (auto& [o, n] : residency::resident) { assert(n == 0 || n == 1); resident += n; }
    assert(residency::adds == gpu_pool.made + standalone);
    assert(resident == gpu_pool.keys.size() + (pooled ? 0 : 1));
    std::printf("PASS %u frames: %llu handoffs, %llu pool misses copied, %llu same-address overwrites, "
                "%llu resizes (%zu made outside a full pool, %zu adopted); pool made %u, reused %u, "
                "at most %u target images of a kind\n",
                frames, handoffs, misses, overwrites, resizes, standalone, adopted, gpu_pool.made, gpu_pool.reused,
                most_live);
  }
  return 0;
}
'''


def main():
    source = (ROOT / "ios/src/native_renderer.mm").read_text()
    pool = source[source.index("std::atomic<uint32_t> gpu_frames_done{0};"):
                  source.index("GpuPool gpu_pool;") + len("GpuPool gpu_pool;")]
    # The OFF path: the setting is read once and gates every handoff change.
    assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_color_handoff, false,' in source
    assert "const bool color_handoff = color_handoff_setting && !dump && lazy_diagnostics" in source
    assert "if (color_handoff) pitch = plan_handoff(" in source
    assert "if (src.handoff_resolve == int32_t(&ev - frame->resolves.data()))" in source
    with tempfile.TemporaryDirectory(prefix="nfsmw-color-handoff-") as temp:
        temp = Path(temp)
        cpp = temp / "test.mm"
        cpp.write_text(HARNESS.replace("@POOL@", pool))
        exe = temp / "test"
        subprocess.run(["xcrun", "clang++", "-std=c++20", "-O1", "-fobjc-arc", "-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer", "-I", str(SDK / "thirdparty/fmt/include"),
                        "-framework", "Foundation", "-framework", "Metal", str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
