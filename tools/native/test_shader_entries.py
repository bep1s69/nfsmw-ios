#!/usr/bin/env python3
"""Check identifier-only renaming and the production Metal loader on macOS."""
import argparse
from pathlib import Path
import subprocess
import unittest
from name_shader_entries import rename

KEY = 'ps_0123456789abcdef'
SOURCE = '''// generated shader fixture
float4 shaderBody(float4 x) { return x * 0.5; }
float4 shaderMain(float4 x) { return shaderBody(x); }
float4 shaderMainMotion(float4 x) { return shaderBody(x); }
'''


class Naming(unittest.TestCase):
    def test_reversible_and_idempotent(self):
        for key in (KEY, 'vs_0123456789abcdef', KEY+'_dbg3'):
            new = rename(SOURCE, key)
            self.assertEqual(rename(new, key), new)
            self.assertEqual(new.replace('nfsmw_'+key+'_motion', 'shaderMainMotion')
                             .replace('nfsmw_'+key, 'shaderMain'), SOURCE)
            self.assertIn('return x * 0.5;', new)

    def test_legacy_without_motion(self):
        self.assertIn('nfsmw_'+KEY+'(', rename('void shaderMain() {}', KEY))

    def test_identifier_boundaries(self):
        extra = 'float shaderMainHelper(float x) { return x; }\n'
        self.assertIn(extra, rename(extra+SOURCE, KEY))

    def test_rejections(self):
        for key in ('../escape', 'ps_short', 'unknown', 'ps_0123456789abcdef;'):
            with self.assertRaises(ValueError):
                rename(SOURCE, key)
        for text in ('void other() {}', 'void shaderMainMotion() {}',
                     'void nfsmw_'+KEY+'() {}\nvoid shaderMain() {}'):
            with self.assertRaises(ValueError):
                rename(text, KEY)
        with self.assertRaises(ValueError):
            rename(rename(SOURCE, KEY), 'ps_fedcba9876543210')


