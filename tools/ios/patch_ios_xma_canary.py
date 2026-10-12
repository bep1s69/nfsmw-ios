#!/usr/bin/env python3
"""
Xenia Canary's later fixes to the XMA decoder's Work(), which our copy lacks.

    python3 tools/ios/patch_ios_xma_canary.py            apply
    python3 tools/ios/patch_ios_xma_canary.py --status
    python3 tools/ios/patch_ios_xma_canary.py --revert

Touches src/audio/xma_context.cpp.

Crackle and "pssch" noise in menus (scrolling) and races, with the output
path measured clean (no gaps, no drops) and clipping ruled out. The SDK's
decoder is Xenia Canary's newer one, from before these changes:

  - NFS: Carbon and NFS: Most Wanted use the output write offset as a stall
    detector: starved of input, it is set equal to the read offset (and the
    output marked not valid); otherwise the game reads a stale stretch again;
  - a consume-only context marks its output not valid once drained;
  - a pass that makes no progress (read offset unchanged, no frame) stops;
  - "output full" is signalled with Canary's condition.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/audio/xma_context.cpp"

BLOCKS = [
    (FILE, 'consume-only output invalidated',
     '    data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;\n    StoreContextMerged(data, initial_data, context_ptr);\n',
     '    data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;\n    // LOCAL PATCH - iOS (Xenia Canary): drained, the output is no longer valid.\n    if (output_rb.empty()) {\n      data.output_buffer_valid = false;\n    }\n    StoreContextMerged(data, initial_data, context_ptr);\n'),
    (FILE, 'progress check (offsets)',
     '  while (remaining_subframe_blocks_in_output_buffer_ >= minimum_subframe_decode_count) {\n    Decode(&data);\n',
     '  while (remaining_subframe_blocks_in_output_buffer_ >= minimum_subframe_decode_count) {\n    const uint32_t pre_decode_offset = data.input_buffer_read_offset;\n    const uint8_t pre_remaining_subframes = current_frame_remaining_subframes_;\n\n    Decode(&data);\n'),
    (FILE, 'stall check',
     '        current_frame_remaining_subframes_ == 0) {\n      break;\n    }\n  }\n',
     '        current_frame_remaining_subframes_ == 0) {\n      break;\n    }\n\n    // LOCAL PATCH - iOS (Xenia Canary): Decode did not move the read offset\n    // and produced no new frame (and none was pending): no progress possible\n    // until the next buffer; stop instead of spinning.\n    if (pre_remaining_subframes == 0 && data.input_buffer_read_offset == pre_decode_offset &&\n        current_frame_remaining_subframes_ == 0) {\n      break;\n    }\n  }\n'),
    (FILE, 'NFS write offset when starved',
     '\n  data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;\n\n',
     '\n  // LOCAL PATCH - iOS (Xenia Canary, tools/ios/patch_ios_xma_canary.py).\n  if (initial_data.IsAnyInputBufferValid()) {\n    data.output_buffer_write_offset = output_rb.write_offset() / kOutputBytesPerBlock;\n  } else {\n    // NFS: Carbon and NFS: Most Wanted use write_offset as a stall detector:\n    // starved of input, make it equal to the read offset (and the output not\n    // valid), or the game reads a stale stretch of the buffer again.\n    if (data.output_buffer_write_offset != data.output_buffer_read_offset) {\n      data.output_buffer_write_offset = data.output_buffer_read_offset;\n      data.output_buffer_valid = 0;\n    }\n  }\n\n'),
    (FILE, 'output full signalled',
     '\n  if (output_rb.empty()) {\n    data.output_buffer_valid = 0;\n',
     '\n  // The output ring buffer is full: tell the game (output not valid).\n  if (remaining_subframe_blocks_in_output_buffer_ == 0 && output_rb.empty()) {\n    data.output_buffer_valid = 0;\n'),
]

if __name__ == "__main__":
    sys.exit(run("ios_xma_canary", BLOCKS))
