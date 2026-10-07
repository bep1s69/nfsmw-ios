#!/usr/bin/env python3
"""
Pixel shaders without the "precise" (NoContraction) arithmetic, on iOS.

    python3 tools/ios/patch_ios_shader_contraction.py            apply
    python3 tools/ios/patch_ios_shader_contraction.py --status
    python3 tools/ios/patch_ios_shader_contraction.py --revert

Touches include/rex/graphics/pipeline/shader/spirv_builder.h,
src/graphics/pipeline/shader/spirv_builder.cpp and
src/graphics/pipeline/shader/spirv_translator.cpp.


WHAT A GPU REPLAY SHOWED
========================

Xcode's replay of a race frame on an iPad Pro M4 (Metal debugger, Counters):
fragment shading in a few passes is most of the frame. The single most
expensive encoder (11.5 %) is one draw; the four costliest pixel shaders take
about a third of the frame and use 110-174 registers per thread, with ALU use
around 15 % and the occupancy manager at its limit: too few threads in flight
to hide memory latency, not too much math.

The Metal source MoltenVK compiled (inside the .gputrace) explains much of it.
The translated pixel shaders are 1,600-4,000 lines, with hundreds of calls like

    [[clang::optnone]] T spvFMul(T l, T r)   // also spvFAdd, spvFSub, ...

SPIRV-Cross writes those wrappers for every SPIR-V operation decorated
NoContraction, so Metal cannot fuse a multiply and an add, and `optnone`
stops the compiler optimizing around each one.


WHY THE DECORATION, AND WHY NOT IN PIXEL SHADERS
================================================

The translator marks Xenos arithmetic NoContraction so that the same vertex
math gives bit-identical positions in every pass: the 360 draws geometry
several times (depth pre-pass, then colour with an EQUAL depth test) and a
fused multiply-add would change the last bit and make it flicker. That is a
vertex-shader concern. A last-bit difference in a pixel shader's colour is
invisible, so pixel shaders are translated without it.

The two SpirvBuilder helpers that add the decoration skip it when
ios_allow_contraction is set; the translator sets it for pixel shaders when
the cvar ios_pixel_shader_contraction is on (default). Vertex shaders are as
before. false gives back the exact previous translation, to compare.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

BH = "include/rex/graphics/pipeline/shader/spirv_builder.h"
BCPP = "src/graphics/pipeline/shader/spirv_builder.cpp"
TCPP = "src/graphics/pipeline/shader/spirv_translator.cpp"

BH_ANCHOR = '''  spv::Id createNoContractionUnaryOp(spv::Op op_code, spv::Id type_id, spv::Id operand);
'''
BH_NEW = '''  // LOCAL PATCH - iOS: when set, the createNoContraction* helpers do not add
  // the NoContraction decoration (pixel shaders; see
  // tools/ios/patch_ios_shader_contraction.py).
  bool ios_allow_contraction = false;

  spv::Id createNoContractionUnaryOp(spv::Op op_code, spv::Id type_id, spv::Id operand);
'''

UNARY_ANCHOR = '''  spv::Id result = createUnaryOp(op_code, type_id, operand);
  addDecoration(result, spv::DecorationNoContraction);
'''
UNARY_NEW = '''  spv::Id result = createUnaryOp(op_code, type_id, operand);
  if (!ios_allow_contraction) {  // LOCAL PATCH - iOS
    addDecoration(result, spv::DecorationNoContraction);
  }
'''

BINARY_ANCHOR = '''  spv::Id result = createBinOp(op_code, type_id, operand1, operand2);
  addDecoration(result, spv::DecorationNoContraction);
'''
BINARY_NEW = '''  spv::Id result = createBinOp(op_code, type_id, operand1, operand2);
  if (!ios_allow_contraction) {  // LOCAL PATCH - iOS
    addDecoration(result, spv::DecorationNoContraction);
  }
'''

CVAR_ANCHOR = '''#include <rex/string/buffer.h>

namespace rex::graphics {
'''
CVAR_NEW = '''#include <rex/string/buffer.h>

#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_shader_contraction.py).
#include <rex/cvar.h>
REXCVAR_DEFINE_BOOL(ios_pixel_shader_contraction, true, "GPU",
                    "iOS: translate pixel shaders without NoContraction (precise) arithmetic, "
                    "so Metal can fuse and optimise it. Vertex shaders keep it.");
#endif

namespace rex::graphics {
'''

START_ANCHOR = '''  builder_ = std::make_unique<SpirvBuilder>(features_.spirv_version, (kSpirvMagicToolId << 16) | 1,
                                            nullptr);
'''
START_NEW = '''  builder_ = std::make_unique<SpirvBuilder>(features_.spirv_version, (kSpirvMagicToolId << 16) | 1,
                                            nullptr);
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: pixel shaders without NoContraction.
  builder_->ios_allow_contraction =
      is_pixel_shader() && REXCVAR_GET(ios_pixel_shader_contraction);
#endif
'''

BLOCKS = [
    (BH, "the ios_allow_contraction flag", BH_ANCHOR, BH_NEW),
    (BCPP, "unary: decoration only without the flag", UNARY_ANCHOR, UNARY_NEW),
    (BCPP, "binary: decoration only without the flag", BINARY_ANCHOR, BINARY_NEW),
    (TCPP, "the ios_pixel_shader_contraction cvar", CVAR_ANCHOR, CVAR_NEW),
    (TCPP, "set the flag for pixel shaders", START_ANCHOR, START_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_shader_contraction", BLOCKS))
