#!/usr/bin/env python3
"""
A trace of the recent semaphore operations, for the hang watchdog.

    python3 tools/ios/patch_ios_semaphore_trace.py            apply
    python3 tools/ios/patch_ios_semaphore_trace.py --status
    python3 tools/ios/patch_ios_semaphore_trace.py --revert

Touches src/kernel/xboxkrnl/xboxkrnl_threading.cpp.

Some boots hung for good: the game's loader waiting for a disc read it had
queued, the threads that read waiting for work, each on a kernel semaphore (a
lost wake-up). This keeps the last 512 semaphore operations (Nt/KeRelease,
waits starting and ending; thread, handle, guest object, counts, result) in a
lock-free ring, and exports rex_semaphore_trace_log(), which the watchdog
(common/src/nfsmw_app.h) calls when every game thread has stopped.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/kernel/xboxkrnl/xboxkrnl_threading.cpp"

BLOCKS = [
    (FILE, 'the trace ring',
     '\nuint32_t xeKeReleaseSemaphore(X_KSEMAPHORE* semaphore_ptr, uint32_t increment, uint32_t adjustment,\n',
     '\n// PARCHE LOCAL - rastro de semaforos: las ultimas 512 operaciones (soltar,\n// empezar a esperar, terminar de esperar) de cualquier semaforo, en un anillo\n// sin cerrojos. El vigilante de NFSMW lo vuelca cuando el juego se queda\n// parado (rex_semaphore_trace_log): un arranque que se cuelga esperando un\n// semaforo que nadie suelta deja ver quien solto que y cuando.\nnamespace {\nstruct SemTrace {\n  uint64_t ns;\n  uint32_t thread, handle, object;  // handle (Nt*, else 0) and the guest object\n  int32_t count, previous;\n  char op;  // R NtRelease, K KeRelease, W espera empieza, w espera acaba\n  uint32_t result;\n};\nconstexpr uint32_t kSemTraceSize = 512;\nSemTrace sem_trace[kSemTraceSize];\nstd::atomic<uint32_t> sem_trace_next{0};\n\nvoid TraceSem(char op, uint32_t handle, uint32_t object, int32_t count, int32_t previous, uint32_t result) {\n  const uint32_t i = sem_trace_next.fetch_add(1, std::memory_order_relaxed) % kSemTraceSize;\n  sem_trace[i] = {uint64_t(std::chrono::duration_cast<std::chrono::nanoseconds>(\n                               std::chrono::steady_clock::now().time_since_epoch())\n                               .count()),\n                  XThread::GetCurrentThreadId(), handle, object, count, previous, op, result};\n}\n\nbool IsSemaphore(const object_ref<XObject>& o) { return o && o->type() == XObject::Type::Semaphore; }\n}  // namespace\n\nextern "C" void rex_semaphore_trace_log() {\n  const uint32_t end = sem_trace_next.load();\n  const uint32_t n = std::min(end, kSemTraceSize);\n  const uint64_t last = n ? sem_trace[(end - 1) % kSemTraceSize].ns : 0;\n  REXLOG_ERROR("[semaforos] las ultimas {} operaciones (de {}), la mas reciente al final:", n, end);\n  for (uint32_t k = end - n; k != end; ++k) {\n    const SemTrace& e = sem_trace[k % kSemTraceSize];\n    REXLOG_ERROR("[semaforos] {:9.3f} ms hilo 0x{:X} {} handle 0x{:08X} objeto 0x{:08X} cuenta {} anterior {} "\n                 "resultado 0x{:X}",\n                 -double(last - e.ns) / 1e6, e.thread, e.op, e.handle, e.object, e.count, e.previous, e.result);\n  }\n}\n\nuint32_t xeKeReleaseSemaphore(X_KSEMAPHORE* semaphore_ptr, uint32_t increment, uint32_t adjustment,\n'),
    (FILE, 'KeReleaseSemaphore traced',
     '      sem->ReleaseSemaphore(static_cast<int32_t>(adjustment), &previous_count);\n  return static_cast<uint32_t>(previous_count);\n',
     "      sem->ReleaseSemaphore(static_cast<int32_t>(adjustment), &previous_count);\n  TraceSem('K', 0, sem->guest_object(), int32_t(adjustment), previous_count, success ? 0u : 1u);\n  return static_cast<uint32_t>(previous_count);\n"),
    (FILE, 'NtReleaseSemaphore traced',
     '      result = X_STATUS_SEMAPHORE_LIMIT_EXCEEDED;\n    }\n  } else {\n',
     "      result = X_STATUS_SEMAPHORE_LIMIT_EXCEEDED;\n    }\n    TraceSem('R', sem_handle, sem->guest_object(), int32_t(release_count), previous_count, result);\n  } else {\n"),
    (FILE, 'KeWaitForSingleObject traced (start)',
     '\n  X_STATUS result = object->Wait(wait_reason, processor_mode, alertable, timeout_ptr);\n',
     "\n  const bool traced = IsSemaphore(object);\n  if (traced) TraceSem('W', 0, object->guest_object(), 0, 0, 0);\n  X_STATUS result = object->Wait(wait_reason, processor_mode, alertable, timeout_ptr);\n"),
    (FILE, 'KeWaitForSingleObject traced (end)',
     '  X_STATUS result = object->Wait(wait_reason, processor_mode, alertable, timeout_ptr);\n\n',
     "  X_STATUS result = object->Wait(wait_reason, processor_mode, alertable, timeout_ptr);\n  if (traced) TraceSem('w', 0, object->guest_object(), 0, 0, result);\n\n"),
    (FILE, 'NtWaitForSingleObjectEx traced (start)',
     '    uint64_t timeout = timeout_ptr ? static_cast<uint64_t>(*timeout_ptr) : 0u;\n    result = object->Wait(3, wait_mode, alertable, timeout_ptr ? &timeout : nullptr);\n',
     "    uint64_t timeout = timeout_ptr ? static_cast<uint64_t>(*timeout_ptr) : 0u;\n    const bool traced = IsSemaphore(object);\n    if (traced) TraceSem('W', object_handle, object->guest_object(), 0, 0, 0);\n    result = object->Wait(3, wait_mode, alertable, timeout_ptr ? &timeout : nullptr);\n"),
    (FILE, 'NtWaitForSingleObjectEx traced (end)',
     '    result = object->Wait(3, wait_mode, alertable, timeout_ptr ? &timeout : nullptr);\n    if (alertable && result == X_STATUS_USER_APC) {\n',
     "    result = object->Wait(3, wait_mode, alertable, timeout_ptr ? &timeout : nullptr);\n    if (traced) TraceSem('w', object_handle, object->guest_object(), 0, 0, result);\n    if (alertable && result == X_STATUS_USER_APC) {\n"),
]

if __name__ == "__main__":
    sys.exit(run("ios_semaphore_trace", BLOCKS))
