// NFSMW Recompiled (iOS) - car reflection faces and the rear-view mirror
// drawn at the update rates chosen in the options, in the game itself.
//
// The game's render thread runs its frame from the deferred-call queue
// (sub_823C8290). dev203's log (Nov 17, iPhone race) shows, every frame:
//   sub_82463488 (begin mirror) ... sub_82463490 (end mirror: its resolve)
//   then six times
//   sub_82463498 (begin face) ... sub_824634A0 (end face, data 18 + face)
// with the view's own entries between (set up the view, draw its lists).
// tools/ios/patch_game_pass_cadence.py makes the runner ask
// nfsmw_pass_cadence_skip before each entry; a block left out issues no
// draws and no resolve, so the game thread, the GPU command thread and the
// renderer all skip it, and the renderer keeps the face / mirror picture
// from the last frame that drew it (its kept cube and kept resolves).
//
// Each face and the mirror keep a phase that grows by rate / cap at each
// of their begins and are drawn when it passes 1 (faces start a sixth
// apart), as the renderer's own cadence did in dev201.
#include <algorithm>
#include <atomic>
#include <cstdint>

#include "nfsmw_pch.h"

#include <rex/cvar.h>
#include <rex/logging.h>

REXCVAR_DEFINE_BOOL(nfsmw_game_pass_cadence, true, "GPU",  // dev208: on again (draw commands only)
                    "dev204/205: the car reflection and mirror update rates applied in the game (their draws "
                    "and resolves left out); false: only the native renderer leaves them out");

REXCVAR_DEFINE_INT32(nfsmw_diag_freeze_faces, 0, "GPU",
                     "Diagnostic (dev210): bit N set = environment cube face N never redrawn after the first few "
                     "(to find which face, if any, the rear-view mirror shows)");
REXCVAR_DEFINE_INT32(nfsmw_native_road_reflection_hz, 0, "GPU",
                     "dev212 (Wet road reflections option): updates per second of the wet road's reflection view "
                     "(15-60; 0 or at least the cap: every frame); never drawn while no road reads it");
REXCVAR_DEFINE_BOOL(nfsmw_diag_hide_view_fb90, false, "GPU",
                    "dev211 (default on): the 784x360 view the game draws before the cube faces (block "
                    "82463488..82463490, ~350 draws and 0.6 ms GPU a frame on the iPhone) drawn only the first "
                    "few times; Stefan's A/B runs (Nov 17) found nothing on screen that uses it");

namespace {
constexpr uint32_t kBeginMirror = 0x82463488, kEndMirror = 0x82463490;
constexpr uint32_t kBeginFace = 0x82463498, kEndFace = 0x824634A0;

double face_phase[6] = {0.0, 1.0 / 6, 2.0 / 6, 3.0 / 6, 4.0 / 6, 5.0 / 6};
double mirror_phase = 0.0;
uint32_t face_drawn[6] = {}, mirror_drawn = 0;
bool skipping = false;
bool in_road_view = false;  // dev212: the wet road view's block is being drawn
std::atomic<uint32_t> road_dest{0};      // its resolve's destination (guest address)
std::atomic<uint32_t> road_unread{1000}; // renderer frames since a draw last sampled it
bool resolve_off = false;   // dev205: the block's resolve left out (sub_8245D788)
bool clear_after = false;   // the block's end entry ran: back to normal at the next entry
uint32_t skipped_entries = 0;
uint64_t blocks_left_out = 0, blocks_seen = 0;

double Share(const char* rate_cvar) {
  const int32_t cap = std::max<int32_t>(rex::cvar::Query<int32_t>("ios_fps_cap"), 1);
  const int32_t hz = rex::cvar::Query<int32_t>(rate_cvar);
  return hz > 0 ? std::min(1.0, double(hz) / double(cap)) : 1.0;
}

// Advances a phase; true: draw this time.
bool Due(double& phase, double share) {
  phase += share;
  if (phase >= 1.0 - 1e-9) {
    phase -= 1.0;
    return true;
  }
  return false;
}

// The face of the block a begin entry opens: its end entry's data - 18.
int FaceOf(uint8_t* base, uint32_t entry) {
  for (int i = 0; i < 48 && entry; ++i) {
    const uint32_t size = REX_LOAD_U32(entry + 4);
    if (size < 8 || size > 0x10000) return -1;
    entry += size;
    const uint32_t fn = REX_LOAD_U32(entry);
    if (fn == kEndFace) {
      const int32_t view = int32_t(REX_LOAD_U32(entry + 8));
      return view >= 18 && view < 24 ? view - 18 : -1;
    }
    if (fn == kBeginFace || fn == kBeginMirror || fn == 0) return -1;
  }
  return -1;
}
}  // namespace

// dev205 (Stefan, dev204: shorter mirror draw distance, flickering objects
// in the mirror and on the reflections): leaving whole blocks out also left
// out the views' own setup (sub_824420B0 begin view, sub_82442CF0 its
// parameters, 33E8/3380) and the end entries' state stores, which later
// views read. Now only the draw lists (sub_82463338 -> sub_824549E8,
// sub_82463368 -> sub_8245BD58) and the end entry's resolve are left out;
// every other entry runs as the game queued it.
constexpr uint32_t kDrawList = 0x82463338, kDrawList2 = 0x82463368;

