#!/usr/bin/env python3
"""Differential tests using the actual generated loops and SDK PPC context.

Run on the Mac after codegen. Builds only a temporary standalone executable;
--benchmark omits sanitizers and times the two paths as a local microbenchmark.
"""
import argparse
import pathlib
import subprocess
import tempfile

import patch_game_constant_copies as patch


HARNESS = r'''
#include <rex/ppc/context.h>
#include <rex/ppc/intrinsics.h>
#include <array>
#include <cassert>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <random>
// Same memory operations as nfsmw_pch.h. Physical/MMIO ranges must fall back
// without dereferencing them in this small ordinary-memory fixture.
#define REX_RAW_ADDR(x) (base + uint32_t(x))
#define REX_LOAD_U32(x) __builtin_bswap32(*(volatile uint32_t*)REX_RAW_ADDR(x))
#define REX_STORE_U32(x,y) (*(volatile uint32_t*)REX_RAW_ADDR(x) = __builtin_bswap32(uint32_t(y)))
#include "@HEADER@"
@REFERENCES@

struct alignas(64) State {
  PPCContext ctx;
  PPCCRRegister cr;
  uint32_t ea;
  alignas(16) std::array<uint8_t, 16384> memory;
};
static std::mt19937 random_bits(82699100);
static void Put(State& s, uint32_t address, uint32_t value) {
  uint8_t* base = s.memory.data();
  REX_STORE_U32(address, value);
}
static State Fixture(bool pixel, uint32_t limit, uint32_t first, int overlap) {
  State s;
  auto* raw = reinterpret_cast<uint8_t*>(&s);
  for (size_t i = 0; i < sizeof(s); ++i) raw[i] = uint8_t(random_bits());
  s.ctx.r1.u32 = 1024;
  s.ctx.r10.u64 = (uint64_t(random_bits()) << 32) | first;
  const uint32_t source = 4096 + random_bits() % 16;
  const uint32_t dest = overlap == 100 ? 8192 + random_bits() % 16 :
      uint32_t(int(source & ~15u) + overlap * 16) + random_bits() % 16;
  s.ctx.r9.u64 = (uint64_t(random_bits()) << 32) | source;
  Put(s, 1024 + 80, 2048);
  Put(s, 1024 + 88, first);
  Put(s, 1024 + 236, source);
  Put(s, 1024 + 244, dest);
  Put(s, 1024 + 248, dest);
  Put(s, 2048 + (pixel ? 8 : 4), (random_bits() & ~(3u << 10)) | (limit << 10));
  return s;
}
template<bool Pixel> static bool Fast(State& s) {
  return nfsmw::constants::TryCopy<Pixel>(s.ctx, s.memory.data(), s.cr, s.ea);
}
template<bool Pixel> static void Reference(State& s) {
  if constexpr(Pixel) ReferencePixel(s.ctx, s.memory.data(), s.cr, s.ea);
  else ReferenceVertex(s.ctx, s.memory.data(), s.cr, s.ea);
}
template<bool Pixel> static void Equal(const State& original) {
  State reference = original, native = original;
  Reference<Pixel>(reference);
  assert(Fast<Pixel>(native));
  assert(std::memcmp(&reference.ctx, &native.ctx, sizeof(PPCContext)) == 0);
  assert(std::memcmp(&reference.cr, &native.cr, sizeof(PPCCRRegister)) == 0);
  assert(reference.ea == native.ea);
  assert(reference.memory == native.memory);
}
template<bool Pixel> static void Reject(const State& original) {
  State native = original;
  assert(!Fast<Pixel>(native));
  assert(std::memcmp(&original, &native, sizeof(State)) == 0);
}
template<bool Pixel> static void Tests(size_t& accepted, size_t& rejected) {
  for (uint32_t limit = 0; limit < 4; ++limit)
    for (uint32_t first = 0; first <= limit; ++first)
      for (int overlap : {100, -2, -1, 0, 1, 2})
        for (int repeat = 0; repeat < 200; ++repeat) {
          Equal<Pixel>(Fixture(Pixel, limit, first, overlap));
          ++accepted;
        }
  auto seed = Fixture(Pixel, 3, 0, 100);
  auto reject = [&](auto mutate) { State s = seed; mutate(s); Reject<Pixel>(s); ++rejected; };
  reject([](State& s) { Put(s, 1024 + 80, 1024 + 160); });
  reject([](State& s) { Put(s, 1024 + 80, 0x7F000000); });
  reject([](State& s) { Put(s, 1024 + 80, 0xFFFFFFFC); });
  reject([](State& s) { Put(s, 1024 + 80, 0xA0000000); });
  reject([](State& s) { Put(s, 1024 + 80, 0xC0000000); });
  reject([](State& s) { s.ctx.r1.u32 = 0xDFFFFF00; });
  reject([](State& s) { s.ctx.r1.u32 = 0xA0000000; });
  reject([](State& s) { s.ctx.r1.u32 = 0xC0000000; });
  reject([](State& s) { s.ctx.r10.u32 = 4; });
  reject([](State& s) { Put(s, 1024 + 88, 1); });
  for (uint32_t source : {1024u, 1104u, 0x7F000000u, 0x9FFFFFF0u, 0xA0000000u, 0xC0000000u, 0xDFFFFFF0u, 0xE0000000u, 0xFFFFFFF0u})
    reject([&](State& s) { if constexpr(Pixel) Put(s, 1024 + 236, source); else s.ctx.r9.u32 = source; });
  for (uint32_t dest : {1024u, 1104u, 2048u, 0x7F000000u, 0x9FFFFFF0u, 0xA0000000u, 0xC0000000u, 0xDFFFFFF0u, 0xE0000000u, 0xFFFFFFF0u})
    reject([&](State& s) { Put(s, 1024 + (Pixel ? 244 : 248), dest); });
}
template<bool Pixel, bool Native> __attribute__((noinline)) static uint64_t Bench(State& s, uint32_t count) {
  uint64_t sum = 0;
  for (uint32_t i = 0; i < count; ++i) {
    s.ctx.r10.u64 = 0;
    Put(s, 1024 + 88, 0);
    if constexpr(!Pixel) s.ctx.r9.u64 = 4096;
    if constexpr(Native) { if(!Fast<Pixel>(s)) Reference<Pixel>(s); }
    else Reference<Pixel>(s);
    sum += s.ea + s.ctx.r10.u64;
    asm volatile("" : : "r"(&s) : "memory");
  }
  return sum;
}
int main(int argc, char**) {
  size_t accepted = 0, rejected = 0;
  Tests<false>(accepted, rejected); Tests<true>(accepted, rejected);
  std::printf("PASS %zu differential copies (full context, CR, ea, memory); %zu unchanged fallbacks\n", accepted, rejected);
  if (argc > 1) {
    volatile uint64_t checksum = 0;
    for (uint32_t limit = 0; limit < 4; ++limit) {
      State s = Fixture(false, limit, 0, 100);
      for (int round = 0; round < 3; ++round) {
        auto a = std::chrono::steady_clock::now();
        checksum = Bench<false, false>(s, 1000000);
        auto b = std::chrono::steady_clock::now();
        checksum = Bench<false, true>(s, 1000000);
        auto c = std::chrono::steady_clock::now();
        std::printf("%u vectors: original %.2f ns, native %.2f ns\n", limit + 1,
          std::chrono::duration<double, std::nano>(b-a).count()/1000000,
          std::chrono::duration<double, std::nano>(c-b).count()/1000000);
      }
    }
    (void)checksum;
  }
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sdk", type=pathlib.Path, default=patch.ROOT.parent / "rexglue-sdk-ios")
    ap.add_argument("--benchmark", action="store_true")
    args = ap.parse_args()
    matches = [p for p in patch.GENERATED.glob("*.cpp")
               if "DEFINE_REX_FUNC(sub_82699100) {" in p.read_text()]
    assert len(matches) == 1
    original = patch.original_text(matches[0].read_text())
    transformed = patch.transform(original)
    assert patch.original_text(transformed) == original
    references = []
    for label, (pixel, _) in patch.SITES.items():
        a = original.index(f"loc_{label}:\n")
        end = f"\tif (!cr6.gt) goto loc_{label};\n"
        b = original.index(end, a) + len(end)
        name = "Pixel" if pixel else "Vertex"
        references.append(f"__attribute__((noinline)) void Reference{name}(PPCContext& ctx, uint8_t* base, PPCCRRegister& cr6, uint32_t& ea) {{\n{original[a:b]}\n}}")
    with tempfile.TemporaryDirectory(prefix="nfsmw-constant-copies-") as temp:
        temp = pathlib.Path(temp)
        # Exercise the real patch CLI, including rollback and failure atomicity.
        fixture = temp / "generated"
        fixture.mkdir()
        file = fixture / "sample.cpp"
        file.write_text(original)
        command = ["python3", str(pathlib.Path(patch.__file__)), "--dir", str(fixture)]
        for options in ([], [], ["--status"], ["--revert"], ["--revert"]):
            subprocess.run(command + options, check=True, capture_output=True)
        assert file.read_text() == original
        file.write_text(original.replace("loc_82699210:", "loc_changed:", 1))
        damaged = file.read_bytes()
        assert subprocess.run(command, capture_output=True).returncode != 0
        assert file.read_bytes() == damaged
        file.write_text(original.replace("loc_82699210:\n", "loc_82699210:\n\t// changed loop body\n", 1))
        damaged = file.read_bytes()
        assert subprocess.run(command, capture_output=True).returncode != 0
        assert file.read_bytes() == damaged
        file.write_text(transformed.replace("loc_82699378_native_done:;", "loc_changed:;", 1))
        damaged = file.read_bytes()
        assert subprocess.run(command, capture_output=True).returncode != 0
        assert file.read_bytes() == damaged
        print("PASS patch apply/idempotence/status/revert and atomic rejection of changed anchors/partial patches", flush=True)
        source = temp / "test.cpp"
        source.write_text(HARNESS.replace("@HEADER@", str(patch.ROOT / "ios/src/game_constant_copies.h"))
                          .replace("@REFERENCES@", "\n".join(references)))
        exe = temp / "test"
        flags = ["-O3"] if args.benchmark else ["-O1", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        subprocess.run(["xcrun", "clang++", "-std=c++23", "-Wno-asm-operand-widths", *flags,
                        "-I", str(args.sdk / "include"), "-I", str(args.sdk / "thirdparty/simde"),
                        str(source), "-o", str(exe)], check=True)
        subprocess.run([str(exe)] + (["benchmark"] if args.benchmark else []), check=True)


if __name__ == "__main__":
    main()
