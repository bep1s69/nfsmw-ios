// NFSMW Recompiled - startup trace on iOS
//
// The SDK's log file only opens in ReXApp::SetupEnvironment, buffered and
// flushed every 2 s. On the first run with the game, the app showed a black
// screen and the log had NOT ONE line from the game: whatever stopped it
// happened before that file opened, or never reached it. This is a second,
// tiny log for exactly that window:
//
//   - Documents/logs/boot.txt, appended to, one line per startup step;
//   - each line goes out with write(): no buffer, so it is in the file even if
//     the process dies right after;
//   - std::terminate (an exception nobody catches) and the fatal signals write
//     their reason before the process goes.
//
// The signal hooks chain to whatever handler was there before, and the SDK
// installs its own SIGSEGV/SIGBUS handler later for write watching (it chains
// too), so this does not get in its way.

#include "boot_trace.h"

#include <fcntl.h>
#include <signal.h>
#include <unistd.h>

#include <atomic>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <ctime>
#include <exception>
#include <string>

namespace nfsmw::boot {

namespace {

std::atomic<int> g_fd{-1};
struct sigaction g_previous[32];

void WriteRaw(const char* text, size_t length) {
  const int fd = g_fd.load(std::memory_order_acquire);
  if (fd < 0) {
    return;
  }
  while (length > 0) {
    const ssize_t n = write(fd, text, length);
    if (n <= 0) {
      if (n < 0 && errno == EINTR) {
        continue;
      }
      return;
    }
    text += n;
    length -= size_t(n);
  }
}

// Only async-signal-safe calls in here.
void OnSignal(int sig, siginfo_t* info, void* context) {
  char line[96];
  const int n = snprintf(line, sizeof(line), "FATAL signal %d (%s) at address %p\n", sig,
                         sig == SIGSEGV ? "SIGSEGV" : sig == SIGBUS ? "SIGBUS"
                         : sig == SIGABRT ? "SIGABRT" : sig == SIGILL ? "SIGILL"
                         : sig == SIGFPE ? "SIGFPE" : "?",
                         info ? info->si_addr : nullptr);
  if (n > 0) {
    WriteRaw(line, size_t(n));
  }
  // Hand over to whoever was there before (or the default: die).
  const struct sigaction& prev = g_previous[sig];
  if (prev.sa_flags & SA_SIGINFO) {
    if (prev.sa_sigaction) {
      prev.sa_sigaction(sig, info, context);
      return;
    }
  } else if (prev.sa_handler != SIG_DFL && prev.sa_handler != SIG_IGN && prev.sa_handler) {
    prev.sa_handler(sig);
    return;
  }
  signal(sig, SIG_DFL);
  raise(sig);
}

void OnTerminate() {
  std::string line = "FATAL std::terminate";
  if (auto e = std::current_exception()) {
    try {
      std::rethrow_exception(e);
    } catch (const std::exception& ex) {
      line += std::string(": uncaught exception: ") + ex.what();
    } catch (...) {
      line += ": uncaught exception of unknown type";
    }
  }
  Trace(line);
  std::abort();
}

}  // namespace

void Open(const std::string& path) {
  const int fd = open(path.c_str(), O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644);
  if (fd < 0) {
    return;
  }
  g_fd.store(fd, std::memory_order_release);
  std::set_terminate(OnTerminate);
  for (int sig : {SIGSEGV, SIGBUS, SIGABRT, SIGILL, SIGFPE}) {
    struct sigaction sa{};
    sa.sa_sigaction = OnSignal;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigemptyset(&sa.sa_mask);
    sigaction(sig, &sa, &g_previous[sig]);
  }
}

namespace {
std::atomic<bool> g_enabled{true};
}  // namespace

void SetEnabled(bool enabled) { g_enabled.store(enabled, std::memory_order_relaxed); }

void Trace(const std::string& line) {
  if (!g_enabled.load(std::memory_order_relaxed)) {
    return;
  }
  // Wall-clock time to the millisecond, like the SDK's log, so both line up.
  const auto now = std::chrono::system_clock::now();
  const std::time_t t = std::chrono::system_clock::to_time_t(now);
  const int ms = int(std::chrono::duration_cast<std::chrono::milliseconds>(
                         now.time_since_epoch()).count() % 1000);
  std::tm tm{};
  localtime_r(&t, &tm);
  char stamp[32];
  const size_t n = std::strftime(stamp, sizeof(stamp), "[%Y-%m-%d %H:%M:%S", &tm);
  std::string text(stamp, n);
  char tail[8];
  snprintf(tail, sizeof(tail), ".%03d] ", ms);
  text += tail;
  text += line;
  text += '\n';
  WriteRaw(text.data(), text.size());
}

}  // namespace nfsmw::boot
