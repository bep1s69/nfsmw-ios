#!/usr/bin/env python3
"""Exercise the production callback: mute must silence AND drain/clock audio."""
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[2]
source = (root / 'ios/src/audio/coreaudio_driver.mm').read_text()
start = source.index('void CoreAudioDriver::Render(')
end = source.index('// ---------------------------------------------------------------------------', start)
render = source[start:end]
fixture = r'''
#include <algorithm>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <memory>
std::atomic<bool> output_muted{false};
struct Semaphore {
  int permits=0;
  bool Release(int n, void*) { permits+=n; return true; }
};
struct CoreAudioDriver {
  static constexpr size_t kSamplesPerChannel=256, kOutputChannels=2;
  static constexpr size_t kCapacity=32768, kMask=kCapacity-1;
  Semaphore* semaphore_=nullptr;
  std::unique_ptr<float[]> ring_{new float[kCapacity]()};
  std::atomic<size_t> write_{0},read_{0};
  std::atomic<uint32_t> underruns_{0},silent_frames_{0},refused_permits_{0};
  std::atomic<uint32_t> lowest_floats_{UINT32_MAX};
  size_t consumed_=0;
  void Render(float*,uint32_t);
};
'''
cases = r'''
int main() {
  // Starting near the end exercises split reads in both modes.
  for(bool mute:{false,true}) {
    CoreAudioDriver d; Semaphore s; d.semaphore_=&s;
    d.read_=CoreAudioDriver::kCapacity-100;
    d.write_=d.read_+1024;
    for(size_t i=0;i<1024;++i) d.ring_[(d.read_+i)&d.kMask]=float(i+1);
    float out[1024]; std::fill_n(out,1024,-1.0f);
    output_muted=mute;
    d.Render(out,256);
    for(size_t i=0;i<512;++i) assert(out[i]==(mute ? 0.0f : float(i+1)));
    assert(d.read_==d.kCapacity-100+512 && s.permits==1 && d.underruns_==0);
    // Unmute consumes the next samples, never replays the muted block.
    output_muted=false;
    d.Render(out,256);
    for(size_t i=0;i<512;++i) assert(out[i]==float(i+513));
    assert(d.read_==d.write_ && s.permits==2);
    output_muted=mute;
    d.Render(out,128);
    for(size_t i=0;i<256;++i) assert(out[i]==0.0f);
    assert(d.underruns_==1 && d.silent_frames_==128 && s.permits==2);
    d.Render(out,128); assert(s.permits==3);
    const auto r=d.read_.load(); d.Render(out,0); assert(d.read_==r);
  }
}
'''
with tempfile.TemporaryDirectory() as tmp:
    cpp = Path(tmp) / 'mute.cpp'
    exe = Path(tmp) / 'mute'
    cpp.write_text(fixture + render + cases)
    subprocess.run(['clang++', '-std=c++20', '-O1', '-fsanitize=address,undefined',
                    str(cpp), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print('PASS production audio callback: mute, wrap, unmute, underrun and permit timing')
