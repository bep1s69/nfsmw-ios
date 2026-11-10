#!/usr/bin/env python3
"""System-wide traces must not charge other apps' samples to the game."""
from pathlib import Path
import tempfile
from summarize_battery_exports import profile
from symbolize_profile_images import name_pc, reference_names

xml = '''<trace-query-result>
<row><sample-time id="1">1000000000</sample-time>
<thread id="2" fmt="OtherThread (1)"/><process id="3" fmt="OtherApp (1)"/>
<core id="4" fmt="CPU 0 (E Core)">0</core><thread-state id="5">Running</thread-state>
<weight id="6">1000000</weight><tagged-backtrace id="7"><frame id="8" name="shared_function"/></tagged-backtrace></row>
<row><sample-time id="9">2000000000</sample-time>
<thread id="10" fmt="GPU Commands (2)"/><process id="11" fmt="LiveContainer (2)"/>
<core ref="4"/><thread-state ref="5"/><weight ref="6"/><tagged-backtrace ref="7"/></row>
<row><sample-time id="12">3000000000</sample-time>
<thread ref="10"/><process ref="11"/><core ref="4"/><thread-state ref="5"/>
<weight ref="6"/><sentinel id="13">No stack</sentinel></row>
<row><sample-time id="14">4000000000</sample-time>
<thread id="15" fmt="OtherLC (3)"/><process id="16" fmt="LiveContainer2 (3)"/>
<core ref="4"/><thread-state ref="5"/><weight ref="6"/><tagged-backtrace ref="7"/></row>
</trace-query-result>'''
with tempfile.TemporaryDirectory() as tmp:
    p = Path(tmp) / 'profile.xml'
    p.write_text(xml)
    all_apps = profile(p, 0, None)
    game = profile(p, 0, None, 'LiveContainer')
    assert all_apps['totals']['samples'] == 4
    assert game['totals']['samples'] == 2
    assert game['totals']['sample_ms'] == 2
    assert game['totals']['unresolved_stack_ms'] == 1
    assert game['top_self_ms'] == [('shared_function', 1)]
    assert list(game['threads']) == ['GPU Commands']
    assert profile(p, 2.5, 3.5, 'LiveContainer')['totals']['samples'] == 1
    assert profile(p, 0, None, 'absent')['totals'] == {}
    image = dict(base=0x4000, preferred=0x1000, sections=[(0x1100, 0x1200)],
                 starts=[0x1110, 0x1150], symbols=[(0x1110, 'first'), (0x1150, 'second')])
    assert name_pc(0x4113, [image]) == 'first'  # tagged non-leaf PC
    assert name_pc(0x4151, [image]) == 'second'
    assert name_pc(0x4100, [image]) is None  # before first function
    assert name_pc(0x4200, [image]) is None  # outside instruction section
    p.write_text('''<root><row><frame addr="0x5013" name="known">
      <binary id="1" UUID="EXACT" load-addr="0x5000"/></frame></row></root>''')
    assert reference_names(p, {('EXACT', 0x10)}) == {('EXACT', 0x10): 'known'}
    assert reference_names(p, {('OTHER', 0x10), ('EXACT', 0x14)}) == {}
print('PASS exact process filtering, cross-process interned refs, unresolved stacks and time window')
print('PASS symbol section bounds, tagged PCs and exact reference UUID/offset matching')
