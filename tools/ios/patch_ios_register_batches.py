#!/usr/bin/env python3
"""Ordered native register-batch tokens; no change unless the app emits them."""
import sys
from patch_engine import run

CP='src/graphics/command_processor.cpp'
PRES='src/ui/vulkan/vulkan_presenter.cpp'
TYPES='''using RexNativeRegisterWrite = void (*)(void*, uint32_t, uint32_t*, uint32_t);
using RexNativeRegisterBatch = bool (*)(uint64_t, RexNativeRegisterWrite, void*);
'''
DEF='std::atomic<void (*)()> rex_native_swap_hook{nullptr};\n'
DECL='extern std::atomic<void (*)()> rex_native_swap_hook;\n'
NOP='''  // skip N 32-bit words to get to the next packet
  // No-op, ignore some data.
'''
TOKEN='''  // LOCAL PATCH - iOS: owned dirty-register batches, ordered with all other
  // packets (tools/ios/patch_ios_register_batches.py). A consumed token can
  // never fall back to omitted register packets: fail the buffer on mismatch.
  if (count == 4) {
    const uint32_t magic = reader->ReadAndSwap<uint32_t>();
    const uint32_t version = reader->ReadAndSwap<uint32_t>();
    const uint64_t low = reader->ReadAndSwap<uint32_t>();
    const uint64_t high = reader->ReadAndSwap<uint32_t>();
    if (magic != 0x4E465242u) return true;  // ordinary NOP
    const uint64_t ticket = low | (high << 32);
    auto consume = rex_native_register_batch_hook.load(std::memory_order_acquire);
    auto write = +[](void* opaque, uint32_t reg, uint32_t* data, uint32_t words) {
      static_cast<CommandProcessor*>(opaque)->WriteRegistersFromMem(reg, data, words);
    };
    if (version != 1 || !consume || !consume(ticket, write, this)) {
      REXGPU_ERROR("Native register batch token invalid/unavailable: {}", ticket);
      return false;
    }
    return true;
  }
'''
BLOCKS=[
 (PRES,'runtime consumer hook',DEF,DEF+TYPES+'std::atomic<RexNativeRegisterBatch> rex_native_register_batch_hook{nullptr};\n'),
 (CP,'consumer declaration',DECL,DECL+TYPES+'extern std::atomic<RexNativeRegisterBatch> rex_native_register_batch_hook;\n'),
 (CP,'ordered NOP consumer',NOP,TOKEN+NOP),
]
if __name__=='__main__':
    sys.exit(run('ios_register_batches',BLOCKS))
