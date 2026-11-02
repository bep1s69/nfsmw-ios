#!/usr/bin/env python3
"""Check the NFS shared ABI and production clear/dedup/upload prefix behavior."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / "ios/src/native_renderer.mm").read_text()
common = (ROOT / "tools/xenosrecomp/shader_common.h").read_text()
abi = common.split("#else\n#define g_Booleans (*(reinterpret_cast<device uint*>(g_PushConstants.SharedConstants + 320)))", 1)[1].split("#endif", 1)[0]
width = {"uint": 4, "bool": 1, "float": 4, "float2": 8, "float4": 16}
readers = [(kind, int(offset)) for kind, offset in re.findall(
    r"reinterpret_cast<device (\w+)\*>\(g_PushConstants.SharedConstants \+ (\d+)\)", abi)]
assert readers and max(offset + width[kind] for kind, offset in readers) == 384
translator = (ROOT / "tools/xenosrecomp/shader_recompiler.cpp").read_text()
assert "#else\nstatic constexpr uint32_t TEXTURE_DESCRIPTOR_COUNT = 16;" in translator
assert "return uint32_t(dimension) * TEXTURE_DESCRIPTOR_COUNT + slot;" in translator
assert max(map(int, re.findall(r"shared_\[(\d+)\]", source))) < 96  # internal movie shader
assert max(map(int, re.findall(r"shared\[(\d+)\] =", source))) < 96
start = source.index("      uint32_t shared[256];")
clear = source[start:source.index("      if (motion_pass", start)]
start = source.index("      if (!have_last_shared || std::memcmp(last_shared, shared,")
upload = source[start:source.index("      const size_t shared_at", start)]

HARNESS = r'''
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <random>
#include <vector>
void Prepare(uint32_t* out, const uint32_t* prefix, size_t shared_bytes) {
  @CLEAR@
  // Supply all ABI words, including flags, reserved words, jitter and raw
  // NaN/-0 bit patterns. No float conversion may alter the payload.
  std::copy(prefix,prefix+96,shared);
  std::memcpy(out,shared,shared_bytes);
}
struct Stream {
  uint32_t last_shared[256];
  size_t last_shared_at=0;
  bool have_last_shared=false;
  std::vector<uint8_t> bytes;
  std::vector<size_t> offsets;
  void Emit(const uint32_t* shared,size_t shared_bytes) {
    constexpr int kSharedUpload=0;
    auto put=[&](const void* p,size_t n,int) {
      const size_t at=(bytes.size()+255)&~size_t(255);
      assert(at%256==0); bytes.resize(at+n);
      std::memcpy(bytes.data()+at,p,n);offsets.push_back(at);return at;
    };
    @UPLOAD@
  }
};
int main() {
  std::mt19937 random(0x4e46534d);
  Stream legacy,compact;
  std::array<uint32_t,96> prefix{};
  size_t expected=0;
  for(unsigned draw=0;draw<5000;++draw) {
    bool changed=draw==0 || draw%7!=0;
    if(changed) { prefix[draw%96]^=1u<<(draw%32);++expected; }
    std::array<uint32_t,256> a,b;
    a.fill(0xaabbccdd);b.fill(random()); // compact tail is deliberately poison
    Prepare(a.data(),prefix.data(),1024);Prepare(b.data(),prefix.data(),384);
    assert(std::memcmp(a.data(),b.data(),384)==0);
    for(size_t i=96;i<a.size();++i)assert(a[i]==0);
    legacy.Emit(a.data(),1024);compact.Emit(b.data(),384);
    assert(legacy.offsets.size()==expected && compact.offsets.size()==expected);
    assert(std::memcmp(legacy.bytes.data()+legacy.last_shared_at,
                       compact.bytes.data()+compact.last_shared_at,384)==0);
    assert(std::memcmp(prefix.data(),compact.bytes.data()+compact.last_shared_at,384)==0);
  }
  assert(compact.bytes.size()<legacy.bytes.size());
  // Explicit edge bit patterns in the final flags and float fields.
  prefix[86]=0x80000000;prefix[87]=0x7fc12345;
  prefix[93]=0x7fa54321;prefix[95]=0xffffffff;
  std::array<uint32_t,256> edge{};Prepare(edge.data(),prefix.data(),384);
  compact.Emit(edge.data(),384);
  assert(std::memcmp(prefix.data(),compact.bytes.data()+compact.last_shared_at,384)==0);
}
'''
with tempfile.TemporaryDirectory(prefix="nfsmw-compact-shared-") as folder:
    path = Path(folder) / "test.cpp"
    binary = Path(folder) / "test"
    path.write_text(HARNESS.replace("@CLEAR@", clear).replace("@UPLOAD@", upload))
    subprocess.run(["clang++", "-std=c++23", "-O1", "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer", str(path), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: NFS ABI bounds, production prefix initialization/dedup/upload, 5000 draws, poisoned tail, alignment and raw float bits (ASan/UBSan)")
