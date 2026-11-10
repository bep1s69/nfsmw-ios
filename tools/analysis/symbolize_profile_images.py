#!/usr/bin/env python3
"""Name raw CPU PCs using explicit, validated image bases and exact binaries.

Manifest: [{"path": "...", "load_address": "0x...", "uuid": "..."}, ...].
This does not discover/validate load bases; document their provenance separately.
Uses only the exact Mach-O symbol table, never possibly overwritten DWARF objects.
Original XML and binaries are read-only. Restrict subsequent analysis to the
process for which the manifest is valid.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path
import re
import struct
import subprocess
import xml.etree.ElementTree as ET


def image(entry):
    path = Path(entry['path'])
    uuids = subprocess.check_output(['xcrun', 'dwarfdump', '--uuid', str(path)], text=True)
    if entry['uuid'].upper() not in uuids.upper():
        raise ValueError(f'UUID mismatch: {path}')
    data = path.read_bytes()
    if struct.unpack_from('<I', data)[0] != 0xFEEDFACF:
        raise ValueError('Requires a thin little-endian 64-bit Mach-O')
    offset = 32
    sections = []
    preferred = None
    for _ in range(struct.unpack_from('<I', data, 16)[0]):
        cmd, size = struct.unpack_from('<II', data, offset)
        if cmd == 0x19:
            seg = data[offset+8:offset+24].rstrip(b'\0')
            if seg == b'__TEXT':
                preferred = struct.unpack_from('<Q', data, offset+24)[0]
            for i in range(struct.unpack_from('<I', data, offset+64)[0]):
                q = offset+72+80*i
                start, length = struct.unpack_from('<QQ', data, q+32)
                flags = struct.unpack_from('<I', data, q+64)[0]
                if flags & (0x80000000 | 0x400):
                    sections.append((start, start+length))
        offset += size
    if preferred is None:
        raise ValueError('No __TEXT')
    symbols = []
    output = subprocess.check_output(['xcrun', 'nm', '-n', '-C', str(path)], text=True)
    for line in output.splitlines():
        match = re.match(r'^([0-9a-fA-F]+)\s+\S\s+(.+)$', line)
        if match:
            address = int(match[1], 16)
            if any(a <= address < b for a, b in sections):
                # nm retains Mach-O's extra underscore on C linkage names.
                symbols.append((address, match[2].removeprefix('_')))
    symbols.sort()
    return dict(path=str(path), base=int(entry['load_address'], 0), preferred=preferred,
                sections=sections, symbols=symbols, starts=[s[0] for s in symbols])


def name_pc(pc, images):
    for im in images:
        address = (pc & ~3) - im['base'] + im['preferred']
        for lo, hi in im['sections']:
            if lo <= address < hi:
                index = bisect_right(im['starts'], address)-1
                if index >= 0 and im['starts'][index] >= lo:
                    return im['symbols'][index][1]
    return None


def reference_names(path, wanted):
    """Reuse only exact UUID + instruction-offset matches, never nearby PCs."""
    binaries, result = {}, {}
    for _, element in ET.iterparse(path, events=('end',)):
        if element.tag == 'binary' and element.get('id'):
            binaries[element.get('id')] = (element.get('UUID'), int(element.get('load-addr', '0'), 0))
        elif element.tag == 'frame' and element.get('addr') and len(element):
            b = element[0]
            image_info = binaries.get(b.get('ref') or b.get('id'))
            if image_info:
                key = (image_info[0], (int(element.get('addr'), 0) & ~3) - image_info[1])
                name = element.get('name', '')
                if key in wanted and name and not name.startswith('0x'):
                    result[key] = name
        elif element.tag == 'row':
            element.clear()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--reference', type=Path, help='Named export: exact system UUID/PC matches only')
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Output must differ from input')
    images = [image(e) for e in json.loads(args.manifest.read_text())]
    tree = ET.parse(args.input)
    binaries = {b.get('id'): (b.get('UUID'), int(b.get('load-addr', '0'), 0))
                for b in tree.iter('binary') if b.get('id')}
    frame_keys = {}
    for frame in tree.iter('frame'):
        if frame.get('addr') and len(frame):
            b = frame[0]
            info = binaries.get(b.get('ref') or b.get('id'))
            if info:
                frame_keys[id(frame)] = (info[0], (int(frame.get('addr'), 0) & ~3) - info[1])
    reference = reference_names(args.reference, set(frame_keys.values())) if args.reference else {}
    changed = 0
    for frame in tree.iter('frame'):
        old = frame.get('name', '')
        if frame.get('addr') and (not old or old.startswith('0x')):
            name = reference.get(frame_keys.get(id(frame))) or name_pc(int(frame.get('addr'), 0), images)
            if name:
                frame.set('name', name)
                changed += 1
    tree.write(args.output, encoding='utf-8', xml_declaration=True)
    print(f'Named {changed} unique frame definitions; explicit mapping valid only for target process')


if __name__ == '__main__':
    main()
