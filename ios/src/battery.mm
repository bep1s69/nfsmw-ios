// NFSMW Recompiled - frame rate and resolution by the game's state and the
// phone's heat (iOS)
//
// All three are at the launcher's 60 fps cap only (40 and 120 change the
// console's screen refresh, which is not switched while playing):
//   - 30 fps while Low Power Mode is on or the phone is warm (thermal state
//     fair or above), 60 again once it is off and the phone is cool
//     (nominal): cvar nfsmw_battery_auto_cap;
//   - 30 fps in menus and pause screens, which redraw much the same picture
//     (game_state.cpp says when): nfsmw_menu_cap;
//   - native renderer, at any cap: 0.75x render resolution from the thermal
//     state "serious" until it is back to fair or below (at least a minute
//     later, so it does not flap), then the resolution chosen:
//     nfsmw_heat_scale. nfsmw_heat_scale_test pretends "serious" for 30 s of
//     every minute, to see the switch without heating the phone.
// The cap is the runtime's cvar ios_fps_cap, which its frame pacing reads
// every frame. Every change is logged ("[battery]").

#import <Foundation/Foundation.h>

#include "battery.h"

#include <atomic>
#include <chrono>
#include <mutex>
#include <string>
#include <thread>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "display_rate.h"
#include "memory_report.h"

REXCVAR_DEFINE_BOOL(nfsmw_battery_auto_cap, false, "Battery",
                    "At the 60 fps cap: 30 while Low Power Mode is on or the phone is warm (thermal state "
                    "fair or above), 60 again once it is off and cool");
REXCVAR_DEFINE_BOOL(nfsmw_menu_cap, false, "Battery",
                    "At the 60 fps cap: 30 in menus and pause screens, 60 while driving");
REXCVAR_DEFINE_BOOL(nfsmw_heat_scale, false, "Battery",
                    "Native renderer: 0.75x render resolution while the phone is hot (thermal state serious), "
                    "the chosen one again once it is back to fair");
REXCVAR_DEFINE_BOOL(nfsmw_heat_scale_test, false, "Battery",
                    "Diagnostics: nfsmw_heat_scale acts as if the phone were hot for 30 s of every minute");

namespace nfsmw::battery {

namespace {

constexpr float kHotScale = 0.75f;

std::atomic<int> in_menu{-1};
std::atomic<float> heat_scale{0.0f};

std::mutex cap_mutex;
bool controlled = false;  // the launcher's cap is 60
bool warm = false;        // Low Power Mode, or thermal state fair and above (with the way back at nominal)
bool menu = false;
int cap = 60;

// The cap for the current state (cap_mutex held), set and logged if new.
void UpdateCap(const char* why) {
  if (!controlled) return;
  const bool auto_cap = REXCVAR_GET(nfsmw_battery_auto_cap) && warm;
  const bool menu_cap = REXCVAR_GET(nfsmw_menu_cap) && menu;
  const int want = auto_cap || menu_cap ? 30 : 60;
  if (want == cap) return;
  cap = want;
  rex::cvar::SetFlagByName("ios_fps_cap", std::to_string(cap));
  REXLOG_INFO("[battery] cap {} fps: {}", cap, why);
  if (nfsmw::display::MatchesCap()) {
    const int now = cap;
    dispatch_async(dispatch_get_main_queue(), ^{
      nfsmw::display::RequestRateForCap(now);
    });
  }
}

}  // namespace

void SetInMenu(bool now) {
  const int v = now ? 1 : 0;
  if (in_menu.exchange(v) == v) return;
  std::lock_guard<std::mutex> lock(cap_mutex);
  menu = now;
  UpdateCap(now ? "menu" : "driving");
}

int InMenu() { return in_menu.load(std::memory_order_relaxed); }

float HeatScale() { return heat_scale.load(std::memory_order_relaxed); }

void Start() {
  const bool auto_cap = REXCVAR_GET(nfsmw_battery_auto_cap);
  const bool hot_scale = REXCVAR_GET(nfsmw_heat_scale);
  {
    std::lock_guard<std::mutex> lock(cap_mutex);
    controlled = rex::cvar::GetFlagByName("ios_fps_cap") == "60";
  }
  REXLOG_INFO("[battery] 30 fps when warm {}, 30 fps in menus {}, 0.75x when hot {}{}",
              auto_cap ? "on" : "off", REXCVAR_GET(nfsmw_menu_cap) ? "on" : "off", hot_scale ? "on" : "off",
              controlled ? "" : " (the caps only at the 60 fps cap)");
  if (!auto_cap && !hot_scale) return;
  std::thread([auto_cap, hot_scale] {
    pthread_setname_np("nfsmw battery");
    using Clock = std::chrono::steady_clock;
    const auto start = Clock::now();
    auto scaled_at = start;
    bool scaled = false;
    for (;;) {
      std::this_thread::sleep_for(std::chrono::seconds(2));
      NSProcessInfo* info = [NSProcessInfo processInfo];
      const bool low_power = info.lowPowerModeEnabled;
      const NSProcessInfoThermalState thermal = info.thermalState;
      if (auto_cap) {
        std::lock_guard<std::mutex> lock(cap_mutex);
        // Back to 60 only once it is cool again (fair keeps 30): no flapping.
        const bool now = low_power || thermal >= NSProcessInfoThermalStateFair ? true
                         : thermal == NSProcessInfoThermalStateNominal     ? false
                                                                            : warm;
        if (now != warm) {
          warm = now;
          REXLOG_INFO("[battery] Low Power Mode {}, thermal state {}", low_power ? "on" : "off",
                      memory::ThermalState());
          UpdateCap(now ? "warm or Low Power Mode" : "cool, Low Power Mode off");
        }
      }
      if (hot_scale) {
        const auto now = Clock::now();
        const bool test = REXCVAR_GET(nfsmw_heat_scale_test);
        const bool test_hot =
            test && std::chrono::duration_cast<std::chrono::seconds>(now - start).count() % 60 >= 30;
        const bool hot = test ? test_hot : thermal >= NSProcessInfoThermalStateSerious;
        const bool cool = test ? !test_hot : thermal <= NSProcessInfoThermalStateFair;
        // Back only after a minute at 0.75x (the test switches every 30 s).
        const bool held = test || now - scaled_at >= std::chrono::seconds(60);
        if (!scaled && hot) {
          scaled = true;
          scaled_at = now;
          heat_scale = kHotScale;
          REXLOG_INFO("[battery] render resolution {:.2f}x: thermal state {}{}", kHotScale, memory::ThermalState(),
                      test ? " (test)" : "");
        } else if (scaled && cool && held) {
          scaled = false;
          heat_scale = 0.0f;
          REXLOG_INFO("[battery] render resolution as chosen again: thermal state {}{}", memory::ThermalState(),
                      test ? " (test)" : "");
        }
      }
    }
  }).detach();
}

}  // namespace nfsmw::battery
