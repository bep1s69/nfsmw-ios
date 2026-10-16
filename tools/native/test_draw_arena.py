#!/usr/bin/env python3
"""Exercise the renderer's actual Attribute, Draw and Frame types with ARC.

Standalone macOS tests: sanitizer lifetime checks, shared ownership, vector
relocation, frame handoff, overflow, alignment, failure cleanup and heap counts.
"""
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]

HARNESS = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "@HEADER@"
#include <cassert>
#include <cstdio>
#include <memory>
#include <set>
#include <string>
#include <thread>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>
struct ResolveEvent {};
struct Texture {};
struct FetchKey { bool operator==(const FetchKey&) const = default; };
struct FetchKeyHash { size_t operator()(const FetchKey&) const { return 0; } };
@ACTUAL_TYPES@
static_assert(std::is_nothrow_move_constructible_v<Draw>);
static_assert(!std::is_copy_constructible_v<Draw>);
static_assert(!std::is_move_constructible_v<Frame>);

class Probe final : public std::pmr::memory_resource {
 public:
  struct Block { size_t bytes, alignment; };
  std::unordered_map<void*, Block> live;
  size_t calls = 0, fail_at = size_t(-1);
 private:
  void* do_allocate(size_t bytes, size_t alignment) override {
    if (calls++ == fail_at) throw std::bad_alloc();
    void* p = std::pmr::new_delete_resource()->allocate(bytes, alignment);
    assert(live.emplace(p, Block{bytes, alignment}).second);
    return p;
  }
  void do_deallocate(void* p, size_t bytes, size_t alignment) override {
    auto it = live.find(p);
    assert(it != live.end() && it->second.bytes == bytes && it->second.alignment == alignment);
    live.erase(it);
    std::pmr::new_delete_resource()->deallocate(p, bytes, alignment);
  }
  bool do_is_equal(const std::pmr::memory_resource& other) const noexcept override { return this == &other; }
};
struct alignas(256) Wide { uint64_t words[32]; };
static void ResourceChecks(bool pooled) {
  Probe probe;
  {
    nfsmw::DrawArena arena(pooled, size_t(-1), &probe);
    std::pmr::vector<Wide> aligned(arena.Resource());
    aligned.resize(17);
    assert(uintptr_t(aligned.data()) % alignof(Wide) == 0);
    for(size_t i=0;i<aligned.size();++i) aligned[i].words[0]=i;
    aligned.resize(20000); // exceeds even the maximum initial block hint
    for(size_t i=0;i<17;++i) assert(aligned[i].words[0]==i);
    assert(arena.Stats().allocations == probe.calls);
    assert(arena.Stats().peak_bytes >= arena.Stats().live_bytes);
  }
  assert(probe.live.empty());
  probe.calls=0; probe.fail_at=1;
  bool failed=false;
  try {
    nfsmw::DrawArena arena(pooled, 0, &probe);
    std::pmr::vector<uint64_t> values(arena.Resource());
    values.resize(4);
    values.resize(1000000); // second upstream allocation fails
  } catch(const std::bad_alloc&) { failed=true; }
  assert(failed && probe.live.empty());
}

