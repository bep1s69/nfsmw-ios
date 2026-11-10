#!/usr/bin/env python3
"""Read xctrace XML exports without modifying captures or launching the game.

Power: export SystemPowerLevel, ProcessSubsystemPowerImpact,
DisplayBrightnessLevel, DeviceChargingState and SystemThermalState together.
Profile: export time-profile. XML IDs are global across the exported tables.
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


def profile(path, skip, end):
    ids, counts = {}, Counter()
    threads, leaf, inclusive = defaultdict(Counter), Counter(), Counter()
    render_threads = set()
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
        if t >= skip and (end is None or t <= end) and value(c[4])[0] == 'Running':
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
                for f in set(frames):
                    inclusive[f] += weight
        e.clear()
    merged = defaultdict(Counter)
    for name, values in threads.items():
        role = 'native render queue' if name in render_threads else name.split(' (')[0]
        merged[role].update(values)
    return {'file': str(path), 'skip_seconds': skip, 'end_seconds': end,
            'totals': dict(counts), 'threads': dict(merged),
            'top_self_ms': leaf.most_common(40), 'top_inclusive_ms': inclusive.most_common(60)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['power', 'profile'])
    p.add_argument('files', nargs='+', type=Path)
    p.add_argument('--skip', type=float, default=10)
    p.add_argument('--end', type=float)
    args = p.parse_args()
    for file in args.files:
        result = power(file, args.skip, args.end) if args.mode == 'power' else profile(file, args.skip, args.end)
        print(json.dumps(result, sort_keys=True))
