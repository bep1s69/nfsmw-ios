// NFSMW Recompiled - on-screen touch controls on iOS (touch_controls.mm)

#pragma once

namespace nfsmw::touch {

// Puts the touch controls over the game's window. Call on the main thread once
// the game's window exists (IosNfsmwApp::OnPostSetup). Idempotent.
void Install();

// The FPS counter in the top-left corner (Android's GameActivity counter):
// frames per second and ms per frame, every half second. Same rules.
void InstallFpsCounter();

}  // namespace nfsmw::touch