extern "C" bool nfsmw_pass_cadence_skip(uint8_t* base, uint32_t entry, uint32_t fn) {
  static const bool on = REXCVAR_GET(nfsmw_game_pass_cadence);
  if (!on) return false;
  if (clear_after) {
    clear_after = false;
    resolve_off = false;
  }
  if (in_road_view && (fn == kEndMirror || fn == kBeginFace)) in_road_view = false;
  if (skipping) {
    if (fn == kEndFace || fn == kEndMirror || ++skipped_entries > 48) {
      skipping = false;
      clear_after = true;  // its resolve (inside the end entry) stays off
      return false;        // the end entry's state stores run
    }
    // dev208 (dev204-206: mirror draw distance and flicker when the draw
    // lists were left out: they also hold the game's per-view work, e.g.
    // visibility and detail levels for the frames after): every entry
    // runs; only D3D's draw calls (native_draw_census.cpp) and the resolve
    // are dropped while the block runs.
    return false;
  }
  if (fn == kBeginMirror) {
    ++blocks_seen;
    // dev211: not the rear-view mirror (that is cube face 2, dev210 tests).
    // dev212 (Stefan: it is the wet road's reflection; dev211 froze it in
    // the rain): drawn at its own rate, and only while a draw of the last
    // few frames sampled its picture (the road in the rain).
    static const bool hide = REXCVAR_GET(nfsmw_diag_hide_view_fb90);
    const bool read = road_unread.load(std::memory_order_relaxed) < 8 || !road_dest.load(std::memory_order_relaxed);
    const bool due = !hide && read && Due(mirror_phase, Share("nfsmw_native_road_reflection_hz"));
    if (due || mirror_drawn < 3) in_road_view = true;
    // The first few always drawn: the renderer needs a kept picture.
    if (due || mirror_drawn < 3) {
      ++mirror_drawn;
      return false;
    }
    skipping = true;
    resolve_off = true;
    skipped_entries = 0;
    ++blocks_left_out;
    return false;  // its setup runs
  }
  if (fn == kBeginFace) {
    ++blocks_seen;
    const int face = FaceOf(base, entry);
    if (face < 0) return false;  // not the shape seen in races: drawn as it is
    static const int32_t frozen = REXCVAR_GET(nfsmw_diag_freeze_faces);
    // dev211 (Stefan's dev210 tests): face 2 is what the rear-view mirror
    // shows (also the matching part of the car's reflection): the mirror
    // option's rate; the other five the reflection option's.
    constexpr int kMirrorFace = 2;
    const bool due = !((frozen >> face) & 1) &&
                     Due(face_phase[face], Share(face == kMirrorFace ? "nfsmw_native_mirror_hz"
                                                                     : "nfsmw_native_reflection_hz"));
    if (due || face_drawn[face] < 3) {
      ++face_drawn[face];
      return false;
    }
    skipping = true;
    resolve_off = true;
    skipped_entries = 0;
    ++blocks_left_out;
    return false;  // its setup runs
  }
  if (blocks_seen >= 4200) {
    REXLOG_INFO("[pass-cadence] {} of {} reflection face and mirror passes left out in the game", blocks_left_out,
                blocks_seen);
    blocks_seen = blocks_left_out = 0;
  }
  return false;
}


// dev206: the resolve itself (D3D's Resolve, sub_82592340, in
// native_draw_census.cpp) asks this. dev205 skipped the game's wrapper
// sub_8245D788 instead; that also skipped the game's own bookkeeping, and a
// later resolve found a null destination (crash leaving the safehouse,
// Nov 17, twice).
extern "C" bool nfsmw_pass_cadence_resolve_off() { return resolve_off; }
// dev208: also the block's draw calls (DrawVertices, DrawIndexedVertices).
extern "C" bool nfsmw_pass_cadence_draws_off() { return resolve_off; }

// dev209 (Stefan: as much saving as possible): the game's shader constant
// commit (sub_82699100: copies the draw's dirty constants into the command
// buffer and marks them sent; the top function of the game's render thread,
// ~17 % of it in the Nov 16 profile) is left out too while a block's draws
// are dropped. The constants it would have sent belong to those dropped
// draws; their dirty bits stay set, so the next drawn view sends them.
extern "C" void __imp__sub_82699100(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_82699100) {
  if (resolve_off) return;
  __imp__sub_82699100(ctx, base);
}

// dev212: the wet road view's resolve (inside its block, sub_82592340):
// its destination texture's base address (fetch dword 1 at +20).
extern "C" void nfsmw_pass_cadence_note_resolve(uint8_t* base, uint32_t dest) {
  if (!in_road_view || !dest) return;
  const uint32_t address = REX_LOAD_U32(dest + 20) & 0xFFFFF000u;
  if (address && road_dest.exchange(address) != address)
    REXLOG_INFO("[pass-cadence] wet road reflection resolves to {:08X}", address);
}
// The renderer, once a frame: whether any draw sampled that picture.
extern "C" uint32_t nfsmw_pass_cadence_road_address() { return road_dest.load(std::memory_order_relaxed); }
extern "C" void nfsmw_pass_cadence_road_sampled(bool sampled) {
  static uint32_t frames = 0, read_frames = 0;
  if (sampled) road_unread.store(0, std::memory_order_relaxed);
  else road_unread.fetch_add(1, std::memory_order_relaxed);
  read_frames += sampled;
  if (++frames == 600) {
    REXLOG_INFO("[pass-cadence] wet road reflection read in {} of 600 frames", read_frames);
    frames = read_frames = 0;
  }
}
