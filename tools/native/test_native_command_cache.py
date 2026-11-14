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
#include <random>
#include <unordered_set>
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
@interface Encoder : NSObject { @public
  unsigned executions,singles,declarations;
  size_t declared_entries;
  std::vector<size_t> counts;
  std::vector<uintptr_t> operations;
  std::unordered_set<uintptr_t> resident;
  std::vector<std::unordered_set<uintptr_t>> at_draw;
}
@end
@implementation Encoder
- (void)useResources:(const id<MTLResource>*)r count:(NSUInteger)n usage:(MTLResourceUsage)u stages:(MTLRenderStages)s {
  assert(n && u==MTLResourceUsageRead && s==(MTLRenderStageVertex|MTLRenderStageFragment));
  ++declarations; declared_entries+=n;
  std::unordered_set<uintptr_t> unique;
  for(size_t i=0;i<n;++i) {
    assert(r[i]); auto p=reinterpret_cast<uintptr_t>((__bridge void*)r[i]);
    assert(unique.insert(p).second); resident.insert(p);
  }
}
- (void)executeCommandsInBuffer:(id)b withRange:(NSRange)r {
  operations.insert(operations.end(),{1,reinterpret_cast<uintptr_t>((__bridge void*)b),r.location,r.length});
  ++executions; for(size_t i=r.location;i<r.location+r.length;++i)
  {
    const auto& k=((Command*)((ICB*)b)->commands[i])->operands;
    assert(resident.count(reinterpret_cast<uintptr_t>((__bridge void*)b)));
    for(auto p:k.buffers) if(p) assert(resident.count(p));
    assert(resident.count(k.index_buffer));
    at_draw.push_back(resident); counts.push_back(k.count);
  }
}
- (void)setVertexBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {
  assert(resident.count(reinterpret_cast<uintptr_t>((__bridge void*)b)));
  operations.insert(operations.end(),{2,reinterpret_cast<uintptr_t>((__bridge void*)b),o,i});
}
- (void)setFragmentBuffer:(id)b offset:(NSUInteger)o atIndex:(NSUInteger)i {
  assert(resident.count(reinterpret_cast<uintptr_t>((__bridge void*)b)));
  operations.insert(operations.end(),{3,reinterpret_cast<uintptr_t>((__bridge void*)b),o,i});
}
- (void)drawIndexedPrimitives:(MTLPrimitiveType)p indexCount:(NSUInteger)c indexType:(MTLIndexType)t
  indexBuffer:(id)b indexBufferOffset:(NSUInteger)o {
  operations.insert(operations.end(),{4,p,c,t,reinterpret_cast<uintptr_t>((__bridge void*)b),o});
  assert(resident.count(reinterpret_cast<uintptr_t>((__bridge void*)b)));
  at_draw.push_back(resident); ++singles; counts.push_back(c);
}
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

  // Differential production Batch paths: growth, repeated buffers, nil slots,
  // nonadjacent commands, state flushes, encoder changes and A->B->A.
  Context comparison; assert(comparison.Begin(device,200,0));
  NSMutableArray* buffers=[NSMutableArray array];
  for(size_t i=0;i<80;++i)[buffers addObject:[dev newBufferWithLength:128 options:0]];
  std::mt19937 rng(90210);
  for(size_t i=0;i<200;++i) {
    NativeCommandKey key{}; key.primitive=MTLPrimitiveTypeTriangle; key.count=(i+1)*3;
    for(size_t s=0;s<5;++s)key.buffers[s]=FixturePointer(buffers[s]);
    key.buffers[8]=FixturePointer(comparison.push); key.offsets[8]=i*kPushStride;
    for(size_t s=9;s<31;++s) if(rng()%3)key.buffers[s]=FixturePointer(buffers[rng()%80]);
    key.index_buffer=FixturePointer(buffers[rng()%80]);
    assert(comparison.Store(i,key));
  }
  Encoder* reference[4]={[Encoder new],[Encoder new],[Encoder new],[Encoder new]};
  Encoder* incremental[4]={[Encoder new],[Encoder new],[Encoder new],[Encoder new]};
  Batch ref,opt;ref.context=opt.context=&comparison;ref.incremental_resources=false;
  for(size_t round=0;round<12;++round) {
    size_t which=(round/2)%4;
    for(size_t i=0;i<200;++i) {
      if(i%17==0) continue; // nonadjacent slots flush automatically
      ref.Add(i,(id<MTLRenderCommandEncoder>)reference[which]);
      opt.Add(i,(id<MTLRenderCommandEncoder>)incremental[which]);
      if(i%5==0) { ref.Flush();opt.Flush(); } // inherited-state mutation
    }
    ref.Flush();opt.Flush();
  }
  for(size_t i=0;i<4;++i) {
    assert(reference[i]->counts==incremental[i]->counts);
    assert(reference[i]->operations==incremental[i]->operations);
    assert(reference[i]->at_draw==incremental[i]->at_draw);
    assert(incremental[i]->declared_entries<reference[i]->declared_entries);
  }
  // Stable two-command runs: exact same 4-resource set, 100x fewer declarations.
  Context stable;assert(stable.Begin(device,2,0));
  NativeCommandKey key{};key.count=6;key.primitive=MTLPrimitiveTypeTriangle;
  key.buffers[8]=FixturePointer(stable.push);key.buffers[9]=FixturePointer(buffers[0]);
  key.index_buffer=FixturePointer(buffers[1]);assert(stable.Store(0,key)&&stable.Store(1,key));
  Encoder* rs=[Encoder new];Encoder* os=[Encoder new];
  Batch rb,ob;rb.context=ob.context=&stable;rb.incremental_resources=false;
  for(size_t i=0;i<100;++i) {
    rb.Add(0,(id<MTLRenderCommandEncoder>)rs);rb.Add(1,(id<MTLRenderCommandEncoder>)rs);rb.Flush();
    ob.Add(0,(id<MTLRenderCommandEncoder>)os);ob.Add(1,(id<MTLRenderCommandEncoder>)os);ob.Flush();
  }
  assert(rs->counts==os->counts&&rs->at_draw==os->at_draw);
  assert(rb.resource_calls==100&&rb.resource_entries==400);
  assert(ob.resource_calls==1&&ob.resource_entries==4);
  // A newly introduced buffer must be declared before the next command uses it.
  key.buffers[9]=FixturePointer(buffers[2]);assert(stable.Store(0,key));
  ob.Add(0,(id<MTLRenderCommandEncoder>)os);ob.Flush();
  assert(ob.resource_entries==5);
  // Holding the declaration encoder prevents allocator address-reuse confusion.
  __weak Encoder* previous;
  { Encoder* e=[Encoder new];previous=e;ob.Add(0,(id<MTLRenderCommandEncoder>)e);ob.Flush(); }
  assert(previous!=nil);
  ob.Add(0,(id<MTLRenderCommandEncoder>)os);ob.Flush();assert(previous==nil);
  ResourceDeclarations set;std::unordered_set<uintptr_t> truth;
  for(size_t i=0;i<100000;++i) {
    if(i%10000==0){set.Clear();truth.clear();}
    uintptr_t p=(rng()%16000)*16;
    assert(set.Insert(p)==(p ? truth.insert(p).second : false));
  }
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
print("PASS: reference/incremental per-draw resource sets and exact operations; encoder changes/lifetime; flat-set growth/collisions")
print("PASS: repeated-run fixture reduces declarations 100 calls/400 entries to 1 call/4 entries (not a device CPU/energy result)")

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
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_command_reuse, true,' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_repeat_counter, false,' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_command_residency, true,' in source
assert 'command_batch.incremental_resources=incremental_command_resources;' in source
print("PASS: production state/encoder/resolve ordering guards, completion release and defaults")
