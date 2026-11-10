#!/usr/bin/env python3
"""Read xctrace XML exports without modifying captures or launching the game.

Power: export SystemPowerLevel, ProcessSubsystemPowerImpact,
DisplayBrightnessLevel, DeviceChargingState and SystemThermalState together.
Profile: export time-profile; use --process LiveContainer for system-wide traces.
XML IDs are global across the exported tables.
The CPU values are sample weights, not exact CPU execution durations.
"""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def power(path, skip, end=None):
    root = ET.parse(path).getroot()
    ids = {e.get('id'): e for e in root.iter() if e.get('id')}

    def resolve(e):
        return ids[e.get('ref')] if e.get('ref') else e

    def val(e):
        return resolve(e).text

    sums, durations = Counter(), Counter()
    thermal = Counter()
    brightness = set()
    for row in root.iter('row'):
        c = list(row)
        start, duration = float(val(c[0])) / 1e9, float(val(c[1])) / 1e9
        dt = max(0, min(start + duration, end if end is not None else float('inf')) - max(start, skip))
        if not dt:
            continue
        tags = [e.tag for e in c]
        if 'percent-per-hour' in tags:
            key = 'system_percent_per_hour'
            sums[key] += float(val(c[tags.index('percent-per-hour')])) * dt
            durations[key] += dt
        if 'display-brightness' in tags:
            brightness.add(float(val(c[tags.index('display-brightness')])))
        if 'thermal-state' in tags:
            thermal[val(c[tags.index('thermal-state')])] += dt
        if 'process-name' in tags and val(c[tags.index('process-name')]) == 'LiveContainer':
            # Keep raw kind/column names: exported schema does not always
            # identify subsystem enums. Do not turn impact into watts.
            kind = val(c[-1])
            impacts = [float(val(e)) for e in c if e.tag == 'subsystem-power-impact']
            for i, impact in enumerate(impacts):
                if impact >= 0:
                    key = f'kind_{kind}_impact_{i}'
                    sums[key] += impact * dt
                    durations[key] += dt
            if kind == '0':
                key = 'instructions_per_second'
                sums[key] += float(val(c[6])) * dt
                durations[key] += dt
    return {'file': str(path), 'skip_seconds': skip, 'end_seconds': end,
            'means': {k: sums[k] / durations[k] for k in sorted(sums)},
            'coverage_seconds': dict(durations), 'brightness_percent': sorted(brightness),
            'thermal_seconds': dict(thermal)}


