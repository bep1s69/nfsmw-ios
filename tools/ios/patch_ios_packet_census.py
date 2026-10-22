#!/usr/bin/env python3
"""
Direct draw path, phase 0: count the PM4 packets and words the CP decodes.

    python3 tools/ios/patch_ios_packet_census.py            apply
    python3 tools/ios/patch_ios_packet_census.py --status
    python3 tools/ios/patch_ios_packet_census.py --revert

Cvar ios_packet_census (default false, diagnostic). With it on, ExecutePacket
counts packets and payload words by key (type-3 opcode 0-127, 128 type 0, 129
type 1/2) into nfsmw_cp_census_packets / nfsmw_cp_census_words (exported: the native
renderer finds them with dlsym, the GPU plugin being loaded at run time) and
prints and resets them with its periodic stats (ios/src/native_renderer.mm).
Counters are plain integers written by the CP thread and read by the render
queue: approximate, for sizing only. See docs/TECHNICAL.md, October 22.
"""
import sys
from patch_engine import run

CP = "src/graphics/command_processor.cpp"

DECL_ANCHOR = '''extern "C" {
uint64_t nfsmw_cp_paquete_ns[130] = {};
'''
DECL_NEW = '''REXCVAR_DEFINE_BOOL(ios_packet_census, false, "GPU",
                    "Diagnostics: count PM4 packets and words per type/opcode (native stats log)");
extern "C" {
__attribute__((visibility("default"))) uint64_t nfsmw_cp_census_packets[130] = {};
__attribute__((visibility("default"))) uint64_t nfsmw_cp_census_words[130] = {};
uint64_t nfsmw_cp_paquete_ns[130] = {};
'''

COUNT_ANCHOR = '''  if (packet == 0xCDCDCDCD) {
    REXGPU_WARN("GPU packet is CDCDCDCD - probably read uninitialized memory!");
  }
'''
COUNT_NEW = COUNT_ANCHOR + '''  if (REXCVAR_GET(ios_packet_census)) {  // LOCAL PATCH - tools/ios/patch_ios_packet_census.py
    const int key = packet_type == 3 ? int((packet >> 8) & 0x7F) : 128 + int(packet_type != 0);
    ++nfsmw_cp_census_packets[key];
    if (packet_type == 0 || packet_type == 3) nfsmw_cp_census_words[key] += ((packet >> 16) & 0x3FFF) + 1;
  }
'''

BLOCKS = [
    (CP, "census counters and cvar", DECL_ANCHOR, DECL_NEW),
    (CP, "count every packet", COUNT_ANCHOR, COUNT_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_packet_census", BLOCKS))
