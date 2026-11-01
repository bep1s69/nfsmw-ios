#!/usr/bin/env python3
"""Host regression checks for the engine cap and generated hook."""
import pathlib
import subprocess
import tempfile
import patch_game_world_step_trace as patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
HARNESS = r'''
#include "world_step_limit.h"
#include <cassert>
#include <cstdio>
#include <limits>
int main() {
  constexpr double step = double(1.0f / 120.0f);
  constexpr double old_cap = double(float(4 * step));
  constexpr double original_cap = double(4.0f / 60.0f);
  auto limit = nfsmw::WorldStepLimit;
  // Every budget multiplier keeps its original elapsed allowance, independent
  // of frame cap, renderer, timing mode, menu, or caller (none are inputs).
  unsigned cases = 0;
  for (float budget : {1.f, 2.f, 4.f, 8.f})
  for (unsigned flag : {0u, 1u, 2u})
  for (double quantum : {step, double(1.0f / 60.0f), double(.020f)}) {
    double value = double(float(budget * quantum));
    bool active = flag != 0 && quantum == step;
    assert(limit(value, quantum, flag) ==
           (active ? double(float(budget / 60.f)) : value));
    ++cases;
  }
  // Steady 30/40/60/120 steps are identical; missed 50 ms survives. Severe
  // stalls remain bounded by the original 66.67 ms allowance (not unlimited).
  for (double input : {1./120, 1./60, .025, 1./30, .050, .075, .250}) {
    double effective = limit(old_cap, step, 2);
    assert(std::fmin(input, effective) == std::fmin(input, original_cap));
  }
  for (double bad : {0., -1., std::numeric_limits<double>::infinity()})
    assert(limit(bad, step, 2) == bad);
  double nan = std::numeric_limits<double>::quiet_NaN();
  assert(std::isnan(limit(nan, step, 2)));
  printf("PASS: %u scope combinations; steady/missed/stall bounds; invalid limits\n", cases);
}
'''.replace('#include <cassert>', '#include <cassert>\n#include <initializer_list>')
with tempfile.TemporaryDirectory(prefix='nfsmw-world-limit-') as folder:
    source = pathlib.Path(folder) / 'test.cpp'
    binary = pathlib.Path(folder) / 'test'
    source.write_text(HARNESS)
    subprocess.run(['clang++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    '-I', str(ROOT / 'ios/src'), str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)

# Generated code is private and optional on a clean checkout; the synthetic
# fixture still checks placement/idempotency/revert and rejection before writes.
fixture = patch.HEAD + '\n' + ''.join(a for a, _ in patch.SITES) + '}\n'
sources = [fixture] + [p.read_text() for p in (ROOT / 'ios/generated/default').glob('*.cpp')
                       if patch.HEAD in p.read_text()]
for source in sources:
    original = patch.transform(source, revert=True)
    applied = patch.transform(original)
    assert patch.transform(applied) == applied
    assert patch.transform(applied, revert=True) == original
    assert applied.index('ctx.f13.f64 = nfsmw_world_step_limit') < applied.index('nfsmw_step_limit = ctx.f13.f64')
    for broken in [original.replace(patch.SITES[2][0], '', 1),
                   applied.replace(patch.SITES[2][1], '', 1)]:
        try:
            patch.transform(broken)
        except ValueError:
            pass
        else:
            raise AssertionError('accepted incomplete patch/anchor')
print(f'PASS: {len(sources)} patch fixtures, idempotency, exact revert, malformed input rejection')
