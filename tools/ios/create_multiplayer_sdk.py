#!/usr/bin/env python3
"""Copy an already prepared SDK to an independent multiplayer tree (no Git/build data)."""
import argparse
from pathlib import Path
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source', type=Path, required=True)
p.add_argument('--destination', type=Path, required=True)
a = p.parse_args()
source, destination = a.source.resolve(), a.destination.resolve()
if destination.exists() or source == destination or source in destination.parents:
    p.error('Destination must be a new directory outside the source SDK.')
if not (source / '.nfsmw-ios/project-patches.applied').is_file():
    p.error('Source must already be prepared for the current controls build.')
subprocess.run(['rsync', '-a', '--exclude=.git', '--exclude=out', '--exclude=.nfsmw-android',
                str(source) + '/', str(destination) + '/'], check=True)
f = destination / 'thirdparty/CMakeLists.txt'
s = f.read_text()
old = 'if(NOT EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/${submodule}/.git")'
if s.count(old) != 1:
    raise SystemExit('SDK submodule validation changed; inspect snapshot before building.')
s = s.replace(old, 'if(NOT IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/${submodule}")')
f.write_text(s)
print('Created independent prepared SDK snapshot:', destination)
