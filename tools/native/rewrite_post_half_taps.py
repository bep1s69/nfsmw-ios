#!/usr/bin/env python3
"""Opt-in: the final post composite takes its 7 blur taps from a half-size scene.

ps_20710a9a2fef88e9 (the scene composite: scene, bloom, blur map, depth)
blends 7 offset taps of the scene (DIFFUSEMAP) into the sharp centre sample
by a depth-based amount. With specialization bit 14 (selected by
nfsmw_native_post_half_taps) the 7 taps read texture slot 15 instead, where
the renderer binds a 2x2-averaged half-size copy of the same scene image;
the centre sample and everything else are unchanged. Unset: the original.
Not identical: the blur is built from a slightly softer source.

The body digest is a fail-closed guard (the same baseline as the removed
dev80 rewrite). Game-derived source is never embedded here.

    rewrite_post_half_taps.py FILE.hlsl [...]   (in place; prints a count)
"""
import hashlib
from pathlib import Path
import re
import sys

TARGET = "ps_20710a9a2fef88e9"
BODY_SHA256 = "b8758215d6da7eb139d373af3a67762e822e45850f96bc3e113f0a4686aed95e"
MARKER = "// NFSMW post half taps: specialization bit 14"
HEAP = "\n#ifdef __air__\n\t\tg_Texture2DDescriptorHeap,\n\t\tg_SamplerDescriptorHeap,\n#endif\n\t\t"
INDICES = "DIFFUSEMAP_SAMPLER_Texture2DDescriptorIndex, DIFFUSEMAP_SAMPLER_SamplerDescriptorIndex, "
TAP = re.compile(r"\t(?P<dst>r\d+\.[xyzw]+) = tfetch2D\(" + re.escape(HEAP) + re.escape(INDICES) +
                 r"(?P<coord>r\d+\.[xyzw]{2}), float2\(0, 0\)\)\.(?P<sw>[xyzw]+);\n")
HALF = ("((g_SpecConstants() & 0x4000u) ? NFSMW_HALF_SAMPLER_Texture2DDescriptorIndex : "
        "DIFFUSEMAP_SAMPLER_Texture2DDescriptorIndex), ((g_SpecConstants() & 0x4000u) ? "
        "NFSMW_HALF_SAMPLER_SamplerDescriptorIndex : DIFFUSEMAP_SAMPLER_SamplerDescriptorIndex), ")
DEFINES = re.compile(r"^#define DIFFUSEMAP_SAMPLER_(?P<kind>Texture2D|Sampler)DescriptorIndex (?P<expr>.*\+ )(?P<off>0|256)\)(?P<tail>\)*)$",
                     re.M)


def rewrite(text, name):
    if Path(name).stem != TARGET:
        return text, 0
    if MARKER in text:
        raise ValueError("post half-tap rewrite already applied; regenerate baseline first")
    start = text.index("\n{\n#ifdef __air__\n\tPixelShaderOutput output")
    end = text.index("\n\treturn output;", start)
    body = text[start:end]
    if hashlib.sha256(body.encode()).hexdigest() != BODY_SHA256:
        raise ValueError("target shader body changed; re-audit the blur taps before rewriting")
    taps = [m for m in TAP.finditer(body) if m["coord"] != "r0.xy"]
    if len(taps) != 7 or len(list(TAP.finditer(body))) != 8:
        raise ValueError("expected 7 offset taps and one centre sample of the scene")
    out, last = [], 0
    for m in taps:
        out.append(body[last:m.start()])
        out.append(m.group().replace(INDICES, HALF, 1))
        last = m.end()
    out.append(body[last:])
    body = "".join(out)
    head = text[:start]
    defs = list(DEFINES.finditer(head))
    if len(defs) != 4:
        raise ValueError("expected two definitions each of the DIFFUSEMAP indices")
    for m in reversed(defs):
        off = "60" if m["kind"] == "Texture2D" else "316"
        line = (f"\n#define NFSMW_HALF_SAMPLER_{m['kind']}DescriptorIndex {m['expr']}{off}){m['tail']}")
        head = head[:m.end()] + line + head[m.end():]
    head = head + "\n" + MARKER
    return head + body + text[end:], 1


def main():
    for arg in sys.argv[1:]:
        path = Path(arg)
        text = path.read_text()
        new, count = rewrite(text, path.name)
        if count:
            path.write_text(new)
        print(f"{path}: {count} post half-tap block(s) made specializable")


if __name__ == "__main__":
    main()
