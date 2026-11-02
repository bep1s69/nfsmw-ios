// Guest rasterizer state for the opt-in culling trial. No Metal dependency:
// the same decision and cache are exercised by the host regression check.
#pragma once

#include <cmath>
#include <cstdint>

namespace nfsmw {
enum class GuestCullMode : uint8_t { None, Front, Back, Both };
enum class GuestCullReason : uint8_t { Eligible, TwoSided, Primitive, Internal, Query, Viewport, Count };

struct GuestCullPlan {
  GuestCullMode mode = GuestCullMode::None;
  bool clockwise = true;  // Metal's legacy/default front-facing orientation
  GuestCullReason reason = GuestCullReason::TwoSided;
};

inline GuestCullPlan PlanGuestCulling(uint32_t raster, uint32_t primitive, uint32_t vte,
                                     const float* viewport, bool internal, bool query,
                                     bool special_viewport) {
  GuestCullPlan p;
  const auto requested = GuestCullMode(raster & 3);
  if (requested == GuestCullMode::None) return p;
  // Original Xenos types, NOT the expanded Metal topology. In particular,
  // rectangle lists (8) become triangles but do not use polygon culling.
  if (primitive != 4 && primitive != 5 && primitive != 6 && primitive != 13) {
    p.reason = GuestCullReason::Primitive;
  } else if (internal) {
    p.reason = GuestCullReason::Internal;
  } else if (query) {
    p.reason = GuestCullReason::Query;
  } else if (special_viewport || (vte & 15) != 15 ||
             !std::isfinite(viewport[0]) || !std::isfinite(viewport[1]) ||
             !std::isfinite(viewport[2]) || !std::isfinite(viewport[3]) ||
             !(viewport[0] > 0) || !(viewport[2] < 0)) {
    // Native uses abs scales; in this supported convention its window x/y
    // equal guest (sx*x+ox, sy*y+oy). No orientation adjustment is needed.
    p.reason = GuestCullReason::Viewport;
  } else {
    p.mode = requested;
    p.clockwise = (raster & 4) != 0;  // PA_SU_SC_MODE_CNTL.face: 0 CCW, 1 CW
    p.reason = GuestCullReason::Eligible;
  }
  return p;
}

struct GuestCullCache {
  bool valid = false;
  GuestCullMode mode = GuestCullMode::None;
  bool clockwise = true;
  bool Update(const GuestCullPlan& p) {
    if (valid && mode == p.mode && clockwise == p.clockwise) return false;
    valid = true;
    mode = p.mode;
    clockwise = p.clockwise;
    return true;
  }
};
}  // namespace nfsmw
