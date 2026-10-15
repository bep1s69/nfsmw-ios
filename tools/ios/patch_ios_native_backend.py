#!/usr/bin/env python3
"""
A graphics backend without Vulkan, for when the native Metal renderer draws
the game: gpu_backend "native".

    python3 tools/ios/patch_ios_native_backend.py            apply
    python3 tools/ios/patch_ios_native_backend.py --status
    python3 tools/ios/patch_ios_native_backend.py --revert

Touches src/graphics/plugin_main.cpp (the GPU plugin's entry point).


WHY
===

The native renderer (ios/src/native_renderer.mm) draws every frame, movies
included, from the draws the command processor hands it. The Vulkan backend
still came up for nothing: MoltenVK, a Vulkan device, its 512 MB
shared-memory buffer, EDRAM, texture and render target caches, a swapchain
(the graphics footprint jumped by ~630 MiB as the game started).


HOW
===

"native" creates:
  - NativeCommandProcessor: the SDK's command processor (every packet read,
    registers, fences, events, swaps, the native renderer's hooks) with no
    host GPU behind it: shaders kept as microcode only (what the native
    renderer reads), draws and resolves done (the native renderer has them),
    occlusion queries answered by the native renderer when it counts, else
    the SDK's fixed count;
  - a provider whose presenter presents nothing: the native renderer has its
    own CAMetalLayer over the game view. No immediate drawer (no ImGui).
Selected by the launcher (gpu_backend=native) with the native renderer on.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import find_sdk, run  # noqa: E402
from patch_ios_native_constants import augment_native_backend  # noqa: E402

FILE = "src/graphics/plugin_main.cpp"

INC_ANCHOR = '''#include <rex/logging.h>
#include <rex/system/gpu_plugin.h>
'''
INC_NEW = '''#include <rex/logging.h>
#include <rex/system/gpu_plugin.h>

// LOCAL PATCH - iOS: the "native" backend (tools/ios/patch_ios_native_backend.py).
#include <atomic>
#include <memory>
#include <unordered_map>
#include <rex/graphics/command_processor.h>
#include <rex/graphics/graphics_system.h>
#include <rex/graphics/pipeline/shader/shader.h>
#include <rex/graphics/xenos.h>
#include <rex/memory/ring_buffer.h>
#include <rex/ui/graphics_provider.h>
#include <rex/ui/immediate_drawer.h>
#include <rex/ui/presenter.h>
#include <rex/ui/surface.h>

// The native renderer's occlusion hook (patch_ios_native_occlusion.py), in
// the runtime.
extern std::atomic<bool (*)(uint32_t, bool, uint64_t*)> rex_native_occlusion_hook;
// The on-screen FPS counter's values (defined in the Vulkan command processor).
extern "C" std::atomic<float> nfsmw_fps_invitado, nfsmw_ms_invitado, nfsmw_ms_peor_invitado;
#include <algorithm>
#include <chrono>

namespace rex::graphics::native_backend {

// Presents nothing: the native renderer shows the game on its own layer.
class NullPresenter : public ::rex::ui::Presenter {
 public:
  explicit NullPresenter(HostGpuLossCallback cb) : Presenter(cb) {}
  ::rex::ui::Surface::TypeFlags GetSupportedSurfaceTypes() const override {
    return ::rex::ui::Surface::kTypeFlag_CAMetalLayer;
  }
  bool CaptureGuestOutput(::rex::ui::RawImage&) override { return false; }

 protected:
  SurfacePaintConnectResult ConnectOrReconnectPaintingToSurfaceFromUIThread(
      ::rex::ui::Surface&, uint32_t, uint32_t, bool, bool& is_vsync_implicit_out) override {
    is_vsync_implicit_out = false;
    return SurfacePaintConnectResult::kSuccess;
  }
  void DisconnectPaintingFromSurfaceFromUIThreadImpl() override {}
  bool RefreshGuestOutputImpl(uint32_t, uint32_t, uint32_t,
                              std::function<bool(GuestOutputRefreshContext& context)>,
                              bool& is_8bpc_out_ref) override {
    is_8bpc_out_ref = true;
    return true;
  }
  PaintResult PaintAndPresentImpl(bool) override { return PaintResult::kPresented; }
};

class NullProvider : public ::rex::ui::GraphicsProvider {
 public:
  std::unique_ptr<::rex::ui::Presenter> CreatePresenter(
      ::rex::ui::Presenter::HostGpuLossCallback cb) override {
    return std::make_unique<NullPresenter>(cb);
  }
  std::unique_ptr<::rex::ui::ImmediateDrawer> CreateImmediateDrawer() override { return nullptr; }
};

class NativeCommandProcessor : public CommandProcessor {
 public:
  NativeCommandProcessor(GraphicsSystem* graphics_system, system::KernelState* kernel_state)
      : CommandProcessor(graphics_system, kernel_state) {}

 protected:
  bool SetupContext() override { return true; }
  void ShutdownContext() override { shaders_.clear(); }
  // The guest's frame rate for the on-screen counter (nfsmw_fps_invitado /
  // nfsmw_ms_invitado, published by the Vulkan backend's swap otherwise).
  void IssueSwap(uint32_t, uint32_t, uint32_t) override {
    const auto now = std::chrono::steady_clock::now();
    if (fps_since_ == std::chrono::steady_clock::time_point{}) {
      fps_since_ = now;
      return;
    }
    ++fps_frames_;
    if (fps_last_ != std::chrono::steady_clock::time_point{}) {
      fps_worst_ms_ = std::max(fps_worst_ms_, std::chrono::duration<double, std::milli>(now - fps_last_).count());
    }
    fps_last_ = now;
    const double seconds = std::chrono::duration<double>(now - fps_since_).count();
    if (seconds >= 0.5) {
      nfsmw_fps_invitado.store(float(fps_frames_ / seconds), std::memory_order_relaxed);
      nfsmw_ms_invitado.store(float(seconds * 1000.0 / fps_frames_), std::memory_order_relaxed);
      nfsmw_ms_peor_invitado.store(float(fps_worst_ms_), std::memory_order_relaxed);
      fps_frames_ = 0;
      fps_worst_ms_ = 0.0;
      fps_since_ = now;
    }
  }
  std::chrono::steady_clock::time_point fps_since_{}, fps_last_{};
  uint32_t fps_frames_ = 0;
  double fps_worst_ms_ = 0.0;

  // Microcode only: the native renderer translates nothing at run time (its
  // shaders are prebuilt Metal libraries keyed by microcode).
  Shader* LoadShader(xenos::ShaderType shader_type, uint32_t, const uint32_t* host_address,
                     uint32_t dword_count) override {
    uint64_t hash = 0xCBF29CE484222325ull;
    for (uint32_t i = 0; i < dword_count; ++i) hash = (hash ^ host_address[i]) * 0x100000001B3ull;
    hash ^= uint64_t(shader_type) << 63;
    auto it = shaders_.find(hash);
    if (it != shaders_.end()) return it->second.get();
    auto shader = std::make_unique<Shader>(shader_type, hash, host_address, dword_count);
    Shader* raw = shader.get();
    shaders_.emplace(hash, std::move(shader));
    return raw;
  }
  bool IssueDraw(xenos::PrimitiveType, uint32_t, IndexBufferInfo*, bool) override { return true; }
  bool IssueCopy() override { return true; }

  // Occlusion queries: the native renderer's count when it counts, else the
  // SDK's fixed one (query_occlusion_fake_sample_count).
  bool ExecutePacketType3_EVENT_WRITE_ZPD(memory::RingBuffer* reader, uint32_t packet,
                                          uint32_t count) override {
    auto* native_query = rex_native_occlusion_hook.load(std::memory_order_relaxed);
    if (native_query) {
      const uint32_t kQueryFinished = rex::byte_swap(0xFFFFFEED);
      const uint32_t sample_count_addr = register_file_->values[XE_GPU_REG_RB_SAMPLE_COUNT_ADDR];
      auto* sample_counts =
          memory_->TranslatePhysical<xenos::xe_gpu_depth_sample_counts*>(sample_count_addr);
      if (sample_counts) {
        const bool is_end = sample_counts->ZPass_A == kQueryFinished ||
                            sample_counts->ZPass_B == kQueryFinished ||
                            sample_counts->ZFail_A == kQueryFinished ||
                            sample_counts->ZFail_B == kQueryFinished;
        uint64_t samples = 0;
        if (native_query(sample_count_addr, is_end, &samples)) {
          const uint32_t initiator = reader->ReadAndSwap<uint32_t>();
          WriteRegister(XE_GPU_REG_VGT_EVENT_INITIATOR, initiator & 0x3F);
          if (is_end) {
            const uint32_t clamped = samples > 0xFFFFFFFFull ? 0xFFFFFFFFu : uint32_t(samples);
            std::memset(sample_counts, 0, sizeof(*sample_counts));
            sample_counts->Total_A = clamped;
            sample_counts->ZPass_A = clamped;
          }
          return true;
        }
      }
    }
    return CommandProcessor::ExecutePacketType3_EVENT_WRITE_ZPD(reader, packet, count);
  }

 private:
  std::unordered_map<uint64_t, std::unique_ptr<Shader>> shaders_;
};

class NativeGraphicsSystem : public GraphicsSystem {
 public:
  std::string name() const override { return "Native (Metal)"; }

 protected:
  void CreateProvider(bool) override { provider_ = std::make_unique<NullProvider>(); }
  std::unique_ptr<CommandProcessor> CreateCommandProcessor() override {
    return std::make_unique<NativeCommandProcessor>(this, kernel_state_);
  }
};

}  // namespace rex::graphics::native_backend
'''

SEL_ANCHOR = '''  std::string_view backend = info->backend ? info->backend : "any";
'''
SEL_NEW = '''  std::string_view backend = info->backend ? info->backend : "any";
  // LOCAL PATCH - iOS (tools/ios/patch_ios_native_backend.py).
  if (backend == "native") {
    REXLOG_INFO("rexgpu-xenos: native backend (no Vulkan; the native Metal renderer draws)");
    return new rex::graphics::native_backend::NativeGraphicsSystem();
  }
'''

# Keep the fast path in fresh SDK preparation as well as existing patched trees.
LEGACY_INC_NEW = INC_NEW
INC_NEW = augment_native_backend(INC_NEW)

BLOCKS = [
    (FILE, "the native backend", INC_ANCHOR, INC_NEW),
    (FILE, "gpu_backend native", SEL_ANCHOR, SEL_NEW),
]

if __name__ == "__main__":
    blocks = BLOCKS
    text = (find_sdk(FILE) / FILE).read_text(encoding="utf-8")
    if LEGACY_INC_NEW in text and INC_NEW not in text and "--status" not in sys.argv:
        # Upgrade the backend already installed by 0.3.0 without duplicating it.
        # Revert still means removing that backend, rather than adding a fast path.
        backend_block = ((FILE, "the native backend", INC_ANCHOR, LEGACY_INC_NEW)
                         if "--revert" in sys.argv else
                         (FILE, "upgrade native constant writes", LEGACY_INC_NEW, INC_NEW))
        blocks = [backend_block, BLOCKS[1]]
    sys.exit(run("ios_native_backend", blocks))
