// NFSMW Recompiled - where the app's memory goes (iOS)
//
// iOS ends the app when its footprint (phys_footprint) reaches its limit
// (about 6 GB on a 12 GB iPhone, far less on older devices). The footprint
// is dirty and compressed memory plus GPU memory; this splits it so a log
// says which part grows:
//   - graphics: the GPU allocations (Metal's own and MoltenVK's);
//   - Metal device: what this process's Metal device has allocated;
//   - malloc: the heap in use;
//   - compressed: memory iOS compressed (it stalls the app to do it).
// It also says where the CPU time goes: each thread's share of a core since
// the last report, with the battery level, to compare settings by heat.

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <UIKit/UIKit.h>

#include "memory_report.h"

#include "boot_trace.h"

#include <dlfcn.h>
#include <execinfo.h>
#include <fcntl.h>
#include <malloc/malloc.h>
#include <unistd.h>
#include <mach-o/dyld.h>
#include <mach/mach.h>
#include <mach/task_info.h>

#include <algorithm>
#include <atomic>
#include <cstring>
#include <chrono>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

// Who allocates the big heap blocks (low-RAM work, November 6): Instruments
// attaches after startup under LiveContainer, so its blocks have no stacks.
REXCVAR_DEFINE_BOOL(nfsmw_diag_alloc_trace, false, "GPU",
                    "Diagnostics: write the call stack of every heap block of 4 MB or more, and of the "
                    "first 8 blocks of 464 KB and 128 KB, to logs/allocs.txt");

// libmalloc calls this (MallocStackLogging's hook) for every allocation.
typedef void(malloc_logger_t)(uint32_t type, uintptr_t arg1, uintptr_t arg2, uintptr_t arg3, uintptr_t result,
                              uint32_t num_hot_frames_to_skip);
extern "C" malloc_logger_t* malloc_logger;

namespace nfsmw::memory {

const char* ThermalState() {
  switch ([NSProcessInfo processInfo].thermalState) {
    case NSProcessInfoThermalStateNominal: return "nominal";
    case NSProcessInfoThermalStateFair: return "fair";
    case NSProcessInfoThermalStateSerious: return "serious";
    case NSProcessInfoThermalStateCritical: return "critical";
  }
  return "unknown";
}

void Report(const char* stage) {
  task_vm_info_data_t vm = {};
  mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
  if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&vm), &count) != KERN_SUCCESS) {
    return;
  }
  malloc_statistics_t heap = {};
  malloc_zone_statistics(nullptr, &heap);
  static id<MTLDevice> device = MTLCreateSystemDefaultDevice();
  constexpr double kMiB = 1024.0 * 1024.0;
  const bool has_limit = count >= TASK_VM_INFO_REV4_COUNT;
  REXLOG_INFO("[memory] {}: footprint {:.0f} MiB (peak {:.0f}), {} | graphics {:.0f} MiB (+{:.0f} compressed), "
              "Metal device {:.0f} MiB | malloc {:.0f} MiB in use | internal {:.0f}, compressed {:.0f}, "
              "files {:.0f} MiB | thermal state {}{}",
              stage, vm.phys_footprint / kMiB, vm.ledger_phys_footprint_peak / kMiB,
              has_limit ? fmt::format("{:.0f} MiB left before the limit", vm.limit_bytes_remaining / kMiB)
                        : std::string("limit unknown"),
              vm.ledger_tag_graphics_footprint / kMiB, vm.ledger_tag_graphics_footprint_compressed / kMiB,
              device ? device.currentAllocatedSize / kMiB : 0.0, heap.size_in_use / kMiB, vm.internal / kMiB,
              vm.compressed / kMiB, vm.external / kMiB, ThermalState(),
              [NSProcessInfo processInfo].lowPowerModeEnabled ? ", Low Power Mode on" : "");
  // Close to the limit: iOS ends the app with SIGKILL, which nothing catches,
  // so say it in boot.txt (written at once) and get the log to the file.
  constexpr uint64_t kNearLimit = 384ull << 20;
  if (has_limit && vm.limit_bytes_remaining < kNearLimit) {
    boot::Trace(fmt::format("memory: {} with {:.0f} MiB left before the limit (footprint {:.0f} MiB)", stage,
                            vm.limit_bytes_remaining / kMiB, vm.phys_footprint / kMiB));
    rex::FlushLogging();
  }
}

