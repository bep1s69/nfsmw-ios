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

#import <Foundation/Foundation.h>
#import <Metal/Metal.h>

#include "memory_report.h"

#include <malloc/malloc.h>
#include <mach/mach.h>
#include <mach/task_info.h>

#include <chrono>
#include <thread>

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

void StartPeriodicReports(int seconds) {
  std::thread([seconds] {
    for (;;) {
      std::this_thread::sleep_for(std::chrono::seconds(seconds));
      Report("every 10 s");
    }
  }).detach();
}

}  // namespace nfsmw::memory
