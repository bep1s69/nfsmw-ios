#!/usr/bin/env python3
"""
Extracts NFSMW's shaders from the game files and rewrites them in the
container layout XenosRecomp reads.

    python3 tools/native/nfsmw_shader_containers.py ZZDATA0.BIN OUT_DIR
    python3 tools/native/nfsmw_shader_containers.py --iso GAME.iso OUT_DIR

Writes OUT_DIR/<vs|ps>_<hash>.bin, one container per shader, and
OUT_DIR/index.json. <hash> is FNV-1a 64 of the microcode, for vertex shaders
with their vertex fetch instructions zeroed (D3D patches those when it binds
the shader to a vertex declaration): the same hashes the draw capture
(ios/src/native_draw_census.cpp) computes at run time.


WHY
===

NFSMW was built with the launch XDK (2.0.2135). Its 206 shaders (98 vertex,
108 pixel) are uncompressed in NFS/ZZDATA0.BIN, in shader containers version
0x102A0E0x; XenosRecomp (written for Sonic Unleashed) reads version
0x102A11xx. The two differ in:

  header      the same nine dwords, but 0x0C is the literal-constant table's
              offset (0 if none), 0x14 the shader descriptor's, 0x18 is 0
  literals    (`def c#` values) a table {0, 1, 0, 0, size} then entries
              0xRRRxCCCC followed by CCCC floats inline: RRR - 48 the first
              register (vertex shaders 0x12E -> c254; pixel shaders 0x22E ->
              510, their c254), CCCC the component count; 0 ends it.
              0x11 keeps {registerIndex, count, physicalOffset} entries and
              the values in the physical section.
  descriptor  dword 0 holds the pixel shader's position register in bits
              8-15 (0x11: dword 3), dword 4 the interpolator info (0x11:
              dword 5); no microcode offset/size (the microcode is the whole
              physical section). Vertex shaders: element count in dword 7 and
              the elements from dword 11, then the interpolators (0x11:
              field18 entries to skip from dword 9). Pixel shaders: outputs in
              dword 7, interpolators from dword 8, as in 0x11.

The microcode itself, the constant table (standard D3DX CTAB) and the packing
of vertex elements and interpolators are the same.
"""

import argparse
import json
import pathlib
import struct
import sys

MAGIC_MASK = 0xFFFFFF00
OLD_MAGIC = 0x102A0E00
NEW_MAGIC = 0x102A1100
XGD2_GAME_OFFSET = 0xFD90000


