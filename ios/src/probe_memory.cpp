// NFSMW Recompiled - guest memory diagnostics for the probe
//
// rex::memory::Memory::Initialize() is the first thing the game does, and on
// the first device run it failed. The SDK does not log errno, so its log line
// can only say which half failed. This repeats its steps by hand, reporting
// the exact call and errno, and then tries the alternative backing.
//
// What the SDK does on macOS (and so on iOS, src/system/xmemory.cpp and
// src/core/memory_posix.cpp):
//   1. shm_open() a POSIX shared memory object;
//   2. ftruncate() it to 0x120000000 + one page (~4.5 GB);
//   3. reserve a contiguous ~4.5 GB range with mmap(PROT_NONE);
//   4. map views of the object into it with mmap(MAP_SHARED | MAP_FIXED). The
//      same physical page is visible at several guest addresses, so two views
//      of the same offset MUST alias.
//
// The alternative is a Mach memory entry (mach_make_memory_entry_64 +
// vm_map), which is how Dolphin backs its emulated memory on iOS: anonymous
// memory, no file or shm name, so nothing for the sandbox to refuse.
//
// Both tests map three small views (two of offset 0, one near the end of the
// object), check that the two offset-0 views alias, and check mprotect() on a
// view, which the SDK's write watching relies on.

#include "probe_memory.h"

#include <fcntl.h>
#include <mach/mach.h>
#include <mach/mach_error.h>
#include <mach/vm_map.h>
#include <sys/mman.h>
#include <unistd.h>

#include <cerrno>
#include <cstdint>
#include <cstring>

#include <fmt/format.h>

namespace {

// What xmemory.cpp asks for: 0x120000000 rounded up past one 16 KB page.
constexpr size_t kBacking = 0x120000000ull + 0x4000;
constexpr size_t kView = 0x10000;
// The offsets of the three test views inside the backing object, and where
// they go inside the reserved range.
constexpr size_t kOffsetHigh = 0x110000000ull;
constexpr size_t kAddrA = 0;
constexpr size_t kAddrB = 0x100000000ull;
constexpr size_t kAddrC = 0x110000000ull;

std::string Errno(int e) { return fmt::format("errno {} ({})", e, std::strerror(e)); }
std::string Kern(kern_return_t kr) {
  return fmt::format("kern_return {} ({})", kr, mach_error_string(kr));
}

// The two offset-0 views see each other's writes, and a view can be made
// read-only. Returns "" if fine, or what went wrong.
std::string CheckViews(uint8_t* a, uint8_t* b, uint8_t* c) {
  a[0] = 0x5A;
  c[kView - 1] = 0xA5;
  if (b[0] != 0x5A) {
    return "the two views of offset 0 do NOT alias";
  }
  if (mprotect(a, 0x4000, PROT_READ) != 0) {
    return "mprotect(PROT_READ) on a view: " + Errno(errno);
  }
  if (mprotect(a, 0x4000, PROT_READ | PROT_WRITE) != 0) {
    return "mprotect(PROT_READ|PROT_WRITE) on a view: " + Errno(errno);
  }
  return "";
}

void* Reserve(std::vector<std::string>& lines, const char* who) {
  void* r = mmap(nullptr, kBacking, PROT_NONE, MAP_PRIVATE | MAP_ANON, -1, 0);
  if (r == MAP_FAILED) {
    lines.push_back(fmt::format("  {}: reserving ~4.5 GB with mmap(PROT_NONE) FAILS, {}", who,
                                Errno(errno)));
    return nullptr;
  }
  return r;
}

void TestPosixShm(std::vector<std::string>& lines) {
  const char* name = "/nfsmw_probe";
  shm_unlink(name);
  const int fd = shm_open(name, O_RDWR | O_CREAT, 0600);
  if (fd < 0) {
    lines.push_back("  POSIX shm (what the SDK uses): shm_open FAILS, " + Errno(errno));
    return;
  }
  shm_unlink(name);
  if (ftruncate(fd, static_cast<off_t>(kBacking)) != 0) {
    lines.push_back("  POSIX shm: shm_open OK, ftruncate to ~4.5 GB FAILS, " + Errno(errno));
    close(fd);
    return;
  }
  auto* base = static_cast<uint8_t*>(Reserve(lines, "POSIX shm"));
  if (!base) {
    close(fd);
    return;
  }
  uint8_t* v[3] = {};
  const size_t addr[3] = {kAddrA, kAddrB, kAddrC};
  const size_t off[3] = {0, 0, kOffsetHigh};
  std::string error;
  for (int i = 0; i < 3 && error.empty(); ++i) {
    void* r = mmap(base + addr[i], kView, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_FIXED, fd,
                   static_cast<off_t>(off[i]));
    if (r == MAP_FAILED) {
      error = fmt::format("mmap of view {} (offset 0x{:X}) FAILS, {}", i, off[i], Errno(errno));
    } else {
      v[i] = static_cast<uint8_t*>(r);
    }
  }
  if (error.empty()) {
    error = CheckViews(v[0], v[1], v[2]);
  }
  lines.push_back(error.empty() ? "  POSIX shm (what the SDK uses): OK"
                                : "  POSIX shm: shm_open and ftruncate OK, " + error);
  munmap(base, kBacking);
  close(fd);
}

void TestMachEntry(std::vector<std::string>& lines) {
  memory_object_size_t size = kBacking;
  mach_port_t entry = MACH_PORT_NULL;
  kern_return_t kr =
      mach_make_memory_entry_64(mach_task_self(), &size, 0,
                                MAP_MEM_NAMED_CREATE | VM_PROT_READ | VM_PROT_WRITE, &entry,
                                MACH_PORT_NULL);
  if (kr != KERN_SUCCESS) {
    lines.push_back("  Mach memory entry: mach_make_memory_entry_64 FAILS, " + Kern(kr));
    return;
  }
  auto* base = static_cast<uint8_t*>(Reserve(lines, "Mach memory entry"));
  if (!base) {
    mach_port_deallocate(mach_task_self(), entry);
    return;
  }
  uint8_t* v[3] = {};
  const size_t addr[3] = {kAddrA, kAddrB, kAddrC};
  const size_t off[3] = {0, 0, kOffsetHigh};
  std::string error;
  for (int i = 0; i < 3 && error.empty(); ++i) {
    vm_address_t a = reinterpret_cast<vm_address_t>(base + addr[i]);
    kr = vm_map(mach_task_self(), &a, kView, 0, VM_FLAGS_FIXED | VM_FLAGS_OVERWRITE, entry,
                off[i], FALSE, VM_PROT_READ | VM_PROT_WRITE, VM_PROT_READ | VM_PROT_WRITE,
                VM_INHERIT_NONE);
    if (kr != KERN_SUCCESS) {
      error = fmt::format("vm_map of view {} (offset 0x{:X}) FAILS, {}", i, off[i], Kern(kr));
    } else {
      v[i] = reinterpret_cast<uint8_t*>(a);
    }
  }
  if (error.empty()) {
    error = CheckViews(v[0], v[1], v[2]);
  }
  lines.push_back(error.empty()
                      ? fmt::format("  Mach memory entry (the alternative): OK, {:.2f} GB entry",
                                    size / 1073741824.0)
                      : "  Mach memory entry: entry OK, " + error);
  munmap(base, kBacking);
  mach_port_deallocate(mach_task_self(), entry);
}

}  // namespace

std::vector<std::string> GuestMemoryDiagnostics() {
  std::vector<std::string> lines;
  lines.push_back("Guest memory backing, step by step:");
  TestPosixShm(lines);
  TestMachEntry(lines);
  return lines;
}
