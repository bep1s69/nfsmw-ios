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
