// NFSMW Recompiled (iOS) - external display decisions, as plain C++
//
// Which pixels the picture on an external display (USB-C, HDMI adapter,
// AirPlay) gets, which shape the game starts in, and when the resolution goes
// back to the phone's after the display has gone. No UIKit here, so that
// tools/native/test_external_display_policy.py checks every case on the Mac;
// external_display.mm and native_renderer.mm carry the decisions out.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>

namespace nfsmw::external_display {

struct Pixels {
  uint32_t w = 0, h = 0;
  bool operator==(const Pixels& o) const { return w == o.w && h == o.h; }
};

// The long side across: the game is landscape on every screen.
inline Pixels Landscape(double w, double h) {
  const double a = std::max(w, h), b = std::min(w, h);
  return {uint32_t(std::max(0L, std::lround(a))), uint32_t(std::max(0L, std::lround(b)))};
}

// The most pixels across the display's picture gets. "1080p" (the default)
// keeps a 4K display at 1920 across: a 4K drawable costs about four times the
// GPU time for a 720p-1440p game picture and has come out black over AirPlay.
// "display" is the display's own pixels. Unknown values: the default.
constexpr uint32_t kDefaultMaxWidth = 1920;
inline uint32_t MaxWidthFor(const std::string& setting) {
  if (setting == "display" || setting == "0") return 0;
  if (setting == "1440p" || setting == "2560") return 2560;
  if (setting == "720p" || setting == "1280") return 1280;
  return kDefaultMaxWidth;
}

// A display of w x h pixels (either orientation) with its picture at most
// max_width across (0: no cap): landscape, its own shape, scaled down to the
// cap, even sizes (video encoders and the compositor prefer them).
inline Pixels CappedPixels(double w, double h, uint32_t max_width) {
  Pixels p = Landscape(w, h);
  if (!p.w || !p.h) return {};
  if (max_width && p.w > max_width) {
    const double k = double(max_width) / double(p.w);
    p = {max_width, uint32_t(std::max(2L, std::lround(double(p.h) * k / 2.0) * 2))};
  }
  return p;
}

// The game's picture shapes (settings_catalog.mm "aspect"): the Xbox 360's
// 16:9, its 4:3 mode, or a wider scene of the screen's own shape.
enum class Shape { k16x9, k4x3, kWide };

// "Fit this screen": the shape closest to a screen's. Wider than 16:9 (by more
// than 0.02): a wide scene; else 16:9 or the game's 4:3 mode, the only
// narrower one it has. The device's own screen keeps its 0.6.0 rule (4:3
// below 1.6: an iPad's 1.43, both panels of an iPhone Duo). An external
// display goes 4:3 only below 1.5: a MacBook over AirPlay (3381x2160,
// 1.565), a 16:10 monitor (1.6) and 3:2 (1.5) get 16:9 with thin bars above
// and below, which loses less of the display than 4:3's bars at the sides.
constexpr double kDeviceFourThreeBelow = 1.6;
constexpr double kExternalFourThreeBelow = 1.5;
inline Shape ShapeFor(double w, double h, bool external = false) {
  const Pixels p = Landscape(w, h);
  if (!p.w || !p.h) return Shape::k16x9;
  const double r = double(p.w) / double(p.h);
  if (r > 16.0 / 9.0 + 0.02) return Shape::kWide;
  return r < (external ? kExternalFourThreeBelow : kDeviceFourThreeBelow) ? Shape::k4x3 : Shape::k16x9;
}

inline const char* ShapeName(Shape s) {
  return s == Shape::kWide ? "wide" : s == Shape::k4x3 ? "4:3" : "16:9";
}

// A wide scene: as wide as the screen's shape at 720 high, in steps of 8
// (1568 on a 2868x1320 iPhone, 1704 on a 2560x1080 monitor).
inline int WideSceneWidth(double w, double h) {
  const Pixels p = Landscape(w, h);
  if (!p.w || !p.h) return 1280;
  const int width = int(std::lround(720.0 * double(p.w) / double(p.h) / 8.0)) * 8;
  return std::clamp(width, 1288, 2400);
}

// The picture of aspect `aspect` (width / height) fitted into w x h pixels,
// centred, bars where the shapes differ (never stretched).
struct Rect {
  double x = 0, y = 0, w = 0, h = 0;
};
inline Rect AspectFit(double aspect, double w, double h) {
  if (!(aspect > 0) || !(w > 0) || !(h > 0)) return {0, 0, std::max(w, 0.0), std::max(h, 0.0)};
  const double dst = w / h;
  const double pw = aspect > dst ? w : std::round(h * aspect);
  const double ph = aspect > dst ? std::round(w / aspect) : h;
  return {std::floor((w - pw) * 0.5), std::floor((h - ph) * 0.5), pw, ph};
}

// Where the picture goes and whose pixels the game's resolution follows.
//
// The picture moves at once: to the display when its scene connects, back to
// the phone when it disconnects. The resolution (the "native" render scale)
// follows the display from its connection, but goes back to the phone's only
// when the app is active and the display has stayed away kGraceSeconds: iOS
// takes the display's scene away whenever the app leaves the foreground and
// gives it back on return, and a display that changes its mode disconnects
// and connects again. Without the grace, each of those would make the game
// rebuild its render targets twice. Times are seconds on any one clock.
class Router {
 public:
  static constexpr double kGraceSeconds = 2.0;

  void Connect(double now) {
    (void)now;
    connected_ = true;
    sizing_external_ = true;
    away_since_ = -1.0;
  }

  void Disconnect(double now) {
    if (!connected_) return;
    connected_ = false;
    away_since_ = now;
  }

  // The app's scene became active (true) or stopped being active (false).
  // Becoming active restarts the grace: the display's scene comes back a
  // moment after the app does.
  void SetActive(bool active, double now) {
    active_ = active;
    if (active && !connected_ && sizing_external_) away_since_ = std::max(away_since_, now);
  }

  // Whether the resolution goes back to the phone's now: true once, when it does.
  bool Settle(double now) {
    if (connected_ || !sizing_external_ || !active_ || away_since_ < 0) return false;
    if (now - away_since_ + 1e-9 < kGraceSeconds) return false;
    sizing_external_ = false;
    away_since_ = -1.0;
    return true;
  }

  // Seconds until Settle should be asked again; negative: not needed (the
  // display is there, the resolution is the phone's already, or the app is
  // not active, when the next SetActive(true) decides).
  double SettleIn(double now) const {
    if (connected_ || !sizing_external_ || !active_ || away_since_ < 0) return -1.0;
    return std::max(0.0, kGraceSeconds - (now - away_since_));
  }

  bool connected() const { return connected_; }              // the picture is on the display
  bool sizing_external() const { return sizing_external_; }  // the resolution follows the display
  bool active() const { return active_; }

 private:
  bool connected_ = false;
  bool sizing_external_ = false;
  bool active_ = true;
  double away_since_ = -1.0;
};

}  // namespace nfsmw::external_display