def u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def fnv1a64(data):
    h = 0xCBF29CE484222325
    for byte in data:
        h = ((h ^ byte) * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def vertex_fetch_masked(microcode):
    """The microcode with its vertex fetch instructions zeroed.

    D3D rewrites a vertex shader's vfetch instructions (fetch constant,
    offset, stride, format) when it binds the shader to a vertex declaration,
    so the microcode the GPU gets never matches the file. Everything else
    does: hashing with the vfetches zeroed gives a key that the runtime
    (ios/src/native_draw_census.cpp, the same walk) can compute too.
    """
    words = list(struct.unpack(f">{len(microcode) // 4}I", microcode))
    n = len(words)
    i = 0
    while i + 2 < n:
        w0, w1, w2 = words[i], words[i + 1], words[i + 2]
        # Two 48-bit control flow instructions per 3 dwords.
        cfs = [(w0 | ((w1 & 0xFFFF) << 32)), ((w1 >> 16) | (w2 << 16))]
        stop = False
        for cf in cfs:
            opcode = (cf >> 44) & 0xF
            if opcode in (1, 2, 3, 4, 5, 6, 13, 14):  # exec variants
                address = cf & 0xFFF
                count = (cf >> 12) & 0x7
                sequence = (cf >> 16) & 0xFFF
                for k in range(count):
                    is_fetch = (sequence >> (2 * k)) & 1
                    at = (address + k) * 3
                    if is_fetch and at + 2 < n and (words[at] & 0x1F) == 0:  # vfetch
                        words[at] = words[at + 1] = words[at + 2] = 0
                if opcode in (2, 4, 6, 14):  # ... end
                    stop = True
        if stop:
            break
        i += 3
    return struct.pack(f">{n}I", *words)


def read_zzdata0_from_iso(iso):
    """NFS/ZZDATA0.BIN from the disc image (XDVDFS, XGD2)."""
    with open(iso, "rb") as f:
        def read(offset, size):
            f.seek(offset)
            return f.read(size)
        go = XGD2_GAME_OFFSET
        if read(go + 32 * 2048, 20) != b"MICROSOFT*XBOX*MEDIA":
            sys.exit("not an XGD2 Xbox 360 disc image")
        root_sector, root_size = struct.unpack("<II", read(go + 32 * 2048 + 20, 8))

        def find(sector, size, path):
            data = read(go + sector * 2048, size)

            def node(index):
                o = index * 4
                if o + 14 > len(data):
                    return None
                left, right, sec, sz, attr, nl = struct.unpack_from("<HHIIBB", data, o)
                if left == 0xFFFF:
                    return None
                name = data[o + 14:o + 14 + nl].decode("latin1").upper()
                if name == path[0]:
                    if len(path) == 1:
                        return read(go + sec * 2048, sz)
                    return find(sec, sz, path[1:]) if attr & 0x10 else None
                for child in (left, right):
                    if child:
                        found = node(child)
                        if found is not None:
                            return found
                return None
            return node(0)
        data = find(root_sector, root_size, ["NFS", "ZZDATA0.BIN"])
        if data is None:
            sys.exit("NFS/ZZDATA0.BIN not found in the disc image")
        return data


# XenosRecomp's USAGE_LOCATIONS: (usage, usage index) -> Metal attribute.
USAGE_LOCATIONS = {
    (0, 0): 0, (0, 1): 1, (0, 2): 2, (0, 3): 3, (3, 0): 4, (3, 1): 5, (3, 2): 6, (3, 3): 7,
    (6, 0): 8, (6, 1): 9, (6, 2): 10, (6, 3): 11, (7, 0): 12, (5, 0): 13, (5, 1): 14, (5, 2): 15,
    (5, 3): 16, (10, 0): 17, (2, 0): 18, (1, 0): 19, **{(5, i): 16 + i for i in range(4, 16)},
    (10, 1): 32, (3, 4): 33, (3, 5): 34, (6, 4): 35, (6, 5): 36, (7, 1): 37, (7, 2): 38, (7, 3): 39,
}


def vertex_inputs(data, c):
    """(vfetch instruction address, usage, usage index, Metal attribute) per element."""
    desc_at = u32(data, c + 20)
    count = u32(data, c + desc_at + 28)
    out = []
    for i in range(count):
        v = u32(data, c + desc_at + 44 + 4 * i)
        address, usage, index = v & 0xFFF, (v >> 12) & 0xF, (v >> 16) & 0xF
        out.append((address, usage, index, USAGE_LOCATIONS.get((usage, index), -1)))
    return out


def convert(data, c):
    """The 0x0E container at offset c -> (kind, microcode, 0x11 container)."""
    flags, virt, phys, literals_at, ct_at, desc_at = struct.unpack_from(">6I", data, c)
    vertex = bool(flags & 1)
    microcode = data[c + virt:c + virt + phys]

    # Constant table container: {size, CTAB}.
    ct_size = u32(data, c + ct_at)
    constant_table = data[c + ct_at:c + ct_at + 4 + ct_size]

    # Literal constants -> 0x11 float4 definitions, values after the microcode.
    definitions = []
    literal_values = b""
    if literals_at:
        size = u32(data, c + literals_at + 16)
        p = c + literals_at + 20 + 4  # skip a leading dword (not an entry)
        end = c + literals_at + 20 + size
        while p < end:
            entry = u32(data, p)
            if entry == 0:
                break
            # The top 12 bits less 48: c252-c255 for vertex shaders, 508-511
            # (the pixel shader's c252-c255) for pixel shaders.
            register = (entry >> 20) - 48
            count = entry & 0xFFFF
            values = data[p + 4:p + 4 + 4 * count]
            definitions.append((register, count,
                                len(microcode) + len(literal_values)))
            literal_values += values + b"\0" * (-len(values) % 16)
            p += 4 + 4 * count

    # Shader descriptor in the 0x11 layout.
    d = [u32(data, c + desc_at + 4 * i) for i in range(12)]
    rest_at = c + desc_at + 4 * (9 if vertex else 8)
    rest = data[rest_at:c + virt]
    if vertex:
        # physicalOffset, size, field8, fieldC, field10, interpolatorInfo,
        # field18 (entries before the elements: dwords 9 and 10),
        # vertexElementCount, field20.
        descriptor = struct.pack(">9I", 0, phys + len(literal_values), 0, 0, 0, d[4], 2, d[7], d[8])
    else:
        # ..., field18, outputs.
        descriptor = struct.pack(">8I", 0, phys + len(literal_values), 0, d[0], 0, d[4], d[6], d[7])
    descriptor += rest

    # Assemble: header, constant table, definition table, descriptor.
    header_size = 36
    ct_off = header_size
    def_off = ct_off + len(constant_table)
    def_table = struct.pack(">5I", 0, 1, 0, 0, 0)
    for register, count, offset in definitions:
        def_table += struct.pack(">HHI", register, count, offset)
    def_table += struct.pack(">3I", 0, 0, 0)  # float4, int4 and bool lists end
    desc_off = def_off + len(def_table)
    virtual = bytearray(constant_table + def_table + descriptor)
    virtual_size = header_size + len(virtual)
    virtual_size += -virtual_size % 4
    physical = microcode + literal_values
    header = struct.pack(">9I", NEW_MAGIC | (flags & 0xFF), virtual_size, len(physical), 0,
                         ct_off, def_off if definitions else 0, desc_off, 0, 0)
    container = header + bytes(virtual) + b"\0" * (virtual_size - header_size - len(virtual))
    return ("vs" if vertex else "ps"), microcode, container + physical


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("source", help="NFS/ZZDATA0.BIN, or the disc image with --iso")
    ap.add_argument("out")
    ap.add_argument("--iso", action="store_true")
    args = ap.parse_args()
    data = read_zzdata0_from_iso(args.source) if args.iso else pathlib.Path(args.source).read_bytes()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    index = []
    inputs_lines = []
    for c in range(0, len(data) - 36, 4):
        if (u32(data, c) & MAGIC_MASK) != OLD_MAGIC:
            continue
        virt, phys = u32(data, c + 4), u32(data, c + 8)
        ct_at, desc_at = u32(data, c + 16), u32(data, c + 20)
        if not (0 < ct_at < virt and 0 < desc_at < virt and 0 < phys < (1 << 20)
                and c + virt + phys <= len(data)):
            continue
        kind, microcode, container = convert(data, c)
        h = fnv1a64(vertex_fetch_masked(microcode) if kind == "vs" else microcode)
        name = f"{kind}_{h:016x}"
        (out / f"{name}.bin").write_bytes(container)
        if kind == "vs":
            for address, usage, usage_index, location in vertex_inputs(data, c):
                # The vfetch's destination swizzle as compiled (the
                # translated shader applies it); D3D may patch another at
                # bind time (e.g. D3DCOLOR's byte order).
                at = address * 3 * 4
                swizzle = struct.unpack_from(">I", microcode, at + 4)[0] & 0xFFF if at + 8 <= len(microcode) else 0x688
                # The register it writes: the run-time shader can have its
                # vfetches in another order (same key: the key ignores
                # them), so the renderer finds each input's by register.
                dst = (struct.unpack_from(">I", microcode, at)[0] >> 12) & 0x3F if at + 4 <= len(microcode) else 0
                inputs_lines.append(f"{h:016x} {address} {usage} {usage_index} {location} {swizzle:x} {dst}")
        index.append({"name": name, "kind": kind, "offset": c, "microcode_dwords": len(microcode) // 4})
    (out / "index.json").write_text(json.dumps(index, indent=1))
    # For the renderer: vertex shader key, vfetch instruction address, usage,
    # usage index, Metal attribute, the vfetch's compiled destination swizzle,
    # the register it writes.
    (out / "vertex_inputs.txt").write_text("\n".join(sorted(set(inputs_lines))) + "\n")
    vs = sum(1 for e in index if e["kind"] == "vs")
    print(f"{len(index)} shaders ({vs} vertex, {len(index) - vs} pixel) -> {out}")


if __name__ == "__main__":
    main()
