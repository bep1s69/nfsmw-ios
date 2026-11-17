// Adaptive QoS (--ios_adaptive_qos, default false): the game's main thread and
// the GPU command thread at Utility QoS (efficiency cores, cheaper clocks) while
// frames arrive on time, back to User Initiated as soon as they do not.
//
// Utility QoS for those two threads cut the iPad Pro M4's estimated drain by a
// quarter at 1.5x / 60 (docs/TECHNICAL.md, October 21), but an iPhone 17 Pro
// (4 efficiency cores) could not hold 60 that way. Here the GPU command thread
// watches the time between swaps: 2 late frames (over 1.2x the cap's interval)
// in the last 120 switch both threads to User Initiated for a hold time, then they
// try Utility again. A retry that fails within 10 s doubles the hold (20 s up to
// 240 s); 60 s on Utility resets it. Each thread can only set its own QoS: the
// command thread at its swap (NativeSwap), the main thread in the game's
// deferred-call runner (sub_823C8290, called from its main loop).
//
// --ios_adaptive_qos_workers (default true): User Initiated also covers the other
// guest threads (Utility through --ios_utility_qos_guest) and the native render
// queue. The October 24 pursuit trace (docs/TECHNICAL.md) had main on the
// performance cores waiting on a guest worker left at Utility on the efficiency
// cores and preempted most of each 80 ms gap. Those threads cannot be asked to
// set their own QoS, so the command thread starts an override on each one
// (pthread_override_qos_class_start_np) and ends it on the way back to Utility.
//
// Since 0.4.3 (Performance "Balanced", the default; docs/TECHNICAL.md, Oct 29):
// while driving (in the world, no menu up: game_state.cpp) the threads stay
// boosted, never at Utility: a GitHub tester's iPhone 17 Pro Max went from 60
// to a flat 40 fps the moment it went back to Utility in the world, and the
// old late test (2 of 120 frames over 1.2x the cap's interval) did not see a
// steady 40 for 36 s. Outside driving a frame is late when its swap interval
// is over 1.1x the cap's budget or the renderer took longer than the budget
// to encode it (OnRendered), and 3 late frames in the last 60 (about 1 s)
// boost. Performance "Max" (ios_main.mm) turns all Utility QoS off instead;
// "Eco" (the default with Battery mode) keeps them all at Utility, no boost.
// Balanced with 6+ efficiency cores (nfsmw_adaptive_qos_original) keeps the
// original rules here, as it keeps the main/GPU threads' fixed Utility.
//
// The boost is tunable: --ios_adaptive_qos_level (user_initiated or default),
// the longest hold --ios_adaptive_qos_max_hold (seconds) and
// --ios_adaptive_qos_workers_count (the busiest guest threads by CPU time; 0
// raises all of them). The defaults are IPA48's (user_initiated, 240 s, all),
// the boost proven in pursuits; IPA49's Default / 20 s / 3 saved no battery on
// the iPhone (docs/TECHNICAL.md, October 24). --ios_adaptive_qos_ipa48=true
// forces the IPA48 values over Extra Args.

#include <pthread.h>
#include <dlfcn.h>
#include <mutex>
#include "performance_profile.h"
#include <pthread/qos.h>
#include <mach/mach.h>
#include <CoreFoundation/CoreFoundation.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <string>
#include <utility>
#include <vector>

#include <rex/cvar.h>
#include <rex/system/xthread.h>

#include "nfsmw_pch.h"

REXCVAR_DEFINE_BOOL(ios_adaptive_qos, false, "Kernel",
                    "Experiment: main and GPU command threads at Utility QoS while frames are on time "
                    "(restart required)");
REXCVAR_DEFINE_BOOL(ios_adaptive_qos_workers, true, "Kernel",
                    "Adaptive QoS: User Initiated also raises the other guest threads and the "
                    "native render queue (restart required)");
REXCVAR_DEFINE_STRING(ios_adaptive_qos_level, "user_initiated", "Kernel",
                      "Adaptive QoS: the class of a boost, default or user_initiated (restart required)");
REXCVAR_DEFINE_INT32(ios_adaptive_qos_max_hold, 240, "Kernel",
                     "Adaptive QoS: longest boost in seconds; IPA49 tried 20 (restart required)");
REXCVAR_DEFINE_INT32(ios_adaptive_qos_workers_count, 0, "Kernel",
                     "Adaptive QoS: how many guest threads a boost raises, busiest first by CPU time; "
                     "0 raises all (restart required)");
REXCVAR_DEFINE_STRING(nfsmw_performance_mode, "balanced", "Kernel",
                      "eco: game and render threads always at Utility QoS; balanced: Utility only outside "
                      "driving (adaptive); max: no Utility QoS for any game or render thread (live)");
REXCVAR_DEFINE_BOOL(nfsmw_adaptive_qos_original, false, "Kernel",
                    "Adaptive QoS with the rules before 0.4.3 (2 of 120 frames over 1.2x, no driving boost); "
                    "Balanced on devices with 6+ efficiency cores (restart required)");
REXCVAR_DEFINE_STRING(nfsmw_performance_source, "default", "Kernel",
                      "Why that Performance mode (launcher): setting, battery_mode or default");
REXCVAR_DEFINE_BOOL(ios_background_qos, false, "Kernel",
                    "Battery trial (Nov 4): the threads Balanced/Eco put at Utility run at "
                    "Background QoS instead (lower efficiency-core clocks, like Low Power Mode "
                    "showed; restart required)");
REXCVAR_DEFINE_BOOL(ios_background_qos_low_workers, false, "Kernel",  // live policy flag since dev73 (Eco at 30/40)
                    "Battery trial (Nov 5): when the frame threads are at Background, guest "
                    "workers at normal or lower guest priority go too; raised-priority guest "
                    "threads (audio is expected there) and host threads keep Utility");
REXCVAR_DEFINE_BOOL(ios_background_qos_workers, false, "Kernel",
                    "Battery trial (Nov 4): only the guest workers and render-queue blocks at "
                    "Background QoS; the frame threads keep Utility (restart required)");
