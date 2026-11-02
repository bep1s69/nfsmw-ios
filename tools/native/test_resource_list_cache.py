#!/usr/bin/env python3
"""Compare production resource list construction against the dev38 loop under ARC."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
FILE = "ios/src/native_renderer.mm"
current = (ROOT / FILE).read_text()
old = subprocess.check_output(["git", "show", f"febbb08:{FILE}"], cwd=ROOT, text=True)
start = old.index("        resident.clear();", old.index("// Everything the argument heaps point to"))
reference = old[start:old.index("        [enc useResources:", start)]
start = current.index("        const std::array<NSUInteger, 5> counts =")
candidate = current[start:current.index("        [enc useResources:", start)]
# Existing Metal declarations, binding, ownership changes and commits remain.
for needle in ("[enc useResource:", "[enc useResources:", "[resolved_textures addObject:",
               "[assembled_cubes addObject:", "[cb commit]", "gpu_pool.Retire("):
    assert [l.strip() for l in old.splitlines() if needle in l] == [
        l.strip() for l in current.splitlines() if needle in l], needle

HARNESS = r'''
#import <Foundation/Foundation.h>
#include <array>
#include <cassert>
#include <vector>
@protocol MTLResource <NSObject> @end
@protocol MTLTexture <MTLResource> @end
static int live=0;
@interface Probe : NSObject<MTLTexture> @end
@implementation Probe
- (instancetype)init { if((self=[super init]))++live;return self; }
- (void)dealloc { --live; }
@end
using List=std::vector<__unsafe_unretained id<MTLResource>>;
struct Inputs {
  NSMutableArray<id<MTLTexture>>* lists[5];
  id<MTLTexture> dummy_array=[Probe new];
  id<MTLResource> data=[Probe new];
  Inputs() { for(auto& list:lists)list=[NSMutableArray array]; }
};
#define INPUTS \
 auto* textures=i.lists[0];auto* resolved_textures=i.lists[1]; \
 auto* assembled_cubes=i.lists[2];auto* volumes=i.lists[3];auto* cubes=i.lists[4]; \
 id<MTLTexture> dummy_array=i.dummy_array;id<MTLResource> data=i.data;
List Reference(const Inputs& i) {
  INPUTS
  List resident;
  @REFERENCE@
  return resident;
}
struct Cache {
  List resident;
  std::array<NSUInteger,5> resident_counts{};
  bool resident_valid=false;
  uint64_t resource_list_builds=0,resource_list_reuses=0,resource_list_entries=0;
  List Declare(const Inputs& i,bool reuse_resource_lists,bool dump=false) {
    INPUTS
    @CANDIDATE@
    return resident;
  }
};
void Equal(const List& a,const List& b) {
  assert(a.size()==b.size());
  for(size_t n=0;n<a.size();++n)assert(a[n]==b[n]); // identity, order, duplicates
}
int main() {
  @autoreleasepool {
    Inputs i;
    Cache on,off;
    for(unsigned pass=0;pass<200;++pass) {
      if(pass<5 || pass%11==0) {
        unsigned kind=pass%5;
        [i.lists[kind] addObject:[Probe new]];
        if(pass%22==0)[i.lists[kind] addObject:i.dummy_array]; // duplicate must stay
      }
      auto expected=Reference(i);
      Equal(expected,on.Declare(i,true));Equal(expected,off.Declare(i,false));
    }
    assert(off.resource_list_builds==200 && off.resource_list_reuses==0);
    assert(on.resource_list_builds+on.resource_list_reuses==200);
    assert(on.resource_list_builds<30 && on.resource_list_reuses>170);
    assert(on.resource_list_entries<off.resource_list_entries);
    // A new frame with identical counts and different identities must build
    // afresh; no cache survives across frames, and fixed extras change too.
    Inputs next;
    for(unsigned k=0;k<5;++k)
      for(NSUInteger n=0;n<i.lists[k].count;++n)[next.lists[k] addObject:[Probe new]];
    Cache fresh;
    Equal(Reference(next),fresh.Declare(next,true));assert(fresh.resource_list_builds==1);
    // Empty arrays still declare both fixed resources, on and off.
    Inputs empty;Cache e;
    Equal(Reference(empty),e.Declare(empty,true));assert(e.resident.size()==2);
    Equal(Reference(empty),e.Declare(empty,true));assert(e.resource_list_reuses==1);
    // Snapshot mode uses the disabled path and does not pollute window stats.
    Cache snapshot;
    Equal(Reference(i),snapshot.Declare(i,false,true));
    assert(snapshot.resource_list_builds==0 && snapshot.resource_list_reuses==0);
  }
  assert(live==0); // unsafe vectors do not retain resources beyond owning arrays
}
'''
with tempfile.TemporaryDirectory(prefix="nfsmw-resource-cache-") as folder:
    path = Path(folder) / "test.mm"
    binary = Path(folder) / "test"
    path.write_text(HARNESS.replace("@REFERENCE@", reference).replace("@CANDIDATE@", candidate))
    subprocess.run(["xcrun", "clang++", "-std=c++23", "-fobjc-arc", "-O1",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer", str(path),
                    "-framework", "Foundation", "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("PASS: production list identity/order/duplicates, all collection invalidations, frame reset, empty lists, OFF/snapshot path and ARC lifetime (ASan/UBSan)")
