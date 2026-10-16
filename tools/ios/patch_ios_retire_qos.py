#!/usr/bin/env python3
"""Retire explicit main/command thread QoS promotion; retain argument compatibility."""
import sys
from patch_engine import run

BLOCKS = [
    ("src/system/xthread.cpp", "disable legacy priority argument by default",
     'REXCVAR_DEFINE_BOOL(ios_thread_qos, true, "Kernel",',
     'REXCVAR_DEFINE_BOOL(ios_thread_qos, false, "Kernel",'),
    ("src/system/xthread.cpp", "remove main-thread promotion",
     '  if (main_thread_ && REXCVAR_GET(ios_thread_qos)) {',
     '  if (false) {  // retired: ordinary scheduling at every frame cap'),
    ("src/graphics/command_processor.cpp", "remove command-thread promotion",
     '  if (REXCVAR_GET(ios_thread_qos)) {',
     '  if (false) {  // retired: ordinary scheduling at every frame cap'),
]

if __name__ == "__main__":
    sys.exit(run("ios_retire_qos", BLOCKS))
