#!/usr/bin/env python3
"""NFSMW's soft shadows in the translated shaders: 9 fetches -> 1 call.

18 of the game's pixel shaders (19 blocks) filter the shadow map the same way:
9 linear fetches of its depth at -0.5, 0 and +0.5 texels in x and y around
one coordinate (each in its own predicated block in XenosRecomp's output),
then compare each with the receiver's depth. This replaces the 9 fetches
with tfetch2DShadow9 (shader_common.h: 4 gathers and the bilinear weights
in the shader), whose 9 results go to the same registers. The comparisons
and everything else are untouched.

    rewrite_shadow_filter.py FILE.hlsl [...]   (in place; prints a count)

A block is rewritten only when the 9 fetches use one coordinate, cover the
3x3 offsets once each, write 9 different components none of which is the
coordinate's register, and nothing but braces, "if (p0)"/"if (!p0)" and
comments stands between them.
"""
import re
import sys

FETCH = re.compile(
    r"(?P<dst>r\d+\.[xyzw]) = tfetch2D\(\s*#ifdef __air__\s*g_Texture2DDescriptorHeap,\s*"
    r"g_SamplerDescriptorHeap,\s*#endif\s*SHADOWMAP_SAMPLER_Texture2DDescriptorIndex, "
    r"SHADOWMAP_SAMPLER_SamplerDescriptorIndex, (?P<coord>r\d+\.[xyzw]{2}), "
    r"float2\((?P<ox>-?[0-9.]+), (?P<oy>-?[0-9.]+)\)\)\.x;"
)
BETWEEN = re.compile(r"^(?:\s|[{}]|if \(!?p0\)|//[^\n]*)*$")
OFFSETS = {-0.5: 0, 0.0: 1, 0.5: 2}


def rewrite(text):
    matches = list(FETCH.finditer(text))
    groups = []
    i = 0
    while i + 9 <= len(matches):
        run = matches[i:i + 9]
        coord = run[0]["coord"]
        ok = all(m["coord"] == coord for m in run)
        ok = ok and all(BETWEEN.match(text[a.end():b.start()]) for a, b in zip(run, run[1:]))
        cells = set()
        dsts = set()
        for m in run:
            ox, oy = float(m["ox"]), float(m["oy"])
            if ox not in OFFSETS or oy not in OFFSETS:
                ok = False
                break
            cells.add((OFFSETS[ox], OFFSETS[oy]))
            dsts.add(m["dst"])
        coord_reg = coord.split(".")[0]
        ok = ok and len(cells) == 9 and len(dsts) == 9
        ok = ok and all(d.split(".")[0] != coord_reg for d in dsts)
        if ok:
            groups.append(run)
            i += 9
        else:
            i += 1
    if not groups:
        return text, 0
    out = []
    pos = 0
    for run in groups:
        for n, m in enumerate(run):
            x, y = OFFSETS[float(m["ox"])], OFFSETS[float(m["oy"])]
            out.append(text[pos:m.start()])
            if n == 0:
                out.append(
                    "_s9 = tfetch2DShadow9(\n#ifdef __air__\n\t\t\tg_Texture2DDescriptorHeap,\n"
                    "\t\t\tg_SamplerDescriptorHeap,\n#endif\n\t\t\tSHADOWMAP_SAMPLER_Texture2DDescriptorIndex, "
                    f"SHADOWMAP_SAMPLER_SamplerDescriptorIndex, {m['coord']});\n\t\t"
                )
            out.append(f"{m['dst']} = _s9.v[{x * 3 + y}];")
            pos = m.end()
    out.append(text[pos:])
    text = "".join(out)
    # One Shadow9 for the shader's body, beside its other temporaries.
    anchor = re.search(r"\n(\s*)float ps = 0\.0;\n", text)
    if not anchor:
        raise SystemExit("no 'float ps = 0.0;' to declare _s9 beside")
    text = text[:anchor.end()] + f"{anchor.group(1)}Shadow9 _s9;\n" + text[anchor.end():]
    return text, len(groups)


def main():
    total_files = total_groups = 0
    for path in sys.argv[1:]:
        with open(path) as f:
            text = f.read()
        new, n = rewrite(text)
        if n:
            with open(path, "w") as f:
                f.write(new)
            total_files += 1
            total_groups += n
    print(f"shadow filter: {total_groups} blocks of 9 fetches rewritten in {total_files} shaders")


if __name__ == "__main__":
    main()
