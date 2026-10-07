// NFSMW Recompiled - what the game's renderer is doing (USA build), for 4:3
//
// A thread that, every half second, logs the renderer's anti-aliasing mode and
// the game's render size when they change, and the mode table once. Only reads
// guest memory. Started from game_app.cpp (weak, like the Extra Options).
//
// Why: at 4:3 the largest resolve was exactly 640x480 (the [ios-readback]
// lines), so the game seems to take its SD path (mode 0, one 640x480 strip)
// even at 1024x768, and the single-pass hook, which forced the HD mode 2, gave
// a scrambled picture. This confirms which mode and size the game really uses.
//
// USA addresses (the renderer's constructor is sub_824581A8, XGetVideoMode's
// caller sub_82440188):
//   0x82A2D1AC  pointer to the renderer; its +0 is the current mode, the
//               table as in render_targets.cpp (+4 strips, +28 width, +52
//               height, +76 MSAA, +100+64*mode the strip rectangles)
//   0x82A2CF68.. four words sub_82440188 sets to the render size
//               (1280/720 for HD, 1024/576 for HD narrower than 1280)

#include <atomic>
#include <chrono>
#include <cstdint>
#include <thread>

#include <rex/logging.h>
#include <rex/system/kernel_state.h>
#include <rex/system/xmemory.h>

namespace {

constexpr uint32_t kRenderer = 0x82A2D1AC;
constexpr uint32_t kRenderSize = 0x82A2CF68;

uint32_t Read32(rex::memory::Memory* memory, uint32_t address) {
  const auto* p = memory->TranslateVirtual<const uint8_t*>(address);
  return uint32_t(p[0]) << 24 | uint32_t(p[1]) << 16 | uint32_t(p[2]) << 8 | p[3];
}

void ProbeMain() {
  auto* memory = rex::system::kernel_state()->memory();
  uint32_t last[6] = {~0u, ~0u, ~0u, ~0u, ~0u, ~0u};
  bool table_said = false;
  for (;;) {
    std::this_thread::sleep_for(std::chrono::milliseconds(500));
    const uint32_t obj = Read32(memory, kRenderer);
    const uint32_t now[6] = {obj, obj ? Read32(memory, obj) : ~0u, Read32(memory, kRenderSize),
                             Read32(memory, kRenderSize + 4), Read32(memory, kRenderSize + 8),
                             Read32(memory, kRenderSize + 12)};
    if (obj && !table_said) {
      table_said = true;
      for (uint32_t m = 0; m < 6; ++m) {
        const uint32_t r = obj + 100 + 64 * m;
        REXLOG_INFO("[render-probe] mode {}: {} strip(s) {}x{} MSAA {}; rects {},{},{},{} / "
                    "{},{},{},{}",
                    m, Read32(memory, obj + 4 + 4 * m), Read32(memory, obj + 28 + 4 * m),
                    Read32(memory, obj + 52 + 4 * m), Read32(memory, obj + 76 + 4 * m),
                    Read32(memory, r), Read32(memory, r + 4), Read32(memory, r + 8),
                    Read32(memory, r + 12), Read32(memory, r + 16), Read32(memory, r + 20),
                    Read32(memory, r + 24), Read32(memory, r + 28));
      }
    }
    bool changed = false;
    for (int i = 0; i < 6; ++i) {
      changed |= now[i] != last[i];
      last[i] = now[i];
    }
    if (changed) {
      REXLOG_INFO("[render-probe] mode {}, render size words {} {} {} {}",
                  int32_t(now[1]), now[2], now[3], now[4], now[5]);
    }
  }
}

}  // namespace

extern "C" void nfsmw_render_probe_start() {
  static std::atomic<bool> started{false};
  if (!started.exchange(true)) {
    std::thread(ProbeMain).detach();
  }
}
