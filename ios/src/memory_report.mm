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

#include <malloc/malloc.h>
#include <mach/mach.h>
#include <mach/task_info.h>

#include <algorithm>
#include <chrono>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

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
