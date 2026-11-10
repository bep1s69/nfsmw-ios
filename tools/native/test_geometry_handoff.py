#!/usr/bin/env python3
"""Actual owner handles, replacement/epoch lifetime, and validation-body guard."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CODE = r'''
#include "native_frame_storage.h"
#include <cassert>
#include <new>
#include <random>
using Values=std::vector<float>;
using Owners=nfsmw::FrameOwners<Values>;
int main() {
  static_assert(sizeof(nfsmw::FrameRef<Values>)==32); // no bigger Attribute/Draw
  Owners owners;
  nfsmw::FrameOwnerHint<Values> hint;
  auto cached=std::make_shared<Values>(16,1.f);
  std::weak_ptr<Values> weak=cached;
  auto original=owners.Capture(cached,&hint);
  assert(original.Slot()==0 && cached.use_count()==2);
  std::vector<nfsmw::FrameRef<Values>> copies;
  for(int i=0;i<10000;++i) copies.push_back(owners.Capture(cached,&hint));
  assert(cached.use_count()==2 && owners.lookups==1 && owners.hint_hits==10000);
  // Version replacement in the same decoded-cache entry must not retarget old draws.
  cached=std::make_shared<Values>(16,2.f);
  auto changed=owners.Capture(cached,&hint);
  assert(changed.Slot()!=original.Slot() && (*changed)[0]==2 && (*original)[0]==1);
  for(int i=0;i<10000;++i) {
    auto extra=owners.Capture(std::make_shared<Values>(16,float(i)));
    assert(extra && (*extra)[0]==i);
  }
  assert((*copies[5000])[0]==1 && !weak.expired()); // stable through deque growth/cache eviction
  // Every role/table has a unique generation even when value identity matches.
  Owners other;
  auto other_ref=other.Capture(cached,&hint);
  assert(other_ref.Slot()==0 && other.lookups==1 && other.hint_hits==0);
  auto returned=owners.Capture(cached,&hint);
  assert(returned.Slot()==changed.Slot());
  nfsmw::FrameRef<Values> owned=cached;
  assert(owned.Slot()==nfsmw::kNoFrameSlot);
  owners.Pin(owned);assert(owned.Slot()==changed.Slot());
  Values local(4,9.f);nfsmw::FrameRef<Values> raw;raw.BorrowRaw(&local);
  assert(raw.get()==&local && !raw.Owner() && raw.Slot()==nfsmw::kNoFrameSlot);
  raw=cached;assert(raw.get()==cached.get() && raw.Slot()==nfsmw::kNoFrameSlot);
  assert(!owners.Capture({}));
  // Simulate reset of pooled storage. A poisoned stale owner must never be read.
  owners.Clear();hint.owner=reinterpret_cast<const std::shared_ptr<Values>*>(uintptr_t(1));
  auto reset=owners.Capture(cached,&hint);
  assert(reset.Slot()==0 && owners.lookups==1 && owners.hint_hits==0 && weak.expired());
  // Even placement-new of a table at the SAME address cannot revive its hint.
  alignas(Owners) unsigned char bytes[sizeof(Owners)];
  auto* table=new(bytes) Owners;
  auto before=table->Capture(cached,&hint);auto generation=hint.generation;
  assert(before.Slot()==0);table->~Owners();table=new(bytes) Owners;
  auto after=table->Capture(cached,&hint);
  assert(after.Slot()==0 && hint.generation!=generation && table->lookups==1);
  table->~Owners();
  // Reference assignment+Pin and direct Capture agree under arbitrary replacement.
  Owners reference,handles;
  std::vector<std::shared_ptr<Values>> cache;
  std::vector<nfsmw::FrameOwnerHint<Values>> hints(128);
  for(int i=0;i<128;++i)cache.push_back(std::make_shared<Values>(8,float(i)));
  std::mt19937 rng(44119);
  for(int i=0;i<30000;++i) {
    size_t k=rng()%cache.size();
    if(i%29==0)cache[k]=std::make_shared<Values>(8,float(i));
    nfsmw::FrameRef<Values> a=cache[k];reference.Pin(a);
    auto b=handles.Capture(cache[k],&hints[k]);
    assert(a.get()==b.get() && a.Slot()==b.Slot() && *a==*b);
  }
  assert(reference.size()==handles.size() && handles.hint_hits>20000);
}
'''
with tempfile.TemporaryDirectory(prefix='nfsmw-geometry-handoff-') as tmp:
    source, exe = Path(tmp)/'test.cpp', Path(tmp)/'test'
    source.write_text(CODE)
    subprocess.run(['clang++', '-std=c++20', '-O1', '-g', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-I', str(ROOT/'ios/src'), str(source), '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print('PASS actual frame handles: footprint, no per-draw shared owner, hint/map counts, replacement, epochs/address reuse and reference equivalence')

source = (ROOT/'ios/src/native_renderer.mm').read_text()
baseline = subprocess.check_output(['git', 'show', '317ea68:ios/src/native_renderer.mm'], cwd=ROOT, text=True)
def record(s):
    return s[s.index('void Record(Frame& frame, const NfsmwNativeDraw& in) {'):s.index('// --- Drawing a recorded frame with Metal')]

# Allow only ownership-handoff edits inside Record. Every existing content,
# layout, index, remap, watch and fingerprint decision must stay byte-for-byte.
edits = [
 ('  Draw d(frame.attribute_arena.Resource());',
  '  Draw d(frame.attribute_arena.Resource());\n  NativeFrameStorage* geometry_storage=NativeGeometryHandoff() ? frame.native_storage.get() : nullptr;'),
 ('    d.indices = ientry->indices;',
  '    d.indices = geometry_storage ? geometry_storage->indices.Capture(ientry->indices,&ientry->frame_owner)\n                                : nfsmw::FrameRef<const std::vector<uint32_t>>(ientry->indices);'),
 ('        a.values = acached.value;  // watched, not written since',
  '        a.values = geometry_storage ? geometry_storage->attributes.Capture(acached.value,&acached.frame_owner)\n                                    : nfsmw::FrameRef<FloatArray>(acached.value); // watched, not written since'),
 ('        a.values = acached.value;',
  '        a.values = geometry_storage ? geometry_storage->attributes.Capture(acached.value,&acached.frame_owner)\n                                    : nfsmw::FrameRef<FloatArray>(acached.value);'),
 ('      acached.fingerprint = afp;',
  '      acached.fingerprint = afp;\n      if (geometry_storage) a.values=geometry_storage->attributes.Capture(acached.value,&acached.frame_owner);'),
 ('          a.values = std::make_shared<FloatArray>(*a.values);',
  '          a.values = std::make_shared<FloatArray>(*a.values);\n          if (geometry_storage) a.values=geometry_storage->attributes.Capture(a.values.Owner());'),
 ('      ientry->primitive = d.primitive;\n    }',
  '      ientry->primitive = d.primitive;\n    }\n    if (geometry_storage) d.indices=geometry_storage->indices.Capture(d.indices.Owner(),ientry ? &ientry->frame_owner : nullptr);'),
 ('    frame.native_storage->indices.Pin(d.indices);\n    for (auto& a : d.attributes) frame.native_storage->attributes.Pin(a.values);',
  '    if (!geometry_storage) {\n      frame.native_storage->indices.Pin(d.indices);\n      for (auto& a : d.attributes) frame.native_storage->attributes.Pin(a.values);\n    }'),
]
expected = record(baseline)
for old, new in edits:
    assert expected.count(old)==1, old
    expected=expected.replace(old,new)
assert record(source)==expected, 'Unexpected validation/decoding/state change in production Record'
def function(s, signature):
    start=s.index(signature);at=s.index('{',start);depth=1;end=at+1
    while depth:
        depth+=(s[end]=='{')-(s[end]=='}');end+=1
    return s[start:end]
assert function(source,'id<MTLBuffer> GpuBufferFor(')==function(baseline,'id<MTLBuffer> GpuBufferFor(')
assert function(source,'void SweepGpu()')==function(baseline,'void SweepGpu()')
assert source.count('gpu_submission_frame = number;')==1
assert source.count('    SweepGpu();')==1
assert 'GpuBufferForGeometry(device,found->values,geometry_attributes' in source
assert 'GpuBufferForGeometry(device,d.indices,geometry_indices' in source
assert 'REXCVAR_DEFINE_BOOL(nfsmw_native_geometry_handoff, true,' in source
print('PASS complete production Record validation-body guard, original GPU lookup/sweep unchanged, role wiring and fixed submission stamps')
