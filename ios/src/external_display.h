// NFSMW Recompiled (iOS) - an external display (USB-C, HDMI adapter, AirPlay)
//
// When a display is connected iOS can give the app a scene of its own on it
// (role UIWindowSceneSessionRoleExternalDisplayNonInteractive) instead of
// mirroring the phone. This file receives that scene, keeps one window on it,
// and hands its content view to the game's picture (native_renderer.mm); the
// phone keeps the touch controls. The decisions themselves (pixels, shape,
// when the resolution goes back) are in external_display_policy.h.
//
// How iOS offers the scene:
//  - iOS 27: only to a registered scene accessory (UISceneAccessory). It is
//    registered on a 1-point window of the app's own scene that lives from
//    the launcher to the end of the game, so the display's scene is not torn
//    down when the launcher's window gives way to the game's.
//  - iOS 17-26: through Info.plist's scene manifest (the external display
//    role names NFSExternalDisplaySceneDelegate). SDL's app delegate answers
//    for the application role only (tools/ios/patch_ios_sdl_scene.py);
//    unpatched, it took the display's scene too and started main() again.
// Without a display nothing here shows anything: the 1-point window is empty,
// below the launcher's and the game's, never key and never touched.
//
// Main thread unless a function says otherwise.
#pragma once

#import <UIKit/UIKit.h>

#include <cstdint>
#include <functional>
#include <string>

#include "external_display_policy.h"

// The game's picture on the display: a CAMetalLayer view for the display's
// content view, its drawable the display's shape at most MaxWidth() across.
// The picture is letterboxed inside it by whoever draws (never stretched).
@interface NFSExternalPictureView : UIView
@end

namespace nfsmw::external_display {

// Once the app's scene is up (the launcher calls it): starts listening for a
// display. Safe to call again.
void Start();

// The 1-point window that holds the iOS 27 registration: never the game's
// window, whatever is key (app_scene.h's lookups skip it).
bool IsAnchorWindow(UIWindow* window);

// The game's picture: called with the display's content view when a display's
// scene connects (at once if one already has), and with nil when it goes.
// The view is black and shows a short note until the picture covers it.
void SetPictureHandler(std::function<void(UIView* host)> handler);

// The game will not show its picture on the display (the emulated renderer,
// or the setting off): the display mirrors the phone, as without this file.
void Release();

// Whether the game's resolution follows the display (with the grace after it
// goes; external_display_policy.h Router). Any thread.
bool SizingExternal();

// The display's pixels for the picture (its shape, at most MaxWidth() across),
// the last ones seen: still there during the grace. {0, 0}: none yet. Any thread.
Pixels PicturePixels();

// At most this many pixels across the display's picture (0: the display's
// own). From the launcher's "External display resolution". Any thread.
void SetMaxWidth(uint32_t max_width);
uint32_t MaxWidth();

// A display's scene is connected now: its pixels for the picture (capped).
bool ConnectedPixels(Pixels* pixels);

// Where the module's lines go (boot.txt until the game's log is open).
void SetLog(std::function<void(const std::string&)> log);

}  // namespace nfsmw::external_display
