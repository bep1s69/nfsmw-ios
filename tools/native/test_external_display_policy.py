#!/usr/bin/env python3
"""Check the external display decisions (ios/src/external_display_policy.h) on the Mac.

Plain C++, no UIKit, no display: the picture's pixels on 1080p, 4K and other
displays, the shape the game starts in, the letterbox, and the Router's
timeline through unplugs, app switches and display mode changes. Also checks
that the iOS sources still route through these functions (the wiring itself
is exercised by tools/ios/external_display_sim/ in the iOS Simulator).

    python3 tools/native/test_external_display_policy.py
"""
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HARNESS = r'''
#include "@HEADER@"
#include <cassert>
#include <cstdio>
#include <vector>
using namespace nfsmw::external_display;

static void Expect(bool ok, const char* what) {
  if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); std::abort(); }
}
static bool Is(Pixels p, uint32_t w, uint32_t h) { return p.w == w && p.h == h; }

static void PicturePixels() {
  Expect(MaxWidthFor("") == 1920 && MaxWidthFor("1080p") == 1920 && MaxWidthFor("bogus") == 1920, "default cap 1920");
  Expect(MaxWidthFor("1440p") == 2560 && MaxWidthFor("display") == 0 && MaxWidthFor("720p") == 1280, "other caps");
  Expect(Is(CappedPixels(1920, 1080, 1920), 1920, 1080), "1080p display: its own pixels");
  Expect(Is(CappedPixels(3840, 2160, 1920), 1920, 1080), "4K display: 1080p by default");
  Expect(Is(CappedPixels(3840, 2160, 2560), 2560, 1440), "4K display at 1440p");
  Expect(Is(CappedPixels(3840, 2160, 0), 3840, 2160), "4K display, the display's own");
  Expect(Is(CappedPixels(2160, 3840, 1920), 1920, 1080), "portrait numbers: landscape");
  Expect(Is(CappedPixels(1280, 720, 1920), 1280, 720), "720p display: never scaled up");
  Expect(Is(CappedPixels(3440, 1440, 1920), 1920, 804), "21:9 monitor: its shape, even height");
  Expect(Is(CappedPixels(2560, 1600, 1920), 1920, 1200), "16:10 monitor");
  Expect(Is(CappedPixels(1024, 768, 1920), 1024, 768), "4:3 projector");
  Expect(Is(CappedPixels(0, 0, 1920), 0, 0) && Is(CappedPixels(1920, 0, 1920), 0, 0), "no size: none");
  std::puts("PASS picture pixels: 1080p cap by default, 4K, 1440p, other shapes, portrait numbers");
}

static void Shapes() {
  Expect(ShapeFor(1920, 1080) == Shape::k16x9, "16:9 TV: 16:9");
  Expect(ShapeFor(3840, 2160) == Shape::k16x9, "4K TV: 16:9");
  Expect(ShapeFor(1280, 720) == Shape::k16x9, "720p: 16:9");
  Expect(ShapeFor(1920, 1200) == Shape::k16x9, "16:10 (1.6): 16:9 with thin bars");
  Expect(ShapeFor(2560, 1080) == Shape::kWide && ShapeFor(3440, 1440) == Shape::kWide, "ultrawide: wide scene");
  Expect(ShapeFor(1024, 768) == Shape::k4x3 && ShapeFor(2388, 1668) == Shape::k4x3, "4:3 and 11-inch iPad: 4:3");
  Expect(ShapeFor(2868, 1320) == Shape::kWide, "iPhone 17 Pro Max: wide (as before)");
  Expect(ShapeFor(2007, 2853) == Shape::k4x3, "an unfolded Duo panel: 4:3 (as before)");
  // The same formula as the old FitSceneWidth: 720 * 2868 / 1320 = 1564.4, to 8: 1568.
  Expect(WideSceneWidth(2868, 1320) == 1568, "iPhone wide scene (as before)");
  Expect(WideSceneWidth(2560, 1080) == 1704, "2560x1080 wide scene 1704");
  Expect(WideSceneWidth(3440, 1440) == 1720, "3440x1440 wide scene 1720");
  Expect(WideSceneWidth(1920, 1080) == 1288, "clamped at 1288 (as before)");
  Expect(WideSceneWidth(7680, 1080) == 2400, "clamped at 2400 (as before)");
  // External displays: 4:3 only below 1.5 (a MacBook over AirPlay reported 3381x2160).
  Expect(ShapeFor(3381, 2160, true) == Shape::k16x9, "MacBook over AirPlay (1.565): 16:9, not 4:3");
  Expect(ShapeFor(2560, 1600, true) == Shape::k16x9 && ShapeFor(1440, 960, true) == Shape::k16x9, "16:10 and 3:2: 16:9");
  Expect(ShapeFor(1920, 1080, true) == Shape::k16x9 && ShapeFor(3840, 2160, true) == Shape::k16x9, "16:9 displays");
  Expect(ShapeFor(1024, 768, true) == Shape::k4x3 && ShapeFor(1400, 1000, true) == Shape::k4x3, "4:3 and 1.4: 4:3");
  Expect(ShapeFor(2560, 1080, true) == Shape::kWide, "ultrawide display: wide");
  // The device itself: the 0.6.0 rule, unchanged (both Duo panels and iPads stay 4:3).
  Expect(ShapeFor(3381, 2160) == Shape::k4x3 && ShapeFor(2034, 1398) == Shape::k4x3, "device below 1.6: 4:3 as before");
  std::puts("PASS shapes: 16:9 TV, 4K, 16:10, MacBook, ultrawide, 4:3, and the phone's own as before");
}

static bool Near(double a, double b) { return a > b - 1e-6 && a < b + 1e-6; }
static void Letterbox() {
  Rect r = AspectFit(16.0 / 9.0, 1920, 1080);
  Expect(Near(r.x, 0) && Near(r.y, 0) && Near(r.w, 1920) && Near(r.h, 1080), "16:9 on 16:9 fills");
  r = AspectFit(1560.0 / 720.0, 1920, 1080);
  Expect(Near(r.w, 1920) && Near(r.h, 886) && Near(r.y, 97), "a phone's wide picture on a TV: bars above and below");
  r = AspectFit(4.0 / 3.0, 1920, 1080);
  Expect(Near(r.w, 1440) && Near(r.h, 1080) && Near(r.x, 240), "4:3 on a TV: bars at the sides");
  r = AspectFit(16.0 / 9.0, 1920, 1200);
  Expect(Near(r.w, 1920) && Near(r.h, 1080) && Near(r.y, 60), "16:9 on 16:10: thin bars");
  r = AspectFit(16.0 / 9.0, 1920, 804);
  Expect(Near(r.h, 804) && Near(r.w, 1429) && Near(r.x, 245), "16:9 on 21:9: bars at the sides");
  std::puts("PASS letterbox: fitted, never stretched");
}

// A timeline: each step is an event; the count of resolution changes (the
// render targets rebuilt) is what the grace is about.
struct Timeline {
  Router r;
  int sizing_changes = 0;
  bool last = false;
  void Note() { if (r.sizing_external() != last) { ++sizing_changes; last = r.sizing_external(); } }
  void Connect(double t) { r.Connect(t); Note(); }
  void Disconnect(double t) { r.Disconnect(t); Note(); }
  void Active(bool a, double t) { r.SetActive(a, t); Note(); }
  bool Settle(double t) { const bool s = r.Settle(t); Note(); return s; }
};

static void Routing() {
  {  // Plugged in, unplugged, stays away.
    Timeline t;
    Expect(!t.r.connected() && !t.r.sizing_external() && t.r.SettleIn(0) < 0, "nothing before a display");
    t.Connect(1);
    Expect(t.r.connected() && t.r.sizing_external(), "connected: picture and resolution on the display");
    t.Disconnect(10);
    Expect(!t.r.connected() && t.r.sizing_external(), "unplugged: picture back at once, resolution waits");
    Expect(Near(t.r.SettleIn(10.5), 1.5), "asks again after the rest of the grace");
    Expect(!t.Settle(11.9), "not within 2 s");
    Expect(t.Settle(12.0) && !t.r.sizing_external(), "after 2 s: the phone's resolution");
    Expect(!t.Settle(20) && t.r.SettleIn(20) < 0, "once");
    Expect(t.sizing_changes == 2, "two resolution changes for a real unplug");
  }
  {  // App switch with the display attached: iOS takes its scene away and gives it back.
    Timeline t;
    t.Connect(1);
    t.Active(false, 10);
    t.Disconnect(10.2);
    Expect(t.r.SettleIn(10.2) < 0, "away: wait for the app to be active");
    Expect(!t.Settle(100), "never while away, however long");
    t.Active(true, 200);
    Expect(Near(t.r.SettleIn(200.5), 1.5), "grace restarts on return");
    t.Connect(200.4);
    Expect(!t.Settle(300) && t.r.sizing_external(), "the display back: no change");
    Expect(t.sizing_changes == 1, "an app switch costs no resolution change");
  }
  {  // App switch, and the display was unplugged meanwhile.
    Timeline t;
    t.Connect(1);
    t.Active(false, 10);
    t.Disconnect(10.2);
    t.Active(true, 60);
    Expect(!t.Settle(61.9), "not within 2 s of the return");
    Expect(t.Settle(62) && !t.r.sizing_external(), "then the phone's");
  }
  {  // A display that changes its mode disconnects and connects again.
    Timeline t;
    t.Connect(1);
    t.Disconnect(5);
    t.Connect(5.8);
    Expect(!t.Settle(9) && t.r.sizing_external() && t.sizing_changes == 1, "a mode change: no resolution change");
  }
  {  // Deactivated (Control Center) while the display stays.
    Timeline t;
    t.Connect(1);
    t.Active(false, 3);
    t.Active(true, 4);
    Expect(!t.Settle(50) && t.r.connected() && t.sizing_changes == 1, "inactive alone changes nothing");
  }
  {  // No display ever: nothing changes.
    Timeline t;
    t.Disconnect(1);
    t.Active(false, 2);
    t.Active(true, 3);
    Expect(!t.Settle(100) && !t.r.sizing_external() && t.sizing_changes == 0, "no display: no change at all");
  }
  {  // Unplugged and plugged again after the grace: changes each time.
    Timeline t;
    t.Connect(1);
    t.Disconnect(2);
    t.Settle(4.5);
    t.Connect(10);
    Expect(t.r.sizing_external() && t.sizing_changes == 3, "back after the grace: the display's again");
  }
  std::puts("PASS routing: unplug, app switch, unplug while away, mode change, inactive, no display, replug");
}

int main() { PicturePixels(); Shapes(); Letterbox(); Routing(); }
'''