REXCVAR_DEFINE_STRING(ios_boost_threads, "both", "Kernel",
                      "Adaptive QoS: which frame thread a driving boost raises: both, gpu (GPU "
                      "Commands), main (Main XThread) or none (Nov 4 battery trial; restart required)");
REXCVAR_DEFINE_BOOL(nfsmw_low_background, false, "Kernel",
                    "Cap controller: its lowest level is Background QoS (the efficiency cores only) for the frame "
                    "threads and guest workers, at every cap (dev179; before: Utility above 30)");
REXCVAR_DEFINE_BOOL(nfsmw_ipad_tolerant_low, true, "Kernel",
                    "Cap controller: on iPads with 6+ efficiency cores at caps up to 60, Low (efficiency cores) "
                    "steps up only when a fifth of the last 60 frames were late, as at 30/40");
REXCVAR_DEFINE_BOOL(nfsmw_drive_step_down, true, "Kernel",
                    "Cap controller: while driving, one level down after a calm stretch (15 s on 6+ efficiency-core "
                    "iPads, 30 s on phones); back up and kept for the drive if late again within 10 s");
REXCVAR_DEFINE_BOOL(nfsmw_qos_learn, true, "Kernel",
                    "Cap controller: each device learns its driving start level per frame rate cap (kept between "
                    "sessions): up after a drive that needed a higher level, one down after a long drive that did not");
REXCVAR_DEFINE_BOOL(nfsmw_cap_controller, true, "Kernel",
                    "dev108/dev109 (Nov 9): hold the FPS cap with the least power instead of the Eco/Balanced/Max "
                    "profiles: frame threads step Low -> Default -> User Initiated only while frames are late, "
                    "stepping down only outside driving (dev109); false restores the profiles (restart required)");
REXCVAR_DEFINE_BOOL(nfsmw_phone_tolerant_low, false, "Kernel",
                    "dev217 test: phones too accept isolated late frames on Low while driving at caps <= 60 "
                    "(step up on 12 late of 60 instead of 3)");
REXCVAR_DEFINE_INT32(nfsmw_start_level, -1, "Kernel",
                     "dev199 test: the cap controller's measured start level while driving: -1 per device and cap "
                     "(default), 0 Low (efficiency cores), 1 Default, 2 User Initiated");
REXCVAR_DEFINE_BOOL(nfsmw_audio_thread_low, false, "Kernel",
                    "dev111 (Nov 10; off since: no saving in the iPhone A/B): with the cap controller the game's audio thread (sub_825E3F40: mixing "
                    "and XMA decode) stays at Utility instead of following the frame threads' boost "
                    "(restart required)");
REXCVAR_DEFINE_BOOL(nfsmw_render_utility_trial, true,  // dev131 default (Nov 16 pair: -19% drain)
                    "Kernel",
                    "Scheduling trial: during cap-controller boosts above 40 FPS, keep native Metal encoding at Utility QoS; "
                    "game and audio threads keep their existing policy. Requires native render Utility enabled (restart required)");
// dev130 (Stefan, Nov 16): ignore late frames for this long after each drive
// starts. dev129's power pair showed world-entry hitches (texture decoding,
// 231 ms frames) raising the controller to User Initiated 30 ms into a drive,
// where it then stayed. 0 restores the dev129 behaviour.
REXCVAR_DEFINE_INT32(nfsmw_drive_start_grace_ms, 2000, "Kernel",
                     "Cap controller: ms after a drive starts in which late frames are not counted (0 = off)");
// dev131 variant (Stefan, Nov 16): where a drive would start at Default, start
// it (and hold it) at User Initiated instead. dev130's trial-on run drained
// least after stepping up to User Initiated (26.7 vs 35.3 %/h at Default).
REXCVAR_DEFINE_BOOL(nfsmw_drive_start_user_initiated, false, "Kernel",
                    "Cap controller variant: drives that start at Default start and stay at User Initiated (restart required)");
REXCVAR_DEFINE_BOOL(ios_adaptive_qos_ipa48, false, "Kernel",
                    "Adaptive QoS: the IPA48 boost (user_initiated, 240 s, all guest threads); "
                    "overrides the three settings above (restart required)");

