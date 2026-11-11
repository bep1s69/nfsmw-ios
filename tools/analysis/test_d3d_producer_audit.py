#!/usr/bin/env python3
"""Conservative audit must not carry constants across unknown writes/flow."""
from audit_d3d_producer import literal_stores, inventory
from pathlib import Path
import hashlib
import tempfile


def scan(text):
    return literal_stores(enumerate(text.splitlines(), 1), {0x22: 'DRAW', 0x3c: 'WAIT'})


prefix='''// lis r11,-16383
// ori r10,r11,8705
'''
assert scan(prefix+'// stw r10,4(r3)')[0] == dict(
    line=3, word='C0012201', opcode='22', operation='DRAW', payload_words=2, predicated=True)
assert scan(prefix+'// mr r9,r10\n// stw r9,4(r3)')
for boundary in ['loc_82590020:', '// bl 0x82590000', '// beq 0x82590000',
                 '// lwz r10,4(r3)', '// xor r10,r10,r9']:
    assert not scan(prefix+boundary+'\n// stw r10,4(r3)')
assert not scan(prefix+'// stw r10,80(r1)')  # stack spill, not a ring candidate
assert not scan(prefix+'// stwu r10,4(r10)\n// stw r10,4(r3)')[1:]
assert not scan('// lis r10,-16383\n// ori r10,r10,21760\n// stw r10,4(r3)')  # unknown opcode
assert not scan('// li r10,8705\n// stw r10,4(r3)')  # not type3
assert scan('// lis r10,-16384\n// addi r10,r10,15360\n// stw r10,4(r3)')[0]['opcode']=='3C'
assert not scan(prefix+'// addi r10,r0,4\n// stw r10,4(r3)')
for update in ['// lwzu r9,4(r10)', '// stdu r9,4(r10)', '// sthux r9,r10,r3', '// lmw r9,4(r3)']:
    assert not scan(prefix+update+'\n// stw r10,4(r3)')
print('PASS literal candidate decoding, spills, control-flow joins/calls, unknown destinations and update-store invalidation')

with tempfile.TemporaryDirectory(prefix='nfsmw-producer-audit-') as tmp:
    root=Path(tmp);generated=root/'generated';sdk=root/'sdk';generated.mkdir()
    files={
        'include/rex/graphics/xenos.h':'enum { PM4_DRAW = 0x22 };',
        'include/rex/graphics/command_processor.h':'// fixture',
        'src/graphics/command_processor.cpp':'case PM4_DRAW: break;',
        'src/graphics/plugin_main.cpp':'// native fixture',
        'src/graphics/vulkan/command_processor.cpp':'// secondary fixture',
        'src/kernel/xboxkrnl/xboxkrnl_video.cpp':'// video fixture',
    }
    for name,text in files.items():
        path=sdk/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    path=generated/'nfsmw_recomp.0.cpp'
    text='DEFINE_REX_FUNC(sub_8258E830) {\n'+prefix+'// stw r10,4(r3)\nsub_82590000(ctx, base);\n}\n'
    text+='DEFINE_REX_FUNC(sub_82200000) {\n'+prefix+'// stw r10,4(r3)\n}\n'
    path.write_text(text)
    result=inventory(generated,sdk)
    assert list(result['functions'])==['sub_8258E830']
    function=result['functions']['sub_8258E830']
    assert function['line']==1 and function['calls']=={'sub_82590000':1}
    assert len(function['literal_store_candidates'])==1
    assert len(inventory(generated,sdk,True)['functions'])==2
    assert result['cp_type3_cases']==['PM4_DRAW'] and result['generated_files']==1
    assert result['source_manifest'][path.name]['sha256']==hashlib.sha256(text.encode()).hexdigest()
    assert path.read_text()==text  # source is never modified
    path.unlink()
    try:
        inventory(generated,sdk)
    except ValueError:
        pass
    else:
        raise AssertionError('missing generated inputs must fail')
print('PASS function boundaries, expanded query range/all-function scope, call counts, input hashes and read-only inventory')
