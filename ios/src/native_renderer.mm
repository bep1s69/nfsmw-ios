// Native renderer, step 3: the first frames drawn by Metal from the game's own
// draws, next to the existing (emulated) renderer.
//
// Every 10 s, if the frame is menu-sized (nfsmw_native_dump), each draw of
// one frame is recorded on the game's thread at draw time, when guest memory
// holds exactly what that draw reads:
//   - the shaders: Metal libraries vs_/ps_<key> from tools/native/
//     build_shaders.sh (bundled in NativeShaders/ in local test builds);
//   - the vertex inputs: for each input of the vertex shader
//     (NativeShaders/vertex_inputs.txt: the vfetch instruction it comes
//     from), that instruction (fetch constant, offset, stride, format) read
//     from the bound microcode, every vertex decoded to a float4 (uint4 for
//     blend indices) with the fetch constant's endianness;
//   - the indices: 16/32-bit with their endianness, plus VGT_INDX_OFFSET;
//     quad and rectangle lists turned into triangle lists;
//   - the constants: c0-255 of each stage straight from the ALU constant
//     registers (the translated shaders read cN at N * 16), the booleans;
//   - the textures of fetch slots 0-15 (2D): untiled, endian-swapped,
//     8_8_8_8 / DXT1 / DXT3 / DXT5 / 8 / 8_8 / 5_6_5 / 4_4_4_4 / 16F, the
//     fetch constant's swizzle as a Metal texture swizzle;
//   - render state: render target (RB_SURFACE_INFO / COLOR_INFO /
//     DEPTH_INFO), blend, depth, colour mask, viewport, scissor.
// Then, on a queue of its own, Metal draws the frame: every render target
// (EDRAM colour base + pitch + format) is a texture of its own, and each one
// is written to Documents/native/pass_NN_<pitch>x<height>.png.
//
// Not yet: inline-vertex draws, alpha test, stencil, cube and 3D textures,
// mip levels, culling, the console's gamma. Resolution scaling and MSAA use
// the native renderer's target allocation and pipeline settings below.

#import <CoreImage/CoreImage.h>
#import <QuartzCore/CAMetalLayer.h>
#import <UIKit/UIKit.h>
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include <mach/mach.h>
#include <mach/mach_time.h>
#include <objc/runtime.h>
#include <pthread.h>
#include <mach/task_info.h>

#include <algorithm>
#include <deque>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <map>
#include <memory>
#include <mutex>
#include <thread>
#include <tuple>
#include <unordered_set>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

#include <rex/cvar.h>
#include <rex/graphics/xenos.h>
#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

#include "native_renderer.h"
#include "memory_report.h"

// The SDK's command processor (tools/ios/patch_ios_native_only.py).
extern std::atomic<bool> rex_native_draws_only;
// Game-thread time in the draw capture (native_draw_census.cpp).
extern std::atomic<uint64_t> nfsmw_capture_ns;
// The command processor's hooks (the same in tools/ios/patch_ios_native_only.py).
struct RexNativeDraw {
  const uint32_t* regs;
  const uint32_t* vs_ucode;
  uint32_t vs_dwords;
  const uint32_t* ps_ucode;
  uint32_t ps_dwords;
  uint64_t vs_hash, ps_hash;
  uint32_t index_base, index_endian, index_count;
};
extern std::atomic<void (*)(const RexNativeDraw*)> rex_native_draw_hook;
extern std::atomic<void (*)(const uint32_t*)> rex_native_resolve_hook;
extern std::atomic<void (*)()> rex_native_swap_hook;
// Occlusion queries (tools/ios/patch_ios_native_occlusion.py): (sample count
// address, query end, count out) -> handled.
extern std::atomic<bool (*)(uint32_t, bool, uint64_t*)> rex_native_occlusion_hook;

REXCVAR_DEFINE_BOOL(nfsmw_native_dump, false, "GPU",
                    "Native renderer bring-up: every 10 s, draw a menu frame with Metal and save "
                    "each render target to Documents/native");
// While the native renderer shows the game, the emulated renderer's draws and
// resolves are skipped (tools/ios/patch_ios_native_only.py): it does every
// other GPU packet still. Off: both draw, as before.
REXCVAR_DEFINE_BOOL(nfsmw_native_exclusive, true, "GPU",
                    "Native renderer: skip the emulated renderer's draws while it shows the game");
// The game waits for the native renderer instead of it dropping frames.
// The sun glare's occlusion query counted by the native renderer.
REXCVAR_DEFINE_BOOL(nfsmw_native_occlusion, false, "GPU",
                    "Native renderer: answer the game's occlusion queries (the sun glare) by "
                    "counting its own samples");
// Cubes made from resolves (environment maps) sampled with the resolves'
// red/blue swap and the fetch swizzle, as 2D resolves are.
REXCVAR_DEFINE_BOOL(nfsmw_native_cube_swizzle, true, "GPU",
                    "Native renderer: sample resolved cube maps with their red/blue swap and fetch swizzle");
// Colour resolves scaled by their exponent bias (colour * 2^bias), as the
// console's resolve does.
REXCVAR_DEFINE_BOOL(nfsmw_native_exp_bias, true, "GPU",
                    "Native renderer: apply the resolves' exponent bias (colour * 2^bias)");
// Tuning shop car colour test: the car paint shaders without their
// environment cube (black), or with a neutral grey 3D texture.
REXCVAR_DEFINE_BOOL(nfsmw_native_test_no_envcube, false, "GPU",
                    "Native renderer test: car paint without its environment cube");
REXCVAR_DEFINE_BOOL(nfsmw_native_test_grey_volume, false, "GPU",
                    "Native renderer test: car paint with a neutral grey 3D texture");
// The movies (XMV player) drawn by the native renderer's own shaders.
REXCVAR_DEFINE_BOOL(nfsmw_native_movies, true, "GPU",
                    "Native renderer: draw the movies itself (off: the emulated renderer draws them)");
REXCVAR_DEFINE_BOOL(nfsmw_native_movie_16_9, true, "GPU",
                    "Native renderer: movies keep 16:9 on wider screens (black bars at the sides)");
REXCVAR_DEFINE_BOOL(nfsmw_native_from_boot, true, "GPU",
                    "Native renderer: the emulated renderer draws nothing from the first frame on "
                    "(its memory is never filled)");
REXCVAR_DEFINE_BOOL(nfsmw_native_metal_hud, false, "GPU",
                    "Native renderer: show Apple's Metal Performance HUD for the game picture");
REXCVAR_DEFINE_BOOL(nfsmw_native_bc_gpu_decode, true, "GPU",
                    "Native renderer: on GPUs without BC (DXT) formats, expand them on the GPU (off: on the CPU)");
REXCVAR_DEFINE_BOOL(nfsmw_native_present_at_time, true, "GPU",
                    "Native renderer: below the display rate, keep each frame on screen at least one cap interval "
                    "(frame pacing at the 30/40/60 caps)");
REXCVAR_DEFINE_BOOL(nfsmw_native_pace, true, "GPU",
                    "Native renderer: the game waits for it rather than frames being dropped");
// The draws from the emulated command processor (its own thread) instead of
// the draw capture's decoding of D3D's command buffers on the game's thread.
REXCVAR_DEFINE_BOOL(nfsmw_native_cp, true, "GPU",
                    "Native renderer: take the draws from the command processor (off: from the game thread)");
// Cached vertex data and textures trusted while the emulator reports no CPU
// write to their pages (write_watch). Off: the SDK's iOS patches stop
// watching pages written often (hot pages), so changes went unnoticed (UI
// textures shown in the wrong places).
REXCVAR_DEFINE_BOOL(nfsmw_native_write_watch, false, "GPU",
                    "Native renderer: trust caches by the memory write watch (experimental)");
REXCVAR_DEFINE_INT32(nfsmw_native_dump_interval_ms, 10000, "GPU",
                     "Native renderer bring-up: time between snapshots (nfsmw_native_dump)");
// Bring-up: the alpha-tested shaders (fences, plants: 684f4711; trees:
// 27d82ea0) replaced every 6 s by debug versions (test builds with
// ps_<key>_dbg1-2 bundled): 1 their alpha as grey, 2 white where the alpha
// test keeps the pixel and red where it discards it; 0 the real shader.
// Bring-up: the wet road's shadow (ps af393d4c, with ps_<key>_dbg1-3): 1 the
// shadow factor, 2 the "shadow map enabled" constant, 3 the shadow map
// coordinates (red, green) and depth (blue); 0 the real shader.
REXCVAR_DEFINE_BOOL(nfsmw_native_shadow_debug, false, "GPU",
                    "Native renderer bring-up: show the wet road's shadow terms");
REXCVAR_DEFINE_BOOL(nfsmw_native_alpha_debug, false, "GPU",
                    "Native renderer bring-up: show what the alpha-tested shaders compute");
// The native renderer's own layer, over the game's view (touch controls stay
// above it): a CAMetalLayer that follows the view's size.
@interface NFSNativeView : UIView
@end
@implementation NFSNativeView
+ (Class)layerClass {
  return CAMetalLayer.class;
}
- (void)layoutSubviews {
  [super layoutSubviews];
  CAMetalLayer* layer = (CAMetalLayer*)self.layer;
  // The screen's real pixels per point: nativeScale, not scale. With Display
  // Zoom ("More Space" on an iPad M1: 1389x970 points on 2388x1668 pixels)
  // scale stays 2 and the drawable would have 35% more pixels than the panel.
  UIScreen* screen = self.window.screen ?: UIScreen.mainScreen;
  const CGFloat scale = screen.nativeScale ?: screen.scale;
  layer.contentsScale = scale;
  layer.drawableSize = CGSizeMake(self.bounds.size.width * scale, self.bounds.size.height * scale);
}
@end

REXCVAR_DEFINE_BOOL(nfsmw_native_scale_shadows, false, "GPU",
                    "Native renderer: the resolution scale also applies to the shadow map (depth-only targets)");
REXCVAR_DEFINE_BOOL(nfsmw_native_present, false, "GPU",
                    "Native renderer (experimental): every frame drawn by the native Metal renderer "
                    "and shown on screen, over the emulated one");

namespace xenos = rex::graphics::xenos;

// The native renderer's own scale: the launcher sets the emulated renderer's
// resolution_scale to 1 while this one shows the game.
// Experiment (did not help, off): above 1x, split a pass after this many
// indices, for the race's first-seconds stalls at 2x (none at 1x), in case
// the scene pass overflowed the GPU's tiler memory. The split pieces stalled
// the same, as did 340-draw loading frames.
// Diagnostics: once every 60 frames, one frame drawn without the draws of
// one pixel shader (in turn the 16 with the most draws), its GPU time logged
// against the frames before: what each shader costs. Those frames lack
// some objects (a flicker once a second).
// The soft-shadow filter's 9 fetches as 4 gathers (tools/native/
// rewrite_shadow_filter.py, shader_common.h's tfetch2DShadow9): function
// constant 1 of every shader. Off: the 9 fetches as the game does them.
REXCVAR_DEFINE_BOOL(nfsmw_native_shadow_gather, true, "GPU",
                    "Native renderer: soft shadows from 4 gathers instead of 9 filtered fetches");
REXCVAR_DEFINE_BOOL(nfsmw_native_async_pipelines, true, "GPU",
                    "Native renderer: compile new pipelines in the background, leaving their draws out until ready "
                    "(instead of a hitch while they compile)");
REXCVAR_DEFINE_INT32(nfsmw_test_cpu_load, 0, "GPU",
                     "Experiment: this many extra threads kept busy from the start (0-6), to see whether CPU load "
                     "makes the system throttle the GPU (the race-start stutter)");
REXCVAR_DEFINE_BOOL(nfsmw_native_constant_ranges, true, "GPU",
                    "Native renderer: compare and upload only the float constants each shader reads "
                    "(false: all 256 of each stage, per draw)");
REXCVAR_DEFINE_INT32(nfsmw_native_writeback_kb, 16, "GPU",
                     "Native renderer: colour resolves up to this size (KB) are copied back to guest memory for the "
                     "game's CPU (the exposure reads its brightness from one); 256 = the old limit");
REXCVAR_DEFINE_BOOL(nfsmw_native_cost_probe, false, "GPU",
                    "Native renderer diagnostics: measure each pixel shader's GPU cost by leaving it out of one frame");
REXCVAR_DEFINE_INT32(nfsmw_native_pass_split_indices, 0, "GPU",
                     "Native renderer: above 1x, a pass is split after this many indices (0 = never)");
REXCVAR_DEFINE_STRING(nfsmw_native_resolution_scale, "1", "GPU",
                      "Native renderer: internal resolution scale (1 = the console's 720p; fractions such as 1.5 "
                      "work; \"native\" = the screen's own pixels)");

// "native": the scale that makes the game's output as many pixels high as the
// screen (render thread: from the layer's drawable and the frame's last
// colour resolve).
std::atomic<float> native_screen_scale{0.0f};

// The internal resolution scale: a target of W x H guest pixels is drawn at
// round(W * scale) x round(H * scale).
float NativeResolutionScale() {
  static const std::string setting = REXCVAR_GET(nfsmw_native_resolution_scale);
  static const bool native = setting == "native";
  static const float fixed = std::clamp(float(std::strtod(setting.c_str(), nullptr)), 0.5f, 4.0f);
  if (!native) return std::isfinite(fixed) && fixed > 0 ? fixed : 1.0f;
  const float s = native_screen_scale.load();
  return s > 0 ? s : 1.0f;  // until the first frame has been shown
}

// Guest pixels at a scale: rounded, so that neighbouring rectangles meet.
inline uint32_t Px(double v, float scale) { return uint32_t(std::max(0L, std::lround(v * scale))); }

uint32_t NativeSampleCount(id<MTLDevice> device, uint32_t surface_info, bool msaa_disabled,
                           uint32_t maximum) {
  if (msaa_disabled) return 1;
  const uint32_t requested = 1u << ((surface_info >> 16) & 3);
  uint32_t samples = std::min(requested, maximum);
  while (samples > 1 && ![device supportsTextureSampleCount:samples]) samples >>= 1;
  return std::max(samples, 1u);
}

extern "C" float nfsmw_mirror_scale_x, nfsmw_mirror_scale_y;  // game_scene_size.cpp

