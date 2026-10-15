#!/usr/bin/env python3
"""Forward unhandled Darwin faults instead of retrying them indefinitely."""
import sys
from patch_engine import run

FILE = "src/core/exception_handler_posix.cpp"
ANCHOR = '''static void ExceptionHandlerCallback(int signal_number, siginfo_t* signal_info,
                                     void* signal_context) {
'''
FORWARD = '''#if REX_PLATFORM_MAC
// Guest MMIO/write-watch faults are handled first. Other faults must reach
// the handler installed before ours (for example Metal's capture layer), or
// the process's default disposition. Returning silently retries the fault.
static void ForwardUnhandledSignal(int number, siginfo_t* info, void* context) {
  struct sigaction* previous = nullptr;
  switch (number) {
    case SIGILL: previous = &original_sigill_handler_; break;
    case SIGSEGV: previous = &original_sigsegv_handler_; break;
    case SIGBUS: previous = &original_sigbus_handler_; break;
    default: return;
  }
  const struct sigaction action = *previous;
  if (action.sa_handler == SIG_DFL || action.sa_handler == SIG_IGN) {
    // Ignoring a synchronous hardware fault cannot make the instruction
    // succeed. Restore default termination rather than creating a retry loop.
    struct sigaction fatal = {};
    fatal.sa_handler = SIG_DFL;
    sigemptyset(&fatal.sa_mask);
    sigaction(number, &fatal, nullptr);
    raise(number);
    return;
  }
  if (action.sa_flags & SA_RESETHAND) {
    previous->sa_handler = SIG_DFL;
    previous->sa_flags = 0;
    sigemptyset(&previous->sa_mask);
  }
  // Invoke with the original fault context so a handler can repair it.
  // Keep ReXGlue installed for subsequent guest faults.
  sigset_t old_mask;
  sigprocmask(SIG_BLOCK, &action.sa_mask, &old_mask);
  if (action.sa_flags & SA_NODEFER) {
    sigset_t current;
    sigprocmask(SIG_BLOCK, nullptr, &current);
    if (!sigismember(&action.sa_mask, number)) sigdelset(&current, number);
    sigprocmask(SIG_SETMASK, &current, nullptr);
  }
  if (action.sa_flags & SA_SIGINFO) action.sa_sigaction(number, info, context);
  else action.sa_handler(number);
  sigprocmask(SIG_SETMASK, &old_mask, nullptr);
}
#endif

'''
TAIL = '''      return;
    }
  }
}

void ExceptionHandler::Install(Handler fn, void* data) {
'''
TAIL_NEW = '''      return;
    }
  }
#if REX_PLATFORM_MAC
  ForwardUnhandledSignal(signal_number, signal_info, signal_context);
#endif
}

void ExceptionHandler::Install(Handler fn, void* data) {
'''
BLOCKS = [
    (FILE, "Darwin unhandled signal forwarding", ANCHOR, FORWARD + ANCHOR),
    (FILE, "forward only faults unclaimed by guest handlers", TAIL, TAIL_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_signal_forwarding", BLOCKS))
