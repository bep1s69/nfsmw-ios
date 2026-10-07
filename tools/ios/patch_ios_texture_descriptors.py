#!/usr/bin/env python3
"""
A draw that uses the same textures and samplers as the previous one reuses its
descriptor sets instead of allocating and writing new ones.

    python3 tools/ios/patch_ios_texture_descriptors.py            apply
    python3 tools/ios/patch_ios_texture_descriptors.py --status
    python3 tools/ios/patch_ios_texture_descriptors.py --revert

Touches src/graphics/vulkan/command_processor.cpp and
include/rex/graphics/vulkan/command_processor.h.


WHAT A CPU PROFILE SHOWED
=========================

Instruments' Time Profiler in a police chase on an iPad Pro M4 (4,000-5,000
draws a frame, the GPU thread the limit): VulkanCommandProcessor::
UpdateBindings was ~15 % of the GPU thread, most of it vkUpdateDescriptorSets
inside MoltenVK. The reason is in the code:

    // TODO(Triang3l): Reuse texture and sampler bindings if not changed.
    current_graphics_descriptor_set_values_up_to_date_ &= ~(textures vertex | pixel);

Every draw allocated new texture/sampler descriptor sets and wrote all of
them, even with the very same textures as the draw before.


THE CHANGE
==========

That TODO, for the texture/sampler sets (vertex and pixel separately). A key
per stage: the frame, the descriptor set layout, the image view of each
texture binding (what the write would put in) and each sampler. If it equals
the key of the set written last for that stage, and that set is still the
current one, the set is kept: not invalidated, not allocated, not written,
not rebound. The sets are transient per frame (freed when the frame is done),
so the frame is part of the key. The image view is what the descriptor
points at; new data loaded into the same texture needs no new descriptor.

Cvar ios_reuse_texture_descriptors, default on; false gives back the
write-every-draw behaviour.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

H = "include/rex/graphics/vulkan/command_processor.h"
CPP = "src/graphics/vulkan/command_processor.cpp"

H_ANCHOR = '''  VkDescriptorSet current_graphics_descriptor_sets_[SpirvShaderTranslator::kDescriptorSetCount];
'''
H_NEW = '''  VkDescriptorSet current_graphics_descriptor_sets_[SpirvShaderTranslator::kDescriptorSetCount];
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the texture/sampler sets last written, per stage
  // (0 vertex, 1 pixel), and what they hold
  // (tools/ios/patch_ios_texture_descriptors.py).
  std::vector<uint64_t> ios_texture_key_[2];
  std::vector<uint64_t> ios_texture_key_new_[2];
  VkDescriptorSet ios_texture_set_[2] = {};
#endif
'''

CVAR_ANCHOR = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
'''
CVAR_NEW = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_texture_descriptors.py).
REXCVAR_DEFINE_BOOL(ios_reuse_texture_descriptors, true, "GPU",
                    "iOS: a draw with the same textures and samplers as the previous one "
                    "reuses its descriptor sets instead of writing new ones");
#endif
'''

KEEP_ANCHOR = '''  // TODO(Triang3l): Reuse texture and sampler bindings if not changed.
  current_graphics_descriptor_set_values_up_to_date_ &=
      ~((UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesVertex) |
        (UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesPixel));
'''
KEEP_NEW = '''  // TODO(Triang3l): Reuse texture and sampler bindings if not changed.
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: done (tools/ios/patch_ios_texture_descriptors.py).
  bool ios_keep[2] = {false, false};
  const bool ios_reuse = REXCVAR_GET(ios_reuse_texture_descriptors);
  if (ios_reuse) {
    auto handle = [](auto h) {
      uint64_t v = 0;
      std::memcpy(&v, &h, sizeof(h));
      return v;
    };
    for (uint32_t stage = 0; stage < 2; ++stage) {
      const bool pixel = stage != 0;
      const std::vector<VulkanShader::TextureBinding>* textures =
          pixel ? textures_pixel : &textures_vertex;
      const auto& samplers = pixel ? current_samplers_pixel_ : current_samplers_vertex_;
      std::vector<uint64_t>& key = ios_texture_key_new_[stage];
      key.clear();
      key.push_back(frame_current_);
      key.push_back(handle(
          pixel ? current_guest_graphics_pipeline_layout_->descriptor_set_layout_textures_pixel_ref()
                : current_guest_graphics_pipeline_layout_
                      ->descriptor_set_layout_textures_vertex_ref()));
      if (textures) {
        for (const VulkanShader::TextureBinding& binding : *textures) {
          key.push_back(handle(texture_cache_->GetActiveBindingOrNullImageView(
              binding.fetch_constant, binding.dimension, bool(binding.is_signed))));
        }
      }
      key.push_back(~uint64_t(0));
      for (const auto& sampler : samplers) {
        key.push_back(handle(sampler.second));
      }
      const uint32_t set_index = pixel ? SpirvShaderTranslator::kDescriptorSetTexturesPixel
                                       : SpirvShaderTranslator::kDescriptorSetTexturesVertex;
      ios_keep[stage] = ios_texture_set_[stage] != VK_NULL_HANDLE &&
                        current_graphics_descriptor_sets_[set_index] == ios_texture_set_[stage] &&
                        key == ios_texture_key_[stage];
    }
  }
  {
    uint32_t ios_stale = 0;
    if (!ios_keep[0]) {
      ios_stale |= UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesVertex;
    }
    if (!ios_keep[1]) {
      ios_stale |= UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesPixel;
    }
    current_graphics_descriptor_set_values_up_to_date_ &= ~ios_stale;
  }
#else
  current_graphics_descriptor_set_values_up_to_date_ &=
      ~((UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesVertex) |
        (UINT32_C(1) << SpirvShaderTranslator::kDescriptorSetTexturesPixel));
#endif
'''

STORE_ANCHOR = '''  current_graphics_descriptor_set_values_up_to_date_ |= write_descriptor_set_bits;
'''
STORE_NEW = '''  current_graphics_descriptor_set_values_up_to_date_ |= write_descriptor_set_bits;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: remember what the texture sets just written hold.
  if (ios_reuse) {
    for (uint32_t stage = 0; stage < 2; ++stage) {
      const uint32_t set_index = stage ? SpirvShaderTranslator::kDescriptorSetTexturesPixel
                                       : SpirvShaderTranslator::kDescriptorSetTexturesVertex;
      if (write_descriptor_set_bits & (UINT32_C(1) << set_index)) {
        ios_texture_key_[stage].swap(ios_texture_key_new_[stage]);
        ios_texture_set_[stage] = current_graphics_descriptor_sets_[set_index];
      }
    }
  }
#endif
'''

BLOCKS = [
    (H, "the last texture sets and their keys", H_ANCHOR, H_NEW),
    (CPP, "the ios_reuse_texture_descriptors cvar", CVAR_ANCHOR, CVAR_NEW),
    (CPP, "keep the texture sets when nothing changed", KEEP_ANCHOR, KEEP_NEW),
    (CPP, "remember the texture sets written", STORE_ANCHOR, STORE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_texture_descriptors", BLOCKS))
