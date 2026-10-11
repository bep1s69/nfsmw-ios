// Native renderer, step 2: do the translated shaders work as Metal pipelines?
//
// tools/native/build_shaders.sh translates NFSMW's shaders (from the game's
// own files) into one .metallib per shader, named vs_/ps_<hash> with the hash
// the draw capture computes (ios/src/native_draw_census.cpp). A local test
// build bundles them in NativeShaders/ (-DNFSMW_NATIVE_SHADERS_DIR).
//
// After each captured frame, the capture hands over the frame's shader pairs
// and this builds a Metal render pipeline for each: vertex and pixel function
// linked, the vertex inputs from the vertex function's own attributes. The log
// says how many pairs had both libraries and how many linked, with the first
// errors. Nothing is drawn yet.

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include <cstdint>
#include <map>
#include <mutex>
#include <set>
#include <string>
#include <utility>
#include <vector>

#include <rex/logging.h>

namespace {

std::mutex mutex;
id<MTLDevice> device;
std::map<std::string, id<MTLFunction>> functions;  // "vs_<hash>" -> shaderMain
std::set<std::pair<uint64_t, uint64_t>> tried;
bool loaded = false;
uint32_t pairs_ok = 0, pairs_missing = 0, pairs_failed = 0;

void Load() {
  if (loaded) {
    return;
  }
  loaded = true;
  device = MTLCreateSystemDefaultDevice();
  NSString* dir = [[NSBundle mainBundle].resourcePath stringByAppendingPathComponent:@"NativeShaders"];
  NSArray<NSString*>* names = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:dir error:nil];
  uint32_t failed = 0;
  // The shaders declare an optional specialization constant
  // (G_SPEC_CONSTANTS, function constant 0); Metal asserts (aborts) when a
  // pipeline uses a function not specialized with constant values.
  MTLFunctionConstantValues* constants = [MTLFunctionConstantValues new];
  const uint32_t spec = 0;
  [constants setConstantValue:&spec type:MTLDataTypeUInt atIndex:0];
  for (NSString* name in names) {
    if (![name.pathExtension isEqualToString:@"metallib"]) {
      continue;
    }
    NSError* error = nil;
    id<MTLLibrary> library =
        [device newLibraryWithURL:[NSURL fileURLWithPath:[dir stringByAppendingPathComponent:name]]
                            error:&error];
    id<MTLFunction> function =
        library ? [library newFunctionWithName:@"shaderMain" constantValues:constants error:&error]
                : nil;
    if (!function) {
      if (++failed <= 3) {
        REXLOG_WARN("[native-metal] {}: {}", name.UTF8String,
                    error ? error.localizedDescription.UTF8String : "no shaderMain");
      }
      continue;
    }
    functions[name.stringByDeletingPathExtension.UTF8String] = function;
  }
  REXLOG_INFO("[native-metal] {} shader libraries loaded from NativeShaders/ ({} failed), GPU {}",
              functions.size(), failed, device.name.UTF8String);
}

id<MTLFunction> Find(const char* kind, uint64_t hash) {
  char name[32];
  snprintf(name, sizeof(name), "%s_%016llx", kind, static_cast<unsigned long long>(hash));
  auto it = functions.find(name);
  return it == functions.end() ? nil : it->second;
}

}  // namespace

