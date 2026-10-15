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
LEGACY_FORWARD = FORWARD
REPORT = '''// Opened outside signal context; only write() and stack formatting on fault.
static int signal_report_fd = -1;
static void ReportUnhandledSignal(int number, siginfo_t* info, void* context) {
  if (signal_report_fd < 0) return;
  char text[2048];
  size_t used = 0;
  auto field = [&](const char* name, uint64_t value) {
    while (*name) text[used++] = *name++;
    text[used++] = '='; text[used++] = '0'; text[used++] = 'x';
    for (int shift = 60; shift >= 0; shift -= 4) text[used++] = "0123456789abcdef"[(value >> shift) & 15];
    text[used++] = '\\n';
  };
  field("signal", number);
  field("code", info->si_code);
  field("fault_address", reinterpret_cast<uintptr_t>(info->si_addr));
#if REX_ARCH_ARM64
  auto mc = reinterpret_cast<ucontext_t*>(context)->uc_mcontext;
#if __DARWIN_OPAQUE_ARM_THREAD_STATE64
  field("pc", reinterpret_cast<uintptr_t>(mc->__ss.__opaque_pc));
  field("lr", reinterpret_cast<uintptr_t>(mc->__ss.__opaque_lr));
  field("sp", reinterpret_cast<uintptr_t>(mc->__ss.__opaque_sp));
#else
  field("pc", mc->__ss.__pc); field("lr", mc->__ss.__lr); field("sp", mc->__ss.__sp);
#endif
  field("esr", mc->__es.__esr);
  for (int i = 0; i < 29; ++i) {
    char name[] = {'x', char('0' + i / 10), char('0' + i % 10), 0};
    field(name, mc->__ss.__x[i]);
  }
#endif
  text[used++] = '\\n';
  (void)write(signal_report_fd, text, used);
}

'''
FORWARD = FORWARD.replace("// Guest MMIO", REPORT + "// Guest MMIO").replace(
    "  const struct sigaction action = *previous;",
    "  ReportUnhandledSignal(number, info, context);\n  const struct sigaction action = *previous;")
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
    (FILE, "signal report system headers", "#include <signal.h>\n",
     "#include <signal.h>\n#include <fcntl.h>\n#include <unistd.h>\n#include <cstdlib>\n"),
    (FILE, "Darwin unhandled signal forwarding", ANCHOR, FORWARD + ANCHOR),
    (FILE, "forward only faults unclaimed by guest handlers", TAIL, TAIL_NEW),
    (FILE, "open optional fault report outside signal context",
     "  if (!signal_handlers_installed_) {\n    struct sigaction signal_handler;",
     '''  if (!signal_handlers_installed_) {
#if REX_PLATFORM_MAC
    if (const char* path = std::getenv("NFSMW_SIGNAL_REPORT")) {
      signal_report_fd = open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0600);
    }
#endif
    struct sigaction signal_handler;'''),
]

if __name__ == "__main__":
    # Upgrade SDKs with the first version of this patch already applied.
    if "--status" not in sys.argv and "--revert" not in sys.argv:
        from patch_engine import find_sdk, read, write
        target = find_sdk(FILE) / FILE
        text, eol = read(target)
        if LEGACY_FORWARD + ANCHOR in text:
            write(target, text.replace(LEGACY_FORWARD + ANCHOR, FORWARD + ANCHOR), eol)
    sys.exit(run("ios_signal_forwarding", BLOCKS))
