#!/usr/bin/env python3
"""Check live-FPS patch reversibility and all-or-nothing SDK mutations."""
import os, pathlib, subprocess, tempfile
import patch_ios_live_fps as patch
from patch_engine import find_sdk
root = pathlib.Path(__file__).resolve().parents[2]
sdk = find_sdk(patch.GS)
with tempfile.TemporaryDirectory(prefix='nfsmw-live-fps-') as t:
    folder = pathlib.Path(t)
    paths = sorted({path for path, _, _, _ in patch.BLOCKS})
    original = {}
    for path in paths:
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((sdk/path).read_bytes())
        original[path] = target.read_bytes()
    env = dict(os.environ, NFSMW_SDK=str(folder))
    def run(*args, success=True):
        p = subprocess.run(['python3',str(root/'tools/ios/patch_ios_live_fps.py'),*args],env=env,capture_output=True,text=True)
        assert (p.returncode == 0) == success, p.stdout+p.stderr
    run('--revert')
    unpatched = {path:(folder/path).read_bytes() for path in paths}
    run(); applied = {path:(folder/path).read_bytes() for path in paths}
    run(); assert applied == {path:(folder/path).read_bytes() for path in paths}
    run('--revert'); assert unpatched == {path:(folder/path).read_bytes() for path in paths}
    # Break the final block so the first two would otherwise be written.
    target = folder / patch.CP
    target.write_text(target.read_text().replace(patch.WAIT, '', 1))
    before = {path:(folder/path).read_bytes() for path in paths}
    run(success=False)
    assert before == {path:(folder/path).read_bytes() for path in paths}
print('PASS: real SDK fixture apply/idempotency/exact revert; malformed final anchor leaves both files unchanged')
