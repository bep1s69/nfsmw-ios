#!/usr/bin/env python3
"""Cooperative live-profile QoS adoption at guest start and wait/yield boundaries.

Apply after utility/cheap-sleep patches. Host threads never opt in.
"""
import sys
from patch_engine import run
T = 'src/core/threading_posix.cpp'
X = 'src/system/xthread.cpp'
CP = 'src/graphics/command_processor.cpp'
TOP = 'namespace rex::thread {\n'
BRIDGE = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: cooperative live profiles (patch_ios_live_profiles.py).
namespace {
using NfsmwQosCallback = void (*)(int);
std::atomic<NfsmwQosCallback> nfsmw_qos_callback{nullptr};
thread_local int nfsmw_qos_role = 0;  // 0 host, 1 guest main, 2 guest worker, 3 command processor
void NfsmwPollQos() {
  if (!nfsmw_qos_role) return;
  if (auto callback = nfsmw_qos_callback.load(std::memory_order_acquire)) callback(nfsmw_qos_role);
}
struct NfsmwQosScope {
  NfsmwQosScope() { NfsmwPollQos(); }
  ~NfsmwQosScope() { NfsmwPollQos(); }
};
}
extern "C" __attribute__((visibility("default"))) void nfsmw_qos_set_callback(NfsmwQosCallback callback) {
  nfsmw_qos_callback.store(callback, std::memory_order_release);
}
extern "C" __attribute__((visibility("default"))) void nfsmw_qos_enter_guest(int role) {
  nfsmw_qos_role = role;
  NfsmwPollQos();
}
#endif

''' + TOP
DECL = '#include <rex/cvar.h>\n'
NEW_DECL = DECL + '''#if REX_PLATFORM_IOS
extern "C" void nfsmw_qos_enter_guest(int role);  // patch_ios_live_profiles.py
#endif
'''
ENTER = '  // Dispatch any APCs that were queued before the thread was created first.\n'
NEW_ENTER = '''#if REX_PLATFORM_IOS
  nfsmw_qos_enter_guest(main_thread_ ? 1 : 2);
#endif
''' + ENTER
SCOPE = '''#if REX_PLATFORM_IOS
  NfsmwQosScope nfsmw_qos_scope;  // patch_ios_live_profiles.py
#endif
'''
HEADS = ['void MaybeYield() {\n', 'void Sleep(std::chrono::microseconds duration) {\n',
         'WaitResult Wait(WaitHandle* wait_handle, bool is_alertable, std::chrono::milliseconds timeout) {\n',
         '                         bool is_alertable, std::chrono::milliseconds timeout) {\n',
         '                                           bool wait_all, bool is_alertable,\n'
         '                                           std::chrono::milliseconds timeout) {\n']
CP_ENTER = '  if (!SetupContext()) {\n'
CP_NEW = '#if REX_PLATFORM_IOS\n  nfsmw_qos_enter_guest(3);\n#endif\n' + CP_ENTER
BLOCKS = [(CP,'bridge declaration','void CommandProcessor::WorkerThreadMain() {\n',
            '#if REX_PLATFORM_IOS\nextern "C" void nfsmw_qos_enter_guest(int role);\n#endif\n' + 'void CommandProcessor::WorkerThreadMain() {\n'),(CP,'command registration',CP_ENTER,CP_NEW),
          (T,'callback bridge',TOP,BRIDGE),(X,'bridge declaration',DECL,NEW_DECL),
          (X,'guest registration',ENTER,NEW_ENTER)] + [
          (T,'safe point '+str(i),h,h+SCOPE) for i,h in enumerate(HEADS)]
if __name__ == '__main__':
    sys.exit(run('ios_live_profiles',BLOCKS))
