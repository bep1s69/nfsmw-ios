// NFSMW Recompiled - the options menu while playing (ingame_options.mm)

#pragma once

namespace nfsmw::options {

// The gear (in menus and pause screens) and L3+R3 that open the options.
// Call on the main thread once the game's window exists. Idempotent.
void Install();

// The options sheet is up (or was just closed and a controller button is
// still held): the game gets no input.
bool BlocksGameInput();

}  // namespace nfsmw::options
