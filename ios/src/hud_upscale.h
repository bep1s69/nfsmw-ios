// NFSMW Recompiled (iOS) - HUD textures upscaled by a neural network, once
//
// The sharp HUD (native_renderer.mm) draws the HUD at the screen's pixels;
// its textures are small (32-512 px). MetalFX spatial gives them clean edges
// at once; this gives them detail: Real-ESRGAN x4 (anime 6B, BSD-3,
// xinntao/Real-ESRGAN; tools/ml/convert_realesrgan.py) on the Neural Engine,
// off the render thread, the result scaled to 2x and kept on disk
// (Caches/HudUpscale, by a hash of the texture's pixels), so that a texture
// is only ever upscaled once per install.
#pragma once

#import <Metal/Metal.h>

#include <cstdint>
#include <vector>

namespace nfsmw::hud_upscale {

// The model is in the app (HudUpscale.mlmodelc) and the setting is on.
bool Available();

// Render thread: `flat` (RGBA8, w x h, written earlier in `cb`) is read
// back when `cb` completes; its 2x upscale comes back from Take later.
void Request(const void* key, id<MTLTexture> flat, id<MTLCommandBuffer> cb);

struct Result {
  const void* key;
  uint32_t width, height;  // 2x the source
  std::vector<uint8_t> rgba;
};
// Render thread: the finished ones since the last call.
std::vector<Result> Take();

}  // namespace nfsmw::hud_upscale
