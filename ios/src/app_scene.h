// The app's own window scene and its screen, for Objective-C++ files.
//
// UIScreen.mainScreen is not "the screen the game is on": on a foldable
// (iPhone Duo) it can be one panel while the app's scene shows on the other,
// and code that picked "the phone's scene" by comparing a scene's screen to
// mainScreen found none there, so the game layer was never attached (a black
// inner screen with sound, issue #14). The app's scene is the one with the
// application role; an external display (HDMI, AirPlay) gets another role.
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

// A screen that is neither the app's nor the device's own (an external display).
inline bool IsExternalScreen(UIScreen* screen) {
  return screen && screen != UIScreen.mainScreen && screen != AppScreen();
}

}  // namespace nfsmw
