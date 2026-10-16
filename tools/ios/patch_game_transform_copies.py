#!/usr/bin/env python3
"""Guard two scalar transfer regions in USA sub_82453768; keep originals inline."""
import argparse
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATED = ROOT / 'ios/generated/default'
MARK = 'nfsmw-transform-copies'
DIGEST = '0a3185dead0f01e7af38e544cb372cb4b09c6d65c8e09f4a8abeb36c72503d99'
INCLUDE = '#include "../../src/game_transform_copies.h" // ' + MARK + '\n'
LOCAL = ('\tconst bool native_transform_copies = FLAGS_nfsmw_native_transform_copies_storage_(); // ' + MARK + '\n'
         '\tbool transform_flush_disabled = true; // ' + MARK + '\n')
SITES = ((1, '\t// lfs f0,12344(r11)\n', '\t// lwz r31,412(r1)\n', '\t// vcfsx v0,v6,0\n'),
         (3, '\t// lfs f0,0(r11)\n', '\t// vmsum3fp128 v8,v11,v10\n', '\t// vmsum3fp128 v8,v11,v10\n'))


def bounds(text):
    a = text.index('DEFINE_REX_FUNC(sub_82453768) {')
    following = re.search(r'\nDEFINE_REX_FUNC\(', text[a + 1:])
    return a, a + 1 + following.start() if following else len(text)


def additions(count):
    return (f'\ttransform_flush_disabled = true; // {MARK}\n'
            f'\tif (!(native_transform_copies && nfsmw::transforms::TryCopy<{count}>'
            f'(ctx, base, temp, transform_flush_disabled))) {{ // {MARK}\n',
            f'\t}} // {MARK}\n')


def transform(text):
    a, b = bounds(text)
    function = text[a:b]
    if hashlib.sha256(function.encode()).hexdigest() != DIGEST:
        raise ValueError('generated sub_82453768 changed')
    for count, start, end, resume in SITES:
        if any(function.count(anchor) != 1 for anchor in (start, end) if anchor):
            raise ValueError('missing or duplicate scalar region')
        x, y = function.index(start), function.index(end)
        begin, close = additions(count)
        function = function[:x] + begin + function[x:y] + close + function[y:]
        anchor = resume + '\tctx.fpscr.enableFlushModeUnconditional();\n'
        if function.count(anchor) != 1:
            raise ValueError('missing vector mode restore')
        function = function.replace(anchor, resume +
            f'\tif (transform_flush_disabled) ctx.fpscr.enableFlushModeUnconditional(); // {MARK}\n', 1)
    function = function.replace('\tREX_FUNC_PROLOGUE();\n', '\tREX_FUNC_PROLOGUE();\n' + LOCAL, 1)
    result = text[:a] + function + text[b:]
    include = re.search(r'^#include "nfsmw_funcs\.[0-9]+\.h"\n', result, re.MULTILINE)
    if not include:
        raise ValueError('missing generated include')
    return result[:include.end()] + INCLUDE + result[include.end():]


def original_text(text):
    if MARK not in text:
        return text
    for addition in (INCLUDE, LOCAL):
        if text.count(addition) != 1:
            raise ValueError('partial or modified patch')
        text = text.replace(addition, '', 1)
    for count, start, end, resume in SITES:
        begin, close = additions(count)
        if text.count(begin + start) != 1 or text.count(close + end) != 1:
            raise ValueError('partial or modified scalar guard')
        text = text.replace(begin + start, start, 1).replace(close + end, end, 1)
        changed = resume + f'\tif (transform_flush_disabled) ctx.fpscr.enableFlushModeUnconditional(); // {MARK}\n'
        if text.count(changed) != 1:
            raise ValueError('partial or modified mode restore')
        text = text.replace(changed, resume + '\tctx.fpscr.enableFlushModeUnconditional();\n', 1)
    if MARK in text:
        raise ValueError('unexpected patch marker')
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dir', type=pathlib.Path, default=GENERATED)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument('--status', action='store_true')
    modes.add_argument('--revert', action='store_true')
    args = ap.parse_args()
    matches = [p for p in args.dir.glob('*.cpp') if 'DEFINE_REX_FUNC(sub_82453768) {' in p.read_text()]
    if len(matches) != 1:
        raise ValueError('expected exactly one USA sub_82453768 definition')
    path = matches[0]
    current = path.read_text()
    if current.count('DEFINE_REX_FUNC(sub_82453768) {') != 1:
        raise ValueError('duplicate USA sub_82453768 definition')
    original = original_text(current)
    patched = transform(original)
    applied = current == patched
    if current != original and not applied:
        raise ValueError('patch placement changed')
    if not args.status:
        wanted = original if args.revert else patched
        if current != wanted:
            path.write_text(wanted)
    state = ('applied' if applied else 'not applied') if args.status else ('reverted' if args.revert else 'applied')
    print(f'[transform-copies] {state} (two guarded scalar regions)')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        print(f'[transform-copies] error: {error}; nothing written', file=sys.stderr)
        sys.exit(1)
