#!/usr/bin/env python3
"""Host ownership/key regressions; does not emulate Metal or validate pixels."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#include "native_frame_storage.h"
#include "native_command_key.h"
#include <cassert>
#include <random>
#include <thread>
#include <atomic>
struct Data { int v[16]; };
struct Storage {
  nfsmw::FrameBlocks<Data, 8, 24> blocks;
  nfsmw::FrameOwners<const int> owners;
  void Reset() { blocks.Reset(); owners.Clear(); }
};
int main() {
  nfsmw::FrameStoragePool<Storage, 2> pool;
  auto a=pool.Take(0), b=pool.Take(0);
  assert(a && b && !pool.Take(0));
  Data* first=a->blocks.Next(); first->v[3]=42;
  for(int i=1;i<24;++i) assert(a->blocks.Next());
  assert(!a->blocks.Next() && first->v[3]==42);
  auto ptr=a.get(); a.reset(); a=pool.Take(0);
  assert(a.get()==ptr && a->blocks.used()==0);
  nfsmw::FrameRef<const Data> raw; raw.BorrowRaw(a->blocks.Next());
  auto raw_copy=raw; assert(raw_copy.get()==raw.get() && !raw.Owner());
  std::weak_ptr<const int> weak;
  {
    auto cache=std::make_shared<const int>(99); weak=cache;
    nfsmw::FrameRef<const int> x=cache, y=x;
    a->owners.Pin(x); a->owners.Pin(y);
    for(int i=0;i<10000;++i) {
      nfsmw::FrameRef<const int> other=std::make_shared<const int>(i);
      a->owners.Pin(other);
    }
    cache.reset(); assert(*x==99 && *y==99 && !weak.expired());
    // Frame-level pins survive arbitrary source cache eviction and deque growth.
    auto moved=std::move(x); assert(*moved==99);
  }
  assert(!weak.expired());
  a.reset(); assert(weak.expired());
  a=pool.Take(1); // epoch purges idle storage, checked-out b remains valid
  assert(a && !pool.Take(1));
  b.reset(); assert(pool.Take(1));
  a.reset();
  std::atomic<int> count=0;
  auto worker=[&] { for(int i=0;i<2000;++i) if(auto s=pool.Take(1)) {
    auto d=s->blocks.Next(); assert(d); d->v[0]=i;
    nfsmw::FrameRef<const int> r=std::make_shared<const int>(i);
    s->owners.Pin(r); assert(*r==i); ++count;
  }};
  std::thread t(worker); worker(); t.join(); assert(count>0);
  nfsmw::NativeCommandKey k;
  k.count=300; k.primitive=3; k.index_buffer=10; k.index_offset=16;
  for(size_t i=0;i<31;++i) { k.buffers[i]=100+i; k.offsets[i]=i*256; }
  auto same=k; assert(k==same);
  for(size_t i=0;i<31;++i) {
    auto q=k; ++q.buffers[i]; assert(!(q==k));
    q=k; ++q.offsets[i]; assert(!(q==k));
  }
  auto q=k; ++q.index_offset; assert(!(q==k));
  q=k; ++q.index_buffer; assert(!(q==k));
  q=k; ++q.count; assert(!(q==k));
  q=k; ++q.primitive; assert(!(q==k));
  nfsmw::CommandRun run;
  assert(!run.Adjacent(0)); run.Add(5); assert(run.Adjacent(6));
  run.Add(6); assert(run.count==2 && !run.Adjacent(8)); run.Clear();
  assert(!run.count);
}
'''

with tempfile.TemporaryDirectory(prefix="nfsmw-native-frame-") as tmp:
    src = Path(tmp) / "test.cpp"
    src.write_text(CODE)
    exe = Path(tmp) / "test"
    subprocess.run(["clang++", "-std=c++20", "-O1", "-g", "-fsanitize=address,undefined",
                    "-fno-omit-frame-pointer", "-I", str(ROOT / "ios/src"),
                    str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: frame ownership, storage bounds/epochs/concurrency and every command operand")
