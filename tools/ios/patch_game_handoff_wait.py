#!/usr/bin/env python3
"""
The frame hand-off waits sleep until the hand-off (USA code).

    python3 tools/ios/patch_game_handoff_wait.py            apply
    python3 tools/ios/patch_game_handoff_wait.py --status
    python3 tools/ios/patch_game_handoff_wait.py --revert

The main loop and the render thread hand each frame over through the word
0x82A2CF40 and wait for each other with Sleep(0) loops (~6,900 wake-ups a
second on the iPad, Nov 4). The two waits' Sleep(0) calls go through
nfsmw_handoff_wait (ios/src/game_handoff_wait.cpp), which sleeps on the word;
the two stores to the word are followed by nfsmw_handoff_wake. Off
(nfsmw_handoff_wait false), the waits sleep as before.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-handoff-wait"
DECL = (f'extern "C" bool nfsmw_handoff_wait(uint8_t* base, uint32_t waiting_value); // {MARK}\n'
        f'extern "C" void nfsmw_handoff_wake(uint8_t* base); // {MARK}\n')


def sleep_site(lr, value):
    old = f"\tctx.lr = 0x{lr};\n\tsub_8262D790(ctx, base);\n"
    new = (f"\tctx.lr = 0x{lr};\n\tif (!nfsmw_handoff_wait(base, {value})) sub_8262D790(ctx, base);"
           f" // {MARK}\n")
    return old, new


def store_site(store):
    old = f"\t{store}\n"
    return old, old + f"\tnfsmw_handoff_wake(base); // {MARK}\n"


# function -> edits (anchor, replacement), each anchor exactly once in the function
SITES = {
    # main loop: while the word is 1
    "sub_82441DB0": [sleep_site("82441E4C", 1)],
    # render thread: while the word is 0; then stores 0 (r26 = 0)
    "sub_82441B60": [sleep_site("82441BBC", 0),
                     store_site("REX_STORE_U32(ctx.r27.u32 + -12480, ctx.r26.u32);")],
    # main loop hands the frame over: stores 1 (r4 = 1, r9 = 0x82A30000)
    "sub_82441EF0": [store_site("REX_STORE_U32(ctx.r9.u32 + -12480, ctx.r4.u32);")],
}


def apply(gen, revert=False, status=False):
    states = []
    for fn, edits in SITES.items():
        head = f"DEFINE_REX_FUNC({fn}) {{"
        paths = [p for p in sorted(gen.glob("nfsmw_recomp.*.cpp")) if head in p.read_text()]
        if len(paths) != 1:
            sys.exit(f"[ERROR] {fn}: found in {len(paths)} generated files")
        path = paths[0]
        text = path.read_text()
        a = text.index(head)
        b = text.find("\nDEFINE_REX_FUNC(", a + 1)
        b = b if b >= 0 else len(text)
        body = text[a:b]
        done = [new in body for _, new in edits]
        states.append((fn, path.name, sum(done), len(edits)))
        if status:
            continue
        if revert:
            for old, new in edits:
                body = body.replace(new, old, 1)
            text = text[:a] + body + text[b:]
            text = text.replace(DECL + head, head, 1)
        else:
            if all(done):
                continue
            if any(done):
                sys.exit(f"[ERROR] {fn}: partly applied; revert first")
            for old, new in edits:
                if body.count(old) != 1:
                    sys.exit(f"[ERROR] {path.name}: anchor not found exactly once in {fn}: {old!r}")
                body = body.replace(old, new, 1)
            text = text[:a] + body + text[b:]
            text = text.replace(head, DECL + head, 1)
        path.write_text(text)
    if status:
        total = sum(s[2] for s in states)
        need = sum(s[3] for s in states)
        print(f"[handoff-wait] {'applied' if total == need else 'not applied'} ({total} of {need} sites)")
        for fn, name, n, m in states:
            print(f"    {fn} ({name}): {n} of {m}")
    else:
        print(f"[ok] handoff_wait: {'reverted' if revert else 'applied'} "
              f"({sum(len(e) for e in SITES.values())} sites)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    apply(pathlib.Path(a.dir), revert=a.revert, status=a.status)
