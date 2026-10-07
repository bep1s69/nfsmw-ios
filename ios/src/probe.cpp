// NFSMW Recompiled - Vulkan probe on iOS (MoltenVK)
//
// The same as the Android probe (android/app/src/main/cpp/sonda_vulkan.cpp),
// plus what has to be known on iOS before playing:
//
//   - does MoltenVK load from the app, and which driver version is it?
//   - can a surface be created on a CAMetalLayer (the SDL window), and can
//     the GPU present to it?
//   - does the SDK accept this GPU for Xenos emulation?
//   - are there BC textures? Asked both of Vulkan (what MoltenVK exposes) and
//     of Metal (supportsBCTextureCompression). Without them the SDK
//     decompresses them with a compute shader (texture_cache.cpp): slower,
//     but it works.
//   - does the guest memory fit? rex::memory::Memory::Initialize() reserves
//     ~4.5 GB of contiguous address space and maps views of a shared memory
//     object into it. It is the first thing the game does, and the part that
//     depends most on the iOS sandbox. probe_memory.cpp repeats it step by
//     step, with errno.
//
// The report goes to the log, to Documents/vulkan_probe.txt and to the screen.
//
// C++, not Objective-C++: see probe_apple.h. The UIKit and Metal bits are
// there.

#include <fstream>
#include <memory>
#include <string>
#include <vector>

#include <SDL3/SDL.h>
#include <SDL3/SDL_metal.h>
#include <fmt/format.h>

#include <rex/cvar.h>
#include <rex/logging.h>
#include <rex/system/xmemory.h>
#include <rex/ui/vulkan/device.h>
#include <rex/ui/vulkan/instance.h>

#include "probe.h"
#include "probe_apple.h"
#include "probe_memory.h"

namespace {

using rex::ui::vulkan::VulkanDevice;
using rex::ui::vulkan::VulkanInstance;

std::string Version(uint32_t v) {
  return fmt::format("{}.{}.{}", VK_API_VERSION_MAJOR(v), VK_API_VERSION_MINOR(v),
                     VK_API_VERSION_PATCH(v));
}

class Report {
 public:
  void Line(const std::string& text) {
    REXLOG_INFO("[probe] {}", text);
    text_ += text;
    text_ += '\n';
  }
  void Save(const std::string& path) const {
    std::ofstream f(path, std::ios::binary | std::ios::trunc);
    f << text_;
  }
  const std::string& text() const { return text_; }