namespace {
int alloc_trace_fd = -1;
std::atomic<int> alloc_trace_464k{0}, alloc_trace_128k{0};
// One stack at a time, all threads: a thread_local here crashed dev96 at Play
// (the first touch of a thread's TLS allocates, which re-entered the hook).
std::atomic_flag alloc_trace_busy = ATOMIC_FLAG_INIT;

// Runs inside malloc: no allocation, only snprintf into the stack, dladdr and
// write(). Frames as image+offset, for atos against the build's binaries.
void AllocTraceHook(uint32_t type, uintptr_t, uintptr_t arg2, uintptr_t arg3, uintptr_t result, uint32_t) {
  constexpr uint32_t kAllocate = 2, kDeallocate = 4;
  if (!(type & kAllocate) || alloc_trace_fd < 0) return;
  const uintptr_t size = (type & kDeallocate) ? arg3 : arg2;  // realloc: new size in arg3
  bool wanted = size >= (4u << 20);
  if (!wanted && size == 464u * 1024) wanted = alloc_trace_464k.fetch_add(1) < 8;
  if (!wanted && size == 128u * 1024) wanted = alloc_trace_128k.fetch_add(1) < 8;
  if (!wanted || alloc_trace_busy.test_and_set(std::memory_order_acquire)) return;
  void* frames[24];
  const int n = backtrace(frames, 24);
  char line[4096];
  int at = snprintf(line, sizeof(line), "alloc %lu bytes (%lu KiB) at %p:", (unsigned long)size,
                    (unsigned long)(size >> 10), (void*)result);
  for (int i = 2; i < n && at < int(sizeof(line)) - 160; ++i) {
    Dl_info info = {};
    if (dladdr(frames[i], &info) && info.dli_fname) {
      const char* name = strrchr(info.dli_fname, '/');
      at += snprintf(line + at, sizeof(line) - at, " %s+0x%lx%s%s", name ? name + 1 : info.dli_fname,
                     (unsigned long)((uintptr_t)frames[i] - (uintptr_t)info.dli_fbase), info.dli_sname ? "/" : "",
                     info.dli_sname ? info.dli_sname : "");
    } else {
      at += snprintf(line + at, sizeof(line) - at, " %p", frames[i]);
    }
  }
  if (at > int(sizeof(line)) - 2) at = int(sizeof(line)) - 2;
  line[at++] = '\n';
  write(alloc_trace_fd, line, at);
  alloc_trace_busy.clear(std::memory_order_release);
}
}  // namespace

void StartAllocationTrace(const char* path) {
  if (!REXCVAR_GET(nfsmw_diag_alloc_trace)) return;
  alloc_trace_fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
  if (alloc_trace_fd < 0) return;
  // Each image's load address, to match the offsets with the binaries.
  for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
    char line[1200];
    const int at = snprintf(line, sizeof(line), "image %p %s\n", (void*)_dyld_get_image_header(i),
                            _dyld_get_image_name(i));
    write(alloc_trace_fd, line, std::min<int>(at, sizeof(line) - 1));
  }
  malloc_logger = &AllocTraceHook;
  REXLOG_INFO("[memory] allocation trace on: logs/allocs.txt");
}

void TraceLimit() {
  task_vm_info_data_t vm = {};
  mach_msg_type_number_t count = TASK_VM_INFO_COUNT;
  constexpr double kMiB = 1024.0 * 1024.0;
  const double ram = [NSProcessInfo processInfo].physicalMemory / kMiB;
  if (task_info(mach_task_self(), TASK_VM_INFO, reinterpret_cast<task_info_t>(&vm), &count) != KERN_SUCCESS ||
      count < TASK_VM_INFO_REV4_COUNT) {
    boot::Trace(fmt::format("memory: limit unknown, device RAM {:.0f} MiB", ram));
    return;
  }
  const double limit = (vm.phys_footprint + vm.limit_bytes_remaining) / kMiB;
  boot::Trace(fmt::format("memory: limit {:.0f} MiB, device RAM {:.0f} MiB{}", limit, ram,
                          limit < 3072 ? " (low: a race needs about 1.7-2 GB)" : ""));
  REXLOG_INFO("[memory] limit {:.0f} MiB, device RAM {:.0f} MiB", limit, ram);
}

