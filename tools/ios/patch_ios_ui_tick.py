#!/usr/bin/env python3
"""
Pace the UI thread's repaints on iOS, as the SDK already does on Windows.

    python3 tools/ios/patch_ios_ui_tick.py            apply
    python3 tools/ios/patch_ios_ui_tick.py --status
    python3 tools/ios/patch_ios_ui_tick.py --revert

Touches src/ui/presenter.cpp.


WHAT WAS MEASURED
=================

iPad Pro M4, iPadOS 27.0.1, a menu and a quick race, with
tools/ios/patch_ios_timing.py:

  - the command processor (CP) never paints: the UI thread does all of it
    (the SDK always has an ImGui drawer registered, so the paint mode is
    kUIThreadOnRequest), and acquire/present cost ~0.01 ms each;
  - the UI thread repainted 120 times a second in the menus, 8.3 ms each:
    busy all the time, mostly redrawing the SAME guest frame. In the race,
    50-55 paints a second at 17-20 ms each;
  - the CP's swap ("refresh": gamma pass + submit) grew with it: 6-8 ms in the
    menus, 15 ms in the race, out of 35-40 ms frames.

MoltenVK exposes ONE queue ("presentando en la cola 0 de la familia 0":
parche_cola_presentar has no second queue to use), and it encodes the Metal
work at vkQueueSubmit, under the queue lock. A UI thread that submits a
full-screen paint (2752x2064 on that iPad) over and over takes that lock and
GPU time from the game.


WHY IT REPAINTS SO MUCH
=======================

Presenter::WaitForUITickFromUIThread() is what limits the UI's repaints, and
it is implemented ONLY for Windows (DXGI's vblank). Everywhere else it returns
at once: the UI thread repaints as fast as it can. On Windows, a new guest
frame or a UI change cuts the wait short through ForceUIThreadPaintTick(),
which elsewhere does nothing.

This gives iOS the same contract with a clock instead of DXGI:

  - a repaint that only redraws what is already there waits until 1/N s after
    the previous paint (cvar ios_ui_repaint_hz, default 30);
  - ForceUIThreadPaintTick() (a new guest frame, a change to the UI) ends the
    wait at once, so the game's own frames are presented without delay.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

P = "src/ui/presenter.cpp"

INCLUDE_ANCHOR = '''#include <utility>

#include <rex/assert.h>
'''
INCLUDE_NEW = '''#include <utility>
// LOCAL PATCH - iOS: the UI tick (tools/ios/patch_ios_ui_tick.py).
#include <chrono>
#include <condition_variable>
#include <mutex>

#include <rex/assert.h>
'''

STATE_ANCHOR = '''void Presenter::WaitForUITickFromUIThread() {
#if REX_PLATFORM_WIN32
'''
STATE_NEW = '''// LOCAL PATCH - iOS: the UI tick, with a clock instead of DXGI's vblank
// (tools/ios/patch_ios_ui_tick.py). File-scope state: one presenter per app.
#if REX_PLATFORM_IOS
}  // namespace ui
}  // namespace rex
REXCVAR_DEFINE_INT32(ios_ui_repaint_hz, 30, "UI",
                     "iOS: how many times a second the UI thread may repaint without a new "
                     "game frame. A new game frame is always presented at once");
namespace rex {
namespace ui {
namespace ios_ui_tick {
std::mutex mutex;
std::condition_variable signal;
bool forced = false;
std::chrono::steady_clock::time_point last_paint{};
}  // namespace ios_ui_tick
#endif

void Presenter::WaitForUITickFromUIThread() {
#if REX_PLATFORM_IOS
  {
    const int32_t hz = std::clamp<int32_t>(REXCVAR_GET(ios_ui_repaint_hz), 1, 240);
    const auto deadline =
        ios_ui_tick::last_paint +
        std::chrono::duration_cast<std::chrono::steady_clock::duration>(
            std::chrono::duration<double>(1.0 / double(hz)));
    std::unique_lock<std::mutex> lock(ios_ui_tick::mutex);
    ios_ui_tick::signal.wait_until(lock, deadline, [] { return ios_ui_tick::forced; });
    ios_ui_tick::forced = false;
    ios_ui_tick::last_paint = std::chrono::steady_clock::now();
  }
#endif
#if REX_PLATFORM_WIN32
'''

FORCE_ANCHOR = '''#endif  // XE_PLATFORM
}

void Presenter::ForceUIThreadPaintTick() {
#if REX_PLATFORM_WIN32
  std::scoped_lock<std::mutex> dxgi_ui_tick_lock(dxgi_ui_tick_mutex_);
  dxgi_ui_tick_force_requested_ = true;
#endif  // XE_PLATFORM
}
'''
FORCE_NEW = '''#endif  // XE_PLATFORM
}

void Presenter::ForceUIThreadPaintTick() {
#if REX_PLATFORM_WIN32
  std::scoped_lock<std::mutex> dxgi_ui_tick_lock(dxgi_ui_tick_mutex_);
  dxgi_ui_tick_force_requested_ = true;
#elif REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: a new guest frame or a UI change ends the wait at once.
  {
    std::scoped_lock<std::mutex> lock(ios_ui_tick::mutex);
    ios_ui_tick::forced = true;
  }
  ios_ui_tick::signal.notify_all();
#endif  // XE_PLATFORM
}
'''

BLOCKS = [
    (P, "include chrono, condition_variable, mutex", INCLUDE_ANCHOR, INCLUDE_NEW),
    (P, "the iOS UI tick (ios_ui_repaint_hz)", STATE_ANCHOR, STATE_NEW),
    (P, "a new frame ends the wait", FORCE_ANCHOR, FORCE_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_ui_tick", BLOCKS))
