#!/usr/bin/env python3
"""
Car reflection faces and the rear-view mirror left out in the game (USA code).

    python3 tools/ios/patch_game_pass_cadence.py            apply
    python3 tools/ios/patch_game_pass_cadence.py --status
    python3 tools/ios/patch_game_pass_cadence.py --revert

The game's render thread runs its frame from the deferred-call queue
(sub_823C8290; entries are a function, a size and data). dev203's log
(Nov 17) shows each environment cube face as a block from sub_82463498
(begin face) to sub_824634A0 (end face, data = view 18 + face), and the
mirror from sub_82463488 to sub_82463490. Before the runner calls an entry
it asks nfsmw_pass_cadence_skip (ios/src/game_pass_cadence.cpp), which
leaves out whole blocks on the frames the chosen update rates skip.
"""
import argparse
import pathlib
import sys

import game_edition

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-pass-cadence"
HEAD = game_edition.usa("DEFINE_REX_FUNC(sub_823C8290) {")
DECL = f'extern "C" bool nfsmw_pass_cadence_skip(uint8_t* base, uint32_t entry, uint32_t fn); // {MARK}\n'
ANCHOR = "\tctx.lr = 0x823C82F8;\n\tREX_CALL_INDIRECT_FUNC(ctx.ctr.u32);\n"
PATCHED = ("\tctx.lr = 0x823C82F8;\n"
           f"\tif (!nfsmw_pass_cadence_skip(base, ctx.r30.u32, ctx.ctr.u32)) REX_CALL_INDIRECT_FUNC(ctx.ctr.u32); // {MARK}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    gen = pathlib.Path(a.dir)
    paths = [x for x in sorted(gen.glob("nfsmw_recomp.*.cpp")) if HEAD in x.read_text()]
    if len(paths) != 1:
        sys.exit(f"[ERROR] sub_823C8290 found in {len(paths)} generated files")
    path = paths[0]
    text = path.read_text()
    start = text.index(HEAD)
    end = text.find("\nDEFINE_REX_FUNC(", start + 1)
    end = end if end >= 0 else len(text)
    body = text[start:end]
    if a.status:
        print(f"  {'yes' if PATCHED in body else ' NO'}  pass cadence in sub_823C8290")
        return
    if a.revert:
        body = body.replace(PATCHED, ANCHOR, 1)
        text = text.replace(DECL, "", 1)
    else:
        if PATCHED not in body:
            if body.count(ANCHOR) != 1:
                sys.exit("[ERROR] runner call site not found exactly once")
            body = body.replace(ANCHOR, PATCHED, 1)
        if DECL not in text[:start]:
            text = text[:start] + DECL + text[start:]
            start += len(DECL)
            end += len(DECL)
    text = text[:start] + body + text[end:]
    path.write_text(text)
    print(f"[ok] pass_cadence: {'reverted' if a.revert else 'applied'}")


if __name__ == "__main__":
    main()
