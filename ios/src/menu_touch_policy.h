#pragma once
#include <cmath>
#include <cstdint>
#include <string_view>

namespace nfsmw::menu_touch {
constexpr int Left=1<<13, Right=1<<14, Up=1<<11, Down=1<<12;
constexpr int LT=1<<20, RT=1<<21;
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
