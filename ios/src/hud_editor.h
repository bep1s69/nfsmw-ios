// NFSMW Recompiled - the Customize HUD editor (hud_editor.mm)

#pragma once

#ifdef __OBJC__
#import <UIKit/UIKit.h>

namespace nfsmw::hud {

// The HUD's elements as outlines on a screen-shaped canvas, with tabs for
// race/free roam and pursuit: drag one to move it (it does not go over
// another), Smaller/Bigger for its own size, sliders for the HUD's size and
// safe zone. It edits hud_scale, hud_safe_zone and hud_layout in settings
// and calls changed after each change (the caller saves and applies).
// Presented full screen in landscape.
UIViewController* MakeEditor(NSMutableDictionary<NSString*, NSString*>* settings, void (^changed)(void));

}  // namespace nfsmw::hud
#endif
