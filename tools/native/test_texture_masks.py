#!/usr/bin/env python3
"""Validate texture metadata and compile the renderer's actual slot loop.

Runs standalone with ASan/UBSan; optionally checks a generated shader corpus
via --shaders PATH. No iOS device or Metal compiler is needed for these tests.
"""
import argparse
import pathlib
import re
import subprocess
import tempfile

import texture_masks as masks

ROOT = pathlib.Path(__file__).resolve().parents[2]


def metadata_tests():
    marker = "// NFSMW_TEXTURE_MASK_V1 2\n"
    assert masks.mask_for(marker) == (2, True)
    assert masks.mask_for("// NFSMW_TEXTURE_MASK_V1 0\n") == (0, True)
    for kind, offset in masks.KIND_OFFSETS.items():
        definition = f"#define Diffuse_Texture{kind}DescriptorIndex (*(uint*)(g_PushConstants.SharedConstants + {offset + 12}))\n"
        assert masks.mask_for(marker + definition) == (10, True)
    for text in ["", marker + marker, "// NFSMW_TEXTURE_MASK_V1 zzzz\n",
                 "// NFSMW_TEXTURE_MASK_V1 10000\n",
                 marker + "use(Unknown_Texture2DDescriptorIndex);\n",
                 marker + "#define X_TextureFooDescriptorIndex SharedConstants + 0\n",
                 marker + "#define X_Texture2DDescriptorIndex SharedConstants + offset\n",
                 marker + "#define X_Texture2DDescriptorIndex SharedConstants + 65\n"]:
        assert masks.mask_for(text) == (0xFFFF, False)
    assert masks.mask_for("// NFSMW_TEXTURE_MASK_V1 8000\n") == (0x8000, True)
    print("PASS metadata empty/declared masks, all texture dimensions, slot 15 and conservative fallbacks", flush=True)