def check_wiring():
    src = ROOT / 'ios/src'
    renderer = (src / 'native_renderer.mm').read_text()
    catalog = (src / 'settings_catalog.mm').read_text()
    module = (src / 'external_display.mm').read_text()
    # The "native" scale follows the display's capped pixels while SizingExternal.
    assert 'external_display::SizingExternal()' in renderer and 'external_display::PicturePixels()' in renderer
    assert 'NFSExternalPictureView' in renderer and 'ed::CappedPixels(size.width * scale' in module
    assert 'ed::SetPictureHandler(' in renderer and 'UIScreen.screens' not in renderer.split('void WatchExternalDisplay')[1][:600]
    # The shape at Play comes from the display when one is connected.
    assert 'external_display::ConnectedPixels(&external)' in catalog
    assert 'ShapeFor(px.width, px.height, external)' in catalog and 'WideSceneWidth(px.width, px.height)' in catalog
    # 16:9 with the native renderer: one pass (it does not replay the game's 3 MSAA strips).
    assert 'wide || native_16_9 ||' in catalog and '[aspect isEqualToString:@"16:9"]' in catalog
    # The phone's layer stays visible with the picture on a display (the touch controls are drawn into it).
    assert 'present_view.alpha = 0' not in renderer and 'if (!phone_controls_only.load(' in renderer
    # The Info.plist names the scene delegate the module defines.
    plist_text = (ROOT / 'ios/Info.plist.in').read_text()
    plist = plistlib.loads(re.sub(r'@[A-Z_]+@', 'x', plist_text).encode())
    roles = plist['UIApplicationSceneManifest']['UISceneConfigurations']
    assert list(roles) == ['UIWindowSceneSessionRoleExternalDisplayNonInteractive'], roles
    delegate = roles['UIWindowSceneSessionRoleExternalDisplayNonInteractive'][0]['UISceneDelegateClassName']
    assert f'@implementation {delegate}' in module, delegate
    # The window lookups skip the 1-point window.
    for name in ('touch_controls.mm', 'ingame_options.mm', 'keyboard_prompts.mm', 'gpu_capture.mm', 'native_renderer.mm'):
        text = (src / name).read_text()
        for m in re.finditer(r'for \(UIWindow\* w in \(\(UIWindowScene\*\)scene\)\.windows\) \{\n(.*)\n', text):
            if 'isKeyWindow' in text[m.end():m.end() + 80] or 'isKeyWindow' in m.group(1):
                assert 'IsHelperWindow(w)' in m.group(1), (name, m.group(1))
    print('PASS wiring: renderer, settings, Info.plist delegate, window lookups')


def main():
    text = HARNESS.replace('@HEADER@', str(ROOT / 'ios/src/external_display_policy.h'))
    with tempfile.TemporaryDirectory(prefix='nfsmw-external-display-') as temp:
        cpp, exe = Path(temp) / 'test.cpp', Path(temp) / 'test'
        cpp.write_text(text)
        subprocess.run(['xcrun', 'clang++', '-std=c++20', '-O1', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(cpp), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)
    check_wiring()


if __name__ == '__main__':
    main()
