// Bounded CPU-side diagnostic history. No Metal calls or rendering decisions.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <optional>

namespace nfsmw {
class NativeGpuTimeline {
 public:
  enum Stage { Swap, Encode, CommitIn, CommitOut, ScheduledCallback,
               GpuStart, GpuEnd, CompleteCallback, Released, Shown, StageCount };
  struct Sample {
    uint32_t frame = 0;
    std::array<double, StageCount> time{};
    bool driving = false;
    uint32_t pool_new = 0, vertex_new = 0, uploads = 0, early_commits = 0;
    size_t entry_add = 0, entry_remove = 0, commit_add = 0, commit_remove = 0;
    int outstanding = 0;
  };
  struct Report {
    uint32_t trigger = 0;
    std::array<Sample, 8> samples{};  // four before, trigger, three after
  };
  template <class F> void Update(uint32_t frame, F update) {
    std::lock_guard<std::mutex> lock(mutex_);
    auto& s = samples_[frame % samples_.size()];
    if (s.frame > frame) return;  // a late callback must not erase newer history
    if (s.frame != frame) { s = {}; s.frame = frame; }
    update(s);
    if (!s.driving || s.time[Released] <= 0 || count_ == triggers_.size() ||
        (last_trigger_ && frame < last_trigger_ + 8)) return;
    auto gap = [&](Stage a, Stage b) {
      return s.time[a] > 0 && s.time[b] > 0 ? s.time[b] - s.time[a] : 0.0;
    };
    if (gap(GpuStart, GpuEnd) > .045 || gap(GpuEnd, CompleteCallback) > .020 ||
        gap(CommitIn, CommitOut) > .020 || gap(Swap, Encode) > .030 ||
        gap(Encode, CommitIn) > .030) {
      triggers_[count_++] = frame;
      last_trigger_ = frame;
    }
  }
  std::optional<Report> TakeReport(uint32_t frontier) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (next_ == count_ || frontier < triggers_[next_] + 4) return std::nullopt;
    Report r;
    r.trigger = triggers_[next_++];
    for (size_t i = 0; i < r.samples.size(); ++i) {
      const int64_t frame = int64_t(r.trigger) - 4 + int64_t(i);
      if (frame <= 0) continue;
      const auto& s = samples_[size_t(frame) % samples_.size()];
      if (s.frame == uint32_t(frame)) r.samples[i] = s;
    }
    return r;
  }
 private:
  std::mutex mutex_;
  std::array<Sample, 128> samples_{};
  std::array<uint32_t, 12> triggers_{};
  size_t count_ = 0, next_ = 0;
  uint32_t last_trigger_ = 0;
};
}  // namespace nfsmw
