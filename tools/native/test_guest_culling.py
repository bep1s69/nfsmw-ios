#!/usr/bin/env python3
"""Check production culling decisions and extracted Metal state wiring on the host.

Fake encoder only: no GPU or device rendering. ASan/UBSan check the actual
helper, counter type, EncoderState reset and culling integration block.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "@HEADER@"
#include <cassert>
#include <cstdio>
#include <limits>
#include <random>
#include <vector>
using namespace nfsmw;
@interface CullEncoder : NSObject {
@public
  MTLCullMode cull;
  MTLWinding winding;
  unsigned cull_calls, winding_calls;
}
@end
@implementation CullEncoder
- (void)setCullMode:(MTLCullMode)value { cull=value; ++cull_calls; }
- (void)setFrontFacingWinding:(MTLWinding)value { winding=value; ++winding_calls; }
@end
struct Draw {
  uint32_t raster_mode=0, guest_primitive=4, vte=0x43f;
  float viewport[6]={780,780,-360,360,1,0};
  int query=-1;
  size_t indices=6;
  size_t index_count() const { return indices; }
};
@COUNTERS@
struct Case { Draw d; bool internal=false, mirror=false, new_encoder=false; };
static size_t Replay(const std::vector<Case>& cases, bool guest_culling, bool dump,
                     CullEncoder* fake, GuestCullCounters& counters, uint32_t& culled_both_this_frame) {
  @ENCODER_STATE@
  id<MTLRenderCommandEncoder> enc=(id<MTLRenderCommandEncoder>)fake;
  GuestCullCounters* cull_counts=&counters;
  size_t drawn=0;
  for (const auto& c : cases) {
    const auto& d=c.d;
    const bool internal=c.internal, mirror=c.mirror;
    if (c.new_encoder) state.enc=nil;  // same encoder address reused, production invalidation
    state.For(enc);
    @INTEGRATION@
    ++drawn;
  }
  return drawn;
}
static void Decisions() {
  Draw d;
  size_t checked=0;
  for (uint32_t primitive=0; primitive<64; ++primitive) {
    for (uint32_t raster=0; raster<256; ++raster) {
      auto p=PlanGuestCulling(raster,primitive,d.vte,d.viewport,false,false,false);
      bool polygon=false;
      switch(primitive) { case 4: case 5: case 6: case 13: polygon=true; }
      if (!(raster&3)) {
        assert(p.mode==GuestCullMode::None && p.clockwise && p.reason==GuestCullReason::TwoSided);
      } else if (!polygon) {
        assert(p.mode==GuestCullMode::None && p.clockwise && p.reason==GuestCullReason::Primitive);
      } else {
        assert(unsigned(p.mode)==(raster&3) && p.clockwise==bool(raster&4));
        assert(p.reason==GuestCullReason::Eligible);
      }
      ++checked;
    }
  }
  // A cached expanded topology cannot turn a rectangle into a cullable polygon.
  assert(PlanGuestCulling(2,8,d.vte,d.viewport,false,false,false).reason==GuestCullReason::Primitive);
  for (unsigned bit=0; bit<4; ++bit) {
    assert(PlanGuestCulling(2,4,d.vte&~(1u<<bit),d.viewport,false,false,false).reason==GuestCullReason::Viewport);
  }
  assert(PlanGuestCulling(2,4,d.vte,d.viewport,true,false,false).reason==GuestCullReason::Internal);
  assert(PlanGuestCulling(2,4,d.vte,d.viewport,false,true,false).reason==GuestCullReason::Query);
  assert(PlanGuestCulling(2,4,d.vte,d.viewport,false,false,true).reason==GuestCullReason::Viewport);
  for (unsigned i=0; i<4; ++i) {
    float saved=d.viewport[i];
    for (float invalid : {std::numeric_limits<float>::infinity(),-std::numeric_limits<float>::infinity(),
                          std::numeric_limits<float>::quiet_NaN()}) {
      d.viewport[i]=invalid;
      assert(PlanGuestCulling(2,4,d.vte,d.viewport,false,false,false).reason==GuestCullReason::Viewport);
    }
    d.viewport[i]=saved;
  }
  for (float x : {0.f,-0.f,-1.f}) {
    d.viewport[0]=x;
    assert(PlanGuestCulling(2,4,d.vte,d.viewport,false,false,false).reason==GuestCullReason::Viewport);
  }
  d.viewport[0]=780;
  for (float y : {0.f,-0.f,1.f}) {
    d.viewport[2]=y;
    assert(PlanGuestCulling(2,4,d.vte,d.viewport,false,false,false).reason==GuestCullReason::Viewport);
  }
  std::printf("PASS %zu primitive/register cases; rectangles, winding bits, query/internal and invalid viewport fallbacks\n",checked);
}
static void ViewportEquivalence() {
  std::mt19937 rng(7182);
  std::uniform_real_distribution<double> pos(-1,1), scale(1,3000), offset(-2000,2000);
  for (unsigned i=0;i<100000;++i) {
    double sx=scale(rng),sy=-scale(rng),ox=offset(rng),oy=offset(rng);
    double x=pos(rng),y=pos(rng);
    // Guest window transform vs native positive-size Metal viewport transform.
    double gx=sx*x+ox,gy=sy*y+oy;
    double mx=(ox-sx)+(x+1)*(2*sx)/2;
    double my=(oy+sy)+(1-y)*(-2*sy)/2;
    assert(std::abs(gx-mx)<1e-9 && std::abs(gy-my)<1e-9);
    // Orientation determinant agrees for either input triangle winding.
    double a=sx*sy,b=(2*sx/2)*(-(-2*sy)/2);
    assert(a<0 && b<0);
  }
  std::puts("PASS 100000 supported guest/native window transforms and orientation determinants (not hardware rendering)");
}
static void Integration() {
  Case back; back.d.raster_mode=2;
  Case front=back;front.d.raster_mode=5;
  Case both=back;both.d.raster_mode=3;
  Case query=back;query.d.query=0;
  Case rect=back;rect.d.guest_primitive=8;
  Case plain=back;plain.d.raster_mode=0;
  Case internal=back;internal.internal=true;
  Case mirror=back;mirror.mirror=true;
  std::vector<Case> cases={back,back,query,front,both,rect,internal,mirror,plain};
  @autoreleasepool {
    auto enc=[CullEncoder new]; GuestCullCounters c;uint32_t skipped=0;
    assert(Replay(cases,false,false,enc,c,skipped)==9);
    assert(enc->cull_calls==0 && enc->winding_calls==0 && skipped==0);
    assert(c.eligible==4 && c.applied==0 && c.eligible_indices==24);
    c={};enc=[CullEncoder new];
    assert(Replay(cases,true,false,enc,c,skipped)==8 && skipped==1);
    assert(c.eligible==4 && c.applied==4 && c.applied_indices==24 && c.skipped_both==1);
    assert(c.modes[0]==1 && c.modes[1]==1 && c.modes[2]==6 && c.modes[3]==1);
    assert(enc->cull==MTLCullModeNone && enc->winding==MTLWindingClockwise);
    assert(enc->cull_calls==5 && enc->winding_calls==5); // duplicate and fallback state reuse
    // Reset even when the new encoder's address equals the last one's.
    back.new_encoder=true; c={};skipped=0;enc=[CullEncoder new];
    assert(Replay({back,back},true,false,enc,c,skipped)==2);
    assert(enc->cull_calls==2 && enc->winding_calls==2);
    assert(enc->cull==MTLCullModeBack && enc->winding==MTLWindingCounterClockwise);
    c={};skipped=0;enc=[CullEncoder new];
    assert(Replay({front,both,plain},true,true,enc,c,skipped)==2 && skipped==1);
    assert(c.eligible==0 && c.applied==0); // diagnostic snapshot doesn't pollute census
  }
  std::puts("PASS actual integration: disabled path, both-face omission, counter partitions, fallback reset, state reuse and recycled encoder address");
}
int main() { Decisions(); ViewportEquivalence(); Integration(); }
'''


def main():
    source = (ROOT / 'ios/src/native_renderer.mm').read_text()
    counters = source[source.index('struct GuestCullCounters {'):
                      source.index('std::map<std::string, GuestCullCounters>')]
    state = source[source.index('    struct EncoderState {'):
                   source.index('    uint32_t last_shared[256];')]
    integration = source[source.index('      const auto cull = nfsmw::PlanGuestCulling'):
                         source.index('      // Constants and shared constants (texture/sampler indices, booleans).')]
    assert 'state.enc = nil;' in source  # production encoder invalidation still exists
    assert source.index('d.guest_primitive = prim;') < source.index('if (index_hit)')
    assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_guest_culling, false' in source
    text = HARNESS.replace('@HEADER@', str(ROOT / 'ios/src/native_guest_culling.h'))
    text = text.replace('@COUNTERS@', counters).replace('@ENCODER_STATE@', state).replace('@INTEGRATION@', integration)
    with tempfile.TemporaryDirectory(prefix='nfsmw-guest-culling-') as temp:
        cpp, exe = Path(temp) / 'test.mm', Path(temp) / 'test'
        cpp.write_text(text)
        subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O1', '-fobjc-arc',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        '-framework', 'Foundation', '-framework', 'Metal', str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    main()