namespace {

// Every texture the renderer makes, described in the system log first (NSLog,
// public) for the first 60: Metal aborts on a descriptor it rejects, and its
// own message is private ("validateWithDevice: ... error '<private>'"), as on
// the iPhone 14 Pro Max (A16) at the first frame.
id<MTLTexture> NewTexture(id<MTLDevice> device, MTLTextureDescriptor* d, const char* what) {
  static std::atomic<int> left{60};
  if (left.fetch_sub(1) > 0) {
    NSLog(@"[nfsmw-native] texture %s: type %d format %d %dx%dx%d array %d mips %d samples %d storage %d usage 0x%x",
          what, int(d.textureType), int(d.pixelFormat), int(d.width), int(d.height), int(d.depth),
          int(d.arrayLength), int(d.mipmapLevelCount), int(d.sampleCount), int(d.storageMode), unsigned(d.usage));
  }
  return [device newTextureWithDescriptor:d];
}


// --- Registers ----------------------------------------------------------------

constexpr uint32_t kRbSurfaceInfo = 0x2000, kRbColorInfo = 0x2001, kRbDepthInfo = 0x2002;
constexpr uint32_t kPaScWindowOffset = 0x2080, kPaScWindowScissorTl = 0x2081,
                   kPaScWindowScissorBr = 0x2082;
constexpr uint32_t kVgtIndxOffset = 0x2102, kRbColorMask = 0x2104;
constexpr uint32_t kVportXScale = 0x210F;  // X scale, X offset, Y scale, Y offset, Z scale, Z offset
constexpr uint32_t kRbDepthControl = 0x2200, kRbBlendControl0 = 0x2201;
constexpr uint32_t kPaSuScModeCntl = 0x2205, kPaClVteCntl = 0x2206;
constexpr uint32_t kAluBase = 0x4000, kFetchBase = 0x4800, kBoolBase = 0x4900;

float AsFloat(uint32_t v) {
  float f;
  std::memcpy(&f, &v, 4);
  return f;
}

// The recording's clock (per draw, several times): mach_absolute_time, one
// register read. steady_clock is mach_continuous_time on iOS, ~10x as slow.
struct FastClock {
  using duration = std::chrono::nanoseconds;
  using rep = duration::rep;
  using period = duration::period;
  using time_point = std::chrono::time_point<FastClock>;
  static constexpr bool is_steady = true;
  static time_point now() noexcept {
    static const mach_timebase_info_data_t tb = [] {
      mach_timebase_info_data_t t;
      mach_timebase_info(&t);
      return t;
    }();
    return time_point(duration(rep(mach_absolute_time() * tb.numer / tb.denom)));
  }
};

// A texture fetch constant (6 dwords): the key of the frame's textures and the
// texture cache.
struct FetchKey {
  uint32_t v[6];
  bool operator==(const FetchKey& o) const { return std::memcmp(v, o.v, sizeof(v)) == 0; }
};
struct FetchKeyHash {
  size_t operator()(const FetchKey& k) const {
    uint64_t h = 0xCBF29CE484222325ull;
    for (uint32_t x : k.v) h = (h ^ x) * 0x100000001B3ull;
    return size_t(h ^ (h >> 29));
  }
};

int64_t NowMs() {
  return std::chrono::duration_cast<std::chrono::milliseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

rex::memory::Memory* Mem() {
  auto* kernel = rex::system::kernel_state();
  return kernel ? kernel->memory() : nullptr;
}

const uint8_t* Physical(uint32_t address) { return Mem()->TranslatePhysical<const uint8_t*>(address); }

// Resolves written back to guest memory (small ones, as the console's GPU
// writes every resolve there: the game may read them on the CPU, e.g. the
// scene's brightness for the exposure). The emulated renderer used to; with
// it skipped (nfsmw_native_exclusive) the native renderer does. Done when
// the GPU has finished; the addresses then go to the game thread, which
// refreshes its fingerprints of them (its own copy stays in use).
struct WriteBack {
  id<MTLBuffer> pixels;  // RGBA8, rows of row_bytes
  uint32_t row_bytes;
  uint32_t src_w, src_h;  // the copied pixels' size
  uint32_t base, pitch;  // guest physical; pitch in texels
  uint32_t x0, y0, w, h;
  float scale = 1;
  bool swap;
  uint32_t endian;
};
std::mutex written_back_mutex;
std::vector<uint32_t> written_back;  // addresses, for the game thread

uint32_t LoadLE32(const uint8_t* p) {
  uint32_t v;
  std::memcpy(&v, p, 4);
  return v;
}

// --- Shaders ------------------------------------------------------------------

struct VertexInput {
  uint32_t address;   // vfetch instruction
  uint32_t usage;
  uint32_t location;  // Metal attribute
  uint32_t swizzle = 0x688;  // the vfetch's destination swizzle in the game's file (XYZW)
  int32_t dst = -1;          // the register it writes (-1: unknown, use the address)
};

struct ShaderStore {
  id<MTLDevice> device;
  std::map<std::string, id<MTLFunction>> functions;
  std::map<std::string, id<MTLLibrary>> libraries;       // for specialized variants
  std::map<std::pair<uint64_t, uint32_t>, id<MTLFunction>> ps_variants;
  std::unordered_map<uint64_t, std::vector<VertexInput>> inputs;  // by VS key
  std::set<uint64_t> internal_keys;  // D3D's run-time vertex shaders (written here)
  // The float constant registers each shader reads, FIRST..END-1
  // (constant_ranges.txt, tools/native/constant_ranges.py); not listed: all.
  std::unordered_map<uint64_t, std::pair<uint16_t, uint16_t>> constant_ranges;  // by "vs"/"ps" key ^ kind
  std::pair<uint16_t, uint16_t> ConstantRange(bool pixel, uint64_t key) const {
    if (!REXCVAR_GET(nfsmw_native_constant_ranges)) return {0, 256};
    auto it = constant_ranges.find(key ^ (pixel ? 1ull : 0ull) << 63);
    return it != constant_ranges.end() ? it->second : std::pair<uint16_t, uint16_t>{0, 256};
  }
  bool loaded = false;

  void Load() {
    if (loaded) {
      return;
    }
    loaded = true;
    device = MTLCreateSystemDefaultDevice();
    // Experiment (nfsmw_test_cpu_load): CPU load that does nothing useful, to
    // see whether the GPU's duty cycling at a race's start follows the SoC's
    // power use rather than anything the renderer does.
    for (int i = 0; i < std::clamp(REXCVAR_GET(nfsmw_test_cpu_load), 0, 6); ++i) {
      std::thread([i] {
        pthread_set_qos_class_self_np(QOS_CLASS_USER_INITIATED, 0);
        volatile double x = 1.0 + i;
        for (;;) {
          for (int k = 0; k < 1000000; ++k) x = x * 1.0000001 + 0.0000001;
        }
      }).detach();
    }
    if (REXCVAR_GET(nfsmw_test_cpu_load) > 0) {
      REXLOG_INFO("[native] experiment: {} busy threads for CPU load", std::clamp(REXCVAR_GET(nfsmw_test_cpu_load), 0, 6));
    }
    {  // Metal's capture layer wraps every call (several times the encoding cost)
      const char* cls = object_getClassName(device);
      const char* env = getenv("MTL_CAPTURE_ENABLED");
      REXLOG_INFO("[native] Metal device {} ({}{}), MTL_CAPTURE_ENABLED={}", device.name.UTF8String, cls,
                  std::strstr(cls, "Capture") ? ": the GPU capture layer is on, CPU timings are inflated" : "",
                  env ? env : "unset");
    }
    NSString* dir =
        [[NSBundle mainBundle].resourcePath stringByAppendingPathComponent:@"NativeShaders"];
    MTLFunctionConstantValues* constants = [MTLFunctionConstantValues new];
    const uint32_t spec = 0;
    [constants setConstantValue:&spec type:MTLDataTypeUInt atIndex:0];
    const bool shadow_gather = REXCVAR_GET(nfsmw_native_shadow_gather);
    [constants setConstantValue:&shadow_gather type:MTLDataTypeBool atIndex:1];
    for (NSString* name in [[NSFileManager defaultManager] contentsOfDirectoryAtPath:dir error:nil]) {
      if (![name.pathExtension isEqualToString:@"metallib"]) {
        continue;
      }
      NSURL* url = [NSURL fileURLWithPath:[dir stringByAppendingPathComponent:name]];
      id<MTLLibrary> library = [device newLibraryWithURL:url error:nil];
      id<MTLFunction> f = [library newFunctionWithName:@"shaderMain" constantValues:constants error:nil];
      if (f) {
        f.label = name.stringByDeletingPathExtension;  // e.g. ps_<key>, named in GPU traces
        functions[name.stringByDeletingPathExtension.UTF8String] = f;
        libraries[name.stringByDeletingPathExtension.UTF8String] = library;
      }
    }
    NSString* text = [NSString stringWithContentsOfFile:[dir stringByAppendingPathComponent:@"vertex_inputs.txt"]
                                               encoding:NSUTF8StringEncoding
                                                  error:nil];
    for (NSString* line in [text componentsSeparatedByString:@"\n"]) {
      unsigned long long key = 0;
      unsigned address = 0, usage = 0, index = 0, swizzle = 0x688;
      int location = -1, dst = -1;
      if (sscanf(line.UTF8String, "%llx %u %u %u %d %x %d", &key, &address, &usage, &index, &location, &swizzle,
                 &dst) >= 5 &&
          location >= 0) {
        inputs[key].push_back({address, usage, uint32_t(location), swizzle, dst});
      }
    }
    NSString* ranges = [NSString stringWithContentsOfFile:[dir stringByAppendingPathComponent:@"constant_ranges.txt"]
                                                 encoding:NSUTF8StringEncoding
                                                    error:nil];
    for (NSString* line in [ranges componentsSeparatedByString:@"\n"]) {
      char kind[3] = {};
      unsigned long long key = 0;
      unsigned first = 0, end = 0;
      if (sscanf(line.UTF8String, "%2s_%llx %u %u", kind, &key, &first, &end) == 4 && first <= end && end <= 256) {
        constant_ranges[key ^ (kind[0] == 'p' ? 1ull : 0ull) << 63] = {uint16_t(first), uint16_t(end)};
      }
    }
    LoadD3DInternalShaders(constants);
    REXLOG_INFO("[native] renderer built {} {}: {} shaders, vertex inputs of {} vertex shaders, constant ranges of {}",
                __DATE__, __TIME__, functions.size(), inputs.size(), constant_ranges.size());
  }

  // The vertex shaders D3D builds at run time (draws from user memory: the
  // final composite, the bloom chain, clears). Not in the game's files, so
  // not translated: written here from their microcode (logged as [d3d-vs]),
  // all three pass-throughs with one vertex fetch constant:
  //   ea96a7e9f897dae6  oPos = (x, y, 1, 1)           x, y: vfetch at 2, 32_32_FLOAT
  //   c4d5a3612b92f170  oPos = xyzw; o0 = (u, v, 0, 1) vfetch at 3 (32_32_32_32_FLOAT)
  //                                                  and 4 (mini, 32_32_FLOAT, +16)
  //   e69ff45e5d083e23  oPos = (x, y, z, 1); o0 = rgba vfetch at 3 (32_32_32_FLOAT)
  //                                                  and 4 (mini, 32_32_32_32_FLOAT, +12)
  // o0 goes to every interpolator: the pixel shader takes its register 0
  // from whichever one it declares.
  void LoadD3DInternalShaders(MTLFunctionConstantValues* constants) {
    std::string outs;
    std::string all;
    for (int i = 0; i < 16; ++i) {
      outs += fmt::format("  float4 t{0} [[user(TEXCOORD{0})]];\n", i);
      all += fmt::format("o.t{} = v; ", i);
    }
    for (int i = 0; i < 6; ++i) {
      outs += fmt::format("  float4 c{0} [[user(COLOR{0})]];\n", i);
      all += fmt::format("o.c{} = v; ", i);
    }
    const std::string source =
        "#include <metal_stdlib>\nusing namespace metal;\n"
        "struct Out {\n  float4 pos [[position]];\n" + outs + "};\n"
        "struct InPos { float4 a0 [[attribute(0)]]; };\n"
        "struct InPosUv { float4 a0 [[attribute(0)]]; float4 a13 [[attribute(13)]]; };\n"
        "struct InPosUv2 { float4 a0 [[attribute(0)]]; float4 a13 [[attribute(13)]]; float4 a14 [[attribute(14)]]; };\n"
        "struct Push { ulong vs; ulong ps; ulong shared_; };\n"
        // xf: positions in pixels (the console's viewport transform off) to
        // Metal's clip space, which Metal clips before any viewport:
        // (2/width, -2/height, -1, 1); (1, 1, 0, 0) when already in clip space.
        "float4 toClip(float4 p, float4 xf) { return float4(p.xy * xf.xy + xf.zw * p.w, p.z, p.w); }\n"
        "vertex Out vs_xy(InPos in [[stage_in]], constant float4& xf [[buffer(30)]]) { Out o; float4 v = 0.0; " + all +
        "o.pos = toClip(float4(in.a0.xy, 1.0, 1.0), xf); return o; }\n"
        "vertex Out vs_xyzw_uv(InPosUv in [[stage_in]], constant float4& xf [[buffer(30)]]) { Out o; float4 v = float4(in.a13.xy, 0.0, 1.0); " + all +
        "o.pos = toClip(in.a0, xf); return o; }\n"
        "vertex Out vs_xyz_rgba(InPosUv in [[stage_in]], constant float4& xf [[buffer(30)]]) { Out o; float4 v = in.a13; " + all +
        "o.pos = toClip(float4(in.a0.xyz, 1.0), xf); return o; }\n"
        // a16249c01dac6178: oPos = xyzw; o0 = (uv at +16, uv at +24)
        "vertex Out vs_xyzw_uv2(InPosUv2 in [[stage_in]], constant float4& xf [[buffer(30)]]) { Out o; "
        "float4 v = float4(in.a13.xy, in.a14.xy); " + all + "o.pos = toClip(in.a0, xf); return o; }\n"
        // 2f583d7c8ddf572a: oPos = (dot(p, c0), dot(p, c1), dot(p, c2), dot(p, c3)), p = (xyz, 1)
        "vertex Out vs_matrix(InPos in [[stage_in]], constant float4& xf [[buffer(30)]], constant Push& pc [[buffer(8)]]) { "
        "Out o; float4 v = 0.0; " + all + "device float4* c = reinterpret_cast<device float4*>(pc.vs); "
        "float4 p = float4(in.a0.xyz, 1.0); "
        "o.pos = toClip(float4(dot(p, c[0]), dot(p, c[1]), dot(p, c[2]), dot(p, c[3])), xf); return o; }\n"
        // The XMV movie player's shaders (built into the executable, not the
        // game's files; from their microcode, logged with ios_log_shader_disasm).
        // acc15ef6157ec934: oPos = (xyz, 1) (32_32_32 at vfetch 3), o0 = uv
        // (mini 32_32 at +12, vfetch 4, bound as r0._xy_: uv lands in y and z).
        "vertex Out vs_xyz_uv(InPosUv in [[stage_in]], constant float4& xf [[buffer(30)]]) { Out o; "
        "float4 v = float4(in.a13.yz, 0.0, 1.0); " + all + "o.pos = toClip(float4(in.a0.xyz, 1.0), xf); return o; }\n"
        // 2d2462de73d283de: Y, U, V from tf0-2 (each read as x) at t0.xy; with
        // its literal constants c254 (Y offset, chroma offset, Y scale) and c255
        // (chroma weights): R = s(Y-o) + V c255.y, G = s(Y-o) + U c255.z + V c255.x,
        // B = s(Y-o) + U c255.w.
        "struct Tex2D { texture2d<float> tex; };\n"
        "struct Samp { sampler samp; };\n"
        "struct InXmv { float4 pos [[position]]; float4 t0 [[user(TEXCOORD0)]]; };\n"
        "fragment float4 ps_xmv(InXmv in [[stage_in]], constant Tex2D* tex [[buffer(0)]], "
        "constant Samp* samp [[buffer(4)]], constant Push& pc [[buffer(8)]]) {\n"
        "  device uint* shared_ = reinterpret_cast<device uint*>(pc.shared_);\n"
        "  device float4* c = reinterpret_cast<device float4*>(pc.ps);\n"
        "  float y = tex[shared_[0]].tex.sample(samp[shared_[64]].samp, in.t0.xy).x;\n"
        "  float u = tex[shared_[1]].tex.sample(samp[shared_[65]].samp, in.t0.xy).x + c[254].y;\n"
        "  float v = tex[shared_[2]].tex.sample(samp[shared_[66]].samp, in.t0.xy).x + c[254].y;\n"
        "  float l = c[254].z * (y - c[254].x);\n"
        "  float3 rgb = float3(l + v * c[255].y, l + u * c[255].z + v * c[255].x, l + u * c[255].w);\n"
        "  return float4(rgb, 1.0); }\n";
    NSError* error = nil;
    MTLCompileOptions* options = [MTLCompileOptions new];
    options.languageVersion = MTLLanguageVersion3_0;  // GPU addresses as pointers
    id<MTLLibrary> library = [device newLibraryWithSource:[NSString stringWithUTF8String:source.c_str()]
                                                  options:options
                                                    error:&error];
    if (!library) {
      REXLOG_WARN("[native] D3D internal vertex shaders: {}", error.localizedDescription.UTF8String);
      return;
    }
    internal_keys = {0xea96a7e9f897dae6ull, 0xc4d5a3612b92f170ull, 0xe69ff45e5d083e23ull,
                     0xa16249c01dac6178ull, 0x2f583d7c8ddf572aull};
    functions["vs_a16249c01dac6178"] = [library newFunctionWithName:@"vs_xyzw_uv2"];
    functions["vs_2f583d7c8ddf572a"] = [library newFunctionWithName:@"vs_matrix"];
    inputs[0xa16249c01dac6178ull] = {{3, 0, 0}, {4, 5, 13}, {5, 5, 14}};
    inputs[0x2f583d7c8ddf572aull] = {{3, 0, 0}};
    functions["vs_ea96a7e9f897dae6"] = [library newFunctionWithName:@"vs_xy"];
    functions["vs_c4d5a3612b92f170"] = [library newFunctionWithName:@"vs_xyzw_uv"];
    functions["vs_e69ff45e5d083e23"] = [library newFunctionWithName:@"vs_xyz_rgba"];
    // The movie player's (see above): movie frames drawn here, not by the
    // emulated renderer, unless nfsmw_native_movies is off.
    if (REXCVAR_GET(nfsmw_native_movies)) {
      internal_keys.insert(0xacc15ef6157ec934ull);
      functions["vs_acc15ef6157ec934"] = [library newFunctionWithName:@"vs_xyz_uv"];
      functions["ps_2d2462de73d283de"] = [library newFunctionWithName:@"ps_xmv"];
      inputs[0xacc15ef6157ec934ull] = {{3, 0, 0}, {4, 5, 13}};
    }
    inputs[0xea96a7e9f897dae6ull] = {{2, 0, 0}};
    inputs[0xc4d5a3612b92f170ull] = {{3, 0, 0}, {4, 5, 13}};
    inputs[0xe69ff45e5d083e23ull] = {{3, 0, 0}, {4, 5, 13}};
  }

  // A pixel shader specialized for an alpha test (G_SPEC_CONSTANTS: bit 1 on,
  // bits 8-10 the compare function, as RB_COLORCONTROL encodes it).
  id<MTLFunction> PixelVariant(uint64_t key, uint32_t spec) {
    if (!spec) {
      return Find("ps", key);
    }
    auto found = ps_variants.find({key, spec});
    if (found != ps_variants.end()) {
      return found->second;
    }
    char name[32];
    snprintf(name, sizeof(name), "ps_%016llx", static_cast<unsigned long long>(key));
    auto lib = libraries.find(name);
    id<MTLFunction> f = nil;
    if (lib != libraries.end()) {
      MTLFunctionConstantValues* values = [MTLFunctionConstantValues new];
      [values setConstantValue:&spec type:MTLDataTypeUInt atIndex:0];
      const bool shadow_gather = REXCVAR_GET(nfsmw_native_shadow_gather);
      [values setConstantValue:&shadow_gather type:MTLDataTypeBool atIndex:1];
      f = [lib->second newFunctionWithName:@"shaderMain" constantValues:values error:nil];
    }
    ps_variants[{key, spec}] = f;
    return f;
  }

  id<MTLFunction> Find(const char* kind, uint64_t key) const {
    char name[32];
    snprintf(name, sizeof(name), "%s_%016llx", kind, static_cast<unsigned long long>(key));
    auto it = functions.find(name);
    return it == functions.end() ? nil : it->second;
  }
};

ShaderStore store;

// --- A recorded frame ----------------------------------------------------------

// Vertex data arrays: not zeroed when made (every element is written right
// after; zeroing them cost ~1 ms per frame of dynamic vertices).
template <typename T>
struct DefaultInitAllocator : std::allocator<T> {
  template <typename U>
  struct rebind {
    using other = DefaultInitAllocator<U>;
  };
  using std::allocator<T>::allocator;
  template <typename U>
  void construct(U* p) noexcept {
    ::new (static_cast<void*>(p)) U;
  }
  template <typename U, typename... Args>
  void construct(U* p, Args&&... args) {
    ::new (static_cast<void*>(p)) U(std::forward<Args>(args)...);
  }
};
using FloatArray = std::vector<float, DefaultInitAllocator<float>>;

struct Attribute {
  uint32_t location;
  bool integer;                // uint4 (blend indices) instead of float4
  // 4 per vertex (uint bits when integer); shared with the attribute cache
  // (and the renderer's Metal buffer for it) while the source is unchanged.
  std::shared_ptr<FloatArray> values;
  bool fresh = false;  // decoded this frame: uploaded with the frame, not kept
};

// --- Residency ---------------------------------------------------------------------
//
// The renderer's long-lived GPU memory (targets, the pool, the texture cache's
// Metal copies, vertex buffers) in one residency set on the queue: resident
// once. Without it the driver wired every resource a frame used when the
// frame ran and unwired it after (about 1,000 a second, 15% of a core); in
// the race's first seconds a wire of a 2x target took up to 6 ms, and the GPU
// waited for each in the middle of the frame (50-150 ms frames).
// Additions and removals come from any thread; the renderer's queue applies
// them before each frame. A removal keeps the object until then.
namespace residency {
std::mutex mutex;
std::vector<id<MTLAllocation>> adds, removes;

void Add(id<MTLAllocation> a) {
  if (!a) return;
  std::lock_guard<std::mutex> lock(mutex);
  adds.push_back(a);
}

void Remove(id<MTLAllocation> a) {
  if (!a) return;
  std::lock_guard<std::mutex> lock(mutex);
  removes.push_back(a);
}

// The renderer's queue, before encoding a frame.
void Apply(id<MTLDevice> device, id<MTLCommandQueue> queue) {
  static id<MTLResidencySet> set = nil;
  if (!set) {
    MTLResidencySetDescriptor* d = [MTLResidencySetDescriptor new];
    d.label = @"nfsmw native";
    d.initialCapacity = 4096;
    NSError* error = nil;
    set = [device newResidencySetWithDescriptor:d error:&error];
    if (!set) {
      REXLOG_WARN("[native] no residency set: {}", error ? error.localizedDescription.UTF8String : "?");
      return;
    }
    [queue addResidencySet:set];
    REXLOG_INFO("[native] resources kept resident in a residency set");
  }
  std::vector<id<MTLAllocation>> add, remove;
  {
    std::lock_guard<std::mutex> lock(mutex);
    add.swap(adds);
    remove.swap(removes);
  }
  if (add.empty() && remove.empty()) return;
  if (!add.empty()) [set addAllocations:add.data() count:add.size()];
  if (!remove.empty()) [set removeAllocations:remove.data() count:remove.size()];
  [set commit];
  [set requestResidency];
}
}  // namespace residency

// The Metal copy of a decoded texture: made by the renderer at its first
// use, released with the texture (the cache entries own both). Counted for
// the memory log.
std::atomic<int64_t> gpu_texture_count{0}, gpu_texture_bytes{0};
struct GpuCopy {
  id<MTLTexture> texture = nil;
  size_t bytes = 0;
  GpuCopy() = default;
  GpuCopy(GpuCopy&& o) noexcept : texture(o.texture), bytes(o.bytes) {
    o.texture = nil;
    o.bytes = 0;
  }
  GpuCopy(const GpuCopy&) = delete;
  GpuCopy& operator=(const GpuCopy&) = delete;
  ~GpuCopy() {
    if (texture) {
      residency::Remove(texture);
      --gpu_texture_count;
      gpu_texture_bytes -= int64_t(bytes);
    }
  }
};

struct Texture {
  MTLPixelFormat format = MTLPixelFormatInvalid;
  uint32_t width = 0, height = 0;
  uint32_t row_bytes = 0;
  // Level 0, linear. Freed by the renderer once uploaded (gpu): a second
  // copy of every texture in CPU memory took the iPhone over its memory
  // limit in races.
  // Default-initialized: the decode writes every byte (zeroing it first was
  // ~44 ms per second of the command processor thread in a race).
  mutable std::vector<uint8_t, DefaultInitAllocator<uint8_t>> data;
  size_t bytes = 0;            // data's size when decoded (the cache's budget)
  mutable GpuCopy gpu;         // render thread only
  MTLTextureSwizzleChannels swizzle = MTLTextureSwizzleChannelsDefault;
  uint32_t clamp_x = 0, clamp_y = 0;
  bool linear_filter = true;
  xenos::AnisoFilter aniso_filter = xenos::AnisoFilter::kDisabled;
  uint32_t address = 0;        // guest physical: a resolve to it replaces it
  uint32_t fetch_swizzle = 0x688;  // the fetch constant's swizzle (XYZW = 0x688)
  bool persistent = false;         // a resolve from an earlier frame stands in for it
  int32_t exp_adjust = 0;          // the fetch constant's exp_adjust: values read * 2^exp_adjust
  bool cube = false;           // six faces in data, one after another
  uint32_t depth = 1;          // 3D textures: depth slices in data, one after another
  bool volume = false;
  bool bc_on_gpu = false;      // BC blocks kept, expanded to RGBA8 by a GPU kernel (no BC on this GPU)
  uint32_t guest_format = 0;   // the fetch constant's format (diagnostics)
  uint32_t guest_endian = 0;   // the fetch constant's endianness (diagnostics)
  bool guest_tiled = false;    // (diagnostics)
  bool guest_signed = false;   // any component signed (diagnostics)
};

// A resolve: a rectangle of the current render target copied into a texture
// at the same coordinates (rexglue draw_util GetResolveInfo).
struct ResolveEvent {
  size_t after_draws;          // draws recorded before it
  bool depth;                  // RB_COPY_CONTROL source 4: the depth buffer
  bool clear_color, clear_depth;
  uint32_t clear_color_value;  // RB_COLOR_CLEAR
  uint32_t clear_depth_value;  // RB_DEPTH_CLEAR (depth 24 | stencil 8)
  int32_t x0, y0, x1, y1;
  uint32_t dest_base, dest_pitch, dest_height;
  // The EDRAM layout the resolve reads (its own registers): the source.
  uint32_t surface_info, color_info, depth_info;
  uint32_t control;
  bool array;                  // RB_COPY_DEST_INFO: into a slice (a cube face)
  uint32_t slice;
  bool swap;                   // RB_COPY_DEST_INFO bit 24: red and blue swapped
  int32_t exp_bias;            // RB_COPY_DEST_INFO bits 16-21: colour * 2^bias
  uint32_t dest_endian = 2;    // RB_COPY_DEST_INFO bits 0-2
  uint32_t dest_format = 6;    // RB_COPY_DEST_INFO bits 7-12 (6: k_8_8_8_8)
};

// A stage's float constants, c0-c255 (1024 dwords). Only the registers its
// draws' shaders read are filled in (Record copies just those): the rest is
// left as it was allocated, never read.
struct ConstantBank {
  uint32_t v[1024];
  const uint32_t* data() const { return v; }
  uint32_t* data() { return v; }
  const uint32_t& operator[](size_t i) const { return v[i]; }
  uint32_t& operator[](size_t i) { return v[i]; }
};

struct Draw {
  id<MTLFunction> vs, ps;
  uint64_t vs_key, ps_key;
  MTLPrimitiveType primitive = MTLPrimitiveTypeTriangle;
  std::vector<Attribute> attributes;
  // Rebased to the decoded vertices; shared with the index cache (and the
  // renderer's Metal buffer for them) unless made this frame (indices_fresh).
  std::shared_ptr<const std::vector<uint32_t>> indices;
  bool indices_fresh = true;
  size_t index_count() const { return indices ? indices->size() : 0; }
  uint32_t vertex_count = 0;
  // 1024 dwords each; shared with the draw before while unchanged (most are).
  std::shared_ptr<const ConstantBank> vs_constants, ps_constants;
  // The registers its shaders read of them (FIRST..END-1): compared, uploaded.
  std::pair<uint16_t, uint16_t> vs_range{0, 256}, ps_range{0, 256};
  uint32_t booleans = 0;
  int textures[16];  // index into Frame::textures, or -1
  // Render state.
  uint32_t surface_info, color_info, depth_info;
  uint32_t depth_control, blend_control, color_mask;
  // A second render target (the pixel shader's oC1), when the colour mask
  // writes one: RB_COLOR1_INFO and RB_BLENDCONTROL1.
  bool second_target = false;
  uint32_t color1_info = 0, blend_control1 = 0;
  // PA_CL_CLIP_CNTL bit 16: clipping off, depth clamped instead (the shadow
  // maps: casters beyond the light's near or far plane stay in them).
  bool clip_disable = false;
  uint32_t color_control;  // RB_COLORCONTROL: alpha test function (0-2), enable (3)
  float alpha_ref;         // RB_ALPHA_REF
  float viewport[6];
  uint32_t vte;
  int32_t window_offset_x, window_offset_y;
  uint32_t scissor[4];
  bool window_offset_enable;
  int query = -1;  // the occlusion query counting it (index into Frame::queries), or -1
};

struct VertexDiagnostics {
  uint64_t watched_cache_hits = 0;
  uint64_t fingerprint_cache_hits = 0;
  uint64_t cache_misses = 0;
  uint64_t fingerprint_calls = 0;
  uint64_t fingerprint_sample_count = 0;
  uint64_t fingerprint_sample_ns = 0;
  uint64_t fingerprint_shared = 0;  // inputs that reused their draw's region fingerprint
  uint64_t decoded_vertex_elements = 0;
  uint64_t expanded_input_indices = 0;
  uint64_t expanded_output_indices = 0;
  uint64_t index_cache_hits = 0, index_cache_misses = 0;

  VertexDiagnostics& operator+=(const VertexDiagnostics& other) {
    watched_cache_hits += other.watched_cache_hits;
    fingerprint_cache_hits += other.fingerprint_cache_hits;
    cache_misses += other.cache_misses;
    fingerprint_calls += other.fingerprint_calls;
    fingerprint_sample_count += other.fingerprint_sample_count;
    fingerprint_sample_ns += other.fingerprint_sample_ns;
    fingerprint_shared += other.fingerprint_shared;
    decoded_vertex_elements += other.decoded_vertex_elements;
    expanded_input_indices += other.expanded_input_indices;
    expanded_output_indices += other.expanded_output_indices;
    index_cache_hits += other.index_cache_hits;
    index_cache_misses += other.index_cache_misses;
    return *this;
  }
};

struct Frame {
  std::vector<Draw> draws;
  // The texture of each fetch slot at the last draw (cleared by a resolve:
  // its address may then stand for the renderer's copy).
  uint32_t slot_fetch[16][6] = {};
  int slot_texture[16] = {};
  bool slot_valid[16] = {};
  std::shared_ptr<const ConstantBank> last_vs_constants, last_ps_constants;
  std::vector<ResolveEvent> resolves;
  // Occlusion queries begun in the frame (their sample count addresses), and
  // the one open now (its draws are counted).
  std::vector<uint32_t> queries;
  int open_query = -1;
  // The frame's textures (indices in Draw::textures), shared with the
  // texture cache while their memory is unchanged.
  std::vector<std::shared_ptr<const Texture>> textures;
  std::unordered_map<FetchKey, int, FetchKeyHash> texture_index;
  uint32_t skipped_inline = 0, skipped_shader = 0, skipped_other = 0;
  uint32_t movie_draws = 0;  // the video player's picture (no library for its shaders)
  uint32_t from_arguments = 0;  // DrawVertices rebuilt from their arguments
  std::set<uint32_t> unsupported_formats;
  std::set<uint32_t> resolved_so_far;  // resolve destinations recorded so far
  std::vector<std::pair<size_t, std::string>> notes;  // first problems
  VertexDiagnostics vertex_diagnostics;
  // For the hitch log: the recording's time and the textures decoded in it.
  uint64_t record_us = 0;
  uint32_t textures_decoded = 0;
  uint64_t texture_decode_bytes = 0, texture_decode_us = 0;
};

std::unique_ptr<Frame> recording;
int64_t next_dump_ms = 0;
uint32_t dump_number = 0;
std::atomic<bool> rendering{false};
std::atomic<int> in_flight{0};               // frames recorded or rendering, not yet done
std::atomic<int> frames_without_output{0};   // e.g. FMVs: the emulated output shows through

void Note(Frame& f, std::string text) {
  if (f.notes.size() < 40) {
    f.notes.emplace_back(f.draws.size(), std::move(text));
  }
}

// --- Caches across frames (game thread) ------------------------------------------
//
// Decoded textures and vertex attributes are kept from frame to frame, keyed by
// what describes them (fetch constant, vertex layout and range) and checked
// against a fingerprint of their source memory: 32 samples of 8 bytes spread
// over it. Static data costs nothing after the first frame; data the game
// rewrites (dynamic vertices, UI text) is decoded again when its bytes change.
// Entries unused for 600 frames are dropped.

uint64_t frame_counter = 0;

// Timing, logged every 300 native frames.
std::atomic<uint64_t> record_us{0}, render_us{0}, presented{0};
// For the hitch log (the renderer's queue only): this frame's texture uploads.
uint32_t frame_uploads = 0, frame_new_buffers = 0;
uint64_t frame_upload_bytes = 0, frame_upload_us = 0;
// Hitch lines left to log (frames much slower than the ones around them).
std::atomic<int> hitch_lines_left{300};
// Parts of the recording (game thread): vertex inputs, then constants and
// textures.
std::atomic<uint64_t> record_vertex_us{0}, record_texture_us{0};
// Textures decoded from guest memory since the last stats line (cache misses).
std::atomic<uint64_t> textures_decoded_total{0}, texture_decode_bytes_total{0};
bool timed_draw = false;  // this draw's recording is timed (one in eight; command processor thread)
std::atomic<uint64_t> gpu_us{0};  // the GPU's own time per frame
std::atomic<uint32_t> gpu_slow_frames{0};  // over 45 ms on the GPU, since the last stats line

// Occlusion queries: the last count per sample count address, at the guest's
// resolution (written when the GPU finishes a frame, read by the command
// processor at the query's end). Visibility result slots per frame, in one of
// a ring of buffers (frames in flight are far fewer).
constexpr size_t kVisibilitySlots = 64;
constexpr int kVisibilityBuffers = 8;
std::mutex occlusion_mutex;
std::unordered_map<uint32_t, uint64_t> occlusion_counts;

// Compiled pipelines kept on disk (Library/Caches), so a pipeline compiled
// once is loaded, not compiled, in later sessions: compiling them as the race
// starts (dozens, tens of ms each, on the render thread) made it stutter.
// Used from the render thread and the background compiles (PipelineCache).
struct PipelineArchive {
  id<MTLBinaryArchive> archive = nil;
  NSURL* url = nil;
  bool tried = false, dirty = false;
  std::mutex mutex;  // the archive's additions and saving, the counts
  // Since the last log line: pipelines made, of them from the archive, time.
  uint32_t made = 0, loaded = 0;
  double ms = 0, worst_ms = 0;
  uint32_t misses_logged = 0;

  static unsigned long long FileSize(NSURL* u) {
    NSDictionary* a = [[NSFileManager defaultManager] attributesOfItemAtPath:u.path error:nil];
    return a ? a.fileSize : 0;
  }

  void Open(id<MTLDevice> device) {
    std::lock_guard<std::mutex> lock(mutex);
    if (tried) return;
    tried = true;
    NSURL* caches = [[NSFileManager defaultManager] URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject;
    // v2: a fresh archive (the first kept missing pipelines it had added and
    // saved, session after session; the misses' log says whether this one does).
    [[NSFileManager defaultManager]
        removeItemAtURL:[caches URLByAppendingPathComponent:@"nfsmw_native_pipelines.metalarchive"]
                  error:nil];
    url = [caches URLByAppendingPathComponent:@"nfsmw_native_pipelines_v2.metalarchive"];
    MTLBinaryArchiveDescriptor* desc = [MTLBinaryArchiveDescriptor new];
    if ([[NSFileManager defaultManager] fileExistsAtPath:url.path]) desc.url = url;
    NSError* error = nil;
    archive = [device newBinaryArchiveWithDescriptor:desc error:&error];
    if (!archive && desc.url) {  // unreadable (a new OS or GPU driver): start again
      REXLOG_WARN("[native] pipeline cache unreadable ({}), starting a new one",
                  error ? error.localizedDescription.UTF8String : "?");
      [[NSFileManager defaultManager] removeItemAtURL:url error:nil];
      archive = [device newBinaryArchiveWithDescriptor:[MTLBinaryArchiveDescriptor new] error:nil];
    }
    REXLOG_INFO("[native] pipeline cache {} ({} KiB)", !archive ? "unavailable" : desc.url ? "loaded" : "new",
                FileSize(url) / 1024);
  }

  // From the archive if it has it, else compiled (and added to it).
  id<MTLRenderPipelineState> Make(id<MTLDevice> device, MTLRenderPipelineDescriptor* desc, NSError** error) {
    Open(device);
    const auto start = std::chrono::steady_clock::now();
    id<MTLRenderPipelineState> pso = nil;
    bool hit = false;
    if (archive) {
      desc.binaryArchives = @[ archive ];
      pso = [device newRenderPipelineStateWithDescriptor:desc
                                                 options:MTLPipelineOptionFailOnBinaryArchiveMiss
                                              reflection:nil
                                                   error:nil];
      hit = pso != nil;
      if (!pso) {
        std::lock_guard<std::mutex> lock(mutex);
        NSError* add_error = nil;
        const bool added = [archive addRenderPipelineFunctionsWithDescriptor:desc error:&add_error];
        if (added) dirty = true;  // compiled into the archive: made from it below
        if (misses_logged < 40) {
          ++misses_logged;
          REXLOG_INFO("[native] pipeline cache miss: {} ({})", desc.label.UTF8String,
                      added ? "added" : add_error ? add_error.localizedDescription.UTF8String : "not added");
        }
      }
    }
    if (!pso) pso = [device newRenderPipelineStateWithDescriptor:desc error:error];
    const double took = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
    std::lock_guard<std::mutex> lock(mutex);
    ++made;
    loaded += hit;
    ms += took;
    worst_ms = std::max(worst_ms, took);
    return pso;
  }

  // With the periodic log line: the counts, and the archive written if it grew.
  void Report() {
    std::lock_guard<std::mutex> lock(mutex);
    if (made) {
      REXLOG_INFO("[native] pipelines: {} made ({} from the cache), {:.1f} ms in all, worst {:.1f} ms", made, loaded,
                  ms, worst_ms);
    }
    made = loaded = 0;
    ms = worst_ms = 0;
    if (dirty && archive) {
      NSError* error = nil;
      if (![archive serializeToURL:url error:&error]) {
        REXLOG_WARN("[native] pipeline cache not saved: {}", error ? error.localizedDescription.UTF8String : "?");
      } else {
        REXLOG_INFO("[native] pipeline cache saved ({} KiB)", FileSize(url) / 1024);
      }
      dirty = false;
    }
  }
};
PipelineArchive pipeline_archive;
int64_t stats_since_ms = 0;

uint64_t Fingerprint(const uint8_t* p, size_t size) {
  uint64_t h = 0xCBF29CE484222325ull ^ size;
  if (!p || !size) {
    return h;
  }
  const size_t samples = 32;
  for (size_t i = 0; i < samples; ++i) {
    const size_t at = size > 8 ? (size - 8) * i / (samples - 1) : 0;
    uint64_t v = 0;
    if (size >= 8) {
      std::memcpy(&v, p + at, 8);
    } else {
      std::memcpy(&v, p + at, size);
    }
    h = (h ^ v) * 0x100000001B3ull;
  }
  return h;
}

template <typename T>
struct CacheEntry {
  std::shared_ptr<T> value;
  uint64_t fingerprint = 0;
  uint64_t last_used = 0;
  bool watched = false;       // its memory is watched (WriteWatch): valid while clean
  uint64_t last_changed = 0;  // frame it last had to be decoded again
  bool dynamic = false;       // rewritten frame after frame: fingerprinted, not watched
  uint64_t last_false_alarm = 0;  // its pages written, its data unchanged (shared with hot data)
};

// Guest memory write watch: a cached decode of a watched range stays valid
// until the CPU writes there, without reading the memory again (a fingerprint
// reads 32 spread-out points: mostly cache misses, for every vertex input and
// texture of every draw). The emulator's page protection calls back on the
// first write to a watched page (host pages, 16 KB), which clears its bit.
namespace write_watch {
constexpr uint32_t kPageShift = 14;
constexpr uint32_t kPages = (512u << 20) >> kPageShift;
std::atomic<uint64_t> armed[kPages / 64];
std::once_flag registered;

std::pair<uint32_t, uint32_t> Written(void*, uint32_t start, uint32_t length, bool) {
  start &= 0x1FFFFFFF;
  const uint32_t first = start >> kPageShift;
  const uint32_t last = std::min<uint32_t>((start + std::max<uint32_t>(length, 1) - 1) >> kPageShift, kPages - 1);
  for (uint32_t page = first; page <= last; ++page) {
    armed[page >> 6].fetch_and(~(1ull << (page & 63)), std::memory_order_relaxed);
  }
  return {0, UINT32_MAX};
}

// Every page of the range watched and not written since.
bool Clean(uint32_t address, size_t size) {
  address &= 0x1FFFFFFF;
  const uint32_t first = address >> kPageShift;
  const uint32_t last = std::min<uint32_t>(uint32_t((address + std::max<size_t>(size, 1) - 1) >> kPageShift), kPages - 1);
  for (uint32_t page = first; page <= last; ++page) {
    if (!(armed[page >> 6].load(std::memory_order_relaxed) & (1ull << (page & 63)))) return false;
  }
  return true;
}

// Watches the range (before it is read: a write while decoding unwatches it).
void Arm(uint32_t address, size_t size) {
  std::call_once(registered, [] { Mem()->RegisterPhysicalMemoryInvalidationCallback(&Written, nullptr); });
  address &= 0x1FFFFFFF;
  const uint32_t first = address >> kPageShift;
  const uint32_t last = std::min<uint32_t>(uint32_t((address + std::max<size_t>(size, 1) - 1) >> kPageShift), kPages - 1);
  bool all = true;
  for (uint32_t page = first; page <= last && all; ++page) {
    all = armed[page >> 6].load(std::memory_order_relaxed) & (1ull << (page & 63));
  }
  if (all) return;
  for (uint32_t page = first; page <= last; ++page) {
    armed[page >> 6].fetch_or(1ull << (page & 63), std::memory_order_relaxed);
  }
  Mem()->EnablePhysicalMemoryAccessCallbacks(first << kPageShift, (last - first + 1) << kPageShift, true, false);
}
}  // namespace write_watch

template <typename Map>
void Sweep(Map& cache) {
  if ((frame_counter & 255) != 0) {
    return;
  }
  for (auto it = cache.begin(); it != cache.end();) {
    it = frame_counter - it->second.last_used > 600 ? cache.erase(it) : std::next(it);
  }
}

std::unordered_map<FetchKey, CacheEntry<Texture>, FetchKeyHash> texture_cache;
// Textures in use (each on the GPU once drawn; its CPU copy freed then).
constexpr size_t kNativeDecodedTextureCacheBudgetBytes = 384u << 20;
constexpr uint64_t kNativeTextureCacheIdleFrames = 120;

size_t DecodedTextureCacheBytes() {
  size_t bytes = 0;
  for (const auto& [key, entry] : texture_cache) {
    (void)key;
    if (entry.value) bytes += entry.value->bytes;
  }
  return bytes;
}

void SweepTextureCache() {
  if ((frame_counter & 63) != 0) return;

  for (auto it = texture_cache.begin(); it != texture_cache.end();) {
    const bool idle = frame_counter - it->second.last_used > kNativeTextureCacheIdleFrames;
    // Keep data owned by an in-flight frame or the GPU texture cache. The GPU
    // cache has its own byte budget and will release those references first.
    it = idle && (!it->second.value || it->second.value.use_count() == 1)
             ? texture_cache.erase(it)
             : std::next(it);
  }

  size_t bytes = DecodedTextureCacheBytes();
  if (bytes <= kNativeDecodedTextureCacheBudgetBytes) return;

  std::vector<std::pair<uint64_t, FetchKey>> candidates;
  candidates.reserve(texture_cache.size());
  for (const auto& [key, entry] : texture_cache) {
    if (entry.value && entry.value.use_count() == 1) candidates.emplace_back(entry.last_used, key);
  }
  std::sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) { return a.first < b.first; });
  for (const auto& [last_used, key] : candidates) {
    (void)last_used;
    auto it = texture_cache.find(key);
    if (it == texture_cache.end() || !it->second.value || it->second.value.use_count() != 1) continue;
    bytes -= it->second.value->bytes;
    texture_cache.erase(it);
    if (bytes <= kNativeDecodedTextureCacheBudgetBytes) break;
  }
}

// Addresses the game resolves to (seen in earlier frames): the renderer always
// draws those from its own resolve output, so they are never decoded from
// memory (the emulated renderer rewrites them every frame).
std::unordered_map<uint32_t, uint64_t> resolve_destinations;  // address -> last frame
// Every resolve the native renderer made, by address: the fingerprint of
// guest memory there at the time. A later frame sampling the address uses the
// renderer's copy while the memory is unchanged (the emulated renderer only
// writes resolves up to 256 KB back, e.g. not the car's livery composited at
// load); if the CPU wrote there since (FMV frames), memory is decoded instead.
struct PersistentResolve {
  uint64_t fingerprint;
  uint32_t span;
  uint64_t frame = 0;  // frame_counter when the renderer last resolved there
};
std::unordered_map<uint32_t, PersistentResolve> persistent_resolves;
// Decoded vertex inputs, by where and how they were read (no strings: one
// lookup per input per draw).
struct AttributeKey {
  uintptr_t base;
  uint32_t stride, offset, format, endian, integer, lo, count, remap;
  bool operator==(const AttributeKey& o) const {
    return base == o.base && stride == o.stride && offset == o.offset && format == o.format &&
           endian == o.endian && integer == o.integer && lo == o.lo && count == o.count && remap == o.remap;
  }
};
struct AttributeKeyHash {
  size_t operator()(const AttributeKey& k) const {
    uint64_t h = 0xCBF29CE484222325ull;
    for (uint64_t v : {uint64_t(k.base), uint64_t(k.stride), uint64_t(k.offset), uint64_t(k.format),
                       uint64_t(k.endian), uint64_t(k.integer), uint64_t(k.lo), uint64_t(k.count), uint64_t(k.remap)}) {
      h = (h ^ v) * 0x100000001B3ull;
      h ^= h >> 29;
    }
    return size_t(h);
  }
};
std::unordered_map<AttributeKey, CacheEntry<FloatArray>, AttributeKeyHash> attribute_cache;
// A draw's indices as the renderer draws them (read, byte-swapped, offset,
// rebased to the lowest vertex, fans and quads made triangles), by where and
// how they were read, checked against their memory like the attributes: most
// draws are static scenery whose index buffers never change.
struct IndexKey {
  uint32_t base, count, offset, flags;  // flags: initiator bits (primitive, source, 32-bit) | endian << 16
  bool operator==(const IndexKey& o) const {
    return base == o.base && count == o.count && offset == o.offset && flags == o.flags;
  }
};
struct IndexKeyHash {
  size_t operator()(const IndexKey& k) const {
    uint64_t h = (uint64_t(k.base) << 32 | k.count) * 0x9E3779B97F4A7C15ull;
    h ^= (uint64_t(k.offset) << 32 | k.flags) + (h >> 29);
    return size_t(h * 0x100000001B3ull);
  }
};
struct IndexEntry {
  std::shared_ptr<const std::vector<uint32_t>> indices;
  uint64_t fingerprint = 0, last_used = 0;
  uint32_t lo = 0, hi = 0;
  MTLPrimitiveType primitive = MTLPrimitiveTypeTriangle;
};
std::unordered_map<IndexKey, IndexEntry, IndexKeyHash> index_cache;

// The index memory's fingerprint: every word up to 4 KB (most draws), else
// the sampled one.
uint64_t IndexFingerprint(const uint8_t* p, size_t size) {
  if (size > 4096) return Fingerprint(p, size);
  uint64_t h = 0xCBF29CE484222325ull ^ size;
  size_t i = 0;
  for (; i + 8 <= size; i += 8) {
    uint64_t v;
    std::memcpy(&v, p + i, 8);
    h = (h ^ v) * 0x100000001B3ull;
  }
  for (; i < size; ++i) h = (h ^ p[i]) * 0x100000001B3ull;
  return h;
}

// --- Vertex fetch -------------------------------------------------------------

struct VFetch {
  uint32_t slot, offset, stride, format;
  uint32_t swizzle;  // destination swizzle: 3 bits per component (0-3 XYZW, 4 zero, 5 one, 7 not written)
  bool is_signed, integer;
};

bool ParseVFetch(const uint32_t* code, uint32_t dwords, uint32_t address, VFetch& out) {
  if ((address + 1) * 3 > dwords) {
    return false;
  }
  const uint32_t* w = code + address * 3;
  if ((w[0] & 0x1F) != 0) {
    return false;
  }
  out.format = (w[1] >> 16) & 0x3F;
  out.swizzle = w[1] & 0xFFF;
  out.is_signed = (w[1] >> 12) & 1;
  out.integer = (w[1] >> 13) & 1;
  out.offset = uint32_t(int32_t(w[2] << 1) >> 9);  // 23-bit signed at 8
  // A mini fetch takes its fetch constant and stride from the full fetch
  // before it.
  const uint32_t* full = w;
  if ((w[1] >> 30) & 1) {
    full = nullptr;
    for (int a = int(address) - 1; a >= 0; --a) {
      const uint32_t* p = code + a * 3;
      if ((p[0] & 0x1F) == 0 && ((p[0] >> 19) & 1) && !((p[1] >> 30) & 1)) {
        full = p;
        break;
      }
    }
    if (!full) {
      return false;
    }
  }
  out.slot = ((full[0] >> 20) & 0x1F) * 3 + ((full[0] >> 25) & 3);
  out.stride = full[2] & 0xFF;
  return true;
}

float Norm(int64_t v, uint32_t bits, bool is_signed, bool integer) {
  if (integer) {
    return float(v);
  }
  if (is_signed) {
    return std::max(float(v) / float((1ll << (bits - 1)) - 1), -1.0f);
  }
  return float(v) / float((1ll << bits) - 1);
}

int64_t Field(uint32_t word, uint32_t shift, uint32_t bits, bool is_signed) {
  uint32_t v = (word >> shift) & ((bits == 32) ? 0xFFFFFFFFu : ((1u << bits) - 1));
  if (is_signed && bits < 32 && (v >> (bits - 1))) {
    return int64_t(v) - (int64_t(1) << bits);
  }
  return is_signed ? int64_t(int32_t(v)) : int64_t(v);
}

// One element (fetch format) to four components.
bool DecodeElement(const uint8_t* p, xenos::Endian endian, const VFetch& f, float out[4]) {
  auto word = [&](int i) { return xenos::GpuSwap(LoadLE32(p + 4 * i), endian); };
  out[0] = out[1] = out[2] = 0;
  out[3] = 1;
  const bool s = f.is_signed, n = f.integer;
  switch (xenos::VertexFormat(f.format)) {
    case xenos::VertexFormat::k_8_8_8_8:
      for (int c = 0; c < 4; ++c) out[c] = Norm(Field(word(0), 8 * c, 8, s), 8, s, n);
      return true;
    case xenos::VertexFormat::k_2_10_10_10:
      for (int c = 0; c < 3; ++c) out[c] = Norm(Field(word(0), 10 * c, 10, s), 10, s, n);
      out[3] = Norm(Field(word(0), 30, 2, s), 2, s, n);
      return true;
    case xenos::VertexFormat::k_11_11_10:
      out[0] = Norm(Field(word(0), 0, 11, s), 11, s, n);
      out[1] = Norm(Field(word(0), 11, 11, s), 11, s, n);
      out[2] = Norm(Field(word(0), 22, 10, s), 10, s, n);
      return true;
    case xenos::VertexFormat::k_10_11_11:
      out[0] = Norm(Field(word(0), 0, 10, s), 10, s, n);
      out[1] = Norm(Field(word(0), 10, 11, s), 11, s, n);
      out[2] = Norm(Field(word(0), 21, 11, s), 11, s, n);
      return true;
    case xenos::VertexFormat::k_16_16:
      for (int c = 0; c < 2; ++c) out[c] = Norm(Field(word(0), 16 * c, 16, s), 16, s, n);
      return true;
    case xenos::VertexFormat::k_16_16_16_16:
      for (int c = 0; c < 4; ++c) out[c] = Norm(Field(word(c / 2), 16 * (c & 1), 16, s), 16, s, n);
      return true;
    case xenos::VertexFormat::k_16_16_FLOAT:
    case xenos::VertexFormat::k_16_16_16_16_FLOAT: {
      const int count = xenos::VertexFormat(f.format) == xenos::VertexFormat::k_16_16_FLOAT ? 2 : 4;
      for (int c = 0; c < count; ++c) {
        const uint16_t h = uint16_t(word(c / 2) >> (16 * (c & 1)));
        __fp16 half;
        std::memcpy(&half, &h, 2);
        out[c] = float(half);
      }
      return true;
    }
    case xenos::VertexFormat::k_32:
    case xenos::VertexFormat::k_32_32:
    case xenos::VertexFormat::k_32_32_32_32: {
      const int count = f.format == 33 ? 1 : f.format == 34 ? 2 : 4;
      for (int c = 0; c < count; ++c) out[c] = Norm(Field(word(c), 0, 32, s), 32, s, n);
      return true;
    }
    case xenos::VertexFormat::k_32_FLOAT:
    case xenos::VertexFormat::k_32_32_FLOAT:
    case xenos::VertexFormat::k_32_32_32_FLOAT:
    case xenos::VertexFormat::k_32_32_32_32_FLOAT: {
      const int count = f.format == 36 ? 1 : f.format == 37 ? 2 : f.format == 57 ? 3 : 4;
      for (int c = 0; c < count; ++c) out[c] = AsFloat(word(c));
      return true;
    }
    default:
      return false;
  }
}

// --- Textures -----------------------------------------------------------------

struct TexFormat {
  MTLPixelFormat format;
  uint32_t block, bytes;  // block size in texels, bytes per block
};

bool TextureFormatInfo(uint32_t f, TexFormat& out) {
  switch (xenos::TextureFormat(f)) {
    case xenos::TextureFormat::k_8_8_8_8: out = {MTLPixelFormatRGBA8Unorm, 1, 4}; return true;
    case xenos::TextureFormat::k_8: out = {MTLPixelFormatR8Unorm, 1, 1}; return true;
    case xenos::TextureFormat::k_8_8: out = {MTLPixelFormatRG8Unorm, 1, 2}; return true;
    case xenos::TextureFormat::k_5_6_5: out = {MTLPixelFormatB5G6R5Unorm, 1, 2}; return true;
    case xenos::TextureFormat::k_4_4_4_4: out = {MTLPixelFormatABGR4Unorm, 1, 2}; return true;
    case xenos::TextureFormat::k_1_5_5_5: out = {MTLPixelFormatA1BGR5Unorm, 1, 2}; return true;
    case xenos::TextureFormat::k_16_16_16_16_FLOAT: out = {MTLPixelFormatRGBA16Float, 1, 8}; return true;
    case xenos::TextureFormat::k_32_FLOAT: out = {MTLPixelFormatR32Float, 1, 4}; return true;
    case xenos::TextureFormat::k_DXT1: out = {MTLPixelFormatBC1_RGBA, 4, 8}; return true;
    case xenos::TextureFormat::k_DXT2_3: out = {MTLPixelFormatBC2_RGBA, 4, 16}; return true;
    case xenos::TextureFormat::k_DXT4_5: out = {MTLPixelFormatBC3_RGBA, 4, 16}; return true;
    default: return false;
  }
}

MTLTextureSwizzle SwizzleOf(uint32_t s) {
  switch (s & 7) {
    case 0: return MTLTextureSwizzleRed;
    case 1: return MTLTextureSwizzleGreen;
    case 2: return MTLTextureSwizzleBlue;
    case 3: return MTLTextureSwizzleAlpha;
    case 4: return MTLTextureSwizzleZero;
    default: return MTLTextureSwizzleOne;
  }
}

// Whether the GPU samples BC (DXT) textures: not the A16 and older iPhones.
bool GpuHasBC() {
  static const bool has = [] {
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    const bool b = device && device.supportsBCTextureCompression;
    REXLOG_INFO("[native] BC (DXT) textures {} on this GPU", b ? "supported" : "NOT supported: decoded on the CPU");
    return b;
  }();
  return has;
}

// A 565 colour to 8-bit RGB.
inline void Unpack565(uint16_t c, uint8_t out[3]) {
  out[0] = uint8_t(((c >> 11) & 31) * 255 / 31);
  out[1] = uint8_t(((c >> 5) & 63) * 255 / 63);
  out[2] = uint8_t((c & 31) * 255 / 31);
}

// One BC1 colour block (8 bytes) into 16 RGBA texels; alpha from the
// 3-colour mode unless the caller's alpha replaces it (BC2/BC3).
void DecodeBC1Block(const uint8_t* b, uint8_t out[16][4], bool three_colour_alpha) {
  const uint16_t c0 = uint16_t(b[0] | (b[1] << 8)), c1 = uint16_t(b[2] | (b[3] << 8));
  uint8_t p[4][4];
  Unpack565(c0, p[0]);
  Unpack565(c1, p[1]);
  p[0][3] = p[1][3] = 255;
  if (c0 > c1 || !three_colour_alpha) {
    for (int k = 0; k < 3; ++k) {
      p[2][k] = uint8_t((2 * p[0][k] + p[1][k]) / 3);
      p[3][k] = uint8_t((p[0][k] + 2 * p[1][k]) / 3);
    }
    p[2][3] = p[3][3] = 255;
  } else {
    for (int k = 0; k < 3; ++k) {
      p[2][k] = uint8_t((p[0][k] + p[1][k]) / 2);
      p[3][k] = 0;
    }
    p[2][3] = 255;
    p[3][3] = 0;
  }
  const uint32_t idx = uint32_t(b[4]) | (uint32_t(b[5]) << 8) | (uint32_t(b[6]) << 16) | (uint32_t(b[7]) << 24);
  for (int i = 0; i < 16; ++i) std::memcpy(out[i], p[(idx >> (2 * i)) & 3], 4);
}

// BC1-3 blocks (tex.data, bw x bh blocks per layer) into RGBA8 texels.
void DecodeBCToRGBA8(Texture& tex, uint32_t layers, uint32_t bw, uint32_t bh) {
  const bool bc1 = tex.format == MTLPixelFormatBC1_RGBA, bc2 = tex.format == MTLPixelFormatBC2_RGBA;
  const size_t block_bytes = bc1 ? 8 : 16;
  const size_t in_face = size_t(bw) * bh * block_bytes;
  const uint32_t w = tex.width, h = tex.height;
  const size_t out_row = size_t(w) * 4, out_face = out_row * h;
  decltype(tex.data) out(out_face * layers);
  uint8_t px[16][4];
  for (uint32_t layer = 0; layer < layers; ++layer) {
    for (uint32_t by = 0; by < bh; ++by) {
      for (uint32_t bx = 0; bx < bw; ++bx) {
        const uint8_t* b = tex.data.data() + layer * in_face + (size_t(by) * bw + bx) * block_bytes;
        if (bc1) {
          DecodeBC1Block(b, px, true);
        } else {
          DecodeBC1Block(b + 8, px, false);
          if (bc2) {
            for (int i = 0; i < 16; ++i) px[i][3] = uint8_t(((b[i / 2] >> (4 * (i & 1))) & 15) * 17);
          } else {
            uint8_t a[8] = {b[0], b[1]};
            if (a[0] > a[1]) {
              for (int i = 1; i < 7; ++i) a[i + 1] = uint8_t(((7 - i) * a[0] + i * a[1]) / 7);
            } else {
              for (int i = 1; i < 5; ++i) a[i + 1] = uint8_t(((5 - i) * a[0] + i * a[1]) / 5);
              a[6] = 0;
              a[7] = 255;
            }
            uint64_t bits = 0;
            for (int i = 0; i < 6; ++i) bits |= uint64_t(b[2 + i]) << (8 * i);
            for (int i = 0; i < 16; ++i) px[i][3] = a[(bits >> (3 * i)) & 7];
          }
        }
        for (int i = 0; i < 16; ++i) {
          const uint32_t x = bx * 4 + (i & 3), y = by * 4 + (i >> 2);
          if (x < w && y < h) std::memcpy(out.data() + layer * out_face + y * out_row + x * 4, px[i], 4);
        }
      }
    }
  }
  tex.data.swap(out);
  tex.format = MTLPixelFormatRGBA8Unorm;
  tex.row_bytes = uint32_t(out_row);
  tex.bytes = tex.data.size();
}

int32_t TiledOffset2D(int32_t x, int32_t y, uint32_t pitch, uint32_t bytes_per_block_log2) {
  // rexglue src/graphics/pipeline/texture/util.cpp GetTiledOffset2D (from UModel).
  pitch = (pitch + 31) & ~31u;
  int32_t macro = ((x >> 5) + (y >> 5) * int32_t(pitch >> 5)) << (bytes_per_block_log2 + 7);
  int32_t micro = ((x & 7) + ((y & 0xE) << 2)) << bytes_per_block_log2;
  int32_t offset = macro + ((micro & ~0xF) << 1) + (micro & 0xF) + ((y & 1) << 4);
  return ((offset & ~0x1FF) << 3) + ((y & 16) << 7) + ((offset & 0x1C0) << 2) +
         (((((y & 8) >> 2) + (x >> 3)) & 3) << 6) + (offset & 0x3F);
}

// The resolves of a finished frame into guest memory: tiled, in the
// resolve's byte order, red and blue swapped if it swapped (what the
// console's resolve writes, and what the texture decoder reads back).
void ApplyWriteBacks(const std::vector<WriteBack>& list) {
  std::vector<uint32_t> done;
  for (const WriteBack& wb : list) {
    uint8_t* base = const_cast<uint8_t*>(Physical(wb.base));
    const uint8_t* src = static_cast<const uint8_t*>(wb.pixels.contents);
    const auto endian = xenos::Endian(wb.endian & 3);
    for (uint32_t y = 0; y < wb.h; ++y) {
      for (uint32_t x = 0; x < wb.w; ++x) {
        uint32_t v;
        // The texel nearest the guest pixel's centre (the copy starts at the rect's scaled origin).
        const uint32_t sy = std::min(uint32_t((y + 0.5f) * wb.scale), wb.src_h - 1);
        const uint32_t sx = std::min(uint32_t((x + 0.5f) * wb.scale), wb.src_w - 1);
        std::memcpy(&v, src + sy * wb.row_bytes + sx * 4, 4);  // R, G, B, A bytes
        if (wb.swap) v = (v & 0xFF00FF00u) | ((v >> 16) & 0xFFu) | ((v & 0xFFu) << 16);
        v = xenos::GpuSwap(v, endian);
        std::memcpy(base + TiledOffset2D(int32_t(wb.x0 + x), int32_t(wb.y0 + y), wb.pitch, 2), &v, 4);
      }
    }
    done.push_back(wb.base);
  }
  std::lock_guard<std::mutex> lock(written_back_mutex);
  written_back.insert(written_back.end(), done.begin(), done.end());
}

int32_t TiledOffset3D(int32_t x, int32_t y, int32_t z, uint32_t pitch, uint32_t height,
                      uint32_t bytes_per_block_log2) {
  // rexglue src/graphics/pipeline/texture/util.cpp GetTiledOffset3D
  // (reconstructed from XGRAPHICS::TileVolume).
  pitch = (pitch + 31) & ~31u;
  height = (height + 31) & ~31u;
  int32_t macro_outer = ((y >> 4) + (z >> 2) * int32_t(height >> 4)) * int32_t(pitch >> 5);
  int32_t macro = ((((x >> 5) + macro_outer) << (bytes_per_block_log2 + 6)) & 0xFFFFFFF) << 1;
  int32_t micro = (((x & 7) + ((y & 6) << 2)) << (bytes_per_block_log2 + 6)) >> 6;
  int32_t offset_outer = ((y >> 3) + (z >> 2)) & 1;
  int32_t offset1 = offset_outer + ((((x >> 3) + (offset_outer << 1)) & 3) << 1);
  int32_t offset2 = ((macro + (micro & ~15)) << 1) + (micro & 15) +
                    ((z & 3) << (bytes_per_block_log2 + 6)) + ((y & 1) << 4);
  int32_t address = (offset1 & 1) << 3;
  address += (offset2 >> 6) & 7;
  address <<= 3;
  address += offset1 & ~1;
  address <<= 2;
  address += offset2 & ~511;
  address <<= 3;
  address += offset2 & 63;
  return address;
}

// The texture of a fetch slot, decoded once per frame.
int TextureOf(Frame& frame, const uint32_t* fetch) {
  xenos::xe_gpu_texture_fetch_t t;
  std::memcpy(&t, fetch, sizeof(t));
  // Textures: 2D, or cube (six faces stored like 2D slices).
  const bool cube = uint32_t(t.dimension) == 3;
  const bool volume = uint32_t(t.dimension) == 2;
  if (uint32_t(t.type) == 2 && uint32_t(t.dimension) != 1 && !cube && !volume &&
      frame.unsupported_formats.insert(0x80000000u | uint32_t(t.dimension)).second) {
    Note(frame, fmt::format("texture dimension {} not decoded (format {})", uint32_t(t.dimension),
                            uint32_t(t.format)));
  }
  if (uint32_t(t.type) != 2 || (uint32_t(t.dimension) != 1 && !cube && !volume)) {
    return -1;
  }
  // 3D textures size their fields differently (11, 11 and 10 bits).
  const uint32_t width = volume ? t.size_3d.width + 1 : t.size_2d.width + 1;
  const uint32_t height = volume ? t.size_3d.height + 1 : t.size_2d.height + 1;
  const uint32_t depth = volume ? t.size_3d.depth + 1 : 1;
  FetchKey key;
  std::memcpy(key.v, fetch, sizeof(key.v));
  if (auto it = frame.texture_index.find(key); it != frame.texture_index.end()) {
    return it->second;
  }
  TexFormat info;
  // Resolved earlier in this frame: the renderer draws it from its own copy.
  // (Only then: an address resolved in other frames can hold what the CPU
  // writes, e.g. the FMVs' video frames.)
  bool persistent = false;
  if (!frame.resolved_so_far.count(uint32_t(t.base_address) << 12)) {
    auto pr = persistent_resolves.find(uint32_t(t.base_address) << 12);
    if (pr != persistent_resolves.end()) {
      // Resolved by the renderer in the last two frames: its own copy, without
      // looking at memory. Its own write-back (small resolves, read back for
      // the CPU) changes that memory a moment after the fingerprint was
      // taken, so the check failed and the texture was decoded again from it
      // every frame (the race's environment cube: 1.5 MB, the bloom buffer).
      if (frame_counter - pr->second.frame <= 2) {
        persistent = true;
      } else if (Fingerprint(Physical(pr->first), pr->second.span) == pr->second.fingerprint) {
        persistent = true;  // the renderer's copy from an earlier frame
      } else {
        persistent_resolves.erase(pr);  // the CPU wrote there since
      }
    }
  }
  if (persistent || frame.resolved_so_far.count(uint32_t(t.base_address) << 12)) {
    {  // The filters the game asks for its resolves (once each): the renderer samples them linear.
      static std::set<uint64_t> said;
      const uint64_t k = (uint64_t(t.base_address) << 12) | (uint64_t(t.mag_filter) << 40) | (uint64_t(t.min_filter) << 42);
      if (said.size() < 64 && said.insert(k).second) {
        REXLOG_INFO("[native] resolve {:08x} ({}x{}) sampled with mag filter {} min filter {} mip filter {} "
                    "(0 point, 1 linear), clamp {}/{}",
                    uint32_t(t.base_address) << 12, width, height, uint32_t(t.mag_filter), uint32_t(t.min_filter),
                    uint32_t(t.mip_filter), uint32_t(t.clamp_x), uint32_t(t.clamp_y));
      }
    }
    Texture placeholder;  // stands in for the renderer's own resolve
    placeholder.width = width;
    placeholder.height = height;
    placeholder.cube = cube;
    placeholder.fetch_swizzle = t.swizzle;
    placeholder.persistent = persistent;
    placeholder.exp_adjust = int32_t(t.exp_adjust);
    placeholder.address = uint32_t(t.base_address) << 12;
    frame.textures.push_back(std::make_shared<const Texture>(std::move(placeholder)));
    const int index = int(frame.textures.size() - 1);
    frame.texture_index[key] = index;
    return index;
  }
  if (!TextureFormatInfo(uint32_t(t.format), info)) {
    // Which formats are missing (once each): white until supported.
    if (frame.unsupported_formats.insert((uint32_t(t.format) << 2) | uint32_t(t.dimension)).second) {
      Note(frame, fmt::format("texture format {} not decoded ({}x{}, {}, tiled {}, endian {}, at {:08x})",
                              uint32_t(t.format), width, height,
                              cube ? "cube" : "2D", uint32_t(t.tiled), uint32_t(t.endianness),
                              uint32_t(t.base_address) << 12));
    }
    // Not decodable from memory (e.g. the depth format of the shadow map):
    // only a resolve can stand in for it; until then, white.
    Texture placeholder;
    placeholder.width = width;
    placeholder.height = height;
    placeholder.address = uint32_t(t.base_address) << 12;
    frame.textures.push_back(std::make_shared<const Texture>(std::move(placeholder)));
    const int index = int(frame.textures.size() - 1);
    frame.texture_index[key] = index;
    return index;
  }
  Texture tex;
  tex.exp_adjust = int32_t(t.exp_adjust);
  tex.address = uint32_t(t.base_address) << 12;
  tex.format = info.format;
  tex.guest_format = uint32_t(t.format);
  tex.guest_endian = uint32_t(t.endianness);
  tex.guest_tiled = t.tiled;
  tex.guest_signed = t.sign_x != xenos::TextureSign::kUnsigned || t.sign_y != xenos::TextureSign::kUnsigned ||
                     t.sign_z != xenos::TextureSign::kUnsigned || t.sign_w != xenos::TextureSign::kUnsigned;
  tex.width = width;
  tex.height = height;
  const uint32_t bw = (width + info.block - 1) / info.block, bh = (height + info.block - 1) / info.block;
  tex.row_bytes = bw * info.bytes;
  tex.cube = cube;
  tex.volume = volume;
  tex.depth = depth;
  const size_t face_bytes = size_t(tex.row_bytes) * bh;
  const uint32_t layers = cube ? 6u : depth;
  const uint8_t* texture_base = Physical(uint32_t(t.base_address) << 12);
  const uint32_t log2 = __builtin_ctz(info.bytes);
  const auto endian = xenos::Endian(uint32_t(t.endianness));
  // Pitch in texels >> 5; in blocks for the tiled addressing.
  const uint32_t pitch_texels = uint32_t(t.pitch) << 5;
  const uint32_t pitch_blocks = (pitch_texels + info.block - 1) / info.block;
  const uint32_t linear_row = (pitch_blocks * info.bytes + 255) & ~255u;
  // Faces of a cube: the base level's row pitch (blocks, tile-aligned) times
  // its height in blocks aligned to 32, aligned to 4 KB (rexglue
  // GetGuestTextureLayout's array slice stride).
  const uint32_t row_pitch_aligned = ((pitch_blocks + 31) & ~31u) * info.bytes;
  const uint32_t face_stride =
      (row_pitch_aligned * ((bh + 31) & ~31u) + 4095) & ~4095u;
  // 3D: linear slices one row pitch x height (aligned to 32 rows) apart;
  // tiled ones addressed by the 3D tiling.
  const size_t linear_slice = size_t(linear_row) * ((bh + 31) & ~31u);
  // Already decoded and its memory unchanged: the cached one.
  const size_t span = size_t(layers) * std::max<size_t>(face_stride, linear_slice);
  const uint32_t texture_address = uint32_t(t.base_address) << 12;
  CacheEntry<Texture>& cached = texture_cache[key];
  cached.last_used = frame_counter;
  // Watched and not written since: no need to read the memory (WriteWatch).
  const bool watch = REXCVAR_GET(nfsmw_native_write_watch);
  bool hit = watch && cached.value && cached.watched && write_watch::Clean(texture_address, span);
  uint64_t fingerprint = 0;
  if (!hit) {
    if (watch && !cached.dynamic) write_watch::Arm(texture_address, span);
    fingerprint = Fingerprint(texture_base, span);
    hit = cached.value && cached.fingerprint == fingerprint;
    if (hit) {
      // Its pages were written but not it (they hold data the CPU writes
      // every frame): fingerprinted from now on, not watched.
      if (cached.watched) {
        if (frame_counter - cached.last_false_alarm <= 2) cached.dynamic = true;
        cached.last_false_alarm = frame_counter;
      }
      cached.watched = !cached.dynamic;
    } else {
      if (cached.value && frame_counter - cached.last_changed <= 2) cached.dynamic = true;  // FMV frames, etc.
      cached.last_changed = frame_counter;
      cached.watched = !cached.dynamic;
    }
  }
  if (hit) {
    frame.textures.push_back(cached.value);
    const int index = int(frame.textures.size() - 1);
    frame.texture_index[key] = index;
    return index;
  }
  const auto decode_start = std::chrono::steady_clock::now();
  // Allocated only now, for a real decode (it was allocated, and zeroed,
  // before the cache check: for every lookup, then thrown away on a hit).
  tex.data.resize(face_bytes * layers);
  tex.bytes = tex.data.size();
  for (uint32_t face = 0; face < layers; ++face) {
  const uint8_t* base = texture_base + (volume ? (t.tiled ? 0 : face * linear_slice) : size_t(face) * face_stride);
  for (uint32_t by = 0; by < bh; ++by) {
    for (uint32_t bx = 0; bx < bw; ++bx) {
      const uint8_t* src = base + (t.tiled ? uint32_t(volume ? TiledOffset3D(int32_t(bx), int32_t(by), int32_t(face), pitch_blocks, bh, log2)
                                                             : TiledOffset2D(int32_t(bx), int32_t(by), pitch_blocks, log2))
                                           : by * linear_row + bx * info.bytes);
      uint8_t* dst = tex.data.data() + face * face_bytes + size_t(by) * tex.row_bytes + size_t(bx) * info.bytes;
      if (info.bytes == 1) {
        *dst = *src;
        continue;
      }
      for (uint32_t i = 0; i < info.bytes; i += 2) {
        if (info.bytes == 2 || endian == xenos::Endian::k8in16) {
          uint16_t v;
          std::memcpy(&v, src + i, 2);
          v = xenos::GpuSwap(v, endian == xenos::Endian::k8in16 ? endian : xenos::Endian::kNone);
          std::memcpy(dst + i, &v, 2);
        } else {
          if (i & 2) {
            continue;
          }
          uint32_t v = xenos::GpuSwap(LoadLE32(src + i), endian);
          std::memcpy(dst + i, &v, 4);
        }
      }
    }
  }
  }
  ++frame.textures_decoded;
  frame.texture_decode_bytes += tex.data.size();
  ++textures_decoded_total;
  texture_decode_bytes_total += tex.data.size();
  {  // Decoded again frame after frame (its memory keeps changing): which one.
    static std::unordered_map<uint32_t, std::pair<uint64_t, uint32_t>> streaks;  // address -> last frame, run
    static std::set<uint32_t> said;
    auto& [last, run] = streaks[tex.address];
    run = (last + 1 == frame_counter || last == frame_counter) ? run + (last != frame_counter) : 1;
    last = frame_counter;
    if (run == 10 && said.size() < 20 && said.insert(tex.address).second) {
      REXLOG_INFO("[native] texture {:08x} decoded every frame: {}x{} format {} ({} KiB, tiled {}, {} layers, "
                  "resolved here before: {})",
                  tex.address, width, height, uint32_t(t.format), tex.data.size() >> 10, bool(t.tiled), layers,
                  resolve_destinations.count(tex.address) ? "yes" : "no");
    }
  }
  frame.texture_decode_us += uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                          std::chrono::steady_clock::now() - decode_start).count());
  // DXT (BC1-3) to RGBA8 on the CPU where the GPU has no BC formats: the
  // iPhone 14 Pro Max (A16) aborted making a BC1 texture (Metal validation).
  if ((tex.format == MTLPixelFormatBC1_RGBA || tex.format == MTLPixelFormatBC2_RGBA ||
       tex.format == MTLPixelFormatBC3_RGBA) && !GpuHasBC()) {
    // Expanded on the GPU at upload (BcDecodeOnGpu): the blocks upload small
    // and the CPU does nothing; 3D textures (rare) on the CPU.
    if (tex.volume || !REXCVAR_GET(nfsmw_native_bc_gpu_decode)) {
      DecodeBCToRGBA8(tex, layers, bw, bh);
    } else {
      tex.bc_on_gpu = true;
    }
  }
  // k_4_4_4_4 to RGBA8 on the CPU, exactly as rexglue's load shader
  // (texture_load_r4g4b4a4_rgba8): R in bits 0-3, G 4-7, B 8-11, A 12-15,
  // each nibble repeated into a byte. Metal's ABGR4 channel order did not
  // match it (the tuning shop's reflection cube came out yellow, then pink).
  if (xenos::TextureFormat(t.format) == xenos::TextureFormat::k_4_4_4_4 && tex.format == MTLPixelFormatABGR4Unorm) {
    decltype(tex.data) out(tex.data.size() * 2);
    for (size_t i = 0, n = tex.data.size() / 2; i < n; ++i) {
      uint16_t v;
      std::memcpy(&v, tex.data.data() + 2 * i, 2);
      for (int k = 0; k < 4; ++k) out[4 * i + k] = uint8_t(((v >> (4 * k)) & 15) * 17);
    }
    tex.data.swap(out);
    tex.format = MTLPixelFormatRGBA8Unorm;
    tex.row_bytes *= 2;
    tex.bytes = tex.data.size();
  }
  // The fetch swizzle over what the console's fetch returns for formats with
  // fewer components: one-component formats read as RRRR, two-component as
  // RGGG, 5_6_5 as RGBB (rexglue texture_cache.cpp host swizzles). Metal
  // gives 0 for the missing ones: a k_8_8 cube (the tuning shop's
  // reflection) lost its blue and turned yellow.
  uint32_t sw = t.swizzle;
  {
    uint8_t host[4] = {0, 1, 2, 3};
    switch (xenos::TextureFormat(t.format)) {
      case xenos::TextureFormat::k_8:
      case xenos::TextureFormat::k_32_FLOAT:
        host[1] = host[2] = host[3] = 0;
        break;
      case xenos::TextureFormat::k_8_8:
        host[2] = host[3] = 1;
        break;
      case xenos::TextureFormat::k_5_6_5:
        host[3] = 2;
        break;
      default:
        break;
    }
    uint32_t mapped = 0;
    for (int i = 0; i < 4; ++i) {
      const uint32_t sel = (sw >> (3 * i)) & 7;
      mapped |= (sel < 4 ? host[sel] : sel) << (3 * i);
    }
    sw = mapped;
  }
  tex.swizzle = MTLTextureSwizzleChannelsMake(SwizzleOf(sw), SwizzleOf(sw >> 3), SwizzleOf(sw >> 6),
                                              SwizzleOf(sw >> 9));
  tex.clamp_x = uint32_t(t.clamp_x);
  tex.clamp_y = uint32_t(t.clamp_y);
  tex.linear_filter = uint32_t(t.min_filter) != 0;
  tex.aniso_filter = t.aniso_filter;
  cached.value = std::make_shared<Texture>(std::move(tex));
  cached.fingerprint = fingerprint;
  frame.textures.push_back(cached.value);
  const int index = int(frame.textures.size() - 1);
  frame.texture_index[key] = index;
  return index;
}

