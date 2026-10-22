#!/usr/bin/env python3
"""
The game's deferred-call queue: publish an entry before its count (USA code).

    python3 tools/ios/patch_game_deferred_queue.py            apply
    python3 tools/ios/patch_game_deferred_queue.py --status
    python3 tools/ios/patch_game_deferred_queue.py --revert

sub_823C8210 appends an entry (function pointer, size, copied data) to a queue
at 0x82919650, then advances the queue's end (+20) and count (+0). sub_823C8290
(called from the main loop) runs pending entries: it reads the end and count,
then each entry's function pointer, and calls it. The recompiled code has no
ordering between the two threads, so on ARM the consumer can see the new end
before the entry's function pointer: it called address 0 ("[FATAL] Call to
invalid or unregistered function at guest address 0x00000000", lr 0x823C82F8,
r3 = the entry, r4 = 0), the crash near the first safehouse since 2026-10-12.

Fix: a release fence before the producer advances the end, an acquire fence
after the consumer reads it, and, if a function pointer still reads 0, a short
bounded re-read (an entry being written) before the original call.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-deferred-queue"

PRODUCER = ("nfsmw_recomp.48.cpp", "DEFINE_REX_FUNC(sub_823C8210) {",
            "\tREX_STORE_U32(ctx.r31.u32 + 20, ctx.r11.u32);\n",
            f"\t__atomic_thread_fence(__ATOMIC_RELEASE); // {MARK}\n")
CONSUMER_END = ("nfsmw_recomp.100.cpp", "DEFINE_REX_FUNC(sub_823C8290) {",
                "\tctx.r11.u64 = REX_LOAD_U32(ctx.r31.u32 + 20);\n",
                f"\t__atomic_thread_fence(__ATOMIC_ACQUIRE); // {MARK}\n")
CONSUMER_CALL = ("nfsmw_recomp.100.cpp", "DEFINE_REX_FUNC(sub_823C8290) {",
                 "\t// mtctr r4\n\tctx.ctr.u64 = ctx.r4.u64;\n",
                 f"\tfor (int nfsmw_spin = 0; !ctx.r4.u32 && nfsmw_spin < 200000; ++nfsmw_spin) {{ // {MARK}\n"
                 f"\t\t__builtin_arm_yield(); // {MARK}\n"
                 f"\t\t__atomic_thread_fence(__ATOMIC_ACQUIRE); // {MARK}\n"
                 f"\t\tctx.r4.u64 = REX_LOAD_U32(ctx.r30.u32 + 0); // {MARK}\n"
                 f"\t}} // {MARK}\n")
# (file, function, anchor, inserted text, after?)
SITES = [(*PRODUCER, False), (*CONSUMER_END, True), (*CONSUMER_CALL, False)]


def function_bounds(text, head):
    a = text.index(head)
    b = text.find("\nDEFINE_REX_FUNC(", a + 1)
    return a, (b if b >= 0 else len(text))


def apply(gen, revert=False, status=False):
    changed = {}
    for name, head, anchor, insert, after in SITES:
        path = gen / name
        text = changed.get(path) or path.read_text()
        a, b = function_bounds(text, head)
        body = text[a:b]
        patched = (anchor + insert) if after else (insert + anchor)
        if status:
            print(f"  {'yes' if patched in body else ' NO'}  {head[16:-3]} {anchor.strip()[:40]}")
            continue
        if revert:
            if patched in body:
                body = body.replace(patched, anchor, 1)
        elif patched not in body:
            if body.count(anchor) != 1:
                sys.exit(f"[ERROR] {name}: anchor not found exactly once in {head}")
            body = body.replace(anchor, patched, 1)
        changed[path] = text[:a] + body + text[b:]
    for path, text in changed.items():
        path.write_text(text)
    if not status:
        print(f"[ok] deferred_queue: {'reverted' if revert else 'applied'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    apply(pathlib.Path(a.dir), revert=a.revert, status=a.status)