HARNESS = r'''
#import "native_shader_entries.h"
#include <cassert>
#include <cstdio>
static id<MTLLibrary> Make(id<MTLDevice> device, NSString* text) {
  NSError* error=nil;
  id<MTLLibrary> library=[device newLibraryWithSource:text options:nil error:&error];
  if (!library) NSLog(@"%@",error);
  assert(library); return library;
}
static uint32_t Execute(id<MTLDevice> d, id<MTLCommandQueue> q, id<MTLFunction> f) {
  assert(f);
  NSError* error=nil;
  id<MTLComputePipelineState> p=[d newComputePipelineStateWithFunction:f error:&error];
  assert(p);
  id<MTLBuffer> result=[d newBufferWithLength:sizeof(uint32_t) options:MTLResourceStorageModeShared];
  *(uint32_t*)result.contents=0xffffffff;
  id<MTLCommandBuffer> cb=[q commandBuffer];
  id<MTLComputeCommandEncoder> e=[cb computeCommandEncoder];
  [e setComputePipelineState:p]; [e setBuffer:result offset:0 atIndex:0];
  [e dispatchThreads:MTLSizeMake(1,1,1) threadsPerThreadgroup:MTLSizeMake(1,1,1)];
  [e endEncoding]; [cb commit]; [cb waitUntilCompleted]; assert(cb.status==MTLCommandBufferStatusCompleted);
  return *(uint32_t*)result.contents;
}
@interface FailedNamedLibrary : NSObject
@property NSMutableArray<NSString*>* requests;
@end
@implementation FailedNamedLibrary
- (NSArray<NSString*>*)functionNames { return @[@"nfsmw_ps_0123456789abcdef",@"shaderMain"]; }
- (id<MTLFunction>)newFunctionWithName:(NSString*)name constantValues:(MTLFunctionConstantValues*)values error:(NSError**)error {
  [self.requests addObject:name];
  return [name isEqualToString:@"shaderMain"] ? (id<MTLFunction>)self : nil;
}
@end
int main() {
 @autoreleasepool {
  id<MTLDevice> d=MTLCreateSystemDefaultDevice(); assert(d);
  id<MTLCommandQueue> q=[d newCommandQueue];
  NSString* key=@"ps_0123456789abcdef";
  NSString* declarations=@"#include <metal_stdlib>\nusing namespace metal;\nconstant uint spec [[function_constant(0)]];\nconstant bool gather [[function_constant(1)]];\n";
  NSString* bodies=@"kernel void shaderMain(device uint* o [[buffer(0)]]) { o[0]=spec+(gather?100:0); }\nkernel void shaderMainMotion(device uint* o [[buffer(0)]]) { o[0]=spec+(gather?100:0)+1000; }\n";
  NSString* named=[bodies stringByReplacingOccurrencesOfString:@"shaderMainMotion" withString:@"nfsmw_ps_0123456789abcdef_motion"];
  named=[named stringByReplacingOccurrencesOfString:@"shaderMain" withString:@"nfsmw_ps_0123456789abcdef"];
  id<MTLLibrary> legacy=Make(d,[declarations stringByAppendingString:bodies]);
  id<MTLLibrary> modern=Make(d,[declarations stringByAppendingString:named]);
  id<MTLLibrary> mixed=Make(d,[[declarations stringByAppendingString:bodies] stringByAppendingString:named]);
  unsigned checks=0;
  for (uint32_t spec : {0u,2u,0x602u,0x1000u,0x2000u,0x2602u}) for (bool gather : {false,true}) for (bool motion : {false,true}) {
    MTLFunctionConstantValues* v=[MTLFunctionConstantValues new];
    [v setConstantValue:&spec type:MTLDataTypeUInt atIndex:0];
    [v setConstantValue:&gather type:MTLDataTypeBool atIndex:1];
    id<MTLFunction> a=NativeShaderFunction(legacy,key,motion,v), b=NativeShaderFunction(modern,key,motion,v), c=NativeShaderFunction(mixed,key,motion,v);
    assert([a.name isEqualToString:motion?@"shaderMainMotion":@"shaderMain"]);
    NSString* expected=motion?@"nfsmw_ps_0123456789abcdef_motion":@"nfsmw_ps_0123456789abcdef";
    assert([b.name isEqualToString:expected] && [c.name isEqualToString:expected]);
    const uint32_t answer=spec+(gather?100:0)+(motion?1000:0);
    assert(Execute(d,q,a)==answer && Execute(d,q,b)==answer && Execute(d,q,c)==answer); ++checks;
  }
  FailedNamedLibrary* failed=[FailedNamedLibrary new]; failed.requests=[NSMutableArray new];
  MTLFunctionConstantValues* empty=[MTLFunctionConstantValues new];
  assert(!NativeShaderFunction((id<MTLLibrary>)failed,key,false,empty));
  assert(failed.requests.count==1 && [failed.requests[0] isEqualToString:@"nfsmw_ps_0123456789abcdef"]);
  assert(!NativeShaderFunction(nil,key,false,empty));
  id<MTLLibrary> baseOnly=Make(d,@"#include <metal_stdlib>\nusing namespace metal;\nkernel void shaderMain(device uint* o [[buffer(0)]]) {o[0]=7;}");
  assert(!NativeShaderFunction(baseOnly,key,true,empty));
  printf("PASS %u base/motion/alpha/gather combinations, 72 dispatches; named preference, legacy compatibility, failure stays closed\n",checks);
 }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Naming))
    if not result.wasSuccessful():
        raise SystemExit(1)
    root = Path(__file__).resolve().parents[2]
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    source = out/'loader-fixture.mm'
    source.write_text('#include <initializer_list>\n'+HARNESS)
    subprocess.run(['xcrun','clang++','-std=c++20','-fobjc-arc','-I'+str(root/'ios/src'),str(source),
                    '-framework','Foundation','-framework','Metal','-o',str(out/'loader-fixture')],check=True)
    subprocess.run([str(out/'loader-fixture')],check=True)


if __name__ == '__main__':
    main()