// --- Recording a draw -----------------------------------------------------------

void Record(Frame& frame, const NfsmwNativeDraw& in) {
  const uint32_t* regs = in.regs;
  // Inline draws (DRAW_INDX_2: D3D's draws from user memory, e.g. the bloom
  // chain): their vertices are in the ring, behind a vertex fetch constant
  // like any other; drawn the same way. Most use vertex shaders D3D builds at
  // run time (no Metal library yet): counted as "without a shader library".
  if (in.inline_draw) {
    ++frame.skipped_inline;  // counted, not skipped
  }
  if (in.from_arguments) {
    ++frame.from_arguments;
  }
  Draw d;
  d.vs_key = in.vs_key;
  d.ps_key = in.ps_key;
  {  // by key, without building the name (the store is loaded before any recording)
    static std::unordered_map<uint64_t, id<MTLFunction>> by_key[2];
    auto find = [](int kind, uint64_t key) {
      auto [it, added] = by_key[kind].try_emplace(key, nil);
      if (added) it->second = store.Find(kind ? "ps" : "vs", key);
      return it->second;
    };
    d.vs = find(0, in.vs_key);
    d.ps = find(1, in.ps_key);
  }
  if (REXCVAR_GET(nfsmw_native_shadow_debug) && in.ps_key == 0xaf393d4c46af230cull) {
    static const auto start = std::chrono::steady_clock::now();
    const uint32_t mode = uint32_t(std::chrono::duration_cast<std::chrono::seconds>(
                                       std::chrono::steady_clock::now() - start).count() / 6 % 4);
    static uint32_t logged = UINT32_MAX;
    if (mode != logged) {
      logged = mode;
      static const char* names[] = {"real shader", "shadow map value read", "the pixel's own shadow depth",
                                    "difference (grey = equal, dark = shadowed)"};
      REXLOG_INFO("[native] shadow debug: {} - {}", mode, names[mode]);
    }
    if (mode) {
      id<MTLFunction> f = store.functions[fmt::format("ps_{:016x}_dbg{}", in.ps_key, mode)];
      if (f) {
        d.ps = f;
        d.ps_key = in.ps_key ^ mode;
      }
    }
  }
  if (REXCVAR_GET(nfsmw_native_alpha_debug) &&
      (in.ps_key == 0x684f4711f29b9f77ull || in.ps_key == 0x27d82ea0faa380a8ull)) {
    static const auto start = std::chrono::steady_clock::now();
    const uint32_t mode = uint32_t(std::chrono::duration_cast<std::chrono::seconds>(
                                       std::chrono::steady_clock::now() - start).count() / 6 % 3);
    static uint32_t logged = UINT32_MAX;
    if (mode != logged) {
      logged = mode;
      static const char* names[] = {"real shaders", "alpha as grey", "alpha test: white kept, red discarded"};
      REXLOG_INFO("[native] alpha debug: {} - {}", mode, names[mode]);
    }
    if (mode) {
      id<MTLFunction> f = store.functions[fmt::format("ps_{:016x}_dbg{}", in.ps_key, mode)];
      if (f) {
        d.ps = f;
        d.ps_key = in.ps_key ^ mode;  // its own pipelines (no alpha test variant)
      }
    }
  }
  if (!d.vs || !d.ps) {
    ++frame.skipped_shader;
    // The video player's picture (the EA logo, the intro, the story movies):
    // its shaders are the XMV player's, built into the executable, not the
    // game's. The emulated renderer draws those frames (NativeSwap).
    if (in.vs_key == 0xacc15ef6157ec934ull || in.ps_key == 0x2d2462de73d283deull) {
      ++frame.movie_draws;
    }
    {  // Which shaders the renderer has no library for (once each): e.g. the
       // movie player's, built into the executable, not the game's files.
      static std::set<std::pair<uint64_t, uint64_t>> said;
      if (said.size() < 40 && said.insert({in.vs_key, in.ps_key}).second) {
        REXLOG_INFO("[native] no shader library: vs {:016x}{} ps {:016x}{}, prim {}, {} indices, target {:x} "
                    "(frame {} draw {})",
                    in.vs_key, d.vs ? "" : " (missing)", in.ps_key, d.ps ? "" : " (missing)", in.initiator & 0x3F,
                    in.initiator >> 16, regs[kRbSurfaceInfo] & 0x3FFF, dump_number + 1,
                    frame.draws.size() + frame.skipped_shader + frame.skipped_other);
      }
    }
    return;
  }
  if ((regs[kRbSurfaceInfo] & 0x3FFF) < 16) {  // no real render target
    ++frame.skipped_other;
    return;
  }

  // Indices: DMA (a buffer), or auto (0..count-1), plus VGT_INDX_OFFSET.
  const uint32_t prim = in.initiator & 0x3F, source = (in.initiator >> 6) & 3;
  const uint32_t count = in.initiator >> 16;
  const bool index32 = (in.initiator >> 11) & 1;
  const uint32_t offset = in.from_arguments ? in.start_vertex : regs[kVgtIndxOffset];
  // Converted before from the same memory: the cached indices.
  const uint32_t endian_bits = source == 0 ? (in.index_size >> 30) : 0;
  const IndexKey ikey{source == 0 ? in.index_base : 0u, count, offset,
                      (in.initiator & 0xFFFF) | (endian_bits << 16)};
  // Rectangle lists add vertices to the attributes: not cached.
  IndexEntry* ientry = prim != 8 && count ? &index_cache[ikey] : nullptr;
  const uint64_t ifp = source == 0 && count ? IndexFingerprint(Physical(in.index_base), size_t(count) * (index32 ? 4 : 2))
                                            : 0;
  const bool index_hit = ientry && ientry->indices && ientry->fingerprint == ifp;
  uint32_t lo = UINT32_MAX, hi = 0;
  static std::vector<uint32_t> raw_buffer;  // reused: no allocation or zeroing per draw
  uint32_t* raw = nullptr;
  if (index_hit) {
    ++frame.vertex_diagnostics.index_cache_hits;
    ientry->last_used = frame_counter;
    lo = ientry->lo;
    hi = ientry->hi;
    d.indices = ientry->indices;
    d.indices_fresh = false;
    d.primitive = ientry->primitive;
  } else {
    ++frame.vertex_diagnostics.index_cache_misses;
    if (raw_buffer.size() < count) raw_buffer.resize(count);
    raw = raw_buffer.data();
    if (source == 0) {
      const auto endian = xenos::Endian(in.index_size >> 30);
      const uint8_t* p = Physical(in.index_base);
      for (uint32_t i = 0; i < count; ++i) {
        if (index32) {
          raw[i] = xenos::GpuSwap(LoadLE32(p + 4 * i), endian);
        } else {
          uint16_t v;
          std::memcpy(&v, p + 2 * i, 2);
          raw[i] = xenos::GpuSwap(v, endian);
        }
      }
    } else if (source == 2) {
      for (uint32_t i = 0; i < count; ++i) raw[i] = i;
    } else {
      ++frame.skipped_other;
      Note(frame, fmt::format("index source {}", source));
      return;
    }
    for (uint32_t i = 0; i < count; ++i) {
      uint32_t& v = raw[i];
      v += offset;
      lo = std::min(lo, v);
      hi = std::max(hi, v);
    }
    if (count == 0 || hi - lo > (1u << 20)) {
      ++frame.skipped_other;
      return;
    }
  }
  d.vertex_count = hi - lo + 1;

  // Vertex inputs.
  const auto vertex_start = timed_draw ? FastClock::now() : FastClock::time_point{};
  const uint8_t* region_fp_base = nullptr;  // the fingerprint of this draw's vertex region, per stream
  size_t region_fp_start = 0, region_fp_size = 0;
  uint64_t region_fp = 0;
  auto inputs_it = store.inputs.find(in.vs_key);
  if (inputs_it != store.inputs.end()) {
    for (const VertexInput& input : inputs_it->second) {
      // The run-time shader may fetch its inputs in another order than the
      // file (the key ignores vfetches): its vfetch for this input is the
      // one writing the same register, among the file's vfetch addresses.
      // Two inputs can share a register (r1.xy and r1.zw): the components
      // written (selectors other than 7) tell them apart.
      auto written = [](uint32_t swizzle) {
        uint32_t mask = 0;
        for (int i = 0; i < 4; ++i) mask |= (((swizzle >> (3 * i)) & 7) != 7) << i;
        return mask;
      };
      uint32_t address = input.address;
      if (input.dst >= 0) {
        int fallback = -1;
        bool found = false;
        for (const VertexInput& other : inputs_it->second) {
          const uint32_t at = other.address * 3;
          if (at + 3 > in.vs_dwords || (in.vs_microcode[at] & 0x1F) != 0 ||
              int32_t((in.vs_microcode[at] >> 12) & 0x3F) != input.dst) {
            continue;
          }
          if (written(in.vs_microcode[at + 1] & 0xFFF) == written(input.swizzle)) {
            address = other.address;
            found = true;
            break;
          }
          if (fallback < 0) fallback = int(other.address);
        }
        if (!found && fallback >= 0) address = uint32_t(fallback);
      }
      VFetch f;
      if (!ParseVFetch(in.vs_microcode, in.vs_dwords, address, f)) {
        Note(frame, fmt::format("vs {:016x}: no vfetch at {}", in.vs_key, input.address));
        continue;
      }
      const uint32_t* fc = regs + kFetchBase + (f.slot / 3) * 6 + (f.slot % 3) * 2;
      const uint32_t buffer = fc[0] & ~3u;
      const uint32_t size_bytes = ((fc[1] >> 2) & 0xFFFFFF) * 4;
      const auto endian = xenos::Endian(fc[1] & 3);
      Attribute a;
      a.location = input.location;
      a.integer = input.usage == 2;  // BLENDINDICES: uint4
      // The translated shader applies the swizzle compiled in the game's
      // file; the console applies the one D3D wrote at bind time (a
      // D3DCOLOR's bytes are ARGB: its fetch picks them in another order).
      // Where they differ, the components are moved so that the file's
      // swizzle gives what the bound one would.
      int remap[4] = {0, 1, 2, 3};  // input component k <- decoded component remap[k] (4 zero, 5 one)
      bool remapped = false;
      if (f.swizzle != input.swizzle) {
        static std::set<std::pair<uint64_t, uint32_t>> logged_swizzles;
        if (logged_swizzles.size() < 200 && logged_swizzles.insert({in.vs_key, input.address}).second) {
          REXLOG_INFO("[native] vs {:016x} vfetch {} (usage {}, format {}): swizzle {:03x} in the file, {:03x} bound",
                      in.vs_key, input.address, input.usage, f.format, input.swizzle, f.swizzle);
        }
        for (int i = 0; i < 4; ++i) {
          const uint32_t file_sel = (input.swizzle >> (3 * i)) & 7, bound_sel = (f.swizzle >> (3 * i)) & 7;
          if (file_sel < 4 && bound_sel < 6 && file_sel != bound_sel) {
            remap[file_sel] = int(bound_sel);
            remapped = true;
          }
        }
      }
      // DrawPrimitiveUP: its own vertices, where it reserved them.
      const uint8_t* base = in.up_vertices ? Mem()->TranslateVirtual<const uint8_t*>(in.up_vertices)
                                           : Physical(buffer);
      // Decoded before from the same bytes: the cached array.
      const AttributeKey akey{uintptr_t(base), f.stride, f.offset, f.format, uint32_t(endian), uint32_t(a.integer),
                              lo, d.vertex_count,
                              remapped ? uint32_t(remap[0] | remap[1] << 3 | remap[2] << 6 | remap[3] << 9) : 0u};
      const size_t first = (size_t(lo) * f.stride + f.offset) * 4;
      const size_t range = size_t(d.vertex_count) * f.stride * 4 + 16;
      CacheEntry<FloatArray>& acached = attribute_cache[akey];
      acached.last_used = frame_counter;
      const bool watchable = REXCVAR_GET(nfsmw_native_write_watch) && buffer && !in.up_vertices && !acached.dynamic;
      if (acached.value && acached.watched && write_watch::Clean(buffer + uint32_t(first), range)) {
        ++frame.vertex_diagnostics.watched_cache_hits;
        a.values = acached.value;  // watched, not written since
        d.attributes.push_back(std::move(a));
        continue;
      }
      if (watchable) write_watch::Arm(buffer + uint32_t(first), range);
      uint64_t afp = 0;
      if (buffer) {
        // The draw's other inputs usually sit in the same vertices (one
        // interleaved buffer): the region of whole vertices is fingerprinted
        // once per draw and stream, not once per input.
        const size_t region = size_t(lo) * f.stride * 4;
        const size_t region_size = size_t(d.vertex_count + 1) * f.stride * 4 + 16;
        if (base == region_fp_base && region == region_fp_start && region_size == region_fp_size) {
          afp = region_fp;
          ++frame.vertex_diagnostics.fingerprint_shared;
        } else {
        const uint64_t call = frame.vertex_diagnostics.fingerprint_calls++;
        const bool sample = (call & 63) == 0;
        const auto fingerprint_start = sample ? FastClock::now() : FastClock::time_point{};
        afp = Fingerprint(base + region, region_size);
        region_fp_base = base;
        region_fp_start = region;
        region_fp_size = region_size;
        region_fp = afp;
        if (sample) {
          frame.vertex_diagnostics.fingerprint_sample_ns += uint64_t(
              std::chrono::duration_cast<std::chrono::nanoseconds>(
                  FastClock::now() - fingerprint_start).count());
          ++frame.vertex_diagnostics.fingerprint_sample_count;
        }
        }
      }
      if (acached.value && acached.fingerprint == afp) {
        ++frame.vertex_diagnostics.fingerprint_cache_hits;
        if (acached.watched) {  // a false alarm (see the textures)
          if (frame_counter - acached.last_false_alarm <= 2) acached.dynamic = true;
          acached.last_false_alarm = frame_counter;
        }
        acached.watched = watchable && !acached.dynamic;
        a.values = acached.value;
        d.attributes.push_back(std::move(a));
        continue;
      }
      ++frame.vertex_diagnostics.cache_misses;
      // Changed: rewritten two frames running, it is dynamic data (not
      // watched from then on: every write would fault).
      if (acached.value && frame_counter - acached.last_changed <= 2) acached.dynamic = true;
      acached.last_changed = frame_counter;
      acached.watched = watchable && !acached.dynamic;
      a.values = std::make_shared<FloatArray>(size_t(d.vertex_count) * 4);
      a.fresh = true;
      FloatArray& values = *a.values;
      bool ok = true;
      for (uint32_t v = 0; v < d.vertex_count && ok; ++v) {
        const uint32_t at = ((lo + v) * f.stride + f.offset) * 4;
        float c[4];
        // The fetch constant's size is not always the whole range a draw
        // reads (D3D's dynamic buffers): only a missing buffer is refused.
        if (!buffer || (size_bytes && at > size_bytes + (1u << 20)) || !DecodeElement(base + at, endian, f, c)) {
          ok = false;
          break;
        }
        ++frame.vertex_diagnostics.decoded_vertex_elements;
        if (remapped) {
          const float raw[6] = {c[0], c[1], c[2], c[3], 0.0f, 1.0f};
          for (int k = 0; k < 4; ++k) c[k] = raw[remap[k]];
        }
        if (a.integer) {
          for (int k = 0; k < 4; ++k) {
            const uint32_t u = uint32_t(std::max(c[k], 0.0f));
            std::memcpy(&values[v * 4 + k], &u, 4);
          }
        } else {
          std::memcpy(&values[v * 4], c, sizeof(c));
        }
      }
      if (!ok) {
        Note(frame, fmt::format("vs {:016x}: vertex format {} at slot {} not decoded (buffer {:08x}, "
                                "{} bytes, stride {} offset {}, vertices {}-{})",
                                in.vs_key, f.format, f.slot, buffer, size_bytes, f.stride * 4,
                                f.offset * 4, lo, hi));
        ++frame.skipped_other;
        return;
      }
      if (in.from_arguments && frame.from_arguments <= 8) {
        Note(frame, fmt::format("from-args draw: vs {:016x} prim {} count {} start {} | input loc {} "
                                "slot {} buffer {:08x} size {} stride {} offset {} fmt {} endian {} | "
                                "v0 ({:.3f}, {:.3f}, {:.3f}, {:.3f}) v{} ({:.3f}, {:.3f}, {:.3f}, {:.3f})",
                                in.vs_key, prim, count, in.start_vertex, input.location, f.slot, buffer,
                                size_bytes, f.stride * 4, f.offset * 4, f.format, uint32_t(endian),
                                values[0], values[1], values[2], values[3],
                                d.vertex_count - 1, values[(d.vertex_count - 1) * 4],
                                values[(d.vertex_count - 1) * 4 + 1], values[(d.vertex_count - 1) * 4 + 2],
                                values[(d.vertex_count - 1) * 4 + 3]));
      }
      acached.value = a.values;
      acached.fingerprint = afp;
      d.attributes.push_back(std::move(a));
    }
  }

  if (!index_hit) {
    // Primitive: lists Metal has, or triangles made from fans/quads/rectangles.
    auto made = std::make_shared<std::vector<uint32_t>>();
    std::vector<uint32_t>& out = *made;
    out.reserve(prim == 5 ? 3 * size_t(count) : prim == 13 ? 3 * size_t(count) / 2 : prim == 8 ? 2 * size_t(count) : count);
    auto at = [&](uint32_t i) { return raw[i] - lo; };
    switch (prim) {
      case 1: d.primitive = MTLPrimitiveTypePoint; for (uint32_t i = 0; i < count; ++i) out.push_back(at(i)); break;
      case 2: d.primitive = MTLPrimitiveTypeLine; for (uint32_t i = 0; i < count; ++i) out.push_back(at(i)); break;
      case 3: d.primitive = MTLPrimitiveTypeLineStrip; for (uint32_t i = 0; i < count; ++i) out.push_back(at(i)); break;
      case 4: for (uint32_t i = 0; i < count; ++i) out.push_back(at(i)); break;
      case 6: d.primitive = MTLPrimitiveTypeTriangleStrip; for (uint32_t i = 0; i < count; ++i) out.push_back(at(i)); break;
      case 5:  // fan
        for (uint32_t i = 2; i < count; ++i) out.insert(out.end(), {at(0), at(i - 1), at(i)});
        break;
      case 13:  // quad list
        for (uint32_t i = 0; i + 3 < count; i += 4)
          out.insert(out.end(), {at(i), at(i + 1), at(i + 2), at(i), at(i + 2), at(i + 3)});
        break;
      case 8: {  // rectangle list: the fourth corner = v1 + v2 - v0, for every input
        for (Attribute& a : d.attributes) {  // a copy: the cached arrays stay as they were
          a.values = std::make_shared<FloatArray>(*a.values);
          a.fresh = true;
        }
        for (uint32_t i = 0; i + 2 < count; i += 3) {
          const uint32_t v0 = at(i), v1 = at(i + 1), v2 = at(i + 2), v3 = d.vertex_count++;
          for (Attribute& a : d.attributes) {
            FloatArray& values = *a.values;
            values.resize(size_t(d.vertex_count) * 4);
            for (int k = 0; k < 4; ++k) {
              values[v3 * 4 + k] = values[v1 * 4 + k] + values[v2 * 4 + k] - values[v0 * 4 + k];
            }
          }
          out.insert(out.end(), {v0, v1, v2, v1, v3, v2});
        }
        break;
      }
      default:
        ++frame.skipped_other;
        Note(frame, fmt::format("primitive {}", prim));
        return;
    }
    if (prim == 5 || prim == 13 || prim == 8) {
      frame.vertex_diagnostics.expanded_input_indices += count;
      frame.vertex_diagnostics.expanded_output_indices += out.size();
    }
    d.indices = made;
    if (ientry) {
      ientry->indices = made;
      ientry->fingerprint = ifp;
      ientry->last_used = frame_counter;
      ientry->lo = lo;
      ientry->hi = hi;
      ientry->primitive = d.primitive;
    }
  }

  // Constants: c0-255 of each stage (VS at 0x4000, PS at 0x4400).
  // The draw before's constants if they are the same (one compare instead of
  // a copy per draw, and one upload of them).
  // Only the registers the draw's shader reads are compared: the others may
  // differ from the draw before's, unread.
  // A new bank holds only those registers too (not zeroed, not all 4 KB
  // copied): a draw whose shader reads others never matches it (their
  // compare differs), so it never reads what was not copied.
  auto constants = [&](std::shared_ptr<const ConstantBank>& last, const uint32_t* from,
                       std::pair<uint16_t, uint16_t> range) {
    const size_t at = size_t(range.first) * 4, n = size_t(range.second - range.first) * 16;
    if (!last || (n && std::memcmp(last->data() + at, from + at, n) != 0)) {
      auto bank = std::shared_ptr<ConstantBank>(new ConstantBank);  // default-initialized: no zeroing
      std::memcpy(bank->data() + at, from + at, n);
      last = std::move(bank);
    }
    return last;
  };
  const auto texture_start = timed_draw ? FastClock::now() : FastClock::time_point{};
  if (timed_draw) {
    record_vertex_us += 8 * uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(texture_start - vertex_start).count());
  }
  d.vs_range = store.ConstantRange(false, d.vs_key);
  d.ps_range = store.ConstantRange(true, d.ps_key);
  d.vs_constants = constants(frame.last_vs_constants, regs + kAluBase, d.vs_range);
  d.ps_constants = constants(frame.last_ps_constants, regs + kAluBase + 1024, d.ps_range);
  // The car's shadow casters: D3D's position-only vertex shader (2f583d7c,
  // no texture coordinate) with the shadow-map pixel shader (4fbaecfb). That
  // one cuts out see-through casters (g_bShadowMapAlphaEnabled, c1) by the
  // diffuse texture's alpha at the texture coordinate; with none, here 0, it
  // read the corner of the foliage texture left bound from the trees and
  // threw every pixel of the car away (no car in the shadow map). Without a
  // texture coordinate there is nothing to cut out: off for these draws.
  // The same for 88e2dcfd (the bridge and other large static casters):
  // position only too, so its cut-out tested whichever foliage texture was
  // drawn last (their shadows came and went with the scenery).
  if ((d.vs_key == 0x2f583d7c8ddf572aull || d.vs_key == 0x88e2dcfd95a47a7bull) &&
      d.ps_key == 0x4fbaecfb8e7c4f40ull && (*d.ps_constants)[4] != 0) {
    auto copy = std::make_shared<ConstantBank>(*d.ps_constants);
    (*copy)[4] = 0;  // c1.x = 0.0f
    d.ps_constants = copy;
  }
  // Booleans: VS 0-15 in bits 0-15, PS 128-143 in bits 16-31.
  d.booleans = (regs[kBoolBase] & 0xFFFF) | ((regs[kBoolBase + 4] & 0xFFFF) << 16);

  // A slot whose fetch constant is the same as at the draw before: the same
  // texture (most are; skips building the slot's key).
  for (int s = 0; s < 16; ++s) {
    const uint32_t* fetch = regs + kFetchBase + s * 6;
    if (frame.slot_valid[s] && std::memcmp(frame.slot_fetch[s], fetch, 24) == 0) {
      d.textures[s] = frame.slot_texture[s];
      continue;
    }
    d.textures[s] = TextureOf(frame, fetch);
    std::memcpy(frame.slot_fetch[s], fetch, 24);
    frame.slot_texture[s] = d.textures[s];
    frame.slot_valid[s] = true;
  }
  if (timed_draw) {
    record_texture_us += 8 * uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                          FastClock::now() - texture_start).count());
  }

  d.surface_info = regs[kRbSurfaceInfo];
  d.color_info = regs[kRbColorInfo];
  d.depth_info = regs[kRbDepthInfo];
  d.depth_control = regs[kRbDepthControl];
  d.blend_control = regs[kRbBlendControl0];
  d.color_mask = regs[kRbColorMask];
  d.color1_info = regs[0x2003];
  d.clip_disable = (regs[0x2204] >> 16) & 1;  // PA_CL_CLIP_CNTL
  d.blend_control1 = regs[0x2209];
  d.second_target = ((d.color_mask >> 4) & 0xF) != 0;
  d.color_control = regs[0x2202];
  d.alpha_ref = AsFloat(regs[0x210E]);
  for (int i = 0; i < 6; ++i) d.viewport[i] = AsFloat(regs[kVportXScale + i]);
  d.vte = regs[kPaClVteCntl];
  const uint32_t wo = regs[kPaScWindowOffset];
  d.window_offset_x = int32_t(wo << 17) >> 17;
  d.window_offset_y = int32_t((wo >> 16) << 17) >> 17;
  d.window_offset_enable = (regs[kPaSuScModeCntl] >> 16) & 1;
  const uint32_t tl = regs[kPaScWindowScissorTl], br = regs[kPaScWindowScissorBr];
  d.scissor[0] = tl & 0x7FFF;
  d.scissor[1] = (tl >> 16) & 0x7FFF;
  d.scissor[2] = br & 0x7FFF;
  d.scissor[3] = (br >> 16) & 0x7FFF;
  frame.draws.push_back(std::move(d));
}

