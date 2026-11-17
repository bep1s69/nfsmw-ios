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

REXCVAR_DEFINE_BOOL(nfsmw_game_pass_cadence, false, "GPU",  // dev207: off (mirror draw distance, flicker)
                    "dev204/205: the car reflection and mirror update rates applied in the game (their draws "
                    "and resolves left out); false: only the native renderer leaves them out");

namespace {
constexpr uint32_t kBeginMirror = 0x82463488, kEndMirror = 0x82463490;
constexpr uint32_t kBeginFace = 0x82463498, kEndFace = 0x824634A0;

double face_phase[6] = {0.0, 1.0 / 6, 2.0 / 6, 3.0 / 6, 4.0 / 6, 5.0 / 6};
double mirror_phase = 0.0;
uint32_t face_drawn[6] = {}, mirror_drawn = 0;
bool skipping = false;
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
  if (skipping) {
    if (fn == kEndFace || fn == kEndMirror || ++skipped_entries > 48) {
      skipping = false;
      clear_after = true;  // its resolve (inside the end entry) stays off
      return false;        // the end entry's state stores run
    }
    return fn == kDrawList || fn == kDrawList2;
  }
  if (fn == kBeginMirror) {
    ++blocks_seen;
    const bool due = Due(mirror_phase, Share("nfsmw_native_mirror_hz"));
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
    const bool due = Due(face_phase[face], Share("nfsmw_native_reflection_hz"));
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
