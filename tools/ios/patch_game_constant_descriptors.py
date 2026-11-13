#!/usr/bin/env python3
"""Install independent USA descriptor-run trial after the existing copy patch.

Exact full-body guards, reversible/idempotent. No writes on invalid input.
The fallback backedge bypasses admission for the remainder of a refused run.
"""
import argparse
import hashlib
from pathlib import Path
import re
import sys
import patch_game_constant_copies as copies

ROOT = Path(__file__).resolve().parents[2]
GENERATED = ROOT / 'ios/generated/default'
MARK = 'nfsmw-descriptor-runs'
INCLUDE = '#include "../../src/game_constant_descriptors.h" // ' + MARK + '\n'
LOCAL = '''\tstatic const bool native_descriptor_runs = FLAGS_nfsmw_native_descriptor_runs_storage_(); // nfsmw-descriptor-runs
\tnfsmw::constants::descriptors::Counts native_descriptor_counts; // nfsmw-descriptor-runs
\tnfsmw::constants::descriptors::Counts* native_descriptor_sample = nullptr; // nfsmw-descriptor-runs
\tif (native_descriptor_runs && nfsmw::constants::descriptors::ShouldSample()) { // nfsmw-descriptor-runs
\t\tnative_descriptor_counts = {}; native_descriptor_sample = &native_descriptor_counts; // nfsmw-descriptor-runs
\t} // nfsmw-descriptor-runs
'''
REPORT = '\tif (native_descriptor_sample) nfsmw::constants::descriptors::Report(*native_descriptor_sample); // ' + MARK + '\n'
SITES = {
    '826991D8': (False, '965bf79981ceb0b3c67897d2ef412adb61bcf2052666c3287d43480f667125ef'),
    '8269933C': (True, '7a676ee8ea9391e754f6fb8f1990079de1e7e95d7030a7a4b9485add9f7d0a98'),
}


def parts(label, pixel):
    entry = (f'\tif (native_descriptor_runs && nfsmw::constants::descriptors::Observe<{str(pixel).lower()}>'
             f'(ctx, base, cr6, ea, temp, native_descriptor_sample)) goto loc_{label}_runs_done; // {MARK}\n'
             f'loc_{label}_runs_fallback:; // {MARK}\n')
    edge = f'\tif (cr6.lt) goto loc_{label}_runs_fallback; // {MARK}\n'
    done = f'loc_{label}_runs_done:; // {MARK}\n'
    return entry, edge, done


def original_text(text):
    if MARK not in text:
        return text
    for addition in [INCLUDE, LOCAL, REPORT]:
        if text.count(addition) != 1:
            raise ValueError('partial/modified descriptor patch')
        text = text.replace(addition, '', 1)
    for label, (pixel, _) in SITES.items():
        entry, edge, done = parts(label, pixel)
        for addition in [entry, edge, done]:
            if text.count(addition) != 1:
                raise ValueError('partial/modified descriptor site')
        text = text.replace(entry, '', 1).replace(done, '', 1)
        text = text.replace(edge, f'\tif (cr6.lt) goto loc_{label};\n', 1)
    if MARK in text:
        raise ValueError('unexpected descriptor marker')
    return text


def transform(text):
    # Validate the ENTIRE original bodies even though fallback uses current copy
    # helpers. Preserve every byte of that current body except its one backedge.
    plain = copies.original_text(text)
    if copies.transform(plain) != text:
        raise ValueError('apply current constant-copy patch first')
    for label, (_, digest) in SITES.items():
        a = plain.index(f'loc_{label}:\n')
        end = f'\tif (cr6.lt) goto loc_{label};\n'
        b = plain.index(end, a) + len(end)
        if hashlib.sha256(plain[a:b].encode()).hexdigest() != digest:
            raise ValueError(f'full descriptor body {label} changed')
    start = text.index('DEFINE_REX_FUNC(sub_82699100) {')
    following = re.search(r'\nDEFINE_REX_FUNC\(', text[start+1:])
    stop = start+1+following.start() if following else len(text)
    function = text[start:stop]
    for label, (pixel, _) in SITES.items():
        anchor = f'loc_{label}:\n'
        edge = f'\tif (cr6.lt) goto loc_{label};\n'
        if function.count(anchor) != 1 or function.count(edge) != 1:
            raise ValueError('descriptor entry/backedge changed')
        entry, new_edge, done = parts(label, pixel)
        function = function.replace(anchor, anchor+entry, 1).replace(edge, new_edge+done, 1)
    if function.count('\tREX_FUNC_PROLOGUE();\n') != 1 or function.count('\t__restgprlr_18(ctx, base);\n') != 1 or function.count('\treturn;') != 1:
        raise ValueError('unexpected descriptor function lifetime')
    function = function.replace(copies.LOCAL, copies.LOCAL+LOCAL, 1)
    function = function.replace('\t__restgprlr_18(ctx, base);\n', REPORT+'\t__restgprlr_18(ctx, base);\n', 1)
    result = text[:start]+function+text[stop:]
    if result.count(copies.INCLUDE) != 1:
        raise ValueError('missing current-copy include')
    return result.replace(copies.INCLUDE,copies.INCLUDE+INCLUDE,1)



def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dir', type=Path, default=GENERATED)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument('--status', action='store_true')
    modes.add_argument('--revert', action='store_true')
    args = ap.parse_args()
    files = [p for p in args.dir.glob('*.cpp') if 'DEFINE_REX_FUNC(sub_82699100) {' in p.read_text()]
    if len(files) != 1:
        raise ValueError('expected one USA constant-commit function')
    path = files[0]; current = path.read_text()
    original = original_text(current); patched = transform(original)
    if current not in (original, patched):
        raise ValueError('descriptor placement changed')
    if args.status:
        print(f'[descriptor-runs] {"applied" if current==patched else "not applied"} (two full runs)')
    else:
        wanted = original if args.revert else patched
        if wanted != current:
            path.write_text(wanted)
        print(f'[descriptor-runs] {"reverted" if args.revert else "applied"} (two full runs)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, AssertionError) as error:
        print(f'[descriptor-runs] error: {error}; nothing written', file=sys.stderr)
        sys.exit(1)
