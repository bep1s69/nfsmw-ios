#!/usr/bin/env python3
"""Opt-in: the final post composite skips its blur taps where they add nothing.

ps_20710a9a2fef88e9 (the scene composite: scene, bloom, blur map, depth)
blends 7 offset taps of the scene into the sharp centre sample by an amount
it computes from the depth and the blur map:
    colour = sharp + amount * (blurred - sharp)
Where that amount is exactly 0 the taps change nothing (finite RGBA samples
times 0, plus sharp, is sharp). Specialization bit 14 (selected by
nfsmw_native_post_blur_skip) computes the amount first, with the same
operations in the same order as the shader does later, and fetches the 7
taps only where it is not 0 (a NaN amount keeps them). Unset: the original
code (the taps always fetched). The registers the taps write start at 0.

The body digest is a fail-closed guard: if the translation changes, re-audit
the amount's dataflow before updating it. Game-derived source is never
embedded here.

    rewrite_post_blur_skip.py FILE.hlsl [...]   (in place; prints a count)
"""
import hashlib
from pathlib import Path
import re
import sys

TARGET = "ps_20710a9a2fef88e9"
BODY_SHA256 = "b8758215d6da7eb139d373af3a67762e822e45850f96bc3e113f0a4686aed95e"
MARKER = "// NFSMW post blur skip: specialization bit 14"
BIT = "(g_SpecConstants() & 0x4000u)"
HEAP = "\n#ifdef __air__\n\t\tg_Texture2DDescriptorHeap,\n\t\tg_SamplerDescriptorHeap,\n#endif\n\t\t"
ANCHOR = "\tps = max(r0.x, r0.x);\n\tr11.x = ps;\n"
TAP = re.compile(r"\t(?P<dst>r\d+\.[xyzw]+) = tfetch2D\(" + re.escape(HEAP) +
                 r"DIFFUSEMAP_SAMPLER_Texture2DDescriptorIndex, DIFFUSEMAP_SAMPLER_SamplerDescriptorIndex, "
                 r"(?P<coord>r\d+\.[xyzw]{2}), float2\(0, 0\)\)\.(?P<sw>[xyzw]+);\n")
# The amount as the shader computes it (each line checked to be present).
AMOUNT_LINES = [
    "\tr2.xyzw = tfetch2D(" + HEAP + "MISCMAP2_SAMPLER_Texture2DDescriptorIndex, MISCMAP2_SAMPLER_SamplerDescriptorIndex, r11.xy, float2(0, 0)).xyzw;\n",
    "\tr0.z = tfetch2D(" + HEAP + "HEIGHTMAP_SAMPLER_Texture2DDescriptorIndex, HEIGHTMAP_SAMPLER_SamplerDescriptorIndex, r0.xy, float2(0, 0)).x;\n",
    "\tr1.x = (float)((r2.x + BlurParams.x));\n",
    "\tps = max(r2.w, r2.w);\n\tr0.x = ps;\n",
    "\tps = BlurParams.y * r0.x;\n\tr0.x = ps;\n",
    "\tps = c254.y - r0.z;\n\tr0.y = ps;\n",
    "\tps = clamp(rcp(r0.y), -FLT_MAX, FLT_MAX);\n\tr0.y = ps;\n",
    "\tr0.y = (float)((saturate(-r0.y * c254.x + c255.y)));\n",
    "\tr0.x = (float)((saturate(r1.x * r0.y + r0.x)));\n",
    "\tr5.xyz = (float3)((r5.xyz * r0.xxx + r3.xyz));\n",
]
EARLY = (
    "\t" + MARKER + "\n"
    "\tbool nfsmwBlur = true;\n"
    "\tif " + BIT + "\n"
    "\t{\n"
    "\t\tfloat4 nfsmwMap = tfetch2D(" + HEAP.replace("\n\t\t", "\n\t\t\t") +
    "MISCMAP2_SAMPLER_Texture2DDescriptorIndex, MISCMAP2_SAMPLER_SamplerDescriptorIndex, r11.xy, float2(0, 0)).xyzw;\n"
    "\t\tfloat nfsmwDepth = tfetch2D(" + HEAP.replace("\n\t\t", "\n\t\t\t") +
    "HEIGHTMAP_SAMPLER_Texture2DDescriptorIndex, HEIGHTMAP_SAMPLER_SamplerDescriptorIndex, r0.xy, float2(0, 0)).x;\n"
    "\t\tfloat nfsmwBias = (float)((nfsmwMap.x + BlurParams.x));\n"
    "\t\tfloat nfsmwBase = max(nfsmwMap.w, nfsmwMap.w);\n"
    "\t\tnfsmwBase = BlurParams.y * nfsmwBase;\n"
    "\t\tfloat nfsmwNear = c254.y - nfsmwDepth;\n"
    "\t\tnfsmwNear = clamp(rcp(nfsmwNear), -FLT_MAX, FLT_MAX);\n"
    "\t\tnfsmwNear = (float)((saturate(-nfsmwNear * c254.x + c255.y)));\n"
    "\t\tfloat nfsmwAmount = (float)((saturate(nfsmwBias * nfsmwNear + nfsmwBase)));\n"
    "\t\tnfsmwBlur = !(nfsmwAmount == 0.0);\n"
    "\t}\n"
)


def rewrite(text, name):
    if Path(name).stem != TARGET:
        return text, 0
    if MARKER in text:
        raise ValueError("post blur rewrite already applied; regenerate baseline first")
    start = text.index("\n{\n#ifdef __air__\n\tPixelShaderOutput output")
    end = text.index("\n\treturn output;", start)
    body = text[start:end]
    if hashlib.sha256(body.encode()).hexdigest() != BODY_SHA256:
        raise ValueError("target shader body changed; re-audit the blur amount dataflow before rewriting")
    for line in AMOUNT_LINES:
        if body.count(line) != 1:
            raise ValueError("expected blur amount statement missing: " + line.strip()[:60])
    if body.count(ANCHOR) != 1:
        raise ValueError("expected texture coordinate setup missing")
    taps = [m for m in TAP.finditer(body) if m["coord"] != "r0.xy"]
    if len(taps) != 7 or len(list(TAP.finditer(body))) != 8:
        raise ValueError("expected 7 offset taps and one centre sample of the scene")
    at = body.index(ANCHOR) + len(ANCHOR)
    if not all(m.start() > at for m in taps):
        raise ValueError("a tap precedes the coordinate setup")
    out = []
    last = 0
    for m in taps:
        out.append(body[last:m.start()])
        out.append("\tif (nfsmwBlur)\n\t{\n" + m.group().replace("\n\t", "\n\t\t").replace("\t" + m["dst"], "\t\t" + m["dst"], 1) + "\t}\n")
        last = m.end()
    out.append(body[last:])
    body = "".join(out)
    body = body.replace(ANCHOR, ANCHOR + EARLY, 1)
    return text[:start] + body + text[end:], 1


def main():
    for arg in sys.argv[1:]:
        path = Path(arg)
        text = path.read_text()
        new, count = rewrite(text, path.name)
        if count:
            path.write_text(new)
        print(f"{path}: {count} post blur block(s) made specializable")


if __name__ == "__main__":
    main()
