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
