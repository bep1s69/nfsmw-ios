#!/usr/bin/env python3
"""Conservative texture-slot masks for the native renderer's compiled shaders.

Usage: texture_masks.py MSL_DIR OUT_FILE
Union the translator's instruction scan with every sampler declared in the
emitted source, including stripped-CTAB synthetic samplers. Unknown metadata
uses all 16 slots. No generated shader code or libraries are changed here.
"""
import pathlib
import re
import sys

VERSION = "nfsmw-texture-masks-v1"
MARKER = re.compile(r"^// NFSMW_TEXTURE_MASK_V1 ([0-9a-fA-F]{1,8})$", re.MULTILINE)
DECL = re.compile(r"^#define \w+_Texture(\w*)DescriptorIndex\s+(.+)$", re.MULTILINE)
OFFSET = re.compile(r"SharedConstants\s*\+\s*(\d+)\b")
KIND_OFFSETS = {"2D": 0, "2DArray": 64, "3D": 128, "Cube": 192}


def mask_for(text):
    markers = MARKER.findall(text)
    if len(markers) != 1:
        return 0xFFFF, False
    mask = int(markers[0], 16)
    for kind, expression in DECL.findall(text):
        offsets = OFFSET.findall(expression)
        if kind not in KIND_OFFSETS or len(offsets) != 1:
            return 0xFFFF, False
        offset = int(offsets[0]) - KIND_OFFSETS[kind]
        if offset < 0 or offset % 4 or offset >= 64:
            return 0xFFFF, False
        mask |= 1 << (offset // 4)
    if mask > 0xFFFF:
        return 0xFFFF, False
    # Every emitted descriptor use must have a declaration. A future emitter
    # spelling or new access form must not silently produce an empty mask.
    definitions = set(re.findall(r"^#define (\w+_Texture\w*DescriptorIndex)\b", text, re.MULTILINE))
    uses = set(re.findall(r"\b(\w+_Texture\w*DescriptorIndex)\b", text))
    if not uses <= definitions:
        return 0xFFFF, False
    return mask, True


def main():
    src, out = map(pathlib.Path, sys.argv[1:])
    lines = [VERSION]
    fallback = 0
    for path in sorted(src.glob("*.hlsl")):
        if not re.fullmatch(r"[vp]s_[0-9a-fA-F]{16}", path.stem):
            continue  # debug variants retain the runtime all-slot fallback
        mask, known = mask_for(path.read_text())
        fallback += not known
        lines.append(f"{path.stem} {mask:08x}")
    if len(lines) == 1:
        raise ValueError("no translated shaders found")
    out.write_text("\n".join(lines) + "\n")
    print(f"texture masks: {len(lines) - 1} shaders, {fallback} conservative all-slot fallbacks")


if __name__ == "__main__":
    main()
