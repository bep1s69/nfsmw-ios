#!/usr/bin/env python3
"""Exercise the production render-only QoS selector across live policy states."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'ios/src/adaptive_qos.cpp').read_text()

def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

selector = function(source, 'unsigned RenderQos()')
program = r'''
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>
#include <pthread/qos.h>
enum : unsigned { MainUtility=1, GuestUtility=2, Adaptive=4, Original=8,
    RenderUtility=16, Background=32, LowWorkers=64 };
std::atomic<int> mode{-1}, policy_cap{60};
unsigned flags=0, boost=QOS_CLASS_DEFAULT;
bool controller=false, workers=false, trial=false;
bool Flag(unsigned flag) { return flags & flag; }
bool AdaptiveEnabled() { return Flag(Adaptive) && !Flag(MainUtility); }
bool WorkersOn() { return workers; }
bool Controller() { return controller; }
unsigned BoostQos(int) { return boost; }
enum class LowRole { Render };
unsigned LowQos(LowRole) { return Flag(Background) ? QOS_CLASS_BACKGROUND : QOS_CLASS_UTILITY; }
#define REXCVAR_GET(name) trial
'''
program += selector + r'''
int main(int argc, char** argv) {
  assert(argc==2); trial=std::atoi(argv[1]);
  unsigned checked=0, changed=0;
  for (int cap : {0,30,40,60,120,144}) for (int m : {-1,0,1,2})
  for (unsigned f=0;f<128;++f) for (bool c : {false,true})
  for (bool w : {false,true}) for (unsigned b : {QOS_CLASS_UTILITY,QOS_CLASS_DEFAULT,QOS_CLASS_USER_INITIATED}) {
    policy_cap=cap; mode=m; flags=f; controller=c; workers=w; boost=b;
    const unsigned original=AdaptiveEnabled() && workers && m>=1 ? b
        : Flag(RenderUtility) ? LowQos(LowRole::Render) : QOS_CLASS_DEFAULT;
    const bool isolated=trial && controller && cap>40 && Flag(RenderUtility)
        && AdaptiveEnabled() && workers && m>=1;
    const unsigned actual=RenderQos();
    assert(actual==(isolated ? QOS_CLASS_UTILITY : original));
    if (!trial || cap<=40 || !controller || !Flag(RenderUtility)) assert(actual==original);
    changed+=actual!=original; ++checked;
  }
  assert(trial ? changed>0 : changed==0);
  std::printf("PASS trial=%d: %u live cap/mode/policy/worker/boost cases, %u changed; low caps and opt-outs preserved\n",trial,checked,changed);
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-render-qos-') as tmp:
    p = Path(tmp)
    (p / 'test.cpp').write_text(program)
    subprocess.run(['clang++', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    str(p / 'test.cpp'), '-o', str(p / 'test')], check=True)
    for trial in (0, 1):
        subprocess.run([str(p / 'test'), str(trial)], check=True)

# A render-only trial must not silently change guest, audio, controller or
# pipeline policies. Compare all other production source to the prior checkpoint.
baseline = subprocess.check_output(['git', 'show', 'd805bce:ios/src/adaptive_qos.cpp'],
                                   cwd=ROOT, text=True)
start = source.index('REXCVAR_DEFINE_BOOL(nfsmw_render_utility_trial,')
end = source.index(');', start) + 3
normalized = source[:start] + source[end:]
normalized = normalized.replace(selector, function(baseline, 'unsigned RenderQos()'), 1)
assert normalized == baseline
print('PASS all guest/audio/controller/pipeline QoS source unchanged from accepted baseline')