// --- Drawing a recorded frame with Metal ----------------------------------------

MTLBlendFactor BlendFactor(uint32_t f) {
  switch (f) {
    case 0: return MTLBlendFactorZero;
    case 1: return MTLBlendFactorOne;
    case 4: return MTLBlendFactorSourceColor;
    case 5: return MTLBlendFactorOneMinusSourceColor;
    case 6: return MTLBlendFactorSourceAlpha;
    case 7: return MTLBlendFactorOneMinusSourceAlpha;
    case 8: return MTLBlendFactorDestinationColor;
    case 9: return MTLBlendFactorOneMinusDestinationColor;
    case 10: return MTLBlendFactorDestinationAlpha;
    case 11: return MTLBlendFactorOneMinusDestinationAlpha;
    case 12: return MTLBlendFactorBlendColor;
    case 13: return MTLBlendFactorOneMinusBlendColor;
    case 14: return MTLBlendFactorBlendAlpha;
    case 15: return MTLBlendFactorOneMinusBlendAlpha;
    case 16: return MTLBlendFactorSourceAlphaSaturated;
    default: return MTLBlendFactorOne;
  }
}

MTLBlendOperation BlendOp(uint32_t op) {
  switch (op) {
    case 1: return MTLBlendOperationSubtract;
    case 2: return MTLBlendOperationMin;
    case 3: return MTLBlendOperationMax;
    case 4: return MTLBlendOperationReverseSubtract;
    default: return MTLBlendOperationAdd;
  }
}

MTLPixelFormat ColorFormat(uint32_t f) {
  switch (f) {
    case 0: case 1: return MTLPixelFormatRGBA8Unorm;
    case 2: case 10: return MTLPixelFormatRGB10A2Unorm;
    case 3: case 12: case 5: case 7: return MTLPixelFormatRGBA16Float;
    case 4: case 6: return MTLPixelFormatRG16Float;
    case 14: return MTLPixelFormatR32Float;
    case 15: return MTLPixelFormatRG32Float;
    default: return MTLPixelFormatRGBA8Unorm;
  }
}

MTLSamplerAddressMode AddressMode(uint32_t clamp) {
  switch (clamp) {
    case 0: return MTLSamplerAddressModeRepeat;
    case 1: return MTLSamplerAddressModeMirrorRepeat;
    case 3: return MTLSamplerAddressModeMirrorClampToEdge;
    case 6: case 7: return MTLSamplerAddressModeClampToBorderColor;
    default: return MTLSamplerAddressModeClampToEdge;
  }
}

std::string EdramKey(uint32_t surface_info, uint32_t color_info, uint32_t depth_info) {
  // Memoized: called for every draw (the few layouts of a frame repeat).
  static thread_local std::unordered_map<uint64_t, std::string> cache;
  const uint64_t k = uint64_t(color_info & 0xFFF) | uint64_t((color_info >> 16) & 0xF) << 12 |
                     uint64_t(surface_info & 0x3FFF) << 16 | uint64_t(depth_info & 0xFFF) << 30 |
                     uint64_t((surface_info >> 16) & 3) << 42;
  auto it = cache.find(k);
  if (it != cache.end()) return it->second;
  return cache.emplace(k, fmt::format("{:03x}_{}_{}_d{:03x}_s{}", color_info & 0xFFF, surface_info & 0x3FFF,
                                      (color_info >> 16) & 0xF, depth_info & 0xFFF,
                                      1u << ((surface_info >> 16) & 3)))
      .first->second;
}

std::vector<NSUInteger> ActiveAttributesUncached(id<MTLFunction> vs);
// Per function, once (asking Metal allocates an array every time).
const std::vector<NSUInteger>& ActiveAttributes(id<MTLFunction> vs) {
  static std::unordered_map<const void*, std::vector<NSUInteger>> cache;
  auto it = cache.find((__bridge const void*)vs);
  if (it == cache.end()) it = cache.emplace((__bridge const void*)vs, ActiveAttributesUncached(vs)).first;
  return it->second;
}
std::vector<NSUInteger> ActiveAttributesUncached(id<MTLFunction> vs) {
  std::vector<NSUInteger> out;
  for (MTLVertexAttribute* a in vs.vertexAttributes) {
    if (a.active) out.push_back(a.attributeIndex);
  }
  std::sort(out.begin(), out.end());
  return out;
}

// --- Pipelines -------------------------------------------------------------------

// A render pipeline by the state it is made from.
struct PipelineKey {
  uint64_t vs, ps;
  uint32_t blend, blend1, mask, format, format1, alpha_spec, sample_count;
  bool alpha_to_coverage;
  bool operator==(const PipelineKey& o) const {
    return vs == o.vs && ps == o.ps && blend == o.blend && blend1 == o.blend1 && mask == o.mask &&
           format == o.format && format1 == o.format1 && alpha_spec == o.alpha_spec &&
           sample_count == o.sample_count && alpha_to_coverage == o.alpha_to_coverage;
  }
};
struct PipelineKeyHash {
  size_t operator()(const PipelineKey& k) const {
    uint64_t h = k.vs * 0x9E3779B97F4A7C15ull ^ k.ps;
    for (uint64_t v : {uint64_t(k.blend), uint64_t(k.blend1), uint64_t(k.mask), uint64_t(k.format),
                       uint64_t(k.format1), uint64_t(k.alpha_spec), uint64_t(k.sample_count),
                       uint64_t(k.alpha_to_coverage)}) {
      h = (h ^ v) * 0x100000001B3ull;
    }
    return size_t(h ^ (h >> 31));
  }
};

// The descriptor of a key's pipeline (format: the Xenos colour format of
// target 0; format1: target 1's + 1, 0 without one; mask: RB_COLOR_MASK bits
// of the targets drawn).
MTLRenderPipelineDescriptor* PipelineDescriptor(const PipelineKey& k, id<MTLFunction> vs, id<MTLFunction> ps) {
  MTLRenderPipelineDescriptor* desc = [MTLRenderPipelineDescriptor new];
  // Named in GPU traces (Instruments' shader timeline) and the cache misses' log.
  desc.label = [NSString stringWithFormat:@"ps_%016llx vs_%016llx alpha%u", (unsigned long long)k.ps,
                                          (unsigned long long)k.vs, k.alpha_spec];
  desc.vertexFunction = vs;
  desc.fragmentFunction = k.alpha_spec ? store.PixelVariant(k.ps, k.alpha_spec) : ps;
  if (!desc.fragmentFunction) {
    desc.fragmentFunction = ps;
  }
  MTLVertexDescriptor* vd = [MTLVertexDescriptor vertexDescriptor];
  const std::vector<NSUInteger>& active = ActiveAttributes(vs);
  for (size_t i = 0; i < active.size(); ++i) {
    const NSUInteger at = active[i];
    MTLVertexAttribute* a = nil;
    for (MTLVertexAttribute* x in vs.vertexAttributes) {
      if (x.attributeIndex == at) a = x;
    }
    vd.attributes[at].format = a.attributeType == MTLDataTypeUInt4 ? MTLVertexFormatUInt4 : MTLVertexFormatFloat4;
    vd.attributes[at].offset = 0;
    vd.attributes[at].bufferIndex = 9 + i;
    vd.layouts[9 + i].stride = 16;
  }
  desc.vertexDescriptor = vd;
  desc.rasterSampleCount = k.sample_count;
  desc.alphaToCoverageEnabled = k.alpha_to_coverage;
  auto attachment = [&](int n, MTLPixelFormat format, uint32_t bc, uint32_t mask) {
    MTLRenderPipelineColorAttachmentDescriptor* c = desc.colorAttachments[n];
    c.pixelFormat = format;
    c.blendingEnabled = (bc & 0x1FFF1FFF) != 0x00010001;  // not one/zero/add for both
    c.sourceRGBBlendFactor = BlendFactor(bc & 0x1F);
    c.rgbBlendOperation = BlendOp((bc >> 5) & 7);
    c.destinationRGBBlendFactor = BlendFactor((bc >> 8) & 0x1F);
    c.sourceAlphaBlendFactor = BlendFactor((bc >> 16) & 0x1F);
    c.alphaBlendOperation = BlendOp((bc >> 21) & 7);
    c.destinationAlphaBlendFactor = BlendFactor((bc >> 24) & 0x1F);
    MTLColorWriteMask m = 0;
    if (mask & 1) m |= MTLColorWriteMaskRed;
    if (mask & 2) m |= MTLColorWriteMaskGreen;
    if (mask & 4) m |= MTLColorWriteMaskBlue;
    if (mask & 8) m |= MTLColorWriteMaskAlpha;
    c.writeMask = m;
  };
  attachment(0, ColorFormat(k.format), k.blend, k.mask & 0xF);
  if (k.format1) {
    attachment(1, ColorFormat(k.format1 - 1), k.blend1, (k.mask >> 4) & 0xF);
  }
  desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float_Stencil8;
  desc.stencilAttachmentPixelFormat = MTLPixelFormatDepth32Float_Stencil8;
  return desc;
}

// The renderer's pipelines (render thread). A new one is compiled on the spot,
// or, with nfsmw_native_async_pipelines, on a background queue while its draws
// are left out (a few frames, the first time only). Every pipeline made is
// listed in Library/Caches/nfsmw_native_pipelines.keys, and the next session
// compiles them all in the background from its start (the menus): a race then
// finds them ready, from the archive or compiled once more if the archive
// lost them.
class PipelineCache {
 public:
  // The key's pipeline, or nil: failed (*failed), or still compiling.
  id<MTLRenderPipelineState> Get(id<MTLDevice> device, const PipelineKey& k, id<MTLFunction> vs,
                                 id<MTLFunction> ps, bool async, bool* failed) {
    if (auto it = ready_.find(k); it != ready_.end()) return it->second;
    if (failed_.count(k)) {
      *failed = true;
      return nil;
    }
    if (async) {
      ++draws_waiting_;
      if (demanded_.insert(k).second) Start(device, k, PipelineDescriptor(k, vs, ps), false);
      return nil;
    }
    NSError* error = nil;
    id<MTLRenderPipelineState> pso = nil;
    @try {
      pso = pipeline_archive.Make(device, PipelineDescriptor(k, vs, ps), &error);
    } @catch (NSException* e) {
      pso = nil;
    }
    Finish(k, pso, false, error ? error.localizedDescription.UTF8String : "exception");
    *failed = !pso;
    return pso;
  }

  size_t size() const { return ready_.size(); }

  // Once per frame (render thread): the background compiles finished since.
  void Collect() {
    std::vector<Done> done;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      done.swap(done_);
    }
    for (Done& d : done) {
      Finish(d.key, d.pso, d.warm, d.error.c_str());
      if (d.warm && --warm_left_ == 0) {
        REXLOG_INFO("[native] pipelines warmed up: {} in {:.0f} ms (background)", warm_total_,
                    std::chrono::duration<double, std::milli>(FastClock::now() - warm_start_).count());
      }
    }
  }

  // Once (render thread, the store loaded): the pipelines of earlier sessions,
  // compiled in the background.
  void WarmUp(id<MTLDevice> device) {
    if (warmed_) return;
    warmed_ = true;
    NSData* data = [NSData dataWithContentsOfURL:KeysUrl()];
    const size_t n = data.length / sizeof(SavedKey);
    const SavedKey* saved = static_cast<const SavedKey*>(data.bytes);
    warm_start_ = FastClock::now();
    for (size_t i = 0; i < n; ++i) {
      const PipelineKey k{saved[i].vs,     saved[i].ps,         saved[i].blend,       saved[i].blend1,
                          saved[i].mask,   saved[i].format,     saved[i].format1,     saved[i].alpha_spec,
                          saved[i].sample_count, saved[i].alpha_to_coverage != 0};
      id<MTLFunction> vs = store.Find("vs", k.vs), ps = store.Find("ps", k.ps);
      if (!vs || !ps || !known_.insert(k).second) continue;  // shaders no longer in this build
      ++warm_total_;
      Start(device, k, PipelineDescriptor(k, vs, ps), true);
    }
    warm_left_ = warm_total_;
    REXLOG_INFO("[native] pipelines: {} known from earlier sessions, compiling them in the background",
                warm_total_);
  }

  // With the periodic log line: draws left out, and the key list written if it grew.
  void Report() {
    if (draws_waiting_) {
      REXLOG_INFO("[native] pipelines: {} draws left out while theirs compiled", draws_waiting_);
      draws_waiting_ = 0;
    }
    pipeline_archive.Report();
    if (!keys_dirty_) return;
    keys_dirty_ = false;
    NSMutableData* data = [NSMutableData dataWithCapacity:known_.size() * sizeof(SavedKey)];
    for (const PipelineKey& k : known_) {
      const SavedKey s{k.vs,      k.ps,         k.blend,        k.blend1,
                       k.mask,    k.format,     k.format1,      k.alpha_spec,
                       k.sample_count, uint32_t(k.alpha_to_coverage)};
      [data appendBytes:&s length:sizeof(s)];
    }
    if (![data writeToURL:KeysUrl() atomically:YES]) {
      REXLOG_WARN("[native] pipeline list not saved");
    }
  }

 private:
  struct SavedKey {  // the file's records (no padding)
    uint64_t vs, ps;
    uint32_t blend, blend1, mask, format, format1, alpha_spec, sample_count, alpha_to_coverage;
  };
  static_assert(sizeof(SavedKey) == 48, "SavedKey layout");
  struct Done {
    PipelineKey key;
    id<MTLRenderPipelineState> pso;
    bool warm;
    std::string error;
  };

  static NSURL* KeysUrl() {
    NSURL* caches = [[NSFileManager defaultManager] URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject;
    return [caches URLByAppendingPathComponent:@"nfsmw_native_pipelines_v2.keys"];
  }

  // Compiled on a serial queue: the warm-up's at utility priority, the ones a
  // frame waits for on their own, ahead of it.
  void Start(id<MTLDevice> device, const PipelineKey& key, MTLRenderPipelineDescriptor* desc, bool warm) {
    const PipelineKey k = key;  // a copy: a block captures a reference as a reference
    static dispatch_queue_t warm_queue = dispatch_queue_create(
        "nfsmw.pipelines.warm", dispatch_queue_attr_make_with_qos_class(DISPATCH_QUEUE_SERIAL, QOS_CLASS_UTILITY, 0));
    static dispatch_queue_t demand_queue = dispatch_queue_create(
        "nfsmw.pipelines", dispatch_queue_attr_make_with_qos_class(DISPATCH_QUEUE_SERIAL, QOS_CLASS_USER_INITIATED, 0));
    dispatch_async(warm ? warm_queue : demand_queue, ^{
      NSError* error = nil;
      id<MTLRenderPipelineState> pso = nil;
      @try {
        pso = pipeline_archive.Make(device, desc, &error);
      } @catch (NSException* e) {
        pso = nil;
      }
      std::lock_guard<std::mutex> lock(mutex_);
      done_.push_back({k, pso, warm, error ? error.localizedDescription.UTF8String : "exception"});
    });
  }

  void Finish(const PipelineKey& k, id<MTLRenderPipelineState> pso, bool warm, const char* error) {
    if (!warm) demanded_.erase(k);
    if (ready_.count(k)) return;  // made twice (the warm-up and a draw): the first kept
    if (pso) {
      ready_[k] = pso;
      if (known_.insert(k).second) keys_dirty_ = true;
      return;
    }
    if (warm) return;  // the draws that need it will try once more and say why
    failed_.insert(k);  // not retried every frame
    if (++failures_logged_ <= 3) {
      REXLOG_WARN("[native] pipeline vs {:016x} ps {:016x}: {}", k.vs, k.ps, error);
    }
  }

  std::unordered_map<PipelineKey, id<MTLRenderPipelineState>, PipelineKeyHash> ready_;
  std::unordered_set<PipelineKey, PipelineKeyHash> failed_, demanded_, known_;
  std::mutex mutex_;
  std::vector<Done> done_;  // guarded by mutex_
  bool warmed_ = false, keys_dirty_ = false;
  uint32_t warm_total_ = 0, warm_left_ = 0, draws_waiting_ = 0, failures_logged_ = 0;
  FastClock::time_point warm_start_;
};
PipelineCache pipeline_cache;

struct Target {
  id<MTLTexture> color;
  id<MTLTexture> depth;
  id<MTLTexture> multisample_color;
  id<MTLTexture> multisample_depth;
  uint32_t pitch, height, format;
  float scale = 1;  // the resolution scale of this target (shadow maps 1)
  uint32_t sample_count = 1;
  uint32_t requested_sample_count = 1;
  uint32_t draws = 0;
  bool used = false;
  // A resolve with clear flags: the next pass on this target starts cleared.
  bool clear_color = false, clear_depth = false;
  MTLClearColor clear_color_value = MTLClearColorMake(0, 0, 0, 0);
  double clear_depth_value = 1.0;
};

// Depth resolves: the depth buffer read into an R32Float texture (the game
// samples the shadow map as a 24-bit depth texture: the value in [0, 1]).
id<MTLRenderPipelineState> DepthCopyPipeline(id<MTLDevice> device) {
  static id<MTLRenderPipelineState> pso;
  if (pso) {
    return pso;
  }
  NSString* source = @"#include <metal_stdlib>\n"
                      "using namespace metal;\n"
                      "struct V { float4 p [[position]]; };\n"
                      "vertex V vs(uint id [[vertex_id]]) {\n"
                      "  float2 uv = float2((id << 1) & 2, id & 2);\n"
                      "  V v; v.p = float4(uv * 2.0 - 1.0, 0.0, 1.0); return v; }\n"
                      "fragment float ps(V in [[stage_in]], depth2d<float> d [[texture(0)]], constant float& scale [[buffer(0)]]) {\n"
                      "  return d.read(uint2(in.p.xy)) * scale; }\n";
  NSError* error = nil;
  id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
  if (!library) {
    REXLOG_WARN("[native] depth copy shader: {}", error.localizedDescription.UTF8String);
    return nil;
  }
  MTLRenderPipelineDescriptor* desc = [MTLRenderPipelineDescriptor new];
  desc.vertexFunction = [library newFunctionWithName:@"vs"];
  desc.fragmentFunction = [library newFunctionWithName:@"ps"];
  desc.colorAttachments[0].pixelFormat = MTLPixelFormatR32Float;
  pso = [device newRenderPipelineStateWithDescriptor:desc error:&error];
  return pso;
}

// Colour resolves with an exponent bias (RB_COPY_DEST_INFO bits 16-21: the
// console writes colour * 2^bias): a copy that scales, per destination format.
// The source is read at the destination pixel plus an offset.
id<MTLRenderPipelineState> ScaledCopyPipeline(id<MTLDevice> device, MTLPixelFormat format) {
  static std::map<MTLPixelFormat, id<MTLRenderPipelineState>> made;
  auto it = made.find(format);
  if (it != made.end()) {
    return it->second;
  }
  static id<MTLLibrary> library;
  if (!library) {
    NSString* source = @"#include <metal_stdlib>\n"
                        "using namespace metal;\n"
                        "struct V { float4 p [[position]]; };\n"
                        "struct C { float scale; int2 offset; };\n"
                        "vertex V vs(uint id [[vertex_id]]) {\n"
                        "  float2 uv = float2((id << 1) & 2, id & 2);\n"
                        "  V v; v.p = float4(uv * 2.0 - 1.0, 0.0, 1.0); return v; }\n"
                        "fragment float4 ps(V in [[stage_in]], texture2d<float> t [[texture(0)]], constant C& c [[buffer(0)]]) {\n"
                        "  return t.read(uint2(int2(in.p.xy) + c.offset)) * c.scale; }\n";
    NSError* error = nil;
    library = [device newLibraryWithSource:source options:nil error:&error];
    if (!library) {
      REXLOG_WARN("[native] scaled copy shader: {}", error.localizedDescription.UTF8String);
      return made[format] = nil;
    }
  }
  MTLRenderPipelineDescriptor* desc = [MTLRenderPipelineDescriptor new];
  desc.vertexFunction = [library newFunctionWithName:@"vs"];
  desc.fragmentFunction = [library newFunctionWithName:@"ps"];
  desc.colorAttachments[0].pixelFormat = format;
  NSError* error = nil;
  return made[format] = [device newRenderPipelineStateWithDescriptor:desc error:&error];
}

// --- GPU-side state kept across frames (render queue only) ----------------------

struct GpuBuffer {
  id<MTLBuffer> buffer;  // an arena chunk's
  size_t offset = 0, size = 0;
  uint32_t chunk = 0;
  std::shared_ptr<const void> keep;
  uint64_t last_used = 0;
};

// The cached vertex and index arrays' GPU copies, packed into large shared
// buffers: one Metal allocation (and one residency set change) per 32 MB
// instead of one per array. Thousands of small buffers made as a race starts
// meant thousands of allocations, each wired and added to the residency set.
// A chunk is reused once nothing in it is alive (arrays leave the cache after
// 600 frames unused, long after the GPU last read them).
struct BufferArena {
  static constexpr size_t kChunk = 32u << 20;
  struct Chunk {
    id<MTLBuffer> buffer;
    size_t used = 0, live = 0;  // bytes handed out, still in use
  };
  std::vector<Chunk> chunks;
  uint32_t current = UINT32_MAX;

  // Room for `size` bytes: its chunk, buffer and offset.
  bool Allocate(id<MTLDevice> device, size_t size, uint32_t& chunk, __strong id<MTLBuffer>& buffer, size_t& offset) {
    size = (size + 255) & ~size_t(255);
    if (current == UINT32_MAX || chunks[current].buffer.length - chunks[current].used < size) {
      if (!Fresh(device, std::max(size, kChunk))) return false;  // larger than a chunk: one of its size
    }
    Chunk& c = chunks[current];
    chunk = current;
    buffer = c.buffer;
    offset = c.used;
    c.used += size;
    c.live += size;
    return true;
  }

  void Release(uint32_t chunk, size_t size) {
    size = (size + 255) & ~size_t(255);
    Chunk& c = chunks[chunk];
    c.live -= std::min(c.live, size);
    if (c.live == 0 && chunk != current) c.used = 0;  // empty: reusable
  }

  size_t Bytes() const {
    size_t n = 0;
    for (const Chunk& c : chunks) n += c.buffer.length;
    return n;
  }

 private:
  bool Fresh(id<MTLDevice> device, size_t size) {
    // An empty chunk big enough, else a new one.
    for (uint32_t i = 0; i < chunks.size(); ++i) {
      if (i != current && chunks[i].used == 0 && chunks[i].buffer.length >= size) {
        current = i;
        return true;
      }
    }
    id<MTLBuffer> b = [device newBufferWithLength:size options:MTLResourceStorageModeShared];
    if (!b) return false;
    residency::Add(b);
    chunks.push_back({b, 0, 0});
    current = uint32_t(chunks.size() - 1);
    return true;
  }
};
BufferArena buffer_arena;
// The renderer's resolve outputs kept across frames, by address (and whether
// the resolve swapped red and blue).
struct KeptResolve {
  id<MTLTexture> texture;
  bool swap;
  float scale;  // its source target's resolution scale
};
std::unordered_map<uint32_t, KeptResolve> kept_resolves;
// The cubes the renderer assembles from face resolves (the race's environment
// map), by address: one texture kept from frame to frame, the faces copied
// into it as they are resolved (in GPU order: draws before a face's copy see
// the frame before's face, as the console's sampling of that memory would).
std::unordered_map<uint32_t, id<MTLTexture>> kept_cubes;
std::unordered_map<uint32_t, bool> kept_cube_swaps;  // whether their faces' resolves swapped red and blue

// --- Recycled GPU memory (the renderer's queue) ------------------------------------
//
// Made anew every frame, the frame's buffers and resolve textures (some the
// size of the 2x screen, 17 MiB) cost the driver a wire and an unwire each:
// 4 GB a second at 2x. While iOS is short of free memory (the race loading
// and its first seconds, when it compresses the app's memory) every one
// waited for pages, and the GPU sat idle in the middle of frames: 50-150 ms
// frames. They are reused instead, back in the pool once the last frame that
// may use them is done on the GPU (frames complete in order on one queue).
std::atomic<uint32_t> gpu_frames_done{0};

void FrameDoneOnGpu(uint32_t number) {
  uint32_t done = gpu_frames_done.load();
  while (number > done && !gpu_frames_done.compare_exchange_weak(done, number)) {
  }
}

struct GpuPool {
  struct Retired {
    id object;
    std::string key;
    uint32_t after;  // reusable once this frame is done
  };
  struct Free {
    id object;
    uint32_t since;  // the frame it was freed at
  };
  std::unordered_map<std::string, std::vector<Free>> free;
  std::deque<Retired> retired;
  std::unordered_map<const void*, std::string> keys;  // the pool's objects
  uint32_t made = 0, reused = 0;

  void Reclaim(uint32_t now) {
    const uint32_t done = gpu_frames_done.load();
    while (!retired.empty() && retired.front().after <= done) {
      free[retired.front().key].push_back({retired.front().object, now});
      retired.pop_front();
    }
    // Unused for 10 s or so: released (a scene that needed more).
    if ((now & 63) == 0) {
      for (auto it = free.begin(); it != free.end();) {
        auto& list = it->second;
        list.erase(std::remove_if(list.begin(), list.end(),
                                  [&](const Free& f) {
                                    if (now - f.since <= 600) return false;
                                    keys.erase((__bridge const void*)f.object);
                                    residency::Remove(f.object);
                                    return true;
                                  }),
                   list.end());
        it = list.empty() ? free.erase(it) : std::next(it);
      }
    }
  }

  id Take(const std::string& key) {
    auto it = free.find(key);
    if (it == free.end() || it->second.empty()) return nil;
    id object = it->second.back().object;
    it->second.pop_back();
    ++reused;
    return object;
  }

  void Add(id object, std::string key) {
    keys[(__bridge const void*)object] = std::move(key);
    residency::Add(object);
    ++made;
  }

  // Back to the pool once frame `after` is done (objects not the pool's: dropped).
  void Retire(id object, uint32_t after) {
    if (!object) return;
    auto it = keys.find((__bridge const void*)object);
    if (it == keys.end()) return;
    retired.push_back({object, it->second, after});
  }

  // Zeroed up to `length` like a new buffer (the texture heaps' unset slots
  // must read as no texture: a stale ID of a released texture hangs the GPU).
  // Zeroed when reused (heap and argument buffers must not keep stale
  // resource IDs), unless the caller writes every byte it uses (zero false).
  id<MTLBuffer> Buffer(id<MTLDevice> device, size_t length, MTLResourceOptions options, bool zero = true) {
    size_t size = 4096;
    while (size < length) size *= 2;
    const std::string key = fmt::format("b {} {}", size, uint64_t(options));
    id<MTLBuffer> b = Take(key);
    if (!b) {
      b = [device newBufferWithLength:size options:options];
      Add(b, key);
    } else if (zero && b.contents) {
      std::memset(b.contents, 0, length);
    }
    return b;
  }

  // `row`: a linear texture over a buffer of its own with this row pitch (0: none).
  id<MTLTexture> Texture(id<MTLDevice> device, MTLTextureDescriptor* d, NSUInteger row = 0) {
    const std::string key = fmt::format("t {} {} {}x{}x{} {} {} {}", uint64_t(d.textureType), uint64_t(d.pixelFormat),
                                        d.width, d.height, d.depth, uint64_t(d.usage), uint64_t(d.storageMode), row);
    id<MTLTexture> t = Take(key);
    if (!t) {
      if (row) {
        id<MTLBuffer> backing = [device newBufferWithLength:row * d.height
                                                    options:MTLResourceOptions(d.storageMode) << MTLResourceStorageModeShift];
        t = [backing newTextureWithDescriptor:d offset:0 bytesPerRow:row];
      } else {
        t = NewTexture(device, d, "d@2");
      }
      if (!t) return nil;
      Add(t, key);
    }
    return t;
  }
};
GpuPool gpu_pool;
std::unordered_map<const void*, GpuBuffer> gpu_buffers;
std::map<uint32_t, id<MTLSamplerState>> gpu_samplers;
uint64_t gpu_frame = 0;

