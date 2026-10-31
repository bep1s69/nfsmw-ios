#pragma once
#include <cstddef>
namespace nfsmw::pc {
// FECustomizationRecord field map from existing ios/src/save_convert.cpp:
// int16 part indices [0,116), padding116/117, 32-bit physics/tunings/preset
// [118,194), bytehandle194 and padding195..197 (hex offsets). Only numeric
// fields change byte order; network conversion never rewrites padding values.
// Existing converter credits sprintstate/nfs-mw-save-editor /
// dbalatoni13/nfsmw.
constexpr size_t CarByte(size_t index, size_t size) {
  if (size == 4)
    return index ^ 3;
  if (size == 408) {
    if (index < 0x116)
      return index ^ 1;
    if (index >= 0x118 && index < 0x194)
      return index ^ 3;
  }
  return index;
}
} // namespace nfsmw::pc