HARNESS = r'''
#include "@HEADER@"
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <iomanip>
#include <random>
#include <vector>
struct Frame {
  uint32_t slot_fetch[16][6] = {};
  int slot_texture[16] = {};
  bool slot_valid[16] = {};
  std::vector<std::array<uint32_t, 6>> textures;
  size_t lookups = 0;
};
struct Draw { int textures[16]; };
constexpr int kFetchBase = 0;
int TextureOf(Frame& frame, const uint32_t* fetch) {
  ++frame.lookups;
  std::array<uint32_t, 6> texture;
  std::memcpy(texture.data(), fetch, 24);
  frame.textures.push_back(texture);
  return int(frame.textures.size() - 1);
}
Draw Record(Frame& frame, const uint32_t* regs, uint16_t texture_mask) {
  Draw d;
@SLOT_LOOP@
  return d;
}
std::string Line(const char* stage, uint64_t key, uint16_t mask) {
  std::ostringstream out;
  out << stage << '_' << std::hex << std::setw(16) << std::setfill('0') << key
      << ' ' << std::setw(8) << uint32_t(mask) << '\n';
  return out.str();
}
int main() {
  nfsmw::TextureMasks masks;
  assert(!masks.ForDraw(0,0));
  std::mt19937 rng(10113);
  std::string text = "nfsmw-texture-masks-v1\n";
  std::array<uint16_t, 100> vertex, pixel;
  for(uint64_t i=0;i<100;++i) {
    vertex[i]=uint16_t(rng()); pixel[i]=uint16_t(rng());
    text += Line("vs", i, vertex[i]) + Line("ps", i, pixel[i]);
  }
  assert(masks.Load(text));
  for(uint64_t i=0;i<100;++i) for(uint64_t j=0;j<100;++j)
    assert(masks.ForDraw(i,j) == uint16_t(vertex[i] | pixel[j]));
  assert(!masks.ForDraw(999,0));
  masks.SetInternal(false, 999, 0);
  assert(masks.ForDraw(999,0) == pixel[0]); // invalidates cached miss
  masks.SetInternal(true, 0, 7);
  assert(masks.ForDraw(999,0) == 7); // invalidates cached hit
  assert(masks.Load(text));
  assert(!masks.ForDraw(999,0)); // reload invalidates both caches
  for(const std::string& invalid : {
      std::string{}, std::string("wrong-version\n"),
      std::string("nfsmw-texture-masks-v1\n"),
      std::string("nfsmw-texture-masks-v1\nvs_0000000000000001 00010000\n"),
      std::string("nfsmw-texture-masks-v1\nxx_0000000000000001 00000000\n"),
      std::string("nfsmw-texture-masks-v1\nvs_000000000000000z 00000000\n"),
      text + Line("vs", 0, 0), text + "truncated\n",
      text + "ps_0000000000000100 00000000 extra\n"}) {
    assert(!masks.Load(invalid));
    assert(masks.Size() == 0 && !masks.ForDraw(0,0));
    assert(masks.Load(text));
  }
  std::puts("PASS 10000 stage-union cases, known-zero/unknown distinction, cache invalidation and atomic parser fallback");
  Frame full, pruned;
  uint32_t regs[96] = {};
  for(int draw=0;draw<20000;++draw) {
    if(draw%1000==0) { full = {}; pruned = {}; }
    if(draw%127==0) { // same invalidation used after resolves
      std::fill(std::begin(full.slot_valid), std::end(full.slot_valid), false);
      std::fill(std::begin(pruned.slot_valid), std::end(pruned.slot_valid), false);
    }
    for(int change=0;change<3;++change) regs[rng()%96]=rng();
    uint16_t mask = draw%3 ? uint16_t(1u << (rng()%16)) : uint16_t(rng());
    if(draw%51==0) mask=0;
    if(draw%53==0) mask=0xFFFF;
    bool was_valid[16]; uint32_t old_fetch[16][6]; int old_texture[16];
    std::memcpy(was_valid, pruned.slot_valid, sizeof(was_valid));
    std::memcpy(old_fetch, pruned.slot_fetch, sizeof(old_fetch));
    std::memcpy(old_texture, pruned.slot_texture, sizeof(old_texture));
    auto expected=Record(full,regs,0xFFFF), actual=Record(pruned,regs,mask);
    for(int slot=0;slot<16;++slot) {
      if(mask & (1u<<slot))
        assert(full.textures[expected.textures[slot]] == pruned.textures[actual.textures[slot]]);
      else {
        assert(actual.textures[slot] == -1);
        assert(pruned.slot_valid[slot] == was_valid[slot]);
        assert(pruned.slot_texture[slot] == old_texture[slot]);
        assert(std::memcmp(pruned.slot_fetch[slot], old_fetch[slot], 24) == 0);
      }
    }
  }
  std::puts("PASS 20000 actual renderer-loop draws: changing bindings while unused, later reuse, resolves, empty/all-slot masks");
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shaders", type=pathlib.Path)
    args = ap.parse_args()
    metadata_tests()
    if args.shaders:
        count = 0
        for path in args.shaders.glob("*.hlsl"):
            if not re.fullmatch(r"[vp]s_[0-9a-fA-F]{16}", path.stem):
                continue
            text = path.read_text()
            mask, known = masks.mask_for(text)
            assert known, path
            raw = int(masks.MARKER.findall(text)[0], 16)
            assert mask & raw == raw
            count += 1
        assert count
        print(f"PASS {count} generated shader interfaces include every translator-referenced slot", flush=True)
    source = (ROOT / "ios/src/native_renderer.mm").read_text()
    start = source.index("  for (int s = 0; s < 16; ++s) {", source.index("// A slot whose fetch constant"))
    end = source.index("  if (timed_draw)", start)
    loop = source[start:end]
    with tempfile.TemporaryDirectory(prefix="nfsmw-texture-mask-tests-") as temp:
        temp = pathlib.Path(temp)
        cpp = temp / "test.cpp"
        cpp.write_text(HARNESS.replace("@HEADER@", str(ROOT / "ios/src/native_texture_masks.h"))
                       .replace("@SLOT_LOOP@", loop))
        exe = temp / "test"
        subprocess.run(["xcrun", "clang++", "-std=c++20", "-O1", "-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer", str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