namespace {

std::atomic<int> mode{-1};  // 0 Utility, 1 boosted (cap controller: 1 Default, 2 User Initiated)
std::atomic<bool> driving{false};       // game_state.cpp
std::atomic<int> render_late{0};
// dev111: the game's audio thread (marked when it enters sub_825E3F40).
std::atomic<uint64_t> audio_thread_id{0};
thread_local bool is_audio_thread = false;        // frames the renderer took over the budget to encode
using Clock = std::chrono::steady_clock;

struct Boost {
  qos_class_t qos;
  const char* name;
  double max_hold_s;
  int workers;  // 0: all
};

const Boost& Settings() {
  static const Boost boost = [] {
    if (REXCVAR_GET(ios_adaptive_qos_ipa48)) return Boost{QOS_CLASS_USER_INITIATED, "User Initiated", 240.0, 0};
    const bool user_initiated = REXCVAR_GET(ios_adaptive_qos_level) == "user_initiated";
    // "utility" (Nov 4 trial): with Background as the low class, a late-frame
    // boost back to Utility only.
    const bool utility = REXCVAR_GET(ios_adaptive_qos_level) == "utility";
    return Boost{user_initiated ? QOS_CLASS_USER_INITIATED : utility ? QOS_CLASS_UTILITY : QOS_CLASS_DEFAULT,
                 user_initiated ? "User Initiated" : utility ? "Utility" : "Default",
                 double(std::clamp<int32_t>(REXCVAR_GET(ios_adaptive_qos_max_hold), 5, 240)),
                 std::max<int32_t>(REXCVAR_GET(ios_adaptive_qos_workers_count), 0)};
  }();
  return boost;
}

enum : unsigned { MainUtility=1, GuestUtility=2, Adaptive=4, Original=8, RenderUtility=16, Background=32, LowWorkers=64 };
const char* policy_names[] = {"ios_utility_qos", "ios_utility_qos_guest", "ios_adaptive_qos",
                            "nfsmw_adaptive_qos_original", "nfsmw_native_render_utility",
                            "ios_background_qos", "ios_background_qos_low_workers"};
constexpr unsigned kPolicyCount = 7;
std::atomic<unsigned> policy_flags{0}, profile_epoch{0};
std::atomic<int> selected_profile{1}, policy_cap{60};
unsigned explicit_mask = 0, override_values = 0;
int efficiency_cores = 0;
bool main_interactive = false, cp_interactive = false;
std::mutex profile_mutex;
bool Flag(unsigned flag) { return (policy_flags.load(std::memory_order_acquire) & flag) != 0; }
bool AdaptiveEnabled() { return Flag(Adaptive) && !Flag(MainUtility); }
int ProfileNumber(const std::string& name) {
  if (REXCVAR_GET(nfsmw_cap_controller)) return 3;
  return name == "eco" ? 0 : name == "max" ? 2 : 1;
}
bool Controller() { return selected_profile.load(std::memory_order_relaxed) == 3; }
// The class of boost level m (>= 1).
qos_class_t BoostQos(int m) {
  if (Controller()) return m >= 2 ? QOS_CLASS_USER_INITIATED : QOS_CLASS_DEFAULT;
  return Settings().qos;
}
const char* LevelName(int m) {
  return m <= 0 ? "Low (efficiency cores)" : m == 1 ? "Default" : "User Initiated";
}
void PublishProfile(int cap) {
  const int selected = selected_profile.load(std::memory_order_relaxed);
  const auto p = nfsmw::performance::Resolve(selected, efficiency_cores, cap);
  const unsigned flags = nfsmw::performance::WithOverrides(
      nfsmw::performance::Encode(p), explicit_mask, override_values);
  // Existing thread-start code still reads these flags. Publish the atomic
  // snapshot only after the legacy flags reflect the selected policy.
  for (unsigned i = 0; i < kPolicyCount; ++i)
    rex::cvar::SetFlagByName(policy_names[i], flags & (1u<<i) ? "true" : "false");
  policy_cap.store(cap, std::memory_order_relaxed);
  policy_flags.store(flags, std::memory_order_release);
  const unsigned epoch = profile_epoch.fetch_add(1, std::memory_order_acq_rel)+1;
  REXLOG_INFO("[live-profile] request {} epoch {} cap {}: main-utility {} guest-utility {} adaptive {} original {} render-utility {} background {} low-workers {} overrides {:02X}",
      selected == 3 ? "cap-controller" : selected == 0 ? "eco" : selected == 2 ? "max" : "balanced", epoch, cap,
      bool(flags&MainUtility), bool(flags&GuestUtility), bool(flags&Adaptive), bool(flags&Original),
      bool(flags&RenderUtility), bool(flags&Background), bool(flags&LowWorkers), explicit_mask);
}
// ios_background_qos: the low class used instead of Utility (read once).
bool Flag(unsigned flag);
// The low class: Background when the profile (tablet Balanced at 30/40) or
// --ios_background_qos asks, live; workers-only trial via its own cvar.
// dev66: the Background flag lowers the frame threads and the render queue
// only; guest workers (audio stream decode among them) keep Utility, since
// dev65's 40 cap starved audio (31 gaps in 5 s) with every worker at
// Background. ios_background_qos_workers still lowers the workers too.
enum class LowRole { Frame, Render, Worker };
bool Controller();
// dev187: Background found too low on this device and cap: Low is Utility
// (still the efficiency cores in practice) before any step to Default.
std::atomic<bool> background_relaxed{false};
qos_class_t LowQos(LowRole role) {
  static const bool workers = REXCVAR_GET(ios_background_qos_workers);
  static const bool low_background = REXCVAR_GET(nfsmw_low_background);
  const bool background = !(role != LowRole::Worker && background_relaxed.load(std::memory_order_relaxed)) &&
                          ((low_background && Controller()) || (role == LowRole::Worker ? workers : Flag(Background)));
  return background ? QOS_CLASS_BACKGROUND : QOS_CLASS_UTILITY;
}
// ios_boost_threads: whether a boost raises this frame thread (read once).
bool BoostRaises(bool main) {
  static const int which = [] {
    const std::string s = REXCVAR_GET(ios_boost_threads);
    const int w = s == "gpu" ? 1 : s == "main" ? 2 : s == "none" ? 3 : 0;
    REXLOG_INFO("[adaptive-qos] boost raises: {}", w == 1 ? "GPU Commands only" : w == 2 ? "Main XThread only"
                                                     : w == 3 ? "neither frame thread" : "both frame threads");
    return w;
  }();
  return which == 0 || (which == 1 && !main) || (which == 2 && main);
}
qos_class_t PrimaryQos(int m, bool main) {
  if ((main && main_interactive) || (!main && cp_interactive)) return QOS_CLASS_USER_INTERACTIVE;
  if (AdaptiveEnabled()) return m >= 1 && BoostRaises(main) ? BoostQos(m) : LowQos(LowRole::Frame);
  return Flag(MainUtility) ? LowQos(LowRole::Frame) : QOS_CLASS_DEFAULT;
}
void ApplyQos(qos_class_t qos, int& applied, const char* role) {
  // All cooperative and main-loop callers share one cache on each thread.
  // Separate caches could skip a needed change after another hook set QoS.
  static thread_local int current = -1;
  if (int(qos) == current) { applied = current; return; }
  const int result = pthread_set_qos_class_self_np(qos, 0);
  if (result == 0) current = applied = int(qos);
  REXLOG_INFO("[live-profile] {} self QoS {} epoch {}: {}", role, unsigned(qos),
              profile_epoch.load(std::memory_order_acquire), result == 0 ? "set" : "FAILED");
}
void Apply(int m, int& applied) { ApplyQos(PrimaryQos(m, false), applied, "GPU Commands"); }

bool WorkersOn() {
  static const bool on = REXCVAR_GET(ios_adaptive_qos_workers);
  return on;
}

// Guest threads keep their default names ("XThreadDF1B (F8000010)"; the main
// thread is "Main XThread", which follows the mode itself).
std::vector<pthread_override_t> overrides;

void RaiseGuestThreads(qos_class_t qos) {  // QOS_CLASS_UNSPECIFIED: none raised
  for (pthread_override_t o : overrides) pthread_override_qos_class_end_np(o);
  overrides.clear();
  if (qos == QOS_CLASS_UNSPECIFIED) return;
  thread_act_array_t threads = nullptr;
  mach_msg_type_number_t count = 0;
  if (task_threads(mach_task_self(), &threads, &count) != KERN_SUCCESS) return;
  // (CPU time since the previous boost, thread), busiest first.
  static std::vector<std::pair<uint64_t, uint64_t>> last_us;  // (thread id, CPU time)
  std::vector<std::pair<uint64_t, uint64_t>> now_us;
  std::vector<std::pair<uint64_t, pthread_t>> guests;
  for (mach_msg_type_number_t i = 0; i < count; ++i) {
    pthread_t thread = pthread_from_mach_thread_np(threads[i]);
    char name[64] = {};
    thread_identifier_info_data_t id = {};
    thread_basic_info_data_t basic = {};
    mach_msg_type_number_t n = THREAD_IDENTIFIER_INFO_COUNT, b = THREAD_BASIC_INFO_COUNT;
    if (thread && pthread_getname_np(thread, name, sizeof(name)) == 0 && std::strncmp(name, "XThread", 7) == 0 &&
        thread_info(threads[i], THREAD_IDENTIFIER_INFO, thread_info_t(&id), &n) == KERN_SUCCESS &&
        thread_info(threads[i], THREAD_BASIC_INFO, thread_info_t(&basic), &b) == KERN_SUCCESS) {
      const uint64_t us = uint64_t(basic.user_time.seconds + basic.system_time.seconds) * 1000000 +
                          basic.user_time.microseconds + basic.system_time.microseconds;
      uint64_t before = 0;
      for (const auto& [tid, t] : last_us) {
        if (tid == id.thread_id) before = t;
      }
      now_us.push_back({id.thread_id, us});
      if (Controller() && REXCVAR_GET(nfsmw_audio_thread_low) &&
          id.thread_id == audio_thread_id.load(std::memory_order_relaxed)) {
        mach_port_deallocate(mach_task_self(), threads[i]);
        continue;
      }
      guests.push_back({us - std::min(us, before), thread});
    }
    mach_port_deallocate(mach_task_self(), threads[i]);
  }
  vm_deallocate(mach_task_self(), vm_address_t(threads), count * sizeof(thread_act_t));
  last_us.swap(now_us);
  std::sort(guests.begin(), guests.end(), [](const auto& a, const auto& b) { return a.first > b.first; });
  const size_t limit = Settings().workers ? size_t(Settings().workers) : guests.size();
  for (size_t i = 0; i < guests.size() && i < limit; ++i) {
    if (pthread_override_t o = pthread_override_qos_class_start_np(guests[i].second, qos, 0)) {
      overrides.push_back(o);
    }
  }
}

}  // namespace