uint64_t ProcessPhysicalFootprint() {
  task_vm_info_data_t info = {};
  mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
  if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&info), &count) != KERN_SUCCESS) {
    return 0;
  }
  return info.phys_footprint;
}

// The Metal texture for a decoded texture: made once, kept while the cache
// keeps the decoded data (a new decode is a new object).
// BC1-3 blocks expanded to RGBA8 by a compute kernel, for GPUs without BC
// formats (A16 and older): the blocks upload as they are, 4-8x smaller than
// texels, and the CPU decodes nothing (it did, at ~10 ms a frame on an
// iPhone 14 Pro Max while a track streamed in). Encoded into one command
// buffer per frame on the frame's queue, committed before the frame's own
// (BcFlush), so it runs first.
id<MTLCommandQueue> bc_queue;           // the frame's queue (render thread)
id<MTLCommandBuffer> bc_cb;             // this frame's decodes, if any
id<MTLComputeCommandEncoder> bc_enc;

id<MTLComputePipelineState> BcPipeline(id<MTLDevice> device, bool cube) {
  static id<MTLComputePipelineState> pso[2];
  static bool tried = false;
  if (!tried) {
    tried = true;
    NSString* source = @"#include <metal_stdlib>\n"
        "using namespace metal;\n"
        "struct P { uint bw; uint bh; uint w; uint h; uint kind; uint layer_bytes; };\n"
        "float3 c565(uint c) { return float3((c >> 11) & 31, (c >> 5) & 63, c & 31) / float3(31.0, 63.0, 31.0); }\n"
        "float4 texel(device const uchar* b, uint kind, uint i) {\n"
        "  device const uchar* c = kind == 1 ? b : b + 8;\n"
        "  uint c0 = c[0] | (c[1] << 8), c1 = c[2] | (c[3] << 8);\n"
        "  uint idx = (c[4 + i / 4] >> (2 * (i % 4))) & 3;\n"
        "  float3 p0 = c565(c0), p1 = c565(c1);\n"
        "  float4 col;\n"
        "  if (kind != 1 || c0 > c1) {\n"
        "    col = float4(idx == 0 ? p0 : idx == 1 ? p1 : idx == 2 ? (2.0 * p0 + p1) / 3.0 : (p0 + 2.0 * p1) / 3.0, 1.0);\n"
        "  } else {\n"
        "    col = idx == 0 ? float4(p0, 1) : idx == 1 ? float4(p1, 1) : idx == 2 ? float4((p0 + p1) * 0.5, 1) : float4(0);\n"
        "  }\n"
        "  if (kind == 2) { col.a = float((b[i / 2] >> (4 * (i % 2))) & 15) / 15.0; }\n"
        "  if (kind == 3) {\n"
        "    float a0 = b[0] / 255.0, a1 = b[1] / 255.0;\n"
        "    uint bit = 3 * i; uint byte = 2 + bit / 8; uint shift = bit % 8;\n"
        "    uint v = (b[byte] | (b[min(byte + 1, 7u)] << 8)) >> shift; uint ai = v & 7;\n"
        "    float a;\n"
        "    if (b[0] > b[1]) a = ai == 0 ? a0 : ai == 1 ? a1 : (float(8 - ai) * a0 + float(ai - 1) * a1) / 7.0;\n"
        "    else a = ai == 0 ? a0 : ai == 1 ? a1 : ai == 6 ? 0.0 : ai == 7 ? 1.0 : (float(6 - ai) * a0 + float(ai - 1) * a1) / 5.0;\n"
        "    col.a = a;\n"
        "  }\n"
        "  return col;\n"
        "}\n"
        "kernel void bc2d(device const uchar* data [[buffer(0)]], constant P& p [[buffer(1)]],\n"
        "                 texture2d<float, access::write> out [[texture(0)]], uint2 g [[thread_position_in_grid]]) {\n"
        "  if (g.x >= p.bw || g.y >= p.bh) return;\n"
        "  device const uchar* b = data + (g.y * p.bw + g.x) * (p.kind == 1 ? 8 : 16);\n"
        "  for (uint i = 0; i < 16; ++i) { uint2 xy = g * 4 + uint2(i % 4, i / 4);\n"
        "    if (xy.x < p.w && xy.y < p.h) out.write(texel(b, p.kind, i), xy); }\n"
        "}\n"
        "kernel void bccube(device const uchar* data [[buffer(0)]], constant P& p [[buffer(1)]],\n"
        "                   texturecube<float, access::write> out [[texture(0)]], uint3 g [[thread_position_in_grid]]) {\n"
        "  if (g.x >= p.bw || g.y >= p.bh || g.z >= 6) return;\n"
        "  device const uchar* b = data + g.z * p.layer_bytes + (g.y * p.bw + g.x) * (p.kind == 1 ? 8 : 16);\n"
        "  for (uint i = 0; i < 16; ++i) { uint2 xy = g.xy * 4 + uint2(i % 4, i / 4);\n"
        "    if (xy.x < p.w && xy.y < p.h) out.write(texel(b, p.kind, i), xy, g.z); }\n"
        "}\n";
    NSError* error = nil;
    id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
    if (!library) {
      REXLOG_WARN("[native] BC decode kernels: {}", error.localizedDescription.UTF8String);
    } else {
      pso[0] = [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"bc2d"] error:&error];
      pso[1] = [device newComputePipelineStateWithFunction:[library newFunctionWithName:@"bccube"] error:&error];
    }
  }
  return pso[cube ? 1 : 0];
}

// The texture for BC blocks, expanded on the GPU; nil if the kernel is
// unavailable (the caller then decodes on the CPU).
id<MTLTexture> BcDecodeOnGpu(id<MTLDevice> device, const Texture& t) {
  id<MTLComputePipelineState> pso = BcPipeline(device, t.cube);
  if (!pso || !bc_queue) return nil;
  MTLTextureDescriptor* desc = [MTLTextureDescriptor new];
  desc.pixelFormat = MTLPixelFormatRGBA8Unorm;
  desc.width = t.width;
  desc.height = t.height;
  if (t.cube) desc.textureType = MTLTextureTypeCube;
  desc.usage = MTLTextureUsageShaderRead | MTLTextureUsageShaderWrite | MTLTextureUsagePixelFormatView;
  desc.storageMode = MTLStorageModePrivate;
  id<MTLTexture> base = NewTexture(device, desc, "bc-gpu");
  if (!base) return nil;
  id<MTLBuffer> blocks = [device newBufferWithBytes:t.data.data() length:t.data.size()
                                            options:MTLResourceStorageModeShared];
  if (!bc_cb) {
    bc_cb = [bc_queue commandBuffer];
    bc_cb.label = @"BC decode";
    bc_enc = [bc_cb computeCommandEncoder];
  }
  const uint32_t bw = (t.width + 3) / 4, bh = (t.height + 3) / 4;
  const uint32_t kind = t.format == MTLPixelFormatBC1_RGBA ? 1 : t.format == MTLPixelFormatBC2_RGBA ? 2 : 3;
  struct { uint32_t bw, bh, w, h, kind, layer_bytes; } params = {
      bw, bh, t.width, t.height, kind, uint32_t(t.data.size() / (t.cube ? 6 : 1))};
  [bc_enc setComputePipelineState:pso];
  [bc_enc setBuffer:blocks offset:0 atIndex:0];
  [bc_enc setBytes:&params length:sizeof(params) atIndex:1];
  [bc_enc setTexture:base atIndex:0];
  [bc_enc dispatchThreads:MTLSizeMake(bw, bh, t.cube ? 6 : 1) threadsPerThreadgroup:MTLSizeMake(8, 8, 1)];
  // The fetch swizzle on a view: a texture the kernel writes carries none.
  const MTLTextureSwizzleChannels identity = MTLTextureSwizzleChannelsDefault;
  if (std::memcmp(&t.swizzle, &identity, sizeof(identity)) == 0) return base;
  return [base newTextureViewWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                 textureType:base.textureType
                                      levels:NSMakeRange(0, 1)
                                      slices:NSMakeRange(0, t.cube ? 6 : 1)
                                     swizzle:t.swizzle];
}

// This frame's decodes, committed ahead of the frame (same queue).
void BcFlush() {
  if (!bc_cb) return;
  [bc_enc endEncoding];
  [bc_cb commit];
  bc_cb = nil;
  bc_enc = nil;
}

id<MTLTexture> GpuTextureFor(id<MTLDevice> device, const std::shared_ptr<const Texture>& tp) {
  const Texture& t = *tp;
  if (t.format == MTLPixelFormatInvalid) {
    return nil;
  }
  if (t.gpu.texture) {
    return t.gpu.texture;
  }
  if (t.data.empty()) {
    return nil;  // not expected: uploaded textures keep their Metal copy
  }
  const auto upload_start = std::chrono::steady_clock::now();
  if (t.bc_on_gpu) {
    if (id<MTLTexture> tex = BcDecodeOnGpu(device, t)) {
      t.gpu.texture = tex;
      t.gpu.bytes = tex.allocatedSize;
      residency::Add(tex);
      ++gpu_texture_count;
      gpu_texture_bytes += int64_t(t.gpu.bytes);
      ++frame_uploads;
      frame_upload_bytes += t.data.size();
      frame_upload_us += uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                      std::chrono::steady_clock::now() - upload_start).count());
      decltype(t.data)().swap(t.data);
      return tex;
    }
    return nil;  // no kernel: drawn without it (logged once at its compile)
  }
  MTLTextureDescriptor* desc = [MTLTextureDescriptor new];
  desc.pixelFormat = t.format;
  desc.width = t.width;
  desc.height = t.height;
  desc.swizzle = t.swizzle;
  if (t.volume) {
    desc.textureType = MTLTextureType3D;
    desc.depth = t.depth;
  } else if (t.cube) {
    desc.textureType = MTLTextureTypeCube;
  }
  id<MTLTexture> tex = NewTexture(device, desc, "desc@3");
  const size_t layers = t.volume ? t.depth : t.cube ? 6 : 1;
  const size_t layer_bytes = t.data.size() / layers;
  if (t.volume) {
    [tex replaceRegion:MTLRegionMake3D(0, 0, 0, t.width, t.height, t.depth)
           mipmapLevel:0
                 slice:0
             withBytes:t.data.data()
           bytesPerRow:t.row_bytes
         bytesPerImage:layer_bytes];
  } else {
    for (NSUInteger layer = 0; layer < layers; ++layer) {
      [tex replaceRegion:MTLRegionMake2D(0, 0, t.width, t.height)
             mipmapLevel:0
                   slice:layer
               withBytes:t.data.data() + layer * layer_bytes
             bytesPerRow:t.row_bytes
           bytesPerImage:layer_bytes];
    }
  }
  t.gpu.texture = tex;
  t.gpu.bytes = tex.allocatedSize;
  residency::Add(tex);
  ++gpu_texture_count;
  gpu_texture_bytes += int64_t(t.gpu.bytes);
  ++frame_uploads;
  frame_upload_bytes += t.data.size();
  frame_upload_us += uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                  std::chrono::steady_clock::now() - upload_start).count());
  decltype(t.data)().swap(t.data);  // the CPU copy is not needed any more
  return tex;
}

id<MTLSamplerState> SamplerFor(id<MTLDevice> device, bool linear, uint32_t clamp_x, uint32_t clamp_y,
                               bool volume_or_cube, uint32_t max_anisotropy = 1) {
  max_anisotropy = std::clamp(max_anisotropy, 1u, 16u);
  const uint32_t key = (linear ? 1u : 0u) | (clamp_x << 1) | (clamp_y << 4) |
                       (volume_or_cube ? 1u << 7 : 0u) | (max_anisotropy << 8);
  auto found = gpu_samplers.find(key);
  if (found != gpu_samplers.end()) {
    return found->second;
  }
  id<MTLSamplerState> s;
  {
    MTLSamplerDescriptor* sd = [MTLSamplerDescriptor new];
    sd.minFilter = sd.magFilter = linear ? MTLSamplerMinMagFilterLinear : MTLSamplerMinMagFilterNearest;
    sd.sAddressMode = volume_or_cube ? MTLSamplerAddressModeClampToEdge : AddressMode(clamp_x);
    sd.tAddressMode = volume_or_cube ? MTLSamplerAddressModeClampToEdge : AddressMode(clamp_y);
    sd.rAddressMode = MTLSamplerAddressModeClampToEdge;
    sd.maxAnisotropy = max_anisotropy;
    sd.supportArgumentBuffers = YES;
    s = [device newSamplerStateWithDescriptor:sd];
  }
  gpu_samplers[key] = s;
  return s;
}

// The array's GPU copy (made once, in the arena): its buffer, and the offset
// in it.
// A small direct-mapped cache in front of gpu_buffers (one hash lookup per
// vertex input per draw added up to ~0.5 ms a frame): its entries point into
// the map, whose nodes stay put until erased; SweepGpu clears an erased
// entry's slot.
struct GpuBufferSlot {
  const void* key = nullptr;
  GpuBuffer* entry = nullptr;
};
GpuBufferSlot gpu_buffer_slots[4096];

template <typename T>
id<MTLBuffer> GpuBufferFor(id<MTLDevice> device, const std::shared_ptr<T>& values, size_t& offset) {
  GpuBufferSlot& slot = gpu_buffer_slots[(uintptr_t(values.get()) >> 4) & 4095];
  if (slot.key != values.get()) {
    slot.key = values.get();
    slot.entry = &gpu_buffers[values.get()];
  }
  GpuBuffer& g = *slot.entry;
  g.last_used = gpu_frame;
  if (!g.buffer) {
    const size_t size = std::max<size_t>(values->size() * sizeof(values->front()), 16);
    if (!buffer_arena.Allocate(device, size, g.chunk, g.buffer, g.offset)) {
      offset = 0;
      return nil;
    }
    ++frame_new_buffers;
    g.keep = values;
    g.size = size;
    std::memcpy(static_cast<uint8_t*>(g.buffer.contents) + g.offset, values->data(),
                values->size() * sizeof(values->front()));
  }
  offset = g.offset;
  return g.buffer;
}

void SweepGpu() {
  if ((gpu_frame & 63) != 0) return;

  for (auto it = gpu_buffers.begin(); it != gpu_buffers.end();) {
    if (gpu_frame - it->second.last_used > 600) {
      if (it->second.buffer) buffer_arena.Release(it->second.chunk, it->second.size);
      GpuBufferSlot& slot = gpu_buffer_slots[(uintptr_t(it->first) >> 4) & 4095];
      if (slot.key == it->first) slot = GpuBufferSlot{};  // only this entry's slot
      it = gpu_buffers.erase(it);
    } else {
      ++it;
    }
  }
}

// The on-screen layer (made on the main thread) and its pipeline.
CAMetalLayer* present_layer = nil;
UIView* present_view = nil;
std::atomic<bool> layer_visible{true};

// Shows or hides the native layer (on the main thread), only on a change.
void UpdateLayerVisibility(bool visible) {
  if (!present_view || layer_visible.exchange(visible) == visible) {
    return;
  }
  dispatch_async(dispatch_get_main_queue(), ^{
    present_view.hidden = !visible;
  });
  REXLOG_INFO("[native] native layer {}", visible ? "shown" : "hidden (no native output: the emulated "
                                                              "renderer's shows)");
}
id<MTLRenderPipelineState> PresentPipeline(id<MTLDevice> device) {
  static id<MTLRenderPipelineState> pso;
  if (pso) {
    return pso;
  }
  NSString* source = @"#include <metal_stdlib>\n"
                      "using namespace metal;\n"
                      "struct V { float4 p [[position]]; float2 uv; };\n"
                      "vertex V vs(uint id [[vertex_id]], constant float4& fit [[buffer(0)]]) {\n"
                      "  float2 uv = float2((id << 1) & 2, id & 2);\n"
                      "  V v; v.p = float4((uv * 2.0 - 1.0) * fit.xy, 0.0, 1.0); v.uv = float2(uv.x, 1.0 - uv.y); return v; }\n"
                      "fragment float4 ps(V in [[stage_in]], texture2d<float> t [[texture(0)]],\n"
                      "                   constant float4& crop [[buffer(0)]]) {\n"
                      "  constexpr sampler s(filter::linear, address::clamp_to_edge);\n"
                      "  return float4(t.sample(s, in.uv * crop.xy).rgb, 1.0); }\n";
  NSError* error = nil;
  id<MTLLibrary> library = [device newLibraryWithSource:source options:nil error:&error];
  if (!library) {
    REXLOG_WARN("[native] present shader: {}", error.localizedDescription.UTF8String);
    return nil;
  }
  MTLRenderPipelineDescriptor* desc = [MTLRenderPipelineDescriptor new];
  desc.vertexFunction = [library newFunctionWithName:@"vs"];
  desc.fragmentFunction = [library newFunctionWithName:@"ps"];
  desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
  pso = [device newRenderPipelineStateWithDescriptor:desc error:&error];
  return pso;
}

