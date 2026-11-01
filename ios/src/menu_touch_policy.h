#pragma once
#include <cmath>
#include <algorithm>
#include <cstdint>
#include <string_view>

namespace nfsmw::menu_touch {
constexpr int Left=1<<13, Right=1<<14, Up=1<<11, Down=1<<12;
constexpr int LT=1<<20, RT=1<<21;
// Internal response: select a popup choice, then wait for its focus frame.
constexpr int SelectChoice=1<<24, WaitForChoice=-2, SelectionDone=-3;
enum DragMode { NoDrag, MenuDrag, HorizontalDrag, VerticalDrag, MapDrag, CameraDrag };
// Lift slow touch motion above the controller's analog dead zone.
inline float CameraMotion(float delta,float full_scale=8.f,float minimum=.35f) {
  if (std::abs(delta)<.1f) return 0;
  return std::copysign(minimum+(1.f-minimum)*std::min(std::abs(delta)/full_scale,1.f),delta);
}
inline float ShowcasePan(float delta) { return -CameraMotion(delta,.5f,.95f); }
inline int BackAction(int fingers,bool enabled) { return fingers>=2&&enabled?2:0; }
constexpr uint32_t Hash(std::string_view name) {
  uint32_t h=0xffffffffu;
  for (char c:name) h=h*33+uint8_t(c);
  return h;
}
inline int Direction(float dx,float dy,bool invert) {
  if (std::hypot(dx,dy)<14) return 0;
  if (invert) { dx=-dx;dy=-dy; }
  return std::abs(dx)>=std::abs(dy) ? (dx>0?Right:Left) : (dy>0?Down:Up);
}
inline int TapAction(int matched,bool empty_accept) {
  return matched>0?matched:matched<0?0:empty_accept?1:0;
}
class DragRepeat {
 public:
  int Buttons(double now,int direction) {
    if (direction!=direction_) { direction_=direction;start_=now; }
    if (!direction_) return 0;
    const double elapsed=now-start_;
    // Neutral gaps create distinct presses even where the frontend does not
    // repeat a held stick. No catch-up burst after a delayed main-thread tick.
    return elapsed<.10 || (elapsed>=.35 && std::fmod(elapsed-.35,.16)<.08) ? direction_ : 0;
  }
  void Reset() { direction_=0;start_=0; }
 private:
  int direction_=0;
  double start_=0;
};
}  // namespace nfsmw::menu_touch
