#!/usr/bin/env python3
"""
While the native Metal renderer draws the game, the emulated renderer does
not: its draws and resolves are skipped.

    python3 tools/ios/patch_ios_native_only.py            apply
    python3 tools/ios/patch_ios_native_only.py --status
    python3 tools/ios/patch_ios_native_only.py --revert

Touches src/graphics/command_processor.cpp (the GPU plugin) and
src/ui/vulkan/vulkan_presenter.cpp (the runtime, where the flag lives: both
the app and the plugin, which the SDK loads with dlopen, link the runtime).
Builds on patch_ios_present_pacing.py and patch_ios_fps_cap.py.


WHY
===

The native renderer (ios/src/native_renderer.mm) draws every frame itself
from the game's own D3D draws and shows it over the emulated renderer's
output. Until now both ran: the emulated renderer's Vulkan work (draws,
EDRAM, resolves and their readbacks) was done for a picture nobody saw.


HOW
===

The native renderer also takes its draws from here: the command processor
runs on its own thread, so finding and recording the draws costs the game's
thread nothing (it was 9-10 ms of a race frame there, decoding D3D's command
buffers from hooks on the game's draw functions). Each draw goes to it with
the register file, the active shaders' microcode and the index buffer; a
resolve with the register file; a swap before it is handled.

A flag, rex_native_draws_only, set by the native renderer while it shows
frames (and cleared when it has none, e.g. FMVs, so the emulated renderer
takes over again). With it set, the command processor still reads every
packet: registers, constants, fences, event and memory writes the game waits
on, swaps. Only the hand-over of a draw to the backend (IssueDraw, which also
does resolves: an EDRAM copy is a draw in copy mode) is skipped, as if it had
succeeded.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

CP = "src/graphics/command_processor.cpp"
PRES = "src/ui/vulkan/vulkan_presenter.cpp"

FLAG_ANCHOR = '''#include <map>  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py)
'''
FLAG_NEW = '''#include <map>  // PARCHE LOCAL - una pasada (tools/parche_una_pasada.py)
#include <atomic>  // LOCAL PATCH - iOS: native renderer only (patch_ios_native_only.py)

// LOCAL PATCH - iOS: set by the native Metal renderer while it draws the game
// (tools/ios/patch_ios_native_only.py): the emulated renderer's draws and
// resolves are skipped; every other packet is still handled. The native
// renderer's hooks: each draw (or resolve) and swap goes to it. All defined
// in the runtime (vulkan_presenter.cpp).
extern std::atomic<bool> rex_native_draws_only;
struct RexNativeDraw {
  const uint32_t* regs;  // the register file
  const uint32_t* vs_ucode;
  uint32_t vs_dwords;
  const uint32_t* ps_ucode;
  uint32_t ps_dwords;
  uint64_t vs_hash, ps_hash;  // the SDK's ucode hashes (cache keys)
  uint32_t index_base, index_endian, index_count;
};
extern std::atomic<void (*)(const RexNativeDraw*)> rex_native_draw_hook;
extern std::atomic<void (*)(const uint32_t*)> rex_native_resolve_hook;
extern std::atomic<void (*)()> rex_native_swap_hook;
'''

DEF_ANCHOR = '''#include <mach/mach_time.h>
#include <rex/cvar.h>
'''
DEF_NEW = '''#include <mach/mach_time.h>
#include <rex/cvar.h>
#include <atomic>
// LOCAL PATCH - iOS: the native Metal renderer draws the game, the emulated
// renderer skips its draws (tools/ios/patch_ios_native_only.py). Here, in the
// runtime: the app sets them, the GPU plugin reads them.
std::atomic<bool> rex_native_draws_only{false};
struct RexNativeDraw;
std::atomic<void (*)(const RexNativeDraw*)> rex_native_draw_hook{nullptr};
std::atomic<void (*)(const uint32_t*)> rex_native_resolve_hook{nullptr};
std::atomic<void (*)()> rex_native_swap_hook{nullptr};
'''

DRAW_ANCHOR = '''      draw_succeeded = IssueDraw(vgt_draw_initiator.prim_type, vgt_draw_initiator.num_indices,
                                 is_indexed ? &index_buffer_info : nullptr, major_mode_explicit);
'''
DRAW_NEW = '''      // LOCAL PATCH - iOS: the native renderer (patch_ios_native_only.py):
      // the draw (or resolve) to it; to the backend only if it is not the
      // one showing the game.
      if (auto* resolve_hook = rex_native_resolve_hook.load(std::memory_order_relaxed);
          resolve_hook &&
          register_file_->Get<reg::RB_MODECONTROL>().edram_mode == xenos::EdramMode::kCopy) {
        resolve_hook(register_file_->values);
      } else if (auto* draw_hook = rex_native_draw_hook.load(std::memory_order_relaxed)) {
        RexNativeDraw info{};
        info.regs = register_file_->values;
        if (active_vertex_shader_) {
          info.vs_ucode = active_vertex_shader_->ucode_dwords();
          info.vs_dwords = uint32_t(active_vertex_shader_->ucode_dword_count());
          info.vs_hash = active_vertex_shader_->ucode_data_hash();
        }
        if (active_pixel_shader_) {
          info.ps_ucode = active_pixel_shader_->ucode_dwords();
          info.ps_dwords = uint32_t(active_pixel_shader_->ucode_dword_count());
          info.ps_hash = active_pixel_shader_->ucode_data_hash();
        }
        if (is_indexed) {
          info.index_base = index_buffer_info.guest_base;
          info.index_endian = uint32_t(index_buffer_info.endianness);
          info.index_count = index_buffer_info.count;
        }
        draw_hook(&info);
      }
      if (!rex_native_draws_only.load(std::memory_order_relaxed)) {
        draw_succeeded = IssueDraw(vgt_draw_initiator.prim_type, vgt_draw_initiator.num_indices,
                                   is_indexed ? &index_buffer_info : nullptr, major_mode_explicit);
      }
'''

SWAP_ANCHOR = '''  IosCapBeforeSwap();  // LOCAL PATCH - iOS: the frame rate cap
'''
SWAP_NEW = '''  IosCapBeforeSwap();  // LOCAL PATCH - iOS: the frame rate cap
  if (auto* swap_hook = rex_native_swap_hook.load(std::memory_order_relaxed)) {
    swap_hook();  // LOCAL PATCH - iOS: the native renderer's frame ends here
  }
'''

BLOCKS = [
    (PRES, "the native-only flag and hooks, in the runtime", DEF_ANCHOR, DEF_NEW),
    (CP, "the native-only flag and hooks", FLAG_ANCHOR, FLAG_NEW),
    (CP, "draws and resolves to the native renderer", DRAW_ANCHOR, DRAW_NEW),
    (CP, "swaps to the native renderer", SWAP_ANCHOR, SWAP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_native_only", BLOCKS))
