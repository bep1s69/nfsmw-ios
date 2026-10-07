#!/usr/bin/env python3
"""
The SDK's memory layer on iOS.

    python3 tools/ios/patch_ios_memory.py            apply
    python3 tools/ios/patch_ios_memory.py --status
    python3 tools/ios/patch_ios_memory.py --revert

Touches two SDK files:
    src/core/memory_posix.cpp   vm_region_64, and the guest memory as a Mach
                                memory entry
    src/system/xmemory.cpp      map the guest views through MapFileView


mach_vm_region ON iOS
=====================

QueryProtect() asks the kernel for the protection of a memory range. On macOS
it uses mach_vm_region(), from <mach/mach_vm.h>. On iOS that header exists
only to say no:

    mach/mach_vm.h:1:2: error: mach_vm.h unsupported.

The equivalent call is vm_region_64(), from <mach/vm_map.h>. In a 64-bit
process (all of iOS today) vm_address_t and vm_size_t are 64 bits, so it is
the same call with other type names. A wrapper with the macOS name goes in
and the rest of the function is unchanged.


THE GUEST MEMORY: A MACH MEMORY ENTRY, NOT POSIX SHM
====================================================

The guest's ~4.5 GB of memory is ONE shared object mapped at several guest
addresses at once (the same physical page is visible through more than one
view). On macOS that object is POSIX shared memory: shm_open + ftruncate,
then mmap(MAP_SHARED | MAP_FIXED) of each view. On iOS the sandbox refuses
it. Measured on an iPhone 17 Pro Max, iOS 27.0.1, inside LiveContainer
(ios/src/probe_memory.cpp):

    POSIX shm (what the SDK uses): shm_open FAILS, errno 1 (Operation not permitted)
    Mach memory entry (the alternative): OK, 4.50 GB entry

and the SDK's own log said only "Unable to reserve the 4gb guest address
space." The address space was never the problem (~508 GB).

A Mach memory entry is the same thing without a name: anonymous memory
created with mach_make_memory_entry_64(MAP_MEM_NAMED_CREATE) and mapped with
vm_map(), as many times and wherever needed. It is how Dolphin backs its
emulated memory on iOS. The probe checked, on the device, that two views of
the same offset alias and that mprotect() works on a view (the SDK's commit,
decommit and write watching are all mprotect/madvise on the views).

FileMappingHandle is an intptr_t and is never read as a descriptor outside
these functions, so on iOS it carries the entry's Mach port instead:

  - CreateFileMappingHandle   mach_make_memory_entry_64 instead of shm_open
  - CloseFileMappingHandle    mach_port_deallocate instead of close+shm_unlink
  - MapFileView               vm_map instead of mmap (FIXED | OVERWRITE over
                              the reservation, like MAP_FIXED)
  - UnmapFileView             unchanged: munmap undoes a vm_map too
  - Memory::MapViewsMac       called mmap on the descriptor directly; it goes
                              through MapFileView instead

Guest memory never becomes executable on the host (ToPageAccess in
xmemory.cpp only yields none, read-only or read-write), so none of this needs
a JIT entitlement.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

MACH_ANCHOR = '''#if REX_PLATFORM_MAC
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/vm_region.h>
#endif  // REX_PLATFORM_MAC
'''
MACH_NEW = '''#if REX_PLATFORM_MAC
#include <mach/mach.h>
#if REX_PLATFORM_IOS
// LOCAL PATCH - iOS: mach/mach_vm.h does not exist on iOS ("unsupported"). Its
// mach_vm_region is vm_region_64 from mach/vm_map.h, the same thing in 64 bits.
#include <mach/vm_map.h>
static inline kern_return_t mach_vm_region(vm_map_t task, mach_vm_address_t* address,
                                           mach_vm_size_t* size, vm_region_flavor_t flavor,
                                           vm_region_info_t info,
                                           mach_msg_type_number_t* info_count,
                                           mach_port_t* object_name) {
  static_assert(sizeof(vm_address_t) == sizeof(mach_vm_address_t) &&
                    sizeof(vm_size_t) == sizeof(mach_vm_size_t),
                "vm_region_64 only stands in for mach_vm_region in 64 bits");
  return vm_region_64(task, reinterpret_cast<vm_address_t*>(address),
                      reinterpret_cast<vm_size_t*>(size), flavor, info, info_count, object_name);
}
#else
#include <mach/mach_vm.h>
#endif
#include <mach/vm_region.h>
#endif  // REX_PLATFORM_MAC
'''

CREATE_ANCHOR = '''FileMappingHandle CreateFileMappingHandle(const std::filesystem::path& path, size_t length,
                                          PageAccess access, bool commit) {
#if REX_PLATFORM_ANDROID
'''
CREATE_NEW = '''FileMappingHandle CreateFileMappingHandle(const std::filesystem::path& path, size_t length,
                                          PageAccess access, bool commit) {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: the sandbox refuses shm_open (EPERM). A Mach memory
  // entry is the same shared object without a name; the handle carries its
  // port. Always read-write: the views are mapped read-write and narrowed with
  // mprotect.
  (void)path;
  (void)access;
  (void)commit;
  memory_object_size_t entry_size = length;
  mach_port_t entry = MACH_PORT_NULL;
  const kern_return_t kr =
      mach_make_memory_entry_64(mach_task_self(), &entry_size, 0,
                                MAP_MEM_NAMED_CREATE | VM_PROT_READ | VM_PROT_WRITE, &entry,
                                MACH_PORT_NULL);
  if (kr != KERN_SUCCESS || entry_size < length) {
    REXLOG_ERROR("CreateFileMappingHandle: mach_make_memory_entry_64 of 0x{:X} bytes failed: "
                 "kern_return {}",
                 length, kr);
    if (entry != MACH_PORT_NULL) {
      mach_port_deallocate(mach_task_self(), entry);
    }
    return kFileMappingHandleInvalid;
  }
  return static_cast<FileMappingHandle>(entry);
#endif
#if REX_PLATFORM_ANDROID
'''

CLOSE_ANCHOR = '''void CloseFileMappingHandle(FileMappingHandle handle, const std::filesystem::path& path) {
  close(static_cast<int>(handle));
'''
CLOSE_NEW = '''void CloseFileMappingHandle(FileMappingHandle handle, const std::filesystem::path& path) {
#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: a Mach memory entry, not a descriptor (see
  // CreateFileMappingHandle). The views already mapped keep the memory alive.
  (void)path;
  mach_port_deallocate(mach_task_self(), static_cast<mach_port_t>(handle));
  return;
#endif
  close(static_cast<int>(handle));
'''

MAP_ANCHOR = '''  int flags = MAP_SHARED;

  // For file views, we need MAP_FIXED to replace existing reservations.
'''
MAP_NEW = '''#if REX_PLATFORM_IOS
  // LOCAL PATCH - iOS: map the Mach memory entry with vm_map. With a base
  // address, over whatever reservation is there (FIXED | OVERWRITE), like
  // MAP_FIXED below. VM_PROT_* and PROT_* have the same values on Darwin. The
  // maximum protection is read-write, so mprotect can widen a view later but
  // never make it executable.
  {
    vm_address_t address = reinterpret_cast<vm_address_t>(base_address);
    const kern_return_t kr =
        vm_map(mach_task_self(), &address, length, 0,
               base_address ? (VM_FLAGS_FIXED | VM_FLAGS_OVERWRITE) : VM_FLAGS_ANYWHERE,
               static_cast<mem_entry_name_port_t>(handle), file_offset, FALSE,
               static_cast<vm_prot_t>(ToPosixProtectFlags(access)),
               VM_PROT_READ | VM_PROT_WRITE, VM_INHERIT_NONE);
    if (kr != KERN_SUCCESS) {
      REXLOG_ERROR("MapFileView: vm_map of 0x{:X} bytes at offset 0x{:X} failed: kern_return {}",
                   length, file_offset, kr);
      return nullptr;
    }
    if (base_address && reinterpret_cast<void*>(address) != base_address) {
      munmap(reinterpret_cast<void*>(address), length);
      return nullptr;
    }
    return reinterpret_cast<void*>(address);
  }
#endif

  int flags = MAP_SHARED;

  // For file views, we need MAP_FIXED to replace existing reservations.
'''

VIEWS_ANCHOR = '''    void* result = mmap(target_address, view_size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_FIXED,
                        mapping_, file_offset);
'''
VIEWS_NEW = '''#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS: mapping_ is a Mach memory entry, not a descriptor
    // (memory_posix.cpp, CreateFileMappingHandle). MapFileView maps it with
    // vm_map; its own log line says why if it fails (errno below is stale).
    void* result = rex::memory::MapFileView(mapping_, target_address, view_size,
                                            rex::memory::PageAccess::kReadWrite, file_offset);
    if (!result) {
      result = MAP_FAILED;
    }
#else
    void* result = mmap(target_address, view_size, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_FIXED,
                        mapping_, file_offset);
#endif
'''

BLOCKS = [
    ("src/core/memory_posix.cpp", "mach_vm_region through vm_region_64", MACH_ANCHOR, MACH_NEW),
    ("src/core/memory_posix.cpp", "guest memory as a Mach memory entry", CREATE_ANCHOR,
     CREATE_NEW),
    ("src/core/memory_posix.cpp", "release the Mach memory entry", CLOSE_ANCHOR, CLOSE_NEW),
    ("src/core/memory_posix.cpp", "map views with vm_map", MAP_ANCHOR, MAP_NEW),
    ("src/system/xmemory.cpp", "guest views through MapFileView", VIEWS_ANCHOR, VIEWS_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_memory", BLOCKS))
