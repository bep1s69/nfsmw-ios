// NFSMW Recompiled (iOS) - keyboard keys that follow the game's context
//
// The SDK's keyboard driver (rex/input/mnk, mnk_mode) presses the
// controller's inputs from the keybind_* cvars, which it reads on every poll.
// One set for everything made Return both Accept and the handbrake (Stefan,
// November 1). The launcher now passes two sets: the driving one as the
// keybind_* cvars themselves, the menu one in nfsmw_menu_keybinds
// ("keybind_a=Return,Space;keybind_b=Escape,Backspace;..."). When a menu
// comes up or goes (game_state.cpp, the same change battery::SetInMenu gets)
// the keybind_* strings are set to the other set.
//
// A key held across the switch would press its other meaning (Escape opens
// the pause menu, where Escape is Back: it would close it again). So the
// switch waits until no key is down (keyboard_prompts.mm polls that), with
// no keys bound meanwhile.
//
// The driver reads those strings on its own thread while they change here.
// Each one gets 256 bytes reserved first and values are cut to fit, so an
// assignment never moves the string's buffer: a poll at that moment can see
// a half-written list for one frame, never freed memory.

#include <array>
#include <atomic>
#include <string>
#include <string_view>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "keyboard_context.h"

REXCVAR_DECLARE(bool, mnk_mode);
REXCVAR_DEFINE_STRING(nfsmw_menu_keybinds, "", "Input",
                      "The keys in menus: keybind_<input>=<keys>;... (the launcher's Menus list); "
                      "empty: the driving keys everywhere");

#define NFSMW_BINDS(X)                                                                          \
  X(keybind_a) X(keybind_b) X(keybind_x) X(keybind_y) X(keybind_left_trigger)                  \
  X(keybind_right_trigger) X(keybind_left_shoulder) X(keybind_right_shoulder)                  \
  X(keybind_lstick_up) X(keybind_lstick_down) X(keybind_lstick_left) X(keybind_lstick_right)   \
  X(keybind_lstick_press) X(keybind_rstick_up) X(keybind_rstick_down) X(keybind_rstick_left)   \
  X(keybind_rstick_right) X(keybind_rstick_press) X(keybind_dpad_up) X(keybind_dpad_down)      \
  X(keybind_dpad_left) X(keybind_dpad_right) X(keybind_back) X(keybind_start) X(keybind_guide)

#define NFSMW_DECLARE(name) REXCVAR_DECLARE(std::string, name);
NFSMW_BINDS(NFSMW_DECLARE)
#undef NFSMW_DECLARE

namespace nfsmw::keyboard {
namespace {

struct Bind {
  const char* name;
  std::string& (*storage)();
  std::string driving, menu;
};

#define NFSMW_ENTRY(name) Bind{#name, &FLAGS_##name##_storage_, {}, {}},
std::array binds = {NFSMW_BINDS(NFSMW_ENTRY)};
#undef NFSMW_ENTRY

constexpr size_t kCapacity = 256;
bool ready = false;
bool have_menu_set = false;
int context = -1;  // 0 driving, 1 menus (what the strings hold)
int wanted_context = -1;
bool blanked = false;
std::atomic<bool> any_key_down{false};

void Prepare() {
  ready = true;
  for (Bind& b : binds) {
    std::string& s = b.storage();
    b.driving = s.substr(0, kCapacity - 1);
    b.menu = b.driving;
    s.reserve(kCapacity);
  }
  std::string_view list = REXCVAR_GET(nfsmw_menu_keybinds);
  while (!list.empty()) {
    const size_t end = list.find(';');
    const std::string_view item = list.substr(0, end);
    list = end == std::string_view::npos ? std::string_view() : list.substr(end + 1);
    const size_t eq = item.find('=');
    if (eq == std::string_view::npos) continue;
    for (Bind& b : binds) {
      if (item.substr(0, eq) == b.name) {
        b.menu = std::string(item.substr(eq + 1, kCapacity - 1));
        have_menu_set = true;
      }
    }
  }
  REXLOG_INFO("[keyboard] {} keys (menu list {} characters)", have_menu_set ? "menu and driving" : "one set of",
              REXCVAR_GET(nfsmw_menu_keybinds).size());
}

}  // namespace

void SetMenu(bool menu) {
  if (!REXCVAR_GET(mnk_mode)) return;
  if (!ready) Prepare();
  if (!have_menu_set) return;
  wanted_context = int(menu);
  Service();
}

void Service() {
  if (!ready || !have_menu_set || wanted_context < 0 || context == wanted_context) return;
  if (context >= 0 && any_key_down.load(std::memory_order_relaxed)) {
    if (!blanked) {
      REXLOG_INFO("[keyboard] switch waits for the keys to be released");
      for (Bind& b : binds) b.storage().clear();
      blanked = true;
    }
    return;
  }
  context = wanted_context;
  blanked = false;
  for (Bind& b : binds) b.storage().assign(context ? b.menu : b.driving);
  REXLOG_INFO("[keyboard] {} keys", context ? "menu" : "driving");
  static int detail = 6;  // the lists themselves, the first few switches
  if (detail-- > 0) {
    for (const Bind& b : binds) REXLOG_INFO("[keyboard]   {} = {}", b.name, b.storage());
  }
}

void SetAnyKeyDown(bool down) { any_key_down.store(down, std::memory_order_relaxed); }

std::string MenuKey(const char* bind) {
  for (const Bind& b : binds) {
    if (std::string_view(b.name) != bind) continue;
    const std::string& keys = ready ? b.menu : b.storage();
    return keys.substr(0, keys.find(','));
  }
  return {};
}

}  // namespace nfsmw::keyboard
