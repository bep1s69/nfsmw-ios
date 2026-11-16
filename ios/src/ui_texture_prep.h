// NFSMW Recompiled (iOS) - the game's UI textures upscaled ahead of time.
// See ui_texture_prep.mm.
#pragma once

#include <cstdint>
#include <functional>
#include <string>

namespace nfsmw::ui_texture_prep {

// The model is in the app and this version's preparation has not run yet.
bool Needed();
// Any thread: reads the UI texture packs from the disc image, upscales and
// saves every texture not prepared yet. progress(done, total).
void Run(const std::string& iso, const std::function<void(uint32_t, uint32_t)>& progress);

}  // namespace nfsmw::ui_texture_prep
