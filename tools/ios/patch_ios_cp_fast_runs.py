#!/usr/bin/env python3
"""
Direct draw path, phase 1: runs of register and filler packets in one pass.

    python3 tools/ios/patch_ios_cp_fast_runs.py            apply
    python3 tools/ios/patch_ios_cp_fast_runs.py --status
    python3 tools/ios/patch_ios_cp_fast_runs.py --revert

Cvar ios_cp_fast_runs (default true since October 22, after a visual check). The October 22 census measured ~17,000
type-0 register packets and ~17,000 type-2 one-word fillers per race frame
(~14 per draw). Each went through the whole ExecutePacket dispatch. With the
cvar on, a type-0 or type-2 packet is followed by the next ones of those two
types in a tight loop (up to 64), with the same handlers: type 0 through
ExecutePacketType0 (bulk ranges and side effects unchanged), type 2 skipped as
before. Any other packet (or a zero / CDCDCDCD word) is left for the normal
path. Not with medir_paquetes (its per-packet timing). The primary buffer's read
pointer writeback can trail by up to one run. See docs/TECHNICAL.md, Oct 22.
"""
import sys
from patch_engine import run

CP = "src/graphics/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_BOOL(ios_packet_census, false, "GPU",'''
CVAR_NEW = '''REXCVAR_DEFINE_BOOL(ios_cp_fast_runs, true, "GPU",
                    "Experiment: runs of type-0/type-2 packets in one pass of ExecutePacket");
''' + CVAR_ANCHOR

RUN_ANCHOR = '''    if (packet_type == 0 || packet_type == 3) nfsmw_cp_census_words[key] += ((packet >> 16) & 0x3FFF) + 1;
  }
'''
RUN_NEW = RUN_ANCHOR + '''  if ((packet_type == 0 || packet_type == 2) && REXCVAR_GET(ios_cp_fast_runs) &&
      !REXCVAR_GET(medir_paquetes)) {  // LOCAL PATCH - tools/ios/patch_ios_cp_fast_runs.py
    const bool census = REXCVAR_GET(ios_packet_census);
    uint32_t run_packet = packet;
    for (int run = 0;; ++run) {
      if ((run_packet >> 30) == 0 && !ExecutePacketType0(reader, run_packet)) return false;
      if (run >= 63 || reader->read_count() < sizeof(uint32_t)) return true;
      const size_t at = reader->read_offset();
      const uint32_t next = reader->ReadAndSwap<uint32_t>();
      const uint32_t next_type = next >> 30;
      if (next == 0 || next == 0xCDCDCDCD || (next_type != 0 && next_type != 2)) {
        reader->set_read_offset(at);
        return true;
      }
      if (census) {
        const int key = 128 + int(next_type != 0);
        ++nfsmw_cp_census_packets[key];
        if (next_type == 0) nfsmw_cp_census_words[key] += ((next >> 16) & 0x3FFF) + 1;
      }
      run_packet = next;
    }
  }
'''

BLOCKS = [
    (CP, "the ios_cp_fast_runs cvar", CVAR_ANCHOR, CVAR_NEW),
    (CP, "type-0/type-2 runs in one pass", RUN_ANCHOR, RUN_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cp_fast_runs", BLOCKS))
