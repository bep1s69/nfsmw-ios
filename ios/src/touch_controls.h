// NFSMW Recompiled - on-screen touch controls on iOS (touch_controls.mm)

#pragma once

#ifdef __OBJC__
@class UIViewController;
#endif

namespace nfsmw::touch {

// Puts the touch controls over the game's window. Call on the main thread once
// the game's window exists (IosNfsmwApp::OnPostSetup). Idempotent.
void Install();

// The FPS counter in the top-left corner (Android's GameActivity counter):
// frames per second and ms per frame, every half second. Same rules.
void InstallFpsCounter();

#ifdef __OBJC__
// The touch layout editor (positions, sizes, opacity), presented full screen
// in landscape from the launcher.
UIViewController* MakeLayoutEditor();
#endif

}  // namespace nfsmw::touch
