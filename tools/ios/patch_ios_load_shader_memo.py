#!/usr/bin/env python3
"""
The native command processor's LoadShader remembers the microcode it last saw
at each guest address and skips re-hashing it when the bytes are unchanged
(memcmp instead of a byte-serial FNV hash).

    python3 tools/ios/patch_ios_load_shader_memo.py            apply
    python3 tools/ios/patch_ios_load_shader_memo.py --status
    python3 tools/ios/patch_ios_load_shader_memo.py --revert

Touches src/graphics/plugin_main.cpp.


WHY
===

November 5 Time Profiles (dev66, dev73; docs/TECHNICAL.md): LoadShader was
~5.4 % of the GPU-commands thread: every shader load hashed the whole
microcode with a multiply per dword. The same shaders are loaded from the
same addresses frame after frame. A memcmp against the remembered copy is
several times faster and exact (no hash collision possible); a changed or new
shader takes the original path. Shaders are only freed at ShutdownContext,
which also clears the memo.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/graphics/plugin_main.cpp"

LOAD_ANCHOR = '''                     uint32_t dword_count) override {
    uint64_t hash = 0xCBF29CE484222325ull;
    for (uint32_t i = 0; i < dword_count; ++i) hash = (hash ^ host_address[i]) * 0x100000001B3ull;
    hash ^= uint64_t(shader_type) << 63;
    auto it = shaders_.find(hash);
    if (it != shaders_.end()) return it->second.get();
    auto shader = std::make_unique<Shader>(shader_type, hash, host_address, dword_count);
    Shader* raw = shader.get();
    shaders_.emplace(hash, std::move(shader));
    return raw;
  }'''
LOAD_NEW = '''                     uint32_t dword_count) override {
    // LOCAL PATCH - iOS (tools/ios/patch_ios_load_shader_memo.py): the same
    // microcode at the same address returns its shader after a memcmp.
    const uint64_t memo_key = uint64_t(uintptr_t(host_address)) ^ (uint64_t(dword_count) << 40) ^
                              (uint64_t(shader_type) << 63);
    auto memo = ios_shader_memo_.find(memo_key);
    if (memo != ios_shader_memo_.end() && memo->second.words.size() == dword_count &&
        std::memcmp(memo->second.words.data(), host_address, size_t(dword_count) * 4) == 0) {
      return memo->second.shader;
    }
    uint64_t hash = 0xCBF29CE484222325ull;
    for (uint32_t i = 0; i < dword_count; ++i) hash = (hash ^ host_address[i]) * 0x100000001B3ull;
    hash ^= uint64_t(shader_type) << 63;
    Shader* raw = nullptr;
    auto it = shaders_.find(hash);
    if (it != shaders_.end()) {
      raw = it->second.get();
    } else {
      auto shader = std::make_unique<Shader>(shader_type, hash, host_address, dword_count);
      raw = shader.get();
      shaders_.emplace(hash, std::move(shader));
    }
    if (ios_shader_memo_.size() >= 8192) ios_shader_memo_.clear();  // bounded
    auto& entry = ios_shader_memo_[memo_key];
    entry.words.assign(host_address, host_address + dword_count);
    entry.shader = raw;
    return raw;
  }'''

MEMBER_ANCHOR = '''  std::unordered_map<uint64_t, std::unique_ptr<Shader>> shaders_;'''
MEMBER_NEW = MEMBER_ANCHOR + '''
  // LOCAL PATCH - iOS (tools/ios/patch_ios_load_shader_memo.py)
  struct IosShaderMemo {
    std::vector<uint32_t> words;
    Shader* shader = nullptr;
  };
  std::unordered_map<uint64_t, IosShaderMemo> ios_shader_memo_;'''

CLEAR_ANCHOR = '''  void ShutdownContext() override { shaders_.clear(); }'''
CLEAR_NEW = '''  void ShutdownContext() override {
    ios_shader_memo_.clear();  // LOCAL PATCH - iOS (tools/ios/patch_ios_load_shader_memo.py)
    shaders_.clear();
  }'''

INC_ANCHOR = "#include <unordered_map>\n"
INC_NEW = INC_ANCHOR + "#include <cstring>  // LOCAL PATCH - iOS (patch_ios_load_shader_memo.py)\n#include <vector>\n"

BLOCKS = [
    (FILE, "includes", INC_ANCHOR, INC_NEW),
    (FILE, "LoadShader memo", LOAD_ANCHOR, LOAD_NEW),
    (FILE, "memo member", MEMBER_ANCHOR, MEMBER_NEW),
    (FILE, "memo cleared with the shaders", CLEAR_ANCHOR, CLEAR_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_load_shader_memo", BLOCKS))
