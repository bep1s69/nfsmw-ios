#!/usr/bin/env python3
"""Check the actual generated rewrite and predicates; pass baseline .hlsl path.

Baseline: current translator output after rewrite_shadow_filter.py, before
rewrite_foliage_early_alpha.py. Generated game code stays in ignored storage.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from rewrite_foliage_early_alpha import BIT, MARKER, TARGET, rewrite

path = Path(sys.argv[1])
baseline = path.read_text()
candidate, count = rewrite(baseline, TARGET + ".hlsl")
assert count == 1
assert rewrite(baseline, "ps_other.hlsl") == (baseline, 0)
for invalid in (candidate, baseline.replace("r9.w * r8.w", "r9.w * r7.w"),
                baseline.replace("r2.www * r2.xyz", "r2.www + r2.xyz"),
                baseline.replace("alphaTestFunction == 5u", "alphaTestFunction == 4u")):
    try:
        rewrite(invalid, TARGET + ".hlsl")
    except ValueError:
        pass
    else:
        raise AssertionError("changed/already rewritten target accepted")

early = re.search(r"\t" + re.escape(MARKER) + r"\n.*?\n\t\}\n", candidate, re.S)
assert early
assert candidate.index(MARKER) < candidate.index("_s9 = tfetch2DShadow9")
assert "return" not in early.group() and "early_fragment_tests" not in candidate
restored = candidate[:early.start()] + candidate[early.end():]
restored = restored.replace(f"!{BIT} && (g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST)",
                            "g_SpecConstants() & SPEC_CONSTANT_ALPHA_TEST")
assert restored == baseline  # False path's original operations preserved exactly.
assert candidate.count("output.oC0.w =") == baseline.count("output.oC0.w =")

predicates = re.findall(r"bool alphaTestPass =\n(.*?);", candidate, re.S)
assert len(predicates) == 2
assert predicates[0].replace("nfsmwEarlyAlpha", "output.oC0.w") == predicates[1]
expr = re.search(r"float nfsmwEarlyAlpha = (.*?);", candidate)[1]
late_expr = re.search(r"output.oC0.w = (.*?);", candidate)[1]
assert expr == late_expr
renderer = (Path(__file__).resolve().parents[2] / "ios/src/native_renderer.mm").read_text()
selection = renderer[renderer.index("      const bool alpha_to_coverage ="):
                     renderer.index("      // The shadow caster (ps 4fbaecfb)")]
selection = selection.replace(
    "static const bool foliage_early_alpha = REXCVAR_GET(nfsmw_native_foliage_early_alpha);", "")
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_foliage_early_alpha, false,' in renderer
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_resource_list_cache, true,' in renderer

def cpp_predicate(text, variable):
    return text.replace(variable, "a").replace("g_AlphaThreshold", "t").replace(
        "any(isnan(float2(a, t)))", "(std::isnan(a) || std::isnan(t))")

harness = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <random>
#include <cstdio>
bool early(float a, float t, unsigned alphaTestFunction) { return @EARLY@; }
bool late(float a, float t, unsigned alphaTestFunction) { return @LATE@; }
bool reference(float a,float t,unsigned f) {
  switch(f) {
    case 0:return false; case 1:return a<t; case 2:return a==t;
    case 3:return a<=t; case 4:return a>t; case 5:return a!=t;
    case 6:return a>=t; case 7:return true;
  } return false;
}
float bits(uint32_t u) { float f; std::memcpy(&f,&u,4);return f; }
uint64_t checks=0;
uint32_t select(uint64_t key,unsigned control,unsigned samples,bool foliage_early_alpha) {
  struct { uint64_t ps_key; unsigned color_control; } d{key,control};
  struct { unsigned sample_count; } t{samples};
  @SELECTION@
  return alpha_spec;
}
void check(float diffuse,float vertex,float t) {
  // Unchanged operand values established by the fail-closed body guard.
  float a=diffuse*vertex, b=diffuse*vertex;
  for(unsigned f=0;f<8;++f) {
    assert(early(a,t,f)==late(b,t,f));
    assert(early(a,t,f)==reference(a,t,f));
    for(bool enabled:{false,true}) {
      assert((!enabled || early(a,t,f))==(!enabled || late(b,t,f)));
    }
    ++checks;
  }
}
int main() {
  for(uint64_t key:{0x684f4711f29b9f77ull,0x27d82ea0faa380a8ull,0x4fbaecfb8e7c4f40ull})
    for(unsigned control=0;control<256;++control)for(unsigned samples:{1u,2u,4u}) {
      auto off=select(key,control,samples,false),on=select(key,control,samples,true);
      assert(!(off & 0x2000u));assert((on & ~0x2000u)==off);
      assert(bool(on & 0x2000u)==(key==0x684f4711f29b9f77ull && (off & 2u)));
    }
  uint32_t edge[]={0,0x80000000,1,0x80000001,0x007fffff,0x00800000,
    0x3effffff,0x3f000000,0x3f000001,0x3f7fffff,0x3f800000,0x3f800001,
    0xbf800000,0x7f7fffff,0xff7fffff,0x7f800000,0xff800000,
    0x7fc00000,0xffc00001,0x7f800001};
  for(auto d:edge)for(auto v:edge)for(auto t:edge)check(bits(d),bits(v),bits(t));
  std::mt19937 rng(0x684f4711);
  for(unsigned i=0;i<200000;++i) {
    float d=bits(rng()),v=bits(rng()),t=bits(rng());
    check(d,v,t);check(d,v,d*v); // thresholds equal to output included.
  }
  std::printf("PASS: %llu predicate cases; all 8 comparisons, NaNs, infinities, signed zero, boundaries\n",
              (unsigned long long)checks);
}
'''.replace("@EARLY@", cpp_predicate(predicates[0], "nfsmwEarlyAlpha")).replace(
    "@LATE@", cpp_predicate(predicates[1], "output.oC0.w")).replace("@SELECTION@", selection)
with tempfile.TemporaryDirectory(prefix="nfsmw-foliage-alpha-") as temp:
    source = Path(temp) / "test.cpp"
    binary = Path(temp) / "test"
    source.write_text(harness)
    subprocess.run(["clang++", "-std=c++20", "-O2", "-fno-fast-math", "-ffp-contract=off",
                    "-fsanitize=address,undefined", str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: exact false-path reconstruction, unchanged final alpha/math, target-only and mutation guards; "
      "4608 production selection cases including alpha-to-coverage")
