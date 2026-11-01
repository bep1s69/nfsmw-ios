// NFSMW Recompiled - keyboard keys that follow the game's context
// (keyboard_context.cpp)

#pragma once

#include <string>

namespace nfsmw::keyboard {

// A menu is up (true) or the player drives (false): the keyboard's keys
// switch to that set. Game thread; cheap when nothing changes.
void SetMenu(bool menu);
// Each frame (game thread): a switch waiting for the keys to be released.
void Service();
// Main thread: a key is down now.
void SetAnyKeyDown(bool down);

// KEY PROMPTS (keyboard_prompts.mm): the menu's button hints get the menu
// key that presses them, while the keyboard is the last thing used.
// The overlay wants hints (keyboard controls on, keyboard used last).
bool PromptsWanted();
// From the game thread: n hints, 5 floats each (x, y, half width, half
// height in the packages' units; the button bits of menu_touch_policy.h).
void SetHints(const float* hints, int n);
// The first key of a menu bind ("keybind_a" -> "Return"), "" if none.
std::string MenuKey(const char* bind);
// Main thread, once the game's window exists.
void InstallPrompts();

}  // namespace nfsmw::keyboard
