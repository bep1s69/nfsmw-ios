#!/usr/bin/env python3
"""
Extra Options features in the GENERATED game code (USA edition). The runtime
half, and how each place was found: ios/src/game_extra_options.cpp.

    python3 tools/ios/patch_game_extra_options.py            apply
    python3 tools/ios/patch_game_extra_options.py --status

Touches ios/generated/default/*.cpp, which tools/ios/generate_code.py writes
and then runs this on. Generating the code again undoes it; there is no
--revert.

Each feature is a list of edits: in a given function, after a given
instruction (its "// ..." comment in the generated code), the C++ line(s)
that follow are replaced by ones that read the setting. All or nothing: unless
every edit is found exactly as many times as expected, nothing is written.
Each edited line carries the feature's mark, which --status counts and which
keeps a second run from touching anything.

  markers    sub_82586768: cmpwi cr6,r3,2 (x2)       nfsmw_markers_to_pick()
             sub_82586E78: subfic rD,rA,2 (x2)
  car-limit  sub_82564B88: cmpwi cr6,r3,10 (x1)      nfsmw_purchased_car_limit()
  skip-movies sub_82282F18, sub_822BBA98, sub_824792D8:
             lwz r11,-12772(r11) (x1 each)           | nfsmw_skip_movies()
"""

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GENERATED = ROOT / "ios" / "generated" / "default"
FUNC = re.compile(r"DEFINE_REX_FUNC\((sub_[0-9A-F]+)\)")
DECL_MARK = "nfsmw-extra-options"

DECLS = f"""// LOCAL PATCH - iOS ({DECL_MARK}): Extra Options features
// (tools/ios/patch_game_extra_options.py, ios/src/game_extra_options.cpp).
extern "C" int32_t nfsmw_markers_to_pick();
extern "C" int32_t nfsmw_purchased_car_limit();
extern "C" int32_t nfsmw_shadow_map_size();
extern "C" int32_t nfsmw_skip_movies();
"""


def compare_edit(reg, value, call, mark):
    """'cmpwi cr6,<reg>,<value>' -> the compare reads <call>."""
    def edit(match, _):
        old = [f"\tcr6.compare<int32_t>(ctx.{reg}.s32, {value}, ctx.xer);"]
        new = [f"\tcr6.compare<int32_t>(ctx.{reg}.s32, {call}, ctx.xer);  // {mark}"]
        return old, new
    return re.compile(rf"\t// cmpwi cr6,{reg},{value}$"), edit


def subfic_edit(value, call, mark):
    """'subfic rD,rA,<value>' -> <call> - rA."""
    def edit(match, _):
        rd, ra = match.groups()
        old = [f"\tctx.xer.ca = ctx.{ra}.u32 <= {value};",
               f"\tctx.{rd}.u64 = static_cast<uint64_t>({value}) - ctx.{ra}.u64;"]
        new = [f"\tctx.xer.ca = ctx.{ra}.u32 <= uint32_t({call});  // {mark}",
               f"\tctx.{rd}.u64 = static_cast<uint64_t>({call}) - ctx.{ra}.u64;  // {mark}"]
        return old, new
    return re.compile(rf"\t// subfic (r\d+),(r\d+),{value}$"), edit


def li_edit(value, call, mark):
    """'li rD,<value>' -> rD = <call>."""
    def edit(match, _):
        rd = match.group(1)
        old = [f"\tctx.{rd}.s64 = {value};"]
        new = [f"\tctx.{rd}.s64 = {call};  // {mark}"]
        return old, new
    return re.compile(rf"\t// li (r\d+),{value}$"), edit


def load_or_edit(reg, base, offset, call, mark):
    """'lwz <reg>,<offset>(<base>)' -> the loaded word | <call>."""
    def edit(match, _):
        old = [f"\tctx.{reg}.u64 = REX_LOAD_U32(ctx.{base}.u32 + {offset});"]
        new = [f"\tctx.{reg}.u64 = REX_LOAD_U32(ctx.{base}.u32 + {offset}) | uint32_t({call});  // {mark}"]
        return old, new
    return re.compile(rf"\t// lwz {reg},{offset}\({base}\)$"), edit


