#!/usr/bin/env python3
"""Guarded native copies in two USA sub_82699100 loops; originals stay inline.

Only exact known generated loop bodies are accepted. Apply after codegen, or
use --status / --revert. Nothing is written until both sites validate.
"""
import argparse
import hashlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATED = ROOT / "ios" / "generated" / "default"
MARK = "nfsmw-constant-copies"
INCLUDE = '#include "../../src/game_constant_copies.h" // ' + MARK + '\n'
LOCAL = '\tconst bool native_constant_copies = FLAGS_nfsmw_native_constant_copies_storage_(); // ' + MARK + '\n'
SITES = {
    "82699210": (False, "c24d5877735a937099f15874ad7ed310cc38e1322c508f62731a0c7f034d0060"),
    "82699378": (True, "8238e4f2e1a819874f90ef048bdd132b2445f3c56308a85f42aa781d2850d1a8"),
}


def additions(label, pixel):
    entry = (f'\tif (native_constant_copies && nfsmw::constants::TryCopy<{str(pixel).lower()}>'
             f'(ctx, base, cr6, ea)) goto loc_{label}_native_done; // {MARK}\n')
    done = f'loc_{label}_native_done:; // {MARK}\n'
    return entry, done


def original_text(text):
    if MARK not in text:
        return text
    # A partial or edited patch must not be silently accepted.
    for addition in [INCLUDE, LOCAL] + [part for label, (pixel, _) in SITES.items()
                                       for part in additions(label, pixel)]:
        if text.count(addition) != 1:
            raise ValueError("partial or modified patch")
        text = text.replace(addition, "", 1)
    if MARK in text:
        raise ValueError("unexpected patch marker")
    return text


def transform(text):
    start = text.index("DEFINE_REX_FUNC(sub_82699100) {")
    following = re.search(r"\nDEFINE_REX_FUNC\(", text[start + 1:])
    stop = start + 1 + following.start() if following else len(text)
    function = text[start:stop]
    for label, (pixel, digest) in SITES.items():
        label_text = f"loc_{label}:\n"
        end_text = f"\tif (!cr6.gt) goto loc_{label};\n"
        if function.count(label_text) != 1 or function.count(end_text) != 1:
            raise ValueError(f"missing or duplicate loop {label}")
        a = function.index(label_text)
        b = function.index(end_text, a) + len(end_text)
        body = function[a:b]
        if hashlib.sha256(body.encode()).hexdigest() != digest:
            raise ValueError(f"generated loop {label} changed")
        entry, done = additions(label, pixel)
        function = function[:a] + body.replace(label_text, label_text + entry, 1) + done + function[b:]
    anchor = "\tREX_FUNC_PROLOGUE();\n"
    if function.count(anchor) != 1:
        raise ValueError("unexpected function prologue")
    function = function.replace(anchor, anchor + LOCAL, 1)
    result = text[:start] + function + text[stop:]
    include = re.search(r'^#include "nfsmw_funcs\.[0-9]+\.h"\n', result, re.MULTILINE)
    if not include:
        raise ValueError("missing generated function header")
    return result[:include.end()] + INCLUDE + result[include.end():]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=pathlib.Path, default=GENERATED)
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--status", action="store_true")
    modes.add_argument("--revert", action="store_true")
    args = ap.parse_args()
    matches = [p for p in args.dir.glob("*.cpp")
               if "DEFINE_REX_FUNC(sub_82699100) {" in p.read_text()]
    if len(matches) != 1:
        raise ValueError("expected exactly one USA sub_82699100 definition")
    path = matches[0]
    current = path.read_text()
    original = original_text(current)
    patched = transform(original)
    applied = current == patched
    if current != original and not applied:
        raise ValueError("patch placement changed")
    if args.status:
        print(f"[constant-copies] {'applied' if applied else 'not applied'} (two guarded loops)")
    else:
        wanted = original if args.revert else patched
        if current != wanted:
            path.write_text(wanted)
        print(f"[constant-copies] {'reverted' if args.revert else 'applied'} (two guarded loops)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"[constant-copies] error: {error}; nothing written", file=sys.stderr)
        sys.exit(1)
