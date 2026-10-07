// NFSMW Recompiled - iOS entry point
//
// SDL_main.h turns this main() into SDL_main() and supplies the real main(),
// which starts UIKit (UIApplicationMain) and calls in here once the app has
// finished launching. Inside LiveContainer it is the same: LiveContainer calls
// the app's main().
//
// What the Android launcher screen (Ajustes.java) and GameActivity do, this
// file does here, without a settings screen for now:
//
//   - folders: everything lives in the app's Documents/, which is visible from
//     the Files app and from Finder (UIFileSharingEnabled in Info.plist):
//         Documents/logs/nfsmw.log      the log
//         Documents/vulkan_probe.txt    the probe report
//         Documents/data/               game saves and settings
//         Documents/*.iso               the game ISO, the first one found
//   - the game arguments, the same fixed set the Android app passes.
//   - probe or game: without generated code (NFSMW_WITH_GAME=0) or without an
//     ISO, the Vulkan probe; otherwise the game.
//   - a startup trace, Documents/logs/boot.txt (boot_trace.cpp): the SDK's
//     own log only opens partway through starting the game.
//   - Documents/extra_args.txt, if present: extra arguments, one per line, to
//     try a setting without rebuilding (the iOS counterpart of the Android
//     test bench's nfsmw.args). Each one REPLACES the app's own value for the
//     same option: the cvar parser (CLI11) does not accept a non-boolean
//     option twice, and a repeated one left others unapplied on Android.

#import <Foundation/Foundation.h>

#include <SDL3/SDL_main.h>
#include <SDL3/SDL_messagebox.h>

#include <sys/stat.h>

#include <algorithm>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <rex/cvar.h>
#include <rex/logging.h>

#include "boot_trace.h"
#include "launcher.h"
#include "probe.h"

#if NFSMW_WITH_GAME
#include <map>
#include <memory>

#include <rex/ui/windowed_app.h>
#include <rex/ui/windowed_app_context_sdl.h>
#endif

namespace fs = std::filesystem;

// The SDK's log level (the launcher's Logging switch sets "off").
REXCVAR_DECLARE(std::string, log_level);

// MoltenVK's queue submissions, synchronous (its default) or not. Measured on
// an iPad Pro M4 in a race: every UI paint spent 12-17 ms inside vkQueueSubmit
// for a tiny command buffer (and ~0.05 ms in the menus), while holding the
// SDK's queue lock, so the game's command processor waited 7-8 ms per frame
// for it. MoltenVK only takes the CAMetalLayer drawable (nextDrawable, paced by
// the display) when it encodes the work that draws to it, and by default it
// encodes inside vkQueueSubmit. Asynchronous, vkQueueSubmit queues the work and
// returns; MoltenVK encodes it, in order, on its own dispatch queue.
REXCVAR_DEFINE_BOOL(ios_async_submits, true, "GPU",
                    "iOS: MoltenVK encodes queue submissions on its own thread "
                    "(MVK_CONFIG_SYNCHRONOUS_QUEUE_SUBMITS=0) instead of inside vkQueueSubmit");

// MoltenVK's own profiling: how long its calls, encoding and shader work take,
// summarised in the log every 300 presented frames (as "mvk-info" Vulkan
// messages). It showed the GPU limits races (~20 ms of GPU time per command
// buffer on an iPad M4, the command processor waiting ~15 ms of each frame).
// Off by default: --ios_mvk_performance=true to measure again.
REXCVAR_DEFINE_BOOL(ios_mvk_performance, false, "GPU",
                    "iOS: MoltenVK performance tracking, summarised in the log every 300 frames");

// A CAPTURE button in the game that saves a Metal GPU frame capture to
// Documents/captures/ (gpu_capture.mm). Needs Metal capture enabled before the
// device exists, so it is decided here, at startup.
REXCVAR_DEFINE_BOOL(ios_gpu_capture, false, "GPU",
                    "iOS: a CAPTURE button that saves a Metal GPU frame capture to "
                    "Documents/captures (open it in Xcode)");

namespace {

fs::path DocumentsFolder() {
  NSArray<NSString*>* paths =
      NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);
  return fs::path(paths.firstObject.UTF8String);
}

