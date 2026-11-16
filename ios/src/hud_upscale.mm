// NFSMW Recompiled (iOS) - HUD textures upscaled by a neural network, once.
// See hud_upscale.h.

#include "hud_upscale.h"

#import <CoreML/CoreML.h>
#import <Foundation/Foundation.h>
#import <ImageIO/ImageIO.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

#include <algorithm>
#include <chrono>
#include <cmath>
#include <mutex>
#include <string>

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_native_hud_ai, true, "GPU",
                    "Native renderer: with the sharp HUD, its textures also upscaled by a neural network "
                    "(Real-ESRGAN, on the device, once, kept on disk)");

namespace nfsmw::hud_upscale {
namespace {

std::mutex g_lock;
std::vector<Result> g_done;
dispatch_queue_t Queue() {
  static dispatch_queue_t q = dispatch_queue_create("nfsmw.hud-upscale", dispatch_queue_attr_make_with_qos_class(
                                                                             DISPATCH_QUEUE_SERIAL, QOS_CLASS_UTILITY, 0));
  return q;
}

NSURL* ModelURL() {
  return [NSBundle.mainBundle URLForResource:@"HudUpscale" withExtension:@"mlmodelc"];
}

// Serial queue only.
MLModel* Model() {
  static MLModel* model = nil;
  static bool tried = false;
  if (tried) return model;
  tried = true;
  NSURL* url = ModelURL();
  if (!url) return nil;
  MLModelConfiguration* config = [MLModelConfiguration new];
  config.computeUnits = MLComputeUnitsAll;
  NSError* error = nil;
  model = [MLModel modelWithContentsOfURL:url configuration:config error:&error];
  if (!model) REXLOG_WARN("[hud-ai] model: {}", error.localizedDescription.UTF8String);
  else REXLOG_INFO("[hud-ai] model loaded");
  return model;
}

NSURL* CacheDir() {
  static NSURL* dir = [] {
    NSURL* caches = [NSFileManager.defaultManager URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject;
    NSURL* d = [caches URLByAppendingPathComponent:@"HudUpscale" isDirectory:YES];
    [NSFileManager.defaultManager createDirectoryAtURL:d withIntermediateDirectories:YES attributes:nil error:nil];
    return d;
  }();
  return dir;
}

uint64_t Hash(const uint8_t* p, size_t n) {
  uint64_t h = 1469598103934665603ull;
  for (size_t i = 0; i < n; ++i) h = (h ^ p[i]) * 1099511628211ull;
  return h;
}

bool Supported(uint32_t v) { return v >= 8 && v <= 1024; }

constexpr uint32_t kTile = 128, kMargin = 8, kCore = kTile - 2 * kMargin;  // the model's one input size

bool LoadPng(NSURL* url, uint32_t w, uint32_t h, std::vector<uint8_t>& out) {
  CGImageSourceRef src = CGImageSourceCreateWithURL((__bridge CFURLRef)url, nullptr);
  if (!src) return false;
  CGImageRef image = CGImageSourceCreateImageAtIndex(src, 0, nullptr);
  CFRelease(src);
  if (!image) return false;
  bool ok = CGImageGetWidth(image) == w && CGImageGetHeight(image) == h;
  if (ok) {
    out.assign(size_t(w) * h * 4, 0);
    CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = CGBitmapContextCreate(out.data(), w, h, 8, w * 4, cs,
                                             kCGImageAlphaPremultipliedLast | kCGBitmapByteOrder32Big);
    CGColorSpaceRelease(cs);
    ok = ctx != nullptr;
    if (ctx) {
      CGContextSetBlendMode(ctx, kCGBlendModeCopy);
      CGContextDrawImage(ctx, CGRectMake(0, 0, w, h), image);
      CGContextRelease(ctx);
      // Back to straight alpha (the game's textures are not premultiplied).
      for (size_t i = 0; i < out.size(); i += 4) {
        const uint32_t a = out[i + 3];
        if (a && a < 255)
          for (int c = 0; c < 3; ++c) out[i + c] = uint8_t(std::min<uint32_t>(255, (out[i + c] * 255 + a / 2) / a));
      }
    }
  }
  CGImageRelease(image);
  return ok;
}

void SavePng(NSURL* url, uint32_t w, uint32_t h, const std::vector<uint8_t>& rgba) {
  CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
  CGDataProviderRef provider = CGDataProviderCreateWithData(nullptr, rgba.data(), rgba.size(), nullptr);
  CGImageRef image = CGImageCreate(w, h, 8, 32, w * 4, cs, kCGImageAlphaLast | kCGBitmapByteOrder32Big, provider,
                                   nullptr, false, kCGRenderingIntentDefault);
  CGDataProviderRelease(provider);
  CGColorSpaceRelease(cs);
  if (!image) return;
  NSURL* tmp = [url URLByAppendingPathExtension:@"part"];
  CGImageDestinationRef dst =
      CGImageDestinationCreateWithURL((__bridge CFURLRef)tmp, (__bridge CFStringRef)UTTypePNG.identifier, 1, nullptr);
  if (dst) {
    CGImageDestinationAddImage(dst, image, nullptr);
    if (CGImageDestinationFinalize(dst)) {
      [NSFileManager.defaultManager removeItemAtURL:url error:nil];
      [NSFileManager.defaultManager moveItemAtURL:tmp toURL:url error:nil];
    }
    CFRelease(dst);
  }
  CGImageRelease(image);
}

// Serial queue: w x h RGBA8 in, 2w x 2h RGBA8 out. The model takes 128x128
// tiles: each covers 112x112 of the texture plus 8 px on every side (edges
// repeated), and only its middle is kept, so tiles meet without seams. Its 4x
// colour is averaged 2x2; the alpha is scaled up bilinearly.
bool Upscale(const std::vector<uint8_t>& in, uint32_t w, uint32_t h, std::vector<uint8_t>& out) {
  MLModel* model = Model();
  if (!model || !Supported(w) || !Supported(h)) return false;
  NSError* error = nil;
  MLMultiArray* x = [[MLMultiArray alloc] initWithShape:@[ @1, @3, @(kTile), @(kTile) ]
                                               dataType:MLMultiArrayDataTypeFloat32
                                                  error:&error];
  if (!x) return false;
  const uint32_t ow = 2 * w, oh = 2 * h;
  out.assign(size_t(ow) * oh * 4, 0);
  float* xp = static_cast<float*>(x.dataPointer);
  const size_t plane = size_t(kTile) * kTile;
  for (uint32_t ty = 0; ty < h; ty += kCore) {
    for (uint32_t tx = 0; tx < w; tx += kCore) {
      for (uint32_t yy = 0; yy < kTile; ++yy) {
        const uint32_t sy = uint32_t(std::clamp(int(ty + yy) - int(kMargin), 0, int(h) - 1));
        for (uint32_t xx = 0; xx < kTile; ++xx) {
          const uint32_t sx = uint32_t(std::clamp(int(tx + xx) - int(kMargin), 0, int(w) - 1));
          const uint8_t* p = &in[(size_t(sy) * w + sx) * 4];
          for (int c = 0; c < 3; ++c) xp[c * plane + size_t(yy) * kTile + xx] = p[c] / 255.0f;
        }
      }
      MLDictionaryFeatureProvider* features =
          [[MLDictionaryFeatureProvider alloc] initWithDictionary:@{@"image" : x} error:&error];
      if (!features) return false;
      id<MLFeatureProvider> result = [model predictionFromFeatures:features error:&error];
      MLMultiArray* y = [result featureValueForName:@"upscaled"].multiArrayValue;
      if (!y || y.shape.count != 4 || y.shape[2].unsignedIntValue != 4 * kTile) {
        REXLOG_WARN("[hud-ai] tile: {}", error ? error.localizedDescription.UTF8String : "unexpected output");
        return false;
      }
      const size_t ys_c = y.strides[1].unsignedLongValue, ys_h = y.strides[2].unsignedLongValue,
                   ys_w = y.strides[3].unsignedLongValue;
      const bool half = y.dataType == MLMultiArrayDataTypeFloat16;
      auto at = [&](int c, uint32_t yy, uint32_t xx) -> float {
        const size_t off = c * ys_c + yy * ys_h + xx * ys_w;
        return half ? float(static_cast<const _Float16*>(y.dataPointer)[off]) : static_cast<const float*>(y.dataPointer)[off];
      };
      // The tile's middle, in output (2x) pixels.
      const uint32_t cw = std::min(kCore, w - tx), ch = std::min(kCore, h - ty);
      for (uint32_t oy = 0; oy < 2 * ch; ++oy) {
        for (uint32_t ox = 0; ox < 2 * cw; ++ox) {
          const uint32_t my = 4 * kMargin + 2 * oy, mx = 4 * kMargin + 2 * ox;  // in the model's 4x output
          uint8_t* p = &out[(size_t(2 * ty + oy) * ow + (2 * tx + ox)) * 4];
          for (int c = 0; c < 3; ++c) {
            const float v = (at(c, my, mx) + at(c, my, mx + 1) + at(c, my + 1, mx) + at(c, my + 1, mx + 1)) * 0.25f;
            p[c] = uint8_t(std::clamp(std::lround(v * 255.0f), 0L, 255L));
          }
        }
      }
    }
  }
  for (uint32_t oy = 0; oy < oh; ++oy) {
    for (uint32_t ox = 0; ox < ow; ++ox) {
      const float sx = std::clamp((ox + 0.5f) / 2.0f - 0.5f, 0.0f, float(w - 1));
      const float sy = std::clamp((oy + 0.5f) / 2.0f - 0.5f, 0.0f, float(h - 1));
      const uint32_t x0 = uint32_t(sx), y0 = uint32_t(sy), x1 = std::min(x0 + 1, w - 1), y1 = std::min(y0 + 1, h - 1);
      const float fx = sx - x0, fy = sy - y0;
      auto a = [&](uint32_t xx, uint32_t yy) { return float(in[(size_t(yy) * w + xx) * 4 + 3]); };
      const float v = (a(x0, y0) * (1 - fx) + a(x1, y0) * fx) * (1 - fy) + (a(x0, y1) * (1 - fx) + a(x1, y1) * fx) * fy;
      out[(size_t(oy) * ow + ox) * 4 + 3] = uint8_t(std::clamp(std::lround(v), 0L, 255L));
    }
  }
  return true;
}

}  // namespace

bool Available() {
  static const bool present = [] {
    NSURL* url = ModelURL();
    REXLOG_INFO("[hud-ai] model in the app: {}", url ? "yes" : "no");
    if (url) {
      // Loaded (and compiled for the Neural Engine) in the background now,
      // not when the first HUD texture needs it.
      dispatch_async(Queue(), ^{
        const auto t0 = std::chrono::steady_clock::now();
        if (Model())
          REXLOG_INFO("[hud-ai] model ready in {:.0f} ms",
                      std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count());
      });
    }
    return url != nil;
  }();
  static bool said = false;
  if (!said) {
    said = true;
    REXLOG_INFO("[hud-ai] setting {}", REXCVAR_GET(nfsmw_native_hud_ai) ? "on" : "off");
  }
  return present && REXCVAR_GET(nfsmw_native_hud_ai);
}

void Request(const void* key, id<MTLTexture> flat, id<MTLCommandBuffer> cb) {
  const uint32_t w = uint32_t(flat.width), h = uint32_t(flat.height);
  if (!Supported(w) || !Supported(h)) return;
  id<MTLBuffer> buffer = [flat.device newBufferWithLength:size_t(w) * h * 4 options:MTLResourceStorageModeShared];
  if (!buffer) return;
  id<MTLBlitCommandEncoder> blit = [cb blitCommandEncoder];
  [blit copyFromTexture:flat
               sourceSlice:0
               sourceLevel:0
              sourceOrigin:MTLOriginMake(0, 0, 0)
                sourceSize:MTLSizeMake(w, h, 1)
                  toBuffer:buffer
         destinationOffset:0
    destinationBytesPerRow:w * 4
  destinationBytesPerImage:size_t(w) * h * 4];
  [blit endEncoding];
  static uint32_t requests = 0;
  if (requests++ < 3) REXLOG_INFO("[hud-ai] request {}x{}", w, h);
  [cb addCompletedHandler:^(id<MTLCommandBuffer>) {
    dispatch_async(Queue(), ^{
      @autoreleasepool {
        const uint8_t* px = static_cast<const uint8_t*>(buffer.contents);
        std::vector<uint8_t> in(px, px + size_t(w) * h * 4);
        const uint64_t hash = Hash(in.data(), in.size());
        NSURL* file = [CacheDir() URLByAppendingPathComponent:[NSString stringWithFormat:@"%016llx_%ux%u.png",
                                                                                         (unsigned long long)hash, w, h]];
        Result r{key, 2 * w, 2 * h, {}};
        bool from_disk = LoadPng(file, r.width, r.height, r.rgba);
        const auto t0 = std::chrono::steady_clock::now();
        if (!from_disk) {
          if (!Upscale(in, w, h, r.rgba)) {
            static uint32_t fails = 0;
            if (fails++ < 5) REXLOG_WARN("[hud-ai] {}x{}: not upscaled (model {})", w, h, Model() ? "loaded" : "missing");
            return;
          }
          SavePng(file, r.width, r.height, r.rgba);
        }
        static uint32_t lines = 0;
        if (lines++ < 60) {
          REXLOG_INFO("[hud-ai] {}x{} {}: {}", w, h, from_disk ? "from disk" : "upscaled",
                      from_disk ? std::string("")
                                : fmt::format("{:.0f} ms", std::chrono::duration<double, std::milli>(
                                                               std::chrono::steady_clock::now() - t0)
                                                               .count()));
        }
        std::lock_guard<std::mutex> g(g_lock);
        g_done.push_back(std::move(r));
      }
    });
  }];
}

std::vector<Result> Take() {
  std::lock_guard<std::mutex> g(g_lock);
  std::vector<Result> out;
  out.swap(g_done);
  return out;
}

}  // namespace nfsmw::hud_upscale
