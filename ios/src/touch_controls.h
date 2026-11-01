// NFSMW Recompiled - on-screen touch controls on iOS (touch_controls.mm)

#pragma once

#ifdef __OBJC__
#import <UIKit/UIKit.h>
@class NSString;
@class UIViewController;

// A button over the game that never takes the keyboard's focus: with a
// hardware keyboard, iPadOS moves focus with the arrow keys and presses the
// focused button with Return and Space, so the game did not get those keys
// (dev13, Stefan: Return and the arrows ignored on the load screen, S worked).
@interface NFSUnfocusableButton : UIButton
@end
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
constexpr int kRaceCircle = 8;  // the circle is an event's (not a shop's or safehouse's)
void SetDriveContext(int bits);

// A drag race (game_state.cpp: HUD_Drag.fng up), on the game's thread: the
// DRAG layout.
void SetDragRace(bool on);

// The world map is up (game_state.cpp): a menu swipe moves the right stick.
void SetMapUp(bool up);

// A one-finger tap in a menu, for the game's thread to look for a button
// hint under it (package units from the middle of the screen); answered
// with MenuTapResult: button bits, 0 blank, -1 ignored, or a popup selection
// response from menu_touch_policy.h. Scroll queries return that header's DragMode.
bool TakeMenuTap(int& serial, float& x, float& y);
void MenuTapResult(int serial, int button);
bool TakeMenuScroll(int& serial, float& x, float& y);
void MenuScrollResult(int serial, int mode);
void SetMoviePlaying(bool on);
// Touches on the game's screen so far (the keyboard prompts hide on a touch).
int TouchesSoFar();
void SetShowcaseUp(bool on);
// Showcase.fng is up (keyboard_prompts.mm: mouse drag turns the car there).
bool ShowcaseUp();

#ifdef __OBJC__
// The touch layout editor (positions, sizes, opacity), presented full screen
// in landscape from the launcher. `steering`: the launcher's touch_steering
// (dynamic, fixed or buttons), which decides the DRIVE layout's steering.
UIViewController* MakeLayoutEditor(NSString* steering);
#endif

}  // namespace nfsmw::touch