using Cache = std::vector<std::shared_ptr<FloatArray>>;
static Cache MakeCache() {
  Cache result;
  for(int i=0;i<8;++i) {
    auto values=std::make_shared<FloatArray>(48);
    for(size_t k=0;k<values->size();++k) (*values)[k]=float(i*100+k);
    result.push_back(std::move(values));
  }
  return result;
}
static void AddDraw(Frame& frame, const Cache& cache, size_t index, id<MTLFunction> function) {
  Draw d(frame.attribute_arena.Resource());
  d.vs=d.ps=function;
  d.vs_key=index; d.ps_key=index+1;
  size_t count=1+index%12; // includes larger lists than any current shader
  ++frame.attribute_lists;
  frame.attribute_hint_bytes += count*sizeof(Attribute);
  if(frame.attribute_arena.Enabled()) d.attributes.reserve(count);
  for(size_t j=0;j<count;++j) {
    Attribute a;
    a.location=uint32_t(j); a.integer=j%2; a.fresh=j%3==0;
    a.values=cache[(index+j)%cache.size()];
    d.attributes.push_back(std::move(a));
  }
  auto* allocation=d.attributes.data();
  frame.draws.push_back(std::move(d));
  assert(frame.draws.back().attributes.data()==allocation);
}
static uint64_t Check(const Frame& frame) {
  uint64_t checksum=0;
  for(size_t i=0;i<frame.draws.size();++i) {
    const auto& d=frame.draws[i];
    assert(d.vs_key==i && d.ps_key==i+1);
    assert(d.attributes.size()==1+i%12);
    assert(d.attributes.get_allocator().resource()==const_cast<Frame&>(frame).attribute_arena.Resource());
    for(size_t j=0;j<d.attributes.size();++j) {
      const auto& a=d.attributes[j];
      assert(a.location==j && a.integer==bool(j%2) && a.fresh==(j%3==0));
      assert((*a.values)[0]==float(((i+j)%8)*100));
      checksum += uint64_t((*a.values)[47])+a.location;
    }
  }
  return checksum;
}
struct Results { uint64_t checksum=0, calls=0, bytes=0; size_t hint=0; };
static Results FrameChecks(bool pooled, size_t previous_bytes, size_t previous_draws) {
  Cache cache=MakeCache();
  auto gpu_keep=cache[0]; // same independent ownership used by the GPU buffer cache
  std::weak_ptr<FloatArray> weak_payload=cache[1];
  __weak NSObject* weak_function;
  Results result;
  {
    auto frame=std::make_unique<Frame>(pooled, previous_bytes, previous_draws);
    if(pooled) assert(frame->draws.capacity()>=std::min(previous_draws,nfsmw::DrawArena::kMaxDrawHint));
    NSObject* function=[NSObject new]; weak_function=function;
    for(size_t i=0;i<3500;++i) AddDraw(*frame,cache,i,(id<MTLFunction>)function);
    function=nil;
    assert(weak_function!=nil);
    // An abandoned draw must release its references even though its arena
    // bytes are reclaimed only at frame destruction.
    auto owners=cache[0].use_count();
    {
      Draw abandoned(frame->attribute_arena.Resource());
      abandoned.attributes.push_back(Attribute{0,false,cache[0],false});
      assert(cache[0].use_count()==owners+1);
    }
    assert(cache[0].use_count()==owners);
    result.checksum=Check(*frame);
    auto stats=frame->attribute_arena.Stats();
    result.calls=stats.allocations; result.bytes=stats.allocated_bytes;
    result.hint=frame->attribute_hint_bytes;
    cache.clear(); // retained draw data must remain valid without its cache
    assert(!weak_payload.expired());
    std::thread render([owned=std::move(frame), expected=result.checksum]() mutable {
      @autoreleasepool {
        assert(Check(*owned)==expected);
        owned.reset();
      }
    });
    render.join();
  }
  assert(weak_payload.expired());
  assert(weak_function==nil);
  assert(gpu_keep && (*gpu_keep)[47]==47);
  return result;
}
int main() {
  @autoreleasepool {
    ResourceChecks(false); ResourceChecks(true);
    auto heap=FrameChecks(false,0,0), cold=FrameChecks(true,0,0), warm=FrameChecks(true,cold.hint,3500);
    assert(heap.checksum==cold.checksum && cold.checksum==warm.checksum);
    assert(cold.calls<heap.calls && warm.calls<=cold.calls);
    std::printf("PASS actual ARC renderer types: 3500 draws/mode, data equality, relocation, shared/Metal ownership, render-thread destruction\n");
    std::printf("Attribute upstream heap calls: individual %llu; pooled cold %llu; pooled with previous-frame hint %llu\n",
      (unsigned long long)heap.calls,(unsigned long long)cold.calls,(unsigned long long)warm.calls);
    // Several independent frames can coexist; no arena is reused early.
    Cache cache=MakeCache();
    auto a=std::make_unique<Frame>(true,0,0), b=std::make_unique<Frame>(true,0,0);
    AddDraw(*a,cache,0,nil); AddDraw(*b,cache,0,nil);
    assert(a->draws[0].attributes.data()!=b->draws[0].attributes.data());
    a.reset(); assert(Check(*b)>0); b.reset();
    std::puts("PASS alignment, overflow, bad_alloc cleanup, bounded hints and independent in-flight frames");
  }
}
'''


def main():
    source = (ROOT / "ios/src/native_renderer.mm").read_text()
    attributes = source[source.index("template <typename T>\nstruct DefaultInitAllocator"):
                        source.index("// --- Residency")]
    draw_and_frame = source[source.index("struct ConstantBank {"):
                            source.index("std::unique_ptr<Frame> recording;")]
    # Verify the lifetime invariant against the production declaration too.
    frame = draw_and_frame[draw_and_frame.index("struct Frame {"):]
    assert frame.index("nfsmw::DrawArena attribute_arena;") < frame.index("std::vector<Draw> draws;")
    with tempfile.TemporaryDirectory(prefix="nfsmw-draw-arena-") as temp:
        temp = pathlib.Path(temp)
        cpp = temp / "test.mm"
        cpp.write_text(HARNESS.replace("@HEADER@", str(ROOT / "ios/src/native_draw_arena.h"))
                       .replace("@ACTUAL_TYPES@", attributes + draw_and_frame))
        exe = temp / "test"
        subprocess.run(["xcrun", "clang++", "-std=c++20", "-O1", "-fobjc-arc", "-fsanitize=address,undefined",
                        "-fno-omit-frame-pointer", "-framework", "Foundation", "-framework", "Metal",
                        str(cpp), "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
