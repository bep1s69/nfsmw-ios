#!/usr/bin/env python3
"""
Battery experiment: run the game's main thread and the GPU command thread at
QOS_CLASS_UTILITY (cvar ios_utility_qos, default false).

    python3 tools/ios/patch_ios_utility_qos.py            apply
    python3 tools/ios/patch_ios_utility_qos.py --status
    python3 tools/ios/patch_ios_utility_qos.py --revert

The matched October 18 iPad recording showed Low Power Mode saving ~44% of
estimated drain with equal FPS, GPU and display cost: only CPU power fell,
while CPU time rose. iOS chooses CPU clocks partly from thread QoS, and these
two threads carry most of the performance-core time. The earlier Utility
experiment moved only the Metal encoding queue, already on efficiency cores.
This asks the scheduler for a cheaper operating point for the threads that
matter; whether it saves energy without dropping frames is what the test
decides. See docs/TECHNICAL.md, October 20.

Applies after patch_ios_battery_group; the baseline control wins when both
are set.
"""
import sys
from patch_engine import run

XT = 'src/system/xthread.cpp'
CP = 'src/graphics/command_processor.cpp'

CVAR_ANCHOR = 'REXCVAR_DEFINE_BOOL(ios_thread_qos, false, "Kernel",'
CVAR_NEW = '''REXCVAR_DEFINE_BOOL(ios_utility_qos, false, "Kernel",
                    "Battery experiment: game main thread and GPU command thread at "
                    "QOS_CLASS_UTILITY (restart required)");
''' + CVAR_ANCHOR

MAIN_ANCHOR = '''    REXLOG_INFO("[ios] game main thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  }
'''
MAIN_NEW = '''    REXLOG_INFO("[ios] game main thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  } else if (main_thread_ && REXCVAR_GET(ios_utility_qos)) {  // battery experiment
    const int qos_result = pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
    REXLOG_INFO("[ios] game main thread: QoS utility {}", qos_result == 0 ? "set" : "FAILED");
  }
'''

CP_ANCHOR = '''    REXLOG_INFO("[ios] GPU Commands thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  }
'''
CP_NEW = '''    REXLOG_INFO("[ios] GPU Commands thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  } else if (rex::cvar::Query<bool>("ios_utility_qos")) {  // battery experiment
    const int qos_result = pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
    REXLOG_INFO("[ios] GPU Commands thread: QoS utility {}", qos_result == 0 ? "set" : "FAILED");
  }
'''

BLOCKS = [
    (XT, 'the ios_utility_qos cvar', CVAR_ANCHOR, CVAR_NEW),
    (XT, 'utility QoS for the game main thread', MAIN_ANCHOR, MAIN_NEW),
    (CP, 'utility QoS for the GPU command thread', CP_ANCHOR, CP_NEW),
]

if __name__ == '__main__':
    sys.exit(run('ios_utility_qos', BLOCKS))