namespace nfsmw::adaptive_qos {

bool Enabled() {
  return AdaptiveEnabled();
}

// For the native render queue: submit this frame at the boost's class (0 when not boosted).
qos_class_t WorkersRaised() {
  const int m = mode.load(std::memory_order_relaxed);
  return Enabled() && WorkersOn() && m >= 1 ? BoostQos(m) : QOS_CLASS_UNSPECIFIED;
}

// From the game's thread when driving starts or stops (game_state.cpp).
void SetDriving(bool on) { driving.store(on, std::memory_order_relaxed); }

// From the native render queue, per frame: its encoding time (no drawable wait).
void OnRendered(double ms) {
  if (!Enabled()) return;
  const int32_t cap = std::max<int32_t>(rex::cvar::Query<int32_t>("ios_fps_cap"), 1);
  if (ms > 1000.0 / cap && ms < 250.0) render_late.fetch_add(1, std::memory_order_relaxed);
}

// On the GPU command thread, once per swap.
void OnSwap(double interval_ms) {
  const int current_cap = rex::cvar::Query<int32_t>("ios_fps_cap");
  if (policy_cap.load(std::memory_order_relaxed) != current_cap) {
    std::lock_guard<std::mutex> lock(profile_mutex);
    PublishProfile(current_cap);
  }
  static int applied = -1;
  static bool late[120] = {};
  const bool original = Flag(Original);
  const int window = original ? 120 : 60, threshold = original ? 2 : 3;
  static int at = 0, late_count = 0;
  static Clock::time_point hold_until, eco_since = Clock::now();
  static double hold_s = 20.0;
  static int lines = 0;
  const auto now = Clock::now();
  static unsigned seen_epoch = 0;
  const unsigned epoch = profile_epoch.load(std::memory_order_acquire);
  if (epoch != seen_epoch) {
    seen_epoch = epoch;
    background_relaxed.store(false, std::memory_order_relaxed);  // a new cap: Background again where it applies
    RaiseGuestThreads(QOS_CLASS_UNSPECIFIED);
    std::fill(std::begin(late), std::end(late), false);
    at = late_count = 0;
    hold_s = 20;
    hold_until = now;
    eco_since = now;
    render_late.store(0, std::memory_order_relaxed);
    mode.store(-1, std::memory_order_relaxed);
    applied = -1;
  }
  if (!Enabled()) {
    mode.store(-1, std::memory_order_relaxed);
    Apply(-1, applied);
    return;
  }
  int m = mode.load(std::memory_order_relaxed);
  if (m < 0) {
    m = 0;
    mode.store(0, std::memory_order_relaxed);
    REXLOG_INFO("[adaptive-qos] on: main and GPU command threads start at Utility; guest workers and render queue {}",
                WorkersOn() ? "follow the mode" : "stay at Utility");
    if (Controller())
      REXLOG_INFO("[cap-controller] on (dev109): Low is {}; while driving at least the device's start level, "
                  "up one level on 3 late frames of 60, steps down only outside driving",
                  LowQos(LowRole::Frame) == QOS_CLASS_BACKGROUND ? "Background" : "Utility");
    else
    REXLOG_INFO("[adaptive-qos] boost: {} QoS, holds up to {:.0f} s, {} guest threads{}", Settings().name,
                Settings().max_hold_s,
                Settings().workers ? fmt::format("the {} busiest", Settings().workers) : std::string("all"),
                REXCVAR_GET(ios_adaptive_qos_ipa48) ? " (IPA48 settings)" : "");
  }
  const int32_t cap = std::max<int32_t>(rex::cvar::Query<int32_t>("ios_fps_cap"), 1);
  const double budget = 1000.0 / cap;
  const bool rendered_late = render_late.exchange(0, std::memory_order_relaxed) > 0 && !original;
  const bool is_late = (interval_ms > budget * (original ? 1.2 : 1.1) && interval_ms < 250.0) ||
                       rendered_late;  // not loading stalls
  static Clock::time_point drive_grace_until{};
  const bool counted = is_late && !(Controller() && now < drive_grace_until);
  late_count += int(counted) - int(late[at]);
  late[at] = counted;
  at = (at + 1) % window;
  if (Controller()) {
    // dev109 cap controller (Stefan, Nov 9: dev108's probing down while
    // driving hitched and saved nothing on the iPhone). While driving the
    // frame threads never step down: they stay at least at the level that
    // held this device and cap in the Nov 9 measurements (iPhone and other
    // devices with < 6 efficiency cores: Default at caps above 30; 6+
    // efficiency-core iPads: Low up to 60; Default at 120, untested) and step
    // up one level on 3 late frames of 60. Outside driving (menus, pause,
    // loading) a late frame is invisible, so there the level steps down one
    // at a time after 5 s without a step up, down to Low.
    const bool drive = driving.load(std::memory_order_relaxed);
    // dev113 (Stefan, Nov 10): iPhones at 30/40 drive on the efficiency cores
    // (Eco 40 measured Nov 9: 17.4-17.5 vs 26-28 %/h, median 39.5-39.7 fps,
    // "almost perfect"); only 60 starts at Default.
    int floor_level = efficiency_cores >= 6 ? (cap > 60 ? 1 : 0) : (cap > 40 ? 1 : 0);
    // dev179 (Stefan: as much as possible on the efficiency cores, adapting
    // to each device, older iPhones included): with the learned start level
    // a device starts every drive at Low (Background: efficiency cores) until
    // a drive shows it needs more; the level it needed is kept for that cap
    // (CFPreferences, between sessions), and after a long drive (60 s+)
    // that never stepped up (120 s+) it tries one level lower next time. Never probed
    // while driving (dev108 hitched).
    static const bool learn = REXCVAR_GET(nfsmw_qos_learn);
    static int learned_cap = -1, learned = 0;
    auto pref_key = [](int c) {
      return CFStringCreateWithFormat(nullptr, nullptr, CFSTR("nfsmw.qos_start_level2.cap%d"), c);
    };
    if (learn) {
      if (learned_cap != cap) {
        learned_cap = cap;
        learned = 0;
        CFStringRef key = pref_key(cap);
        Boolean valid = false;
        const CFIndex v = CFPreferencesGetAppIntegerValue(key, kCFPreferencesCurrentApplication, &valid);
        CFRelease(key);
        if (valid) learned = int(std::clamp<CFIndex>(v, 0, 2));
        if (lines++ < 200) REXLOG_INFO("[cap-controller] learned start level for cap {}: {}", cap, LevelName(learned));
      }
      // dev188 (Stefan: match the best measured results first): the learned
      // level only adds to the measured start level (iPhone 60/120 Default,
      // dev109/dev113), never goes below it (dev108 probing below hitched).
      floor_level = std::max(floor_level, learned);
    }
    // dev199 (after learning) (Stefan: with sim 60 the iPhone does ~30 % less work at 60; can
    // it drive on the efficiency cores now?): a forced measured start level.
    if (const int32_t forced = REXCVAR_GET(nfsmw_start_level); forced >= 0 && forced <= 2) floor_level = forced;

    static Clock::time_point drive_began{}, last_late{}, last_tick{}, stepped_down_at{};
    static int drive_max = 0;
    static double secs_above = 0;  // this drive, above its start level
    static bool latched = false;   // a step-down was followed by lateness: stay up this drive
    {
      const double tick = last_tick.time_since_epoch().count() ? std::chrono::duration<double>(now - last_tick).count() : 0;
      last_tick = now;
      if (driving.load(std::memory_order_relaxed) && mode.load(std::memory_order_relaxed) > floor_level)
        secs_above += std::min(tick, 0.5);
    }
    static const bool drive_ui = REXCVAR_GET(nfsmw_drive_start_user_initiated);
    if (drive_ui && floor_level == 1) floor_level = 2;
    // On Low while driving at 30/40 an isolated late frame is accepted (Eco's
    // behaviour): step up only when a fifth of the last 60 frames were late.
    // dev185: iPads with 6+ efficiency cores also accept isolated late frames
    // on Low while driving at 60 (a fifth of the last 60 before stepping up):
    // the Nov 3-4 tablet profile (dev50 trace: frame threads entirely on the
    // efficiency cores, dev62 24.0 vs 28 %/h, smooth for Stefan) never
    // boosted; dev183/184 logs show Low lasting only 7-15 s on the 3-of-60 rule.
    // dev217 test (Stefan, iPhone 60 on Low with low reflection rates: 0-1
    // off per 300 for ~28 s, then 3 late of 60 sent it to Default): phones
    // may use the same tolerance at 60.
    const bool tolerant = cap <= 60 && ((REXCVAR_GET(nfsmw_ipad_tolerant_low) && efficiency_cores >= 6) ||
                                        REXCVAR_GET(nfsmw_phone_tolerant_low));
    const int up_threshold = (drive && m == 0 && (cap <= 40 || tolerant)) ? 12 : 3;
    static bool was_driving = false;
    bool started = false;
    if (drive != was_driving) {
      was_driving = drive;
      started = drive;
      if (drive) {
        drive_began = now;
        drive_max = floor_level;
        secs_above = 0;
        latched = false;
        last_late = now;
      } else if (learn) {
        const double secs = std::chrono::duration<double>(now - drive_began).count();
        int next = learned;
        // dev183: raised only when the drive spent a third of its time above
        // its start level (one GPU hitch, e.g. a recording starting, no
        // longer teaches the iPad to drive on the performance cores).
        // dev188: relative to the measured start level (learned is the extra).
        if (drive_max > std::max(learned, floor_level) && secs_above > secs / 3) next = drive_max;
        else if (secs >= 120 && learned > 0) next = learned - 1;  // two calm minutes: try lower
        if (next != learned) {
          learned = next;
          CFStringRef key = pref_key(cap);
          CFNumberRef num = CFNumberCreate(nullptr, kCFNumberIntType, &next);
          CFPreferencesSetAppValue(key, num, kCFPreferencesCurrentApplication);
          CFPreferencesAppSynchronize(kCFPreferencesCurrentApplication);
          CFRelease(num);
          CFRelease(key);
          if (lines++ < 200)
            REXLOG_INFO("[cap-controller] learned start level for cap {} now {} (drive {:.0f} s, highest {})", cap,
                        LevelName(next), secs, LevelName(drive_max));
        }
      }
      if (lines++ < 200)
        REXLOG_INFO("[cap-controller] {} (start level {}, cap {})", drive ? "driving: no step down" : "driving stopped: step down allowed",
                    LevelName(floor_level), cap);
    }
    // dev110: driving always starts at the start level. dev109 kept a level
    // raised by loading-screen late frames (User Initiated) for the whole
    // drive (Nov 10 iPhone run: 40.2 %/h instead of Default's ~38).
    if (started) {
      // dev130: every drive starts with an empty late window and a short
      // grace period, whatever level the loading screens left.
      std::fill(std::begin(late), std::end(late), false);
      late_count = 0;
      const int32_t grace_ms = std::max<int32_t>(REXCVAR_GET(nfsmw_drive_start_grace_ms), 0);
      drive_grace_until = now + std::chrono::milliseconds(grace_ms);
      if (grace_ms > 0 && lines++ < 200)
        REXLOG_INFO("[cap-controller] driving: late frames ignored for {} ms", grace_ms);
    }
    if (started && m != floor_level) {
      m = floor_level;
      if (lines++ < 200) REXLOG_INFO("[cap-controller] driving: {} (start level, cap {})", LevelName(m), cap);
    } else if (drive && m < floor_level) {
      m = floor_level;
      if (lines++ < 200) REXLOG_INFO("[cap-controller] driving: {} (start level, cap {})", LevelName(m), cap);
    } else if (m == 0 && late_count >= up_threshold && LowQos(LowRole::Frame) == QOS_CLASS_BACKGROUND) {
      // dev187: from Background first to Utility (efficiency cores, higher
      // priority), then Default; kept until the frame rate cap changes.
      background_relaxed.store(true, std::memory_order_relaxed);
      std::fill(std::begin(late), std::end(late), false);
      late_count = 0;
      applied = -1;  // re-apply the low class
      RaiseGuestThreads(QOS_CLASS_UNSPECIFIED);
      if (lines++ < 200) REXLOG_INFO("[cap-controller] up to Utility from Background (cap {}, {})", cap,
                                     drive ? "driving" : "not driving");
    } else if (m < 2 && late_count >= up_threshold) {
      ++m;
      if (drive) {
        drive_max = std::max(drive_max, m);
        if (stepped_down_at.time_since_epoch().count() && now - stepped_down_at < std::chrono::seconds(10)) {
          latched = true;  // it needed the level: no more step-downs this drive
          if (lines++ < 200) REXLOG_INFO("[cap-controller] driving: stays at {} for this drive", LevelName(m));
        }
      }
      last_late = now;
      hold_until = now + std::chrono::seconds(5);
      if (lines++ < 200)
        REXLOG_INFO("[cap-controller] up to {} ({} late frames of 60, cap {}, {})", LevelName(m), late_count, cap,
                    drive ? "driving" : "not driving");
    } else if (drive && m > floor_level && !latched && REXCVAR_GET(nfsmw_drive_step_down) &&
               now - last_late > std::chrono::seconds(efficiency_cores >= 6 ? 15 : 30) && now >= hold_until) {
      // dev183 (Stefan: the iPad still ended up on the performance cores):
      // while driving, after 15 s (iPads with 6+ efficiency cores) or 30 s
      // (phones) without a late frame, one level down; if it is late again
      // within 10 s it goes back up and stays there for this drive.
      --m;
      stepped_down_at = now;
      hold_until = now + std::chrono::seconds(5);
      last_late = now;
      if (lines++ < 200) REXLOG_INFO("[cap-controller] driving: down to {} (calm, cap {})", LevelName(m), cap);
    } else if (!drive && m > 0 && now >= hold_until) {
      --m;
      hold_until = now + std::chrono::seconds(5);
      if (lines++ < 200) REXLOG_INFO("[cap-controller] down to {} (not driving, cap {})", LevelName(m), cap);
    }
    if (m != mode.load(std::memory_order_relaxed)) {
      std::fill(std::begin(late), std::end(late), false);
      late_count = 0;
      mode.store(m, std::memory_order_relaxed);
      if (WorkersOn()) RaiseGuestThreads(m >= 1 ? BoostQos(m) : QOS_CLASS_UNSPECIFIED);
    }
    Apply(m, applied);
    return;
  }
  const bool drive = driving.load(std::memory_order_relaxed) && !original;
  static bool was_driving = false;
  if (drive != was_driving) {
    was_driving = drive;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] {}", drive ? "driving: boosted until driving stops" : "driving stopped: Utility allowed again");
  }
  if (drive) {
    // Never Utility while driving; a short hold after it stops (pause, results).
    if (m == 0) {
      m = 1;
      if (lines++ < 60) REXLOG_INFO("[adaptive-qos] {} (driving)", Settings().name);
    }
    hold_until = now + std::chrono::seconds(5);
    hold_s = 20.0;
  } else if (m == 0 && late_count >= threshold) {
    const double eco_s = std::chrono::duration<double>(now - eco_since).count();
    hold_s = eco_s < 10.0 ? std::min(hold_s * 2.0, Settings().max_hold_s) : eco_s > 60.0 ? 20.0 : hold_s;
    hold_s = std::min(hold_s, Settings().max_hold_s);
    hold_until = now + std::chrono::milliseconds(int64_t(hold_s * 1000));
    m = 1;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] {} for {:.0f} s ({} late frames of {}, {:.0f} s on Utility)", Settings().name, hold_s, late_count, window, eco_s);
  } else if (m == 1 && now >= hold_until) {
    m = 0;
    eco_since = now;
    if (lines++ < 60) REXLOG_INFO("[adaptive-qos] back to Utility");
  }
  if (m != mode.load(std::memory_order_relaxed)) {
    std::fill(std::begin(late), std::end(late), false);
    late_count = 0;
    mode.store(m, std::memory_order_relaxed);
    if (WorkersOn()) {
      RaiseGuestThreads(m == 1 ? BoostQos(m) : QOS_CLASS_UNSPECIFIED);
      if (m == 1 && lines < 60) REXLOG_INFO("[adaptive-qos] {} guest threads and the render queue raised", overrides.size());
    }
  }
  Apply(m, applied);
}

