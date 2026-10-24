#!/usr/bin/env python3
"""
Every 5 s: which XMA streams were fed, which were reset, and which stopped
after a reset (fed in the previous 5 s, not in these, last event a reset).

    python3 tools/ios/patch_ios_xma_voice_log.py            apply
    python3 tools/ios/patch_ios_xma_voice_log.py --status
    python3 tools/ios/patch_ios_xma_voice_log.py --revert

Touches src/audio/xma_context.cpp. Builds on patch_ios_xma_reset_stats.py.
Diagnostics only: no change to what is decoded or played.


WHY
===

October 24 (docs/TECHNICAL.md, BACKLOG D-003/D-004): heavy stutters at the end
of an iPhone pursuit and an engine sound that faded out lined up with bursts of
stream resets ("[xma-resets]", up to 556 a second on 116 contexts), but those
lines only give per-second totals. "[xma-voices]" names the streams: a fade
should show as a group of long-fed contexts that stop after a reset and do not
come back. Each stopped context is listed with its input buffer address, so a
later run can tell which bank it plays from. Bursts (any second with 300 or
more resets) are counted in the same line.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

HELPERS_ANCHOR = '''bool XmaContext::Work() {
  if (!is_allocated() || !is_enabled()) {
'''
HELPERS_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_xma_voice_log.py): per-stream feeds
// and resets, summarized every 5 s ("[xma-voices]").
namespace {
struct IosVoice {
  uint32_t fed_windows = 0;  // consecutive 5 s windows with input
  bool fed_now = false, fed_before = false, reset_last = false;
  uint32_t resets = 0, input_ptr = 0;
};
std::mutex ios_voice_mutex;
IosVoice ios_voices[1024];
std::chrono::steady_clock::time_point ios_voice_since, ios_voice_second;
uint32_t ios_voice_second_resets = 0, ios_voice_bursts = 0, ios_voice_lines = 0;

// Under ios_voice_mutex.
void IosVoiceWindow(std::chrono::steady_clock::time_point now) {
  if (ios_voice_since.time_since_epoch().count() == 0) ios_voice_since = now;
  if (now - ios_voice_since < std::chrono::seconds(5)) return;
  uint32_t fed = 0, reset = 0, resets = 0;
  std::vector<std::pair<uint32_t, uint32_t>> stopped;  // (fed windows, id)
  for (uint32_t id = 0; id < 1024; ++id) {
    IosVoice& v = ios_voices[id];
    fed += v.fed_now;
    reset += v.resets > 0;
    resets += v.resets;
    if (v.fed_before && !v.fed_now && v.reset_last) stopped.push_back({v.fed_windows, id});
    v.fed_windows = v.fed_now ? v.fed_windows + 1 : 0;
    v.fed_before = v.fed_now;
    v.fed_now = false;
    v.resets = 0;
  }
  if (ios_voice_lines++ < 2000) {
    std::sort(stopped.rbegin(), stopped.rend());
    std::string list;
    for (size_t i = 0; i < stopped.size() && i < 12; ++i) {
      const IosVoice& v = ios_voices[stopped[i].second];
      list += fmt::format(" {}({}x5s,{:08X})", stopped[i].second, stopped[i].first, v.input_ptr);
    }
    REXLOG_INFO("[xma-voices] 5 s: {} streams fed, {} reset ({} resets, {} bursts of 300+/s), "
                "{} stopped after a reset{}{}",
                fed, reset, resets, ios_voice_bursts, stopped.size(), stopped.empty() ? "" : ":", list);
  }
  ios_voice_bursts = 0;
  ios_voice_since = now;
}

void IosVoiceFed(uint32_t id, uint32_t input_ptr) {
  if (id >= 1024) return;
  const auto now = std::chrono::steady_clock::now();
  std::lock_guard<std::mutex> lock(ios_voice_mutex);
  IosVoice& v = ios_voices[id];
  v.fed_now = true;
  v.reset_last = false;
  v.input_ptr = input_ptr;
  IosVoiceWindow(now);
}

void IosVoiceReset(uint32_t id) {
  if (id >= 1024) return;
  const auto now = std::chrono::steady_clock::now();
  std::lock_guard<std::mutex> lock(ios_voice_mutex);
  IosVoice& v = ios_voices[id];
  ++v.resets;
  v.reset_last = true;
  if (now - ios_voice_second >= std::chrono::seconds(1)) {
    if (ios_voice_second_resets >= 300) ++ios_voice_bursts;
    ios_voice_second_resets = 0;
    ios_voice_second = now;
  }
  ++ios_voice_second_resets;
  IosVoiceWindow(now);
}
}  // namespace

''' + HELPERS_ANCHOR

FED_ANCHOR = '''    ios_starve_seen_ = false;  // LOCAL PATCH - iOS: fed again
'''
FED_NEW = FED_ANCHOR + '''    IosVoiceFed(id(), initial_data.input_buffer_0_ptr);  // LOCAL PATCH - iOS (patch_ios_xma_voice_log.py)
'''

RESET_ANCHOR = '''      data.output_buffer_write_offset = data.output_buffer_read_offset;
      data.output_buffer_valid = 0;
'''
RESET_NEW = RESET_ANCHOR + '''      IosVoiceReset(id());  // LOCAL PATCH - iOS (patch_ios_xma_voice_log.py)
'''

BLOCKS = [
    (FILE, "per-stream feed and reset summaries", HELPERS_ANCHOR, HELPERS_NEW),
    (FILE, "count a feed", FED_ANCHOR, FED_NEW),
    (FILE, "count a reset", RESET_ANCHOR, RESET_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_voice_log", BLOCKS))
