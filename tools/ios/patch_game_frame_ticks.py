#!/usr/bin/env python3
"""
The main loop's frame time goes through the app (USA code).

    python3 tools/ios/patch_game_frame_ticks.py            apply
    python3 tools/ios/patch_game_frame_ticks.py --status
    python3 tools/ios/patch_game_frame_ticks.py --revert

sub_823B0008 is the game's main loop: it polls the timebase (mftb >> 2),
turns the time since the last frame into milliseconds (f0), waits until that
is over f10, then runs a frame (sub_823AFE20) with r3 = (int)(f0 * f30)
(f30 = 65536: 16.16 fixed point) and restarts its count from now. The world
and camera step by that time.

Nothing paces that loop to the refresh: it runs until the GPU queue pushes
back, so its frames came at 13.5 / 19.5 ms alternating, with 30-45 ms stalls
and quick 5-12 ms catch-up frames (Oct 28, IPA122), while the screen showed
one frame per refresh: the motion judders with every frame on time (D-005).
Before the fctiwz, f9 (f0 * f30) now goes through nfsmw_frame_ticks
(ios/src/frame_clock.cpp), which gives each frame one display period
(cvar nfsmw_frame_ticks, see there).
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-frame-ticks"
FILE = "nfsmw_recomp.89.cpp"
HEAD = "DEFINE_REX_FUNC(sub_823B0008) {"
DECL = f'extern "C" double nfsmw_frame_ticks(double ticks, double milliseconds, double rate, double wait, double clamp); // {MARK}\n'
ANCHOR = "\t// fctiwz f8,f9\n"
INSERT = (f"\tctx.f9.f64 = nfsmw_frame_ticks(ctx.f9.f64, ctx.f0.f64, ctx.f30.f64, ctx.f10.f64, ctx.f31.f64); "
          f"// {MARK}\n")


def apply(gen, revert=False, status=False):
    path = gen / FILE
    text = path.read_text()
    a = text.index(HEAD)
    b = text.find("\nDEFINE_REX_FUNC(", a + 1)
    b = b if b >= 0 else len(text)
    body = text[a:b]
    done = INSERT + ANCHOR in body and DECL + HEAD in text
    if status:
        print(f"[frame-ticks] {'applied' if done else 'not applied'}")
        return
    if revert:
        body = body.replace(INSERT + ANCHOR, ANCHOR, 1)
        text = text[:a] + body + text[b:]
        text = text.replace(DECL + HEAD, HEAD, 1)
    elif not done:
        if body.count(ANCHOR) != 1:
            sys.exit(f"[ERROR] {FILE}: fctiwz f8,f9 not found exactly once in sub_823B0008")
        body = body.replace(ANCHOR, INSERT + ANCHOR, 1)
        text = text[:a] + body + text[b:]
        text = text.replace(HEAD, DECL + HEAD, 1)
    path.write_text(text)
    print(f"[ok] frame_ticks: {'reverted' if revert else 'applied'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    apply(pathlib.Path(a.dir), revert=a.revert, status=a.status)
