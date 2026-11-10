#!/usr/bin/env python3
"""
Reuse flushed XMA codecs instead of reopening one for every new stream (CPU).

    NFSMW_SDK=... python3 tools/ios/patch_ios_xma_codec_pool.py            apply
    NFSMW_SDK=... python3 tools/ios/patch_ios_xma_codec_pool.py --status
    NFSMW_SDK=... python3 tools/ios/patch_ios_xma_codec_pool.py --revert

Touches thirdparty/FFmpeg/libavcodec/wmaprodec.c and src/audio/xma_context.cpp.
Builds on patch_ios_xma_lazy_codec.py and patch_ios_xma_reset_stats.py.


WHY
===

dev110 iPhone pursuit Time Profiler (November 10): ~9 % of the game's audio
thread is XmaContext::PrepareDecoder -> avcodec_open2 -> ff_mdct_init, i.e.
building MDCT tables for a fresh FFmpeg codec each time the game starts a new
stream on a context (the [xma-work] line counts ~5 reopens a second). The
reopen exists only to drop the previous stream's overlap-add history, because
ff_xmaframes_decoder had no flush callback.

Change: (1) ff_xmaframes_decoder gets a flush callback that restores the
state decode_init leaves (output history zeroed, packet_loss = 1, previous
block lengths = the frame length, frame counter 0); (2) a released context's
codec is flushed and kept in a small process-wide pool by (sample rate,
channels), at most 32 (~15 MiB), and PrepareDecoder takes one from the pool
before opening a new one. ios_xma_codec_pool=false restores the reopen.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CTX = "src/audio/xma_context.cpp"
WMA = "thirdparty/FFmpeg/libavcodec/wmaprodec.c"

FLUSH_ANCHOR = '''AVCodec ff_xmaframes_decoder = {
    .name           = "xmaframes",
'''
FLUSH_NEW = '''/* LOCAL PATCH - iOS (tools/ios/patch_ios_xma_codec_pool.py): back to the
   state decode_init leaves, so a pooled codec can start a new stream. */
static void xmaframes_flush(AVCodecContext *avctx)
{
    WMAProDecodeCtx *s = avctx->priv_data;
    int i;

    flush(s);
    for (i = 0; i < s->nb_channels; i++)
        s->channel[i].prev_block_len = s->samples_per_frame;
    s->frame_num = 0;
    s->skip_frame = 0;
}

AVCodec ff_xmaframes_decoder = {
    .name           = "xmaframes",
'''

FIELD_ANCHOR = '''    .close          = xmaframes_decode_end,
    .decode         = xmaframes_decode_packet,
'''
FIELD_NEW = '''    .close          = xmaframes_decode_end,
    .decode         = xmaframes_decode_packet,
    .flush          = xmaframes_flush,  /* LOCAL PATCH - iOS (patch_ios_xma_codec_pool.py) */
'''

CVAR_ANCHOR = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py).
static std::atomic<uint64_t> ios_xma_codec_reopens{0};
'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_reset_stats.py).
static std::atomic<uint64_t> ios_xma_codec_reopens{0};
// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_codec_pool.py).
REXCVAR_DEFINE_BOOL(ios_xma_codec_pool, true, "Audio",
                    "iOS: keep up to 32 flushed XMA codecs from released contexts and reuse them for new "
                    "streams instead of opening a new codec each time (CPU; ~15 MiB at most)");
static std::mutex ios_xma_pool_mutex;
struct IosPooledCodec {
  AVCodecContext* context;
  int sample_rate, channels;
};
static std::vector<IosPooledCodec> ios_xma_pool;
static bool IosCodecPoolPut(AVCodecContext* context, int sample_rate, int channels) {
  if (!REXCVAR_GET(ios_xma_codec_pool) || sample_rate <= 0 || channels <= 0) return false;
  avcodec_flush_buffers(context);
  context->sample_rate = sample_rate;
  context->channels = channels;
  std::lock_guard<std::mutex> lock(ios_xma_pool_mutex);
  if (ios_xma_pool.size() >= 32) return false;
  ios_xma_pool.push_back({context, sample_rate, channels});
  return true;
}
static AVCodecContext* IosCodecPoolTake(int sample_rate, int channels) {
  if (!REXCVAR_GET(ios_xma_codec_pool)) return nullptr;
  std::lock_guard<std::mutex> lock(ios_xma_pool_mutex);
  for (size_t i = ios_xma_pool.size(); i-- > 0;) {
    if (ios_xma_pool[i].sample_rate == sample_rate && ios_xma_pool[i].channels == channels) {
      AVCodecContext* context = ios_xma_pool[i].context;
      ios_xma_pool[i] = ios_xma_pool.back();
      ios_xma_pool.pop_back();
      return context;
    }
  }
  return nullptr;
}
'''

RELEASE_ANCHOR = '''  set_is_allocated(false);
  ResetDecoderState();
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): the next user
  // reopens the codec anyway; free its 464 KiB until then.
  if (REXCVAR_GET(ios_xma_lazy_codec) && av_context_) {
    avcodec_free_context(&av_context_);
  }
'''
RELEASE_NEW = '''  set_is_allocated(false);
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_codec_pool.py): its format,
  // before ResetDecoderState clears it.
  const int pool_rate = av_context_ ? av_context_->sample_rate : 0;
  const int pool_channels = av_context_ ? av_context_->channels : 0;
  ResetDecoderState();
  // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_lazy_codec.py): the next user
  // reopens the codec anyway; free its 464 KiB until then.
  if (REXCVAR_GET(ios_xma_lazy_codec) && av_context_) {
    // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_codec_pool.py): or keep it,
    // flushed, for the next stream of the same format.
    if (IosCodecPoolPut(av_context_, pool_rate, pool_channels)) {
      av_context_ = nullptr;
    } else {
      avcodec_free_context(&av_context_);
    }
  }
'''

PREPARE_ANCHOR = '''    if (av_context_) avcodec_free_context(&av_context_);  // LOCAL PATCH - iOS (patch_ios_xma_lazy_codec.py)
    av_context_ = avcodec_alloc_context3(av_codec_);
'''
PREPARE_NEW = '''    // LOCAL PATCH - iOS (tools/ios/patch_ios_xma_codec_pool.py): a flushed
    // codec of this format from a released context, if one is kept.
    if (AVCodecContext* pooled = IosCodecPoolTake(sample_rate, static_cast<int>(channels))) {
      if (av_context_) avcodec_free_context(&av_context_);
      av_context_ = pooled;
      return 1;
    }
    if (av_context_) avcodec_free_context(&av_context_);  // LOCAL PATCH - iOS (patch_ios_xma_lazy_codec.py)
    av_context_ = avcodec_alloc_context3(av_codec_);
'''

BLOCKS = [
    (CTX, "the ios_xma_codec_pool cvar and pool", CVAR_ANCHOR, CVAR_NEW),
    (CTX, "released codecs kept, flushed", RELEASE_ANCHOR, RELEASE_NEW),
    (CTX, "new streams take a pooled codec", PREPARE_ANCHOR, PREPARE_NEW),
    (WMA, "xmaframes flush callback", FLUSH_ANCHOR, FLUSH_NEW),
    (WMA, "xmaframes flush registered", FIELD_ANCHOR, FIELD_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_codec_pool", BLOCKS))
