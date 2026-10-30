#!/usr/bin/env python3
"""Host checks for elapsed-time conservation and 30 fps frame quanta."""
import pathlib, subprocess, tempfile
root = pathlib.Path(__file__).resolve().parents[2]
harness = r'''
#include "frame_clock_policy.h"
#include <cassert>
#include <cstdio>
int main() {
  for (int cap : {30, 40, 60, 120}) {
    double guest = cap == 30 ? 1000./60 : 1000./cap;
    double period = nfsmw::WorldFramePeriod(guest, cap, true);
    assert(std::abs(period - 1000./cap) < 1e-9);
    assert(nfsmw::WorldFramePeriod(guest, cap, false) == guest);
    // Jitter in arrival must not alternate half and one-and-a-half frames.
    double debt = 0, total = 0;
    for (int i = 0; i < 6000; ++i) {
      auto s = nfsmw::AdvanceWorldClock(debt, period + (i % 2 ? 3 : -3), period);
      assert(std::abs(s.given - period) < 1e-9 && !s.resync);
      total += s.given;
    }
    assert(std::abs(total - 6000 * period) < 1e-5);
    // Sustained GPU-limited 25 fps at every cap must conserve elapsed time.
    debt = total = 0;
    for (int i = 0; i < 6000; ++i) {
      auto s = nfsmw::AdvanceWorldClock(debt, 40, period);
      assert(!s.resync && s.given <= 1000./15 + 1e-8);
      total += s.given;
    }
    assert(std::abs(total + debt - 240000) < 1e-5);
    // Loading-scale discontinuities remain bounded and resynchronize.
    auto s = nfsmw::AdvanceWorldClock(debt, 500, period);
    assert(s.resync && debt == 0 && s.given <= 1000./15 + 1e-8);
  }
  // Original 60 fps algorithm and result preserved over mixed arrivals.
  double old = 0, now = 0;
  const double p = 16.6682;
  for (int i = 0; i < 10000; ++i) {
    double elapsed = 5 + (i * 17 % 90);
    old += elapsed - p;
    double give = p;
    while (old > p*.75 && give < p*4) { give += p; old -= p; }
    bool reset = old < -2*p || old > 4*p;
    if (reset) old = 0;
    auto s = nfsmw::AdvanceWorldClock(now, elapsed, p);
    assert(std::abs(s.given - give) < 1e-8 && std::abs(now-old) < 1e-8 && s.resync == reset);
  }
  puts("PASS: 30/40/60/120 steady jitter, 25fps conservation, loading bounds; 10000 legacy60 comparisons");
}
'''
with tempfile.TemporaryDirectory() as t:
    p = pathlib.Path(t);(p/'test.cpp').write_text(harness)
    subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I',str(root/'ios/src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
