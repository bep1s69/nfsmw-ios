#!/usr/bin/env python3
"""
The game's render thread sleeps while its deferred-call queue is empty (USA code).

    python3 tools/ios/patch_game_queue_wait.py            apply
    python3 tools/ios/patch_game_queue_wait.py --status
    python3 tools/ios/patch_game_queue_wait.py --revert

sub_82441B60 (the render thread's main loop) keeps calling the queue runner
sub_823C8290 with the number of pending entries (written - run) until the
frame's end flag is set; while the world thread has not queued more, that
number is 0 and the loop spins (Nov 16 iPad profile: ~13 % of the thread).
Here an empty queue waits (ios/src/game_queue_wait.cpp: woken by the
producer sub_823C8210 after it publishes an entry, at most 250 us).
"""
import argparse
import pathlib
import sys

import game_edition

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-queue-wait"
DECL = (f'extern "C" void nfsmw_queue_wait(uint8_t* base, uint32_t queue); // {MARK}\n'
        f'extern "C" void nfsmw_queue_wake(); // {MARK}\n')
SITES = [
    (game_edition.usa("DEFINE_REX_FUNC(sub_82441B60) {"),
     "\tctx.lr = 0x82441C5C;\n\tsub_823C8290(ctx, base);\n",
     f"\tif (!ctx.r4.u32) nfsmw_queue_wait(base, ctx.r30.u32); // {MARK}\n", False),
    (game_edition.usa("DEFINE_REX_FUNC(sub_823C8210) {"),
     "\t__atomic_thread_fence(__ATOMIC_RELEASE); // nfsmw-deferred-queue\n",
     f"\tnfsmw_queue_wake(); // {MARK}\n", True),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    gen = pathlib.Path(a.dir)
    for head, anchor, insert, after in SITES:
        paths = [x for x in sorted(gen.glob("nfsmw_recomp.*.cpp")) if head in x.read_text()]
        if len(paths) != 1:
            sys.exit(f"[ERROR] {head}: found in {len(paths)} generated files")
        path = paths[0]
        text = path.read_text()
        start = text.index(head)
        end = text.find("\nDEFINE_REX_FUNC(", start + 1)
        end = end if end >= 0 else len(text)
        body = text[start:end]
        patched = anchor + insert if after else insert + anchor
        if a.status:
            print(f"  {'yes' if patched in body else ' NO'}  {head[16:-3]}")
            continue
        if a.revert:
            body = body.replace(patched, anchor, 1)
        elif patched not in body:
            if body.count(anchor) != 1:
                sys.exit(f"[ERROR] anchor not found exactly once in {head}")
            body = body.replace(anchor, patched, 1)
        text = text[:start] + body + text[end:]
        if a.revert:
            text = text.replace(DECL, "", 1)
        elif DECL not in text:
            first = text.index("DEFINE_REX_FUNC(")
            text = text[:first] + DECL + text[first:]
        path.write_text(text)
    if not a.status:
        print(f"[ok] queue_wait: {'reverted' if a.revert else 'applied'}")


if __name__ == "__main__":
    main()