# feature -> [(function, (pattern, edit), expected count)]
FEATURES = {
    "markers": [
        ("sub_82586768", compare_edit("r3", 2, "nfsmw_markers_to_pick()", "nfsmw-markers"), 2),
        ("sub_82586E78", subfic_edit(2, "nfsmw_markers_to_pick()", "nfsmw-markers"), 2),
    ],
    "car-limit": [
        ("sub_82564B88",
         compare_edit("r3", 10, "nfsmw_purchased_car_limit()", "nfsmw-car-limit"), 1),
    ],
    # The shadow map's size (not an Extra Options feature: a graphics setting).
    # sub_82454C18 creates it: a 1600x1600 render target descriptor (width and
    # height both from one 'li r11,1600') for sub_8245D1B8, and two 1600x1600
    # textures from sub_82589EA8 ('li r4,1600', 'li r3,1600').
    "shadow-size": [
        ("sub_82454C18", li_edit(1600, "nfsmw_shadow_map_size()", "nfsmw-shadow-size"), 3),
    ],
    # The game's own SkipMovies (the debug setting SKIPMOVIES, the word at
    # 0x82A2CE1C; Extra Options' SkipMovies sets it on PC): its three readers
    # see it set while nfsmw_skip_movies() is 1 (ios/src/game_extra_options.cpp).
    "skip-movies": [
        (fn, load_or_edit("r11", "r11", -12772, "nfsmw_skip_movies()", "nfsmw-skip-movies"), 1)
        for fn in ("sub_82282F18", "sub_822BBA98", "sub_824792D8")
    ],
}
MARKS = {"markers": ("nfsmw-markers", 6), "car-limit": ("nfsmw-car-limit", 1),
         "shadow-size": ("nfsmw-shadow-size", 3), "skip-movies": ("nfsmw-skip-movies", 3)}


def fail(msg):
    print(f"[error] {msg}\n        Nothing was written.")
    sys.exit(1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--dir", default=str(GENERATED))
    args = ap.parse_args()
    gen = pathlib.Path(args.dir)
    if not any(gen.glob("*.cpp")):
        fail(f"no generated code in {gen}")

    if args.status:
        texts = [p.read_text(encoding="utf-8") for p in gen.glob("*.cpp")]
        parts, applied = [], True
        for feature, (mark, expected) in MARKS.items():
            n = sum(t.count(f"// {mark}") for t in texts)
            applied &= n == expected
            parts.append(f"{feature} {n}/{expected}")
        print(f"[extra-options] {'applied' if applied else 'NOT applied'}: {', '.join(parts)}")
        return 0

    wanted = {fn for edits in FEATURES.values() for fn, _, _ in edits}
    found = {(f, fn): 0 for f, edits in FEATURES.items() for fn, _, _ in edits}
    pending = {}
    for path in sorted(gen.glob("*.cpp")):
        text = path.read_text(encoding="utf-8")
        if not any(fn in text for fn in wanted):
            continue
        lines = text.split("\n")
        changed = False
        fn = None
        for i in range(len(lines)):
            m = FUNC.match(lines[i])
            if m:
                fn = m.group(1)
            for feature, edits in FEATURES.items():
                for efn, (pattern, edit), _ in edits:
                    if fn != efn:
                        continue
                    mm = pattern.match(lines[i])
                    if not mm:
                        continue
                    old, new = edit(mm, lines)
                    span = lines[i + 1:i + 1 + len(old)]
                    if span == old:
                        lines[i + 1:i + 1 + len(old)] = new
                        changed = True
                    elif span != new:
                        fail(f"{fn}: unexpected C++ after '{lines[i].strip()}': "
                             f"{span[0].strip() if span else '(end)'}")
                    found[(feature, efn)] += 1
        if changed:
            if "nfsmw_skip_movies();" not in "\n".join(lines[:80]):
                inc = next((k for k, l in enumerate(lines)
                            if l.startswith('#include "nfsmw_funcs.')), None)
                if inc is None:
                    fail(f"{path.name}: no #include \"nfsmw_funcs.*.h\" for the declarations")
                lines.insert(inc + 1, "\n" + DECLS.rstrip("\n"))
            pending[path] = "\n".join(lines)

    for feature, edits in FEATURES.items():
        for fn, _, expected in edits:
            if found[(feature, fn)] != expected:
                fail(f"{feature}: {fn}: found {found[(feature, fn)]} place(s), expected "
                     f"{expected}. Is this the USA edition?")
    for path, text in pending.items():
        path.write_text(text, encoding="utf-8")
    print(f"[extra-options] {'patched' if pending else 'already patched'}: "
          f"{', '.join(FEATURES)} ({len(pending)} file(s) written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
