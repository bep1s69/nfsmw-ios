#!/usr/bin/env python3
"""
The game's render hand-off can be made single-threaded (USA code).

    python3 tools/ios/patch_game_render_handoff.py            apply
    python3 tools/ios/patch_game_render_handoff.py --status
    python3 tools/ios/patch_game_render_handoff.py --revert

At the end of each main-loop frame sub_82441050 picks how the frame is
drawn: when [0x82912F50+32] is 6 (gameplay, inferred) the flag 0x828FBB50
becomes 1 and sub_82441EF0 hands the frame to the render thread (state
0x82A2CF40 = 1), which draws it while the main loop already updates the next
frame (the next frame's sub_82441DB0 waits for the state to leave 1 before
handing over again); otherwise sub_82441E70 draws on the main loop thread.
The camera log (Oct 28) shows the drawn camera running one update ahead for
1-3 frames in stretches: consistent with the render thread reading camera
data the main loop is already updating for the next frame. With
nfsmw_render_single_thread (ios/src/frame_clock.cpp) the comparison is made
to fail, so gameplay frames take the single-threaded path.
"""
import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MARK = "nfsmw-render-handoff"
FILE = "nfsmw_recomp.45.cpp"
HEAD = "DEFINE_REX_FUNC(sub_82441050) {"
DECL = f'extern "C" bool nfsmw_render_single_thread(); // {MARK}\n'
ANCHOR = "loc_824410A8:\n\t// clrlwi r8,r11,24\n"
INSERT = f"\tif (ctx.r11.u32 && nfsmw_render_single_thread()) ctx.r11.s64 = 0; // {MARK}\n"


def apply(gen, revert=False, status=False):
    path = gen / FILE
    text = path.read_text()
    a = text.index(HEAD)
    b = text.find("\nDEFINE_REX_FUNC(", a + 1)
    b = b if b >= 0 else len(text)
    body = text[a:b]
    PATCHED = ANCHOR.split('\n')[0] + '\n' + INSERT + ANCHOR.split('\n', 1)[1]
    done = PATCHED in body and DECL + HEAD in text
    if status:
        print(f"[render-handoff] {'applied' if done else 'not applied'}")
        return
    if revert:
        body = body.replace(PATCHED, ANCHOR, 1)
        text = text[:a] + body + text[b:]
        text = text.replace(DECL + HEAD, HEAD, 1)
    elif not done:
        if body.count(ANCHOR) != 1:
            sys.exit(f"[ERROR] {FILE}: the state-6 test not found exactly once in sub_82441050")
        body = body.replace(ANCHOR, ANCHOR.split('\n')[0] + '\n' + INSERT + ANCHOR.split('\n', 1)[1], 1)
        text = text[:a] + body + text[b:]
        text = text.replace(HEAD, DECL + HEAD, 1)
    path.write_text(text)
    print(f"[ok] render_handoff: {'reverted' if revert else 'applied'}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dir", default=str(ROOT / "ios/generated/default"))
    p.add_argument("--status", action="store_true")
    p.add_argument("--revert", action="store_true")
    a = p.parse_args()
    apply(pathlib.Path(a.dir), revert=a.revert, status=a.status)
