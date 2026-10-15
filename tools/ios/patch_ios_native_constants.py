#!/usr/bin/env python3
"""Native-only bulk constant writes; apply, --status, or --revert.

Only complete shader-constant ranges bypass WriteRegister. All other writes
retain its side effects. patch_ios_native_backend also includes these blocks
when creating a fresh backend, and upgrades the earlier backend in place.
"""
import sys
from patch_engine import run

FILE = "src/graphics/plugin_main.cpp"
NAMESPACE = 'namespace rex::graphics::native_backend {\n'
NAMESPACE_NEW = '''#include <rex/cvar.h>
#include <rex/memory/utils.h>

namespace rex::graphics::native_backend {

REXCVAR_DEFINE_BOOL(ios_native_bulk_constants, true, "GPU",
                    "Native backend: byte-swap shader constant ranges in bulk");
'''
METHOD = '''  bool SetupContext() override { return true; }
'''
METHOD_NEW = '''  // Only constant banks have no WriteRegister side effects in this backend.
  // The ring reader already splits wrapped ranges before calling this method.
  void WriteRegistersFromMem(uint32_t start_index, uint32_t* source, uint32_t count) override {
    if (!count) return;
    auto within = [&](uint32_t first, uint32_t last) {
      return start_index >= first && start_index <= last && count <= last - start_index + 1;
    };
    const bool constants = within(XE_GPU_REG_SHADER_CONSTANT_000_X, XE_GPU_REG_SHADER_CONSTANT_511_W) ||
                           within(XE_GPU_REG_SHADER_CONSTANT_FETCH_00_0, XE_GPU_REG_SHADER_CONSTANT_FETCH_31_5) ||
                           within(XE_GPU_REG_SHADER_CONSTANT_BOOL_000_031, XE_GPU_REG_SHADER_CONSTANT_LOOP_31);
    if (constants) {
      ++constant_ranges_;
      constant_words_ += count;
    }
    if (constants && count > 1 && REXCVAR_GET(ios_native_bulk_constants)) {
      memory::copy_and_swap(register_file_->values + start_index, source, count);
      ++bulk_ranges_;
      bulk_words_ += count;
      return;
    }
    ++fallback_ranges_;
    fallback_words_ += count;
    CommandProcessor::WriteRegistersFromMem(start_index, source, count);
  }

  bool SetupContext() override { return true; }
'''
SWAP = '''  void IssueSwap(uint32_t, uint32_t, uint32_t) override {
    const auto now = std::chrono::steady_clock::now();
'''
SWAP_NEW = '''  void IssueSwap(uint32_t, uint32_t, uint32_t) override {
    if (++constant_stats_frames_ == 300) {
      REXLOG_INFO("[native-constants] bulk {}; over {} frames: {:.1f} constant ranges / {:.1f} words per frame, "
                  "{:.1f} bulk ranges / {:.1f} words, {:.1f} fallback ranges / {:.1f} words",
                  REXCVAR_GET(ios_native_bulk_constants) ? "on" : "off", constant_stats_frames_,
                  double(constant_ranges_) / constant_stats_frames_, double(constant_words_) / constant_stats_frames_,
                  double(bulk_ranges_) / constant_stats_frames_, double(bulk_words_) / constant_stats_frames_,
                  double(fallback_ranges_) / constant_stats_frames_, double(fallback_words_) / constant_stats_frames_);
      constant_stats_frames_ = 0;
      constant_ranges_ = constant_words_ = bulk_ranges_ = bulk_words_ = fallback_ranges_ = fallback_words_ = 0;
    }
    const auto now = std::chrono::steady_clock::now();
'''
FIELDS = ''' private:
  std::unordered_map<uint64_t, std::unique_ptr<Shader>> shaders_;
'''
FIELDS_NEW = ''' private:
  uint32_t constant_stats_frames_ = 0;
  uint64_t constant_ranges_ = 0, constant_words_ = 0, bulk_ranges_ = 0, bulk_words_ = 0;
  uint64_t fallback_ranges_ = 0, fallback_words_ = 0;
  std::unordered_map<uint64_t, std::unique_ptr<Shader>> shaders_;
'''
BLOCKS = [
    (FILE, "native bulk constant switch", NAMESPACE, NAMESPACE_NEW),
    (FILE, "native constant range override", METHOD, METHOD_NEW),
    (FILE, "native constant range statistics", SWAP, SWAP_NEW),
    (FILE, "native constant range counters", FIELDS, FIELDS_NEW),
]


def augment_native_backend(text):
    for _, name, before, after in BLOCKS:
        if text.count(before) != 1:
            raise ValueError(f"Expected one {name} anchor in native backend template")
        text = text.replace(before, after)
    return text


if __name__ == "__main__":
    sys.exit(run("ios_native_constants", BLOCKS))
