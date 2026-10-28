#!/usr/bin/env python3
"""
The main loop's tick count goes through the app (USA code).

    python3 tools/ios/patch_game_frame_ticks.py            apply
    python3 tools/ios/patch_game_frame_ticks.py --status
    python3 tools/ios/patch_game_frame_ticks.py --revert

sub_823B0008 is the game's main loop: it polls the timebase (mftb >> 2),
turns the time since the last frame into seconds (f0, clamped to f31), waits
until that is over f10, then runs a frame (sub_823AFE20) with
r3 = (int)(f0 * f30), truncated (fctiwz), and restarts its count from now.
The camera log (Oct 28, IPA117/118) shows the camera stepping 2x, 0, 2x, 0
in stretches: frame periods jitter around a whole number of ticks, so the
truncation gives one tick less on one frame (its remainder thrown away) and
more on another. Before the fctiwz, f9 (elapsed * rate) now goes through
nfsmw_frame_ticks (ios/src/frame_clock.cpp), which logs it and can carry the
remainder (cvar nfsmw_frame_ticks).

Also (IPA123): right after the frame (the call to sub_823AFE20), the loop
calls nfsmw_frame_pace, which can wait until just after the next display
refresh (cvar nfsmw_frame_pace), so each frame starts on the refresh grid as
on the 360. IPA122 measured the frames at 13.5 / 19.5 ms alternating and
40-45 ms stalls followed by 6, 6, 9 ms catch-up frames: the loop was paced
only by back-pressure from the GPU queue.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-frame-ticks"
FILE = "nfsmw_recomp.89.cpp"
HEAD = "DEFINE_REX_FUNC(sub_823B0008) {"
DECL = (f'extern "C" double nfsmw_frame_ticks(double ticks, double seconds, double rate, double wait, double clamp); // {MARK}\n'
        f'extern "C" void nfsmw_frame_pace(); // {MARK}\n')
ANCHOR = "\t// fctiwz f8,f9\n"
CALL = "\tsub_823AFE20(ctx, base);\n"
PACE = f"\tnfsmw_frame_pace(); // {MARK}\n"
INSERT = (f"\tctx.f9.f64 = nfsmw_frame_ticks(ctx.f9.f64, ctx.f0.f64, ctx.f30.f64, ctx.f10.f64, ctx.f31.f64); "
          f"// {MARK}\n")


def apply(gen, revert=False, status=False):
    path = gen / FILE
    text = path.read_text()
    a = text.index(HEAD)
    b = text.find("\nDEFINE_REX_FUNC(", a + 1)
    b = b if b >= 0 else len(text)
    body = text[a:b]
    done = INSERT + ANCHOR in body and CALL + PACE in body and DECL + HEAD in text
    if status:
        print(f"[frame-ticks] {'applied' if done else 'not applied'}")
        return
    if revert:
        body = body.replace(INSERT + ANCHOR, ANCHOR, 1).replace(CALL + PACE, CALL, 1)
        text = text[:a] + body + text[b:]
        text = text.replace(DECL + HEAD, HEAD, 1)
    elif not done:
        if body.count(ANCHOR) != 1:
            sys.exit(f"[ERROR] {FILE}: fctiwz f8,f9 not found exactly once in sub_823B0008")
        body = body.replace(ANCHOR, INSERT + ANCHOR, 1)
        if body.count(CALL) != 1:
            sys.exit(f"[ERROR] {FILE}: the frame call not found exactly once in sub_823B0008")
        body = body.replace(CALL, CALL + PACE, 1)
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