void RenderFrame(std::unique_ptr<Frame> frame, uint32_t number, bool present, bool dump) {
  // RenderFrame is called on the renderer's serial dispatch queue. Accumulate
  // the game-thread capture diagnostics here so the hot draw path stays local.
  static VertexDiagnostics vertex_diagnostics;
  if (!dump) vertex_diagnostics += frame->vertex_diagnostics;
  const auto render_start = std::chrono::steady_clock::now();
  struct RenderTimer {
    std::chrono::steady_clock::time_point t0;
    ~RenderTimer() {
      render_us += uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                std::chrono::steady_clock::now() - t0).count());
    }
  } render_timer{render_start};
  gpu_pool.Reclaim(number);
  // This frame's pooled buffers and textures: retired when it ends.
  struct FrameResources {
    uint32_t number;
    std::vector<id> objects;
    ~FrameResources() {
      for (id o : objects) gpu_pool.Retire(o, number);
    }
  } frame_resources{number, {}};
  auto pooled_buffer = [&](size_t length, MTLResourceOptions options, bool zero = true) {
    id<MTLBuffer> b = gpu_pool.Buffer(store.device, length, options, zero);
    frame_resources.objects.push_back(b);
    return b;
  };
  frame_uploads = 0;
  frame_new_buffers = 0;
  frame_upload_bytes = 0;
  frame_upload_us = 0;
  double drawable_wait_ms = 0;
  @autoreleasepool {
    id<MTLDevice> device = store.device;
    static id<MTLCommandQueue> queue = [device newCommandQueue];
    bc_queue = queue;  // BC decodes go on the frame's queue (BcDecodeOnGpu)
    residency::Apply(device, queue);
    ++gpu_frame;
    SweepGpu();

    // Textures and samplers, and the shaders' descriptor heaps (argument
    // buffers of resource IDs): 2D textures by index, index 0 a 1x1 white.
    MTLTextureDescriptor* white_desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                          width:1
                                                                                         height:1
                                                                                      mipmapped:NO];
    static id<MTLTexture> white = NewTexture(device, white_desc, "white_desc@4");
    static bool white_filled = false;
    if (!white_filled) {
      const uint32_t white_pixel = 0xFFFFFFFF;
      [white replaceRegion:MTLRegionMake2D(0, 0, 1, 1) mipmapLevel:0 withBytes:&white_pixel bytesPerRow:4];
      white_filled = true;
    }
    NSMutableArray<id<MTLTexture>>* textures = [NSMutableArray arrayWithObject:white];
    NSMutableArray<id<MTLSamplerState>>* samplers = [NSMutableArray array];
    // Match the launcher's anisotropic_override values: -1 uses each Xenos
    // texture's fetch constant, 0 disables it, and 1..5 select 1x..16x.
    // Query by name because this cvar is owned by the Vulkan GPU plugin and
    // the native renderer lives in the app binary.
    const int32_t anisotropic_override = rex::cvar::Query<int32_t>("anisotropic_override");
    // Cube and 3D textures go to their own heaps (index 0 a placeholder);
    // their slot in the 2D list holds white so indices stay aligned.
    NSMutableArray<id<MTLTexture>>* cubes = [NSMutableArray array];
    std::vector<uint32_t> cube_index(frame->textures.size(), 0);
    NSMutableArray<id<MTLTexture>>* volumes = [NSMutableArray array];
    std::vector<uint32_t> volume_index(frame->textures.size(), 0);
    for (size_t i = 0; i < frame->textures.size(); ++i) {
      const Texture& t = *frame->textures[i];
      id<MTLTexture> tex = GpuTextureFor(device, frame->textures[i]);
      if (tex && t.volume) {
        [volumes addObject:tex];
        volume_index[i] = uint32_t(volumes.count);  // 0 is the placeholder
        tex = nil;
      } else if (tex && t.cube) {
        [cubes addObject:tex];
        cube_index[i] = uint32_t(cubes.count);
        tex = nil;
      }
      [textures addObject:tex ?: white];
      uint32_t anisotropy = 1;
      if (t.linear_filter && !t.cube && !t.volume) {
        const uint32_t fetch_anisotropy = uint32_t(t.aniso_filter);
        const uint32_t selected = anisotropic_override < 0
                                      ? fetch_anisotropy
                                      : anisotropic_override == 0
                                            ? 0u
                                            : uint32_t(std::min(anisotropic_override, 5));
        if (selected >= uint32_t(xenos::AnisoFilter::kMax_1_1) &&
            selected <= uint32_t(xenos::AnisoFilter::kMax_16_1)) {
          anisotropy = 1u << (selected - uint32_t(xenos::AnisoFilter::kMax_1_1));
        }
      }
      [samplers addObject:SamplerFor(device, t.linear_filter || t.cube || t.volume, t.clamp_x, t.clamp_y,
                                     t.cube || t.volume, anisotropy)];
    }
    [samplers insertObject:SamplerFor(device, true, 2, 2, false) atIndex:0];
    BcFlush();  // the frame's BC decodes run before the frame

    auto heap = [&](NSArray* objects, bool are_samplers) {
      // Room for the textures resolves make while the frame is encoded.
      id<MTLBuffer> b = pooled_buffer((std::max<NSUInteger>(objects.count, 1) + frame->resolves.size() * 4 +
                                       frame->textures.size() * 2) * 8,
                                      MTLResourceStorageModeShared);
      auto* ids = static_cast<MTLResourceID*>(b.contents);
      for (NSUInteger i = 0; i < objects.count; ++i) {
        ids[i] = are_samplers ? [(id<MTLSamplerState>)objects[i] gpuResourceID]
                              : [(id<MTLTexture>)objects[i] gpuResourceID];
      }
      return b;
    };
    id<MTLBuffer> texture_heap = heap(textures, false);
    id<MTLBuffer> sampler_heap = heap(samplers, true);
    {
      // The resolves (and their views) get heap indices past the frame's
      // textures, and draws use the same index for the sampler: those sampler
      // entries were left 0, no sampler. The A19 and M4 sample with defaults
      // anyway; the A16 (iPhone 14 Pro Max) and the M1 read black: the whole
      // scene, which reaches the screen through resolves, was black there.
      // A linear, clamped sampler in every entry past the textures'.
      id<MTLSamplerState> resolve_sampler = SamplerFor(device, true, 2, 2, false);
      auto* ids = static_cast<MTLResourceID*>(sampler_heap.contents);
      const NSUInteger capacity = sampler_heap.length / sizeof(MTLResourceID);
      for (NSUInteger i = samplers.count; i < capacity; ++i) ids[i] = resolve_sampler.gpuResourceID;
    }
    // Array, 3D and cube textures: not decoded yet; every index reads a 1x1
    // placeholder of the right type (a heap of one entry is enough: all the
    // indices of those types are 0).
    // Filled with black: a texture that is missing must not show garbage.
    auto dummy = [&](MTLTextureType type) {
      // Built the canonical way for each type (a cube from its own factory):
      // the A16 (iPhone 14 Pro Max) aborted in MTLTextureDescriptor
      // validation on the hand-filled 1x1 cube descriptor.
      MTLTextureDescriptor* desc = nil;
      if (type == MTLTextureTypeCube) {
        desc = [MTLTextureDescriptor textureCubeDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                     size:1
                                                                mipmapped:NO];
      } else {
        desc = [MTLTextureDescriptor new];
        desc.textureType = type;
        desc.pixelFormat = MTLPixelFormatRGBA8Unorm;
        desc.width = desc.height = 1;
        desc.depth = 1;
        desc.arrayLength = 1;
      }
      desc.usage = MTLTextureUsageShaderRead;
      desc.storageMode = MTLStorageModeShared;
      id<MTLTexture> tex = NewTexture(device, desc, "desc@5");
      const uint32_t black = 0xFF000000;
      const NSUInteger slices = type == MTLTextureTypeCube ? 6 : 1;
      for (NSUInteger s = 0; s < slices; ++s) {
        [tex replaceRegion:MTLRegionMake3D(0, 0, 0, 1, 1, 1) mipmapLevel:0 slice:s withBytes:&black
               bytesPerRow:4 bytesPerImage:4];
      }
      return tex;
    };
    static id<MTLTexture> dummy_array = dummy(MTLTextureType2DArray);
    static id<MTLTexture> dummy_volume = dummy(MTLTextureType3D);
    static id<MTLTexture> dummy_cube = dummy(MTLTextureTypeCube);
    static id<MTLTexture> grey_volume = [&] {  // the 3D texture test: mid grey
      id<MTLTexture> t = dummy(MTLTextureType3D);
      const uint32_t grey = 0xFF808080;
      [t replaceRegion:MTLRegionMake3D(0, 0, 0, 1, 1, 1) mipmapLevel:0 slice:0 withBytes:&grey
           bytesPerRow:4 bytesPerImage:4];
      residency::Add(t);
      return t;
    }();
    static const bool dummies_resident = [] {
      residency::Add(dummy_array);
      residency::Add(dummy_volume);
      residency::Add(dummy_cube);
      return true;
    }();
    (void)dummies_resident;
    id<MTLBuffer> array_heap = heap(@[ dummy_array ], false);
    [volumes insertObject:dummy_volume atIndex:0];
    [volumes addObject:grey_volume];  // last: the 3D texture test's index
    const uint32_t grey_volume_index = uint32_t(volumes.count - 1);
    id<MTLBuffer> volume_heap = heap(volumes, false);
    [cubes insertObject:dummy_cube atIndex:0];
    id<MTLBuffer> cube_heap = heap(cubes, false);
    static id<MTLBuffer> zeros = [device newBufferWithLength:1 << 16 options:MTLResourceStorageModeShared];
    static const bool zeros_resident = (residency::Add(zeros), true);
    (void)zeros_resident;

    // Per-draw data in one shared buffer: VS constants, PS constants, shared
    // constants, vertex attributes, indices.
    // Constants: the registers the draw's shader reads, uploaded again only
    // when they are not already (the same set, a range that covers them).
    struct UploadedConstants {
      const void* set = nullptr;
      std::pair<uint16_t, uint16_t> range{0, 0};
      size_t at = 0;
      bool Covers(const void* s, std::pair<uint16_t, uint16_t> r) const {
        return r.first >= r.second || (set == s && range.first <= r.first && r.second <= range.second);
      }
    };
    size_t total = 0;
    {
      UploadedConstants vs, ps;
      for (const Draw& d : frame->draws) {
        if (!vs.Covers(d.vs_constants.get(), d.vs_range)) {
          total += (d.vs_range.second - d.vs_range.first) * 16 + 256;
          vs = {d.vs_constants.get(), d.vs_range};
        }
        if (!ps.Covers(d.ps_constants.get(), d.ps_range)) {
          total += (d.ps_range.second - d.ps_range.first) * 16 + 256;
          ps = {d.ps_constants.get(), d.ps_range};
        }
      }
    }
    for (const Draw& d : frame->draws) {
      total += 1024 + 256 + (d.indices_fresh ? d.index_count() * 4 + 256 : 0);
      for (const Attribute& a : d.attributes) {
        if (a.fresh && a.values) total += a.values->size() * 4 + 256;
      }
    }
    // Every byte read from it is written by put() first: not zeroed.
    id<MTLBuffer> data = pooled_buffer(std::max<size_t>(total, 256), MTLResourceStorageModeShared, false);
    uint8_t* cursor = static_cast<uint8_t*>(data.contents);
    size_t used = 0;
    UploadedConstants uploaded_vs, uploaded_ps;
    // What the current encoder already has set: a draw sets only what differs
    // from the draw before (each set costs the driver; most draws in a pass
    // share their pipeline, depth state, viewport and vertex buffers, and the
    // cached arrays share a few large buffers, so mostly only the offset
    // changes). Reset with each new encoder.
    struct EncoderState {
      __unsafe_unretained id<MTLRenderCommandEncoder> enc = nil;
      __unsafe_unretained id<MTLRenderPipelineState> pso = nil;
      __unsafe_unretained id<MTLDepthStencilState> ds = nil;
      bool viewport_set = false, scissor_set = false, push_set = false;
      MTLViewport viewport{};
      MTLScissorRect scissor{};
      uint64_t push[3] = {};
      __unsafe_unretained id<MTLBuffer> vb[31] = {};
      NSUInteger vb_offset[31] = {};
      void For(id<MTLRenderCommandEncoder> e) {
        if (e == enc) return;
        *this = EncoderState{};
        enc = e;
      }
      void VertexBuffer(id<MTLBuffer> b, NSUInteger offset, NSUInteger index) {
        if (vb[index] == b) {
          if (vb_offset[index] != offset) {
            [enc setVertexBufferOffset:offset atIndex:index];
            vb_offset[index] = offset;
          }
          return;
        }
        [enc setVertexBuffer:b offset:offset atIndex:index];
        vb[index] = b;
        vb_offset[index] = offset;
      }
    } state;
    uint32_t last_shared[256];
    size_t last_shared_at = 0;
    bool have_last_shared = false;
    auto put = [&](const void* bytes, size_t size) {
      used = (used + 255) & ~size_t(255);
      std::memcpy(cursor + used, bytes, size);
      const size_t at = used;
      used += size;
      return at;
    };

    // Render targets: one per EDRAM colour base + pitch + format; the height
    // from the largest scissor bottom of their draws.
    // Kept across frames: recreated only when a size or format changes.
    static std::map<std::string, Target> targets;
    for (auto& [key, t] : targets) {
      t.used = false;
      t.clear_color = t.clear_depth = false;
      t.draws = 0;
    }
    std::map<std::string, std::pair<uint32_t, uint32_t>> sizes;  // this frame's pitch, height (guest pixels)
    std::map<std::string, uint32_t> sample_counts;
    // Depth-only draws per target (no colour written): a target drawn mostly
    // that way is a shadow map, kept at 1x unless nfsmw_native_scale_shadows
    // (a 1600 x 1600 map is 3200 x 3200 at 2x, for little visible gain).
    std::map<std::string, uint32_t> depth_only_draws;
    std::map<std::string, std::string> second_of;  // MRT: the second target's first target
    const float resolution_scale = NativeResolutionScale();
    const bool msaa_disabled = rex::cvar::Query<bool>("gpu_sin_msaa");
    const int32_t configured_maximum = rex::cvar::Query<int32_t>("gpu_msaa_muestras");
    const uint32_t maximum_samples = configured_maximum >= 4 ? 4u : configured_maximum >= 2 ? 2u : 1u;
    static bool settings_logged = false;
    if (!settings_logged) {
      settings_logged = true;
      REXLOG_INFO("[native] internal resolution {:.3f}x (setting {}), MSAA {} (up to {}x)", resolution_scale,
                  REXCVAR_GET(nfsmw_native_resolution_scale),
                  msaa_disabled ? "off" : "from game targets", maximum_samples);
    }
    // A target per pass: each time the render target registers change, a
    // fresh image (the shadow map and the final UI pass share colour base,
    // pitch and depth buffer). A pass resumed later is not merged yet.
    std::vector<uint32_t> pass_of(frame->draws.size());
    {
      uint32_t pass = 0;
      for (size_t i = 0; i < frame->draws.size(); ++i) {
        const Draw& d = frame->draws[i];
        if (i && (d.surface_info != frame->draws[i - 1].surface_info ||
                  d.color_info != frame->draws[i - 1].color_info ||
                  d.depth_info != frame->draws[i - 1].depth_info)) {
          ++pass;
        }
        pass_of[i] = pass;
      }
    }
    size_t draw_number = 0;
    auto target_key = [&](const Draw& d) {
      const size_t i = &d - frame->draws.data();
      (void)draw_number;
      // Keyed by EDRAM location, shared across the frame like the console's
      // EDRAM: a resolve copies everything drawn there since its last clear
      // (pass_of is kept for the log only).
      (void)pass_of[i];
      return EdramKey(d.surface_info, d.color_info, d.depth_info);
    };
    for (const Draw& d : frame->draws) {
      const std::string key = target_key(d);
      Target& t = targets[key];
      auto& size = sizes[key];
      size.first = std::max<uint32_t>(d.surface_info & 0x3FFF, 1);
      if ((d.color_mask & 0xF) == 0) ++depth_only_draws[key];
      sample_counts[key] = NativeSampleCount(device, d.surface_info, msaa_disabled, maximum_samples);
      // The height: the viewport's bottom (the scissor is often the whole
      // EDRAM range).
      const float viewport_bottom = ((d.vte & 8) ? d.viewport[3] : 0.0f) + std::fabs((d.vte & 4) ? d.viewport[2] : 1.0f);
      const uint32_t bottom = viewport_bottom >= 16 ? uint32_t(std::ceil(viewport_bottom)) : d.scissor[3];
      size.second = std::max(size.second, std::min<uint32_t>(bottom, 2048));
      t.draws++;
      t.format = (d.color_info >> 16) & 0xF;
      if (d.second_target) {
        const std::string key1 = EdramKey(d.surface_info, d.color1_info, d.depth_info);
        Target& t1 = targets[key1];
        auto& size1 = sizes[key1];
        size1.first = size.first;
        size1.second = std::max(size1.second, size.second);
        t1.draws++;
        t1.format = (d.color1_info >> 16) & 0xF;
        sample_counts[key1] = sample_counts[key];
        second_of[key1] = key;
      }
    }
    const bool scale_shadows = REXCVAR_GET(nfsmw_native_scale_shadows);
    auto scale_of = [&](const std::string& key) -> float {
      const auto first = second_of.find(key);
      const std::string& k = first != second_of.end() ? first->second : key;
      const bool shadow = depth_only_draws[k] * 2 > targets[k].draws;
      return shadow && !scale_shadows ? 1.0f : resolution_scale;
    };
    for (auto& [key, size] : sizes) {
      Target& t = targets[key];
      const float scale = scale_of(key);
      const uint32_t pitch = Px(size.first, scale);
      const uint32_t height = std::max<uint32_t>(Px(size.second, scale), 16);
      t.scale = scale;
      if (t.color && t.pitch == pitch && t.height == height &&
          t.color.pixelFormat == ColorFormat(t.format) &&
          t.requested_sample_count == sample_counts[key]) {
        continue;  // the same target as the last frame's
      }
      // Replaced (another size or format): the old ones leave the residency set.
      if (t.multisample_color != t.color) residency::Remove(t.multisample_color);
      if (t.multisample_depth != t.depth) residency::Remove(t.multisample_depth);
      residency::Remove(t.color);
      residency::Remove(t.depth);
      t.pitch = pitch;
      t.height = height;
      t.requested_sample_count = sample_counts[key];
      t.sample_count = sample_counts[key];
      MTLTextureDescriptor* cd = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:ColorFormat(t.format)
                                                                                    width:t.pitch
                                                                                   height:t.height
                                                                                mipmapped:NO];
      cd.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
      t.color = NewTexture(device, cd, "cd@6");
      MTLTextureDescriptor* dd = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatDepth32Float_Stencil8
                                                                                    width:t.pitch
                                                                                   height:t.height
                                                                                mipmapped:NO];
      dd.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;  // depth resolves read it
      dd.storageMode = MTLStorageModePrivate;
      t.depth = NewTexture(device, dd, "dd@7");
      if (t.sample_count > 1) {
        MTLTextureDescriptor* cm = [MTLTextureDescriptor new];
        cm.textureType = MTLTextureType2DMultisample;
        cm.pixelFormat = cd.pixelFormat;
        cm.width = t.pitch;
        cm.height = t.height;
        cm.sampleCount = t.sample_count;
        cm.usage = MTLTextureUsageRenderTarget;
        cm.storageMode = MTLStorageModePrivate;
        MTLTextureDescriptor* dm = [MTLTextureDescriptor new];
        dm.textureType = MTLTextureType2DMultisample;
        dm.pixelFormat = dd.pixelFormat;
        dm.width = t.pitch;
        dm.height = t.height;
        dm.sampleCount = t.sample_count;
        dm.usage = MTLTextureUsageRenderTarget;
        dm.storageMode = MTLStorageModePrivate;
        @try {
          t.multisample_color = NewTexture(device, cm, "cm@8");
          t.multisample_depth = NewTexture(device, dm, "dm@9");
        } @catch (NSException* e) {
          t.multisample_color = nil;
          t.multisample_depth = nil;
        }
        if (!t.multisample_color || !t.multisample_depth) {
          REXLOG_WARN("[native] {}x MSAA target allocation failed; using 1x for {}", t.sample_count, key);
          t.sample_count = 1;
        }
      }
      if (t.sample_count == 1) {
        t.multisample_color = t.color;
        t.multisample_depth = t.depth;
      }
      residency::Add(t.color);
      residency::Add(t.depth);
      if (t.multisample_color != t.color) residency::Add(t.multisample_color);
      if (t.multisample_depth != t.depth) residency::Add(t.multisample_depth);
    }

    // A target starts the frame as the game's resolves clear it (they clear
    // for the next frame): the clear values of the last clearing resolve of
    // that layout in this frame.
    for (const ResolveEvent& ev : frame->resolves) {
      auto it = targets.find(EdramKey(ev.surface_info, ev.color_info, ev.depth_info));
      if (it == targets.end()) continue;
      if (ev.clear_color) {
        const uint32_t c = ev.clear_color_value;
        it->second.clear_color = true;
        it->second.clear_color_value = MTLClearColorMake(((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0,
                                                         (c & 0xFF) / 255.0, (c >> 24) / 255.0);
      }
      if (ev.clear_depth) {
        it->second.clear_depth = true;
        it->second.clear_depth_value = double(ev.clear_depth_value >> 8) / double(0xFFFFFF);
      }
    }

    // Pipelines by their state (no strings per draw).
    pipeline_cache.WarmUp(device);
    pipeline_cache.Collect();
    const bool async_pipelines = REXCVAR_GET(nfsmw_native_async_pipelines);
    static std::map<uint32_t, id<MTLDepthStencilState>> depth_states;
    uint32_t drawn = 0, pipeline_failures = 0, screen_space_game_draws = 0;
    std::vector<std::string> order;  // targets in order of first use

    id<MTLCommandBuffer> cb = [queue commandBuffer];
    // Resolved textures by destination address -> heap index.
    std::map<uint32_t, uint32_t> resolved;
    // For sampling a resolve the way the console does: what it swapped in
    // memory (RB_COPY_DEST_INFO swap) then the fetch constant's swizzle.
    std::map<uint32_t, id<MTLTexture>> resolved_texture;
    std::map<uint32_t, bool> resolved_swap;
    std::map<uint32_t, float> resolved_scale;  // the resolution scale of its source target
    // (resolved texture, swizzle | swap << 12, width, height) -> heap index:
    // keyed by the texture, not the address (one address can be resolved
    // several times in a frame: each resolve is a new texture).
    std::map<std::tuple<uintptr_t, uint32_t, uint32_t, uint32_t>, uint32_t> resolved_views;
    // Cubes the frame samples at addresses it resolves to (placeholders):
    // each face resolved to base + face * face size (the race's environment
    // map: six 256x256 resolves 0x40000 apart).
    struct CubeTarget {
      uint32_t base, width, face_stride;
    };
    std::vector<CubeTarget> cube_targets;
    NSMutableArray<id<MTLTexture>>* assembled_cubes = [NSMutableArray array];  // made resident
    for (const auto& tp : frame->textures) {
      if (tp->cube && tp->format == MTLPixelFormatInvalid && tp->width) {
        const uint32_t w32 = (tp->width + 31) & ~31u;
        const uint32_t stride = (w32 * 4 * ((tp->height + 31) & ~31u) + 4095) & ~4095u;
        cube_targets.push_back({tp->address, tp->width, stride});
      }
    }
    // Resolved cubes (faces resolved one by one) by address -> cube heap index.
    std::map<uint32_t, id<MTLTexture>> resolved_cubes;
    std::map<uint32_t, uint32_t> resolved_cube_index;
    // Whether the faces' resolves swapped red and blue in memory (sampled
    // like 2D resolves: that swap, then the fetch swizzle), and the swizzled
    // views made for them: (cube, swizzle | swap << 12) -> cube heap index.
    std::map<uint32_t, bool> resolved_cube_swap;
    std::map<std::pair<uintptr_t, uint32_t>, uint32_t> cube_views;
    uint32_t next_cube = uint32_t(cubes.count);
    const uint32_t cube_capacity = uint32_t(cubes.count + frame->resolves.size() + cube_targets.size());
    // Cubes kept from earlier frames: bound from the frame's start.
    for (const CubeTarget& ct : cube_targets) {
      auto kept = kept_cubes.find(ct.base);
      if (kept == kept_cubes.end() || next_cube >= cube_capacity) continue;
      resolved_cubes[ct.base] = kept->second;
      resolved_cube_swap[ct.base] = kept_cube_swaps[ct.base];
      [assembled_cubes addObject:kept->second];
      static_cast<MTLResourceID*>(cube_heap.contents)[next_cube] = kept->second.gpuResourceID;
      resolved_cube_index[ct.base] = next_cube++;
    }
    NSMutableArray<id<MTLTexture>>* resolved_textures = [NSMutableArray array];
    uint32_t next_heap = uint32_t(textures.count);
    uint32_t resolves_done = 0, resolves_skipped = 0;
    std::vector<std::string> resolve_names;  // what each resolve copied, to save
    std::vector<CGRect> resolve_rects;
    const NSUInteger heap_capacity = textures.count + frame->resolves.size() * 4 + frame->textures.size() * 2;

    // What each 2D heap index holds (for the snapshot of watched draws' inputs).
    std::vector<id<MTLTexture>> heap_object(heap_capacity + 1);
    for (NSUInteger i = 0; i < textures.count; ++i) heap_object[i] = textures[i];
    // Watched draws (snapshot frames only): the first draws of these pixel
    // shaders save every 2D texture they are given, as Metal sees it.
    // The wet road, and the car body's two shaders.
    // Shadow receivers: the wet road and the fence/plant/static shader.
    static const std::set<uint64_t> watched = {0xaf393d4c46af230cull, 0x684f4711f29b9f77ull};
    std::map<uint64_t, int> watched_seen;
    struct WatchSave {
      id<MTLTexture> texture;
      std::string name;
    };
    std::vector<WatchSave> watch_saves;
    // Resolves from earlier frames the recording found unchanged: in the
    // heap from the start (a resolve in this frame replaces them).
    uint32_t kept_used = 0;
    for (const auto& tp : frame->textures) {
      if (!tp->persistent || resolved.count(tp->address)) continue;
      auto kept = kept_resolves.find(tp->address);
      if (kept == kept_resolves.end() || next_heap >= heap_capacity || kept->second.texture.textureType != MTLTextureType2D) continue;
      static_cast<MTLResourceID*>(texture_heap.contents)[next_heap] = kept->second.texture.gpuResourceID;
      heap_object[next_heap] = kept->second.texture;
      resolved[tp->address] = next_heap++;
      resolved_texture[tp->address] = kept->second.texture;
      resolved_swap[tp->address] = kept->second.swap;
      resolved_scale[tp->address] = kept->second.scale;
      [resolved_textures addObject:kept->second.texture];
      resolve_names.push_back("kept");
      resolve_rects.push_back(CGRectZero);
      ++kept_used;
    }
    id<MTLTexture> final_texture = nil;
    CGRect final_rect = CGRectZero;
    int32_t final_guest_width = 0, final_guest_height = 0;  // the displayed resolve's size in guest pixels
    std::vector<std::string> diagnostics;
    if (dump) {  // textures read with an exp_adjust (values * 2^n)
      std::set<std::string> seen;
      for (const auto& tp : frame->textures) {
        if (!tp->exp_adjust) continue;
        const std::string line = fmt::format("group exp_adjust: texture {:08x} {}x{} format {}{} exp_adjust {}", tp->address,
                                             tp->width, tp->height, int(tp->format),
                                             tp->format == MTLPixelFormatInvalid ? " (a resolve)" : "", tp->exp_adjust);
        if (seen.insert(line).second) diagnostics.push_back(line);
      }
    }
    size_t next_resolve = 0;

    id<MTLRenderCommandEncoder> enc = nil;
    std::string current;
    // Occlusion queries: each query's draws counted into a slot per pass
    // (counts are per render pass), summed when the GPU is done.
    id<MTLBuffer> visibility = nil;
    struct VisibilitySlot {
      int query;
      double divisor;  // samples per guest pixel: scale squared times MSAA samples
    };
    std::vector<VisibilitySlot> visibility_slots;
    std::vector<int> pass_slot(frame->queries.size(), -1);  // in the current pass
    __unsafe_unretained id<MTLRenderCommandEncoder> visibility_encoder = nil;
    int visibility_slot = -1;  // the slot the current encoder counts into
    if (!frame->queries.empty() && REXCVAR_GET(nfsmw_native_occlusion)) {
      static id<MTLBuffer> ring[kVisibilityBuffers];
      const int at = number % kVisibilityBuffers;
      if (!ring[at]) ring[at] = [device newBufferWithLength:kVisibilitySlots * 8 options:MTLResourceStorageModeShared];
      std::memset(ring[at].contents, 0, kVisibilitySlots * 8);
      visibility = ring[at];
    }
    size_t pass_indices = 0;  // indices drawn in the current pass (see nfsmw_native_pass_split_indices)
    uint32_t pass_splits = 0;
    const size_t split_after = size_t(std::max(REXCVAR_GET(nfsmw_native_pass_split_indices), 0));
    std::vector<__unsafe_unretained id<MTLResource>> resident;  // the arrays above keep them alive
    std::map<std::string, std::pair<size_t, size_t>> groups;  // snapshot: draw groups of the pass (first draw, count)
    std::string group_target;
    __unsafe_unretained id<MTLRenderCommandEncoder> clip_mode_encoder = nil;  // the depth clip mode set on
    bool clip_mode_clamp = false;
    // GPU profile (every frame while hitches are logged, else every 300th; not
    // in snapshots): a timestamp at the start and end of each pass and blit.
    // The log lists the costliest of every 300th frame and of slow frames.
    // One sample buffer per frame in flight.
    constexpr int kProfileBuffers = 4;
    static id<MTLCounterSampleBuffer> profile_buffers[kProfileBuffers] = {};
    static bool profile_checked = false;
    static MTLTimestamp profile_cpu0 = 0, profile_gpu0 = 0;
    if (!profile_checked) {
      profile_checked = true;
      if ([device supportsCounterSampling:MTLCounterSamplingPointAtStageBoundary]) {
        for (id<MTLCounterSet> set in device.counterSets) {
          if (![set.name isEqualToString:MTLCommonCounterSetTimestamp]) continue;
          MTLCounterSampleBufferDescriptor* sd = [MTLCounterSampleBufferDescriptor new];
          sd.counterSet = set;
          sd.sampleCount = 512;
          sd.storageMode = MTLStorageModeShared;
          for (auto& b : profile_buffers) b = [device newCounterSampleBufferWithDescriptor:sd error:nil];
          [device sampleTimestamps:&profile_cpu0 gpuTimestamp:&profile_gpu0];
        }
      }
      REXLOG_INFO("[native] GPU pass profiling {}", profile_buffers[kProfileBuffers - 1] ? "available" : "not available");
    }
    id<MTLCounterSampleBuffer> profile_buffer = profile_buffers[number % kProfileBuffers];
    const bool profile_report = number % 300 == 150;
    const bool profile = profile_buffer && !dump && (profile_report || hitch_lines_left.load() > 0);
    auto profile_labels = std::make_shared<std::vector<std::string>>();
    auto profile_pass = [&](MTLRenderPassDescriptor* rp, std::string label) {
      if (!profile || profile_labels->size() >= 255) return;
      const NSUInteger i = profile_labels->size();
      rp.sampleBufferAttachments[0].sampleBuffer = profile_buffer;
      rp.sampleBufferAttachments[0].startOfVertexSampleIndex = 2 * i;
      rp.sampleBufferAttachments[0].endOfVertexSampleIndex = MTLCounterDontSample;
      rp.sampleBufferAttachments[0].startOfFragmentSampleIndex = MTLCounterDontSample;
      rp.sampleBufferAttachments[0].endOfFragmentSampleIndex = 2 * i + 1;
      profile_labels->push_back(std::move(label));
    };
    auto new_blit = [&](const char* label) -> id<MTLBlitCommandEncoder> {
      if (!profile || profile_labels->size() >= 255) return [cb blitCommandEncoder];
      const NSUInteger i = profile_labels->size();
      MTLBlitPassDescriptor* bd = [MTLBlitPassDescriptor blitPassDescriptor];
      bd.sampleBufferAttachments[0].sampleBuffer = profile_buffer;
      bd.sampleBufferAttachments[0].startOfEncoderSampleIndex = 2 * i;
      bd.sampleBufferAttachments[0].endOfEncoderSampleIndex = 2 * i + 1;
      profile_labels->push_back(label);
      return [cb blitCommandEncoderWithDescriptor:bd];
    };
    // A colour resolve with an exponent bias: copied by a draw that scales by
    // 2^bias (a blit cannot). False when there is no bias: the caller blits.
    auto scaled_copy = [&](id<MTLTexture> from, id<MTLTexture> to, NSUInteger slice, NSUInteger fx, NSUInteger fy,
                           NSUInteger tx, NSUInteger ty, NSUInteger cw, NSUInteger ch, const ResolveEvent& ev,
                           const char* label) -> bool {
      if (!ev.exp_bias || !REXCVAR_GET(nfsmw_native_exp_bias) || !(to.usage & MTLTextureUsageRenderTarget)) {
        return false;
      }
      id<MTLRenderPipelineState> copy = ScaledCopyPipeline(device, to.pixelFormat);
      if (!copy || !cw || !ch) return false;
      {
        static std::set<std::pair<uint32_t, int32_t>> said;
        if (said.size() < 32 && said.insert({ev.dest_base, ev.exp_bias}).second) {
          REXLOG_INFO("[native] resolve to {:08x}{}: exponent bias {} (colour x {})", ev.dest_base,
                      ev.array ? fmt::format(" face {}", ev.slice) : std::string(), ev.exp_bias,
                      std::ldexp(1.0, ev.exp_bias));
        }
      }
      MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];
      rp.colorAttachments[0].texture = to;
      rp.colorAttachments[0].slice = slice;
      rp.colorAttachments[0].loadAction = MTLLoadActionLoad;
      rp.colorAttachments[0].storeAction = MTLStoreActionStore;
      profile_pass(rp, label);
      id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp];
      [e setRenderPipelineState:copy];
      [e setFragmentTexture:from atIndex:0];
      struct {
        float scale;
        float pad;  // int2 is 8-byte aligned in the shader
        int32_t offset[2];
      } c = {std::ldexp(1.0f, ev.exp_bias), 0.0f, {int32_t(fx) - int32_t(tx), int32_t(fy) - int32_t(ty)}};
      [e setFragmentBytes:&c length:sizeof(c) atIndex:0];
      [e setScissorRect:(MTLScissorRect){tx, ty, cw, ch}];
      [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
      [e endEncoding];
      return true;
    };
    auto writebacks = std::make_shared<std::vector<WriteBack>>();
    auto do_resolve = [&](const ResolveEvent& ev, const Draw& last) {
      // The source: the EDRAM layout in the resolve's own registers (a
      // thumbnail drawn in another layout may come between the scene and
      // its resolve); the last draw's target if that layout was not drawn.
      const std::string own_key = EdramKey(ev.surface_info, ev.color_info, ev.depth_info);
      auto found = targets.find(own_key);
      const bool own = found != targets.end() && found->second.color;
      Target& src = own ? found->second : targets[target_key(last)];
      diagnostics.push_back(fmt::format(
          "resolve {} after draw {}: ctrl {:08x} ({} rt{}, clear {}{}), reads {} ({}), last draw {}, "
          "rect {},{}-{},{} -> {:08x} {}x{} swap {} exp {}",
          resolves_done + resolves_skipped, ev.after_draws, ev.control, ev.depth ? "depth" : "color",
          ev.control & 3, ev.clear_color ? "C" : "-", ev.clear_depth ? "D" : "-", own_key,
          own ? "found" : "NOT drawn, using the last draw's", target_key(last), ev.x0, ev.y0, ev.x1, ev.y1,
          ev.dest_base, ev.dest_pitch, ev.dest_height, ev.swap, ev.exp_bias));
      [enc endEncoding];
      enc = nil;
      current.clear();
      const float scale = src.scale;
      NSUInteger dw = Px(ev.dest_pitch ? ev.dest_pitch : uint32_t(std::max(ev.x1, 1)), scale);
      NSUInteger dh = Px(ev.dest_height ? ev.dest_height : uint32_t(std::max(ev.y1, 1)), scale);

      // Edges rounded on their own, so that rectangles side by side meet.
      const NSUInteger x0 = Px(std::max(ev.x0, 0), scale);
      const NSUInteger y0 = Px(std::max(ev.y0, 0), scale);
      const NSUInteger x1 = std::max<NSUInteger>(Px(std::max(ev.x1, 0), scale), x0);
      const NSUInteger y1 = std::max<NSUInteger>(Px(std::max(ev.y1, 0), scale), y0);
      const NSUInteger w = std::min({x1 - x0, NSUInteger(src.pitch) - std::min<NSUInteger>(x0, src.pitch),
                                     dw - std::min(x0, dw)});
      const NSUInteger h = std::min({y1 - y0, NSUInteger(src.height) - std::min<NSUInteger>(y0, src.height),
                                     dh - std::min(y0, dh)});
      if (ev.array && !ev.depth && w && h) {
        // Into a face of a cube (the race's environment map, from its 320
        // passes): a Metal cube made at the first face, the face copied.
        id<MTLTexture> cube = resolved_cubes[ev.dest_base];
        if (!cube && next_cube < cube_capacity) {
          MTLTextureDescriptor* cd = [MTLTextureDescriptor textureCubeDescriptorWithPixelFormat:src.color.pixelFormat
                                                                                         size:std::max(w, h)
                                                                                    mipmapped:NO];
          cd.usage = MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView | MTLTextureUsageRenderTarget;
          cube = gpu_pool.Texture(device, cd);
          frame_resources.objects.push_back(cube);
          resolved_cubes[ev.dest_base] = cube;
          static_cast<MTLResourceID*>(cube_heap.contents)[next_cube] = cube.gpuResourceID;
          resolved_cube_index[ev.dest_base] = next_cube++;
          [resolved_textures addObject:cube];
          resolve_names.push_back(fmt::format("resolve_{:02}_cube_{}x{}_to_{:08x}", resolves_done, w, h, ev.dest_base));
          resolve_rects.push_back(CGRectMake(0, 0, w, h));
        }
        if (cube && ev.slice < 6) {
          resolved_cube_swap[ev.dest_base] = ev.swap;
          if (scaled_copy(src.color, cube, ev.slice, x0, y0, 0, 0, std::min(w, cube.width), std::min(h, cube.height),
                          ev, "cube face (exp bias)")) {
            ++resolves_done;
          } else {
          id<MTLBlitCommandEncoder> blit = new_blit("blit: cube face");
          [blit copyFromTexture:src.color
                    sourceSlice:0
                    sourceLevel:0
                   sourceOrigin:MTLOriginMake(x0, y0, 0)
                     sourceSize:MTLSizeMake(std::min(w, cube.width), std::min(h, cube.height), 1)
                      toTexture:cube
               destinationSlice:ev.slice
               destinationLevel:0
              destinationOrigin:MTLOriginMake(0, 0, 0)];
          [blit endEncoding];
          ++resolves_done;
          }
        } else {
          ++resolves_skipped;
        }
      } else if (!w || !h || dw > 8192 || dh > 8192 || next_heap >= heap_capacity) {
        ++resolves_skipped;
      } else {
        MTLTextureDescriptor* rd = [MTLTextureDescriptor
            texture2DDescriptorWithPixelFormat:(ev.depth ? MTLPixelFormatR32Float : src.color.pixelFormat)
                                         width:dw
                                        height:dh
                                     mipmapped:NO];
        rd.usage = ev.depth ? (MTLTextureUsageShaderRead | MTLTextureUsageRenderTarget)
                            : (MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView);
        if (!ev.depth && ev.exp_bias && REXCVAR_GET(nfsmw_native_exp_bias)) {
          rd.usage |= MTLTextureUsageRenderTarget;  // the scaled copy draws into it
        }
        id<MTLTexture> dest = nil;
        // Linear (slow for the GPU to write: a 1600 x 1600 shadow map copy took
        // 2.5 ms) only when the resolve does not fill its pitch, i.e. when
        // draws may sample it at a smaller size than the texture.
        const bool may_crop = NSUInteger(std::max(ev.x1 - ev.x0, 0)) < dw || NSUInteger(std::max(ev.y1 - ev.y0, 0)) < dh;
        if (may_crop) {
          // Linear, in a buffer, so draws sampling it at a smaller size get a
          // texture over the same memory (see the binding). Depth too: its
          // copy is an R32Float colour target (the depth-based post effects
          // sample it at the scene's size, e.g. 960 in a 1024 pitch).
          const MTLPixelFormat pf = rd.pixelFormat;
          const NSUInteger bpp = (pf == MTLPixelFormatRGBA16Float || pf == MTLPixelFormatRG32Float) ? 8 : 4;
          const NSUInteger align = [device minimumLinearTextureAlignmentForPixelFormat:pf];
          const NSUInteger row = (dw * bpp + align - 1) / align * align;
          rd.storageMode = MTLStorageModePrivate;
          dest = gpu_pool.Texture(device, rd, row);
        }
        if (!dest) {
          rd.storageMode = MTLStorageModePrivate;
          dest = gpu_pool.Texture(device, rd);
        }
        if (ev.depth) {
          id<MTLRenderPipelineState> copy = DepthCopyPipeline(device);
          MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];
          rp.colorAttachments[0].texture = dest;
          rp.colorAttachments[0].loadAction = MTLLoadActionClear;
          rp.colorAttachments[0].clearColor = MTLClearColorMake(1, 1, 1, 1);
          rp.colorAttachments[0].storeAction = MTLStoreActionStore;
          profile_pass(rp, "depth copy");
          id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp];
          if (copy) {
            [e setRenderPipelineState:copy];
            [e setFragmentTexture:src.depth atIndex:0];
            // The fetch constant's exp_adjust (2^n), applied where the
            // console's texture fetch applies it: the shadow map's depth is
            // compared with the receivers' own depth in that scale.
            float scale = 1.0f;
            for (const auto& tp : frame->textures) {
              if (tp->address == ev.dest_base && tp->exp_adjust) {
                scale = std::ldexp(1.0f, tp->exp_adjust);
                break;
              }
            }
            [e setFragmentBytes:&scale length:sizeof(scale) atIndex:0];
            [e setScissorRect:(MTLScissorRect){x0, y0, w, h}];
            [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
          }
          [e endEncoding];
        } else {
          id<MTLBlitCommandEncoder> blit = nil;
          if (!scaled_copy(src.color, dest, 0, x0, y0, x0, y0, w, h, ev, "resolve copy (exp bias)")) {
          blit = new_blit("blit: resolve copy");
          [blit copyFromTexture:src.color
                    sourceSlice:0
                    sourceLevel:0
                   sourceOrigin:MTLOriginMake(x0, y0, 0)
                     sourceSize:MTLSizeMake(w, h, 1)
                      toTexture:dest
               destinationSlice:0
               destinationLevel:0
              destinationOrigin:MTLOriginMake(x0, y0, 0)];
          }
          // Small 8-bit colour resolves also go to guest memory (WriteBack).
          // Up to nfsmw_native_writeback_kb: what the game reads on the CPU is
          // small (the scene's brightness for the exposure); the environment
          // cube's faces (256 KB each) and the bloom buffer were copied back
          // too, ~1.3 ms of CPU a frame, for nobody.
          const size_t writeback_bytes = size_t(ev.dest_pitch) * ev.dest_height * 4;
          if (ev.dest_format == 6 && dest.pixelFormat == MTLPixelFormatRGBA8Unorm && ev.dest_pitch) {
            static std::set<uint32_t> said;
            if (said.size() < 24 && said.insert(ev.dest_base).second) {
              REXLOG_INFO("[native] resolve {:08x} {}x{} ({} KiB): {} to guest memory", ev.dest_base, ev.dest_pitch,
                          ev.dest_height, writeback_bytes >> 10,
                          writeback_bytes <= size_t(REXCVAR_GET(nfsmw_native_writeback_kb)) * 1024 ? "written back"
                                                                                                  : "not written back");
            }
          }
          if (ev.dest_format == 6 && dest.pixelFormat == MTLPixelFormatRGBA8Unorm && ev.dest_pitch &&
              writeback_bytes <= size_t(REXCVAR_GET(nfsmw_native_writeback_kb)) * 1024 &&
              x0 + w <= Px(ev.dest_pitch, scale) && y0 + h <= Px(ev.dest_height, scale)) {
            const uint32_t row_bytes = uint32_t((w * 4 + 255) & ~NSUInteger(255));
            id<MTLBuffer> pixels = pooled_buffer(row_bytes * h, MTLResourceStorageModeShared);
            if (!blit) blit = new_blit("blit: write-back");
            [blit copyFromTexture:dest
                      sourceSlice:0
                      sourceLevel:0
                     sourceOrigin:MTLOriginMake(x0, y0, 0)
                       sourceSize:MTLSizeMake(w, h, 1)
                         toBuffer:pixels
                destinationOffset:0
           destinationBytesPerRow:row_bytes
         destinationBytesPerImage:row_bytes * h];
            // In guest pixels: the resolve's own rectangle (as far as was copied).
            const uint32_t gx0 = uint32_t(std::max(ev.x0, 0)), gy0 = uint32_t(std::max(ev.y0, 0));
            const uint32_t gw = std::min(uint32_t(std::max(ev.x1 - ev.x0, 0)), uint32_t(w / scale));
            const uint32_t gh = std::min(uint32_t(std::max(ev.y1 - ev.y0, 0)), uint32_t(h / scale));
            writebacks->push_back({pixels, row_bytes, uint32_t(w), uint32_t(h), ev.dest_base, ev.dest_pitch,
                                   gx0, gy0, gw, gh, scale, ev.swap, ev.dest_endian});
          }
          [blit endEncoding];  // nil when the scaled copy did it and nothing was written back: no-op
        }
        static_cast<MTLResourceID*>(texture_heap.contents)[next_heap] = dest.gpuResourceID;
        // A depth copy (R32Float) where the GPU cannot filter 32-bit floats
        // (A16, M1): sampled nearest, not linear (undefined there).
        if (dest.pixelFormat == MTLPixelFormatR32Float && !device.supports32BitFloatFiltering) {
          static_cast<MTLResourceID*>(sampler_heap.contents)[next_heap] =
              SamplerFor(device, false, 2, 2, false).gpuResourceID;
        }
        heap_object[next_heap] = dest;
        resolved[ev.dest_base] = next_heap++;
        resolved_texture[ev.dest_base] = dest;
        resolved_swap[ev.dest_base] = !ev.depth && ev.swap;
        resolved_scale[ev.dest_base] = scale;
        // The texture it replaces: back to the pool after this frame (which
        // may still sample it, from before this resolve).
        if (auto old = kept_resolves.find(ev.dest_base); old != kept_resolves.end() && old->second.texture != dest) {
          gpu_pool.Retire(old->second.texture, number);
        }
        kept_resolves[ev.dest_base] = {dest, !ev.depth && ev.swap, scale};
        // A face of a cube the frame samples: also copied into that cube.
        for (const CubeTarget& ct : cube_targets) {
          if (ev.dest_base < ct.base || (ev.dest_base - ct.base) % ct.face_stride != 0) continue;
          const uint32_t face = (ev.dest_base - ct.base) / ct.face_stride;
          if (face >= 6) continue;
          id<MTLTexture> cube = resolved_cubes[ct.base];
          if (cube && (cube.pixelFormat != dest.pixelFormat || cube.width != Px(ct.width, scale))) {
            cube = nil;  // the kept one no longer matches (another scale or format): a new one
          }
          if (!cube && next_cube < cube_capacity) {
            MTLTextureDescriptor* cd = [MTLTextureDescriptor textureCubeDescriptorWithPixelFormat:dest.pixelFormat
                                                                                           size:Px(ct.width, scale)
                                                                                      mipmapped:NO];
            cd.usage = MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView;
            cd.storageMode = MTLStorageModePrivate;
            cube = NewTexture(device, cd, "cd@10");
            residency::Add(cube);
            if (auto old = kept_cubes.find(ct.base); old != kept_cubes.end()) {
              // Frames in flight keep it alive (their command buffers retain it).
              residency::Remove(old->second);
            }
            kept_cubes[ct.base] = cube;
            resolved_cubes[ct.base] = cube;
            [assembled_cubes addObject:cube];
            static_cast<MTLResourceID*>(cube_heap.contents)[next_cube] = cube.gpuResourceID;
            resolved_cube_index[ct.base] = next_cube++;
          }
          if (cube && cube.pixelFormat == dest.pixelFormat) {
            resolved_cube_swap[ct.base] = kept_cube_swaps[ct.base] = ev.swap;
            id<MTLBlitCommandEncoder> blit = new_blit("blit: cube assembly");
            [blit copyFromTexture:dest
                      sourceSlice:0
                      sourceLevel:0
                     sourceOrigin:MTLOriginMake(x0, y0, 0)
                       sourceSize:MTLSizeMake(std::min<NSUInteger>(w, cube.width), std::min<NSUInteger>(h, cube.height), 1)
                        toTexture:cube
                 destinationSlice:face
                 destinationLevel:0
                destinationOrigin:MTLOriginMake(0, 0, 0)];
            [blit endEncoding];
          }
        }
        [resolved_textures addObject:dest];
        if (!ev.depth) {  // the frame's last colour resolve: what is displayed
          final_texture = dest;
          final_rect = CGRectMake(x0, y0, w, h);
          final_guest_width = std::max(ev.x1 - ev.x0, 0);
          final_guest_height = std::max(ev.y1 - ev.y0, 0);
        }
        resolve_names.push_back(fmt::format("resolve_{:02}_{}_{}x{}_to_{:08x}", resolves_done,
                                            ev.depth ? "depth" : "color", w, h, ev.dest_base));
        resolve_rects.push_back(CGRectMake(x0, y0, w, h));
        ++resolves_done;
      }
      if (ev.clear_color) {
        src.clear_color = true;
        const uint32_t c = ev.clear_color_value;  // A8R8G8B8
        src.clear_color_value = MTLClearColorMake(((c >> 16) & 0xFF) / 255.0, ((c >> 8) & 0xFF) / 255.0,
                                                  (c & 0xFF) / 255.0, (c >> 24) / 255.0);
      }
      if (ev.clear_depth) {
        src.clear_depth = true;
        src.clear_depth_value = double(ev.clear_depth_value >> 8) / double(0xFFFFFF);
      }
    };
    // The cost probe (nfsmw_native_cost_probe): this frame's left-out shader.
    uint64_t probe_ps = 0;
    size_t probe_draws = 0;
    if (!dump && REXCVAR_GET(nfsmw_native_cost_probe) && number % 60 == 30 && frame->draws.size() > 1000) {
      std::unordered_map<uint64_t, size_t> counts;
      for (const Draw& d : frame->draws) ++counts[d.ps_key];
      std::vector<std::pair<size_t, uint64_t>> top;
      for (const auto& [k, c] : counts) top.push_back({c, k});
      std::sort(top.rbegin(), top.rend());
      static size_t turn = 0;
      if (!top.empty()) {
        const auto& pick = top[turn++ % std::min<size_t>(top.size(), 16)];
        probe_ps = pick.second;
        probe_draws = pick.first;
      }
    }
    for (size_t di = 0; di < frame->draws.size(); ++di) {
      const Draw& d = frame->draws[di];
      while (next_resolve < frame->resolves.size() && frame->resolves[next_resolve].after_draws <= di) {
        if (di > 0) {
          do_resolve(frame->resolves[next_resolve], frame->draws[di - 1]);
        }
        ++next_resolve;
      }
      const std::string tk = target_key(d);
      if (dump) {
        // Snapshots: each pass's draws grouped (shaders, viewport, depth,
        // mask, clipping), with the first draw of each group.
        if (tk != group_target) {
          for (const auto& [g, c] : groups) diagnostics.push_back(fmt::format("group {}: {} x {}", group_target, c.second, g + fmt::format(" (first draw {})", c.first)));
          groups.clear();
          group_target = tk;
        }
        const std::string g = fmt::format("vs {:016x} ps {:016x} vp {:.0f}x{:.0f} at {:.0f},{:.0f} z {:.3f}+{:.3f} vte {:x} zc {:03x} mask {:x} clipoff {} prim {}",
                                          d.vs_key, d.ps_key, 2 * d.viewport[0], 2 * d.viewport[2], d.viewport[1] - d.viewport[0],
                                          d.viewport[3] - d.viewport[2], d.viewport[5], d.viewport[4], d.vte, d.depth_control & 0xFFF,
                                          d.color_mask & 0xF, d.clip_disable, uint32_t(d.primitive));
        auto& c = groups[g];
        if (!c.second) c.first = di;
        ++c.second;
        if (di + 1 == frame->draws.size()) {
          for (const auto& [gg, cc] : groups) diagnostics.push_back(fmt::format("group {}: {} x {}", group_target, cc.second, gg + fmt::format(" (first draw {})", cc.first)));
        }
      }
      if (dump && di + 40 >= frame->draws.size()) {  // the post-processing chain, in snapshots
        std::string tex;
        for (int s = 0; s < 16; ++s) {
          if (d.textures[s] < 0) continue;
          const Texture& ft = *frame->textures[d.textures[s]];
          tex += fmt::format(" t{}={:08x}:{}x{}", s, ft.address, ft.width, ft.height);
        }
        diagnostics.push_back(fmt::format("post draw {}: ps {:016x} vs {:016x} target {}{} blend {:08x} mask {:x}{}", di,
                                          d.ps_key, d.vs_key, tk,
                                          d.second_target ? "+" + EdramKey(d.surface_info, d.color1_info, d.depth_info) : "",
                                          d.blend_control, d.color_mask, tex));
      }
      Target& t = targets[tk];
      const std::string tk1 = d.second_target ? EdramKey(d.surface_info, d.color1_info, d.depth_info) : std::string();
      Target* t1 = d.second_target ? &targets[tk1] : nullptr;
      if (t1 && (!t1->color || t1->color.width != t.color.width || t1->color.height != t.color.height)) {
        t1 = nullptr;  // not the same size: drawn without it
      }
      const std::string pass_key = t1 ? tk + "+" + tk1 : tk;
      const bool split = pass_key == current && split_after && t.scale > 1.0f && pass_indices >= split_after;
      pass_splits += split;
      if (pass_key != current || split) {
        pass_indices = 0;
        if (dump) diagnostics.push_back(fmt::format("draw {}: target {}{}{} (z {:08x}, viewport {}x{} at {},{})", di, tk,
                                          !t.used ? " first use" : "", t.clear_color ? " clear-color" : "",
                                          d.depth_control, 2 * std::fabs(d.viewport[2] == 0 ? 0.f : d.viewport[0]),
                                          2 * std::fabs(d.viewport[2]), d.viewport[1], d.viewport[3]));
        [enc endEncoding];
        MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];
        const bool clear_color = !t.used || t.clear_color, clear_depth = !t.used || t.clear_depth;
        rp.colorAttachments[0].texture = t.multisample_color;
        rp.colorAttachments[0].loadAction = clear_color ? MTLLoadActionClear : MTLLoadActionLoad;
        rp.colorAttachments[0].clearColor = t.clear_color ? t.clear_color_value : MTLClearColorMake(0, 0, 0, 0);
        if (t.sample_count > 1) {
          rp.colorAttachments[0].resolveTexture = t.color;
          rp.colorAttachments[0].storeAction = MTLStoreActionStoreAndMultisampleResolve;
        } else {
          rp.colorAttachments[0].storeAction = MTLStoreActionStore;
        }
        if (t1) {
          const bool clear1 = !t1->used || t1->clear_color;
          rp.colorAttachments[1].texture = t1->multisample_color;
          rp.colorAttachments[1].loadAction = clear1 ? MTLLoadActionClear : MTLLoadActionLoad;
          rp.colorAttachments[1].clearColor = t1->clear_color ? t1->clear_color_value : MTLClearColorMake(0, 0, 0, 0);
          if (t1->sample_count > 1) {
            rp.colorAttachments[1].resolveTexture = t1->color;
            rp.colorAttachments[1].storeAction = MTLStoreActionStoreAndMultisampleResolve;
          } else {
            rp.colorAttachments[1].storeAction = MTLStoreActionStore;
          }
          t1->clear_color = false;
          if (!t1->used) order.push_back(tk1);
          t1->used = true;
        }
        rp.depthAttachment.texture = t.multisample_depth;
        rp.depthAttachment.loadAction = clear_depth ? MTLLoadActionClear : MTLLoadActionLoad;
        rp.depthAttachment.clearDepth = t.clear_depth ? t.clear_depth_value : 1.0;
        rp.visibilityResultBuffer = visibility;
        t.clear_color = t.clear_depth = false;
        if (t.sample_count > 1) {
          rp.depthAttachment.resolveTexture = t.depth;
          rp.depthAttachment.depthResolveFilter = MTLMultisampleDepthResolveFilterMin;
          rp.depthAttachment.storeAction = MTLStoreActionStoreAndMultisampleResolve;
        } else {
          rp.depthAttachment.storeAction = MTLStoreActionStore;
        }
        rp.stencilAttachment.texture = t.multisample_depth;
        rp.stencilAttachment.loadAction = clear_depth ? MTLLoadActionClear : MTLLoadActionLoad;
        if (t.sample_count > 1) {
          rp.stencilAttachment.resolveTexture = t.depth;
          rp.stencilAttachment.storeAction = MTLStoreActionStoreAndMultisampleResolve;
        } else {
          rp.stencilAttachment.storeAction = MTLStoreActionStore;
        }
        if (!t.used) {
          order.push_back(tk);
        }
        t.used = true;
        profile_pass(rp, fmt::format("pass {} from draw {} ({}x{})", pass_key, di, t.color.width, t.color.height));
        enc = [cb renderCommandEncoderWithDescriptor:rp];
        clip_mode_encoder = nil;  // a new encoder starts clipping
        clip_mode_clamp = false;
        // Everything the argument heaps point to, resident for this pass: one
        // call (it was one per texture, for each of the frame's passes).
        resident.clear();
        for (NSArray<id<MTLTexture>>* list in @[ textures, resolved_textures, assembled_cubes, volumes, cubes ]) {
          for (id<MTLTexture> tex in list) resident.push_back(tex);
        }
        resident.push_back(dummy_array);
        resident.push_back(data);
        [enc useResources:resident.data() count:resident.size()
                    usage:MTLResourceUsageRead
                   stages:MTLRenderStageVertex | MTLRenderStageFragment];
        id<MTLBuffer> heaps[4] = {texture_heap, array_heap, volume_heap, cube_heap};
        for (int i = 0; i < 4; ++i) {
          [enc setVertexBuffer:heaps[i] offset:0 atIndex:i];
          [enc setFragmentBuffer:heaps[i] offset:0 atIndex:i];
        }
        [enc setVertexBuffer:sampler_heap offset:0 atIndex:4];
        [enc setFragmentBuffer:sampler_heap offset:0 atIndex:4];
        current = pass_key;
      }
      pass_indices += d.index_count();
      if (probe_ps && d.ps_key == probe_ps) continue;  // the cost probe's left-out shader
      // State of the shaders that cost the most (cost probe, 2x race): every
      // 600 frames, per pixel shader, the alpha test, blend and depth state
      // its draws use, and their indices.
      if (!dump && REXCVAR_GET(nfsmw_native_cost_probe) && number % 600 == 300) {
        static std::map<std::string, std::pair<size_t, size_t>> states;  // -> (draws, indices)
        if (d.ps_key == 0x27d82ea0faa380a8ull || d.ps_key == 0xaf393d4c46af230cull ||
            d.ps_key == 0x684f4711f29b9f77ull || d.ps_key == 0x4fbaecfb8e7c4f40ull) {
          auto& e = states[fmt::format("ps {:016x} target {} alpha test {} (func {}, ref {:.3f}) blend {:08x} "
                                       "depth {:03x} mask {:x}",
                                       d.ps_key, tk, (d.color_control & 8) ? "on" : "off", d.color_control & 7,
                                       d.alpha_ref, d.blend_control, d.depth_control & 0xFFF, d.color_mask & 0xF)];
          ++e.first;
          e.second += d.index_count();
        }
        if (di + 1 == frame->draws.size()) {
          for (const auto& [k, e] : states) REXLOG_INFO("[cost-state] {}: {} draws, {} indices", k, e.first, e.second);
          states.clear();
        }
      }

      // Pipeline.
      // Alpha to coverage (bit 4) without multisampling: alpha at least 0.5
      // covers the pixel (an alpha test, threshold set where the constants
      // are written).
      const bool alpha_to_coverage = !(d.color_control & 8) && (d.color_control & 0x10);
      const uint32_t alpha_spec = (d.color_control & 8) ? (2u | ((d.color_control & 7) << 8))
                                  : alpha_to_coverage && t.sample_count == 1 ? (2u | (6u << 8))
                                                                            : 0u;
      const PipelineKey pk{d.vs_key, d.ps_key, d.blend_control, t1 ? d.blend_control1 : 0u,
                           t1 ? (d.color_mask & 0xFF) : (d.color_mask & 0xF), t.format,
                           t1 ? t1->format + 1 : 0u, alpha_spec, t.sample_count,
                           alpha_to_coverage && t.sample_count > 1};
      bool pipeline_failed = false;
      id<MTLRenderPipelineState> pso = pipeline_cache.Get(device, pk, d.vs, d.ps, async_pipelines, &pipeline_failed);
      if (!pso) {
        pipeline_failures += pipeline_failed;
        continue;  // failed, or compiling in the background (left out until ready)
      }
      state.For(enc);
      if (state.pso != pso) {
        [enc setRenderPipelineState:pso];
        state.pso = pso;
      }
      // Depth clamped where the game turns clipping off (as the emulated
      // renderer does with depthClamp); per encoder, so set on each new one.
      if (enc != clip_mode_encoder || d.clip_disable != clip_mode_clamp) {
        [enc setDepthClipMode:d.clip_disable ? MTLDepthClipModeClamp : MTLDepthClipModeClip];
        clip_mode_encoder = enc;
        clip_mode_clamp = d.clip_disable;
      }
      // Occlusion query: counted while its draws run (a new encoder starts
      // with counting off, and with new slots).
      if (visibility) {
        if (enc != visibility_encoder) {
          visibility_encoder = enc;
          visibility_slot = -1;
          std::fill(pass_slot.begin(), pass_slot.end(), -1);
        }
        int want = -1;
        if (d.query >= 0) {
          int& slot = pass_slot[d.query];
          if (slot < 0 && visibility_slots.size() < kVisibilitySlots) {
            slot = int(visibility_slots.size());
            visibility_slots.push_back({d.query, double(t.scale) * t.scale * std::max<uint32_t>(t.sample_count, 1)});
          }
          want = slot;
        }
        if (want != visibility_slot) {
          [enc setVisibilityResultMode:want >= 0 ? MTLVisibilityResultModeCounting : MTLVisibilityResultModeDisabled
                                offset:want >= 0 ? NSUInteger(want) * 8 : 0];
          visibility_slot = want;
        }
      }

      // Depth: RB_DEPTHCONTROL z enable (bit 1), write (2), function (4-6).
      const uint32_t dc = d.depth_control & 0x76;
      id<MTLDepthStencilState> ds = depth_states[dc];
      if (!ds) {
        MTLDepthStencilDescriptor* dsd = [MTLDepthStencilDescriptor new];
        if (dc & 2) {
          static const MTLCompareFunction kFuncs[] = {
              MTLCompareFunctionNever,   MTLCompareFunctionLess,     MTLCompareFunctionEqual,
              MTLCompareFunctionLessEqual, MTLCompareFunctionGreater, MTLCompareFunctionNotEqual,
              MTLCompareFunctionGreaterEqual, MTLCompareFunctionAlways};
          dsd.depthCompareFunction = kFuncs[(dc >> 4) & 7];
          dsd.depthWriteEnabled = (dc & 4) != 0;
        }
        ds = depth_states[dc] = [device newDepthStencilStateWithDescriptor:dsd];
      }
      if (state.ds != ds) {
        [enc setDepthStencilState:ds];
        state.ds = ds;
      }
      // (Culling is off by default on a new encoder.)

      // Viewport: Xenos window = ndc * scale + offset (each enabled by
      // PA_CL_VTE_CNTL), plus the window offset.
      const float sx = ((d.vte & 1) ? d.viewport[0] : 1.0f) * t.scale;
      const float ox = ((d.vte & 2) ? d.viewport[1] : 0.0f) * t.scale;
      const float sy = ((d.vte & 4) ? d.viewport[2] : 1.0f) * t.scale;
      const float oy = ((d.vte & 8) ? d.viewport[3] : 0.0f) * t.scale;
      const float sz = (d.vte & 16) ? d.viewport[4] : 1.0f, oz = (d.vte & 32) ? d.viewport[5] : 0.0f;
      // The window offset and window scissor belong to the console's tiled
      // rendering (BeginTiling/EndTiling set them per tile when the tiles are
      // replayed, not in the draws' own packets): a whole pass is drawn here
      // at once, so neither applies.
      const float wx = 0.0f, wy = 0.0f;
      // Positions in pixels (VTE x scale off, as D3D's blits): Metal clips
      // before the viewport, so D3D's own vertex shaders (written here) turn
      // them into clip space themselves; the viewport is then the target.
      const bool internal = store.internal_keys.count(d.vs_key) != 0;
      const bool pixels = !(d.vte & 1);
      if (internal) {
        // The positions are guest pixels: the target is t.scale times larger.
        float xf[4] = {pixels ? 2.0f * t.scale / float(t.pitch) : 1.0f,
                       pixels ? -2.0f * t.scale / float(t.height) : 1.0f,
                       pixels ? -1.0f : 0.0f, pixels ? 1.0f : 0.0f};
        // The movies keep their 16:9 on a wider screen (pillarboxed): the
        // picture's clip-space x narrowed about the centre.
        if (d.ps_key == 0x2d2462de73d283deull && REXCVAR_GET(nfsmw_native_movie_16_9) && t.pitch && t.height) {
          const float aspect = float(t.color.width) / float(t.color.height);
          if (aspect > 16.0f / 9.0f + 0.01f) {
            const float f = (16.0f / 9.0f) / aspect;
            xf[0] *= f;
            xf[2] *= f;
          }
        }
        [enc setVertexBytes:xf length:sizeof(xf) atIndex:30];
      }
      if (pixels && !internal) {
        ++screen_space_game_draws;
      }
      // The rear-view mirror's picture (8436534c: the environment cube seen
      // backwards, RVMWorldBrightness): its quad has screen positions of its
      // own, not through the HUD's matrix, which game_scene_size.cpp scales
      // (title-safe area removed at 4:3, wider than 16:9). Scaled as much,
      // about the middle of the screen (the viewport's centre), to stay in
      // its frame.
      const bool mirror = d.ps_key == 0x8436534cfafcc0ebull;
      if (mirror) {
        static bool said = false;
        if (!said) {
          said = true;
          REXLOG_INFO("[native] mirror picture: scaled {:.3f} x {:.3f} ({})", nfsmw_mirror_scale_x,
                      nfsmw_mirror_scale_y, pixels ? "positions in pixels: not scaled" : "by its viewport");
        }
      }
      MTLViewport vp;
      if (pixels) {
        vp = {0, 0, double(t.pitch), double(t.height), (d.vte & 32) ? double(d.viewport[5]) : 0.0, 1.0};
        if (!state.viewport_set || std::memcmp(&vp, &state.viewport, sizeof(vp)) != 0) {
          [enc setViewport:vp];
          state.viewport = vp;
          state.viewport_set = true;
        }
      } else {
      const float mx = mirror ? nfsmw_mirror_scale_x : 1.0f, my = mirror ? nfsmw_mirror_scale_y : 1.0f;
      vp.originX = ox - std::fabs(sx) * mx + wx;
      vp.width = 2 * std::fabs(sx) * mx;
      vp.originY = oy - std::fabs(sy) * my + wy;
      vp.height = 2 * std::fabs(sy) * my;
      vp.znear = oz;
      vp.zfar = oz + sz;
      if (!(vp.width >= 1 && vp.height >= 1)) {
        continue;
      }
      if (!state.viewport_set || std::memcmp(&vp, &state.viewport, sizeof(vp)) != 0) {
        [enc setViewport:vp];
        state.viewport = vp;
        state.viewport_set = true;
      }
      }
      MTLScissorRect sc;
      if (true) {
        sc = {0, 0, t.pitch, t.height};
      } else {
      sc.x = std::min<NSUInteger>(d.scissor[0], t.pitch - 1);
      sc.y = std::min<NSUInteger>(d.scissor[1], t.height - 1);
      sc.width = std::min<NSUInteger>(std::max<int>(int(d.scissor[2]) - int(sc.x), 1), t.pitch - sc.x);
      sc.height = std::min<NSUInteger>(std::max<int>(int(d.scissor[3]) - int(sc.y), 1), t.height - sc.y);
      }
      if (!state.scissor_set || std::memcmp(&sc, &state.scissor, sizeof(sc)) != 0) {
        [enc setScissorRect:sc];
        state.scissor = sc;
        state.scissor_set = true;
      }

      // Constants and shared constants (texture/sampler indices, booleans).
      // Uploaded once per distinct set (consecutive draws share them).
      // The stage's constant address is where register 0 would be: the
      // upload starts at the range's first register.
      auto upload = [&](UploadedConstants& u, const ConstantBank& set, std::pair<uint16_t, uint16_t> r) {
        if (!u.Covers(&set, r)) {
          u = {&set, r, put(set.data() + size_t(r.first) * 4, size_t(r.second - r.first) * 16)};
        }
        return data.gpuAddress + u.at - size_t(u.range.first) * 16;
      };
      const uint64_t vs_address = upload(uploaded_vs, *d.vs_constants, d.vs_range);
      const uint64_t ps_address = upload(uploaded_ps, *d.ps_constants, d.ps_range);
      uint32_t shared[256] = {};
      for (int s = 0; s < 16; ++s) {
        int index = d.textures[s] < 0 ? 0 : d.textures[s] + 1;
        if (d.textures[s] >= 0) {
          // Resolved earlier in this frame: our texture, not guest memory.
          const Texture& ft = *frame->textures[d.textures[s]];
          auto it = resolved.find(ft.address);
          if (it != resolved.end()) {
            index = int(it->second);
            // The console reads the resolve back from memory: in memory X
            // and Z are swapped if the resolve swapped; then the fetch
            // swizzle picks channels. A view with both, unless both are the
            // identity.
            const bool swap = resolved_swap[ft.address];
            const uint32_t sw = ft.fetch_swizzle;
            id<MTLTexture> base = resolved_texture[ft.address];
            // Sampled at its own size, smaller than the resolve's pitch (a
            // 960-texel-wide scene in a 1024 pitch): coordinates are
            // normalized by that size, so a texture of that size over the
            // same memory (resolve textures are linear, in a buffer). The
            // fetch size is in guest texels: times the resolve's scale.
            const auto scale_it = resolved_scale.find(ft.address);
            const float fs = scale_it != resolved_scale.end() ? scale_it->second : 1.0f;
            const uint32_t fw = Px(ft.width, fs), fh = Px(ft.height, fs);
            const bool crop = base.buffer && fw && fh && (fw < base.width || fh < base.height) && fw <= base.width &&
                              fh <= base.height;
            if (sw != 0x688 || swap || crop) {
              const auto view_key = std::make_tuple(uintptr_t((__bridge void*)base), sw | (swap ? 0x1000u : 0u),
                                                    crop ? fw : 0u, crop ? fh : 0u);
              auto view = resolved_views.find(view_key);
              if (view != resolved_views.end()) {
                index = int(view->second);
              } else if (next_heap < heap_capacity) {
                auto channel = [&](uint32_t sel) {
                  switch (sel & 7) {
                    case 0: return swap ? MTLTextureSwizzleBlue : MTLTextureSwizzleRed;
                    case 1: return MTLTextureSwizzleGreen;
                    case 2: return swap ? MTLTextureSwizzleRed : MTLTextureSwizzleBlue;
                    case 3: return MTLTextureSwizzleAlpha;
                    case 4: return MTLTextureSwizzleZero;
                    default: return MTLTextureSwizzleOne;
                  }
                };
                id<MTLTexture> source = base;
                if (crop) {
                  MTLTextureDescriptor* cd = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:base.pixelFormat
                                                                                                width:fw
                                                                                               height:fh
                                                                                            mipmapped:NO];
                  cd.usage = MTLTextureUsageShaderRead | MTLTextureUsagePixelFormatView;
                  cd.storageMode = base.buffer.storageMode;
                  source = [base.buffer newTextureWithDescriptor:cd
                                                          offset:base.bufferOffset
                                                     bytesPerRow:base.bufferBytesPerRow];
                  [enc useResource:base.buffer usage:MTLResourceUsageRead
                            stages:MTLRenderStageVertex | MTLRenderStageFragment];
                }
                id<MTLTexture> v = [source newTextureViewWithPixelFormat:source.pixelFormat
                                                           textureType:base.textureType
                                                                levels:NSMakeRange(0, 1)
                                                                slices:NSMakeRange(0, 1)
                                                               swizzle:MTLTextureSwizzleChannelsMake(
                                                                           channel(sw), channel(sw >> 3),
                                                                           channel(sw >> 6), channel(sw >> 9))];
                if (v) {
                  static_cast<MTLResourceID*>(texture_heap.contents)[next_heap] = v.gpuResourceID;
                  heap_object[next_heap] = v;
                  [resolved_textures addObject:v];
                  resolve_names.push_back("view");
                  resolve_rects.push_back(CGRectZero);
                  [enc useResource:v usage:MTLResourceUsageRead stages:MTLRenderStageVertex | MTLRenderStageFragment];
                  if (source != base) {  // the crop: named too (the snapshot pairs names and textures by position)
                    [enc useResource:source usage:MTLResourceUsageRead stages:MTLRenderStageVertex | MTLRenderStageFragment];
                    [resolved_textures addObject:source];
                    resolve_names.push_back("crop");
                    resolve_rects.push_back(CGRectZero);
                  }
                  resolved_views[view_key] = next_heap;
                  index = int(next_heap++);
                }
              }
            }
          }
        }
        shared[s] = uint32_t(index);        // Texture2D index
        shared[64 + s] = uint32_t(index);   // sampler index
        if (d.textures[s] >= 0) {
          shared[48 + s] = cube_index[d.textures[s]];    // TextureCube index (byte 192)
          auto rc = resolved_cube_index.find(frame->textures[d.textures[s]]->address);
          if (rc != resolved_cube_index.end()) {
            shared[48 + s] = rc->second;  // a cube resolved earlier in this frame
            // Sampled as the console does: the faces' red/blue swap in memory,
            // then the fetch swizzle (as for 2D resolves above).
            const Texture& ft = *frame->textures[d.textures[s]];
            const bool swap = resolved_cube_swap[ft.address];
            const uint32_t sw = ft.fetch_swizzle;
            id<MTLTexture> base = resolved_cubes[ft.address];
            if (base && (sw != 0x688 || swap) && REXCVAR_GET(nfsmw_native_cube_swizzle)) {
              const auto view_key = std::make_pair(uintptr_t((__bridge void*)base), sw | (swap ? 0x1000u : 0u));
              auto view = cube_views.find(view_key);
              if (view != cube_views.end()) {
                shared[48 + s] = view->second;
              } else if (next_cube < cube_heap.length / sizeof(MTLResourceID)) {
                auto channel = [&](uint32_t sel) {
                  switch (sel & 7) {
                    case 0: return swap ? MTLTextureSwizzleBlue : MTLTextureSwizzleRed;
                    case 1: return MTLTextureSwizzleGreen;
                    case 2: return swap ? MTLTextureSwizzleRed : MTLTextureSwizzleBlue;
                    case 3: return MTLTextureSwizzleAlpha;
                    case 4: return MTLTextureSwizzleZero;
                    default: return MTLTextureSwizzleOne;
                  }
                };
                id<MTLTexture> v = [base newTextureViewWithPixelFormat:base.pixelFormat
                                                           textureType:MTLTextureTypeCube
                                                                levels:NSMakeRange(0, 1)
                                                                slices:NSMakeRange(0, 6)
                                                               swizzle:MTLTextureSwizzleChannelsMake(
                                                                           channel(sw), channel(sw >> 3),
                                                                           channel(sw >> 6), channel(sw >> 9))];
                if (v) {
                  static_cast<MTLResourceID*>(cube_heap.contents)[next_cube] = v.gpuResourceID;
                  [assembled_cubes addObject:v];
                  [enc useResource:v usage:MTLResourceUsageRead stages:MTLRenderStageVertex | MTLRenderStageFragment];
                  cube_views[view_key] = next_cube;
                  shared[48 + s] = next_cube++;
                }
              }
            }
          }
          shared[32 + s] = volume_index[d.textures[s]];  // Texture3D index (byte 128)
          // Tuning shop colour test: the car paint shaders' textures, logged
          // once each; the cube or the 3D texture left out on request.
          if (d.ps_key == 0x2442daf2d3a7097aull || d.ps_key == 0xd1f317fad0f46ac6ull) {
            const Texture& ft = *frame->textures[d.textures[s]];
            static std::set<std::tuple<uint64_t, int, uint32_t>> said;
            // 2D textures: the first 64; cubes and 3D textures: all (few).
            if ((said.size() < 64 || ft.cube || ft.volume) && said.insert({d.ps_key, s, ft.address}).second) {
              REXLOG_INFO("[car-paint] ps {:016x} slot {}: {:08x} {}x{}x{} guest format {}{} metal format {} {}{} "
                          "fetch swizzle {:03x} exp_adjust {} endian {} tiled {}",
                          d.ps_key, s, ft.address, ft.width, ft.height, ft.depth, ft.guest_format,
                          ft.guest_signed ? " signed" : "", int(ft.format),
                          ft.cube ? "cube" : ft.volume ? "3D" : "2D",
                          resolved_cube_index.count(ft.address) ? " (made from resolves)"
                          : ft.format == MTLPixelFormatInvalid ? " (a resolve)" : "",
                          ft.fetch_swizzle, ft.exp_adjust, ft.guest_endian, ft.guest_tiled);
            }
            // Snapshots: which cube the paint reads (decoded from memory or
            // made from resolves), and its six faces saved once per frame.
            if (dump && ft.cube) {
              const bool from_resolves = resolved_cubes.count(ft.address) && resolved_cubes[ft.address];
              id<MTLTexture> bound = from_resolves ? resolved_cubes[ft.address]
                                     : cube_index[d.textures[s]] < cubes.count ? cubes[cube_index[d.textures[s]]] : nil;
              const std::string line = fmt::format("group car cube: ps {:016x} slot {} cube {:08x} {}", d.ps_key, s,
                                                   ft.address, from_resolves ? "made from resolves" : "decoded from memory");
              static std::set<std::string> seen_this_frame;
              static uint32_t seen_frame = 0;
              if (seen_frame != number) {
                seen_this_frame.clear();
                seen_frame = number;
              }
              if (bound && seen_this_frame.insert(line).second) {
                diagnostics.push_back(line);
                for (NSUInteger face = 0; face < 6; ++face) {
                  id<MTLTexture> v = [bound newTextureViewWithPixelFormat:bound.pixelFormat
                                                              textureType:MTLTextureType2D
                                                                   levels:NSMakeRange(0, 1)
                                                                   slices:NSMakeRange(face, 1)];
                  if (v) {
                    watch_saves.push_back({v, fmt::format("car_cube_{:08x}_{}_face{}", ft.address,
                                                          from_resolves ? "resolved" : "decoded", face)});
                  }
                }
              }
            }
            if (ft.cube && REXCVAR_GET(nfsmw_native_test_no_envcube)) shared[48 + s] = 0;
            if (ft.volume && REXCVAR_GET(nfsmw_native_test_grey_volume)) shared[32 + s] = grey_volume_index;
          }
        }
      }
      // Plus, for the car shaders, every draw whose first texture is 1024
      // wide or more (the car's skin, with its livery).
      const bool skin = d.textures[0] >= 0 && frame->textures[d.textures[0]]->width >= 1024 &&
                        d.ps_key != 0xaf393d4c46af230cull && watched_seen[d.ps_key ^ 1]++ < 4;
      // Snapshots: the shadow receivers' shadow constants (pixel c0-c8: the
      // "enabled" switch and bias; vertex c17, c19, c40: the shadow map
      // matrix's first row, depending on the shader).
      if (dump && (d.ps_key == 0x684f4711f29b9f77ull || d.ps_key == 0xaf393d4c46af230cull ||
                   d.ps_key == 0xd1f317fad0f46ac6ull) &&
          watched_seen[d.ps_key ^ 0x5A5A]++ < 2) {
        auto c = [](const ConstantBank& k, int r) {
          float f[4];
          std::memcpy(f, &k[r * 4], 16);
          return fmt::format("({:.3g} {:.3g} {:.3g} {:.3g})", f[0], f[1], f[2], f[3]);
        };
        std::string ps_c, vs_c;
        for (int r = 0; r <= 8; ++r) ps_c += fmt::format(" c{}{}", r, c(*d.ps_constants, r));
        for (int r : {17, 19, 40}) vs_c += fmt::format(" c{}{}", r, c(*d.vs_constants, r));
        diagnostics.push_back(fmt::format("group consts draw {} ps {:016x} vs {:016x}: PS{} | VS{}", &d - frame->draws.data(),
                                          d.ps_key, d.vs_key, ps_c, vs_c));
      }
      // Snapshots: the hand-written matrix shader's draws (car shadow casters?):
      // their matrix, first vertex and where it lands in clip space.
      if (dump && d.vs_key == 0x2f583d7c8ddf572aull && watched_seen[0x2f583d7c]++ < 2) {
        const auto& k = *d.vs_constants;
        float m[16];
        std::memcpy(m, k.data(), 64);
        float p[4] = {0, 0, 0, 1};
        for (const Attribute& a : d.attributes) {
          if (a.location == 0 && a.values && a.values->size() >= 4) {
            std::memcpy(p, a.values->data(), 12);
            p[3] = 1.0f;
          }
        }
        float o[4];
        for (int r = 0; r < 4; ++r) o[r] = m[r * 4] * p[0] + m[r * 4 + 1] * p[1] + m[r * 4 + 2] * p[2] + m[r * 4 + 3] * p[3];
        diagnostics.push_back(fmt::format(
            "group matrix draw {}: c0 ({:.3g} {:.3g} {:.3g} {:.3g}) c1 ({:.3g} {:.3g} {:.3g} {:.3g}) c2 ({:.3g} {:.3g} {:.3g} {:.3g}) "
            "c3 ({:.3g} {:.3g} {:.3g} {:.3g}) | vertex 0 ({:.4g} {:.4g} {:.4g}) of {} -> clip ({:.4g} {:.4g} {:.4g} {:.4g}) "
            "ndc ({:.3g} {:.3g} {:.3g}) | {} attributes, prim {}, {} indices | PS c0 {:.3g} c1 {:.3g} cc {:08x} t0 {}",
            &d - frame->draws.data(), m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], m[9], m[10], m[11], m[12], m[13],
            m[14], m[15], p[0], p[1], p[2], d.vertex_count, o[0], o[1], o[2], o[3], o[0] / o[3], o[1] / o[3], o[2] / o[3],
            d.attributes.size(), uint32_t(d.primitive), d.index_count(), [&] { float f; std::memcpy(&f, &(*d.ps_constants)[0], 4); return f; }(),
            [&] { float f; std::memcpy(&f, &(*d.ps_constants)[4], 4); return f; }(), d.color_control,
            d.textures[0] < 0 ? std::string("none")
                              : fmt::format("{:08x} {}x{} format {}", frame->textures[d.textures[0]]->address,
                                            frame->textures[d.textures[0]]->width, frame->textures[d.textures[0]]->height,
                                            int(frame->textures[d.textures[0]]->format))));
      }
      if (dump && watched.count(d.ps_key) && (watched_seen[d.ps_key]++ < 3 || skin)) {
        for (int s = 0; s < (skin ? 1 : 16); ++s) {
          const uint32_t index = shared[s];
          if (d.textures[s] < 0 || index >= heap_object.size() || !heap_object[index]) continue;
          const Texture& ft = *frame->textures[d.textures[s]];
          // The saved image is the texture's memory as Metal holds it (a
          // view's swizzle is not applied): the name gives the fetch swizzle
          // and whether the resolve swapped red and blue.
          watch_saves.push_back({heap_object[index],
                                 fmt::format("watch_ps{:016x}_d{}_t{}_{:08x}_{}x{}_sw{:03x}{}{}", d.ps_key,
                                             &d - frame->draws.data(), s, ft.address, ft.width, ft.height,
                                             ft.fetch_swizzle, resolved_swap[ft.address] ? "_swap" : "",
                                             ft.persistent ? "_kept" : ft.format == MTLPixelFormatInvalid ? "_resolved" : "")});
        }
      }
      shared[80] = d.booleans;  // g_Booleans at byte 320
      {
        const float threshold = (!(d.color_control & 8) && (d.color_control & 0x10)) ? 0.5f : d.alpha_ref;
        std::memcpy(&shared[93], &threshold, 4);  // g_AlphaThreshold at byte 372
      }
      // The same as the draw before's (most are): its copy again.
      if (!have_last_shared || std::memcmp(last_shared, shared, sizeof(shared)) != 0) {
        last_shared_at = put(shared, sizeof(shared));
        std::memcpy(last_shared, shared, sizeof(shared));
        have_last_shared = true;
      }
      const size_t shared_at = last_shared_at;
      struct {
        uint64_t vs, ps, shared;
      } push = {vs_address, ps_address, data.gpuAddress + shared_at};
      if (!state.push_set || std::memcmp(&push, state.push, sizeof(push)) != 0) {
        [enc setVertexBytes:&push length:sizeof(push) atIndex:8];
        [enc setFragmentBytes:&push length:sizeof(push) atIndex:8];
        std::memcpy(state.push, &push, sizeof(push));
        state.push_set = true;
      }

      // Vertex attributes: the shader's active inputs, in order, in buffers
      // 9 onwards; an input the draw did not provide reads zeros.
      const std::vector<NSUInteger>& active = ActiveAttributes(d.vs);
      for (size_t k = 0; k < active.size() && 9 + k <= 30; ++k) {
        const Attribute* found = nullptr;
        for (const Attribute& a : d.attributes) {
          if (a.location == active[k]) found = &a;
        }
        if (found && found->values && !found->values->empty() && found->fresh) {
          // Changed this frame: with the frame's data, no buffer of its own.
          state.VertexBuffer(data, put(found->values->data(), found->values->size() * 4), 9 + k);
        } else if (found && found->values && !found->values->empty()) {
          size_t vb_offset = 0;
          id<MTLBuffer> vb = GpuBufferFor(device, found->values, vb_offset);
          state.VertexBuffer(vb ?: zeros, vb_offset, 9 + k);  // bound: resident without useResource
        } else {
          state.VertexBuffer(zeros, 0, 9 + k);
        }
      }
      if (d.index_count()) {
        // Made this frame: with the frame's data; cached: its own buffer.
        size_t index_at = 0;
        id<MTLBuffer> ib = data;
        if (d.indices_fresh) {
          index_at = put(d.indices->data(), d.index_count() * 4);
        } else if (!(ib = GpuBufferFor(device, d.indices, index_at))) {
          continue;
        }
        [enc drawIndexedPrimitives:d.primitive
                        indexCount:d.index_count()
                         indexType:MTLIndexTypeUInt32
                       indexBuffer:ib
                 indexBufferOffset:index_at];
        ++drawn;
      }
    }
    // Resolves after the last draw (the frame's last: what is displayed).
    while (next_resolve < frame->resolves.size()) {
      if (!frame->draws.empty()) {
        do_resolve(frame->resolves[next_resolve], frame->draws.back());
      }
      ++next_resolve;
    }
    [enc endEncoding];

    // On screen: the frame's last colour resolve, fitted to the layer.
    CAMetalLayer* layer = present_layer;
    id<MTLRenderPipelineState> present_pso = present ? PresentPipeline(device) : nil;
    if (present && layer && final_texture && present_pso) {
      const auto drawable_start = std::chrono::steady_clock::now();
      id<CAMetalDrawable> drawable = [layer nextDrawable];
      drawable_wait_ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - drawable_start).count();
      if (drawable) {
        MTLRenderPassDescriptor* rp = [MTLRenderPassDescriptor renderPassDescriptor];
        rp.colorAttachments[0].texture = drawable.texture;
        rp.colorAttachments[0].loadAction = MTLLoadActionClear;
        rp.colorAttachments[0].clearColor = MTLClearColorMake(0, 0, 0, 1);
        rp.colorAttachments[0].storeAction = MTLStoreActionStore;
        id<MTLRenderCommandEncoder> e = [cb renderCommandEncoderWithDescriptor:rp];
        // "native" scale: the displayed image as large as it is shown (it fits
        // the drawable by its height, or by its width when relatively wider).
        if (final_guest_width >= 320 && final_guest_height >= 240) {
          const float want = std::min(float(drawable.texture.width) / float(final_guest_width),
                                      float(drawable.texture.height) / float(final_guest_height));
          const float rounded = std::round(want * 1000.0f) / 1000.0f;
          if (std::fabs(native_screen_scale.load() - rounded) > 0.0005f) {
            native_screen_scale = rounded;
            if (REXCVAR_GET(nfsmw_native_resolution_scale) == "native") {
              REXLOG_INFO("[native] native resolution: {}x{} shown in {}x{}: scale {:.3f}", final_guest_width,
                          final_guest_height, drawable.texture.width, drawable.texture.height, rounded);
            }
          }
        }
        const float sw = float(final_rect.size.width), sh = float(final_rect.size.height);
        const float dw = float(drawable.texture.width), dh = float(drawable.texture.height);
        const float src = sw / sh, dst = dw / dh;
        const float fit[4] = {src > dst ? 1.0f : src / dst, src > dst ? dst / src : 1.0f, 0, 0};
        // The resolve's rectangle within its texture (it starts at 0, 0).
        const float crop[4] = {sw / float(final_texture.width), sh / float(final_texture.height), 0, 0};
        // Only the picture's rectangle: the one triangle covering it reaches
        // past its right and top edges (to 3x), where the sampler's clamp
        // smeared the picture's edge over the black bar (the 4:3 picture on an
        // 11" iPad: black on the left, the edge stretched on the right).
        {
          const double pw = std::round(dw * fit[0]), ph = std::round(dh * fit[1]);
          const NSUInteger px = NSUInteger(std::max(0.0, std::floor((dw - pw) * 0.5)));
          const NSUInteger py = NSUInteger(std::max(0.0, std::floor((dh - ph) * 0.5)));
          [e setScissorRect:(MTLScissorRect){px, py,
                                             std::min<NSUInteger>(NSUInteger(pw), drawable.texture.width - px),
                                             std::min<NSUInteger>(NSUInteger(ph), drawable.texture.height - py)}];
        }
        [e setRenderPipelineState:present_pso];
        [e setVertexBytes:fit length:sizeof(fit) atIndex:0];
        [e setFragmentBytes:crop length:sizeof(crop) atIndex:0];
        [e setFragmentTexture:final_texture atIndex:0];
        [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:3];
        [e endEncoding];
        // What the screen shows: a gap between two frames on it (a stutter
        // the player sees, whatever its cause), logged with the frame's number.
        // Frame pacing: below the display's rate (the 30, 40 and 60 caps on a
        // 120 Hz screen, 30 on 60 Hz) each frame is presented at a target time
        // one cap interval after the one before it: shown as soon as ready, a
        // frame a hair late stayed one refresh more and the next one less
        // (microstutter at 30). The grid is in step with the screen's own
        // refreshes: it starts from the last time a frame was really shown
        // (a grid of our own fell between refreshes and the screen rounded
        // either way), and each target is 2 ms early so that it rounds to its
        // refresh. (presentDrawable:afterMinimumDuration: added a refresh to
        // every frame: 30 became 26.7.)
        const int32_t cap = rex::cvar::Query<int32_t>("ios_fps_cap");
        const double interval = cap > 0 ? 1.0 / double(cap) : 0.0;
        const double display_hz = double(UIScreen.mainScreen.maximumFramesPerSecond);
        static std::atomic<double> shown_at{0};  // the last frame really shown (presentedTime)
        const bool paced = REXCVAR_GET(nfsmw_native_present_at_time) && interval > 0 && shown_at.load() > 0 &&
                           double(cap) < display_hz - 1.0;
        [drawable addPresentedHandler:^(id<MTLDrawable> shown) {
          static std::atomic<double> last_shown{0};
          static std::atomic<int> gap_lines{200};
          const double at = shown.presentedTime;
          if (at <= 0) return;  // dropped, not shown
          const double before = last_shown.exchange(at);
          shown_at = at;
          const double gap_ms = (at - before) * 1000.0;
          if (before > 0 && gap_ms > 50.0 && gap_lines.fetch_sub(1) > 0) {
            REXLOG_INFO("[native] screen gap: {:.0f} ms before frame {} was shown", gap_ms, number);
          }
          // Pacing: frames shown off the cap's grid (more than 4 ms from one
          // interval after the one before), every 300 shown frames.
          static std::atomic<uint32_t> shown_count{0}, off_grid{0};
          static std::atomic<double> worst_ms{0};
          if (before > 0 && interval > 0 && gap_ms < 200.0) {
            const double off = std::fabs(gap_ms - interval * 1000.0);
            if (off > 4.0) ++off_grid;
            double w = worst_ms.load();
            while (off > w && !worst_ms.compare_exchange_weak(w, off)) {}
          }
          if (++shown_count % 300 == 0) {
            REXLOG_INFO("[native] pacing: {} of 300 frames off the {:.1f} ms grid (worst {:.1f} ms off){}",
                        off_grid.exchange(0), interval * 1000.0, worst_ms.exchange(0.0),
                        paced ? ", paced" : "");
          }
        }];
        static double last_target = 0;
        if (paced) {
          // The first refresh of the grid from now on, and never the same
          // refresh as the frame before (which may not be shown yet).
          const double now = CACurrentMediaTime(), base = shown_at.load();
          double target = base + std::ceil((now - base) / interval) * interval;
          if (last_target + interval > target && last_target + interval < now + 2.0 * interval) {
            target = last_target + interval;
          }
          last_target = target;
          [cb presentDrawable:drawable atTime:target - 0.002];
        } else {
          [cb presentDrawable:drawable];
        }
        ++presented;
      }
    }
    // Without PNGs nothing waits for the GPU: the next frame is encoded while
    // this one runs (in_flight counts them; the game thread records the next
    // frame meanwhile).
    if (!dump) {
      // The frame's textures stay alive until the GPU is done with them:
      // the argument buffers do not retain them, and the cache may release
      // a texture (with its Metal copy) while the frame is still running.
      NSArray* in_use = @[ textures, cubes, volumes ];
      const uint32_t uploads = frame_uploads, new_buffers = frame_new_buffers;
      const size_t probe_frame_draws = frame->draws.size();
      const size_t drawn_count = drawn;
      [cb addCompletedHandler:^(id<MTLCommandBuffer> done) {
        (void)in_use;
        if (done.error) {
          REXLOG_WARN("[native] GPU error: {}", done.error.localizedDescription.UTF8String);
        } else {
          ApplyWriteBacks(*writebacks);
          const double gpu_ms = std::max(0.0, done.GPUEndTime - done.GPUStartTime) * 1000.0;
          gpu_us += uint64_t(gpu_ms * 1000.0);
          {  // the cost probe: this frame against the average of the 8 before
            static std::mutex m;
            static double recent[8] = {};
            static int count = 0;
            std::lock_guard<std::mutex> lock(m);
            if (probe_ps && count >= 8) {
              double avg = 0;
              for (double v : recent) avg += v;
              avg /= 8;
              REXLOG_INFO("[cost-probe] without ps {:016x} ({} of {} draws): GPU {:.2f} ms, the 8 frames before {:.2f} ms: "
                          "{:+.2f} ms",
                          probe_ps, probe_draws, probe_frame_draws, gpu_ms, avg, gpu_ms - avg);
            } else if (!probe_ps) {
              recent[count++ % 8] = gpu_ms;
            }
          }
          if (gpu_ms > 45.0) ++gpu_slow_frames;
          const bool slow = gpu_ms > 45.0 && hitch_lines_left.fetch_sub(1) > 0;
          if (slow) {
            REXLOG_INFO("[native] hitch: frame {} took {:.1f} ms on the GPU ({} draws, {} texture uploads, "
                        "{} new vertex buffers; thermal state {})",
                        number, gpu_ms, drawn_count, uploads, new_buffers, nfsmw::memory::ThermalState());
          }
          if (profile && (profile_report || slow) && !profile_labels->empty()) {
            const NSUInteger n = profile_labels->size();
            NSData* raw = [profile_buffer resolveCounterRange:NSMakeRange(0, 2 * n)];
            const auto* ts = static_cast<const MTLCounterResultTimestamp*>(raw.bytes);
            MTLTimestamp cpu1 = 0, gpu1 = 0;
            [done.device sampleTimestamps:&cpu1 gpuTimestamp:&gpu1];
            const double ns_per_tick = gpu1 > profile_gpu0 ? double(cpu1 - profile_cpu0) / double(gpu1 - profile_gpu0) : 1.0;
            // Each pass's incremental cost: how much later the frame's work
            // ends because of it (passes overlap on the GPU: a pass's own
            // span includes waiting for the one before, e.g. the depth copy
            // after the scene). In order of submission, the end beyond the
            // latest end so far. Grouped by label without " from draw N".
            std::vector<std::pair<double, size_t>> cost;
            std::map<std::string, std::pair<double, int>> groups;
            double sum = 0, latest = 0, first = -1;
            for (NSUInteger i = 0; ts && i < n; ++i) {
              const uint64_t a = ts[2 * i].timestamp, b = ts[2 * i + 1].timestamp;
              if (a == MTLCounterErrorValue || b == MTLCounterErrorValue || b < a) continue;
              const double start = double(a) * ns_per_tick / 1e6, end = double(b) * ns_per_tick / 1e6;
              if (first < 0) first = latest = start;
              const double ms = std::max(0.0, end - std::max(latest, start));
              latest = std::max(latest, end);
              cost.push_back({ms, i});
              sum += ms;
              std::string label = (*profile_labels)[i];
              if (const size_t at = label.find(" from draw "); at != std::string::npos) {
                const size_t paren = label.find(" (", at);
                label = label.substr(0, at) + (paren != std::string::npos ? label.substr(paren) : "");
              }
              auto& g = groups[label];
              g.first += ms;
              ++g.second;
            }
            std::sort(cost.rbegin(), cost.rend());
            std::vector<std::pair<double, std::string>> grouped;
            for (const auto& [label, g] : groups) {
              grouped.push_back({g.first, g.second > 1 ? fmt::format("{} ({} of them)", label, g.second) : label});
            }
            std::sort(grouped.rbegin(), grouped.rend());
            REXLOG_INFO("[native] GPU profile{}: {} passes and blits, {:.2f} ms of incremental cost (first start to "
                        "last end {:.2f} ms), frame {:.2f} ms on the GPU",
                        slow ? " of the slow frame" : "", n, sum, latest - std::max(first, 0.0),
                        (done.GPUEndTime - done.GPUStartTime) * 1000.0);
            for (size_t i = 0; i < grouped.size() && i < (slow ? 8 : 14); ++i) {
              REXLOG_INFO("[native]   {:6.2f} ms  {}", grouped[i].first, grouped[i].second);
            }
            if (!slow) {
              for (size_t i = 0; i < cost.size() && i < 5; ++i) {
                REXLOG_INFO("[native]   single: {:6.2f} ms  {}", cost[i].first, (*profile_labels)[cost[i].second]);
              }
            }
          }
        }
        FrameDoneOnGpu(number);
        --in_flight;
      }];
    }
    if (visibility && !visibility_slots.empty()) {
      // The counts, once the GPU is done: per query, the sum of its slots at
      // the guest's resolution. A query whose draws were all left out keeps
      // its last count.
      const std::vector<uint32_t> queries = frame->queries;
      const std::vector<VisibilitySlot> slots = visibility_slots;
      id<MTLBuffer> results = visibility;
      [cb addCompletedHandler:^(id<MTLCommandBuffer> done) {
        if (done.error) return;
        const uint64_t* r = static_cast<const uint64_t*>(results.contents);
        std::vector<double> sums(queries.size(), -1.0);
        for (size_t i = 0; i < slots.size(); ++i) {
          double& sum = sums[slots[i].query];
          sum = std::max(sum, 0.0) + double(r[i]) / slots[i].divisor;
        }
        std::lock_guard<std::mutex> lock(occlusion_mutex);
        for (size_t q = 0; q < queries.size(); ++q) {
          if (sums[q] >= 0) occlusion_counts[queries[q]] = uint64_t(std::llround(sums[q]));
        }
      }];
    }
    [cb commit];
    {
      const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - render_start).count();
      if (!dump && ms > 30.0 && hitch_lines_left.fetch_sub(1) > 0) {
        REXLOG_INFO("[native] hitch: frame {} took {:.1f} ms to encode: {} texture uploads ({} KiB, {:.1f} ms), "
                    "waiting for a drawable {:.1f} ms",
                    number, ms, frame_uploads, frame_upload_bytes >> 10, frame_upload_us / 1000.0, drawable_wait_ms);
      }
    }
    if (!final_texture) {
      ++frames_without_output;
    } else {
      frames_without_output = 0;
    }
    if (!dump) {  // The frame's notes (texture formats not decoded...), each new one once.
      static std::set<std::string> said;
      for (const auto& [draw, note] : frame->notes) {
        if (said.size() < 60 && said.insert(note).second) {
          REXLOG_INFO("[native] frame {} draw {}: {}", number, draw, note);
        }
      }
    }
    if (!dump) {
      if (number % 300 == 1) {
        uint64_t target_bytes = 0;
        for (const auto& [key, t] : targets) {
          (void)key;
          if (t.color) target_bytes += t.color.allocatedSize;
          if (t.depth) target_bytes += t.depth.allocatedSize;
          if (t.multisample_color && t.multisample_color != t.color) target_bytes += t.multisample_color.allocatedSize;
          if (t.multisample_depth && t.multisample_depth != t.depth) target_bytes += t.multisample_depth.allocatedSize;
        }
        uint64_t resolve_bytes = 0;
        for (const auto& [address, kept] : kept_resolves) {
          (void)address;
          if (kept.texture) resolve_bytes += kept.texture.allocatedSize;
        }
        const int64_t texture_bytes = gpu_texture_bytes.load();
        uint64_t buffer_bytes = 0;
        buffer_bytes = buffer_arena.Bytes();
        nfsmw::memory::Report("native renderer");
        constexpr double kMiB = 1024.0 * 1024.0;
        REXLOG_INFO("[native] memory: process {:.0f} MiB; retained targets {} / {:.0f} MiB, resolves {} / {:.0f} MiB, "
                    "textures {} / {:.0f} MiB (GPU), vertex buffers {} / {:.0f} MiB | frame buffers and resolves: "
                    "{} made, {} reused since the last line",
                    ProcessPhysicalFootprint() / kMiB, targets.size(), target_bytes / kMiB, kept_resolves.size(),
                    resolve_bytes / kMiB, gpu_texture_count.load(), texture_bytes / kMiB,
                    gpu_buffers.size(), buffer_bytes / kMiB, gpu_pool.made, gpu_pool.reused);
        gpu_pool.made = gpu_pool.reused = 0;
        const int64_t now = NowMs();
        const double seconds = stats_since_ms ? (now - stats_since_ms) / 1000.0 : 0;
        const uint64_t frames = number > 1 ? 300 : 1;
        REXLOG_INFO("[native] frame {}: {} of {} draws ({} without a shader library), {} resolves, {} textures ({} cached on the GPU), "
                    "{} vertex buffers cached, {} pipelines, {} resolves from earlier frames, {} passes split | {:.1f} frames/s on screen, recording "
                    "{:.2f} ms/frame (game thread: vertices {:.2f}, constants and textures {:.2f}; with the command stream "
                    "decoding {:.2f}), rendering {:.2f} ms/frame, "
                    "GPU {:.2f} ms/frame ({} over 45 ms) | vertex cache watch/fingerprint/miss {}/{}/{}, decoded {} attribute elements, "
                    "expanded indices {} -> {}, index cache hits/misses {}/{}, fingerprints {} calls / {} samples ({:.2f} us/sample) | "
                    "textures decoded {} ({} MiB)",
                    number, drawn, frame->draws.size(), frame->skipped_shader, resolves_done, frame->textures.size(),
                    gpu_texture_count.load(), gpu_buffers.size(), pipeline_cache.size(), kept_used, pass_splits,
                    seconds > 0 ? presented.exchange(0) / seconds : 0.0,
                    record_us.exchange(0) / 1000.0 / frames, record_vertex_us.exchange(0) / 1000.0 / frames,
                    record_texture_us.exchange(0) / 1000.0 / frames, nfsmw_capture_ns.exchange(0) / 1e6 / frames,
                    render_us.exchange(0) / 1000.0 / frames,
                    gpu_us.exchange(0) / 1000.0 / frames, gpu_slow_frames.exchange(0),
                    vertex_diagnostics.watched_cache_hits, vertex_diagnostics.fingerprint_cache_hits,
                    vertex_diagnostics.cache_misses, vertex_diagnostics.decoded_vertex_elements,
                    vertex_diagnostics.expanded_input_indices, vertex_diagnostics.expanded_output_indices,
                    vertex_diagnostics.index_cache_hits, vertex_diagnostics.index_cache_misses,
                    vertex_diagnostics.fingerprint_calls, vertex_diagnostics.fingerprint_sample_count,
                    vertex_diagnostics.fingerprint_sample_count
                        ? double(vertex_diagnostics.fingerprint_sample_ns) /
                              double(vertex_diagnostics.fingerprint_sample_count) / 1000.0
                        : 0.0,
                    textures_decoded_total.exchange(0), texture_decode_bytes_total.exchange(0) >> 20);
        vertex_diagnostics = {};
        stats_since_ms = now;
        pipeline_cache.Report();
      }
      return;
    }
    [cb waitUntilCompleted];
    ApplyWriteBacks(*writebacks);
    FrameDoneOnGpu(number);
    --in_flight;

    // Every target as a PNG, in order of first use.
    NSString* docs = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES).firstObject;
    NSString* root = [docs stringByAppendingPathComponent:@"native"];
    static bool cleared = false;
    if (!cleared) {
      cleared = true;
      [[NSFileManager defaultManager] removeItemAtPath:root error:nil];
    }
    // One folder per snapshot (menu and race both kept).
    NSString* dir = [root stringByAppendingPathComponent:[NSString stringWithFormat:@"frame_%05llu",
                                                                     (unsigned long long)number]];
    [[NSFileManager defaultManager] createDirectoryAtPath:dir withIntermediateDirectories:YES attributes:nil error:nil];
    CIContext* ci = [CIContext contextWithMTLDevice:device];
    CGColorSpaceRef space = CGColorSpaceCreateDeviceRGB();
    int n = 0;
    for (const std::string& key : order) {
      const Target& t = targets[key];
      CIImage* image = [CIImage imageWithMTLTexture:t.color options:@{kCIImageColorSpace : (__bridge id)space}];
      // Opaque: targets often keep alpha 0, which saved as plain white.
      image = [image imageBySettingAlphaOneInExtent:image.extent];
      image = [image imageByApplyingTransform:CGAffineTransformMake(1, 0, 0, -1, 0, t.height)];
      NSString* file = [dir stringByAppendingPathComponent:[NSString stringWithFormat:@"pass_%02d_%ux%u_fmt%u_%udraws.png", n++,
                                                                                      t.pitch, t.height, t.format, t.draws]];
      [ci writePNGRepresentationOfImage:image
                                  toURL:[NSURL fileURLWithPath:file]
                                 format:kCIFormatRGBA8
                             colorSpace:space
                                options:@{}
                                  error:nil];
    }
    // What each resolve copied out, cropped to its rectangle: the passes'
    // real outputs (a target can be cleared by its resolve), the last one
    // the finished frame.
    for (NSUInteger i = 0; i < resolved_textures.count && i < resolve_rects.size(); ++i) {
      id<MTLTexture> tex = resolved_textures[i];
      if (tex.textureType != MTLTextureType2D || resolve_rects[i].size.width == 0) {
        continue;  // cubes (environment map faces) and swizzled views: not saved
      }
      CIImage* image = [CIImage imageWithMTLTexture:tex options:@{kCIImageColorSpace : (__bridge id)space}];
      // Opaque: targets often keep alpha 0, which saved as plain white.
      image = [image imageBySettingAlphaOneInExtent:image.extent];
      if (tex.pixelFormat == MTLPixelFormatR32Float) {
        // Depth (one channel): grey, stretched over 0.9-1.0 where it lives.
        CIFilter* matrix = [CIFilter filterWithName:@"CIColorMatrix"];
        [matrix setValue:image forKey:kCIInputImageKey];
        const CGFloat k = 10.0;
        [matrix setValue:[CIVector vectorWithX:k Y:0 Z:0 W:0] forKey:@"inputRVector"];
        [matrix setValue:[CIVector vectorWithX:k Y:0 Z:0 W:0] forKey:@"inputGVector"];
        [matrix setValue:[CIVector vectorWithX:k Y:0 Z:0 W:0] forKey:@"inputBVector"];
        [matrix setValue:[CIVector vectorWithX:0 Y:0 Z:0 W:0] forKey:@"inputAVector"];
        [matrix setValue:[CIVector vectorWithX:-9 Y:-9 Z:-9 W:1] forKey:@"inputBiasVector"];
        image = matrix.outputImage;
      }
      image = [image imageByApplyingTransform:CGAffineTransformMake(1, 0, 0, -1, 0, tex.height)];
      image = [image imageByCroppingToRect:resolve_rects[i]];
      image = [image imageByApplyingTransform:CGAffineTransformMakeTranslation(-resolve_rects[i].origin.x,
                                                                               -resolve_rects[i].origin.y)];
      NSString* file = [dir stringByAppendingPathComponent:
                                [NSString stringWithFormat:@"%s.png", resolve_names[i].c_str()]];
      [ci writePNGRepresentationOfImage:image
                                  toURL:[NSURL fileURLWithPath:file]
                                 format:kCIFormatRGBA8
                             colorSpace:space
                                options:@{}
                                  error:nil];
    }
    for (const WatchSave& w : watch_saves) {
      if (w.texture.textureType != MTLTextureType2D) continue;
      CIImage* image = [CIImage imageWithMTLTexture:w.texture options:@{kCIImageColorSpace : (__bridge id)space}];
      // Opaque: targets often keep alpha 0, which saved as plain white.
      image = [image imageBySettingAlphaOneInExtent:image.extent];
      image = [image imageByApplyingTransform:CGAffineTransformMake(1, 0, 0, -1, 0, w.texture.height)];
      NSString* file = [dir stringByAppendingPathComponent:[NSString stringWithFormat:@"%s.png", w.name.c_str()]];
      [ci writePNGRepresentationOfImage:image toURL:[NSURL fileURLWithPath:file] format:kCIFormatRGBA8
                             colorSpace:space options:@{} error:nil];
    }
    CGColorSpaceRelease(space);
    REXLOG_INFO("[native] frame {}: {} of {} recorded draws drawn, {} targets saved to Documents/native; "
                "skipped: {} inline, {} without a shader library, {} other; {} textures; {} pipeline "
                "failures; resolves: {} done, {} skipped of {}; {} game-shader draws in pixel coordinates; "
                "{} from their arguments",
                number, drawn, frame->draws.size(), order.size(), frame->skipped_inline,
                frame->skipped_shader, frame->skipped_other, frame->textures.size(), pipeline_failures,
                resolves_done, resolves_skipped, frame->resolves.size(), screen_space_game_draws,
                frame->from_arguments);
    {  // snapshot frames only (every 10 s): the resolves and pass changes
      for (const std::string& line : diagnostics) {
        if (line.rfind("resolve", 0) != 0 && line.rfind("post draw", 0) != 0 && line.rfind("group", 0) != 0) continue;
        REXLOG_INFO("[native]   {}", line);
      }
    }
    for (const auto& [draw, note] : frame->notes) {
      REXLOG_INFO("[native]   at draw {}: {}", draw, note);
    }
  }
}

}  // namespace

