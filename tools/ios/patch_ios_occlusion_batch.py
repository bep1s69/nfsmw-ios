#!/usr/bin/env python3
"""
Occlusion queries reset and copied in batches: one pool reset for up to 64
queries and one result copy per run of consecutive queries, per submission,
instead of a reset and a copy for each query.

    python3 tools/ios/patch_ios_occlusion_batch.py            apply
    python3 tools/ios/patch_ios_occlusion_batch.py --status
    python3 tools/ios/patch_ios_occlusion_batch.py --revert

Touches src/graphics/vulkan/command_processor.cpp. Builds on
patch_ios_occlusion_async.py (results read a submission later). Cvar
ios_batch_occlusion (on).


WHY
===

A Metal System Trace in a race at the 120 fps cap (~95 fps, GPU busy 84 %):
13 % of the GPU's time went to unlabelled "Blit Command" encoders, ~9 a frame
at ~150 us each, all at the end of the command buffers. They are MoltenVK's
vkCmdResetQueryPool and vkCmdCopyQueryPoolResults: the SDK resets the query
before each guest occlusion query and copies its one result after it, and
each becomes a blit of its own. NFSMW uses the queries for the sun glare and
the like; they have to keep working (the glare fades when the sun is hidden).

Now, in a submission, the first query resets the pool for itself and the next
63 indices (the cursor only moves forward, so they are the next queries), and
the queries' results are copied when the submission ends, one copy for each
run of consecutive indices (normally one). Same queries, same results, read at
the same time (a submission later, as with patch_ios_occlusion_async.py).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/graphics/vulkan/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_async_occlusion, true, "GPU",
                    "iOS: answer occlusion queries with the previous result instead of making "
                    "the CPU wait for the GPU (one forced wait per frame in NFSMW)");
#endif
'''
CVAR_NEW = '''REXCVAR_DEFINE_BOOL(ios_async_occlusion, true, "GPU",
                    "iOS: answer occlusion queries with the previous result instead of making "
                    "the CPU wait for the GPU (one forced wait per frame in NFSMW)");
#endif
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_occlusion_batch.py).
REXCVAR_DEFINE_BOOL(ios_batch_occlusion, true, "GPU",
                    "iOS: occlusion queries reset and copied in batches per submission instead "
                    "of a blit for each query (with ios_async_occlusion)");
namespace {
// The query indices reset in the current submission, and the queries whose
// results are still to be copied when it ends. One command processor.
uint64_t ios_occlusion_reset_submission = UINT64_MAX;
uint32_t ios_occlusion_reset_first = 0, ios_occlusion_reset_end = 0;
std::vector<uint32_t> ios_occlusion_copies;
bool IosBatchOcclusion() {
  return REXCVAR_GET(ios_batch_occlusion) && REXCVAR_GET(ios_async_occlusion);
}
}  // namespace
#endif
'''

RESET_ANCHOR = '''  DeferredCommandBuffer& command_buffer = deferred_command_buffer();
  command_buffer.CmdVkResetQueryPool(occlusion_query_pool_, host_index, 1);
  command_buffer.CmdVkBeginQuery(occlusion_query_pool_, host_index, 0);
'''
RESET_NEW = '''  DeferredCommandBuffer& command_buffer = deferred_command_buffer();
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: one reset for this query and the next 63 in this
  // submission (tools/ios/patch_ios_occlusion_batch.py).
  if (IosBatchOcclusion()) {
    const uint64_t submission = GetCurrentSubmission();
    if (ios_occlusion_reset_submission != submission || host_index < ios_occlusion_reset_first ||
        host_index >= ios_occlusion_reset_end) {
      const uint32_t count = std::min<uint32_t>(64, kMaxOcclusionQueries - host_index);
      command_buffer.CmdVkResetQueryPool(occlusion_query_pool_, host_index, count);
      ios_occlusion_reset_submission = submission;
      ios_occlusion_reset_first = host_index;
      ios_occlusion_reset_end = host_index + count;
    }
  } else
#endif
  command_buffer.CmdVkResetQueryPool(occlusion_query_pool_, host_index, 1);
  command_buffer.CmdVkBeginQuery(occlusion_query_pool_, host_index, 0);
'''

COPY_ANCHOR = '''  command_buffer.CmdVkEndQuery(occlusion_query_pool_, host_index);
  command_buffer.CmdVkCopyQueryPoolResults(occlusion_query_pool_, host_index, 1,
                                           occlusion_query_readback_buffer_,
                                           sizeof(uint64_t) * host_index, sizeof(uint64_t),
                                           VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
'''
COPY_NEW = '''  command_buffer.CmdVkEndQuery(occlusion_query_pool_, host_index);
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: copied with the others when the submission ends
  // (tools/ios/patch_ios_occlusion_batch.py).
  if (IosBatchOcclusion()) {
    ios_occlusion_copies.push_back(host_index);
  } else
#endif
  command_buffer.CmdVkCopyQueryPoolResults(occlusion_query_pool_, host_index, 1,
                                           occlusion_query_readback_buffer_,
                                           sizeof(uint64_t) * host_index, sizeof(uint64_t),
                                           VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
'''

FLUSH_ANCHOR = '''    if (active_occlusion_query_.valid && occlusion_query_pool_ != VK_NULL_HANDLE) {
      deferred_command_buffer_.CmdVkEndQuery(occlusion_query_pool_,
                                             active_occlusion_query_.host_index);
      active_occlusion_query_ = {};
    }

    EndRenderPass();
'''
FLUSH_NEW = '''    if (active_occlusion_query_.valid && occlusion_query_pool_ != VK_NULL_HANDLE) {
      deferred_command_buffer_.CmdVkEndQuery(occlusion_query_pool_,
                                             active_occlusion_query_.host_index);
      active_occlusion_query_ = {};
    }

    EndRenderPass();
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: this submission's query results, one copy per run of
    // consecutive indices (tools/ios/patch_ios_occlusion_batch.py).
    if (!ios_occlusion_copies.empty()) {
      if (occlusion_query_pool_ != VK_NULL_HANDLE) {
        const std::vector<uint32_t>& c = ios_occlusion_copies;
        for (size_t i = 0; i < c.size();) {
          uint32_t count = 1;
          while (i + count < c.size() && c[i + count] == c[i] + count) {
            ++count;
          }
          deferred_command_buffer_.CmdVkCopyQueryPoolResults(
              occlusion_query_pool_, c[i], count, occlusion_query_readback_buffer_,
              sizeof(uint64_t) * c[i], sizeof(uint64_t),
              VK_QUERY_RESULT_64_BIT | VK_QUERY_RESULT_WAIT_BIT);
          i += count;
        }
      }
      ios_occlusion_copies.clear();
    }
#endif
'''

BLOCKS = [
    (F, "the cvar and the batch state", CVAR_ANCHOR, CVAR_NEW),
    (F, "one reset for the next 64 queries", RESET_ANCHOR, RESET_NEW),
    (F, "results copied at the end of the submission", COPY_ANCHOR, COPY_NEW),
    (F, "the copies, one per run of indices", FLUSH_ANCHOR, FLUSH_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_occlusion_batch", BLOCKS))