// The Android app's fixed arguments (Ajustes.argumentos) with their default
// values, minus the ones that do not exist on iOS (android_*,
// thread_affinity). The command line wins over nfsmw.toml.
std::vector<std::string> GameArguments(const fs::path& docs, const fs::path& iso) {
  return {
      "--gpu_plugin=xenos",
      "--gpu_backend=vulkan",
      "--render_target_path_vulkan=fbo",
      // On iOS the window is the whole screen (19.5:9 on an iPhone): the
      // presenter adds the 16:9 bars.
      "--present_letterbox=true",
      "--present_allow_overscan_cutoff=false",
      "--vulkan_sparse_shared_memory=false",
      "--fullscreen=true",
      "--resolution_scale=1",
      "--readback_resolve=fast",
      "--gpu_sin_msaa=true",
      "--nfsmw_render_sin_mosaico=true",
      "--audio_maxqframes=64",
      // The Xbox 360 language and country of the game's edition (USA).
      "--user_language=" NFSMW_GAME_LANGUAGE,
      "--user_country=" NFSMW_GAME_COUNTRY,
      "--user_data_root=" + (docs / "data").string(),
      "--log_file=" + (docs / "logs" / "nfsmw.log").string(),
      // info, not debug: at debug, parche_anillo's XMA trace alone writes
      // ~4,700 lines a second (5 MB of log every ~10 s on an iPad M4), which
      // costs frames and rotates the startup lines out of the log.
      "--log_level=info",
      "--log_flush_interval=2",
      "--game_data_root=" + iso.string(),
  };
}

// "--name=value" or "--name" -> "--name".
std::string OptionName(const std::string& arg) {
  return arg.substr(0, arg.find('='));
}

// Puts `arg` in `args`, replacing any argument with the same option name
// (args[0] is the program name).
void SetArgument(std::vector<std::string>& args, const std::string& arg) {
  const std::string name = OptionName(arg);
  args.erase(std::remove_if(args.begin() + 1, args.end(),
                            [&](const std::string& x) { return OptionName(x) == name; }),
             args.end());
  args.push_back(arg);
}

// Documents/extra_args.txt: one argument per line; blank lines and lines
// starting with '#' are ignored. Each replaces any argument with the same
// option name already in `args`.
void ApplyExtraArguments(const fs::path& file, std::vector<std::string>& args) {
  std::ifstream in(file);
  if (!in) {
    return;
  }
  std::string line;
  while (std::getline(in, line)) {
    const auto a = line.find_first_not_of(" \t");
    const auto b = line.find_last_not_of(" \t\r\n");
    if (a == std::string::npos || line[a] == '#') {
      continue;
    }
    line = line.substr(a, b - a + 1);
    // iOS' Smart Punctuation turns a typed "--" into an em dash (and sometimes
    // an en dash): "—resolution=..." reached the parser as a plain word and
    // was ignored. Both, as a prefix, mean "--".
    for (const char* dash : {"\u2014", "\u2013"}) {
      const std::string d(dash);
      if (line.compare(0, d.size(), d) == 0) {
        line = "--" + line.substr(d.size());
        break;
      }
    }
    // And a curly quote, should one get in, is a straight one.
    for (const char* quote : {"\u201C", "\u201D"}) {
      for (size_t at; (at = line.find(quote)) != std::string::npos;) {
        line.replace(at, std::string(quote).size(), "\"");
      }
    }
    // Option names are C++ identifiers (cvars): "--ios-retina" can only mean
    // "--ios_retina". Only the name, before '=', is touched.
    if (line.compare(0, 2, "--") == 0) {
      const size_t name_end = std::min(line.find('='), line.size());
      std::replace(line.begin() + 2, line.begin() + name_end, '-', '_');
    }
    SetArgument(args, line);
    nfsmw::boot::Trace("extra argument: " + line);
  }
}

#if NFSMW_WITH_GAME
// The same as EjecutarJuego in android_main.cpp. On iOS the SDK is not in
// "several apps in one library" mode (that is Android only), so the app comes
// from GetWindowedAppCreator(), as on desktop.
int RunGame(int argc, char* argv[], const fs::path& docs) {
  namespace boot = nfsmw::boot;
  boot::Trace("game: parsing the arguments");
  auto leftovers = rex::cvar::Init(argc, argv);
  rex::cvar::ApplyEnvironment();
  rex::InitLoggingEarly();
  // Before OnInitialize, which loads MoltenVK: it reads its settings from the
  // environment when it starts.
  setenv("MVK_CONFIG_SYNCHRONOUS_QUEUE_SUBMITS", REXCVAR_GET(ios_async_submits) ? "0" : "1", 1);
  if (REXCVAR_GET(ios_gpu_capture)) {
    setenv("MTL_CAPTURE_ENABLED", "1", 1);
  }
  if (REXCVAR_GET(ios_mvk_performance)) {
    setenv("MVK_CONFIG_PERFORMANCE_TRACKING", "1", 1);
    setenv("MVK_CONFIG_PERFORMANCE_LOGGING_FRAME_COUNT", "300", 1);
  }
  // The log file now, not only when the app sets it up in SetupEnvironment:
  // that call only changes levels, and anything the SDK says before it lands
  // in the file too.
  rex::InitLogging((docs / "logs" / "nfsmw.log").c_str(),
                   REXCVAR_GET(log_level) == "off" ? spdlog::level::off : spdlog::level::info);
  REXLOG_INFO("[ios] game: starting, build " __DATE__ " " __TIME__
              " (MoltenVK submissions {}, MoltenVK profiling {})",
              REXCVAR_GET(ios_async_submits) ? "asynchronous" : "synchronous",
              REXCVAR_GET(ios_mvk_performance) ? "on" : "off");
  boot::Trace("game: initializing the SDL context");

  rex::ui::SDLWindowedAppContext context;
  if (!context.Initialize()) {
    boot::Trace("game: the SDL context did NOT initialize");
    REXLOG_ERROR("Could not initialize the SDL context");
    return EXIT_FAILURE;
  }
  boot::Trace("game: creating the app");
  std::unique_ptr<rex::ui::WindowedApp> app = rex::ui::GetWindowedAppCreator()(context);

  const auto& names = app->GetPositionalOptions();
  std::map<std::string, std::string> options;
  const size_t n = std::min(leftovers.size(), names.size());
  for (size_t i = 0; i < n; ++i) {
    options[names[i]] = leftovers[i];
  }
  app->SetParsedArguments(std::move(options));

  boot::Trace("game: OnInitialize (paths, log, GPU plugin, runtime, XEX)");
  rex::FlushLogging();
  const bool initialized = app->OnInitialize();
  boot::Trace(initialized ? "game: OnInitialize done, entering the main loop"
                          : "game: OnInitialize FAILED (reason in nfsmw.log)");
  rex::FlushLogging();
  const int result = initialized ? context.RunMainMessageLoop() : EXIT_FAILURE;
  boot::Trace("game: main loop ended");
  app->InvokeOnDestroy();
  return result;
}
#endif

