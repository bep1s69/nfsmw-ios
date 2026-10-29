#!/usr/bin/env python3
"""Host-check the actual pacer's clock arithmetic without UIKit/Metal.

Extract the arithmetic block used by the Objective-C++ callback; test its
physical invariants, not a second implementation of the conversion.
"""
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[2]
source = (root / "ios/src/metal_display_pacer.mm").read_text()
begin = source.index("  double cadence = .025;")
end = source.index("  pending = update;", begin)
body = source[begin:end].replace("const double now = CACurrentMediaTime();", "")
harness = r"""
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cassert>
#include <cstdio>
struct Grid {
  double previous_target = 0;
  uint64_t guest_period_ns = 0, guest_timestamp_ns = 0;
  void update(double target, double now) {
""" + body + r"""
  }
};
int main() {
  unsigned cases = 0;
  for (double interval : {.025, .025025, .02499}) {
    Grid g;
    double target = 100;
    g.update(target, target - .049);
    assert(g.guest_period_ns == 8333333);
    for (int i = 1; i <= 1000; ++i) {
      const int skipped = i % 17 == 0 ? 3 : i % 11 == 0 ? 2 : 1;
      target += interval * skipped;
      const double now = target - .049 + (i % 9) * .0001;
      g.update(target, now);
      // Three virtual guest periods per 40 fps slot, even after lost callbacks.
      assert(std::abs(double(g.guest_period_ns) - interval * 1e9 / 3) < 1);
      // Latest guest tick must be in the past, less than one period old.
      assert(double(g.guest_timestamp_ns) <= now * 1e9 + 1);
      assert(now * 1e9 - double(g.guest_timestamp_ns) < double(g.guest_period_ns) + 1);
      ++cases;
    }
  }
  std::printf("PASS %u updates: cadence, missed callbacks, latest nonfuture tick\n", cases);
}
"""
with tempfile.TemporaryDirectory(prefix="nfsmw-metal-grid-") as scratch:
    folder = pathlib.Path(scratch)
    cpp, exe = folder / "test.cpp", folder / "test"
    cpp.write_text(harness)
    subprocess.run(["xcrun", "clang++", "-std=c++17", "-O2", str(cpp), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
