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
// back when `cb` completes; its 2x upscale comes back from Take later. With a
// content hash (the decoded texture's level 0, ContentHash), a copy prepared
// ahead of time (ui_texture_prep.mm) is used instead when there is one.
void Request(const void* key, id<MTLTexture> flat, id<MTLCommandBuffer> cb, uint64_t content_hash = 0);

struct Result {
  const void* key;
  uint32_t width, height;  // 2x the source
  std::vector<uint8_t> rgba;
  bool prepared = false;  // from the ahead-of-time set: not swizzled yet
  bool plain = false;     // soft or photographic art: draw the original texture (no rgba)
};

// The key of a texture's decoded level 0 (untiled, byte-swapped blocks, as
// the native renderer's decoder writes them): same on the device and at
// preparation.
uint64_t ContentHash(const uint8_t* p, size_t n);
// Any thread (serialized): w x h RGBA8 to 2w x 2h with the network.
bool UpscaleRgba(const std::vector<uint8_t>& in, uint32_t w, uint32_t h, std::vector<uint8_t>& out);
// The prepared copy's file for a content hash.
NSURL* PreparedFile(uint64_t content_hash, uint32_t w, uint32_t h);
void SavePngFile(NSURL* url, uint32_t w, uint32_t h, const std::vector<uint8_t>& rgba);
bool ModelPresent();
// Render thread: the finished ones since the last call.
std::vector<Result> Take();

}  // namespace nfsmw::hud_upscale
