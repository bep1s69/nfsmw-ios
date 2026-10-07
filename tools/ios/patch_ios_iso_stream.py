#!/usr/bin/env python3
"""
When an ISO cannot be mapped into memory whole, it is read in pieces instead
of failing.

    python3 tools/ios/patch_ios_iso_stream.py            apply
    python3 tools/ios/patch_ios_iso_stream.py --status
    python3 tools/ios/patch_ios_iso_stream.py --revert

Touches include/rex/filesystem/devices/disc_image_device.h,
include/rex/filesystem/devices/disc_image_entry.h,
src/filesystem/devices/disc_image_device.cpp and
src/filesystem/devices/disc_image_file.cpp.


WHY
===

A player's iPad with an M1 chip: the game never started, "Disc image could
not be mapped", then the runtime setup failed (and the app aborted on the way
out). DiscImageDevice maps the whole ISO (7.8 GB for NFSMW) into the address
space at once; with the guest memory's 4.5 GB reservation besides, that is
more address space than iOS gives the app there (it worked on an iPad Pro M4
and an iPhone 17 Pro Max).

Now, only if that mapping fails, the device keeps the file open instead:
- the disc header and the directory tree are read with pread (a few small
  reads: the magic, sector 32, then each directory's own sectors);
- DiscImageFile::ReadSync reads a file's bytes with pread at its offset;
- DiscImageEntry::can_map() says no, so the XEX loader (UserModule) reads
  default.xex through ReadSync instead of a mapped view, as it already does
  for devices that cannot map.
With the mapping (every device where it works), nothing changes.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

DH = "include/rex/filesystem/devices/disc_image_device.h"
EH = "include/rex/filesystem/devices/disc_image_entry.h"
DC = "src/filesystem/devices/disc_image_device.cpp"
FC = "src/filesystem/devices/disc_image_file.cpp"

DH_UNITS_ANCHOR = '''  uint32_t total_allocation_units() const override {
    return uint32_t(mmap_->size() / sectors_per_allocation_unit() / bytes_per_sector());
  }
'''
DH_UNITS_NEW = '''  uint32_t total_allocation_units() const override {
    // LOCAL PATCH - iOS: also when read in pieces (tools/ios/patch_ios_iso_stream.py).
    return uint32_t((mmap_ ? mmap_->size() : disc_info_.host_size) /
                    sectors_per_allocation_unit() / bytes_per_sector());
  }

  // LOCAL PATCH - iOS: reading the image in pieces when it cannot be mapped
  // whole (tools/ios/patch_ios_iso_stream.py). False on a short read.
  bool IosReadAt(size_t offset, void* dest, size_t length) const;
'''

DH_MEMBER_ANCHOR = '''  std::unique_ptr<memory::MappedMemory> mmap_;
  DiscInfo disc_info_{};
'''
DH_MEMBER_NEW = '''  std::unique_ptr<memory::MappedMemory> mmap_;
  int ios_fd_ = -1;  // LOCAL PATCH - iOS: the open image when not mapped
  DiscInfo disc_info_{};
'''

EH_ANCHOR = '''  bool can_map() const override { return true; }
'''
EH_NEW = '''  // LOCAL PATCH - iOS: not when the image is read in pieces
  // (tools/ios/patch_ios_iso_stream.py).
  bool can_map() const override { return mmap_ != nullptr; }
'''

DC_INCLUDE_ANCHOR = '''#include <rex/memory.h>
'''
DC_INCLUDE_NEW = '''#include <rex/memory.h>

// LOCAL PATCH - iOS: reading the image in pieces (tools/ios/patch_ios_iso_stream.py).
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstring>
#include <vector>
#include <rex/cvar.h>
REXCVAR_DEFINE_BOOL(ios_iso_stream, false, "Storage",
                    "iOS: read the disc image in pieces even when it could be mapped whole "
                    "(for testing the fallback used when it cannot)");
'''

DC_DTOR_ANCHOR = '''DiscImageDevice::~DiscImageDevice() = default;
'''
DC_DTOR_NEW = '''DiscImageDevice::~DiscImageDevice() {
  // LOCAL PATCH - iOS (tools/ios/patch_ios_iso_stream.py).
  if (ios_fd_ >= 0) {
    close(ios_fd_);
  }
}

bool DiscImageDevice::IosReadAt(size_t offset, void* dest, size_t length) const {
  auto* out = static_cast<uint8_t*>(dest);
  while (length) {
    const ssize_t n = pread(ios_fd_, out, length, off_t(offset));
    if (n <= 0) {
      return false;
    }
    out += n;
    offset += size_t(n);
    length -= size_t(n);
  }
  return true;
}
'''

DC_INIT_ANCHOR = '''  mmap_ = memory::MappedMemory::Open(host_path_, memory::MappedMemory::Mode::kRead);
  if (!mmap_) {
    REXFS_ERROR("Disc image could not be mapped");
    return false;
  }

  ParseState state = {};
  state.ptr = mmap_->data();
  state.size = mmap_->size();
'''
DC_INIT_NEW = '''  // LOCAL PATCH - iOS: ios_iso_stream forces reading in pieces, for testing
  // (tools/ios/patch_ios_iso_stream.py).
  if (!REXCVAR_GET(ios_iso_stream)) {
    mmap_ = memory::MappedMemory::Open(host_path_, memory::MappedMemory::Mode::kRead);
  }
  ParseState state = {};
  if (mmap_) {
    state.ptr = mmap_->data();
    state.size = mmap_->size();
  } else {
    // LOCAL PATCH - iOS: not enough address space to map the image whole
    // (an iPad M1): read it in pieces (tools/ios/patch_ios_iso_stream.py).
    ios_fd_ = open(host_path_.c_str(), O_RDONLY | O_CLOEXEC);
    struct stat st = {};
    if (ios_fd_ < 0 || fstat(ios_fd_, &st) != 0) {
      REXFS_ERROR("Disc image could not be mapped or opened");
      return false;
    }
    REXFS_INFO("Disc image could not be mapped whole ({} MB): reading it in pieces",
               uint64_t(st.st_size) >> 20);
    state.ptr = nullptr;
    state.size = size_t(st.st_size);
  }
'''

DC_ROOT_ANCHOR = '''  result = ReadAllEntries(&state, state.ptr + state.root_offset);
'''
DC_ROOT_NEW = '''  // LOCAL PATCH - iOS: the root directory read into a buffer when not mapped
  // (tools/ios/patch_ios_iso_stream.py).
  std::vector<uint8_t> ios_root;
  if (!state.ptr) {
    ios_root.resize(state.root_size);
    if (!IosReadAt(state.root_offset, ios_root.data(), ios_root.size())) {
      REXFS_ERROR("Failed to read the disc image's root directory");
      return false;
    }
  }
  result = ReadAllEntries(&state, state.ptr ? state.ptr + state.root_offset : ios_root.data());
'''

DC_SECTOR_ANCHOR = '''  uint8_t* fs_ptr = state->ptr + state->game_offset + (32 * kXESectorSize);
'''
DC_SECTOR_NEW = '''  // LOCAL PATCH - iOS: read when not mapped (tools/ios/patch_ios_iso_stream.py).
  uint8_t ios_sector[32] = {};
  if (!state->ptr &&
      !IosReadAt(state->game_offset + (32 * kXESectorSize), ios_sector, sizeof(ios_sector))) {
    return Error::kErrorReadError;
  }
  const uint8_t* fs_ptr =
      state->ptr ? state->ptr + state->game_offset + (32 * kXESectorSize) : ios_sector;
'''

DC_MAGIC_ANCHOR = '''  // Simple check to see if the given offset contains the magic value.
  return std::memcmp(state->ptr + offset, "MICROSOFT*XBOX*MEDIA", 20) == 0;
'''
DC_MAGIC_NEW = '''  // Simple check to see if the given offset contains the magic value.
  if (!state->ptr) {
    // LOCAL PATCH - iOS: read when not mapped (tools/ios/patch_ios_iso_stream.py).
    char magic[20];
    return IosReadAt(offset, magic, sizeof(magic)) &&
           std::memcmp(magic, "MICROSOFT*XBOX*MEDIA", 20) == 0;
  }
  return std::memcmp(state->ptr + offset, "MICROSOFT*XBOX*MEDIA", 20) == 0;
'''

DC_FOLDER_ANCHOR = '''      // Read child list.
      uint8_t* folder_ptr = state->ptr + state->game_offset + (sector * kXESectorSize);
      if (!ReadEntry(state, folder_ptr, 0, entry.get())) {
        return false;
      }
'''
DC_FOLDER_NEW = '''      // Read child list.
      if (!state->ptr) {
        // LOCAL PATCH - iOS: the directory read into a buffer when not mapped
        // (tools/ios/patch_ios_iso_stream.py).
        std::vector<uint8_t> folder(length);
        if (!IosReadAt(state->game_offset + (sector * kXESectorSize), folder.data(), length) ||
            !ReadEntry(state, folder.data(), 0, entry.get())) {
          return false;
        }
      } else {
      uint8_t* folder_ptr = state->ptr + state->game_offset + (sector * kXESectorSize);
      if (!ReadEntry(state, folder_ptr, 0, entry.get())) {
        return false;
      }
      }
'''

FC_INCLUDE_ANCHOR = '''#include <rex/filesystem/devices/disc_image_entry.h>
'''
FC_INCLUDE_NEW = '''#include <rex/filesystem/devices/disc_image_device.h>  // LOCAL PATCH - iOS (patch_ios_iso_stream.py)
#include <rex/filesystem/devices/disc_image_entry.h>
'''

FC_READ_ANCHOR = '''  std::memcpy(buffer.data(), entry_->mmap()->data() + real_offset, real_length);
'''
FC_READ_NEW = '''  if (!entry_->mmap()) {
    // LOCAL PATCH - iOS: the image is read in pieces (tools/ios/patch_ios_iso_stream.py).
    if (!static_cast<DiscImageDevice*>(entry_->device())
             ->IosReadAt(real_offset, buffer.data(), real_length)) {
      return X_STATUS_UNSUCCESSFUL;
    }
    *out_bytes_read = real_length;
    return X_STATUS_SUCCESS;
  }
  std::memcpy(buffer.data(), entry_->mmap()->data() + real_offset, real_length);
'''

BLOCKS = [
    (DH, "allocation units and the reader", DH_UNITS_ANCHOR, DH_UNITS_NEW),
    (DH, "the open image", DH_MEMBER_ANCHOR, DH_MEMBER_NEW),
    (EH, "no mapping when read in pieces", EH_ANCHOR, EH_NEW),
    (DC, "includes", DC_INCLUDE_ANCHOR, DC_INCLUDE_NEW),
    (DC, "close and read", DC_DTOR_ANCHOR, DC_DTOR_NEW),
    (DC, "open in pieces when it cannot be mapped", DC_INIT_ANCHOR, DC_INIT_NEW),
    (DC, "the root directory", DC_ROOT_ANCHOR, DC_ROOT_NEW),
    (DC, "sector 32", DC_SECTOR_ANCHOR, DC_SECTOR_NEW),
    (DC, "the magic", DC_MAGIC_ANCHOR, DC_MAGIC_NEW),
    (DC, "directories", DC_FOLDER_ANCHOR, DC_FOLDER_NEW),
    (FC, "include the device", FC_INCLUDE_ANCHOR, FC_INCLUDE_NEW),
    (FC, "files read with pread", FC_READ_ANCHOR, FC_READ_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_iso_stream", BLOCKS))
