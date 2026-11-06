#!/usr/bin/env python3
"""
Give each XMA context its FFmpeg decoder only while the game uses it (low-RAM).

    python3 tools/ios/patch_ios_xma_lazy_codec.py            apply
    python3 tools/ios/patch_ios_xma_lazy_codec.py --status
    python3 tools/ios/patch_ios_xma_lazy_codec.py --revert

Touches src/audio/xma_context.cpp. Builds on patch_ios_xma_starve_mono.py.


WHY
===

Instruments on the iPhone (dev94, November 6): 320 heap blocks of 464 KiB
(145 MiB), all from av_mallocz in librexruntime, and ~324 blocks of 128 KiB.
The decoder has 320 XMA contexts. Each kept an FFmpeg codec context (its
private data is the 464 KiB block) from Setup on, and a 128 KiB packet
buffer that is never read (the packet's data points at xma_frame_). The game
uses a few dozen contexts at once but hands them out round-robin, so after a
while all 320 hold a codec. Now the codec is made when PrepareDecoder first
needs it and freed when the game releases the context; the packet carries no
buffer of its own (FFmpeg copies the small frame on send). A released context
already reopened its codec on next use (ResetDecoderState), so this adds no
codec opens. ios_xma_lazy_codec=false restores the old behaviour.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

CVAR_ANCHOR = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_mono.py).
REXCVAR_DEFINE_BOOL(ios_xma_starve_keep_mono, true, "Audio",
'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py).
REXCVAR_DEFINE_BOOL(ios_xma_lazy_codec, true, "Audio",
                    "iOS: each XMA context has an FFmpeg decoder (464 KiB) only while the game uses it, "
                    "not all 320 from the start (~180 MiB less memory)");
// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_starve_mono.py).
REXCVAR_DEFINE_BOOL(ios_xma_starve_keep_mono, true, "Audio",
'''

SETUP_ANCHOR = '''  av_packet_ = av_packet_alloc();
  assert_not_null(av_packet_);
  av_packet_->buf = av_buffer_alloc(128 * 1024);
'''
SETUP_NEW = '''  av_packet_ = av_packet_alloc();
  assert_not_null(av_packet_);
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): the packet's
  // data is xma_frame_, so its own 128 KiB buffer was never read.
  if (!REXCVAR_GET(ios_xma_lazy_codec)) {
    av_packet_->buf = av_buffer_alloc(128 * 1024);
  }
'''

ALLOC_ANCHOR = '''  av_context_ = avcodec_alloc_context3(av_codec_);
  if (!av_context_) {
    REXAPU_ERROR("XmaContext {}: Couldn't allocate context", id);
    return 1;
  }

  // Initialize these to 0. They'll actually be set later.
  av_context_->channels = 0;
  av_context_->sample_rate = 0;
'''
ALLOC_NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): with
  // ios_xma_lazy_codec PrepareDecoder makes the codec context on first use.
  if (!REXCVAR_GET(ios_xma_lazy_codec)) {
    av_context_ = avcodec_alloc_context3(av_codec_);
    if (!av_context_) {
      REXAPU_ERROR("XmaContext {}: Couldn't allocate context", id);
      return 1;
    }

    // Initialize these to 0. They'll actually be set later.
    av_context_->channels = 0;
    av_context_->sample_rate = 0;
  }
'''

RELEASE_ANCHOR = '''  set_is_allocated(false);
  ResetDecoderState();
'''
RELEASE_NEW = '''  set_is_allocated(false);
  ResetDecoderState();
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): the next user
  // reopens the codec anyway; free its 464 KiB until then.
  if (REXCVAR_GET(ios_xma_lazy_codec) && av_context_) {
    avcodec_free_context(&av_context_);
  }
'''

PREPARE_ANCHOR = '''  if (av_context_->sample_rate != sample_rate ||
      av_context_->channels != static_cast<int>(channels)) {
'''
PREPARE_NEW = '''  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): no codec yet.
  if (!av_context_ || av_context_->sample_rate != sample_rate ||
      av_context_->channels != static_cast<int>(channels)) {
'''

FREE_ANCHOR = '''    avcodec_free_context(&av_context_);
    av_context_ = avcodec_alloc_context3(av_codec_);

    av_context_->sample_rate = sample_rate;
'''
FREE_NEW = '''    if (av_context_) avcodec_free_context(&av_context_);  // LOCAL PATCH - iOS (patch_ios_xma_lazy_codec.py)
    av_context_ = avcodec_alloc_context3(av_codec_);
    if (!av_context_) {
      REXAPU_ERROR("XmaContext {}: Couldn't allocate context", id());
      return -1;
    }

    av_context_->sample_rate = sample_rate;
'''

BLOCKS = [
    (FILE, "the ios_xma_lazy_codec cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "no unused 128 KiB packet buffer", SETUP_ANCHOR, SETUP_NEW),
    (FILE, "no codec context at setup", ALLOC_ANCHOR, ALLOC_NEW),
    (FILE, "codec context freed on release", RELEASE_ANCHOR, RELEASE_NEW),
    (FILE, "codec context made on first decode", PREPARE_ANCHOR, PREPARE_NEW),
    (FILE, "reopen tolerates a missing context", FREE_ANCHOR, FREE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_lazy_codec", BLOCKS))
