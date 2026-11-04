#!/usr/bin/env python3
"""
The UI thread's event loop waits for events instead of polling every 1 ms
(cvar ios_event_wait, default true; false = SDL's polling as before).

    python3 tools/ios/patch_ios_sdl_event_wait.py            apply
    python3 tools/ios/patch_ios_sdl_event_wait.py --status
    python3 tools/ios/patch_ios_sdl_event_wait.py --revert

Touches thirdparty/sdl3/src/video/uikit/SDL_uikitevents.m/.h,
thirdparty/sdl3/src/video/uikit/SDL_uikitvideo.m,
thirdparty/sdl3/src/joystick/SDL_joystick.c,
thirdparty/sdl3/src/events/SDL_events.c and src/ui/windowed_app_context_sdl.cpp.


WHY
===

November 4 (docs/TECHNICAL.md), dev50 iPad System Trace: SDL's UIKit backend
has no WaitEventTimeout, so SDL_WaitEvent (RunMainMessageLoop) pumps the run
loop and sleeps 1 ms in a loop: ~830 loops/s on the UI thread, ~2,800 wakes/s
and ~15,000 system calls a second. The touch controls' virtual joystick also
keeps SDL's 1 ms joystick polling interval on.

HOW
===

UIKit_WaitEventTimeout runs the main run loop in its default mode until a
source is handled (touches, the display links, the main dispatch queue,
performSelector...), the loop woke for anything else (a timer) and is about
to sleep again (run-loop observer: NSTimers then get their pump too), the timeout passes or
UIKit_SendWakeupEvent signals its own run-loop source (SDL calls it when
another thread pushes an event while the loop waits). A wait without a
timeout still returns after 100 ms (safety net). With only virtual joysticks
open, SDL's 1 ms joystick polling is not needed (their state changes on the
UI thread itself); with a real controller it stays.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

EV_M = "thirdparty/sdl3/src/video/uikit/SDL_uikitevents.m"
EV_H = "thirdparty/sdl3/src/video/uikit/SDL_uikitevents.h"
VID = "thirdparty/sdl3/src/video/uikit/SDL_uikitvideo.m"
JOY = "thirdparty/sdl3/src/joystick/SDL_joystick.c"
EVC = "thirdparty/sdl3/src/events/SDL_events.c"
APP = "src/ui/windowed_app_context_sdl.cpp"

H_ANCHOR = "extern void UIKit_PumpEvents(SDL_VideoDevice *_this);\n"
H_NEW = H_ANCHOR + """// LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py)
extern int UIKit_WaitEventTimeout(SDL_VideoDevice *_this, Sint64 timeoutNS);
extern void UIKit_SendWakeupEvent(SDL_VideoDevice *_this, SDL_Window *window);
"""

M_ANCHOR = """    // See the comment in the function definition.
#if defined(SDL_VIDEO_OPENGL_ES) || defined(SDL_VIDEO_OPENGL_ES2)
    UIKit_GL_RestoreCurrentContext();
#endif
}
"""
M_NEW = M_ANCHOR + """
// LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py): a real wait for
// SDL_WaitEvent instead of SDL's 1 ms polling loop. Off (hint
// NFSMW_IOS_EVENT_WAIT "0"), -1 makes SDL poll as before.
static CFRunLoopSourceRef UIKit_wakeup_source;
static CFRunLoopObserverRef UIKit_wait_observer;
static bool UIKit_in_wait;
static bool UIKit_woke;
// Wait results for the [ui-wait] line: waits, timed out, stopped (a timer), sources.
static uint64_t UIKit_wait_stats[4];

static void UIKit_WakeupPerform(void *info)
{
}

static void UIKit_WaitObserve(CFRunLoopObserverRef observer, CFRunLoopActivity activity, void *info)
{
    if (!UIKit_in_wait) {
        return;
    }
    if (activity == kCFRunLoopAfterWaiting) {
        UIKit_woke = true;
    } else if (activity == kCFRunLoopBeforeWaiting && UIKit_woke) {
        // Woken for something that was not a source (a timer, which may have
        // changed input state) and about to sleep again: back to SDL to pump.
        CFRunLoopStop(CFRunLoopGetCurrent());
    }
}

bool UIKit_EventWaitEnabled(void)
{
    static int enabled = -1;
    if (enabled < 0) {
        enabled = SDL_GetHintBoolean("NFSMW_IOS_EVENT_WAIT", true) ? 1 : 0;
    }
    return enabled == 1;
}