def profile(path, skip, end, process=None):
    ids, counts = {}, Counter()
    threads, leaf, inclusive = defaultdict(Counter), Counter(), Counter()
    thread_leaf = defaultdict(Counter)
    render_threads = set()
    graphics = Counter()
    d3d_addresses = ('825A3EC8', '82593A58', '82593818', '825930E0',
                     '82593408', '8259A308', '82592340', '82597070',
                     '825A28A8', '825A2A60')
    d3d_functions = {prefix + address for prefix in ('sub_', '__imp__sub_')
                     for address in d3d_addresses}
    root = None
    for event, e in ET.iterparse(path, events=('start', 'end')):
        if event == 'start':
            if root is None:
                root = e
            continue
        if e.tag != 'row':
            continue
        # Intern only compact immutable values, not the entire 500 MB tree.
        for n in e.iter():
            if n.get('id'):
                if n.tag == 'tagged-backtrace':
                    continue
                elif n.tag == 'frame':
                    ids[n.get('id')] = n.get('name', n.get('addr', '?'))
                else:
                    ids[n.get('id')] = (n.text, n.get('fmt', ''))
        # Frames appear before their enclosing backtrace ends, but the loop
        # above visits parents first. Resolve stack after its children.
        stack = e[-1]
        if stack.get('id'):
            ids[stack.get('id')] = tuple(ids[f.get('ref') or f.get('id')] for f in stack)
        c = list(e)
        def value(n):
            return ids[n.get('ref') or n.get('id')]
        t = float(value(c[0])[0]) / 1e9
        process_name = value(c[2])[1].split(' (')[0]
        if (t >= skip and (end is None or t <= end) and value(c[4])[0] == 'Running'
                and (process is None or process_name == process)):
            weight = float(value(c[5])[0]) / 1e6
            name = value(c[1])[1]
            frames = value(c[6]) if c[6].tag != 'sentinel' else ()
            render = any('RenderFrame(' in f for f in frames)
            if render:
                render_threads.add(name)
            role = name
            core = value(c[3])[1]
            threads[role]['sample_ms'] += weight
            threads[role]['p_core_ms' if 'S Core' in core or 'P Core' in core else 'e_core_ms'] += weight
            counts['samples'] += 1
            counts['sample_ms'] += weight
            if not frames:
                counts['unresolved_stack_ms'] += weight
            if frames:
                leaf[frames[0]] += weight
                thread_leaf[name][frames[0]] += weight
                for f in set(frames):
                    inclusive[f] += weight
                writer = bool(d3d_functions.intersection(frames))
                cp_packet = any('CommandProcessor::ExecutePacket(' in f for f in frames)
                native = any(any(marker in f for marker in
                                 ('::Record(', '::CpDraw(', '::NativeDraw(', '::NativeSwap('))
                             for f in frames)
                cp_overhead = cp_packet and not native
                if writer:
                    graphics['guest_d3d_writer_path_ms'] += weight
                if cp_overhead:
                    graphics['cp_packet_outside_native_path_ms'] += weight
                if writer or cp_overhead:
                    graphics['writer_cp_union_ms'] += weight
                if any('::Record(' in f for f in frames):
                    graphics['record_inclusive_ms'] += weight
                draw_cleanup = any('::Draw::~Draw(' in f for f in frames)
                if draw_cleanup:
                    graphics['draw_destructor_inclusive_ms'] += weight
                if any('nfsmw::commands::Batch::Flush(' in f for f in frames):
                    graphics['command_batch_flush_named_path_ms'] += weight
                if any('nfsmw::commands::' in f for f in frames):
                    graphics['native_command_named_path_ms'] += weight
                frame_cleanup = any('::Frame::~Frame(' in f for f in frames)
                storage_lifecycle = any('nfsmw::FrameStoragePool<' in f for f in frames)
                if frame_cleanup:
                    graphics['frame_destructor_inclusive_ms'] += weight
                if storage_lifecycle:
                    graphics['frame_storage_named_path_ms'] += weight
                if frame_cleanup or storage_lifecycle:
                    graphics['frame_cleanup_storage_union_ms'] += weight
                if draw_cleanup or frame_cleanup or storage_lifecycle:
                    graphics['draw_frame_storage_lifecycle_union_ms'] += weight
                if any('nfsmw::FrameOwners<' in f and '::Capture(' in f for f in frames):
                    graphics['geometry_owner_capture_named_path_ms'] += weight
                if any('GpuBufferFor<' in f or 'GpuBufferForGeometry<' in f for f in frames):
                    graphics['geometry_gpu_selection_named_path_ms'] += weight
                if frames[0].startswith(('AGX::', '-[AGX')):
                    graphics['agx_leaf_ms'] += weight
        e.clear()
    merged = defaultdict(Counter)
    merged_leaf = defaultdict(Counter)
    for name, values in threads.items():
        role = 'native render queue' if name in render_threads else name.split(' (')[0]
        merged[role].update(values)
        merged_leaf[role].update(thread_leaf[name])
    return {'file': str(path), 'skip_seconds': skip, 'end_seconds': end,
            'process_filter': process,
            'totals': dict(counts), 'threads': dict(merged),
            'graphics_footprints_ms': dict(graphics),
            'thread_self_ms': {name: values.most_common(60) for name, values in merged_leaf.items()},
            'top_self_ms': leaf.most_common(40), 'top_inclusive_ms': inclusive.most_common(60)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['power', 'profile'])
    p.add_argument('files', nargs='+', type=Path)
    p.add_argument('--skip', type=float, default=10)
    p.add_argument('--end', type=float)
    p.add_argument('--process', help='Exact process name for CPU samples (e.g. LiveContainer)')
    args = p.parse_args()
    for file in args.files:
        result = power(file, args.skip, args.end) if args.mode == 'power' else profile(file, args.skip, args.end, args.process)
        print(json.dumps(result, sort_keys=True))
