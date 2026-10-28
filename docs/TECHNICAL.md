# Technical notes

How the iOS port works: what each part does, every patch to the SDK and to the
generated code, and the measurements behind them. Paths are relative to the
repository root.

The port targets the **USA** edition of the game. The game-side code shared
with the original project is in `common/`; the SDK is prepared in
`../rexglue-sdk-ios` by `tools/ios/prepare_sdk.py`, which first applies the
original project's patches (`tools/preparar_sdk.py`, `tools/parche_*.py`) and
then the iOS ones (`tools/ios/patch_ios_*.py`).

## Development history

How the port got to running, kept for reference:

| Stage | What | Result |
|---|---|---|
| 1 | Compiles and links for arm64 iOS | Done |
| 2 | Vulkan probe on MoltenVK (CAMetalLayer surface, driver, GPU accepted, BC formats) | Done on an iPhone 17 Pro Max (A19 Pro), including the guest memory on a Mach memory entry |
| 3 | The game boots from the ISO and plays | Done on an iPad Pro M4. Races went from 17-25 fps in the first build to 60 fps through the patches listed below |

What the first probe run found:

- MoltenVK 1.4.1 loads from the app, the CAMetalLayer surface works and the
  SDK accepts the GPU for Xenos emulation.
- BC1/2/3/5 are supported, both through Vulkan and natively in Metal.
- `fragmentShaderPixelInterlock` and `fillModeNonSolid` are present.
  `geometryShader` and `pointPolygons` are not (expected on MoltenVK).
- Address space is ~508 GB, so the 4.5 GB reservation is not the problem.
  About 6 GB of RAM is available to the app.
- `rex::memory::Memory::Initialize()` failed: the iOS sandbox refuses
  `shm_open`, which the SDK uses on Apple for the guest memory. A Mach memory
  entry works (4.5 GB, views alias, `mprotect` works), so `patch_ios_memory`
  backs the guest memory with one. The probe (`ios/src/probe_memory.cpp`) keeps
  testing both backings, step by step; the app runs it when no ISO is present.

## Building

See [Building in the README](../README.md#building). The notes below explain
what the scripts do.

`generate_code.py` builds the SDK's `rexglue` CLI for macOS from the iOS tree
(its own `mac-arm64` preset) and runs the codegen. It detects the edition of
your `default.xex` and, if it is not PAL Spain (the original project's
reference), translates the project's addresses with
`tools/ediciones/<edition>/`. For USA, two `huecos.toml` entries have no safe
equivalent and are dropped; that is the translator's normal behaviour.

The build folder is `~/Library/Caches/nfsmw-ios/build`, outside the
repository, on purpose: with `~/Documents` in iCloud Drive, the file provider
tags everything with extended attributes (`com.apple.fileprovider.fpfs#P`),
puts them back if removed, and `codesign` will not sign a bundle carrying
them. It also keeps gigabytes of build output from uploading to iCloud.

## Where things are on the device

Everything is in the app's `Documents/` folder, visible from the Files app
(inside LiveContainer, in the app's data folder) and from Finder:

| File | What |
|---|---|
| `logs/nfsmw.log` | The log |
| `achievements/` | The game's achievement list (`list.json`) and icons, written by the game at every start (`ios/src/achievements_export.cpp`) for the pre-launch screen. What is unlocked stays in the SDK's `data/achievements/454107D9.toml` |
| `settings.json` | What the pre-launch screen saves (see below). Readable and editable by hand |
| `extra_args.txt` | Optional: extra arguments, one per line (`#` for comments), to try a setting without rebuilding. Each replaces the app's own value for that option, the pre-launch screen's included. For example `--resolution=1024x768` for a 4:3 display. A leading em or en dash (iOS' Smart Punctuation turns a typed `--` into one) is read as `--`, and hyphens in an option's name as underscores (`--ios-retina` is `--ios_retina`). |
| `logs/boot.txt` | The startup trace: one line per startup step, written unbuffered, plus the reason if the process dies (uncaught exception, fatal signal). For when the app stops before the log opens |
| `vulkan_probe.txt` | The probe report |
| `data/` | Game saves and settings |
| `*.iso` | The game ISO. With more than one, the pre-launch screen picks |

To put the ISO there, copy it with the Files app or Finder into the app's
folder. Inside LiveContainer, that is LiveContainer's folder, then
`Data/Application/<the app's id>/Documents`: the log line `Report saved to ...`
shows the exact path.

## The pre-launch screen

Before the game starts, the app shows its settings and a Play button
(`ios/src/launcher.mm`): Android's setup screen, with the options that exist on
iOS, in the same sections and words. Each change is saved to
`Documents/settings.json` at once and becomes game arguments on Play
(`extra_args.txt` still comes after and wins). Reset puts every option back.

Left out, and why: Android's GPU driver import, GPU turbo and thread affinity
(Android only; iOS has its own thread priority and asynchronous submission
switches instead), the native engine's options (that engine is not in the iOS
port), the app language (English only), the gamertag (with a custom one the game
asked to sign in to Xbox Live, and yes froze it), and tilt steering and the touch
layout editor. Tilt only acts while driving, and only the native engine can
tell when that is: on Android's Xenos engine, the one iOS uses, it never turns
on.

## Extra Options

Features of the PC mod [Extra Options](https://nfsmods.xyz/mod/43)
([source](https://github.com/ExOptsTeam/NFSMWExOpts)), ported to the Xbox 360
code, in the pre-launch screen's "Extra Options" section. The mod patches PC
addresses; each feature's Xbox 360 counterpart has to be found again
(`ios/src/game_extra_options.cpp` says how, feature by feature).

| Feature | Setting | How |
|---|---|---|
| Selectable marker count | `nfsmw_marker_count`, 1-6 (2) | The four places that use "2 markers" after a rival race read the setting (`tools/ios/patch_game_extra_options.py`) |
| Purchased car limit | `nfsmw_purchased_car_limit`, 1-25 (10) | The car lot's one "fewer than 10 bought" check reads the setting (same script) |
| Remove Old Bridge barrier | `nfsmw_remove_old_bridge_barrier` (off) | At boot, two letters of the scenery group name `SCENERY_GROUP_DOOR` are changed (read-only data, made writable for it), so the barrier is never switched on |

Tools for finding them: `tools/ios/patch_ios_dump_image.py` lets the rexglue
CLI write the decrypted image (`NFSMW_DUMP_IMAGE=<file>`, run on a copy of the
manifest: never in `ios/generated/`), for the game's strings and tables.

## 4:3

Display -> Aspect ratio: 4:3 HD (1024x768) or SD (640x480). The game is told
the console has a 4:3 video mode and uses its own 4:3 path, with its field of
view and HUD layout.

At 4:3 the game draws its scene in its SD mode: mode 0 of the renderer's
table, one 640x480 strip with 2x MSAA (`ios/src/render_probe.cpp` logs the mode
and size, `[render-probe]`). That is blurry, and at Internal resolution 2x the
scaled-resolution resolves cost a lot (~26 fps in races at 1920x1440).

"Sharper 4:3 scene" (`nfsmw_sd_scene_720`, on; `ios/src/game_sd_scene.cpp`, USA
addresses) makes mode 0 one 960x720 strip without MSAA, at 1x: 720 lines like
HD, 60 fps in races on an iPad Pro M4.

| Function (USA) | What changes |
|---|---|
| `sub_824581A8`, the renderer's constructor | Mode 0's table entry: 960x720, no MSAA, strip rectangle 0,0,960,720 |
| `sub_824585E0`, sets the mode | For mode 0, the render-size words (0x82A2CF68..74) are 960/720 instead of 640/480 |
| `sub_82440D80`, the HUD's title-safe matrix | Runs with the screen size at 640x480: in SD it scales by 576/width and 448/height, which at 960x720 shrank the HUD toward the middle |

The single-pass hook (`render_targets.cpp`) only collapses the multi-strip
modes 3-5 into mode 2; it used to force every mode to 2, including the SD
mode, which scrambled the 4:3 picture.

## Why it is built this way

### The same SDK as Android, plus the iOS bits

The stock SDK already knows macOS, and on iOS `TARGET_OS_MAC` is 1 too, so
almost everything applies: CAMetalLayer, MoltenVK, 16 KB pages, the arm64
signal handler. But its codegen template emits no memory barriers on ARM64,
and hells-gate's Android patch does. So `tools/ios/prepare_sdk.py` builds the
tree the same way as Android's (it imports its steps, unchanged) and applies
the `tools/ios/` patches on top. With the same template, the generated code is
the same text as Android's.

The project's patches are applied **once** each and recorded in
`.nfsmw-ios/project-patches.applied` inside the SDK. Re-running them over a
prepared tree is not safe: `parche_tiempos` inserts its block in the middle of
`parche_fps`'s, and a re-run of `parche_fps` inserts its own again
(`redefinition of 'nfsmw_fps_invitado'`). Re-running
`tools/ios/prepare_sdk.py` is safe: it only applies what is missing.

### The iOS patches

Same rules as the project's existing ones (see
[docs/parches.md](../docs/parches.md)): exact text, block by block, they refuse
to write unless each anchor appears exactly once, idempotent, `--status` and
`--revert`. The shared engine is `tools/ios/patch_engine.py`.

| Script | What it does |
|---|---|
| `patch_ios_platform` | `REX_PLATFORM_IOS`, a sub-flag of `REX_PLATFORM_MAC` |
| `patch_ios_cmake` | Don't build the Vulkan loader or MoltenVK from the submodules; `REX_PLATFORM_IOS=1` from CMake (some files test it before including `platform.h`) |
| `patch_ios_paths` | Find the GPU plugin and MoltenVK in the app's `Frameworks/`, also inside LiveContainer |
| `patch_ios_waits` | Apple's futex (`os_sync_wait_on_address`) for the ring-space, vblank and swap waits of `parche_espera_anillo`, `parche_anillo_bloques` and `parche_vblank`, which only had a Linux branch |
| `patch_ios_pause` | `Pause()`/`Resume()` on `IGraphicsSystem`, so the app can stop the GPU emulation while in the background (iOS forbids GPU work there) |
| `patch_ios_sdl` | SDL's `uikit` video driver on iOS: the SDK forced `cocoa` on all of Apple, and the game failed with "cocoa not available" (a black screen) |
| `patch_ios_timing` | A `[ios-swap]` line in the log every 5 s: where the swap time goes (the CP's gamma pass and submit, who paints and how long, `vkAcquireNextImageKHR`, `vkQueuePresentKHR`) |
| `patch_ios_ui_tick` | Paces the UI thread's repaints (cvar `ios_ui_repaint_hz`, default 30) while a new game frame still paints at once. The SDK only paced them on Windows: on iOS the UI thread repainted the same frame up to 120 times a second, competing with the game for MoltenVK's single queue |
| `patch_ios_aspect` | An exact 4:3 mode (`--resolution=1024x768`) is reported to the game as 4:3: the SDK's `width*3 >= height*4` called it widescreen |
| `patch_ios_retina` | Cvar `ios_retina` (default `auto`): the screen layer at point resolution where the points are at least the game's 1280x720 (1600x1200 on an iPad Pro M4 with Display Zoom "More Space"), full density otherwise (an iPhone 17 Pro Max has 956x440 points). `true`/`false` force it |
| `patch_ios_qos` / `patch_ios_retire_qos` | The original main/command-thread priority promotion is retired on the battery branch. The launcher setting is removed; `ios_thread_qos` remains accepted but has no promotion effect. M4 testing held 120 FPS at 1.5x without promotion; iPhone testing also maintained 60 FPS. This establishes performance headroom in those tests, not a measured energy saving. |
| `patch_ios_utility_qos` | Battery experiment (cvar `ios_utility_qos`, default false, restart required): the game main thread and GPU command thread request `QOS_CLASS_UTILITY`, to ask for a cheaper CPU operating point like Low Power Mode. Logs `[ios] ... QoS utility set`. `ios_battery_baseline_qos` wins when both are set. October 20, IPA25; energy and frame-rate effect untested |
| `patch_ios_fault_log` | The same guest fault back to back is logged in full only 3 times, then one line at 10, 100, 1000... repeats. A stuck guest thread wrote ~100 MB in 4 s and the log's rotation lost the moment it started |
| `patch_ios_register_check` | Two per-draw costs found with Instruments' Time Profiler (attached to the running game in a police chase): the "unknown register" check on every GPU register write (a switch with static guards, 7.4 % of the GPU thread) is a table built once, and the memexport readback setting is no longer looked up by name on every draw (2.3 %) |
| `patch_ios_fps_cap` | Frame rate cap (cvar `ios_fps_cap`: 30, 40, 60, 120; pre-launch screen, Display). Counted in guest vblanks, just before each swap: a frame is not presented until N vblanks after the previous one, and a late frame does not wait. 40 and 120 run the guest vblank at 120 Hz (experimental: the game was made for 60) |
| `patch_ios_occlusion_async` | Occlusion queries (NFSMW's sun flare, one per frame) no longer make the command processor wait for the whole GPU: the game gets the last count for that query at once, the real one a frame later (cvar `ios_async_occlusion`). In free roam the CP was the limit, with one 2-7 ms GPU wait per frame |
| `patch_ios_shader_contraction` | Pixel shaders are translated without the `NoContraction` (precise) decoration (cvar `ios_pixel_shader_contraction`); vertex shaders keep it, for bit-identical positions across passes. SPIRV-Cross turned every precise operation into a `[[clang::optnone]] spvFMul/spvFAdd` call: hundreds per shader, in the shaders an Xcode replay showed using 110-174 registers and a third of a race frame |
| `patch_ios_vblank_grid` | The guest vblank makes up the vblank thread's wake-up delays of up to 2 ms instead of re-anchoring on them (cvar `ios_vblank_catch_up`): with each iOS sleep waking ~0.5 ms late, vblanks came ~17.2 ms apart and the game topped out at ~58 fps |
| `patch_ios_upload_batch` | The uploads of guest memory that `parche_subidas` moves before a render pass share one barrier pair per pass (cvar `ios_batch_uploads`), kept aside and put at the start of their pass once. A Metal frame capture of a race showed 318-522 blit encoders per frame, one per upload (MoltenVK ends the encoder at each barrier); a CPU profile then showed the per-upload `std::rotate` of the first version at 4 % of the GPU thread |
| `patch_ios_readback_limit` | With "Accurate exposure" (`readback_resolve=fast`) only resolves up to `ios_readback_max_kb` (256 KB) are read back to guest memory: the CPU needs small ones (exposure), not full-screen effects, which were 15 % of the GPU thread in a chase. A `[ios-readback]` log line every 5 s shows what was kept and skipped |
| `patch_ios_suboptimal` | A suboptimal present always recreates the swapchain (at most twice a second). A screenshot made iOS give the layer portrait bounds for a moment; the swapchain was rebuilt portrait and, suboptimal from its first present, never again: black screen with sound and input working |
| `patch_ios_surface_reattach` | Attaching a surface clears the presenter's "paint already requested" flag. A request made while the surface was detached (the app paused for another app) was dropped with the flag still set, and no paint was asked for again: black screen with sound |
| `patch_ios_paint_suspend` | While the app is paused (another app on screen) no GPU work: `nfsmw_ios_suspend_paints(bool)` stops the UI thread's paints, and every submission off the main thread waits in `nfsmw_ios_gpu_gate()` before taking the queue. The surface stays (detaching it made a new Metal view at each return), and the command processor is not suspended (`GraphicsSystem::Pause()` races with a quick resume: frozen game, or still submitting in the background) |
| `patch_ios_texture_stats` | Diagnostic (`ios_texture_stats`): every 5 s, `[ios-textures]` counts texture loads, reloads, and whether the GPU (a resolve) or the CPU outdated them, with the textures reloaded most. A Metal trace at the 120 cap showed ~45 texture uploads a frame |
| `patch_ios_narrow_invalidation` | A CPU write invalidates the 256 KB around it only up to the nearest watched ranges it does not touch (`ios_narrow_invalidation`). NFSMW writes per-frame data next to textures: the widening outdated those textures every frame (4,000-18,000 reloads every 5 s in a race, the fps falling from ~115 to ~68 with them) |
| `patch_ios_occlusion_batch` | Occlusion queries reset and copied in batches per submission (`ios_batch_occlusion`): one pool reset for up to 64 queries and one result copy per run of consecutive queries, instead of a reset and a copy each. MoltenVK made each a blit of its own: ~9 a frame, 13 % of the GPU's time in a race |
| `patch_ios_dispatch_stats` | Diagnostic (`ios_dispatch_stats`): every 5 s, `[ios-dispatch]` lists the compute dispatches by the function that recorded them (23 % of the GPU's time in a race, unlabelled in a Metal trace) |
| `patch_ios_shared_stats` | `[ios-shared]` every 5 s: CPU write faults, invalidated pages, MB uploaded (`ios_shared_stats`); and `ios_invalidation_widen_kb` (4/16/64/256, the SDK's 256): how far a CPU write's invalidation is widened. Uploading guest memory was 26 % of the GPU command thread in a race, re-protecting it 11 % |
| `patch_ios_hot_pages` | OFF by default (`ios_hot_pages`): tried on, the faults fell ~100x but the GPU took 70-75 ms a frame from ~1,500 per-draw uploads. The idea: a page that faults 4 times within a second becomes "hot": unprotected and never valid, so each use uploads it and writes to it no longer fault. Pages a watch covers (texture data) and GPU-written pages are never hot. In a race the game's dynamic buffers faulted 100-450 times a frame, each fault stopping a game thread and each upload re-protecting the page |
| `patch_ios_async_copies` | The copies of guest memory into the upload buffers run on two worker threads (`ios_async_upload_copies`), woken once per upload call; the command processor queues them and waits only before `vkQueueSubmit`, helping while it waits. The protection (`mprotect`) stays on the command processor: moving it to the workers was slower (it serialises on the address space map) |
| `patch_ios_type0_ranges` | Type-0 packets writing a range of registers use the bulk path (`ios_type0_ranges`): shader constants in one byte-swapped copy and one constant-buffer check, instead of the full `WriteRegister` per register. NFSMW writes its constants this way: ~33 % of the command processor in a race went to type-0 packets and `WriteRegister` |
| `patch_ios_resolve_stats` | Diagnostic (`ios_resolve_stats`, off): every 5 s, `[ios-resolve]` lists the kinds of resolve that cost the most EDRAM dumping (size, destination, render target, dump groups). ~8.7 M samples a frame were dumped in a race |
| `patch_ios_iso_stream` | When the ISO cannot be mapped into memory whole, it is read in pieces with `pread` (the header and directories at start, each file at its offset; `default.xex` through `ReadSync`, since the entries then say they cannot be mapped). On an iPad M1 the 7.8 GB mapping failed (with the 4.5 GB guest reservation, more address space than iOS gave the app) and the game never started. `ios_iso_stream` forces it, for testing |
| `patch_ios_texture_descriptors` | A draw with the same textures and samplers as the previous one reuses its descriptor sets (the SDK's own TODO; cvar `ios_reuse_texture_descriptors`). Every draw wrote new ones: ~15 % of the GPU thread in a chase |
| `patch_ios_vblank_display` | At the 30 and 40 fps caps the guest vblank is phase-locked to the display refresh (`ios/src/display_rate.mm`'s CADisplayLink publishes each refresh's timestamp and period), so frames are made and shown in step with the screen; the free-running vblank timer drifted against it and a frame landed a refresh late every so often. Cvar `ios_vblank_from_display` |
| `patch_ios_ui_tick_cap` | At the 30 and 40 fps caps the UI thread's idle repaint waits 1/10 s: at 1/30 s it raced the next game frame at the 30 cap (37-44 presents a second for 30 frames), and the repeat pushed real frames a refresh late |
| `patch_ios_present_pacing` | At the 30 and 40 fps caps each frame is presented with a target time one interval after the previous one (`VK_GOOGLE_display_timing`, Metal's `presentAtTime:`), and defines `ios_fps_cap` (the runtime's presenter needs it). With `ios/src/display_rate.mm` asking iOS for 120 Hz at the 40 and 120 caps |
| `patch_ios_dump_image` | `NFSMW_DUMP_IMAGE=<file>` makes the rexglue CLI write the decrypted image and exit (host tool only), for porting PC mods |
| `patch_ios_save_log` | Every save the game creates, opens or deletes, and its request for the Xbox Live sign-in screen, in the log at info level (they are debug lines otherwise, and debug drowns in the audio trace) |
| `patch_ios_touch_pad` | The touch controls' virtual gamepad is a "synthetic" device: it always plays as player 1 and never takes a slot. When it connected before an Xbox controller, the controller became player 2, which has no profile: the game asked to sign in to Xbox Live and softlocked saving a new career alias |
| `patch_ios_memory` | `mach_vm_region` through `vm_region_64` (`mach/mach_vm.h` does not exist on iOS); the guest memory as a Mach memory entry instead of POSIX shm, which the sandbox refuses |

`patch_ios_waits` edits inside blocks that three of the project's patches
inserted, because their Linux branch is there. That is safe only because the
project patches are applied once and never re-run over this tree; for the same
reason, `prepare_sdk.py --status` reports their recorded list rather than
re-checking their blocks.

### The app icon

`ios/resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png`, 1024x1024, a single
size from which `actool` makes the rest at build time (`ios/CMakeLists.txt`);
its `Info.plist` keys are in `Info.plist.in`. It is cropped from the original
artwork to the inside of its own rounded frame, since iOS applies its own mask.

### MoltenVK submissions: asynchronous

`ios_main.mm` sets `MVK_CONFIG_SYNCHRONOUS_QUEUE_SUBMITS=0` (cvar
`ios_async_submits`, default on) before MoltenVK loads. Measured on an iPad
Pro M4 in a race: every UI paint spent 12-17 ms inside `vkQueueSubmit` for a
tiny command buffer (~0.05 ms in the menus), holding the SDK's queue lock, and
the game's command processor waited 7-8 ms per frame for it. MoltenVK takes the
`CAMetalLayer` drawable (`nextDrawable`, paced by the display) only when it
encodes the work that draws to it, and by default it encodes inside
`vkQueueSubmit`. Asynchronous, it encodes on its own dispatch queue, in order.

Cvar `ios_mvk_performance` turns on MoltenVK's own profiling
(`MVK_CONFIG_PERFORMANCE_TRACKING`), summarised in the log every 300 presented
frames. On for measuring; it adds its own timing overhead.

### Settings tried, and what they did (iPad Pro M4, first challenge race)

With the presentation fixed, the GPU limits races: the command processor waits
~15 ms per frame for it, and MoltenVK reports ~20-22 ms of GPU time per command
buffer. None of the cheap switches change that:

| Setting | Result |
|---|---|
| `--render_target_path_vulkan=fsi` | Worse: 25-28 ms per frame (from ~20.7), and some UI text drawn wrong |
| `--occlusion_query_enable=false` | The game hangs at boot (all threads stop) |
| `--readback_resolve=none` | No change in time; exposure looked fine |
| `--resolution=1024x768` or `640x480` (4:3) | The game hung at boot at the time; 4:3 now works (see 4:3 above) |
| `--ios_thread_qos=false` | No measurable change (the CP mostly waits for the GPU) |

### Solved: starting the career froze the game (Black Edition patch)

Symptom (USA edition, iPad and iPhone): pressing start career, the menu music
kept playing and nothing else happened; a game thread read through a null
pointer forever.

What happens, found with temporary hooks on the game's own functions (USA
addresses):

- 0.6 s after boot, loading the global and frontend data, `sub_822CB458`
  creates 84 records of one kind. Each takes a slot of a 200-slot table
  (`sub_822C9488`) and an entry of a 75-entry pool (`sub_822C9570`, 408 bytes
  each, at table+4000). The pool runs out and the last records are silently
  dropped.
- Starting the career, `sub_822CC300` looks one of them up (key `0x38A3C42C`),
  gets null, and the caller dereferences it.
- With `--black_edition=false` there is no overflow and the career starts.

The project's Black Edition patch (`common/src/nfsmw_app.h`) sets the game's
Black Edition flag at `0x82A2CE04`, the same address for every edition in
Xenia's game-patches (which ship it disabled). On a regular disc, that content
needs more of those records than the pool holds. It is game logic, so the PC
and Android builds, which turn the patch on by default, very likely freeze at
career start too.

The fix: a pool of 150 (`ios/src/game_pool.cpp`). The first 75 entries stay in
place; the rest live in a block allocated on the guest heap. The game turns an
index into an address inline, in 31 places, so `tools/ios/patch_game_pool.py`
edits the generated code there: that call and its "index <= 75" check, plus
one reset line in `sub_822CBC00`. It is all-or-nothing and checks every place
against the exact instructions. `tools/ios/generate_code.py` runs it after the
codegen, and CMake refuses to build USA code without it. The functions that
walk the pool by pointer (init, allocate, any free, reset, room for one more)
are replaced in `game_pool.cpp`.

Black Edition is on by default again (`--black_edition=false` in
`extra_args.txt` turns it off).

### The game on iOS

| File | What |
|---|---|
| `ios/src/game_app.cpp` | The app: the same `NfsmwApp` as every platform, with CoreAudio and the background pause. The iOS `juego.cpp` |
| `ios/src/game_hooks.cpp` | The iOS copy of `ganchos.cpp`: the same hooks and addresses, with Apple's futex. Translated to the edition like Android's |
| `common/src/render_targets.cpp` | Used as is: nothing Android-specific in it |
| `ios/src/touch_controls.mm` | On-screen touch controls, on an SDL virtual gamepad: the PAD layout (a full gamepad, after the original project's Android layout) and the DRIVE layout (steering circle, pedals, nitrous, speedbreaker, handbrake, shifting on the right stick, camera, look back, reset, pause), switched by the DRIVE/PAD pill; HIDE/TOUCH hides them, and they hide themselves when a physical controller connects. Cvar `ios_touch_controls`. No layout editor or tilt steering yet |
| `ios/src/audio/coreaudio_driver.mm` | Audio: the AAudio driver's design (lock-free ring, 5.1 fold, semaphore paced by the hardware) on a RemoteIO unit, with `AVAudioSession` interruptions |

### LiveContainer

LiveContainer loads the app's executable into ITS process. Two consequences:

- `_NSGetExecutablePath()` and `@executable_path` are LiveContainer's. The SDK
  would look for the GPU plugin in the wrong bundle. `patch_ios_paths` makes
  `GetExecutableFolder()` the folder of `librexruntime.dylib` (through
  `dladdr`, like `android_main.cpp`), and the executable finds its libraries
  through `@loader_path/Frameworks`.
- The entitlements that apply are LiveContainer's, not the app's.

### MoltenVK

The exact version the SDK's `thirdparty/moltenvk` submodule pins (v1.4.1),
from Khronos' release, as `MoltenVK.framework` inside the app. It is loader
and driver at once.

## Legal

See [Legal in the README](../README.md#legal). The app built without generated
code (probe only) contains nothing from the game; built with it, it contains the
game's code and is only for your own devices.

### Combined battery experiment (battery-optimization branch)

`--nfsmw_battery_optimizations=true` (accepted working default on this branch) forces
cube destination deduplication, native bulk constant writes, geometry arena
range reuse, vertex-fetch layout caching, and compression-eligible resolve
usage on. The last two experiments remain individually inconclusive.
`--nfsmw_battery_optimizations=false` forces those five off and restores the
historical explicit main/command-thread priority above 40 FPS. At 30/40 FPS
both arms use ordinary scheduling. The launcher priority setting stays removed.

Restart between arms. The group overrides individual switches in extra_args.txt;
resolution, cap, graphics settings, diagnostics and correctness fixes remain the
same in both arms. Check `[battery-group]` at startup and individual summaries
before attributing results. This is a combined experiment, not proof of an
energy saving or a way to identify which component caused a difference.

The October 16 iPad three-lap comparison (`nfsmw_run_6_ipad.log`, off then on)
confirmed all five switches in each arm at 1.5x / 60 FPS. Across the driving
samples, median recorded GPU duration fell from 6.81 to 5.65 ms, while median
draw recording stayed at 1.87 ms. Final geometry arena reservation was 192 MiB
off versus 32 MiB on. Both held approximately 60 FPS with nominal thermal
state. These are timing and allocation observations, not a measured energy
reduction: GPU clocks were not controlled and several passes became faster.
The user reported 78% to 72% battery across the pair and accepted the combined
default. The off switch remains available for regression comparisons.

### Native game constant-copy experiment (USA edition)

`--nfsmw_native_constant_copies=true` enables two guarded float-constant copy
loops in `sub_82699100`, before the game submits its Xbox graphics commands.
It is on in the test build and independent of the five-option battery group.
Use `--nfsmw_native_constant_copies=false` and restart to compare against the
original loops while keeping the five accepted optimizations active.

The generated loops copy one to four 16-byte vectors. Their compiled ARM64
retained guest-stack counter and pointer reloads and inverse SIMD byte shuffles.
The helper copies raw vectors in the same forward order, applies the final
shuffle for the visible PPC vector register, and restores the final GPR,
condition-register, effective-address and stack-counter results. The surrounding
dirty-mask updates and integer conversions are unchanged. Physical/MMIO ranges,
wrapping ranges, stack aliases, descriptor destinations and inconsistent entry
counters take the original loops. Source/destination overlap keeps the original
vector-by-vector behavior. Constant inputs and the guest stack are owned by the
calling game thread; no synchronization operation is removed.

`tools/ios/patch_game_constant_copies.py` checks exact hashes for both original
loop bodies before writing; it supports status, idempotent application and revert.
Code generation applies it for USA, and CMake requires it for that edition.
The helper is included relative to the generated source directory, avoiding a
change to every generated translation unit's include path.

Validation: `python3 tools/ios/test_game_constant_copies.py` extracts the original
loops and compares them with the helper using the actual SDK PPC context under
AddressSanitizer and UndefinedBehaviorSanitizer. It covers all one-to-four-vector
counts and entry indices, unaligned base addresses, forward/backward overlap,
arbitrary vector bits, complete context/memory output and unchanged fallback
state (24,000 differential cases and 58 rejection cases). It also checks patch
apply/status/revert/idempotence and atomic rejection of changed or partial code.
`--benchmark` runs a local optimized ARM64 microbenchmark; two-to-four-vector
copies were faster, but one-vector copies were slightly slower. This does not
establish a device CPU or battery benefit. The earlier matching CPU trace placed
the whole function's self time at approximately 2.8% of samples, bounding the
scope of this experiment; the two loops account for only part of that time.

The first device run (`nfsmw_run_7_ipad.log`, October 16) confirmed native float
copies and the five accepted optimizations on, at 1.5x / 60 FPS. Driving held
approximately 60 FPS with nominal thermal state, no driving error entries or
GPU command failures, and 32 of 10,200 reported frames off the pacing grid.
Final geometry reservation remained 32 MiB. Relative to the on arm of run 6,
median aggregate CPU was 76% versus 73% of a core, recording 2.055 versus
1.87 ms/frame, and GPU duration 6.535 versus 5.65 ms/frame. Work was different:
the median draw count in reported frames was 2,453.5 versus 2,270, and interval
attribute-decode counts were higher. Driving duration was about 168 versus
197 seconds. These observations establish neither a saving nor a regression
from the copy helper. It remains enabled provisionally; its path coverage and
CPU benefit have not been measured on device. No visual assessment is inferred
from the log.

### Battery test cadence

Per the user's October 16 testing preference, small isolated changes receive
correctness tests and device stability/visual checks without requiring a fresh
race A/B for every increment. Plausible changes with inconclusive performance
results may remain enabled provisionally, with separate rollback switches and
local commits. Inconclusive is not recorded as a demonstrated energy saving.

Use combined A/B comparisons at meaningful milestones, with matched settings
and longer or repeated runs when practical. Opponent/traffic variation, route,
GPU clocks and different race lengths limit single-run comparisons. A batch
improvement cannot identify each member's contribution; a clear regression
still warrants isolating changes. The current master controls only the original
five changes: a future complete-batch comparison must also explicitly toggle
native constant copies (and any later experiments), or extend the master first.

### Shader texture-slot experiment

`--nfsmw_native_texture_masks=true` (on in the test build) processes only texture
slots declared or referenced by the current vertex/pixel shader pair. It is
independent of the five-option master and native constant copies. Set it false
and restart to restore the original all-16-slot behavior. No new quality setting
or reduced-resolution resource is introduced.

The shader translator exports its existing texture-instruction mask as a versioned
source comment. `tools/native/texture_masks.py` conservatively unions that with
all sampler declarations in every resource dimension and writes
`NativeShaders/texture_masks.txt`. Build packaging already copies that directory.
Missing/unsupported source metadata keeps all slots. Runtime metadata parsing
rejects malformed, duplicate or unsupported entries as a whole. Either unknown
shader stage keeps all 16 slots; an explicitly known zero mask is distinguished
from missing metadata. Hand-written vertex shaders use zero, and the hand-written
XMV pixel shader uses its three Y/U/V slots. Shadow/alpha/motion diagnostics,
native dumps, texture replacement tests, cost probes and Metal capture retain
the original all-slot behavior.

Record skips fetch comparisons and TextureOf for unused slots and marks those
draw bindings absent. It leaves the slot cache untouched until a shader needs
that slot again; the existing comparison then validates its current binding.
Resolves still invalidate every slot. The later renderer consequently avoids
handling those unused texture bindings, and resources referenced only through
unused slots need not be decoded or uploaded. Required texture sampling and
rendering passes are unchanged. Actual allocation/upload/energy benefits remain
unmeasured; removing slot work is not equivalent to removing a texture resource
that another draw still needs.

The existing 300-frame summary reports `[native] texture slots`: skipped and
considered slots, and unknown-shader draws that retained all slots. Metadata
coverage is logged at startup. Counters stay on the recording thread and are
aggregated through the existing diagnostics; no per-draw atomics or log writes.

Validation: all 101 rebuilt shader sources matched their prior source hashes
after removing only the new metadata comment, and all 101 interfaces covered
the translator's referenced slots. `python3 tools/native/test_texture_masks.py
--shaders ~/Library/Caches/nfsmw-ios/shaders/msl` checks conservative extraction,
10,000 stage-mask unions, malformed metadata and cache invalidation. It also
extracts and compiles the actual renderer slot loop and compares required texture
bindings against the original all-slot path across 20,000 draws with changing
bindings, later reuse, resolve invalidation and empty/full masks. C++ checks run
under AddressSanitizer and UndefinedBehaviorSanitizer. Device visual/stability
validation is still required before claiming the experiment is established.

First device check: `nfsmw_run_8_ipad.log` (October 16), iPad 1.5x / 60 FPS,
all previous optimizations on. The user reported no visual issues in the same
test race. All 101 exported shader interfaces loaded. Driving summaries skipped
271,996,013 of 307,678,736 texture-slot visits (88.403%), averaging 1.856 processed
slots per draw, with zero unknown-shader fallbacks. This is a reduction in slot
bookkeeping, not an 88% reduction in renderer work or energy consumption.

Driving median FPS was 60, thermal state remained nominal, and no driving error
entries or GPU command failures were logged. Three of 8,400 reported frames
were off the pacing grid. Geometry reservation stayed at 32 MiB (18 MiB live
at the final summary). The initial driving transition had a 42 ms hitch; the
earlier startup watchdog report and frontend transitions also remain present,
as in prior builds.

Compared with run 7, median recording time was 1.86 versus 2.055 ms/frame and
aggregate CPU 70.5% versus 76% of a core. However, reported-frame draw counts
were lower (median 2,301 versus 2,453.5), interval geometry decoding was lower,
and driving duration was about 137 versus 168 seconds. GPU duration's median
was lower (5.73 versus 6.535 ms) but its mean was higher (7.259 versus 6.986 ms).
No isolated CPU, GPU or battery improvement is inferred from these differences.
Keep enabled following the visual/stability check and measured slot elimination;
include it in a later complete-batch energy/performance comparison.

### CPU draw-attribute arena experiment

`--nfsmw_native_draw_arena=true` (on in the test build) gives each recorded Frame
a CPU `std::pmr::monotonic_buffer_resource` for its small attribute lists. Each
list reserves its known shader input count once. The frame's draw vector also
reserves the previous frame's draw count. It is independent of the five-option
master, native constant copies and texture masks. Set it false and restart to
restore individual attribute heap allocations, geometric list growth and no
draw-vector preallocation. Both arms use `std::pmr::vector<Attribute>`; the off
arm changes its resource to the ordinary heap and preserves the old growth
policy, rather than being a byte-identical copy of the older executable.

The arena is declared before Frame::draws and is destroyed after every draw.
Draws move without copying their attribute lists; copying or move-assigning
draws is prohibited to prevent accidental transfer between frame resources.
The frame itself remains at a stable address and passes to the serial renderer
queue through the existing unique_ptr handoff. No pool is recycled across
in-flight frames. Attribute objects still release all shared references, and
the separately allocated FloatArray data and its cache/GPU-buffer owners are
unchanged. This is CPU storage, separate from the earlier Metal geometry arena.

Previous-frame sizing is an initial hint only: attribute block hints are clamped
to 4 KiB..4 MiB and draw reserve hints to 8,192 draws. Actual storage can grow
beyond either hint without skipping data. Blocks, including abandoned draw
storage, are released when the frame is destroyed. A transition to a much smaller
frame may overreserve once; no permanent high-water reservation is kept.

`[native] CPU draw arena` logs attribute lists and upstream heap allocation
calls/bytes per submitted frame, plus the window's peak per-frame attribute
storage. Heap counters are local to each frame, with a snapshot before handoff;
there are no per-draw atomics or log writes. These counters cover attribute-list
backing storage, not decoded arrays, constant banks or draw-vector allocations.
The off arm also counts heap requests, adding a small instrumentation cost.

Validation: `python3 tools/native/test_draw_arena.py` extracts the production
allocator, Attribute, Draw, diagnostics and Frame declarations into an ARC-enabled
Objective-C++ test under AddressSanitizer/UndefinedBehaviorSanitizer. Three
3,500-draw cases compare data and ownership for individual allocations, a cold
pool and a pool sized from the previous frame. It checks vector relocation,
abandoned draws, cached payloads, Metal-object retention, render-thread destruction,
independent frames, over-alignment, block overflow and bad_alloc cleanup. In this
fixture, attribute upstream allocations were 13,121 / 7 / 1 respectively. Those
are fixture counts, not device CPU or battery measurements. The iOS IPA built
successfully; device visual/stability validation remains pending.

First device check: `nfsmw_run_9_ipad.log` (October 16), iPad 1.5x / 60 FPS,
all previous optimizations on. The user reported no visual bugs. Across driving
summaries, the median 2,425.4 attribute lists/frame used 1.00 upstream heap
allocations/frame (mean 1.0003, maximum reported window average 1.01). Median
heap bytes requested were 0.489 MiB/frame; the largest per-frame attribute
storage high-water mark was 0.881 MiB. These are device allocation counters,
confirming that thousands of individual list allocations are avoided. There
is no measured off-arm device allocation count for this run.

Driving held median 60 FPS with nominal thermal state, 21 of 9,300 reported
frames off the pacing grid, and no GPU command failures. The Metal geometry
arena stayed at 32 MiB reserved (19 MiB live at the final summary). Relative
to run 8, median recording was 1.74 versus 1.86 ms/frame and aggregate CPU
70% versus 70.5% of a core. Reported draw counts and geometry decoding were
higher, and GPU duration increased to median 8.46 ms (run 8: 5.73 ms). Driving
duration was about 155 versus 137 seconds. No isolated CPU or energy gain is
inferred from these uncontrolled timing comparisons. Keep the pool enabled
following the allocation and visual checks; include it in the batch comparison.

One watchdog dump occurred during driving at 15:32:49.609 (in addition to the
usual startup dump), then reported movement again one second later. Its claimed
five-second game stall conflicts with frames 5,701..6,001 advancing in exactly
five seconds and zero pacing misses in that interval. The watchdog in
`common/src/nfsmw_app.h` samples LR/SP/r3 once per second; unchanged samples do
not establish lack of frame progress. A false alarm is the current inference,
not a confirmed hang or a pool failure. No semaphore-recovery pushes were logged.
The 531 in-race error-level lines are this single watchdog/semaphore trace dump,
not 531 separate faults. A future diagnostic improvement should consult actual
frame progress before declaring a stall; no watchdog code changed here.

Longer session check: `nfsmw_run_10_ipad.log` (October 16, 22:18..22:37),
all eight options on, iPad 1.5x / 60 FPS. Across 163 driving summaries, median
FPS was 60 (mean 59.991), recording 2.03 ms/frame, aggregate CPU 84% of a core,
and recorded GPU duration 8.70 ms/frame. Driving workloads averaged about
2,761 draws in reported frames, so these timings are not an A/B against the
shorter races. Pacing reported 293 off-grid frames out of 48,900 (0.60%). All
thermal reports were nominal and no GPU command failures were found.

Attribute pooling stayed on with median 1.00 upstream heap allocations/frame
(maximum reporting-window average 1.01); peak per-frame attribute storage was
1.038 MiB. Texture-slot work skipped 88.079% of considered driving slots with
zero unknown-shader fallbacks. The geometry arena reached at most 64 MiB
reserved and ended with 6 MiB live / 64 MiB reserved. Process footprint reached
about 1.6 GiB and later fell to 1,455 MiB: no runaway memory growth was observed
over this session. Logged battery levels were only 100% then 95%; the coarse
readings and 100% starting point cannot establish an energy improvement.

Watchdog/semaphore dumps recur. The two largest inter-swap gaps (21.3 and
50.3 seconds) occurred after logged scene-inactive/background transitions and
outside active driving; their recording time was about 0.2 ms and renderer
wait 0..0.7 ms. Treat those regions as lifecycle/profiling interruptions when
analyzing active gameplay; the log alone cannot establish their exact cause.
No watchdog recovery semaphore pushes were logged.

The next measurement is Power Profiler on the optimized build before another
batch A/B. Installed Instruments templates include Power Profiler and CPU
Profiler. Apple's current setup guidance requires wireless debugging on battery
power for overall system power usage (charging reports zero), and a specific
process target for per-app subsystem lanes (All Processes records system power
only). Target the LiveContainer process hosting the game; the previous CPU
trace identified that host. Record Power Profiler plus CPU Profiler with fixed
brightness, scale/cap and optimization settings, and separate menu/gameplay and
background intervals. Source: [Apple Power Profiler documentation](https://developer.apple.com/documentation/xcode/measuring-your-app-s-power-use-with-power-profiler).

### First iPad power trace: CPU is the leading app subsystem

`power_profiler_1_ipad.trace` and `nfsmw_run_11_ipad.log` (October 16) were
recorded on the 13-inch M4 iPad Pro, iPadOS 27.0.1, targeting LiveContainer
PID 1259. The trace runs 23:17:05.336..23:27:42.107 (636.77 seconds).
All eight optimization switches were on; scale 1.5x, cap 60, MetalFX/FXAA off,
forced MSAA 0. Brightness was constant at 39%, thermal state nominal throughout.
System-power data is populated over 636.01 seconds, with no charging intervals.

The log marks the test race at trace time 00:44.414..03:00.198 and the
challenge-series chase at 03:12.602..10:35.044, matching the user's transition
at approximately 03:15. For steady-section comparisons, exclude five seconds
at each boundary: race 00:49.414..02:55.198, chase 03:17.602..10:30.044.
Means below weight each exported interval by its overlap with that selection;
sentinel/missing subsystem values are excluded, not treated as zero.

| Measurement | Steady race | Steady chase |
|---|---:|---:|
| Whole-device battery energy per hour | 31.52%/hr | 33.14%/hr |
| LiveContainer CPU power impact | 11.98 | 13.45 |
| LiveContainer GPU power impact | 2.41 | 2.88 |
| LiveContainer display power impact | 6.00 | 5.97 |
| LiveContainer networking power impact | 0.00 | 0.00 |
| CPU execution time / elapsed time, from QoS intervals | 0.699 cores | 0.843 cores |
| Median logged CPU, complete 10-second windows | 69% of a core | 85% of a core |
| Median logged draw recording | 1.62 ms/frame | 2.13 ms/frame |
| Median logged CPU render encoding | 1.95 ms/frame | 2.38 ms/frame |
| Median logged GPU duration | 5.87 ms/frame | 8.73 ms/frame |

The whole trace's weighted system mean is 31.93%/hr, integrating to about
5.64 battery percentage points over the covered intervals. This is a measured
system rate during profiling, not a prediction for every session or a measure
of game-only energy. The log's coarser battery readings were 90% then 85%.
Subsystem impact values are comparative scores, not watts or percentages of
total battery drain; do not add them into a percentage breakdown. Apple
explicitly permits comparing subsystems within the same device. Here CPU
impact is about 4.7..5.0 times GPU impact, with display also above GPU. This
supports prioritizing CPU work on this device/configuration; it does not
establish the same ranking on the iPhone or at higher render scales.

Time Profiler contains 85,818 ms of running sample weight in the guarded race
and 355,407 ms in the chase. The local executable UUID matches the trace
(`5C92B5DD-A428-369E-B28B-1ECB654857CB`). Useful CPU shares:

| Sampled work | Race | Chase |
|---|---:|---:|
| Recompiled guest functions, self time only | 34.96% | 36.81% |
| NativeDraw including its callees | 13.55% | 14.65% |
| Record including its callees | 11.60% | 12.34% |
| Record self time | 8.28% | 8.92% |
| RenderFrame including its callees | 15.01% | 15.16% |
| Entire dispatched NativeSwap render block | 18.38% | 18.61% |

Rows overlap: Record is under NativeDraw; RenderFrame is under the render
block. They must not be summed. Guest self excludes called native/runtime
functions, so it is not the guest thread's entire cost. Several guest threads,
the command processor and render workers all contribute. Approximately 99%
of running sample weight is on performance cores, despite baseline top QoS
being off; most QoS execution is Default. This is an observation, not evidence
that forcing background QoS or adding parallelism would save power while
preserving frame deadlines. The existing priority-off change does not force
efficiency-core scheduling.

The largest Record leaf PCs map into its inlined attribute_cache lookup.
In the UUID-matched ARM64 executable, linked addresses
`0x1000b48c4..0x1000b4b14` build the nine-field AttributeKey hash, select a
bucket, compare the full key and traverse nodes (including division for
non-power-of-two bucket counts). This range accounts for 1,926 ms / 2.24%
of race sample weight and 8,578 ms / 2.41% of chase sample weight. These are
statistical instruction-region samples, not separately timed lookup calls or
proof of a particular collision count. The source lookup is
`attribute_cache[akey]` in Record. Separately, the renderer's gpu_buffers
operator[] remains about 1.12% / 1.49% inclusive despite its existing 4,096-slot
front cache; its collision rate has not been measured. Index fingerprints and
the sampled Fingerprint function also remain visible; the current trace does
not justify weakening content validation.

Proposed next isolated experiment, not implemented: add a bounded front cache
for decoded attribute entries, with a cheap slot selector and comparison of
every AttributeKey field. Misses/collisions retain the original map lookup.
Map nodes remain stable across rehashes, but all retained pointers must be
invalidated before Sweep erases entries. Cached entry lookup must still run
the existing write-watch/fingerprint checks and last-used updates on every
access; never assume guest vertex data stays unchanged for a whole frame.
Keep an independent restart-required switch and aggregate hit/miss counters.
Expected benefit is limited to part of the measured lookup cost, not all
Record time, and no numerical battery saving is promised.

Proposed files: `ios/src/native_renderer.mm` for lookup/invalidation/switch and
counters; new `tools/native/test_attribute_lookup.py` for extracted production
code checks against the original map, collision cases, key changes, source
mutations, rehash and eviction under ASan/UBSan; this document for results.
Seek user approval before implementation. Validate correctness and cache hit
coverage first, then include the experiment in the next batch power comparison.
Broader CPU work should continue into native draw-state recording and measured
guest draw/constant-building functions; a bypass of Xbox command construction
and decoding could have a larger ceiling but has higher ordering/state risk.

Steady race log summaries all reported 60 FPS and zero pacing misses in 7,500
frames. Chase summaries all reported 60 FPS, with 416/26,100 frames off the
pacing grid (1.59%); a 60 FPS average does not imply every interval is uniform.
Pooling remained at 1.00 upstream attribute allocations/frame, unknown shader
mask fallbacks were zero, geometry reservation reached 64 MiB, and no GPU
command failures were logged. The three watchdog dumps were two in startup
and one at 23:28:45 after the trace and after entering the pause menu; none
occurred during the recorded race or chase. Menu auto-cap was disabled in this
configuration, so the menus also ran at 60; the existing optional 30 FPS menu
cap remains relevant to normal play but cannot explain active-race drain.

Tooling note: the bundled Power Profiler template's Network Connections
analyzer crashed Instruments on the Mac three times in
`NetworkConnectionStatsModeling.receive(row:writer:context:)`. Removing Network
Connections, Metal Performance Overview and Location Energy Model left Power
Profiler, Thermal State and Time Profiler; the user then successfully recorded
this trace. Instruments' wireless discovery also disagreed with Device Hub;
connecting by cable, selecting the device, then unplugging allowed recording.
This is a profiling-tool workaround, not a game change. No new IPA was built.

### Optional Utility QoS for native CPU rendering

Following the power trace, the user approved a separate scheduling experiment
before the proposed attribute-cache change. `--nfsmw_native_render_utility=true`
assigns QOS_CLASS_UTILITY to the existing serial `nfsmw.native` Dispatch queue
when it is created. The switch defaults false, is independent of the previous
eight options and the five-option master, and requires a full game restart.
False preserves the original unspecified queue attributes and ordinary QoS
inheritance. There is no automatic frame-cap or thermal policy in this switch;
initial device testing is at 60 FPS, not 120.

Only the queue executing RenderFrame and its normal cleanup changes priority.
The guest main thread, Xbox command processor, audio and pipeline-compilation
queues are unchanged. Shader work still executes on the GPU. The same unique_ptr
handoff, serial ordering, in-flight limit, GPU resource lifetimes and pacing
waits remain. No visual settings or rendering commands change. This requests a
scheduling class, not efficiency-core affinity, and does not guarantee an
energy saving or that frame deadlines will still be met.

The installed iOS SDK's `dispatch/block.h` specifies that ordinary asynchronous
blocks use an explicitly specified queue QoS before their normally inherited
submitter QoS. The existing dispatch_async block therefore needs no extra
wrapper or priority manipulation. System promotion can still occur for
dependencies. A new startup line reports the requested queue mode, and
`[native] render scheduling` reports counts of observed worker QoS classes at
non-dump frame entry, in the existing 300-frame summary. The counters are local
to the serial render queue; qos_class_self is read once per frame in both arms,
not per draw. Entry samples are not whole-frame QoS or core-residency metrics.

Validation: an ARC-enabled macOS harness extracted the production queue
initializer and frame-handoff block, submitting from User Initiated QoS.
Under ASan/UBSan, each arm processed 2,000 frames in serial order with frame
owners released. The legacy queue reported unspecified configured QoS and
2,000 User Initiated entries; the experiment reported configured Utility and
2,000 Utility entries. This verifies Dispatch QoS selection and the handoff on
the host, not on-device core placement or performance. The Release iOS IPA
built successfully with the existing SDK/UIKit warnings.

Test IPA: `ios/build/NFSMW-battery-render-utility-15.ipa`. Enable the switch
alongside the previous eight options, at iPad 1.5x / 60 FPS and fixed brightness.
First check gameplay/pacing and effective entry QoS. Use the working minimal
Power Profiler setup and the run-11 race/chase pattern to compare CPU/GPU/display
impact, system energy rate and Time Profiler P/E-core residency. Compare
ordinary frame timing and hitches as well as average FPS. Run 11 is the current
optimized baseline; a new off-arm run is useful only if conditions changed or
the power difference is too close to separate from run variation. Roll back
this experiment with false and restart. Device validation is pending.

First attempted device check: `nfsmw_run_12_ipad.log` and
`power_profiler_2_ipad.trace`. This is another baseline run, **not a Utility
QoS result**. The trace's NFSMW binary UUID is
`5C92B5DD-A428-369E-B28B-1ECB654857CB`, matching draw-arena IPA 14 and run 11;
the new Utility IPA 15 contains `083A8A88-7DEF-3614-A916-CB4666564E9A`.
The log likewise reports the old renderer build (October 16, 15:27:36), with
neither the new render-queue startup line nor the frame-entry QoS summaries.
Why LiveContainer loaded the previous executable is not established. The
Utility switch's effect, core placement and performance remain untested.

The trace runs 23:44:32.357..23:54:33.457 (601.10 seconds). Brightness is again
39% and thermal state nominal. Driving transitions are at 00:28.231 and
02:52.682, consistent with the user's approximately 02:55 pursuit start.
With guarded race selection 00:33.231..02:36.388 and pursuit selection
02:57.682..09:56.100, weighted system rates are 31.54%/hr and 33.03%/hr;
CPU/GPU impact scores are 11.83/2.44 and 13.38/3.01. The whole trace's
available system intervals average 31.94%/hr, versus 31.93%/hr in run 11.
These are repeated baseline observations under similar conditions, not an
energy gain or an estimate of the comparison's statistical error. Do not
attribute any difference to the unexecuted scheduling change. Verify a short
startup log from IPA 15 with Utility requested on before another long trace.

Confirmed Utility device check: `nfsmw_run_13_ipad.log` and
`power_profiler_3_ipad.trace`, October 16 23:57 through October 17 00:09.
The trace runs 23:57:59.469..00:08:27.943 (628.47 seconds), targeting
LiveContainer PID 1284. NFSMW UUID is the expected
`083A8A88-7DEF-3614-A916-CB4666564E9A`, renderer build 23:41:43. Queue startup
reports Utility. All 40,201 frame-entry QoS samples across the entire game log
report Utility, with none in the other classes. Prior eight options remain on;
1.5x / 60 FPS, MetalFX/FXAA off, forced MSAA 0, brightness fixed at 39%,
thermal state nominal, and no charging intervals in the trace.

The race starts at trace 00:23.528 and exits at 02:42.472; the pursuit starts
at 02:52.498, agreeing with the user's approximately 02:55. Guarded selections
are race 00:28.528..02:37.472 and pursuit 02:57.498..10:23.474. System and
subsystem means use duration-weighted interval overlap as in run 11.

| Measurement | Baseline run 11 | Baseline run 12 | Utility run 13 |
|---|---:|---:|---:|
| Race system energy rate, % battery/hr | 31.52 | 31.54 | 31.85 |
| Pursuit system energy rate, % battery/hr | 33.14 | 33.03 | 32.66 |
| Entire trace system energy rate, % battery/hr | 31.93 | 31.94 | 31.90 |
| Race CPU power impact | 11.98 | 11.83 | 10.44 |
| Pursuit CPU power impact | 13.45 | 13.38 | 11.95 |
| Race GPU power impact | 2.41 | 2.44 | 2.77 |
| Pursuit GPU power impact | 2.88 | 3.01 | 2.41 |
| Race CPU execution / elapsed, core equivalents | 0.699 | 0.696 | 0.842 |
| Pursuit CPU execution / elapsed, core equivalents | 0.843 | 0.848 | 1.049 |
| Race median logged CPU encoding, ms/frame | 1.95 | 1.90 | 4.78 |
| Pursuit median logged CPU encoding, ms/frame | 2.38 | 2.47 | 5.82 |

Time Profiler directly confirms core migration: 99.967% of the dispatched
NativeSwap render block's running sample weight is on E cores during the race,
99.973% during the pursuit. In run 11 it was predominantly on P cores (only
0.478% on E cores during the pursuit). The game main thread and NativeDraw
recording remain almost entirely on P cores in run 13. Across the entire app,
E-core sample shares rise from 0.67% / 0.98% in run 11's race/pursuit to
36.42% / 36.21% in run 13. Those are shares of sampled CPU execution time,
not percentages of original work or battery energy. CPU time grows when the
same work executes more slowly. The render block's sampled CPU time per second
increases from approximately 125/153 ms in run 11 to 306/379 ms in run 13.

The scheduling request therefore achieves its immediate purpose. Its energy
benefit is not established: CPU impact is about 12% lower in the race and 11%
lower in the pursuit relative to the mean of the two baseline selections, but
whole-device power is about 1.0% higher in the race, 1.3% lower in the pursuit,
and nearly unchanged over the full recordings. Impact scores are not additive
watts, and workload differences remain. Median reported draw counts are
2,423/2,376/2,219.5 for the races and 2,668/2,751/2,700 for the pursuits.
Longer E-core execution can offset lower instantaneous power, but this trace
does not establish the cause of the nearly unchanged system energy rate.
Do not call it an 11..12% battery improvement or infer GPU energy savings from
the shorter recorded GPU durations (race/pursuit medians 4.085/4.27 ms).

Race summaries report 60 FPS, with 4/7,800 frames off the pacing grid. Pursuit
summaries have median 60 FPS, mean 59.999, minimum 59.9, and 49/26,700 off-grid
frames (0.18%). This run sustains approximately 60 FPS despite the encoding
slowdown. Better pacing than these baseline runs is observed, not isolated
proof that Utility improves pacing. The log has no GPU command failures;
attribute allocations stay at 1.00/frame, unknown shader-mask fallbacks are
zero, and geometry reservation reaches 64 MiB. Three watchdog dumps during
the recorded gameplay again conflict with 300 rendered frames advancing in
five seconds at surrounding summaries; they do not establish a stall.

Keep Utility as an optional, provisional 60 FPS experiment; it remains false
by default. No 120 FPS conclusion follows from this test, since the encoding
slowdown consumes much more of an 8.33 ms frame budget. No iPhone or 30 FPS
energy result exists yet. The next recommended implementation remains removal
of measured attribute-cache lookup work, pending user approval, before lowering
another frame-critical thread's QoS. No renderer code or new IPA changed while
analyzing run 13.

### Optional decoded-attribute entry lookup cache

The next approved isolated experiment is
`--nfsmw_native_attribute_lookup=true` (false by default, restart required).
It is independent of the previous optimization switches, including Utility
scheduling and the five-option master. Record still builds the identical
AttributeKey, then looks up the live CacheEntry through an 8,192-slot,
two-way cache in front of the original unordered_map. A cheap set selector
uses address, stride, offset, lowest vertex and vertex count; every hit
compares all nine identity fields, including format, endian, integer and
component remapping. Selector collisions are allowed and do not share data.
Each set replaces its least recently hit slot; a miss uses the original map.
The fixed table occupies 416 KiB on the arm64 host (4,096 sets of 104 bytes).

Retained pointers refer to unordered_map entries, whose addresses survive
rehashing. SweepAttributeCache clears the entire lookup table before the
existing periodic sweep can erase any entries. Both operate on the recording
thread, with no new synchronization. In-flight draws and GPU caches continue
owning their decoded arrays independently through the existing shared_ptrs.
This cache owns no decoded payload and adds no Metal resource operation.

Only entry lookup is bypassed on a hit. The existing last-used update,
write-watch checks, fingerprints, cache mutation/decode behavior, and fresh
attribute handling still execute. The Record source body from the last-used
update through attribute decoding was checked byte-for-byte against its
pre-change version. In particular, the cache never assumes that guest vertex
bytes remain unchanged within a frame. Off takes the original map lookup,
with the new bypass counter and switch check; it is not a byte-identical copy
of the older executable. Logs add `[native] attribute lookup` hit, miss and
bypass counts through the existing per-frame diagnostics and 300-frame summary,
without per-draw atomics or log writes.

`python3 tools/native/test_attribute_lookup.py` extracts production key,
hash, lookup, fingerprint, CacheEntry and sweep code into a standalone C++
harness and runs each launch-switch arm under ASan/UBSan. It checks all key
fields, deliberately colliding formats, original-map identity, node stability
through rehash, live-entry changes after source mutation, survivor/erased node
handling at actual sweep boundaries, reinsertion and retained array ownership.
Another 90,000 changing-key operations with immediate reuse and periodic
sweeps execute 180,000 accesses per arm; all checks passed. The enabled run
recorded 110,719 hits and 69,281 misses; the disabled run recorded 180,000
bypasses. Source mutation checks use the actual fingerprint and entry, not the
complete GPU/Record path, which still requires device validation.

The optional `--benchmark` harness mode runs a fixed 4,096-key host workload
with 3,686,400 timed accesses. One Release run took 68.66 ms off and 64.57 ms
on, with identical checksums. Including warm-up, the enabled fixture recorded
2,615,400 hits and 1,075,096 misses. These are synthetic host observations,
not an estimate of game CPU or battery improvement. Device key locality and
the miss overhead can differ; inspect the new hit counters before deciding
whether the table is useful. Expected benefit is confined to part of the
previously measured 2.2..2.4% lookup region, not all draw preparation.

The Release iOS build passed with the existing SDK/UIKit warnings. Test IPA:
`ios/build/NFSMW-battery-attribute-lookup-16.ipa`. Keep
`--nfsmw_native_render_utility=true` alongside the new lookup flag at iPad
1.5x / 60 FPS, so run 13 remains the scheduling baseline. First request the
usual two-lap race and game log for hit coverage, pacing and visual/stability
validation; defer another long power trace until more changes are stacked.
The lookup experiment can be disabled independently with false and a restart.
No graphics settings, shaders, command ordering or scheduling policy changed
in this experiment. Device validation is pending.

First device check: `nfsmw_run_14_ipad.log`, October 17 00:19..00:22. The user
reported no bugs. Renderer build is 00:16:30; lookup reports on with zero
bypasses and Utility scheduling remains on. The previous eight options and
1.5x / 60 FPS, MetalFX/FXAA off, forced MSAA 0 remain as in run 13.
The test race runs 00:20:12.391..00:22:32.022 (139.631 seconds). For steady
comparison, exclude five seconds at either end, as in earlier analyses.

The guarded driving summaries record 54,117,077 front-cache hits and 6,404,571
map fallbacks: 89.418% of lookups bypass the map. Across all driving summaries,
the counts are 57,179,059 hits / 6,845,653 misses (89.308%). These are reductions
in attribute-entry map lookups, not percentages of CPU or energy saved. The
device cache locality is better than the synthetic host benchmark's fixture.
Existing fingerprints, source validation and decoding remain active.

| Guarded race measurement | Run 13, lookup off | Run 14, lookup on |
|---|---:|---:|
| Median recording, ms/frame | 1.475 | 1.360 |
| Mean recording, ms/frame | 1.486 | 1.392 |
| Median logged CPU, complete 10-second windows | 82.5% of a core | 80.5% of a core |
| Median CPU encoding, ms/frame | 4.780 | 4.675 |
| Median GPU duration, ms/frame | 4.085 | 4.085 |
| Median draws in reported frames | 2,219.5 | 2,353.5 |
| Mean decoded attribute elements/reporting interval | 3,167,426 | 3,317,293 |
| Reported average FPS, median and mean | 60 / 60 | 60 / 60 |
| Frames off pacing grid | 4 / 7,800 | 39 / 7,800 |

The recording/CPU observations are encouraging, but the race workload differs:
reported draw counts and mean decoded elements are higher in run 14, while
median decoded elements are lower. Do not claim an isolated 7.8% recording
gain or an energy improvement from this single uncontrolled comparison.
Pacing is somewhat less uniform than run 13 (0.50% versus 0.05% off-grid in
the guarded selections) while average FPS remains 60; no visible stutter was
reported, and the log does not establish that the lookup cache caused this.

There are no error-level entries during driving and no GPU command failures.
The only watchdog/semaphore dump is during startup. All 54 logged thermal
reports are nominal. All guarded frame-entry QoS samples remain Utility;
attribute allocations are 1.00/frame, shader-mask fallbacks are zero, and
geometry reservation stays 32 MiB (at most 25 MiB live across driving reports).
Retain the lookup switch enabled for subsequent stacked tests following the
correctness check and measured lookup elimination. Its default remains false
pending broader validation. A long power trace is deferred to the next batch
comparison; no additional code or IPA changed while analyzing this log.

### Next CPU targets after attribute lookup validation

Read-only source/instruction investigation on October 17 found a game-code
lead distinct from the previously optimized constant copies. In the original
P-core power trace, sub_82453768 has 1.635% race self time (1.573% weighted
over the guarded race and pursuit together). Its generated function in
`ios/generated/default/nfsmw_recomp.109.cpp` contains transform/matrix work,
647 source lines, and calls later routines to update/upload game state.
Its arithmetic already compiles to ARM NEON instructions; replacing SIMD
syntax alone is not evidence of a useful optimization.

The UUID-matched baseline executable's function has five FPCR writes. Four
correspond to two disableFlushModeUnconditional / enableFlushModeUnconditional
pairs surrounding scalar lfs/stfs sequences, between vector operations. The
first scalar region loads one float, converts it to double in the guest FPR,
then converts/stores it as float to the guest stack. The second does that for
three floats. Those source regions are at function-relative lines 313..350
and 393..413. The generator's required scalar/vector floating-point behavior
must be preserved; globally deleting mode switches or enabling fast-math is
not proposed.

Across the guarded race/pursuit, the function has 6,942 ms of self sample
weight. Five hot leaf PCs immediately after FPCR writes account for 4,649 ms
of it (~67%): linked addresses 0x101fdfde4, 0x101fdff88, 0x101fe0178,
0x101fe0274 and 0x101fe0920. This implicates floating-point mode transitions
as a useful hypothesis, but statistical PC attribution does not separately
time FPCR writes, prove pipeline-stall causality or establish the recoverable
cost. The entire function's self share bounds the direct opportunity here.

Recommended next experiment, not implemented: investigate guarded native
scalar-transfer paths in just these two regions, seeking to avoid mode
round-trips where the loaded values can be proven unaffected. Preserve guest
FPR values, memory access order, final control state and exact outputs, with
the original generated sequence retained for unsupported values, address
ranges or aliases. NaNs, subnormals, rounding modes and exceptional cases
require differential validation; they are not implicitly safe. Benchmark the
actual original block and candidate locally before producing another device
build. This is a focused generated-code patch, not a rewrite of the whole
transform function or a claim that most guest CPU time can be eliminated.

Proposed implementation files, subject to approval: new
`ios/src/game_transform_copies.h`, `tools/ios/patch_game_transform_copies.py`
and a standalone differential test under `tools/native/`; integrate the
idempotent codegen patch in `tools/ios/generate_code.py`, validate/register it
in `ios/CMakeLists.txt`, and expose an independent switch in
`ios/src/ios_main.mm`. Exact patch boundaries must be validated against the
known generated code. No generated source has been modified in this audit.

Other ranked directions:
- Renderer resource/state bookkeeping: gpu_buffers operator[] still takes
  1.12% of baseline race samples, or 1.55% in the Utility run, despite an
  existing 4,096-entry direct cache. Measure that cache's hit/collision coverage
  before changing it. Per-draw shared constants, active-input lookup, ARC and
  shared ownership also remain visible; their combined shares are not all
  known to be avoidable. CPU encoding duration includes drawable waits.
- Further constant/state-building fast paths: sub_82699100 is the largest
  individual guest leaf (~2.96% baseline race self), but the two short copy
  loops are already patched. Current hot instructions include descriptor/
  safety validation and dirty-state updates. Expanding small-copy patches
  without measuring their guard and fallback cost is not justified.
- Larger architecture: bypass selected Xbox draw/state packet construction
  and the corresponding command decoding, delivering equivalent native draw
  snapshots. This has a potentially broader ceiling but unmeasured savings
  and substantially higher state-ordering, query/fence/writeback risk. The
  existing native_cp=false bring-up path does not itself eliminate packet
  construction; it also parses the guest ring. Do not present that flag as a
  shortcut to a native game loop.

CPU shares are work performed, not proof of waste. Changing core scheduling
does not remove these instructions. No renderer/game patch or new IPA was
made during this investigation; await approval for the focused transform
transfer experiment.

### Guarded transform scalar transfers (IPA 17)

After approval, implemented the two-region experiment above, limited to USA
sub_82453768. `ios/src/game_transform_copies.h` handles the one-float and
three-float transfers. For finite normal binary32 values and signed zero it
constructs the exact binary64 guest FPR bits using integer operations, then
stores the original binary32 bits. This avoids two FPCR round-trips (four
writes) on the supported path; the function's initial vector-mode enable and
all matrix arithmetic remain generated code. This is not fast-math.

Subnormals, infinities and NaNs keep the original scalar conversions with
flush mode disabled. Ordinary, aligned guest source/destination spans are
required; MMIO, physical aliases, boundary-crossing or unaligned spans retain
the untouched inline generated sequence. Overlapping ordinary spans are
supported: each source is loaded once, in original order, before any scalar
destination store. The helper reuses those words for exceptional conversions,
so falling back for a value does not reread memory. In the three-float helper,
loads precede FPR conversion; those local FPR updates have no intervening
observer/call in this region. This relies on the runtime's existing disabled
FP-exception policy. It preserves exception status flags, guest FPRs, temporary
register bits, rounding/control state, final flush mode and memory outputs.
The first region's interleaved GPR changes and vector stores are unchanged.

`tools/ios/patch_game_transform_copies.py` checks the complete original
function SHA256 before adding guards and conditional vector-mode restores.
It provides apply/status/revert, rejects duplicate definitions and partial or
modified patches, and validates everything before writing. Codegen integration
is in `tools/ios/generate_code.py`; `ios/CMakeLists.txt` requires the validated
patch for USA builds. Generated sources remain ignored. No SDK source change.
`ios/src/ios_main.mm` defines/logs the independent, restart-required switch
`--nfsmw_native_transform_copies=true`, default false, separate from the
five-option group. No per-transfer logging or counters were added.

Validation using `python3 tools/native/test_transform_copies.py`:
- 122,112 differential region cases under ASan/UBSan, both enabled and disabled
  arms, using the real SDK context and extracted actual generated regions.
- Compared every guest register, temp/ea, all fixture memory, ordered scalar
  read/write addresses and values, hardware FPCR and FPSR. Included the first
  region's interleaved operations and the next vector arithmetic instruction.
- All four rounding modes, default-NaN on/off, preexisting exception flags,
  signed zero, all normal exponents and mantissa boundaries, subnormals,
  infinities, quiet/signaling NaNs, random bit patterns and source/destination
  overlap. Rejected address cases leave state and memory untouched.
- Real patch CLI apply/idempotence/status/revert and failure atomicity passed.

The -O3 `--benchmark` run also passed the differential cases. With alternating
measurement order, the actual original one-float region plus its interleaved
operations took 33.95–36.51 ns, candidate 5.92–7.37 ns; the three-float region
plus its following vector instruction took 38.15–43.02 ns, candidate
5.04–6.07 ns on the host Mac. This fixture includes address/representation
guards and temporary/register updates. These are local microbenchmarks of
normal-input regions, not whole-function, device or energy improvements.
Unsupported-value paths and real hit coverage have no performance claim.
The linked iOS executable was inspected: the switch/guards and exceptional
mode-write paths remain; the compiler outlines the three-float helper.

Build `cmake --build --preset ios --target ipa -j 6` passed. IPA ZIP CRC and
strict deep codesign verification passed; all 104 Metal libraries match IPA16.
`ios/build/NFSMW-battery-transform-copies-17.ipa`:
UUID `1B58A18F-1922-3760-8D2A-3555A8134162`, SHA256
`d7ee984fd8951271585f65529fa4bf88de4e0b93539d7dadf62d6e78f07500cb`.
Device validation pending: retain the previous tested settings/switches,
add `--nfsmw_native_transform_copies=true`, run the usual two-lap iPad race
at 1.5x / 60 FPS and send the game log plus any visual/stability issues.
No separate long power A/B is requested for this small addition. Keep it
experimental until device validation; do not stack another code change first.

### Transform transfer device validation (run 15)

`nfsmw_run_15_ipad.log` (October 17, renderer build 00:36:25, IPA17) confirms
`[transform-copies] native scalar transfers on`. The previous five-option
group, constant copies, texture masks, draw pool, Utility rendering and
attribute lookup remain enabled. The user reports no issues so far. Settings
are still 1.5x, 60 FPS, MetalFX/FXAA off, game MSAA.

Driving spans 00:39:36.603–00:41:50.904 (134.301 s). Removing five seconds at
each end and using only summaries whose complete approximate interval lies
within that window gives 23 five-second renderer summaries and 11 ten-second
CPU summaries. Run 14 was recomputed with this same full-interval rule (25
renderer summaries, 12 CPU summaries); its previous documented renderer
figures included the first partially overlapping summary, explaining the
small difference from those earlier figures.

| Metric | Run 14 (transform path off) | Run 15 (on) |
|---|---:|---:|
| CPU mean, % of one core | 83.58 | 83.55 |
| CPU median | 80.5 | 82 |
| Main guest-thread mean, % of one core | 14.17 | 13.64 |
| Recording median, ms/frame | 1.35 | 1.45 |
| Encoding median, ms/frame | 4.66 | 4.76 |
| GPU median, ms/frame | 4.07 | 4.11 |
| Draws/frame mean | 2,357 | 2,261 |
| Decoded attribute elements/summary mean | 3,193,785 | 3,014,712 |
| Reported FPS, min/median/max | 60/60/60 | 60/60/60 |
| Frames off the pacing grid | 39/7,500 | 0/6,900 |
| Attribute lookup hit rate | 89.53% | 89.71% |

All 52 thermal observations in run 15 are nominal. No driving error lines or
GPU command failures were found; the watchdog/semaphore dump is confined to
startup before the race, consistent with prior runs. The user saw no visual
issues. Better pacing in this single run is not attributed to this patch.

This passes the initial device correctness check, but whole-app CPU use is
essentially unchanged and the workloads/routes differ. The recording metric
measures the renderer rather than this guest transform function, so its small
increase does not separately time the new code. Neither a device CPU win nor
a battery saving has been established. Keep the transform switch enabled for
subsequent stacked tests, with its default still false. Local differential
and microbenchmark results remain the evidence for equivalence and potential
savings; there are no on-device fast/fallback coverage counters. A later
matched Time Profiler comparison can inspect sub_82453768 and the outlined
helper, while a cumulative power comparison tests actual energy benefit.
No new source change or IPA was made for this log analysis.

### Renderer bookkeeping audit after run 15 (read-only)

The next audit found avoidable diagnostic preparation in RenderFrame, distinct
from logging itself. This does not contradict the earlier observation that
normal log volume is small. No renderer source or generated code was changed.

Concrete source findings in `ios/src/native_renderer.mm`:
- Around 4852, do_resolve unconditionally formats and appends a detailed
  resolve description to `diagnostics`. Its consumer at the end of the
  function is snapshot-only, after the non-dump return around 6682.
- `resolve_names` / `resolve_rects` are filled for kept resolves, assembled
  cubes, copied resolves, views and crops (roughly 4666, 4891, 5119, 5765).
  Their consumers around 6721–6746 save snapshot PNGs after that same return.
  The resolve-name formatting and metadata allocations have no normal-frame
  output. The actual resolve textures and copies remain required.
- `heap_object` around 4639 is a strong-reference vector sized to heap capacity
  and populated with the frame's textures and subsequent resolve/view objects.
  Its only readers are inside the dump-only watched-texture block around 5926.
  This is additional snapshot ownership/bookkeeping. `textures`,
  `resolved_textures`, `assembled_cubes`, `volumes`, `cubes` and the actual GPU
  completion/resource lifetimes must remain intact. In particular,
  `resolved_textures` is also enumerated for useResources and must NOT be
  treated as snapshot-only merely because its name parallels resolve_names.
- The `skin` predicate around 5879 updates `watched_seen[d.ps_key ^ 1]` on
  qualifying ordinary draws, although its consumer is dump-only around 5926.
  Guarding it with dump preserves all snapshot behavior while avoiding normal
  texture inspection and map updates/allocations.
- The formatted main-pass label around 5434 is evaluated before profile_pass
  checks `profile` / label capacity around 4743. Constructing that label only
  when a timestamp sample will be recorded preserves profiler functionality.
  Do not remove the Metal pass itself or its required state/resource calls.

Existing profiles still support GPU buffer lookup as a separate measured
lead. Recomputed self shares for gpu_buffers operator[]: baseline race 1.122%,
chase 1.487%; Utility race 1.543%, chase 1.950%. ActiveAttributes is only
0.023–0.062%, a lower priority. These are different CPU-time denominators,
not energy percentages, and the profiles predate the last two small patches.

Instruction inspection used the UUID-matched baseline binary. Within
operator[] at linked 0x1000a212c, race/chase samples total 963/5,284 ms.
0x1000a220c accounts for 720/4,143 ms, and 0x1000a21ec for 107/562 ms.
These PCs are in bucket-chain hash/key checking, before the node-creation
block at 0x1000a2254. This strengthens the lookup hypothesis; sample skid and
child-function allocation cost prevent treating it as exact lookup/creation
accounting or a per-call hit/miss ratio. The linked libc++ pointer hash mixes
pointer bits; do not assume std::hash<void*> is the identity operation.

GpuBufferFor already has a 4,096-slot direct cache using pointer bits 4..15.
Keys 64 KiB apart map to the same slot regardless of higher address bits.
That proves the alias pattern, not its frequency on device. It currently has
no hit/miss counters. Full pointer equality, stable map nodes, g.keep,
last_submission updates, GPU completion checks and SweepGpu invalidation are
correctness requirements for any replacement. Two-way/full-pointer-mixed
lookup caching is a candidate, not yet a justified winning policy.

A third source lead is residency-list assembly around 5440: every new render
encoder rebuilds a flattened list by enumerating five Objective-C arrays,
then appends dummy_array/data and calls useResources. Base texture/volume/cube
arrays stop growing before the draw loop; resolved_textures and
assembled_cubes only grow during it. Reusing a flattened list when collection
counts are unchanged could remove rebuilding while preserving the required
useResources call on every encoder. Its CPU cost is not isolated in the
current profile; do not skip resource declarations across encoders.

Recommended next approved scope: restrict snapshot-only metadata preparation
and pass-label construction to frames that consume them. One renderer source
file; optional independent restart-required switch if retaining a direct
comparison arm. Validate snapshot-on behavior and actual ARC ownership, then
run the usual short correctness race before another source change. This
removes proven unnecessary work, with an unmeasured and likely modest total
CPU/power benefit. It is not a claim that diagnostic scaffolding dominates
the game's battery drain. Separately, lightweight GPU-buffer front-cache
hit/collision/missing-entry counters would resolve the next cache-policy
question; instrumentation needs approval before implementation. No new build
or source modifications were made for this audit.

### Lazy snapshot diagnostics (IPA 18)

After approval, implemented the audit's diagnostic cleanup in
`ios/src/native_renderer.mm`. Independent restart-required switch
`--nfsmw_native_lazy_diagnostics=true`, default false, outside the original
five-option group. `prepare_snapshots = dump || !lazy_diagnostics` preserves
the old preparation when disabled and always prepares metadata on actual
snapshot frames. The normal-frame summary logs whether preparation is active
or skipped. No GPU-buffer cache policy/instrumentation change was included.

When enabled on ordinary frames:
- Do not allocate/populate the diagnostic heap_object strong-reference table.
- Do not format/store unused resolve descriptions, resolve PNG names or rects.
- Short-circuit the snapshot skin/watched_seen predicate before texture
  inspection or counter-map insertion.
- At all seven profile_pass call sites, only construct labels if profiling is
  active and its 255-label capacity has space. Keep all profiling timestamps
  and label ordering on sampled frames. new_blit and profile_labels lifetime
  management remain unchanged.

Actual Metal texture creation, copies, heaps, binding indices, required
textures/resolved_textures/assembled_cubes/volume/cube ownership arrays,
useResource/useResources calls, GPU completion handlers, pooling, reclamation
and submission remain unchanged. The extra diagnostic references previously
ended at RenderFrame return, so removing them does not shorten a GPU-completion
retention period. This eliminates proven unused preparation; its whole-app
CPU and energy benefit has not been measured.

`python3 tools/native/test_lazy_diagnostics.py` passed under Objective-C ARC,
ASan and UBSan, comparing extracted production bookkeeping against pre-change
commit de599a6. It checks all five resolve metadata variants, resolve
description, heap lookup writes and skin-counter state. Snapshot-on metadata
matches with either switch setting; the disabled ordinary arm matches the
old path; enabled ordinary frames leave this metadata empty. Real NSObject
weak-reference/deallocation checks show all fixture textures remain alive
without diagnostic references until the original frame-local ownership lists
are released, then deallocate. Sampled main-pass labels match with profiling
on/off and initial counts 0/254/255/256. Required texture ownership,
residency and submission statement sequences also match the old source.
This host fixture submits no GPU work and does not exercise the full iOS
PNG-writing or GPU-retention path; device PNG output has not been tested.

The iOS IPA build, ZIP CRC and strict deep codesign checks passed. All 104
Metal shader libraries are byte-identical to IPA17.
`ios/build/NFSMW-battery-lazy-diagnostics-18.ipa`:
UUID `27AD258B-5C3B-3A9A-B4B1-632AF439C10C`, SHA256
`eb8f8b0912567d6e3d9d504faf5d62306bef7f4722fe17ddd63b41ba12b64e65`.
Device correctness pending: keep prior arguments/settings, add
`--nfsmw_native_lazy_diagnostics=true`, run the usual two-lap iPad race at
1.5x/60 FPS, and send its log plus any visual/stability observations. No long
individual power A/B requested. Await device validation before another code
change or any decision to enable by default.

### Lazy diagnostics device log (run 16)

`nfsmw_run_16_ipad.log` confirms renderer build October 17 00:49:53 (IPA18)
and 33 summaries reporting lazy diagnostics on / snapshot-only preparation
skipped. The older 00:36:25 startup build string belongs to unchanged
`ios_main.mm`; it does not identify this incremental renderer build as IPA17.
The transform path, attribute lookup, Utility queue and previous battery
options remain enabled. Scale is 1.5x, cap 60, MetalFX/FXAA off, game MSAA.

Driving spans 01:08:37.588–01:10:53.469 (135.881 s). As for run 15, exclude
five seconds at each end and include only summaries whose complete approximate
interval is inside the guarded window: 24 renderer and 12 CPU summaries.

| Metric | Run 15 (lazy diagnostics off) | Run 16 (on) |
|---|---:|---:|
| CPU mean, % of one core | 83.55 | 82.17 |
| CPU median | 82 | 80.5 |
| Recording median, ms/frame | 1.45 | 1.405 |
| Encoding median, ms/frame | 4.76 | 4.51 |
| GPU median, ms/frame | 4.11 | 4.055 |
| Draws/frame mean | 2,261 | 2,339 |
| Decoded attribute elements/summary mean | 3,014,712 | 2,948,652 |
| Reported FPS min/median/max | 60/60/60 | 60/60/60 |
| Frames off the pacing grid | 0/6,900 | 28/7,200 |
| Worst off-grid deviation | 0 ms | 8.3 ms |
| Attribute lookup hit rate | 89.71% | 89.65% |

All 53 thermal observations are nominal. No GPU errors or driving error-level
lines were found. The watchdog/semaphore dump is confined to frontend startup.
The 75 ms screen gap occurs immediately as driving starts, during initial
texture decoding, outside the guarded window; the 67 ms gap occurs after the
return to the frontend. The guarded pacing deviations are mostly paired
one/three-refresh intervals rather than long stalls. The log still has file
probe warnings; no separate visual/stability observation accompanied this run.
GPU pass profiling remains operational (32 reports, including the expected
47-pass driving reports). The draw pool remains one upstream allocation/frame;
geometry reserves 64 MiB by the end, within the existing 32 MiB chunk policy.

Retain lazy diagnostics for accumulated tests. The CPU/encoding changes are
encouraging, but workload and route differences, lower decoded work and a
single pair of runs prevent attributing an isolated percentage gain or battery
saving. This log establishes that the intended metadata preparation is skipped
and no major steady-race performance fault is visible. It does not validate
on-device snapshot PNG output or prove identical rendered pixels.

Next proposed measurement remains GPU-buffer front-cache coverage: separate
full-pointer hits, occupied-slot collisions, empty-slot misses and actual new
map entries, using local render-queue counters summarized at the existing
300-frame interval. Keep lookup policy, uploads, GPU completion and ownership
unchanged until the miss distribution is known. This instrumentation has not
been implemented; await approval. No new source patch/build was made for this
log analysis.

### GPU-buffer lookup counters (IPA 19)

After approval, added diagnostic-only instrumentation to
`ios/src/native_renderer.mm`. `--nfsmw_native_gpu_lookup_stats=true` enables
it at startup; default false, independent of the five-option battery group
and every optimization switch. The cache policy remains the same 4,096-slot
pointer-bits-4..15 selector and full-pointer match with unordered_map fallback.
No SDK or generated game source changes.

The existing normal-frame summary interval now reports:
- Frames covered, with snapshot frames counted separately if present.
- Front-cache full-pointer hits, empty-slot misses and occupied-slot misses
  (labelled collisions). Each lookup belongs to exactly one category.
- Misses returning an existing map node versus inserting a new map node,
  determined by map size before/after the same existing operator[] call.
- Current occupied front slots and total backing-map entries. Occupancy is
  scanned once per summary, not maintained in the hot lookup path.

Counters use render-queue-local uint64_t fields, no atomics, clocks, per-call
logging or diagnostic allocation. They reset after each summary; cache state
is preserved. Misses should equal existing plus new map fallbacks. New map
entries are not counts of Metal allocations, arena uploads or new chunks;
failed arena allocation can leave an existing node for a later retry. The
counters cover vertex and index GpuBufferFor calls together; fresh geometry
uploaded into the per-frame data buffer bypasses this function. An occupied
slot miss proves front-cache displacement, not an unordered_map bucket
collision. This first measurement does not separately distinguish working-set
capacity pressure from poor slot distribution; further policy measurements
may be needed after its coverage is known.

A standalone host check extracted the actual front-cache/statistics code and
ran both switch arms under ASan/UBSan. A controlled full-pointer sequence,
including two pointers 64 KiB apart, produced the expected 2 hits / 2 empty
misses / 2 collisions, with 3 new and 1 existing map fallback. Disabling
statistics leaves counts zero. Summary reset preserves node identity and
front-cache contents. Source comparison confirms the remainder of GpuBufferFor
(upload, ownership, last-use/submission updates) and SweepGpu are byte-for-byte
unchanged. Instrumented CPU timings must not be treated as a saving from this
measurement build.

The iOS build, ZIP CRC and strict deep codesign verification passed; all 104
Metal libraries match IPA18. `ios/build/NFSMW-battery-gpu-lookup-stats-19.ipa`:
UUID `F5A35C35-FD08-3DC9-B43D-84ECAABE656F`, SHA256
`a851e8933477d2d2cfd913bbc40d477d8839ba7d93e5e964fffbede15ae62ba6`.
Device data pending: retain all prior arguments/settings, add
`--nfsmw_native_gpu_lookup_stats=true`, and run the usual two-lap iPad race
at 1.5x / 60 FPS. The game log contains all required counters; no Instruments
capture or long power A/B is needed for this measurement. Await that log
before choosing or implementing a cache replacement.

### GPU-buffer lookup results and next proposal (run 17)

`nfsmw_run_17_ipad.log` confirms IPA19 renderer build October 17 01:15:40,
lookup statistics on, and the previously tested options still enabled.
Settings remain 1.5x / 60 FPS, MetalFX/FXAA off. Driving spans
01:19:37.003–01:22:00.927 (143.924 s). The same five-second guards and complete
summary interval rule yield 26 renderer windows covering 7,800 frames.
All 36 lookup summaries in the complete log satisfy
empty_misses + collisions == existing_entries + new_entries.

Guarded race totals:

| Counter | Value |
|---|---:|
| GPU buffer lookups | 76,002,892 |
| Front-cache hits | 43,484,291 (57.214%) |
| Empty-slot misses | 12 |
| Occupied-slot collisions | 32,518,589 |
| Total fallbacks | 32,518,601 (42.786%) |
| Fallback to existing map entry | 32,416,621 (99.686% of fallbacks) |
| New map entry | 101,980 (0.314% of fallbacks) |
| Lookups / frame | 9,743.96 |
| Fallbacks / frame | 4,169.05 |
| Occupied front slots at summaries | 1,360–1,364 / 4,096 |
| Backing-map entries at summaries | 9,353–18,244 |
| Snapshot frames | 0 |

Thus most fallbacks repeat a lookup for an existing buffer. This is not
mostly new-resource insertion. The full nominal cache is also poorly used:
only roughly one third of the slots are occupied despite many more backing
entries, and essentially every miss replaces an occupied slot. The current
selector ignores higher pointer bits and repeats every 64 KiB. These data
support an address-distribution/conflict hypothesis, but they do not record
pointer streams, identify a precise allocator cause or determine the active
working-set size. The backing map retains unused entries for hundreds of
frames, so its entry count is not the instantaneous hot-set size. A better
selector may help; its recoverable misses and added hashing cost must be tested.

Guarded performance: all FPS summaries 60; CPU mean 80.33%, median 78% of a
core; recording median 1.37 ms, encoding 4.42 ms, GPU 4.045 ms. Run 16 had
CPU mean 82.17%, encoding 4.51 ms, but run 17's draw mean was lower
(2,270 vs 2,339), as was decoded work (2.66M vs 2.95M elements/summary).
Instrumentation did not implement an optimization; do not attribute a saving
to this comparison. All 56 thermal observations are nominal and no GPU error
is logged. Pacing has 41/7,800 off-grid intervals (0.526%), worst 8.3 ms.
The in-race watchdog dump at 01:20:45.915 conflicts with uninterrupted
frame 5401 -> 5701 progression in 5 s and 60 FPS, consistent with the existing
watchdog false positives, rather than evidence of a measured five-second
freeze. A second dump is after the frontend return; large screen gaps are
also around that transition. No visual/stability report accompanied this log.

Recommended next isolated experiment, not implemented: keep the existing
4,096 slots and replacement policy, but optionally mix higher pointer bits
into the selector. Share one selector helper between GpuBufferFor and
SweepGpu so eviction invalidates the correct slot. Preserve full-pointer
identity checks, map fallback, uploads, g.keep, last-use/submission updates,
GPU completion checks and arena reclamation. Use an independent default-off
restart-required switch (proposed name nfsmw_native_gpu_lookup_hash), retain
the current counters, and benchmark the extra selector cost before building.
Do not simultaneously enlarge the table or add associativity: first measure
whether using its existing slots better is enough.

Production change would be confined to `ios/src/native_renderer.mm`, with
focused host validation of full-pointer matches, forced collisions, map
rehash, erasure/invalidation, allocation retry and resource lifetime paths.
Then run the usual short ON device race; its log can show whether occupancy
and existing-entry fallbacks improve. This is a CPU bookkeeping opportunity:
42.8% lookup misses do not imply 42.8% CPU or battery savings. Previous
profiles put the backing-map leaf at roughly 1–2% of app CPU samples, so any
whole-app gain is expected to be incremental. Approval is required before
implementing this selector change. No source patch or new IPA was made for
this log analysis.

### Higher-bit GPU-buffer slot selector (IPA 20)

After approval, added `--nfsmw_native_gpu_lookup_hash=true`, default false,
restart-required and separate from every other option. Production changes are
limited to `ios/src/native_renderer.mm`. The same 4,096-slot table, slot
structure, replacement policy, full-pointer hit comparison and backing map
remain in use. A shared GpuBufferSlotIndex helper is used by both lookup and
SweepGpu invalidation. A periodic selector log identifies the chosen path.

The enabled selector takes pointer >> 4 as before, folds the higher region
bits into 12-bit groups, multiplies that regional salt by 0x9E37, XORs it into
the key, then masks to 4,096 slots. Within an aligned 64 KiB region the salt
is constant, so distinct legacy slots within that region stay distinct. The
salt varies between regions; the multiply spreads small regional differences
across the selected bits. It is only a slot selector, never a resource identity
or content-validity check. The disabled arm uses the legacy low-bit selector;
the new switch check means it is not byte-identical old machine code.

Uploads, shared ownership, last-used/last-submission refreshes, GPU completion
checks, expiry rules and geometry reclamation are unchanged. Source comparison
confirmed the upload/sweep body matches the previous source except the shared
selector expression used during erasure. The existing counters remain
independent and unchanged, enabling comparison against run 17's 57.214% hits,
42.786% fallbacks and 1,360–1,364 occupied slots.

`python3 tools/native/test_gpu_buffer_lookup.py` passed all four selector /
counter switch combinations under real Objective-C ARC plus ASan/UBSan. It
extracts the production GpuBuffer, slot/statistics definitions, complete
GpuBufferFor and SweepGpu. Host-memory buffer/arena fixtures allow checking:
- All 4,096 distinct legacy slots within one region remain distinct; output
  bounds also hold for individual pointer bits through bit 63.
- Forced full-pointer collisions return the correct uploaded array and
  original offset, without duplicate upload on an existing node.
- Map rehash keeps cached node pointers valid.
- Expired entries remain until their GPU submission completes; removing an
  older colliding entry does not invalidate its newer slot occupant.
- Erasing the slot occupant clears its cached pointer before node destruction.
- Guest decoded-array ownership survives pending submissions and ends on
  completed eviction. Allocation failure/retry and reuse of exactly the same
  object address cause correct fresh upload rather than a dangling hit.
These fixtures submit no actual GPU work; device rendering/lifetime validation
remains necessary.

The -O3 `--benchmark` passed the same correctness checks with counters on and
timed the extracted front lookup / actual backing-map type. Controlled pointer
layouts (48-byte steps in 64 KiB regions, fixed cyclic order) gave:

| Synthetic layout | Legacy | Higher-bit mix |
|---|---|---|
| 1 region, 1,024 keys | 2.20–2.35 ns, 100% hits, 1,024 slots | 2.17–2.20 ns, 100% hits, 1,024 slots |
| 4 regions, 4,096 keys | 10.38–14.80 ns, 0% hits, 1,024 slots | 5.90–6.53 ns, 43.70% hits, 2,844 slots |
| 16 regions, 4,096 keys | 8.64–8.93 ns, 0% hits, 256 slots | 5.94–6.09 ns, 39.14% hits, 2,700 slots |

These are host synthetic microbenchmarks, not a replay of actual device
addresses, an isolated universal hashing-cost estimate, or device/energy gains.
A plain XOR-only fold was also considered locally; it left the 16-region
synthetic case clustered, motivating the regional salt multiply in the final
implementation. Device counters must determine whether the game benefits.

The iOS build, ZIP CRC and strict deep codesign verification passed. All 104
Metal libraries are byte-identical to IPA19.
`ios/build/NFSMW-battery-gpu-lookup-hash-20.ipa`:
UUID `2CD6D542-84B7-3379-BB26-DAE64A642F64`, SHA256
`311ddbcc7ae6c75c23f3bb57f63e152f0c52757aeb78203d84a9a4c3e6161648`.
Device validation pending: retain all previous arguments, especially
`--nfsmw_native_gpu_lookup_stats=true`, add
`--nfsmw_native_gpu_lookup_hash=true`, and run the usual two-lap iPad race
at 1.5x / 60 FPS. Compare hits/fallbacks and occupancy against run 17, plus
resource churn, timing/pacing and visual/stability observations. No repeated
OFF race or long individual power A/B requested. Await the device log before
stacking another implementation change or enabling this selector by default.

### IPA20 iPad result and iPhone loading freeze (October 17)

The user supplied `/Users/bep1s/Desktop/debug/17 October 2026/nfsmw_run_1_ipad.log`
and reported no visual glitches. Renderer build is 01:30:55, higher-bit mix
and lookup statistics enabled, previous tested options enabled. Driving spans
18:07:49.176–18:10:07.889 as recorded in the log. With the existing five-second
guards and complete-interval rule, there are 25 summaries / 7,500 frames.

| Metric | Run 17 / legacy selector | October 17 iPad run 1 / mix |
|---|---:|---:|
| Front-cache hit rate | 57.214% | 73.987% |
| Hits | 43,484,291 | 54,313,200 |
| Empty misses | 12 | 4,271 |
| Occupied-slot misses | 32,518,589 | 19,091,921 |
| Existing-entry fallbacks | 32,416,621 | 19,004,467 |
| New map entries | 101,980 | 91,725 |
| Fallbacks/frame | 4,169.05 | 2,546.16 |
| Occupied slots | 1,360–1,364 | 3,646–4,036 |
| Backing-map entries | 9,353–18,244 | 9,384–17,012 |
| CPU mean, % of one core | 80.33 | 91.18 |
| Recording median, ms | 1.37 | 1.49 |
| Encoding median, ms | 4.42 | 5.73 |
| GPU median, ms | 4.045 | 4.10 |
| Draws/frame mean | 2,270 | 2,323 |
| Decoded elements/summary mean | 2.66M | 2.84M |
| Reported FPS min/median/max | 60/60/60 | 60/60/60 |
| Pacing off-grid intervals | 41/7,800 | 2/7,500 |

All 54 thermal observations are nominal, and no driving error-level lines or
GPU command errors were found. The selector demonstrably uses more slots and
has fewer repeated map lookups. Total CPU and encoding time were higher,
including drawable waiting in the latter metric. Workloads differ, but that
does not establish the reason for the increase or exclude a performance cost.
Do not claim a CPU/energy win or enable the selector by default based on this
run. Further optimization implementation is paused for the iPhone issue.

The user also reports that recent builds reach the iPhone frontend but freeze
on event loading (career/quick race/challenge), while touch controls remain
responsive. They tried individually disabling recent options. They confirm
stable 0.3.0 worked; the last working experimental IPA is unknown. They say
the supplied `nfsmw_iphone crash.log` was probably saved before those OFF tests.

That file is appended history, not a single crash session:
- October 16 12:47, renderer 12:43:25: older code successfully enters driving.
- October 17 01:40, 06:31 and 06:32: renderer 01:30:55 (IPA20). All three
  sessions report the recent switches ON, including Utility, attribute lookup,
  pooled attributes, transform copies, lazy diagnostics and higher-bit mix.
  Thus this log does not verify behavior with the changes disabled.
- The final session stops producing render summaries after frame 301 at
  06:33:06.122, never reports transition beyond frontend state 3, and continues
  CPU/memory/watchdog reporting. At 06:33:14 CPU is 16% of a core, footprint
  1,130 MiB (peak 1,238), nominal thermal state, roughly 5 GiB memory headroom.
  No GPU error or native fatal exception is recorded. This supports a guest
  progress stall, not evidence of a memory-pressure termination.
- The 06:33:20 watchdog shows guest thread 7 at sub_821BD920's request-completion
  polling loop via 821BD96C / 821BD774 / 821B9F74 / 823B5234 / 823B41A0.
  Source reads a request ID at *(r31+256)+52, calls sub_825D79F0, and loops on
  sub_825D7BB8 with a 1 ms sleep until the ID is no longer pending in a linked
  request list. Main thread 6 waits in the usual frame-dispatch path. This
  locates an outstanding guest request; it does not identify why it remains
  pending, prove a file-I/O or GPU cause, or establish a fix. The existing
  sub_8261D610 lost-job-wakeup hook handles a different wait and is not a
  justified patch target from this stack alone.

Next controlled diagnostic uses the same IPA20 with all recent experiment
switches false together, keeping unrelated settings unchanged. A real cold
launch (force-quit LiveContainer before reopening) is required for cached
restart-only choices. The five-option master must be false: it overwrites its
five individual options after parsing, so independently disabling one of
those while leaving the master true does not disable it. Include false for
constant copies, texture masks, draw arena, Utility, attribute lookup,
transform copies, lazy diagnostics, GPU hash and GPU statistics as well.
The group OFF setting also restores its historical baseline QoS policy above
40 FPS. This is a functional OFF path, not the exact 0.3.0 binary: e.g. the
heap-backed PMR draw representation remains compiled in. If it still freezes,
that does not rule out unconditional binary changes or an exposed timing bug.
Only one attempt to enter Quick Race and its latest log is needed; avoid more
battery testing until the freeze is isolated. No speculative fix, source
patch or new IPA has been made for this investigation.

### User-reported sustained iPad battery result (October 17)

The user reports an uninterrupted 1 h 35 min iPad session during a flight,
battery 75% -> 55%, using the game's Battery mode with a 30 FPS cap plus
system Low Power Mode. They report that the 30 FPS cap held without a single
observed drop. Logging was disabled, so there is no trace or game log for
this session. Exact build/experiment arguments, resolution/upscaling,
brightness, thermal conditions, connectivity and mix of gameplay were not
recorded here; do not infer those from earlier test runs.

The reported change corresponds to approximately 12.6 battery percentage
points per hour over 95 minutes. This is a useful sustained real-world result
and a practical configuration worth retaining for future tests, not a
controlled comparison with the shorter race or Instruments runs. Game Battery
mode bundles graphical/workload changes; system Low Power Mode and the 30 FPS
cap were also active. Their individual contributions, and any contribution
from this branch's optimizations, cannot be separated from this observation.
It does not establish equivalent efficiency at default fidelity or 60 FPS.

Preserve this report when planning later power measurements. Once the iPhone
loading regression is isolated, test these factors separately with comparable
brightness, content, resolution/fidelity and duration. No immediate repeat
flight-length session or retroactive log is required. The iPhone full-OFF
loading check remains the next pending diagnostic; no code was changed for
this battery observation.

### iPhone full-OFF loading success (October 17, run 1)

The user reports that the requested full-OFF cold launch worked, supplying
`/Users/bep1s/Desktop/debug/17 October 2026/nfsmw_run_1_iphone.log`.
The renderer build is still IPA20 / October 17 01:30:55. Startup/runtime lines
verify the master group off, constant and transform copies off, legacy
unspecified render QoS, legacy GPU selector, lookup counters off, lazy
diagnostics off, attribute lookup off and draw pooling off. Bulk-constant
reports show bulk off; group-managed options use their OFF control paths.

The log transitions through frontend -> loading region at 22:00:03.022 ->
loading track at 22:00:05.074 -> in-world/driving at 22:00:10.194. The last
renderer summary at 22:00:11.176 reports 30 FPS. Thus this log verifies event
loading, not a complete long driving session. No GPU error is logged.

Settings remain game Battery mode / 0.85x, FXAA normal, MetalFX off, cap 30,
matching the two failed 06:31/06:32 sessions in the prior appended log.
Importantly baseline QoS is OFF even with the group disabled, because the
30 FPS cap suppresses its historical elevated-priority control path. Do not
attribute this successful loading to restored top guest/CP thread priority.
A cold restart and simultaneous option changes still prevent identifying a
single cause. The latest binary can load on this iPhone in this configuration;
there is no basis yet for a speculative synchronization or resource fix.

Proposed first focused isolation uses the verified OFF block unchanged except
`--nfsmw_native_render_utility=true`, retaining the same Battery-mode and cap
settings and a real force-quit/relaunch of LiveContainer. Utility modifies
render-queue scheduling and had previously been validated on iPad; it is a
reasonable candidate to test individually on the phone, not an identified
culprit. One attempt to load the same Quick Race and a new log is sufficient.
Failure would show Utility alone is sufficient under these conditions;
success would not rule out interactions with other options. Keep the other
options OFF and inspect the new log before changing the next set. No new
code, build or default setting was changed for this step.

### iPhone Utility-only and default-settings loading checks (October 18)

`/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_1_iphone.log`
verifies the requested Utility-only test: the five-option master group,
constant copies, transform copies, texture pruning, draw pooling, attribute
lookup, lazy diagnostics, mixed GPU selector and lookup counters are OFF;
the render queue and its entry samples report Utility QoS. IPA20 reaches
in-world/driving at 17:16:24.245. Utility alone therefore did not reproduce
the reported freeze on this attempt; interactions and intermittent failure
remain possible.

The user then cleared Extra Args and reported successful loading in
`/Users/bep1s/Desktop/debug/18 October 2026/nfsmw-run_2_iphone.log`.
This is an appended log containing the previous launch and a second launch
starting at 17:17:37.590. Analyze the second launch separately: it verifies
the five-option group ON, constant copies ON, texture pruning ON and draw
pooling ON. Utility scheduling, attribute lookup, transform copies, lazy
diagnostics, mixed GPU lookup and lookup counters remain OFF, matching the
compiled defaults. This is not an all-experiments-ON test.

The same IPA20 renderer (October 17 01:30:55), 0.85x resolution, normal FXAA,
MetalFX OFF and 30 FPS cap reach region loading, track loading, then driving
at 17:18:02.473. The last renderer summary at 17:18:08.593 reports 30 FPS;
the log ends at 17:18:09.350. Neither supplied October 18 log contains an
error outside the existing watchdog/semaphore dumps; the successful event
transitions do not establish sustained stability or a battery improvement.

These results supersede the proposed sequence from the full-OFF baseline.
Next proposed check: retain the now-working default configuration and add
only `--nfsmw_native_gpu_lookup_hash=true`, force-quit/relaunch LiveContainer,
then load the same event once. This tests the newest optional cache selector
against the verified default baseline without stacking other experiments.
No source code, build or default was changed for these loading checks.

### iPhone mixed GPU selector loading check and offline clue (October 18)

`/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_3_iphone.log`
contains one launch, starting at 17:20:50.996, of the same IPA20 renderer.
The five-option master group, constant copies, texture pruning and draw
pooling are ON. The GPU selector reports higher-bit mix; Utility scheduling,
attribute lookup, transform copies, lazy diagnostics and lookup counters are
OFF. Settings remain 0.85x, FXAA normal, MetalFX OFF, cap 30. The game reaches
in-world/driving at 17:21:19.357 and the last renderer summary reports 30 FPS
at 17:21:21.909; the app resigns active at 17:21:23.030. No error is logged
outside the watchdog/semaphore categories. This verifies another successful
event load, not sustained stability or an energy improvement.

The user recalls airplane mode with Wi-Fi OFF during the previous day's
failure. Connectivity is user-reported, not recorded by these logs; neither
the earlier appended failure log nor this run has network-keyword messages.
A limited source check found no network/reachability use in ios/src.
The SDK's src/kernel/xam/xam_net.cpp returns a fixed zero from
NetDll_XNetGetEthernetLinkStatus_entry, a loopback address from
NetDll_XNetGetTitleXnAddr_entry, and a stub error/signaled event from
NetDll_XNetDnsLookup_entry. Other socket functions exist, so this does not
prove that connectivity cannot affect execution. The prior frozen stack
also did not identify a network wait.

Proposed next diagnostic: retain this exact Extra Args line and graphics
configuration, enable airplane mode with Wi-Fi OFF, force-quit/relaunch
LiveContainer and load the same event. If the freeze recurs, restore network
connectivity and repeat without changing arguments. This checks the new
environmental clue before adding another optional optimization. A passing
offline attempt would not rule out an intermittent freeze or interactions
among the still-disabled experiments. No code or defaults changed.

### iPhone run 4 after requested offline check (October 18)

`/Users/bep1s/Desktop/debug/18 October 2026/nfsmw-run_4_iphone.log`
contains one IPA20 launch at 17:24:21.511 and reaches in-world/driving at
17:24:48.132; the log ends at 17:24:50.044. Settings and optimization state
match run 3: defaults ON plus the mixed GPU selector, with Utility,
attribute lookup, transform copies, lazy diagnostics and lookup counters
OFF; 0.85x, normal FXAA, MetalFX OFF, cap 30. The last renderer summary
precedes driving, so it is not a gameplay performance measurement.

This log was supplied in response to the requested airplane-mode/Wi-Fi-OFF
test, without an explicit accompanying confirmation of connectivity. The
log itself cannot verify radio state. It does verify another successful
load and provides no new evidence that airplane mode caused the previous
freeze. Two watchdog dumps occur before driving, including one at
17:24:46.746 shortly before the successful transition; they do not establish
a persistent hang. No other error category is logged.

Next proposed isolation adds only --nfsmw_native_transform_copies=true to
the existing --nfsmw_native_gpu_lookup_hash=true line, keeping graphics and
connectivity unchanged. Cold-launch LiveContainer and enter the same event
once. Utility, attribute lookup, lazy diagnostics and lookup counters remain
OFF. This checks the optional game-code scalar transfer change against the
now repeatedly loading configuration. No code, build or defaults changed.

### Battery work resumed; iPhone issue parked (October 18)

The user explicitly requests that the loading issue be marked resolved for
now and retained in the backlog. It is no longer an investigation blocker;
there is no established fix or causal attribution. The transform-copy-only
addition proposed after run 4 was not tested. See [BACKLOG.md](BACKLOG.md).

The 95-minute iPad report (75% to 55%, Battery mode plus system Low Power
Mode, stable reported 30 FPS) remains the sustained low-drain reference,
approximately 12.6 battery percentage points per hour. It is not a controlled
comparison against the earlier 60 FPS Power Profiler runs at roughly 31.9
percentage points per hour. The user subsequently recalls low brightness
in the dark aircraft cabin. The exact brightness and experiment state remain
unknown: they recall either no Extra Args or the arguments from the last
optimization check. Do not label the flight all-experiments-ON or defaults-only.
Low brightness is another plausible contributor to the sustained result,
whose contribution requires matched display conditions to separate.

Read-only follow-up checked current low-cap behavior:
- launcher.mm BatteryValue selects 0.85x, MetalFX OFF, FXAA, half-size
  shadows, half-rate cube reflection updates and thermal/menu policies.
- battery.mm can switch a launcher's 60 cap to 30 for system Low Power Mode
  or heat; therefore explicitly choosing 30 in both comparison arms is
  necessary to avoid inadvertently comparing 60 FPS against 30 FPS.
- display_rate.mm requests 60 Hz for the 30/60 caps, 120 Hz for 40/120.
  This is a request, not proof of actual panel refresh or callback rate.
- The display-vblank SDK patch sleeps until the next refresh. Its display
  lock expects a period close to the guest's 60 Hz at the 30 FPS cap;
  simply lowering CADisplayLink to 30 would break that condition and select
  the fallback timer. No pacing change is justified by inspection alone.
- RenderFrame still flattens textures, resolved_textures, assembled_cubes,
  volumes and cubes for every main render encoder. The base arrays are
  fixed before the draw loop and the dynamic arrays only append. A frame-
  local flattened-list cache keyed by collection counts could avoid repeated
  enumeration when unchanged. Every encoder must still receive useResources,
  with the same objects, order, usage and stage flags. Existing owning arrays
  and GPU completion lifetimes must remain intact. Savings are unmeasured.

Next recommended measurement is two matched iPad Power Profiler recordings,
8–10 minutes each, Battery mode ON and explicit cap 30, same current build
and arguments, manual brightness, content, connectivity and starting thermal
state. Change only system Low Power Mode OFF/ON. Record Power Profiler,
Thermal State and Time Profiler, unplugged, using the working minimal template.
Compare whole-device drain rate, CPU/GPU/display impact, CPU running samples
and core distribution, frame pacing, logged effective scale and thermal state.
Do not use short integer battery deltas or GPU milliseconds alone as the
success criterion. Check any heat-scale change or brightness difference
before attributing the result to scheduling or clock/power management.

Keep the newer experiments optional: better GPU lookup coverage has not
established a CPU or energy improvement. Reuse the resulting profile to
choose between renderer bookkeeping and remaining guest-code work; do not
assume another guest-native rewrite will recover the full guest CPU share.
The next concrete lossless code candidate is the resource-list cache in
ios/src/native_renderer.mm, with targeted ARC/list-equivalence validation,
subject to user approval and evidence of relevant cost. No implementation,
default changes or new IPA were made during this review.

Apple's [iPad Low Power Mode documentation](https://support.apple.com/en-gb/guide/ipad/ipadbaefc31d/26/ipados/26)
confirms the ProMotion display limit of 60 FPS; it does not quantify this
game's CPU/GPU or whole-device savings. Source and instrumentation must
establish the actual behavior in LiveContainer.

### Matched iPad Low Power Mode recording (October 18)

Inputs supplied by the user:
- `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_1_ipad.log`
- `/Users/bep1s/Desktop/debug/18 October 2026/Power_Profiler_1_ipad.trace`

The trace contains both comparison arms, not just its first run:
- Run 1, "Low Power Mode": 17:35:20.151–17:45:20.552, 600.401 seconds.
- Run 2, "No Low Power Mode": 17:45:53.439–17:55:53.666, 600.226 seconds.

Times are the trace's recorded Europe/Madrid local times (+02:00). Both
attach to LiveContainer PID 2404 on the 13-inch M4 iPad. The appended game
log first contains an earlier 1.5x/60 FPS launch, which is outside these
recordings. The profiled launch starts at 17:34:52.680 and uses IPA20,
renderer October 17 01:30:55, UUID 2CD6D542-84B7-3379-BB26-DAE64A642F64.

For both recorded arms the five-option group, constant copies, texture
pruning, draw pooling, Utility render queue, attribute lookup, transform
copies, lazy diagnostics, mixed GPU selector and lookup counters are ON.
The effective scale is consistently 0.85x, FXAA normal, MetalFX OFF and
explicit cap 30. System Low Power Mode is logged ON before run 1 and OFF
at 17:45:47.651, between the recordings. There is no intervening game restart.
All trace thermal intervals are Nominal; brightness is exactly 34% in both.
The charging-state tables contain no rows, so they do not independently
verify cable state. Nonzero system power estimates are available throughout.

The user recalls all events being Challenge Series pursuits. Do not label
the first event a race from its post-event menu names. One pursuit starts
at 17:39:29.460 and continues into the second recording until 17:51:57.073,
with short pause intervals. Another event begins at 17:52:18.672. Scenes,
traffic and pursuit intensity are not an exact replay.

The exported power rows are duration-weighted, including clipped intervals.
Active-gameplay analysis excludes five seconds around driving/menu state
transitions; log summaries are included only if their entire ten-second
window lies inside an eligible interval. Subsystem impact values are the
profiler's own modeled scales, not watts or additive shares of system power.

| Metric | Low Power Mode ON | OFF |
|---|---:|---:|
| Whole-run system drain estimate, battery percentage points/hour | 13.612 | 24.540 |
| Guarded active-gameplay drain estimate | 13.856 | 24.879 |
| Continuing-pursuit drain estimate, pauses excluded | 13.646 | 24.670 |
| Whole-run CPU power impact | 3.242 | 8.359 |
| Whole-run GPU power impact | 0.919 | 0.945 |
| Whole-run display power impact | 4.506 | 4.306 |
| Whole-run networking power impact | 0 | 0 |
| Brightness | 34% | 34% |
| Thermal state | Nominal | Nominal |
| Active QoS-accounted CPU time, % of one core | 91.40 | 59.17 |
| Active retired instructions/second, profiler estimate | 6.049 billion | 6.404 billion |
| Active log FPS, min/median/max | 30/30/30 | 30/30/30 |
| Active median CPU recording time, ms/frame | 3.41 | 2.20 |
| Active median render encoding time including waits, ms/frame | 6.315 | 7.89 |
| Active median GPU time, ms/frame | 5.39 | 4.78 |
| Active mean draws/frame | 2,700 | 2,729 |
| Active pacing off-grid intervals | 32/15,600 | 0/14,100 |

Whole-run estimated drain is 44.53% lower with Low Power Mode; the guarded
comparison gives 44.31%, and the continuing pursuit gives 44.68%. Each
two-minute bin is 13.20–14.32 points/hour ON versus 23.50–25.50 OFF.
CPU power impact is about 61% lower in the whole-run comparison. GPU impact
is close between arms, and display impact is slightly higher ON. This is
strong evidence of an important CPU/system power-policy effect in this
configuration, with no detected frame-cap or render-scale explanation.
It corroborates the approximate 12.6 points/hour flight observation without
establishing a universal 45% saving, attributing it to this branch's code,
or proving equivalent results at normal fidelity/60 FPS. Run order, evolving
pursuits, profiler overhead and unmeasured system activity remain limitations.

CPU-time utilization alone gives the wrong direction for energy here: the
ON arm spends more CPU time executing broadly similar instruction volume
while its modeled power cost is much lower. Running-sample core weights are
76.39% P / 23.61% E ON versus 69.58% P / 30.42% E OFF during guarded gameplay.
The NativeSwap render block remains largely on E cores (99.96% ON, 94.96%
OFF). There is no evidence here of wholesale migration of guest work onto
E cores. A more economical CPU operating point is the leading explanation;
CPU clock/voltage changes were not directly established by these exports.
Do not treat Utility QoS or core affinity as equivalent to system Low Power
Mode, or infer that more CPU-time percentage necessarily means more work.

### Next CPU candidate from this recording (not implemented)

Time Profiler still shows guest-code self at roughly 34.6% / 31.3% of active
running sample weight, NativeDraw inclusive at 10.59% / 9.88%, and RenderFrame
inclusive at 18.02% / 23.01%, ON/OFF respectively. Rows overlap and must not
be summed; they are CPU-time shares, not energy fractions.

A UUID-matched instruction audit refines the earlier resource-list proposal.
The main list-construction block before useResources, linked addresses
0x10007ad68..0x10007b038 (end exclusive), accounts for 226 / 206 ms of self
sample weight: 0.048% / 0.070% of active app CPU. This excludes callees and
outlined vector-growth blocks, so it is not a complete cost bound. Driver
resource-list processing also costs time but must remain. List caching is
therefore lower priority than a newly identified sizing prepass hotspot.

RenderFrame walks frame->draws twice to size its pooled upload buffer:
first tracking VS/PS/previous-VS constant ranges, then counting shared data,
fresh indices and fresh attributes. Source is ios/src/native_renderer.mm
around lines 4240–4280. The compiled binary retains both separate scans.
Their linked main-loop range 0x1000735e0..0x10007374c accounts for 7,280 /
6,081 ms of self samples, approximately 1.54% / 2.06% of active app CPU,
or 26.7% / 27.5% of RenderFrame self. The hot load at 0x100073654 alone has
4,989 / 4,296 ms. Sampling skid/cache stalls prevent exact per-instruction
cost attribution. These totals describe the existing scans, not recoverable
savings from removing only their redundant traversal.

Recommended isolated experiment, subject to user approval: fuse the two
sizing scans into one while preserving the same total allocation budget,
constant-range coverage semantics, fresh geometry accounting, alignment
allowances, actual upload order and pooled-buffer/GPU ownership. Only
ios/src/native_renderer.mm needs production changes; a targeted host fixture
in tools/native/test_upload_sizing.py would compare legacy and fused totals
for repeated/covering/empty/changing ranges, previous-frame constants, cached
and fresh geometry, empty frames and randomized draw sequences, and benchmark
the traversal. Keep a separate OFF control path for device comparison.
Check compiled ARM64 and any register-pressure regressions, then request one
short device correctness run before stacking more changes. Expected gain is
modest and unquantified; this is not a substitute for the much larger observed
system-mode effect. No new code, build, default or QoS policy changed here.

Analysis exports and scripts currently in /tmp use the nfsmw_oct18_ prefix:
power1_toc.xml, power_tables.xml, time_profile.xml, analyze.py, cpu.py,
renderer_pcs.py, power_summary.json, cpu_summary.json, renderer_pcs.json and
render_disassembly.txt. Raw device logs/traces are not committed. Both arms
have been analyzed; no second recording or repeated A/B is needed for this
specific comparison. The iPhone loading investigation remains parked.

### IPA21 — fused upload-buffer sizing (October 18)

The user approved the proposed sizing experiment and requested that every
meaningful observation, change and test be persisted in Markdown for session
and agent continuity. docs/DEVELOPMENT_PROGRESS.md is the shared current
checkpoint/index; root AGENTS.md / CLAUDE.md and README point to it. Keep that
checkpoint current alongside this chronological evidence; preserve negative
results and pending device checks. The original HANDOFF_CHATGPT.md remains
untracked and unchanged, and docs/BACKLOG.md retains deferred investigations.

Production change is limited to ios/src/native_renderer.mm:
- New independent, restart-only nfsmw_native_fused_upload_sizing defaults false.
- Budget helpers preserve the existing per-stage coverage state and all byte
  allowances. ON evaluates constant and geometry budgets in one Draw traversal;
  OFF keeps the original two traversals. Actual uploads, pooling, Metal buffer
  size, resource ordering and completion ownership retain their source behavior.
- Both tiny budget lambdas are explicitly always_inline. The mode is logged
  once per ordinary 300-frame summary, including the initial frame, as
  `[native] upload sizing: fused single traversal` or `legacy two traversals`.
- No new hot-path counters/clocks, no shader, quality, SDK or QoS changes.

tools/native/test_upload_sizing.py extracts the actual Attribute, ConstantBank
and Draw definitions, the original sizing block from 03da344 and both current
arms. FloatArray uses a normal host float-vector allocator; no Metal work is
submitted. sizeof(Draw) is 328, matching the profiled ARM64 stride. The fixture
uses real shared array ownership and Objective-C ARC, covers empty/reversed/
covering/changing ranges, separate VS/PS/previous banks, null and empty arrays,
fresh/cached indices and attributes, empty frames and 2,000 randomized frames.
An independent alignment/upload simulation bounds maximum possible writes;
relevant input identities/values remain unchanged. Instrumented iterators
verify exactly one versus two complete traversals, including empty frames.

Validation history:
1. Initial ASan/UBSan run passed all 2,011 edge/random frame checks for exact
   original/current-OFF/fused totals, traversal counts, input preservation and
   aligned upload bounds. Initial timing overlapped the iOS build and was noisy;
   it was not treated as a performance result.
2. A warmed seven-trial host benchmark exposed slower fused cases. Before the
   inlining correction, original/current-OFF/fused medians in microseconds were
   24.949/22.648/28.711 at 0% fresh, 48.474/52.547/49.053 at 20%, and
   41.915/41.724/46.323 at 100%. Inspection of the first iOS executable found
   a constant-budget lambda call for every draw in both switch arms. The first
   build passed packaging but was superseded, not issued as the test build.
3. Added always_inline to both budget lambdas. ASan/UBSan again passed all
   2,011 checks. The -O3 benchmark also passed the differential checks, warmed
   all arms, rotated their order and timed 2,000 iterations per arm per trial.
   Seven-trial medians, 2,700 synthetic draws with eight attributes each:

| Fresh geometry probability | Original two scans | Current OFF | Fused ON |
|---|---:|---:|---:|
| 0% | 26.944 us | 26.897 us | 19.212 us |
| 20% | 49.910 us | 52.877 us | 38.127 us |
| 100% | 42.676 us | 43.328 us | 37.955 us |

This is about 11–29% less time for the synthetic sizing step versus original,
not whole-renderer, device or energy improvement. OFF timings are not identical
in every layout; the 20% case was about 6% slower than original in this host
run. Preserve that observation instead of claiming zero performance risk.
Device profiling and accumulated power testing remain the actual outcome.

4. Final `cmake --build --preset ios --target ipa -j 6` passed. The 13 warnings
   are from the existing FPSCR asm constraint and UIScreen deprecations, with
   no errors. Final ARM64 has one sizing draw loop ON (advance at linked
   0x10007362c), two OFF (advances at 0x1000737f4 / 0x10007387c); budget helper
   call operators are not emitted. Source from the subsequent pooled-buffer
   allocation through upload/encoding/ownership before the summary entry is
   byte-identical to the reference. Compiler layout elsewhere may differ.
5. ZIP CRC and strict deep codesign verification passed. All 104 actual
   .metallib payloads match IPA20 byte for byte. A naive ZIP suffix count is
   208 because __MACOSX AppleDouble metadata entries also end in .metallib;
   those must not be counted as additional shader libraries.

Final artifact: `ios/build/NFSMW-battery-upload-sizing-21.ipa`.
Implementation and host validation fixture are saved in local commit 2463b16.
UUID `BB547F91-F458-34B1-856F-BED78713E517`; SHA256
`8663dd8a610febf1d4461cfe5898e0b884f4e562f214d11ca4a5af01fe484a9e`.
The provisional outlined-helper build at that same path was replaced before
handoff: UUID 161393D6-CBA1-38ED-A7D3-29A75747C2A0, SHA256
afdf3f8b0e40681a2abaf5f6a3f43405dbf360a04df7bffed4ad93d4ab6b4863. Do not
confuse its assembly or timing with the final build.

Temporary build/benchmark/assembly details have the /tmp/nfsmw_upload* prefix;
the essential results and identities above are durable even if /tmp is cleared.
An additional Python syntax check initially hit the sandbox's external Python
cache-write restriction; directing its .pyc output to /tmp passed without
changing the script or requesting broader filesystem access.
Device validation is pending: preserve the last iPad experiment arguments and
graphics settings, add only --nfsmw_native_fused_upload_sizing=true, cold-launch
LiveContainer and complete one short correctness event. Check the new mode
line, visuals, stability and pacing. A short race/pursuit cannot establish an
energy saving; no repeated long Low Power Mode A/B or individual OFF race is
requested. Await the log before stacking another source change. Defaults are
unchanged, and the iPhone loading investigation remains parked.

### IPA21 first iPad correctness result (October 18, run 2)

The user supplied
`/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_2_ipad.log`
and reports that everything looks fine. Before the test they asked to return
to 1.5x / 60 FPS; that was explicitly accepted with Battery mode and system
Low Power Mode OFF. This changes the visual/workload configuration from the
preceding 0.85x / 30 power traces, so this is not an energy comparison.

The single launch starts at 18:51:47.316; renderer build Oct 18 18:16:30 and
all 21 mode summaries confirm fused single traversal. The five-option group,
constant/transform copies, texture pruning, draw pooling, Utility rendering,
attribute lookup, lazy diagnostics, mixed GPU selector and lookup counters
are enabled. Effective settings are 1.5x, 60 FPS, FXAA OFF, MetalFX OFF and
no forced MSAA. Memory-report suffixes do not report Low Power Mode ON.

Driving begins at 18:52:15.356; the app resigns active at 18:53:32.567,
77.211 seconds later. Five-second transition guards and fully contained
five-second renderer/pacing summaries give 13 summaries / 3,900 frames.
CPU reports use fully contained ten-second intervals.

| Metric | Guarded sample |
|---|---:|
| FPS min/median/max | 60/60/60 |
| CPU recording median | 1.45 ms/frame |
| CPU render encoding median, includes waits | 13.90 ms/frame |
| GPU median | 10.03 ms/frame |
| Draws/frame mean | 2,378 |
| CPU mean, % of one core, six intervals | 87.33 |
| Pacing off-grid intervals | 16/3,900 |
| Worst pacing deviation | 4.2 ms |

All 34 thermal observations are Nominal. There are no GPU command failures
or error-level lines during driving. Watchdog and semaphore dump entries occur
before driving and do not establish a persistent hang. One 41.6 ms swap hitch
at 18:52:15.429, immediately after entering the event and outside the guarded
window, includes 235 texture decodes / 61,371 KiB taking 31.8 ms. Do not erase
this observation or attribute it to fused sizing without further evidence.

This passes the initial short visual/stability/performance check. The trace
does not cover a complete long session, isolate the sizing code's duration,
or establish an energy improvement; workloads and settings differ from prior
measurements. Retain the new switch ON for accumulated tests, with its default
still false. No repeated long power A/B or OFF race is requested for this small
change. Record a future recurrence if any issue appears. No new implementation,
default change, build or push was made while analyzing this log. The iPhone
loading issue remains parked. Temporary detailed analysis and summary are
/tmp/nfsmw_upload21_run2_analysis.py and /tmp/nfsmw_upload21_run2_summary.json;
the material evidence is preserved here and in DEVELOPMENT_PROGRESS.md.

### Next-target audit after IPA21 device validation (October 18)

Read-only review reused the IPA20 Low Power Mode trace's active-gameplay CPU
samples, because the cache and Record code is unchanged by IPA21's sizing
experiment. This does not substitute for a current full-fidelity power trace.
There is no new production implementation or build in this audit.

Three candidates were checked before recommending the next source change:

1. Record computes two initial geometry MotionMix hashes and one per vertex
   input even when their sole consumer, temporal/debug motion-vector matching,
   is inactive. Source around 2424/2484/2679 and the compiled arithmetic agree.
   Initial hash region 0x1000b5a08..0x1000b5a5c has 37 / 19 ms of active self
   samples, and per-input mixing 0x1000b65f4..0x1000b6630 has 371 / 204 ms,
   ON/OFF respectively. Combined roughly 0.086% / 0.076% app CPU. This is real
   unnecessary work, but lower priority. Sampling skid limits exact attribution.
2. The frame upload buffer's GPU address is queried repeatedly for VS/PS and
   shared data, despite a fixed buffer for the frame. objc_msgSend$gpuAddress
   plus IOGPUMetalResource's getter have roughly 0.112% / 0.091% self shares.
   Caching that address is another small candidate, not the next priority.
3. Attribute front-cache lookup remains material despite its demonstrated
   benefit. The selector/slot-test region 0x1000b6640..0x1000b6830 has
   5,525 / 3,226 ms, 1.165% / 1.095% of app CPU. Hot PCs include
   0x1000b66d8 (1,770 / 1,022 ms), 0x1000b6740 (1,532 / 924), and
   0x1000b6758 (503 / 270). ARM64 compares the base and eight integer fields
   with a sequence of loads and conditional branches in each candidate slot.
   Selector and miss work are included; the full region is not recoverable.

The current AttributeKey is exactly 40 bytes on this target: uintptr_t base
and eight uint32_t fields. A temporary host prototype used the existing
tools/native/test_attribute_lookup.py harness and extracted production
Fingerprint/cache/sweep definitions, replacing ONLY
`slot.entry && slot.key == key` with a complete
`std::memcmp(&slot.key, &key, sizeof(AttributeKey)) == 0` check after testing
slot.entry. Backing-map equality, hashing, replacement and cache contents
were unchanged. Separate compilation confirmed sizeof==40, trivially-copyable
and unique-object-representations properties. A production implementation
must retain equivalent representation guards if the struct later changes.

Both original and candidate passed the extracted front-cache fixture under
ASan/UBSan: each identity field differs independently; forced two-way collisions;
map fallback/rehash; same-frame guest-memory mutation rejection; live entry
updates; production sweep invalidation; erasure/reinsertion and retained
ownership; 90,000 changing-key accesses with immediate reuse. Both produced
110,719 hits / 69,281 misses / zero bypasses for that randomized phase.
This validates the prototype's lookup behavior, not actual GPU rendering.

Seven alternating -O3 benchmark trials used the existing fixture's 4,096
synthetic keys, 300 frames and three passes, 3,686,400 timed lookups per trial:

| Front-key comparison | Median | Min–max |
|---|---:|---:|
| Original field comparisons | 66.64 ms | 64.46–98.44 ms |
| Complete 40-byte comparison | 32.78 ms | 30.45–65.35 ms |

All timed runs have identical checksum 551116800 and counters
2,615,400 hits / 1,075,096 misses / zero bypasses, including warm population.
The median is about 50.8% lower for this fixture only. It is not a device
address replay, instruction/energy accounting, or evidence that Record or
the whole game becomes 50% faster. The real cache already has different
coverage, and bulk comparison may load more bytes on early mismatches.

Recommended next isolated experiment, pending approval:
- Production file ios/src/native_renderer.mm: independent default-false
  bulk-comparison switch affecting only the attribute front-cache's exact
  equality test. Retain the scalar control and all fields, mutation checks,
  cache capacity/selection, lifetime and sweep behavior. Log the active mode.
- Extend tools/native/test_attribute_lookup.py for both comparison paths,
  representation guards, each-field differences and miss/hit-heavy layouts.
  Benchmark the actual switch path and inspect optimized ARM64 so optional
  control or helper outlining does not consume the anticipated benefit.
- Preserve textures/shaders/draws and ordinary GPU resource operations; then
  request one short iPad test before stacking another implementation change.
  Expected total saving is modest and not yet quantified. No new power trace
  or repeated IPA21 correctness run is needed before this proposal.

The probe, captured output and source are currently
/tmp/nfsmw_probe_key_compare.py, /tmp/nfsmw_key_compare_probe.txt and
/tmp/nfsmw-key-compare-probe/{original,memcmp}.cpp. Record PC extraction and
disassembly are /tmp/nfsmw_oct18_record_pcs.py/.json and
/tmp/nfsmw_record20_disassembly.txt. This entry retains the material findings
if those temporary files disappear. Guest sub_82699100's two short copy loops
are already optimized; no repeat of that earlier experiment is proposed.

### October 18, 2026 — IPA22: exact attribute front-key comparison

User approved implementation after the preceding audit and IPA21 device check.
Production changes are confined to ios/src/native_renderer.mm; the extracted
fixture tools/native/test_attribute_lookup.py and Markdown records are updated.
No sibling SDK, shader, guest code, settings defaults or asset changes.

The independent restart-only flag `nfsmw_native_attribute_bulk_compare` defaults
false. It affects only front-cache equality when the existing
`nfsmw_native_attribute_lookup` flag is true. It does not enable that cache.
AttributeEntryFor chooses Find<true> or Find<false>; each candidate first requires
a populated entry. The final ON implementation rejects a different 64-bit base
address, then uses memcmp on the remaining eight uint32_t fields (32 bytes).
Thus the entire 40-byte identity remains exact. Static assertions require size40,
standard layout, base at offset0, trivial copyability and unique object
representations. Backing unordered_map equality is the original scalar operator.
No fingerprint/content validation, hash selector, two-way capacity, replacement,
sweep, pointer ownership or source mutation behavior has changed. Periodic log:

```
[native] attribute key comparison: base + bulk 32 bytes; front cache on (exact identity, restart required)
```

Scalar mode logs `scalar fields`; cache state is independently reported. All
prior experimental controls, including fused sizing, remain independent.

The first production candidate used full-40-byte memcmp. All four switch arms
passed correctness, but expanded host testing exposed a downside omitted by the
original one-layout probe. Seven alternating trials, 3,686,400 timed lookups each:

| Synthetic layout | Scalar median ms | Initial full40 median ms | Final base + bulk 32 median ms (separate run) | Final scalar control ms |
|---|---:|---:|---:|---:|
| small-hit: 512 keys | 20.06 | 15.73 | 15.87 | 20.68 |
| mixed: 4,096 keys | 51.11 | 41.42 | 34.65 | 47.37 |
| large-miss: 16,384 keys | 114.21 | 116.83 | 102.38 | 108.38 |
| same-set: 32 keys, differing format, same base | 53.11 | 53.34 | 51.84 | 53.11 |
| early-miss: 32 keys, differing base low bits/format | 50.18 | 54.66 | 47.95 | 49.66 |

Full40 was ~8.9% slower for early mismatches. A temporary base-first probe then
passed optimized correctness and gave scalar/bulk medians 20.62/16.01,
47.46/34.37, 113.24/106.76, 54.55/53.24 and 56.32/51.62 ms respectively.
This justified refining the production implementation within the approved
scope. Final figures above come from a fresh run of actual production extraction
and both runtime switches, not that temporary replacement. Machine timing and
control codegen vary between runs; compare paired controls within each run.
Final gains are ~2–27% for these lookup workloads only. This is not a device
address replay, whole-renderer improvement or a battery measurement. The sampled
lookup region was ~1.1% of app CPU and includes work not removed here.

Validation command, exit0:

```
python3 tools/native/test_attribute_lookup.py --benchmark
```

Each of four independent-process configurations (lookup OFF/ON × comparison
OFF/ON) passed ASan/UBSan at -O1 and correctness again at -O3. Coverage retains
nine individual fields, now also every one of 320 object bits, forced two-way
collisions, map fallback/rehash, same-frame source mutation rejection, live
entry metadata and payload updates, extracted production sweep invalidation,
surviving nodes, erased/reinserted keys and retained ownership. Randomized
90,000 changing-key pairs per arm produce 110,719 hits / 69,281 misses / zero
bypasses with lookup ON in both comparison modes; lookup OFF gives 180,000
bypasses regardless of comparison mode. Content validation remains necessary.

Seven alternating timing trials per layout compare both modes with lookup ON;
all 3,686,400 timed calls include actual switch selection. Matching checksums /
hits-misses-bypasses across modes and trials (counts include warm population):

| Layout | Checksum | Hits / misses / bypasses |
|---|---:|---|
| small-hit | 4421836800 | 3686400 / 512 / 0 |
| mixed | 551116800 | 2615400 / 1075096 / 0 |
| large-miss | 136396800 | 357075 / 3345709 / 0 |
| same-set and early-miss | 70777036800 | 0 / 3686432 / 0 |

Final iOS build `cmake --build --preset ios --target ipa -j 6` passed with 13
existing FPSCR/UIScreen warnings. Optimized ARM64 has both lookup paths inline
in Record, no outlined Find/flag helper symbols or memcmp/bcmp call for key
comparison. At 0x1000b6a94..0x1000b6b18 the two bulk slots reject empty entries
and unequal bases, then load four 64-bit words and use cmp/ccmp with one final
branch per remainder. Scalar field-by-field comparisons remain at
0x1000b6b34..0x1000b6c3c. This is conditional scalar code, not a vector/SIMD
claim; compiler combines pairs of uint32_t fields into each 64-bit comparison.
No extra always_inline annotation was needed. Fallback/map work remains.

Final artifact: `ios/build/NFSMW-battery-attribute-bulk-22.ipa` (29,942,979 bytes).
UUID: `3CDAD6C3-51F9-372C-B7C5-DB5B3FBF1640` (arm64).
SHA256: `88dd71bf9d4e379e682ea6ac168211c6d3f90b06285ca32efe90030a392ee7c7`.
ZIP CRC passed; packaged executable matches signed cache app; strict deep
codesign passed; all 104 actual .metallib files are byte-identical to IPA21
(excluding AppleDouble __MACOSX records). Initial packaging's hash print used
hashlib.file_digest unavailable in system Python, so verification was repeated
successfully with streaming SHA256. This was a verification-script issue.
An initial full40 iOS build completed but was superseded before issuing a named
IPA22. A documentation patch context mismatch was corrected; source unaffected.

Pending first device check: same accumulated flags as IPA21, preserve
`--nfsmw_native_attribute_lookup=true` and
`--nfsmw_native_fused_upload_sizing=true`, add only
`--nfsmw_native_attribute_bulk_compare=true`. Cold force-quit LiveContainer.
iPad, usual 1.5x / 60 FPS, Battery mode OFF and system Low Power Mode OFF; one
short event, log plus visual/stability report. No long tiny-change power A/B
requested. New comparison stays compiled-default false; do not stack another
source change before validation. No device energy benefit is yet established.

Temporary outputs: /tmp/nfsmw_bulk_compare22_tests.txt (initial full40),
/tmp/nfsmw_bulk22_hybrid_probe.{py,cpp,txt} (intermediate),
/tmp/nfsmw_bulk_compare22_final_tests.txt,
/tmp/nfsmw_bulk_compare22_final_build.log,
/tmp/nfsmw_bulk22_record_disassembly.txt. Essential evidence is retained here
so continuation does not depend on temporary files. No push or release.

Implementation/fixture and evidence saved in local commit `7b848b1` on
`battery-optimization`. Original HANDOFF_CHATGPT.md remains untracked.


### October 18, 2026 — IPA22 first iPad validation passes

Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_3_ipad.log`
(1,480 lines), user reports "still no issues". One launch; renderer build Oct 18
19:11:46 matches the final IPA22 source build. New periodic mode confirms
`base + bulk 32 bytes; front cache on`. All previous experimental controls are
retained: fused sizing, attribute lookup, higher-bit GPU cache selector and
statistics, Utility render queue, lazy diagnostics, CPU draw arena, texture-slot
pruning, native float/scalar copies and the master battery group. This is an
initial visual/correctness check, not an isolated power/performance comparison.

Settings logged: scale 1.500, cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0. Requested
Battery mode OFF and system Low Power Mode OFF; memory reports contain no LPM
suffix. No brightness or instrument power recording accompanies this run.
Driving begins 19:17:07.563; scene resigns active 19:18:18.581, duration 71.018 s.
As for IPA21, exclude five seconds at each boundary and accept only complete
five-second summaries / complete ten-second CPU intervals inside that guard.

| Guarded metric | Result |
|---|---:|
| Renderer summaries / reported frames | 11 / 3,300 |
| Reported FPS in each summary | 60.0 |
| Off-grid pacing / intervals | 0 / 3,300 |
| Worst logged grid deviation | 0.0 ms |
| Median sampled recording | 1.62 ms |
| Median rendering/encoding, including drawable waits | 9.56 ms |
| Median GPU | 8.57 ms |
| Mean CPU, five complete 10 s intervals | 88.4% of one core |
| Median CPU | 89% |
| Mean last-frame draws across summaries | 2,388.73 |
| Attribute front-cache hits / misses / bypasses | 23,417,964 / 2,809,215 / 0 |

CPU intervals are 81%, 81%, 91%, 100%, 89%. All 33 logged thermal observations across
the file are Nominal. No error/critical-level lines or GPU failure messages.
CPU recording is sampled; GPU/encode timing and scene complexity vary. The draw
count is the last frame of each summary, not an average of all 3,300 frames.
No direct key-comparison timing exists in this log. Differences from IPA21's
short run therefore establish neither improvement nor regression of this step.

A 41.5 ms swap hitch at 19:17:07.637 contains 238 texture decodes /61,559KiB taking
32.0 ms, outside guarded gameplay. At 19:18:18.904, after resigning active,
encoding takes301.5 ms including 295.8 ms waiting for a drawable; the next summary
reports 56.8 FPS. These transition measurements are excluded. Startup/menu file
probe warnings continue, with two additional traffic asset probes during driving
and two after backgrounding. No visual/stability issue was reported. Battery
reports remain 65%; this brief integer-percentage reading proves no energy gain.

Outcome: initial correctness and user visual check pass. Keep
`--nfsmw_native_attribute_bulk_compare=true` alongside previous experimental
arguments for accumulated testing. Compiled default remains false. No repeat
short correctness run, build or long tiny-change A/B is required for this result.
Sustained stability and isolated/device energy benefit remain unproven. No app
source was changed and no next implementation approved. iPhone loading stays
parked per user request. Checkpoint updated; no push or release.


### October 18, 2026 — next step: profile current stack at usual settings

Following IPA22's initial check, user asks what comes next. Rechecked existing
IPA20 Power Profiler/Time Profiler summaries before proposing more source work.
Those detailed traces use 0.85x /30 FPS and predate both fused upload sizing
and bulk attribute-key comparison. New short logs establish correctness, not
instruction-level attribution or energy gains. Old active self shares remain
Record5.394% /4.979%, RenderFrame5.744% /7.495%, guest sub_82699100 2.384% /
2.027%, Fingerprint1.126% /1.025% (Low Power ON/OFF). These are overlapping
pipeline functions' individual self shares, not energy fractions or removable
work. Guest constant-copy patches are already present; content fingerprints
remain necessary. Motion hash and gpuAddress micro-targets were previously
estimated at only about0.08–0.11% app CPU each; no next implementation selected.

Recommended input: a single8–10 minute Power Profiler recording on iPad with
Time Profiler and Thermal State using the established working minimal template,
IPA22, normal1.5x /60 FPS, Battery mode OFF and system Low Power Mode OFF.
Keep all accumulated Extra Args including attribute lookup, fused upload sizing
and bulk comparison ON. Hold manual brightness fixed, record unplugged using
the working wireless workflow. Usual race followed by pursuit, note approximate
transition time; supply game log plus trace. No comparison-OFF run, new build,
GPU capture repair or iPhone freeze re-investigation requested.

Purpose: find current game-code, renderer and GPU costs at the user's normal
settings before choosing a larger or another incremental change. This single
run cannot establish batch savings against earlier0.85x /30 FPS data. A later
matched energy comparison must hold graphics, frame cap, brightness, workload
and Low Power Mode state consistent. No source implementation approved or made;
checkpoint updated with the pending recommendation.

### October 18, 2026 — IPA22 current-build power profile and next target

Inputs supplied together:
- `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_4_ipad.log`
- `/Users/bep1s/Desktop/debug/18 October 2026/Power_Profiler_2_ipad.trace`

User clarification: "i think only the last gameplay stretch matters, it should
match the 10 minute long power profiler and it was a chase only". Treat that
last stretch as the confirmed chase and primary result. Actual trace metadata
covers 19:23:41.755–19:33:48.860347, 607.105347 s, not ten minutes of the last
stretch alone. The log's first driving interval is 19:23:49.048–19:28:34.480;
the second is 19:28:48.813–19:34:32.587. Earlier event type is unclassified;
do not relabel it a race or infer it from PostRace menu filenames. The final
chase overlaps the trace for about 300 s. Apply five-second guards around actual
gameplay boundaries AND trace endpoints: primary trace-relative window
312.058–602.105347 s, 290.047347 s, wall time 19:28:53.813–19:33:43.860347.
Earlier guarded window 12.293–287.725s,275.432 s, is secondary only.

Device is M4 iPad Pro 13-inch, iPadOS 27.0.1 (24A446); Instruments 27.1, attached
LiveContainer PID 2532. Time Profiler binary UUID is exactly IPA22
`3CDAD6C3-51F9-372C-B7C5-DB5B3FBF1640`, load address 0x10fe4c000. Renderer
build Oct 18 19:11:46; both SDK UUIDs match the preceding device logs. Log confirms
scale 1.500, cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0; all accumulated switches
ON, including fused sizing, base + bulk 32 attribute comparison, lookup, mixed GPU
selector and lookup stats, Utility queue, lazy diagnostics, copy patches,
texture masks, draw arena and master group. No Low Power Mode suffix appears.
Requested Battery mode OFF/system Low Power Mode OFF is consistent with logs;
no default or option changes were made for analysis.

SystemPowerLevel and DisplayBrightnessLevel both report 34% throughout. The
thermal table is Nominal for the entire 607.105 s; all 210 log thermal observations
are nominal. DeviceChargingState exports zero rows, so unplugged state cannot
be independently established from that table. CPU cluster/GPU-state/performance-
state and dyld-load selections export no sample rows despite their TOC entries;
CPU stack binary metadata is available. These exports do not establish GPU
utilization, limiter, CPU/GPU clocks or voltages. No new capture debugging needed.

Interval-weighted power/model measurements, clipping each source interval to
the analysis window and excluding sentinel values:

| Phase | Seconds | System drain estimate, battery pp/hour | CPU impact | GPU impact | Display impact | Network impact |
|---|---:|---:|---:|---:|---:|---:|
| Whole recording |607.105|32.407|11.525|2.198|5.784|0|
| Earlier unclassified gameplay, guarded |275.432|33.587|12.458|2.141|5.887|0|
| **Confirmed chase, guarded** |**290.047**|**31.956**|**11.088**|**2.273**|**5.731**|**0**|
| Both guarded gameplay intervals |565.479|32.751|11.755|2.209|5.807|0|

Power-usage coverage is essentially complete within the primary window
(290.047334924s). Impact scores are dimensionless modeled subsystem indicators;
do not add them, divide them into energy fractions or call them watts. Whole-
device drain estimate is not app-only consumption. Chase CPU core-equivalent
from QoS durations 94.68% of one core; retired instructions about 9.968 billion/s.
No ON/OFF arm exists. Comparing this to earlier 0.85x / 30 FPS traces cannot isolate
IPA21/22 gains or establish regression: resolution, rate and gameplay differ.
CPU still deserves priority based on the model plus CPU sample attribution;
GPU timing is headroom, not proof that GPU or memory traffic is cheap.

Log metrics require complete five-second intervals inside the guarded primary
window; CPU percentages require complete ten-second intervals:
- 57 summaries / 17,100 reported frames, all 60.0 FPS. Pacing 20/17,100 off-grid
 (0.117%), worst logged deviation 8.3 ms; no broad missed-deadline problem shown.
- Median recording 1.88 ms, encoding 5.10 ms (includes drawable waits), GPU 4.08 ms.
  Last-frame draw count median 2,496; this is not the average of every frame.
- 28 CPU intervals, mean 94.36%, median 95.5%, range 69–129% of one core. These
  interval windows differ slightly from QoS duration clipping.
- Attribute front-cache 120,251,574 hits / 22,122,121 misses / 0 bypasses (~84.46%).
  GPU buffer front cache 120,643,981 hits / 4,125 empty misses / 54,274,621 collisions
  (~68.97% hits). No comparison of raw coverage with different scenes is a win
  or regression claim for the selector; no disabled arm provided.
- No error-level lines in guarded confirmed chase and no GPU-failure messages
  anywhere. Earlier recording includes a watchdog dump 19:28:15.575 and recovery
  warning 19:28:16.578, with semaphore details; its five-second FPS summaries
  remain 60. Startup and post-pause diagnostics also occur. Do not claim the
  entire file error-free or assume the watchdog is a demonstrated 5 s image freeze.
  This was not investigated as a recurrence of the parked iPhone issue.

Time Profiler, primary guarded chase: 266,762 ms running sample weight,
266,762 rows. Self shares and inclusive regions describe CPU time, not power;
inclusive rows overlap and must not be summed:

| Region | CPU share | Meaning |
|---|---:|---|
| Native render task, including driver calls/destruction |35.767% inclusive|99.971% of its running weight on E cores|
| NativeDraw recording role |10.442% inclusive|Mostly P cores; includes Record and callees|
| Guest __imp__sub_ functions |26.524% self|Original game work plus translated implementation; not all removable|
| RenderFrame main function |7.800% self|Excludes separately outlined lambdas|
| Record main function |5.369% self|Same-frame content validation retained|
| Guest sub_82699100 |2.293% self|Earlier copy optimizations already active|
| Fingerprint |1.113% self|Required mutation detection; don't skip it|
| std::map<string,Target>::operator[] |1.042% self|Repeated target lookup candidate|
| Draw destructor |0.992% self|Ownership/lifetime work; not safe to remove wholesale|

Overall P/E running weights 63.955% / 36.045%. Render task already runs almost
entirely on E cores; repeating Utility QoS experiments is not the next target.
The ~5.233% unsymbolicated IOKit leaf 0x1a46a4f19 resolves, using UUID-matched
DeviceSupport symbols, to iokit_user_client_trap + 9. Its major callers are GPU
command queue submission (13,933ms), not proven application busy-polling.
There is one normal frame command-buffer commit; separate BC decode submission
is not evidence of redundant main-frame submission. Removing driver calls or
waits without semantic proof is not proposed. UUID-matched libsystem_platform
leaves0x1a19ac055 and0x1a19ab9cd resolve to memmove+181 and memset+141; these
include multiple call sites/driver work and are not wholly redundant app copies.

Instruction/source checks of the matched IPA22 binary:
- Ready-pipeline hash/find main block0x10007b998..0x10007bc00 has 1,850 ms self,
  0.6935% app CPU, excluding ARC calls and other pipeline work. Useful secondary
  candidate; any front cache must retain full key, successful-ready-only state,
  asynchronous collection and failure behavior.
- Per-texture resolve-map check0x10007ce34..0x10007cebc has 1,190 ms, 0.4461%; maps
  change after resolves, so cross-draw reuse would need correct invalidation.
- GPU-buffer lookup/bind main block0x10007fbf0..0x10007ff0c has 4,705 ms, 1.7637%,
  excluding outlined backing map 0.726%. Includes binding, diagnostics, ownership
  and real uploads: not all recoverable. Lookup statistics are ON consistently.
- Attribute front-check main block0x1000b6a30..0x1000b6ca4 has 2,778 ms, 1.0414%.
  Fused-sizing inspected subrange0x1000736a0..0x100073764 has 3,297 ms, 1.2359%;
  neither establishes gains versus the differently configured IPA20 profile.
  Sampling skid/cache stalls limit exact per-instruction cost interpretation.

Recommended next isolated experiment, pending approval: **reuse the last exact
render-target lookup result in each hot draw traversal**. This is preferable
as a low-risk first step to replacing the renderer's string identity system.
The existing persistent std::map<string,Target> has stable node addresses and
no erasure; values are mutated/resized in place. Consecutive draws often use
the same target, but both the frame setup and encoding loop call operator[].
Primary chase lookup caller attribution: 1,674 ms at call0x100079f54 (encoding),
1,067 ms at 0x100074034 (frame setup),39 ms elsewhere; total 2,780 ms / 1.042% app CPU.
These two sites account for 98.6% of target-map self weight. Stack non-leaf PC
flags were masked to instruction boundaries and matched to actual bl sites;
leaf PCs normalize using UUID/load address and low tag bit removal.

Proposed scope:
- Production: ios/src/native_renderer.mm only. Independent default-false
  restart-only switch. A small frame-local last-key/Target* cache per hot
  traversal uses full existing string equality, returns the live map value,
  and calls the original operator[] on a miss. Preserve original fallback,
  map keys/order, insertion behavior, MRT identities, resize/format mutation,
  resolves, diagnostics and all Metal resource operations. Cache no copies of
  target textures, no missing entries; reset cache before each traversal.
- Add tools/native/test_target_lookup.py extracting the actual helper when
  implemented: differential ON/OFF identity, exact keys, repeated/interleaved
  layouts, insertion while cached, live target replacement/resizing, MRT and
  frame reset tests under sanitizers. Benchmark long same-target runs and
  alternating/miss-heavy layouts; include switch overhead, inspect iOS ARM64.
- No change to shaders, graphics defaults, guest or SDK code. Expected total
  gain is modest and unmeasured; the entire 1.042% is not a guaranteed saving.
  If host/codegen evidence is favorable, build an independently gated IPA and
  get one short correctness run, retaining the stacked-testing strategy.

Other priorities: pipeline ready lookup and resolve metadata reuse are secondary;
a broader PM4/guest draw-state bypass has a higher possible ceiling but lacks
measured equivalent-path savings and carries substantial ordering/query/fence
risk. Do not repeat patched guest copy loops, content-check skipping, write-watch
experiments or core-QoS changes. No further trace is needed to propose the
isolated target-lookup step. User approval remains required before implementing.

All exports completed successfully. Essential findings are retained here;
temporary analysis files are /tmp/nfsmw_oct18_power2_{toc.xml,tables.xml,cpu.xml,
metal.xml,summary.json,cpu_summary.json,windows.json,analyze.py,cpu.py,
target_callers.py,target_callers.json,render_disassembly.txt}. A temporary caller
PC display initially missed flagged unaligned non-leaf addresses; correcting
normalization located the actual call sites. No app, SDK, shader, defaults or
IPA modifications; Markdown checkpoint updated. No push/release.

### October 18, 2026 — IPA23: last exact target lookup reuse

User approved the preceding target-reference proposal. Production changes are
confined to ios/src/native_renderer.mm. New independent restart-only flag
`nfsmw_native_target_lookup` defaults false and is read once per RenderFrame
through a cached launch value. It does not enable or disable earlier experiments.
The frame-setup traversal and primary encoding traversal each construct their
own TargetLookupCache, retaining only a pointer to an existing map entry.

ON: if the previous entry's full std::string key equals the requested key,
return its live mutable Target. On a miss, try_emplace(requested) obtains the
map node with the same default-value insertion semantics as original operator[].
The map owns both the const key and mutable Target, so no second key string,
texture reference or target state is copied/retained. Insertion preserves node
addresses, and this renderer does not erase targets during either traversal.
Caches have separate traversal lifetimes and do not persist across frames.
OFF calls original targets[requested]. Existing secondary/MRT lookups remain
unchanged. No target identity, string-map order, creation/resize, resolve,
clear flags, rendering order, diagnostic snapshots, shader or resource operation
is bypassed. The two optimized call sites are the ones measured previously.

A small member always_inline annotation keeps cache selection at the call sites;
flag selection is outside both loops. Periodic renderer log identifies mode:

```
[native] target lookup: frame-local last target (exact key, live target, restart required)
```

OFF logs `original map`. This is an optional incremental CPU experiment, not
a wholesale renderer/guest rewrite or an established battery saving.

The initial implementation held its own std::string copy of the last key and
Target*. It called original operator[] on a miss. Correctness passed, but the
extra key assignment made miss-heavy host layouts slower. Before building,
refined it to borrow the existing map node/key and use default try_emplace on
miss. OFF behavior remains original operator[]. This differs mechanically from
the proposed miss call, while preserving its exact map insertion and lookup
semantics; this is within the approved last-target reuse scope. Both versions'
negative results are retained instead of claiming a universal speedup.

Extracted production fixture:

```
python3 tools/native/test_target_lookup.py --benchmark
```

Both initial and final helpers pass OFF/ON at -O1 ASan/UBSan and correctness
again at -O3: 720,102 checks per configuration. Coverage includes empty, embedded-
NUL and long keys, differences in each representative EDRAM key component,
different string objects with equal bytes, temporary/mutated caller strings,
map rotations through hundreds of unrelated insertions, exact returned node
identity, live dimensions/format/flags, in-place target replacement, resource
rebinding without cache ownership, primary/MRT aliasing, distinct primary and
secondary keys, frame resets and two traversals over 2,000 randomized frames.
Randomized final maps/values/order are compared to an independent original-map
reference. Frame-boundary map clears were moved before construction of the new
frame's caches, after the previous caches are destroyed. The fixture also checks
the two intended source integration sites and retained secondary-map operation.

The test substitutes CPU Target fields plus shared resource tokens for actual
Metal objects; it checks lookup identity, visibility and ownership, not GPU
execution/texture resize correctness. The pending device visual test remains
necessary. No unrelated broad suite was rerun for this isolated lookup change.

Seven alternating host trials per layout. Each timed trial is 1,000 frames ×
two independent traversals × 2,400 draw keys = 4,800,000 lookups. It runs the
actual cached-switch/helper path; original direct map is an additional control.
A full 4.8-million-lookup warm-up precedes timing. Draw count includes warm+timed
operations. Payload/checksums and insertion counts match across all three arms.

| Layout | Initial original / OFF / ON median ms | Final original / OFF / ON median ms |
|---|---|---|
| one-target: same key for 2,400 draws |40.654 /40.540 /14.345|40.652 /41.035 /13.901|
| runs: 12 targets in 50-draw runs |43.237 /43.224 /17.934|43.246 /43.117 /17.504|
| short-runs: 12 targets in four-draw runs |46.811 /45.751 /23.562|45.591 /45.946 /23.986|
| alternating: 12 targets, new key each draw |42.623 /42.576 /51.428|43.467 /43.470 /49.813|
| many-targets: 256 targets, new key each draw |95.818 /101.683 /116.694|103.638 /95.403 /106.385|
| long-keys: 50-draw runs, >120-byte keys |58.420 /58.601 /31.241|57.507 /57.495 /30.348|

Final repeated-target workloads are ~47–66% faster versus current OFF for this
lookup fixture. Alternating is ~14.6% slower, many-targets ~11.5% slower versus
current OFF. Different original/OFF controls for many-targets show host timing
variability; neither a universally identical OFF timing nor an across-run
refinement speedup is claimed. Cache checks still cost time when every lookup
misses. Expected normal target runs motivate device testing, but this is not
an actual device target-key replay or a measured hit rate. Source/sample
analysis bounds direct opportunity at about 1.04% of app CPU, only partly
recoverable. No whole-app or device energy percentage follows from host gains.

Matching checksum / draw updates / entries for all seven trials and modes:
- one-target: 4608000000 /9600000 /12
- runs, short-runs, alternating, long-keys: 4634400000 /9600000 /12
- many-targets: 5204640000 /9600000 /256

Final iOS build `cmake --build --preset ios --target ipa -j 6` passed with 13
existing FPSCR/UIKit warnings. Optimized ARM64 inspection shows the cached
flag loaded once per frame and helper logic inline. Setup uses x28 for the
last map entry, with length/full-byte comparison at0x100073e78..0x100073ed0;
a hit branches to0x100074248 and returns existing node value. Encoding keeps
its own pointer at stack+0x330; check0x100079dac..0x100079e10, hit returns live
value at0x100079e2c. Both cache hits branch around the tree lookup. String
equality calls a byte comparison routine; it is not a completely call-free
fast path. ON misses and OFF calls reach the same default-insertion tree
routine0x100098fac. No standalone TargetLookupCache::Find/TargetLookupEnabled
symbol or custom helper call per draw remains. This verifies code shape,
not device speed or energy. No further source refinement was made after tests.

Final artifact `ios/build/NFSMW-battery-target-lookup-23.ipa`,29,945,793 bytes.
UUID `18262CD0-8C95-3E09-B2C1-26931A50BED2` (arm64).
SHA256 `dd300305e12bc45adf890a505e2a2978fd3ed350b833859e7500d7c8f564b644`.
ZIP CRC passed, packaged executable equals signed cache app, strict deep
codesign passed. All 104 actual .metallib payloads and both bundled SDK dylibs
are byte-identical to IPA22; AppleDouble records excluded. SDK, guest and shader
sources were not edited. No provisional named IPA23 was issued.

Pending next action: one short iPad event, same accumulated Extra Args as IPA22,
including fused sizing and bulk attribute comparison ON. Add only
`--nfsmw_native_target_lookup=true`, fully force-quit LiveContainer, usual
1.5x /60 FPS, Battery mode OFF and system Low Power Mode OFF. Supply log and
visual/stability report. Do not request another long small-change power A/B
or stack another implementation before this check. New default remains false.
No push, release, attribution line or author configuration change.

Temporary outputs /tmp/nfsmw_target_lookup23_tests.txt (initial),
/tmp/nfsmw_target_lookup23_final_tests.txt, /tmp/nfsmw_target_lookup23_build.log,
/tmp/nfsmw_target_lookup23_disassembly.txt; essential evidence retained here.

Implementation, extracted fixture and validation record saved in local commit
`5e612c8` on `battery-optimization`. Device validation remains pending.


### October 18, 2026 — IPA23 first iPad correctness result

Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_5_ipad.log`
(1,544 lines), user reports "still looks jsut fine". Renderer built Oct 18
19:48:54, consistent with IPA23. Mode line confirms:

```
[native] target lookup: frame-local last target (exact key, live target, restart required)
```

Fused upload sizing and base + bulk32 attribute comparison/front cache remain
ON, along with earlier master group, native copies, mixed GPU selector and
lookup statistics, Utility rendering, lazy diagnostics, texture masks and draw
arena. Graphics remain scale 1.500 / cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0.
Requested Battery mode OFF / system Low Power Mode OFF; no LPM suffix appears.
No brightness or power recording provided; this is an initial correctness run.

Driving 20:01:56.374–20:03:10.142 (73.768 s), ending at scene resigns active.
As before, exclude five seconds at each transition and accept only complete
five-second renderer/pacing windows, complete ten-second CPU windows within
20:02:01.374–20:03:05.142.

| Guarded metric | Result |
|---|---:|
| Renderer summaries / reported frames |12 /3,600|
| FPS in every summary |60.0|
| Off-grid pacing / frames |0 /3,600|
| Worst grid deviation |0.0 ms|
| Median sampled recording |1.455 ms|
| Median encoding, including drawable waits |7.51 ms|
| Median GPU |4.12 ms|
| Five CPU intervals |82 /78 /80 /96 /90% of one core|
| Mean / median CPU |85.2% /82%|
| Mean last-frame draw count |2,376.5|

All 33 thermal observations in the file are Nominal. No error/critical-level
or GPU-failure messages. Six guarded gameplay NtCreateFile warnings are asset
probes; user reports no visual issue. Do not attribute changes in the CPU or
recording/encoding summaries to target lookup reuse from differing short scenes;
this is not an isolated speed or energy comparison. Recording is sampled,
encoding includes waits and draw counts describe the last frame per summary.

Loading hitch 20:01:56.448 (41.7 ms swap interval) includes 241 texture decodes,
61,673 KiB / 31.9 ms, outside guarded gameplay. Post-background encode hitch at
20:03:10.446 is 282.9 ms, of which 275.3 ms waits for a drawable; exclude it. Raw
battery log moves 55% to 50% in one coarse step in this brief run. No controlled
power recording or starting-state evidence supports extrapolating that delta
into a drain rate, optimization gain or regression.

Outcome: initial IPA23 visual/correctness check passes. Preserve
`--nfsmw_native_target_lookup=true` alongside the previous accumulated flags;
compiled default remains false. No repeat short test, new IPA or tiny-change
power A/B requested. Sustained stability and device energy gain remain unproven.
Only Markdown updated; no new implementation authorized by this log submission.
iPhone loading and other parked diagnostics remain parked. No push/release.


### October 18, 2026 — next proposal: reuse last ready pipeline lookup

After IPA23's initial check, user asks what comes next. Read-only source/profile
review confirms another small CPU candidate in PipelineCache::Get. Its first
operation searches ready_ using the full PipelineKey hash; later encoder state
caching suppresses redundant pipeline binding but does not avoid this search.
The existing UUID-matched IPA22 confirmed-chase profile attributes 1,850 ms /
266,762 ms = 0.6935% app CPU self to ready hash/find main block
0x10007b998..0x10007bc00 (exclusive). This includes cache lookup work and excludes
ARC callees/other pipeline operations; do not promise recovery of the whole
region or translate the CPU fraction to energy. IPA23 changed target lookup,
not this pipeline source path; no new profile is needed to propose a candidate.

Current lifecycle: only successful non-nil pipeline states enter ready_; Finish
keeps the first successful entry when demand and warm compilation duplicate it.
No ready_ erasure/clear exists. Get and Collect run on the renderer's serial
queue; background compilation only appends Done records under the mutex.
A borrowed ready-map node remains valid across insertions/rehash. A small last-
successful-entry check can therefore return the same strongly map-owned PSO on
full key equality without extra cached PSO ownership. PipelineKey contains a
bool and possible padding, so use its existing field operator==; the attribute
key's representation guards/raw comparison do not apply here.

Proposed production scope, **pending approval**, ios/src/native_renderer.mm:
- Independent default-false restart-only pipeline lookup switch. Select once
  per RenderFrame and pass the mode into the sole pipeline_cache.Get call;
  avoid introducing a cached-flag guard/function call per draw.
- Before ready_.find, optionally compare the last ready entry's full key. Only
  a successful ready-map lookup updates that reference; cache no nil/failed/
  still-compiling responses. On mismatch use the original Get path, with
  unchanged failed out-parameter semantics, descriptor generation, async
  demand/warm scheduling, Collect, duplicate completion and archive behavior.
- Retain every PipelineKey field, actual pipeline binding/state filtering,
  draw order, render-target formats/sample counts, shader variants and all
  GPU resource/PSO lifetimes. No shader, guest, SDK, graphics-default edits.

Add tools/native/test_pipeline_lookup.py for extracted lookup/control behavior:
exact identity for every field, collision/miss behavior, ready insertion/rehash,
failed and pending requests becoming ready, duplicate results and owner lifetime.
Include original disabled path, actual switch overhead, repeated-key and
all-miss host benchmarks, then optimized iOS ARM64 inspection. Host fixtures
alone do not establish rendering or device energy; if favorable, make a gated
build and request one short correctness run under the existing normal settings.
A simpler last-entry cache has miss overhead too; preserve negative findings.

Following a successful device check, recommend a matched accumulated-batch power
comparison for IPA21 fused sizing, IPA22 bulk attribute keys, IPA23 targets and
this proposed pipeline step before adding further small caches. Both arms must
hold graphics/FPS, brightness, LPM state, gameplay type and prior stack fixed;
old mixed-setting recordings cannot serve as that control. This future proposal
is not a request for another recording now or authorization for code/default
changes. CPU work still warrants priority, but this is an incremental target;
a broader guest/PM4 bypass needs separate evidence/ordering analysis.

No app or SDK source, flags, IPA, archive persistence or capture changed in this
review. Checkpoint and proposal saved in Markdown; implementation approval is
pending. No push/release.

### October 18, 2026 — IPA24 exact last-ready pipeline lookup

User approved the preceding pipeline-lookup proposal. Production source change
is confined to ios/src/native_renderer.mm. Independent restart-only flag
`nfsmw_native_pipeline_lookup` defaults false, selected once per RenderFrame and
passed to the only PipelineCache::Get caller. Earlier switches remain intact.

PipelineLookupCache<Value> holds one raw pointer to the map-owned key/value
pair. ON compares all 11 existing PipelineKey fields with original operator==;
no padded-object memcmp, new hash, guessed shader identity or PSO copy. A match
returns the same ready-map entry. On mismatch/OFF it performs original find;
only a successful ready-map lookup updates the optional pointer. A miss leaves
it alone and follows original Get failure/descriptor/compilation behavior.
A newly synchronously compiled PSO is not cached by the shortcut until a later
successful ready-map lookup. No nil/pending/failed response is cached. Lifetime
relies on existing successful ready entries never being erased/replaced and
unordered_map node stability across rehash. Background compilation still only
queues Done records; serial renderer Collect/Finish publishes actual readiness.

Actual Get suffix from failed_.count onward, entire Finish and Collect are
byte-identical to Git reference 8623510. Pipeline creation, async warm/demand,
duplicate completion, failure out-parameter behavior, encoder-state filtering,
PSO ownership, draw order and all resource/shader work remain unchanged. One
borrowed pointer adds no extra retained PSO. No archive persistence changes.

Test command:

```
python3 tools/native/test_pipeline_lookup.py --benchmark
```

The new Objective-C++ fixture extracts actual key/hash/helper/Get/Finish and
compares candidate Get to the pinned original method, with Foundation pipeline
objects and descriptor/compilation stand-ins. Source guards require unchanged
miss suffix, Finish/Collect and correct frame/caller integration. This tests
actual lookup/control behavior and ARC ownership, not actual Metal compilation,
GPU rendering or concurrent scheduling. Original scheduling code is unchanged.

Initial fixture attempt had two bugs: its descriptor class reused the real
MTLRenderPipelineDescriptor runtime name (duplicate-class warning), and repeated
rehash doubled buckets without a bound. It reached the first sanitized arm,
then was stopped by terminating our owned test PID 57211. Default sandbox denied
the signal; escalation succeeded. No automatic approval rejection occurred.
Renamed the stand-in FixturePipelineDescriptor (including extracted method type
references) and bounded randomized rehash to 256–1280 buckets, then reran. This
was a host-fixture failure, not a device/app regression; no provisional IPA built.

Corrected fixture exits 0. Candidate OFF/ON pass -O1 ASan/UBSan and correctness
again at -O3, each 60,456 differential checks. Coverage:
- Every one of 11 key fields differs independently, original failed-output value
  retained on ready hits, forced bucket collisions, insertion/rehash and stable
  borrowed-node identity.
- Actual Get/Finish synchronous success/failure/Objective-C exception, missing
  descriptor, pending demand deduplication, warm failure/retry, publication of
  readiness, duplicate success/failure keeping the first PSO, and later ready
  entry taking precedence over an old failed-set entry.
- Weak-reference check with real Foundation ARC objects proves the shortcut
  does not retain a second PSO owner; test-only map erasure is followed by no
  further lookup. Production ready_ does not erase.
- 500 frames / 60,000 randomized requests including completion, warm races,
  failed-output inputs and repeated/missing/ready requests; candidate and original
  maps, sets, work requests, compile counts and bookkeeping match after each step.

Seven alternating optimized host trials per layout; three arms: original Get,
current OFF, current ON. Each timed trial is 2,000 frames × 2,400 requests =
4,800,000 calls after a full-size warmup. Candidate launch value is selected
once/frame, actual Get and ARC return path are included. All requested entries
are ready in timing tests: "miss-heavy" means misses of the new last-entry
shortcut, not shader compilation. No actual GPU commands are submitted.

| Synthetic layout | Original median ms | OFF median ms | ON median ms |
|---|---:|---:|---:|
| One pipeline |102.234|103.070|88.889|
|12 pipelines, 50-draw runs |108.969|110.001|90.274|
|12 pipelines, four-draw runs |121.873|124.658|109.204|
|12 alternating pipelines, early mismatch |136.693|139.533|139.544|
|256 alternating pipelines |138.065|140.929|141.491|
|12 alternating keys differing in alpha_spec, later mismatch |125.129|127.886|151.610|

Repeated-key fixtures are 12–18% faster against current OFF. Two early-mismatch
fixtures are approximately unchanged (many-pipelines ON 0.4% slower), but late-
field mismatch is 18.6% slower. OFF/original codegen/timing varies; no universally
identical OFF performance, actual device key distribution or energy benefit is
established. No attempt was made to hide this cost through weaker equality.
The targeted hash/find region was 0.6935% of app CPU in the confirmed chase,
only partly recoverable, so host percentages cannot become whole-app savings.

Matching checksum / ready entries / zero compilation requests across all modes:
- one:12732845799654063104 /1 /0
- runs, short-runs, alternating:4472847380238121088 /12 /0
- many:18231629890471510704 /256 /0
- late-mismatch:7021216598412459136 /12 /0

Final iOS build `cmake --build --preset ios --target ipa -j 6` passed with 13
existing FPSCR/UIKit warnings. ARM64 main-frame inline path at 0x10007b8cc..
0x10007b98c checks cached mode/pointer then all fields, with bool loaded as one
byte. Success branches to 0x10007bc10, bypassing hash/find at 0x10007b990 onward;
OFF/mismatch uses original search and pending/failure paths. No custom Find,
PipelineLookupEnabled or PipelineCache::Get call per draw; no extra always_inline
annotation on Get was necessary. Helper itself has a small always_inline member
annotation. Node storage is one pointer, no additional owned PSO. This confirms
code shape, not device performance. No source edits after passing host tests.

Final artifact `ios/build/NFSMW-battery-pipeline-lookup-24.ipa`,29,946,097 bytes.
UUID `6E360E6A-9918-3D39-B4FE-70B755E02D30` (arm64).
SHA256 `7adc3d1885b29f7921e72b2f80a4b6bed50e55deffc2fe48a3bfb5365af367a9`.
ZIP CRC passed; packaged executable equals signed cache app; strict deep codesign
passed. All 104 actual .metallib files and both bundled SDK dylibs are byte-
identical to IPA23 (AppleDouble records excluded). SDK, guest, shaders, graphics
and earlier experiment defaults unchanged. Periodic mode log:

```
[native] pipeline lookup: last ready entry (exact key, ready results only, restart required)
```

OFF identifies `original map`. New flag stays compiled-default false.
Pending one short iPad event: retain all previous accumulated arguments,
including IPA21 fused sizing, IPA22 bulk comparison and IPA23 target lookup ON;
add only `--nfsmw_native_pipeline_lookup=true`. Cold force-quit LiveContainer;
usual 1.5x / 60 FPS, Battery mode OFF, system Low Power Mode OFF; log and visual/
stability check. No next implementation before that validation.

After this check, recommend a matched power comparison of these four accumulated
changes ON versus OFF, preserving earlier stack, manual brightness, normal
resolution/FPS, system Low Power Mode state, thermal starting state and comparable
gameplay. These flags are independent of nfsmw_battery_optimizations; do not use
the master as a substitute or change earlier QoS/graphics behavior between arms.
This is the next measurement proposal after correctness, not another request
for a tiny isolated power A/B now. No device energy improvement established.

Temporary outputs /tmp/nfsmw_pipeline_lookup24_tests.txt (stopped initial fixture),
/tmp/nfsmw_pipeline_lookup24_final_tests.txt (corrected complete run),
/tmp/nfsmw_pipeline_lookup24_build.log, /tmp/nfsmw_pipeline_lookup24_disassembly.txt.
Essential failures/results/build identity retained here and checkpoint updated.
No push, release, author configuration change or attribution added.

Implementation, fixture and evidence saved in local commit `9474672` on
`battery-optimization`; initial IPA24 device validation remains pending.


### October 18, 2026 — IPA24 first iPad validation passes

Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_6_ipad.log`;
user reports "everything is fine". Renderer built Oct 18 20:14:16, consistent
with final IPA24. All 23 pipeline mode lines confirm last-ready-entry reuse;
fused sizing, bulk attribute comparison/front cache, target reuse and earlier
stack remain ON. Settings scale 1.500/cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0;
no LPM suffix. Requested normal Battery mode OFF / system Low Power Mode OFF.
The file has 2,742 lines; final partial timestamp is excluded from parsing.

Driving 20:21:32.432–20:22:51.576, 79.144 s, ends with scene resigns active.
Five-second transition guards and complete-window rules leave 13 summaries /
3,900 frames: every summary 60.0 FPS; pacing 0/3,900 off-grid, worst 0.0 ms. All 39
logged thermal observations Nominal. Median sampled recording 1.49 ms,
encoding 8.64 ms including waits, GPU 4.12 ms. Six complete CPU intervals
81/80/92/96/100/81%, mean 88.33%, median 86.5% of one core. Mean last-frame draw
count 2,396.62, not average over every frame. No isolated shortcut speed or
energy conclusion follows from comparison with other short scenes.

No gameplay error-level lines or GPU failure messages. Existing watchdog/
semaphore groups occur 20:21:09.460 and 20:21:26.508, before driving. They do not
justify reopening the parked iPhone issue. Loading hitch 20:21:32.500, 41.2 ms
swap interval, includes 243 texture decodes / 61,871 KiB taking 32.3 ms, outside
guarded sample. Battery reports 50% throughout. No power trace; cannot infer
energy savings from this check. Initial visual/correctness pass, sustained
stability and energy benefit unproven. Default stays false, keep switch ON
with accumulated args; no repeat short run or new build required.

Next recommendation is a matched same-build power comparison of the recent
four independent controls (fused_upload_sizing, attribute_bulk_compare,
target_lookup, pipeline_lookup), OFF then ON. Detailed protocol and exact
arguments are saved in DEVELOPMENT_PROGRESS.md. Keep all older experiments
including attribute lookup/master group, normal 1.5x/60, LPM/Battery mode OFF,
manual brightness and comparable thermals/connectivity fixed. Restart the same
Challenge Series pursuit for each 8–10 minute recording, start capture during
gameplay, save paired logs/working Power Profiler + Time Profiler + Thermal State
traces. Fully force-quit LiveContainer before both arms; replace the four
existing entries, do not append contradictory duplicates or clear other args.
This isolates the recent batch, not the entire branch; it remains proposed,
not already measured. Gameplay variability/order limit conclusions. Review
batch evidence before additional cache implementations; no next source change
approved. No production changes or push/release in this analysis.

User replied "continue" following the validation update. Provide the batch
comparison instructions above; next input is the two paired logs/traces.
No batch result or new implementation is implied by that reply.

### October 19, 2026 — shared session protocol recorded

Documentation-only session following Stefan's explicit startup, evidence and
handoff requirements. Read AGENTS.md completely, DEVELOPMENT_PROGRESS.md,
BACKLOG.md and the newest TECHNICAL.md entries; reviewed the recent documentation
commits `fc27788`, `6368386` and `4246e94`. Also checked CLAUDE.md: it points to
AGENTS.md and the shared checkpoint. No parallel status or evidence file added.

Observed commands (all exit 0): `cat AGENTS.md`,
`cat docs/DEVELOPMENT_PROGRESS.md` (tool output truncated; read the missing
middle with `sed -n '230,490p' docs/DEVELOPMENT_PROGRESS.md`),
`cat docs/BACKLOG.md`, `tail -n 200 docs/TECHNICAL.md`,
`wc -l docs/DEVELOPMENT_PROGRESS.md docs/TECHNICAL.md` (720 / 2,968 lines before
edits), `git status --short --branch` (battery-optimization, only
`?? HANDOFF_CHATGPT.md`), `git log --oneline -15` (15 entries, HEAD `fc27788`),
`git show --stat fc27788 6368386 4246e94`,
`git show fc27788 -- AGENTS.md docs/BACKLOG.md docs/DEVELOPMENT_PROGRESS.md`,
and `cat CLAUDE.md`. Backlog/instruction search found no assigned B-/D-numbered
entries in the checked files; retained the existing unnumbered items.

Updated AGENTS.md with the ordered startup checks, exact-evidence requirements,
existing-file and stable-ID rules, private-material handling and mandatory
end-of-session documentation/local commit. Updated checkpoint/working rules and
the existing active battery item; corrected its checkpoint link for October 19.
Pre-existing HANDOFF_CHATGPT.md remains untouched and untracked by the existing
explicit repository rule. No source, SDK, build procedure, flag/default or
release changed. No build, application tests or device measurements run; these
documentation checks establish no new correctness or energy result.

Validation: `git diff --check` exited 0 with no output. `git diff --stat` and
`git diff -- AGENTS.md docs/DEVELOPMENT_PROGRESS.md docs/BACKLOG.md docs/TECHNICAL.md`
both exited 0; reviewed changes are confined to those four documentation files.
`git status` exited 0 and listed those four modified files plus the preserved
untracked handoff. Local commit includes only those four documentation files.

Initial sandboxed `git add AGENTS.md docs/DEVELOPMENT_PROGRESS.md docs/BACKLOG.md
docs/TECHNICAL.md` and the subsequent `git commit` attempt each exited 128:
unable to create `.git/index.lock` (Operation not permitted). Documentation
edits remained intact and unstaged; retry requires the Git-metadata sandbox
escalation. This is a filesystem restriction, not a validation failure.
Escalated `git add` and `git commit` then each exited 0;
`git diff --cached --check` exited 0 with no output. Post-commit
`git status --short --branch` exited 0 and showed only the intentionally
untracked HANDOFF_CHATGPT.md. This success note is included by amending that
same local documentation commit.

Next action remains the documented matched IPA24 four-change OFF/ON power
comparison; await paired user logs/traces. No further source change approved.

### October 19, 2026 — IPA24 four-change pursuit power A/B

Inputs (new debug location):
- `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/19 October 2026/nfsmw_run_1_ipad.log`
- `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/19 October 2026/power_profiler_1_ipad.trace`

User confirms both arms restarted the same Challenge Series pursuit and gameplay
was kept as similar as possible. This answers the pending event-identity question;
do not request another recording on the assumption that the second arm is absent.
The trace contains BOTH recordings. Actual order is ON first, OFF second.

Repository is now `/Users/bep1s/Developer/GitHub/nfsmw-ios`, sibling SDK and
reference repository also under `~/Developer/GitHub`. Old Documents/GitHub cwd
no longer exists. Initial default-cwd execution failed with CreateProcess ENOENT;
subsequent commands use explicit workdir at the new repository. Startup branch
`battery-optimization`, HEAD `cdd04b2`, only untracked `HANDOFF_CHATGPT.md`;
pre-existing handoff preserved. Documentation-only analysis; no build or source
change, SDK mutation, flag/default change, push, publication or release.

Identity and controls:
- Run 1, `New Optimizations On`, 22:48:25.674+02:00, 600.471787 s, PID 3929.
- Run 2, `New Optimizations Off`, 23:00:25.586+02:00, 600.472493 s, PID 3935.
- Both NFSMW UUIDs match final IPA24 exactly:
  `6E360E6A-9918-3D39-B4FE-70B755E02D30`. Runtime UUID both
  `5EB416B2-DBBA-35B8-B411-EE9B10AA2E75`. Packaged IPA24 executable extracted
  to `/tmp/nfsmw_oct19_IPA24`; `xcrun dwarfdump --uuid` agrees. Log renderer
  build October 18 20:14:16 in both launches. No replacement IPA produced.
- Four restart-only settings ON then OFF: `nfsmw_native_fused_upload_sizing`,
  `nfsmw_native_attribute_bulk_compare`, `nfsmw_native_target_lookup`,
  `nfsmw_native_pipeline_lookup`. Mode logs confirm every change in both arms.
  Bulk comparison OFF retains attribute front cache ON; it is not disabling
  the earlier cache. Target/pipeline OFF return to original map lookup.
- Earlier five-option battery group stays ON, baseline elevated QoS OFF,
  native constant copies and transform copies ON; Utility rendering,
  attribute lookup, lazy diagnostics, higher-bit GPU buffer selector and lookup
  statistics, CPU draw pooling and resolve compression eligibility retained.
  Geometry arena range reuse OFF in both. Master battery flag is not this A/B.
- Scale 1.500, cap60, MetalFX OFF, FXAA OFF, forced MSAA0, no LPM suffix in either
  log. These establish logged controls, not independent proof of system LPM.
- M4 13-inch iPad Pro / iPadOS27.0.1(24A446). Constant 35% brightness. Entire
  trace duration Nominal thermal state in both arms; all407 log thermal
  observations Nominal. Charging-state table empty in both, so not independent
  proof of unplugged state. No GPU command-buffer failure messages found.

Method:
- Exported TOC and relevant tables with `xcrun xctrace export --input <trace>
  --toc --output /tmp/nfsmw_oct19_power1_toc.xml` and `--xpath` exports.
  Both runs have table10 ProcessQOSExecution,12 device-thermal-state-intervals,
  14 DeviceChargingState,20 ProcessSubsystemPowerImpact,22 time-profile,
  44 SystemPowerLevel,48 DisplayBrightnessLevel. Representative CPU query:
  `/trace-toc/run/data/table[@schema="time-profile"]`, output
  `/tmp/nfsmw_oct19_power1_cpu.xml` (347,004,335 bytes). Export completed.
  Local TOC/schema-driven parsing resolves all id/ref values. XML power table
  engineering type explicitly confirms percent-per-hour units; impact scores
  are dimensionless, not watts or additive energy shares.
- Python analysis `/tmp/nfsmw_oct19_analyze.py`: align log wall clock to each
  trace start; identify actual driving and pause/background transitions. One
  concatenated launch header has a partial timestamp prefix; recover the first
  complete timestamp without modifying the original log. 20,890 input lines.
- Five-second guards at driving/trace boundaries. Main comparison intersects
  both arms' active windows by elapsed time since event start, excluding either
  arm's pauses. Equal527.534787 s per arm. Common event-elapsed windows in s:
  [8.411,10.188], [25.055,388.467], [403.431,505.334],
  [518.532,558.473], [577.708,598.209787]. Trace starts are2.738 s and3.411 s
  after the first driving log respectively; subtract these offsets to reproduce
  trace-relative windows. Original unguarded active intervals saved below.
- Interval-weight power/impact/brightness with exact overlap duration; full
  coverage of main windows. Sum prorated process CPU instruction intervals
  (row-kind0) and QoS CPU durations. Complete five-second log summaries and
  ten-second CPU windows only. CPU utilization is a fraction of ONE core.
  Draw counts are one last-frame sample per log summary, not every-frame totals.

| Main equal-time guarded comparison | Four ON | Four OFF |
|---|---:|---:|
| Estimated system drain, percentage points/hour |34.1868|33.3576|
| Process CPU impact score |12.6924|12.2919|
| Process GPU impact score |2.3447|2.4020|
| Display impact score |5.9109|5.9118|
| Network impact score |0|0|
| QoS-derived CPU, % one core |110.114|109.074|
| Retired CPU instructions, billion/second |11.5769|11.3734|
| Complete log summaries / frames |101 /30,300|101 /30,300|
| Mean logged FPS |60.000|59.999 (one59.9 summary)|
| Off-grid pacing / sampled frames |69 /30,300|34 /30,300|
| Worst logged pacing displacement, ms |8.3|8.3|
| Mean recording, ms/frame (sampled) |2.1781|2.1251|
| Mean encoding incl drawable waits, ms/frame |5.9593|6.0308|
| Mean GPU, ms/frame |4.2991|4.3048|
| Median recording / encoding / GPU, ms |2.17 /5.96 /4.27|2.07 /5.88 /4.29|
| Mean sampled last-frame draws |2,893.48|2,809.15|

Main ON drain is2.49% higher (+0.8292 pp/hour), CPU impact3.26% higher,
GPU impact2.39% lower; display score essentially equal. ON retired1.79% more
instructions and last-frame draw samples average3.00% higher. This is NOT a
normalization formula: varying AI/traffic/camera/state can change non-draw CPU
work and cost per draw. Do not divide drain by draws to claim an energy gain.
Mean/median encoding point in different directions and include waits.

Sensitivity checks:
- Whole600.47 s recordings: drain34.1413 /33.3342 pp/hour (ON/OFF).
- Each arm's separately guarded active sample556.273 /562.407 s:
  drain34.1936 /33.3423. Unequal duration; secondary check only.
- Common event elapsed30–180,180–360,360–540 s: ON drain
  34.2482 /34.3681 /33.8915; OFF33.3936 /33.6807 /33.1836. Last band has
  151.838 s after pause exclusion. ON higher in every band, so whole-recording
  menu/pause contamination does not explain the direction.
- OFF emits three watchdog/semaphore groups inside gameplay at23:02:24.307,
  23:05:44.825,23:10:04.528:54 vigilante lines and1,539 semaforos lines within
  the main windows. ON has none in these windows. Both also have startup/menu
  watchdog activity. Logged rendering keeps progressing; these messages alone
  do not prove a visible freeze or establish a cause. Keep parked phone issue
  parked. Diagnostic log overhead remains a confound.
- Remove +/-5 s around each OFF gameplay dump from BOTH arms at matched event
  elapsed time:497.889787 s each, drain34.1285 /33.3994, CPU impact
  12.6997 /12.3468, GPU2.3019 /2.4243, CPU110.125 /109.688%,
  Ginst/s11.5723 /11.4414. Direction unchanged. This limited exclusion cannot
  remove all possible diagnostic effects.

CPU sampling and compiled-path check:
- `/tmp/nfsmw_oct19_cpu.py` resolves frames/binaries/stacks and weights in the
  exported time-profile, both runs642,068 /640,373 rows. Main windows contain
  565.321 /561.438 CPU seconds, equivalent107.163 /106.427% one core. Sampling
  differs from QoS accounting; do not present them as identical measurements.
- Self in guest `__imp__sub_` functions148.611 /170.705 s (26.29 /30.40% app
  samples); RenderFrame main46.905 /38.407 s (8.297 /6.841%); Record31.863 /
  28.485 s (5.636 /5.074%). Guest worker role includes original game work and
  translated work; it is not a measure of removable emulator overhead.
- Native render block incl callees204.299 /184.500 s; NativeDraw role63.781 /
  54.127 s; separate CommandProcessor role20.752 /13.228 s. Roles are assigned
  from available stacks (render first, recording second, then CP); inlining,
  unwind coverage and changed event work limit cross-arm interpretation.
  Overall P/E weights63.58/36.42% ON and63.25/36.75% OFF; these are CPU samples,
  not energy shares or evidence for another priority experiment.
- UUID-matched IPA24 disassembly (`xcrun llvm-objdump --disassemble
  --no-show-raw-insn --start-address=0x10007119c
  --stop-address=0x1000a2500 /tmp/nfsmw_oct19_IPA24`) confirms original pipeline
  hash/find0x10007b990..0x10007bbf8, added comparison0x10007b8cc..0x10007b990,
  map-hit shortcut pointer update0x10007bbf8..0x10007bc10. PCs normalized using
  EACH run's binary load address, low two tagged address bits masked.
- Original hash/find self0.755 /2.927 s, about74.2% fewer samples ON. But new
  comparison self2.066 /0.029 s; pointer update0.004 /0.003. Combined region
  2.825 /2.959 s, only0.134 CPU seconds lower over527.535 wall seconds (~0.025%
  of one core). Statistical samples/skid and small region prohibit an exact
  latency or energy claim. The shortcut operates; hash-only savings would
  overstate its net benefit. This is a reason to stop extrapolating synthetic
  repeated-key gains into large whole-game savings.
- Largest individual guest leaf remains sub_82699100,13.006 /13.726 CPU s;
  its previously optimized short copies are already enabled. Inspect remaining
  descriptor validation/dirty-state construction before any further patch.
  Keep guard/fallback/FPR semantics; do not repeat earlier copy experiments or
  remove content validation based on aggregate cost.
- GPU-buffer backing map self8.092 /6.459 s. Cache diagnostics still show
  122,704,349 /122,184,726 occupied-slot collisions over30,300 frames, against
  243,054,967 /232,261,893 hits and5,080 /4,766 empty misses. These are lookups,
  not GPU allocations. Higher-bit selector remains ON both arms. This is a
  remaining measured CPU cost, not evidence yet for an efficient replacement.
- Indexed Metal draw call site0x1000802a0 has25.239 /23.408 s inclusive;
  resolve-event lambda call0x100078ea8 has13.634 /18.273 s; main render-encoder
  creation call0x10007ae34 has5.792 /8.219 s. Driver costs and live rendering
  requirements cannot simply be removed. Need semantic/source audit before
  any batching or pass merging proposal.

Conclusion and next action:
The four-change batch has **no demonstrated whole-device power saving** in
this comparison; the measured direction is worse ON. Do not call it a proven
regression either: a single fixed-order pair, non-deterministic pursuit work,
model limitations, sample variation and logging differences remain. Do not
claim benefits from earlier baseline/entire-branch comparisons for this batch.
Keep the four flags experimental/default false; no silent removal or default
promotion. Earlier validated/default-on changes stay unchanged. User previously
asked not to abandon small inconclusive changes automatically; retain them for
future accumulated comparisons rather than repeatedly requesting this race.

Recommended next work is a read-only audit of larger repeated CPU work across
guest constant/state construction, Xbox draw submission/PM4 decoding and native
Record, using this existing profile. Main places to inspect:
`ios/src/native_renderer.mm`, `ios/src/game_constant_copies.h`,
`ios/src/native_draw_census.cpp`, `ios/src/ios_main.mm`, generated guest
sub_82699100 and SDK `CommandProcessor` draw/state path. Generated files must
not be edited manually. Seek a concrete state reuse/bypass that preserves
ordering, full state snapshots, mutation detection, fences/queries and resource
lifetimes before proposing a source change. Potential ceiling exceeds another
small lookup, but no safe shortcut or promised battery saving is established.
No further user trace is needed to begin that audit. No next implementation
approved; exact source scope/verification required before seeking approval.
The much larger previous30 FPS + system LPM result remains distinct evidence,
not directly comparable to1.5x/60 here. No visual compromise proposed.

Raw unguarded driving intervals (wall clock):
ON22:48:22.936–22:54:56.403,22:54:57.437–22:54:57.704,
22:55:01.367–22:57:46.409,22:57:55.644–22:58:28.410.
OFF23:00:22.175–23:00:37.363,23:00:42.230–23:08:52.509,
23:08:55.707–23:10:28.755. Transition guards discard the267 ms ON blip.

Temporary outputs: `/tmp/nfsmw_oct19_power1_{toc,tables,cpu}.xml`, six
`schema_*.xml` exports, `analyze.py`, `summary.json`, `windows.json`,
`analysis.txt`, `cpu.py`, `cpu_summary.json`, `cpu_analysis.txt`,
`sensitivity.py`, `sensitivity.json`, `sensitivity_windows.json`,
`sensitivity.txt`, `render_disasm.txt`, executable `IPA24`, all with prefix
`nfsmw_oct19_`. Temporary files are not the durable record; evidence, input
paths, windows, identities, methods, negative results and next action are
preserved above. Exports/analysis/disassembly exited0. An attempted old tmp
schema glob had no matches after tmp cleanup; re-exported fresh schemas. An
initial source-path probe `src/gpu/native_renderer.mm` failed (file absent);
`rg --files` located actual `ios/src/native_renderer.mm`. One overly broad
schema read was truncated; schema units verified in its header. No application
or test failure follows from those local inspection mistakes.

Documentation validation: `git diff --check` exited 0; reviewed diff/stat and
confirmed only TECHNICAL.md, DEVELOPMENT_PROGRESS.md and BACKLOG.md changed.
Existing author configuration remains Stefan Stoica. No application tests were
run for this documentation-only change. Save these three files in one local
commit; intentionally untracked HANDOFF_CHATGPT.md remains excluded.

### October 19, 2026 — broader CPU audit; GPR helper prototype proposed

After the matched pursuit result, Stefan replied "alright" to continuing the
read-only audit. This authorizes investigation, not a new implementation. Branch
`battery-optimization`, starting HEAD `ca379b1`, only intentionally untracked
HANDOFF_CHATGPT.md in main repository. The sibling SDK has extensive pre-existing
tracked, untracked and submodule changes; inspected read-only and preserved.
No production source, generated source, SDK, flags, graphics or build changed.

Evidence is the SAME IPA24 paired trace and common-event windows from the
preceding entry: ON / OFF over 527.534787 s each; CPU sample weight 565.321 /
561.438 s. UUID `6E360E6A-9918-3D39-B4FE-70B755E02D30`. No new device test,
re-export, speculative optimization benchmark or app build was needed.

Source-path audit:

- `ios/src/native_draw_census.cpp`: default native_cp path already bypasses
  the old game-thread Capture parser (`Capturing()` requires !native_cp).
  Existing draw wrappers still dispatch the guest function; plain/indexed calls
  update known_device, but the old full capture is not duplicated per draw.
  Do not present deleting this diagnostic parser as a large current saving.
- Native backend lives in sibling SDK `src/graphics/plugin_main.cpp`, generated
  by `tools/ios/patch_ios_native_backend.py`, not a separate native command
  processor file. It loads microcode objects without Vulkan host rendering.
  `CommandProcessor::ExecutePacketType3Draw` sends live registers/shaders to
  CpDraw and avoids backend draws when native-only is armed. PM4 still carries
  ordering, predicates, queries, memory events and swaps; bypassing arbitrary
  packets or the ring would break required behavior.
- `tools/ios/patch_ios_native_constants.py` / live plugin_main.cpp already use
  bounded bulk byte-swapping for side-effect-free shader constants, including
  ranges emitted by type-0 packets. Other registers retain WriteRegister's
  scratch writebacks, coherency handling, gamma state and game-specific
  adjustments. Re-proposing bulk constant writes repeats an implemented change.
- `Record` in `ios/src/native_renderer.mm` already reuses shader-read constant
  ranges and validates vertex/index content. Its two constant memcmp call sites
  0x1000b9764 and 0x1000b9860 total only 0.483 /0.616 CPU s inclusive here,
  ~0.085 /0.110% of app CPU samples. These sites were identified from linked
  _memcmp stub0x102629d44 (`llvm-objdump --macho --indirect-symbols`) and UUID-
  matched Record disassembly. Sampling/skid can miss very short calls, but this
  evidence does not justify SDK-to-renderer dirty-generation tracking first.
- `sub_82699100` remains the largest guest self leaf, 13.006 /13.726 CPU s,
  ~2.30 /2.44% app CPU. Located in ignored generated
  `ios/generated/default/nfsmw_recomp.93.cpp`, 2,272 lines. Two short-copy
  fast paths are already applied (`python3 tools/ios/patch_game_constant_copies.py
  --status`: exit0, applied two guarded loops). Inspection shows remaining
  descriptor/dirty-state traversal, conversions and helper guards; compiled
  0x101b6c300 region includes existing range/overlap validation. Removing these
  without proving equivalence or counting failures is not the next proposal.

A broader, mechanically bounded target was found in recompiled register
save/restore helpers. Measured self weights (CPU seconds; NOT device energy):

| Region | Four ON | Four OFF |
|---|---:|---:|
| GPR helper bodies, ordinary names plus __imp originals |21.510 (3.805%)|24.241 (4.318%)|
| Their separately sampled DYLD-STUB leaves |4.307 (0.762%)|3.823 (0.681%)|
| Combined non-overlapping self |25.817 (4.567%)|28.064 (4.999%)|
| Family29 save+restore bodies alone |7.174|5.895|

Summed self names matching savegprlr_ /restgprlr_, grouping ordinary, __imp and
DYLD-STUB symbols separately. Self leaves do not overlap. Helper bodies are a
real translated implementation cost; call/link stubs are not all removable by
an address calculation optimization. These measurements do not imply that all
4.6–5.0% is waste or available as a saving. Optimizing part of the 3.8–4.3% body
share could yield a modest CPU improvement; no battery percentage is predicted.
It cannot by itself promise a dramatic increase in runtime.

Structural check (read-only Python scan of generated *.cpp): **36/36 functions
match the expected full bodies exactly**, all18 save and18 restore entry points
for GPR14..31. No exceptions in this generated edition. Each saves/loads its
suffix of 64-bit GPRs at fixed negative offsets from r1, plus a32-bit saved link
register at -8. Restore zero-extends that saved word into r12 and LR. Save does
not modify LR/r12; neither operation changes r1, CTR, CR, XER, FPSCR or FPRs.
The last four bytes immediately below r1 are not written. Maximum touched span
for GPR14 is148 bytes, from r1-152 through r1-5, including the32-bit LR field.
Do not convert the LR field to64 bits, skip the guest-stack writes or assume
PPCContext's distinct register members form a C++ array.

Example originals: save29 in nfsmw_recomp.39.cpp:27832; restore29 in
nfsmw_recomp.57.cpp:28211. `nfsmw_init.cpp` mappings use ordinary weak entry
names (e.g. guest0x826BDB2C /0x826BDB7C), so a standard strong native hook can
cover direct callers and dispatcher mappings without editing generated code.
`xcrun nm -m` confirms weak ordinary symbols and strong __imp originals in
IPA24. Original entry points remain callable for fallback. UUID-matched ARM64:

- save29 ordinary0x100bffe0c, original0x100c38230;
- restore29 ordinary0x10110755c, original0x10113fb14.
Actual bodies repeatedly reload/normalize guest stack offsets and select the
physical-alias adjustment for each individual access. A common ordinary-stack
path can calculate the host stack base once, retain the same ordered volatile
access widths and byte swaps, and leave unusual addresses to originals.
The generated PCH describes weak musttail wrappers; current compiled ordinary
save/restore entries contain bodies as well as __imp entries. Do not count all
ordinary-name time as empty thunk overhead or assume the comment proves codegen.

Ranked next directions:
1. **Guarded native GPR save/restore prototype**: measured body pool3.8–4.3% of
   app CPU, only partly avoidable. Medium implementation effort and regression
   risk because helpers are used throughout the game, but simple exact semantics
   and36 uniform originals allow full differential tests. Recommended first
   experiment; benchmark before spending another device build/test.
2. Guest state/PM4/native snapshot bypass: potentially a larger combined ceiling,
   unquantified. High complexity/risk: live register state, predicates, shader
   microcode changes, query boundaries, memory writes and ring progress must
   remain equivalent. Existing native_cp=false does not remove guest packet
   generation. Not approved or ready for implementation; do not sell guest CPU
   self share as removable emulator overhead.
3. Constant dirty-generation reuse or another lookup shortcut: measured constant
   compare coverage is small here; tracking overhead and SDK ABI/state coupling
   could cost more. Keep as secondary, not the next speculative build. Vertex
   fingerprints and mutation checks remain necessary.

Concrete proposed first experiment (NOT IMPLEMENTED / awaiting approval):

- Add `ios/src/game_gpr_helpers.h`: specialized ordinary-stack save/restore
  operations using actual named PPCContext members and compile-time register
  suffixes. Guard before any mutation; preserve guest byte order, access order,
  full64-bit GPR values,32-bit LR save and zero-extension on restore. Normal
  virtual, non-wrapping/aligned ranges only; other cases decline intact.
- Add `ios/src/game_gpr_helpers.cpp`: strong overrides for the36 existing weak
  entries, with original __imp entry as OFF/guard-failure fallback. Define the
  independent proposed `nfsmw_native_gpr_helpers` control here, default false,
  so its storage access can inline in this translation unit. No string registry
  queries, clocks, logging or counters per helper call. Treat the mode as a
  launch/restart experiment, independent of master/four-cache flags.
- Change `ios/src/ios_main.mm`: startup mode declaration/log only; no launch
  graphics, priority or existing optimization defaults change.
- Change `ios/CMakeLists.txt`: add hook source for the currently validated USA
  edition; invoke read-only generated-helper pattern verification at configure
  time. Leave generated files and SDK source unchanged. Strong-symbol binding
  and existing other hooks must be checked in the linked app, including mapped
  indirect entry points and the preserved original fallback.
- Add `tools/ios/test_game_gpr_helpers.py`: read-only36-body matcher plus host
  differential fixture extracting the ACTUAL originals and using SDK context;
  no manually maintained fake originals. Exercise both switches, all18 suffixes,
  full randomized64-bit registers/LR upper bits, complete context/stack equality,
  untouched padding and surrounding bytes, repeated calls and boundary/fallback
  decisions. Invalid/unmapped ranges should test safe decline without
  dereferencing them; valid mapped alias fallbacks retain original translation.
  Alignment and uint32-wrap cases must not introduce UB in the sanitizer fixture.
- Update existing TECHNICAL/checkpoint/backlog with exact implementation/test
  results if approved; no parallel status file or generated game code commit.

Validation gates BEFORE an IPA: differential ASan/UBSan and optimized tests;
benchmark original / hook OFF / hook ON, including dispatch and guard costs,
short and long helpers, varied stack/context locality, mixed suffixes and
fallbacks. Confirm flag/accessor overhead does not erase gains or penalize OFF
materially. Inspect actual iOS ARM64 for repeated address dispatch/outlined
helpers and compare with originals. If the native guarded path does not improve
realistic host cases, stop/revise before issuing a device build. A host pass is
not evidence of device energy savings.

Only after those gates: iOS build, linked-symbol/dispatcher binding validation,
strict codesign/ZIP checks and byte-identical shaders/SDK libraries, one short
on-device event correctness run. No tiny isolated power A/B demanded; if correct,
retain experiment for accumulated testing. Any eventual saving must be measured
in comparable device CPU/instruction/power samples, not assumed from host speed.

Commands/results: source inspection with rg/sed; `xcrun nm -n` / `nm -m`;
`llvm-objdump --disassemble --no-show-raw-insn` address slices; indirect-symbol
export; helper inventory script all exit0. No new implementation fixture run or
benchmark; only the36-body structural inspection passed. Source probes at old
src/graphics/command_processor.h and guessed native backend paths failed;
`include/rex/graphics/command_processor.h` and live plugin_main.cpp identified.
Old Desktop debug paths no longer exist; prior battery notes found under
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/14 October 2026/`.
No previous GPR save/restore experiment found in those notes or shared history.
A missing guessed transform fixture path and optional unmatched generated-config
probe/glob were inspection misses, not app/test failures. No fallback behavior,
correctness or speed of a new GPR implementation has yet been tested.

Temporary artifacts: `/tmp/nfsmw_oct19_gpr_helper_inventory.json`,
`guest_82699100.txt`, `guest_disasm.txt`, `record_disasm.txt`,
`audit_symbols.txt`, `memory_imports.txt` (all with nfsmw_oct19_ prefix). Raw
source stays outside tracked docs. Essential inventory, sample weights,
semantics, proposal files, tests/limits and next approval boundary saved here.

Documentation checks: `git diff --check` exit0; reviewed diff/stat, only the three
shared Markdown files changed. No application tests needed for this analysis.
Author configuration unchanged. Local documentation commit only; original
untracked handoff and pre-existing SDK changes remain excluded and preserved.
Next action is user approval of the host GPR prototype, not another trace.


### October 19, 2026 — energy strategy reassessment before the GPR proposal

Stefan challenges the return from the recent experiments: most have not shown a
battery benefit, while system Low Power Mode is the only major demonstrated
power discovery. He raises this BEFORE approving the GPR prototype. Keep that
proposal on hold/unapproved; no new helper code, fixture or IPA should follow
from the preceding audit alone. The assistant acknowledges that prioritizing
many small CPU hotspots has not matched the goal of substantial battery savings.

Evidence calibration, unchanged from earlier records:
- Recent IPA21–24 batch demonstrates no system energy saving; direction slightly
  worse ON, workload/measurement confounds prevent causal regression attribution.
- Earlier changes improved individual timings, memory reservation, cache coverage
  or correctness. Those are not proof of reduced whole-device energy consumption.
- Earlier matched 30 FPS /0.85x LPM comparison estimated whole-run drain13.612
  versus24.540 pp/hour, guarded13.856 versus24.879, ~44% lower ON. Brightness34%
  and nominal thermals in both, approximately similar work; CPU execution time
  increases ON despite lower estimated drain. Leading explanation remains a more
  economical CPU/system operating point, NOT directly measured clocks/voltage or
  a demonstrated wholesale move to E cores. The prior Utility experiment does
  not reproduce the LPM result. Do not propose another generic QoS/core-affinity
  change as if it were an established equivalent to system LPM.
- This is evidence of substantially more economical execution at those 30 FPS
  settings, not proof of equal savings at1.5x/60 or an app-level way to reproduce
  OS power policy. It also does not establish that the port has reached its
  minimum energy cost. GPR bodies3.8–4.3% CPU, only partly recoverable, cannot
  credibly be presented as a dramatic battery solution.

Recommended strategy (a proposal, not a new implemented policy or authorized
source change): prioritize the LPM/system-policy clue and higher-ceiling work.
Use existing evidence to separate how efficiently work executes from how much
work is required. Audit frame deadlines, render-ahead, bursts/concurrency and
wakeups only for specific new evidence; retain previous sleeping waits and QoS
findings rather than repeating failed experiments. Investigate removing a
complete redundant guest graphics/state stage (packet construction plus decode)
where exact native-state submission can preserve ordering/queries/fences. Audit
GPU passes, copies and bandwidth only where dependency/resource evidence shows
avoidable work at identical output. These are candidate investigations, not
established causes or guaranteed optimizations. Broad bypass carries significant
state/lifetime risk; no claim that all guest work can be removed.

Any next measurement should isolate a specific energy cost and decide whether a
substantial opportunity exists, with settings/scene controls and explicit limits.
Do not request another generic pursuit A/B or implement another small shortcut
just to keep changes moving. Existing CPU-time profiles cannot assign watts to
individual functions; exported clock/performance-state tables were empty. A
focused diagnostic may be needed, but no particular new diagnostic/source change
or device test is approved in this discussion. No new source, settings, build,
device measurement or test result. This is a correction in prioritization and
interpretation; keep uncertainty visible and avoid promising large gains.

### October 19, 2026 — three-axis energy investigation and concrete next measurement

Stefan approves investigating the three proposed areas: work scheduling/pacing,
removal of redundant graphics stages, and GPU passes/copies/bandwidth. This is
investigation approval, not approval to implement any new source experiment.
GPR helper prototype remains held. Main repo starts at e2c5d3b on
battery-optimization, only intentionally untracked HANDOFF_CHATGPT.md. SDK's
extensive existing local/submodule changes preserved; no SDK edits. No source,
flags, entitlements, build or device settings changed during this investigation.

Deployment clarification from Stefan:
- Game Mode appears only after converting NFSMW to a shared app and launching
  it from LiveContainer 2. Typical users should not need those extra steps.
- LiveContainer is signed with a FREE account. The main battery solution must
  work with ordinary LiveContainer/free signing. Do not make it depend on a paid
  capability or a Game Mode/shared-app workaround. This does not establish which
  host/Game Mode state was used in every historical recording.

Evidence: same October19 paired IPA24 trace/log, common-event 527.534787 s
windows and UUIDs already documented above. Fresh analysis of existing CPU
samples and existing per-pass/copy logs; no new trace or repeat race collected.

1. Scheduling and work delivery

Source inspection confirms:
- display_rate.mm requests 60 Hz for cap30/60 and120 for cap40/120. It publishes
  CADisplayLink timestamps/target period to the SDK and invokes the lifecycle
  heartbeat. Actual callback cadence is not continuously logged.
- SDK graphics_system.cpp display locking applies only at cap30/40, with a
  target period within10% of guest60/120 Hz. At cap60/120 the guest worker uses
  its timer/grid path. A callback period change can disable the lock; the
  one-time lock message cannot prove the lock stayed active for an entire run.
  Requested refresh/callback period is not an independent panel power measure.
- Simply requesting30 Hz at cap30 would violate the current60 Hz lock condition.
  Any new pacing path must preserve the guest vblank cadence/interrupt semantics
  while handling presentation cadence separately. Do not repeat the old blind
  refresh-rate proposal.
- SDK IosCapBeforeSwap sleeps in vblank-counter waits before invoking the native
  swap hook. Consequently this cap wait occurs AFTER the frame's draws have been
  recorded, BEFORE that completed Frame is dispatched for Metal encoding. At
  30/40 it is not a deadline supplied before CPU draw preparation begins.
- NativeSwap dispatches serial Metal encoding; in_flight counts submitted frames
  until GPU completion, uses address waits above the two-frame threshold, with
  a50 ms bound. Recording of the next Frame is separate from this count. GPU
  completion frees a slot; actual drawable presentation happens separately.
  Exact guest ring/render-ahead depth and its energy effect are not measured.
- nextDrawable plus custom presentDrawable:atTime: targeting last shown time
  handles presentation. Ordinary rendering is asynchronous; waitUntilCompleted
  is on the dump path. No busy polling of renderer completion remains.
- Empty-ring CP work still uses64 yields then5 ms bounded event waits. Existing
  profiles show very little WorkerThreadMain self; that does not measure wake
  counts or prove idle timeouts have zero energy cost. Cap/vblank waits already
  block rather than running a whole extra game frame.

Missing evidence: current Power Profiler time-profile explicitly has
context-switch-sampling=0 and record-waiting-threads=0. It measures running
samples; it cannot reconstruct exact blocked/runnable intervals, wakeup counts,
queue depth or deadline slack. Prior CPU/GPU performance-state tables had no
samples. No proof yet that bursts/render-ahead cause the LPM energy difference.
Changing priorities again is not justified by this inspection.

Two public platform directions checked using installed iPhoneOS27.1 headers and
Apple primary documentation:
- CAMetalDisplayLink exists from iOS17; provides a drawable plus CPU/presentation
  timestamps and a requested latency of1 or2 frames. It is a concrete native
  frame-delivery alternative to the separate CADisplayLink/nextDrawable/custom
  timing sequence. It does not promise LPM-equivalent clocks or energy savings.
  A migration is a real pacing change, requiring guest timing, lifecycle,
  drawable ownership and30/40/60/120 behavior validation. Apple's delegate docs
  prohibit timed presentation methods with this path; current atTime presentation
  cannot simply remain enabled. Potential energy gain is a hypothesis.
  [CAMetalDisplayLink](https://developer.apple.com/documentation/quartzcore/cametaldisplaylink),
  [delegate contract](https://developer.apple.com/documentation/quartzcore/cametaldisplaylinkdelegate/metaldisplaylink(_:needsupdate:)),
  [frame latency](https://developer.apple.com/documentation/quartzcore/cametaldisplaylink/preferredframelatency).
- Apple's Sustained Execution entitlement constrains burst performance on
  applicable devices. It is a relevant system-policy lead, not an established
  substitute for LPM. Its effective availability is not established for this
  deployment: ios/CMakeLists.txt and nfsmw.entitlements explicitly document that
  LiveContainer's host-process entitlements apply. The game already declares
  GCSupportsGameMode/racing category; do not claim the game lacks that declaration.
  Adding a game-bundle entitlement alone would not enable a host capability.
  Given the free-signing/user-workflow constraint, this is not the main route.
  No signing/account/host modifications proposed or performed.
  [Sustained Execution](https://developer.apple.com/documentation/bundleresources/entitlements/com.apple.developer.sustained-execution),
  [Apple's capability setup discussion](https://developer.apple.com/videos/play/wwdc2025/209/).

2. Remaining graphics construction and decoding

New stack attribution resolves id/ref values from existing exported CPU XML,
uses the same eligible samples as the preceding audit (565,321 /561,438 ms),
and counts membership in named call paths once per sample. Inclusive rows
otherwise overlap and must not be added. Results ON/OFF:

| Call-path footprint | CPU s ON /OFF | % app CPU ON /OFF |
|---|---:|---:|
| Guest draw/state/resolve writers union |17.055 /16.981|3.017 /3.025|
| Above plus engine constant preparation sub_82699100 |32.617 /33.887|5.770 /6.036|
| CP ExecutePacket outside CpDraw and NativeSwap paths |19.015 /11.527|3.364 /2.053|
| Explicit union of these identified graphics stages |51.632 /45.414|9.133 /8.089|
| sub_82593A58 inclusive (nested; do not add) |15.851 /15.300|2.804 /2.725|
| sub_825A3EC8 inclusive (nested; do not add) |13.509 /13.740|2.390 /2.447|
| sub_82699100 inclusive |15.562 /16.906|2.753 /3.011|
| Record inclusive (native work still required) |53.036 /46.302|9.382 /8.247|

Guest writer union includes825A3EC8,82593A58,82593818,825930E0,82593408,
8259A308,82592340,82597070. This is a measured envelope with incomplete-unwind/
sampling limits, not a strict whole-pipeline upper bound or recoverable saving.
Record and CpDraw already overlap with CP's total12–15% inclusive footprint;
calling that whole CP share removable decoding would overstate the opportunity.
The separate native Metal indexed draw call site remains4.46 /4.17% inclusive
CPU from the preceding audit; native batching might address part of driver
submission, but unchanged per-draw state/query/ordering must be proven first.
No batchability distribution or successful indirect-command experiment exists.

Generated functions inspected read-only: sub_82593A58 (368 lines,
nfsmw_recomp.55.cpp) flushes state, checks segment space, emits commands and
handles indexed/tiling state; sub_825A3EC8 (306 lines, .85.cpp) walks dirty masks
and delegates register/constant writes; sub_82592340 (1,949 lines, .87.cpp)
handles complex resolve state/quad/clear sequences. Current old Capture parser
still decodes PM4 when native_cp=false; toggling it is not a native submission
bypass. Native backend already omits Vulkan device/EDRAM rendering and bulk-
copies side-effect-free constants. Those are not new opportunities.

A direct guest-to-native state/draw submission design could eliminate selected
packet generation/decoding, but must preserve command ordering, shader loads,
register side effects, predicate/tiling decisions, queries, fences, writebacks,
segment/ring progress, async lifetime and guest ABI effects. Immediate calls on
the game thread are not automatically equivalent to ordered CP consumption;
state and memory can change before later packets execute. Identified envelope
is larger than a tiny cache but insufficient to promise a large battery change.
High complexity/risk; no blind replacement of all guest graphics or game logic.

3. GPU pass and resource audit

Parsed105 sampled per-pass profiles per arm inside the common windows. Each
profile describes one instrumented frame; means are not continuously measured
per-pass averages. Incremental timestamp contributions overlap execution and
are NOT watts, bandwidth or exact recoverable costs. Mean frame span4.3518 /
4.2555 ms; approximately46.90 passes/blits per sampled frame in both.

| Incremental category, mean ms/profile | ON | OFF |
|---|---:|---:|
| Main scene (~2.9 passes) |1.9472|1.8829|
| Reflection rendering (6 passes) |0.8013|0.7900|
| Shadow rendering (2 passes) |0.4391|0.4289|
| Ordinary color resolve copies (18 blits) |0.2976|0.2907|
| Depth copies (3) |0.2843|0.2883|
| Cube assembly (6 blits) |0.0604|0.0614|
| Main presentation |0.0614|0.0602|
| Other passes/blits combined |0.4350|0.4277|

Main scene + reflection + shadow is ~73% of sampled span. Those are real image
work; removing faces, lowering shadows or shrinking resolution affects fidelity
and stays optional Battery mode. These timings do not establish the GPU's
current utilization/limiter or DRAM traffic. Full-frame GPU time alone cannot
rule out bandwidth-related energy, and shortening a pass is not an energy result.

New reanalysis of existing diagnostics, NOT a repeated device experiment:
-105 depth-audit frames/arm:315 snapshots each, ZERO unchanged single-sample
 candidates. Two shadow snapshots represent different depth generations. Do
 not repeat reuse/removal of unchanged depth copies without new evidence.
-101 complete300-frame summaries/arm: ZERO artificial pass splits; seven final
 passes/summary already discard unread attachments. Presentation drawable
 sizing already uses the picture's requested size when applicable. These old
 ideas are implemented/off as appropriate; they are not fresh savings.
-Pooled frame buffers/resolves:442 made/847,958 reused ON;431 /847,925 OFF,
 ~99.95% reuse of THIS pool's checkouts. Does not count all textures/views or
 prove no allocation/driver overhead remains. Do not call persistent resource
 creation per frame the dominant cost based on source allocation expressions.
-Logged logical CPU copies (vertices/indices/constants/shared):2.168 /2.076
 MiB/frame (~130.06 /124.53 MiB/s at60), spans2.592 /2.486 MiB/frame including
 alignment. Logical sizes are not measured DRAM bytes or a bandwidth diagnosis.

Concrete GPU dataflow opportunities worth proving:
A. Whole-surface COLOR resolve after the source's last write: potentially keep
   the original color image as the resolved snapshot instead of copying it.
   Requires identical pixel format/dimensions/coordinate interpretation, no
   exponent conversion, correct swap/swizzle, and per-frame/versioned target
   ownership so the next clear/write cannot corrupt a retained snapshot. Partial
   resolves, cropping/linear views, MSAA, CPU readbacks and later writes need
   original behavior. Existing retained targets/kept resolves cannot just alias.
B. Reflection faces currently may flow source color -> individual2D resolve ->
   assembled cube face (separate blits). Remove an intermediate only if consumers,
   dimensions/cropping, exponent conversion, CPU writeback, final-output tracking
   and cross-frame persistence remain equivalent. A face may also be sampled as
   2D; a cube reused next frame cannot silently replace an immutable old snapshot.
   A versioned cube/2D-view design might preserve both, but compatibility and
   liveness coverage are unmeasured. Current code already directly handles array
   resolves; investigate the additional ordinary2D-to-cube assembly path only.

Color copies plus cube assembly contribute ~0.358 /0.352 ms/profile (~8% GPU
span), only partly eligible; depth-copy savings are NOT included in that number.
This bounds expectations for these specific copy proposals. Uncompressed texel
bytes could be estimated from eligible rectangles but are not physical traffic.
Need actual format/rectangle/consumer/version counts before implementation.

Priorities and recommended first change (PROPOSED, NOT APPROVED):
1. Frame-delivery/deadline diagnostic, leading toward an optional native Metal
   display-link pacing experiment if timing evidence supports it. Highest
   uncertainty but directly pursues the large system-policy signal. Medium
   diagnostic effort/low behavior risk; an actual pacing rewrite is higher risk
   (stutter, latency and guest cadence). No guaranteed energy benefit.
2. Versioned color-resolve / reflection intermediate removal after eligibility
   audit. Concrete stage elimination, limited measured timing envelope; medium-
   high complexity and lifetime/image risk. Preserve original path for all
   incompatible cases and default fidelity.
3. Guest graphics/native submission bypass (possibly native Metal batching
   separately). Identified8–9% CPU stage envelope, only partly avoidable, high
   complexity/regression risk. Needs detailed state-equivalence design, not a
   rushed whole-renderer change. GPR micro-optimization remains held.

Recommended single diagnostic build scope, before an optimization build:
- ios/src/native_renderer.mm: opt-in per-frame signposts/IDs at recording/frame
  ready, render-queue start, command-buffer commit, GPU completion and actual
  presentation; queue/in-flight state. Rare-frame resolve eligibility and texel-
  byte summaries using existing Draw/Resolve records. No per-draw clocks, no
  image dumps, skipped draws, changed copies or altered resource lifetimes.
- ios/src/native_draw_census.cpp: opt-in guest Swap begin/end markers to connect
  game production with CP/native submission; establish IDs/order carefully,
  including menus, dropped/non-recorded frames, movies and restarts.
- ios/src/display_rate.mm: opt-in callback timestamp/target-period observations
  and lifecycle/rate transitions; no refresh/cap policy change. This addresses
  missing evidence about dynamic LPM/display-lock behavior.
- ios/src/ios_main.mm: independent diagnostic control default false, startup
  mode/settings logging. No new entitlement, QoS or default optimization change.
- Shared docs updated with implementation/checks if approved. No SDK/generated
  source edits required for this proposed diagnostic scope. No flag exists yet.

Validation plan if approved: first confirm ordinary rendering/draw counts, copy
counts, caps and existing controls unchanged with diagnostics off/on; bound
marker/audit overhead. Then a short targeted System Trace + Points of Interest
recording with thread-state/runnable/wait information, same settings/event work,
LPM ON/OFF at explicitly fixed30 FPS. Begin with the already established LPM
configuration to investigate its timing difference; higher-resolution/60 FPS
validation follows an actual candidate, not another generic test sequence now.
Use existing Power Profiler for eventual energy validation; diagnostic observer
effect and nondeterministic gameplay remain controlled/qualified. No GPU hardware
counters or parked GPU capture repair required. This new trace would answer the
missing scheduling question; it is not needed to reconfirm the old drain result.

Decisions the diagnostic should resolve: (1) deadline slack/render-ahead and
actual callback/guest timing states, (2) whether LPM changes work delivery as well
as execution cost, (3) how many compatible copy stages/bytes can be removed
without changing snapshots. A pacing change must preserve FPS, gameplay speed,
input/lifecycle and image, and show reduced comparable device power; lower CPU
percent or lower GPU milliseconds alone does not pass.

Commands/results: rg/sed source/prior-findings review; git status/log (HEAD
e2c5d3b, untracked handoff only); xcrun --sdk iphoneos --show-sdk-path identifies
installed iPhoneOS27.1 SDK with nonfatal Xcode cache/FSEvents warnings; read its
CAMetalDisplayLink.h. Official Apple docs researched; only primary sources used.
Temporary stage_audit.py initially encountered an empty backtrace row; fixed to
skip it and matched prior sample totals exactly. Corrected analysis and explicit
union scan exit0; GPU log parser exit0. Full source snippets/guessed optional
paths sometimes absent or output-truncated; actual paths inspected via rg and
bounded reads. No application/compiler/test failure or new device result.

Temporary outputs all prefix /tmp/nfsmw_oct19_: stage_audit.py/.txt/.json,
stage_union.py/.txt (writes same stage_audit.json with union fields),
gpu_audit.py/.txt/.json and ignored guest-function extracts sub_82593A58.txt,
sub_825A3EC8.txt, sub_82592340.txt. Inputs, windows, counts, formulas, semantics,
platform sources, user deployment constraint, proposed files and next approval
boundary are preserved here; temporary files are not the sole handoff record.

Documentation validation: git diff --check exit0; reviewed diff/stat and current
checkpoint/backlog. Only these three Markdown files changed. No production test
or build required for read-only analysis. Existing Stefan Stoica author retained.
Local documentation commit only; untracked handoff and SDK changes excluded.
Next action: approval of the specific diagnostic build above. No implementation
or repeated device test should be inferred from investigation approval alone.


### October 20, 2026 — Retaining useful work without assuming an energy benefit

User asks whether CPU optimizations should stay enabled despite inconclusive
battery gains, and whether those results imply a different source of drain.
Accepted/default-on changes should remain enabled. Retain newer experiments
and their independent OFF controls; stable changes need not be discarded just
because one small or variable comparison cannot establish a battery benefit.
Recent experimental defaults remain false; no setting, source or build changed.

Qualification: not all changes have demonstrated lower total application CPU
work. In the October 19 four-change pair, ON/OFF CPU execution was 110.114 /
109.074% of one core, retired instructions were about 1.79% higher ON and sampled
last-frame draws about 3% higher ON. This is neither a proven CPU saving nor a
causal regression: gameplay variation remains. Removing allocations, copies or
redundant visits is useful evidence for the specific operation; cache checks and
miss handling can offset savings elsewhere. Headroom/memory benefits should be
reported separately from established app-level CPU or energy improvements.

An undetectable battery change does not exclude CPU power as a principal cost.
The earlier matched LPM comparison had about 91.4% versus 59.2% CPU time of one
core, yet approximately 44% lower estimated whole-device drain with LPM. CPU
utilization is time running, not energy per unit work. A different CPU/system
operating point remains a leading hypothesis; clocks/voltage were not measured.
Small work reductions can be masked by gameplay variance and other device costs.

Recommendation: preserve accepted defaults, keep stable experiments available
for development/batch testing and use a fixed control configuration for the next
investigation. Do not toggle the master group to isolate the newer four because
it also changes guest/CP QoS above 40 FPS. No new device test requested for this
conceptual clarification. The proposed frame-flow/copy diagnostic still awaits
explicit source approval; no GPR prototype, pacing rewrite or new build approved.

Documentation-only update; git diff --check and reviewed diff required before
local commit. No production tests needed. Existing author configuration retained;
untracked handoff and SDK edits excluded.


### October 20, 2026 — What Low Power Mode changes and what the game can copy

Question from Stefan: why does iPad Low Power Mode cut estimated drain from
24.540 to 13.612 pp/hour, and what can the game do to approach that without
LPM, keeping the default look and every MetalFX mode. Analysis only, using the
October 18 matched recording above; no source, flag, build or device test.

What LPM changed in that recording (measured, both arms 0.85x / FXAA / MetalFX
OFF / explicit cap 30 / 60 Hz request / 34% brightness / Nominal):
- Frame rate, refresh request, render scale, draws (~2,700/frame) and GPU impact
  (0.919 / 0.945) were effectively equal; display impact was slightly higher ON.
  The ProMotion 60 Hz limit therefore played no part in this result.
- CPU power impact fell 8.359 -> 3.242 (~61%) while CPU time ROSE 59.2% ->
  91.4% of one core for similar instruction volume (6.05 vs 6.40 G/s) and CPU
  recording time rose 2.20 -> 3.41 ms/frame. Core mix barely moved (76/24 vs
  70/30 P/E). Inference: LPM runs the same work at a lower CPU frequency/voltage
  ceiling instead of racing at high clocks and idling. Clocks were not exported.
- Background work reduction (mail fetch, iCloud, etc.) is not visible in this
  trace and is unlikely to explain a ~5 W-scale CPU impact difference (inference).

What an app cannot do: set CPU clocks, voltage or the system DVFS ceiling.
There is no public API; Game Mode / Sustained Execution are unavailable under
free LiveContainer signing (see the October 19 deployment constraint).

What the game can influence: the performance controller chooses clocks from
thread QoS, how bursty the work is, and how much slack exists before a deadline.
At 30 FPS the OFF arm finished CPU recording in 2.2 ms of a 33 ms budget, so the
controller had no reason to stay low. Candidate levers, ranked by expected gain
versus visual cost (all keep the image, scale and MetalFX modes unchanged; all
are hypotheses until measured):

1. Guest game-thread QoS experiment (highest expected gain, lowest effort,
   zero visual cost if FPS holds). Previous Utility work moved only the serial
   Metal encoding queue, which already ran ~95-100% on E cores; it could not
   test LPM's lever. The guest main/CP threads, which carry most P-core time,
   have never been demoted (baseline promotion is retired; ios_battery_baseline_qos
   only restores promotion). A switch requesting QOS_CLASS_UTILITY (or DEFAULT)
   for those threads, default false, tested at 1.5x/60 with MetalFX on, is the
   closest app-side imitation of a lower operating point. Risk: dropped frames,
   audio or input latency; gameplay speed must not change. This is a QoS change
   and needs Stefan's explicit approval despite the October 19 caution (that
   caution concerned the render queue and generic affinity, not this thread).
2. Deadline-aware pacing via CAMetalDisplayLink (medium/high effort, zero
   visual cost). Gives the system per-frame deadlines rather than bursts after
   a vblank wait; may let clocks stay lower with unchanged FPS. Already listed
   as a candidate; requires guest vblank and presentation migration.
3. Spread work instead of bursting: start frame preparation at a predictable
   time after vblank and avoid parallel wakeups (the CP 64-yield spin before 5 ms
   waits, concurrent warm/pipeline queues). Small expected gain; low risk.
4. Keep reducing CPU work (existing lines of investigation). Real but small per
   change, and masked by variance; do not expect LPM-sized gains from it alone.
5. Follow LPM automatically when the user enables it (battery.mm already
   switches 60 -> 30 there). Changes nothing when LPM is off; listed only for
   completeness.

Not candidates: capping refresh below the frame cap (the guest 60 Hz lock needs
it; earlier finding), lighter MetalFX (excluded by Stefan; GPU impact was not the
LPM difference anyway), Game Mode / entitlements (deployment constraint).

Unknown: whether LPM saves the same share at the default 1.5x / 60 / MetalFX
setting, where GPU and display take a larger part of drain. The first device
test of lever 1 should therefore be at default settings, LPM OFF, with a matched
OFF arm, same brightness, Power Profiler plus thermal state.

Next action: Stefan chooses whether to approve lever 1 (a single default-false
switch). Nothing implemented. Documentation-only change.


### October 20, 2026 — IPA25 guest-thread Utility QoS switch (approved, built)

Stefan approved lever 1 of the entry above ("sure lets do it"), on
battery-optimization. New SDK patch `tools/ios/patch_ios_utility_qos.py`,
listed last in `prepare_sdk.py` IOS_PATCHES and applied to the sibling SDK
(3 of 3 blocks; no other SDK edits). Cvar `ios_utility_qos`, default false:
at the start of their own bodies, XThread::Execute (main_thread_ only) and
CommandProcessor::WorkerThreadMain call
`pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0)` and log
`[ios] game main thread: QoS utility set` / `[ios] GPU Commands thread: QoS
utility set` (FAILED on error). It is an `else` of the baseline-promotion
control, so `ios_battery_baseline_qos=true` still wins. No visual, scale, cap
or MetalFX change; the Metal encoding queue keeps its own setting.

Build: `cmake --build --preset ios --target ipa -j 6` exit 0; only xthread.cpp
and command_processor.cpp recompiled, two dylibs relinked, app relinked/signed.
IPA25 `ios/build/NFSMW-battery-utility-qos-25.ipa`, SHA256
`3ac6f0456a05edf10f67782268cc54674bf84c98928dfaaba249c23a751ab9c8`; NFSMW UUID
`D50A53D8-C274-3D12-924E-B73273D35F8D`, librexruntime
`2D163E20-61E8-3D72-AF89-1AD955AE0E45`, librexgpu-xenos
`D01DFAC8-C338-3717-A457-114B4F70741B`. `unzip -tq` no errors; `codesign -v`
OK; both dylibs contain the new log strings (strings count 2 each).
Not run on a device yet.

Proposed device test: (1) a short correctness check with Extra Args
`--ios_utility_qos=true` after a cold LiveContainer restart: both log lines
present, FPS, audio and input normal at the usual 1.5x / 60 / MetalFX setting.
(2) If it passes, two matched ~10-minute Power Profiler recordings, same IPA,
settings, other Extra Args, manual brightness, LPM OFF, only `ios_utility_qos`
toggled (cold restart between arms). Pass criterion: lower whole-device drain
with FPS and game speed unchanged. Failure modes to watch: frame drops,
audio crackle, input lag, slower game time.

### October 20, 2026 — IPA25 first device check: frozen image after skipping the intro movie

Stefan: iPad, IPA25 with `--ios_utility_qos=true`. After skipping the movie
with A, the image stayed on the last movie frame while the "press start" audio
played. Log: `~/Developer/Debug/Most Wanted (2005) Debug/20 October 2026/nfsmw_run_1_ipad.log`
(two launches, 13:30:19 and 13:30:56; both log `QoS utility set` for the main and
GPU Commands threads; 1.5x, cap 60, MetalFX off, five-option group on).

Measured: launch 2 skips at ~13:31:01 (815.7 ms hitch, frame 95), last frame
log 13:31:01.6, disc loads (CARS, StreamL2RA_Perm.bun) at 13:31:01-02, watchdog
"5 s without any guest register moving" at 13:31:07.203, app to background at
13:31:07.266, 63 ms later. CPU 16% of a core over the preceding 10 s, so no
thread was spinning. Launch 1 had the same watchdog at 13:30:35.752 after its own
skip and logged "moving again after 5 s" at 13:30:36.766, then rendered the menu.
The October 19 log without the flag (`19 October 2026/nfsmw_run_1_ipad.log`) shows
the same post-start watchdog stalls of 5-9 s that recover.

Inference: the log does not show a hang; it shows the usual post-skip loading
pause, with the app left ~6 s in. Not established whether Utility makes that pause
longer. Note for the experiment: Darwin threads inherit the creating thread's
QoS, so guest threads created by the main thread after it switches likely run at
Utility too, including loading threads (Utility I/O is throttled). Next: Stefan
retries and waits at least 15 s; if it never recovers, compare with the flag off.

Correction (same day): Stefan waited over 30 s on a later attempt; menu music
played but the image stayed on the last movie frame. So this is a real visual
freeze, not only the loading pause; the earlier inference is withdrawn. That
attempt is not in the supplied log (ends 13:31:07). Requested: its log, and one
IPA25 run without `--ios_utility_qos=true` to separate the switch from the build.
Do not use the switch for power tests until resolved.

### October 20, 2026 — Cause of the IPA25 freeze: shader libraries missing; IPA26

Stefan: still freezes with `--ios_utility_qos=false`; log
`20 October 2026/nfsmw_run_2_ipad.log` (13:35:12 launch, the >30 s attempt; it
still logs `QoS utility set`, so the flag-OFF run itself is not in a log).
Measured: every game draw logs `no shader library ... (missing)`; after the skip
the command processor keeps running the menu (~1168 constant ranges/frame) but
no native frame reaches the screen, while audio continues. The October 19 IPA24
log reports `0 without a shader library` on every summary.

Cause: IPA25 contains 0 `.metallib` files (40 entries) versus IPA24's
NativeShaders directory (104 libraries plus 4 text files). The build directory's
CMakeCache had `NFSMW_NATIVE_SHADERS_DIR` empty, so packaging skipped the copy.
The movie still played because its shaders are built into the executable. The
freeze is a packaging error, not the QoS switch. IPA25 is withdrawn.

Fix (build configuration only): `cmake -S ios -B ~/Library/Caches/nfsmw-ios/build
-DNFSMW_NATIVE_SHADERS_DIR=$HOME/Library/Caches/nfsmw-ios/shaders/lib`, then
the usual `cmake --build --preset ios --target ipa -j 6` (both exit 0). IPA24's
NativeShaders and that directory were checked identical (`diff -rq`, 108 files)
before and after the build. IPA26 `ios/build/NFSMW-battery-utility-qos-26.ipa`,
SHA256 `1f5b7c3d1b7e54619346bd8386b5d0484b0a55a9d588f7ec738926ee340761c0`, NFSMW
UUID `8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1`; `unzip -tq` OK, `codesign --verify
--deep --strict` OK. Same sources as IPA25. Not yet run on a device.

### October 20, 2026 — IPA26 short correctness check passes

Stefan: IPA26 worked, full usual two-lap Quick Race. Log
`20 October 2026/nfsmw_run_3_ipad.log`: launch 1 at 13:38:30 without the flag,
launch 2 at 13:42:02 logging `QoS utility set` for GPU Commands and the game
main thread. Launch 2 frame summaries: 30 at 60.0 fps on screen; below 59.5 only
frame 301 (38.4, menu/loading, 33 draws), 901 (58.6), 1501 (58.2, load into the
race) and the final 10501 (54.9, post-race). Battery-percentage field stayed 85%
(not an energy measure). Correctness/frame-rate only; no power data. Next: the
matched ~10-minute Power Profiler pair, flag ON vs OFF, as specified above.

### October 20, 2026 — IPA26 Utility QoS power recording (one arm)

Stefan recorded one ~10-minute arm (no time for the OFF arm), the same Challenge
Series pursuit and as similar a route as possible as the October 19 IPA24 pair,
and asked to compare with those. Inputs: `20 October 2026/nfsmw_run_4_ipad.log`,
`20 October 2026/power_profiler_1_ipad.trace` (run 1 13:49:03.784+02:00,
600.224 s; Metal performance overview tables included). Log: IPA26 launch
13:48:33, `QoS utility set` for GPU Commands and main thread, scale 1.500, MetalFX
off, FXAA off, MSAA 0, cap 60, five-option group on; the four IPA24 lookup flags
at their default false (= the Oct 19 OFF arm). Thermal Nominal for the whole run.

Method: `xctrace export` of SystemPowerLevel, ProcessSubsystemPowerImpact,
DisplayBrightnessLevel, thermal for today and both Oct 19 runs, the same
duration-weighted whole-run parser for all three (scratchpad an.py/gpu.py,
temporary). It reproduces the Oct 19 whole-run values recorded above
(34.141 / 33.334), so the method matches. LiveContainer process rows.

| Whole run (599 s) | Oct 19 IPA24 four ON | Oct 19 four OFF | Oct 20 IPA26 Utility QoS |
|---|---:|---:|---:|
| Estimated system drain, pp/hour | 34.141 | 33.334 | 31.263 |
| Process CPU impact | 12.639 | 12.292 | 8.740 |
| Process GPU impact | 2.244 | 2.291 | 2.401 |
| Display impact | 5.895 | 5.922 | 5.506 |
| CPU instructions, billion/s | 11.52 | 11.35 | 10.91 |
| Brightness | 35% | 35% | 29% |
| Log CPU % of one core, median of 10 s windows | 106 (whole Oct 19 log) | | 142 |

Log FPS: 133 summaries, 128 at >= 59.5; below were 0.0 (launch), 28.7 (load),
58.6, 57.7, 59.4.

Measured: drain 6.2% lower than the comparable OFF arm (-2.07 pp/h); CPU impact
29% lower with only ~4% fewer instructions while CPU time rose: the same
signature as system Low Power Mode (cheaper CPU operating point, inferred, clocks
not exported). GPU impact unchanged within ~5%.
Limits: different day, one arm, non-identical pursuit, and brightness 29% vs
35% lowers display cost (display impact -7%), so part of the drain difference
is brightness. The CPU-impact drop is not explained by brightness. Not yet a
proven whole-device saving; a same-day OFF arm at the same brightness would
settle it. FPS held, no visual change.

### October 20, 2026 — Core placement in the IPA26 trace; IPA27 adds guest-thread Utility

Stefan asked to stack more changes before further power tests. Time Profiler of
`20 October 2026/power_profiler_1_ipad.trace` (time-profile export 218 MB,
861.4 s of samples; scratchpad tp.py/tp2.py, temporary). Measured core split:
665.6 s E cores / 195.9 s P cores (23% P). Per thread+core share of all samples:
LiveContainer dispatch workers E 28.9% / P 5.5%, GPU Commands E 25.3% (P none),
Main XThread E 23.1% (P none), XThread3243 P 9.0%, XThread14E07 P 5.2%, UI Main
Thread P 1.6%, XMA Decoder P 0.6%. So Utility moved both target threads fully to
E cores at 60 FPS. XThread3243 (guest game code under PosixCondition waits) and
XThread14E07 (guest audio code plus wma/fft decode) did not inherit Utility and
stay on P cores. P-core LiveContainer time is mostly an unsymbolized dispatch
workloop (0x1a46a4f19; likely Metal/IOGPU completion, not app-controlled).
Spin/wait candidates are negligible in this profile: MaybeYield 0.02%,
RtlEnterCriticalSection 0.00%, Wait( 0.30% inclusive, so the CP yield spin and
critical-section spin changes considered earlier are not worth stacking.
Top self costs remain Record 10.3%, RenderFrame 6.7%, Fingerprint 4.2%,
sub_82699100 4.1% (existing CPU-work lines).

Change (same patch script `tools/ios/patch_ios_utility_qos.py`, now 5 blocks,
applied, `--status` 5 of 5, re-run idempotent): cvar `ios_utility_qos_guest`,
default false. In XThread::Execute every guest thread other than main_thread_
requests QOS_CLASS_UTILITY and logs `[ios] guest thread <id>: QoS utility set`.
XHostThread overrides Execute, so host threads (XMA Decoder, GPU VSync, audio
worker) are unchanged. Risk to watch: audio gaps (coreaudio 5 s lines report
gaps) and loading time, since audio decode and streaming threads move to E cores.

Build exit 0 (xthread.cpp, command_processor.cpp recompiled). IPA27
`ios/build/NFSMW-battery-utility-qos-guest-27.ipa`, SHA256
`f534f92f1456229906719dafd12b4242cc1940ac548a078a2b4b412efdc6ccdf`; NFSMW UUID
`8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1` (unchanged from IPA26), librexruntime
`1FAE8DDC-9FAE-3CF3-962C-DB86037B1E89`. 104 metallibs, NativeShaders identical
to the shader cache, `unzip -tq` OK, `codesign --verify --deep --strict` OK.
Not run on a device. Test with Extra Args `--ios_utility_qos=true
--ios_utility_qos_guest=true`; OFF arm both false.

### October 21, 2026 — IPA27 matched pair: Utility QoS (main+CP+guest) ON vs OFF

Inputs: `~/Developer/Debug/Most Wanted (2005) Debug/21 October 2026/nfsmw_run_1_ipad.log` (renamed by Stefan from nfsmw.log)
and `.../21 October 2026/power_profiler_1_ipad.trace` (two runs: run 1
22:05:12.598+02:00, 604.118 s; run 2 22:19:06.437, 600.844 s). Log launch 1
22:01:59 logs `QoS utility set` for GPU Commands, main thread and 22 guest
threads (ON arm = run 1); launch 2 22:18:28 logs none (OFF arm = run 2, both
flags false). Both: IPA27 build, scale 1.500, MetalFX off, FXAA off, MSAA 0, cap 60,
five-option group on, IPA24 lookup flags default false. Brightness 32.0% in both
(SystemPowerLevel), thermal Nominal throughout both runs. Same pursuit per Stefan.
Same whole-run parser as October 20 (validated against Oct 19 values).

| Whole run | ON (run 1) | OFF (run 2) | Change |
|---|---:|---:|---:|
| Estimated system drain, pp/hour | 25.703 | 33.656 | -23.6% |
| Process CPU impact | 5.299 | 12.457 | -57.5% |
| Process GPU impact (row kind 2) | 2.799 | 2.309 | +21% |
| Display impact | 5.587 | 5.251 | +6% |
| CPU instructions, billion/s | 10.69 | 11.40 | -6% |
| Log CPU % of one core, median 10 s window | 192 | 105 | |
| Log FPS summaries >= 59.5 | 157 / 171 | 142 / 145 | |
| Audio gaps (coreaudio 5 s lines) | 0 | 0 | |

ON low summaries: 37.6 (load) and twelve between 57.3 and 59.4; OFF: 28.2
(load) and 59.3. Log battery field: launch 1 100% -> 95%, launch 2 95% -> 85%.

Measured: at the normal 1.5x / 60 setting and equal brightness, Utility QoS on
all game threads cut estimated whole-device drain by about a quarter and CPU
power impact by 57%, close to system Low Power Mode's 61% CPU reduction in the
Oct 18 30 FPS pair. CPU time nearly doubles for 6% fewer instructions: the
lower-operating-point signature. GPU impact rose 21% (cause not established;
possibly the GPU clocking up as CPU work arrives later, inferred).
Cost: slightly more frequent small frame-rate dips (summaries of 57-59.4 fps).
Limits: one pair, ON first (fuller battery), pursuit not identical. The
-23.6% is far larger than the Oct 19/20 pursuit-to-pursuit variation (~2.5%).
Next: Stefan decides whether to make both flags default; check the dips in play.

### October 21, 2026 — Utility QoS made the default (IPA28)

Stefan: the small dips appeared only while Instruments was recording; ~3 minutes
of the same pursuit before the first trace, unrecorded, had no stutter; "great
news so far! whats next?". Decision recorded: both flags default true.
Inferred: the extra ON-arm dips in the Oct 21 pair are at least partly profiler
overhead; not separately measured.

Change: `tools/ios/patch_ios_utility_qos.py` defines `ios_utility_qos` and
`ios_utility_qos_guest` with default true; the applied SDK `xthread.cpp` was
edited to the same text so `--status` stays 5 of 5 (re-run: all applied, no
duplicate). Opt out: `--ios_utility_qos=false --ios_utility_qos_guest=false`.
CHANGELOG "Unreleased" entry added. Build exit 0. IPA28
`ios/build/NFSMW-battery-utility-default-28.ipa`, SHA256
`ce31d0a89fd44ac19d34ed763f6ec8abece1871506dbe3e078004eafbe6866d8`; NFSMW UUID
`8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1`, librexruntime
`C4710F54-F0DE-3948-83FC-1B75F230B23D`; 104 metallibs identical to the shader
cache; `unzip -tq` OK; `codesign --verify --deep --strict` OK.
Untested: iPhone (A19 Pro has fewer E cores than the M4; 60 FPS on E cores is
not established there), Battery mode / 30 FPS, MetalFX modes with these flags.

### October 21, 2026 — iPhone stutters with Utility QoS; default limited by E-core count (IPA29)

Stefan, iPhone (A19 Pro, the 17 Pro), IPA28, three laps: 1.5x, then 1x with
MetalFX "to the screen", then Battery mode; all with very bad stuttering. Log
`21 October 2026/nfsmw_run_1_iphone.log`: three launches (22:37:24, 22:39:37,
22:41:38), each logs `QoS utility set` for main and GPU Commands. Energy lines:
1.5x/MetalFX off/cap 60; 1.0x/MetalFX screen/cap 60; 0.85x/FXAA normal, cap 60
(briefly 30). FPS summaries bucketed by 5: 0 x3, 25 x2, 30 x4, 35 x3, 40 x3,
45 x8, 50 x23, 55 x8; none at 60. 639 hitch lines. CPU line sample: GPU Commands
34%, Main XThread 23%, XThreadD113 22%, XThread10033 16%. Earlier iPhone tests
without promotion held 60 FPS (patch table), so the cause is inferred to be
Utility QoS: the iPhone's 4 efficiency cores cannot carry these threads at 60 FPS
(the M4 has 6 and held 60).

Change (`ios/src/ios_main.mm`): `ApplyUtilityQosDefault` reads
`hw.perflevel1.physicalcpu` (efficiency cores) and, unless Extra Args set the
flag, passes `--ios_utility_qos` and `--ios_utility_qos_guest` = true only with
6 or more E cores, false otherwise. Logs `[utility-qos] <n> efficiency cores;
main/GPU threads on|off, other guest threads on|off (default|Extra Args)`.
The SDK cvar defaults stay true. Build exit 0. IPA29
`ios/build/NFSMW-battery-utility-ecores-29.ipa`, SHA256
`ea7e301e241b4ba9bab77588888cf08f06cab8431a666498cca4209255c6fe4e`, NFSMW UUID
`DDF5F784-C577-3AA9-8115-FF5769EB088B`; 104 metallibs identical; `unzip -tq` OK;
`codesign --verify --deep --strict` OK. Not run on a device: needs the iPhone
log line to show 4 / off and 60 FPS restored, and the iPad to show 6 / on.
Possible later refinement (not implemented): on 4-E-core devices put only the
non-critical guest threads at Utility, or adapt QoS to measured frame rate.

### October 21, 2026 — IPA29 device check on both devices passes

`21 October 2026/nfsmw_run_2_iphone.log` (22:48:12–22:49:59): `[utility-qos] 4
efficiency cores; main/GPU threads off, other guest threads off (default)`, no
`QoS utility set`; 20 of 22 FPS summaries >= 59.5 (low 56.8); CPU median 80% of
a core. Stefan: 1.5x / 60 very smooth. `21 October 2026/nfsmw_run_2_ipad.log`
(22:51:10–22:52:51): `6 efficiency cores; ... on, ... on (default)`, 24
`QoS utility set` lines; 15 of 20 summaries >= 59.5 (31.8 load, 58.6, 59.4,
57.7); CPU median 150%. Stefan: smooth as ever at 1.5x / 60. E-core rule
confirmed on both devices. The iPhone keeps the old (higher) drain.
Next candidate for 4-E-core devices, no code needed: iPhone with Extra Args
`--ios_utility_qos=false --ios_utility_qos_guest=true` (only the non-main guest
threads at Utility; main and GPU command threads keep their normal QoS).

### October 21, 2026 — Step 3 investigation: renderer per-draw CPU work and the GPU rise

Stefan asked to move on to the renderer's CPU work. Read-only; no source change.
Evidence: the Oct 20 IPA26 time profile (scratchpad tp3.py, temporary) and the
Oct 21 ON-arm log `21 October 2026/nfsmw_run_1_ipad.log` (frame 17701 summary,
300 frames, 2,794 draws/frame, Extra Args in `21 October 2026/extra_args.txt`).

Profile, % of all samples: Record 18.31% inclusive (self 4.44%, nested Record
5.89%, Fingerprint 4.12%, AttributeKey map 1.06%, operator new 0.67%, Metal
function map 0.58%); RenderFrame 19.98% inclusive (self 2.44%, nested 6.34%,
unsymbolized Metal driver ~4.3%, GpuBuffer map 1.17%, string-keyed tree 0.88%).
Fingerprint callers: Record 4.12%, NativeResolve 0.06%.

Log per 300 frames: vertex cache watch/fingerprint/miss 0 / 2,925,878 /
123,715; 1,410,395 attribute fingerprints (0.12 us/sample incl. timing); index
cache hits/misses 1,013,384 / 628. Recording 6.23 ms/frame (vertices 3.21),
rendering 8.73 ms/frame, GPU 10.92 ms/frame. Write watch is off by default
(`nfsmw_native_write_watch`, correctness problems recorded earlier), so every
cached attribute is re-validated by sampled fingerprint (~4,700 calls/frame)
and every cached index list by a full hash up to 4 KiB (~3,400/frame).
RenderFrame encodes the whole frame into ONE command buffer and commits at
the end (native_renderer.mm ~4741 / ~6709).

Interpretation (inferred): after Utility QoS the CPU side is cheap per
instruction, so the remaining per-draw CPU work is worth roughly a few percent
of drain at most. GPU impact rose 21% in the Oct 21 ON arm; with encoding
now ~8.7 ms on E cores and a single end-of-frame commit, the GPU receives each
frame later and has less slack, which may raise its clock.

Proposals (not implemented; awaiting Stefan):
A. Early command-buffer commit (default-off switch): commit the frame's command
   buffer at a few render-pass boundaries and continue in a new one on the same
   queue, so the GPU starts while encoding continues. Same passes, order and
   image; completion/lifetime handling must wait for the last buffer. Target:
   recover the +21% GPU impact. Medium effort; gain unproven.
B. Per-frame fingerprint memo for non-dynamic attribute regions (default-off):
   one fingerprint per (base, region, size) per frame instead of per draw, for
   meshes drawn again in reflection/shadow passes. Dynamic entries keep
   per-draw checks. Needs a duplicate counter first. Small CPU gain (<= ~4%).
Not proposed: sampled index hashing or write-watch reuse (could miss changes,
visual risk), and the earlier caution against core-QoS changes is superseded
by the Oct 21 measured result.

### October 21, 2026 — IPA30: five experiments made default; proposals A and B implemented

Stefan: "yes make the 5 default, and also implement both A and B and if
something goes wrong we'll go from there".

Defaults changed to true (they were on in every iPad measurement, including the
Oct 21 -23.6% pair, per the run_1_ipad log mode lines): `nfsmw_native_render_utility`,
`nfsmw_native_attribute_lookup`, `nfsmw_native_gpu_lookup_hash`,
`nfsmw_native_lazy_diagnostics` (native_renderer.mm) and
`nfsmw_native_transform_copies` (ios_main.mm). `nfsmw_native_gpu_lookup_stats`
stays false (diagnostic only). The iPhone runs of Oct 21 had all five off; an
iPhone correctness lap is still needed.

B, `nfsmw_native_fingerprint_memo` (default false), Record in
native_renderer.mm: a per-frame map (base, region start, region size) ->
fingerprint, cleared when frame_counter changes. Used only for attribute entries
not marked dynamic and not for DrawPrimitiveUP vertices; dynamic data keeps its
per-draw fingerprint. Consequence: a non-dynamic region rewritten mid-frame is
seen one frame later. Counter: the frame summary now ends the fingerprint part
with `, <n> from this frame's memo`.

A, `nfsmw_native_early_commit` (default false), RenderFrame: at a render-pass
boundary (after the previous encoder ends and the motion copy), once at least
max(400, draws/3) draws were encoded since the last commit and at least half
that many remain, the command buffer is committed and encoding continues in a
new one on the same queue. Disabled while GPU pass profiling, dumps or capture
are active. Present, write-backs and completion handlers stay on the last buffer;
each buffer retains its resources; same-queue order keeps pass order. GPU ms per
frame becomes the span from the first buffer's GPU start to the last one's end.
New line every stats window: `[native] early commit on|off: <n> early command
buffers over <frames> frames; fingerprint memo on|off`.

Build exit 0, no native_renderer warnings. IPA30
`ios/build/NFSMW-battery-defaults-early-commit-30.ipa`, SHA256
`0f24555d5ae48cae59616ec4592865317ad0509b61b7106ad6a8ca85fcee185c`, NFSMW UUID
`5E8C4D54-6722-3B1C-95FD-3B23FFA00AAD`; 104 metallibs identical to the cache;
`unzip -tq` OK; `codesign --verify --deep --strict` OK. Not run on a device.
Test: iPhone and iPad correctness with defaults; then A and B with
`--nfsmw_native_early_commit=true --nfsmw_native_fingerprint_memo=true`.

### October 21, 2026 — IPA30 checks: defaults fine, B works, A never fired; IPA31 fixes A

iPhone, `21 October 2026/nfsmw_run_4_iphone.log` (IPA30 defaults, A/B off):
`4 efficiency cores ... off`, render queue Utility, 16 of 21 summaries >= 59.5
(57.3, 59.4, 58.8, 58.6). Stefan: seemed OK.
iPad, `21 October 2026/nfsmw_run_3_ipad.log` (23:10:18-23:11:58, defaults + A + B):
`early commit on ... fingerprint memo on`; 15 of 20 summaries >= 59.5 (37.9 load,
58.2, 59.4, 57.7), similar to the Oct 21 reference run. All hitch lines are in
the intro/loading, as in the reference. Stefan felt possible microstutters, not
confirmed by the log.
B measured: race windows 276k-416k attribute fingerprints per 300 frames versus
1.03M-2.03M in the reference run (~70-80% fewer), 597k-830k served by the memo;
recording 3.7-5.3 ms/frame versus 5.2-7.9 ms in the reference. No visual issue.
A measured: `0 early command buffers` in every window. Cause: the threshold
(max(400, draws/3) since the last commit with half of that left) never met at a
pass boundary, since most draws sit in one long main-scene pass.
IPA31 change: up to three early commits per frame, each at a pass boundary
after >= 250 draws since the last commit with >= 100 draws left, counted by
draw position; also allowed while GPU pass profiling is active (sample buffers
are read in the last buffer's completion handler, after the earlier ones).
Dumps and capture still disable it. Build exit 0. IPA31
`ios/build/NFSMW-battery-early-commit-fix-31.ipa`, SHA256
`2f09dae9f714acbe8586436032403af2c260c738a9a1a422acce99bc7034ff85`, NFSMW UUID
`9AEF39D1-5E2D-3902-A6F0-E687F0F36DD4`; 104 metallibs identical; zip and
codesign checks OK. Next: one lap to see nonzero early commits, then Stefan's
single A+B power run on the same pursuit/route, compared with the Oct 21 ON arm.

### October 21, 2026 — IPA31 A+B power run (one arm) against the Oct 21 ON arm

Inputs: `21 October 2026/nfsmw_run_4_ipad.log` (one unrecorded Quick Race lap,
then the pursuit) and `21 October 2026/power_profiler_2_ipad.trace` (run 1,
23:20:00.048+02:00, 544.509 s). IPA31 defaults plus
`--nfsmw_native_early_commit=true --nfsmw_native_fingerprint_memo=true`.
Early commit fired: 118 windows at 900 early buffers / 300 frames (3 per frame),
6 at 0 (menus/loading). Brightness 32.0%, thermal Nominal. Same parser; GPU
impact recomputed with the actual duration (gpu.py assumed 599 s).

| Whole run | Oct 21 ON arm (IPA27) | IPA31 A+B |
|---|---:|---:|
| Estimated drain, pp/hour | 25.703 | 25.413 |
| CPU impact | 5.299 | 5.221 |
| GPU impact | 2.781 | 2.900 |
| Display impact | 5.587 | 5.399 |
| CPU instructions, billion/s | 10.69 | 9.94 |
| Log FPS >= 59.5 | 157/171 | 139/147 |

Measured: -1.1% drain, within the ~2.5% pursuit-to-pursuit variation; B lowers
instructions ~7% but CPU impact only -1.5% (cheap E-core clocks); A did not
lower GPU impact (+4%), so the "GPU starved by a late single commit" inference is
not supported. Log GPU ms/frame now spans all buffers (10.91 vs 9.35) and is
not comparable to earlier values. FPS lows 55.6-58.8 outside loading.
Charging: DeviceChargingState has no rows; the log battery field fell 80% -> 75%
during the recording, consistent with running on battery. The "charger
connected" Stefan sees is inferred to be the device state Instruments captured
when it first attached over the cable; the power estimate is modeled.
Recommendation: keep B (less work, no visual issue seen), leave A off by default.

### October 21, 2026 — Fingerprint memo default on (IPA32); GPU options without lower resolution

Stefan agreed: B default, A off. `nfsmw_native_fingerprint_memo` default true;
`nfsmw_native_early_commit` stays false. Build exit 0. IPA32
`ios/build/NFSMW-battery-memo-default-32.ipa`, SHA256
`1f4990de76be2b6bd59b629741591bf8ba5cdf52bc00c6bd47ce27da000802af`, NFSMW UUID
`5D1534C8-183D-3D26-84B4-F178ADB0FDC4`; 104 metallibs identical; zip and codesign OK.

Stefan asked whether the GPU can be cheapened other than by resolution. From the
Oct 19 per-pass audit above (mean sampled span 4.35 ms): main scene 1.95,
reflection 0.80, shadow 0.44 ms (~73%, real image work); color resolve copies
0.30, depth copies 0.28, cube assembly 0.06 ms (~15% together); other 0.43 ms.
Already done: BC textures sampled natively where supported, unread attachments
discarded, no artificial pass splits, pooled targets, no unchanged depth copies.
Image-identical candidates, ranked:
1. Avoid whole-surface color resolve copies (dataflow A/B above): keep the
   source image as the snapshot when format/size/swizzle match and nothing
   writes it later; versioned targets needed. Up to ~0.3-0.6 ms of the span,
   only partly eligible; medium-high effort.
2. Per-shader GPU cost: profile which translated pixel shaders dominate the main
   scene and reflection passes, then improve their translation (registers,
   redundant conversions) without changing results. Largest ceiling, unknown
   size until profiled; needs a GPU capture or per-draw timing diagnostic.
3. Memoryless storage for attachments that are cleared and discarded within
   one pass: saves memory, small bandwidth gain.
Not image-identical (settings only): MetalFX temporal from a lower internal
resolution to the same output, Battery mode's half-rate reflections/shadows.

### October 21, 2026 — GPU next steps: cost probe for shaders, memoryless deferred

Stefan chose candidate 2 (shader cost) and 3 (memoryless), with 1 (resolve-copy
avoidance) kept on the backlog.

2: no new build needed. The renderer already has `--nfsmw_native_cost_probe=true`
(native_renderer.mm ~5361 / ~6676, default false): every 60th frame with more than
1,000 draws it leaves out one pixel shader, cycling through the 16 most-drawn,
and logs `[cost-probe] without ps <key> (<n> of <m> draws): GPU <x> ms, the 8
frames before <y> ms: <delta> ms`. A ~5-minute pursuit gives roughly 19 samples
per shader. Limits: ranks by draw count (a costly full-screen shader with few
draws is missed), one frame per sample, noisy. The left-out frame is visible as
a missing material for one frame. Next: Stefan records one pursuit with the
probe on (no profiler), then shader translation work targets the top deltas.
3: on inspection the renderer already discards attachments not read later
(last-pass store actions, "last passes storing only what is read"), so the
bandwidth that memoryless storage would save is already avoided; memoryless
would mainly save memory. Expected energy gain about zero; deferred to the
backlog with 1. Not implemented.

### October 21, 2026 — Cost probe results (IPA32, iPad pursuit)

Log `21 October 2026/nfsmw_run_5_ipad.log`, `--nfsmw_native_cost_probe=true`:
264 probe frames; mean GPU of the 8 frames before each probe 10.12 ms. Median
GPU time saved when the pixel shader's draws are left out (includes their
vertex, raster and overdraw cost, not only the pixel shader):

| ps key | samples | median saved, ms | draws/frame | what it is (from the translated source) |
|---|---:|---:|---:|---|
| 4fbaecfb8e7c4f40 | 19 | 0.91 | 620 | shadow-map caster: writes 1,1,1,1; optional alpha test on the float constant g_bShadowMapAlphaEnabled |
| 27d82ea0faa380a8 | 23 | 0.90 | 326 | alpha-tested trees (known from bring-up) |
| 684f4711f29b9f77 | 14 | 0.76 | 460 | alpha-tested fences/plants (known), 12 fetches |
| fe510d2d256c173b | 12 | 0.49 | 8 | few large draws |
| 2d8bf2c63ddd2608 | 20 | 0.30 | 186 | |
| d8bb87fee2d8ec76 | 20 | 0.26 | 126 | 18 fetches |
| d1f317fad0f46ac6 | 15 | 0.24 | 369 | uses g_bDoCarShadowMap |
| 705e150f5ef6e09b | 20 | 0.24 | 16 | |
| 914048260028ca21 | 2 | 1.21 | 10 | too few samples |

Every translated pixel shader has the alpha-test block behind a Metal function
constant (G_SPEC_CONSTANTS, compiled out when off), so generic discards are not
the issue. The top three are inherent work: shadow casters and alpha-tested
foliage, whose discard is required. Lossless candidate found: the shadow-caster
shader keeps a discard reachable through a uniform (`p0 = g_bShadowMapAlphaEnabled.x
!= 0.0`), which can prevent Apple's hidden-surface removal/early depth for all
620 casters even when the constant is 0. Proposal (not implemented): a function
constant variant with that branch compiled out, chosen per draw when the
constant register is 0 (shader rewrite in the style of rewrite_shadow_filter.py
plus a pipeline-key bit). Expected: part of ~0.9 ms (shadow casters), size
unknown until measured with the same probe. Memoryless (candidate 3) moved to
the backlog for its memory benefit on older devices, at Stefan's request.

### October 21, 2026 — IPA33: shadow-caster variant without the unused cut-out

Stefan approved the proposal ("yes"). Shader side: new
`tools/native/rewrite_shadow_caster_alpha.py`, run by `build_shaders.sh` after
the shadow-filter rewrite, changes only ps_4fbaecfb8e7c4f40 line
`p0 = g_bShadowMapAlphaEnabled.x != 0.0;` to
`p0 = ((g_SpecConstants() & 0x1000u) == 0u) && (g_bShadowMapAlphaEnabled.x != 0.0);`
(G_SPEC_CONSTANTS is function constant 0; unset = 0 = original behavior). Applied
to the shader cache and that one library recompiled with the script's exact
commands (`-O2 -std=metal3.1 -D__air__ -mios-version-min=26.0`); all other 103
libraries unchanged; previous library kept in the scratchpad.
Renderer: `nfsmw_native_shadow_caster_variant` (default false). For ps 4fbaecfb
draws whose c1.x (ps constant word 4) is 0.0f, bit 0x1000 is added to the
pipeline key's alpha_spec, so PixelVariant/MotionVariant build the function
with that bit set; the branch it removes is never taken for those draws, so the
shadow map is unchanged. New pipelines for the variant are compiled at first
use (one-time). The stats line now ends with `shadow caster variant on|off:
<n> draws`.
Build exit 0. IPA33 `ios/build/NFSMW-battery-shadow-caster-33.ipa`, SHA256
`080f5418db319dc276aa2f5828a8e9519e2e01a4f6257e30272dc81cfc4ad6a4`, NFSMW UUID
`516A4623-1FCF-3AD4-B994-4939E6ABA39E`; 104 metallibs identical to the cache
(ps_4fbaecfb now SHA256 prefix 3f45de43a3f7f522); zip and codesign OK. Not run
on a device. Test: one pursuit with `--nfsmw_native_shadow_caster_variant=true
--nfsmw_native_cost_probe=true`; compare 4fbaecfb's probe delta (0.91 ms) and
the frame GPU time with the IPA32 probe run; check shadows look the same.

### October 21, 2026 — IPA33 shadow-caster variant result; default on (IPA34)

Log `21 October 2026/nfsmw_run_6_ipad.log` (IPA33, variant + cost probe, same
pursuit). Stefan: shadows looked identical. Variant draws per 300-frame window
94,610-98,510 in race windows (~320 of the ~620 caster draws per frame), 0 in
menus. Probe comparison with run_5 (IPA32):

| | run_5 IPA32 | run_6 IPA33 variant |
|---|---:|---:|
| Probe samples | 264 | 287 |
| Mean GPU of the 8 frames before each probe, ms | 10.12 | 8.85 |
| Mean logged GPU ms/frame (summaries) | 9.38 (58) | 8.35 (62) |
| ps 4fbaecfb median saved when left out, ms | 0.91 (n=19) | 0.96 (n=18) |
| ps 27d82ea0 (trees) | 0.90 (n=23) | 1.44 (n=17) |
| ps 684f4711 (fences/plants) | 0.76 (n=14) | 0.22 (n=16) |
| FPS summaries >= 59.5 | | 52/62 |

Frame GPU time is ~11-13% lower, but the casters' own probe delta did not fall,
so the drop cannot be attributed to the variant; route/scene variation (the
foliage deltas moved a lot) is the more likely explanation (inference). The
variant is equivalent by construction (removed branch not taken for those
draws) and showed no visual difference, so it is default on from IPA34; its
energy effect is unproven. IPA34 `ios/build/NFSMW-battery-shadow-caster-default-34.ipa`,
SHA256 `f86bceb52fea01c9d7135371bf9ab5917f9f2a5620bb9c7a97f8df8d088f83f2`, NFSMW
UUID `36D129D7-74A9-3D18-A33C-9E9B4DD91D77`; 104 metallibs identical; zip/codesign OK.

### October 21-22, 2026 — Stutters after the shader change (pipeline archive), iPhone heat, iPhone baseline

Stefan (IPA34, iPad and iPhone): two big stutters since the shadow-caster change,
one right after "loading save data" into the main menu, one from the pursuit's
opening scene until a few seconds of control. iPhone profiler run: 60 FPS locked
until ~6 minutes, then 30-40 logged but felt like 10-15, never recovered; the
profiler showed Nominal -> Fair while the phone felt very hot.

Stutters, measured: `21 October 2026/nfsmw_run_5_iphone.log` logs 8 `pipeline
cache miss: ps_4fbaecfb8e7c4f40 ... (added)` (the rewritten library invalidates
its archived pipelines), `334 draws left out while theirs compiled`, and two
synchronous archive saves exactly at the two stutters: 00:03:19.344 `saved
(43699 KiB)` after the menu load, 00:03:40.384 `saved (21057 KiB)` at the pursuit
start. iPad `nfsmw_run_6_ipad.log`: same, saves 24372 then 14356 KiB. The IPA32
iPad log has no misses and no saves. This is the parked "pipeline archive
persistence" issue (synchronous save ~2.7 s stall) exposed by the library change.
The saved file shrinking (43.7 -> 21.1 MB, 24.4 -> 14.4 MB) is consistent with
saving over the file the archive was loaded from losing entries (inferred), which
the old v2 comment also reports (misses recurring session after session).
Fix (IPA35, no switch, no visual effect): PipelineArchive::Report no longer
serializes on the render queue; it sets dirty=false and dispatches the save to a
serial Utility queue `nfsmw.pipelines.save`, which serializes to
`<archive>.new` under the archive mutex, then rename()s it over the archive
(one save in flight; on failure dirty is set again). Log: `pipeline cache saved
in the background (<n> KiB)`. Risk: archive lookups (outside the mutex) can run
while a save is in progress; MTLBinaryArchive thread-safety for that case is
assumed, not verified. Still expected once per changed library: the first
compile of new pipelines (draws left out while compiling).

iPhone heat, measured from the same log: FPS summaries 57-60 until 00:08:49, then
50.4, 45.8, 36.7, 28.0, 26.1, then 19.7-25.9 to the end; late windows GPU
23.7-24.2 ms/frame and rendering 21-33 ms/frame (GPU and CPU slowed by thermal
throttling, inferred). Stefan's settings have `[battery] 30 fps when warm off,
30 fps in menus off, 0.75x when hot off`, so no automatic step-down happened;
uneven 20-40 FPS under a 60 cap judders, which explains "feels like 10-15".
iPhone baseline power (no Utility QoS; `power_profiler_1_iphone.trace`, run 1
00:04:07.015, 549.654 s): drain 37.599 pp/h, CPU impact 21.014, display 1.993,
instructions 9.85 G/s, brightness 47%; Nominal 0-5:48, Fair 5:48-9:09. CPU
dominates the iPhone's cost, so the guest-only Utility setting is the main lever.
IPA35 `ios/build/NFSMW-battery-pipeline-save-35.ipa`, SHA256
`50b0f8419dfb7d2ba89ef9239135ee4a72a227063395abdf0f0a51a33304d1da`, NFSMW UUID
`EC48DBCA-637F-3BA7-841D-C28D8B1B6EDF`; 104 metallibs identical; zip/codesign OK.

### October 22, 2026 — iPhone null-call crash near the safehouse: deferred-queue ordering fix (IPA36)

Stefan, iPhone, `--ios_utility_qos_guest=true` in all three logs
(`22 October 2026/`): `nfsmw_crash_iphone.log` (1.5x, 16:08:48-16:19:04, 3
launches) and `nfsmw_crash_2_iphone.log` (1x, 16:20:33-16:21:26) both end with
`[invalid-call] lr=0x823C82F8 r1=0x7018FB80 r3=0x8293CD30 r4=0x00000000 r5=0x00000001
| stack <- 0x82441C5C <- 0x82441DAC <- 0x8262E904` and `[FATAL] Call to invalid or
unregistered function at guest address 0x00000000` (the crash
patch_ios_invalid_call_log.py was added to locate). `nfsmw_run_1_iphone.log` (1x,
16:23:38-16:42:27) did not crash.

Cause, from the generated USA code: lr 0x823C82F8 is the bctrl in sub_823C8290
(nfsmw_recomp.100.cpp), the main loop's runner of a deferred-call queue at
0x82919650 (+0 count written, +4 count run, +12 flag, +20 end, +24 read pointer;
entries: function pointer, size, copied data). sub_823C8210
(nfsmw_recomp.48.cpp) appends: copies the data, stores the function pointer and
size, then advances +20 and +0, with no barrier. r3 is the entry, r4 its function
pointer (0) and r5 = 1 pending entry: the consumer saw the advanced queue before
the entry's function pointer (inferred: a cross-thread publication race the
recompiled code allows on ARM; the producer thread is not identified).

Fix: new `tools/ios/patch_game_deferred_queue.py` (run by generate_code.py after
the transform copies; --status/--revert; applied, idempotent): release fence before
the producer stores +20; acquire fence after the consumer loads +20; if the
function pointer reads 0, up to 200,000 re-reads with yield + acquire fence
before the original call (if it stays 0 the original crash still occurs). Not a
fix if the queue is also reset concurrently (not observed). Build exit 0, only
nfsmw_recomp.48/.100 recompiled. IPA36 `ios/build/NFSMW-battery-queue-fix-36.ipa`,
SHA256 `41398761a0c0cb8851b15fb54576b77370535a4f48fdcb3e2b08cce77f235429`, NFSMW
UUID `D8A19FC2-C3A9-3E63-AA24-47E9EAF8D600`; 104 metallibs; zip/codesign OK.
Not run on a device.

Heat, from the same logs: 1.5x session FPS 60 from 16:11 to 16:16:31, then 46.1,
29.2 (battery field 65% -> 55% in 10 min including menus); 1x session held
57-60 throughout except loading/menus (3.2, 10.0, 17.3), battery 55% -> 45% in
18.6 min. The game log's thermal field stayed `nominal` in both; Stefan reports
the 1.5x phone hot. Inferred: 1x roughly halves the iPhone's drain rate and
avoids the throttling; Stefan's "30 fps when warm"/"0.75x when hot" are off.

### October 22, 2026 — iPhone CPU profile (from the Oct 21 iPhone baseline trace)

Time profile of `21 October 2026/power_profiler_1_iphone.trace` (no Utility QoS;
1.5x; 652.9 s of samples; scratchpad tp.py/tp3.py, temporary). iPhone cores are
labelled E and "S" (performance) in this trace. Per thread: LiveContainer dispatch
workers (native render queue + Metal driver) 43.5%, GPU Commands 16.2%, Main
XThread 15.3%, XThreadA70F 12.5%, XThreadDB0B 7.6%, UI main thread 2.5%.
RenderFrame 24.85% inclusive (self 10.04% nested + driver: drawIndexedPrimitives
4.38%, renderCommandEncoderWithDescriptor 1.29%, AGX context 1.21%,
setRenderPipelineState 0.45%, newTextureView 0.25%; GpuBuffer map 1.58%,
string-keyed tree map 0.73%, EdramKey 0.30%). Record 10.32% inclusive
(Fingerprint only 0.81%: the memo works). Inference: on the iPhone the Metal
encoding loop is the largest single CPU cost; its own bookkeeping (~10% self plus
maps/strings) is the lossless target, driver draw calls largely are not.
Next (proposal): attribute RenderFrame self time to source lines (atos on the
matching binary) and trim per-pass/per-draw bookkeeping; a new iPhone profile is
optional for that first step.

### October 22, 2026 — Renderer bookkeeping trims and line tables (IPA37)

Stefan approved starting on the renderer's own CPU cost. The Oct 21 iPhone trace
was recorded with IPA34 (NFSMW UUID 36D129D7..., load 0x10ba58000). RenderFrame
self samples by address (scratchpad addr.py): 7.50% of all samples; hottest
address RenderFrame+9916 (0.93% of all samples), then a cluster near +61524 and
+43968/+49060. The IPA34 binary had no line tables; with the same function start
in IPA37, +9916 maps to the upload-sizing traversal (`size_constants` over all
draws, native_renderer.mm ~4434; two full passes over ~2,800 328-byte Draws) and
+61524 near the vertex-buffer binding (~6288). Mapping across builds is
approximate; future traces will map exactly (below).

Changes (IPA37, all exact equivalents, no switches):
- Setup loop over draws: target key, Target, size entry and sample count looked
  up once per run of draws on the same target (surface/colour/depth info), as
  the existing motion `key_of` memo does; depth-only counter entry cached too.
  Second-target (MRT) path unchanged.
- Main encode loop: the target key string made once per run of draws on the
  same target (reset at position 0 of every frame).
- `nfsmw_native_fused_upload_sizing` default true (IPA21 experiment, iPad
  correctness passed): one traversal for the upload budget instead of two.
- `ios/CMakeLists.txt`: native_renderer.mm compiled with `-gline-tables-only`
  (no code change); a dSYM is kept beside the IPA copy so Time Profiler
  addresses from a device trace resolve to source lines with atos.
Expected gain: about 1-2% of app CPU (inferred from the sampled hot spots), not
measured. Build exit 0. IPA37 `ios/build/NFSMW-battery-target-memo-37.ipa`,
SHA256 `774badbd173be121227419f22059522b0171d6e4f71d9b8ddaef46340b7c6654`, NFSMW
UUID `353B6258-10CB-347B-91AB-38E4DCAB69BC`; dSYM
`ios/build/NFSMW-battery-target-memo-37.dSYM` (ignored, same UUID); 104 metallibs;
zip/codesign OK. Includes the IPA36 queue fix. Not run on a device.
Next: an iPhone Power Profiler run on IPA37 (with `--ios_utility_qos_guest=true`),
then symbolize RenderFrame/Record self time to lines and trim the top items.

### October 22, 2026 — Queue fix device check

`22 October 2026/nfsmw_run_2_iphone.log` (one launch, 22:23:22-22:26:30, 1x,
`[utility-qos] 4 efficiency cores; main/GPU threads off, other guest threads on
(Extra Args)`): Stefan completed the race that crashed at its start in both
earlier logs; 0 invalid-call/FATAL lines; 31 of 37 FPS summaries >= 59.5. The log
does not identify the IPA build (36 or 37; both contain the fix). One clean run of
an intermittent crash; D-001 moved to monitor.

### October 22, 2026 — Direct draw path (backlog item 3): iPhone size check before design

Stefan wants to start on the direct guest-to-native draw path. Before any design,
the same stage attribution as Oct 19 (iPad) was run on the Oct 21 iPhone trace
(scratchpad stage.py, temporary; call-path membership, each sample counted once
per category; categories overlap):

| Call-path footprint, % of all iPhone samples | |
|---|---:|
| Guest draw/state/resolve packet writers (sub_825A3EC8, 82593A58, 82593818, 825930E0, 82593408, 8259A308, 82592340, 82597070) | 3.13 |
| Engine constant preparation sub_82699100 | 2.73 |
| CP ExecutePacket outside CpDraw/NativeSwap (packet decoding) | 3.46 |
| Union of the above (removable envelope) | 9.33 |
| CP thread total (WorkerThreadMain) | 17.39 |

The envelope matches the iPad's 9.13% (Oct 19). It is an upper bound: a direct
path still needs the state those writers compute (dirty registers, constants,
fetch constants), so only part of it would disappear; inferred realistic saving
~4-6% of app CPU. The native recording itself (Record, ~10%) stays, only moved
to the game thread. Correction to the earlier chat summary that called this "a
large share of CPU work": measured, it is the largest single removable stage,
but under 10% even as an upper bound. Risks unchanged from Oct 19: command
ordering, register side effects, predicates, queries, fences, writebacks,
ring/segment progress. No code written; direction awaits Stefan.

### October 22, 2026 — Direct draw path: how the game feeds the GPU, and a phased design

Stefan chose to start the direct path (backlog item 3) and parked the older-chip
profile (it is Battery mode chosen automatically: polishing work).

How state reaches the GPU today (read from the generated USA code):
- sub_825A3EC8 is the game's D3D "flush dirty state" before a draw. The device
  object holds 64-bit dirty masks at +16, +24, +32, +40 and +48 and a register
  shadow. For each mask it calls an emitter and then clears the mask.
- sub_825A28A8 (nfsmw_recomp.56.cpp), the emitter: (device, mask, first
  register, shadow pointer). For every run of set bits it writes a PM4 type-0
  header `((count-1) << 16) | register` into the ring, then copies the run's
  values from the shadow, wrapping or flushing via sub_825A27F0 when the
  segment is full.
- sub_825A2A60 (nfsmw_recomp.22.cpp): the same for 4-word groups (float4
  constants), with a 0x80000000-based header.
- sub_82593A58: the draw itself (state flush, segment space check, draw packet,
  indexed/tiling state). Draws, resolves, fences and queries all reach the SDK
  CommandProcessor through the same ordered ring.
So every dirty register is copied twice: shadow -> ring by the game, ring ->
register file by the CP (ExecutePacket), before native Record reads it.

Phased design (each phase is a default-off switch, measured before the next):
- P0, diagnostic (no behaviour change): per-frame counts of register words
  written per emitter (type-0 runs, float4 groups), draw packets and other
  packet types, so each phase's ceiling is known on device.
- P1, register runs as one block: the emitters copy the dirty runs into one
  host-side block appended to the ring as a single private packet (e.g. a
  type-3 NOP carrying a pointer and length), in the same position in the
  stream. The CP applies the block with one copy into its register file, and
  runs the existing per-register side-effect handling only for registers that
  have side effects. Order, fences and queries are unchanged because the block
  stays in the stream. Saves header formatting and per-packet decoding.
- P2, draw records: the draw packet carries a pointer to a draw record prepared
  on the game thread (indices, fetch constants), so CpDraw skips re-deriving it.
- P3, direct native recording on the game thread, keeping a stream marker for
  order. Largest change; only if P1/P2 show the stage is worth it.
Ceiling for the whole path on the iPhone: 9.3% of app CPU (measured envelope),
realistic 4-6% (inferred). Main risks: register side effects, ring segment
wrap and CP read-pointer writeback, predicated packets, and anything else that
reads the ring (resolves, occlusion queries, swaps). Validation: bit-exact frame
snapshots (nfsmw_native_dump) with the switch on/off on the same scene, plus
the usual device checks. Next: implement P0 on Stefan's approval.

### October 22, 2026 — Direct draw path P0: PM4 census build (IPA38)

Stefan approved P0 ("ok"). New SDK patch `tools/ios/patch_ios_packet_census.py`
(listed last in prepare_sdk.py, applied 2/2): cvar `ios_packet_census` (default
false). In CommandProcessor::ExecutePacket it counts packets and payload words by
key (type-3 opcode 0-127; 128 type 0; 129 type 1/2) into exported arrays
`nfsmw_cp_census_packets` / `nfsmw_cp_census_words` in librexgpu-xenos. The native
renderer finds them with dlsym (the GPU plugin is loaded at run time; the first
link failed with undefined symbols and the first export attempt was hidden, both
fixed) and, with each 300-frame stats window, logs `[pm4-census] per frame over
<n> frames | op <xx>: <p> packets, <w> words | type 0: ...` for the top ten
keys, then resets. Counters are plain integers (CP thread writes, render queue
reads): approximate, diagnostic only. Build exit 0. IPA38
`ios/build/NFSMW-battery-pm4-census-38.ipa`, SHA256
`bf0bd4b08f5ec3660c35e579e3fd4424c9f8472496cdc99b7e5994fc240f56b2`, NFSMW UUID
`83839B57-2037-347F-BD4C-310AEB0B51BF`, dSYM beside it; 104 metallibs; zip and
codesign OK; both symbols exported (nm). Not run on a device.
Test: one race or pursuit with `--ios_packet_census=true` (iPhone or iPad).

### October 22, 2026 — P0 census result (iPhone race lap)

`22 October 2026/nfsmw_run_3_iphone.log`, IPA38, `--ios_packet_census=true`,
21 census windows. Race windows (5 shown in the log tail; ~1,830-3,270 draws
per frame summary sample), per frame:
- type 0 (register runs): 16,500-18,200 packets, 214,500-233,900 words
- type 1/2 (2 = 1-word NOP): 16,200-18,400 packets, ~1 per type-0 packet
  (the float4 emitter sub_825A2A60 writes a 0x80000000 word before its header)
- op 0x22 DRAW_INDX: 2,270-2,660 packets, 8,800-10,300 words
- op 0x2b: 130-360 packets, 4,500-13,000 words; op 0x50: ~2,000-2,300;
  op 0x27 / 0x3b: 1,500-1,870 each; op 0x5a ~1,000-1,130; op 0x46 ~1,000-1,160
Menus/loading: type 0 1,160-6,700 packets.
Reading: ~7 type-0 runs and ~90 register words per draw, written by the game's
emitters and decoded by the CP; ~34,000 tiny packets per frame in all. The CP
already copies type-0 runs in bulk (`ios_type0_ranges`,
patch_ios_type0_ranges.py), so the remaining CP cost is mainly per-packet
dispatch (~34k ExecutePacket calls/frame) plus the guest's header/NOP writes.
P1 (one block per state flush, ~2,400/frame instead of ~34,000 packets) would
remove most of that dispatch; estimated ~2-3% of app CPU (inferred from the
3.46% CP-decode footprint), within the 4-6% realistic estimate for the whole
path. Decision for Stefan: implement P1 (guest emitter rewrite + private packet
+ CP handler, medium risk) or stop the direct path here.

### October 22, 2026 — Direct draw path P1a: CP fast runs (IPA39)

Stefan: "yes lets go" for P1. Implemented first as the lower-risk CP-side half of
P1 (no guest code change): new SDK patch `tools/ios/patch_ios_cp_fast_runs.py`
(after the census in prepare_sdk.py, applied 2/2), cvar `ios_cp_fast_runs`
(default false). In ExecutePacket, a type-0 or type-2 packet continues in a tight
loop with the following type-0/type-2 packets (up to 64): type 0 through the
unchanged ExecutePacketType0 (bulk ranges, side effects), type 2 skipped as
before. The next word is peeked (read, then set_read_offset back) and anything
else (type 1/3, 0, 0xCDCDCDCD) is left to the normal path. Disabled while
medir_paquetes timing is on; the census still counts run packets. Effect: the
~34,000 per-frame ExecutePacket dispatches of register/filler packets become
one per run. Known difference: the primary ring's read-pointer writeback can
trail by up to one run (<= 64 small packets). Expected ~1-2% app CPU (inferred);
the guest-side half (emitters writing one block) is deferred until this is
measured. Build exit 0. IPA39 `ios/build/NFSMW-battery-cp-fast-runs-39.ipa`,
SHA256 `334fc422a32af5ad424a8f2eef514f8c8f49f32747246987893d68aeb94167c9`, NFSMW
UUID `83839B57-2037-347F-BD4C-310AEB0B51BF` (unchanged), librexgpu-xenos
`7BC3CF79-94F8-39EB-B333-7174107B362E`; dSYM beside it; 104 metallibs;
zip/codesign OK. Not run on a device.
Test: a race with `--ios_cp_fast_runs=true` for correctness (image, no hangs at
loading or resolves), then an iPhone profiler pair ON/OFF.

### October 22, 2026 — P1a visual check passed; fast runs default on (IPA40); P1b assessment

`22 October 2026/nfsmw_run_4_iphone.log` (IPA39, `--ios_cp_fast_runs=true` per
Stefan; the build had no log line confirming the switch): one launch
22:46:36-22:48:23, visual check passed per Stefan, no FATAL/invalid-call, one
startup watchdog at 22:46:53 (the usual post-start pause), 16 of 21 summaries
>= 59.5. Stefan asks to postpone Time Profiler measurement to the end and keep
stacking. `ios_cp_fast_runs` default true (patch reverted and re-applied with the
new default; status 2/2); the stats line now ends `CP fast runs on|off`. IPA40
`ios/build/NFSMW-battery-cp-fast-runs-default-40.ipa`, SHA256
`3296d281f638e0e1e3061897936ffaa24b4df5f9ea933ed9a5e3616ff393b420`, NFSMW UUID
`32FD84F2-2FE2-3492-B1E5-67E3AD6D9388`, GPU plugin `7B12845A-4D0E-31A6-AD60-29E219B31569`,
dSYM beside it; 104 metallibs; zip/codesign OK.
P1b (guest emitters writing one block) assessment: with fast runs, the
remaining per-packet cost on the CP is gone; what the guest still does is write
~17k headers + ~17k fillers around ~220k value words it must copy anyway (the CP
consumes asynchronously, so values cannot be read from the device shadow in
place without a snapshot copy). Removing headers/fillers saves ~34k of ~254k
words per frame of guest stores: inferred well under 1% CPU, for a rewrite of two
emitters plus a private packet. Recommendation: skip P1b/P2; the direct path's
remaining value does not justify its risk.

### October 22, 2026 — Native GPR save/restore helpers (IPA41)

Stefan approved the held October 19 GPR helper prototype ("yes"). Implemented a
reduced version of that proposal: `ios/src/game_gpr_helpers.cpp` (added to the
USA-edition sources in ios/CMakeLists.txt) defines strong `__savegprlr_14..31` and
`__restgprlr_14..31` (the generated ones are weak thunks to `__imp__` bodies),
switch `nfsmw_native_gpr_helpers` (CPU, default false, restart required). With it
on and an ordinary stack pointer (256 <= r1 < 0xE0000000) the helper computes
`base + r1` once and stores/loads byte-swapped 64-bit rK at r1-8*(32-K)-8 in
ascending order and the 32-bit r12 word at r1-8 (restore: zero-extended into
r12 and LR), the same layout as the generated bodies; otherwise, or with the
switch off, it calls the original `__imp__` body. Not done from the proposal: the
host differential/sanitizer fixture and benchmark (skipped for time; every guest
function with a frame uses these helpers, so a mistake would crash at once).
Linked-app checks: all 36 ordinary helper symbols are the app's strong
definitions (`nm -m`, external, in the hook object); disassembly of save29: new
path 3 instructions per register (ldr, rev, stur) after a flag and range check,
versus ~9 per register in `__imp____savegprlr_29` (r1 reloaded and the physical
alias offset selected for every access). Inferred gain: roughly half of the
helpers' 3.8-4.3% body share, ~1.5-2% of app CPU; not measured.
Build exit 0. IPA41 `ios/build/NFSMW-battery-gpr-helpers-41.ipa`, SHA256
`c49270cf225398eae76720fc0427ec3b6efe5ea593d315e5e99e645265b827e3`, NFSMW UUID
`0CEBC0F6-811F-3547-865C-C345953E4273`, dSYM beside it; 104 metallibs;
zip/codesign OK. Not run on a device. Test: a race with
`--nfsmw_native_gpr_helpers=true` (any crash or freeze is the first check).

Extra Args guidance given to Stefan for IPA41: everything measured so far is a
compiled default now, so the old experiment lines should be deleted. iPad:
`--nfsmw_native_gpr_helpers=true` only. iPhone: that plus
`--ios_utility_qos_guest=true`. The log's `[cpu] <n>% of a core over 10 s` lines
are a rough CPU-time indicator (not energy; gameplay varies them by ~10%).

### October 22, 2026 — GPR helpers device check; default on (IPA42)

`22 October 2026/nfsmw_run_5_iphone.log` (IPA41, 22:56:17-22:58:03, 1x, guest
Utility via Extra Args; Stefan set `--nfsmw_native_gpr_helpers=true`, which IPA41
did not log): full race, no FATAL/invalid-call, 16 of 21 FPS summaries >= 59.5,
`[cpu]` median 100% of a core (runs 3/4 the same evening: 106 / 98; within
gameplay variation, so no CPU claim). Switch default true from IPA42; startup
log `[gpr-helpers] native register save/restore helpers on|off`. IPA42
`ios/build/NFSMW-battery-gpr-default-42.ipa`, SHA256
`1781118ace622b3b3a356238a06408f5796a644e841637b10ea0ce8733793500`, NFSMW UUID
`5C6A9AF4-41C0-33C3-94E3-964C285291D7`, dSYM beside it; 104 metallibs; zip/codesign OK.

### October 22, 2026 — iOS 26 shader libraries: stale bring-up variants (IPA43); battery ceiling

Stefan: shaders for iOS 26 still not compiled. Measured in the shader cache
(`strings` of each .metallib's target triple): 101 libraries `apple-ios26.0.0`,
3 `apple-ios27.0.0`: `ps_af393d4c46af230c_dbg1/2/3.metallib`, the wet-road shadow
bring-up variants, dated Oct 8 (built by hand from their own .metal in air/,
before `-mios-version-min`, and never rebuilt by build_shaders.sh, which only
compiles containers). They match the 0.3.0 iOS 26 log's
`ps_af393d4c46af230c_dbg2.metallib not loaded ... (0x00020009)` and `3 shader
libraries could not be loaded`. Fix: recompiled the three from air/ with the
script's flags and `-mios-version-min=26.0` (originals in the scratchpad); all
104 now `apple-ios26.0.0`. build_shaders.sh now checks every lib/*.metallib after
building and rebuilds any whose target is not `$ios_min` from air/, failing
otherwise (`sh -n` OK; full script not re-run, it needs the ISO containers).
IPA43 `ios/build/NFSMW-battery-ios26-shaders-43.ipa`, SHA256
`0ea5572853704b6eb694a5a8c290b53adea06cdc058ebe28675687f0bb20e65a`, NFSMW UUID
unchanged `5C6A9AF4-41C0-33C3-94E3-964C285291D7`; 104 metallibs all iOS 26.0;
zip/codesign OK. Not tested on iOS 26 (no device). Unverified: whether these
debug-only libraries caused the 0.3.0 black screen, or only the load warning.

Battery ceiling (Stefan's question), from the Oct 21 iPad pair (impact units):
with Utility QoS the whole run was CPU 5.30, GPU 2.80, display 5.59. Display is
now the largest and depends on brightness and refresh (already 60 Hz); the GPU is
mostly real image work (73% of span). Remaining lossless items are 1-3% each
(renderer trims, resolve-copy avoidance). Inference: on the iPad the big lossless
wins are taken. On the iPhone (Oct 21 baseline CPU impact 21.0 vs display 2.0)
CPU is still the dominant cost; the main open lever is Utility QoS for the main
and GPU command threads without dropping frames, e.g. adaptive QoS (Utility while
the frame's CPU work has headroom, normal QoS when it nears the budget).

### October 22, 2026 — Adaptive QoS for 4-E-core devices (IPA44)

Stefan agreed to the adaptive QoS idea. New `ios/src/adaptive_qos.cpp` (USA
sources in ios/CMakeLists.txt), cvar `ios_adaptive_qos` (Kernel, default false,
restart required; ignored when `ios_utility_qos` is on, i.e. on the iPad).
- The GPU command thread calls `OnSwap(interval)` from NativeSwap: a 60-swap
  window of late frames (interval > 1.3x the cap's 1000/ios_fps_cap ms and below
  250 ms, so loading stalls do not count). On Utility, 4 late frames switch both
  threads to User Initiated for a hold time; when it expires they return to
  Utility. Hold starts at 10 s, doubles (max 120 s) when Utility fails within 5 s
  of a retry, resets to 10 s after 60 s on Utility. Starts at Utility.
- The main thread follows through a strong override of `sub_823C8290` (the
  deferred-call runner called from its main loop): the first thread to call it
  applies the current mode to itself, then the original runs.
- Each thread sets only its own QoS (pthread_set_qos_class_self_np).
- Logs: `[adaptive-qos] on ...`, `main loop thread <id> follows the mode`,
  `User Initiated for <n> s (<late> late frames of 60, <s> s on Utility)`,
  `back to Utility` (first 60 transitions).
Not verified on device: that sub_823C8290 runs every loop on the main thread
(the log line will show which thread follows), oscillation behaviour, battery.
Build exit 0. IPA44 `ios/build/NFSMW-battery-adaptive-qos-44.ipa`, SHA256
`e4f5d178c4cf83a443f5e139adc648ecfd69fbc3e9e3928f60188a94125ec36b`, NFSMW UUID
`145F69E6-0EA9-3207-85BA-7D87F64413D8`, dSYM beside it; strong `_sub_823C8290`
bound (nm); 104 metallibs; zip/codesign OK.
Test (iPhone): `--ios_utility_qos_guest=true --ios_adaptive_qos=true`, one race;
check smoothness and how often the log switches.

### October 22, 2026 — Adaptive QoS iPhone result; cap-aware QoS defaults (IPA45); GPU view

`22 October 2026/nfsmw_run_6_iphone.log` (IPA44, guest Utility + adaptive):
`main loop thread 23742f follows the mode` (the sub_823C8290 hook works on the main
thread); two boosts (23:08:58 after 1 s on Utility, 23:10:17 after 59 s), each 20 s.
FPS summaries mostly 57-60 (e.g. 59.3, 58.0, 57.0, 56.8, 57.9), but Stefan: "not
really smooth 60": up to 3 late frames per 60 were tolerated before boosting.
IPA45 tightens it: late = over 1.2x the interval, 2 late in a 120-frame window
boost, hold 20 s doubling to 240 s when a retry fails within 10 s.

Stefan's point (correct): Utility QoS trades peak performance for efficiency; it
does not reduce work. At the 120 cap on the iPad, fixed Utility on the main/GPU
threads could cap the frame rate. IPA45 ApplyUtilityQosDefault: with >= 6 E
cores and `ios_fps_cap` > 60, main/GPU threads default to adaptive instead of
fixed Utility (other guest threads stay Utility); log
`[utility-qos] ... adaptive on|off`. Devices with fewer than 6 E cores (iPhone 17
Pro, M1 iPads: 4 E cores) keep full-speed defaults, so an M1 tester is not
slowed by this work. IPA45 `ios/build/NFSMW-battery-qos-cap-aware-45.ipa`, SHA256
`a89e2776d77938f9740657d7a3b8e4d8df722b14e9980528187ee8e40e0faec9`, NFSMW UUID
`3D31A4DB-CA99-3D00-B23F-EFCE6EADF310`; 104 metallibs; zip/codesign OK. Not tested.

GPU view for "native resolution melts the phone" (inferred from earlier data):
1.5x is 1920x1080, 2.25x the console's pixels; the iPhone's native panel is ~3.4x
more. Per sampled iPad frame the GPU spends ~1.95 ms main scene, 0.80 ms six
reflection faces (every frame), 0.44 ms two 1600x1600 shadow maps, ~0.64 ms copies
(Oct 19 audit). The console's shaders run in full 32-bit precision, unlike games
written for phones (half precision where it does not show). Candidates:
(a) half-precision arithmetic in translated pixel shaders where the source math
cannot change the 8-bit result (largest GPU lever on Apple GPUs; not
bit-identical, needs a per-shader safety analysis), (b) resolve-copy avoidance
(backlog), (c) MetalFX temporal from 1x to the native output as the "native look"
at much lower GPU cost (settings, already available).

### October 22, 2026 — IPA45 iPhone adaptive check; adaptive default on below 6 E cores (IPA46)

`22 October 2026/nfsmw_run_7_iphone.log` (IPA45, 1x + MetalFX "to the screen",
guest Utility + adaptive via Extra Args): boosts at 23:18:38 (after 1 s on Utility,
hold 40 s) and 23:19:21 (after 2 s, hold 80 s); main thread followed at 23:19:10.
16 of 21 FPS summaries >= 59.5; Stefan saw no dropped frames; `[cpu]` median 126%.
Reading: at 60 fps on the iPhone the main/GPU threads cannot stay on Utility; the
backoff makes adaptive settle at full speed (few late frames per retry, retries
every 80-240 s). Stefan asks about the 30/40 caps: the lateness budget follows
`ios_fps_cap` (33.3 / 25 ms), so there Utility is expected to hold (inferred from
the Oct 18 30 FPS Low Power pair; not measured on the iPhone).
IPA46: `ios_adaptive_qos` defaults on whenever the device has fewer than 6 E
cores (and, as in IPA45, with >= 6 E cores above 60 fps); guest-thread Utility
stays default off there (not self-correcting). IPA46
`ios/build/NFSMW-battery-adaptive-default-46.ipa`, SHA256
`e53538ebb055566abff989b0e4a9c3d9e13d956f02d7f7006233bf8e89e11798`, NFSMW UUID
`C60ADFE5-E2BA-319E-8715-3BF3AC5CDBEC`; 104 metallibs; zip/codesign OK.
Test: iPhone at cap 30 and 40, log should show long stretches on Utility.

### October 22, 2026 — Adaptive QoS at the 40 cap (iPhone)

`22 October 2026/nfsmw_run_8_iphone.log` (IPA46 or 45 with Extra Args showing
`adaptive on`, 1x + MetalFX "to the screen", cap 40, 23:24:39-23:26:25): one
boost at 23:24:41 (1 s after start, during loading; hold 40 s), `back to Utility`
at 23:25:21, then no further boost to the end (~64 s on Utility in the race).
FPS summaries after loading: 39.0, 40.0, 39.6, 40.0, 40.0, 39.9 and 40.0 x8.
`[cpu]` median 110%. Short run; no power data. Measured: at the 40 cap the iPhone's
main/GPU threads held the cap on Utility. Half-precision shader work put at the
top of the backlog at Stefan's request.

### October 22, 2026 — Guest-thread Utility default on all devices (IPA47)

Stefan asked why `--ios_utility_qos_guest=true` is not the default on the
iPhone after using it since Oct 21. It was default on only with >= 6 E cores
because, unlike adaptive QoS, it does not back off when frames are late. Every
iPhone run with it (Oct 21 run_3/4, Oct 22 runs 1-8) held 60 at 1x (and 40 at the
40 cap). IPA47 makes it default on for every device (Extra Args can still turn it
off); power effect on the iPhone still unmeasured; older 4-E-core chips (A15, M1)
untested. Last log's `[cpu]` lines (run_8, cap 40, 10 s windows): 15, 22, 34, 71%
during loading/menus, then 110, 128, 128, 131, 136, 120% in the race (GPU Commands
22-29%, Main XThread 18-26%, XThread1000B 17-20%, XThread10423 11-16%). CPU-time
percent is higher on efficiency cores for the same work and is not an energy
measure. IPA47 `ios/build/NFSMW-battery-guest-utility-default-47.ipa`, SHA256
`4abe8f7a501e49c59c2baea2f679a329f7baf9d855395ef53f4d541f14007e57`, NFSMW UUID
`E67B131A-6620-3978-8D16-AB741FA96B32`; 104 metallibs; zip/codesign OK.

### October 22, 2026 — IPA47 no-Extra-Args iPhone run (cap 40, MetalFX lighter)

`22 October 2026/nfsmw_run_9_iphone.log` (23:31:41-23:33:3x): defaults confirmed
(`4 efficiency cores; main/GPU threads off, other guest threads on, adaptive on
(default)`, `[gpr-helpers] ... on`); 1x, MetalFX "lower", cap 40. Adaptive: boost
at 23:31:42 (loading, 40 s), Utility at 23:32:22, boost again at 23:32:27 after 5 s
(80 s hold), i.e. most of this race at full speed. FPS summaries: 40.0, 37.8
(23:32:08, during the first full-speed hold, so not caused by Utility), then
39.7-40.0. Hitches: 37.1 and 38.9 ms encodes, a 62.7 ms swap gap at 23:32:59
(2,070 draws), two 49.2 ms GPU frames at 23:33:32. `[cpu]` race windows 84-114%
(run_8, MetalFX "to the screen": 110-136%). Late summaries: GPU 20.7-23.3 ms/frame
at a 25 ms budget (may reflect lowered GPU clocks with slack; not a saturation
proof). No FATAL. Inference: at cap 40 the iPhone is near its GPU budget in some
scenes, so a heavy moment late-frames even at full CPU speed; half-precision
shaders (top of backlog) target exactly this.

### October 24, 2026 — iPhone pursuit trace: Utility guest workers stall the frame (IPA48)

Inputs (local, not tracked): `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/24 October 2026/game_performance.trace`
(Instruments Game Performance, windowed, wired, two 60 s runs) and
`nfsmw_iphone_traces_a_b.log`. iPhone 17 Pro Max (A19 Pro, 2 P + 4 E), iOS 27.0.1,
IPA46 in LiveContainer, default settings, 1x, cap 40, Low Power Mode off.
Run 1 "Trace A" (16:13:56, normal driving) and run 2 = Trace B (16:20:10, police
pursuit). Windowed mode kept CPU samples only for the last ~7.2 s of A and
~10.6 s of B; drawable signposts cover more. Symbols resolved without dSYMs
(host code named, guest code as `__imp__sub_XXXXXXXX`). Exported with
`xcrun xctrace export` and parsed with throwaway scripts (not kept).

Measured:
- Pacing (CAMetalLayer ClientDrawable end to end, last 10 s): A 40.0 fps, 391 of
  422 intervals 20-29 ms, p50 25.0, p99 33 ms. B 22 fps in a strict two-step:
  ~20 ms then 72-90 ms, repeating; 104 of 232 intervals over 60 ms.
- GPU busy per frame: A p50 7.6 ms (p99 12.0); B p50 15.5 ms (p99 20.2). Under the
  25 ms budget in both.
- CPU per presented frame, A -> B: Main XThread 5.5 -> 13.9 ms (all in the game
  main loop `sub_82441B60`; self time diffuse, top `sub_82699100` 13% / 4.5%);
  XThreadDF1B (entry `sub_8284FE40`) 3.8 -> 13.4 ms, diffuse self time
  (`sub_8243E670`, `sub_8243E1F0`, `sub_824C26E8`, `sub_824542C0` 2-3% each);
  XThread9633 1.8 -> 4.0 ms; GPU Commands 5.9 -> 4.8 ms (`Record()` 29-32% and
  `Fingerprint()` 3-6% of the thread under `NativeDraw`/`CpDraw`); render-queue
  workers (`RenderFrame` + AGX encode) ~10 -> ~19 ms over 6+ dispatch threads;
  TimerQueue 1.5 -> 52 ms/s. No thread above ~30% of a core in B.
- Core placement (time-profile samples): in A every hot thread on cores 0-3. In B
  Main XThread and GPU Commands ~95% on cores 4-5 (log: adaptive QoS User Initiated
  from 16:20:51 for 80 s), XThreadDF1B 100% and XThread9633 ~100% on 0-3.
- Thread states in B's >60 ms gaps (8.7 s of wall): XThreadDF1B Preempted 69%,
  Running 20% (Utility pri 20); XThread9633 Preempted 64%; render workers
  Preempted 59% summed over workers (11% in normal frames); Main XThread Blocked
  62%, Running 30%; GPU Commands Blocked 83%. In A preemption was 1-4% for the
  same threads. Main XThread made runnable by idle ~24,000 times in 10.6 s in B
  (~2,300/s) vs ~3,000 in 7.2 s in A. Recorded preempters were mostly wired
  tracing daemons (AppleT8150USBXDCI, remotepairingdeviced, DTServiceHub) and
  AppleCLPC, small totals. iOS thermal state nominal.

Inference (not proven): adaptive QoS raises only main and GPU Commands to User
Initiated; the guest workers they depend on stay at Utility on the E cluster and
are descheduled, while main waits in a short poll/timed wait (the wake rate and
TimerQueue growth fit this). Draw count and GPU time grow in B but do not set the
pace. The trace has no waiting-thread stacks, so the exact wait site is unknown.

Change (IPA48): `--ios_adaptive_qos_workers` (default true; only acts when
adaptive QoS is on). When adaptive switches to User Initiated, the GPU command
thread starts a `pthread_override_qos_class_start_np` User Initiated override on
every thread named `XThread...` (the guest threads `--ios_utility_qos_guest` puts
at Utility; Main XThread follows the mode itself) and ends them on the way back
to Utility. While raised, each frame goes to the native render queue as a
`DISPATCH_BLOCK_ENFORCE_QOS_CLASS` User Initiated block. Log: `[adaptive-qos] on:
... guest workers and render queue follow the mode` and `[adaptive-qos] N guest
threads and the render queue raised`. Files: `ios/src/adaptive_qos.cpp`,
`ios/src/native_renderer.mm`. Built only; not run on a device. Checked: build
succeeded, 208 metallibs (as IPA47), ZIP OK, ad-hoc signature, cvar string present.
IPA48 `ios/build/NFSMW-adaptive-qos-workers-48.ipa`, SHA256
`ca452c544695d62a40f51b20488a37fb0e50fad79e1bb46d5cd72fe66efadfd5`, NFSMW UUID
`0107077C-F537-3823-8DD3-F6DD482419EA`. Not proven: that the stall goes away,
or the battery cost of raising the workers during holds.

### October 24, 2026 — IPA48 iPhone pursuit result; audio crackle evidence

`24 October 2026/nfsmw_ipa48_chase_iphone.log`, 16:43:54-16:54:47 (10.9 min),
iPhone 17 Pro Max, IPA48, AirPods. Log: `[utility-qos] 4 efficiency cores;
main/GPU threads off, other guest threads on, adaptive on (default)` (no Extra
Args override reported), energy baseline `scale 1.000, MetalFX off, FXAA off,
forced MSAA 0, cap 40`. Low Power Mode and thermal state are not in the log
(Stefan's test plan: Low Power Mode off).

Pursuit, measured:
- Frame counter 5101 (16:46:07.085) -> 17701 (16:51:22.502): 12,600 frames in
  315.4 s = 39.95 fps. Draws per frame (sampled lines from 16:46) 1,803-4,812,
  median 3,104, higher than the morning trace's 2,200-3,300.
- `[adaptive-qos]`: holds of 40/20/20/20/40/80 s from 16:43:56; each followed by
  `10 guest threads and the render queue raised`. From 16:48:36 on, an 80 s hold.
- Hitches from 16:46: 7 swap gaps of 41.1, 41.3, 55.5, 71.5, 76.9, 103.7, 107.4 ms
  and one 41.0 ms encode (16:54:41). The morning IPA46 trace B had a >60 ms gap
  on nearly every other frame.
- `[cpu]` in the pursuit 207-314% of a core per 10 s (IPA46 morning: 153-191%);
  XThreadE40B and XThreadE643 at 50-76% each, Main XThread 19-31%, GPU Commands
  12-32%. More CPU time per second is expected with the workers on the P cores
  and twice the frames; not an energy measure on its own.
- Battery (Stefan): 72% -> 66% over the run, about 33 %/h (6 points in 0.18 h;
  with a +-1 point reading error 28-39 %/h). Not comparable with the Instruments
  model drain estimates used for the iPad pairs.

Audio, measured (AirPods; `[coreaudio] session: 48000 Hz, IO buffer 5.3 ms, 2
output channels`):
- 5 s `[coreaudio]` summaries: 0 gaps, 0 permits refused and 0 blocks dropped in
  every window; 52 blocks trimmed only in the first window (startup). Ring minimum
  12 blocks while driving calmly, 10-11 in the pursuit, lowest 8 (16:48:59, longest
  wait between blocks 27.7 ms). The longest wait rose from ~6.5 ms to 10-17 ms in
  the pursuit. No underrun.
- Limiter: 0% of samples turned down until 16:46:09; in the pursuit 6-100% of
  samples per 5 s window (100% at 16:54:25 and 16:54:30), deepest -6.6 dB.
  `coreaudio_driver.mm` uses an instant-attack limiter (gain set to the
  ceiling/peak on the same sample, ~100 ms release) with no look-ahead.
- `[xma-resets]` (streams that ran out of input with output pending, decoded
  blocks dropped): 46-336 resets per minute before the pursuit, 6,600-12,400 per
  minute during it (~200/s, about 20 decoded blocks dropped per reset).
- 60 `sudden drop: block peak -140.0 dB after -12 to -18 dB` lines, mostly
  16:45-16:47 (2 / 6 / 32 / 20 per minute).
- Engine sound: nothing in this log stands out (Stefan saw the fade on IPA47, no
  timestamp). Five `CAR_*_ENG_*.abk` / `CAR_TRANNY.abk` / `CAR_WHINE_00.abk` open
  failures (0xc000000f) at load are present; not checked whether they also occur
  in logs without the fade.

Inference (not proven): the crackles are not output underruns. Two candidates
line up with the pursuit: (1) the instant-attack limiter working hard (hard gain
steps on loud transients such as sirens plus radio chatter), and (2) XMA streams
being reset with decoded output thrown away about 200 times a second, which cuts
streamed sounds such as police radio mid-waveform. Neither is tied to the
adaptive QoS transitions (holds started at 16:45:58, 16:47:04, 16:47:35, 16:47:56,
16:48:36; the limiter and reset rates stay high throughout the 80 s hold).

### October 24, 2026 — IPA48 iPhone Low Power Mode run (1x/40, pursuit)

`24 October 2026/nfsmw_ipa48_battery_test_iphone.log`, 17:02:44-17:13:05 (10.35
min), iPhone 17 Pro Max, IPA48, Low Power Mode on (Stefan; the log does not record
it or the thermal state), no Extra Args, energy baseline `scale 1.000, MetalFX
off, FXAA off, forced MSAA 0, cap 40`, heavy police pursuit. Compared with the
same day's normal-mode run (`nfsmw_ipa48_chase_iphone.log`, entry above).

Measured:
- Battery (Stefan): 66% at 17:03 -> 63% at 17:13. 3 points in 0.1725 h = 17.4 %/h;
  with +-1 point 11.6-23.2 %/h. Normal mode: 33 %/h (28-39). The ranges do not
  overlap; about half the drain. Single runs each, different pursuit content.
- Frames 2101 (17:03:44.924) -> 23701 (17:12:52.673): 21,600 in 547.7 s = 39.43 fps
  (normal mode 39.95). Stefan: fps "99% the same".
- Hitches: 111 (normal mode 46), of which 51 in the first two minutes (loading;
  the 100-809 ms ones there decode textures). Gameplay from 17:05: 1-16 per
  minute, mostly 40-60 ms (one missed frame at the 40 cap); largest 95.7 ms. Normal
  mode had 8 from the start of the pursuit.
- GPU ms per frame (native summaries): median 9.4, max 15.1 (normal mode median
  12.6, max 16.5); scene-dependent, not a clock measurement.
- `[cpu]` in gameplay 110-265% of a core per 10 s, around 200% typical (normal
  mode 207-314%, around 280%). CPU-time percent rises at lower clocks for the
  same work, so this is not an energy figure.
- `[adaptive-qos]`: 5 User Initiated holds (40 s, then 80 s from 17:03:29, 160 s
  from 17:04:50, 160 s from 17:08:20, 160 s from 17:11:01), each `10 guest threads
  and the render queue raised`. Most of the run was on User Initiated, as in
  normal mode.
- Audio: 0 gaps and 0 dropped blocks in every 5 s window; ring minimum 9.

Inference (not proven): Low Power Mode caps CPU (and likely GPU) clocks and trims
background work. Energy per unit of work falls steeply at lower voltage and
frequency, and at the 40 cap our frame work still fits: only ~1.3% fps and a few
extra single late frames were lost. So in normal mode, the clocks iOS picks for
our User Initiated threads are well above what 40 fps needs. We cannot set clocks
directly; the levers are QoS class, how long holds last and how the work is
spread across threads.

### October 24, 2026 — Correction: the logs record Low Power Mode and thermal state

The two IPA48 entries above say the logs do not record Low Power Mode or thermal
state. They do, in every `[memory]` line (`thermal state ...`, plus `, Low Power
Mode on` when on). `nfsmw_ipa48_battery_test_iphone.log`: Low Power Mode on in all
146 lines, thermal nominal throughout. `nfsmw_ipa48_chase_iphone.log`: Low Power
Mode off; nominal until 16:52:52, then fair to the end (about the last 2 minutes).
`[cpu]` battery (UIDevice, 5% steps): chase 70% at 16:44:04, 65% from 16:52:44;
Low Power Mode run 65% throughout. The normal-mode run therefore also ended warmer;
its drain is not inflated by Low Power Mode differences but the thermal states
differ for the last ~2 minutes.

### October 24, 2026 — Tunable adaptive boost (IPA49)

Stefan approved the lower-clock experiment from the Low Power Mode result. Change
(`ios/src/adaptive_qos.cpp`, `native_renderer.mm`, `memory_report.mm`):
- `--ios_adaptive_qos_level` = `default` (new default) or `user_initiated`: the QoS
  class of a boost, for main, GPU Commands, the raised guest threads (override) and
  the render-queue frame blocks.
- `--ios_adaptive_qos_max_hold` = 20 (new default; 5-240 s): the longest hold. The
  20 s start and the doubling stay; IPA48 grew to 240 s.
- `--ios_adaptive_qos_workers_count` = 3 (new default; 0 = all): at each boost the
  guest threads (`XThread...`) are ranked by CPU time since the previous boost
  (`thread_info`) and only the busiest N get the override. The pursuit logs show
  two guest threads at 50-76% of a core and one at ~20%; the rest are small.
- `--ios_adaptive_qos_ipa48=true`: user_initiated, 240 s, all guest threads (IPA48).
- Startup log: `[adaptive-qos] boost: Default QoS, holds up to 20 s, the 3 busiest
  guest threads`; boosts log `[adaptive-qos] Default for N s (...)`.
- `[cpu]` lines end with `battery N%, Low Power Mode on|off, thermal <state>`.
Why Default: it is the class between Utility and User Initiated; whether iOS
picks lower clocks for it on the iPhone is what the run tests (inference only).
Risk: shorter holds mean more boosts and more late frames when a pursuit needs the
speed; Default may not leave the efficiency cores enough.
Checks: build OK, 208 metallibs, ZIP OK, the four cvar names present. IPA49
`ios/build/NFSMW-adaptive-qos-tunable-49.ipa`, SHA256
`152861503300d87504c50c2d9191b588424ce8fe9e9773afa7866917d3b85551`, NFSMW UUID
`A14E11CE-3C31-34FB-9808-5B4E615141DA`. Not run on a device.

### October 24, 2026 — IPA49 run A: gentler boost, drain, audio stutters

`24 October 2026/nfsmw_ipa49_battery_test.log`, 17:22:19-17:33:04, iPhone 17 Pro
Max, IPA49, no Extra Args, `[cpu]`: Low Power Mode off, thermal nominal until
17:32:59, then fair. Startup: `boost: Default QoS, holds up to 20 s, the 3 busiest
guest threads`. Stefan: 61% at 17:23, 56% at 17:33; noticeably hotter than IPA48 in
Low Power Mode; close to locked 40; engine sound fade around 17:27; heavy audio
stutters in the last ~2 minutes.

Measured:
- Drain: 5 points in ~0.167 h = ~30 %/h (24-37 with +-1 point). IPA48 normal 33
  (28-39), IPA48 Low Power Mode 17 (12-23). No measurable saving.
- Frames 2101 (17:23:20.577) -> 23701 (17:32:22.893): 39.83 fps. Hitches 87, of
  which 58 in the first minute (loading); 1-8 per minute after.
- `[adaptive-qos]`: 15 boosts, each 20 s (the cap), 1-118 s on Utility between
  them; 3 guest threads + render queue raised each time. About half the run was
  boosted.
- `[cpu]` in gameplay 65-214% of a core, ~150% typical (IPA48 normal ~280%, Low
  Power Mode ~200%). Less CPU time than IPA48 normal mode for the same drain.
- Display: `cap 40: guest vblank locked to the display refresh (8.33 ms)`; native
  pacing lines show 120 Hz refresh gaps of mostly 3 (40 fps on 120 Hz) in normal
  mode, and gaps of 2 and 4 (a 60 Hz display) in the Low Power Mode run.
  `display_rate.mm` asks for 80-120 Hz at the 40 cap.
- Audio output: 0 gaps, 0 dropped, ring minimum 11-12 blocks in every window,
  including 17:31-17:33. Limiter 0-94% per window. The `sudden drop` lines stop
  after 60 per run (all three logs have exactly 60); use the per-5 s `sudden drops`
  counts: run totals 109 (IPA49), 99 (IPA48 normal), 167 (IPA48 Low Power Mode).
  IPA49 clusters: 17:32:05 (11), 17:32:10 (19), 17:32:40 (39), with peaks right
  before the drop at -0.2 to -7 dB, one every ~100 ms at 17:32:03-17:32:07. They
  happened both on Utility and during a boost (boost started 17:32:07.6 and
  17:32:40.7).
- 17:27 engine fade window: XMA resets peaked at 17:27:21 (556 on 116 contexts in
  one second; run maximum 585); XMA decode time (`[xma-work]`) then fell from
  60-100 ms/s to 15-26 ms/s for ~40 s (17:27:22-17:28:05) before recovering.
  17:27:20 window: 18 silent blocks from the game, longest run 75 ms. No failed
  file opens near 17:27.

Inference: (1) Lower QoS cut CPU time but not drain, so Low Power Mode's saving is
not CPU scheduling; likely the CPU/GPU clock caps plus the 60 Hz display, which
our QoS cannot reach. The display rate is the one lever we control. (2) The
stutters are game-side: the game's mix delivers isolated silent 5-11 ms blocks
after loud ones, while output never runs dry. Probably XMA voices whose streams run
dry and get reset (decoded output dropped). They are not tied to QoS changes and
occur in every mode, most in Low Power Mode. Medium confidence. (3) The 17:27
engine fade lines up with the largest burst of XMA resets and a drop in decode
work, consistent with many voices (the engine banks) being reset at once. Low to
medium confidence; one occurrence.

### October 24, 2026 — Display at the cap's rate; XMA stream log (IPA50)

Stefan approved the display-rate test and asked for it at every cap. Change:
- `ios/src/display_rate.mm`: `--ios_display_match_cap` (default true). At the 30,
  40 and 60 caps the CADisplayLink asks for `CAFrameRateRangeMake(cap, cap, cap)`;
  otherwise (false, or the 120 cap) the old ranges (80-120 at 40/120, 30-60
  otherwise). The guest vblank lock in the GPU plugin needs a display period within
  10% of its interval (60 Hz at the 30 cap, 120 Hz at 40): each tick now publishes
  the refresh's time with the period divided by round(period x guest rate) (3 at
  40 Hz, 2 at 30 Hz, 1 otherwise), so the lock extrapolates evenly spaced guest
  vblanks on the display's phase. No SDK change for this.
- Log: `[display] cap N fps: asking for N Hz, the cap's rate (...)` at start and on
  each request; `[display] refresh now N Hz (asked N Hz, cap N)` when the rate iOS
  gives changes (stable for 30 refreshes, max 40 lines).
- `ios/src/battery.mm`: when Battery mode moves the cap (60 <-> 30, warm or menus)
  and the switch is on, the display rate is requested again (main queue).
- Audio diagnostics, no behaviour change: SDK patch
  `tools/ios/patch_ios_xma_voice_log.py` (added to `prepare_sdk.py` after the reset
  stats; applied to `../rexglue-sdk-ios/src/audio/xma_context.cpp`). Every 5 s:
  `[xma-voices] 5 s: F streams fed, R reset (N resets, B bursts of 300+/s), S
  stopped after a reset: id(windows fed x5s,input buffer address) ...` (up to 12
  ids, longest-fed first; 2,000 lines max). A fade should show as long-fed
  contexts stopping together. The bank behind an address is not resolved yet.
Risks: 30/40 Hz may make pacing or input feel different; a frame that misses a
refresh at 30 Hz waits 33 ms; iOS may not grant 40 Hz (the `refresh now` line
shows it). Checks: build OK, 208 metallibs, ZIP OK, both new log strings present
(NFSMW and librexruntime). IPA50 `ios/build/NFSMW-display-match-cap-50.ipa`,
SHA256 `43fb543badf5ad8d7507e97a3330faa811eb5adca2469a4445d7181900e08205`, NFSMW
UUID `A5BF2569-4D0E-3E79-8F9D-64F20FF4C300`. Not run on a device.

### October 24, 2026 — IPA50 run: display at the cap's rate, no saving

`24 October 2026/nfsmw_ipa50_battery_test.log`, 17:45:15-17:55:32, iPhone 17 Pro
Max, IPA50, no Extra Args, Low Power Mode off (`[cpu]`), thermal nominal until
17:54:06, then fair. Stefan: 54% at 17:45 -> 49% at 17:55, as warm as IPA49 and much
warmer than Low Power Mode; audio stutters from 17:52.

Measured:
- Drain ~30 %/h (24-37 with +-1 point), the same as IPA49 (~30) and IPA48 (~33);
  Low Power Mode ~17.
- Display: `cap 40 fps: asking for 40 Hz, the cap's rate`; `[ios-vblank] cap 40:
  guest vblank locked to the display refresh (8.33 ms)`; then `[display] refresh
  now 30 Hz (asked 40 Hz, cap 40)` (the CADisplayLink's period was 33.3 ms). Pacing
  lines: gaps in 120 Hz refreshes 2:~148 4:~152 per 300 frames, the same pattern as
  the Low Power Mode run (a 60 Hz panel, 40 fps alternating 16.7/33.3 ms), versus
  mostly 3 in IPA49. So iOS did not grant 40 Hz; the presentation matched Low
  Power Mode's.
- Frames 301 (17:45:28.310) -> 24301 (17:55:31.568): 39.78 fps. Hitches 67.
- GPU ms per frame (native summaries): median 12.9, max 18.2 (IPA49 12.3/18.1; Low
  Power Mode 9.4/15.1). `[cpu]` median 149% of a core (IPA49 142%, Low Power Mode
  198%).
- `[xma-voices]` (new): all 256 contexts fed in most windows. 17:51:17-17:52:07
  ~700-1,000 resets per 5 s; from 17:52:17 to 17:54:47 1,100-2,270 per 5 s with 1-5
  bursts of 300+/s (17:52:52 2,269 resets, 5 bursts). Silent-block clusters at
  17:52:56, 17:53:36, 17:54:36-17:54:51 (86 silent blocks, longest run 235 ms) and
  17:55:11. Output path: 0 gaps, ring 12 throughout. The big "stopped after a
  reset" lists (17:50:37, 127; 17:51:42, 100, with 299 silent blocks and a 1,259
  ms run) look like scene changes, not single voices.
- Input buffer addresses are per context (0x0A28C000 + id x 0x1000), so they are
  each voice's own ring, not bank addresses: they cannot identify the engine
  streams. Stefan did not report an engine fade in this run.

Inference: (1) The display rate is not Low Power Mode's saving either: same
presentation, same drain as IPA49. Left: Low Power Mode's CPU (and maybe GPU)
clock caps. More CPU time per second at lower clocks fits that. The levers left
are less work per frame, or recommending Low Power Mode. (2) Stutters again
coincide with the XMA reset rate roughly doubling, with the output healthy;
medium confidence that the reset path (streams run dry and dropped) is the cause.

### October 24, 2026 — IPA51 test baseline

Stefan approved a baseline build for profiling and held 0.4.0 (not enough beyond
battery tweaks). Defaults changed: `ios_display_match_cap` false (IPA50 gave no
saving); `ios_adaptive_qos_level` user_initiated, `ios_adaptive_qos_max_hold` 240,
`ios_adaptive_qos_workers_count` 0 (IPA48's boost, proven in pursuits; IPA49's
Default / 20 s / 3 saved nothing). `[xma-voices]` and the `[cpu]` Low Power Mode /
thermal fields stay. Expected startup lines: `[display] cap 40 fps: asking for 120
Hz`, `[adaptive-qos] boost: User Initiated QoS, holds up to 240 s, all guest
threads`. Checks: build OK, 208 metallibs, ZIP OK. IPA51
`ios/build/NFSMW-baseline-51.ipa`, SHA256
`e57392a8143ef4a703bb13b7e961817e97376271a7fab79e62bcc4e9df20d667`, NFSMW UUID
`A954195D-C945-38B7-A6E2-A663B55A1524`. Not run on a device.

### October 24, 2026 (evening) — IPA51 iPhone traces: power, main-thread polling

Recorded by Claude with `xctrace record` because attaching to LiveContainer from
the command line failed ("Cannot find process" by name and by devicectl PID); from
now on Stefan records in the Instruments app (working rules).
- First GUI Power Profiler run (with CPU Counters) crashed Instruments 27.1 in
  analysis (`CoreTypeDistributionCalculator.receive`, EXC_BREAKPOINT; report
  `~/Library/Logs/DiagnosticReports/Instruments-2026-10-24-195534.ips`). Its raw
  ktrace imported (`24 October 2026/recovery/ipa51_power_lpm_off.trace`, 136.9 s)
  but holds no power tables (those come from the device at save time); it did
  show the hot game threads 54-82% on P cores 4-5.
- `24 October 2026/ipa51_power_lpm_off.trace` (whole phone, Power Profiler +
  Thermal State + Display instruments; the template refuses all-processes):
  SystemPowerLevel 162 samples; race part (~110 s) 42.5 %/h estimated (p10/p50/p90
  40/42/45), brightness 32%, thermal nominal -> fair at 1:19. Instruments' model;
  not comparable with battery-% figures. Saving took ~25 min over Wi-Fi.
- Low Power Mode arm: the device disconnected after 2.3 s, twice. Low Power Mode
  appears to drop the wireless profiling link; needs the cable.
- `24 October 2026/ipa51_waiting_pursuit.trace` (System Trace, whole phone,
  90.9 s, 6.8 GB; 13 GB raw): syscall table, LiveContainer threads.
  - Main XThread: 64,306 `sys_ulock_wait2` (709/s, 70.6 s total, ~1.1 ms each), all
    on one address; call sites `sub_82593A58` (13,309), `sub_825A2968` <
    `sub_825A3EC8` (7,784), a `sub_825A27F0` chain (2,589), many unsymbolized.
    Only 9,358 wakes of that address, all from GPU Commands
    (`CommandProcessor::WorkerThreadMain`): most waits end by timeout, i.e. the
    main thread polls the command processor's progress. Plus 21,374
    `mach_wait_until` (236/s) from the main loop `sub_82441B60`, ~0.14 ms each.
  - GPU Commands: 82,373 `swtch_pri` (908/s) from `rex::thread::MaybeYield()` in
    `WorkerThreadMain` (spinning for ring-buffer work), and 12,746
    `sys_ulock_wait2` (141/s, 71.6 s) in `ExecutePacketType3`, woken only by GPU
    VSync (10,858): the vblank-paced wait at the 40 cap.
Inference: the main thread's wait in `sub_82593A58` / `sub_825A3EC8` is a
short-timeout poll on GPU command progress (probably a fence or ring read
pointer), and the CP thread spins with yields while idle. Proposals (not approved):
(1) find the host wait behind those guest calls and wake it exactly when the CP
writes the awaited value, with a longer timeout; (2) replace the `MaybeYield` spin
in `WorkerThreadMain` with a blocking wait on the ring write pointer. Expected:
far fewer wakeups (P cores can idle); energy effect unmeasured.

### October 24, 2026 — IPA52: fewer wakeups in the ring-space wait and CP idle

Where the pursuit trace's waits come from (generated code, USA edition):
`sub_82593A58` is D3D DrawIndexedVertices; it and `sub_825A3EC8` reach the
ring-space loops (`sub_82597070` -> ... -> `sub_82597498`), which call the watchdog
`sub_825A5B20` (PAL `sub_825A5D18`), hooked in `ios/src/game_hooks.cpp`: when the
CP read pointer has not moved it sleeps on `nfsmw_cp_rptr_seq`
(os_sync_wait_on_address_with_timeout), capped at 1 ms. The CP bumps and wakes
that counter after every primary buffer and on mid-stream publishes. So the main
thread's 709 waits/s are real waits for ring space while the CP sits in its
vblank wait (its own 141 waits/s woken by GPU VSync); ~600/s of them were just the
1 ms cap expiring. The GPU Commands yields come from `WorkerThreadMain`'s idle
loop: 64 `MaybeYield` (sched_yield) laps before the 5 ms event wait; the event is
set on every CP_RB_WPTR write.

Change:
- `ios/src/game_hooks.cpp`: `--ios_ring_wait_ms` (default 8, 1-50; 1 = before).
  Logs `[ring-wait] 10 s: N waits for ring space, M timed out (8 ms cap)`.
- SDK patch `tools/ios/patch_ios_cp_idle_wait.py` (in `prepare_sdk.py`, applied):
  `--ios_cp_idle_spins` (default 4; 64 = before); no yield on laps that wait.
  Logs `[cp-idle] 10 s: N idle stalls, Y yields, W event waits`.
- Left alone: the main loop's ~236/s `mach_wait_until` (~0.14 ms, from
  `sub_82441B60`): that is the game's own timing and changing it could alter
  pacing.
Risks: a missed counter bump would cost up to 8 ms of ring wait (a hitch) instead
of 1 ms; the publish points make that unlikely. Fewer CP yields add a little
latency only when new work arrives within the first few laps (the event then
wakes the thread). Expected: hundreds fewer wakeups a second on the P cores;
energy effect unmeasured. Checks: build OK, 208 metallibs, ZIP OK, `ring-wait`
in NFSMW and `cp-idle` in librexgpu-xenos. IPA52
`ios/build/NFSMW-wait-fixes-52.ipa`, SHA256
`95f6c2ba2087b9e428d337a1cd033c35df8587487370aea471cf98f9b8822144`, NFSMW UUID
`AE1010F1-4FC9-35F6-9A01-C0946DF82931`. Not run on a device.

### October 24, 2026 (night) — IPA52 iPhone police chase: first clear saving

`24 October 2026/nfsmw_ipa52_police_chase.log` (several launches 19:44-23:21; the
measured run is the last, 23:11-23:21). `[cpu]`: Low Power Mode off, thermal
nominal in every line of that run; energy baseline `scale 1.000, MetalFX off,
FXAA off, forced MSAA 0, cap 40`. Stefan: 79% at 23:11 -> 75% at 23:22, police
chase, "this was finally it", the phone heats less than in the old 10-minute Low
Power Mode runs.
- Drain: 4 points in 0.183 h = ~22 %/h (16-27 with +-1 point). IPA51 ~30 (24-36),
  IPA48 ~33 (28-39), IPA48 Low Power Mode ~17 (12-23). One run; battery at 75-79%.
- Frames 1501 (23:11:01.326) -> 26401 (23:21:24.468): 39.96 fps. 6 hitches (largest
  47.7, 50.4, 109.7 ms). GPU median 12.2 ms. `[cpu]` median 127% of a core (IPA51
  ~145%, IPA48 ~280%).
- `[ring-wait]` (64 x 10 s): 66,566 waits (104/s, trace before: 709/s), 44,755 timed
  out at 8 ms (70/s, before ~600/s at 1 ms).
- `[cp-idle]` (64 x 10 s): 104,706 yields (164/s, trace before: 908/s), 37,842 event
  waits.
Inference: the drop in wakeups lets the P cores (and likely the GPU driver
thread) idle between frames; that, on top of the earlier QoS and renderer work,
is the first change that moves the battery-% drain toward Low Power Mode without
its clock caps. Still 70 ring-wait timeouts/s: the 8 ms cap expiring during the
40 fps vblank pause (a frame-relative cap would remove most).

### October 24, 2026 (night) — IPA53: frame-relative ring wait, faster index fingerprint

- `ios/src/game_hooks.cpp`: `--ios_ring_wait_ms` default 0 = half a frame of the
  current `ios_fps_cap` (read per wait, so Battery mode's 30 gives 16.7 ms;
  uncapped counts as 120); a value above 0 is a fixed cap in ms (IPA52 = 8, older
  = 1). IPA52 still had 70 timeouts/s at 8 ms in the 40 fps pursuit. The
  `[ring-wait]` line now shows the cap in use.
- `ios/src/native_renderer.mm` `IndexFingerprint`: for index ranges up to 4 KB
  (most draws), every 8-byte word went through one FNV chain: up to 512 dependent
  multiplies per draw, ~3,000 draws a frame in pursuits; it is inlined into
  `Record()`, so part of `Record()`'s self time (~15-19% of GPU Commands in the
  Oct 24 trace) and `Fingerprint` (~3-6%) is this. With
  `--nfsmw_native_fast_index_fingerprint` (default true) four chains run over
  32-byte blocks and are folded at the end; the remaining words go through the
  old chain. Same input coverage, different values; the values are used only for
  this session's index cache (not persisted), so no visual change is expected.
- Not changed: the rest of `Record()`. A line-level profile is needed to pick
  the next target (the build keeps line tables; Stefan's Time Profiler trace
  attached to LiveContainer would do).
Risks: a collision in the new hash would reuse a stale index buffer (same risk
class as before); the half-frame cap at 30 fps is 16.7 ms (only on a missed
wake). Checks: build OK, 208 metallibs, ZIP OK, both new strings present. IPA53
`ios/build/NFSMW-frame-wait-encode-53.ipa`, SHA256
`c08433ff248cba276584a44eaf8605135342e34ee045a959d138b2ae2d4076e5`, NFSMW UUID
`4AECB5A4-A7C1-3162-8D46-5180E300A7EF`. Not run on a device.

### October 24, 2026 (night) — IPA53 iPhone police chase: drain not repeated

`24 October 2026/nfsmw_ipa53_police_chase.log`, 23:35:11-23:45:16, Low Power Mode
off, thermal nominal in every `[cpu]` line, cap 40. Stefan: 74/73% at 23:35-23:36
-> 68% at 23:45 (~30-40 %/h depending on the start reading), "seems worse, much
hotter" than IPA52. The 7th launch of the evening, ~13 min after the IPA52 run.
Measured, against IPA52 (23:11-23:21):
- Frames 301 -> 24001 in 593.2 s = 39.95 fps (IPA52 39.96). Hitches 31, all but 2
  in the first ~90 s of loading (IPA52: 6). Draws median 3,156. GPU median 11.1 ms
  (IPA52 12.2).
- `[cpu]` in play 67-177% of a core, ~100% typical (IPA52 ~127%).
- `[ring-wait]` (cap 12.5 ms, half a frame): 47,167 waits (79/s), 22,895 timeouts
  (38/s) (IPA52: 104/s, 70/s at 8 ms). `[cp-idle]`: 98,737 yields (165/s), as IPA52.
- Adaptive QoS: same behaviour (User Initiated holds, all guest threads).
Inference: every in-game counter is equal or better than IPA52 (less CPU, fewer
wakeups), so neither IPA53 change explains a higher drain; more likely the run
conditions (phone and battery already warm from back-to-back runs, a different
chase) plus the 1-point battery readings on short runs (IPA52 16-27, IPA53 ~25-44
%/h with the reading error). Not proven either way. A fair comparison needs both
builds after a full cool-down, ideally same chase, longer than 10 min.


### October 24, 2026 (late) — Half-precision shaders: analysis of the costly pixel shaders

Read-only analysis, no code or build. Sources: the translated shaders in
`~/Library/Caches/nfsmw-ios/shaders/air/ps_<key>.metal` (the Oct 21 cost-probe
list). Body of each `shaderBody` after the register declarations:
- 4fbaecfb (shadow caster, 0.91 ms): writes a constant colour; the only fetch and
  compare are already compiled out by the IPA34 variant. No arithmetic to narrow.
- 27d82ea0 (trees, 0.90 ms): one texture fetch and three multiply-adds.
- 684f4711 (fences/plants, 0.76 ms): the shadow part (9-tap shadow fetch, depth
  bias, compares against depth in [0,1]) must stay 32-bit (half has an 11-bit
  mantissa against a 24-bit depth map: shadow acne); the colour tail is 5
  multiply-adds.
- Next tier, counted roughly (lines with arithmetic / fetches): fe510d2d 17/10,
  2d8bf2c6 5/4, d8bb87fe 47/18 (2 shadow blocks), d1f317fa 22/14 (2),
  705e150f 48/14 (2), 91404826 43/18 (2).
Inference: the probe deltas (which include vertex, raster and overdraw) come from
fill, overdraw of alpha-tested foliage and texture fetches, not pixel arithmetic.
Half precision in these shaders can only narrow a handful of colour operations
and the texture return values; on recent Apple GPUs half mainly saves registers
and interpolator storage, not ALU rate (general knowledge, not measured here).
Expected GPU saving: small, likely below the probe's noise. UVs cannot become
half (11-bit mantissa snaps texels on 1-2k textures and tiled coordinates).
Not implemented; options sent to Stefan for a decision.

### October 24, 2026 (late) — Oct 22-23 iPhone logs sent on the morning of Oct 24

Stefan's message (sent Oct 24 10:59, reached this session late) with three logs
from build "Oct 22 2026 23:29:47": `nfsmw.1_morning.log` (Oct 22 23:57 onwards;
default settings until the heat-up, then QoS off in Extra Args), `nfsmw_morning.log`
(Oct 23 10:56) and `nfsmw_night.log` (Oct 23 21:27, Battery preset + Low Power
Mode). He reported 1x/40: badly hot after ~10 min, ~32 fps, choppy; Battery preset
+ Low Power Mode: barely warm, low drain. Measured: `[memory]` lines report thermal
state nominal in every line of all three logs (595, 58 and 455 lines), including
the 147 Low Power Mode-off lines of the default session. Inference: iOS did not
raise its thermal state while the phone felt hot, so the in-game heat reactions
keyed to it would not have fired. Superseded for planning by the Oct 24 work
(Low Power Mode comparison, IPA48-53, Stefan's IPA51 traces); no new action.

### October 24, 2026 (night) — sun flicker is the occlusion answer; IPA54

Stefan, iPhone, IPA53 (`24 October 2026/nfsmw_ipa53_sun_issues.log`, 23:59-00:20).
Test 1 `--nfsmw_native_sky_last=false`: flicker unchanged. Test 2
`--nfsmw_native_occlusion=true`: no flicker, sun hidden by buildings and tunnels,
no crash in the log (it ends 00:20; the arguments are not logged); the sun was never seen in the sky in ~10 min (weather or a
low count, open). The sun stayed visible in the car's reflection (IMG_3949/3950):
the reflection does not use the query (inferred: the cube map sees the sun behind
the camera). Cause: with native counting off (`06ac2b3`, Oct 12, suspected in the
safehouse crash) the ZPD events went to the emulated Vulkan queries, whose draws
are skipped while the native renderer shows the game; the answer did not follow
the geometry and flickered. The crash was later found to be the deferred-queue
race (IPA36), so the suspicion is cleared. The sky reorder (`e046455`) skips draws
with a query and is not involved. Night log: "sky drawn last" 1 or 2 per sampled
frame (the reorder varies per frame but did not cause the flicker).

Change: `nfsmw_native_occlusion` default true; the native renderer keeps, per
query address, the answers given since the last 300-frame stats line (count,
how many 0, largest, last; 921600 = full 1280x720 before the first count) and
logs `[native] occlusion queries since the last line: ...`. IPA54
`ios/build/NFSMW-sun-occlusion-54.ipa`, SHA256
`cb18b4f439df5f2252bf2265d8d66d06e3dd13a7964cd10c88aaa0cbc37669a2`, NFSMW UUID
`78D6C91B-A711-3DF5-9BE6-6813754DD15E`; 208 metallib entries (same as IPA53);
zip test and codesign OK. Not run on a device.

Audio, same log: Low Power Mode on from ~00:11. Coreaudio output clean (0 gaps
in every 5 s line). XMA resets per minute: 00:00-00:11 between 234 and 6818,
00:12 9641, 00:13 13545, 00:14 14129, 00:15 11008, 00:16 5761. `[xma-voices]`
from 00:12: 256 streams fed, 164-242 reset per 5 s, 1-5 bursts of 300+/s, 0
stopped after a reset. Matches Stefan's "boop" at ~00:12 and the glitches with
the engine bug at ~00:15. See BACKLOG D-004.

### October 25, 2026 — IPA54 sun test: every occlusion answer is nonzero

Stefan, iPhone, IPA54 (`24 October 2026/nfsmw_ipa54_sun_test.log`, 00:32-00:34,
~1.5 min, 40 fps, MetalFX off). 12 `occlusion queries` lines: frames 1-901
(menus/loading) `none`; frames 1201-3601 (in game) 6-7 query addresses per
line (`05D81080`, `05D81340`, `05D81600`, `05D82040`, `05D82580`, `05D82B00`,
`05D82DC0`), 12-242 answers each per 300 frames, and **0 answers of 0 on every
address in every line**. Largest/last per address: `05D81600` 3.3M-7.8M,
`05D82040` 2.2M-4.5M, the others ~65k-650k (921600 in the first in-game line is
the default before the first count). So the game is never told a query is
fully hidden; the count is not too low.

Two things do not fit a one-sun-per-frame query (TECHNICAL table above, inferred):
seven addresses, not one, and counts up to 8x a full 1280x720 frame. Likely the
queries cover several flares/lights (not only the sun) and the counting sums
overlapping draws or passes (one slot per query per pass, summed; divisor =
scale² x MSAA). If the game decides sun visibility as a ratio of two queries
or against a fixed threshold, the units matter and could still hide the sun;
unverified. Which address is the sun, and how the game turns the count into
glare, is not known from the log. The log has no weather or sun markers, so
whether the sun was on screen is Stefan's observation.

### October 25, 2026 — flashing billboard; IPA55 texture change log

Stefan: the flashing is the billboard at the top left ("Get in the Zone") and
many like it, not the car. Crops of `ScreenRecording_10-25-2026 00-09-10_1.mp4`
every 0.25 s, car standing still: the billboard switches between sharp and
blurry (a lower mip or lower-resolution copy); the tree and sky stay sharp.
Seen since the Vulkan renderer (shared texture path suspected, inferred).
The native renderer ignores the fetch constant's `mip_min_level`/`lod_bias`
(sampler bias is only MetalFX's); textures are cached per full fetch constant.

Change (`nfsmw_native_texture_flip_log`, default true): per texture address,
the last bind (fetch constant, size, levels, content fingerprint) and, since
the last 300-frame stats line, how often it differed from its use in an
earlier frame. Logs `[native] textures changing between frames since the last
line: N` and the top 8 as `texture ADDR: uses, fetch changed, size/levels,
content | before -> after` (size, levels, mips min-max, bias, mip filter,
aniso, format, low 16 bits of the fingerprint). Limit: an address bound with
two fetch constants in one frame also counts as a change.
IPA55 `ios/build/NFSMW-texture-flips-55.ipa`, SHA256
`d757be2b28f4dc01b21fa2848935b175c2e3ed24423b465a92bfcee1fc5b08ff`, NFSMW UUID
`DD867111-3B2F-3716-A693-0A416DAD6AA6`; 208 metallib entries; zip test and
codesign OK. Not run on a device. Test: drive or stand near a flashing
billboard for a minute.

### October 25, 2026 — IPA55 run: the flashing billboard's textures do not change

Stefan, iPhone, IPA55 (`24 October 2026/nfsmw_ipa55_texture_flickering.log`,
00:54-00:58), the same billboard flashing towards the end. In-game lines
00:56:45-00:57:22 list 1-27 changing textures, all minor: the fetch constant
changing 1-3 times per 300 frames with identical size, mips (bias 0, aniso 0)
and content (the same address bound with two fetch constants), or content
changes of small 1-level 128x128 textures (dynamic). The last six lines
(00:57:30-00:58:07, the billboard part) show **0 textures changing**; frames
7501-9301 draw 2924-3133 draws and 410-417 textures per frame, stable.
So the billboard's texture is not rebound, resized, re-mipped or rewritten
between frames; the sharp/blurry flip comes from what is drawn, not from the
texture cache. Remaining suspects (inferred): two models/textures at
different addresses alternating (a model LOD switch, e.g. camera shake around
a LOD distance), or the sampler/derivative (anisotropy setting constant;
`anisotropic_override` is a launcher setting). Next proposal: log texture
addresses bound in one frame but not the next and back (A/B alternation).

### October 25, 2026 — billboard flicker is z-fighting; IPA56 polygon offset

Stefan: the billboard flicker is a dark grey layer over it, worse when moving,
gone from some still positions: z-fighting of an overlay pass, matching IPA55
(texture unchanged). The native renderer never applied the guest polygon
offset (PA_SU_SC_MODE_CNTL bits 11-13, PA_SU_POLY_OFFSET_* 0x2380-0x2383); its
Metal shaders also have no invariant position / fast-math control (second
suspect, needs a shader rebuild). Note: rexglue's Vulkan renderer does apply
the offset, and Stefan saw the flicker there too, so this may not be enough.

Change: `nfsmw_native_depth_bias` (default true) applies the offset as
`setDepthBias` per draw, as rexglue's GetPreferredFacePolygonOffset and Vulkan
renderer do (constant x 2^24 or 2^24-1 by RB_DEPTH_INFO's depth format, slope
/16 x resolution scale; reset per encoder). New line per 300 frames:
`[native] depth: N draws with a polygon offset (applied|ignored), M with an
equal depth test`. Removed: the IPA55 texture change log. Settings lines that
cannot change while running (upload sizing, GPU buffer selector/lookup off,
lazy diagnostics, attribute key comparison, target/pipeline lookup, resolve
compression eligibility) now print in the first summary only.
IPA56 `ios/build/NFSMW-depth-bias-56.ipa`, SHA256
`d11c2bb652b2e1c07399ebf6ab784c06599ca5bec9827c60b9df4baac4a68985`, NFSMW UUID
`F38E4682-8A98-3F34-B51C-A6CB6FC9B038`; 208 metallib entries; zip test and
codesign OK. Not run. Test: the same billboard; A/B with
`--nfsmw_native_depth_bias=false`.

### October 25, 2026 — IPA56 did not fix the billboard; IPA57 shader invariance

Stefan: IPA56 "still the same" (no log). Second suspect: the translated vertex
shaders declare `oPos [[position]] [[invariant]]`, but `build_shaders.sh`
compiled them without `-fpreserve-invariance`, so the attribute was ignored
and two passes over one surface can compute different depths (fast math).
Change: `-fpreserve-invariance` in both compile lines of
`tools/native/build_shaders.sh`; the D3D internal vertex shaders (runtime
source) get `[[invariant]]` and `preserveInvariance = YES`. All 104
`air/*.metal` in `~/Library/Caches/nfsmw-ios/shaders` recompiled into `lib/`
(old ones kept in `lib.before-invariance-ipa57/`); the IPA's metallibs match
the new ones. IPA56's polygon offset stays on.
IPA57 `ios/build/NFSMW-invariance-57.ipa`, SHA256
`e4470f5798d3d58b57e5b914b718cb60357d08556fdfdb89aef2b26ef0226678`, NFSMW UUID
`70800D84-C16E-3563-B095-F5927A4D936D`; 208 metallib entries; zip test and
codesign OK. Not run. Watch also GPU ms (invariance can cost a little).

### October 25, 2026 — IPA57 did not fix the billboard; IPA58 exact shader math

Stefan, IPA57 (`24 October 2026/nfsmw_ipa57_texture_flickering.log`): billboard
unchanged; the screen was black until the shaders were cached and in free roam
things were invisible for moments, then one big stutter (pipelines rebuilt
after the metallibs changed: once per shader change, inferred). He recalls an
early performance change that started this.
Found in the history: 0.1.0 (Oct 7, `patch_ios_shader_contraction`) dropped
the `NoContraction` (precise) arithmetic from pixel shaders for speed; its
own notes say the 360 draws geometry several times and a fused multiply-add
"would change the last bit and make it flicker". The native renderer's
XenosRecomp shaders were then always compiled with Metal's default fast math
(contraction on), vertex and pixel alike. The dark layer is likely a pass
whose result depends on bit-exact math (a depth/shadow comparison, inferred).
Change: `build_shaders.sh` compiles with `-fno-fast-math -ffp-contract=off`
instead of IPA57's `-fpreserve-invariance` (taken out, also from the D3D
internal vertex shaders); all 104 libraries rebuilt. IPA56's polygon offset
stays. Expect the one-time shader recompile again on first launch, and watch
GPU ms (exact math can cost some).
IPA58 `ios/build/NFSMW-exact-math-58.ipa`, SHA256
`19dc46a870cd371c2283e66e3f334653301e41edf665d1e8b52e798ab7fff0d7`, NFSMW UUID
`9558B802-B89B-3385-AAF0-5B792472CCF3`; 208 metallib entries; zip test and
codesign OK. Not run. If it fixes the flicker but costs too much GPU time:
exact math only for vertex shaders, or only for the shaders of that pass.

### October 25, 2026 — IPA58 did not fix the billboard either

Stefan, IPA58 (`nfsmw_ipa58_texture_flickering.log`,
`ScreenRecording_10-25-2026 01-20-21_1.mp4`): still flickers. GPU time is
unchanged by exact math or invariance (last 8 lines: IPA55 9.2-10.1 ms,
IPA57 9.3-9.7, IPA58 8.1-10.2). Crops of the new clip every 33 ms (1.0-1.4 s):
in some frames the billboard is replaced by a **darker, blurred copy** of
itself (lettering soft, colours dimmer), in others it is sharp. This looks
less like z-fighting of a decal than like a blurred post-processing layer
(the game's blur/visual-treatment composite) blended in with a weight that
changes from frame to frame (inferred). The stats show 1 resolve sampled
from an earlier frame per frame (the renderer's previous-frame copy).
Three negative results so far: polygon offset (IPA56), shader invariance
(IPA57), exact shader math (IPA58).
Stefan: the same flicker with the Vulkan renderer, so it is in shared code or
game patches, not the native renderer. He also reports glass panes looking
wrong on both renderers (IMG_3456: airport terminal, the glass shows a bright,
hard-edged rectangle of the outside; issues looking through two glass
surfaces). Suspect for both (inferred): the 19.5:9 mode. The game renders
1560x720 (resolves 1560x720, blur chain 390x180/195x90) while its
post-processing and screen-copy shaders were written for 1280x720; a
mis-scaled blurred copy or refraction copy would match "a darker blurred
copy" and the hard-edged glass. Next: the same spots with Screen shape 16:9.
Stefan, 16:9: both still present, so not the 19.5:9 mode. IMG_3953 (bus
terminal, from inside): the trees behind distant glass panes are drawn as
hard dark silhouettes on top of the glass's bright reflection, and the upper
panes look wrong too: the trees are not seen through the glass, they cover
it (inferred: draw order/depth of the translucent glass versus the
alpha-tested trees). Both renderers show it. Next: snapshot dump at that spot
(`--nfsmw_native_dump=true --nfsmw_native_dump_interval_ms=3000`) to read the
glass and tree draws' order, blend, depth and alpha-test state.
Glass capture (`nfsmw_ipa58_glass_issues.log`, IMG_3954-3957): the
`24 October 2026/native` folder arrived empty (the log says 61 snapshots
were saved on the phone), so only the log's per-pass draw groups are
available (shader pairs, depth control 0x732 = test, no write / 0x736 = test
and write, LEQUAL; no blend state). Screenshots: the bus-terminal skylights
and wall panes show crisp trees and bright sky, as a reflection map would
(IMG_3957: trees inside the roof panes, where only sky is above), not what
is behind them. Inferred: the glass samples the dynamic environment cube
(the same as the car paint), so the question is whether the cube's faces or
orientation are wrong, or whether this is the game's own look. Needs the
snapshot images and a reference (360 footage of the same spot).
Snapshots arrived (61 frames, `24 October 2026/native`); frames 3000-3168
match IMG_3957. References from Stefan (IMG_3958-3961, 360/PC footage of the
bus terminal): the glass shows a dim, low-contrast reflection over a dark
interior; ours is a bright, high-contrast picture of trees and sky, also in
the roof panes. In the snapshots: pass_01 (800x360, ~200-340 draws) is a
mirrored scene with trees (the planar/road reflection, resolved 784x360 to
07280000); pass_02 (320x256, ~620 draws, the environment cube's faces) is
black in 53 of 56 frames, and all six resolved cube faces (256x256 to
06fd4000 etc.) are black in 55. Inferred, unverified: the glass shows the
planar reflection image (trees, sky) at full strength while the cube it
would otherwise reflect is black. Next: a capture of the glass draw itself
(its textures and blend state) to see which image it samples and how it
blends; check why the cube faces are black.
IPA59 (`ios/build/NFSMW-glass-capture-59.ipa`, SHA256
`398daccc8797d5287d3a98999edc14e725cdbd67a8439818c9b73bf37501a68e`, NFSMW UUID
`55DAC1E5-98A3-3C14-99FD-D179B2D10063`; 208 metallib entries, zip test and
codesign OK; not run): with `nfsmw_native_dump`, draws into the main picture
(pitch >= 1280) that read a cube or one of the renderer's own resolves are
logged as `reflective draw N: vs, ps, blend, depth, mask, colorctl, t<slot>
<address> <size> [cube] [resolve]` (3 per shader per snapshot) and their
textures saved as `watch_ps<key>_d<draw>_t<slot>_...png`.
Stefan: interval snapshots (even 15 s) make driving impossible. IPA60
(`ios/build/NFSMW-snap-button-60.ipa`, SHA256
`6eb5f9edc401d4b263a5f9bde00917bdeb2d12103997d4e10b733ff7d83ab638`, NFSMW UUID
`C174D6A8-0FDC-3564-8B32-ED17B874ADAA`; 208 metallib entries, zip test and
codesign OK; not run): `--nfsmw_native_dump_manual=true` shows a SNAP pill
right of HIDE; each tap saves one snapshot (same content as
`nfsmw_native_dump`, including IPA59's reflective draws; log
`[touch] snapshot requested`). No timed snapshots in that mode.

### October 25, 2026 — IPA60 snapshots: the environment cube renders black

Stefan, IPA60 SNAP (`24 October 2026/native_ipa60`, 4 frames incl. one at the
flickering billboard; `nfsmw.log`). The `reflective draw` log lines did not
appear (the diagnostics list is not printed on this path), but the textures
were saved. Draws reading the environment cube 06fd4000 (as a "kept" copy
from the previous frame): ps ae927576, d1f317fa, 1181eda3, 2442daf2, 8436534c
(glass and other reflective surfaces). Draws reading the 195x90 buffer
08734000 (kept) plus the previous frame's depth 08954000: ps 4fbaecfb,
8c8b5358, 8436534c. Measured (every 4th pixel): pass_02 (the cube pass,
000_320_0_d7c0, 6 faces of 256x256 per frame, 683 draws of the same world
shaders, colour mask 7, depth LEQUAL, viewport 256x-256) is **all zero**, as
are all six cube resolves and the 200x90 resolve to 08734000; pass_01 (planar
reflection) is fine (mean 0.13, max 1). So every surface that reflects the
cube reflects black. Each cube resolve clears colour and depth after the copy
(ctrl 00100300); the planar one does too and is fine, so the clear alone does
not explain it. Next: why the cube faces' draws leave nothing (depth clear
value/format of the 320x256 target, draws passing the depth test, colour
writes).
IPA61 (`ios/build/NFSMW-cube-test-61.ipa`, SHA256 `db7d3558b5407fe70997ce1762cd8269e367a83a5bd1fb39898460e8069f0f41`, NFSMW UUID `8A4F5D9B-5D7D-3C6F-91DF-AB58E3957D8B`; 208 metallib entries, zip test and codesign OK; not run): on
snapshot frames logs `pass start <key> at draw N (WxH, depth <MTLPixelFormat>):
colour clear|load (rgba), depth clear|load <value>` for every pass, and now
prints IPA59's `reflective draw` lines (the diagnostics filter dropped them).
`--nfsmw_native_test_small_no_depth=true` turns the depth test off in the
320- and 240-wide targets (cube faces, small blur) to see whether they fill.
IPA61 runs (`nfsmw_ipa61_run1.log`/`native_ipa61_run1`, run2 with
`--nfsmw_native_test_small_no_depth=true`): the cube pass starts with colour
cleared to 0 and depth cleared to 1.0 (Depth32Float_Stencil8), like the
passes that work; with no depth test (run2) the cube faces, the cube resolves
and the 200x90 blur resolves are still all zero. So it is not the depth test
or the clears: the draws write black (or nothing). Reflective draws now
logged (e.g. ps 2442daf2/ae927576/1181eda3/d1f317fa read the cube 06fd4000;
ps 4fbaecfb, 8c8b5358, 8436534c, 20710a9a read the 195x90 blur 08734000 with
the previous frame's depth). Next: A/B without the CPU-side experiments that
change what the GPU receives (`--nfsmw_battery_optimizations=false
--nfsmw_native_constant_copies=false --nfsmw_native_transform_copies=false`).

### October 26, 2026 — the environment cube is not black; sun still never hidden

No build, no source change. Inputs (Stefan, iPhone, build `Oct 22 2026 23:29:47`
= IPA54 line, default arguments, battery group on, constant/transform copies on):
`Most Wanted (2005) Debug/26 October 2026/25 October Long Playthrough Sun Issues/`
(`nfsmw.2.log`, `nfsmw.1.log`, `nfsmw.log`; IMG_3975-3977, Oct 25 17:28-17:51).

**Environment cube (refutes the IPA60/61 inference).** The rear-view mirror's
picture shader ps 8436534c (`shaders/msl/ps_8436534cfafcc0eb.hlsl`, texture mask
3) writes `tfetchCube(ENVIROMAP_SAMPLER) * RVMWorldBrightness`, tone-mapped; its
cube slot t1 is 06fd4000 (IPA61 `reflective draw` lines), the same cube the
glass shaders read. In IMG_3975/3977 the mirror shows the overpass, road and
trees behind the car, and IPA53's IMG_3949/3950 showed the sun in the car's
reflection. So on screen the cube has content; the all-zero pass_02, cube
resolves and car_cube faces in the IPA60/61 snapshots are a snapshot/readback
artefact (cause not checked; 3 of 56 IPA60 frames were not black). The glass
roof panes showing trees is then the cube's real content (trees around the car)
at a strength above the 360's faint look, not a black map. The planned A/B
without the battery switches would not test anything about the cube; dropped.
Also inferred from the texture masks: ps 4fbaecfb (mask 1) and 8c8b5358 (mask
0) never sample the 195x90 buffer, so the `reflective draw` lines list stale
fetch slots; only slots in a shader's mask are read.

**Sun.** Stefan: in sunny weather the sun shows but is always visible, also
behind buildings/overpasses (IMG_3975: glare drawn over the overpass; IMG_3977:
through trees). 1003 `occlusion queries` lines over the runs of Oct 25 16:20 to
21:04: 8 addresses (05D818C0 new, 19 lines), ~860k answers in all, **0 answers
of 0**. Smallest answer per address: 05D81340 65536 (exactly 256x256),
05D81080 65902, 05D82DC0 75089, 05D82B00 99223, 05D82580 109491, 05D81600
2.74M (never under ~3 full frames), 05D82040/05D818C0 921600 (the default).
Largest: 05D81600 28.8M (31 full 1280x720 frames), 05D82040 24.1M. Inferred:
the counted draws of at least these two queries cover far more than a sun
quad (many draws or passes inside one begin/end), and no query ever drops to
0 behind geometry. Not known: which draws each query brackets, their pass and
depth state.

**Plane run (Stefan's report, not from the log):** ~2+ h of play in Low Power
Mode, 72% to 35% (~17 %/h). The logs (rotated at 5 MB, so the start is lost)
show runs 16:20-16:58, 19:26-19:53, 19:53-20:10, 20:11-21:01, 21:01-21:04;
`Low Power Mode on` in 2614 lines, off in 19.

**Hang, Oct 26 02:30 run:** 39 s after start, during loading (frame 1350), the
watchdog logged `5 s sin que se mueva ni un registro en ninguno de los 17
hilos` with the semaphore history; the log ends there. Same signature as the
parked iPhone event-loading freeze (BACKLOG); whether the game froze for
Stefan is unconfirmed.
Stefan (Oct 26): he did not notice the game freezing in that run.

### October 26, 2026 — IPA62: per-query draw log, world cube test switch

Approved by Stefan. `ios/src/native_renderer.mm` only; no default behaviour change.
- On snapshot frames (SNAP with `--nfsmw_native_dump_manual=true`, or
  `nfsmw_native_dump`), the log lists `query N at <address>` and, per query and
  pass/slot, `query N in <pass> slot S: D draws (first-last), I indices,
  counted C samples (/divisor = guest pixels); ps ...; depth ...; mask ...`
  (up to 4 pixel shaders; every depth control and colour mask). Answers which
  draws the sun's query brackets and why it never reaches 0.
- `--nfsmw_native_test_no_envcube_world=true` (default false): every shader but
  the car paint (2442daf2, d1f317fa) and the rear-view mirror (8436534c) reads
  the black placeholder cube (index 0). If the bus-terminal glass then looks
  like the 360's faint reflection, the cube term is too strong; if the trees
  stay, they come from another texture.
IPA62 `ios/build/NFSMW-query-glass-62.ipa`, SHA256
`c893bb527aaf6a2f4f2e731cbd76c37c4953cc3619e4f23dd513c2572f43941e`, NFSMW UUID
`9350B67F-51B7-3C0E-B933-F679A01D2B87`; 208 metallib entries (same as IPA61),
zip test and codesign OK. Not run on a device.

### October 26, 2026 — IPA62 iPad run: the sun query's end goes to another address

Stefan, iPad, IPA62 (`26 October 2026/nfsmw_ipad_sun_reflections.log`,
`native_ipad_sun_reflections/` frames 3217, 3897, 4209, 5910; `extra_args.txt`:
`--nfsmw_native_dump_manual=true --nfsmw_native_test_no_envcube_world=false`).
(The log's `build Oct 22 2026 23:29:47` line is not the IPA62 build date; the new
`query` lines prove IPA62.)

Measured, snapshot query lines: each sun query is one 6-index quad, ps
2d8bf2c6, colour mask 0, depth 00700732; most are drawn in the environment cube
pass (000_320_0_d7c0) and one in the main picture. In frames 3217, 3897 and
5910 every quad counted 0 or 91-98 guest pixels: the GPU count is right. The
game's answers (`occlusion queries since` lines) are all given on addresses
0x20 **below** the begin addresses (begin 066b75a0/7b20/6360/6620/7060, answers
on 066B7580/7B00/6340/6600/7040), and still never 0. Frame 4209: begins at
both 066b7de0 and 066b7dc0, 066b60a0 and 066b6080, 066b6620 and 066b6600:
the end ZPD at X-0x20 was taken for a new begin (no 0xFFFFFEED marker seen),
so that "query" stayed open and counted the next draws: 286 world draws,
then 1114 main-pass draws plus the post effects (5,956,000 samples), until
the next begin.

Inferred cause (code read, `CpOcclusion` and the native ZPD override in the
SDK's plugin_main.cpp): counts are stored under the begin address
(`occlusion_counts[queries[q]]`) but looked up at the end under the end
address (X-0x20), so the real counts (often 0) are never returned; the end
address only gets a count when an unrecognized end opened a runaway query
there, which explains the huge, never-zero answers. Proposed fix (native
renderer only): store each query's count under the address of the end that
closed it; a ZPD at the open query's begin address minus 0x20 without the
marker closes it instead of opening a new query.

Glass: this run had the black-cube switch off. Stefan: the terminal glass still
looks wrong, worst inside the terminal. Halo: Stefan reports a halo around the
gas price sign (frame 5910), the car's spoiler (worse when moving) and
antennae, since the first Metal version. In the snapshot PNGs the sky is black,
so the halo against the sky cannot be seen there. Candidate (inferred, not
checked): the final composite ps 20710a9a (scene t0, bloom t1 390x180, blur t3
195x90, this frame's depth t4) blends the low-resolution blur by depth.
Correction (Stefan): both runs share the log; the second run (13:38, frames
3217-5910, bus terminal) had `--nfsmw_native_test_no_envcube_world=true`. With
the world cube black the terminal glass still shows trees/sky (frames 3217,
3897), so they do not come from the environment cube. No main-pass draw in those
frames read a cube or resolve (no `reflective draw` lines besides the stale-slot
4fbaecfb/8c8b5358), so the glass draw is still unidentified (27d82ea0's blended
draws, blend 07060706, are tree cards). Proposed with the sun fix (IPA63):
`--nfsmw_native_test_skip_ps=<hex>` to skip one pixel shader and find the glass.

### October 26, 2026 — IPA63: sun query answers filed under the end address

Stefan: halo (also on Vulkan) and bus-terminal glass parked as likely the
game's own look; fix the sun. Change (`ios/src/native_renderer.mm`, no switch;
gated by `nfsmw_native_occlusion` as before): each recorded query keeps the
address it ended at (`Frame::query_ends`); the GPU count is stored under that
address, which is where the game reads its answer (begin minus 0x20). A ZPD at
the open query's begin address minus 0x20 without the 0xFFFFFEED marker now
closes the query instead of opening a runaway one (no answer is written for
it; counted in the stats line as `(N ends without the marker)`). Snapshot
query lines also print `ended at <address>`. Expected: answers of 0 behind
geometry and counts no larger than the sun quad.
IPA63 `ios/build/NFSMW-sun-fix-63.ipa`, SHA256
`3be16d73ade549e73a78998b9c103b7380aa815b900e5d9793bfdc177a56206b`, NFSMW UUID
`AC72C463-778A-3A66-8C38-EBC701644EFE`; 208 metallib entries, zip test and
codesign OK. Not run on a device.

### October 26, 2026 — IPA63 run: sun fixed

Stefan, iPad, IPA63 (`26 October 2026/nfsmw_ipa63_sun_fixed_ipad.log`,
13:54-15:16, two runs): the sun glare now fades out when going into cover and
back in when leaving it. Log: 145 `occlusion queries` lines, 8 answer
addresses (all begin-0x20), ~127k answers, ~99k of them 0 (e.g. 066B7580:
21298 of 21301); largest 921600 (the default before a first count, no more
multi-frame counts); 46,774 ends without the marker closed by the new rule.
11 watchdog groups (14:00-14:03, 15:09-15:10) while the renderer kept logging
frames; Stefan reported no freeze (same as the earlier watchdog-only cases).

### October 26, 2026 — IPA63 iPhone Time Profiler, police chase: where the CPU goes

Stefan, iPhone 17 Pro Max (iOS 27.0.1), IPA63 (NFSMW UUID
`AC72C463-778A-3A66-8C38-EBC701644EFE`), 1.0x / cap 40, MetalFX and FXAA off,
LPM off. Instruments Time Profiler attached to LiveContainer, High Frequency,
Deferred, 61 s of a police chase
(`26 October 2026/ipa_63_time_profile_chase_iphone.trace`, log
`26 October 2026/nfsmw_ipa63_police_chase_iphone.log`). dSYM for line lookup:
`ios/build/NFSMW-sun-fix-63.dSYM` (dsymutil of the IPA63 binary, same UUID).
Log in the window: 37.8 frames/s on screen, 3,051 draws/frame, 26,054 vertex
buffers cached, GPU 7.7-11.6 ms/frame.

Measured (Running samples only, ms of CPU per second; app total 791 = ~0.8 core):

| Thread | ms/s | Main content |
|---|---|---|
| Render queue (`NativeSwap` blocks, unnamed workqueue) | ~180 | `RenderFrame` 98 incl (32.6 self), Metal `drawIndexed` 16.6, Frame reset / `Draw::~Draw` 17 / 13, `gpu_buffers` map 8.9, encoder creation 5.8 |
| GPU Commands | 155 | `Record()` 109 incl / 68 self, `Fingerprint` 9.5, attribute map 9.0, PM4 parsing ~25, `operator new` 10.7, `LoadShader` 4.3 |
| Main XThread (game) | 145 | recompiled game code; `adaptive_qos::OnMainLoop` 8.1 self |
| XThreadB91B (game worker) | 125 | recompiled game code |
| XThreadE013 | 83 | game thread (XMA/WMA decode appears in it) |
| Main Thread (UIKit/SDL pump) | 25 | `SDL_WaitEventTimeoutNS` / `UIKit_PumpEvents` |
| Audio, XMA decoder, timers, others | ~30 | |

Per frame at 37.8 fps: `Record()` ~2.9 ms, render-queue encode ~4.8 ms. Game
simulation threads (~350 ms/s, ~45%) are recompiled guest code.

Hottest lines (self, ms/s; `native_renderer.mm` at b2bb38e):
- 2617 `AttributeEntryFor` (attribute cache lookup, inlined) 13.5, plus the
  `unordered_map<AttributeKey>` fallback 9.7: ~23 total, the largest single
  item in `Record()`. The front cache misses into a 26k-entry map.
- 6453/6454 + map: `GpuBufferFor` slot misses into `unordered_map<const void*,
  GpuBuffer>` 8.8 plus ~8 on the two lines.
- 1366/1369 `Fingerprint` sample loop 8.7.
- 1004 `Draw::~Draw` 5.7 self (13 incl): per-frame teardown of 3,051 draws.
- 2499/2500 index cache key + `IndexFingerprint` 7.5; 2595 swizzle check 4.0;
  2903 texture slot compare 4.1; 2658 memo lookup 3.4.
- `adaptive_qos::OnMainLoop` 8.1: almost all on the `casal` of the owner
  compare-exchange (plus `pthread_threadid_np`) that runs on every call
  (disassembly of the IPA63 binary). The cost implies the deferred-call runner
  `sub_823C8290` is called hundreds of thousands of times per second, i.e. the
  main loop still spins through it (inference: Time Profiler gives no call
  counts).
- Unsymbolicated system code at `0x241cd8xxx` (~35 ms/s over all threads) and
  `start_wqthread` self 16.2: not attributable from this trace.

Conclusion: no single large waste left. The renderer's CPU work is spread
across per-draw lookups; the candidates below together are ~40-50 ms/s
(~5-6% of app CPU), a small battery effect (estimate, not measured). Proposals
(not approved, not implemented): (A) `OnMainLoop` keeps the owner check in a
thread_local after the first call (no atomic per call, ~8 ms/s); (B) larger or
better-hashed GPU buffer slot table (needs `--nfsmw_native_gpu_lookup_stats=true`
once to see the hit rate); (C) larger attribute front cache; (D) reuse `Draw`
objects across frames instead of destroying 3,051 per frame.

### October 26, 2026 — IPA64: proposals A-C from the IPA63 profile (built, not run)

Stefan approved A-D. D (reuse `Draw` objects across frames) was dropped after
reading the code: `~Draw` is mostly the shared_ptr releases of indices,
constants and attribute arrays, which a reused object would still do when
overwritten; no CPU saved, only moved.
- A (`ios/src/adaptive_qos.cpp`, no switch, same behaviour): `OnMainLoop`
  settles whether this thread is the owner once (thread_local) instead of a
  `pthread_threadid_np` + compare-exchange on every call.
- B (`--nfsmw_native_gpu_lookup_slots_log2`, default 14 = 16,384 slots; 12 =
  the old 4,096): larger direct-mapped cache in front of `gpu_buffers`.
- C (`--nfsmw_native_attribute_lookup_sets_log2`, default 14 = 16,384 sets x 2;
  12 = the old 4,096): larger attribute front cache. IPA63 chase log: 2,493,136
  hits / 539,758 misses (18% misses) at 4,096 sets.
Static memory: +~0.45 MiB (B) and +~1.3 MiB (C). Startup log lines print the
slot and set counts. Shader libraries untouched (208 metallib entries).
IPA64 `ios/build/NFSMW-lookup-caches-64.ipa`, SHA256
`e997fa1868ca4a3f89bc884eb236ea19191709c01658a9ae3c26c364834b4ee0`, NFSMW UUID
`111B9391-F612-3460-936B-350557198BFB`, dSYM `ios/build/NFSMW-lookup-caches-64.dSYM`;
zip test and codesign OK. Test: same chase and settings as the IPA63 Time
Profiler (1x/40, 60 s, High Frequency, Deferred); compare `OnMainLoop`,
`unordered_map` and `Record()`/`RenderFrame` ms/s and the attribute lookup
miss ratio in the log. Old sizes for an A/B:
`--nfsmw_native_gpu_lookup_slots_log2=12 --nfsmw_native_attribute_lookup_sets_log2=12`.

### October 26, 2026 — IPA64 iPhone Time Profiler, police chase: caches work, runs not comparable in ms

Stefan, iPhone 17 Pro Max, IPA64 (UUID `111B9391-F612-3460-936B-350557198BFB`),
same settings as the IPA63 trace, no Extra Args
(`26 October 2026/ipa64_time_profile_police_chase_iphone.trace`, 15:45:34-15:46:36;
log `26 October 2026/nfsmw_ipa64_polica_chase_iphone.log`).

Measured:
- Not comparable in absolute ms/s: the IPA63 trace window was entirely in an
  adaptive-QoS boost (User Initiated from 15:31:26; 76% of running samples on
  P cores), the IPA64 window boosted only until 15:45:44 and then ran at
  Utility (86% of samples on E cores). App total 1,358 ms/s vs 791 is the
  slower E cores, not more work. Both held ~40 fps; IPA64 drew more
  (2,400-4,200 draws/frame vs 2,500-3,100).
- C: attribute lookup misses ~18% -> ~3% (log: 2,830,355 hits / 80,486
  misses vs 2,493,136 / 539,758). `unordered_map<AttributeKey>` 5.8% -> 1.0%
  of GPU Commands time.
- B: `unordered_map<const void*, GpuBuffer>` 3.9% -> 1.8% of render-queue time.
- A: `OnMainLoop` 5.6% -> 3.6% of Main XThread time. The `casal` is gone; the
  remaining samples sit on the function's first instructions (guard and
  Enabled loads), i.e. the cost of the call itself, which the deferred-call
  runner makes extremely often (inference). Removing that needs fewer calls
  (the main-loop spin), not a cheaper hook.
- `Fingerprint` 6.1% -> 12.9% of GPU Commands (more draws in this window;
  not explained further).
Inference: B and C remove their lookups as intended; the battery effect is
small and cannot be read from these traces (different cores). Whether the
adaptive boost engages dominates CPU energy in a chase far more than these
lookups.

### October 26, 2026 — IPA64 iPad test race: GPU cost per resolution and frame cap

Stefan, iPad, IPA64, test race, ~3 min each, LPM off, no Extra Args. Logs
`26 October 2026/nfsmw_ipa64_race{1,2,3,4}_ipad.log` (race3's log also holds
the 1.5x run before it; the 2x part starts at its first `scale 2.000` line).
Battery (Stefan, 1% steps, too coarse for a rate): 1x/60 84->83, 1.5x/60
83->81, 2x/60 81->81, 1.5x/120 with 120 Hz sim 79->76 (only run that got warm).

Measured from the log's `GPU profile` lines (race frames, 47 passes):

| Run | GPU ms/frame mean (median, max) | Frame budget |
|---|---|---|
| 1x / 60 | 5.9 (5.4, 9.2) | 16.7 |
| 1.5x / 60 | 10.2 (10.6, 15.2) | 16.7 |
| 2x / 60 | 14.2 (14.8, 15.6) | 16.7 |
| 1.5x / 120 | 6.1 (6.5, 8.0) | 8.3 |

All runs held 60.0 (or ~119-120) frames/s on screen; in-race hitches (>~40 ms)
only 1-4 per run, the rest at loading. The log has no frame-interval
distribution, so pacing below ~40 ms is not visible.
GPU ms are at whatever clock the GPU chose: 1.5x/120 does the same work as
1.5x/60 in ~6 ms because it runs at a higher clock (more energy per frame and
twice the frames: the heat). At 2x/60 the GPU is ~85-90% busy.
Pass breakdown (one late window each): main scene (960x720 guest, 3 passes)
1.36 ms at 1x -> 6.84 ms at 2x; the six 320x256 passes (scaled to 640x512 at
2x) 1.48 -> 3.01 ms; the 1600x1600 shadow pair 0.9 -> 1.3 ms (not scaled);
resolve copies 0.22 -> 1.05 ms.
Inference/lead: the six 320x256 passes grow with the scale; if they are the
reflection (environment cube) faces, keeping them at 1x size would save ~0.7 ms
at 1.5x and ~1.5 ms at 2x. Not checked, not proposed for implementation yet.

### October 26, 2026 — IPA65: environment cube faces at 1x (built, not run)

Approved by Stefan ("reflections don't really need to scale up with
resolution"). Change (`ios/src/native_renderer.mm`, target sizing): colour
targets whose resolves in the frame all go into a cube slice (the
environment cube's 320x256 faces) get scale 1 like the shadow map; the cube
texture follows (it is sized from the source). Source key matched like the
resolve picks it (own EDRAM key, else the last draw's). Switch
`--nfsmw_native_scale_reflections` (default false; true = scaled as before).
Startup log: `[native] reflections at 1x: N environment cube target(s)` (up to
3 lines). Expected (from the IPA64 race): ~0.7 ms/frame saved at 1.5x, ~1.5 ms
at 2x; reflections as sharp as at 1x.
IPA65 `ios/build/NFSMW-reflections-1x-65.ipa`, SHA256
`9c21849057464232fb096e33da74f284d90ce03bb836aff52e091c74d9cad56a`, NFSMW UUID
`C024EDFD-25F8-31BE-AB6C-12A27CD41FB8`; 208 metallib entries, zip test and
codesign OK. Test: iPad 1.5x/60 test race with the log; check the log line and
the 320 passes in the `GPU profile` lines (should read 320x256), and that the
car reflections look right.

### October 26, 2026 — IPA65 run: did not apply; IPA66 fix (built, not run)

Stefan, iPad, IPA65, 1.5x/60 test race (`26 October 2026/nfsmw_ipa65_r1.5x:60_ipad.log`,
16:16-16:19). Measured: no `reflections at 1x` line; the six cube passes
still 480x384 (2.78 ms in one late window); GPU 11.4 ms/frame mean (IPA64 run
10.2: within run-to-run spread, not a regression claim). Cause: the race's
cube is not filled by cube-slice resolves (`ev.array`) but by six 2D resolves
at the face addresses of a cube the frame samples (the `cube_targets`
assembly), so no source was recognised. IPA66 also counts a resolve whose
destination is a face of a sampled placeholder cube (same address/stride rule
as `cube_targets`).
IPA66 `ios/build/NFSMW-reflections-1x-66.ipa`, SHA256
`00aff81491845240decafd27a78215fb72060a4b00e2c5472c417b4735ba5702`, NFSMW UUID
`08466B13-142E-3EC6-A762-31507638FE99`; 208 metallib entries, zip test and
codesign OK. Same test as IPA65.

### October 26, 2026 — IPA66 run: environment cube at 1x applied

Stefan, iPad, IPA66, 1.5x/60 test race (`26 October 2026/nfsmw_ipa66_reflections_ipad.log`).
Measured: `reflections at 1x: 1 environment cube target(s), e.g.
000_320_0_d7c0_s1`; the six cube passes now 320x256, 1.0-1.5 ms per window
(IPA64/65 at 480x384: 2.0-2.8 ms). GPU ms/frame mean 8.9 (median 9.4) vs
10.2 (IPA64) and 11.4 (IPA65) at the same setting: ~1 ms/frame (~10% of the
GPU frame) saved, with run-to-run spread. Stefan noticed the rear-view
mirror is softer: expected, the mirror is the environment cube times a
brightness (ps 8436534c, Oct 26 entry), so it is now 320 per face as on the
360. `--nfsmw_native_scale_reflections=true` restores the scaled cube.


## October 26, 2026 (night): in-game options menu (IPA67)

Branch `in-game-options` (local, off `battery-optimization` at 6588d8e).
Design approved by Stefan before coding: gear for touch, L3+R3 for
controllers, graphics settings only (Extra Options not complete yet).

What changed:
- `ios/src/ingame_options.mm/.h` (new): a sheet over the game with the
  launcher's rows for `scale`, `metalfx_mode`, `fps_cap`, `antialiasing`,
  `shadow_scale`, `reflection_rate`, `auto_cap`, `menu_cap`, `heat_scale`,
  `battery_mode` (native-only rows hidden without the native renderer). Opened
  only while `battery::InMenu() == 1` (menus and pause screens) by a gear at
  the top right or L3+R3 (GCController polled 10x/s, 30x/s while open; D-pad
  moves/changes, A changes, B or L3+R3 closes). Each change saves
  `Documents/settings.json`, recomputes the launcher's arguments and sets the
  live cvars with `rex::cvar::SetFlagByName`. Rows show "next launch" for
  40/120 fps (or from them) and MSAA; the footer says when anything else
  launch-only differs from the start (e.g. values Battery mode sets).
  `extra_args.txt` is not reapplied: a value changed in the menu wins until
  the next launch.
- Game input is blocked while the sheet is up and until every controller
  button is released after it closes: `game_app.cpp` sets the input system's
  active callback (it replaces the SDK's, used only by the ImGui overlays).
- `native_renderer.mm`: `NativeResolutionScale()` and `MetalFxTemporal()`
  re-read their cvars when `NativeSettingsChanged()` bumps a generation (they
  were read once). The scale change uses the same rebuild path as 0.75x when
  hot; MetalFX on/off is evaluated once per recorded frame (motion, jitter);
  mode changes rebuild the scaler (requested size changes).
- `battery.mm`: the watcher thread always runs (cvars read every 2 s, so the
  switches work when turned on in game; turning 0.75x when hot off restores
  the scale); a chosen cap (`ChooseCap`, 30 or 60) replaces the fixed 60;
  caps handled when the game started at 30 or 60 (was 60 only).
- `launcher.h/.mm`: `Rows`, `ReadSettings`, `WriteSettings`, `SettingValue`,
  `SetByBatteryMode`, `ArgumentsFor` for the menu.

Build: `cmake --build --preset ios --target ipa -j 6`, exit 0 (one
deprecation warning, `UIScreen.mainScreen`, as in touch_controls.mm).
`ios/build/NFSMW-ingame-options-67.ipa`, 30026877 bytes, SHA256 prefix
a4e058869069787d, executable UUID 5B4C54E7-EA65-3FCB-A45C-9B8D06664A06,
208 metallib entries, `unzip -t` no errors.

Not yet tested on device. Untested risks (inferences): MetalFX off->on mid-
game may stutter while motion shader variants compile; a scale change from
1x to above 1x keeps `ios_retina=auto` until the next launch (the picture
may be presented at fewer pixels on large screens); controller focus in
the sheet is drawn with the table's selection only.
Device checklist: open with the gear and L3+R3 in the pause menu (not while
driving); change resolution, MetalFX (each mode and off/on), FXAA, 30/60 and
Battery mode and watch the `[options]`, `[native] internal resolution now`
and `[battery] cap` log lines; close with B and check that the pause menu did
not take the B; relaunch and check the launcher shows the new values.

IPA67 device result (Stefan, Oct 26, device not stated): live and working:
render resolution, MetalFX, FXAA, 30<->60 cap, car reflection rate, shadow
drawing size, Battery mode; the gear shows only in the pause and main menus.
40/120 fps and MSAA did nothing while playing: expected, they are next-launch
only (marked in the sheet). FXAA vs FXAA high looked the same to him: the
two differ only in edge threshold (0.125 vs 0.063) and subpixel amount (0.75
vs 1.0), the same as from the launcher; not a menu fault (inference). Not yet
reported: whether B leaked into the pause menu, relaunch check.

IPA68 (`ios/build/NFSMW-battery-30fps-68.ipa`, 30026701 bytes, SHA256 prefix
cd838a3083b2032d, UUID B174EADB-7000-3A87-A186-A4615096AB48, 208 metallib,
`unzip -t` ok): Battery mode now also sets the 30 fps cap (Stefan, Oct 26),
in the launcher (row greyed "Set by Battery mode") and in the in-game menu
(applied live through `battery::ChooseCap` when the game started at 30 or 60;
from 40/120 it waits for the next launch). Build exit 0. Not yet run.

IPA67 follow-up (Stefan, Oct 26): the "next launch" label shows on the 40/120
fps and MSAA rows; closing the sheet with B does not reach the game's pause
menu. Still unreported: the launcher showing the menu's values after a
relaunch; IPA68 not yet run.

IPA69 (`ios/build/NFSMW-reflection-size-69.ipa`, 30027403 bytes, SHA256
prefix c0a118bffa4469b3, UUID 36230D8D-9618-3D01-B9A3-AF661E45D1C7, 208
metallib, `unzip -t` ok; includes IPA68): new setting "Reflection and mirror
resolution" (Stefan's request), launcher Graphics tab and in-game menu:
`reflection_size` = `1x` (default, the IPA66 behaviour) or `scaled`, giving
`--nfsmw_native_scale_reflections`. Live in game: the renderer decides it
every frame (no static). Battery mode sets 1x. Build exit 0. Not yet run.

### October 26: HUD layout (movable/resizable HUD, step 1)

Stefan asked whether single HUD elements can be moved. The HUD is a FEng
package of named objects; the 19.5:9 code already finds the left group
(0x1603009E: minimap side) and the right group (0x5D0101F1: speedometer side)
and moves their x (object+44 -> +28). Found while reading the code:
`sub_822AA6D0` (the HUD's widescreen switch) is called from `sub_822A8C50`
(the HUD's update, assumed every frame) and only acts when the mode changes;
the minimap is moved apart from the left group by `sub_8229C020`, which adds
to its +184 (x) and its children's (+60/64/68/72/144) x, sets child 144's y
from +188, and sets the map picture's offset x at 0x82A2C60C outright; the map
drawing code (recomp.82, `lfs -14836/-14832`) reads that offset as x and y
(0x82A2C610). So the minimap can move in y as well (inferred, not run).

IPA70 (`ios/build/NFSMW-hud-layout-70.ipa`, 30040211 bytes, SHA256 prefix
c1515f8e194e8f19, UUID 80317259-0F8A-3737-A022-7524F0DDE5FB, `unzip -t` ok;
includes IPA69): new settings, launcher Graphics tab (section HUD) and the
in-game menu, all live:

| Setting | Cvar | Values |
|---|---|---|
| HUD size | `nfsmw_hud_scale` | 0.70-1.30 by 0.05 (1.00) |
| Minimap left/right, up/down | `nfsmw_hud_left_x`, `nfsmw_hud_left_y` | -160..160 HUD units by 10 (0) |
| Speedometer left/right, up/down | `nfsmw_hud_right_x`, `nfsmw_hud_right_y` | same |

`game_scene_size.cpp`: the size multiplies the HUD matrix's x/y scale (the
`sub_82453768` hook) while driving only (`battery::InMenu() == 0`), so menus
keep their size; the mirror follows through `nfsmw_mirror_scale_*`. The sides:
the groups' x and y are base + offset every call (base taken again whenever
the game or its script moved them); the minimap's object and children get the
difference from what was applied, and the picture offset is kept as the
game's value + offset. The 19.5:9 extra is now part of the same offset. Logs:
`[hud] matrix built (1/2/1000)` shows whether the matrix is rebuilt every
frame (if not, the size only changes on the next race); `[hud] left group ...`
on each new HUD. Not verified: y positive = down (the arrows' labels), the
heat meter being in the left group. Build exit 0. Not yet run.

Device checklist: (1) default 0s/100% look as IPA69 at 19.5:9, 16:9, 4:3;
(2) HUD size 80% and 120% in a race, menus unchanged, mirror picture inside
its frame; (3) minimap moved right and up: the map picture moves with its
ring, the arrow stays in the middle; (4) speedometer moved left and up;
(5) a new race and a restart keep the positions (no doubled moves);
(6) changed in the pause menu: applied after resuming.

IPA70 result (Stefan, Oct 26, device not stated): 80% and 120% work, but the
HUD shrinks toward / grows away from the middle of the screen (it scales
about the middle, so the margins change). The positions move correctly and
stay put in a race. The race element showing progress and position moves
with the speedometer: it is in the right group (0x5D0101F1).

IPA71 (`ios/build/NFSMW-hud-anchors-71.ipa`, 30042058 bytes, SHA256 prefix
8b59180dfff2e049, UUID 2EC8FCCF-C13F-33E5-B9A4-0E7D9CCFD185, `unzip -t` ok):
the sides are moved so each scales about its own middle: with g the side's
middle in HUD units before the matrix, the offset d solves
s * (g + d) = g + offset. g = (221 + 120 when the game's widescreen layout is
on, 138), measured on the Oct 26 screenshots (4:3 iPad speedometer centre at
0.845 x 0.787 of the screen = 221 x 138 HUD units; 19.5:9 iPhone at 0.895
x = 446 x 0.92 HD title-safe = 410, as measured). The minimap moves with the
left side's d. New log: `[hud] right group +00..+60` (raw words) and `right
group data pos/size`, once per new HUD, to find the race position/progress
objects inside the right group (next: split them off so they stay put).
Not yet run.

IPA71 result (Stefan, Oct 26, iPad, 4:3; log
`Debug/26 October 2026/nfsmw_ipa71_hud_ipad.log`, IMG_0314-0316): at 80% and
120% the speedometer's dial, arc, digits and KM/H, and the minimap's map,
rings and heat icon come apart: only some of them are in the two groups, so
the size compensation moved those and not the rest. Speedometer up (-80)
also moves the race standings (top right) off the screen: they are in the
right group; with left y -80 a ring piece of the minimap went much higher
than the map (moved twice, inferred: by the group and as a minimap child).
`[hud] matrix built` reached 1000 calls 21 s after start: the matrix is
rebuilt every frame (size changes are live, as seen). Right group dump: +0
vtable 82080070, +4/+8 next/prev, +0C GUID, +10 hash, +18 type 5, +1C flags,
+2C data (pos 209.7,49.8, size 1,1); lists with vtable 82080030 at +34 (2),
+44 (3) and +5C (1 entry: its child list, head = tail).

IPA72 (`ios/build/NFSMW-hud-tree-72.ipa`, 30042673 bytes, SHA256 prefix
d5cc50c6c7c4d482, UUID 837807C0-2EB9-3535-AFD3-50F99229C894, `unzip -t` ok):
the size compensation removed (as IPA70); new `[hud-tree]` log once per new
HUD: every object of the HUD package, from the right group's first sibling,
children of groups indented (hash, type, flags, position, size). Next: map
hashes to elements and move them one by one. Not yet run.

IPA72 result (Stefan, Oct 26, iPad, one race; log
`Debug/26 October 2026/nfsmw_ipa72_hud_race_ipad.log`): no `[hud-tree]` and
no `[hud] left group` lines: with every HUD setting 0/100% the hook returned
before the dump. Stefan also reports the Post-processing switch does nothing
(and is not in the in-game menu).

IPA73 (`ios/build/NFSMW-hud-tree-73.ipa`, 30043163 bytes, SHA256 prefix
6a376db45d6f8881, UUID AA0038A5-C0D7-319B-985E-2BEE9B869ABA, `unzip -t` ok):
the tree is dumped once per HUD package whatever the settings; `[post] no
post-processing: hook runs, byte 0x828F48B2 was N` (first two calls) shows
whether the "Disable Post Processing" hooks run with the switch off and what
the byte held. Not yet run.

IPA73 result (Stefan, Oct 26, iPad 4:3, one race, Post-processing off; log
`Debug/26 October 2026/nfsmw_ipa73_hud_race_ipad.log`):
- `[post]`: the no-post-processing hooks run; the byte 0x828F48B2 was 1 at
  the outer call (0 at the nested one, already cleared). Stefan: no visible
  change, so the flag alone does not remove the look here (open).
- `[hud-tree]`, 373 lines; HUD units are from the middle of the screen, y
  down. Top level: 82D60021 (-72,173), 0F365871 (-221,139: the minimap's map,
  four 128x128 quadrants), 4E4566E5, 157C5B37 (-226,7) > 1603009E (left
  group), AB9C1D4D (middle), 5D0101F1 (209.7,49.8, right group) > 5C7A5C8A,
  7FAC287B (0,-176: two 128x87 halves, the mirror's frame, inferred),
  00A1A862 (minimap icons; DD9EF5FF at -222,139 the player arrow).
  Left group: the minimap ring C46A80A9 (with the heat icon/multiplier),
  382D2FC9, B0F63386 at y ~105-139 from the middle; the rest at -96..-197
  (top left, not seen in a race). Right inner group: the speedometer's
  pieces (5164D4EA dial and needle, 87C38E97, EDFB6D37, C5D551B7, 5DF2F5B4,
  8991BD54, 941FFF09 digits) at y 83-165; three rows EA903012, 3F8644CA,
  D60FC075 at -32, 2, 38; the race standings 5ED609A1 (4 rows of 175x18) at
  -123, and DE89E070, B1C5ED0D, 9AFCE2B8, 2269D232 at the top right.
  (Pieces' y: position plus the mean of their children's, recursively.)

IPA74 (`ios/build/NFSMW-hud-elements-74.ipa`, 30051752 bytes, SHA256 prefix
c6a78be1f6c38270, UUID CB3DD738-3A1B-3298-B6AD-A699EB189B9B, `unzip -t` ok):
each child of the two inner groups is a piece; below 60 units under the
middle it belongs to the minimap (left) or the speedometer (right), above
on the right to the race info (new `nfsmw_hud_race_x/y`, rows "Race info"),
top-left pieces stay. The two groups now only carry the 19.5:9 extra; the
minimap's map moves with the minimap offset (MoveMinimap). Size unchanged
(IPA70: whole HUD about the middle; its summary now says to move the pieces
back). Log: `[hud] package ...: pieces: minimap N, speedometer N, race info N`
(expected 3, 7, 10 from IPA73's tree). Not yet run.

IPA74 result (Stefan, Oct 26): the minimap, speedometer and race info move
correctly on their own. Asked: the size should keep the default safe zone
(margins), and the safe zone should be its own slider.

IPA75 (`ios/build/NFSMW-hud-safe-zone-75.ipa`, 30046422 bytes, SHA256 prefix
979884e7228f1fdb, UUID 0557CDF7-7E38-3F93-81FC-76EB30FD0AE9, `unzip -t` ok):
every piece of an element gets one offset d with s * (g + e + d) =
k * (g + e) + offset: g the element's middle as the game draws it (x 221,
+120 in the widescreen layout, left ones negative; y 139 minimap and
speedometer, -150 race info and the top-left pieces, which are now an
element of their own with no player offset), e the 19.5:9 extra (carried by
the two groups), s the size, k the new safe zone (`nfsmw_hud_safe_zone`,
`hud_safe_zone`, 0.80-1.10 by 0.02, 1.00; live). Unlike IPA71 every piece is
moved, not the two groups. The centres are estimates (IPA73 tree): an
element whose middle is off drifts a little with the size. Not yet run.

IPA75 result (Stefan, Oct 26, iPad 4:3; log
`Debug/26 October 2026/nfsmw_ipa75_hud_ipad.log`, ipa75_hud_min/max/default
_ipad.png): `[hud] package ...: pieces: minimap 3, speedometer 9, race info 6`.
At 70% and the largest size the parts that change while driving (needle,
digits, nitrous arc, KM/H, the minimap's map) keep their margins, but the
still ones (the dial's face with its numbers, the gray ring, the heat icon)
sit exactly where the matrix alone puts them: (1690-1000)*0.7+1000 = 1483 px,
seen ~1480. Inference: FEng keeps a laid-out position for objects that are
not redrawn, taken when the pause screen closes; the offsets used HudScale(),
which is 1 while a menu is up, so those objects kept the size-1 offsets.

IPA76 (`ios/build/NFSMW-hud-scale-76.ipa`, 30046463 bytes, SHA256 prefix
3101e048e6491840, UUID 251E5148-0C10-3DFD-A57E-2508B0FB6CDA, `unzip -t` ok):
the offsets use the size setting at all times (the matrix still scales only
while driving), so they are the same before and after a pause screen. If the
still parts stay off, the next lead is the FEng object's "needs layout" flag
(flags at +0x1C) after each offset change. Not yet run.

IPA76 result (Stefan, Oct 26, iPad): the pieces stay together (no report of
parts coming apart), so the pause-screen offsets were the cause. But at the
smallest size the elements sit closer to the middle and at the largest
slightly closer to the edges than at 100%: their middles were kept, so their
outer edges moved. The mirror goes about half off the top at the largest.

IPA77 (`ios/build/NFSMW-hud-corners-77.ipa`, 30046523 bytes, SHA256 prefix
d9caf58e4a21feec, UUID 9F2A6248-D033-3655-9155-B24063E50C7D, `unzip -t` ok):
the kept point is each element's outer corner: x = middle + 76 units, y 215
(minimap, speedometer) or -213 (race info, top left). The mirror: its frame
(0x7FAC287B, inferred from the tree) moved in y so its top (-220) keeps its
margin (with the safe zone too), and the native renderer moves the mirror's
picture by as much (`nfsmw_mirror_shift_y`, of the screen's half height:
HUD units x 0.92/240 in HD, 1/240 at 4:3, x the size). Not yet run.

IPA77 result (Stefan, Oct 26, iPad): the HUD scales correctly in free roam
(corners and mirror kept). Starting a race crashed (log
`Debug/26 October 2026/nfsmw_ipa76_hud_race_crash_ipad.log`, named ipa76):
right after `HUDTEXRACE.BIN` loaded, "Unhandled guest access violation: read
of guest 0x0000011B", lr 0x822A8D5C (the return from sub_822AA6D0 in
sub_822A8C50, so inside the HUD hook), r3 = r4 = 0xBE8F9CB0, r31 = 0.
Inference: the race HUD was built at the free-roam package's address, so the
cached pieces were not looked up again and MoveGroup read a freed piece's
data pointer (small garbage, + 28/32 = 0x11B).

IPA78 (`ios/build/NFSMW-hud-race-fix-78.ipa`, 30047117 bytes, SHA256 prefix
f02e3358106a3a80, UUID 13CD6D6C-9BE7-3A01-9679-773C6E9E6BDE, `unzip -t` ok):
the pieces are found again when the package, either group, or any piece's
vtable or name hash differs from when found (checked every frame); MoveGroup
and the minimap's children only follow plausible heap pointers. Not yet run.

IPA78 result (Stefan, Oct 26, iPad): races work, scaling as in free roam.
Minor: at the smallest size, loading into a race, the game shows through at
the top and bottom of the black loading screen (the HUD matrix shrinks it).
Loading.fng and WS_Loading.fng are already "menus" (game_state.cpp) and none
was logged before the IPA77 crash, so the black screen is another package.
The game's image (`NFSMW_DUMP_IMAGE`, run from a scratch copy of the
manifest with the Mac rexglue and `DYLD_LIBRARY_PATH` at its Release folder)
lists FadeScreen.fng, FadeScreenNoLoadingBar.fng, BLACK_BACKGROUND.fng,
BLACK_FADE_OUT.fng (also Loading_Tips, Loading_Controller, MW_LS_Splash).

IPA79 (`ios/build/NFSMW-hud-fade-79.ipa`, 30058419 bytes, SHA256 prefix
890c72a64d3ab4a9, UUID A06DB669-25E2-3568-BE90-F1C4CD9D5D0A, `unzip -t` ok):
game_state.cpp also asks, in the world and outside menus, whether one of
those four fade packages is up (`nfsmw_fade_up`, logged `[game] fade ...`,
40 lines at most); the HUD matrix keeps size 1 meanwhile. Not menus, so the
frame cap and touch layout are unchanged. Inference to check in the log:
which one is the pre-race black screen. Not yet run.

IPA79 result (Stefan, Oct 26, iPad, 70%; log
`Debug/26 October 2026/nfsmw_ipa_79_loading_screen_ipad.log`,
ipa79_broken_race_min_hud.png): the loading screen was fine, but in the race
the HUD was at full size with the 70% offsets, so its pieces sat off the
screen. The log has `[game] fade FadeScreen.fng` as the world started and no
"gone" afterwards: the package stays pushed for the whole race.

IPA80 (`ios/build/NFSMW-hud-fade-hold-80.ipa`, 30058319 bytes, SHA256 prefix
1142e3c516283122, UUID A0E6287A-3073-3ED5-BA26-052158A100FD, `unzip -t` ok):
game_state.cpp counts the world's starts and ends and each coming of a fade
package (`nfsmw_world_fades`; fades not asked about under a menu, so a pause
does not count); the HUD matrix keeps size 1 for 3 s after a change of that
count or a new HUD package (the pieces found again). Expected: the HUD shows
at 100% for ~3 s at the start of a race, then takes the chosen size. Not
yet run.

IPA80 result (Stefan, Oct 26, iPad): as expected, the HUD shows at 100% for
3 s at a race's start, then takes the size; Stefan: not nice looking.

IPA81 (`ios/build/NFSMW-hud-fade-fit-81.ipa`, 30050240 bytes, SHA256 prefix
e6806c410a5dfea7, UUID FAE1F971-36FD-3E1D-AC74-8DB3101E9630, `unzip -t` ok):
the hold is gone. While a fade package
is pushed in the world, game_state.cpp finds it (sub_82284CA8,
FindPackage(cFEng, name); the HUD's own "package" at hud+36 is its name,
0x8207BFC8 = "HUD_SingleRace.fng") and game_scene_size.cpp finds its object
list by the list header (vtable 0x82080030, count, first) within its first
0x200 bytes, logs it once (`[hud] fade package ...` and its objects), and
divides the position and size of each top-level image 400 units wide or more
(the black screen, inferred) by the HUD's size, so the matrix draws it as at
size 1. Not yet run; if the log shows no list or no wide image, the black
screen is elsewhere in the package.

IPA81 result (Stefan, Oct 26, iPad; log
`Debug/26 October 2026/nfsmw_ipa81_loading_hud.log`): the picture still shows
through. `[hud] fade package BE909B60: objects list at +44, first BE909920`
(found as expected), and its tree: top level 6A0831F6 (217,-148; the loading
bar and its text, a 1200x46 bar in D2C6710F > B8AF84C3) and 027FF2DC
(115.4,68.4) holding EB4CF244 and 54EB3AF6, two 1200x650 images at
(-116,-69): the black screen, inside a group, which IPA81 did not look into.

IPA82 (`ios/build/NFSMW-hud-fade-fit-82.ipa`, 30050588 bytes, SHA256 prefix
86f78bbc4132e326, UUID DE47FEE5-3402-3037-8B6A-BBBD515242D5, `unzip -t` ok):
images 400 units wide or more anywhere in the package (groups 4 deep) get
position and size / s, and the groups holding them position / s (their size
left: it may be a scale). Open risk: a still image may keep its old layout
(as the HUD's still pieces did, IPA75). Not yet run.

IPA82 result (Stefan, Oct 26, iPad; log
`Debug/26 October 2026/nfsmw_ipa82_hud_ipad.log`, ipa82_hud_ipad.png): the
picture still showed through, for less time, at the very end of the loading
screen. New: the song's name (EA_Trax.fng, its own package over the HUD) keeps
the matrix's scaling about the middle, not the safe zone; the radar
detector's green arcs (the HUD's middle group 0xAB9C1D4D, child 062743F5 at
y -141 from the middle, under the mirror) did not follow the mirror's frame.

IPA83 (`ios/build/NFSMW-hud-overlays-83.ipa`, 30063553 bytes, SHA256 prefix
aa46c7723c1cfa29, UUID BFC0BD9D-9763-3750-95B2-1F3143DE7B81, `unzip -t` ok):
- every fade package that is up is fitted (not only the first), and while a
  fitted black image's alpha (FEColor at data+0, a at +12, inferred) is 255
  the HUD matrix keeps size 1 (logged `[hud] fade ...: black screen up /
  fading`); no fade up clears it.
- EA_Trax.fng, while pushed and driving: each top-level object's extent
  (images by size, text as points, groups recursively) gives its outer
  corner a, and it is moved by d with s * (a + d) = k * a (logged once with
  its tree: `[hud] overlay package`).
- the middle group's children become pieces: above -60 units with the
  mirror (top edge -220), below +60 with the bottom edge (215), in between
  left alone.
Not yet run.

IPA83 result (Stefan, Oct 26, iPad, smallest size; log
`Debug/26 October 2026/nfsmw_ipa83_broken_hud_ipad.log`, ipa_83_broken_hud.png):
the race HUD was at full size with the small size's offsets (off the
screen). `[hud] fade BE909B60: black screen up (alpha 255)` and never
"fading": FadeScreen.fng's black images keep alpha 255 the whole race, so the
alpha is not what hides them. EA_Trax.fng was found (`overlay package
BE8D73E0`, list at +44): a text at (266,-269) and the song box group
A1341735 at (-203,-191).

IPA84 (`ios/build/NFSMW-hud-overlays-84.ipa`, 30063250 bytes, SHA256 prefix
939e8f5ba7161061, UUID D08AB079-6B1A-3CEC-B1ED-6717541FF21B, `unzip -t` ok):
the alpha hold removed (still logged); the rest of IPA83 kept. The bleed at
the end of the loading screen (IPA82) is back; open: what hides the black
screen (flags at +0x1C, the package's own state). Not yet run.

IPA84 result (Stefan, Oct 26, iPad): all good apart from the short bleed at
the end of the loading screen. Stefan: the HUD is finished for now
(functional, not its final form; BACKLOG keeps the rest).

### October 26: post-processing switch

The switch (`postprocessing` -> `nfsmw_sin_posprocesado`) did nothing
visible (Stefan). Reading the code: the byte 0x828F48B2 that the Xenia
"Disable Post Processing" patch clears only chooses, in sub_822246F0, the
technique "visualtreatment_branching" over "visualtreatment" (0x82075510,
0x8207552C, in the image's strings next to the post chain's: downscale,
blur, brightpass, bloom, calculate_luminance, finalhdrpass, UVESVIGNETTE),
and sub_822241A0 also has to say the branch is needed; sub_82224380 passes
it on as a shader bool. So the colour filter, bloom and vignette stay
either way. The post chain is run by sub_82442310 (the same function that
builds the HUD matrix): the byte at +9 of its argument gates the bloom chain
(sub_82224C00) and the visual treatment (sub_822246F0 with r4 = 1); with it
0 the function takes its other path.

IPA85 (`ios/build/NFSMW-no-post-85.ipa`, 30063575 bytes, SHA256 prefix
646f10859c651317, UUID FCCE461C-26AD-323F-A972-85077586777F, `unzip -t` ok):
with the switch off, that byte reads 0 while sub_82442310 runs
(game_scene_size.cpp, USA addresses: tools/ediciones refused a new address
in game_hooks.cpp, which is translated from the reference edition); logged
`[post] frame without post-processing: view byte +9 was N`. The switch is in
the in-game menu, live (the cvar is read every frame). Risk: the other path
may need pipelines not yet compiled (a few frames missing) or show the scene
unexposed/too dark. Not yet run.

IPA85 result (Stefan, Oct 26, iPad; log
`Debug/26 October 2026/nfsmwipa85_no_post_ipad.log`, ipa85_no_post_ipad.png):
with Post-processing off the picture has no colour filter, bloom or
vignette; Stefan: "looks just like no post processing should". `[post]` lines
logged (the first two in the frontend, byte +9 already 0 there). A 5 s
`[vigilante]` stall at 18:13:02, during startup/loading, not looked into
(not seen as a problem by Stefan).

### October 26: uneven 60 fps frame pacing (IPA86)

Stefan (iPad): at the 60 cap the counter reads 60 and the frame time moves
16.6-16.8 ms, but there are smooth moments and choppier ones; the 40 cap
does not do it. The renderer's presented-time statistics (`[native] pacing`,
every 300 shown frames, from `presentedTime`) already see this. iPad race
logs `Debug/26 October 2026/nfsmw_ipa64_race{1,2,3}_ipad.log`,
`nfsmw_ipa73_hud_race_ipad.log`, `nfsmw_ipa82_hud_ipad.log`: most 300-frame
windows have 2-6 frames off the 16.7 ms grid, with gaps in 120 Hz refreshes
like `1:1 2:298 3:1` / `1:2 2:296 3:2`, i.e. a frame held one 120 Hz refresh
late (25 ms) followed by one 8.3 ms later: a stutter pair every 1-3 s,
invisible in average fps and in the >40 ms hitch counts. (Odd refresh
counts also mean the panel ran at 120 Hz although the link asked 60.)
At 60 the guest vblank is the SDK timer, not the display (only 30/40 were
locked, `patch_ios_vblank_display`): the same drift that made the 40 cap
land a frame a refresh late before it was locked.

IPA86 (`ios/build/NFSMW-pacing-60-86.ipa`, 30065097 bytes, SHA256 prefix
b847ee93aafd1b78, UUID 9F0D1D4B-CC3C-3FA0-A88C-9069A643E1EC, `unzip -t` ok,
codesign ok, 208 metallib entries): `patch_ios_vblank_display` locks the 60
cap too (cvar `ios_vblank_lock_60`, default on; needs
`ios_vblank_from_display`); `display_rate.mm` publishes the refresh period
split to 60 Hz at the 60 cap (so a 120 Hz link still locks); the fps cap's
"a late frame is shown at once" rule is unchanged. The log says
`[ios-vblank] cap 60: guest vblank locked to the display refresh` and, for
the first 120 off-grid frames, `[native] off grid: frame N shown X ms after
the one before (the one before: Y ms)`. Test: one race with defaults, one
with `--ios_vblank_lock_60=false`; compare off-grid counts and feel. Risk: a
frame that misses its refresh now meets a refresh-aligned vblank; watch for
more 33 ms gaps (`gaps ... 4:`) under load. Not yet run.

IPA86 result (Stefan, Oct 26, iPad, one race, cap 60, FPS counter on; log
`Debug/26 October 2026/nfsmw_ipa86_frame_pacing.log`): "didn't change much",
prolonged choppy moments near the end that the counters did not show. The
lock engaged (`[ios-vblank] cap 60: ... locked (16.67 ms)`), yet the race
still has the 25 + 8.3 ms pairs (21 in the 120 logged off-grid lines). 19 of
the 21 are shown at second fractions .023 or .523: a 0.5 s period. The
on-screen FPS counter (`NFSFpsLabel`, touch_controls.mm) is a UILabel that a
0.5 s NSTimer re-texts and re-frames; when the text changes (e.g. 16.6 ->
16.8 ms) the UIKit commit evidently delays the Metal frame of that refresh by
one 120 Hz refresh. Hypothesis, not yet isolated: the counter causes the
stutter it is meant to show, and "choppy moments" are stretches where the
ms text changes at every tick. The vblank lock is not what helps or hurts
here. Next: one race with the FPS counter off (no build needed).

IPA86 with the FPS counter off (Stefan, Oct 26, iPad, one race; log
`Debug/26 October 2026/nfsmw_ipa86_fps_counter_off.log`): "a few isolated
hitches, but those moments of choppiness weren't present" (Stefan unsure if
placebo). Log: 25 + 8.3 ms pairs fell from 21 (counter on) to 1, none on the
0.5 s phase; 67 off-grid frames in 18 windows against 99 in 19, most of them
in the first 20 s (loading, 117-158 ms hitches); after that 13 of 15
windows have 0. Confirmed: the counter's text changes caused the pairs. The
IPA86 vblank lock was on in both runs, so its own effect is not isolated;
kept on (no harm seen).

IPA87 (`ios/build/NFSMW-fps-counter-87.ipa`, 30064846 bytes, SHA256 prefix
25f8c03c4040f20e, UUID 9C1B527E-0352-3A0C-961C-3675E25BC8BA, `unzip -t` ok,
codesign ok, 208 metallib entries): `NFSFpsLabel` keeps its rounded
background on the layer without `masksToBounds` (which renders the label
off screen in the compositor whenever the text changes), sizes its frame
once for the widest text, and sets text/frame only when they change. Test:
one race with the counter on; success = no 25 + 8.3 ms pairs at .023/.523.
If they stay, next step is drawing the counter into the game's Metal frame.
Not yet run.

IPA87 result (Stefan, Oct 26, iPad; log
`Debug/26 October 2026/nfsmw_ipa_87_fps_counter_broken_choppy_ipad.png` and
`nfsmw_ipa_87_fps_counter_broken_choppy_ipad.log`): worse. The counter's old
and new texts showed on top of each other (a UILabel with no background
colour does not clear its old text), and the choppy stretches were more
frequent. Log: 22 pairs of 25 + 8.3 ms, 15 of them on the counter's 0.5 s
phase (.963/.463 this run), 103 off-grid frames in 21 windows. Any UIKit
update over the game's layer seems to cost the game's frame its refresh.
IPA87's label change reverted.

IPA88 (`ios/build/NFSMW-fps-in-frame-88.ipa`, 30055438 bytes, SHA256 prefix
943c7e134aa1f02d, UUID BDBB615F-A4D6-3578-9606-6F8D821C8FE3, `unzip -t` ok,
codesign ok, 208 metallib entries): with the native layer showing, the
counter is drawn into the game's frame. The label's 0.5 s timer still
formats the text; when it changes it is drawn with Core Graphics into a
BGRA bitmap (white on a near-black box, no rounded corners) and handed to
the renderer (`nfsmw_native_set_fps_overlay`), which makes a new small
texture and draws it with the present pipeline in its own viewport after
the picture. The label stays hidden and untouched (no text or frame
changes); with the emulated renderer it works as before. Test: race with
the counter on; success = no pairs on the 0.5 s phase. Not yet run.

IPA88 result (Stefan, Oct 26, iPad, 1x render scale; log
`Debug/26 October 2026/nfsmw_ipa88_fps_in_frame_ipad.log`): the counter
works and seems to catch smaller hitches, but is visibly low-resolution (the
bitmap was made at the screen's scale and shrunk into the 1x frame); the
first ~20 s of the race were still very choppy. Log: 8 pairs of 25 + 8.3
ms, none on a 0.5 s phase (the counter's pairs are gone); from 18:45:58 most
windows have 0-2 off-grid frames. The race start (18:45:38-56) has 33 ms
frames (`4:` 1-3 per window) and two texture-decode hitches: frame 670,
116 ms between swaps, 148 textures / 54.8 MiB decoded (96.7 ms) and 23.5 ms
of uploads; frame 1392, 110 ms, 236 textures / 61.6 MiB (83.3 ms) and 24.9
ms of uploads. So the race start's choppiness is first-use texture
decoding/uploading plus smaller (33 ms) misses the log does not explain;
an Instruments trace of the race start is the next step.

IPA89 (`ios/build/NFSMW-sharp-counter-89.ipa`, 30065730 bytes, SHA256
prefix 679c8ec782481a19, UUID 75B7CB51-68E9-3577-BFD3-0919B2531096, `unzip
-t` ok, codesign ok, 208 metallib entries): the counter's bitmap is made at
the shown frame's resolution (`nfsmw_native_drawable_width`), one bitmap
pixel per frame pixel. At 1x it is still the frame's resolution, below the
screen's. Not yet run.

IPA89 result and Game Performance trace (Stefan, Oct 26, iPad, 1x, cap 60;
`Debug/26 October 2026/ipa89_game_performance_ipad.trace` (73.6 s from
18:52:50) and `nfsmw_ipa89_race_game_performance_ipad.log`): the counter
looks even blurrier (one bitmap pixel per frame pixel at 1x is coarser than
the screen-scale bitmap; the frame itself is below screen resolution), so
an in-frame counter cannot be sharp at low render scales. Trace: thermal
state Nominal throughout; no graphics-compiler activity (no shader
compiles); the displayed surfaces (3200x2400, direct to display) are 16.67
ms apart almost always: per 5 s, 0-4 frames held 33 ms and 0-2 pairs of
8.3/25 ms, the most in 20-55 s (the race's first ~20-30 s, matching the
log's 18:53:13-18:53:38 windows with 2-6 off-grid). One 166 ms gap at
race start (frame 3534: 252 textures, 61.8 MiB decoded, 32.8 ms of
uploads). The per-frame off-grid log was used up by loading (120-line
cap). So the screen gets an even 60 fps apart from a dropped frame every
1-3 s at the race start; that alone seems too little for "very bad
choppiness". Hypothesis to check with Stefan: the judder is in the content
(e.g. other cars or parts of the scene updated at a lower rate than 60,
as the Xbox 360 game ran at 30), which display timing cannot show.

Stefan (Oct 26): the whole screen looks choppy in the race's first ~20 s,
not just other cars. The game reads the real clock (it imports
KeQueryPerformanceFrequency; the recompiled code reads the timebase), so if
the game reaches its swaps unevenly, each frame's motion step is uneven
even though the screen shows the frames 16.7 ms apart: a judder neither
the display trace nor the fps counter can see.

IPA90 (`ios/build/NFSMW-swap-periods-90.ipa`, 30066262 bytes, SHA256 prefix
5cd6a575021d69bb, UUID 32A65BB5-F0A0-3409-B8C1-2B891862D43C, `unzip -t` ok,
codesign ok, 208 metallib entries), diagnostic: every 300 swaps `[native]
swap periods: mean, spread (sd), min-max | bands <12 ... 30+` (swap entry to
swap entry). Even motion needs nearly all in 16.2-17.2. Also the counter
bitmap is back at the screen's scale (IPA88; IPA89's frame resolution was
blurrier). Test: one race; compare the race start's swap periods with the
later, smooth part. Not yet run.

IPA90 result (Stefan, Oct 26, iPad, cap 60; log
`Debug/26 October 2026/nfsmw_ipa90_race_stutter.log`): the choppiness comes
at random through the race, not only at the start. Swap periods: mean 16.67
ms, spread 0.40-0.55 ms in nearly every window (about 15% at ~15.7 and 15%
at ~17.7 ms, the rest 16.2-17.2, in smooth and choppy parts alike); a few
windows (19:55:23-19:55:53) have single 21-23 ms / 11-12 ms periods. The
presented frames are on the 16.7 ms grid (0 off-grid) in most windows. So
neither the game's frame timing nor frame delivery shows the random
choppiness. Post-processing (motion blur) was on.

Remaining lead: at the 60 cap the app asks the display for 60 Hz, and the
120 Hz panel still ran at 120 at times (odd refresh counts and 8.3 ms
displayed intervals in the IPA64-89 logs and the IPA89 trace), i.e. iOS
switches the panel's rate while playing; the 40 cap (smooth, Stefan) asks
a steady 120. IPA91 (`ios/build/NFSMW-120hz-at-60-91.ipa`, 30055878 bytes,
SHA256 prefix cf377cd29f579200, UUID 01B30646-5594-3983-BE64-A38A361FC95D,
`unzip -t` ok, codesign ok, 208 metallib entries): at the 60 cap the link
asks 120 Hz (range 80-120; cvar `ios_display_120_at_60`, default on; off
with `--ios_display_120_at_60=false`); the guest vblank stays 60 Hz,
locked to every other refresh (display_rate.mm publishes every other tick
with twice the period). Expect a little more display power. Not yet run.

IPA91 result (Stefan, Oct 26, iPad, cap 60; log
`Debug/26 October 2026/nfsmw_ipa91_race_Stutter_ipad.log`): "still looks
like it's skipping frames". The display ran a steady 120 Hz (`refresh now
120 Hz`), the guest vblank locked (16.67 ms), and every pacing window of
the race is `0 of 300 off ... 2:300`: every frame shown exactly 16.7 ms
after the one before. Swap periods sd 0.40-0.64 ms, the same ~15.7/~17.7 ms
bimodal pattern as IPA90. So frame delivery is now perfect and the
"skipped frames" must be in the content: the picture's motion does not
advance evenly from frame to frame. Leading hypothesis (untested): the game
steps its simulation in fixed ticks from the real clock (an accumulator);
with frame periods jittering about +-1 ms around one tick, a frame
sometimes gets no tick (a repeated picture) and the next two (a jump),
in stretches that come and go as the accumulator's phase drifts. Next:
find the game's frame-time code (its timebase / KeQuerySystemTime reads and
any fixed step) and log ticks per frame, or remove the 1 ms jitter at its
source. Also seen: the race-finish background (asphalt and leaves) is
letterboxed top and bottom on the iPad (screenshot
`ipa_91_finish_race_wrong_aspect_ratio.png`); Stefan: it filled the iPad
screen before (on 19.5:9 iPhones it bled at the sides). Not investigated;
likely from the HUD/scene-size work (IPA70-85).

Game timing, first look (Oct 26, Stefan approved digging into it): the
game reads the timebase inline (`mftb` in ~80 places, mostly `>> 2`, e.g.
sub_820E0008, a bare ticker; sub_8284DE88 is QueryPerformanceCounter with
38 library callers). No single frame-time function found yet. Before
reverse engineering further, a direct test of the fixed-step hypothesis:
IPA92 (`ios/build/NFSMW-repeated-frames-92.ipa`, 30056278 bytes, SHA256
prefix 73a8db35a8ee1fd6, UUID 2B42AB94-DB4B-35F1-BCE2-28E9ACF7CE6F, `unzip
-t` ok, codesign ok, 208 metallib entries) sums, per frame, a hash of each
draw's c0-c15 vertex constants (its matrices) and logs every 300 frames
with over 100 draws `[native] content: N of 300 frames repeat the previous
frame's picture (R times, longest L in a row)`. While driving, N > 0 means
the game drew a frame without moving its world (the "skipped frames"); 0
would rule the hypothesis out. Cost: 64 dwords hashed per draw. Not yet
run.

IPA92 result (Stefan, Oct 26 night, iPad, cap 60; log
`Debug/26 October 2026/nfsmw_ipa92_race_stutter_ipad.log`; Stefan is sure
of the choppiness in the race's last ~20 s): `[native] content: 0 of 300
frames repeat` in every window of the race, including the last 20 s;
pacing 0 off-grid (one window 2, a single 8.8/26 ms swap pair at 01:35:29);
swap periods sd 0.40-0.52 ms. So the game draws a new picture every frame,
reaches its swaps evenly and every frame is shown 16.7 ms apart: the
fixed-step (repeated frame) hypothesis is ruled out. What the logs cannot
see: unequal motion steps between distinct frames (a frame moving the world
by 1.5 ticks and the next by 0.5) and perception (60 fps held for two
refreshes on a 120 Hz panel). No measured delivery or timing fault remains.

Wrap-up (Stefan, Oct 26 night): keep the in-frame FPS counter (IPA88/90:
it did cause the 0.5 s stutter pairs); turn off the steady 120 Hz at 60
and the diagnostics. IPA93 (`ios/build/NFSMW-pacing-cleanup-93.ipa`):
`ios_display_120_at_60` default false (60 cap asks 60 Hz again; on with
`--ios_display_120_at_60=true`); the swap-period and repeated-picture
logging behind `nfsmw_native_frame_timing_log` (default false). Kept: the
60 cap's vblank lock (IPA86, `ios_vblank_lock_60`, no harm seen), the
per-frame off-grid lines (first 120) and the in-frame counter at screen
scale. Remaining choppiness unexplained (no delivery, timing or repeated
frame fault measured); untested suggestion: compare with the 120 fps cap.
Still to do: a sharp counter on its own layer.

October 27: 120 fps and 120 Hz simulation (Stefan, iPad, IPA93; logs in
`Debug/27 October 2026/`). 120 fps cap with 60 Hz simulation
(`nfsmw_ipa93_120fps_race_ipad.log`): dips to ~100 fps (13:44:16-48, up to
35 of 300 frames at two refreshes); CPU 118-160% of a core. 120 fps with
120 Hz simulation (`nfsmw_ipa93_120fps_120hz_ipad.log`, Extra Args with the
three Utility QoS switches off, adaptive QoS still on): "incredibly
smooth", 3% battery in a ~1:10 lap; CPU 123-267%. 60 fps with 120 Hz
simulation, without and with the QoS Extra Args
(`nfsmw_ipa93_120hz_60fps_no_extra_args_ipad.log`, `..._extra_args_ipad.log`):
both "felt amazing", i.e. the 60 fps choppiness gone; CPU in the race 65-84%
and 62-80% of a core (the same within noise). Yesterday's 60 fps / 60 Hz
races (IPA85-92) logged 134-176%, with every thread about twice as busy
(GPU Commands 29% vs 11%, same ~2100 draws), which the simulation rate
cannot explain: not a matched comparison (other day, battery 100% vs 65%).
Explanation (consistent, not proven): NFSMW steps its world in fixed 1/60
s ticks from the real clock; at 60 fps with frame periods jittering about
+-1 ms the number of ticks per frame occasionally changes, while with 1/120
ticks each frame gets two and a change is half as large. Next: a matched
IPA93 60 fps / 60 Hz run for CPU; check that 120 Hz simulation at 60 fps
keeps normal game speed (lap times).

Matched 60 fps / 60 Hz run (Stefan, Oct 27, iPad, IPA93; log
`Debug/27 October 2026/nfsmw_ipa93_60hz_60fps_extra_args.log`): skipped-
looking frames seen again at times. CPU in the race 64-82% of a core, the
same as 120 Hz simulation at 60 fps (62-84%): no measurable CPU cost for
120 Hz simulation. All of today's runs had the three Utility QoS switches
off (Stefan had left the Extra Args in); yesterday's 134-176% had them on
(Utility threads on efficiency cores read as more "% of a core", not
necessarily more energy). Stefan: at 60 fps the QoS settings only helped.
Clue (Stefan, Oct 26, doing donuts): only the main picture judders; the
rear-view mirror stays smooth. The mirror view is fixed to the car, the
main view is the chase camera, so the judder is the chase camera moving
unevenly against the world at 60 Hz steps (its own real-time smoothing,
presumably).

IPA94 (`ios/build/NFSMW-sim-120-default-94.ipa`, 30056611 bytes, SHA256
prefix 4ed4fcb54ecbf2b1, UUID D2CDAE1E-E4BB-3F4E-B44C-26DAAA5AE741, `unzip
-t` ok, codesign ok, 208 metallib entries): 120 Hz simulation is the
default (launcher switch "120 Hz simulation" on for new settings; cvar
`nfsmw_sim_rate` default 120). Existing launcher settings keep their
value. Needs a longer play test (game speed, physics, AI, pursuits).

### October 27: what the Black Edition flag does (investigation, no code change)

Static read of the generated USA code (`ios/generated/default`). The patch's
32-bit write of 0x00000100 to `0x82A2CE04` sets byte `0x82A2CE06` to 1 (bytes
CE04, CE05 and CE07 become 0). Readers of that byte (`lbz rX,-12794` after
`lis rY,-32093`): `sub_8226A548`, `sub_82259408`, `sub_822C5CC0`,
`sub_822C62D8`, `sub_822E8D48`, `sub_822EA0E8`, `sub_822EAA60`,
`sub_822EAB88`, `sub_822EAC88`, `sub_823AF000`, `sub_8253C5F8`,
`sub_82568690`, `sub_8257A420`. The game's initializer (`nfsmw_recomp.58.cpp`)
writes CE00, CE01, CE02 and CE08, not CE06, so nothing resets the flag.
`sub_822EAA60` returns 1 when the flag is set and the car passes the normal
check; `sub_822EA0E8` ORs in `flag && sub_822EABD0(key)`, a hardcoded switch
over 10 car keys (list in BACKLOG D-007). The flag only marks those cars as
downloaded/owned; it adds no assets. Negative: the 10 keys match none of the PC
`CARS` folder names under bStringHash (init 0 or 0xFFFFFFFF, x31/x33/x131) or
Jenkins lookup2 with init 0xABCDEF00, with or without suffixes. The 360 ISO is
not on the Mac, so the disc's car folders were not checked.

Disc layout (Oct 27): `NFS/ZDIR.BIN` is 24-byte entries (path hash, archive
number, two offsets, size, checksum), sorted by hash; the hash is bStringHash
(init 0xFFFFFFFF, x33) of the uppercase path with backslashes, e.g.
`CARS\BMWM3GTRE46\GEOMETRY.BIN`. Every Black Edition car folder from the PC
copy is on the USA 360 disc; see BACKLOG D-007.

### October 27: IPA95 Black Edition event probe (temporary, D-007)

`ios/src/game_be_probe.cpp` wraps `sub_822EAA60` (event availability) and logs
each distinct (event key, caller, result) once as `[be-probe]`, with the flag
byte at `0x82A2CE06`. Built `ios/build/NFSMW-be-probe-95.ipa`, UUID
84A1B7D7-4CD2-33DA-85BB-67B135FD8716, SHA256 2905095dba746485..., ZIP test
OK, 208 metallibs. Test: Black Edition on, fresh profile, open Challenge
Series and scroll to the end. Remove the probe once D-007 is understood.

IPA95 result (Oct 27, iPad): 70 `[be-probe]` lines from the Challenge Series
list (caller 0x8256AA50); 68 events -> 1, `19.8.31` and `19.9.70` -> 0, flag
byte 0x82A2CE06 = 0 in every line. The Black Edition patch writes a host-endian
uint32, which sets byte 0x82A2CE05 instead (see BACKLOG D-007).

### October 27: IPA96 Black Edition flag fix (D-007)

`common/src/nfsmw_app.h` now writes the four guest bytes 00 00 01 00 at
`0x82A2CE04` one by one (byte CE06 = 1, as Xenia's be32 write), instead of a
host-endian uint32 that set CE05. The IPA95 probe stays in to show the flag.
Built `ios/build/NFSMW-be-flag-fix-96.ipa`, UUID
1A18D1C7-D979-36C6-AC68-2EEE5CCDCF93, SHA256 b3398d4913c80bd2..., ZIP test
OK, 208 metallibs. To test: fresh profile with Black Edition on; expect
`[be-probe] ... 19.9.70 ... -> 1 (flag 1` and 70 Challenge Series events,
then Quick Race cars and starting a career (the record pool overflow may no
longer happen).

IPA96 result (Stefan, iPad, Oct 27): fresh profile with Black Edition on, the
Camaro challenge (event 70) shows, the Black Edition cars are in Quick Race and
the career starts. The temporary probe (`game_be_probe.cpp`) is removed. Open:
whether the record pool overflow still happens now that CE05 is no longer set.

### October 27: IPA97 Black Edition always on

Stefan: a save made with the switch off (BEPPY) loads with it on and has all
the content, so the switch is gone. `ios/src/launcher.mm` no longer lists it
and always passes `--black_edition=true` (`extra_args.txt` can still pass
false). No temporary probe. Built `ios/build/NFSMW-be-always-on-97.ipa`, UUID
B5067ADE-65F8-3178-A5B0-EB23EABC2C42, SHA256 e87187c039374a3f..., ZIP test
OK, 208 metallibs. Untested on device.

### October 27: IPA98 save manager, extras file and sync after saving (D-008)

Stefan: a save that differs between iPad and iPhone only by a Challenge Series
event is not seen as newer on the other device, which also shows an older
date. Inference from the code (not reproduced): `game_pool.cpp` writes the
record-pool overflow to `Documents/save_extras/<NAME>.pool` when the game
creates a save; `save_manager.mm` hashed, dated and copied only the save
folder and header, so that file was never compared, backed up, exported or
synced. Second gap: uploads only ran at launcher start (`AutoSync`).

Change (`ios/src/save_manager.mm`, `.h`, `ios/src/game_pool.cpp`): a save is
now folder + header + extras (`Place`, `CopySave`; copies keep `<NAME>.pool`
beside `<NAME>.header`). The extras file is hashed last under a fixed name, so
saves without one keep their old hash; a save with one gets a new hash once
(expect one "changed on both sides" prompt on the second device). Copying a
save without extras removes stale extras at the destination. Delete removes it.
`SyncAfterGameSave()` runs `AutoSync` (backups + iCloud upload) 10 s after the
last save-create event, on a utility-QoS queue. No switch.

Built `ios/build/NFSMW-save-sync-98.ipa`, UUID
B5BE6635-9C17-3160-9861-89B132587E0F, SHA256 ed8009319e9ecf43..., ZIP test OK,
208 metallibs. Build exit 0, only the pre-existing fpscr.h warning. Untested
on device. Test: finish a challenge on device A, wait ~15 s in game, open the
save manager on device B: the save should show "Newer in iCloud".

IPA98 result (Stefan, Oct 27): two-device sync works (a newer save is now seen
as newer). He asked why the delay is 10 s and noted saves deleted on every
device (NAME, TEST) stay listed as "Only in iCloud" with no way to delete them.

### October 27: IPA99 shorter sync delay, delete from iCloud

`SyncAfterGameSave` waits 3 s (was 10 s) after the last save-create event; the
event comes when the game creates the save, before it writes it, and the
debounce absorbs repeated saves. Tapping a save only in iCloud now offers
Download or Delete from iCloud (confirmed; removes `NFSMW Saves/<id>` with a
coordinated delete and its synced hash; local saves untouched). Built
`ios/build/NFSMW-save-cloud-delete-99.ipa`, UUID
D33159B4-CCCC-31B1-81B5-701AD30B12B3, SHA256 d9d3bc4db88c2b40..., ZIP test OK,
208 metallibs, build exit 0. Untested on device.

IPA99 result (Stefan, Oct 27): deleting saves only in iCloud works.

### October 27: IPA100 save manager redesign (step 2)

`ios/src/save_manager.mm`: sections are now Careers (this device's saves, then
those only in iCloud, in one list), iCloud Drive folder, Import. Each career:
name, cash/bounty, "This device: saved <date>", and when the copies differ
"iCloud: saved <date> on <device>" (device from info.plist, written by the
uploading device). Badge "Newer on <device>". iCloud-only careers read
cash/bounty from the iCloud copy with a coordinated read. Tap: for newer in
iCloud or changed on both, "Use the save from <device>" and "Keep this
device's save" come first; local-only/newer gets "Copy to iCloud now"; then
Back up, Restore, Export, Delete. Sync now moved to the navigation bar.
Built `ios/build/NFSMW-save-redesign-100.ipa`, UUID
B65A01FE-83C7-3BD7-B683-B23770CF5722, SHA256 6c08e19052cf2be7..., ZIP test OK,
208 metallibs, build exit 0. Not run on device or simulator.

IPA100 result (Stefan, Oct 27): the new screen is good; replaying a finished
race shows the new save time (16:07), which the old manager missed. He said
120 Hz simulation did not fix the 60 fps judder.

### October 27: IPA101 save import, 120 Hz simulation off by default

Import (`ios/src/save_manager.mm` `importFrom:`, new `ios/src/save_import.cpp`):
the picker takes folders, .zip and any data file. A .zip is unpacked with a
small reader (stored/deflate, zlib, `z` linked); a file starting `CON `,
`LIVE` or `PIRS` is unpacked with the SDK's `StfsContainerDevice`; anything
else is copied as is. The save is the first MC02 file found (depth 6),
preferring `<NAME>/<NAME>`; the header is taken from beside its folder or
Xenia's `<title>/Headers/00000001/`, otherwise written (0x148 bytes: HDD,
saved game, name, xuid 0, the target title id; checked against BEPPY.header).
Host check: `Unzip` on two zips of BEPPY (Finder-style and `zip -r`)
extracted byte-identical files. STFS and the whole import are untested (no
360 package at hand); whether the game takes another profile's save is
unknown.

120 Hz simulation: launcher switch moved to Advanced > Performance under a
new key `sim_120_hz` (default off; the old `sim_120` value is ignored);
the launcher passes 120 when it is on or the fps cap is 120. The cvar default
`nfsmw_sim_rate` is 60 again.

Built `ios/build/NFSMW-save-import-101.ipa`, UUID
52310492-DF86-3C2A-8A19-C4C69ED03826, SHA256 0a08ef11c06fcd6a..., ZIP test OK,
208 metallibs, build exit 0. Untested on device.

### October 27: IPA102 achievements merged across devices (D-009)

The SDK's `AchievementManager` loads `Documents/data/achievements/<title>.toml`
at start and rewrites it from memory on each unlock (`[unlocked.<id>]`,
`filetime = <n>`). The save manager's `AutoSync` now also merges that file with
`<iCloud folder>/NFSMW Achievements/<title>.toml`: union of ids, earliest
nonzero filetime, written to whichever side lacks something (coordinated
access on the iCloud side). Kept outside `NFSMW Saves/` so it is not listed as
a career. Limitation: an unlock during a run rewrites the local file from the
SDK's memory, dropping entries merged after start until the next sync; the
iCloud copy never loses one. Built `ios/build/NFSMW-achievement-sync-102.ipa`,
UUID A9F1E193-308C-3B24-B6BF-5B4D0B6C9401, SHA256 8ad0984a11878fa3..., ZIP
test OK, 208 metallibs, build exit 0. Untested on device.

IPA102 result (Stefan, Oct 27): after both devices synced, Vic (id 3) is
missing on both; the iCloud union file holds ids 1, 2, 4, 5 only. The Oct 16
iPad log shows `XGIUserWriteAchievements: id=3` and `Achievement unlocked:
00000003` at 03:20:49 (local, UTC+1 offset judged from id 5: log 16:43:06,
filetime 15:43:06 UTC), so the unlock happened and was lost later; cause not
found. Id 3 added by hand to `<iCloud folder>/NFSMW Achievements/454107D9.toml`
with filetime 134365908494400000 (2026-10-16 02:20:49.44 UTC); the devices
pick it up at their next sync.

### October 27: motion blur switch (IPA103)

Where the blur is decided (read in the generated code, USA addresses): the
visual treatment, sub_822246F0, picks "visualtreatment_branching" over
"visualtreatment" when the post byte 0x828F48B2 is 0 or sub_822241A0 says
so. sub_822241A0 reads the view's entry in the table 0x82C3F590 (384 bytes
per view, index r4; byte +4 = view in use) and returns 1 when either float
at +144/+148 exceeds 0.0001 (0x8290DBA0); two globals at 0x82A2C4E4/E8 (0.0 in
the image) override those floats when not 0. sub_82224240 scales the same two
values into the shader's blur vector (x, y, 1/y, 0), and when they are above
that threshold binds the blur texture (r3+512) and sets the effect's blur
bool. The shader also has MOTIONALPHA and IS_MOTIONBLUR_VIGNETTED parameters
(ids 87 and 67 in sub_8244B888's table; their setters not found) and the
image names `ENISMotionBlur` (cutscenes). Inference, not proven: the +144/+148
amounts are the motion blur Stefan sees; the mirror is a different view.

Change: cvar `nfsmw_motion_blur` (default true, game_scene_size.cpp). Off,
sub_822241A0 and sub_82224240 run with the view's two amounts and the two
override globals read 0 (restored after), so the plain technique is used, the
bool is false and no blur texture is bound. Logs `[blur] motion blur off:
view N blur amounts were x, y` (first 4 nonzero cases). Launcher switch
"Motion blur" (key `motion_blur`, Graphics, after Post-processing); also in
the in-game menu, live (cvar read on every call). Build exit 0; both hooks
linked as strong symbols (`nm -m`).

Built `ios/build/NFSMW-motion-blur-103.ipa`, 30093993 bytes, UUID
B5E9F031-B498-3BAA-9362-ECBED0A55F0B, SHA256 239f27fa08d225ba..., `unzip -t`
OK, 208 metallibs, codesign verify OK. Untested on device. Test: a race at
60 fps with Motion blur on, then off (in-game menu): visible blur at speed
gone, `[blur]` lines in the log, and whether the judder changes.

Stefan (Oct 27, quick test, build before IPA103): turning Post-processing off
also removes the motion blur, and the frame-skipping-like judder at 60 fps
was absent. One short run, no log; suggests the post chain causes the
judder but does not separate the blur from bloom/colour filter. Next: IPA103
with Post-processing on and Motion blur off isolates the blur.

IPA103 result (Stefan, Oct 27, iPad, Motion blur off; log
`Debug/27 October 2026/nfsmw_ipa103_motion_blur_off_ipad.log`): no motion
blur visible; Stefan could not tell whether the picture was fully smooth.
`[blur]` lines: view 1, values 50000.5547 and 99998.8906 (8 lines, 4 per
hooked function: each template copy has its own counter). The values are far
above the 0.0001 threshold and look more like distances than blur amounts;
what they are exactly is not known, but zeroing them removed the blur.
`[native] pacing` (22 windows of 300 frames, 16:32:16-16:34:02): 11 windows
with 0 frames off the 16.7 ms grid, 6 with 2-4 off (worst 4.2-16.7 ms), 5
with 6-62 off and 100-167 ms gaps (not matched to loading/race start here).
So the screen got an even 60 most of the time; blur on vs off was not
compared in pacing numbers.


## October 27, 2026: PC save import (into 0.4.0)

Developed on `dev-0.5` (full record there, in TECHNICAL: "PC vs Xbox 360
saves", "IPA105 PC save import", "IPA105 crash ...", "IPA106 result ...")
and brought here on Stefan's approval once it worked.

`ios/src/save_convert.cpp` converts a PC v1.3 save (63,596 bytes, `20CM`) to
the Xbox 360 layout (62,688 bytes, `MC02`, version 0x10D): every 2- and
4-byte value byte-swapped field by field, Lua table flag bits reordered,
0xCD fillers to 0xAA, header CRC32s and MD5s recomputed. The map follows the
Xbox loader's read order (sub_822C3A60 -> sub_822C2998 -> sub_822C2D30):
gameplay section 0x34-0x4034, cash and settings, profile id, race count and
300 records (0x42AD), unlock bytes, 63x12 words, alias, 30 records at
0x5A51, FEPlayerCarDB (PC 0x5BC5 / Xbox 0x5BCD, 36,040 bytes), then a byte,
3032 bytes of career stats and the current car of 11 modes. Taken from a
career on the device (the template): the header prelude, the check word at
0x5A2D (the loader refuses a value that differs from the game's), the
options block (132 bytes on PC, 140 on the Xbox) and the end of the tail.
Field map source: sprintstate/nfs-mw-save-editor (GPL-3.0), the dbalatoni13
nfsmw decompilation (CC0), the generated code.

Failed attempts kept: IPA105 crashed on load (race count left
little-endian: the loader's signed clamp let a negative count overrun a
stack buffer); IPA106 loaded but crashed after My Cars (template car handles
left in the 11 current-car slots). IPA107 (dev-0.5): works, Stefan on the
iPad: My Cars shows the save's 89 cars, career, racing and saving work.
Logs: `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/27 October 2026/nfsmw_ipa105_pc_save_crash_ipad.log`,
`nfsmw_ipa106_pc_save_missing_cars_crash_ipad.log`.

Import (`ios/src/save_manager.mm`): files starting `20CM` count as saves and
are converted with the first local career as template; none on the device
gives a message. Import failures now say why.

IPA108 (`ios/build/NFSMW-pc-save-import-108.ipa`, branch `frame-pacing-60`,
30093277 bytes, SHA256 prefix 165a17bfde4427f6, UUID
79034B76-F201-3BD9-80B8-2B1DBF5257AC, `unzip -t` ok), build exit 0: IPA103
plus PC save import; the binary has the import message and none of the 0.5
Extra Options cvars (`strings`). Not run on a device yet.

## October 27, 2026: 0.4.0 release build

Stefan approved (Oct 27) RELEASING steps 1-4; he publishes the GitHub
release himself. Version 0.4.0, code 4 (`ios/CMakeLists.txt`), CHANGELOG
"Unreleased" became 0.4.0, README version line.
- SDK `prepare_sdk.py --status` exit 0. Reported partial blocks, the same
  SDK tree as the tested IPA103-108 builds: `ios_timing` 11 of 15,
  `ios_ui_tick` 1 of 3, `ios_qos` 0 of 4 (replaced by `ios_utility_qos`,
  applied), `ios_save_log` 2 of 3 (the save create/open lines do appear in
  device logs). Not changed for the release.
- `ios_resolve_stats` defaults to true in its patch script, as in v0.3.0
  (RELEASING says diagnostics off); left as released before, noted here.
- Game patches: pool 63 of 63, extra-options fully applied (0.4 set, no
  `heat`).
- Build exit 0 (existing build dir, its configuration kept), `codesign
  --verify --deep --strict` ok, Info.plist com.bep1s.nfsmwios, 0.4.0 / 4,
  208 metallibs, `unzip -t` ok, `git status --ignored`: ios/build,
  ios/generated, assets ignored; nothing of the game tracked.
- `ios/build/NFS-Most-Wanted-0.4.0.ipa`, 30093267 bytes, SHA-256
  685328f8ceb4c96fc2a2e9cace64ceacc1c0cd59926752071903f12efbee54ca, UUID
  D0F38C8B-8764-3CB5-8495-03BA3D561288. Same sources as IPA108 plus the
  version bump; this exact file not installed on a device (RELEASING step 5's
  fresh-container race is Stefan's).

## October 27, 2026: 0.4.1 fixes from SpeedBreaker (IPA109)

Branch `release-0.4.1` off `main` (e0151ce). Source: SpeedBreaker
(github.com/SpeedBreakerProject/speedbreaker, GPL-3.0, same USA disc), v0.1.8
`runtime/apu/ea_cpu_budget.*` and v0.1.4 `runtime/video/vblank_timer.cpp`,
`presenter.cpp`; their findings, not re-measured here.

- EA SND budget (D-004). Checked in `ios/generated/default`: sub_82601528
  (`nfsmw_recomp.68.cpp`) computes f1 (fsubs, then fcmpu against a constant)
  and calls sub_82601788 (`nfsmw_recomp.71.cpp`), which saves f1 and r3 and
  calls sub_826016B8 (`.78`) and sub_825D04B8 (`.122`) in a loop: the same
  structure SpeedBreaker describes, so the USA addresses match. Hook in
  `ios/src/game_audio_budget.cpp` (USA addresses, not translated by
  tools/ediciones); the object defines a strong `_sub_82601788` (nm `T`).
- Vblank thread priority: `tools/ios/patch_ios_vblank_realtime.py`, applied to
  the SDK's `src/graphics/graphics_system.cpp`; period = 1/guest vblank rate
  at thread start, computation 1 ms, constraint 2 ms, preemptible.
- Pacing watchdog in `ios/src/native_renderer.mm` (the existing
  present-at-time grid; SpeedBreaker's present-after-vblank scheme was not
  copied because ours already locks the 60 cap's vblank to the display and
  paces on a presentedTime grid).
- Build `cmake --build --preset ios --target ipa -j 6` exit 0 (existing
  build dir; graphics_system.cpp, game_audio_budget.cpp, native_renderer.mm
  rebuilt). Strings present: `[ea-budget]`, `nfsmw_ea_cpu_budget`, `[native]
  pacing off`, and `[ios-vblank] real-time priority` / `ios_vblank_realtime`
  in `librexgpu-xenos.dylib`. Info.plist 0.4.1 / 5, 208 metallibs, `unzip -t`
  ok, `codesign --verify --deep --strict` ok.
- `ios/build/NFSMW-0.4.1-audio-pacing-109.ipa`, 30103705 bytes, SHA-256
  385ab46ee195aa5d708d0908894cdee2b5936a10935b5267fd45e6a86dcf37f3, UUID
  5031C546-2A4A-3676-AA5C-F8A9765CB08E. Not run on a device: whether the fade
  is gone, whether `thread_policy_set` succeeds on iOS and whether pacing gets
  more even are untested.

IPA109 first run (Oct 27, 23:16-23:20, Stefan: free roam and the test
race; Apple A19 Pro, so the iPhone 17 Pro Max; 60 cap, Battery group on). Log
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/27 October 2026/nfsmw_ipa109_freeroam_race.log`.
- `[ios-vblank] real-time priority (16.67 ms period): set` on both vblank
  threads (boot and game); 60 cap locked to the display.
- Pacing (paced, 50 windows of 300 frames): the first (loading) 255 off the
  grid, then 0 off in 33 windows, 1-6 in 13, 8-21 in 4 (23:18:56-23:19:16).
  The off frames are almost all 4-refresh (33 ms) gaps, i.e. missed frames,
  not uneven presents. The watchdog did not fire. 48 screen gaps of 50+ ms,
  clustered at loads and at 23:20:47 (texture decode hitch, 121 textures).
- `[ea-budget]` once, at 23:20:40.677, 1 ms after `[coreaudio] sudden drop:
  block peak -140.0 dB after -6.3 dB` (an end-of-race or scene change,
  inference). Without the fix EA would have expelled voices there.
- Not shown by this log: whether the engine sound stayed audible
  (Stefan's ears), and no A/B against `nfsmw_ea_cpu_budget=true` or
  `ios_vblank_realtime=false`.

## October 27, 2026: IPA110, issue #5 and iOS 18 target

- `common/src/nfsmw_app.h`: `PonerSiNadieLoPidio` checks
  `rex::cvar::GetFlagSource(name) != Source::kDefault` instead of
  `HasNonDefaultValue` (GitHub #5). The launcher passes
  `--readback_resolve=` on the command line (`ios/src/launcher.mm`), source
  kCommandLine, so Off now stays `none`. Not run yet.
- iOS 18: `CMAKE_OSX_DEPLOYMENT_TARGET` 18.0. Shaders: `sh
  tools/native/build_shaders.sh -` exit 0, 101 translated, the 3 `_dbg`
  variants rebuilt, all 104 libraries `apple-ios18.0.0`;
  constant_ranges, texture_masks, vertex_inputs, camera_constants identical
  to the IPA109 set (so the same translated shaders). `cmake --preset ios`
  then build exit 0 (899 steps): no unguarded-availability warnings, only
  deprecations (UIScreen.screens/setScreen:/connect notifications for the
  external display, CC_MD5 in save_convert). minos 18.0 for NFSMW,
  librexgpu-xenos, librexruntime; MoltenVK 14.0. Metal 3.1 needs iOS 17,
  residency sets iOS 18, MetalFX iOS 16; lodBias already behind
  `@available(iOS 26.0)`.
- `ios/build/NFSMW-0.4.1-ios18-110.ipa`, 30101026 bytes, SHA-256
  f07918eda76d983728fd6c9954ea9fb6126cdd82bcd817cfde6633c83d905526, UUID
  21164B43-FE9B-339D-899C-12545E646386, Info.plist MinimumOSVersion 18.0,
  208 metallibs, `unzip -t` ok, codesign ok. Not run on any device; whether
  it runs on iOS 18 is unknown (runtime-only failures, e.g. a shader
  library the OS cannot load, would only show there).

IPA110 on the iPhone 17 Pro Max (iOS 27.2), Oct 27 23:50-23:53, two
sessions (log `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/27 October 2026/nfsmw_ipa110_iphone.log`,
which also holds the IPA109 run; screenshot `ipa110_metal_hud.png` there).
Stefan: works. Log: build Oct 27 23:45, real-time vblank set, no shader
library load failures, `[ea-budget]` once (23:53:03). Pacing after loading:
0-5 of 300 off. GPU 13-15 ms/frame driving at 1x. Apple's Metal HUD agrees
(GPU 13.70 ms, frame interval 16.95 ms) and shows the same small frame-interval
spikes Stefan feels: missed frames, not a logging artefact.
Stefan: Accurate exposure is greyed out with the native renderer (it only
affects Vulkan); he plans to remove that option once older-iOS users confirm
the native renderer works for them.

## October 28, 2026: IPA110 donut-stutter trace (iPhone)

iPhone 17 Pro Max, iOS 27.2, IPA110, 1x/60. Stefan's Game Performance trace
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/28 October 2026/ipa110_i-think_donut_stutters_game_performance_iphone.trace`
(12:54:45, 31.2 s) and log `nfsmw_ipa110_i_think_donut_stutters_iphone.log`
there (session from 12:53:51). Stutters expected after 0:15 (donuts).
- Trace: presents stop for 1.23 s (4.7 s), 3.47 s (9.0 s), 7.56 s (15.5 s) and
  0.98 s (23.1 s); Instruments flags them as main-thread hangs. Over those
  13 s the time profile has ~100 samples from all threads instead of ~1300/s.
  The game log shows the game running normally then (300 frames every 5 s,
  `pacing: 0 of 300` through 12:54:51-12:55:17), so these are gaps in the
  recording (the Mac's disk was nearly full, the Instruments temp file
  9.3 GB), not freezes. They cover most of the donut period.
- Captured parts: present interval median 16.67 ms, one frame over 20 ms
  (25.8 ms at 2.7 s).
- Log during donuts: 2100-3050 draws per frame (vs ~380 in normal driving), GPU
  7.4-7.7 ms/frame, 0 over 45 ms, no `hitch:` lines (>40 ms), pacing 4 frames
  one refresh late in 12:54:42-46, then 0-1 per 300. Renderer
  `rendering` 15.8-15.9 ms/frame while RenderFrame is ~8% of a core in the
  profile, so that time is mostly waiting, not encoding.
- Inference: at 1x/60 the donuts did not drop frames on screen. Whatever
  Stefan felt is not a present-timing hitch at 1x; untested whether it is
  content-side (uneven game steps) or only at 1.5x MetalFX, where the GPU is
  ~13.7 ms. Next: short re-trace with free disk space, or at 1.5x.

Second trace, same day: `ipa110_donut_stutters_game_performance_iphone.trace`
(13:19:04.75, 30.0 s, 1x/60) and `nfsmw_ipa110_donut_stutters_iphone.log`,
same folder. Disk had 86 GB free and the trace still has two gaps (5.5 s at
6.3 s, 9.1 s at 16.35 s), so the gaps are not (only) disk space.
- Log: during donuts before the trace (13:18:03-13:19:03, 2400-4500 draws)
  pacing 0-2 of 300 off; from 13:19:04 4-8 of 300 off per 5 s, each one 120 Hz
  refresh pair late ("4:" gaps = 33 ms), matching Stefan's Metal HUD spikes.
  GPU 12.5-14.8 ms/frame average at 1x, game-thread recording 6-7.5 ms.
- Trace: GPU frame span median 12.7 ms, p90 15.4 ms. 13 frames span 19-37 ms
  but their GPU busy time is normal (12-15.6 ms): the GPU sits idle ~15 ms
  (one refresh) inside them, right after an in-process
  `coreanimation.command-buffer` (assembly encoder). Command buffers are
  committed on time (~every 16 ms) around them.
- All 13 slow frames coincide with one of the 35 in-process Core Animation
  commits in the trace (0.64-0.69, 2.06-2.83 burst, 12.11, 13.08, 13.54,
  15.43, 15.64, 28.68, 29.35 s). This is the IPA86/IPA88 FPS-label mechanism:
  a UIKit layer change over the game's layer delays that refresh's frame.
- Source of the commits (inference, not yet proven): the touch overlay,
  `touch_controls.mm` `sendState` calls `setNeedsDisplayInRect:` whenever a
  control's look changes (stick knob moves, presses/releases), which donuts
  do constantly. The FPS counter already draws into the native frame.
- Proposed: a no-code check (donuts with a controller, touch overlay hidden),
  then draw the touch controls into the native frame like the FPS counter, or
  stop redrawing them on press/knob moves. Not approved or built yet.

Touch overlay check, same day (log uploaded by Stefan,
`nfsmw_ipa110_touch_controls_off_iphone.log`; two sessions, 1x/60,
DualShock 4). Run 1 (13:33, touch controls hidden): two windows with 22-24
frames shown as 25 + 8 ms pairs (`3:` gaps), otherwise 0. Run 2 (13:34:46,
touch controls disabled): donuts 13:35:16-13:35:46 with 0 of 300 off in every
window; Stefan saw 0 Metal HUD spikes. Driving afterwards: 1 late frame in
13:35:51-56 (58 ms hitch at 13:35:57, 52 ms outside the recording, i.e. the
game side; adaptive QoS had been on Utility since 13:35:26 and boosted
again) and 1 in 13:35:56-36:01. GPU 11.5-14.8 ms/frame while driving at 1x.
Result: the touch overlay's redraws cause the HUD spikes during donuts
(hidden is not enough; disabled removes them). Stefan still feels the game
stutter with an even screen, donuts and driving: that is D-005's judder
(content motion uneven, swaps even), not a frame-timing miss.

### IPA111: touch controls drawn into the native frame

Stefan approved (Oct 28). Branch `touch-overlay-native` (off `main`).
`touch_controls.mm`: with the native layer showing and not editing, the
touch view's `setNeedsDisplay`/`setNeedsDisplayInRect:` no longer touch its
layer; the changed rectangle is redrawn (same `drawRect:`, view opacity as a
transparency layer) into a kept BGRA bitmap at the screen scale, at most once
per run loop turn, and handed to `nfsmw_native_set_touch_overlay`. The layer
is emptied once. The mode follows the native layer (0.5 s check, and on each
redraw request); `[touch] drawn into the native frame / by UIKit` logged.
`native_renderer.mm`: one shared texture, updated only in the changed
rectangle, blended (premultiplied) over the whole drawable before the FPS
counter. Known limit: the texture is written while an earlier frame may read
it (at worst a knob half-moved for one frame). Cvar `ios_touch_native`,
default true (Extra Args `--ios_touch_native=false` restores the UIKit layer).
Built `ios/build/NFSMW-0.4.1-touch-native-111.ipa`, 30106035 bytes, SHA-256
beaf16d0f4719a07cb423e7ae112aa90bd3c068b7c9f6dac8ee49c69f1b537e4, UUID
B2072EDF-FFA9-31F1-A567-AD08C7E5EDE4, 208 metallibs, `unzip -t` ok, codesign
ok. Not run on a device. Test: donuts at 1x/60 with touch controls on: no
Metal HUD spikes, `pacing` 0 of 300 off as with them disabled; the controls
look the same (opacity, pressed colours, knob) and still respond.

Colour filter switch (Stefan, Oct 28: turn off only the yellow filter, keep
bloom/blur): not built. The filter is part of the visual treatment
(sub_822246F0): it binds five textures (scene r5, effect params at view+332
/+340/+344 with globals 0x82A2C4B8/0x82A2C4C4, r6) and sets constants in
sub_82223D40/sub_82223BB8 (a 3x3-looking matrix times a scalar, likely the
colour transform) before sub_82224240 (blur) and sub_82224380. Which constant
or texture carries the tint is not identified yet; the translated pixel
shaders have no names (cache `shaders/msl`).

IPA111 result (Stefan, Oct 28, iPhone 17 Pro Max, 1x/60; log
`Debug/28 October 2026/nfsmw_ipa111_touch_controls_iphone.log`, runtime build
BA87D48F-...): `[touch] drawn into the native frame` logged; Metal HUD
"virtually stutter free" during donuts with the touch controls on; pacing 0-4
of 300 off per window after loading. Fixed for the touch overlay. The game
world still judders at random moments (D-005), with an even screen.

### IPA112: frame-step clock (experiment for D-005)

Stefan approved (Oct 28). Hypothesis: the main thread's clock reads jitter
~1 ms around the vblank they follow, so each frame's world/camera step is
slightly uneven at 60 fps while the screen gets an even 60. SDK hook
`tools/ios/patch_ios_frame_clock.py` (in prepare_sdk.py): a filter on
`Clock::QueryGuestTickCount` (all mftb/KeQueryPerformanceCounter reads).
`ios/src/frame_clock.cpp`: cvar `nfsmw_frame_clock_ms` (default 0 = off).
On the game's main thread only (first caller of the deferred-call hook
sub_823C8290), reads less than that many ms after the latest guest vblank
(the display refresh display_rate.mm publishes) return the vblank's time;
later reads stay real; never backwards. Logs `[frame-clock] on` and, every
300 vblanks, the main thread's reads by time after the vblank (<1, 1-2, 2-4,
4-8, 8-12, 12+ ms) and how many were snapped. Risks: a wait that polls the
clock right after a vblank waits up to the window longer; if the frame's
read sits near the window's edge, steps of 0/2 vblanks (worse). Also has
IPA111's touch fix.
Built `ios/build/NFSMW-0.4.1-frame-clock-112.ipa`, 30098542 bytes, SHA-256
d5e2bde35bf5d219caf5cf594aec0bd508c6a4e128ff705ae97f9d400835c0cf, UUID
8BDD84C4-5899-3DDC-84DF-0534275C8503, 208 metallibs, `unzip -t` ok,
codesign ok. Not run on a device. Test (1x/60): donuts/driving with
`--nfsmw_frame_clock_ms=8`, then without, same spot; send the log.

IPA112 first test (Oct 28): no `[frame-clock] on` in either session
(`nfsmw_ipa112_60hz_clock_iphone.log`, 14:14 and 14:18): boot.txt shows the
14:18 run's `extra_args.txt` was UTF-16 LE with a byte-order mark (copied via
the Mac), so the argument reached the parser as garbage and the switch was
off. Not a frame-clock result.

IPA113: `ios_main.mm` `ApplyExtraArguments` reads `extra_args.txt` as UTF-16
(either order, by its mark) or UTF-8 (a UTF-8 mark is dropped); boot.txt says
`extra_args.txt: UTF-16, converted`. Checked the decoding on the Mac with a
UTF-16 LE file. Also has IPA112's frame clock and IPA111's touch fix.
`ios/build/NFSMW-0.4.1-frame-clock-utf16-113.ipa`, 30099717 bytes, SHA-256
3fda5a78242583414519ea8c009141c212ce9164930e20eddc8f6758b3ea8cfd, UUID
DB56663F-5840-3B84-AE44-3F52A7B37F20, 208 metallibs, `unzip -t` ok, codesign
ok. Not run on a device.

IPA113 run with the switch (Oct 28 14:26-14:27, iPhone, 1x/60; log
`Debug/28 October 2026/nfsmw_ipa113_utf_fix.log`): `[frame-clock] on: main
thread 17f88d, reads up to 8 ms` (the UTF-16 file was read). The main-loop
thread reads the clock ~3 times per vblank, spread over the whole frame, and
the spread drifts: 8-12 ms after the vblank at first (774 of 906), later
4-8 ms (583 of 900); only 16-759 of ~900 reads per 300 vblanks snapped. So
the game's loop is not in step with the vblank: its phase drifts against the
display, and an 8 ms window snaps some frames' reads and not others. The
swaps (`between swaps` lines) run on another thread (t1570948) than the
main loop (1570957). Pacing 0-5 of 300 off. Inference: the snap as built
cannot give equal steps; a clock that advances one period per swap (on the
thread that swaps) would.

IPA114: frame clock v2 (`nfsmw_frame_clock_swap`, default false). On the
main loop thread and the thread that swaps (native renderer swap), the guest
clock advances by whole refresh periods at each swap (as many as really
passed, normally 1) and runs on the real clock in between, held at one tick
short of the next period; past two periods without a swap it runs again
(one period behind until the next swap). Never backwards per thread. Logs
`[frame-clock] v2 on` and every 300 swaps the periods per swap and how far
the virtual clock is behind the real one. Other threads untouched.
`ios/build/NFSMW-0.4.1-frame-clock-v2-114.ipa`, 30111876 bytes, SHA-256 f5090d2bd341a49b93f53db9e1b4a39c6748c2ec1fa8a4746fa71c12e1c25a1d, UUID FA7EB3D8-FF71-3E6D-9C53-B8D8466FAA53, 208 metallibs, `unzip -t`
ok, codesign ok. Not run on a device. Test: extra_args.txt
`--nfsmw_frame_clock_swap=true` (drop `--nfsmw_frame_clock_ms`), donuts at
1x/60, then without.

IPA114 result (Stefan, Oct 28 14:32-14:33, iPhone, 1x/60; log
`Debug/28 October 2026/nfsmw_ipa114_clock_v2_iphone.log`): `[frame-clock] v2
on`; in gameplay 296-300 of every 300 swaps advanced exactly one period (the
main loop and swap threads saw an exact 1/60 per frame); pacing 0-4 of 300
off (14 in the last window). The virtual clock fell behind the real one by
up to 312 ms near the end (late frames counted as one period). Stefan: the
judder "still seems to be there", can't tell better or worse (it varies by
itself). So exact per-frame time on those two threads does not visibly fix
it: the uneven-step hypothesis is weakened (other threads' clock reads, e.g.
physics or camera on a worker, are not covered). No objective judder
measure yet.

Screen recording (Stefan, Oct 28 14:37, iPhone, 1x/60, Motion blur and
Post-processing off, donuts; `Debug/28 October 2026/ScreenRecording_10-28-2026
14-37-39_1.MP4`, 37.4 s, 1320x2868, 2226 frames). Measured with an
AVFoundation script (per-frame mean luma difference on a 64x36 grid;
scratch tool, not in the repo). Recorder frame intervals: 2192 of 2225 at
16.6-16.7 ms. During motion a frame normally differs from the one before by
~4-6 (grey levels); 133 frames are near-identical (< 0.15) to the previous
one: an exact repeat of the picture. They come as stretches where every
other frame repeats (11.10-12.24 s: 26 repeats in 1.1 s; 15.57-16.30 s:
18), i.e. 30 fps motion shown at 60, plus scattered single repeats
(3.3-5.2 s, 6.3, 8.4, 25.7, 26.0 s). This is the judder, measured: the
screen gets 60 refreshes but only 30 distinct pictures in those stretches.
Whether the game swaps identical frames, or the renderer presents a frame
twice, needs the game log of the same run (none sent yet).
Game log of the recorded run (`nfsmw_ipa114_screen_recording_iphone.log`,
frame clock v2 on): the display went 48 -> 60 Hz at 14:37:39.67 (the
recording starting). Over 14:37:45-14:38:05, which covers the video's
repeat stretches (11-12 s, 15.6-16.3 s), every window is `pacing: 0 of 300
off`, 60.0 frames/s on screen and 300 of 300 swaps one period. So the game
swapped and the renderer presented 60 frames a second, each 16.7 ms apart,
yet every other picture was identical in those stretches. IPA92 (iPad) found
no frame repeating the previous one's vertex constants. Inference: the
picture repeats although the frame is new: the displayed texture (the
frame's last colour resolve, or a resolve kept from an earlier frame,
`1 resolves from earlier frames` in every gameplay line) is at times the
previous frame's picture. Next (proposed): a diagnostic that compares a row
of the displayed picture with the previous frame's and logs each repeat
with the final resolve's address and source.

IPA115: repeated-picture diagnostic (Stefan approved, Oct 28). Cvar
`nfsmw_native_repeat_log`, default TRUE in this diagnostic build (turn off
or remove before a release). Each frame blits a 2-row strip (up to 1024
pixels) across the middle of the displayed picture (`final_texture`, before
MetalFX/FXAA) to a shared buffer; on GPU completion it is compared with the
previous frame's strip. In gameplay (over 300 draws) each byte-identical
repeat logs `[native] repeat: frame N ...` (first 200): which resolve of the
frame was displayed, how many colour resolves, the address and whether it
is the previous frame's, draws drawn of total, resolves kept from earlier
frames; every 300 frames a count. Frame clock switches stay off by default.
`ios/build/NFSMW-0.4.1-repeat-log-115.ipa`, 30104610 bytes, SHA-256
075ef8096767bc4ef718d30163407bf7d52aa9045a766c8e8fe029e9df20bf31, UUID
CDBB8433-2F60-3150-958D-B83BAF2E9C0F, 208 metallibs, `unzip -t` ok, codesign
ok. Not run on a device. Test: no extra_args needed; donuts until the
judder shows; send the log (a screen recording too if easy).

IPA115 result (Stefan, Oct 28 14:51-14:53, iPad, 60 cap, extra_args still
with `--nfsmw_frame_clock_swap=true`; log
`Debug/28 October 2026/nfsmw_ipa115_stutters_ipad.log`): Stefan saw the
judder ("plenty"). The repeat diagnostic found 0 repeated pictures in every
300-frame window of gameplay except one: 4 frames at 14:52:31 (frames
1453-1456, a burst of quick frames, the final resolve alternating 092DA000 /
0958C000, all 2165 draws drawn). Pacing 0 of 300 off in every window, 60.0
frames/s, frame clock 300 of 300 one period. So on the iPad the judder comes
with every displayed picture new and on time: it is not repeated frames.
The iPhone recording's every-other-frame repeats (11-12 s, 15.6-16.3 s) did
not show up here; whether they came from the screen recorder (the display
switched 48 -> 60 Hz when it started) or only happen on the iPhone is open.
Remaining explanation: uneven motion between distinct frames (content), or
perception. Next: a motion-per-frame measurement from a recording (the
first script's shift estimate failed; needs a 2D estimate).

IPA115 on the iPhone (Oct 28 ~14:55-14:58; log
`Debug/28 October 2026/nfsmw_ipa115_stutters_iphone.log`): Stefan saw the
judder. 0 repeated pictures in 20 of 21 windows; one burst of 4 at
14:57:02.82-.87 (frames 1690-1693, 12-17 ms apart, final resolve alternating
09222000 / 08DBB000). Same as the iPad: the judder comes with new pictures on
time. So the screen recording's every-other-frame repeats (14:37) were most
likely made by the recorder (the display went 48 -> 60 Hz when it started),
not by the game. Remaining: uneven motion between distinct frames.

Stefan's clue (Oct 28 15:00): an area gets smoother the more he does donuts
there, and stays smoother in later runs (after relaunching). iPad recording
`ScreenRecording_10-28-2026 15-00-44_1.mov` (3200x2400, 25.4 s) and log
`nfsmw_ipa115_dnuts_ipad.log`. Second measurement script (block matching on
a 384x216 luma grid, upper picture): 162 recorded repeats, in stretches
where every other recorded frame repeats (6.95-7.81 s, 13.43-14.06 s, ...)
and single double-steps then zero-steps (5.20-5.23 s). The game log for the
same seconds: 0 repeated pictures, pacing 0 of 300 off, display 60 Hz
throughout. So the screen recorder's frames are not a faithful record of
what was shown (it repeats/skips frames by itself); recordings cannot measure
this judder. Pipelines in that log: all 163 made from the cache (23 ms in
all), no draws left out after the first frame, so the across-runs cache is
not the pipeline cache. Candidate: iOS' file cache of the game data (the
game streams the city from the ISO; a reread area comes from memory).
Proposed no-code check: restart the device (clears the file cache) and drive
the "smooth" area again.

Restart test (Stefan, Oct 28 ~15:08): after restarting the device, even
leaving the safehouse "felt like 30 fps" with the counter at 60. Confirms
the judder depends on iOS' file cache, i.e. on cold disc reads: the ISO is
mapped (DiscImageFile::ReadSync = memcpy from the mapping), so a first read
page-faults the data in from flash on the game thread that reads.

IPA116: `tools/ios/patch_ios_iso_readahead.py` (in prepare_sdk.py), SDK
`disc_image_file.cpp`. Cvar `ios_iso_readahead_mb`, default 16: after a read,
madvise(MADV_WILLNEED) on the next 16 MB of the image (again only when reads
have used up half the last advised stretch of that file), so the kernel
reads ahead in the background. `[iso-read]` every 5 s per thread: reads,
KiB, ms reading, slowest (first 400 lines). `nfsmw_native_repeat_log` now
default false. Frame clock switches still default off.
`ios/build/NFSMW-0.4.1-iso-readahead-116.ipa`, 30109492 bytes, SHA-256
7387778bb6bbff8a8227c63ecd5aafe88ad7463d038187b4a9f30aa38444f40c, UUID
8442B440-6748-3100-9622-A4D98599FA61, 208 metallibs, `unzip -t` ok,
codesign ok. Copied to iCloud Drive/NFSMW (also zipped). Not run on a
device. Test: empty extra_args.txt, restart the device, leave the
safehouse; then the same with `--ios_iso_readahead_mb=0` after another
restart; send both logs.

IPA116 result (Stefan, Oct 28 15:13-15:14, iPad, no device restart, no
extra args; log `Debug/28 October 2026/nfsmw_ipa116_ipad.log`): "just
driving around was pretty bad". `[iso-read]`: all disc reads on one thread
(XThread10713, a loader, not the main loop), 8-71 reads per 5 s, 0.5-40 ms
spent reading per 5 s, slowest single read 11.9 ms (3.3-5 ms typical). The
main loop thread did no disc reads. So in this run disc reads cost the game
very little and not on its main thread; they do not explain the judder here.
The restart observation (worse after a device restart) is not explained yet.

Stefan (Oct 28 ~15:17): at the 30 fps cap too, some parts of a donut feel
better paced than others. So the unevenness is not specific to 60 fps and
seems to depend on where the car/camera points within the donut.
Proposed next diagnostic: log the game's camera per frame from the world
draws' view matrix (the renderer already sees c0-c15; IPA92 hashed them) and
the per-frame change of its position and angle, to measure whether the
game's own camera motion is uneven.

IPA117: camera-motion diagnostic (Stefan approved, Oct 28). Cvar
`nfsmw_native_camera_log`, default TRUE in this build. In NativeDraw each
draw's c0-c3 is hashed; at the swap the frame's most common one (static
world draws share the view-projection) is the camera; its w row (c3.xyz) or
column (c0-c2 .w), whichever has length ~1, is the forward axis. Per frame
the angle turned; every 60 frames of 3D scene (over 300 draws, turning over
0.05 deg/frame): `[camera] 60 frames: turn X deg/frame, spread Y%, N off
their neighbours by over 25%` and the 60 values (first 600 lines). Same
thread as IPA92's content hash. Unknown whether the most common matrix is
the world's in every scene (HUD matrices could win). ISO read-ahead (16 MB)
and its log stay on.
`ios/build/NFSMW-0.4.1-camera-log-117.ipa`, 30113544 bytes, SHA-256 32a62a90cda67b0a91e6a7def931736533eb4638235710573ee18429d5696338, UUID F12C371A-F27F-3346-8864-755D7B112877, 208 metallibs, `unzip -t`
ok, codesign ok. Not run on a device. Test: donuts (any cap), note roughly
when it feels uneven; send the log.

IPA117 result (Stefan, Oct 28 15:22, iPad, no extra args, judder clearly
visible; log `Debug/28 October 2026/nfsmw_ipa117_camera_ipad.log`): 16
`[camera]` lines. The camera turns a steady ~2.0-2.3 deg/frame in donuts,
but in stretches the values go 4.40 0.00 4.40 0.00 ... (e.g. 15:22:36,
15:22:42: 20-30 frames in a row), single pairs elsewhere (4.17 0.02, 3.96
0.00). So the game's camera moves only every other frame in those stretches:
its world/camera steps 0 or 2 fixed ticks per frame. This is the judder,
measured in the game's own data. (Isolated 85-88 / 178 deg values: another
camera's matrix, probably the mirror's, won the vote for one frame.)
Explanation: the fixed 1/60 step accumulator, with the frame's clock reads
right at a tick boundary. IPA114's v2 clock let the clock run within a frame
(base + real time since the swap), so reads on either side of a boundary
remained possible.

IPA118: `nfsmw_frame_clock_hold` (default false, with
`nfsmw_frame_clock_swap`): within a frame the clock stands still at the
swap's virtual time (runs again after two periods without a swap). Camera
log and read-ahead still on.
`ios/build/NFSMW-0.4.1-frame-clock-hold-118.ipa`, 30115297 bytes, SHA-256 165eb6f58fdafc6b4c277eeed9d418d958d97def59a25abc443c947e1739817c, UUID 09457470-1622-38D1-A232-5ACC39C83AEF, 208 metallibs, `unzip -t`
ok, codesign ok. Not run on a device. Test: extra_args.txt
`--nfsmw_frame_clock_swap=true` and `--nfsmw_frame_clock_hold=true`, donuts;
the camera lines should show no 2x/0 pairs.

IPA118 result (Stefan, Oct 28 15:26, iPad, frame clock swap + hold on; log
`Debug/28 October 2026/nfsmw_ipa118_camera_ipad.log`): still the 30 fps
feeling; camera lines still full of 2x/0 pairs (163 pairs of 3-9 deg then
~0 in 18 lines, e.g. 15:26:28 four-plus seconds of 4.4/0). v2 reported 300
of 300 swaps one period. So the camera's steps do not come from the main
loop/swap threads' clock reads. New explanation (inference): the world and
camera update on the guest vblank (display-locked), while the game's drawing
loop runs at its own ~60 (paced only by our in-flight limit, the swap
returning at once); two unlocked 60 Hz loops drift, and when they line up
badly a frame draws the camera state the previous frame drew, the next one
a state two vblanks on.

IPA119: `nfsmw_native_swap_vsync` (default false): NativeSwap returns 0.5
ms after the display refresh at or after the swap (the 360's swap waits for
the vblank), keeping the drawing loop in step with the vblank. Logs
`[native] swap vsync on`. Camera log, read-ahead stay on.
`ios/build/`,  bytes, SHA-256 , UUID ,  metallibs, `unzip -t`
, codesign . Not run on a device. Test: extra_args.txt only
`--nfsmw_native_swap_vsync=true`; donuts; camera lines should show no 2x/0
pairs. Risk: a frame over 16.7 ms waits to the next refresh (33 ms), as on
the 360.

IPA119 result (Stefan, Oct 28 15:29, iPad; log
`Debug/28 October 2026/nfsmw_ipa119_lag_ipad.log`): `swap vsync on`; the
game ran at 18-25 fps (20.1 frames/s, pacing 217 of 300 off, gaps of 2-7+
refreshes). So the game already waits for the guest vblank itself after its
swap: our wait made it miss that vblank and wait for the next. The drawing
loop is therefore already in step with the vblank, and the "two unlocked
loops" explanation is wrong as stated. Switch stays default off (do not
use). Open: where the camera's 2x/0 steps come from (main loop and swap
threads have exact per-frame time, frames are drawn once per vblank). Next
lead: find the camera/world update in the game code and log its time step
and caller thread.

Main loop found (Oct 28): sub_823B0008 polls mftb>>2, converts the time
since the last frame to seconds (scale at 0x82A2BEF8), waits until it is over
a constant (0x820624E8), clamps it (0x82062824), and runs the frame
sub_823AFE20 with r3 = fctiwz(elapsed * rate (0x82062DAC)), i.e. truncated,
then restarts its count from now (the remainder is lost). sub_823AFE20 turns
r3 back into a time step (r3 * 0x820AFE00 * 0x82062AD0) for the world
(sub_823C6500) and calls World_Service (sub_824CE048). Inference: frame
periods jitter around a whole number of ticks, so truncation sometimes gives
one tick less (remainder lost) and the frames around it more: the camera's
2x/0 steps.

IPA120: `tools/ios/patch_game_frame_ticks.py` (generated code, USA; also run
by generate_code.py): before that fctiwz, f9 goes through
`nfsmw_frame_ticks` (frame_clock.cpp). Cvar `nfsmw_frame_ticks` default 1:
the remainder is carried to the next frame (ticks add up to elapsed time);
0 = the game's truncation. Logs the constants once (`[frame-ticks] main
loop: rate ..., waits for over ..., clamps at ...`) and every 300 frames
elapsed x rate by band and the ticks run. Camera log and read-ahead stay on.
`ios/build/NFSMW-0.4.1-frame-ticks-120.ipa`, 30116964 bytes, SHA-256 d554629c46ace70ed32fe3d6d7d28ed56d78b2748c4324290f7952ae9eab9d78, UUID F7A7C868-6ECD-3C64-B92D-A4767158E5A4, 208 metallibs, `unzip -t`
ok, codesign ok. Not run on a device. Test: empty extra_args.txt; donuts;
then `--nfsmw_frame_ticks=0` to compare.

IPA120 result (Stefan, Oct 28 16:15-16:16, iPad, no extra args, mode 1;
log `Debug/28 October 2026/nfsmw_ipa20_camera_ipad.log`): "seems much
better although maybe it was just luck". Constants logged: rate 65536
ticks/s (the "ticks" are 1/65536 s units: ~1092 a frame), wait constant
0.25, clamp 32000. So the truncation loses under 1/65536 s per frame and the
carry (mode 1) changes the step by at most that: numerically almost a no-op;
the tick-truncation explanation is wrong as stated. Camera log, counted the
same way (a value 1-10 deg followed by <0.05): IPA117 113 pairs in 960
frames, IPA118 197 in 900, IPA120 6 in 2400 (isolated zeros 117 / 206 / 4).
The measured judder dropped ~40x in this run, but the change cannot explain
it; needs an A/B with `--nfsmw_frame_ticks=0` in the same conditions.
IPA120 on the iPhone (Oct 28 ~16:19; log
`Debug/28 October 2026/nfsmw_ipa120_camera_iphone.log`, mode 1): Stefan:
better than before. Camera: 94 pairs in 3420 frames (2.7%), isolated zeros
113. No iPhone camera log before IPA120 to compare with (iPad IPA117/118:
12-22%).

IPA120 A/B (Stefan, Oct 28 ~16:25-16:30, iPad, same spot, warmed up first,
force-quit between runs): mode 1 (`nfsmw_ipa120_on_ipad.log`) 18 pairs in
3960 frames; mode 0 (`nfsmw_ipa120_off_ipad.log`, the game's truncation) 0
pairs in 2040 frames; Stefan: "off was very smooth too". So the tick carry
does nothing (as its numbers said). The judder rate tracks the session's
state, not any switch: 12-22% of frames in the runs after the 15:08 device
restart (IPA117/118, 15:22-15:26), 0-0.25% an hour later on the same iPad
(16:15-16:30), 2.7% on the iPhone. Consistent with Stefan's observations
(worse after a device restart, better the more an area is driven), i.e.
something that warms up over time across launches (iOS file cache, or
memory/paging state), though the measured disc reads are small and off the
main loop. Next (proposed): an Instruments trace right after a device
restart, during donuts, to see what the main loop thread does in the 2x/0
stretches (camera log on to mark them).

Time Profiler trace, waiting threads on (Stefan, Oct 28 18:35, iPad Pro M4,
IPA120 mode 1, no restart; `Debug/28 October 2026/ipa120_stutters_time_profile_ipad.trace`
runs 1 (18:35:50, 20.5 s) and 2 (18:36:42, 22.9 s), log
`nfsmw_ipa120_stutters_time_profile_ipad.log`). Camera log: run 1 mostly
clean (0-4 pairs per second, single ones), run 2 with stretches of 4-11
pairs per second (t = 7.5-13.5 s). The pattern is often not adjacent: a
double step, then one to three normal steps, then a zero (4.3 2.2 0.0,
3.8 1.9 1.9 0.0): the drawn camera runs one step ahead for a few frames and
then falls back in line. That looks like the drawing picking up the camera
already advanced for the next frame (an ordering between the update and the
drawing that varies), rather than uneven time steps. Main XThread in the
trace: no different activity within 50 ms before the judder frames than
elsewhere (most stack frames unsymbolicated, `?`); it runs almost all the
time (the main loop polls the clock). Not conclusive.

Next test (proposed to Stefan, Oct 28 ~18:45, no build): the ordering-race
idea. Our Utility QoS placement (guest threads on efficiency cores; iPad
log: 4 efficiency cores, main/GPU off, other guest threads on, adaptive on;
iPhone log: main/GPU on, guest on, adaptive off) changes the threads' relative
timing versus the 360. extra_args: `--ios_utility_qos=false`,
`--ios_utility_qos_guest=false`, `--ios_adaptive_qos=false`; device restart,
donuts as in run 2; compare camera-log pairs.

QoS-off result (Stefan, Oct 28 18:45, iPad restarted, IPA120, extra_args
`--ios_utility_qos=false --ios_utility_qos_guest=false
--ios_adaptive_qos=false`, logged `main/GPU threads off, other guest threads
off, adaptive off (Extra Args)`; log
`nfsmw_ipa120_stutters_after_restart_qos_off_ipad.log`): Stefan: donuts still
stuttered, but leaving the safehouse no longer stuttered "like crazy".
Camera: 75 pairs in 1440 frames (5.2%), in the donut seconds 18:45:34-46
(2-16 per second). So Utility QoS is not the cause of the donut judder
(maybe of the worse post-restart driving).
Threads (time profile, run 2): the game's main loop sub_823B0008 and its
frame sub_823AFE20 run on one guest thread (XThread9793); draws reach the
native renderer on the CP thread ("GPU Commands", NativeDraw/NativeSwap),
and RenderFrame on the render queue. Constants arrive as type-0 register
writes copied into the ring by the game (Oct 22 census: no LOAD_ALU_CONSTANT
traffic listed), so the CP cannot read a newer camera than the game wrote:
the step-ahead pattern is in what the game itself emitted.

Render hand-off found (Oct 28, from the trace's stacks): the main loop thread
(XThread9793, entry sub_8284FE40) spends its idle time in sub_823B0008 >
sub_823AFE20 > sub_823AFC68 > sub_82441050 > sub_82441DB0 > Sleep(0) (100 us
sleeps, KeDelayExecutionThread): waiting for the render state 0x82A2CF40 to
leave 1. sub_82441050 picks the frame's drawing path: if [0x82912F50+32] == 6
(and 0x82A2D1B4 == 0), flag 0x828FBB50 = 1 and sub_82441EF0 sets state 1 and
hands the frame to the render thread (Main XThread, entry sub_82593A58, busy
most of the time), and the main loop goes on to update the next frame while
it is drawn; otherwise sub_82441E70 (no hand-off). Hypothesis: the render
thread reads camera data that the main loop is already updating for the next
frame, so the drawn camera is one update ahead for 1-3 frames whenever the
two threads' timing lines up that way (varies with load, warm-up, cores).

IPA121: `tools/ios/patch_game_render_handoff.py` (generated code; also in
generate_code.py) and cvar `nfsmw_render_single_thread` (default false,
read once, logs `[render-handoff] gameplay frames ...`): the state-6 test
in sub_82441050 fails, so gameplay frames take the sub_82441E70 path.
Unknown whether that path draws gameplay correctly (it may be the
single-threaded draw, or something else). Camera log and read-ahead on.
`ios/build/`,  bytes, SHA-256 , UUID ,  metallibs, `unzip -t`
, codesign . Not run on a device. Test: extra_args
`--nfsmw_render_single_thread=true`; check the picture, fps and camera pairs.

IPA121 result (Stefan, Oct 28 18:54-18:55, iPad, extra_args
`--nfsmw_render_single_thread=true`; log `nfsmw_ipa121_judder_ipad.log`):
picture and 60 fps fine; "still juddered like crazy" at a new location (end
of the log). Camera: 18:55:06-19 10-18 pairs per second (2.2 2.2 4.4 0.0 ...),
pacing 0-1 of 300 off. No `[render-handoff]` line at all: the switch's
function is only called when the state-6 test passes, so in this run
gameplay frames never took the hand-off path (sub_82441EF0); the hypothesis
"render thread reads the next frame's camera" is not what happens here (the
hand-off is not used, or not in this state). Note: judder strongest at a
place visited for the first time.

IPA122: `[frame-steps] 60 frames | ...`: per main-loop frame, the elapsed
value it runs with (f0 = the r3 ticks / 65536, expected ~1.00 per 1/60 s if
f0 counts frames), 60 a line, beside the camera log. Tests "a slow frame
gives a double step, the next a near-zero one, while presentation stays
even" (judder worst at places seen for the first time). Same switches as
IPA121 (all experiments default off; frame_ticks carry 1, negligible).
`ios/build/`,  bytes, SHA-256 , UUID ,  metallibs, `unzip -t`
, codesign . Not run on a device. Test: empty extra_args; drive to a new
place and do donuts.

IPA122 result (Stefan, Oct 28 ~19:00, iPad, new location, no extra args;
log `nfsmw_ipa122_judders_ipad.log`): the main loop's per-frame elapsed
time (`[frame-steps]`, in ms: f0 is milliseconds) alternates ~13.5 / ~19.5
ms nearly every frame, and has stalls of 30-45 ms followed by quick frames of
4.5-6.8, 6, 9-12 ms (e.g. 44.35 6.23 6.50 9.04; 30.65 4.53 11.68). The camera
in the same seconds: steady 2.2 deg except 4.4/0 and 6.6/0/0 sequences, i.e.
the world steps fixed 1/60 ticks from these elapsed times, a 44 ms frame 2-3
ticks, the quick ones 0. Presentation stays on the 16.7 ms grid (frames
buffered), so the motion is uneven while the frame timing is perfect.
Cause (inference, well supported): the game's main loop is not paced by the
refresh; it runs until the GPU queue pushes back (pacing wait / ring space),
in bursts.

IPA123: `nfsmw_frame_pace` (default TRUE, 60 cap only): patch_game_frame_ticks.py
now also inserts `nfsmw_frame_pace()` right after the frame call in
sub_823B0008; it waits until 0.3 ms after the next display refresh unless the
frame ended under 2 ms after one. Logs `[frame-pace] on` and every 300
frames how many waited / started at once. Frame steps and camera logs stay.
`ios/build/NFSMW-0.4.1-frame-pace-123.ipa`, 30119960 bytes, SHA-256 3c2cdff4f7a8d3ff4d96830c683849b4c2ce21b4eb9386d0ed77e1d895bacff6, UUID FD2AC64E-830C-37F7-AD92-3438710F85DD, 208 metallibs, `unzip -t`
ok, codesign ok. Not run on a device. Test: empty extra_args; new location,
donuts; frame steps should sit near 16.7 and camera pairs vanish. Off:
`--nfsmw_frame_pace=false`.

IPA123 result (Stefan, Oct 28 19:05, iPad; log `nfsmw_ipa123_lowfps_ipad.log`):
"crazy low fps everywhere, menu included": 27-55 frames/s; frame steps 0.3
... 166 ms (many 80-130 ms). Pacing the loop itself stacks with the GPU
queue's back-pressure. nfsmw_frame_pace now default false (do not use).

IPA124: `nfsmw_frame_ticks` mode 2, default: in the existing hook before the
main loop's fctiwz, the frame's elapsed time f0 (ms) is replaced by one
display period (16.67 ms at 60 Hz), or more periods when real time has run
over 0.75 of a period ahead (frames missed on screen too); a debt beyond -2
or +4 periods resyncs (loading). The loop itself is not slowed. Rationale:
the screen shows one game frame per refresh (pacing 0 of 300 off), so the
world should advance one refresh per frame.
`ios/build/`,  bytes, SHA-256 , UUID ,  metallibs, `unzip -t`
, codesign . Not run on a device. Test: empty extra_args; new location,
donuts; camera pairs should vanish, fps unchanged. Off:
`--nfsmw_frame_ticks=0`.

IPA124 result (Stefan, Oct 28 ~19:10-19:14, iPad, no extra args; log
`Debug/28 October 2026/nfsmw_ipa124_possible_fix_ipad.log`): "a bit of
judder" once ~15 s after leaving the safehouse; donuts at several new
locations judder-free; the test race's usual judder spot "buttery smooth";
60 fps throughout. Camera log: 3 pairs in 6120 frames (0.05%; 19:12:13,
:14, :36), versus 113-197 per ~900 frames in IPA117/118 and 10-18 per second
at new places in IPA121/122. fps lines: 23 of 27 windows 60.0, the rest
57.6-59.9. First fix that removes the measured judder at new places. Next:
iPhone test; then remove the failed experiments and decide defaults.

IPA124 on the iPhone (Stefan, Oct 28 ~19:16; log
`nfsmw_ipa124_possible_fix_iphone.log`): no judder driving or doing donuts at
three spots that had it before; camera 0 pairs in 4080 frames; 60 fps (one
30.1 window: loading). Stefan: ship it in 0.4.2 with the touch fix and UTF-16.

### 0.4.2 cleanup (Oct 28)

Kept: touch controls in the native frame (IPA111), UTF-16 extra_args.txt
(IPA113), the even frame time (`tools/ios/patch_game_frame_ticks.py` +
`ios/src/frame_clock.cpp`, cvar `nfsmw_frame_ticks` 2 default / 0 off; the
remainder-carry mode 1 removed), the camera log and repeat log as off-by-
default diagnostics (`nfsmw_native_camera_log`, `nfsmw_native_repeat_log`).
Removed (reverted from the SDK / generated code, scripts deleted, results
kept above): frame clock v1/v2/v3 (`patch_ios_frame_clock.py`, cvars
nfsmw_frame_clock_ms/_swap/_hold), swap vsync (nfsmw_native_swap_vsync),
main-loop pacing (nfsmw_frame_pace), render hand-off switch
(`patch_game_render_handoff.py`), ISO read-ahead and read timing
(`patch_ios_iso_readahead.py`), the frame-steps log. Version 0.4.2 (code 6).

30 / 40 fps check (Stefan, Oct 28 19:25-19:29, iPhone, IPA124; log
`nfsmw_ipa124_30_40_fps_tests.log`): no judder, even pacing, but at 40 fps
"the mirror picture, the map rotation etc. seem much higher fps than the main
game". Camera log at 40: per-frame turns alternate 2.26 / 4.52 deg (1 and 2
world ticks) through whole seconds: the world steps in fixed 1/60 s ticks and
a 25 ms frame is 1.5 ticks, so frames alternate 16.7 / 33.3 ms of world
motion (a 30 fps-like cadence in a 40 fps picture), while the mirror and map
follow the frame's real time. At 30: mostly 4.6 (2 ticks) with occasional
6.9 / 2.3. Proposed: 120 Hz simulation (`nfsmw_sim_rate` 120, exactly 3 ticks
per 25 ms frame) automatically at the 40 cap, as already at the 120 cap; to
be tested (game speed at 120 Hz simulation was never checked).

Battery mode (Stefan, Oct 28): keeps the frame rate cap at 30 or 40 as
chosen (60 and 120 become 30), instead of forcing 30: launcher.mm Value()
and the setting texts; `fps_cap` removed from BatteryValue (no longer
greyed out). For 0.4.2.

Power Profiler, iPhone 17 Pro Max, IPA124, 1x/60, test race (Oct 28 19:22,
`ipa124_test_race_power_profile_iphone.trace`, 140.7 s, log
`nfsmw_ipa124_test_race_power_profile_iphone.log`): not charging, brightness
33%, thermal Nominal throughout. Duration-weighted: estimated system drain
40.6 pp/h; LiveContainer CPU impact 8.88, GPU 1.75, display 0.67, CPU
instructions ~2.97 G/s; log 59.6-60.0 fps, CPU 76-97% of a core. Oct 21
iPhone baseline (549 s, brightness 47%, no Utility QoS): drain 37.6, CPU impact
21.0, display 1.99, 9.85 G instr/s. CPU work is far lower now; the drain
estimate is not comparable (140 s, race start and loading included, Power
Profiler's estimate swings 22-62 per second here). A longer (10 min) run is
needed for a drain figure.

0.4.2 release candidate (Oct 28): `ios/build/NFS-Most-Wanted-0.4.2.ipa`,
30115301 bytes, SHA-256
95d3897cbbbc821c59b9c858aec22009bee96c29b9b17d0cfa096f6033bfab32, NFSMW UUID
F597DB27-A2D6-38B1-99FF-ABBA29E5F173, 208 metallibs, `unzip -t` ok,
`codesign --verify --deep --strict` ok, bundle com.bep1s.nfsmwios 0.4.2 (6).
Contains: even frame time (nfsmw_frame_ticks 2), touch controls in the native
frame, UTF-16 extra_args.txt, Battery mode 30/40 choice; diagnostics off.
Not yet run on a device as a release build (fresh container). Branch
`touch-overlay-native`, not merged, tagged or pushed.

120 Hz simulation at the 40 cap (Stefan wants it in 0.4.2): launcher.mm
passes `--nfsmw_sim_rate=120` when the cap is 40 (as at 120) or the switch is
on; the 120 Hz simulation switch text updated. With nfsmw_frame_ticks 2 the
period at the 40 cap is the 120 Hz guest grid (8.33 ms), so a 25 ms frame gets
exactly 3 periods. Game speed at 120 Hz simulation still unverified (check a
lap / speedometer against 60). The sim rate is set at startup: changing the
cap to 40 in the in-game menu does not switch it until a restart.
Release candidate 2: `ios/build/NFS-Most-Wanted-0.4.2.ipa`, 30115889 bytes,
SHA-256 c67ac530a0d9f07a7b8e684db69292f3448ddf88014274b1055fd679dc85f485, UUID
FD902E47-6A66-395E-986E-3FA0723B9B86, 208 metallibs, `unzip -t` ok, codesign
--deep --strict ok. Not run on a device.

0.4.2 RC2 test (Stefan, Oct 28 ~21:45, iPhone, fresh install; log
`nfsmw_0.4.2rc2_tests_iphone.log`): Battery mode at 40: "great (not perfect)";
`sim rate: 120 Hz set`, 39.3-40.0 fps; a race "just like I know it" (game
speed normal with 120 Hz simulation, by feel); 60 fps checked on IPA124 ("99%
perfect"). Camera log off in the release build. Pacing at 40: ~200 of 300 off
the 25 ms grid, refresh gaps 2/3/4 in about equal parts, the same as IPA124:
presentation at the 40 cap is uneven (pre-existing, BACKLOG). Minimap position
bug reported (BACKLOG).

Custom HUD master switch (Stefan, Oct 28, for 0.4.2): launcher key
`hud_custom` (switch "Custom HUD", default off) at the top of the HUD section
and in the in-game options. While off, Value() returns the game's values for
hud_scale / hud_safe_zone / hud_left_x/_y / hud_right_x/_y / hud_race_x/_y
(1.00, 1.00, 0...), so the launcher passes those and the in-game menu applies
them live; the rows are greyed out ("Turn on Custom HUD to change.", new
`HudLocked`); saved choices are kept for when it is on. Whether this avoids
the minimap bug is not known (the bug may also happen at the game's values:
the wide-scene HUD offset is not part of this switch).
Release candidate 3: `ios/build/NFS-Most-Wanted-0.4.2.ipa`, 30116322 bytes,
SHA-256 b8618590cb2770ed3fcad7b884f5d73ba35443228801c6ce96ec1632199f2960, UUID
D78B1872-D3E4-3516-95D1-7196DF28628D, 208 metallibs, `unzip -t` ok, codesign
--deep --strict ok. Not run on a device.

40 fps presentation fix (Stefan, Oct 28: before the final 0.4.2 tests):
native_renderer.mm paced presentation (caps below the display rate, e.g.
40 on 120 Hz) now keeps a fixed grid: each frame's target is the previous
target + one interval, moved on by whole intervals until it is at least the
recent GPU time (EMA of the frame GPU time, `recent_gpu_seconds`) + 4 ms
from now; restart from the last shown frame only when the previous target is
more than 4 intervals away. Before, the grid restarted from the last frame
actually shown each time, and frames finishing near their target were shown
16.7 / 25 / 33 ms apart (~200 of 300 off the grid at 40 on the iPhone). Cost:
up to one interval of extra latency when frames cannot make the next slot.
Release candidate 4: `ios/build/NFS-Most-Wanted-0.4.2.ipa`, 30117907 bytes,
SHA-256 83c4a791fd8890ed12629517e49ef346bc0addf3314c0aaafabeafd47f75a3c8, UUID 62DD5A51-C3B3-3292-A332-492D65743636, 208 metallibs, `unzip -t` ok, codesign --deep --strict
ok. Not run on a device. Test: 40 cap (and 30) on the iPhone; pacing lines
should read mostly `3:` (40) / `4:` (30) and few off the grid.

RC4 test (Stefan, Oct 28 22:02-22:07, iPhone, a lap of the test race each;
logs `nfsmw_0.4.2rc4_40fps_race_iphone.log`, `nfsmw_0.4.2rc4_30fps_race_iphone.log`):
30 fps clean (0-5 of 300 off, gaps 4:293-300). 40 fps not fixed: steady
windows exactly `2:100 3:100 4:100` (shown 16.7 / 25 / 33.3 ms apart in a
repeating cycle), others 130-291 of 300 off. Reading: on the fixed grid, one
frame in three still misses its slot by one refresh (33.3) and the next two
are on time (16.7, then 25): the margin (average GPU time + 4 ms) is too
small for the compositor at 40.
RC5: the margin is the recent longest GPU time (decaying max, x0.98 a frame)
+ 12.5 ms. `ios/build/NFS-Most-Wanted-0.4.2.ipa`, 30117858 bytes, SHA-256
683c4105882c5180fdf03c09d82757c796e6f2cf8034d67665e8f6680f28c98b, UUID
E649837C-FDBE-3D84-980B-7DB6BAA36692, 208 metallibs, codesign ok; copied to
iCloud Drive Desktop as NFS-Most-Wanted-0.4.2-rc5.ipa (RC4's copy removed;
RC4 is rebuildable from 1619e70). Not run on a device.

RC5 test (Stefan, Oct 28 22:10, iPhone, 40 cap; log
`nfsmw_0.4.2rc5_40fps_iphone.log`): frame-time counter "jumping all over the
place"; pacing worse: 190-282 of 300 off, many 8.3 ms gaps (1:46-88) beside
4:106-178, steady windows again 2:100 3:100 4:100. A wider margin does not
help: presentAtTime targets do not control the 40 cap here.
(ios_display_match_cap, asking the display for 40 Hz, was tried Oct 24: iOS
ran a 60 Hz pattern.)
RC6: at the 40 cap only, `presentDrawable:afterMinimumDuration:` 21 ms (the
interval - 4 ms): the system keeps each frame at least 21 ms after the one
before, i.e. three 120 Hz refreshes. Other paced caps keep RC5's grid (30 was
clean in RC4). `ios/build/NFS-Most-Wanted-0.4.2.ipa`, 30117012 bytes, SHA-256
e2e500026ee635de4ee870641b3e87cb3a3caec3f160f26924678b858314c622, UUID
6BED9CE3-879B-3256-A583-4ACDF0EA43C4, codesign ok; iCloud Desktop as
NFS-Most-Wanted-0.4.2-rc6.ipa (RC5 copy removed). Not run on a device.

RC6 test (Stefan, Oct 28 22:15, iPhone, 40 cap; log
`nfsmw_0.4.2rc6_40fps_iphone.log`, also holds the RC5 session): "still not
it". Pacing in the RC6 session: steady windows `2:100 3:100 4:100` again,
others 3:~100 4:98-167 5:18-80. The same 16.7 / 25 / 33.3 ms cycle with
three different presentation methods (shown-anchored target, fixed grid,
minimum duration): the unevenness is upstream of presentation (when the
frames are produced or committed at the 40 cap), not how they are scheduled.
Not solved for 0.4.2; needs a per-frame diagnostic (CP swap time, commit,
target, shown) at the 40 cap.

Stefan (Oct 28): not in a rush; fix 40 fps before releasing. IPA126
frame-trace diagnostic (cvar `nfsmw_native_frame_trace`, default TRUE in
this build): per frame, CACurrentMediaTime at the renderer's swap (NativeSwap,
after the cap wait), at the hand-over to Metal (present call), the GPU end
(GPUEndTime) and shown (presentedTime). Every 60 shown frames: four lines of
gaps between consecutive frames per stage and one line of per-frame
latencies (swap->handed / handed->GPU end / GPU end->shown). RC6's 40-cap
minimum-duration present still in. `ios/build/NFSMW-0.4.2-frame-trace-126.ipa`, 30120996 bytes, SHA-256 57071e301dc149af161a39356bd4b4da238901512d2deee65b04666a866e6bfe,
UUID B208FD8F-3000-3DA0-BB17-DEEABA5C8587, codesign ok; iCloud Desktop copy. Not run on a device.
IPA126 run (Stefan, Oct 28 22:21, iPhone, 40 cap; log
`nfsmw_ipa126_frame_trace_40fps_iphone.log`): no `[frame-trace]` line at all
(13 pacing lines), so the trace did not run: most likely an earlier build
was installed (the log has no build marker that tells them apart; the
dylibs are unchanged since RC1). IPA127 adds a startup line `[frame-trace] on
(IPA127)`: `ios/build/NFSMW-0.4.2-frame-trace-127.ipa`, 30119905 bytes, SHA-256
43c78cb9c49d663b6b4527ef121555881cfb4d8142c1c43968330abbf6071ec6, UUID
6B21ED6E-72D6-3F15-A435-1890D6E374DC, codesign ok; iCloud Desktop copy
replaces IPA126's.

IPA127 frame trace (Stefan, Oct 28 22:28-22:30, iPhone, 40 cap; log
`nfsmw_ipa127_frame_trace_40fps_iphone.log`, 241 trace lines; Stefan
stopped early, "it started dropping frames": one 809 ms gap in the log).
In gameplay the renderer's swap, the hand-over to Metal and the GPU end are
all an even ~25 ms apart (24-26), but the shown times alternate 16.7 / 33.3
in stretches (e.g. "16.7 33.3" x4, then 25.0 x11, then x7 again), with GPU
end -> shown alternating ~12 / ~20 ms. Everything up to the GPU is even: the
unevenness is in the display stage, a 60 Hz pattern (only multiples of 16.7)
in those stretches, although the display link reports 120 Hz and the frames
ask for at least 21 ms (RC6). Menus: 33.3 cadence.
IPA128: at the 40 cap the display link's range is 120-120 Hz (was 80-120),
startup marker IPA128. `ios/build/NFSMW-0.4.2-frame-trace-128.ipa`, 30120373 bytes, SHA-256 5a966291f8d8caf28531f6a74c819a34243562c87d3e188b12d9d3e7d3b3975c, UUID 3B2066B4-9A0F-3524-9F7D-BEE641781EE3,
codesign ok; iCloud Desktop copy replaces 127. Not run on a device.

IPA128 test (Stefan, Oct 28 22:34-22:37, iPhone, 40 cap; log
`nfsmw_ipa128_frame_trace_40fps_iphone.log`): "fps randomly drops to 32",
since one or two builds. Windows at 32.8-36.2 fps: swap -> hand-over 37-58
ms (frames waiting in the render queue), hand-over gaps 33 / 33 / 25 (three
frames per 91.7 ms), GPU 15-16 ms/frame; 40.0 windows show 2:100 3:100 4:100
again. Reading: RC5/RC6 (later targets, minimum-duration presents) hold
drawables longer; the renderer waits for a free drawable and the pipeline
backs up to ~33 fps. The 120 Hz minimum did not remove the 16.7/33.3 cycle.
IPA129: RC4's presentation restored (fixed grid, average GPU time + 4 ms; no
minimum-duration path), 120-120 Hz display range at the 40 cap kept, trace
on, marker IPA129. `ios/build/NFSMW-0.4.2-frame-trace-129.ipa`, 30120043 bytes, SHA-256 c0e5d333405705feac48a3f75934d316164058fcfaa077db0aaaa9e13d5b461e, UUID 014D557F-264C-3FF7-987F-4F13E0C500D3, codesign
ok; iCloud Desktop copy replaces 128. Not run on a device.

IPA129 test (Stefan, Oct 28 22:39-22:41, iPhone, 40 cap, Battery mode; log
`nfsmw_ipa129_frame_trace_40fps_iphone.log`): no fps drops (39.7-40.0), but
the shown gaps settle into an exact repeating 25.0 / 16.7 / 33.3 cycle while
swap, hand-over and GPU end stay ~25 ms (+-2): GPU end -> shown alternates
~37 / ~28 / ~37 ms, i.e. one frame in three is shown a refresh earlier than
its neighbours. Stefan also asked whether "30 fps in menus" still works: the
log says `(the caps only at the 60 fps cap)`: menus/warm 30 apply only at
the 60 cap, so not at Battery mode's 40.
IPA130: the trace also logs each paced frame's target (shown minus target,
target minus hand-over), to see whether those frames are shown before their
target. `ios/build/NFSMW-0.4.2-frame-trace-130.ipa`, 30120133 bytes, SHA-256 7be63fc5ebd1282921d807c045b8ec4a2197a9880702d9295947b81b250a2b1d, UUID E2CE10C7-0C6F-3D45-B395-67815BEDAD3F, codesign ok; iCloud
Desktop copy replaces 129.
