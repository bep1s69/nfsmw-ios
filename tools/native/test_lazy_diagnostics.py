#!/usr/bin/env python3
"""Exercise extracted snapshot bookkeeping under real Objective-C ARC.

Compares against the pre-cleanup source in git, verifies snapshot metadata,
frame-local texture ownership, and sampled pass labels at the 255-label cap.
No Metal device or GPU work is submitted; on-device PNG output is not tested.
"""
import pathlib
import re
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILE = 'ios/src/native_renderer.mm'
BASE = 'de599a6'

HARNESS = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <cassert>
#include <cstdio>
#include <map>
#include <memory>
#include <set>
#include <string>
#include <vector>
#define FMT_HEADER_ONLY
#include <fmt/format.h>
static int deaths=0;
@interface LifetimeTexture : NSObject
@end
@implementation LifetimeTexture
- (void)dealloc { ++deaths; }
@end
struct Result {
  std::vector<std::string> names, diagnostics;
  std::vector<CGRect> rects;
  std::vector<bool> skins;
  size_t heap_size=0, watched_size=0;
};
@FUNCTIONS@
void EqualSnapshots(const Result& a,const Result& b) {
  assert(a.names==b.names && a.diagnostics==b.diagnostics && a.skins==b.skins);
  assert(a.heap_size==b.heap_size && a.watched_size==b.watched_size && a.rects.size()==b.rects.size());
  for(size_t i=0;i<a.rects.size();++i)assert(CGRectEqualToRect(a.rects[i],b.rects[i]));
}
@PROFILES@
int main() {
 @autoreleasepool {
  for(bool dump : {false,true}) for(bool lazy : {false,true}) {
    const int before=deaths;
    auto ref=Reference(dump,lazy);auto candidate=Candidate(dump,lazy);
    assert(deaths==before+12); // six objects per arm, no lifetime leaks
    if(dump || !lazy) EqualSnapshots(ref,candidate);
    else {
      assert(candidate.heap_size==0 && candidate.names.empty() && candidate.rects.empty());
      assert(candidate.diagnostics.empty() && candidate.watched_size==0);
      for(bool skin:candidate.skins)assert(!skin);
    }
  }
  for(bool profile : {false,true})for(bool lazy : {false,true})for(size_t initial : {0u,254u,255u,256u}) {
    assert(ProfileReference(profile,lazy,initial)==ProfileCandidate(profile,lazy,initial));
  }
  std::puts("PASS extracted snapshot metadata, legacy arm, unused normal-frame metadata, ARC ownership/release, sampled labels and 255-label cap");
 }
}
'''


def between(s, start, end):
    a=s.index(start)
    return s[a:s.index(end,a)]


def block(s, anchor):
    a=s.index(anchor);start=s.index('{',a);depth=1;i=start+1
    while depth:
        depth+=(s[i]=='{')-(s[i]=='}');i+=1
    return s[a:i]


def guarded_pair(s, first, last):
    a=s.index(first);b=s.index(last,a)+len(last)
    if s[max(0,a-80):a].rstrip().endswith('if (prepare_snapshots) {'):
        a=s.rfind('if (prepare_snapshots) {',0,a)
        b=s.index('}',b)+1
    return s[a:b]


def function(s,name):
    init=between(s,'    std::vector<id<MTLTexture>> heap_object', '    // Watched draws')
    kept=next(x for x in s.splitlines() if 'heap_object[next_heap] = kept' in x)
    dest=next(x for x in s.splitlines() if 'heap_object[next_heap] = dest' in x)
    view=next(x for x in s.splitlines() if 'heap_object[next_heap] = v;' in x)
    pairs=[guarded_pair(s,'resolve_names.push_back("kept");','resolve_rects.push_back(CGRectZero);'),
           guarded_pair(s,'resolve_names.push_back(fmt::format("resolve_{:02}_cube_', 'resolve_rects.push_back(CGRectMake(0, 0, w, h));'),
           guarded_pair(s,'resolve_names.push_back(fmt::format("resolve_{:02}_{}_', 'resolve_rects.push_back(CGRectMake(x0, y0, w, h));'),
           guarded_pair(s,'resolve_names.push_back("view");','resolve_rects.push_back(CGRectZero);'),
           guarded_pair(s,'resolve_names.push_back("crop");','resolve_rects.push_back(CGRectZero);')]
    diagnostic=between(s,'      if (prepare_snapshots) diagnostics.push_back(fmt::format(' if 'if (prepare_snapshots) diagnostics' in s else '      diagnostics.push_back(fmt::format(\n          "resolve ', '      [enc endEncoding];')
    skin=between(s,'      const bool skin =','      // Snapshots: the shadow')
    return r'''
