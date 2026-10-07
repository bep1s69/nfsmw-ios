// NFSMW Recompiled - the app on iOS
//
// The iOS counterpart of android/app/src/main/cpp/juego.cpp: the same NfsmwApp
// as every other platform (app/src/nfsmw_app.h), with two iOS-specific things:
//
//   - audio through CoreAudio (audio/coreaudio_driver.mm) instead of SDL's;
//   - on-screen touch controls (touch_controls.mm), a basic version of
//     Android's TouchControllerView;
//   - the GPU emulation paused while the app is in the background. iOS does
//     not let a background app submit GPU work: Metal fails the command
//     buffers and MoltenVK loses the device. parche_pausa already releases
//     the surface; this also stops the command processor
//     (tools/ios/patch_ios_pause.py) and lets it go on when the app returns.
//
// The generated header is included by name: on iOS the generated code lives in
// ios/generated/default, which ios/CMakeLists.txt puts on the include path.

#include "nfsmw_init.h"

#include "nfsmw_app.h"


#include <rex/logging.h>
#include <rex/runtime.h>
#include <rex/system/interfaces/graphics.h>

#include "achievements_export.h"
#include "audio/coreaudio_driver.h"
#include "display_rate.h"
#include "gpu_capture.h"
#include "boot_trace.h"
#include "launcher.h"
#include "lifecycle.h"

// The UI thread's paints stopped while paused (the runtime's presenter,
// tools/ios/patch_ios_paint_suspend.py).
extern "C" void nfsmw_ios_suspend_paints(bool suspend);
#include "touch_controls.h"

#include <rex/cvar.h>

#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <cstring>

// Extra Options' data patches (game_extra_options.cpp, USA build only).
extern "C" void nfsmw_extra_options_apply() __attribute__((weak));
// The renderer's mode and size in the log (render_probe.cpp, USA build only).
extern "C" void nfsmw_render_probe_start() __attribute__((weak));

REXCVAR_DECLARE(bool, ios_gpu_capture);  // ios_main.mm
REXCVAR_DECLARE(int32_t, ios_fps_cap);    // the runtime (patch_ios_present_pacing.py)

REXCVAR_DEFINE_BOOL(ios_touch_controls, true, "Input",
                    "iOS: on-screen touch controls (they hide themselves while a physical "
                    "controller is connected)");
REXCVAR_DEFINE_BOOL(ios_show_fps, true, "Display",
                    "iOS: frames per second and ms per frame in the top-left corner");

class IosNfsmwApp : public NfsmwApp {
 public:
  using NfsmwApp::NfsmwApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<IosNfsmwApp>(new IosNfsmwApp(ctx, "nfsmw", PPCImageConfig));
  }

 protected:
  void OnPreSetup(rex::RuntimeConfig& config) override {
    NfsmwApp::OnPreSetup(config);
    config.audio_factory = REX_AUDIO_BACKEND(rex::audio::ios::CoreAudioSystem);
  }

  // The build UUID of each of our libraries, so a log says which build ran
  // (the GPU plugin and the runtime change with every SDK patch).
  static void LogBuildIds() {
    for (uint32_t i = 0; i < _dyld_image_count(); ++i) {
      const char* path = _dyld_get_image_name(i);
      const char* name = path ? std::strrchr(path, '/') : nullptr;
      name = name ? name + 1 : path;
      if (!name || (std::strncmp(name, "librex", 6) != 0 && std::strcmp(name, "nfsmw") != 0)) {
        continue;
      }
      const auto* header = reinterpret_cast<const mach_header_64*>(_dyld_get_image_header(i));
      const auto* cmd = reinterpret_cast<const load_command*>(header + 1);
      for (uint32_t c = 0; c < header->ncmds; ++c) {
        if (cmd->cmd == LC_UUID) {
          const uint8_t* u = reinterpret_cast<const uuid_command*>(cmd)->uuid;
          REXLOG_INFO("[ios] build of {}: {:02X}{:02X}{:02X}{:02X}-{:02X}{:02X}-{:02X}{:02X}-"
                      "{:02X}{:02X}-{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}",
                      name, u[0], u[1], u[2], u[3], u[4], u[5], u[6], u[7], u[8], u[9], u[10],
                      u[11], u[12], u[13], u[14], u[15]);
          break;
        }
        cmd = reinterpret_cast<const load_command*>(reinterpret_cast<const uint8_t*>(cmd) +
                                                    cmd->cmdsize);
      }
    }
  }

  void OnPostSetup() override {
    nfsmw::boot::Trace("game: runtime set up (OnPostSetup)");
    LogBuildIds();
    NfsmwApp::OnPostSetup();
    // The GPU emulation paused while the app is in the background (lifecycle.mm).
    // No GPU work while the app is paused (lifecycle.mm): the UI thread's
    // paints stop and the GPU emulation's submissions wait, so iOS never sees
    // GPU work from the background (tools/ios/patch_ios_paint_suspend.py).
    // The command processor's thread is not suspended (Pause() races).
    nfsmw::lifecycle::Install([] { nfsmw_ios_suspend_paints(true); },
                              [] { nfsmw_ios_suspend_paints(false); });
    // Extra Options' data patches: the XEX is loaded, the game has not read them yet.
    if (nfsmw_render_probe_start) {
      nfsmw_render_probe_start();
    }
    if (nfsmw_extra_options_apply) {
      nfsmw_extra_options_apply();
    }
    // The achievement list, for the pre-launch screen (achievements_export.cpp).
    nfsmw::achievements::Export(nfsmw::launcher::Documents());
    // The game's window exists by now (SetupPresentation).
    if (REXCVAR_GET(ios_touch_controls)) {
      nfsmw::touch::Install();
    }
    // After the touch controls, so it is drawn over them.
    if (REXCVAR_GET(ios_show_fps)) {
      nfsmw::touch::InstallFpsCounter();
    }
    // The display refresh rate for the frame rate cap (ProMotion).
    nfsmw::display::RequestRateForCap(REXCVAR_GET(ios_fps_cap));
    // Last, so it is on top of the touch controls.
    if (REXCVAR_GET(ios_gpu_capture)) {
      nfsmw::gpu_capture::InstallButton();
    }
  }

  void OnShutdown() override { NfsmwApp::OnShutdown(); }

 private:
};

REX_DEFINE_APP(nfsmw, IosNfsmwApp::Create)
