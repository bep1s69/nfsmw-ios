#!/usr/bin/env python3
"""The float constants each translated shader reads, for the renderer.

    constant_ranges.py MSL_DIR OUT_FILE

A translated shader names its stage's constants (c0-c255, 16 bytes each) with
macros: "#define Name (... ShaderConstants + 64 ...)" for one register,
"#define Name(INDEX) ... (BASE + min(INDEX, LIMIT)) * 16 ..." for an array.
The registers it reads are those of the macros its code uses: an array used
with constant indices only (WorldViewProj(0) .. (3)) reads those registers; an
array indexed by a register (relative addressing, e.g. skinning) reads all of
it. The renderer then compares and uploads only those registers, not all 4 KB
per draw. One line per shader:

    vs_0123456789abcdef FIRST END      (registers FIRST..END-1)

A constant read in any other way makes the range the whole bank (0 256).
"""
import pathlib
import re
import sys

DEFINE = re.compile(r"^\s*#define\s+(\w+)(\(INDEX\))?\s+(.*)$")
FIXED = re.compile(r"(Vertex|Pixel)ShaderConstants\s*\+\s*(\d+)\s*[,)]")
ARRAY = re.compile(r"(Vertex|Pixel)ShaderConstants\s*\+\s*\(\s*(\d+)\s*\+\s*min\(.*?,\s*\(?(?:uint\))?\s*(\d+)\)\)\s*\*\s*16")
ACCESS = re.compile(r"(Vertex|Pixel)ShaderConstants\b")
DECL = re.compile(r"^\s*((uint64_t|ulong)\s+(Vertex|Pixel)ShaderConstants;|cbuffer\s+(Vertex|Pixel)ShaderConstants\b.*)\s*$")


def ranges(text, kind):
    fixed, arrays = {}, {}
    body = []
    for line in text.splitlines():
        m = DEFINE.match(line)
        if m:
            name, is_array, value = m.groups()
            if not ACCESS.search(value):
                body.append(value)  # may use the constants' macros itself
                continue
            if is_array:
                a = ARRAY.search(value)
                if not a:
                    return 0, 256
                if a.group(1) == kind:
                    arrays[name] = (int(a.group(2)), int(a.group(3)))
            else:
                f = FIXED.search(value)
                if not f or int(f.group(2)) % 16:
                    return 0, 256
                if f.group(1) == kind:
                    fixed[name] = int(f.group(2)) // 16
            continue
        if DECL.match(line) or line.lstrip().startswith(("float4 ", "\tfloat4 ")) and "packoffset" in line:
            continue
        # The motion entry point's frame-before constants: the same registers.
        if "PreviousVertexShaderConstants" in line:
            continue
        if ACCESS.search(line):
            return 0, 256  # read directly, not through a macro
        body.append(line)
    code = "\n".join(body)
    regs = set()
    for name, reg in fixed.items():
        if re.search(rf"\b{name}\b", code):
            regs.add(reg)
    for name, (base, limit) in arrays.items():
        for m in re.finditer(rf"\b{name}\(([^()]*(?:\([^()]*\))*[^()]*)\)", code):
            arg = m.group(1).strip()
            if arg.isdigit():
                if int(arg) <= limit:
                    regs.add(base + int(arg))
            else:
                regs.update(range(base, base + limit + 1))
    if not regs:
        return 0, 0
    return min(regs), max(regs) + 1


def main():
    src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    lines = []
    for path in sorted(src.glob("*.hlsl")):
        kind = "Vertex" if path.stem.startswith("vs_") else "Pixel"
        lo, hi = ranges(path.read_text(errors="replace"), kind)
        lines.append(f"{path.stem} {lo} {hi}")
    out.write_text("\n".join(lines) + "\n")
    full = sum(1 for l in lines if l.endswith(" 0 256"))
    used = sum(int(l.split()[2]) - int(l.split()[1]) for l in lines)
    print(f"constant ranges: {len(lines)} shaders, {full} read the whole bank, "
          f"{used / max(len(lines), 1):.0f} registers on average")


if __name__ == "__main__":
    main()