Result @NAME@(bool dump,bool lazy_diagnostics) {
 Result result;
 __weak id weak[6];
 @autoreleasepool {
  const bool prepare_snapshots=dump || !lazy_diagnostics;
  NSMutableArray<id<MTLTexture>>* textures=[NSMutableArray new];
  NSMutableArray<id<MTLTexture>>* resolved_textures=[NSMutableArray new];
  for(int i=0;i<6;++i) {
    id<MTLTexture> value=(id<MTLTexture>)[LifetimeTexture new];weak[i]=value;
    if(i<2)[textures addObject:value];else [resolved_textures addObject:value];
  }
  const NSUInteger heap_capacity=32;
  @INIT@
  struct Kept { struct { id<MTLTexture> texture; } second; } kept_value{{resolved_textures[0]}};
  auto* kept=&kept_value;
  id<MTLTexture> dest=resolved_textures[1],v=resolved_textures[2];
  NSUInteger next_heap=2;
  @KEPT@
  ++next_heap;
  @DEST@
  ++next_heap;
  @VIEW@
  std::vector<std::string> resolve_names,diagnostics;
  std::vector<CGRect> resolve_rects;
  const int resolves_done=2,resolves_skipped=1,x0=0,y0=0,w=320,h=256;
  struct {unsigned after_draws=10,control=0,x0=0,y0=0,x1=320,y1=256,dest_base=123,dest_pitch=320,dest_height=256;bool depth=false,clear_color=false,clear_depth=false,swap=false;int exp_bias=0;}ev;
  const std::string own_key="target";const bool own=true;int last=0;
  auto target_key=[](int){return std::string("last");};
  @DIAGNOSTIC@
  @PAIRS@
  struct Texture {unsigned width;};
  struct {std::vector<std::shared_ptr<Texture>> textures;}frame_value;
  auto* frame=&frame_value;frame->textures.push_back(std::make_shared<Texture>(Texture{1024}));
  struct {int textures[1]={0};uint64_t ps_key=0x684f4711f29b9f77ull;}d;
  std::map<uint64_t,int> watched_seen;
  for(int draw=0;draw<8;++draw) { @SKIN@ result.skins.push_back(skin); }
  result.names=resolve_names;result.rects=resolve_rects;result.diagnostics=diagnostics;
  result.heap_size=heap_object.size();result.watched_size=watched_seen.size();
  // Dropping snapshot references must not destroy actual frame resources.
  heap_object.clear();kept_value.second.texture=nil;dest=nil;v=nil;
  for(int i=0;i<6;++i)assert(weak[i]!=nil);
 }
 for(int i=0;i<6;++i)assert(weak[i]==nil);
 return result;
}
'''.replace('@NAME@',name).replace('@INIT@',init).replace('@KEPT@',kept).replace('@DEST@',dest).replace('@VIEW@',view).replace('@DIAGNOSTIC@',diagnostic).replace('@PAIRS@','\n'.join(pairs)).replace('@SKIN@',skin)


def profile_function(s,name):
    body=block(s,'    auto profile_pass =')+';'
    call=next(x for x in s.splitlines() if 'profile_pass(rp, fmt::format("pass ' in x)
    if 'if (!lazy_diagnostics' in s:
        call='if (!lazy_diagnostics || (profile && profile_labels->size() < 255))\n'+call
    return r'''
std::vector<std::string> @NAME@(bool profile,bool lazy_diagnostics,size_t initial) {
 auto profile_labels=std::make_shared<std::vector<std::string>>(initial,"old");
 id<MTLCounterSampleBuffer> profile_buffer=nil;
 @BODY@
 const std::string pass_key="scene";struct {struct {unsigned width=960,height=720;}color;}t;
 for(int di=0;di<300;++di) {
   auto* rp=[MTLRenderPassDescriptor renderPassDescriptor];
   @CALL@
 }
 return *profile_labels;
}
'''.replace('@NAME@',name).replace('@BODY@',body).replace('@CALL@',call)


def main():
    old=subprocess.check_output(['git','show',f'{BASE}:{FILE}'],cwd=ROOT,text=True)
    new=(ROOT/FILE).read_text()
    # These ownership, residency and submission statements must not change in
    # a patch whose only removals are diagnostic metadata references.
    for needle in ('[resolved_textures addObject:', '[assembled_cubes addObject:',
                   '[enc useResource:', '[enc useResources:', '[cb addCompletedHandler:',
                   '[cb commit]', 'gpu_pool.Retire(', 'buffer_arena.Release('):
        assert [x.strip() for x in old.splitlines() if needle in x]==[x.strip() for x in new.splitlines() if needle in x],needle
    source=HARNESS.replace('@FUNCTIONS@',function(old,'Reference')+function(new,'Candidate')).replace('@PROFILES@',profile_function(old,'ProfileReference')+profile_function(new,'ProfileCandidate'))
    with tempfile.TemporaryDirectory(prefix='nfsmw-lazy-diagnostics-') as temp:
        temp=pathlib.Path(temp);path=temp/'test.mm';path.write_text(source);exe=temp/'test'
        subprocess.run(['xcrun','clang++','-std=c++23','-fobjc-arc','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer',
                        '-I',str(ROOT.parent/'rexglue-sdk-ios/thirdparty/fmt/include'),str(path),'-framework','Foundation','-framework','Metal','-framework','CoreGraphics','-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)


if __name__=='__main__':
    main()
