#!/usr/bin/env python3
"""Read-only USA source inventory; literal candidates are NOT runtime coverage.

Scans generated PPC annotations within basic blocks, conservatively forgetting
constants at labels/branches/calls. Dynamic headers, memory loads, control-flow
joins and non-scalar stores are intentionally unresolved. A candidate store may
be payload data, not a packet header: verify its destination/callsite manually.
No generated game code or payload bytes are copied into this tool's output.
Only DEFINE_REX_FUNC(sub_XXXXXXXX) definitions are indexed; imported or
handwritten writers require separate inspection.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

FUNCTION = re.compile(r'^DEFINE_REX_FUNC\((sub_([0-9A-Fa-f]{8}))\)')
CALL = re.compile(r'\b(sub_[0-9A-Fa-f]{8})\(ctx, base\)')


def literal_stores(lines, opcodes):
    registers, result = {}, []
    for number, line in lines:
        if line.startswith('loc_'):
            registers.clear()
        if not line.lstrip().startswith('// '):
            continue
        assembly = line.strip()[3:].strip()
        if not assembly:
            continue
        instruction, _, operands = assembly.partition(' ')
        args = operands.split(',')
        if instruction.startswith('b'):
            registers.clear()
            continue
        if instruction in ('lmw', 'lswi', 'lswx'):
            registers.clear()  # more than one GPR written
            continue
        dest = args[0]
        def invalidate_update_base():
            if instruction.endswith(('u', 'ux')):
                base = re.search(r'\((r\d+)\)$', operands)
                if base:
                    registers.pop(base[1], None)
                elif len(args) > 1:
                    registers.pop(args[1], None)
        def reg(i):
            return registers.get(args[i])
        def immediate(i):
            return int(args[i], 0)
        value = None
        try:
            if instruction in ('li', 'lis'):
                value = immediate(1) << (16 if instruction == 'lis' else 0)
            elif instruction == 'mr':
                value = reg(1)
            elif instruction in ('ori', 'oris') and reg(1) is not None:
                value = reg(1) | (immediate(2) << (16 if instruction == 'oris' else 0))
            elif instruction in ('addi', 'addis'):
                base = 0 if args[1] == 'r0' else reg(1)
                if base is not None:
                    value = base + (immediate(2) << (16 if instruction == 'addis' else 0))
            elif instruction == 'or' and reg(1) is not None and reg(2) is not None:
                value = reg(1) | reg(2)
            elif instruction in ('stw', 'stwu', 'stwx', 'stwux'):
                word = registers.get(dest)
                stack = bool(re.search(r'\(r1\)$', operands)) or (len(args) > 2 and 'r1' in args[1:])
                if word is not None and not stack and word >> 30 == 3 and (word >> 8) & 127 in opcodes:
                    result.append(dict(line=number, word=f'{word:08X}',
                                       opcode=f'{(word >> 8) & 127:02X}',
                                       operation=opcodes[(word >> 8) & 127],
                                       payload_words=((word >> 16) & 0x3fff)+1,
                                       predicated=bool(word & 1)))
                invalidate_update_base()
                continue
            elif instruction.startswith(('st', 'cmp', 'cmpl')):
                if instruction.startswith('st'):
                    invalidate_update_base()
                continue
        except (ValueError, IndexError):
            value = None
        if re.fullmatch(r'r\d+', dest):
            if instruction.startswith('l'):
                invalidate_update_base()
            registers.pop(dest, None)
            if value is not None:
                registers[dest] = value & 0xffffffff
    return result


def inventory(generated, sdk, all_functions=False):
    header = sdk/'include/rex/graphics/xenos.h'
    opcodes = {int(value, 16): name for name, value in
               re.findall(r'\b(PM4_\w+)\s*=\s*0x([0-9a-fA-F]+)', header.read_text())}
    functions, manifest = {}, {}
    for path in sorted(generated.glob('nfsmw_recomp.*.cpp')):
        data = path.read_bytes()
        manifest[path.name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        name, first, body = None, 0, []
        def finish():
            if name is None or (not all_functions and not 0x82580000 <= int(name[4:], 16) < 0x825B0000):
                return
            functions[name] = dict(file=str(path.resolve()), line=first,
                calls=dict(Counter(call for _, line in body for call in CALL.findall(line))),
                indirect_calls=sum('// bctrl' in line or '// bctr ' in line for _, line in body),
                literal_store_candidates=literal_stores(body, opcodes))
        for number, line in enumerate(data.decode().splitlines(), 1):
            match = FUNCTION.match(line)
            if match:
                finish()
                name, first, body = match[1], number, []
            body.append((number, line))
        finish()
    if not manifest or not functions:
        raise ValueError('No generated USA D3D functions found; check source path/edition')
    cp = sdk/'src/graphics/command_processor.cpp'
    cases = sorted(set(re.findall(r'case (PM4_\w+):', cp.read_text())))
    canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
    return dict(limitations=__doc__.strip(), scope='all generated functions' if all_functions else '[82580000,825B0000)', generated_files=len(manifest),
                generated_manifest_sha256=hashlib.sha256(canonical).hexdigest(),
                source_manifest=manifest,
                sdk_inputs={str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in [header, cp, sdk/'include/rex/graphics/command_processor.h',
                                      sdk/'src/graphics/plugin_main.cpp',
                                      sdk/'src/graphics/vulkan/command_processor.cpp',
                                      sdk/'src/kernel/xboxkrnl/xboxkrnl_video.cpp']},
                cp_type3_cases=cases, functions=functions)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generated', required=True, type=Path)
    parser.add_argument('--sdk', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--all-functions', action='store_true')
    args = parser.parse_args()
    result = json.dumps(inventory(args.generated, args.sdk, args.all_functions), indent=2, sort_keys=True)+'\n'
    if args.output:
        args.output.write_text(result)
    else:
        print(result, end='')
