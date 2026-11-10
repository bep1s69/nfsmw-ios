#!/usr/bin/env python3
"""Exercise actual command cache with Objective-C stand-ins, no GPU required."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#import <Foundation/Foundation.h>
#include "native_command_cache.h"
#include <cassert>
using namespace nfsmw;
using namespace nfsmw::commands;
@interface Buffer : NSObject { @public std::vector<unsigned char> bytes; }
- (NSUInteger)length;
- (void*)contents;
@end
@implementation Buffer
- (NSUInteger)length { return bytes.size(); }
- (void*)contents { return bytes.data(); }
@end
@interface Command : NSObject { @public NativeCommandKey operands; unsigned builds,resets; }
@end
@implementation Command
- (void)reset { operands={}; ++resets; }
- (void)setVertexBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {
  operands.buffers[i]=reinterpret_cast<uintptr_t>((__bridge void*)b); operands.offsets[i]=o;
}
- (void)setFragmentBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {
  assert(operands.buffers[i]==reinterpret_cast<uintptr_t>((__bridge void*)b));
  assert(operands.offsets[i]==o);
}
- (void)drawIndexedPrimitives:(MTLPrimitiveType)p indexCount:(NSUInteger)c indexType:(MTLIndexType)t
  indexBuffer:(id)b indexBufferOffset:(NSUInteger)o instanceCount:(NSUInteger)n
  baseVertex:(NSInteger)v baseInstance:(NSUInteger)base {
  assert(t==MTLIndexTypeUInt32 && n==1 && v==0 && base==0);
  operands.primitive=p; operands.count=c; operands.index_offset=o;
  operands.index_buffer=reinterpret_cast<uintptr_t>((__bridge void*)b); ++builds;
}
@end
@interface ICB : NSObject { @public NSMutableArray* commands; }
@end
@implementation ICB
- (id)indirectRenderCommandAtIndex:(NSUInteger)i { return commands[i]; }
@end
@interface Device : NSObject { @public bool fail; }
@end
@implementation Device
- (id)newBufferWithLength:(NSUInteger)n options:(MTLResourceOptions)o {
  if(fail)return nil;
  Buffer* b=[Buffer new]; b->bytes.resize(n); return b;
}
- (id)newIndirectCommandBufferWithDescriptor:(MTLIndirectCommandBufferDescriptor*)d
  maxCommandCount:(NSUInteger)n options:(MTLResourceOptions)o {
  assert(d.inheritBuffers==NO && d.inheritPipelineState==YES);
  assert(d.commandTypes==MTLIndirectCommandTypeDrawIndexed);
  ICB* b=[ICB new]; b->commands=[NSMutableArray array];
  for(size_t i=0;i<n;++i)[b->commands addObject:[Command new]];
  return b;
}
@end
@interface Encoder : NSObject { @public unsigned executions,singles; std::vector<size_t> counts; }
@end
@implementation Encoder
- (void)useResources:(const id<MTLResource>*)r count:(NSUInteger)n usage:(MTLResourceUsage)u stages:(MTLRenderStages)s {
  for(size_t i=0;i<n;++i)assert(r[i]);
}
- (void)executeCommandsInBuffer:(id)b withRange:(NSRange)r {
  ++executions; for(size_t i=r.location;i<r.location+r.length;++i)
    counts.push_back(((Command*)((ICB*)b)->commands[i])->operands.count);
}
- (void)setVertexBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {}
- (void)setFragmentBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {}
- (void)drawIndexedPrimitives:(MTLPrimitiveType)p indexCount:(NSUInteger)c indexType:(MTLIndexType)t
  indexBuffer:(id)b indexBufferOffset:(NSUInteger)o { ++singles; counts.push_back(c); }
@end
static uintptr_t FixturePointer(id p) { return reinterpret_cast<uintptr_t>((__bridge void*)p); }
int main() { @autoreleasepool {
  Device* dev=[Device new]; id<MTLDevice> device=(id<MTLDevice>)dev;
  Context c; assert(c.Begin(device,10,0));
  auto heap=c.Heap(device,0,100); assert(heap && heap.length>=100);
  Buffer* index=[dev newBufferWithLength:128 options:0];
  Buffer* vertex=[dev newBufferWithLength:256 options:0];
  __weak Buffer* old=vertex;
  NativeCommandKey k{}; k.index_buffer=FixturePointer(index); k.buffers[9]=FixturePointer(vertex);
  k.buffers[8]=FixturePointer(c.push); k.offsets[8]=0; k.primitive=MTLPrimitiveTypeTriangle; k.count=6;
  assert(c.Store(0,k)); assert(c.stats.builds==1 && c.Store(0,k) && c.stats.hits==1);
  assert(((Command*)((ICB*)c.icb)->commands[0])->operands==k);
  vertex=nil; assert(old!=nil); // command itself retains no resources: cache pin is required
  auto q=k; q.offsets[9]=16; q.count=12; q.offsets[8]=256;
  assert(c.Store(1,q)); assert(c.pins[k.buffers[9]].refs==2);
  Encoder* enc=[Encoder new]; Batch batch; batch.context=&c;
  batch.Add(0,(id<MTLRenderCommandEncoder>)enc); batch.Add(1,(id<MTLRenderCommandEncoder>)enc);
  assert(batch.Flush() && enc->executions==1 && enc->counts==std::vector<size_t>({6,12}));
  batch.Add(1,(id<MTLRenderCommandEncoder>)enc); batch.Flush();
  assert(enc->singles==1 && c.stats.singles==1 && c.stats.submitted==2);
  auto replaced=k; Buffer* next=[dev newBufferWithLength:300 options:0];
  replaced.buffers[9]=FixturePointer(next); assert(c.Store(0,replaced));
  assert(old!=nil); c.Reset(1); assert(old==nil); // old pin freed only after its LAST command resets
  Buffer* huge=[dev newBufferWithLength:kPinBudget+1 options:0];
  auto bad=replaced; bad.index_buffer=FixturePointer(huge);
  assert(!c.Store(0,bad) && c.entries[0].key==replaced); // transactional budget fallback
  assert(c.Begin(device,1,0)); assert(c.entries[0].valid); // stable context retains command
  auto bytes=c.pin_bytes; assert(bytes>0);
  c.FinishFrame(); assert(!c.entries[0].valid && !c.pin_bytes); // old slot unused after Begin
  assert(c.Store(0,replaced)); c.Heap(device,0,heap.length+1);
  assert(!c.entries[0].valid && c.pin_bytes==0); // growth invalidates stale heap bindings
  assert(!c.Begin(device,kMaxDraws+1,0));
  assert(c.Begin(device,1,1)); assert(!c.entries[0].valid);
  dev->fail=true; Context failed; assert(!failed.Begin(device,10,0)); dev->fail=false;
  auto* a=Acquire(device,1,1); auto* b=Acquire(device,1,1); auto* d=Acquire(device,1,1);
  assert(a && b && d && !Acquire(device,1,1));
  { Lease lease; lease.context=a; } // CPU abort makes the context reusable
  assert(!a->busy.load());
  a=Acquire(device,1,1); assert(a);
  { Lease lease; lease.context=a; lease.submitted=true; }
  assert(a->busy.load()); PurgeIdle(2); assert(a->epoch==1); // GPU-owned cannot be purged
  a->busy.store(false,std::memory_order_release); // simulated completion, including GPU errors
  PurgeIdle(2); assert(a->epoch==2 && !a->icb);
  b->busy=false; d->busy=false; PurgeIdle(2);
  c.Clear(); assert(c.pins.empty() && c.pin_bytes==0);
}}
'''

with tempfile.TemporaryDirectory(prefix="nfsmw-command-cache-") as tmp:
    src, exe = Path(tmp) / "test.mm", Path(tmp) / "test"
    src.write_text(CODE)
    subprocess.run(["clang++", "-std=c++20", "-O1", "-g", "-fobjc-arc",
                    "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                    "-framework", "Foundation", "-framework", "Metal",
                    "-I", str(ROOT / "ios/src"), str(src), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print("PASS: actual cache operands/reuse, last-pin lifetime, batch order/singles, budget/growth, CPU abort/GPU completion/purge")

# Guard production integration boundaries as well as testing the actual cache.
import re
source = (ROOT / "ios/src/native_renderer.mm").read_text()
loop = source[source.index("    TargetLookupCache draw_target_lookup;"):source.index("    // Resolves after the last draw")]
selectors = ("setRenderPipelineState", "setDepthClipMode", "setDepthBias", "setVisibilityResultMode",
             "setDepthStencilState", "setStencilReferenceValue", "setViewport", "setScissorRect",
             "setCullMode", "setFrontFacingWinding", "endEncoding")
for selector in selectors:
    matches = list(re.finditer(r"\[enc " + selector + r"[:\]]", loop))
    assert matches, selector
    for match in matches:
        assert loop[:match.start()].rstrip().endswith("flush_commands();"), selector
assert "auto do_resolve = [&](const ResolveEvent& ev, const Draw& last) {\n      flush_commands();" in source
assert "    flush_commands();\n    if (command_context) command_context->FinishFrame();" in source
assert "completed_context->busy.store(false, std::memory_order_release)" in source
assert "!REXCVAR_GET(nfsmw_native_early_commit) && !capture.active" in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_command_reuse, false,' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_repeat_counter, false,' in source
print("PASS: production state/encoder/resolve ordering guards, completion release and defaults")
