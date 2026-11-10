#!/usr/bin/env python3
"""Actual archive/cache code with stand-ins: no GPU or device shader compilation."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = (ROOT / "ios/src/native_renderer.mm").read_text()


def method(signature):
    start = SOURCE.index(signature)
    pos = SOURCE.index("{", start)
    depth, end = 1, pos + 1
    while depth:
        depth += (SOURCE[end] == "{") - (SOURCE[end] == "}")
        end += 1
    return SOURCE[start:end]


COMMON = r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <algorithm>
#include <atomic>
#include <cassert>
#include <chrono>
#include <cstring>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>
#define REXCVAR_GET(name) true
#define REXLOG_INFO(...) ((void)0)
#define REXLOG_WARN(...) ((void)0)
using FastClock=std::chrono::steady_clock;
'''

ARCHIVE = r'''
static dispatch_semaphore_t entered=dispatch_semaphore_create(0), release_work=dispatch_semaphore_create(0);
static bool block_make=false;
@interface ArchiveFixture : NSObject @end
@implementation ArchiveFixture
- (BOOL)serializeToURL:(NSURL*)url error:(NSError**)e {
  dispatch_semaphore_signal(entered);
  dispatch_semaphore_wait(release_work,dispatch_time(DISPATCH_TIME_NOW,1000000000));
  return [@"archive fixture" writeToURL:url atomically:YES encoding:NSUTF8StringEncoding error:e];
}
- (BOOL)addRenderPipelineFunctionsWithDescriptor:(id)d error:(NSError**)e { return YES; }
@end
@interface DeviceFixture : NSObject @end
@implementation DeviceFixture
- (id)newRenderPipelineStateWithDescriptor:(id)d options:(MTLPipelineOption)o reflection:(id*)r error:(NSError**)e {
  if(block_make) {
    dispatch_semaphore_signal(entered);
    dispatch_semaphore_wait(release_work,dispatch_time(DISPATCH_TIME_NOW,1000000000));
  }
  return [NSObject new];
}
- (id)newRenderPipelineStateWithDescriptor:(id)d error:(NSError**)e { return [NSObject new]; }
@end
struct PipelineArchive {
 id<MTLBinaryArchive> archive=nil; NSURL* url=nil;
 bool tried=false,dirty=false,saving=false;
 std::atomic<bool> warmed{false}; uint32_t active=0;
 std::mutex mutex;
 uint32_t made=0,loaded=0,misses_logged=0;
 double ms=0,worst_ms=0;
 static unsigned long long FileSize(NSURL*) {return 0;}
 NSURL* SavingMarker() const {return [url URLByAppendingPathExtension:@"saving"];}
 void Open(id<MTLDevice>) {tried=true;}
 @MAKE@
 @REPORT@
 @SAVE_QUEUE@
 @FINISH_PREPARATION@
};
int main(int argc,char** argv) { @autoreleasepool {
 PipelineArchive a;
 a.archive=(id<MTLBinaryArchive>)[ArchiveFixture new]; a.warmed=true;
 a.url=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
 // A render-side Report must not wait behind the serialization mutex.
 std::thread holder([&] {std::lock_guard lock(a.mutex);dispatch_semaphore_signal(entered);
   dispatch_semaphore_wait(release_work,dispatch_time(DISPATCH_TIME_NOW,500000000));});
 dispatch_semaphore_wait(entered,DISPATCH_TIME_FOREVER);
 auto start=FastClock::now(); a.Report();
 assert(std::chrono::duration<double>(FastClock::now()-start).count()<0.1);
 dispatch_semaphore_signal(release_work);holder.join();
 // Even an otherwise idle archive cannot be released under an active Make.
 block_make=true;
 std::thread maker([&] { @autoreleasepool {
   MTLRenderPipelineDescriptor* d=[MTLRenderPipelineDescriptor new];
   NSError* e=nil;
   assert(a.Make((id<MTLDevice>)[DeviceFixture new],d,&e));
 }});
 dispatch_semaphore_wait(entered,DISPATCH_TIME_FOREVER);
 a.Report(); assert(a.archive && a.active==1);
 dispatch_semaphore_signal(release_work);maker.join(); assert(a.active==0);
 // Real production save path: progress/reporting stays responsive, startup
 // explicitly drains the save before guest threads may begin.
 a.dirty=true; a.Report();
 dispatch_semaphore_wait(entered,DISPATCH_TIME_FOREVER);
 start=FastClock::now(); a.Report();
 assert(std::chrono::duration<double>(FastClock::now()-start).count()<0.1);
 dispatch_semaphore_signal(release_work);a.FinishPreparation();
 assert(!a.saving && !a.dirty && !a.archive && !a.tried);
 assert([[NSFileManager defaultManager] fileExistsAtPath:a.url.path]);
 assert(![[NSFileManager defaultManager] fileExistsAtPath:a.SavingMarker().path]);
}}
'''

CACHE = r'''
namespace nfsmw::performance { int PipelineQos(){return QOS_CLASS_UTILITY;} }
static NSURL* cache_dir;
static NSURL* bundle_catalog;
NSURL* FixtureCache(){return cache_dir;}
NSURL* FixtureCatalog(){return bundle_catalog;}
struct Store {
 std::unordered_set<uint64_t> internal_keys;
 id<MTLFunction> Find(const char*,uint64_t){static id f=[NSObject new];return (id<MTLFunction>)f;}
} store;
@KEYS@
MTLRenderPipelineDescriptor* PipelineDescriptor(const PipelineKey&,id<MTLFunction>,id<MTLFunction>,bool indirect=false) {
 auto* d=[MTLRenderPipelineDescriptor new]; d.supportIndirectCommandBuffers=indirect;return d;
}
struct Archive {
 std::mutex mutex;std::atomic<bool> warmed{false};std::vector<bool> capabilities;
 id<MTLRenderPipelineState> Make(id<MTLDevice>,MTLRenderPipelineDescriptor* d,NSError**) {
   capabilities.push_back(d.supportIndirectCommandBuffers);return (id<MTLRenderPipelineState>)[NSObject new];
 }
 void Report(){}
} pipeline_archive;
@interface DeviceFixture : NSObject @end
@implementation DeviceFixture
- (BOOL)supportsTextureSampleCount:(NSUInteger)n {return n==1 || n==4;}
@end
@CACHE@
int main(int argc,char** argv) { @autoreleasepool {
 cache_dir=[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]];
 PipelineCache direct,indirect(true);
 PipelineKey a{1,2,0x10001,0,15,0,0,0,1,false,0},b=a;b.vs=3;
 NSURL* normal=[cache_dir URLByAppendingPathComponent:@"nfsmw_native_pipelines_v2.keys"];
 PipelineCache::WriteCatalog({a,b,a},normal);
 assert(direct.PreparationKeys(false).size()==2);
 assert(indirect.PreparationKeys(true).size()==2); // zero ICB keys, seeded from normal cache
 int progress=0;
 direct.Prepare((id<MTLDevice>)[DeviceFixture new],direct.PreparationKeys(false),[&]{++progress;});
 indirect.Prepare((id<MTLDevice>)[DeviceFixture new],indirect.PreparationKeys(true),[&]{++progress;});
 assert(progress==4 && direct.size()==2 && indirect.size()==2);
 assert(pipeline_archive.capabilities==std::vector<bool>({false,false,true,true}));
 bool failed=false;
 assert(direct.Get(nil,a,nil,nil,true,&failed,true));
 assert(indirect.Get(nil,a,nil,nil,true,&failed,true));
 direct.WarmUp(nil);indirect.WarmUp(nil);assert(pipeline_archive.capabilities.size()==4);
 [@"truncated" writeToURL:normal atomically:YES encoding:NSUTF8StringEncoding error:nil];
 assert(direct.PreparationKeys(false).empty());
 // Fresh install with optional bundled seed; invalid metadata cannot reach Metal.
 bundle_catalog=[cache_dir URLByAppendingPathComponent:@"seed.bin"];
 auto bad=a;bad.sample_count=0;
 PipelineCache::WriteCatalog({a,bad},bundle_catalog);
 assert(indirect.PreparationKeys(true).size()==1);
 [NSMutableData.data writeToURL:bundle_catalog atomically:YES];
 assert(direct.PreparationKeys(false).empty());
}}
'''

archive = COMMON + ARCHIVE
for name, signature in [("MAKE", "id<MTLRenderPipelineState> Make("),
                        ("REPORT", "void Report()"),
                        ("SAVE_QUEUE", "static dispatch_queue_t SaveQueue()"),
                        ("FINISH_PREPARATION", "void FinishPreparation()")]:
    archive = archive.replace("@" + name + "@", method(signature))
keys = SOURCE[SOURCE.index("struct PipelineKey {"):SOURCE.index("// Motion vectors (in the viewport")]
cache = SOURCE[SOURCE.index("class PipelineCache {"):SOURCE.index("PipelineCache pipeline_cache;")]
locator = "[[NSFileManager defaultManager] URLsForDirectory:NSCachesDirectory inDomains:NSUserDomainMask].firstObject"
assert cache.count(locator) == 2
cache = cache.replace(locator, "FixtureCache()")
cache = cache.replace('[[NSBundle mainBundle] URLForResource:@"pipeline_keys" withExtension:@"bin" subdirectory:@"NativeShaders"]',
                      "FixtureCatalog()")
cache = COMMON + CACHE.replace("@KEYS@", keys).replace("@CACHE@", cache)

with tempfile.TemporaryDirectory(prefix="nfsmw-pipeline-preparation-") as tmp:
    for name, code in [("archive", archive), ("cache", cache)]:
        src, exe = Path(tmp) / (name + ".mm"), Path(tmp) / name
        src.write_text(code)
        subprocess.run(["clang++", "-std=c++20", "-O1", "-g", "-fobjc-arc",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-framework", "Foundation", "-framework", "Metal", str(src), "-o", str(exe)], check=True)
        subprocess.run([str(exe), str(Path(tmp) / ("archive.bin" if name == "archive" else ""))], check=True)
        print("PASS actual production " + name + " preparation/locking", flush=True)

main = (ROOT / "ios/src/ios_main.mm").read_text()
assert main.index("nfsmw::launcher::PrepareGraphics();") < main.index("rex::ui::SDLWindowedAppContext context;")
assert main.index('setenv("MTL_CAPTURE_ENABLED"') < main.index("nfsmw::launcher::PrepareGraphics();")
assert "pipeline_archive.warmed.store(true" in method("void Collect()")
assert "lock(pipeline_archive.mutex)" not in method("void Collect()")
print("PASS pre-game call ordering and nonblocking warm-completion publication")