// On the game's main thread (the first thread to call it), once per loop.
// The owner is settled once per thread: the game calls this hundreds of
// thousands of times a second in pursuits, and the compare-exchange on every
// call cost ~8 ms/s on the iPhone (IPA63 profile).
void OnMainLoop() {
  // Called from the game's deferred-call runner very often: 5.5 % of the
  // render thread incl. thread-local lookups (Nov 5 Time Profile). The mode
  // and policy change rarely, so only every 64th call does the work.
  static std::atomic<uint32_t> calls{0};
  if ((calls.fetch_add(1, std::memory_order_relaxed) & 63) != 0) return;
  static std::atomic<uint64_t> owner{0};
  thread_local int applied = -1;
  thread_local int8_t is_owner = -1;  // -1 not checked yet
  if (is_owner < 0) {
    uint64_t self = 0;
    pthread_threadid_np(nullptr, &self);
    uint64_t expected = 0;
    if (owner.compare_exchange_strong(expected, self)) {
      REXLOG_INFO("[adaptive-qos] main loop thread {:x} follows the mode", self);
    }
    is_owner = expected == 0 || expected == self;
  }
  if (!is_owner) return;
  ApplyQos(PrimaryQos(mode.load(std::memory_order_relaxed), true), applied, "Main XThread");
}

}  // namespace nfsmw::adaptive_qos

