#!/usr/bin/env python3
"""Host checks for actual managed-slot accounting (no Metal device needed)."""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
harness = r"""
#include "managed_frame_slots.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
  constexpr double period = .02502;
  unsigned checked = 0;
  // Steady 40: clock/queue arrival jitter must not invent missed slots.
  nfsmw::ManagedFrameSlots steady;
  steady.Assign(100, period, true);
  for (int i = 1; i <= 10000; ++i) {
    steady.Assign(100 + i * period + ((i % 3) - 1) * .000001, period, true);
    assert(steady.Take(3) == 0);
    ++checked;
  }
  // World updates precede assignment of their render slot. Verify conservation
  // with that feedback delay at sustained 30/20 fps and changing load.
  for (int pattern = 0; pattern < 4; ++pattern) {
    nfsmw::ManagedFrameSlots slots;
    double target = 100;
    slots.Assign(target, period, true);
    uint64_t missed = 0, delivered = 0;
    for (int i = 0; i < 3000; ++i) {
      delivered += slots.Take(9);
      const unsigned advance = pattern == 0 ? (i % 3 == 0 ? 2 : 1) :
                               pattern == 1 ? 2 : pattern == 2 ? (i % 19 == 0 ? 4 : 1) : 8;
      target += period * advance;
      slots.Assign(target, period, true);
      missed += advance - 1;
      assert(delivered + slots.Pending() == missed);
      ++checked;
    }
    delivered += slots.Take(9);
    assert(delivered == missed && slots.Pending() == 0);
  }
  // Phase jitter must cancel; it is not an additional elapsed output slot.
  nfsmw::ManagedFrameSlots phase;
  phase.Assign(100, period, true);
  for (int i = 0; i < 1000; ++i) {
    phase.Assign(100 + (i * 2 + 1.5) * period, period, true);
    assert(phase.Take(9) == 0);
    phase.Assign(100 + (i * 2 + 2) * period, period, true);
    assert(phase.Take(9) == 0);
  }
  // Nonintegral target spacing accumulates to whole missed slots over time.
  nfsmw::ManagedFrameSlots fractional;
  fractional.Assign(100, period, true);
  unsigned fractional_missed = 0;
  for (int i = 1; i <= 5000; ++i) {
    fractional.Assign(100 + i * 1.2 * period, period, true);
    fractional_missed += fractional.Take(9);
  }
  assert(fractional_missed == 1000);
  checked += 7000;
  nfsmw::ManagedFrameSlots bounded;
  bounded.Assign(100, period, true);
  bounded.Assign(100 + 8 * period, period, true);
  assert(bounded.Take(3) == 3);
  assert(bounded.Take(3) == 3);
  assert(bounded.Take(3) == 1);
  assert(bounded.Take(3) == 0);
  bounded.Assign(100 + 16 * period, period, true);
  bounded.Assign(100 + 24 * period, period, true);
  assert(bounded.Pending() == 12);  // bounded debt after a severe backlog
  bounded.Assign(101, period, false);
  assert(bounded.Pending() == 0);
  bounded.Assign(102, period, true);  // no menu/lifecycle catch-up
  assert(bounded.Take(3) == 0);
  bounded.Assign(103, period, true); // long discontinuity discarded
  assert(bounded.Take(3) == 0);
  bounded.Assign(102, period, true); // backward discontinuity discarded
  assert(bounded.Take(3) == 0);
  bounded.Assign(std::numeric_limits<double>::quiet_NaN(), period, true);
  assert(bounded.Pending() == 0);
  bounded.Assign(104, 0, true);
  assert(bounded.Take(3) == 0);
  bounded.Reset();
  assert(bounded.Pending() == 0);
  std::printf("PASS %u slot assignments: steady cadence, conservation, phase jitter, bounded catch-up and resets\n", checked);
}
"""
with tempfile.TemporaryDirectory(prefix="nfsmw-frame-slots-") as scratch:
    folder = pathlib.Path(scratch)
    cpp, exe = folder / "test.cpp", folder / "test"
    cpp.write_text(harness)
    subprocess.run(["xcrun", "clang++", "-std=c++17", "-O2",
                    "-fsanitize=address,undefined", "-I", str(root / "ios/src"),
                    str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
