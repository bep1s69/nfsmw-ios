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
    # Frame destructor and shared frame-store recycling can be on ONE stack;
    # the lifecycle union must count that sample once, not add both weights.
    cleanup=xml.replace('name="shared_function"', 'name="(anonymous namespace)::Frame::~Frame()"')
    cleanup=cleanup.replace('</tagged-backtrace>', '<frame id="20" name="nfsmw::FrameStoragePool&lt;Data, 3ul&gt;::Take(unsigned int)"/></tagged-backtrace>', 1)
    p.write_text(cleanup)
    lifecycle=profile(p, 0, None, 'LiveContainer')['graphics_footprints_ms']
    assert lifecycle['frame_destructor_inclusive_ms']==1
    assert lifecycle['frame_storage_named_path_ms']==1
    assert lifecycle['frame_cleanup_storage_union_ms']==1
    assert lifecycle['draw_frame_storage_lifecycle_union_ms']==1
    p.write_text(xml.replace('name="shared_function"', 'name="(anonymous namespace)::Draw::~Draw()"'))
    draw_only=profile(p, 0, None, 'LiveContainer')['graphics_footprints_ms']
    assert draw_only['draw_destructor_inclusive_ms']==1
    assert draw_only['draw_frame_storage_lifecycle_union_ms']==1
    assert 'frame_cleanup_storage_union_ms' not in draw_only
    batches=xml.replace('name="shared_function"','name="(anonymous namespace)::Try(PPCContext&amp;, unsigned char*, unsigned int)"')
    batches=batches.replace('</tagged-backtrace>','<frame id="20" name="nfsmw::register_batch::Pool&lt;2048ul&gt;::Reserve()"/></tagged-backtrace>',1)
    p.write_text(batches)
    scope=profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
    assert scope['register_batch_producer_named_path_ms']==1 and scope['register_batch_named_union_ms']==1
    assert 'register_batch_consumer_named_path_ms' not in scope
    p.write_text(xml.replace('name="shared_function"','name="(anonymous namespace)::Consume(unsigned long long, void (*)(void*, unsigned int, unsigned int*, unsigned int), void*)"'))
    scope=profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
    assert scope['register_batch_consumer_named_path_ms']==scope['register_batch_named_union_ms']==1
    p.write_text(xml.replace('name="shared_function"','name="rex::audio::XmaContext::Consume(rex::memory::RingBuffer*)"'))
    assert 'register_batch_named_union_ms' not in profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
    from html import escape
    for name, key in [
        ('(anonymous namespace)::Collector::AddCall(PPCContext&, unsigned int)', 'register_flush_collector_named_path_ms'),
        ("(anonymous namespace)::Collector::AddCall(PPCContext&, unsigned int)::'lambda'()::operator()() const", 'register_flush_collector_named_path_ms'),
        ('(anonymous namespace)::Collector::Flush()', 'register_flush_collector_named_path_ms'),
        ('(anonymous namespace)::Publish(nfsmw::register_batch::Pool<2048ul>::Reservation&, unsigned char*, unsigned int, unsigned int, unsigned int)', 'register_batch_publish_named_path_ms'),
        ('(anonymous namespace)::WorthCollecting(unsigned char*, unsigned int)', 'register_flush_gate_named_path_ms'),
        ('sub_825A3EC8', 'register_flush_outer_self_ms'),
    ]:
        stack=xml.replace('name="shared_function"',f'name="{escape(name)}"')
        # Ancestor wrapper also contains useful original work; do not add it
        # again to the producer/transport union for this nested sample.
        stack=stack.replace('</tagged-backtrace>','<frame id="20" name="sub_825A3EC8"/></tagged-backtrace>',1)
        p.write_text(stack)
        scope=profile(p,0,None,'LiveContainer',register_flush_hooks=True)['graphics_footprints_ms']
        assert scope[key]==scope['register_batch_named_union_ms']==1
        assert scope['register_batch_producer_helpers_union_ms']==1
        assert scope['register_flush_outer_inclusive_ms']==1
    for name in ['other::Collector::Flush()', '(anonymous namespace)::Publish(Audio&)', '__imp__sub_825A3EC8']:
        p.write_text(xml.replace('name="shared_function"',f'name="{escape(name)}"'))
        assert 'register_batch_named_union_ms' not in profile(p,0,None,'LiveContainer',register_flush_hooks=True)['graphics_footprints_ms']
    # Original shader work nested under new wrapper is inclusive outer work,
    # not a C1 helper. The wrapper is not the leaf in this sample.
    p.write_text(xml.replace('name="shared_function"','name="original_shader_helper"').replace('</tagged-backtrace>','<frame id="20" name="sub_825A3EC8"/></tagged-backtrace>',1))
    scope=profile(p,0,None,'LiveContainer',register_flush_hooks=True)['graphics_footprints_ms']
    assert scope['register_flush_outer_inclusive_ms']==1 and 'register_batch_named_union_ms' not in scope
    # In a pre-C1 binary this same weak alias can name the original body.
    p.write_text(xml.replace('name="shared_function"','name="sub_825A3EC8"'))
    old=profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
    assert old['register_flush_outer_inclusive_ms']==1 and 'register_batch_named_union_ms' not in old
    prefix='nfsmw::PreparedGeometryCache<(anonymous namespace)::PreparedGeometryKey, (anonymous namespace)::PreparedGeometry, 1024ul>::'
    prepared=xml.replace('name="shared_function"',f'name="{escape("(anonymous namespace)::PreparedGeometry* "+prefix+"Find<Lambda>(Key const&, unsigned long long, Lambda&&)")}"')
    prepared=prepared.replace('</tagged-backtrace>',f'<frame id="20" name="{escape(prefix+"Admit(Key const&, unsigned long long)")}"/></tagged-backtrace>',1)
    p.write_text(prepared)
    scopes=profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
    assert scopes['prepared_geometry_find_named_path_ms']==1
    assert scopes['prepared_geometry_admit_named_path_ms']==1
    assert scopes['prepared_geometry_named_union_ms']==1
    for name in ['(anonymous namespace)::PreparedGeometryFor(Draw const&, Layout const*)',
                 '(anonymous namespace)::PrepareGeometryInput(Input&, Fetch const&)']:
        p.write_text(xml.replace('name="shared_function"',f'name="{escape(name)}"'))
        assert profile(p,0,None,'LiveContainer')['graphics_footprints_ms']['prepared_geometry_named_union_ms']==1
    for name in ['other::PreparedGeometryCache<Key>::Find()',prefix.replace('1024ul','512ul')+'Find<Lambda>()']:
        p.write_text(xml.replace('name="shared_function"',f'name="{escape(name)}"'))
        assert 'prepared_geometry_named_union_ms' not in profile(p,0,None,'LiveContainer')['graphics_footprints_ms']
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
print('PASS frame cleanup/storage scopes overlap without double-counting union weight')
print('PASS exact register-batch producer/consumer matching, nested helper union and unrelated Consume exclusion')
print('PASS C1 collector/publish/gate/outer self union and original-work ancestor exclusion')
print('PASS prepared geometry return-type names, nested union, exact table identity and unrelated-type exclusion')