namespace nfsmw::performance {
void CaptureOverrides(const std::vector<std::string>& args, int cores) {
  efficiency_cores = cores;
  explicit_mask = 0;
  for (const auto& arg : args) {
    const auto name = arg.substr(0, arg.find('='));
    for (unsigned i=0; i<kPolicyCount; ++i)
      if (name == std::string("--")+policy_names[i]) explicit_mask |= 1u<<i;
  }
}
// Runs on the actual guest thread at startup and wait/yield safe points.
void AdoptGuestQos(int role) {
  thread_local int applied = -1;
  qos_class_t qos;
  if (role == 1 || role == 3) qos = PrimaryQos(mode.load(std::memory_order_relaxed), role == 1);
  else {
    qos = Flag(GuestUtility) ? LowQos(LowRole::Worker) : QOS_CLASS_DEFAULT;
    // Trial: low-priority guest workers follow the frame threads to Background.
    if (Flag(LowWorkers) && qos == QOS_CLASS_UTILITY && Flag(Background)) {
      thread_local int32_t said_priority = INT32_MIN;
      auto* xt = rex::system::XThread::GetCurrentThread();
      const bool guest = xt && xt->is_guest_thread();
      const int32_t priority = xt ? xt->priority() : 0;
      if (guest && priority <= 0) qos = QOS_CLASS_BACKGROUND;
      if (priority != said_priority) {
        said_priority = priority;
        REXLOG_INFO("[adaptive-qos] worker {} ({}), guest priority {}: {}", xt ? xt->thread_id() : 0,
                    guest ? "guest" : "host", priority, qos == QOS_CLASS_BACKGROUND ? "Background" : "Utility");
      }
    }
    const int m = mode.load(std::memory_order_relaxed);
    const bool audio_low = is_audio_thread && Controller() && REXCVAR_GET(nfsmw_audio_thread_low);
    if (!audio_low && AdaptiveEnabled() && WorkersOn() && (Settings().workers == 0 || Controller()) && m >= 1)
      qos = BoostQos(m);
  }
  ApplyQos(qos, applied, role == 1 ? "guest-main safe point" : role == 3 ? "GPU Commands safe point" : "guest-worker safe point");
}
void Initialize() {
  override_values = 0;
  for (unsigned i=0; i<kPolicyCount; ++i) {
    const auto source = rex::cvar::GetFlagSource(policy_names[i]);
    if (source == rex::cvar::Source::kConfig || source == rex::cvar::Source::kEnvironment)
      explicit_mask |= 1u<<i;
    if (rex::cvar::GetFlagByName(policy_names[i]) == "true") override_values |= 1u<<i;
  }
  main_interactive = rex::cvar::Query<bool>("ios_thread_qos") || rex::cvar::Query<bool>("ios_battery_baseline_qos");
  cp_interactive = rex::cvar::Query<bool>("ios_battery_baseline_qos");
  selected_profile.store(ProfileNumber(REXCVAR_GET(nfsmw_performance_mode)));
  PublishProfile(rex::cvar::Query<int32_t>("ios_fps_cap"));
  using SetCallback = void (*)(void (*)(int));
  const auto setter = reinterpret_cast<SetCallback>(dlsym(RTLD_DEFAULT, "nfsmw_qos_set_callback"));
  if (setter) setter(AdoptGuestQos);
  else REXLOG_ERROR("[live-profile] guest callback bridge missing; SDK live-profile patch required");
}
void Choose(const std::string& name) {
  std::lock_guard<std::mutex> lock(profile_mutex);
  const int selected = ProfileNumber(name);
  selected_profile.store(selected);
  if (selected != 3)
    rex::cvar::SetFlagByName("nfsmw_performance_mode", selected == 0 ? "eco" : selected == 2 ? "max" : "balanced");
  rex::cvar::SetFlagByName("nfsmw_performance_source", "in_game");
  PublishProfile(rex::cvar::Query<int32_t>("ios_fps_cap"));
}
unsigned RenderQos() {
  const int m = mode.load(std::memory_order_relaxed);
  static const bool utility_trial = REXCVAR_GET(nfsmw_render_utility_trial);
  // Isolate encoding from guest-worker boosts without changing queue order or
  // the established 30/40 policy. Explicit render-utility=false still wins.
  // dev132 (Stefan, Nov 16): only caps 41-60; at 120 encoding on Utility
  // missed the cap on the iPhone (110 vs 118 fps mean).
  const int render_cap = policy_cap.load(std::memory_order_relaxed);
  if (utility_trial && Controller() && render_cap > 40 && render_cap <= 60 &&
      Flag(RenderUtility) && AdaptiveEnabled() && WorkersOn() && m >= 1)
    return QOS_CLASS_UTILITY;
  if (AdaptiveEnabled() && WorkersOn() && m >= 1) return BoostQos(m);
  return Flag(RenderUtility) ? LowQos(LowRole::Render) : QOS_CLASS_DEFAULT;
}
unsigned PipelineQos() {
  return selected_profile.load(std::memory_order_relaxed) == 0 ? QOS_CLASS_UTILITY : QOS_CLASS_USER_INITIATED;
}
}  // namespace nfsmw::performance

