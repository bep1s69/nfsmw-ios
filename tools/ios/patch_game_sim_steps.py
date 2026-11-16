#!/usr/bin/env python3
"""
The 120 Hz simulation counts its steps at the simulation rate (USA code).

    python3 tools/ios/patch_game_sim_steps.py            apply
    python3 tools/ios/patch_game_sim_steps.py --status
    python3 tools/ios/patch_game_sim_steps.py --revert

nfsmw_sim_rate 120 (game_extra_options.cpp) makes the shared 1/60 step
(0x820AFDD0) 1/120. Two functions that run the world's fixed steps,
sub_823C66C8 and sub_823C6858, add the frame's time to an accumulator, take
steps = (int)(accumulator * 60.0) (0x82057114, a shared 60.0 left as it is)
and subtract steps * the step. At 120 Hz that counted with the 60 Hz rule
and subtracted 1/120 per step: the accumulator settled at two steps' worth
(33.33 ms) and, with a frame time of exactly 16.6667 ms (the iPad), sat on
the boundary of 1, 2 or 3 steps a frame: the camera's sawtooth (Nov 3).
The multiplier now goes through nfsmw_sim_steps_per_second
(game_extra_options.cpp): 1 / the step in use, i.e. 120 at 120 Hz, the
game's own 60 otherwise.
"""
import argparse
import pathlib
import sys

import game_edition

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-sim-steps"
DECL = f'extern "C" double nfsmw_sim_steps_per_second(double rate); // {MARK}\n'
# (function, register loaded from 28948(r10), i.e. 0x82057114 = 60.0)
SITES = [(game_edition.usa("sub_823C66C8"), "f12"), (game_edition.usa("sub_823C6858"), "f11")]


def anchor(reg):
    return (f"\t// lfs {reg},28948(r10)\n\ttemp.u32 = REX_LOAD_U32(ctx.r10.u32 + 28948);\n"
            f"\tctx.{reg}.f64 = double(temp.f32);\n")


def insert(reg):
    return f"\tctx.{reg}.f64 = nfsmw_sim_steps_per_second(ctx.{reg}.f64); // {MARK}\n"


def apply(gen, revert=False, status=False):
    results = []
    for fn, reg in SITES:
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
        done = anchor(reg) + insert(reg) in body
        results.append((fn, path.name, done))
        if status:
            continue
        if revert:
            if done:
                body = body.replace(anchor(reg) + insert(reg), anchor(reg), 1)
                text = text[:a] + body + text[b:]
                text = text.replace(DECL + head, head, 1)
        elif not done:
            if body.count(anchor(reg)) != 1:
                sys.exit(f"[ERROR] {path.name}: the 60.0 load into {reg} not found exactly once in {fn}")
            body = body.replace(anchor(reg), anchor(reg) + insert(reg), 1)
            text = text[:a] + body + text[b:]
            text = text.replace(head, DECL + head, 1)
        path.write_text(text)
    if status:
        for fn, name, done in results:
            print(f"[sim-steps] {fn} ({name}): {'applied' if done else 'not applied'}")
    else:
        print(f"[ok] sim_steps: {'reverted' if revert else 'applied'} ({len(SITES)} sites)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    apply(pathlib.Path(a.dir), revert=a.revert, status=a.status)
