// NFSMW Recompiled - on-screen touch controls on iOS (touch_controls.mm)

#pragma once

#ifdef __OBJC__
@class NSString;
@class UIViewController;
#endif

namespace nfsmw::touch {

// Puts the touch controls over the game's window. Call on the main thread once
// the game's window exists (IosNfsmwApp::OnPostSetup). Idempotent.
void Install();

// The FPS counter in the top-left corner (Android's GameActivity counter):
// frames per second and ms per frame, every half second. Same rules.
void InstallFpsCounter();

// What the HUD shows while driving (game_scene_size.cpp, twice a second, on
// the game's thread): the DRIVE layout's D-pad buttons follow it.
constexpr int kInCircle = 1;  // an event, shop or safehouse circle: ENTER
constexpr int kInRace = 2;    // a race or another event (a pursuit challenge): STATS only
constexpr int kInPursuit = 4;  // a pursuit: STATS, and MAP outside events
void SetDriveContext(int bits);

#ifdef __OBJC__
// The touch layout editor (positions, sizes, opacity), presented full screen
// in landscape from the launcher. `steering`: the launcher's touch_steering
// (dynamic, fixed or buttons), which decides the DRIVE layout's steering.
UIViewController* MakeLayoutEditor(NSString* steering);
#endif

}  // namespace nfsmw::touch
