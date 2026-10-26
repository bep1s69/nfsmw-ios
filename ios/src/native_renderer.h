// Native renderer bring-up: the interface between the draw capture
// (native_draw_census.cpp, which decodes what each D3D draw wrote into the
// ring) and the Metal renderer (native_renderer.mm).

#pragma once

#include <cstdint>

extern "C" {

struct NfsmwNativeDraw {
  const uint32_t* regs;          // the decoded Xenos register file (0x6000 dwords)
  const uint32_t* vs_microcode;  // the bound vertex shader, host byte order
  uint32_t vs_dwords;
  uint64_t vs_key;               // Metal library names (vs_/ps_<key>)
  uint64_t ps_key;
  uint32_t initiator;            // VGT_DRAW_INITIATOR of the draw packet
  uint32_t index_base;           // DRAW_INDX: index buffer (guest physical)
  uint32_t index_size;           // DRAW_INDX: size dword (endian in bits 30-31)
  uint32_t inline_draw;          // DRAW_INDX_2 (inline data)
  // From the draw function's own arguments when its draw packet went to
  // another buffer (D3D's predicated tiling path): the start vertex replaces
  // VGT_INDX_OFFSET.
  uint32_t from_arguments;
  uint32_t start_vertex;
  // DrawPrimitiveUP (sub_825930E0): where its vertices are (guest virtual,
  // its return value); its fetch constant update goes to the other buffer.
  uint32_t up_vertices;
  uint64_t vs_microcode_hash = 0;  // full SDK hash, including fetches (0: uncached legacy capture)
};

// At each Swap: finishes the frame being recorded (if any) and says whether
// to record the next one.
bool nfsmw_native_swap();
// Each draw of a recorded frame.
void nfsmw_native_draw(const NfsmwNativeDraw* draw);
// A resolve between draws of a recorded frame (the register file after its
// packets).
void nfsmw_native_resolve(const uint32_t* regs);

// The FPS counter, drawn into the native frame itself (IPA88): a UIKit label
// over the game's layer delayed the game's frame each time its text changed.
// Whether the native layer is showing frames (then it draws the counter).
bool nfsmw_native_overlay_active();
// The counter's picture (BGRA, premultiplied over its dark box, w x h pixels)
// and where it goes, as fractions of the window (x, y from the top left).
// Null bgra: no counter.
// The width in pixels of the last frame shown (0 before the first): the
// counter is drawn at that resolution, not the screen's (IPA89).
int nfsmw_native_drawable_width();
void nfsmw_native_set_fps_overlay(const uint8_t* bgra, int w, int h, float x, float y, float fw, float fh);

}  // extern "C"
