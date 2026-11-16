// The app's own window scene and its screen, for Objective-C++ files.
//
// UIScreen.mainScreen is not "the screen the game is on": on a foldable
// (iPhone Duo) it can be one panel while the app's scene shows on the other,
// and code that picked "the phone's scene" by comparing a scene's screen to
// mainScreen found none there, so the game layer was never attached (a black
// inner screen with sound, issue #14). The app's scene is the one with the
// application role; an external display (HDMI, AirPlay) gets another role
// (external_display.mm).
// Main thread only (connectedScenes is UIKit state).
#pragma once

#import <UIKit/UIKit.h>

namespace nfsmw {

inline bool IsAppScene(UIScene* scene) {
  return [scene isKindOfClass:UIWindowScene.class] &&
         [scene.session.role isEqualToString:UIWindowSceneSessionRoleApplication];
}

// The app's scene, the most active one if there are several.
inline UIWindowScene* AppScene() {
  auto rank = [](UISceneActivationState s) {
    switch (s) {
      case UISceneActivationStateForegroundActive: return 0;
      case UISceneActivationStateForegroundInactive: return 1;
      case UISceneActivationStateBackground: return 2;
      default: return 3;
    }
  };
  UIWindowScene* best = nil;
  for (UIScene* scene in UIApplication.sharedApplication.connectedScenes) {
    if (IsAppScene(scene) && (!best || rank(scene.activationState) < rank(best.activationState))) {
      best = (UIWindowScene*)scene;
    }
  }
  return best;
}

// The screen the game is shown on (mainScreen before the scene connects).
inline UIScreen* AppScreen() {
  UIWindowScene* scene = AppScene();
  return scene && scene.screen ? scene.screen : UIScreen.mainScreen;
}

// A window of the app's scene that is never the game's or the launcher's:
// the 1-point window external_display.mm keeps for an external display's
// scene accessory (iOS 27). Lookups of "the key window, else the first" skip it.
inline bool IsHelperWindow(UIWindow* window) {
  static Class anchor = NSClassFromString(@"NFSExternalDisplayAnchorWindow");
  return anchor && [window isKindOfClass:anchor];
}

}  // namespace nfsmw
