#!/usr/bin/env python3
"""
A swapchain that stays suboptimal after being recreated is kept.

    python3 tools/ios/patch_ios_suboptimal_limit.py            apply
    python3 tools/ios/patch_ios_suboptimal_limit.py --status
    python3 tools/ios/patch_ios_suboptimal_limit.py --revert

Touches src/ui/presenter.cpp. Builds on patch_ios_suboptimal.py.

patch_ios_suboptimal.py recreates a suboptimal swapchain (at most twice a
second): after a screenshot iOS can leave it made for portrait bounds, and
recreating it fixes that. But with Display Zoom "More Space" on an iPad M1
the screen's scale is fractional (2388x1668 pixels over 1389x970 points,
"contents scale 1.7"): at full pixel density every swapchain is suboptimal
from its first present, recreating it changes nothing, and it was recreated
every 500 ms for good: a blank frame each time, the flicker a tester saw
above 1x (where the launcher now asks for full density). Now: at most two
recreations in a row without an optimal present in between; then the
swapchain stays (its picture is right, just scaled by the system), until a
present is optimal again.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

FILE = "src/ui/presenter.cpp"

A1 = '''    case PaintResult::kPresented:
      surface_paint_connection_was_optimal_at_successful_paint_ = true;
      break;
'''
N1 = '''    case PaintResult::kPresented:
      surface_paint_connection_was_optimal_at_successful_paint_ = true;
#if REX_PLATFORM_IOS
      ios_futile_recreates = 0;  // LOCAL PATCH - iOS (patch_ios_suboptimal_limit.py)
#endif
      break;
'''
A2 = '''        static std::chrono::steady_clock::time_point ios_last_recreate{};
        const auto now = std::chrono::steady_clock::now();
        if (now - ios_last_recreate > std::chrono::milliseconds(500)) {
          ios_last_recreate = now;
          REXLOG_INFO("Presenter: suboptimal swapchain (the layer changed size): recreating it");
          surface_paint_connection_state_ = SurfacePaintConnectionState::kConnectedOutdated;
        }
'''
N2 = '''        static std::chrono::steady_clock::time_point ios_last_recreate{};
        const auto now = std::chrono::steady_clock::now();
        // LOCAL PATCH - iOS: twice at most without an optimal present
        // (patch_ios_suboptimal_limit.py): a fractional screen scale keeps it
        // suboptimal whatever is done, and each recreation is a blank frame.
        if (ios_futile_recreates < 2 && now - ios_last_recreate > std::chrono::milliseconds(500)) {
          ios_last_recreate = now;
          ++ios_futile_recreates;
          REXLOG_INFO("Presenter: suboptimal swapchain (the layer changed size): recreating it");
          surface_paint_connection_state_ = SurfacePaintConnectionState::kConnectedOutdated;
        } else if (ios_futile_recreates == 2) {
          ++ios_futile_recreates;
          REXLOG_INFO("Presenter: still suboptimal after recreating it twice (fractional screen scale?): "
                      "keeping this swapchain");
        }
'''
A3 = '''Presenter::PaintResult Presenter::PaintAndPresent(bool execute_ui_drawers) {
'''
N3 = '''#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: suboptimal recreations since the last optimal present
// (patch_ios_suboptimal_limit.py).
static int ios_futile_recreates = 0;
#endif

Presenter::PaintResult Presenter::PaintAndPresent(bool execute_ui_drawers) {
'''

BLOCKS = [
    (FILE, "the counter", A3, N3),
    (FILE, "reset on an optimal present", A1, N1),
    (FILE, "at most two recreations", A2, N2),
]

if __name__ == "__main__":
    sys.exit(run("ios_suboptimal_limit", BLOCKS))
