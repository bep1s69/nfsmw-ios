// NFSMW Recompiled - pausing the GPU emulation while the app is in the background
//
// iOS does not let a background app submit GPU work (patch_ios_pause.py), so
// the GPU emulation is paused there. It used to follow SDL's app events:
// paused on SDL_EVENT_WILL_ENTER_BACKGROUND, resumed on
// SDL_EVENT_DID_ENTER_FOREGROUND. Two problems, seen in the log:
//   - SDL sends "will enter background" on every resign-active: a
//     screenshot, Control Center, a notification, the app switcher. The app is
//     still on screen and may still draw.
//   - under LiveContainer the "did enter foreground" never came: the GPU
//     emulation stayed paused, sound and input went on, the screen stayed
//     black until the game was restarted.
// Now:
//   - paused on "will resign active" (app and scene), and "did enter
//     background" in case that was missed. Not later: pausing only at "did
//     enter background" left GPU work (the command processor's last
//     submissions, the UI thread's repaints) to reach Metal in the
//     background, and iOS answered with "Insufficient Permission": device
//     lost, the game gone. The pause also stops the UI thread's paints
//     (game_app.cpp, patch_ios_paint_suspend.py). A screenshot or Control
//     Center pauses too, for as long as they are up;
//   - resumed on any of "will enter foreground" / "did become active" (app
//     and scene), and, if all of those were missed, on the next tick of the
//     display link (display_rate.mm) once the app is active again.
// Both are idempotent.
//
// The display tick also keeps SDL's Metal view the size of its window. After
// a screenshot, the view (and so the CAMetalLayer) stayed PORTRAIT while the
// window was landscape again: MoltenVK took the portrait bounds, the swapchain
// was rebuilt portrait (patch_ios_suboptimal.py could only rebuild it at the
// same wrong size) and the game was drawn into a corner of the screen. If the
// view or a view holding it is not the size of the window, it is given the
// window's bounds; SDL's layoutSubviews then sets the drawable size and the
// swapchain is rebuilt from it.

#import <UIKit/UIKit.h>

#include <rex/logging.h>

#include "lifecycle.h"

namespace nfsmw::lifecycle {
namespace {

std::function<void()> g_pause, g_resume;
bool g_paused = false;  // main thread only

void Pause(const char* why) {
  if (g_paused || !g_pause) {
    return;
  }
  g_paused = true;
  REXLOG_INFO("[ios] to the background ({}): pausing the GPU emulation", why);
  g_pause();
}

void Resume(const char* why) {
  if (!g_paused || !g_resume) {
    return;
  }
  g_paused = false;
  REXLOG_INFO("[ios] back on screen ({}): resuming the GPU emulation", why);
  g_resume();
}

}  // namespace

void Install(std::function<void()> pause, std::function<void()> resume) {
  g_pause = std::move(pause);
  g_resume = std::move(resume);
  NSNotificationCenter* center = NSNotificationCenter.defaultCenter;
  NSOperationQueue* main = NSOperationQueue.mainQueue;
  auto on = [&](NSNotificationName name, void (*action)(const char*), const char* why) {
    [center addObserverForName:name
                        object:nil
                         queue:main
                    usingBlock:^(NSNotification*) {
                      action(why);
                    }];
  };
  on(UIApplicationWillResignActiveNotification, Pause, "app resigns active");
  on(UISceneWillDeactivateNotification, Pause, "scene resigns active");
  on(UIApplicationDidEnterBackgroundNotification, Pause, "app");
  on(UISceneDidEnterBackgroundNotification, Pause, "scene");
  // Only "active" resumes: "will enter foreground" comes before the app may
  // draw, and an inactive app (a screenshot's preview, Control Center) is
  // still paused.
  on(UIApplicationDidBecomeActiveNotification, Resume, "app active");
  on(UISceneDidActivateNotification, Resume, "scene active");
}

namespace {

UIView* FindMetalView(UIView* view, Class metal) {
  if ([view isKindOfClass:metal]) {
    return view;
  }
  for (UIView* sub in view.subviews) {
    if (UIView* found = FindMetalView(sub, metal)) {
      return found;
    }
  }
  return nil;
}

void KeepMetalViewWindowSized() {
  static Class metal = NSClassFromString(@"SDL_uikitmetalview");
  static __weak UIView* cached = nil;
  if (!metal) {
    return;
  }
  UIView* view = cached;
  if (!view || !view.window) {
    view = nil;
    for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
      if (![scene isKindOfClass:UIWindowScene.class]) {
        continue;
      }
      for (UIWindow* w in ((UIWindowScene*)scene).windows) {
        if ((view = FindMetalView(w, metal))) {
          break;
        }
      }
      if (view) {
        break;
      }
    }
    cached = view;
  }
  UIWindow* window = view.window;
  if (!window) {
    return;
  }
  const CGSize want = window.bounds.size;
  for (UIView* v = view; v && v != window; v = v.superview) {
    if (!CGSizeEqualToSize(v.bounds.size, want)) {
      REXLOG_INFO("[ios] a game view is {:.0f}x{:.0f}, its window {:.0f}x{:.0f}: resized to it",
                  v.bounds.size.width, v.bounds.size.height, want.width, want.height);
      v.frame = window.bounds;
      [v setNeedsLayout];
      [v layoutIfNeeded];
    }
  }
}

}  // namespace

void OnDisplayTick() {
  KeepMetalViewWindowSized();
  if (g_paused && UIApplication.sharedApplication.applicationState == UIApplicationStateActive) {
    Resume("display refresh");
  }
}

}  // namespace nfsmw::lifecycle
