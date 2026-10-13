#!/usr/bin/env python3
"""
XMA frames handed to the game as soon as they are decoded (Xenia Canary),
as a test switch.

    python3 tools/ios/patch_ios_xma_direct_output.py            apply
    python3 tools/ios/patch_ios_xma_direct_output.py --status
    python3 tools/ios/patch_ios_xma_direct_output.py --revert

Touches src/audio/xma_context.cpp.


WHY
===

In police chases the game starts ~100 sound streams a second, every one is
reset by the stall detector exactly 6 times with 20 blocks unread, and the
whole mix goes silent for 245 ms at a time. Decoding is cheap (~60 ms of
work a second, longest 2 ms), so the decoder keeps up. The SDK's decoder
(unlike Canary's) realigns FFmpeg's output by its 192-sample start padding:
each frame's sound is handed over one decode later, together with the next
frame's head, and the first frame of a stream gives nothing. A stream of
one or two frames, or one whose next input arrives late, then delivers
nothing in time. With ios_xma_direct_output on, each decoded frame goes out
at once, as in Canary (loop limits and skips as Canary applies them).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

ANCHOR = '''  if (decoded) {
    ConvertFrame(reinterpret_cast<const uint8_t**>(&av_frame_->data), bool(data->is_stereo),
                 decoded_frame_.data());
'''
NEW = '''  if (decoded && REXCVAR_GET(ios_xma_direct_output)) {
    // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_direct_output.py): the frame
    // out at once, as Xenia Canary does.
    ConvertFrame(reinterpret_cast<const uint8_t**>(&av_frame_->data), bool(data->is_stereo),
                 raw_frame_.data());
    carry_valid_ = false;
    current_frame_remaining_subframes_ = 4 << data->is_stereo;
    loop_frame_output_limit_ =
        is_loop_end_frame ? static_cast<uint8_t>((data->loop_subframe_end + 1) << data->is_stereo) : 0;
    if (loop_start_skip_pending_) {
      const uint8_t skip = static_cast<uint8_t>(data->loop_subframe_skip << data->is_stereo);
      if (skip < current_frame_remaining_subframes_) current_frame_remaining_subframes_ -= skip;
      loop_start_skip_pending_ = false;
    }
  } else if (decoded) {
    ConvertFrame(reinterpret_cast<const uint8_t**>(&av_frame_->data), bool(data->is_stereo),
                 decoded_frame_.data());
'''

CVAR_ANCHOR = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py).
static std::atomic<uint64_t> ios_xma_codec_reopens{0};
'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py).
static std::atomic<uint64_t> ios_xma_codec_reopens{0};
// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_direct_output.py).
REXCVAR_DEFINE_BOOL(ios_xma_direct_output, false, "Audio",
                    "iOS: hand each decoded XMA frame to the game at once (Xenia Canary), without "
                    "the start-padding realignment");
'''

BLOCKS = [
    (FILE, "the ios_xma_direct_output cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "decoded frames out at once", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_direct_output", BLOCKS))
