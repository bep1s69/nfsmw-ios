#!/usr/bin/env python3
"""
On iOS a "suboptimal" present always gets the swapchain recreated (at most
twice a second), even if the swapchain was suboptimal from its first present.

    python3 tools/ios/patch_ios_suboptimal.py            apply
    python3 tools/ios/patch_ios_suboptimal.py --status
    python3 tools/ios/patch_ios_suboptimal.py --revert

Touches src/ui/presenter.cpp.


WHY
===

Taking a screenshot (or the like) the game went black for good, with sound and
input still working. The log: at the screenshot the swapchain was recreated
PORTRAIT (1320x2868 on a landscape 2868x1320 iPhone): for a moment iOS gives
the layer portrait bounds, and the presenter rebuilt the swapchain from them.
Back in landscape, every present is VK_SUBOPTIMAL_KHR (MoltenVK: the drawable
no longer matches the layer), but Presenter only treats suboptimal as outdated
"if previously optimal": a swapchain suboptimal from its first present (as
here, the layer was landscape again before it) is never recreated, and its
image is not what the screen shows.

On iOS a suboptimal present marks the connection outdated (so the swapchain is
recreated from the layer's current size), unless that was done in the last
500 ms: if the layer stayed suboptimal for some other reason, it does not
recreate the swapchain every frame.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/ui/presenter.cpp"

ANCHOR = '''    case PaintResult::kPresentedSuboptimal:
      // Make outdated if previously optimal, now suboptimal, but don't cause
      // the connection to become outdated if it has been suboptimal from the
      // very beginning.
      if (surface_paint_connection_was_optimal_at_successful_paint_) {
        surface_paint_connection_state_ = SurfacePaintConnectionState::kConnectedOutdated;
      }
      break;
'''
NEW = '''    case PaintResult::kPresentedSuboptimal:
      // Make outdated if previously optimal, now suboptimal, but don't cause
      // the connection to become outdated if it has been suboptimal from the
      // very beginning.
      if (surface_paint_connection_was_optimal_at_successful_paint_) {
        surface_paint_connection_state_ = SurfacePaintConnectionState::kConnectedOutdated;
      }
#if REX_PLATFORM_IOS
      // LOCAL PATCH - iOS: also when suboptimal from the start (a swapchain
      // made while iOS gave the layer portrait bounds, for a screenshot), at
      // most twice a second (tools/ios/patch_ios_suboptimal.py).
      else {
        static std::chrono::steady_clock::time_point ios_last_recreate{};
        const auto now = std::chrono::steady_clock::now();
        if (now - ios_last_recreate > std::chrono::milliseconds(500)) {
          ios_last_recreate = now;
          REXLOG_INFO("Presenter: suboptimal swapchain (the layer changed size): recreating it");
          surface_paint_connection_state_ = SurfacePaintConnectionState::kConnectedOutdated;
        }
      }
#endif
      break;
'''

BLOCKS = [
    (F, "recreate a swapchain suboptimal from the start", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_suboptimal", BLOCKS))