void StartPressureWatch(void (*on_pressure)()) {
  static dispatch_source_t source = dispatch_source_create(
      DISPATCH_SOURCE_TYPE_MEMORYPRESSURE, 0, DISPATCH_MEMORYPRESSURE_WARN | DISPATCH_MEMORYPRESSURE_CRITICAL,
      dispatch_get_global_queue(QOS_CLASS_UTILITY, 0));
  if (!source) return;
  dispatch_source_set_event_handler(source, ^{
    const unsigned long level = dispatch_source_get_data(source);
    const bool critical = level & DISPATCH_MEMORYPRESSURE_CRITICAL;
    const bool warn = level & DISPATCH_MEMORYPRESSURE_WARN;
    if (!critical && !warn) return;  // back to normal
    boot::Trace(critical ? "memory: iOS says memory is critical, freeing caches"
                         : "memory: iOS warns memory is short, freeing caches");
    REXLOG_WARN("[memory] pressure {}: freeing idle caches", critical ? "critical" : "warning");
    if (on_pressure) on_pressure();
    Report(critical ? "memory critical" : "memory warning");
    rex::FlushLogging();
  });
  dispatch_resume(source);
}

void ReportCpu() {
  // CPU time of each thread so far (user + system), by its system-wide id.
  static std::unordered_map<uint64_t, uint64_t> last_us;
  static auto last_time = std::chrono::steady_clock::now();
  thread_act_array_t threads = nullptr;
  mach_msg_type_number_t thread_count = 0;
  if (task_threads(mach_task_self(), &threads, &thread_count) != KERN_SUCCESS) {
    return;
  }
  std::unordered_map<uint64_t, uint64_t> now_us;
  std::vector<std::pair<uint64_t, std::string>> used;  // microseconds since the last report, name
  uint64_t total_us = 0;
  for (mach_msg_type_number_t i = 0; i < thread_count; ++i) {
    thread_identifier_info_data_t id_info = {};
    mach_msg_type_number_t n = THREAD_IDENTIFIER_INFO_COUNT;
    thread_extended_info_data_t ext = {};
    mach_msg_type_number_t m = THREAD_EXTENDED_INFO_COUNT;
    if (thread_info(threads[i], THREAD_IDENTIFIER_INFO, reinterpret_cast<thread_info_t>(&id_info), &n) ==
            KERN_SUCCESS &&
        thread_info(threads[i], THREAD_EXTENDED_INFO, reinterpret_cast<thread_info_t>(&ext), &m) == KERN_SUCCESS) {
      const uint64_t us = (ext.pth_user_time + ext.pth_system_time) / 1000;  // nanoseconds
      now_us[id_info.thread_id] = us;
      auto before = last_us.find(id_info.thread_id);
      const uint64_t delta = before == last_us.end() ? 0 : us - std::min(us, before->second);
      total_us += delta;
      if (delta) used.emplace_back(delta, ext.pth_name[0] ? std::string(ext.pth_name)
                                                          : "tid " + std::to_string(id_info.thread_id));
    }
    mach_port_deallocate(mach_task_self(), threads[i]);
  }
  vm_deallocate(mach_task_self(), vm_address_t(threads), thread_count * sizeof(thread_act_t));
  const auto now = std::chrono::steady_clock::now();
  const double wall_us = std::chrono::duration<double, std::micro>(now - last_time).count();
  const bool first = last_us.empty();
  last_us.swap(now_us);
  last_time = now;
  if (first || wall_us <= 0) return;
  std::sort(used.begin(), used.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
  std::string top;
  for (size_t i = 0; i < used.size() && i < 8; ++i) {
    top += fmt::format("{}{} {:.0f}%", i ? ", " : "", used[i].second, 100.0 * used[i].first / wall_us);
  }
  const float battery = [UIDevice currentDevice].batteryLevel;  // -1 until monitoring is on
  REXLOG_INFO("[cpu] {:.0f}% of a core over {:.0f} s ({} threads) | {} | battery {}, Low Power Mode {}, thermal {}",
              100.0 * total_us / wall_us, wall_us / 1e6, thread_count, top,
              battery >= 0 ? fmt::format("{:.0f}%", battery * 100.0f) : std::string("unknown"),
              [NSProcessInfo processInfo].lowPowerModeEnabled ? "on" : "off", ThermalState());
}

void StartPeriodicReports(int seconds) {
  dispatch_async(dispatch_get_main_queue(), ^{
    [UIDevice currentDevice].batteryMonitoringEnabled = YES;
  });
  std::thread([seconds] {
    pthread_setname_np("nfsmw reports");
    ReportCpu();  // the starting point
    for (;;) {
      std::this_thread::sleep_for(std::chrono::seconds(seconds));
      Report("every 10 s");
      ReportCpu();
    }
  }).detach();
}

}  // namespace nfsmw::memory
