#!/usr/bin/env python3
"""
When a surface is attached again, the presenter forgets any paint request
made while it had none.

    python3 tools/ios/patch_ios_surface_reattach.py            apply
    python3 tools/ios/patch_ios_surface_reattach.py --status
    python3 tools/ios/patch_ios_surface_reattach.py --revert

Touches src/ui/presenter.cpp.


WHY
===

The app detaches the window's surface while it is paused (ios/src/lifecycle.mm,
another app opened) and attaches a new one when it comes back. After coming
back the game ran at 57 fps, the swapchain was created, and the UI thread
painted 0 times a second: black screen, sound playing.

Presenter::RequestPaintOrConnectionRecoveryViaWindow asks the window for a
paint only if ui_thread_paint_requested_ was false, and sets it; the flag is
cleared in PaintFromUIThread. A request made just before the surface went
away was delivered to Window::OnPaint, which skips the presenter when there
is no surface: the flag stayed set, and every later request (new guest
frames, the reattach itself) took it for one already queued. No paint was
ever asked for again.

On attaching a surface the flag is cleared before the connection's own paint
request.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

F = "src/ui/presenter.cpp"

ANCHOR = '''    assert_true(surface_paint_connection_state_ ==
                SurfacePaintConnectionState::kUnconnectedRetryAtStateChange);
    bool request_repaint;
    UpdateSurfacePaintConnectionFromUIThread(&request_repaint, true);
'''
NEW = '''    assert_true(surface_paint_connection_state_ ==
                SurfacePaintConnectionState::kUnconnectedRetryAtStateChange);
    // LOCAL PATCH - iOS: a paint request made while there was no surface was
    // dropped by Window::OnPaint without clearing this; left set, no paint
    // would ever be requested again (tools/ios/patch_ios_surface_reattach.py).
    ui_thread_paint_requested_.store(false, std::memory_order_relaxed);
    bool request_repaint;
    UpdateSurfacePaintConnectionFromUIThread(&request_repaint, true);
'''

BLOCKS = [
    (F, "forget paint requests made without a surface", ANCHOR, NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_surface_reattach", BLOCKS))