namespace {

void Probe(const std::vector<uint64_t>& pairs_in) {
  const uint64_t* pairs = pairs_in.data();
  const uint32_t count = uint32_t(pairs_in.size() / 2);
  std::lock_guard<std::mutex> lock(mutex);
  @autoreleasepool {
    Load();
    if (functions.empty()) {
      return;
    }
    uint32_t ok = 0, missing = 0, failed = 0;
    for (uint32_t i = 0; i < count; ++i) {
      const uint64_t vs_key = pairs[2 * i], ps_key = pairs[2 * i + 1];
      if (!tried.insert({vs_key, ps_key}).second) {
        continue;
      }
      id<MTLFunction> vs = Find("vs", vs_key);
      id<MTLFunction> ps = Find("ps", ps_key);
      if (!vs || !ps) {
        ++missing;
        REXLOG_INFO("[native-metal]   pair vs {:016x}{} ps {:016x}{}", vs_key, vs ? "" : " (missing)",
                    ps_key, ps ? "" : " (missing)");
        continue;
      }
      MTLRenderPipelineDescriptor* desc = [MTLRenderPipelineDescriptor new];
      desc.vertexFunction = vs;
      desc.fragmentFunction = ps;
      // Every vertex input as a float4 from its own buffer (16 + attribute):
      // buffers 0-8 are the shaders' descriptor heaps and push constants.
      // Metal has 31 vertex attributes; the translator numbers some
      // semantics up to 39 (to be renumbered in the build): report those.
      MTLVertexDescriptor* vertex = [MTLVertexDescriptor vertexDescriptor];
      NSUInteger beyond = 0;
      for (MTLVertexAttribute* attribute in vs.vertexAttributes) {
        if (!attribute.active) {
          continue;
        }
        const NSUInteger index = attribute.attributeIndex;
        if (index > 30) {
          beyond = index;
          break;
        }
        vertex.attributes[index].format = attribute.attributeType == MTLDataTypeUInt4
                                              ? MTLVertexFormatUInt4
                                              : MTLVertexFormatFloat4;
        vertex.attributes[index].offset = 0;
        vertex.attributes[index].bufferIndex = 16 + index % 14;
        vertex.layouts[16 + index % 14].stride = 16;
      }
      if (beyond) {
        ++failed;
        REXLOG_WARN("[native-metal]   pair vs {:016x} ps {:016x}: vertex input at attribute {} "
                    "(Metal has 0-30)",
                    vs_key, ps_key, uint32_t(beyond));
        continue;
      }
      desc.vertexDescriptor = vertex;
      for (int c = 0; c < 4; ++c) {
        desc.colorAttachments[c].pixelFormat = MTLPixelFormatRGBA8Unorm;
      }
      desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float_Stencil8;
      desc.stencilAttachmentPixelFormat = MTLPixelFormatDepth32Float_Stencil8;
      NSError* error = nil;
      id<MTLRenderPipelineState> state = nil;
      @try {
        state = [device newRenderPipelineStateWithDescriptor:desc error:&error];
      } @catch (NSException* exception) {
        REXLOG_WARN("[native-metal]   pair vs {:016x} ps {:016x} threw: {}", vs_key, ps_key,
                    exception.reason.UTF8String);
        ++failed;
        continue;
      }
      if (state) {
        ++ok;
      } else {
        ++failed;
        REXLOG_WARN("[native-metal]   pair vs {:016x} ps {:016x} failed: {}", vs_key, ps_key,
                    error.localizedDescription.UTF8String);
      }
    }
    pairs_ok += ok;
    pairs_missing += missing;
    pairs_failed += failed;
    REXLOG_INFO("[native-metal] this frame's new shader pairs: {} linked, {} missing a library, {} "
                "failed (so far {} / {} / {})",
                ok, missing, failed, pairs_ok, pairs_missing, pairs_failed);
  }
}

}  // namespace

// Called by the draw capture after a frame (pairs of vertex shader key, pixel
// shader hash). The work runs on a queue of its own: the game's threads have
// small stacks (Metal's shader compiler needs more) and must not wait for it.
extern "C" void nfsmw_native_probe_pipelines(const uint64_t* pairs, uint32_t count) {
  std::vector<uint64_t> copy(pairs, pairs + 2 * count);
  static dispatch_queue_t queue =
      dispatch_queue_create("nfsmw.native-metal-probe", DISPATCH_QUEUE_SERIAL);
  dispatch_async(queue, ^{
    Probe(copy);
  });
}
