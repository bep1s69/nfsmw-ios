#!/usr/bin/env python3
"""Apply victorgbd's LAN network code plus Darwin adaptations to an ISOLATED SDK.

NFSMW_SDK=/path/to/multiplayer-sdk python3 tools/ios/patch_ios_multiplayer.py [--status|--revert]
The shared controls/release SDK is deliberately rejected. Upstream attribution and
pinned source identity are in CHANGELOG.md and docs/TECHNICAL.md.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group()
    g.add_argument('--status', action='store_true')
    g.add_argument('--revert', action='store_true')
    args = p.parse_args()
    value = os.environ.get('NFSMW_SDK')
    if not value:
        p.error('Set NFSMW_SDK explicitly to the isolated multiplayer SDK snapshot.')
    sdk = Path(value).resolve()
    shared = Path.home() / 'Developer/GitHub/rexglue-sdk-ios'
    if sdk == shared.resolve():
        p.error('Refusing the shared controls/release SDK; use an independent snapshot.')
    patch = Path(__file__).resolve().parent / 'patches/multiplayer_sdk.patch'
    def apply(*options):
        return subprocess.run(['git', 'apply', *options, str(patch)], cwd=sdk,
                              capture_output=True, text=True)
    undone = apply('--check').returncode == 0
    done = apply('--reverse', '--check').returncode == 0
    if args.status:
        print('[multiplayer] ' + ('applied' if done else 'not applied' if undone else 'SDK differs; inspect before patching'))
        return 0 if done or undone else 1
    if args.revert and undone or not args.revert and done:
        print('[multiplayer] already ' + ('reverted' if args.revert else 'applied'))
        return 0
    options = ['--reverse'] if args.revert else []
    checked = apply(*options, '--check')
    if checked.returncode:
        print(checked.stderr, file=sys.stderr)
        return checked.returncode
    result = apply(*options)
    print(result.stderr, end='', file=sys.stderr)
    if not result.returncode:
        print('[multiplayer] ' + ('reverted' if args.revert else 'applied') + ' to ' + str(sdk))
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