 private:
  std::string text_;
};

void ProbeGuestMemory(Report& report) {
  for (const auto& l : GuestMemoryDiagnostics()) {
    report.Line(l);
  }
  auto memory = std::make_unique<rex::memory::Memory>();
  if (memory->Initialize()) {
    report.Line("Guest memory, as the SDK sets it up (4.5 GB reserved, views mapped): OK");
  } else {
    report.Line("Guest memory, as the SDK sets it up: FAILS (see above, and the log). "
                "The game would not start");
  }
}

void ProbeDevice(Report& report, const VulkanInstance& instance, VkPhysicalDevice physical,
                 VkSurfaceKHR surface) {
  const auto& ifn = instance.functions();

  VkPhysicalDeviceProperties props{};
  ifn.vkGetPhysicalDeviceProperties(physical, &props);
  report.Line(fmt::format("GPU: {}  (vendor 0x{:04X}, device 0x{:08X})", props.deviceName,
                          props.vendorID, props.deviceID));
  report.Line(fmt::format("Device Vulkan: {}", Version(props.apiVersion)));

  if (props.apiVersion >= VK_MAKE_API_VERSION(0, 1, 2, 0) && ifn.vkGetPhysicalDeviceProperties2) {
    VkPhysicalDeviceDriverProperties driver{};
    driver.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_DRIVER_PROPERTIES;
    VkPhysicalDeviceProperties2 props2{};
    props2.sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_PROPERTIES_2;
    props2.pNext = &driver;
    ifn.vkGetPhysicalDeviceProperties2(physical, &props2);
    report.Line(fmt::format("Driver: {}  [{}]  {} {}",
                            driver.driverID == VK_DRIVER_ID_MOLTENVK ? "MoltenVK" : "other",
                            static_cast<int>(driver.driverID), driver.driverName,
                            driver.driverInfo));
  }

  // The surface: can queue 0 present to the CAMetalLayer?
  if (surface != VK_NULL_HANDLE) {
    VkBool32 presents = VK_FALSE;
    ifn.vkGetPhysicalDeviceSurfaceSupportKHR(physical, 0, surface, &presents);
    uint32_t formats = 0;
    ifn.vkGetPhysicalDeviceSurfaceFormatsKHR(physical, surface, &formats, nullptr);
    VkSurfaceCapabilitiesKHR caps{};
    ifn.vkGetPhysicalDeviceSurfaceCapabilitiesKHR(physical, surface, &caps);
    report.Line(fmt::format("CAMetalLayer surface: present={} formats={} size={}x{} "
                            "images {}-{}",
                            presents ? "yes" : "NO", formats, caps.currentExtent.width,
                            caps.currentExtent.height, caps.minImageCount, caps.maxImageCount));
  }

  const std::pair<VkFormat, const char*> bc_formats[] = {
      {VK_FORMAT_BC1_RGBA_UNORM_BLOCK, "BC1"},
      {VK_FORMAT_BC2_UNORM_BLOCK, "BC2"},
      {VK_FORMAT_BC3_UNORM_BLOCK, "BC3"},
      {VK_FORMAT_BC5_UNORM_BLOCK, "BC5"},
  };
  std::string bc;
  for (const auto& [format, name] : bc_formats) {
    VkFormatProperties fp{};
    ifn.vkGetPhysicalDeviceFormatProperties(physical, format, &fp);
    const bool ok = (fp.optimalTilingFeatures & VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) != 0;
    bc += fmt::format("{}={} ", name, ok ? "yes" : "NO");
  }
  report.Line("Compressed textures (Vulkan): " + bc);

  auto device = VulkanDevice::CreateIfSupported(&instance, physical,
                                                /*with_gpu_emulation=*/true,
                                                /*with_swapchain=*/true);
  if (!device) {
    report.Line("RESULT: the SDK does NOT accept this GPU for Xenos emulation (reason in the log)");
    return;
  }
  report.Line("RESULT: the SDK accepts this GPU for Xenos emulation");

  const auto& p = device->properties();
  const std::pair<bool, const char*> features[] = {
      {p.fragmentStoresAndAtomics, "fragmentStoresAndAtomics"},
      {p.vertexPipelineStoresAndAtomics, "vertexPipelineStoresAndAtomics"},
      {p.independentBlend, "independentBlend"},
      {p.geometryShader, "geometryShader"},
      {p.tessellationShader, "tessellationShader"},
      {p.sampleRateShading, "sampleRateShading"},
      {p.depthClamp, "depthClamp"},
      {p.fillModeNonSolid, "fillModeNonSolid"},
      {p.samplerAnisotropy, "samplerAnisotropy"},
      {p.shaderClipDistance, "shaderClipDistance"},
      {p.fullDrawIndexUint32, "fullDrawIndexUint32"},
      {p.fragmentShaderPixelInterlock, "fragmentShaderPixelInterlock"},
      {p.shaderDemoteToHelperInvocation, "shaderDemoteToHelperInvocation"},
      {p.dynamicRendering, "dynamicRendering"},
      // From the portability subset (MoltenVK).
      {p.constantAlphaColorBlendFactors, "constantAlphaColorBlendFactors"},
      {p.imageViewFormatReinterpretation, "imageViewFormatReinterpretation"},
      {p.imageViewFormatSwizzle, "imageViewFormatSwizzle"},
      {p.pointPolygons, "pointPolygons"},
      {p.separateStencilMaskRef, "separateStencilMaskRef"},
  };
  for (const auto& [ok, name] : features) {
    report.Line(fmt::format("  {:3} {}", ok ? "yes" : "NO", name));
  }
  report.Line(fmt::format("  maxPerStageDescriptorSamplers={} SampledImages={} StorageBuffers={}",
                          p.maxPerStageDescriptorSamplers, p.maxPerStageDescriptorSampledImages,
                          p.maxPerStageDescriptorStorageBuffers));
}

}  // namespace

