#!/usr/bin/env python3
"""Host regression checks for the managed-40 engine cap and generated hook."""
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
  auto limit = [](bool managed, int menu, int cap, int mode, unsigned caller,
                  unsigned flag, double quantum, double value) {
    return nfsmw::WorldStepLimit(value, quantum, flag, caller == 0x823AFE64, managed, menu, cap, mode);
  };
  // Cross-product: every unrelated cap, caller, menu, timing mode and branch
  // retains its original cap. Only the observed managed driving path changes.
  unsigned cases = 0;
  for (bool managed : {false, true})
  for (int menu : {-1, 0, 1})
  for (int cap : {30, 40, 60, 120})
  for (int mode : {0, 2})
  for (unsigned caller : {0x823AFE64u, 0x823AFDA0u})
  for (unsigned flag : {0u, 2u})
  for (double quantum : {step, double(1.0f / 60.0f), double(.020f)}) {
    bool active = managed && menu == 0 && cap == 40 && mode == 2 &&
                  caller == 0x823AFE64 && flag != 0 && quantum == step;
    assert(limit(managed, menu, cap, mode, caller, flag, quantum, old_cap) ==
           (active ? original_cap : old_cap));
    ++cases;
  }
  // Steady 40 is identical. One missed 25 ms slot survives intact. Severe
  // stalls remain bounded by the original 66.67 ms allowance (not unlimited).
  for (double input : {.025, .050, .075, .250}) {
    double effective = limit(true, 0, 40, 2, 0x823AFE64, 2, step, old_cap);
    assert(std::fmin(input, effective) == std::fmin(input, original_cap));
  }
  for (double bad : {0., -1., std::numeric_limits<double>::infinity()})
    assert(limit(true, 0, 40, 2, 0x823AFE64, 2, step, bad) == bad);
  double nan = std::numeric_limits<double>::quiet_NaN();
  assert(std::isnan(limit(true, 0, 40, 2, 0x823AFE64, 2, step, nan)));
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
