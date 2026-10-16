#!/usr/bin/env python3
"""
Top scheduling priority for the two threads that set the frame rate, on iOS.

    python3 tools/ios/patch_ios_qos.py            apply
    python3 tools/ios/patch_ios_qos.py --status
    python3 tools/ios/patch_ios_qos.py --revert

Touches src/system/xthread.cpp and src/graphics/command_processor.cpp.


WHY
===

On Android, android/app/src/main/cpp/afinidad.cpp pins "GPU Commands" and
"Main XThread" to the prime cores and everything else off them: +17 % fps with
many draws, because the game's main thread was only on a prime core 25-32 % of
the time (docs/android.md, "Afinidad de hilos a nucleos").

iOS has no thread affinity. What it has is QoS classes: the scheduler keeps
QOS_CLASS_USER_INTERACTIVE work on the performance cores and ahead of
everything else. After the presentation fixes, the command processor (CP) is
what limits races on an iPad M4: it spends nearly the whole frame translating
draws, at ~7-9 us each.

A thread can only set its own QoS (pthread_set_qos_class_self_np), so this goes
at the start of each thread's own body, not where the SDK names it (on Apple,
naming another thread is a no-op anyway):

  - CommandProcessor::WorkerThreadMain: the "GPU Commands" thread;
  - XThread::Execute, for the guest's entry-point thread (main_thread_): the
    game's main thread.

Cvar ios_thread_qos, default on, to compare from Documents/extra_args.txt
(--ios_thread_qos=false).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

XT = "src/system/xthread.cpp"
CP = "src/graphics/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ignore_thread_priorities, true, "Kernel",
'''
CVAR_NEW = '''// LOCAL PATCH - iOS: QoS for the threads that set the frame rate
// (tools/ios/patch_ios_qos.py).
#if REX_PLATFORM_IOS
#include <pthread.h>
REXCVAR_DEFINE_BOOL(ios_thread_qos, true, "Kernel",
                    "iOS: run the game's main thread and the GPU command thread at "
                    "QOS_CLASS_USER_INTERACTIVE (performance cores, first in line)");
#endif
REXCVAR_DEFINE_BOOL(ignore_thread_priorities, true, "Kernel",
'''

MAIN_ANCHOR = '''                     thread_name_, thread_->system_id());

  // Let the kernel know we are starting.
  kernel_state_->OnThreadExecute(this);
'''
MAIN_NEW = '''                     thread_name_, thread_->system_id());

#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the game's main thread at the top QoS. Only a thread can
  // set its own, so here, at the start of its body.
  if (main_thread_ && REXCVAR_GET(ios_thread_qos)) {
    const int qos_result = pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
    REXLOG_INFO("[ios] game main thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  }
#endif
  // Let the kernel know we are starting.
  kernel_state_->OnThreadExecute(this);
'''

CP_INCLUDE_ANCHOR = '''#include <rex/graphics/xenos.h>
'''
CP_INCLUDE_NEW = '''#include <rex/graphics/xenos.h>
// LOCAL PATCH - iOS: QoS for the GPU command thread (tools/ios/patch_ios_qos.py).
#if REX_PLATFORM_IOS
#include <pthread.h>
#include <rex/cvar.h>
REXCVAR_DECLARE(bool, ios_thread_qos);
#endif
'''

CP_MAIN_ANCHOR = '''void CommandProcessor::WorkerThreadMain() {
  if (!SetupContext()) {
'''
CP_MAIN_NEW = '''void CommandProcessor::WorkerThreadMain() {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the GPU command thread at the top QoS.
  if (REXCVAR_GET(ios_thread_qos)) {
    const int qos_result = pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
    REXLOG_INFO("[ios] GPU Commands thread: QoS user-interactive {}",
                qos_result == 0 ? "set" : "FAILED");
  }
#endif
  if (!SetupContext()) {
'''

BLOCKS = [
    (XT, "the ios_thread_qos cvar", CVAR_ANCHOR, CVAR_NEW),
    (XT, "QoS for the game's main thread", MAIN_ANCHOR, MAIN_NEW),
    (CP, "declare ios_thread_qos", CP_INCLUDE_ANCHOR, CP_INCLUDE_NEW),
    (CP, "QoS for the GPU command thread", CP_MAIN_ANCHOR, CP_MAIN_NEW),
]

if __name__ == "__main__":
    # A prepared SDK may already contain the later retirement patch. Do not
    # reintroduce the obsolete hooks when prepare_sdk runs again.
    if "--revert" not in sys.argv:
        from patch_engine import find_sdk
        from patch_ios_retire_qos import BLOCKS as retired
        sdk = find_sdk(XT)
        if all(after in (sdk / path).read_text() for path, _, _, after in retired):
            print("[ok] ios_qos: superseded by ios_retire_qos")
            sys.exit(0)
    sys.exit(run("ios_qos", BLOCKS))
