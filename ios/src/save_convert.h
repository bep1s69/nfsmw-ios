// NFSMW Recompiled - converting a PC (v1.3) save to the Xbox 360 layout, for
// the save manager's import (save_convert.cpp).

#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace nfsmw::saves {

// A PC v1.3 save file (63,596 bytes, "20CM").
bool IsPcSave(const uint8_t* data, size_t size);

// An Xbox 360 save file of this game (62,688 bytes, "MC02", version 0x10D).
bool IsXboxSave(const uint8_t* data, size_t size);

// The PC save in the Xbox 360 layout. Parts with no known map (options,
// the Xbox-only tail) come from xbox_template, an Xbox 360 save. Empty, with
// *error set, when either file is not what is expected.
std::vector<uint8_t> ConvertPcSave(const std::vector<uint8_t>& pc, const std::vector<uint8_t>& xbox_template,
                                   std::string* error);

}  // namespace nfsmw::saves