int RunProbe(int argc, char* argv[], const fs::path& docs) {
  rex::cvar::Init(argc, argv);
  rex::cvar::ApplyEnvironment();
  rex::InitLoggingEarly();
  // There is no app to open the log file in the probe: open it here.
  rex::InitLogging((docs / "logs" / "nfsmw.log").c_str());
  return NfsmwVulkanProbe((docs / "vulkan_probe.txt").string());
}

}  // namespace

int main(int argc, char* argv[]) {
  const fs::path docs = DocumentsFolder();
  std::error_code ec;
  fs::create_directories(docs / "logs", ec);
  fs::create_directories(docs / "data", ec);

  namespace boot = nfsmw::boot;
  boot::Open((docs / "logs" / "boot.txt").string());
  boot::Trace("---- start, build " __DATE__ " " __TIME__);
  boot::Trace("Documents: " + docs.string());

#if NFSMW_WITH_GAME
  // The pre-launch screen: settings, the ISO, Play (launcher.mm).
  boot::Trace("launcher: on screen");
  const fs::path iso = nfsmw::launcher::Run(docs);
  boot::Trace("launcher: Play");
#else
  const auto isos = nfsmw::launcher::FindIsos(docs);
  const fs::path iso = isos.empty() ? fs::path() : isos.front();
#endif
  const bool play = NFSMW_WITH_GAME && !iso.empty();
  if (iso.empty()) {
    boot::Trace("ISO: none in Documents/");
  } else {
    struct stat st{};
    const bool ok = stat(iso.c_str(), &st) == 0;
    boot::Trace("ISO: " + iso.filename().string() + ", " +
                (ok ? std::to_string(st.st_size) + " bytes" : "stat FAILED"));
  }
  boot::Trace(std::string("mode: ") + (play ? "game" : "probe") +
              (NFSMW_WITH_GAME ? "" : " (this build has no game code)"));

  std::vector<std::string> texts{argc > 0 ? argv[0] : "nfsmw"};
  if (play) {
    const auto game = GameArguments(docs, iso);
    texts.insert(texts.end(), game.begin(), game.end());
    for (const std::string& a : nfsmw::launcher::SettingsArguments(docs)) {
      SetArgument(texts, a);
      boot::Trace("setting: " + a);
    }
    ApplyExtraArguments(docs / "extra_args.txt", texts);
    // The Logging switch off: no more boot trace either.
    if (std::find(texts.begin(), texts.end(), std::string("--log_level=off")) != texts.end()) {
      boot::Trace("logging off");
      boot::SetEnabled(false);
    }
  } else {
    texts.push_back("--log_file=" + (docs / "logs" / "nfsmw.log").string());
    texts.push_back("--log_level=info");
  }
  std::vector<char*> args;
  for (auto& t : texts) {
    args.push_back(t.data());
  }
  args.push_back(nullptr);
  const int n = static_cast<int>(args.size()) - 1;

#if NFSMW_WITH_GAME
  if (play) {
    const int result = RunGame(n, args.data(), docs);
    if (result != EXIT_SUCCESS) {
      // On iOS, returning from main leaves SDL's window up: without this, a
      // failed start is a black screen forever and looks like a hang.
      boot::Trace("game: failed to start");
      SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "NFSMW",
                               "The game failed to start.\n\nThe reason is in the app's "
                               "Documents/logs folder (boot.txt and nfsmw.log).",
                               nullptr);
    }
    return result;
  }
#endif
  return RunProbe(n, args.data(), docs);
}