namespace {

bool recording_dumps = false;  // the frame being recorded also saves PNGs

// The layer, once, on the main thread.
void EnsurePresentLayer() {
  static std::atomic<bool> requested{false};
  if (requested.exchange(true)) {
    return;
  }
  id<MTLDevice> device = store.device;
  dispatch_async(dispatch_get_main_queue(), ^{
    UIWindow* window = nil;
    for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
      if ([scene isKindOfClass:UIWindowScene.class]) {
        for (UIWindow* w in ((UIWindowScene*)scene).windows) {
          if (w.isKeyWindow || !window) window = w;
        }
      }
    }
    if (!window) {
      REXLOG_WARN("[native] no window for the native renderer's layer");
      return;
    }
    NFSNativeView* view = [[NFSNativeView alloc] initWithFrame:window.bounds];
    view.userInteractionEnabled = NO;
    view.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    CAMetalLayer* layer = (CAMetalLayer*)view.layer;
    layer.device = device;
    layer.pixelFormat = MTLPixelFormatBGRA8Unorm;
    layer.framebufferOnly = YES;
    // Apple's Metal Performance HUD on this layer (the one showing the game),
    // not on the emulated renderer's, which now hardly presents (the HUD
    // shrank to a frame counter there).
    if (REXCVAR_GET(nfsmw_native_metal_hud)) {
      if (@available(iOS 16.0, *)) {
        layer.developerHUDProperties = @{@"mode" : @"default", @"logging" : @"default"};
      }
    }
    UIView* game = window.rootViewController.view;
    if (game && game.superview == window) {
      [window insertSubview:view aboveSubview:game];
    } else if (game) {
      [game addSubview:view];
    } else {
      [window addSubview:view];
    }
    [view setNeedsLayout];
    [view layoutIfNeeded];
    present_layer = layer;
    present_view = view;
    REXLOG_INFO("[native] on screen ({} x {} points)", int(view.bounds.size.width),
                int(view.bounds.size.height));
  });
}

}  // namespace

