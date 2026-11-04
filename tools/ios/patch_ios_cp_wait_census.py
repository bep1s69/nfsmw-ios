#!/usr/bin/env python3
"""
What the command processor's WAIT_REG_MEM waits for, every 10 s
("[cp-wait]", cvar ios_cp_wait_census, default false; logging only).

    python3 tools/ios/patch_ios_cp_wait_census.py            apply
    python3 tools/ios/patch_ios_cp_wait_census.py --status
    python3 tools/ios/patch_ios_cp_wait_census.py --revert

Touches src/graphics/command_processor.cpp.


WHY
===

November 4 (docs/TECHNICAL.md), dev50 iPad System Trace: GPU Commands made
~790 os_sync waits a second in ExecutePacketType3_WAIT_REG_MEM, median
1.13 ms (the wait's own 1 ms lap, woken early only by the vblank). Which
register or memory word, compare function and reference it polls decides
whether an exact wake is possible.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/graphics/command_processor.cpp"

CVAR_ANCHOR = '''REXCVAR_DEFINE_INT32(ios_cp_idle_spins, 4, "GPU",'''
CVAR_NEW = '''// LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_census.py).
REXCVAR_DEFINE_BOOL(ios_cp_wait_census, false, "GPU",
                    "iOS: log what WAIT_REG_MEM polls every 10 s ([cp-wait], logging only)");
''' + CVAR_ANCHOR

LAP_ANCHOR = '''    if (!matched) {
      // Wait.
      if (wait >= 0x100) {
        PrepareForWait();'''
LAP_NEW = '''    // LOCAL PATCH - iOS (tools/ios/patch_ios_cp_wait_census.py): count each
    // unmatched lap by what it polls; only the CP thread runs this.
    if (!matched && REXCVAR_GET(ios_cp_wait_census)) {
      struct IosWaitKey {
        uint32_t addr, info, ref, mask, wait;
        bool operator<(const IosWaitKey& o) const {
          return std::tie(addr, info, ref, mask, wait) < std::tie(o.addr, o.info, o.ref, o.mask, o.wait);
        }
      };
      static std::map<IosWaitKey, std::pair<uint64_t, uint32_t>> ios_laps;  // laps, last value
      static auto ios_since = std::chrono::steady_clock::now();
      auto& e = ios_laps[IosWaitKey{poll_reg_addr, wait_info, ref, mask, wait}];
      ++e.first;
      e.second = value;
      const auto ios_now = std::chrono::steady_clock::now();
      if (ios_now - ios_since >= std::chrono::seconds(10)) {
        std::vector<std::pair<uint64_t, IosWaitKey>> top;
        uint64_t total = 0;
        for (const auto& [k, v] : ios_laps) {
          top.push_back({v.first, k});
          total += v.first;
        }
        std::sort(top.begin(), top.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
        std::string most;
        for (size_t i = 0; i < top.size() && i < 4; ++i) {
          const IosWaitKey& k = top[i].second;
          most += fmt::format(" | {} laps: {} {:08X} func {} ref {:08X} mask {:08X} wait {:X} last {:08X}",
                              top[i].first, (k.info & 0x10) ? "mem" : "reg", k.addr, k.info & 7,
                              k.ref, k.mask, k.wait, ios_laps[k].second);
        }
        REXGPU_INFO("[cp-wait] 10 s: {} unmatched laps on {} kinds{}", total, ios_laps.size(), most);
        ios_laps.clear();
        ios_since = ios_now;
      }
    }
''' + LAP_ANCHOR

INC_ANCHOR = "#include <map>  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py)\n"
INC_NEW = INC_ANCHOR + "#include <tuple>  // LOCAL PATCH - iOS (patch_ios_cp_wait_census.py)\n"

BLOCKS = [
    (FILE, "<tuple>", INC_ANCHOR, INC_NEW),
    (FILE, "the ios_cp_wait_census cvar", CVAR_ANCHOR, CVAR_NEW),
    (FILE, "the [cp-wait] census", LAP_ANCHOR, LAP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_cp_wait_census", BLOCKS))
