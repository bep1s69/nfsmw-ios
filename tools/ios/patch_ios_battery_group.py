#!/usr/bin/env python3
"""Restore historical priority only for the all-off battery experiment control."""
import sys
from patch_engine import run

FILE = 'src/system/xthread.cpp'
MARKER = 'REXCVAR_DEFINE_BOOL(ios_thread_qos, false, "Kernel",'
PREFIX = '''REXCVAR_DEFINE_BOOL(ios_battery_baseline_qos, false, "Kernel",
                    "Battery experiment control: restore historical top priority above 40 FPS");
'''
BLOCKS = [
    (FILE, 'baseline priority control', MARKER, PREFIX + MARKER),
    (FILE, 'baseline main priority',
     '  if (false) {  // retired: ordinary scheduling at every frame cap',
     '  if (main_thread_ && REXCVAR_GET(ios_battery_baseline_qos)) {  // experiment control only'),
    ('src/graphics/command_processor.cpp', 'baseline command priority',
     '  if (false) {  // retired: ordinary scheduling at every frame cap',
     '  if (rex::cvar::Query<bool>("ios_battery_baseline_qos")) {  // experiment control only'),
]
if __name__ == '__main__':
    sys.exit(run('ios_battery_group', BLOCKS))