namespace {
bool NativeSwap();
void NativeDraw(const NfsmwNativeDraw* draw);
void NativeResolve(const uint32_t* regs);
}  // namespace

// The draw capture (native_draw_census.cpp, on the game thread) hands frames
// over here unless the command processor does (nfsmw_native_cp).
extern "C" bool nfsmw_native_cp_mode() { return REXCVAR_GET(nfsmw_native_cp); }
extern "C" bool nfsmw_native_swap() { return REXCVAR_GET(nfsmw_native_cp) ? false : NativeSwap(); }
extern "C" void nfsmw_native_draw(const NfsmwNativeDraw* draw) {
  if (!REXCVAR_GET(nfsmw_native_cp)) NativeDraw(draw);
}
extern "C" void nfsmw_native_resolve(const uint32_t* regs) {
  if (!REXCVAR_GET(nfsmw_native_cp)) NativeResolve(regs);
}

// From the command processor (tools/ios/patch_ios_native_only.py), on its
// thread: the draws as it handles them, with its register file and shaders.
namespace {
// The renderer's keys for a shader: vertex shaders hashed with their vertex
// fetches zeroed, pixel shaders whole (FNV-1a over the big-endian bytes, as
// tools/native/nfsmw_shader_containers.py and the draw capture compute them).
uint64_t ShaderKey(const uint32_t* ucode, uint32_t n, bool vertex) {
  std::vector<uint32_t> w(ucode, ucode + n);
  if (vertex) {
    for (uint32_t i = 0; i + 2 < n; i += 3) {
      const uint64_t cfs[2] = {w[i] | (uint64_t(w[i + 1] & 0xFFFF) << 32),
                               (w[i + 1] >> 16) | (uint64_t(w[i + 2]) << 16)};
      bool stop = false;
      for (uint64_t cf : cfs) {
        const uint32_t opcode = (cf >> 44) & 0xF;
        if (opcode == 1 || opcode == 2 || (opcode >= 3 && opcode <= 6) || opcode == 13 || opcode == 14) {
          const uint32_t address = cf & 0xFFF, count = (cf >> 12) & 7, sequence = (cf >> 16) & 0xFFF;
          for (uint32_t k = 0; k < count; ++k) {
            const uint32_t at = (address + k) * 3;
            if (((sequence >> (2 * k)) & 1) && at + 2 < n && (w[at] & 0x1F) == 0) {
              w[at] = w[at + 1] = w[at + 2] = 0;
            }
          }
          stop |= opcode == 2 || opcode == 4 || opcode == 6 || opcode == 14;
        }
      }
      if (stop) break;
    }
  }
  uint64_t h = 0xCBF29CE484222325ull;
  for (uint32_t v : w) {
    for (int b = 3; b >= 0; --b) h = (h ^ ((v >> (8 * b)) & 0xFF)) * 0x100000001B3ull;
  }
  return h;
}

// From the very first draw, the emulated renderer draws nothing while the
// native one is on (nfsmw_native_from_boot): its boot frames (the EA logo's
// loading) uploaded guest memory into Vulkan's 512 MB shared-memory buffer,
// which then stayed resident (~650 MiB of graphics memory before the native
// renderer's first frame), for nothing.
void ArmNativeOnlyFromBoot() {
  static bool armed = false;
  if (armed) return;
  armed = true;
  if (REXCVAR_GET(nfsmw_native_cp) && REXCVAR_GET(nfsmw_native_present) && REXCVAR_GET(nfsmw_native_exclusive) &&
      REXCVAR_GET(nfsmw_native_from_boot)) {
    rex_native_draws_only.store(true, std::memory_order_relaxed);
    REXLOG_INFO("[native] the emulated renderer draws nothing from the first draw on");
  }
}

void CpDraw(const RexNativeDraw* in) {
  ArmNativeOnlyFromBoot();
  if (!REXCVAR_GET(nfsmw_native_cp) || !recording || !in->vs_ucode || !in->ps_ucode) {
    return;
  }
  static std::unordered_map<uint64_t, uint64_t> vs_keys, ps_keys;  // SDK hash -> key
  auto key = [](std::unordered_map<uint64_t, uint64_t>& keys, uint64_t hash, const uint32_t* ucode, uint32_t n,
                bool vertex) {
    auto it = keys.find(hash);
    if (it == keys.end()) it = keys.emplace(hash, ShaderKey(ucode, n, vertex)).first;
    return it->second;
  };
  NfsmwNativeDraw d = {};
  d.regs = in->regs;
  d.vs_microcode = in->vs_ucode;
  d.vs_dwords = in->vs_dwords;
  d.vs_key = key(vs_keys, in->vs_hash, in->vs_ucode, in->vs_dwords, true);
  d.ps_key = key(ps_keys, in->ps_hash, in->ps_ucode, in->ps_dwords, false);
  d.initiator = in->regs[0x21FC];  // VGT_DRAW_INITIATOR
  d.index_base = in->index_base;
  d.index_size = (in->index_endian & 3) << 30;
  NativeDraw(&d);
}

void CpResolve(const uint32_t* regs) {
  ArmNativeOnlyFromBoot();
  if (REXCVAR_GET(nfsmw_native_cp)) NativeResolve(regs);
}

void CpSwap() {
  if (REXCVAR_GET(nfsmw_native_cp)) NativeSwap();
}

// A query's begin: the draws that follow are counted. Its end: the last count
// the GPU gave for it (a frame or two late), or "fully visible" (a 1280x720
// target) before the first, as the emulated renderer's async queries do.
bool CpOcclusion(uint32_t address, bool end, uint64_t* samples) {
  if (!REXCVAR_GET(nfsmw_native_cp) || !REXCVAR_GET(nfsmw_native_occlusion)) {
    return false;
  }
  if (!end) {
    if (recording && recording->queries.size() < kVisibilitySlots) {
      recording->open_query = int(recording->queries.size());
      recording->queries.push_back(address);
    }
    return true;
  }
  if (recording) recording->open_query = -1;
  std::lock_guard<std::mutex> lock(occlusion_mutex);
  auto it = occlusion_counts.find(address);
  *samples = it != occlusion_counts.end() ? it->second : 1280u * 720u;
  return true;
}

// Installed when the app loads; each checks nfsmw_native_cp when called.
__attribute__((constructor)) void InstallCommandProcessorHooks() {
  rex_native_draw_hook.store(&CpDraw);
  rex_native_resolve_hook.store(&CpResolve);
  rex_native_swap_hook.store(&CpSwap);
  rex_native_occlusion_hook.store(&CpOcclusion);
}

bool NativeSwap() {
  // Resolves the renderer wrote back to guest memory: its copies stay valid.
  {
    std::vector<uint32_t> addresses;
    {
      std::lock_guard<std::mutex> lock(written_back_mutex);
      addresses.swap(written_back);
    }
    for (uint32_t a : addresses) {
      auto pr = persistent_resolves.find(a);
      if (pr != persistent_resolves.end()) pr->second.fingerprint = Fingerprint(Physical(a), pr->second.span);
    }
  }
  // Hitch log: the time since the last swap on this (the command processor's)
  // thread, and what the frame's recording spent it on.
  static auto last_swap = std::chrono::steady_clock::now();
  const auto swap_start = std::chrono::steady_clock::now();
  const double swap_interval_ms = std::chrono::duration<double, std::milli>(swap_start - last_swap).count();
  struct {
    bool valid = false;
    size_t draws = 0;
    uint64_t record_us = 0, vertex_misses = 0, vertex_elements = 0;
    uint32_t textures_decoded = 0;
    uint64_t texture_bytes = 0, texture_us = 0;
  } hitch;
  if (recording) {
    hitch = {true, recording->draws.size(), recording->record_us, recording->vertex_diagnostics.cache_misses,
             recording->vertex_diagnostics.decoded_vertex_elements, recording->textures_decoded,
             recording->texture_decode_bytes, recording->texture_decode_us};
  }
  ++frame_counter;
  SweepTextureCache();
  Sweep(attribute_cache);
  Sweep(index_cache);
  const bool present = REXCVAR_GET(nfsmw_native_present);
  if (recording) {
    std::unique_ptr<Frame> frame = std::move(recording);
    if (frame->movie_draws) {
      // A movie frame: not drawn here. After three, the emulated renderer
      // draws again and its image shows (below); the first native frame
      // without the movie takes over again.
      static bool said = false;
      if (!said) {
        said = true;
        REXLOG_INFO("[native] a movie is playing: its frames go to the emulated renderer");
      }
      ++frames_without_output;
    } else if (frame->draws.empty()) {
      if (recording_dumps) next_dump_ms = 0;  // nothing drawn: try the next frame
    } else {
      ++in_flight;
      const uint32_t number = ++dump_number;
      const bool dump = recording_dumps;
      static dispatch_queue_t queue = dispatch_queue_create("nfsmw.native", DISPATCH_QUEUE_SERIAL);
      __block Frame* raw = frame.release();
      dispatch_async(queue, ^{
        RenderFrame(std::unique_ptr<Frame>(raw), number, present, dump);
      });
    }
  }
  // Two frames already in flight (one encoding, one on the GPU). Paced: the
  // game waits for one to finish (up to 50 ms), so every frame it makes is
  // shown, evenly, instead of the renderer dropping every other one at
  // irregular times. Not paced: this frame is skipped.
  if (in_flight >= 2 && REXCVAR_GET(nfsmw_native_present) && REXCVAR_GET(nfsmw_native_pace)) {
    const auto give_up = std::chrono::steady_clock::now() + std::chrono::milliseconds(50);
    while (in_flight >= 2 && std::chrono::steady_clock::now() < give_up) {
      std::this_thread::sleep_for(std::chrono::microseconds(250));
    }
  }
  last_swap = std::chrono::steady_clock::now();
  if (hitch.valid && swap_interval_ms > 40.0 && hitch_lines_left.fetch_sub(1) > 0) {
    const double record_ms = hitch.record_us / 1000.0;
    REXLOG_INFO("[native] hitch: frame {} took {:.1f} ms between swaps ({} draws): recording {:.1f} ms "
                "({} textures decoded, {} KiB, {:.1f} ms; {} vertex cache misses, {} elements), "
                "outside the recording {:.1f} ms, then waiting for the renderer {:.1f} ms",
                dump_number, swap_interval_ms, hitch.draws, record_ms, hitch.textures_decoded,
                hitch.texture_bytes >> 10, hitch.texture_us / 1000.0, hitch.vertex_misses, hitch.vertex_elements,
                swap_interval_ms - record_ms,
                std::chrono::duration<double, std::milli>(last_swap - swap_start).count());
  }
  if (in_flight >= 2) {
    return false;
  }
  // No native output for a while (FMVs): the emulated renderer shows through.
  UpdateLayerVisibility(present && frames_without_output < 3);
  // No native frames for a while (FMVs): the emulated renderer draws again.
  rex_native_draws_only.store(present && REXCVAR_GET(nfsmw_native_exclusive) && frames_without_output < 3,
                              std::memory_order_relaxed);
  const bool dump_due = REXCVAR_GET(nfsmw_native_dump) && NowMs() >= next_dump_ms;
  if (!present && !dump_due) {
    return false;
  }
  store.Load();
  if (store.functions.empty()) {
    return false;
  }
  if (present) {
    EnsurePresentLayer();
  }
  if (dump_due) {
    next_dump_ms = NowMs() + std::max(500, REXCVAR_GET(nfsmw_native_dump_interval_ms));
  }
  recording_dumps = dump_due;
  recording = std::make_unique<Frame>();
  return true;
}

void NativeDraw(const NfsmwNativeDraw* draw) {
  if (!recording) {
    return;
  }
  // Timed: one draw in eight (counted eight times). Reading the clock five
  // times for every draw cost ~1 ms per frame on its own.
  static uint32_t draw_tick = 0;
  timed_draw = (++draw_tick & 7) == 0;
  struct Timer {
    FastClock::time_point t0;
    bool on;
    ~Timer() {
      if (!on) return;
      const uint64_t us = 8 * uint64_t(std::chrono::duration_cast<std::chrono::microseconds>(
                                           FastClock::now() - t0).count());
      record_us += us;
      if (recording) recording->record_us += us;
    }
  } timer{timed_draw ? FastClock::now() : FastClock::time_point{}, timed_draw};
  // Without the native renderer on screen, PNG frames are menu frames only
  // (~330 draws): a race frame (2,000-3,000) is dropped instead of decoded.
  const size_t limit = REXCVAR_GET(nfsmw_native_present) ? 20000 : 700;
  if (recording->draws.size() + recording->skipped_shader + recording->skipped_other > limit) {
    recording.reset();
    return;
  }
  const size_t before = recording->draws.size();
  Record(*recording, *draw);
  if (recording && recording->open_query >= 0 && recording->draws.size() > before) {
    recording->draws.back().query = recording->open_query;
  }
}

void NativeResolve(const uint32_t* regs) {
  if (!recording) {
    return;
  }
  ResolveEvent ev = {};
  ev.after_draws = recording->draws.size();
  const uint32_t control = regs[0x2318];  // RB_COPY_CONTROL
  ev.control = control;
  ev.depth = (control & 7) >= 4;
  ev.clear_color = (control >> 8) & 1;
  ev.clear_depth = (control >> 9) & 1;
  ev.clear_color_value = regs[0x231E];
  ev.clear_depth_value = regs[0x231D];
  ev.surface_info = regs[kRbSurfaceInfo];
  // RB_COLOR_INFO of the selected render target (0: 0x2001, 1-3: 0x2003-5).
  const uint32_t rt = control & 3;
  ev.color_info = regs[rt == 0 ? kRbColorInfo : 0x2002 + rt];
  ev.depth_info = regs[kRbDepthInfo];
  ev.dest_base = regs[0x2319] & ~0xFFFu;
  resolve_destinations[ev.dest_base] = frame_counter;
  const uint32_t dest_info = regs[0x231B];  // RB_COPY_DEST_INFO
  ev.array = (dest_info >> 3) & 1;
  ev.slice = (dest_info >> 4) & 7;
  ev.swap = (dest_info >> 24) & 1;
  ev.exp_bias = int32_t(dest_info << 10) >> 26;  // 6 bits at 16, signed
  ev.dest_endian = dest_info & 7;
  ev.dest_format = (dest_info >> 7) & 0x3F;
  ev.dest_pitch = regs[0x231A] & 0x3FFF;
  ev.dest_height = (regs[0x231A] >> 16) & 0x3FFF;
  // The rectangle: three vertices (x, y) at vertex fetch 0, plus the D3D
  // half-pixel offset and the window offset; aligned to 8 pixels.
  const uint32_t f0 = regs[kFetchBase], f1 = regs[kFetchBase + 1];
  if ((f0 & 3) != 3 || ((f1 >> 2) & 0xFFFFFF) != 6) {
    Note(*recording, "resolve without its rectangle");
    return;
  }
  const uint8_t* p = Physical(f0 & ~3u);
  const auto endian = xenos::Endian(f1 & 3);
  const float half = (regs[0x2302] & 1) ? 0.0f : 0.5f;  // PA_SU_VTX_CNTL pix_center
  float v[6];
  for (int i = 0; i < 6; ++i) v[i] = AsFloat(xenos::GpuSwap(LoadLE32(p + 4 * i), endian)) + half;
  int32_t x0 = int32_t(std::lround(std::min({v[0], v[2], v[4]})));
  int32_t y0 = int32_t(std::lround(std::min({v[1], v[3], v[5]})));
  int32_t x1 = int32_t(std::lround(std::max({v[0], v[2], v[4]})));
  int32_t y1 = int32_t(std::lround(std::max({v[1], v[3], v[5]})));
  // No window offset: tiling's (see the draws); the rectangle in target
  // coordinates, clamped.
  x0 = std::max(x0, 0);
  y0 = std::max(y0, 0);
  ev.x0 = x0 & ~7;
  ev.y0 = y0 & ~7;
  ev.x1 = (x1 + 7) & ~7;
  ev.y1 = (y1 + 7) & ~7;
  recording->resolves.push_back(ev);
  recording->resolved_so_far.insert(ev.dest_base);
  std::fill(std::begin(recording->slot_valid), std::end(recording->slot_valid), false);
  {
    const uint32_t span = std::max<uint32_t>(ev.dest_pitch, 32) * std::max<uint32_t>(ev.dest_height, 32) * 4;
    persistent_resolves[ev.dest_base] = {Fingerprint(Physical(ev.dest_base), span), span, frame_counter};
  }
}

}  // namespace