int NfsmwVulkanProbe(const std::string& report_path) {
  Report report;
  report.Line("NFSMW Recompiled - Vulkan probe (iOS)");
  // Which build this is: the report lines rarely change between builds, so
  // without this an old install looks the same as a new one.
  report.Line("Build: " __DATE__ " " __TIME__);
  for (const auto& l : nfsmw::apple::SystemInfo()) {
    report.Line(l);
  }
  for (const auto& l : nfsmw::apple::MetalInfo()) {
    report.Line(l);
  }

  // The SDL window, which on iOS carries a view with a CAMetalLayer.
  SDL_Window* window = nullptr;
  SDL_MetalView metal_view = nullptr;
  if (SDL_InitSubSystem(SDL_INIT_VIDEO)) {
    window = SDL_CreateWindow("NFSMW", 0, 0,
                              SDL_WINDOW_FULLSCREEN | SDL_WINDOW_HIGH_PIXEL_DENSITY |
                                  SDL_WINDOW_METAL);
  }
  if (window) {
    metal_view = SDL_Metal_CreateView(window);
  }
  void* layer = metal_view ? SDL_Metal_GetLayer(metal_view) : nullptr;
  if (!layer) {
    report.Line(fmt::format("Window or CAMetalLayer: FAILS ({})", SDL_GetError()));
  }

  auto instance = VulkanInstance::Create(/*with_surface=*/true, /*try_enable_validation=*/false);
  if (!instance) {
    report.Line("RESULT: could not create a Vulkan instance: MoltenVK does not load (see log)");
  } else {
    report.Line(fmt::format("Vulkan instance: {}", Version(instance->api_version())));
    const auto& ifn = instance->functions();

    VkSurfaceKHR surface = VK_NULL_HANDLE;
    if (layer && instance->extensions().ext_EXT_metal_surface) {
      VkMetalSurfaceCreateInfoEXT info{};
      info.sType = VK_STRUCTURE_TYPE_METAL_SURFACE_CREATE_INFO_EXT;
      // In C++ CAMetalLayer is void (vulkan_metal.h).
      info.pLayer = static_cast<const CAMetalLayer*>(layer);
      const VkResult r = ifn.vkCreateMetalSurfaceEXT(instance->instance(), &info, nullptr,
                                                     &surface);
      report.Line(r == VK_SUCCESS ? "Vulkan surface on the CAMetalLayer: OK"
                                  : fmt::format("Vulkan surface: FAILS (VkResult {})",
                                                static_cast<int>(r)));
    } else if (!instance->extensions().ext_EXT_metal_surface) {
      report.Line("VK_EXT_metal_surface: missing");
    }

    std::vector<VkPhysicalDevice> physicals;
    instance->EnumeratePhysicalDevices(physicals);
    if (physicals.empty()) {
      report.Line("RESULT: MoltenVK reports no GPU");
    }
    for (VkPhysicalDevice physical : physicals) {
      ProbeDevice(report, *instance, physical, surface);
    }
    if (surface != VK_NULL_HANDLE) {
      ifn.vkDestroySurfaceKHR(instance->instance(), surface, nullptr);
    }
  }

  ProbeGuestMemory(report);

  report.Save(report_path);
  report.Line(fmt::format("Report saved to {}", report_path));
  rex::FlushLogging();

  if (window) {
    nfsmw::apple::ShowText(window, report.text());
    // iOS does not close apps: keep showing the report until the user leaves.
    for (;;) {
      SDL_Event e;
      while (SDL_WaitEvent(&e)) {
        if (e.type == SDL_EVENT_QUIT || e.type == SDL_EVENT_TERMINATING) {
          return 0;
        }
      }
    }
  }
  return 0;
}
