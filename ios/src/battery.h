// NFSMW Recompiled - frame rate and resolution by the game's state and the
// phone's heat (battery.mm)

#pragma once

namespace nfsmw::battery {

// Starts the thread that follows Low Power Mode and the thermal state (every
// 2 s): at the 60 cap, 30 fps while warm or on Low Power
// (nfsmw_battery_auto_cap); 0.75x render resolution from "serious" until
// cool again (nfsmw_heat_scale). Call once the cvars are parsed.
void Start();

// From the game's thread (game_state.cpp) every frame: whether a menu or a
// pause screen is up (anything but driving). At the 60 cap, 30 fps in them
// (nfsmw_menu_cap).
void SetInMenu(bool in_menu);

// What SetInMenu last said: -1 not known yet, 0 driving, 1 in a menu. Any
// thread (the touch controls read it).
int InMenu();

// The native renderer's resolution scale while the phone is hot (0.75), or 0
// (the scale chosen). Any thread.
float HeatScale();

}  // namespace nfsmw::battery
