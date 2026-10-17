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
