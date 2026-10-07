"""
Shared engine for the iOS SDK patches (tools/ios/patch_ios_*.py).

It does exactly what each tools/parche_*.py carries inline (see docs/parches.md,
"Por que los parches estan escritos asi"):

  - exact text substitution, no .original backups;
  - block by block: each block is checked and applied on its own;
  - refuses to write if an anchor does not appear exactly once;
  - idempotent: applying N times leaves the same file as applying once;
  - --status and --revert.

It lives in one place because the iOS patches are several and new; the
Android ones are left untouched.

Each patch defines BLOCKS = [(path, name, anchor, new), ...] and calls
run(short_name, BLOCKS).
"""

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]


def find_sdk(probe_file):
    """
    The iOS SDK tree. As with the Android patches, NFSMW_SDK wins and, when
    set, is the ONLY path looked at: silently falling back to another tree
    would patch the wrong one.
    """
    other = os.environ.get("NFSMW_SDK")
    candidates = [pathlib.Path(other)] if other else [ROOT.parent / "rexglue-sdk-ios"]
    for cand in candidates:
        if (cand / probe_file).exists():
            return cand
    sys.exit(f"[ERROR] Cannot find the SDK's {probe_file}.\n"
             f"        Looked in NFSMW_SDK, or in ../rexglue-sdk-ios")


def read(f):
    with open(f, encoding="utf-8", newline="") as h:
        txt = h.read()
    eol = "\r\n" if "\r\n" in txt else "\n"
    return txt.replace("\r\n", "\n"), eol


def write(f, txt, eol):
    with open(f, "w", encoding="utf-8", newline="") as h:
        h.write(txt.replace("\n", eol))


def run(name, blocks):
    p = argparse.ArgumentParser(add_help=True)
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    args = p.parse_args()

    sdk = find_sdk(blocks[0][0])
    files = {}
    for path, _, _, _ in blocks:
        if path not in files:
            f = sdk / path
            if not f.exists():
                sys.exit(f"[ERROR] Cannot find {f}")
            files[path] = [f, *read(f)]

    if args.status:
        applied = sum(1 for path, _, _, new in blocks if new in files[path][1])
        print(f"  {name:26s} {applied} of {len(blocks)} blocks applied")
        for path, desc, _, new in blocks:
            print(f"      {'yes' if new in files[path][1] else 'NO':>3}  {desc}  ({path})")
        return 0

    if args.revert:
        removed = 0
        # Backwards: a later block may anchor on what an earlier one left.
        for path, desc, anchor, new in reversed(blocks):
            txt = files[path][1]
            if new not in txt:
                continue
            if txt.count(new) != 1:
                sys.exit(f"[ERROR] Block '{desc}' appears {txt.count(new)} times "
                         f"in {path}. Not touching it; remove it by hand.")
            files[path][1] = txt.replace(new, anchor)
            removed += 1
        if not removed:
            print(f"[ok] {name}: nothing was applied")
            return 0
        for f, txt, eol in files.values():
            write(f, txt, eol)
        print(f"[ok] {name}: removed {removed} blocks")
        return 0

    missing = [b for b in blocks if b[3] not in files[b[0]][1]]
    if not missing:
        print(f"[ok] {name}: all {len(blocks)} blocks already applied")
        return 0
    # In memory and in order (a block may anchor on what the previous one
    # left); to disk only if ALL of them fit. A half-applied patch is worse
    # than one that fails.
    done = []
    for path, desc, anchor, new in missing:
        n = files[path][1].count(anchor)
        if n != 1:
            sys.exit(f"[ERROR] {name}: the anchor for '{desc}' appears {n} times in {path}, "
                     f"expected 1. The SDK must have changed. Nothing was written.")
        files[path][1] = files[path][1].replace(anchor, new)
        done.append(desc)
    for desc in done:
        print(f"[ok] {name}: applied {desc}")
    for f, txt, eol in files.values():
        write(f, txt, eol)
    return 0
