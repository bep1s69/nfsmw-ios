#!/usr/bin/env python3
"""Profile policy/override transitions and transactional cooperative SDK patch."""
import os, pathlib, subprocess, tempfile
import patch_ios_live_profiles as patch
from patch_engine import find_sdk
root = pathlib.Path(__file__).resolve().parents[2]
harness = r'''
#include "performance_profile.h"
#include <cassert>
#include <cstdio>
int main() {
  unsigned checked = 0;
  for (int cores : {0,4,6,8}) for (int cap : {30,40,60,120})
  for (int from : {0,1,2}) for (int to : {0,1,2}) {
    if (from == to) continue;
    auto previous = nfsmw::performance::Resolve(from,cores,cap);
    auto next = nfsmw::performance::Resolve(to,cores,cap);
    unsigned a = nfsmw::performance::Encode(previous), b = nfsmw::performance::Encode(next);
    // Compare shared policy against original launch-table expectations.
    const bool eco=to==0,max=to==2,tablet=to==1&&cores>=6;  // tablet profile back in dev62
    unsigned expected = unsigned(eco||(tablet&&cap<=60)) | (unsigned(!max)<<1) |
        (unsigned(!max&&!eco&&(!tablet||cap>60))<<2) | (unsigned(tablet)<<3) | (unsigned(!max)<<4) |
        (unsigned(!max&&cores>=6&&cap<=40)<<5) |  // dev73: Balanced and Eco at 30/40 on 6+ E cores
        (unsigned(eco&&cores>=6&&cap<=40)<<6);  // dev73: Eco also lowers normal-priority workers
    assert(b == expected);
    for (unsigned mask=0;mask<128;++mask) for (unsigned values=0;values<128;++values) {
      unsigned result=nfsmw::performance::WithOverrides(b,mask,values);
      assert((result&mask)==(values&mask));
      assert((result&~mask)==(b&~mask));
      // Going back must match the original settings, without stale overrides.
      unsigned back=nfsmw::performance::WithOverrides(a,mask,values);
      assert(back==((a&~mask)|(values&mask)));
      ++checked;
    }
  }
  printf("PASS: %u profile/override round trips across six transitions, devices and caps\n",checked);
}
'''
with tempfile.TemporaryDirectory() as t:
    p=pathlib.Path(t);(p/'test.cpp').write_text(harness)
    subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-I',str(root/'ios/src'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
    # Compile the actual SDK callback bridge, checking TLS isolation and both
    # sides of a cooperative wait scope without requiring a guest runtime.
    bridge = '#define REX_PLATFORM_IOS 1\n#include <atomic>\n#include <cassert>\n#include <thread>\n' + patch.BRIDGE.removesuffix(patch.TOP)
    bridge += r"""
std::atomic<int> first{0}, second{0};
void a(int role) { assert(role == 2); ++first; }
void b(int role) { assert(role == 2); ++second; }
int main() {
  nfsmw_qos_set_callback(a);
  { NfsmwQosScope host; } // host thread never participates
  assert(first == 0);
  std::thread guest([] {
    nfsmw_qos_enter_guest(2);
    { NfsmwQosScope wait; nfsmw_qos_set_callback(b); }
  });
  guest.join();
  assert(first == 2 && second == 1); // enter, pre-wait, post-wait new callback
  { NfsmwQosScope still_host; }
  assert(first == 2 && second == 1);
}
"""
    (p/'bridge.cpp').write_text(bridge)
    subprocess.run(['clang++','-std=c++20','-pthread',str(p/'bridge.cpp'),'-o',str(p/'bridge')],check=True)
    subprocess.run([str(p/'bridge')],check=True)
    sdk=find_sdk(patch.T);paths=sorted({x[0] for x in patch.BLOCKS})
    for path in paths:
        target=p/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((sdk/path).read_bytes())
    env=dict(os.environ,NFSMW_SDK=str(p))
    def run(*args,success=True):
        r=subprocess.run(['python3',str(root/'tools/ios/patch_ios_live_profiles.py'),*args],env=env,capture_output=True,text=True)
        assert (r.returncode==0)==success,r.stdout+r.stderr
    def snapshot():return {path:(p/path).read_bytes() for path in paths}
    run('--revert');before=snapshot();run();applied=snapshot();run();assert snapshot()==applied
    run('--revert');assert snapshot()==before
    last_path,_,anchor,_=patch.BLOCKS[-1];target=p/last_path;target.write_text(target.read_text().replace(anchor,'',1))
    damaged=snapshot();run(success=False);assert snapshot()==damaged
print('PASS: actual callback bridge TLS and wake adoption; SDK 3-file patch idempotency/exact revert/atomic missing-anchor rejection')