int UIKit_WaitEventTimeout(SDL_VideoDevice *_this, Sint64 timeoutNS)
{
    if (!UIKit_EventPumpEnabled || !UIKit_EventWaitEnabled() || ![NSThread isMainThread]) {
        return -1;
    }
    @autoreleasepool {
        if (!UIKit_wakeup_source) {
            CFRunLoopSourceContext context;
            SDL_zero(context);
            context.perform = UIKit_WakeupPerform;
            CFRunLoopSourceRef source = CFRunLoopSourceCreate(kCFAllocatorDefault, 0, &context);
            CFRunLoopAddSource(CFRunLoopGetMain(), source, kCFRunLoopCommonModes);
            UIKit_wait_observer = CFRunLoopObserverCreate(kCFAllocatorDefault,
                                                          kCFRunLoopAfterWaiting | kCFRunLoopBeforeWaiting,
                                                          true, 0, UIKit_WaitObserve, NULL);
            CFRunLoopAddObserver(CFRunLoopGetMain(), UIKit_wait_observer, kCFRunLoopCommonModes);
            __atomic_store_n(&UIKit_wakeup_source, source, __ATOMIC_RELEASE);
        }
        const Sint64 kSafetyNS = SDL_MS_TO_NS(100);
        const bool finite = timeoutNS >= 0 && timeoutNS <= kSafetyNS;
        const Sint64 waitNS = finite ? timeoutNS : kSafetyNS;
        UIKit_in_wait = true;
        UIKit_woke = false;
        const SInt32 result = CFRunLoopRunInMode(kCFRunLoopDefaultMode, (CFTimeInterval)waitNS / SDL_NS_PER_SECOND, TRUE);
        UIKit_in_wait = false;
        UIKit_wait_stats[0]++;
        UIKit_wait_stats[result == kCFRunLoopRunTimedOut ? 1 : result == kCFRunLoopRunStopped ? 2 : 3]++;
        // 0 only for a caller's own timeout; otherwise SDL pumps and waits again.
        return (result == kCFRunLoopRunTimedOut && finite) ? 0 : 1;
    }
}

// Read and reset by the [ui-wait] line (UI thread only).
void UIKit_NfsmwWaitStats(uint64_t out[4])
{
    for (int i = 0; i < 4; ++i) {
        out[i] = UIKit_wait_stats[i];
        UIKit_wait_stats[i] = 0;
    }
}

void UIKit_SendWakeupEvent(SDL_VideoDevice *_this, SDL_Window *window)
{
    CFRunLoopSourceRef source = __atomic_load_n(&UIKit_wakeup_source, __ATOMIC_ACQUIRE);
    if (source) {
        CFRunLoopSourceSignal(source);
        CFRunLoopWakeUp(CFRunLoopGetMain());
    }
}
"""

V_ANCHOR = "        device->PumpEvents = UIKit_PumpEvents;\n"
V_NEW = V_ANCHOR + """        // LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py)
        device->WaitEventTimeout = UIKit_WaitEventTimeout;
        device->SendWakeupEvent = UIKit_SendWakeupEvent;
"""

J_ANCHOR = "bool SDL_JoysticksOpened(void)\n{"
J_NEW = """// LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py): only virtual
// joysticks open (their state is set on the UI thread, no polling needed).
bool SDL_NfsmwOnlyVirtualJoysticksOpened(void)
{
    bool only = true;
    SDL_LockJoysticks();
    {
        if (!SDL_joysticks) {
            only = false;
        }
        for (SDL_Joystick *joystick = SDL_joysticks; joystick; joystick = joystick->next) {
            if (!joystick->is_virtual) {
                only = false;
                break;
            }
        }
    }
    SDL_UnlockJoysticks();
    return only;
}

