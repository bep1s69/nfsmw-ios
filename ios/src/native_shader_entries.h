// Stable compiled names, with compatibility for existing private shader caches.
#pragma once
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

inline id<MTLFunction> NativeShaderFunction(id<MTLLibrary> library, NSString* material,
                                           bool motion, MTLFunctionConstantValues* values) {
  NSString* named = [@"nfsmw_" stringByAppendingString:material];
  if (motion) named = [named stringByAppendingString:@"_motion"];
  // Fall back only when the entry is absent. A failed specialization of a
  // present named entry must not silently select a different shader.
  NSString* entry = [library.functionNames containsObject:named]
                        ? named : (motion ? @"shaderMainMotion" : @"shaderMain");
  return [library newFunctionWithName:entry constantValues:values error:nil];
}
