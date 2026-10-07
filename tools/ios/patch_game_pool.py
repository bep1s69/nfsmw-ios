#!/usr/bin/env python3
"""
Larger record pool in the GENERATED game code (USA edition), so Black Edition
content fits. The runtime half, and the full story, is ios/src/game_pool.cpp.

    python3 tools/ios/patch_game_pool.py            apply
    python3 tools/ios/patch_game_pool.py --status

Touches ios/generated/default/*.cpp, which tools/ios/generate_code.py writes
and then runs this on. Generating the code again undoes it; there is no
--revert.

This edits generated game code, which the project otherwise avoids. Here there
is no hook-sized alternative: the game turns a pool index into an address
inline, in 31 places across 30 functions.


WHAT IT CHANGES
===============

Each place looks like this (registers vary; some start from the owning object
and add 5052 instead of 4000, the table being object+1052):

    cmplwi cr6,rI,75          index <= 75?          -> index <= kPoolTotal-1
    ...
    mulli  rM,rI,408          index * 408
    add    rA,rM,rT           + table               -> nfsmw_pool_entry() - OFF
    addi   rD,rA,4000|5052                          (unchanged)

So after the add, rA + OFF is the entry's address, whichever block it is in,
and everything after it is unchanged. The `add` must be within 4 instructions
of the mulli, and the `addi` within 3 of the add; the check is the nearest
"cmplwi ...,75" before the mulli in the same function.

Plus one line in sub_822CBC00, right after its inline loop that frees the 75
entries: nfsmw_pool_reset() frees the overflow too, before that function goes
on to create records.

sub_822C9570 (the allocator) also has a mulli 408; game_pool.cpp replaces that
function, so it is left alone.


SAFETY
======

Everything is worked out in memory first. If any place does not look exactly
as expected, or the counts are not exactly 31 sites, 31 checks and 1 reset,
nothing is written. Each edited line carries "nfsmw-pool", which --status
counts and which keeps a second run from touching anything.
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATED = ROOT / "ios" / "generated" / "default"
POOL_CPP = ROOT / "ios" / "src" / "game_pool.cpp"
MARK = "nfsmw-pool"

# Function -> how many index sites it has (USA edition).
SITES = {
    "sub_822418E8": 1, "sub_8226B210": 1, "sub_822A67F8": 1, "sub_822C4698": 1,
    "sub_822CB178": 1, "sub_822CB398": 1, "sub_822CB870": 1, "sub_822CC278": 1,
    "sub_822CC300": 1, "sub_822CC3B8": 1, "sub_822CC410": 1, "sub_822CC4D8": 1,
    "sub_822E7B38": 1, "sub_822E80E0": 1, "sub_824729E0": 1, "sub_82476B08": 1,
    "sub_824D5558": 1, "sub_8254E710": 1, "sub_8255BFD0": 1, "sub_8255C598": 1,
    "sub_825669F0": 2, "sub_8256B248": 1, "sub_8256C470": 1, "sub_8256C650": 1,
    "sub_8256C6C0": 1, "sub_8256C788": 1, "sub_8256C8C8": 1, "sub_8256C918": 1,
    "sub_82582D78": 1, "sub_82584688": 1,
}
SKIPPED = {"sub_822C9570"}  # replaced in game_pool.cpp
RESET_FN = "sub_822CBC00"
RESET_AFTER = "\tif (!cr6.eq) goto loc_822CBC3C;"
EXPECTED_SITES = sum(SITES.values())

DECLS = f"""// LOCAL PATCH - iOS ({MARK}): a larger record pool (tools/ios/patch_game_pool.py,
// ios/src/game_pool.cpp).
extern "C" uint32_t nfsmw_pool_entry(uint8_t* base, uint32_t table, uint32_t index);
extern "C" void nfsmw_pool_reset(uint8_t* base, uint32_t table);
"""

ASM = re.compile(r"\t// (.*)$")
FUNC = re.compile(r"DEFINE_REX_FUNC\((sub_[0-9A-F]+)\)")


def fail(msg):
    print(f"[error] {msg}\n        Nothing was written.")
    sys.exit(1)


def pool_total():
    m = re.search(r"constexpr uint32_t kPoolTotal = (\d+);", POOL_CPP.read_text(encoding="utf-8"))
    if not m:
        fail(f"cannot find kPoolTotal in {POOL_CPP}")
    return int(m.group(1))


def instructions(lines, start, end):
    """(index of the asm comment line, asm text) for lines[start:end]."""
    out = []
    for i in range(start, end):
        m = ASM.match(lines[i])
        if m:
            out.append((i, m.group(1).strip()))
    return out


def patch_file(path, last):
    """Returns (new text or None, sites, checks, resets)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    starts = [(i, FUNC.match(l).group(1)) for i, l in enumerate(lines) if FUNC.match(l)]
    sites = checks = resets = 0
    changed = False
    for n, (start, fn) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        if fn == RESET_FN:
            hits = [i for i in range(start, end) if lines[i] == RESET_AFTER]
            if len(hits) != 1:
                fail(f"{fn}: expected its reset loop once, found {len(hits)}")
            i = hits[0]
            if MARK not in lines[i + 1]:
                lines.insert(i + 1, f"\tnfsmw_pool_reset(base, ctx.r23.u32);  // {MARK}: the overflow too")
                changed = True
            resets += 1
            continue
        if fn not in SITES:
            continue
        asm = instructions(lines, start, end)
        found = 0
        for k, (li, text) in enumerate(asm):
            m = re.fullmatch(r"mulli (r\d+),(r\d+),408", text)
            if not m:
                continue
            rm = m.group(1)
            # the add: rA = rM + rT
            add = None
            for kk in range(k + 1, min(k + 5, len(asm))):
                ma = re.fullmatch(r"add (r\d+),(r\d+),(r\d+)", asm[kk][1])
                if ma and rm in (ma.group(2), ma.group(3)):
                    add = (kk, ma)
                    break
                if re.match(rf"\S+ {rm},", asm[kk][1]):
                    break  # rM overwritten first
            if add is None:
                fail(f"{fn}: no 'add ...,{rm},...' right after '{text}'")
            kk, ma = add
            ra = ma.group(1)
            rt = ma.group(3) if ma.group(2) == rm else ma.group(2)
            off = None
            for k3 in range(kk + 1, min(kk + 4, len(asm))):
                mo = re.fullmatch(rf"addi r\d+,{ra},(4000|5052)", asm[k3][1])
                if mo:
                    off = int(mo.group(1))
                    break
            if off is None:
                fail(f"{fn}: no 'addi ...,{ra},4000|5052' after '{asm[kk][1]}'")
            # the add's C++ line
            ci = asm[kk][0] + 1
            want = f"\tctx.{ra}.u64 = ctx.{ma.group(2)}.u64 + ctx.{ma.group(3)}.u64;"
            new = (f"\tctx.{ra}.u64 = uint32_t(nfsmw_pool_entry(base, ctx.{rt}.u32 + {off - 4000}, "
                   f"ctx.{rm}.u32 / 408) - {off});  // {MARK}")
            if lines[ci] == want:
                lines[ci] = new
                changed = True
            elif lines[ci] != new:
                fail(f"{fn}: unexpected C++ for '{asm[kk][1]}': {lines[ci].strip()}")
            # the check: the nearest "cmplwi crN,rX,75" before the mulli
            for kc in range(k - 1, -1, -1):
                mc = re.fullmatch(r"cmplwi (cr\d),(r\d+),75", asm[kc][1])
                if mc:
                    break
            else:
                fail(f"{fn}: no 'cmplwi ...,75' before '{text}'")
            cc = asm[kc][0] + 1
            cr, rx = mc.groups()
            want = f"\t{cr}.compare<uint32_t>(ctx.{rx}.u32, 75, ctx.xer);"
            new = f"\t{cr}.compare<uint32_t>(ctx.{rx}.u32, {last}, ctx.xer);  // {MARK}: was 75"
            if lines[cc] == want:
                lines[cc] = new
                changed = True
            elif lines[cc] != new:
                fail(f"{fn}: unexpected C++ for '{asm[kc][1]}': {lines[cc].strip()}")
            found += 1
            checks += 1
        if found != SITES[fn]:
            fail(f"{fn}: expected {SITES[fn]} site(s), found {found}")
        sites += found
    if changed and MARK not in "\n".join(lines[:40]):
        inc = next((i for i, l in enumerate(lines) if l.startswith('#include "nfsmw_funcs.')), None)
        if inc is None:
            fail(f"{path.name}: no #include \"nfsmw_funcs.*.h\" to put the declarations after")
        lines.insert(inc + 1, "\n" + DECLS.rstrip("\n"))
    return ("\n".join(lines) if changed else None), sites, checks, resets


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dir", default=str(GENERATED))
    args = ap.parse_args()
    gen = pathlib.Path(args.dir)
    if not any(gen.glob("*.cpp")):
        fail(f"no generated code in {gen}")

    if args.status:
        marks = sum(p.read_text(encoding="utf-8").count(f"// {MARK}") for p in gen.glob("*.cpp"))
        expected = 2 * EXPECTED_SITES + 1
        state = "applied" if marks == expected else ("not applied" if marks == 0 else "PARTIAL")
        print(f"[pool] {state}: {marks} of {expected} edited lines")
        return 0

    last = pool_total() - 1
    pending = {}
    sites = checks = resets = 0
    for path in sorted(gen.glob("*.cpp")):
        text, s, c, r = patch_file(path, last)
        sites, checks, resets = sites + s, checks + c, resets + r
        if text is not None:
            pending[path] = text
    if (sites, checks, resets) != (EXPECTED_SITES, EXPECTED_SITES, 1):
        fail(f"found {sites} sites, {checks} checks, {resets} reset(s); "
             f"expected {EXPECTED_SITES}, {EXPECTED_SITES}, 1. Is this the USA edition?")
    for path, text in pending.items():
        path.write_text(text, encoding="utf-8")
    print(f"[pool] {'patched' if pending else 'already patched'}: {sites} sites, {checks} checks "
          f"(index <= {last}), 1 reset, in {len(pending)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