// The game's deferred-call runner, from its main loop (see
// tools/ios/patch_game_deferred_queue.py): the main thread's QoS, then the original.
extern "C" void __imp__sub_823C8290(PPCContext& __restrict ctx, uint8_t* base);
REXCVAR_DEFINE_BOOL(nfsmw_diag_deferred_entries, false, "Kernel",
                    "Diagnostic (dev203): 10 s into the first drive, log the next 3000 entries the game's render thread "
                    "runs from its deferred-call queue (function, size, first data words), to map each pass");
// dev203: the queue (0x82909650): +0 entries written, +4 entries run, +20
// the write pointer, +24 the read pointer; an entry is its function (+0),
// its size in bytes (+4), then its data. sub_823C8290 runs up to r4 of them.
static void LogDeferredEntries(PPCContext& ctx, uint8_t* base) {
  // From 10 s into the first drive (race frames, not menus).
  static std::chrono::steady_clock::time_point drive_since{};
  static uint32_t logged = 0;
  static std::string line;
  static uint32_t in_line = 0;
  if (logged >= 3000) return;
  const auto now = std::chrono::steady_clock::now();
  if (!driving.load(std::memory_order_relaxed)) {
    if (!logged) drive_since = {};
    return;
  }
  if (drive_since == std::chrono::steady_clock::time_point{}) drive_since = now;
  if (now - drive_since < std::chrono::seconds(10)) return;
  constexpr uint32_t kQueue = 0x82909650;
  const uint32_t written = REX_LOAD_U32(kQueue + 0), run = REX_LOAD_U32(kQueue + 4);
  uint32_t at = REX_LOAD_U32(kQueue + 24);
  const uint32_t end = REX_LOAD_U32(kQueue + 20);
  uint32_t n = std::min<uint32_t>(ctx.r4.u32, written - run);
  if (!n) return;
  for (; n && at < end && logged < 3000; --n, ++logged) {
    const uint32_t fn = REX_LOAD_U32(at), size = REX_LOAD_U32(at + 4);
    const uint32_t d0 = size > 8 ? REX_LOAD_U32(at + 8) : 0, d1 = size > 12 ? REX_LOAD_U32(at + 12) : 0,
                   d2 = size > 16 ? REX_LOAD_U32(at + 16) : 0;
    line += fmt::format(" {:08X}/{}:{:X},{:X},{:X}", fn, size, d0, d1, d2);
    if (++in_line == 6) {
      REXLOG_INFO("[deferred] #{}:{}", logged - 5, line);
      line.clear();
      in_line = 0;
    }
    if (size < 8 || size > 0x10000) break;
    at += size;
  }
  if (logged >= 3000 && in_line) REXLOG_INFO("[deferred] end:{}", line);
}

extern "C" REX_FUNC(sub_823C8290) {
  nfsmw::adaptive_qos::OnMainLoop();
  static const bool diag = REXCVAR_GET(nfsmw_diag_deferred_entries);
  if (diag) LogDeferredEntries(ctx, base);
  __imp__sub_823C8290(ctx, base);
}

// dev111: the game's audio thread procedure (mixing and XMA decode, Nov 10
// iPhone profile: 152 ms/s, 56 % on performance cores under the controller's
// boost). Marked once, then the original runs for the thread's lifetime.
extern "C" void __imp__sub_825E3F40(PPCContext& __restrict ctx, uint8_t* base);
extern "C" REX_FUNC(sub_825E3F40) {
  uint64_t self = 0;
  pthread_threadid_np(nullptr, &self);
  is_audio_thread = true;
  audio_thread_id.store(self, std::memory_order_relaxed);
  REXLOG_INFO("[cap-controller] audio thread {:x} {}", self,
              REXCVAR_GET(nfsmw_audio_thread_low) ? "stays at Utility" : "follows the boost");
  if (REXCVAR_GET(nfsmw_audio_thread_low) && Controller()) pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0);
  __imp__sub_825E3F40(ctx, base);
}
