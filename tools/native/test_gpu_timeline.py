#!/usr/bin/env python3
"""Exercise bounded timeline history with late and concurrent callback delivery."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include "native_gpu_timeline.h"
#include <cassert>
#include <thread>
using T = nfsmw::NativeGpuTimeline;
void finish(T& t, unsigned frame, bool driving, double gpu = .06) {
  t.Update(frame, [&](auto& s) {
    s.driving = driving;
    s.time[T::GpuStart] = 1;
    s.time[T::GpuEnd] = 1 + gpu;
    s.time[T::CompleteCallback] = 1 + gpu + .001;
    s.time[T::Released] = 1 + gpu + .002;
  });
}
int main() {
  // Menu/loading must not spend the driving report budget. Normal and
  // incomplete samples must not look like a delay measured from time zero.
  T clean;
  finish(clean, 10, false);
  finish(clean, 20, true, .01);
  clean.Update(30, [](auto& s) { s.driving=true; s.time[T::Released]=100; });
  assert(!clean.TakeReport(40));

  // Completion can arrive before commit() returns. Trigger only once,
  // preserve preceding frames, accept presentation arriving after release.
  T t;
  for (unsigned f=6; f<=13; ++f)
    t.Update(f, [=](auto& s) { s.time[T::Swap]=double(f); });
  t.Update(10, [](auto& s) {
    s.driving=true; s.time[T::CommitIn]=10; s.time[T::Released]=10.04;
  });
  assert(!t.TakeReport(14));
  t.Update(10, [](auto& s) { s.time[T::CommitOut]=10.035; s.commit_add=7; });
  t.Update(10, [](auto& s) { s.time[T::Shown]=10.05; });
  assert(!t.TakeReport(13));
  auto report=t.TakeReport(14);
  assert(report && report->trigger==10);
  for (unsigned i=0; i<8; ++i) assert(report->samples[i].frame==6+i);
  assert(report->samples[4].time[T::Shown]==10.05);
  assert(report->samples[4].commit_add==7);
  assert(!t.TakeReport(14));

  // Coalesce adjacent hitches and cap output, even if callbacks keep coming.
  T bounded;
  unsigned count=0;
  for (unsigned f=20; f<420; ++f) {
    finish(bounded, f, true);
    if (bounded.TakeReport(f+4)) ++count;
  }
  assert(count==12 && !bounded.TakeReport(1000));

  // A very late callback must not replace a newer frame sharing its slot.
  T wrapped;
  wrapped.Update(138, [](auto& s) { s.time[T::Swap]=138; });
  wrapped.Update(10, [](auto& s) { s.time[T::Shown]=10; });
  finish(wrapped, 139, true);
  auto history=wrapped.TakeReport(143);
  assert(history && history->samples[3].frame==138);
  assert(history->samples[3].time[T::Shown]==0);

  // Independent callbacks update the same live samples concurrently; no
  // fields may be lost when each event acquires/releases the history lock.
  T concurrent;
  std::thread a([&] {
    for (unsigned f=1;f<=64;++f)
      concurrent.Update(f, [=](auto& s) { s.time[T::Swap]=f; });
  });
  std::thread b([&] {
    for (unsigned f=64;f>0;--f)
      concurrent.Update(f, [=](auto& s) { s.time[T::Shown]=f+.1; });
  });
  a.join(); b.join();
  finish(concurrent, 40, true);
  auto merged=concurrent.TakeReport(44);
  assert(merged);
  for (const auto& s:merged->samples) {
    assert(s.time[T::Swap]==s.frame);
    assert(s.time[T::Shown]==s.frame+.1);
  }
}
'''

with tempfile.TemporaryDirectory(prefix="nfsmw-gpu-timeline-") as folder:
    source = Path(folder) / "timeline.cpp"
    binary = Path(folder) / "timeline"
    source.write_text(HARNESS)
    subprocess.run([
        "clang++", "-std=c++23", "-O1", "-g", "-fsanitize=address,undefined",
        "-fno-omit-frame-pointer", "-I", str(ROOT / "ios/src"),
        str(source), "-o", str(binary),
    ], check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: timeline ordering, missing events, coalescing, budget, wrap and concurrent callbacks (ASan/UBSan)")
