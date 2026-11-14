#!/usr/bin/env python3
"""Host-only Metal foliage depth-phase gate using private translated shaders.

Does not patch the game or live shader caches. Synthetic meshes, mipmaps and
constants exercise the actual named dev128 VS/PS code. This is not a captured
scene or a production admission/lifetime implementation. Output contains private
generated shader copies.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PAIRS = [('vs_03bfebaa942ca64c', 'ps_27d82ea0faa380a8'),
         ('vs_5c1d4bcee3584aa5', 'ps_684f4711f29b9f77')]
# Re-audit the alpha/depth assumptions if any private source changes.
SOURCE_SHA256 = {
    'vs_03bfebaa942ca64c': 'e616c083e2e5a5c6c79c3abedb5126df97c60078565948e65c3f309a573aeaf3',
    'ps_27d82ea0faa380a8': 'b228b77c7c13900038e37f4015d6faf749d86a443f13afc4ee7dc238a84b1d7e',
    'vs_5c1d4bcee3584aa5': 'dabadf062a2b196317c0945eb1880a2747c6e65b79a59425eb465b9d1e875c04',
    'ps_684f4711f29b9f77': '72296b93a70d71dc8bf503424eaed1c6ff11e53b759cfeb70cb37c60cd4d115b',
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--benchmark', action='store_true')
    a = ap.parse_args()
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    config = []
    for vs, ps in PAIRS:
        item = {'vs': vs, 'ps': ps}
        for key in (vs, ps):
            text = (a.sources / (key + '.hlsl')).read_text()
            item[key[:2] + '_source_sha256'] = hashlib.sha256(text.encode()).hexdigest()
            if item[key[:2] + '_source_sha256'] != SOURCE_SHA256[key]:
                raise ValueError('private shader changed; re-audit foliage gate: ' + key)
            if key.startswith('ps_'):
                # Same shaderBody and predicates; ignored colour output permits DCE.
                entry = re.search(r'\[\[fragment\]\]\s*PixelShaderOutput nfsmw_' + key
                                  + r'(\(.*?\))\s*\{\s*return (shaderBody\(.*?\));\s*\}', text, re.S)
                if not entry:
                    raise ValueError('unrecognized fragment entry: ' + key)
                text += '\n[[fragment]] void foliage_depth' + entry[1] + '\n{ (void)' + entry[2] + '; }\n'
            target = out / (key + '.metal')
            target.write_text(text)
            for cmd in ([ 'xcrun', '-sdk', 'macosx', 'metal', '-w', '-O2', '-std=metal3.1',
                          '-D__air__', '-fno-fast-math', '-ffp-contract=off', '-mmacosx-version-min=14.0',
                          '-c', str(target), '-o', str(target.with_suffix('.air'))],
                        ['xcrun', '-sdk', 'macosx', 'metal', str(target.with_suffix('.air')),
                         '-o', str(target.with_suffix('.metallib'))]):
                subprocess.run(cmd, check=True)
            if key.startswith('vs_'):
                item['offsets'] = dict((name, int(offset)) for name, offset in re.findall(
                    r'#define (\w+) \(\*\(reinterpret_cast<device float4\*>\(g_PushConstants.VertexShaderConstants \+ (\d+)\)\)\)', text))
                item['matrices'] = dict((name, int(offset)) for name, offset in re.findall(
                    r'#define (\w+)\(INDEX\).*?VertexShaderConstants \+ \((\d+) \+ min', text))
        config.append(item)
    (out / 'config.json').write_text(json.dumps(config, indent=2) + '\n')
    exe = out / 'foliage-depth'
    subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O2', '-fobjc-arc',
                    str(ROOT / 'tools/native/foliage_depth_fixture.mm'),
                    '-framework', 'Foundation', '-framework', 'Metal', '-o', str(exe)], check=True)
    subprocess.run([str(exe), str(out), 'benchmark' if a.benchmark else 'check'], check=True)


if __name__ == '__main__':
    main()