""" + J_ANCHOR

E_ANCHOR = """        if (SDL_JoysticksOpened()) {
            // If we have joysticks open, we need to poll rapidly for events
            poll_intervalNS = SDL_min(poll_intervalNS, EVENT_POLL_INTERVAL_NS);"""
E_NEW = """        // LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py)
        if (SDL_JoysticksOpened() && !(UIKit_EventWaitEnabled() && SDL_NfsmwOnlyVirtualJoysticksOpened())) {
            // If we have joysticks open, we need to poll rapidly for events
            poll_intervalNS = SDL_min(poll_intervalNS, EVENT_POLL_INTERVAL_NS);"""
E_DECL_ANCHOR = "static Sint64 SDL_events_get_polling_interval(void)\n{"
E_DECL_NEW = """// LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py)
#ifdef SDL_PLATFORM_IOS
extern bool UIKit_EventWaitEnabled(void);
#else
static bool UIKit_EventWaitEnabled(void) { return false; }
#endif
extern bool SDL_NfsmwOnlyVirtualJoysticksOpened(void);

""" + E_DECL_ANCHOR

A_DEF_ANCHOR = "#include <rex/ui/window_sdl.h>\n"
A_DEF_NEW = A_DEF_ANCHOR + """
// LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py).
#include <chrono>
#if REX_PLATFORM_IOS
extern "C" void UIKit_NfsmwWaitStats(uint64_t out[4]);
#endif
REXCVAR_DEFINE_BOOL(ios_event_wait, true, "UI",
                    "iOS: the UI thread waits for events instead of SDL's 1 ms polling "
                    "(restart required)");
"""
A_CVAR_ANCHOR = "int SDLWindowedAppContext::RunMainMessageLoop() {\n"
A_CVAR_NEW = A_CVAR_ANCHOR + """  SDL_SetHint("NFSMW_IOS_EVENT_WAIT", REXCVAR_GET(ios_event_wait) ? "1" : "0");
  REXLOG_INFO("[ui-wait] UI thread event loop: {}",
              REXCVAR_GET(ios_event_wait) ? "waits for events" : "SDL polling (1 ms)");
#if REX_PLATFORM_IOS
  auto ios_wait_since = std::chrono::steady_clock::now();
  uint64_t ios_events = 0;
#endif
"""

A_LOOP_ANCHOR = """    ProcessEvent(event);
  }
  return EXIT_SUCCESS;
}
"""
A_LOOP_NEW = """    ProcessEvent(event);
#if REX_PLATFORM_IOS
    // LOCAL PATCH - iOS (tools/ios/patch_ios_sdl_event_wait.py): [ui-wait] every 10 s.
    ++ios_events;
    const auto ios_now = std::chrono::steady_clock::now();
    if (ios_now - ios_wait_since >= std::chrono::seconds(10)) {
      uint64_t s[4];
      UIKit_NfsmwWaitStats(s);
      const double secs = std::chrono::duration<double>(ios_now - ios_wait_since).count();
      REXLOG_INFO("[ui-wait] 10 s: {:.0f} events/s, {:.0f} waits/s ({:.0f} timed out, {:.0f} timers, "
                  "{:.0f} sources /s){}",
                  ios_events / secs, s[0] / secs, s[1] / secs, s[2] / secs, s[3] / secs,
                  s[0] == 0 ? " - not waiting (SDL polling)" : "");
      // What keeps SDL's 1 ms polling interval (opened joysticks / sensors), when it changes.
      static std::string ios_devices_said;
      std::string devices;
      int count = 0;
      if (SDL_JoystickID* ids = SDL_GetJoysticks(&count)) {
        for (int i = 0; i < count; ++i) {
          if (SDL_GetJoystickFromID(ids[i])) {
            const char* name = SDL_GetJoystickNameForID(ids[i]);
            devices += fmt::format(" joystick '{}'{}", name ? name : "?",
                                   SDL_IsJoystickVirtual(ids[i]) ? " (virtual)" : "");
          }
        }
        SDL_free(ids);
      }
      if (SDL_SensorID* ids = SDL_GetSensors(&count)) {
        for (int i = 0; i < count; ++i) {
          if (SDL_GetSensorFromID(ids[i])) {
            const char* name = SDL_GetSensorNameForID(ids[i]);
            devices += fmt::format(" sensor '{}'", name ? name : "?");
          }
        }
        SDL_free(ids);
      }
      if (devices.empty()) devices = " none";
      if (devices != ios_devices_said) {
        REXLOG_INFO("[ui-wait] open input devices:{}", devices);
        ios_devices_said = devices;
      }
      ios_events = 0;
      ios_wait_since = ios_now;
    }
#endif
  }
  return EXIT_SUCCESS;
}
"""

BLOCKS = [
    (EV_H, "UIKit wait declarations", H_ANCHOR, H_NEW),
    (EV_M, "UIKit_WaitEventTimeout / UIKit_SendWakeupEvent", M_ANCHOR, M_NEW),
    (VID, "UIKit wait hooked into the video device", V_ANCHOR, V_NEW),
    (JOY, "only-virtual-joysticks helper", J_ANCHOR, J_NEW),
    (EVC, "polling interval declarations", E_DECL_ANCHOR, E_DECL_NEW),
    (EVC, "no 1 ms polling for virtual joysticks only", E_ANCHOR, E_NEW),
    (APP, "the ios_event_wait cvar", A_DEF_ANCHOR, A_DEF_NEW),
    (APP, "the hint and [ui-wait] line", A_CVAR_ANCHOR, A_CVAR_NEW),
    (APP, "the [ui-wait] counters", A_LOOP_ANCHOR, A_LOOP_NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_sdl_event_wait", BLOCKS))
