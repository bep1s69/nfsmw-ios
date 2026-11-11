#!/usr/bin/env python3
"""Execute production mode helpers and ownership/acquisition gates in all modes."""
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'ios/src/native_renderer.mm').read_text()
def function(text,signature):
    start=text.index(signature);pos=text.index('{',start);end=pos+1;depth=1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]

gate_start=source.index('    if (NativeCommandEncoding() && !dump &&')
acquire=function(source[gate_start:],'if (NativeCommandEncoding()')
owner_start=source.index('  if (NativeCommandReuse() && !dump_due &&')
owner_end=source.index('    recording->native_storage = TakeNativeFrameStorage();',owner_start)
ownership=source[owner_start:owner_end+len('    recording->native_storage = TakeNativeFrameStorage();')]
helpers='\n'.join(function(source,'bool '+name+'()') for name in
                  ['NativeCommandReuse','NativeCommandEncoding','NativeGeometryHandoff'])
code=r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include "native_frame_storage.h"
#include <atomic>
#include <cassert>
#include <cstdlib>
#include <string_view>
bool reuse_flag=false,encoding_flag=false,geometry_flag=false,early=false,motion=false,repeat=false;
bool Flag(std::string_view n) {
  if(n=="nfsmw_native_command_reuse")return reuse_flag;
  if(n=="nfsmw_native_command_encoding")return encoding_flag;
  if(n=="nfsmw_native_geometry_handoff")return geometry_flag;
  assert(n=="nfsmw_native_early_commit");return early;
}
#define REXCVAR_GET(n) Flag(#n)
@HELPERS@
bool MotionVectorsWanted(){return motion;}
bool RepeatCounterEnabled(){return repeat;}
struct Storage { nfsmw::FrameOwners<const int> values; };
struct Frame { std::shared_ptr<Storage> native_storage; std::vector<int> draws=std::vector<int>(8); };
unsigned takes=0,acquires=0;
std::shared_ptr<Storage> TakeNativeFrameStorage(){++takes;return std::make_shared<Storage>();}
namespace nfsmw::commands {
struct Context{};struct Lease{Context* context=nullptr;};
Context* Acquire(id<MTLDevice>,size_t count,unsigned){assert(count==8);++acquires;static Context c;return &c;}
}
@interface Device : NSObject
@property BOOL supported;
@end
@implementation Device
- (BOOL)supportsFamily:(MTLGPUFamily)f {assert(f==MTLGPUFamilyApple3);return self.supported;}
@end
std::atomic<unsigned> memory_purge_requests{0};
void Check(bool dump_due,bool dump,bool captured,bool supported) {
  auto recording=std::make_unique<Frame>();
  @OWNERSHIP@
  bool cpu_expected=reuse_flag&&!dump_due&&!motion&&!repeat;
  assert(bool(recording->native_storage)==cpu_expected);
  if(cpu_expected) {
    auto value=std::make_shared<const int>(77);
    auto ref=recording->native_storage->values.Capture(value);
    assert(*ref==77&&ref.Slot()==0&&value.use_count()==2);
    assert(NativeGeometryHandoff()==geometry_flag);
  }
  Frame* frame=recording.get();
  Device* fake=[Device new];fake.supported=supported;id<MTLDevice> device=(id<MTLDevice>)fake;
  struct {bool active;}capture{captured};
  nfsmw::commands::Lease command_lease;
  auto* command_context=static_cast<nfsmw::commands::Context*>(nullptr);
  unsigned before=acquires;
  @ACQUIRE@
  bool gpu_expected=reuse_flag&&encoding_flag&&!dump&&!motion&&!repeat&&!early&&!captured&&supported;
  assert(bool(command_context)==gpu_expected&&acquires-before==unsigned(gpu_expected));
}
int main(int argc,char** argv){ @autoreleasepool {
 assert(argc==4);reuse_flag=std::atoi(argv[1]);encoding_flag=std::atoi(argv[2]);geometry_flag=std::atoi(argv[3]);
 assert(NativeCommandReuse()==reuse_flag);
 assert(NativeCommandEncoding()==(reuse_flag&&encoding_flag));
 Check(false,false,false,true);
 Check(true,true,false,true);Check(false,false,true,true);Check(false,false,false,false);
 motion=true;Check(false,false,false,true);motion=false;
 repeat=true;Check(false,false,false,true);repeat=false;
 early=true;Check(false,false,false,true);early=false;
}}
'''.replace('@HELPERS@',helpers).replace('@OWNERSHIP@',ownership).replace('@ACQUIRE@',acquire)
with tempfile.TemporaryDirectory(prefix='nfsmw-encoding-control-') as tmp:
    path,exe=Path(tmp)/'test.mm',Path(tmp)/'test';path.write_text(code)
    subprocess.run(['clang++','-std=c++20','-O1','-g','-fobjc-arc','-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer','-I',str(ROOT/'ios/src'),str(path),'-framework','Foundation',
                    '-framework','Metal','-o',str(exe)],check=True)
    for reuse in range(2):
        for encoding in range(2):
            for geometry in range(2):
                subprocess.run([str(exe),str(reuse),str(encoding),str(geometry)],check=True)
print('PASS actual cached helpers and production ownership/context gates: all 8 modes and dump/capture/motion/repeat/early/family exclusions')

baseline=subprocess.check_output(['git','show','7ac511c:ios/src/native_renderer.mm'],cwd=ROOT,text=True)
from test_prepared_geometry import normalize_prepared_record
assert normalize_prepared_record(function(source,'void Record(Frame& frame, const NfsmwNativeDraw& in)'))==function(baseline,'void Record(Frame& frame, const NfsmwNativeDraw& in)')
start='    TargetLookupCache draw_target_lookup;';end='    // Resolves after the last draw'
assert source[source.index(start):source.index(end)]==baseline[baseline.index(start):baseline.index(end)]
assert 'if (NativeCommandEncoding()) {\n      indirect_pipeline_cache.WarmUp(device);\n      indirect_pipeline_cache.Collect();' in source
assert 'if (NativeCommandEncoding()) indirect_pipeline_cache.Report();' in source
prepare=function(source,'extern "C" void nfsmw_native_prepare_graphics(')
assert 'const bool reuse=NativeCommandEncoding()' in prepare
assert 'if(reuse) indirect_pipeline_cache.Prepare' in prepare
assert 'const auto normal=pipeline_cache.PreparationKeys(false);' in prepare
assert 'pipeline_cache.Prepare(store.device,normal,tick);' in prepare
assert 'const auto* geometry_storage=NativeGeometryHandoff() ? frame->native_storage.get() : nullptr;' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_command_encoding, true,' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_command_reuse, false,' in source
print('PASS normal preparation/geometry stay independent; all ICB preparation/collection/report gates; Record and entire draw loop unchanged from dev119')
