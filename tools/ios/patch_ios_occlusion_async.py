#!/usr/bin/env python3
"""
Occlusion queries answered without stopping the CPU for the GPU: the game gets
the previous result for the same query at once, and the real one a frame later.

    python3 tools/ios/patch_ios_occlusion_async.py            apply
    python3 tools/ios/patch_ios_occlusion_async.py --status
    python3 tools/ios/patch_ios_occlusion_async.py --revert

Touches src/graphics/vulkan/command_processor.cpp and
include/rex/graphics/vulkan/command_processor.h.


WHAT THE LOG SHOWED
===================

In free roam on an iPad Pro M4 the game settled at 50-56 fps with the GPU not
the limit: the command processor (CP) thread was busy the whole frame
("idle 0.0") and, inside its ~19 ms, waited for the GPU 2-7 ms, exactly once
per frame.

VulkanCommandProcessor::EndGuestOcclusionQuery ends the open submission and
waits for ALL GPU work to finish (AwaitAllQueueOperationsCompletion), then
writes the sample count into guest memory. NFSMW runs a query per frame (the
sun flare: how much of the sun is visible), so every frame the CP stood idle
while the GPU caught up, and the GPU then ran dry while the CP recorded the
rest of the frame. (Turning the queries off is not an option: the game waits
for the count to be written and hangs at boot.)


THE CHANGE
==========

With the cvar ios_async_occlusion on (default):

  - the end of the query and the copy of its result are recorded in the open
    submission as before, but the submission is not ended and nothing waits;
  - the game gets, at once, the last count seen for that guest address (the
    query is the same object every frame), or a "fully visible" count the
    first time;
  - each query end first collects, without blocking, the queries whose
    submission the GPU has already finished, and updates the counts.

So the flare reacts one frame or two late, which cannot be seen. false gives
back the synchronous behaviour.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

H = "include/rex/graphics/vulkan/command_processor.h"
CPP = "src/graphics/vulkan/command_processor.cpp"

H_DECL_ANCHOR = '''  bool EndGuestOcclusionQuery(uint32_t sample_count_address);
'''
H_DECL_NEW = '''  bool EndGuestOcclusionQuery(uint32_t sample_count_address);
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: occlusion queries without a CPU-GPU sync
  // (tools/ios/patch_ios_occlusion_async.py).
  bool IosEndOcclusionQueryAsync(uint32_t sample_count_address, uint32_t host_index);
  void IosCollectOcclusionResults();
#endif
'''

H_MEMBERS_ANCHOR = '''  size_t nfsmw_inicio_pase_ = SIZE_MAX;  // PARCHE LOCAL - subidas adelantadas
'''
H_MEMBERS_NEW = '''  size_t nfsmw_inicio_pase_ = SIZE_MAX;  // PARCHE LOCAL - subidas adelantadas
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: occlusion queries waiting for their result, and the
  // last result per guest address (tools/ios/patch_ios_occlusion_async.py).
  struct IosPendingOcclusion {
    uint32_t sample_count_address;
    uint32_t host_index;
    uint64_t submission;
  };
  std::vector<IosPendingOcclusion> ios_pending_occlusion_;
  std::unordered_map<uint32_t, uint64_t> ios_occlusion_last_;
#endif
'''

CVAR_ANCHOR = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
'''
CVAR_NEW = '''REXCVAR_DECLARE(bool, medir_paquetes);  // idem
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_occlusion_async.py).
REXCVAR_DEFINE_BOOL(ios_async_occlusion, true, "GPU",
                    "iOS: answer occlusion queries with the previous result instead of making "
                    "the CPU wait for the GPU (one forced wait per frame in NFSMW)");
#endif
'''

END_ANCHOR = '''                                           VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);

  if (!EndSubmission(false)) {
    return false;
  }
  if (!AwaitAllQueueOperationsCompletion()) {
    return false;
  }
'''
END_NEW = '''                                           VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);

#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: no submission end, no wait.
  if (REXCVAR_GET(ios_async_occlusion)) {
    return IosEndOcclusionQueryAsync(sample_count_address, host_index);
  }
#endif
  if (!EndSubmission(false)) {
    return false;
  }
  if (!AwaitAllQueueOperationsCompletion()) {
    return false;
  }
'''

IMPL_ANCHOR = '''uint64_t VulkanCommandProcessor::NormalizeOcclusionSamples(uint64_t samples) const {
'''
IMPL_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_occlusion_async.py).
void VulkanCommandProcessor::IosCollectOcclusionResults() {
  if (ios_pending_occlusion_.empty()) {
    return;
  }
  CheckSubmissionFenceAndDeviceLoss(0);  // only looks, does not wait
  const uint64_t completed = GetCompletedSubmission();
  bool any_done = false;
  for (const IosPendingOcclusion& p : ios_pending_occlusion_) {
    any_done |= p.submission <= completed;
  }
  if (!any_done) {
    return;
  }
  const ui::vulkan::VulkanDevice* vulkan_device = GetVulkanDevice();
  if (!(vulkan_device->memory_types().host_coherent &
        (uint32_t(1) << occlusion_query_readback_memory_type_))) {
    VkMappedMemoryRange memory_range = {};
    memory_range.sType = VK_STRUCTURE_TYPE_MAPPED_MEMORY_RANGE;
    memory_range.memory = occlusion_query_readback_memory_;
    memory_range.offset = 0;
    memory_range.size =
        std::min(rex::round_up(VkDeviceSize(sizeof(uint64_t) * kMaxOcclusionQueries),
                               vulkan_device->properties().nonCoherentAtomSize),
                 occlusion_query_readback_memory_size_);
    vulkan_device->functions().vkInvalidateMappedMemoryRanges(vulkan_device->device(), 1,
                                                               &memory_range);
  }
  const uint64_t* results = reinterpret_cast<const uint64_t*>(occlusion_query_readback_mapping_);
  size_t kept = 0;
  for (const IosPendingOcclusion& p : ios_pending_occlusion_) {
    if (p.submission <= completed) {
      ios_occlusion_last_[p.sample_count_address] = NormalizeOcclusionSamples(results[p.host_index]);
    } else {
      ios_pending_occlusion_[kept++] = p;
    }
  }
  ios_pending_occlusion_.resize(kept);
}

bool VulkanCommandProcessor::IosEndOcclusionQueryAsync(uint32_t sample_count_address,
                                                       uint32_t host_index) {
  IosCollectOcclusionResults();
  ios_pending_occlusion_.push_back({sample_count_address, host_index, GetCurrentSubmission()});
  // Never let the list grow without bound if the GPU stalls.
  if (ios_pending_occlusion_.size() > 1024) {
    ios_pending_occlusion_.erase(ios_pending_occlusion_.begin());
  }
  // The last count for this query, or "fully visible" (a 1280x720 target) the
  // first time.
  auto last = ios_occlusion_last_.find(sample_count_address);
  WriteGuestOcclusionResult(sample_count_address,
                            last != ios_occlusion_last_.end() ? last->second : 1280u * 720u);
  return true;
}
#endif

uint64_t VulkanCommandProcessor::NormalizeOcclusionSamples(uint64_t samples) const {
'''

BLOCKS = [
    (H, "declare the async query functions", H_DECL_ANCHOR, H_DECL_NEW),
    (H, "the pending queries and last results", H_MEMBERS_ANCHOR, H_MEMBERS_NEW),
    (CPP, "the ios_async_occlusion cvar", CVAR_ANCHOR, CVAR_NEW),
    (CPP, "query end: async on iOS", END_ANCHOR, END_NEW),
    (CPP, "the async query functions", IMPL_ANCHOR, IMPL_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_occlusion_async", BLOCKS))
