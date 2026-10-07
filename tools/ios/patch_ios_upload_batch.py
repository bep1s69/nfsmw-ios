#!/usr/bin/env python3
"""
Uploads hoisted before the same render pass share one block: one Metal blit
encoder and one barrier pair per pass, not one per upload; and the block is
put in place once per pass, not once per upload.

    python3 tools/ios/patch_ios_upload_batch.py            apply
    python3 tools/ios/patch_ios_upload_batch.py --status
    python3 tools/ios/patch_ios_upload_batch.py --revert

Touches src/graphics/vulkan/shared_memory.cpp, src/graphics/vulkan/
deferred_command_buffer.cpp and include/rex/graphics/vulkan/
deferred_command_buffer.h. Builds on tools/parche_subidas.py (Android), which
prepare_sdk.py applies first.


WHAT A GPU FRAME CAPTURE SHOWED
===============================

Two Metal frame captures of a race on an iPad Pro M4 (34 and 40 fps), counted
by the labels MoltenVK gives its encoders: 318-522 blit encoders of buffer
copies a frame, growing with the frame time. They are the uploads of guest
memory to the shared memory buffer (VulkanSharedMemory::UploadRanges).
parche_subidas.py moves each one to before the start of the open render pass,
so it does not cut the pass, but each with its own barrier pair, and MoltenVK
ends the current Metal encoder at a pipeline barrier outside a render pass:
every upload was its own blit encoder behind its own wait for all the GPU
work before it.


WHAT A CPU PROFILE SHOWED NEXT
==============================

The first version of this patch joined the uploads into one block per pass
(the copy encoders went from 522 to 79 in the same race), but still moved
each upload into place as it came, with std::rotate over everything recorded
since the start of the pass: 4.1-4.7 % of the GPU thread in a police chase
(Instruments' Time Profiler).


THE CHANGE
==========

While a pass is open, its hoisted uploads are kept aside in the deferred
command buffer (opening barrier, then the copies), not in the stream. They go
in, at the start of their pass, with their closing barrier, once:

  - when an upload for another pass comes along (the open pass's recorded
    start then moves by what was inserted, as parche_subidas tracks it); or
  - when the stream is replayed (DeferredCommandBuffer::Execute).

All of a pass's commands come after its start in the stream, and nothing else
moves the stream, so the position stays valid until then. The barriers cover
the whole buffer, since a block holds several uploads. Which uploads may be
hoisted (none the pass has read yet) is parche_subidas' own rule, unchanged.

Cvar ios_batch_uploads, default on; false gives back parche_subidas' exact
behaviour.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

DCB_H = "include/rex/graphics/vulkan/deferred_command_buffer.h"
DCB_CPP = "src/graphics/vulkan/deferred_command_buffer.cpp"
CPP = "src/graphics/vulkan/shared_memory.cpp"

H_ANCHOR = '''  size_t NfsmwTamano() const { return command_stream_.size(); }
'''
H_NEW = '''  size_t NfsmwTamano() const { return command_stream_.size(); }
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the hoisted uploads of the open render pass, kept aside
  // and put at the start of their pass once (tools/ios/patch_ios_upload_batch.py).
  bool IosHoistPending() const { return !ios_hoist_.empty(); }
  bool IosHoistOpenFor(size_t pass_start) const {
    return !ios_hoist_.empty() && ios_hoist_at_ == pass_start;
  }
  void IosHoistBegin(size_t pass_start, const VkBufferMemoryBarrier& closing) {
    ios_hoist_at_ = pass_start;
    ios_hoist_closing_ = closing;
  }
  // What was recorded from `from` to the end goes aside.
  void IosHoistTake(size_t from) {
    ios_hoist_.insert(ios_hoist_.end(), command_stream_.begin() + from, command_stream_.end());
    command_stream_.resize(from);
  }
  // The block, with its closing barrier, at the start of its pass. Returns how
  // many elements went in before that point (0 if there was nothing).
  size_t IosHoistFlush() {
    if (ios_hoist_.empty()) {
      return 0;
    }
    const size_t from = command_stream_.size();
    CmdVkPipelineBarrier(VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0,
                         nullptr, 1, &ios_hoist_closing_, 0, nullptr);
    IosHoistTake(from);
    command_stream_.insert(command_stream_.begin() + ios_hoist_at_, ios_hoist_.begin(),
                           ios_hoist_.end());
    const size_t inserted = ios_hoist_.size();
    ios_hoist_.clear();
    ios_hoist_at_ = SIZE_MAX;
    return inserted;
  }
#endif
'''

H_MEMBER_ANCHOR = '''  std::vector<uintmax_t> command_stream_;
'''
H_MEMBER_NEW = '''  std::vector<uintmax_t> command_stream_;
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS (tools/ios/patch_ios_upload_batch.py).
  std::vector<uintmax_t> ios_hoist_;
  size_t ios_hoist_at_ = SIZE_MAX;
  VkBufferMemoryBarrier ios_hoist_closing_ = {};
#endif
'''

EXEC_ANCHOR = '''void DeferredCommandBuffer::Execute(VkCommandBuffer command_buffer) {
'''
EXEC_NEW = '''void DeferredCommandBuffer::Execute(VkCommandBuffer command_buffer) {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the last pass's hoisted uploads, before replaying
  // (tools/ios/patch_ios_upload_batch.py).
  IosHoistFlush();
#endif
'''

RESET_ANCHOR = '''void DeferredCommandBuffer::Reset() {
'''
RESET_NEW = '''void DeferredCommandBuffer::Reset() {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: a stream thrown away takes its hoisted uploads with it
  // (their position is in that stream; tools/ios/patch_ios_upload_batch.py).
  ios_hoist_.clear();
  ios_hoist_at_ = SIZE_MAX;
#endif
'''

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(vulkan_adelantar_subidas, true, "GPU/Vulkan",
'''
CVAR_NEW = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS (tools/ios/patch_ios_upload_batch.py).
REXCVAR_DEFINE_BOOL(ios_batch_uploads, true, "GPU/Vulkan",
                    "iOS: uploads hoisted before the same render pass share one barrier pair "
                    "(one Metal blit encoder per pass instead of one per upload)");
#endif
REXCVAR_DEFINE_BOOL(vulkan_adelantar_subidas, true, "GPU/Vulkan",
'''

# The previous pass's block goes in before anything is computed from the
# stream's size or the pass start.
START_ANCHOR = '''  DeferredCommandBuffer& command_buffer = command_processor_.deferred_command_buffer();
  const uint32_t nfsmw_pagina = upload_page_ranges.front().first;
'''
START_NEW = '''  DeferredCommandBuffer& command_buffer = command_processor_.deferred_command_buffer();
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: another pass's hoisted uploads go in first; the open
  // pass (after them in the stream) moves by what was inserted.
  if (REXCVAR_GET(ios_batch_uploads) && command_buffer.IosHoistPending() &&
      !command_buffer.IosHoistOpenFor(command_processor_.NfsmwInicioPase())) {
    const size_t ios_inserted = command_buffer.IosHoistFlush();
    if (command_processor_.NfsmwInicioPase() != SIZE_MAX) {
      command_processor_.NfsmwPaseDesplazado(ios_inserted);
    }
  }
#endif
  const uint32_t nfsmw_pagina = upload_page_ranges.front().first;
'''

PRE_ANCHOR = '''  if (nfsmw_adelantar) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    command_buffer.CmdVkPipelineBarrier(VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                                        VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 1,
                                        &nfsmw_barrera, 0, nullptr);
  } else {
'''
PRE_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the opening barrier only for the pass's first hoisted
  // upload; the block's barriers cover the whole buffer.
  const bool ios_batch = nfsmw_adelantar && REXCVAR_GET(ios_batch_uploads);
  const bool ios_join = ios_batch && command_buffer.IosHoistOpenFor(nfsmw_inicio_pase);
  if (ios_batch) {
    nfsmw_barrera.offset = 0;
    nfsmw_barrera.size = VK_WHOLE_SIZE;
  }
#else
  const bool ios_join = false;
#endif
  if (nfsmw_adelantar) {
    if (!ios_join) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    command_buffer.CmdVkPipelineBarrier(VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
                                        VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 1,
                                        &nfsmw_barrera, 0, nullptr);
    }
  } else {
'''

POST_ANCHOR = '''  if (nfsmw_adelantar) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
'''
POST_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: aside, until the block goes in at the pass start.
  if (ios_batch) {
    if (!ios_join) {
      nfsmw_barrera.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
      nfsmw_barrera.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
      command_buffer.IosHoistBegin(nfsmw_inicio_pase, nfsmw_barrera);
    }
    command_buffer.IosHoistTake(nfsmw_cola);
    ++nfsmw_adelantadas;
  } else
#endif
  if (nfsmw_adelantar) {
    nfsmw_barrera.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    nfsmw_barrera.dstAccessMask = VK_ACCESS_MEMORY_READ_BIT | VK_ACCESS_MEMORY_WRITE_BIT;
'''

BLOCKS = [
    (DCB_H, "the hoisted-upload block helpers", H_ANCHOR, H_NEW),
    (DCB_H, "the hoisted-upload block storage", H_MEMBER_ANCHOR, H_MEMBER_NEW),
    (DCB_CPP, "flush the block before replaying", EXEC_ANCHOR, EXEC_NEW),
    (DCB_CPP, "a reset drops the block", RESET_ANCHOR, RESET_NEW),
    (CPP, "the ios_batch_uploads cvar", CVAR_ANCHOR, CVAR_NEW),
    (CPP, "another pass's block goes in first", START_ANCHOR, START_NEW),
    (CPP, "opening barrier only once per pass", PRE_ANCHOR, PRE_NEW),
    (CPP, "the copies go aside", POST_ANCHOR, POST_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_upload_batch", BLOCKS))
