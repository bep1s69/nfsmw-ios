# Development progress and session handoff

This is the entry point for continuing the battery work. Update the current
checkpoint and append meaningful observations, changes, tests, failures and
decisions as work proceeds. Do not rely on chat history or temporary files as
the only record. Keep measured results separate from hypotheses, including
negative or inconclusive results. Record the exact build, arguments, settings,
input paths, test commands, outcomes and next action for each experiment.

## Read first

- [Technical history and evidence](TECHNICAL.md): architecture, SDK patches,
  chronological experiment records, measurements, test limitations and build IDs.
  Old "pending" paragraphs are historical; use this checkpoint for current state.
- [Backlog](BACKLOG.md): open bugs (iOS 26 shader libraries, sun flicker, red FMV
  frame, dim edge band), parked iPhone loading issue, pipeline archive
  persistence, GPU capture, feature ideas. Do not reopen those during battery
  work unless requested or the issue recurs.
- `../HANDOFF_CHATGPT.md`: the original October 15 architecture/history handoff,
  present locally but intentionally untracked. Do not overwrite or stage it.
- Previous battery investigations, before repeating an experiment:
  `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/14 October 2026/BATTERY_FINDINGS.md` and
  `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/14 October 2026/BATTERY_OPTIMIZATION.md`.

## Working rules

- November 6 (Stefan): skip-unread resolves stays an Extra Args soak trial
  (`--nfsmw_native_skip_unread_resolves=true --nfsmw_native_resolve_labels=true`)
  until made default; remind him of these lines if he forgets.

- November 4 (Stefan, all threads): after every new dev IPA build, copy the
  `.ipa` (no zip) from `ios/build/` to iCloud Drive's Desktop
  (`~/Library/Mobile Documents/com~apple~CloudDocs/Desktop/`) and move any older
  dev IPA there to Trash (Desktop only, never from `ios/build/`). The latest
  stable release IPA always stays on the Desktop.

- November 2 (Stefan, latest): thermal and battery improvements are the main
  acceptance criterion; base performance is already good across devices. Seek
  concrete recurring-work reductions that scale across resolution settings and
  devices. GPU milliseconds/logical bytes are leads, not proof of lower energy.
  Keep largest-first priority and propose before source changes.


- November 2 (Stefan, latest optimization priority): tackle measured costs from
  largest to smallest. Prioritize dominant GPU work before small overlay/CPU
  opportunities. The sparse-overlay proposal is deferred, not approved.


- November 2 (Stefan, compact shared-data experiment): use existing baseline
  logs; only one new enabled correctness run needed. Do not request another
  baseline/A-B sequence without a concrete new reason. Keep energy claims
  limited to what the actual evidence supports.

- November 2 (Stefan, latest): park D-017 unless a very interesting new finding
  emerges. Focus on making actual CPU/GPU work as light as feasible to improve
  performance, battery and thermals. Preserve default visual quality; investigate
  and propose before code changes. Do not keep requesting stutter experiments.

- November 2 (Stefan): next 0.6.0 work is performance, battery and low-RAM
  devices, before the remaining items (My Cars taps D-016, free camera,
  Extra Options menu patches). He tests on device and records traces himself.

- November 2 (Stefan): free look defaults to inverted vertical (mouse and
  swipe). He tests in LiveContainer, so Info.plist keys of the IPA (pointer
  lock's UIApplicationSupportsIndirectInputEvents) do not apply there.

- November 2: never set GCKeyboard's `keyChangedHandler` in app code: SDL's
  iOS backend owns it (SDL_uikitevents.m) and replacing it removes all
  keyboard input from the game (dev21). Poll key state instead.

- November 1 (Stefan): builds use `-j 12` (M2 Pro, 12 cores; `-j 6` was
  for the old Mac). Time the next full build and record it in TECHNICAL.
  Version 0.6.0 (code 11) from dev5 on.

- November 1 (Stefan): nothing still in use may live in /private/tmp
  (cleared on reboot). Multiplayer SDK, LAN reference server, upstream
  source and the `multiplayer` worktree are now in `~/Developer/GitHub/`
  (`nfsmw-multiplayer-sdk`, `nfsmw-server-lan-research`,
  `nfsmw-multiplayer-upstream`, `nfsmw-ios-multiplayer`); the PC cross-play
  Wine bottle/game, image cache and archived research/logs are in
  `~/Developer/Debug/Most Wanted (2005) Debug/Multiplayer/`. Older records
  that name /private/tmp paths: see TECHNICAL, November 1, "/private/tmp move".

- November 1: `dev-0.5` (0.6.0) now contains 0.5.2 `main` and `multiplayer`
  (ced4ff6). Build it only against the multiplayer-patched SDK, into
  `~/Library/Caches/nfsmw-ios/build-0.6` (TECHNICAL, November 1, 0.6.0
  merges); the plain `ios` preset is for `main`. Run
  `patch_game_extra_options.py` first. Low-RAM devices / memory use is a
  0.6.0 goal (Stefan).

- November 1 (Stefan, 0.6.0 priorities): first all feasible Extra Options
  (including useful Xbox 360 prototype debug menu items) and performance/
  battery work; later better keyboard support, a menu redesign, a touch pass
  for the multiplayer screens, an Android check and dropping the iOS 18
  "experimental" label. 0.6.0 = `dev-0.5` + 0.5.2 `main` + `multiplayer`;
  merge only after his OK (plan: TECHNICAL, November 1; roadmap: BACKLOG).

- November 1 (Stefan, preview13 follow-up): try a few focused reverse-host
  discovery builds, prepare shared handoff for Claude because usage is low.
  Archive all five new logs in `1 November 2026`. PC-host endurance/finish/
  return-to-room/rematch success is confirmed by user; do not treat that path
  as still awaiting its first completed race. Phone hosting discovery fails.

- November 1 (Stefan): start reverse PC hosting now, initially as a separate
  **Host for PCs (Experimental)** option; integrate mixed hosting only after the
  separate directions work. This supersedes the previous session's testing hold
  and reverse-host deferral. Stefan will test both PC-host/mobile-join and
  mobile-host/PC-join when the build is ready. Keep native PC unchanged, all work
  local on `multiplayer`, and controls/main independently releasable.

- October31 (Stefan, PC UX): final goal is native PC discovery/join directly
  from this port, no extra script/software on PC. Experimental bridge is only
  investigation tooling, not the accepted final user flow.

- October31 (Stefan, after mobile device tests): explicitly approved investigating
  PC cross-play now with remaining usage; this supersedes earlier PC hold for
  this investigation. Keep everything on local multiplayer, preserve mobile
  success and separate controls release. Friend Motorola Edge30Fusion, Android14
  per recollection, Android/data denied; further Android testing on own Galaxy
  S21+ later. User subsequently supplied original server.dll/server.cfg into
  PC Game Files. No push/merge/release authorization.

- October31 (Stefan, preview3): iPhonehosts; iPadcannotfindit bothinQuickMatch
  andwhilehostwaitsinlauncher. SameWi-Fi permitsdevicecommunication peruser;
  LocalNetworkaccess enabledonBOTH devices. Treat these as confirmed user
  reports; do not repeatedly suggest enabling them. The Personal Hotspot test
  subsequently reached a shared room and exchanged peer packets, then both
  devices crashed (October 31 preview3); see current checkpoint.

- October 31 (Stefan, LAN preview1): tried both hosting roles without managing
  to play; setup described as clunky and extremely unintuitive. Improve the
  Host/Join flow with visible shared-lobby state and explicit race-role guidance;
  do not treat the supplied logs as proof of peer network failure or success.

- October 31 (Stefan, multiplayer implementation): approved starting LAN play for
  **iOS↔iOS and iOS↔Android**. PC cross-play waits until those work. Rename branch
  to `multiplayer` (local only); latest controls/test11 is the starting baseline.
  Main must remain independently releasable for fixed touch controls; no network
  work in its source, shared SDK or build output. Credit victorgbd for both the
  original Android networking and copied/adapted C++ lobby/compatibility work in
  CHANGELOG, explicitly acknowledging direct reuse. No push/merge/release approved.

- October 31 (Stefan, multiplayer research): investigate Android LAN methodology,
  Android cross-play and original Windows PC compatibility. **Implementation is
  initially held; Stefan subsequently approved implementation (rule above).**
  All multiplayer work stays on separate `multiplayer`, with no
  merge/push/release until ready, tested and explicitly authorized. Research-only
  branch forked from main `62c0dc7`; separate worktree
  `/Users/bep1s/Developer/GitHub/nfsmw-ios-multiplayer` leaves the active controls checkout intact.

- October 31 (Stefan, test8 results): profile-name taps select only; A remains
  manual. Options/race-details: vertical swipes select rows, horizontal swipes
  on the highlighted row change its value; taps can select another row. Event
  taps select first, a second tap on the selected event can launch. Try the
  entire event box for swipes (Challenge/Blacklist races/milestones/bounty).
  Add Rap Sheet page navigation, improve slow showcase motion and zoom gain.

- October 31 (Stefan, test7 follow-up): strict menu gestures must still skip
  intro movies and advance Press Start. Add opt-in other-app music mixing;
  map/car-preview swipe areas, category Up/Down and showcase drag/pinch where
  supported. Keep free-roam map behavior separate. Popup screens have OK/Cancel,
  not their own A hint: compare with PAD A while OK is selected if isolating
  the reported safehouse freeze. No ordinary-A-hint comparison was performed.

- October 31 (Stefan): the empty-space accept toggle also controls anywhere
  scrolling. OFF means taps on actionable controls and swipes starting inside
  scrollable widgets. Two-finger Back has its own independent live option,
  default ON. Selected carousel icons, selector chevrons, icon-only LT/RT and
  individual popup choices must work directly with anywhere gestures OFF.

- October31 (Stefan):confirmed dimbandbelow1x(inBattery mode),AirPods crackles,
  engine-sound fade,safehousecrash andevent-loadingfreeze fixed. Markthemclosed
  ratherthanrelistingasoutstanding;exactfixingversionsnotnewlyestablished.
  New0.5.2priority:polishmenu touch navigation against suppliedAndroidreference;
  inversionmustbeoptional,currentdirectiondefault;repeathelddrags,tappable
  visiblebuttonhints/icon-onlyLT/RT andleft/rightselectors.

- October30 (Stefan):0.5.1 is live. First0.5.2 features are live switching
  among all FPS caps and Eco/Balanced/Max. Audit profile effects (17PM holds
  locked60fps/1x inEco per user). Reopen CPU/GPU optimization at IDENTICAL
  graphics settings before quality reductions. Backlog comprehensive PC-style
  graphics menu with High Fidelity/High Performance presets; distinguish
  graphics quality presets from scheduling profiles. No0.5.2 push/release
  authorized merely by earlier0.5.1 authorization.

- October 30 (Stefan): approved verifying the downstream world-time clamp
  and simulation/render update accounting after test6 still slowed under
  load. Next trial adds diagnostics first; keep the confirmed60fps fix and
  accepted steady40 behavior, then make the scoped correction from evidence.

- October 30 (Stefan, 40 fps): truly smooth world/presentation motion
  matters more than minimal latency; roughly one extra frame of input delay
  is acceptable if it achieves that. Test2 felt mostly more jerky world
  motion, with only a little additional input lag; do not equate improved
  presentedTime statistics alone with an accepted fix.
- October 30 (Stefan): 0.5.1 hotfix scope is only the iPhone 14 Pro Max
  60/~40 cycling fix and the 40 fps frame-pacing fix. No unrelated additions.
- October 30 (Stefan): archive all logs, photos and other test evidence he
  sends in `~/Developer/Debug/Most Wanted (2005) Debug/`, under the relevant
  test folder with names similar to the previous evidence (device and test
  suffix). Preserve originals, never overwrite earlier evidence; record
  archived paths in TECHNICAL so the full test history remains available.
- October 28: AGENTS.md and CLAUDE.md are local only (Stefan): untracked
  and in .gitignore, not on GitHub. Keep them on disk; never re-add them.
  They remain in older history and on other branches (`dev-0.5`,
  `frame-pacing-60`); a merge that touches them must keep them untracked.
  Later on October 28 (Stefan approved): removed from all history with
  `git filter-branch` on every local branch and tag, force-pushed `main`,
  `release-0.4.1`, `frame-pacing-60` and tag `v0.4.0`. Commit hashes in
  older records refer to the old history (v0.4.0 3e2a74b is now e24238c);
  backup mirror and the broken "main 2" refs in
  `/Users/bep1s/Developer/Debug/nfsmw-ios-history-backup-2026-10-28`.
- October 29 (Stefan): today's `main` (planned as 0.4.3) is released as
  0.5.0; the `dev-0.5` work is now planned as 0.6.0 (branch not renamed;
  Stefan may rename it).
- October 27: post-0.4 work (0.5.0, now 0.6.0: Extra Options, Widescreen Fix
  features, PC mods) lives on the local branch `dev-0.5`; never commit it here. The
  exception, approved by Stefan: PC save import, in 0.4.0 because it works.

- October 27: all post-0.4 work (0.5.0: Extra Options, Widescreen Fix
  features, PC mods) lives on the local branch `dev-0.5` (renamed from
  `pc-mods-research`, made from `frame-pacing-60`); never commit it to
  `frame-pacing-60` or `main`. Stefan: Extra Options before PC modding. No code changes for it without
  Stefan's approval; no pushes.
- October 27: Stefan: 120 Hz simulation did not fix the 60 fps judder; off by
  default, switch kept in Advanced. Order of work: finish the save manager,
  then the motion blur switch (suspected judder cause: the mirror, drawn
  without motion blur, stays smooth).
- October 26: Stefan declared the movable/resizable HUD finished for now
  (IPA84): functional, not final; remaining items in BACKLOG.
- October 26: Stefan declared performance/battery solved for now (after the
  IPA63/64 profiles and IPA66 1x reflections). Battery leads stay in the
  backlog, parked; next work is QoL features (save manager, movable/resizable
  HUD, extra and in-game options, live graphics settings, pre-launch menu).
- October 24: Stefan records Instruments traces himself in the Instruments app,
  attached to LiveContainer (the plain one, not LiveContainer2/3), and sends the
  saved path; agents only analyze. Agent-driven `xctrace record` uses his usage
  limit and, recording the whole phone, made 13-21 GB raw files.
- October 24: 0.4.0 is held until it has more than battery tweaks that do not
  measurably help (Stefan). No tag or version bump; IPA51 is a test baseline.
- October 21: Stefan approved Utility QoS for all game threads as the default
  (`ios_utility_qos`, `ios_utility_qos_guest`); keep the Extra Args opt-out.
- Work locally on `battery-optimization`; do not push, publish, tag or release
  without explicit permission. Local commits are authorized.
- Preserve Stefan Stoica's existing Git author configuration; add no attribution
  lines. Do not commit game assets, generated game code, logs, traces or IPAs.
- Investigate and explain new source changes before implementation; obtain the
  user's approval. IPA24 ready-pipeline lookup reuse is implemented and its
  initial iPad check passed. No next source change is approved.
- Preserve default visual fidelity, stability and functionality. Quality
  reductions belong only in optional Battery mode or its settings.
- Make isolated changes. Validate on device before stacking another source
  change. Small experiments get short correctness runs; accumulate them for
  meaningful power comparisons rather than demanding repeated tiny race A/Bs.
- Preserve user-owned and pre-existing changes, especially the heavily patched
  sibling SDK. No SDK source edits are required for the current experiment.
- Persist observations and results in Markdown as explicitly requested on
  October 18, including inconclusive/failed tests and pending device validation.
- October 19: everything (changes, test results, bugs and feature requests)
  must be documented in this repository so both Claude and ChatGPT Codex can
  continue from it. See [AGENTS.md](../AGENTS.md) for what goes where. Open bugs
  and feature ideas live in [BACKLOG.md](BACKLOG.md).
- October 19 session protocol: read AGENTS completely, this checkpoint, backlog
  and newest TECHNICAL evidence in that order; inspect `git status` and
  `git log --oneline -15`, including other-agent documentation changes; state
  current state/next step before working. Preserve and report others' local work.
  Use existing records, keep backlog IDs stable and record exact observed
  commands/results plus failures and limits. End every session, even unfinished,
  with dated TECHNICAL evidence, current next action, matching backlog updates
  and a local commit; document why anything must remain uncommitted. Private
  material stays in ignored local folders, with paths recorded in the docs.

## Workspace and build

### Isolated multiplayer preview (branch `multiplayer` only)

Read-only Mac path diagnostic (does not change the IPA or network settings):

```sh
clang++ -std=c++23 -fobjc-arc tools/ios/lan_path_probe.mm -framework Foundation -framework Network -o /private/tmp/nfsmw-lan-path
/private/tmp/nfsmw-lan-path <current-host-IP> 10902
```

Five-second bounded TCP attempt; reports Apple connection state/error/path reason,
including local-network-denied if the API reports it. A zero denial reason does
not prove every network policy permits traffic. Mac permission state is not
proof of phone permission state. Use known-good listener and closed-port controls.
Temporary diagnostic servers from October31 are STOPPED; do not assume207lobby
or8080HTTP still running. Do not mistake approved/willing hotspot test for success.

Do NOT use the ordinary `ios` preset for this branch: it shares the controls
build directory. Current worktree `/Users/bep1s/Developer/GitHub/nfsmw-ios-multiplayer`; SDK
`/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk`; build `/Users/bep1s/Library/Caches/nfsmw-ios/build-0.6`.
The branch is based on main/test11 `19177b6`, merged in `f848ce3`.

To reproduce isolation from an already prepared SDK, from this branch:

```sh
python3 tools/ios/create_multiplayer_sdk.py --source /Users/bep1s/Developer/GitHub/rexglue-sdk-ios --destination /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk
NFSMW_SDK=/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk python3 tools/ios/patch_ios_multiplayer.py
```

The destination must not exist. Snapshot copies all prepared source/dependencies
except Git/build metadata, then changes submodule validation to accept source
folders without `.git`. Multiplayer patch refuses the canonical shared SDK and
requires explicit `NFSMW_SDK`. Apply/revert/check is transactional. Preparing a
fresh SDK on this branch also includes the multiplayer patch last; always pass
an isolated destination. Preserve controls SDK changes as the snapshot baseline.

Use a private copy of `ios/generated/` from the validated controls build (no
shared writable generated directory); fresh generation also works with this
branch's existing USA pipeline and isolated SDK. Native shaders may be shared
read-only. Configure/build explicitly:

```sh
cmake -S ios -B /Users/bep1s/Library/Caches/nfsmw-ios/build-0.6 -G Ninja -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=18.0 -DCMAKE_BUILD_TYPE=Release -DNFSMW_SDK=/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk -DNFSMW_NATIVE_SHADERS_DIR=/Users/bep1s/Library/Caches/nfsmw-ios/shaders/lib
cmake --build /Users/bep1s/Library/Caches/nfsmw-ios/build-0.6 --target ipa -j 12
```

Native shader trial build note (November 2, dev41): the normal
`tools/native/build_shaders.sh` now runs `rewrite_foliage_early_alpha.py` after
the existing shadow rewrites. This fails on an unaudited target-body change;
do not bypass its guard or update the digest without a new dataflow review.
For a single-library build, preserve the existing lib/ manifest and metadata,
translate the target container, run `rewrite_shadow_filter.py`, then
`python3 tools/native/test_foliage_early_alpha.py <baseline-target.hlsl>`,
then `rewrite_foliage_early_alpha.py <target.hlsl>`. Compile/link ONLY that target
with `xcrun -sdk iphoneos metal -w -O2 -std=metal3.1 -D__air__ -fno-fast-math -ffp-contract=off -mios-version-min=18.0 -c <target.metal> -o <target.air>`
and `xcrun -sdk iphoneos metal -mios-version-min=18.0 <target.air> -o <target.metallib>`.
Copy just the target into the configured native shader lib/ cache; verify all
other hashes and unchanged constant-range/texture-mask metadata before packaging.
The source body for the host test is generated private data, kept ignored.
If xcrun reports missing Metal Toolchain, install Apple's component with
`xcodebuild -downloadComponent MetalToolchain` (dev41 installed 27B47).
In this environment Metal compilation also needs access outside the sandbox.
The runtime switch is restart-only and default off; false keeps the late alpha
path. Do not enable by default merely because offline compilation passes.

Guest-culling host check (November 2, dev42):
`python3 tools/native/test_guest_culling.py` compiles the production decision
helper and extracted renderer integration/EncoderState/counters with ARC and
ASan/UBSan against a fake Metal encoder; no GPU/device rendering. Existing IPA
build command above unchanged. Runtime flag default false, restart required.
No shader rebuild needed; preserve all dev41 native shader libraries.

Host checks (local listener permission required):

```sh
python3 tools/ios/test_multiplayer.py --sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk --reference-server /Users/bep1s/Developer/GitHub/nfsmw-server-lan-research
python3 tools/ios/test_multiplayer_transport.py --sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk
python3 tools/ios/test_menu_touch.py
python3 tools/ios/test_lan_setup.py
python3 tools/ios/test_pc_host.py --sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk --ip <this-Mac-LAN-IPv4>
python3 tools/ios/test_pc_host.py --sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk --ip <this-Mac-LAN-IPv4> --simulate-broadcast-failure
python3 tools/ios/test_lan_interface.py
python3 tools/ios/test_lan_roster.py
python3 tools/ios/test_pc_gateway.py
python3 tools/ios/test_pc_udp.py
```

Reference server must be the pinned unchanged upstream tree in TECHNICAL.
Preview2 launcher flow is Game → Host or join a game: choose Host on one
phone and Join on the others, discover/select the remote host, then Launch game.
The ordinary launcher Play button clears LAN mode and starts single-player.
Names default to iPhone/iPad plus local IP suffix; saved valid names retained.
Back cancels setup and stops this device's host. Setup logs use [lan-setup] in
boot.txt. UI discovery calls upstream BuscarServidores; broadcasts plus unicast
fallback for /24..30, ignores own addresses, manual entry available. iOS/LiveContainer
network permissions still apply; no multicast entitlement is assumed.
Preview3 retains UDP10902 unicast search, explicitly binds before sending, and
falls back to TCP30960 @dir queries if no UDP replies are accepted. This uses
existing EA protocol, not a new host service. Scan is bounded to nearby /24;
32concurrent/350msperprobe/4soverall TCP phase. Generic LAN host label when only
TCP found it; no name/playercount advertised in that old directory response.
[lan-discovery] diagnostics in boot.txt expose the failed stage. No multicast
entitlement assumed, no broadcast on Apple discovery socket. ManualIP unchanged.
Internal mode `off` (default), `join`, `host`;
`lan_server` IPv4/hostname and `lan_gamertag` (empty uses User). Preflight checks
TCP10902; duplicate names/unreachable servers stop launch with an error. Host
shows its address before game launch; use Xbox Live → Quick Match. Keep host
foreground. Host stats in Documents/data/lan_server; log logs/servidor_lan.log.
No background audio workaround added; discovery UI added in preview2. iOS local-network prompt
uses the added usage description; LiveContainer's permissions govern its process.
Settings map to upstream `red_lan`, `red_live`, `grant_user_privileges`,
`red_dns`, `red_ip`, with network diagnostics `red_registro=true` in preview.
Extra Args still override settings. These are not real Xbox Live credentials.


Main repository: `/Users/bep1s/Developer/GitHub/nfsmw-ios`.
SDK: `/Users/bep1s/Developer/GitHub/rexglue-sdk-ios`, also on the battery branch,
with extensive pre-existing local platform patches and submodule changes.
The Android reference repository is the sibling `NFSMW-Recompiled-Mobile`.

Build from the main repository's `ios` directory:

```sh
cmake --build --preset ios --target ipa -j 12
```

The actual build directory is `/Users/bep1s/Library/Caches/nfsmw-ios/build`;
compiled shaders are in the sibling cache `shaders` directory. The build dir
must be configured with `-DNFSMW_NATIVE_SHADERS_DIR=$HOME/Library/Caches/nfsmw-ios/shaders/lib`;
if that cache entry is empty the IPA has no `NativeShaders` and every game draw
is skipped (IPA25). Check `unzip -l <ipa> | grep -c metallib` before handing off. The IPA is
copied into `ios/build/NFSMW.ipa`. CMake/Ninja is used; there is no Xcode project.
On this restored laptop, invoke generation with the already built host CLI:
`python3 tools/ios/generate_code.py --rexglue /Users/bep1s/Developer/GitHub/rexglue-sdk-ios/out/mac-arm64/Release/rexglue`.
The old default host cache still points to Documents; current host build is
`<SDK>/out/build/mac-arm64-restored`, with the host-only shim documented in
TECHNICAL October30 test7. Never pass that shim to the iOS compiler.

For USA generation, `tools/ios/generate_code.py` now also applies
`patch_game_world_step_trace.py` after frame_ticks. Existing
`--nfsmw_frame_ticks_log=true` enables the downstream [world-step] diagnostic
at managed40 while driving; default false. Regenerate before building from
a fresh checkout, or apply that script to existing patched generated code.

Keep uniquely named copies for device tests and record UUID/SHA256, build,
ZIP-integrity and codesign results. Native shader libraries should remain
byte-identical for a CPU-only change. Install/test via LiveContainer; cold
force-quit it when changing restart-only arguments.

## Architecture relevant to optimization

Guest PPC is statically recompiled to C++/ARM64; this is not a general CPU
interpreter. Original engine and Xbox graphics code still build a PM4 command
stream; the SDK command processor preserves ordering, queries, fences and
writebacks. The default renderer snapshots draws and encodes native Metal on
a serial queue; Vulkan rendering is bypassed. Decoded geometry/textures,
constant banks, pooled uploads, residency sets and completion-gated resource
reclamation preserve GPU lifetimes. Bypassing guest/PM4 work requires semantic
equivalence; do not treat the whole guest CPU share as removable overhead.

At 30 FPS the app requests 60 Hz and uses display-locked guest vblank with
sleeping waits. Blindly changing CADisplayLink to 30 breaks the current lock
condition. CPU utilization and GPU milliseconds alone are not energy metrics.

## Current checkpoint — November 4, 2026 (continued from November 3)

**November 6, dev92 BUILT: iPhone Duo black inner screen (GitHub #14, D-019
Duo).** The app picked "its" scene by `scene.screen == UIScreen.mainScreen` in
eight places; on a foldable mainScreen is likely one panel while the app shows
on the other, so the game layer was never attached (black, sound plays, even
when launched on the inner screen). New `ios/src/app_scene.h`: the app's scene
is the one with the application role; launcher screen size and 120 Hz check
use that scene's screen; a screen is external only if it is neither main nor
the app's. Startup log lists every scene and screen. Untested (no Duo); IPA
`ios/build/NFSMW-0.6.0-dev92-duo-scene.ipa` (SHA256
eabf57f3d0426519e8d64a622f1aa88424e0dea6594f29f90b59e31dd6d119f0) for the
reporter. Golf engine stutter (#15) waits for Stefan's Golf logs.

**November 6, dev91 on the iPhone: normal (Stefan), all switches active in the
log, drain 21.6 %/h at 27 % brightness vs dev89 22.5 at 18 %, CPU instructions
-2 %.** Single run; keep the defaults. TECHNICAL "dev91 iPhone Power Profiler".

**November 6, dev91 BUILT: the unsure CPU switches default on too (Stefan:
"make the unsure ones on by default and we'll follow up with a test or 2").**
`nfsmw_native_record_memo`, `nfsmw_native_target_lookup`, `nfsmw_native_pipeline_lookup` and `nfsmw_native_attribute_bulk_compare` now true (attribute lookup was already on). Their host tests are still
stale (open). IPA `ios/build/NFSMW-0.6.0-dev91-cpu-defaults-all.ipa` (SHA256
adee074212ee67215804be05af991edeb60253f9b0a485ab0b953032d4e28741). Next: Stefan's test runs; first suspect for any wrong picture or
crash is this group (turn off one at a time in Extra Args).

**November 6, dev90 BUILT: CPU-reducing switches default on (Stefan: "make all
changes that reduce cpu usage the default, even if not proven for battery").**
On by default: `nfsmw_native_skip_unread_resolves`, `nfsmw_native_guest_culling`, `nfsmw_native_color_handoff`, `nfsmw_native_foliage_early_alpha` (now true in native_renderer.mm) and `ios_multi_wait` (now `--ios_multi_wait=true` in GameArguments, ios_main.mm, so the dev89 `ios_multi_wait_own` word is live). Each can still be turned off in Extra Args.
Stefan can drop `skip_unread_resolves` and `resolve_labels` from his Extra Args.
Not flipped in dev90 (flipped in dev91): record_memo and the lookup trio.
Left off: diagnostics, shadow depth handoff (wrong picture), native D3D draws
(parked), `ios_cp_wait_wptr` (adds wake-ups). Host tests test_color_handoff and
test_guest_culling PASS with the new defaults. IPA
`ios/build/NFSMW-0.6.0-dev90-cpu-defaults.ipa` (SHA256 9e63d66e072e879c344cbf692f90592bcdab6086083dd5c6f85c83478a62df8b). Next: Stefan's
normal-session run (picture, audio, any "[native] unread resolve ... sampled now").
TECHNICAL "dev90 CPU defaults".

**November 6, dev89 Power Profiler A/B: no battery change** (22.6 vs 22.5 %/h,
CPU impact 4.56 vs 4.59, iPhone, 18 %, Nominal). Wake cuts on non-frame
threads are not a battery lever (as Nov 4); dev90 wake ideas dropped unless
Stefan asks. dev89 defaults kept (audio clean). TECHNICAL "dev89 iPhone
Power Profiler A/B".

**November 6, dev89 measured on the iPhone (System Trace):** −3,015 blocking
waits/s (−20 %): XMA worker and the two guest sleepers gone as planned; audio
clean (AirPods). Audio worker unchanged (~1,120/s): its wait is alertable and
the alertable multi-wait wrapper still slices at 1 ms; plus a 1 us Sleep in
XAudioGetVoiceCategoryVolumeChangeMask (187/s). TimerQueue unchanged: ~1,000/s
is the kernel's 1 ms KeTimeStampBundle tick timer (game timers only ~200/s).
Next (proposal, awaiting Stefan): alertable waits wake on the callback word
instead of 1 ms slices; drop the 1 us Sleep; probe a longer tick only if the
game's use of the tick count allows. TECHNICAL "dev89 iPhone System Trace".

**November 6, dev89 BUILT: wake-up cuts (Stefan approved fixes 1-3 + census).**
`tools/ios/patch_ios_wake_cuts.py` (SDK, after patch_ios_multi_wait): alertable
sleeps wait the whole time (`ios_alertable_wait`, true), no XMA worker wake
after an inline kick decode (`ios_xma_kick_wake`, false = skip), multi-waits
on their own word (`ios_multi_wait_own`, true; only matters with
`--ios_multi_wait=true`), census `ios_timer_census` (false). IPA
`ios/build/NFSMW-0.6.0-dev89-wake-cuts.ipa` (SHA256 1b8a2de44844d685c95eb26b87b938c728e4e4ccb9e3f65a91e0a738121272d5).
Next: Stefan's iPhone run (listen for audio, issue #15) and a System Trace or
Power Profiler A/B. Stefan also wants to move further from the 360 roots:
replacing XMA with native audio is a separate, unscoped project.

**November 6, wake-up sources outside D3D analysed (dev88 iPhone trace); proposal awaiting Stefan.**
On dev-0.5 (not native-d3d). Causes found: (1) `rex::thread::AlertableSleep`
polls for APCs in 1 ms slices, so the game's 5 ms and 10 ms alertable sleeps
(XThread14B27, XThread10407) wake 5-10 times each (~1,780/s); (2) every XMA
kick decodes inline and then wakes the XMA worker for a sweep that mostly
finds nothing (~1,500/s); (3) the audio worker wakes ~930/s for ~188 real
permits/s (multi-wait's single global sequence, or 1 ms polling without it);
(4) TimerQueue ~1,240/s are two guest threads re-arming one-shot timers
(game data, unknown due time). Proposed: (1)-(3) as switchable fixes in one
build plus a timer due-time census for (4); no code until approved. Prior
negative result kept in view: dev56-dev60 wake cuts on E-core threads showed
no measurable iPad drain change. TECHNICAL "November 6: wake-up sources".

**November 6, dev88 confirmed on the iPhone:** the displayed frame is shown
from the post target on every frame (300/300), picture normal (Stefan), the
0.42 ms copy gone. Soak continues with the same two lines. Stefan wants to
pursue a native Direct3D-to-Metal layer (replacing the game's statically
linked D3D functions instead of decoding PM4): separate project/plan.
Done and PARKED the same night (Stefan): local branch `native-d3d` (not
pushed) holds the plan, N0-N2a and evidence; the device object carries the
draw state (picture normal) but the saving (~3-5% CPU) is not worth it now.
The shared SDK has its inert `patch_ios_d3d_marker.py` applied (not listed in
this branch's prepare_sdk.py). XMA replacement judged not worth it either.

**November 6, dev88 BUILT: half taps removed (no gain); the displayed frame shown from its target.**
The skip-unread soak never skipped anything: the unread copy is the displayed
one. dev88 (same soak flag) presents it straight from the post target.
IPA `ios/build/NFSMW-0.6.0-dev88-present-from-target.ipa` (SHA256 4bfba4d86ebbfde13efc1966e7f5a1ac7b5a43e05e41459e92545a89d4cb2518).
Next: Stefan's iPhone race with the soak lines; expect "M shown from the
target" counts and no "blit: resolve copy ... -> 09222000" line.

**November 6, dev87 BUILT: post composite blur taps from a half-size scene (default off).**
`nfsmw_native_post_half_taps=false`; composite library rebuilt with the new
rewrite (bit-off path = recompiled baseline). IPA
`ios/build/NFSMW-0.6.0-dev87-post-half-taps.ipa` (SHA256 bc8d4019186e527f59bf8020ad06e79958b8d6f33bbeec0d835ad4da84fa66af). Next:
Stefan's iPhone race with it on + pass counters; compare post pass d47c with
dev81 (1.99 ms) and judge blur/depth-of-field look. TECHNICAL "dev87".
Also: 0.85x scene + sharp HUD only as a Battery-mode idea (Stefan).

**November 6, shadow depth handoff PARKED:** dev86 self-test shows the iPhone
reads depth through the shader heap and the (R,0,0,1) view exactly like the
copy, so the fault is in ownership/order, not reads. Flag stays off; BACKLOG
"Native GPU follow-ups" has the next step. TECHNICAL "dev86 self-test".

**November 6, dev85 handoff WRONG on the iPhone (darker, shadows off); dev86 self-test.**
Keep `nfsmw_native_shadow_depth_handoff` off. dev86 (SHA256 72ccd6b8a1f6fef5520d6f37d3949f1f6cb4168ad99554b6bcb2fe11b04dcd6b) logs
how the iPhone GPU reads a depth texture through the shader heap. Next: one
launch with the flag on, reach a race start, send the log; then fix or drop.

**November 6, dev85 BUILT: shadow depth handoff (default off).** The two
1600x1600 shadow depth copies (~0.44 ms iPhone) are replaced by handing the
depth texture itself to the receivers through an (R,0,0,1) view.
`nfsmw_native_shadow_depth_handoff=false`. IPA
`ios/build/NFSMW-0.6.0-dev85-shadow-depth-handoff.ipa` (SHA256 22be06e20d67a26fe9a4398c562aea8e2c5e6a3208fb4cdfdcaf292423fb7fa3).
Next: Stefan's iPhone race with it on (+ his soak args, pass counters, resolve
labels); check car and world shadows. TECHNICAL "dev85".

**November 6, skip-unread resolves: long soak by Stefan (decision).** Not
testable in one session (race replays do not exist in this game). Stefan
keeps `--nfsmw_native_skip_unread_resolves=true --nfsmw_native_resolve_labels=true`
in Extra Args for normal play until it can become the default; remind him if
he forgets. In his logs look for "[native] unread resolve ... sampled now".
Next: unidentified main-scene shader d1a189fd (read-only source recovery).

**November 6, dev84 BUILT: skip large resolves nothing reads (default off).**
dev83: the post copies to 09222000 (0.42 ms) and 08dbb000 are never sampled
(1200 frames, pause menu included). `nfsmw_native_skip_unread_resolves=false`
leaves such copies out. IPA `ios/build/NFSMW-0.6.0-dev84-skip-unread-resolves.ipa`
(SHA256 a472b44271ea82f32e15ed5f427417329fbf8ddc70fbf9202140061e2c96f85e). Next: Stefan's iPhone race with it on + pass counters
+ resolve labels; check menus, pause, race end, replays. TECHNICAL "dev84".

**November 6, dev82 BUILT: one-time log of why large colour resolves stay linear.**
dev81 split: colour copies ~0.75 ms (post intermediate 0.42 ms LINEAR, final
0.33 ms); depth copies 0.44 + 0.34 ms. Fence/plant shader 684f read: one
diffuse fetch, the shadow 9-tap (already 4 gathers) and a few ALU ops, so
its ~1.2 ms is mostly drawing ~500 small objects, not removable shader work.
IPA `ios/build/NFSMW-0.6.0-dev82-linear-resolve-log.ipa` (SHA256 db0e753a0f9c19337488b5ff9b3e28991b12ddf3a6d9b9f7cb47e9097c0ab99a).
Next: one iPhone race with pass counters (resolve labels optional) to read
the "[native] linear resolve" lines, then make that copy tiled. Other
follow-ups queued in BACKLOG "Native GPU follow-ups".

**November 5, dev81 BUILT: dev80 trials removed (negative), resolve-copy labels.**
Post blur skip slowed the post pass (2.38 -> 2.78 ms); masked sky-last never
applied. Both removed, original composite library restored.
`nfsmw_native_resolve_labels=false` names each resolve copy in the pass
profile. IPA `ios/build/NFSMW-0.6.0-dev81-resolve-labels.ipa` (SHA256 841518017e0cca9dfe1e14f62ff7d5390ae9362fe6a1dc61c3064165b52c3c6f).
Next: Stefan's iPhone race with `--nfsmw_native_resolve_labels=true
--nfsmw_native_pass_counters=true` (no cost probe), then cut the largest
copies. TECHNICAL "dev81".

**November 5, dev80 BUILT: post blur skip + masked sky-last trials (both default off).**
dev79 full probe (iPhone): final post composite 20710a9a 12.9 % of the
frame (1 draw), fences 7.5 %, sky 5.5 % (never deferred in cube/mirror,
mask 7). `nfsmw_native_post_blur_skip=false` (shader bit 14, new rewrite
script, one library rebuilt) and `nfsmw_native_sky_last_masked=false`.
IPA `ios/build/NFSMW-0.6.0-dev80-post-blur-skip-sky-masked.ipa` (Desktop).
Next: Stefan's iPhone run with both on + cost probe all; check blur/depth of
field, sky in reflections and mirror. TECHNICAL "dev80".

**November 5, dev79 BUILT: tree edge LESS default ON (Stefan approved) + full cost probe.**
dev78 run: identical picture, trees ~18 % -> ~15.5 % of the frame. dev79 adds
`nfsmw_native_cost_probe_all=false` (diagnostic: every shader in turn, sky-wait
census) to find what in the iPhone post pass and sky is left to cut. IPA
`ios/build/NFSMW-0.6.0-dev79-tree-edge-default-probe-all.ipa` (Desktop).
Next: Stefan's long iPhone race with `--nfsmw_native_cost_probe=true
--nfsmw_native_cost_probe_all=true --nfsmw_native_pass_counters=true`.
TECHNICAL "dev79".

**November 5, dev78 BUILT (approved trial): tree edge pass depth LESS, default off.**
dev77 cost probe (iPhone native): trees 27d82ea0 2.74 ms median, then sky
1.02, shadow casters 0.78. Tree edge pass re-shades pixels the solid pass
drew; `nfsmw_native_tree_edge_less=false` switches its depth test to LESS.
IPA `ios/build/NFSMW-0.6.0-dev78-tree-edge-less.ipa` (Desktop). Next:
Stefan's iPhone run with the flag + cost probe + pass counters; check tree
edges look the same. TECHNICAL "dev78".

**November 5, dev77 BUILT (Stefan approved): sparse touch overlay default ON.**
`nfsmw_native_sparse_touch_overlay=true`; `=false` restores the full-screen
draw. IPA `ios/build/NFSMW-0.6.0-dev77-sparse-touch-default.ipa` (Desktop;
dev76 trashed from Desktop). Stefan tests on the iPhone for now; iPad
comparison after all GPU changes. Next: B2 assessment (final-resolve copy,
~0.2 ms) vs larger targets. TECHNICAL "dev77".

**November 5, dev76 sparse touch overlay ON, iPhone: present 1.17 -> 0.44 ms,
controls identical (Stefan).** ~13.5 % of the screen still blended. Proposal
to Stefan: default ON (iPad check in the same build), then B2. TECHNICAL
"dev76 sparse touch overlay ON".

**November 5, GPU-at-native thread: dev76 sparse touch overlay BUILT (default off):**
dev75 native/60 Balanced pass profiles, both devices (logs
`Debug/5 November 2026/dev75_{ipad,iphone}_native60_pass_profiles_nfsmw.log`):
~15 ms GPU per frame driving; main scene 65 % iPad / 46 % iPhone, then post
(iPhone), cube faces, present, shadow map, resolve copies. Stefan approved
B (cheaper present) and D (shadow depth copies). A (half-rate cube) is the
existing Car reflections setting; fixed reflection rates went to BACKLOG.
D turned out to need shader-library changes (the copies are read): parked in
BACKLOG awaiting Stefan. B1 built: `nfsmw_native_sparse_touch_overlay=false`
(restart-only) blends the touch layer only over occupied 32 px tiles.
IPA `ios/build/NFSMW-0.6.0-dev76-sparse-touch-overlay.ipa` (on Desktop).
Next: Stefan's enabled run with `--nfsmw_native_sparse_touch_overlay=true
--nfsmw_native_pass_counters=true`, compare "present: main display" with the
dev75 logs and check controls look identical. B2 (final-resolve handoff,
~0.2 ms) next after that. TECHNICAL "dev75 native pass profiles; dev76".

**November 5, dev75 BUILT (Stefan approved both):** Balanced at the 30 cap on
every device = frame threads + render queue at Background with the original
adaptive late-swap boost as safety net (`performance_profile.h`); MetalFX
removed from the launcher and in-game options (renderer path kept, cvar
`nfsmw_native_metalfx` default off). Old 30 cap via Extra Args:
`--nfsmw_adaptive_qos_original=false --ios_background_qos=false` (phones).
Next: Stefan's 17 Pro Max A30/new-30 pair, an iPhone 14 Pro Max drive at 30
and a quick iPad 30 check; watch `[adaptive-qos]` boosts in the logs.

**November 5, iPhone sizing:** E60 (~7 % less, stutters) and E40 (−26 %, inconsistent fps) not usable on the phone; E30 smooth at 10.8 %/h (no A30 baseline). Proposal awaiting Stefan: Balanced 30 cap on every device at Background with the late-swap boost as safety net (TECHNICAL, "iPhone Balanced on efficiency cores").

**November 5, iPad battery thread closed (dev74, 616f66f):** CPU micro-cuts at
their floor (24.4–24.9 %/h at 60). Next, per Stefan: iPhone battery in a new
thread; GPU work at native deferred to a later thread (first step: Metal
System Trace at native, Balanced 60, T block, 10–15 s driving).

**November 5, dev73:** iPad 30/40 caps: Balanced = frame threads + render queue
at Background (16.3 %/h, smooth); Eco also lowers normal-priority workers
(12.5 %/h, isolated late frames). Profile wording/function overhaul wanted
later (Stefan). dev72/73 render-queue trims await a power run. Next: power runs
60/40, then a fresh Time Profiler for the next tier.

**November 5, dev71 (defaults):** iPad Balanced 60 fps 24.4 %/h (E cores,
smooth); 30/40 caps: frame threads, render queue and normal-priority guest
workers at Background, raised-priority (audio) workers at Utility: 12.5 %/h at
40 with clean audio and a few isolated late frames. Next: Stefan's choice of
GPU work (matters mostly at native) or more CPU overhead cuts.

**November 5, dev66 40 cap confirmed: 16.3 %/h, "perfect" (Stefan).** Next: CPU
cuts on the frame threads for 60 fps (still ~24 %/h); iPhone in its own thread.

**November 5, dev66 BUILT:** dev65 40 cap 12.5 %/h but microstutters and audio
cut-outs (guest audio decode starved at Background); the 60 Background/Utility
trial stays on Utility (24.6, no saving). dev66 lowers only frame threads +
render queue at 30/40. Next: Stefan's 40-cap run with audio check.

**November 4, dev65 BUILT (iPad 30/40 caps at Background QoS by default):**
dev64: 40 cap all-Background 12.6 %/h at an almost perfect 40; 60 cap
all-Background 15.6 %/h unsmooth; workers-only and improvements at Utility
within noise of 24.4. dev65 makes tablet Balanced at 30/40 use Background and
adds a Background/Utility adaptive trial for 60. Next: Stefan's 40-cap
confirmation and the 60 adaptive trial.

**November 4, dev63 BUILT (Background QoS trial, default off):** dev62
confirmed 24.4 %/h at 1.5x; iOS Low Power Mode gives 16.8 %/h with minor
drops (clocks, not work). dev63 `--ios_background_qos=true` tries lower
classes for the Utility threads. Next: Stefan's 1.5x run with it.

**November 4, dev62 BUILT (iPad Balanced on efficiency cores):** sizing run Q
(frame threads at Utility, no boost) 24.0 vs ~28 %/h, smooth (Stefan); 60 Hz
sim saves nothing. dev62 restores the tablet profile (6+ E cores). Time
Profile: render queue 29 % of CPU (Metal submit 23 % of it), GPU Commands
19 %, guest code ~44 %. Next: Stefan's dev62 confirmation drive (+ iPhone
unchanged check); then render-queue submit/Record cuts toward 20 %/h.

**November 4, dev60 BUILT (multi-object waits, ON by default):** the audio
worker's WaitAny no longer polls every 1 ms (`ios_multi_wait`, false = old).
Next: Stefan's iPad A/M run + listening check; then the CP flag writer and
render-queue CPU.

**November 4, dev59 (defaults):** dev58 submission wake and the GPU trials at
1.5x showed no battery change; `ios_cp_wait_wptr` now default false. New
Balanced is ~27–28 %/h on the iPad (from 32.9) with the same smoothness, from
dev55. Next: Stefan's choice among audio multi-wait, CP flag writer search,
render-queue CPU.

**November 4, dev58 BUILT (CP wait wakes on submissions, ON by default):**
dev57: boosting one frame thread saved nothing (B 27.9, G 29.0, M 29.4 %/h),
keep both. The CP's only WAIT_REG_MEM waits for the CPU to clear memory
0x1FCA5004 in 1 ms laps; dev58 also wakes it on every submission
(`ios_cp_wait_wptr`) and logs open input devices (the UI wait is still capped
at 1 ms). Next: Stefan's iPad A/W set.

**November 4, dev57 BUILT (boost selector, default unchanged):** dev56 U run
27.7 %/h (no measurable change vs dev55 27.1); Stefan keeps `ios_event_wait`
on. dev57 adds `ios_boost_threads` (both/gpu/main/none) and `[ui-wait]`
counters. Next: Stefan's iPad B/G/M Power Profiler set with the census on.

**November 4, dev56 BUILT (UI-thread event wait, ON by default):** SDL's iOS
event loop polled every 1 ms (~2,800 wakes/s on the UI thread); dev56 waits on
the run loop instead (`ios_event_wait`, false = old polling) and adds a
logging-only WAIT_REG_MEM census (`ios_cp_wait_census`). Audio multi-wait
deferred. Next: Stefan's iPad A/U Power Profiler + input check.

**November 4, dev55 BUILT (exact-wake hand-off, ON by default):** dev54
measured 400 us zero-length sleeps at 28.5 vs 32.9 %/h (record memo 32.6, no
benefit). Stefan chose the device-independent fix: the two frame hand-off
waits sleep on the hand-off word and both writers wake them
(`nfsmw_handoff_wait`, `--nfsmw_handoff_wait=false` restores polling). Next:
Stefan's iPad Power Profiler A (off) / H (on), pacing and menus/loading check.
Result: A 32.7, H **27.1 %/h** (−17 %), pacing unchanged; iPhone drive normal. Next: Stefan's choice of the remaining plan items (one boosted thread, render-queue CPU).

**November 4, dev54 BUILT (probe, default unchanged):** battery work now starts
from new Balanced (dev51, 34.1 %/h). The game main loop and render threads
wake ~6,800 times/s on 100 us zero-length guest sleeps (sub_82441DB0,
sub_82441B60). `--ios_delay0_us` (default 100) probes their cost. Next: Stefan's
one Power Profiler session A/B/C (baseline, record memo, delay 400); then an
exact-wake fix if C helps. TECHNICAL "November 4: battery plan".

**November 3, dev51:** iPad System Traces showed tablet Balanced running the
main loop and GPU-commands threads 100% on E cores (~1.9x core time); the
tablet profile is removed, Balanced boosts them while driving everywhere.
Next: iPad Balanced check, then Power Profiler old/new Balanced vs Max, then
the GPU trial comparison at native.

**November 3, dev50:** iPad camera smooth (step count + 2 µs bias, 2.8% zigzag,
no start burst; Stefan "fully smooth"), both now default. Next: iPhone
regression drive; then Balanced/core scheduling (step 2, System Traces from
Stefan when available) and the pending OFF/ON GPU trace comparison.

**November 3, dev48:** iPad camera sawtooth is tied to the 120 Hz simulation
(sim 60: 2.9% vs 37.6% zigzag) and likely to the iPad's exact 16.6667 ms
quantum sitting on the 2-step boundary. Stefan wants the 120 Hz sim fixed, not
per-device sim 60. dev48 adds default-off `nfsmw_world_quantum_bias_us` to
confirm; then fix the guest step loop properly (not yet located).

**November 3, dev47:** full-screen Extra arguments editor (Stefan's request),
untested. iPad findings today: Balanced tablet profile's Utility QoS causes big
host hitches; heavy sections at native are GPU-near-budget; at 1.5x/Max the
remaining judder is an iPad-only camera sawtooth (37.6% vs iPhone 1.8% zigzag
frames), cause open. Matched OFF/ON trace comparison still pending.

**November 3, iPad crash loop fixed in dev46 (device check pending):** a damaged
pipeline cache made Metal abort inside our background save at every launch
that added pipelines. A `.saving` marker now makes the next launch discard an
archive whose save never finished. Stefan prioritized this before the OFF/ON
trace comparison (still next after it). TECHNICAL “iPad crash loop”.

**November 3, dev45 device run: main copy removed on 100% of driving frames**
(3900/3900), 0 misses/mismatches/late passes, visuals unchanged (Stefan). The
remaining copy-elimination question is whether it saves measurable energy:
next step is Stefan's choice of a matched OFF/ON comparison before any
default change. Default false. TECHNICAL “dev45 handoff ON device run”.

**November 3, dev45 BUILT (approved):** color handoff accepts occlusion-query
draws under the same viewport-extent bound. IPA
`ios/build/NFSMW-0.6.0-dev45-handoff-queries.ipa`. Next: Stefan's run with
dev43 Extra Args; watch sun glare, compare main planned share.

**November 3, dev44 blocker census:** the main-target handoff is blocked in
the 0-planned stretches by an occlusion-query draw (ps 2d8bf2c6, likely sun
glare); mirror rejections are on another target. Proposal awaiting approval:
allow query draws under the same viewport-extent bound. TECHNICAL
“dev44 blocker census result”.

**November 3, dev44 blocker census BUILT (approved):** logs which draw guard and
shader keys block the main-target handoff; behavior unchanged, default false.
IPA `ios/build/NFSMW-0.6.0-dev44-handoff-blockers.ipa`. Next: Stefan's run with
dev43 Extra Args, then decide whether the blocking draw can be bounded safely.

**November 3, dev43 handoff ON device run: visuals unchanged (Stefan), partial coverage:**
2347 main copies not encoded (14.396 MiB logical each), 0 pool misses,
0 mismatches, 0 late passes, at most 3 images. While driving the main target
was planned in ~38% of frames; the rest were rejected by an unsupported draw
(`draws` guard, reason not split). Log archived under Debug/3 November 2026.
No energy/GPU-time claim; default false. Next: propose per-guard `draws`
census (with first rejecting shader) before any power comparison. TECHNICAL
“dev43 color handoff ON”.

**November 2, dev43 color handoff BUILT (default off); one enabled device run pending:**
Stefan approved the isolated trial only. `nfsmw_native_color_handoff=false`
(restart-only) plans the main scene target's physical width to its normal tiled
resolve's sampled size under strict draw/viewport/resolve/layout guards, hands
the finished image to that resolve and leases a pooled replacement (at most
min(4, 128MiB/image) per kind; normal copy on miss). Shared `resolve_layout`
helper used by resolve and planner; pool-owned target colors retired, never
residency-Removed in use; standalone same-size colors adopted once. New host
harness `tools/native/test_color_handoff.py` PASS (actual GpuPool, ARC/ASan);
its first failure exposed and fixed per-frame remaking at the pool cap. Build
exit0; only the app executable differs from dev42, all104 metallibs identical.
IPA `ios/build/NFSMW-0.6.0-dev43-color-handoff.ipa` (SHA256 9a4d2dc6…44a4).
Next: Stefan's one enabled correctness run with culling ON (Extra Args in
TECHNICAL “dev43 color handoff implementation”); log census decides whether the
plan is reached and copies are removed. No energy claim; default stays false.

**November 2, color-copy elimination DESIGN complete; implementation awaits approval:**
Prefer main-scene color image handoff before finished-frame copy: main's normal
resolve already has one-size private/tiled layout. Proposed
`nfsmw_native_color_handoff=false` restart-only trial plans eligible scene source
physical width to that exact normal destination shape, then donates completed
color image and leases replacement for next clear. Preserve viewport/pixel grid,
shaders, depth copies, intermediate distortion copy and presenter. Strict full
consumer/layout/viewport/read/last-write/MSAA/query/MRT/diagnostic guards;
normal copy fallback, bounded leases. Source/kept/retired ownership and resize
cleanup must change together; existing raw target residency Remove is insufficient
for pool-owned colors. Same guest address09689000 is overwritten later by POST,
so old main image must survive GPU completion even after kept entry replaced.

Old dev31 never eligible due padded shapes; new plan resolves that mismatch.
Candidate main copy trace span~0.351/0.354ms, only~0.157ms without overlap;
no large FPS gain promised. One native image14.396MiB explicit copy payload,
not previous TWO-copy28.792MiB estimate or physical bandwidth/energy. Final
copy~0.20ms needs additional future-consumer/crop handling, deferred. Existing
trace reused; abstract30000frame ownership model and10503rounding cases passed,
not production/GPU tests. No renderer changes/new IPA or device request yet.
Next: approval of concrete handoff proposal, then production host checks/build
and one enabled correctness run with cullingON baseline preserved. Culling default
staysFALSE; no promotion or dependency changes bundled. TECHNICAL “color-copy
elimination design” has exact plan, bounds, pool constraints and model limits.
HANDOFF_CHATGPT.md preserved untracked; documentation-only local commit/no push.


**November 2, dev42 enabled device correctness PASSED:** Stefan says absolutely
all visuals looked as before. Archived log
`Debug/Most Wanted (2005) Debug/2 November 2026/dev42_iphone_guest_culling_on_nfsmw.log`
under ~/Developer (SHA04f016defb94864541b3069b89ac7f6a77b21e9c5fa639401e5615ea7da2516e).
14complete driving windows/4200frames: back-face culling applied to45.514%main
indexed draws,54.276%cube,48.463%reflection; shadow requests NONE, unaffected.
All eligible draws selected; front/both requests0, so no hardware validation of
those modes inferred. Counters are NOT saved fragment or time percentages.
Reported59.8–60fps,0>45ms GPU frames in summaries,3/4200complete driving pacing
frames off-grid; thermal nominal. Pre-driving watchdog/semaphore diagnostics
remain in log, analogous to prior baseline, not a clean-error-free claim.

GPU/battery/thermal improvement still UNMEASURED; route/load differences prevent
attributing timing versus older logs. No more correctness run requested.
Keep trial available, default FALSE unchanged; visual report does not authorize
promotion or other source changes. Next read-only priority: versioned cropped
render-output/copy-elimination design from structural audit, then concrete
proposal. D-018 remains open/default-off, validated on this iPhone path; D-017
parked. TECHNICAL “dev42 culling ON” has exact controls/counts/timings/limits.
No new build/source change. Local docs commit; HANDOFF_CHATGPT.md preserved.


**November 2, approved guest-culling trial BUILT as dev42; device result pending:**
Stefan approved implementing isolated default-OFF culling. Added
`nfsmw_native_guest_culling=false` (restart-only), captures original primitive
and PA_SU_SC_MODE_CNTL in Draw even on index-cache hits. Supported triangle
lists/fans/strips/quads use guest front/back/face bits; both faces suppress only
the draw, retaining clears/resolves. Two-sided draws retain legacy state.
Queries, internal shaders, rectangles/lines/points, special mirror viewport and
nonstandard/nonfinite viewport conventions fall back. New per-target census
reports guest modes, eligible/applied indexed draws/indices, both-face skips and
fallback reasons; counts are NOT saved fragments or energy. No shader changes.

Host sanitizer tests PASS: guest-culling16384primitive/register cases,
100000window-transform/orientation checks and extracted real renderer state/
counter/skip integration including recycled encoder address; existing draw-arena
regression3500draws/mode/lifetime/ownership also PASS. iOS IPA build exit0,
20.17s real(-j12), strict/deep signing and ZIP member read/CRC checks passed.
All104metallibs identical to dev41. Runtime rebuilt during CMake header-glob
reconfiguration: all file-backed sections identical except __cstring build ID;
__text identical. No SDK source edited.

IPA `ios/build/NFSMW-0.6.0-dev42-guest-culling.ipa`, identical Desktop copy,
30552446bytes, SHA256
`eb78474c3c71fed82536f17661c1c467d98a1d0a85783f70321e2ae4892d695e`.
App UUID9E55444D-3348-3C70-B1C8-F1D0BB03E0BE; runtime
D28C7A83-094A-34B4-B2A4-8DC7D09C3EA0;0.6.0(11),arm64/iOS18min.
Next: one cold-launch enabled correctness run, same native/60 baseline,
normal menus then~60s driving; no Instruments/cache clear/new baseline request.
Use `--nfsmw_native_guest_culling=true --nfsmw_native_dump_manual=false
--nfsmw_native_foliage_early_alpha=false --nfsmw_native_pass_counters=false
--nfsmw_native_gpu_timeline=false --nfsmw_native_early_commit=false`.
Send nfsmw.log and observations of cars/foliage/shadows/reflections/missing faces.
Real cull-side mapping and benefit still require device evidence; keep default
OFF, D-018 open. Broader copy/dependency implementation remains unapproved.
TECHNICAL “dev42 guest-culling implementation” has full evidence/build/limits.
No push/release; pre-existing HANDOFF_CHATGPT.md preserved untracked.


**November 2, larger structural audit complete; proposed first step awaits approval:**
Native renderer drops guest face-cull/front-winding bits entirely (D-018).
Initial code explicitly CullNone; Oct12 removal was redundant-call cleanup,
not a failed guest-culling trial. Propose isolated opt-in/default-OFF
`nfsmw_native_guest_culling` plus exact eligibility/state summaries and host
winding/primitive/reset checks. Respect guest two-sided draws, original primitive
classification (expanded rectangles must not inherit triangle culling), viewport
orientation, queries/clear/resolve behavior. Existing logs omit actual cull bits;
no affected draw count or GPU/battery saving proven. One enabled correctness run
if approved; no shader rewrite/cache clear required by proposed dynamic state.

Broader ownership project: main resolve10/final20 read completed generations
in snapshot; copy payload together28.792MiB/frame(native screenshot), not physical
traffic or measured savings. Need versioned lifetimes AND cropped consumer sizes;
old dev31 swap never eligible due shape, not absence of its restore logic.
Post resolve19 really needed by displaced-coordinate distortion; cannot simply
alias to writable target/framebuffer-fetch it. Presenter remains needed.

Independent port-wide lead: all texture resources declared VS|PS, despite all
42packaged VS texture masks zero. Existing419frames/arm show1.094/1.103ms
vertex-only active time vs1.121/1.130ms total vertex; unnecessary dependency is
plausible, causation/recoverable time/energy NOT established. Exact pass/stage
resource declarations require residency/alias/fallback safety, separate trial.
Main snapshot has no camera Z-prepass; depth-only draws are light-space shadows.
Generic sorting/prepass not selected: blend ordering and hardware HSR constraints.
No game/source/default/build changes. Research authorized, implementation NOT.
See TECHNICAL “structural GPU audit” for code references, primary Apple sources,
analysis scripts, measured bounds, negative findings and proposal. D-017 parked,
overlay and zero-alpha microtrial deferred. HANDOFF_CHATGPT.md preserved untracked.


**November 2, priority correction after Stefan challenges small trial:** zero-alpha
PS27 trial is deprioritized/unapproved; do not build it or request a device run.
It still pays texture fetch and almost all shading; no evidence of material
energy benefit. Being inside the largest pass does not make a change large.
Next is read-only structural investigation: (1) visibility/opaque ordering and
existing depth generations in dominant scene, without a blind extra prepass or
reordering blended edges; (2) retained/versioned color resolve and final-output
consumer lifetimes, without repeating failed whole-target swap. Existing data
bounds copy opportunities as secondary; neither track has a proven saving yet.
No new capture requested, no code changes authorized, no large speedup promised.
Details: TECHNICAL “scope correction: meaningful optimization headroom”.


**November 2, native snapshot analyzed; no source change approved:** dev41
frame1923 contains2583draws/9targets, main1048draws with348tree and330fence/plant
draws. Those are draw counts, not GPU cost shares. Matched tree groups are
complementary opaque and blended-edge passes, not removable duplicates. Current
rain0.798 rules out dry-rain specialization. Watched PNG alpha is deliberately
forced opaque, so no transparent-fragment census is available.
Correction: adjacent renderer comment DOES explain full-target scissors as
untiled reconstruction; previous audit missed it. No established scissor bug.
Next proposal awaiting approval: narrow default-OFF tree PS27 exact-zero-alpha
rejection for finite-output blended/no-depth-write states, preserving positive
soft edges and all side effects. Benefit unproven; may be optimized by hardware
already. One correctness run if approved, existing baseline; power/thermal claims
require actual measurements after useful GPU reduction. No new test needed now.
See TECHNICAL “dev41 native snapshot” for paths, hash, controls, safety gates and
failed alpha-histogram attempt. Remove dump_manual after snapshot capture.
D-017 parked, overlay deferred, all dev41 defaults unchanged. Local docs only;
preserved untracked HANDOFF_CHATGPT.md. Earlier request below is now completed.


**November 2, energy-first broad-device scene audit (read-only):** Stefan
prioritizes thermal/battery benefit across resolutions/devices over more base
fps. Recovered8additional shader sources from local ISO into ignored
`ios/build/perf-gpu-nov2/main-scene-audit/`, applying only existing baseline
rewrites. No live shaders/build/code/default changes. Shader-body counts narrow
older rough fetch estimates; no new safe large shader rewrite proven. Dry-rain
specialization is not substantiated: old af393d c2/RainIntensity samples all
nonzero(0.8 or0.0482), so no claim those2rain samples are generally removable.

Broad lead: native renderer records guest window scissors but hardcodes full
render-target scissor (`if(true)` since Oct11). Dormant else path unscaled,
no window-offset/screen-scissor handling and forces minimum1pixel, so enabling
it directly is wrong. Potential excess scene raster work is UNQUANTIFIED;
no change approved. Current iPhone already single-strip, so do not promise
3xwork reduction. Sky-last, occlusion and compression eligibility already on;
individual false defaults can be overridden by battery group, check logs.

Current trace labels alone don't map Render18 to current shader/material mix.
Next smallest missing input: SAME dev41, add
`--nfsmw_native_dump_manual=true --nfsmw_native_foliage_early_alpha=false`,
keep other settings/diagnostic overrides unchanged, cold launch, tap SNAP once
while actually driving in a representative scene. No Instruments/new IPA.
Snapshot may pause while saving. Send nfsmw.log plus game's Documents/native
folder; this is material/target inventory, NOT performance/energy comparison.
Remove dump_manual afterward; that launch mode disables texture-slot pruning
even on ordinary frames.
Existing dump doesn't log full effective scissor state, so it will NOT by
itself quantify clipping savings; further bounded census only if justified and
approved. Snapshot path disables some optimization paths for diagnostics;
compare target/shader identities, not its timing/order directly to normal frames.

Next after inventory: rank main-scene work against source, verify exact image/
depth/blend constraints, then propose specific change. No new baseline/power
run requested until meaningful candidate exists. Energy acceptance needs actual
matched frame-cap/brightness/thermal conditions, beyond static work counts.
D-017 parked, overlay deferred, alpha default OFF. TECHNICAL “energy-first scene
audit” has commands/artifacts/negative findings. Local docs commit only;
HANDOFF_CHATGPT.md remains pre-existing untracked, no push/release.


**November 2, Stefan redirects priority: largest costs FIRST.** Overlay proposal
is deferred/unapproved. Next target is dominant RenderCommand18 fragment work,
~6.3ms/frame (~57%reported active GPU), main scene inferred; establish actual
shader/material/draw-state attribution before any code proposal. Existing A/B
proves no early-alpha gain, not that every scene shader is already optimal.
Use current trace, recovered sources and historical cost/state logs first.
Do not start a smaller CPU/overlay change while this larger target is unresolved.

Read-only follow-up: sky-last/stencil rejection already implemented; no new
“draw sky last” proposal. Historical Oct21 cost-state log includes colour-mask0
and colour-writing passes with distinct depth/blend/alpha states; don't blindly
add a generic depth prepass or reorder blended draws. Historical omission
probe includes geometry/raster/overdraw, not isolated shader time. Need map the
current dominant encoder and determine which repeated shading/texture/coverage
work can be safely removed; no specific rewrite proven or new capture requested
yet. D-017 remains parked. No source/flag/build/cache changes. TECHNICAL “largest
cost first” records priority and initial code/evidence check. Local docs commit,
HANDOFF_CHATGPT.md remains pre-existing untracked; no push/release.


**November 2, next optimization recommendation (NOT implemented/approved):**
conservative sparse coverage for native touch-overlay drawing. Source audit:
touch_controls.mm draws a premultiplied BGRA image and updates dirty regions;
native renderer copies/uploads only dirty pixels, but draws the overlay using
a FULL drawable viewport/scissor every frame (native_renderer.mm7298ff).
OverlayPipeline4309ff samples with linear/clamp and premultiplied One / OneMinus
SourceAlpha blending. Fully zero BGRA regions therefore contribute identity;
current path still rasterizes/samples them. Existing dirty-upload rectangle
is NOT the complete visible overlay footprint and must not be used alone to
clip drawing. No existing culling experiment found in targeted docs search.

Proposed opt-in/default-OFF trial, pending Stefan approval: cache conservative
occupied regions, update coverage only for changed image tiles, include linear
filter footprint and conservative source-to-drawable rounding; retain full
viewport/UVs/shader/blending. Draw bounded, disjoint scissor regions, merge
filter halos to avoid double blending; fallback to existing full-screen draw
for dense/complex coverage. No full-image scan per render frame. All-channel
zero test avoids assumptions about alpha0/nonzero RGB. Host pixel-coverage,
dirty-update/resize/clear/disjointness tests, counters for covered pixel area,
extra draws/coverage-update CPU work, then one enabled correctness run if
approved. No game metallib changes/recaching required by proposed approach.

Benefit not measured. Entire likely presentation encoder Render39 median~0.65ms,
not overlay-alone time; only a fraction recoverable, extra CPU/draw overhead
could offset benefit. Native-resolution fill reduction is structural hypothesis,
not a promised fps/power gain. Main fragment work~6.3ms remains largest broader
GPU target, but no safe scene rewrite established; prior foliage/half/resolve
negatives remain applicable. CPU attribute/index caches already optimized,
no repeated old optimization proposed. Next wait approval before source work;
D-017 parked, no new device test/build in this recommendation turn.


**November 2, usable dev41 OFF/ON Metal A/B analyzed:** trace
`Debug/2 November 2026/dev41_iphone_early_foliage_ab.trace` has two~15.5s runs,
Shader Timeline DISABLED, same iPhone17PM/iOS27.2/Instruments27.2, nominal
thermals. Log archived as dev41_iphone_foliage_early_ab_metal_nfsmw.log;
OFF/ON flags verified, no pipeline misses. GPU rows51,685/55,618, submissions
903/907, CPU samples14,221/16,777. User only disabled Shader Timeline and kept
capture short; lengths nearly match failed15.57s capture, so duration alone did
not determine success. Long captures still unverified; no known universal fix.

Aligned fully-contained frames3–10s after driving:419per arm. Reported active
GPU mean11.058ms OFF/11.169ms ON; envelope11.073/11.182ms, no demonstrated
shader benefit.3–12s sensitivity gives active10.892/10.954ms; route/scene and
GPU-state changes prevent causal tiny-delta claims. Dominant fragment encoder
RenderCommand18 averages6.293/6.364ms (~57%active GPU, main scene inferred);
next fragment encoders~0.80/~0.67ms. CPU Record self~7%sample weight, attribute
lookup already ON; no code change ready/approved. Early-alpha stays FALSE,
compact/resource TRUE. No further device capture requested now.

Interesting D-017 evidence recorded without reopening experiments: ON log
frame2481 corresponds to trace frame662,111.716ms envelope,39.235ms active and
72.481ms trace-reported Idle,13gaps4.33–6.17ms;9fragment slices inside SAME
already-encoded dominant encoder. CPU encoding finished before GPU began.
Overlapping performance-state records say Minimum; not MHz/physical power-off
or a diagnosed scheduling/residency/power cause. All5ON>45ms hitches INSIDE
recording; OFF0inside, but many OFFafter stop, so do not blame early-alpha or
claim Instruments always prevents hitches. Background GPU-permission errors
start AFTER each trace, excluded from timing comparison.

Next: read-only investigation of dominant fragment work and sampled Record
lookup/fingerprint/decode hotspots against prior evidence, then concrete proposal
before source changes. Keep D-017 parked aside from preserving this distinctive
trace observation. TECHNICAL “usable dev41 A/B Metal trace” has identities,
windows, methods, limits and source checks. Documentation-only local commit,
no build/cache/source changes or push; HANDOFF_CHATGPT.md remains untracked.


**November 2, supplied OFF Metal trace not usable for timing A/B:** exported
15.571979s trace18:34:23.393–38.965 (iPhone17ProMax/iOS27.2(24B119),
Instruments27.2(27B52), MacOS27.2(26B123), attached LiveContainer1567).
Shader Timeline ENABLED, Performance Limiters, Default induced state, Deferred.
GPU/pass/shader/submission/encoder/CPU-sample tables all0rows; Instruments UI
also No Data.7,128,712raw counter rows survive but only timestamps0.318–4.627s;
17,109signposts continue through16.152s. This is partial collection, not simply
slow UI processing or proof laptop hardware is at fault. User clarifies successful
7s capture was MAIN MENU; race capture adds Shader Timeline. Earlier length-only
hypothesis unsupported. Successful menu trace discarded, unavailable for comparison.
No diagnosed root cause or known verified fix. Do NOT request ON capture yet.

Next proposed diagnostic: same dev41/OFF,7s in race, Shader Timeline DISABLED,
other recording/game settings unchanged; inspect whether normal execution
streams return before asking for ON. No cache clearing, code or OS change.
If usable, perform ON under that identical recording configuration. Current
trace and pasted log archived/inspected; no new game build/test this turn.
TECHNICAL “dev41 OFF trace validation” has exact paths/export evidence/limits.
D-017 parked; early-alpha default FALSE, resource/compact TRUE. Local-only.


**November 2, trace-length correction:** Stefan reports7s Metal System Trace
worked, but the2minute capture was completely empty. Long capture capability
is NOT established; earlier proposed2lap/2–3minute recording is superseded.
No new file supplied to verify failure mechanism; do not infer a duration limit,
resource exhaustion or app failure. Next proposed A/B: warm driving about1minute
WITHOUT recording, then capture ONLY7s at comparable track section/camera in
OFF and ON arms, same dev41/settings. Supply raw.trace+matching log per arm.
This is representative-frame/queue/pass inspection, not sustained timing,
thermal or energy acceptance. No repeated long capture requested. Existing
same-build/flags/temperature controls remain. D-017 parked, no code changes.


**November 2, Metal System Trace now works (Stefan):** he volunteers an A/B
and broader performance traces. This supersedes the earlier inability to record
Metal System Trace and the immediately preceding “no device request” status.
No new build/source change needed. Proposed next: iPhone17ProMax, SAME dev41
IPA, native/60 Balanced, same race2laps per arm; A early-alpha FALSE then B TRUE,
cold restart between flags. Keep pass counters/timeline/early commit FALSE,
compact/resource defaults TRUE, other graphics/settings/brightness/charging
state same and comparable initial temperature. Record both laps with Instruments
already recording before race start in BOTH arms; first lap provides warmup,
compare later steady common driving windows, exclude transitions/compilation.
Stefan supplies raw.trace plus corresponding nfsmw.log for each arm. No cache
clearing, no extra OFF/ON/OFF repetitions initially. Analyze GPU work, queue/
submission/copy timing available in trace, count eligibility and failures,
check whether observed change is meaningful vs scene variation. Instruments
can change GPU behavior (prior evidence); this comparison measures instrumented
performance and cannot establish ordinary-run stutter cure or battery savings.
Additional GPU passes/CPU stalls may supply next proposal, not authorization
to change code. D-017 remains parked; early-alpha default FALSE. See TECHNICAL
“Metal System Trace available; volunteered dev41 A/B protocol”.


**November 2, dev41 two-lap device result:** Stefan reports initial heavy
stuttering including menu, then confirms visuals normal and stuttering settled.
Log archived as `Debug/2 November 2026/dev41_iphone_early_foliage_alpha_2laps_nfsmw.log`
under the existing Debug root. Trial ON verified;410,083 eligible/selected draws
across all summaries. Startup has22 archive misses, ALL changed shader684f;
219 old keys warmed in855ms. Pipeline batches total231/209hits/22misses,
755.8ms; dev40 initial228/228hits/37.4ms. Recaching is supported as a contributor
to startup disturbance, not proven sole cause. Three GPU >45ms race hitches
(54.4/51.7/101.1ms) happen6.7–27.9s after driving, after final logged miss;
do not attribute all stutter to recaching or call D-017 fixed. Final14 complete
pacing windows4200frames have0off-grid; GPU averages15.15–15.51ms, comparable
to later dev40 medians, not proof of optimization benefit. No native GPU or
pipeline failures; nominal thermal samples. No fresh baseline/device repeat
requested. Correctness passes on tested path; time/energy/thermal benefit
UNPROVEN, early-alpha default stays FALSE, compact/resource defaults TRUE.

Next: continue read-only GPU cost investigation against existing evidence;
propose before further code/default changes. No pending device request.
Pipeline-save shared-mutex blocking remains a possible startup contributor,
recorded against existing archive backlog, not a diagnosed cause or a request
to reopen D-017. TECHNICAL “dev41 two-lap result” records times, counters,
limits and negative results. Latest IPA unchanged dev41 identity below;
no code, shader, cache, build or device test performed by this analysis turn.
Local documentation commit only; HANDOFF_CHATGPT.md remains untracked.


**November 2, dev41 READY; device test pending:** Stefan approved both the
resource-list default promotion and the separate early foliage-alpha trial.
`nfsmw_native_resource_list_cache` now defaults true, false fallback retained;
compact shared constants remain true. New restart-only
`nfsmw_native_foliage_early_alpha` defaults FALSE. When enabled it selects
specialization bit13 only for shader684f4711f29b9f77 with effective alpha test
(including single-sample alpha-to-coverage emulation); all compare/NaN rules,
late-path math, surviving outputs and depth state preserved. No early return
or forced early depth updates. Rebuilt only that shader library with exact
math/iOS18.0. Counts report eligible/selected submitted indexed draws, not
fragments or GPU time saved. Production-body digest guard fails closed on
translation changes; re-audit before changing it. Host checks pass: 3,264,000
predicate cases, 4608 selection cases, exact false-path reconstruction,
resource-list ARC/ASan/UBSan. Build/signature/ZIP checks pass; other103 shader
libraries and all bundled frameworks unchanged. No device/GPU/energy success
claimed yet. D-017 stays parked.

IPA `ios/build/NFSMW-0.6.0-dev41-foliage-early-alpha.ipa`, identical Desktop
copy; SHA256 `59ba4c08522362532e7800d6328245c5b52984f11227847fe460081a11971329`,
arm64 UUID `925E490E-2487-3D5E-806D-E1E7EAC37EC6`, 0.6.0(11).
Next: ONE enabled correctness run by Stefan at the existing native/60 Balanced
settings, no Instruments, ~60s driving past foliage/fences, check edges,
shadows and motion. Cold-launch LiveContainer with:
`--nfsmw_native_foliage_early_alpha=true --nfsmw_native_pass_counters=false --nfsmw_native_gpu_timeline=false --nfsmw_native_early_commit=false`.
Remove any old `resource_list_cache=false`; explicit true is optional now.
Use existing dev40 baseline, no fresh OFF run requested. Send log and visual
result. Do not promote foliage trial or infer savings before evidence.
TECHNICAL “dev41 resource-list default and opt-in early foliage alpha” records
implementation, toolchain installation, build identities/commands and limits.
Local-only, no push/release. HANDOFF_CHATGPT.md remains pre-existing untracked.


**November 2, dev40 work reduction + device correctness CONFIRMED:** Stefan
explicitly says everything normal. Archived
`Debug/2 November 2026/dev40_iphone_incremental_resource_list_nfsmw.log` (root
~/Developer/Debug/Most Wanted (2005) Debug/), ~70 s driving, native/60 Balanced,
cache/compact ON, other diagnostics/early commit OFF. Zero GPU hitches/errors,
13 full windows perfectly on-grid. Over 3900 frames: 3900 builds +70,200 updates,
zero unchanged hits; 1,317,444 source entries vs23,226,564 full entries declared
(94.33% fewer source copies). Including shifts/reserve moves gives 87.05% fewer
counted pointer operations, NOT total CPU time/energy savings. Cache source
default still false awaiting promotion; compact true. No more cache baseline
needed; GPU work next. Latest IPA dev40, no new build in this analysis.

Read-only GPU lead now concrete: recovered two baseline shader sources from
original ISO `~/Downloads/Need for Speed - Most Wanted (USA).iso` into ignored
`ios/build/perf-gpu-nov2`. For shadowed cutout shader 684f4711f29b9f77 final
alpha is known after first diffuse fetch, before shadow filter/lighting now
preceding its source-level alpha test. Cheap tree 27d82ea0 not a major target.
Next proposal awaiting approval: incremental cache default ON, and independent
opt-in early alpha rejection for 684f only, preserving compare/NaN/derivative/
depth semantics and image quality; exact math, one target library changed,
eligibility counters, host equivalence then one enabled correctness run.
Source eligibility is not a GPU-speed claim (compiler/helpers may limit gain).
TECHNICAL “dev40 incremental list work reduced” has evidence, source recovery
commands/paths, primary Metal semantics and proposal. D-017 parked; no app/
shader/default modifications during research. Local-only/no-push; untracked
HANDOFF_CHATGPT.md preserved.


**November 2, dev40 incremental resource list READY, device test pending:**
Stefan approved correction after dev39 zero hits. Same independent switch
`nfsmw_native_resource_list_cache`, still default false; ON now builds once
and inserts newly appended entries at exact collection boundaries, preserving
all objects/order/duplicates and per-encoder declarations. Shrink rebuild
fallback, per-frame reset, geometric reserve. New counters separate full builds,
updates, unchanged hits, source copies, suffix shifts, reserve relocations and
full entries declared. Compact upload default true unchanged. Host actual-code
ARC/ASan/UBSan tests cover every-pass growth and shrink/order/lifetime; pass.
Incremental -j 12 build 16.53 s, ZIP/signature valid, all shaders/runtime libs
identical to dev39. Latest IPA
`ios/build/NFSMW-0.6.0-dev40-resource-list-incremental.ipa`, also Desktop;
old dev39 archived, 0.5.2 release preserved. Identity/limits in TECHNICAL
“dev40 incremental resource-list correction”. No actual savings claimed yet.

Next (Stefan): ONE new enabled ~45–60 s native/60 Balanced same-race run,
existing dev39/dev38 baseline; no Instruments. Cold LiveContainer, Extra Args
`--nfsmw_native_resource_list_cache=true`, `--nfsmw_native_gpu_timeline=false`,
`--nfsmw_native_pass_counters=false`, `--nfsmw_native_early_commit=false`.
Compact default ON. Full log + any issues; inspect source copies plus shifts/
relocations, not just unchanged hits (can still be zero). No extra OFF run.
Cache default false until evidence; no further source step yet. D-017 parked,
CPU/GPU efficiency active; local-only/no-push, untracked HANDOFF_CHATGPT.md
preserved.


**November 2, dev39 device correctness good, resource-list trial INEFFECTIVE:**
Stefan reports all good; ~72 s driving, zero driving GPU hitches/errors. Log
confirms compact 384 ON/cache ON, native/60 Balanced, other diagnostics/early
commit OFF. However thirteen full 300-frame windows show 74,100 builds and
ZERO reuses: resolve/view arrays grow between every pass. Do NOT promote the
count-unchanged cache or claim CPU/power savings; source default stays false.
Compact shared default true retains separately validated upload/capacity wins.
Archive `Debug/2 November 2026/dev39_iphone_resource_list_cache_nfsmw.log`
(root ~/Developer/Debug/Most Wanted (2005) Debug/). No repeat of this exact
cache experiment needed. Disable/remove its Extra Arg for ordinary play.

Next proposal awaiting code approval: incremental ordered insertion of newly
appended resources into frame-local list, keeping fixed/seen entries, exact
group order, all Metal declarations and lifetime unchanged. Full-rebuild
fallback on shrink, per-frame reset; host interleaved-growth/order tests and
new work counters before ONE enabled device correctness/log run, no new
baseline. See TECHNICAL “dev39 correct on device but zero driving list-cache
reuse”. No new source/default/build this results turn; latest IPA dev39.
D-017 remains parked; CPU/GPU efficiency active. Local-only/no-push,
pre-existing untracked HANDOFF_CHATGPT.md preserved.


**November 2, dev39 resource-list cache READY; compact uploads default ON:**
Stefan approved. New independent restart-only
`nfsmw_native_resource_list_cache` defaults false: optional frame-local reuse
of flattened resource list when five collection counts unchanged. Same objects,
order, usage/stages and useResources on EVERY encoder; no GPU work removed.
Separate modest CPU-saving candidate, not additional savings from defaulting
compact uploads. Compact validated dev38 path now default true, false fallback
retained. Host production/reference identity/invalidation/ARC checks pass under
ASan/UBSan; incremental -j 12 build 16.50 s, ZIP/signature valid. All 104 shaders
and runtime libraries identical to dev38, only app executable changed. Latest
IPA `ios/build/NFSMW-0.6.0-dev39-resource-list-cache.ipa`, also Desktop; dev38
archived, release 0.5.2 preserved. Identity/limits in TECHNICAL “dev39 frame-local”.

Next (Stefan): ONE enabled correctness/log run vs existing dev38 baseline,
no additional baseline. Cold LiveContainer, native/60 Balanced, no Instruments,
Extra Args `--nfsmw_native_resource_list_cache=true`,
`--nfsmw_native_gpu_timeline=false`, `--nfsmw_native_pass_counters=false`,
`--nfsmw_native_early_commit=false`; compact default ON (remove explicit false).
Normal menus then same race ~45–60 s, full log and any issues. Inspect cache
build/reuse/entries counters and shared layout 384. Actual CPU/power/thermal
benefit unmeasured; new cache default stays false pending result. D-017 parked;
larger GPU work still active. No further source step yet. Local-only/no-push,
pre-existing untracked HANDOFF_CHATGPT.md preserved.


**November 2, dev38 DEVICE-CONFIRMED on tested iPhone path:** Stefan reports
stutter-free performance, no visual bugs; log confirms 384-byte compact ON,
native/60 Balanced, timeline/counters/early commit OFF, ~72 s driving, zero
GPU hitches >45 ms/errors. Archive
`Debug/2 November 2026/dev38_iphone_compact_shared_success_nfsmw.log` (root
~/Developer/Debug/Most Wanted (2005) Debug/). Existing dev37 OFF session reused:
eight complete windows in first 45 s, shared-payload median 0.6825→0.258
MiB/frame (~62% less); upload capacity median 8→4 MiB, used span 2.064→1.674.
Logical allocation/upload evidence, not measured battery/thermal/CPU-speed
improvement. One enabled run complete; do not request another baseline.

Next proposal awaiting source approval: compact default ON with false fallback,
plus independently switchable frame-local resource-list reuse (new switch
initially OFF). Cache only list construction when array counts unchanged;
preserve every encoder's identical useResources objects/order/flags and all
owning arrays/mid-pass view declarations. Host equivalence checks then ONE new
enabled correctness run using dev38 baseline. No new code/default/build this
turn; latest IPA remains dev38. Details in TECHNICAL “dev38 compact shared
uploads device-confirmed”. D-017 stays parked; CPU/GPU efficiency active.
Local-only/no-push; untracked HANDOFF_CHATGPT.md preserved.


**November 2, dev38 compact shared data READY, awaiting ONE device run:**
Stefan approved; new restart-only `nfsmw_native_compact_shared_constants`
default false, true prepares/compares/uploads 384 bytes instead of 1024 per
shared descriptor/flag set. Shader field offsets and 256-byte alignment
unchanged; VS/PS float banks untouched. Existing path retained. Host prefix/
dedup/raw-bit checks (5000 draws) and sizing checks (2011 frames, both compact/
legacy and fused/unfused modes) pass under ASan/UBSan. Incremental -j 12 build
17.07 s, ZIP/signature valid, all 104 shaders and runtime dylibs byte-identical
to dev37; only app executable changed. Latest IPA:
`ios/build/NFSMW-0.6.0-dev38-compact-shared.ipa`, also Desktop; dev37 archived,
0.5.2 release preserved. Identity/evidence in TECHNICAL “dev38 compact shared”.

Next (Stefan, one new enabled run; existing dev37 logs are baseline): cold
LiveContainer launch, native/60 Balanced, no Instruments. Extra Args
`--nfsmw_native_compact_shared_constants=true`,
`--nfsmw_native_gpu_timeline=false`, `--nfsmw_native_pass_counters=false`,
`--nfsmw_native_early_commit=false`. Normal menus then same race ~45–60 s;
export full log, note image/menu/movie issues and smoothness. Verify startup
shared layout 384 and actual copy/capacity statistics. No new baseline/A-B
requested. Logical blob bytes shrink 62.5%; CPU/power/thermal savings not yet
measured. Default stays false pending result; no next source change yet.
D-017 remains parked; CPU/GPU efficiency active. Local-only/no-push; preserved
pre-existing untracked HANDOFF_CHATGPT.md remains excluded from commits.


**November 2, D-017 PARKED by Stefan; CPU/GPU cost reduction is active:** Latest
same-dev37 timeline OFF/ON runs both smooth per user, zero logged GPU hitches
>45 ms over ~49/~48 s driving coverage. No clear timeline effect; mechanism
unresolved, not fixed. Archive `Debug/2 November 2026/dev37_iphone_timeline_off_on_smooth_nfsmw.log`
(root ~/Developer/Debug/Most Wanted (2005) Debug/). No more D-017 experiments
unless exceptional new evidence emerges. Latest IPA remains dev37, no new
build/source change in this analysis.

New read-only optimization finding: shared per-draw descriptor/flag payload
uses a 1024-byte block but current NFS shader ABI fits first 384 bytes. Next
proposal awaiting code approval: independent default-off compact-payload
switch, preserving offsets/alignment and 1024-byte fallback; update sizing,
zero/compare/copy/upload together, prove prefix/layout equivalence then device
correctness. Logical shared upload bytes could fall 62.5%; CPU/energy/GPU gains
unmeasured. Do not shrink VS/PS float banks. Then resource-list CPU caching and
larger GPU shader/copy work, each separately reviewed/tested. Foliage early
alpha rejection is a hypothesis requiring actual shader-source analysis;
restored shader cache has libraries only, historical source paths absent.
Details in TECHNICAL “timeline OFF/ON both smooth; park D-017”. Default visual
fidelity and local-only/no-push rules remain. Ordinary optimization baseline:
timeline OFF, early commit OFF, settings matched; no claimed energy savings.
Pre-existing untracked HANDOFF_CHATGPT.md preserved.


**November 2, dev37 first device run SMOOTH; D-017 not reproduced:** Stefan saw
no stutters. Archived `Debug/2 November 2026/dev37_iphone_gpu_timeline_smooth_nfsmw.log`
(root ~/Developer/Debug/Most Wanted (2005) Debug/). Verified timeline ON,
pass counters OFF, early commit OFF, native/60 Balanced. ~51 s after first
driving label, zero GPU frames logged >45 ms, nine consecutive 300-frame
pacing windows with zero off-grid frames; GPU averages later ~14–15.5 ms.
One initial-load timeline report triggered by 31.1 ms encoding (GPU 9.2 ms,
completion lag 0.084 ms), not D-017. No fault timeline yet; not a fix or power
acceptance. Latest IPA remains dev37; no new code/build this analysis.
Next proposed device comparison: SAME dev37 timeline OFF then ON, keeping
counters/early commit OFF and native/60 Balanced, no Instruments, cold
force-quit between runs, same race ~45 s. Tests whether the diagnostic itself
changes the smooth/stalling state; not another counter A/B. Reverse order
only if a difference appears. If both smooth, record inconclusive rather than
repeat without a new discriminator. See TECHNICAL “dev37 first timeline run
smooth” for evidence/limits. No further source change approved; local only,
pre-existing untracked HANDOFF_CHATGPT.md preserved.


**November 2, dev37 GPU timeline READY, awaiting device test:** Stefan approved
bounded timeline instrumentation. New restart-only
`nfsmw_native_gpu_timeline` default false; enable captures 128-frame history
and up to 12 eight-frame reports around driving delays. Includes submission,
GPU, callback/release and presentation timestamps plus pending residency,
new pool/vertex/upload counts. No GPU commands, QoS, quality, residency or
submission-policy changes. Host ASan/UBSan ordering/concurrency/history tests
pass; incremental -j 12 build 18.91 s, ZIP/signature valid, all 104 metallibs
unchanged. Runtime rebuilt for build-stamp metadata only (__text identical).
Latest IPA `ios/build/NFSMW-0.6.0-dev37-gpu-timeline.ipa`, also on Desktop;
dev36 archived in repo, Desktop old copy to Trash; release 0.5.2 preserved.

Next (Stefan): force-quit LiveContainer; native/60 Balanced, no Instruments,
Extra Args `--nfsmw_native_gpu_timeline=true`,
`--nfsmw_native_pass_counters=false`, `--nfsmw_native_early_commit=false`.
One ~45 s same-race drive from start; export complete log and note stutter.
This is diagnostic, not a fix or battery acceptance. If no hitch/report,
record inconclusive rather than success. Details, log schema, trigger limits,
commands, build identity in TECHNICAL “dev37 bounded GPU timeline”. No source
behavior change beyond optional telemetry; wait for evidence before a fix.
Pre-existing untracked HANDOFF_CHATGPT.md preserved; local only, no push/release.


**November 2, dev36 device comparison COMPLETE; D-017 still open:**
Archived four-session log `Debug/2 November 2026/dev36_iphone_pass_counters_abba_nfsmw.log`
(full root ~/Developer/Debug/Most Wanted (2005) Debug/). Counter OFF/ON/ON/OFF
and early commit OFF verified; native 1.833/60 Balanced. Driving GPU hitches
>45 ms: 4 / 2 / 0 / 2 over ~33–35 s per run; maxima 120.3 / 139.3 / none /
86.7 ms. Disabling counters does not prevent severe stalls, so keep default
true; no further counter A/B needed. User felt two slight stutters / one tiny /
none / heavier start plus dropped frames. Preserve those reports separately:
run 3 also logged two ~50–53 fps windows with GPU averages 19–20 ms despite
no large hitches. Sustained native/60 and battery parity remain unvalidated.
No source change/new build this analysis; latest IPA remains dev36 below.
Next proposal awaiting code approval: bounded CPU-side submission/GPU/callback/
presentation timeline plus pending residency/allocation counts, without
changing rendering/residency/submission policy. See TECHNICAL “dev36
OFF/ON/ON/OFF device results” for archive hash, windows, limits and proposal.
Pre-existing untracked HANDOFF_CHATGPT.md preserved; local commits only.


**November 2, dev36 pass-counter diagnostic READY, awaiting device test:**
Stefan approved the counter-sampling experiment. New restart-only Extra Arg
`--nfsmw_native_pass_counters=false` skips pass/blit timestamp buffers,
attachments, resolution and calibration. Default true preserves prior behavior;
command-buffer GPU timing, hitch counts and presentation-gap reporting remain.
No rendering, quality, residency, QoS or submission changes. Latest IPA:
`ios/build/NFSMW-0.6.0-dev36-pass-counters.ipa`, also on Desktop (0.5.2 release
retained; dev35 Desktop copy moved to Trash, repo archive retained). Incremental
`-j 12` build 17.72 s, exit 0; ZIP/signature valid, all 104 metallibs and all
other packaged files except NFSMW executable byte-identical to dev35.

Next (Stefan): native / 60, Balanced, no Instruments; Extra Args
`--nfsmw_native_early_commit=false` in every launch. Short same-race runs in
order pass counters OFF / ON / ON / OFF, force-quit LiveContainer between
runs. Use explicit `--nfsmw_native_pass_counters=false` or `true`; collect logs
and perceived stutter. Inspect startup `GPU pass profiling disabled ... off`
vs `available ... on`; keep other settings/conditions unchanged. This tests
D-017's instrumentation lead, not battery acceptance. No device result yet;
do not stack another experiment until results. Build identity/limits in
TECHNICAL “dev36 pass-counter switch”. Pre-existing untracked HANDOFF_CHATGPT.md
remains untouched/excluded from commits. Local only, no push or release.


**November 2, independent evidence audit (documentation only):** Performance
remains the active goal per Stefan; do not switch to other 0.6.0 work. No code
change approved or made. Next proposed experiment is a restart-only switch to
disable GPU pass-counter instrumentation while retaining command-buffer timing
and screen-gap logs, with early commit explicitly OFF; implementation awaits
approval. Details/reproduction in TECHNICAL, “independent D-017 evidence audit”.
Corrections to the earlier handoff: dev33 Time Profiler's three GPU hitches
were AFTER recording stopped (zero inside its 40.378 s window); the earlier
Power Profiler native run does contain seven during recording (four driving).
Recording-state association is strong but “always absent” is not established.
Power-state mechanism, complete residency coverage, and instrumentation effects
remain unproven. dev35 iPhone logs retain early commit ON and mix whole-frame
and final-command-buffer profile times. Native/60 battery target is not yet
validated. No new device test/build; latest IPA remains dev35 below.
Pre-existing untracked HANDOFF_CHATGPT.md preserved, excluded from this session's
local documentation commit. No source, SDK, generated code or shaders edited;
no push/release. Stefan runs all device tests and Instruments recordings.


**November 2 (Claude), handoff to Codex: 0.6.0 performance work, branch
`dev-0.5`, local commits only (nothing pushed).** Latest IPA
`ios/build/NFSMW-0.6.0-dev35-lighter-native.ipa` (on Desktop with 0.5.2).
Version is 0.6.0. Read BACKLOG "Performance goal for 0.6.0" (status end of
November 2) and D-017, and the TECHNICAL sections dated November 2 from
"baseline Power Profiler traces" to the end, before doing anything: they
hold every measurement and negative result of the day (do not repeat them).
State: Extra Options, keyboard, mouse look, swipe look and Showcase touch are
done and device-confirmed. Performance: dev35 saves ~1 ms of the native GPU
frame (tiled cropped resolves, small targets at 1x); the iPhone's native
stutter (D-017) is not fixed and its cause is unknown.
Stefan asked (November 2): **investigate everything yourself first, with
fresh eyes; you may have different and new ideas.** Then propose before
changing code. Open choice put to Stefan: (1) foliage overdraw in the main
scene (largest GPU item, helps iPad 120), or (2) move to the other 0.6.0
goals (low-RAM support, D-016 My Cars taps, free camera, Extra Options menu
patches, in-game menu mirroring the launcher); Claude leaned to (2). Also
confirm with Stefan whether `nfsmw_native_small_targets_1x` stays default
(working rule: default look must not change).
Build: `python3 tools/ios/patch_game_extra_options.py`, then
`cmake --build ~/Library/Caches/nfsmw-ios/build-0.6 --target ipa -j 12`
(SDK `~/Developer/GitHub/nfsmw-multiplayer-sdk`). Name IPAs
`NFSMW-0.6.0-devNN-<topic>.ipa`, keep only the newest dev build and the
latest release on the Desktop. Logs go to Debug/<date>/; Stefan records
Instruments traces himself.

## Earlier checkpoint — October 22, 2026

- **November 1: 0.5.2 (build 10) released (Stefan's go).** Stefan validated
  test12 Blacklist scrolling in safehouse and free roam, and declares the whole
  0.5.2 menu touch matrix and "keep music playing" device-validated; future
  issues will be noted separately. New default: `ios_touch_menu_empty_accept`
  false (strict, widget-targeted gestures); launcher default matches. The
  setting did not exist in 0.5.1, so every user gets the new default.
  CHANGELOG 0.5.2 explains the changed way of playing and the switches that
  restore 0.5.1 behaviour. Release checks: SDK 31/31 project patches (same
  ios_timing 11/15 diagnostic state as 0.5.1), pool 63/63, extra options all
  applied, host menu tests pass, `codesign --verify --deep --strict` ok,
  Info.plist com.bep1s.nfsmwios 0.5.2 (10). `NFS-Most-Wanted-0.5.2.ipa`,
  30186591 bytes, SHA-256
  `95acb5e31318fdae2237bad62b015fb0ae95484c494f3624babe2a5a70c74eeb`, also on
  Desktop. Multiplayer stays out of releases until Stefan says otherwise.

- **November 1: test12 Blacklist rival scrolling ready (Stefan's report).**
  On `InGameReputationOverview` / `SafeHouseReputationOverview` the rival
  up/down arrows are the side ARROW texture rotated 90 degrees; the hint walker
  reads only the mirror sign, so they sent Left/Right and moved the event-type
  icons (Race/Milestones/Bounty). Now two same-texture side arrows stacked
  15-60 apart in one column on these screens become Up (top) / Down (bottom);
  row arrows and glow copies unchanged. Swipes had no region: the photo and
  arrow column (-285,-150 to -25,180) is now a VerticalDrag. Geometry from the
  31 October test8 ui-tree and IPA159 IMG_4069; host test pass. Artifact
  `ios/build/NFSMW-0.5.2-test12-blacklist-scroll.ipa`, 30186507 bytes, SHA-256
  `b4f8c89e658cf18c77b42abc2b96b44cfad0541db8d92d822e227bd5842b819d`, copied to
  Desktop. **Next:** device check of arrows/photo swipe in free roam and
  safehouse; then the multiplayer-screen touch pass (Stefan: 0.5.2 is all of
  `main`, incl. live performance profiles and FPS caps). No push.

**Session closed at Stefan's request (November 1):** Stop development/testing
now to conserve usage. Resume with Claude only when Stefan returns. Sourcefix
commit0b6ef8e; localmultiplayer clean at session-close audit; latestIPA hash
rechecked and matches below. No release/push/merge. Local ignored AGENTS.md and
CLAUDE.md entrypoints ensured in this worktree, pointing to this record. They
remain untracked/ignored per project rule; no other session edits left pending.
Main's pre-existing checkpoint edit/HANDOFF remain deliberately preserved.

**November 1 (Claude) — MULTIPLAYER PAUSED at validated preview18 (Stefan):**
Stefan considers multiplayer complete for now and wants to work on other things
before any release. Do not continue multiplayer work unless he asks. Before a
release it still needs: a touch-controls pass (bring main's newer, more
comprehensive menu touch system, built with Codex, into this branch and check the
multiplayer menus), an Android regression check, and optionally the cosmetic PC
guest 7200 s countdown. Branch `multiplayer` is local only, nothing pushed.

**November 1 (Claude) — preview17 automatic LAN, mixed PC/mobile rooms; device test next:**
Stefan approved: one automatic LAN option (in-game Xbox Live sign-in joins a
nearby phone/PC lobby or hosts one), PCs and phones in the same hosted room (up
to three PCs), and per-peer PC race translation on every iOS device. PC↔Android
race relay was cut (Android port cannot be changed). Details, limits and test
commands: newest TECHNICAL section “preview17”. All local tests pass; nothing is
device-tested yet.

LATEST IPA:
`/Users/bep1s/Developer/GitHub/nfsmw-ios/ios/build/NFSMW-multiplayer-preview17-auto-lan.ipa`
30445025 bytes, SHA256
`2f3f106b2d78a020ba064fdadd77b491918e4efa80bf122b4ce35073064a58a5`, app UUID
9AFDA099-5E6E-329B-B516-4ADFAC0A3CC2. Preview16 stays the fallback.

Next device tests (Stefan): every device taps “Play on this Wi-Fi”.
1. PASSED on device: iPad hosted, iPhone joined automatically, race flawless
   (host decision 4.4 s, guest 1.6 s). Simultaneous sign-in also PASSED: the
   one that started its search first hosted and the other joined it.
2. PASSED on device both ways (iPhone joined the PC lobby automatically; iPhone
   hosted, PC joined, race finished with results). Cosmetic: PC guest countdown
   shows 7200 s instead of 60; noted, not worth fixing now (Stefan).
3. PASSED for racing: iPhone host + PC + iPad raced normally. Cosmetic: the
   PC's room list did not show the iPad (stale room count on the PC). Fix
   approved and built as preview18
   (`ios/build/NFSMW-multiplayer-preview18-pc-room-count.ipa`, SHA256
   74852ad6a236faa0fd6610a32048df92b7a973f0f3c899ce35383af219f2fcd3): host
   resends the room record to PCs on join/leave. DEVICE-CONFIRMED: the PC
   lists all three players. Preview18 is the latest validated IPA.
4. NOT RUN: no Android device available; Stefan expects no Android regression.
Collect boot/game/server logs; look for `[lan-auto]` decisions, `PC peers in
host room` on guests and `[pc-udp]` role/ID lines.

The original preview16 validation checklist below still applies to Host for PCs
history but is superseded for new testing by the list above.

**November 1 current handoff — preview16 PC guest name FIXED on device, Claude next:**
Stefan authorized fixing host missing connected-player rows. Preview16 adds
LAN-only USA room-count synchronization from the actual native slot0 member
list before the member-change callback forwards room data to the frontend, and
before the original name lookup. No networking/session/ready flag change.
Code-supported cause: host create record.C stays1 while +usm adds guests; native
82545A88 forwards that record unchanged. Exact callback fixture reproduces
stale count1 with2members and forwards2 after repair. Direct guest indexed-name
lookup already works; don't claim the name parser itself rejects Guest.
Stefan tested preview16 during this session and explicitly reports “it works
now i can see the pc's player name”. PC guest name display FIXED/DEVICE-CONFIRMED
inpreview16 for this pairing. No newlogs/deviceOS supplied for that confirmation.
Do not leave it labeled candidate/unvalidated for PC. iOS/Android guest roster
regressions and guest leave/rejoin/carupdate still need separate device checks.

LATEST IPA:
`/Users/bep1s/Developer/GitHub/nfsmw-ios/ios/build/NFSMW-multiplayer-preview16-host-roster.ipa`
30439031bytes, SHA256
`f15c4ae4dcb8a6da1b70accac921677d14f08fe0aa6eed03a73df2d0d99c18b4`,
appUUID90D3671A-2F4C-34FB-A002-3997B0ED8EB4; runtime unchanged.
Next device tests: iOS/Android guest rows, guest leave/rejoin/car changes and a
short race regression; PC guest name already confirmed visible.
If still hidden, collect boot/game/server logs and inspect [lan-roster] count
repair trace and actual frontend row enumeration/filter, not protocol bytes.
Original gameplay-ready baseline remains preview15; all previous IPAs preserved.
Host for PCs remains separate; no mixed mode or release authorization.

**Confirmed preview15 baseline (unchanged by this experiment):**
Both native PC-host→iOS-join AND iOS-host→native-PC-join now have device-confirmed
racing, without a PC helper/script/mod. Reverse PC hosting is still a separate
opt-in **Host for PCs (Experimental)** / host_pc mode, one phone + one PC.
Continue on local `multiplayer` in `/Users/bep1s/Developer/GitHub/nfsmw-ios-multiplayer`; no
push/merge/release authorized. Controls/main and shared SDK remain separate.

Preview15 result: phone192.168.101.106, PC192.168.101.163/useramog. Listener ID
captured17:22:59.210, first RX/TX8bytes sameinstant,21byte exchange59.343/.349.
Both car factories succeed17:23:18.173/.174 (remote5A784095/localCD88083F).
State6 in-world17:23:22.204, race traffic until17:23:57.663,569RX/582TX3658,
zero guestAV. Stefan reports race started and everything went well. PC name
was missing in that preview15 test, subsequently FIXED/confirmed in preview16
above. PC sees host. Do not reopen fixed discovery/handshake/car loading without
regression evidence. Do not infer crash or intentional quit merely from log end.

Validation limits/next work for Claude:
1. Phone-host→PC-join: finish/results/return-to-room/rematch/endurance still
   UNTESTED. PC-host path already passed long session/finish/return/rematch in
   preview13; preserve that baseline instead of repeating first validation.
2. Preview16 PC guest name now visible per user. Verify same roster repair for
   iOS/Android guests and leave/rejoin; avoid reopening first PC-name validation.
3. Mixed hosting/multiple-PC integration remains deferred, separate PC mode
   retained. Broader vehicles/tracks/mobile regressions before any release.

Preview15 confirmed gameplay IPA (preserved):
`/Users/bep1s/Developer/GitHub/nfsmw-ios/ios/build/NFSMW-multiplayer-preview15-pc-host-listener.ipa`
30438761bytes, SHA256
`c48e3ca707d23da431ec3ba620d438f9da3eb734e29d39fb0393eed8f047c5a1`,
appUUID FEF119BC-0E2C-3C03-AEA3-18DEB9E8CB58; runtime unchanged
DE9DB5F9-8E8C-3A59-A412-0BD728F3161C. Source280a07f. Preserve13/14 too.

**Archive exception RESOLVED:** Stefan reattached earlier3logs with “2” names
and supplied current3logs without “2”. All6 copied/verified in requested
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/1 November 2026/`:
`nfsmw_lan_preview14_reverse_handshake_{boot.txt,game.log,server.log}` and
`nfsmw_lan_preview15_reverse_gameplay_success_{boot.txt,game.log,server.log}`.
Old lost clipboard paths remain historical only; no files pending reattachment.
Exact provenance/sizes/evidence in newest TECHNICAL. Main pre-existing modified
checkpoint/untracked HANDOFF preserved. That evidence-only turn was documentation-only. The current preview16 code/test/build
experiment is recorded above and in newest TECHNICAL; no push/release.

**Previous preview14 checkpoint context (superseded where noted above):**
Stefan is low on Codex usage and requests the shared record be ready for Claude.
Continue in `/Users/bep1s/Developer/GitHub/nfsmw-ios-multiplayer`, local branch `multiplayer`.
Canonical main checkout remains controls-only with its pre-existing modified
checkpoint and untracked HANDOFF preserved. No push/merge/release authorized.
If starting from main, `git worktree list` locates this checkout, or read
`git show multiplayer:docs/DEVELOPMENT_PROGRESS.md` before changing anything.
All source/history is locally committed; do not rely on chat or temporary logs.
Isolated SDK/build recreation commands are above; no shared SDK changes.

**PC hosts: validated on preview13.** Stefan reports good synchronization,
~18min AFK, then PC completed the race while phone stayed AFK; BOTH returned to
room and a second race started without issues. Logs show first in-world
16:36:44.109 → frontend17:02:45.770 (~26min), rematch in-world17:03:07.876;
9676RX/9905TX3658 datagrams across supplied rotated logs, zero guestAV. PC
172.20.10.4 / phone172.20.10.1. Retain preview13 as completed-race/rematch baseline,
preview12 as first gameplay baseline. Broader vehicle/track/mobile coverage and
both-player finish edge cases remain beyond this test; no blanket release claim.

**Phone hosts: preview13 discovery FAILED on Wi-Fi AND hotspot.** Server logs
show announcement sendto returning EHOSTUNREACH / “No route to host” on
192.168.101.106 and172.20.10.1, with NO TCP9900 PC connection. Phone backend and
own room work; do not debug race handshake until discovery/TCP is reached.
Inference: failed iOS/LiveContainer broadcast path, consistent with earlier
mobile discovery history; exact entitlement vs routing cause not proven.

**Preview14 ready:** adds identical PC UDP9999 announcements sent directly to
nearby hosts on the exact selected interface, in addition to broadcast. Respects
hotspot /28, caps broad LANs at local /24, excludes own/network/broadcast/VPN/
cellular, paces sends and logs direct target/success/error counts. No PC helper,
new entitlement or firewall changes. Host for PCs remains opt-in host_pc with
one PC guest; mobile Host and PC Join/race code unchanged. Local injected
EHOSTUNREACH test passes; subsequent preview14 device test confirms PC discovery/login/room join.

Ready IPA:
`/Users/bep1s/Developer/GitHub/nfsmw-ios/ios/build/NFSMW-multiplayer-preview14-pc-direct-discovery.ipa`
30438233bytes; SHA256
`54d7b2b6e4a7c55e5c6f73f7bd958fb875669d429767392f0e7ec7e55502dd6d`.
App UUID `C1080D85-E1FB-3DD9-981B-CAE6B3D44160`, runtime unchanged
`DE9DB5F9-8E8C-3A59-A412-0BD728F3161C`. Previous preview13 IPA preserved:
`ios/build/NFSMW-multiplayer-preview13-pc-host.ipa`,30435895bytes, SHA256
`96b90c94d0d805f7ab885540549dab4a16dad405d18c71682188f2c9d1abe224`.

**Next device action:** preview14, same Wi-Fi first; distinct names, Logging on,
phone launcher Host for PCs → Launch → Xbox Live → Quick Match → Create Game;
PC LAN browser select advertised phone name (first11characters), then join.
No scripts. If still invisible, obtain server.log + boot/game logs and current
PC/phone IPs. Inspect [pc-host] direct counts first. If sends succeed but PC
still sees nothing, next investigate native PC UDP9999 receive/firewall/capture
and unicast acceptance; do not blindly edit room/race serializers. Once PC
connects TCP9900, diagnose auth→room→peerready→race in order. Restart Host before
another PC IP (first peer pinned). Mixed/multiple-PC hosting still unsupported.
Host missing guest names remains OPEN, unrelated to this discovery change.

All five new supplied logs archived under
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/1 November 2026/`
with prefix `nfsmw_lan_preview13_reverse_discovery_and_pc_endurance_`, suffixes
`boot.txt`, `game.2.log`, `game.1.log`, `game.log`, `server.log`. This is the
user-requested dated folder; pre-existing evidence there was preserved.
See newest TECHNICAL entry for exact commands/results and failure evidence.
Older deferred/pending paragraphs below are historical.

- **November1 preview12: first PC-hosted iOS gameplay CONFIRMED; intentional quit.**
  Stefan reports itworked, thenclarifieslogsendedbecausehequit, NOcrash.
  NativePCendpoint192.168.1.133:9900 (newaddress, don'treuse202), hostNAME,
  room012.NAME; phone.205. Bothfactorycreations succeed00:20:51.265–266:
  localCD88083F→BFAD520C, remoteA800B5BB→BFAD9AEC (differentcarrecord).
  State6inworld00:20:55.212, bidirectional3658through00:22:49; logends50.295.
 1705RX/1668TX loggedrace datagrams,0guestAV. Userintentionalquitexplainsend;
  do NOT reopencrash/timeoutbasedonlogending. NativePCgameplayworkswithout
  PChelper; race-loadingcar-IDfix deviceconfirmed for thissession. Preserve
  preview12asfirstknownworkingPCbaseline, source4ae8893/artifactSHA256
 9e174345bfaf9357c3aabcab12f6745cc453182ec8597a11af8dd9bd7f31286d.
  No new source/IPA thisturn; testsnotrerunforrecordonlychange. Readyartifact
  unchanged `ios/build/NFSMW-multiplayer-preview12-pc-car-records.ipa`.
  **Next validation:** finish/results andrematch, widercars/tracks/customization,
  mobile regression beforecleanup/release. No rank/results in suppliedlog;
  userdidnotreportcompletedrace. Do NOT claimallmodes/platformsvalidated.
  ReversePCdiscovery/iOShost stilldeferredpendingPChostvalidation/polish;
  hostmissingmobileguestnames stillopen. No unsolicitednewfeaturework now.
  New2logs archivedDebug/1November:nfsmw_lan_preview12_pc_gameplay_success_*.
  Alllocalmultiplayer, controls/mainpreexistingcheckpoint/HANDOFF/sharedSDK
  untouched, no push/merge/release authorized. OldpendingPCgameplayentries
  below arehistorical andsupersededbythissuccessfuldevicetest.

- **November1 preview12: remote car record byte order identified; targeted fix ready.**
  Two new boot/game uploads are byte-identical (oneattempt00:10). Factory
 1396EBE1registered82A3E350/callback823D3F98 createslocalcarCD88083F with
  resultBFADE00C, failsremote3F0888CD withresult0. Thus missingregistration
  ruledout; nativecarrecord keybyte-reversed. FullRXsetuphas3F0888CD at24,
  TXCD88083F at26 (variablegamertaglength), don'tpatchfixedpacketoffsets.
  Actualserializer824D54B4 reads4rawbytes into participant+4432;824D5704
  emits4nativebytes. Customization408bytes also raw at54FC/574C. Preview12
  hooks these specific bitstream boundaries to reverse4bytecarID andtyped
  customizationnumericfields using existingPCsaveimportmap (u16parts0..115,
  u32physics/tunings/preset118..193; padding/bytehandleunchanged, hexoffsets).
  No savedrecord mutation, forceddummyobject or guessedcompressedpacketparse;
  PCmodeonly; mobilehostpathunchanged. Race/physicsPDUs nottranslated.
  NewactualcarhookASan/UBSan testpasses capturedIDbothdirections, typedfields,
  padding/handle/roundtrip/originalbuffer/off/otherfields andunexpectedlength.
  UDP/factory/gatewayregressionspass; strongoriginal+hook entriesverifiednm.
  Ready `ios/build/NFSMW-multiplayer-preview12-pc-car-records.ipa`,30431970bytes,
  SHA2569e174345bfaf9357c3aabcab12f6745cc453182ec8597a11af8dd9bd7f31286d,
  appUUIDAC77427C-C73A-31CF-A1F2-CBD93A4DE9F6,
  runtimeUUIDDE9DB5F9-8E8C-3A59-A412-0BD728F3161C. Build/ZIP/signaturepass,
  GPUdylib/104shaders identicalpreview11; runtimeonlySDKbuildstampoverlayrebuild.
  **Next:** preview12samePCroom/racewithLoggingon; confirmbothcarcreations
  succeed/load, thenrace. Devicefixacceptancepending; otherappdatadifferences
  mayremain. BOTHboot/game iffails. InputsarchivedDebug/1Nov as
  nfsmw_lan_preview11_pc_car_factory_{a,b}_{boot.txt,nfsmw.log}. NoPCdumpyet.
  Alllocalmultiplayer; controls/mainpreexistingdocsedit/HANDOFF/sharedSDK
  preserved; no push/merge/release. Hostnamesopen/reversediscoverydeferred.

- **November1 preview10 connected; both games reported crash during race load.**
  New game log confirms bidirectional DATA/ack traffic and +ses, state4region
 00:02:03.899, state5track05.431, nullguestread06.504/LR82474944. Caller
 824743C0 dereferences result of classfactory8212BFB8 withoutnullcheck.
  Factory may have no registration OR matchingcallbackreturned0; exactcause
  notknown. PCcrash userreported, noPCdump/callstack supplied. Do NOT conflate
  handshake success with whole race compatibility, or blind-swap application
  payloads/force dummyobjects. GAMEPLAY.BIN warnings alsoin workingmobilelogs.
  Preview11 DIAGNOSTIC only: PC-only exactfactorycallsite traces requestedkey,
  matchingfactory/callback,args,participant/localflag/carrecord,result (8calls);
  complete initial>32byte gamepackets, max32/direction and2048bytes/packet,
  inboot.txt. Originalresults, handshake/packetcontents/payloads unchanged.
  Actualfactory/UDPdiagnostic tests passASan/UBSan; gateway/guestdecoders/room
  pass; build/ZIP/signature pass. Factorystronghook+originalimp verifiednm.
  Ready `ios/build/NFSMW-multiplayer-preview11-pc-race-diagnostics.ipa`,30431786bytes,
  SHA2566e72154e1fdf1c3796f8245d3a2265d52d8f153f9a472ecb328cfb4cff3f0832,
  appUUID89CE2C4E-5A6C-3705-A7FD-0B1D5964012F,
  runtimeUUID4D5257DA-DD90-352A-9B20-DE0228BD98FC. GPUdylib/104shaders identical
  preview10; SDKruntimeonlydebug_overlay rebuiltforCMakeversionstamp, noSDK
  source/networkchanges. NativePCtransportfunctionalityconfirmed, actualrace
  stillfails. **Next:** preview11samePCroom test withLoggingenabled, obtain
  BOTHboot.txt andnfsmw.log forfactory+fullsetupdata; PCcrashdetailsifavailable.
  Thisbuilddoesnotclaimtopreventcrash. Rawnewlog archivedDebug/1November as
  nfsmw_lan_preview10_pc_race_load_crash_game.log. Alllocalmultiplayer;
  controls/mainpreexistingdocsedit/HANDOFF/sharedSDK preserved. No push/release.

- **November1 preview10: header-only device experiment FAILED; PC listener ID learned.**
  Follow-up log23:54 shows10TX0100000000000000 (translatedLE) and10PCreplies
 05000000C5B964C6,10s timeout. Thus headerhook ran; do NOT offerpreview9again
  or callheader-onlyfixdeviceaccepted. Exactinstalledhashnotestablished.
  Originalspeed.exe disassembly identifies CommUDP8505E0 receive/control;
 850A13–3F emits opcode5 with listener's connectionID at+0x98. Listener
  acceptsINIT1 only withmatchingID (850710–725/850C4F–57). Phone requests0,
  PC advertisesC664B9C5; header swap alone doesn't reconcilelogicalidentity.
  Preview10 learns ID ONLYfromselectedPCopcode5, maps outgoinghandshake1–3
  ID toPC and incomingmatchinghandshake1–5 ID backtooriginalclientID.
  Originalconnectedstate stillrequiresactualhandshake; no readyforcing.
  DataACK/sequence andpayloadunchanged. PCtarget/local+remoteIDs clearedon
  Start/Stop; mobile/voice bypass unchanged. TestsactualUDP hooks+gateway ID
  lifecycle/session+room passASan/UBSan; build/ZIP/signature pass.
  Ready `ios/build/NFSMW-multiplayer-preview10-pc-connection-id.ipa`,30421055bytes,
  SHA256697c3d9c5d14a85b8d1974a0d5da928823ec9afc568c5747ee6938e97643b75c,
  appUUID9BCA14F6-5127-3567-995B-9E912E79F7E1; runtime325ECA6F-B026-3D4A-
 A158-0618E2381E30. BothSDKdylibs/104shaders identicalpreview9.
  **Next:** preview10samePCroomJoin/QuickMatch, inspectactualhandshake/race.
  Identifier translation devicepending; noPCraceclaim. Latestlogarchivehas
  historicalmislabelnfsmw_lan_preview8_pc_peer_timeout_followup_game.log;
  preservepath, dataactuallyshowsheadertranslatedpreview9-styleexecution.
  PrivatePCdisassemblyarchived inDebug/31October, no proprietarycodetracked.
  Alllocalmultiplayer, controls/mainpre-existingdocsedit/HANDOFF/sharedSDK
  preserved. Hostnamesopen/reversediscoverydeferred. Nopush/release.

- **October31 preview9: bidirectional PC race UDP confirmed; header experiment ready.**
  Preview8 now opens3658/6000, XnAddr maps PC.202, sends/receives race datagrams.
  Two joins (~23:42:39/23:42:58) timeout ~10s; each repeats8byte requests and
  replies. Overall20TX0000000100000000,20RX05000000C5B964C6. No longer a
  discovery or unattempted socket issue; reachability for3658 evidenced.
  Xbox CommUDP parser uses big-endian header fields; PC wire values suggest
  little-endian headers. Preview9 TEST translates just two32bit transport
  words at original DirtySock synchronous send/dequeued-receive boundary,
  onlyselectedPCIP/port3658/CommUDPcallers/LANenabled. Payload/voice/mobile
  untouched; original sendbuffer preserved via private gueststack copy.
  No SDK source changes or async receiver changes, no ready-state forcing.
  Actual hook tests ASan/UBSan cover captured bytes, payload/retrybuffer/stack/
  return preservation and bypasses; gateway/session/room/preflight all pass.
  Strong hooks verified in executable alongside original __imp__ entries.
  Ready `ios/build/NFSMW-multiplayer-preview9-pc-udp-header.ipa`,30432156bytes,
  SHA2568ab434c333c7fb46b26387c1f3d9dc90855f9b9a8e8ddd856a5560d10f9fdca6,
  appUUID3763C3DA-7834-3C34-ACA2-4040E98DDD51,
  runtimeUUID325ECA6F-B026-3D4A-A158-0618E2381E30. SDK runtime rebuilt only
  debug_overlay.cpp afterCMake/versionstamp regeneration; networking patch
  stillapplied, noSDKsourceedit. GPUdylib/104shaders identicalpreview8.
  **Next:** existingoriginalPCroom + phonepreview9Join/QuickMatch; check actual
  peer handshake, thenrace; captureboot/game iftimeout. Header translation is
  a boundedexperiment, NOT proven fix/wholegame byte-order compatibility.
  CurrentselectedPC endpointonly; doesn't generalizeotherPCpeers/voice.
  New2logs archivednfsmw_lan_preview8_pc_peer_timeout_*. Hostmissingnames
  stillopen/reversePCdiscovery deferred. Localmultiplayeronly; maincontrols,
  pre-existingdocsedit/HANDOFF andsharedSDK preserved; nopush/release.

- **October31 preview8: PC room joined, peer session adaptation ready.**
  Preview7 on phone joins PC073.TKM (.202), gjoi/+mgm COUNT2, sees live car/
  track updates, stays Waiting for players to connect. Logs: PC session has
  no SESS/PLATPARAMS; no UDP socket, XNetXnAddrToInAddr or peer QoS logged.
  Do not classify this as another discovery failure or established firewall
  failure. PC control/lobby interoperability now DEVICE-CONFIRMED; racing not.
  Preview8 adds PC-only local Xbox session record from matching HOST/OPPOi
  physical ADDRi plus gameIDENT, stable across updates; converts PC MA/MADDRi
  IPv4 forms into Xbox XUID^XNADDR and outgoing Xbox login MADDR into PC IPv4
  form. Uses existing LAN SDK behavior, no shared/isolated SDK source changes,
  no ready-flag forcing, no race payload rewrite. Existing sessions/unknown
  encodings preserved; invalid/missing host gets no fabricated session.
  Actual generated USA session/address decoder tests pass ASan/UBSan, as do
  fragmented actual gateway, prior room filter and preflight. These establish
  local envelope correctness, NOT PC peer handshake or race compatibility.
  Ready `ios/build/NFSMW-multiplayer-preview8-pc-peer-session.ipa`,30431007bytes,
  SHA2569b9dae9fd489b9c4ac6be58d4085863918f17da1a3a33ab0056b5aa073cdb959,
  appUUID35B56DBC-36E4-3E52-8EAF-D949C3091669; runtimeUUID unchanged preview7.
  Build/ZIP/signature pass; both SDK dylibs and104shaders identicalpreview7.
  **Next:** PC original LAN room open, phonepreview8 Join/launch/QuickMatch,
  check peer connection bar clears and PC can start race; capture boot/game
  if not. Need actual packet exchange before further protocol conclusions.
  Inputs (2logs/3screens) archivednfsmw_lan_preview7_pc_room_waiting_*.
  Hostguestnames still OPEN, reversePCdiscovery deferred. All localmultiplayer;
  controls/main pre-existing docs edit/HANDOFF and shared SDK preserved.

- **October 31 preview7: PC room filter identified; device join test next.**
  Preview6 device logs pass native discovery/login and receive PC room005.TKM,
  COUNT1, but Xbox rejects its encoded P/V192359. Actual generated USA
  sub_82546178 compares against192641 and returns0 before QoS on mismatch.
  Preview7 aliases ONLY that observed PC room build in PC-mode control
  metadata (+uss/+ust/ujoi/ucre/uadm); unknown versions, room flags, peer
  description, addresses and session/race payloads remain unchanged.
  Actual generated-validator test reproduces rejection and reaches QoS/return1
  with the alias (dependency stubs, NOT a real peer/race). ASan/UBSan gateway
  tests and existing preflight pass. Missing host guest names remain OPEN.
  Ready `ios/build/NFSMW-multiplayer-preview7-pc-room-discovery.ipa`,30424196bytes,
  SHA2564709104bbeae6e14ecd6844283916ea148eb1255c25e39f8ab417642f0ec2dd3,
  appUUIDF2E7FC8A-971D-3F10-BEA2-25A5E56AE2C5, runtime unchanged frompreview6.
  Build/ZIP/signature pass; GPUdylib/104shaders unchanged. No PC-side helper.
  **Next:** original PC LANroom remains open, phonepreview7 JoinPC/search,
  XboxLive→QuickMatch; verify room visible, then join and race. New boot
  diagnostics report join/subcodes and session field lengths without passwords.
  Do not infer race compatibility from metadata adaptation. PC discovering an
  iPhone host is requested but deferred by Stefan until PC-host joining works;
  needs original PC UDP9999 discovery and TCP9900 protocol hosting in iOS,
  plus reverse session/peer compatibility. No PC-host-side script/mod required
  by intended UX. Raw3logs archived asnfsmw_lan_preview6_pc_room_missing_*;
  preview6 historical device-test-next wording below is now superseded.
  Work remains isolated on localmultiplayer; main's pre-existing checkpoint
  edit and untracked HANDOFF preserved. No shared SDK or controls edits.

- **October31 preview6: native PC discovery/login adapter ready; device test next.**
  Laptop succeeds via helper on hotspot172.20.10.8 but game fails disconnect%
  query. Logs prove PC personaPERSempty (Xbox sendsGTAG only), then repeated
  Xbox `user` requests returnuserbadc. New in-app loopback adapter handles these
  control differences: addsPERS fromGTAG, fresh localLAN history44zero entries,
  forwardsotherEAframes/binaryfields unchanged. Does not importPC/official
  stats or translate racepayloads; actualPC/mobile room/race still unvalidated.
  Launcher now scans originalPC9900 plusmobile30960 directly, validates tab/
  newline@dir responses, probesnativePCbeforecustom10902preflight and routes
  gameEAcontrol throughlocal127.0.0.1 adapter. PCneedsNO Python/helper/mod.
  RealphysicalsourceADDR preserved toPC, joinred_ip selectedbyOSroute tohost
  toavoidloopback/wrong-interfacepeeridentity. LANoff/Hoststopadapter; no
  changes tosharedSDK/mobilehostprotocol. Mobilechoicesremainavailable.
  Actual originalserver.dll test passes directory/auth/PERS/presence with name,
  nativeadapter userhistoryresponsevalid; C++ASan/UBSan gatewaytests, mobile
 25stageparity, nativePC9900 tabdiscovery, preflight/interface/receive/touch pass.
  Build/ZIP/signature pass.104shaders/GPUdylib identicalpreview5; runtime rebuilt
  onlydebug_overlay forgeneratedSDKversion/buildstamp (networksourcepatch
  unchanged/applied, sourceoverlayidenticalsharedSDK). RuntimeUUIDFBF94504-
 0804-3C58-9C40-E28D663FE4C2. Unique IPA
  `ios/build/NFSMW-multiplayer-preview6-native-pc-lan.ipa`,30408180bytes,
  SHA256bbdf36fc64c194bdeffd6ffafbd43c122e76303ff8a810932d478ab009f99079,
  appUUIDF5F24A7A-FB0F-3B4D-BCE3-33E6DF8B6A13,0.5.1/build9.
  **Next:** normalPCgame LANhost, stopoldPythonbridge, installpreview6, Join/
  searchorcurrentPCIP, launchXboxLiveQuickMatch; verifygets pastlogin, roomjoin,
  thenrace. Captureboot/gameandPCroomstateifnextgatefails. No PCraceclaim.
  Newfiveinputlogs archived asnfsmw_lan_pc_laptop_and_three_player_*.
  Same logs prove mixedWi-Fi3players(.205bep1s/.133TKMachine/.149iPhone149)
  completedrace21:35:25–27 positions1/2/3, smoothperuser, noguestAV. Earlier
  AndroidWi-Fifailuresretained/intermittent, latestsuccessnowproven. Host's
  missingnames affectsBOTH guestplatforms inthisrun (earlierAndroid-only
  narrowing superseded); guestsseehostname, serverdeliversallnames. StillOPEN,
  no speculativeUI/rosterpatch. Maincontrols/sharedSDKuntouched/localonly.
  VMfirewallactioncode correctionandapprovedchanges/rollbackinTECHNICAL;
  earlierexplicitBLOCKclaimwasincorrect (Action2=Allow). No furtherVMchanges.

- **October31 user PC test: server/bridge READY in Parallels Shared network.**
  FirstWindows142:9900 refused beforeEA negotiation (PC listener/state/address
  not proven). Later Windows11 VM10.211.55.3 directory succeeds/PORT9900 and
  bridgeREADY, but iPhoneJoin says LANserver noresponse. Read-only prlctl confirms
  runningWindows11 net0 type=shared. SharedNAT guests normally inaccessible
  directly from physicalLAN; this is a concrete reachability obstacle before
  phonePCcompatibility test. No VM configuration changed. Next user switches
  VM network to Bridged on actualMacWi-Fi, gets newLANIPv4, restartsPCgame LAN
  host/bridge usingnewIP, phonejoinsnewIP. Await result, don't claim racefix.
  Desiredfinalflow noPChelper recordedabove. No newIPA/sourcefix thisturn.

- **October31 PC investigation: original server accepts mobile-style login.**
  User supplied server.dll(380928bytes)/server.cfg(1462bytes). Original DLL
  starts in isolated temporary CrossOver bottle using own bounded30s PE harness;
  binds observedMac192.168.1.152:9900. Actual @dir accepts PC and Xbox identities;
  complete Xbox-style auth(GTAG/XUID/NETV0/CLST192641) and persona accepted.
  Earlier authmiss was synthetic probe missingVERS, not incompatibility proof.
  Graphical speed.exe launch failed display-mode setup/exit5 in CrossOver;
  no PC racer or actual PC/mobile race tested. PC NETV20 vsXbox0 remains a
  compatibility question, not a proven blocker after directory/auth success.
  Added standalone Python pc_lan_probe.py, pc_lan_server_harness.py and explicit
  pc_lan_bridge.py. Bridge only forwards mobile30960 directory to original PC
 9900, launcher discovery/preflight10902; unchanged directory sends lobby direct
  to PC9900. NO race/roster/content/version translation and no playable-host
  claim. Name holds cover bridge clients only; choose distinct PC/mobile names.
  Five host boundary tests pass; actual DLL relay/preflight/discovery verified.
  No new IPA/SDK/mobile behavior changes. Protocol source credits in scripts/
  TECHNICAL; copied proprietary files remain /tmp ignored, never committed.
  **Next:** native Windows PC game hosting real LAN room, run bridge on PC,
  phoneJoin bridge address, test actual lobby visibility/join, then CommUDP
  handshake and race payloads. If no room, capture PC/mobile search-version/
  session metadata before patching; common directory/login is not cross-play.
  Commands below; logs archived Debug/31 October2026/nfsmw-pc-*. Tests stopped
  after bounded30s/15s. Temporary bottle/gamecopy retained for reproduction.
  Outstanding Android Wi-Fi and Android-only missing-name defects retained;
  user will test S21+ later. Main controls/sharedSDK untouched/no push.

- **October31 Android Wi-Fi host evidence received/archived:** host205 serves
  its own directory/login twice19:05/19:06; UDP discovery requests from133 at
 19:05:07/18/32, replies logged, but NO remote directory/lobby TCP or gamertag
  check recorded. This narrows failure before Android directory reaches host,
  not proof of router/TCP filtering. Android logs still needed if generated:
  default release disables game logging; native REGISTRO/debug build writes
  Android/data/io.github.nfsmwrecomp/files/logs/nfsmw.log. Do not ask friend to
  hunt indefinitely for a file normal release may never create. No source fix.

- **October 31 Android follow-up:** friend reports latest victorgbd release
  (exact version unknown), sees iOS host name in hotspot game room. On regular
  Wi-Fi Android fails discovery/gets stuck connecting to EA even after MANUAL
  current host192.168.1.205 entered. User explicitly confirms manual currentIP;
  do not repeat stale-address/search-only explanations. iOS↔iOS Wi-Fi works.
  Next required evidence: Android nfsmw.log plus iPhone boot/server from SAME
  failed Wi-Fi attempt to locate directory/service/login boundary; also compare
  Android roster/identity against working iOS. No fix yet, no new build.

- **October 31: Android hotspot gameplay and iOS Wi-Fi race completion confirmed.**
  Stefan confirms Android race worked after correct hotspot address, intentional
  quit; Android saw occasional remote-car flicker/proximity stutter. iOS host
  still hid Android's name/connected row. Later confirms iOS↔iOS names display
  correctly, so treat missing roster as Android-specific interoperability.
  Wi-Fi follow-up: discovery finds phone192.168.1.205; guest192.168.1.200
  (zestygooner/iPad) joins and user reports playing through the race, smoother
  opponent movement/no flicker observed. Five Wi-Fi files archived under Debug/
 31 October2026/nfsmw_lan_wifi_race_completed_*; bothgame logs zero guestAV.
  Do not claim Android↔iOS Wi-Fi tested: latest logs are two iOS devices.
  Android supplied logs initially read (18:51–18:55, TKMachine/.6), but their
  temporary pasteboard paths vanished before archive; exact failure recorded
  in TECHNICAL. Need re-export for further raw analysis, not silently lost.
  **Next:** Android release/build and its name-display behavior requested;
  compare Android vs iOS roster/identity path while preserving working iOS
  display. Android logs and renewed iOS host logs for name test needed. No
  roster fix identified yet. Android Wi-Fi, rematch/reconnect/reliability also
  unvalidated. Car flicker/stutter lower priority per Stefan; no speculative
  transport/game timing changes. PC deferred. Preview5 ready, actual installed
  preview4/5 not newly proven by append-only build stamp. No new IPA this turn.
  All work local multiplayer; main controls/sharedSDK unchanged/no push.

- **October 31: first Android test reaches lobby, fails peer connection; mixed interfaces.**
  User confirms Android on iPhone hotspot while iPhone Wi-Fi also enabled.
  Phone chose/advertised192.168.1.151, Android172.20.10.6, directory correctly
  answers Android172.20.10.1 but peer metadata retains phone's Wi-Fi address.
  RoomCOUNT=2, Android sees both, iOS never completes peer appearance. iOS
  receives Android8byte connect requests and sends replies/data; no guest AV.
  This is not the prior iOS crash or proof of gameplay compatibility.
  Host selector favored en0 over bridge; preview5 now prefers active private
  bridge over en0 (Wi-Fi fallback retained). No new flag/protocol/SDK change.
  Interface regression, setup/receive and protocol/discovery checks pass;
  build/signature/ZIP pass;104metallibs andbothSDKdylibs identicalpreview4.
  IPA `ios/build/NFSMW-multiplayer-preview5-hotspot-address.ipa`,30393361bytes,
  SHA256490f9fe9990e4a05f72ba5980152fd20cb4cc583ca4dbc7bfca06392e45f2260,
  UUIDB55A1AC5-73EE-38CA-A588-28BDD0E2E5EF; version0.5.1/build9.
  **Next:** user offered to retest preview4 with iPhone Wi-Fi disabled; agreed,
  restart Host and confirm172.20.10.1 before launch, Android reconnect. Outcome
  pending, not implied success. Preview5 also ready to remove that workaround;
  test with both interfaces active. Android logs needed if correct-address test
  still fails; check actual release identity/region then, no speculative bypass.
  Android source VERS/CLST matches iOS, SLUS differs21351/21267; significance
  unproved. PC deferred; regular Wi-Fi unresolved. Archive five originals as
  nfsmw_lan_preview4_android_mixed_interface_* (TECHNICAL identities).
  Local multiplayer only; main/sharedSDK/controlrelease unchanged, no push.

- **October 31 follow-up:** Stefan confirms he intentionally quit after the
  successful hotspot race; do not treat the final disconnect as a crash.
  Regular Wi-Fi still fails per user. Android cross-play is implemented using
  victorgbd's protocol but untested; test USA over the known-working hotspot
  path first. No Android compatibility acceptance or PC work yet.

- **October 31: preview4 iOS↔iOS hotspot race startup/gameplay confirmed.**
  Stefan reports success and supplied five logs plus two screenshots showing
  BMW and Fiat, reciprocal positions1/2 and2/2, lap1/3, opponent18m apart.
  Phone172.20.10.1 hosts, iPad172.20.10.5 joins; serverCOUNT=2 at18:37:54.932,
  gsta/+ses to BOTH at18:38:10.808. Both game logs show >1minute of peer
  UDP3658 traffic, zero guest AVs; prior0x160 crash did not recur. This validates
  preview4 receive fix and actual race startup/gameplay on tested hotspot.
  Finish/results/rematch/reconnect and prolonged play are not yet established.
  Tested build is preview4-receive-fix (SHA/UUID below); no new build/code/flags.
  All seven originals preserved under Debug/31 October 2026 with prefix
  nfsmw_lan_preview4_hotspot_success_; hashes/evidence in TECHNICAL.
  **Next:** finish a race/results/rematch, then verify victorgbd AndroidUSA
  interoperability and resolve original Wi-Fi reachability/setup usability.
  PC cross-play remains deferred until mobile interoperability is tested.
  Branch remains local multiplayer, no push/merge/release. Main controls and
  shared SDK unchanged; pre-existing main checkpoint edit/HANDOFF preserved.

- **October 31: hotspot reaches both peers; preview4 fixes receive descriptor lifetime.**
  Preview3 phone 172.20.10.1 and iPad 172.20.10.5 discover/connect, share room
  (COUNT=2), then exchange 21-byte UDP3658 handshakes. Both immediately fault
  at guest0x160, LR82829FE4, r11=0x100. Source identifies an async WSABUF
  descriptor retained on a returned stack frame: NetCrit reuses that exact
  slot to save r27 (global socket-list pointer); packet prefix00000100 then
  overwrites the list head. Copy descriptors before returning/pending; worker
  owns the copy. No protocol, game assets, controls or main/shared SDK changes.
  Actual receive regression reproduces unrelated-memory overwrite with preview3,
  passes fixed code under ASan/UBSan, including scatter and immediate delivery.
  Existing protocol25-stage/discovery/transport/setup/touch tests pass.
  Preview4 build/ZIP/signature pass,104shader libraries andGPU dylib unchanged;
  runtime dylib changed (UUID6FEF5993-683D-3AD0-BF01-0B465BFF3EA0).
  IPA `ios/build/NFSMW-multiplayer-preview4-receive-fix.ipa`,30393878bytes,
  SHA256 e2b352835356a97c8accf3a55db9236c2d4e2f2d29eea552084a25a021fd2390.
  Main executable UUID unchanged F5EC48E6-6A61-37F9-89DC-1D402CC03C18:
  this fix lives in runtime, so identify IPA by SHA/name/runtimeUUID.
  **Next:** install preview4 on BOTH devices; repeat phoneHost/iPadJoin over
  Personal Hotspot, then check shared room/race start and driving. Device fix
  and full race remain unvalidated; AndroidUSA follows, PC held. Original
  Wi-Fi intermittent reachability remains unresolved, separate from this crash.
  New boot also shows prior brief directory success was PHONE205, not Mac207;
  do not treat the user's earlier transient listing as verified Mac contact.
  All five logs archived; exact identities/source proof in TECHNICAL.
  Added regression command:
  `python3 tools/ios/test_multiplayer_receive.py --sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk`.
  Work stays local `multiplayer`; main's pre-existing modified checkpoint and
  untracked HANDOFF preserved. No push/merge/release.

- **October31: preview3 still fails; network-path controls, hotspot result pending.**
  Newhost/join evidence archived (TECHNICAL paths/hashes). FouriPadscans:UDP0,
  TCP253attempts/0connections, last_errno61; this is aggregate last-error, NOT
  proof205specificallyrefused. Host205selflogin/roomworks; freshHostonly18:03:27
  alsoinvisible. Launcher shutdown not established cause: server serves game
  afterlaunch; failurealsoinsetup. UserconfirmsWi-Fipeersallowed/permissionsON.
  LiveMac(.207)checkwhileuserconfirmedhostforeground:phone30960/10901/10902
  andUDP10902timeout. ARPresolved/directen0, MacnativefirewallOFF/noVPNorlisted
  networkextensions. Network.frameworkpathreportsWi-Fi,satisfied,nolocal-denial,
  butphoneconnecttimesout. MaccompatibleserverandHTTP8080controlverifiedlocally;
  no remotedataobserved. UserinitiallysaidMacappeared/connectedonIPad,thenclarified
  itbrieflyshowedconnectedbutcouldnotfinditagain; notverifiedbyserverlog. iPhone
  alsofailsMacJoin. SafariHTTPcontrolfailsonBOTH devices peruser, independentof
  game/LiveContainer. This establishesadditionalLANreachabilityfailure, notits
  cause; do not concluderouterisolation/TCC/app-hostingbugwithoutmoreevidence.
  TemporaryMacservers stoppedafterchecks. Packetcaptureunavailable:BPFpermission;
  devicectlCoreDeviceServicefailedtoinitialize. No newIPA/app-source change.
  Added read-only `tools/ios/lan_path_probe.mm` (macOSNetwork.frameworkCLI),
  verifiedgoodselfconnection/closedportandnegativepeerpath. ExactcommandsTECHNICAL.
  **Next:** userwilltryPersonalHotspot:restartHostonphone, noteCURRENTaddress,
  iPadJoin/discover/manualaddress beforegame. Awaitactualoutcome ("I'lltry" is
  NOTaresult). Ifhotspotworks, compareoriginalnetworkpath; ifnot, collectbothnew
  boot/serverlogs andtargetedcurrentendpoint/path/listenerstatebeforechanging
  transportagain. Sharedroom/race/AndroidUSAstillunvalidated; PCheld. Allworkon
  localmultiplayer, maincontrols/SDK/build preserved. No push/merge/release.

- **October 31: preview2 failure isolated to discovery; preview3 TCP fallback ready.**
  User DID choose Host on205 and Join on150. New21-line joinboot has8searches,
  all0hosts; hostserver records replies to150 during repeated searches. Host
  creates room with1player; guest neverlaunches. Screenshot agrees. This is
  failure before shared lobby/peer racing, not proof of wrong user steps. Exact
  UDP receive/drop cause still unproved (no receive diagnostics inpreview2).
  Newlogs/screenshot archived and hashes recorded inTECHNICAL.
  Preview3: explicitly bound unicastUDP discovery onApple; no broadcast on this
  socket because restricted entitlement isn't assumed. IfUDP returnsnohosts,
  probes unchanged EA TCP30960 directory, validates@dir/ADDR/PORT10901 and lists
  reachable hostIP. No server changes or gamertag reservations during scan;
  works with existing Android/Python protocol.32concurrent probes,350ms each,
 4s overall; nearby/24 bounded, excludes allownIPs/deduplicates. ManualIP remains.
  Host names/counts unavailable through oldTCP directory, shown generically.
  [lan-discovery] boot diagnostics show ownIPs,UDP reads/rejections/errors and
  TCP attempts/connections/verifiedhost. Forced UDP-blackhole tests pass against
  both host implementations, including fragmentation/malformedframe handling;
  existing25-stage/binarysession/patch tests pass. Bothbuilds/ZIP/signature pass;
 104shaders and2SDKdylibs byte-identicalpreview2. Artifact:
  `ios/build/NFSMW-multiplayer-preview3-tcp-discovery.ipa`,30393662bytes,
  SHA256 `d9264dd84701cd01483e9a5a1d1f47b5ee0b654e79d3797117115e7f71bce043`,
  UUID `F5EC48E6-6A61-37F9-89DC-1D402CC03C18`,bundle0.5.1/build9.
  **Next FIRST:** preview3 onboth, Host205(orcurrentdisplayedIP), Join150search;
  confirmhostlisted/selected and remoteconnectionready. Ifstill0sendjoinboot
  andhostserverlog; manual currenthostIP bypassesdiscovery as separatecheck.
  Onlythen launchboth andhostcreates/guestjoinssameoriginalgame room/race.
  No physical preview3test or sharedroom/race acceptance. Main controls/source/
  SDK untouched; no push/merge/tag/release. AndroidUSA/PC gates unchanged.

- **October 31: multiplayer preview2 guided setup ready; preview1 workflow failed.**
  Six supplied files archived under Debug/31 October2026 (TECHNICAL hashes/paths).
  Current game launches route EA to their own device (.150/.205), server logs
  only have their own client, all rooms COUNT1; zero ujoi/gjoi/gsta/COUNT2. Last
  .205 boot stops at launcher after17:07:53. No successful shared lobby/race,
  remote join or peer-transport test established; attempted preflight failure
  cannot be reconstructed because preview1 did not log it. Older log prefixes
  are historical; don't aggregate them as current gameplay failures.
  New Game→Host or join a game screen: distinct Host/Join, default device name,
  live status, nearby-host search plus manual fallback, visible Launch game,
  explicit host-creates/guest-joins in-game instructions. Host can wait in setup
  while the other discovers it. Own-IP Join rejected; normal Play always
  single-player; back cancels/stops setup, generations ignore stale callbacks.
  Discovery uses upstream protocol with nonblocking send; no restricted
  entitlement added, /24-or-smaller unicast fallback/manual IP remain important
  under LiveContainer. Listener rebind allows bounded500ms teardown window.
  SDK network/race code unchanged.25-stage host parity now verifies full
  high-byte MADDR/SESS/PLATPARAMS, preflight boundary/retry fixtures and existing
  menu tests pass. Two builds, ZIP/signature/104shaders checks pass. All shaders
  and GPU dylib identicalpreview1; runtime differs only in10cstring bytes among
  file-backed Mach-O sections after debug-overlay version-stamp rebuild.
  Artifact `ios/build/NFSMW-multiplayer-preview2-guided-setup.ipa`,30378275bytes,
  SHA256 `2dae71db4824e5cacdd799c16cf5d00e343cf233080e2a0ec43bed087c34186f`,
  UUID `792F461C-B08F-3AB5-A784-F89CFC9321E4`,bundle0.5.1/build9.
  Same-byte copy in main's ignoredios/build; main source/SDK/build unchanged.
  **Next:** install preview2 on both devices; one Host, other Join→tap that
  host (or its IP), confirm remote address then Launch game on both. In-game
  host Xbox Live→Quick Match→Create Game; guest Quick Match→join SAME race.
  Send both complete logs/boot/server logs if blocked; boot now records setup
  role/endpoint/search/failures. Actual discovery UI, shared room and full race
  remain device-unvalidated. Keep apps foreground. iOS first, Android USA later;
  PC remains deferred. No push/merge/tag/release; main controls remain separate.

- **October 31: multiplayer preview1 ready for device tests, local branch `multiplayer`.**
  Latest test11 controls/main19177b6 merged as baseline; controls sources remain
  byte-identical. Foreground Host/Join/Off(default), unique LAN gamertags,
  Android-compatible EA lobby plus direct peer sockets and mapped USA hook.
  Original Android implementation AND copied C++ adaptation credited to victorgbd
  in branch-only CHANGELOG. Main remains on controls work, with only its existing
  issue11 checkpoint note unstaged/HANDOFF untracked; shared SDK/build untouched.
  Isolated SDK/source/generated/build commands in Workspace section below.
  Host checks:25two-player lobby stages match upstream Python; real Darwin
  sockets/endian/address/close checks, actual event-wait and USA hook fixtures
  pass; test11 FE suite passes. Final IPA build/ZIP/signature/104shaders pass;
  shaders identicaltest11. Both SDKdylibs differ after full isolated rebuild;
  no GPU-code/energy/performance equivalence claim. Artifact:
  `ios/build/NFSMW-multiplayer-preview1-test11.ipa`,30377384bytes,SHA256
  `36afd106ecac81e371969c8da74f9fb4deba23d7dbdc80d0b91806792ab3bdb7`,
  UUID `FA4C17B7-4509-3EFA-ADA8-74CB2EAD5E0A`,bundle0.5.1/build9.
  Same bytes copied to main's ignored ios/build directory, no source changes there.
  **Next:** Stefan's two iOS devices: distinct gamertags, same LAN, one Host,
  other Join displayedIP, then Xbox Live→Quick Match; create/find/join, player
  list, full race/results/return, then swap host. Keep both foreground, logging
  ON, send both full logs plus device/OS/settings/edition. Then victorgbd USA
  Android peer both host roles; matchedUSA baseline confirmed by Stefan.
  No physical-device run, race-payload compatibility or acceptance yet. Test
  disconnect/rejoin/permission denial/LAN-off single-player/save/control regression
  before promotion. Discovery UI/background hosting not implemented. MixedPAL/USA
  unclaimed. Original PC work held until mobile LAN works. No push/merge/tag/release.

- **October 31: multiplayer feasibility researched on `codex/multiplayer` only.**
  No implementation/build/device test. Current upstream Android uses replacement
  EA Aries lobby + direct CommUDP race traffic, NOT System Link; the local sibling
  reference is outdated. Android/iOS Xbox-360 cross-play is a credible first goal,
  not yet validated, especially USA versus upstream PAL Spain. Original PC binary
  shares EA lobby vocabulary but native LAN and race wire compatibility remain
  unproved. Detailed pinned sources, local binary identity, integration points,
  staged plan and limitations in TECHNICAL; matching feature in BACKLOG.
  **Historical next action (now superseded by implementation approval):** first
  map the USA network hook and isolate SDK networking patches, then join an
  unchanged Android/Python lobby. Keep controls work on main. Main had pre-existing
  uncommitted `docs/DEVELOPMENT_PROGRESS.md`, `ios/src/game_scene_size.cpp`,
  `ios/src/menu_touch_policy.h`, `ios/src/touch_controls.mm`,
  `tools/ios/test_menu_touch.py`, and untracked `HANDOFF_CHATGPT.md`; none brought
  into this branch or altered. Sibling Android/SDK local work also untouched.

- **October 31: test11 alias popup/profile/Rankings selection trial ready.**
  Test10/log28 and alias confirmation screenshot archived (TECHNICAL exact
  paths/hashes). Log identifies profile first-row exclusion: content viewport
  was trimmed as outer dialog; now keeps full named region and OPTION_NAME_i
  rows. Profiles remain select-only/manual A. Rankings aborted on transient
  unobservable focus after first move; now bounded wait through color fade,
  two stable focus observations before next Rap Sheet move. Steady white vs
  green color detection confirmed by runtime channels. MC_Main_GC stacked
  BUTTON1..3 choices now supported, live Up/Down geometry and observed highlight
  before A; covered MC_Main cannot intercept MC_List. Small showcase pan gain
  raised0.8->0.95floor/full-scale1->0.5pt, maximum analog camera speed unchanged.
  One initial host assertion failed due gating applied to Options too; scoped
  stability gate to Rap Sheet. Two subsequent host runs/build/ZIP/signature
  pass;104metallibs/2SDKdylibs identicaltest10. Final artifact:
  `ios/build/NFSMW-0.5.2-test11-popup-profile-selection.ipa`,30185722bytes,
  SHA256 `c328f6dcdbaebf25739b1579e163d9ef17995a44032b16596ec0f9a0712afd6d`,
  UUID `A05B9FB0-96C2-3E84-B317-357567642887`,bundle0.5.1/build9.
  Same bytes verified on Desktop; ignored JSON beside build, older IPAs kept.
  **Next:** direct alias No/Yes choices, first/other profile names then manual
  A, distant Rankings taps up/down across highlight fade, small showcase pan.
  MC_Main live geometry and Rankings continuation remain device-pending. If
  maximum pan is still too slow, inspect guest camera response; virtual stick
  is already capped at1. Prior remaining menu matrix/safehouse stall/music
  acceptance remain pending where not explicitly accepted. No SDK/timing/profile
  edits, push/tag/release/version bump. Preserve pre-existing13-line issue11
  checkpoint note unstaged,HANDOFF untracked and sibling SDK changes.

- **October 31: test10 profile/Rap Sheet focus and showcase pan trial ready.**
  Test9/log27 archived with3screenshots (TECHNICAL paths/hashes). User confirms
  main Rap Sheet and Vehicle Database swipes; profile selection fails with
  selected00000000, main Rap Sheet falsely always selects last row, Rankings
  rows absent from model. Test10 uses unique white label focus (not backing
  strips), observed Rankings row hashes, narrow profile highlight/text-row
  vertical matching. Runtime FE color/profile geometry remains device-pending;
  first3row taps log color/geometry even on successful hits. No forced focus/A
  on missing/ambiguous state; profiles still require manual confirmation.
  Showcase pan axes reversed; slow motion minimum0.8/full-scale1pt/start0.5pt.
  Original maximum analog speed, pinch, release pulses and map path preserved.
  Infractions original82246518/82246778 creates8entries/8visible slots; screenshot
  shows all8, so no extra content to scroll. No changes to Vehicle Database.
  Host test script three runs exit0;2normal ipa builds exit0; ZIP/signature pass;
 104metallibs/2SDKdylibs identicaltest9r2. Final artifact:
  `ios/build/NFSMW-0.5.2-test10-profile-rap-pan.ipa`,30185747bytes,
  SHA256 `2a85b3579542469c1f27b44df4ac646fe0ac0923a672d9aee4028917d2eca55f`,
  UUID `0C48BE41-BDA4-3AA5-983A-7F246D329D2F`,bundle0.5.1/build9.
  Same bytes verified on Desktop; ignored.json beside build.
  **Next:** test profile/alias name taps (manual A), Rap Sheet main/Rankings
  row taps and swipes, slow showcase pan direction/response with anywhere
  gestures disabled; regress Vehicle Database. Remaining prior options/events
  matrix still pending where not explicitly accepted. If profile/Rap focus
  remains wrong, use new `[touch-focus]` / `[touch-focus-frame]` evidence, not
  another unobserved layout guess. Safehouse stall/music acceptance stay open.
  No push/tag/release/version bump, timing/profile/SDK edits. Preserve pre-existing
 13-line issue11 note unstaged, HANDOFF untracked and sibling SDK work.

- **October 31: test9-r2 row/grid selection trial ready, device validation next.**
  Archived test8 rotated logs25/26 and six screenshots (TECHNICAL exact paths/
  hashes); user says much better, reports row/grid/Rap Sheet/camera gaps.
  Concrete options regression: car-arrow vertical-pair rule was applied to all
  stacked LEFT_ARROW_i/RIGHT_ARROW_i rows. Now car-only. Wider selected frames
  (660-unit limit, 40-unit corner glyphs) cover options/milestones. Added model
  for Options/Track_Options rows, profile text rows, EVENT_ICON_i event tiles,
  Rap Sheet bullets/named text slots/viewports. Known event scrollbar groups
  send Up/Down. Options allow both axes on highlighted row, vertical elsewhere;
  event swipe viewport includes gaps. Bounded Rap Sheet subpage drag fallback.
  Selection uses existing controller inputs and observed focus, not native FE
  click callbacks. Profiles/settings never auto-A. Events/Rap Sheet first tap
  selects, an already-selected tap A. Event column-first path accounts for
  viewport cell reuse through selected-slot/content changes. Cancel on missing
  focus, replaced package or timeout; identical unobservable content shifts can
  safely time out. Runtime layout coverage/feel remain unconfirmed.
  Showcase starts at2pt instead14; small analog motions lifted above dead zone,
  pan full-scale8pt instead35 and pinch14pt instead25, stop pulses unchanged.
  Host actual walker/model/selection tests and three IPA builds pass. Final ZIP/
  signature/104shaders/2SDKdylibs verified; shaders/SDK identical to test8.
  `ios/build/NFSMW-0.5.2-test9-menu-selection-r2.ipa`,30185581bytes,
  SHA256 `43ece719b7174715ccaab29029e17e91d38f35d042576897678819a9bd72d43c`,
  UUID `7ADB4704-B768-3B41-B74E-55FC1195393A`, bundle0.5.1/build9. Same file verified on
  Desktop (superseded internal test9 Desktop copy removed; build copy retained).
  **Next:** profile tap doesn't load; Audio/Gameplay/Track options axes/arrows/
  row taps; Challenge row2/3 targets across viewport shifts, second tap launch;
  full event-box feel, Blacklist/milestones/bounty; Rap Sheet main/subpages;
  slow showcase swipes and pinch. No additional options screenshots needed yet;
  new failures should include log/layout evidence. Safehouse stall/music device
  acceptance not established by this report; entries remain pending/open. No
  push/tag/release or timing/profile/SDK edits. Preserve pre-existing issue11
  note unstaged, HANDOFF untracked and sibling SDK work.

- **October 31: test8 menu/audio trial ready; safehouse stall remains unresolved.**
  Test7/log24 contains the entire log23 prefix plus a new launch at01:28:39.820.
  Archived log/four screenshots under Debug/31 October2026 (`17pm_24_*`).
  Root-level pause highlight now recognized alongside decorative frame; generic
  ARROW directions corrected from observed pause taps. Rotated car-category
  chevrons resolve Up/Down, and Car_Select's visible RB Showcase overrides its
  misleading CIRCLE texture. Wider list panel uses vertical navigation. Quick
  Race Track_Select map and car-preview regions use horizontal navigation;
  world-map cursor remains separate. Showcase trial: one-finger camera motion,
  pinch trigger zoom, short analog pulses stop when fingers stop; needs actual
  axis/layout validation on device (no claim all shop/showcase variants work).
  Intro movie taps explicitly skip via movie-input detection including native
  movie shaders; Splash tap sends Start with anywhere OFF. Music option in
  launcher Audio: **Keep other music playing**, `ios_audio_mix_others=false`
  default/restart-only. Ambient mixing with silent-mode sound OFF; Playback+
  MixWithOthers when ON. No game-music auto-mute.
  Popup log shows desired OK highlight and one A, then engine request/job wait,
  renderer stops, audio zeros, nominal thermal/ample memory. Cause NOT fixed or
  proven touch-related. Added [job-wait] job/worker/caller/elapsed diagnostics
  after1s then5s; no forced job completion/timing-policy change. Next FIRST:
  safehouse popup with PAD A while OK selected, then direct OK, send full log.
  Then strict startup/save/pause/category/track/car gestures; showcase drag/pinch;
  music playing before game launch with new option ON, silent-mode combinations.
  Host tests/four incremental builds pass; ZIP/signature/104shaders/2SDKdylibs
  verified (shaders/dylibs identical to test7). Final artifact:
  `ios/build/NFSMW-0.5.2-test8-menu-areas-and-music-r2.ipa`, 30171188 bytes,
  SHA256 `535a4e5ed5d7ca27a7aefae0c4195af3d95ccf2f82a90757c18ab26948f9476b`,
  UUID `DF24267D-B2DC-35CB-BEEE-B8FECA0C2A6B`, bundle0.5.1/build9. No device validation yet,
  push/tag/release/version bump. Preserve pre-existing issue11 note unstaged,
  HANDOFF untracked, sibling SDK work. Detailed evidence/limits TECHNICAL;
  matching menu/audio and recurring loading-stall backlog entries updated.

- **October 31: test7 menu widgets and independent two-finger Back ready.**
  Test6/log23: user confirms blank-tap OFF works; main selected icon, Quick Race
  arrows/region triggers, world-map zoom and popup choices need corrections.
  Archived log plus four screenshots (TECHNICAL paths/hashes). Actual L1/R1
  texture names draw LT/RT here; corrected to trigger axes. Mapped observed
  carousel/track chevrons. Live FE focus-frame bounds now activate selected
  entries. Popup taps use live button bounds, select the desired choice, then
  require its observed highlight before A; failed/replaced/timed-out targets
  never accept. Unanswered ordinary queries now ignore instead of guessing A.
  Existing saved empty-accept key now labels **Tap and swipe anywhere**; OFF
  queries visible widget/selector/list/map areas at gesture start, ON retains
  universal navigation. New **Two-finger tap to go back** live/default ON,
  independent in launcher and in-game settings. Inversion unchanged.
  Host actual walker/popup tests, two incremental IPA builds, ZIP/signature,
  104 unchanged shaders and two unchanged SDK dylibs pass. Artifact:
  `ios/build/NFSMW-0.5.2-test7-menu-widgets.ipa`, 30164878 bytes, SHA256
  `b22937161ec577cef26664c4449d0812827a6f4e24c1e0877ab0dab230e1eacf`,
  UUID `81C2B2FE-7D27-32AE-A5FF-139322E10507`, bundle 0.5.1/build 9.
  **Next:** device test anywhere OFF: selected main-menu icon, arrows and held
  drags inside carousel/save/Blacklist versus outside; Quick Race track arrows
  and region LT/RT; map zoom/cursor; tap BOTH selected and unselected popup
  choices. Toggle two-finger Back OFF/ON independently; visible B hint stays
  active. Check anywhere ON, inversion and PAD/GESTURES return. Generic FE
  frame/list recognition and popup layout coverage remain unconfirmed on device;
  no universal coverage or energy savings claimed. No SDK/timing/profile edits,
  push/tag/release. Preserve the pre-existing 13-line issue11 checkpoint note
  unstaged, untracked HANDOFF_CHATGPT.md and sibling SDK changes.

- **October31:test6 corrects hint visibility,optionalblankA,andpadreturn.**
  Usertest5/log22:14tapsallnoicon->A;5two-fingerB. InvalidHUDkShownvisibility
  assumptionfound:guestFEquery82282CC0/showhide82282BF8 usehiddenbit26,
  notHUDbit23. Walkerfixed,regressionfixtureusesrealvisible42000000flags;
  broadimagecandidates/per-package/nearest-iconmissdiagnosticsadded.
  NewTap empty space to accept option live/defaultON inbothmenus;OFFignores
  unmatched/no-response taps;two-fingerBunchanged. PADoverridepillnowGESTURES
  returnsdirectly;unregisteredpilltouchescan'tbecomegestures/taps. Repeatpulses
  useoriginalleft-stickroute (mapcontinuousrightstickunchanged).
  Hosttests/build/ZIP/signature/104shaderspass;SDKdylibsidenticaltotest5.
  `ios/build/NFSMW-0.5.2-test6-menu-fallback-and-pad.ipa`,SHA256
  `3808820226985ffb83843d247d761b483f3a62c0c6a6f0ce72aa37b1efcfa169`,
  UUID `1E6C0B72-8C55-3F04-83AF-204029C4EF1D`,30148720bytes;
  bundle0.5.1/build9. NextsetblankacceptOFF,mainmenubuttons/chevrons/helddrag,
  PAD->GESTURESroundtrip,emptytapnoaction/twofingerB,thenmap/QuickRaceLT/RT.
  Sendlog;main-menucoverageNOTyetconfirmedondevice. Nosdk/timing/profile
  changes,no push/tag/release. Preserveissue11note,HANDOFF,SDKwork.

- **October31:test5 menu touch polish built;device verification next.**
  ArchivedAndroidreferencevideo(TECHNICAL hash/path);sampledframes inspected.
  NewInvert menu swipes setting live/defaultOFF inlauncher/in-game;worldmap
  cursor remainsdirect. Heldmenu drags sendboundedrepeatingDpadpulses;end/
  cancel/layoutclearstopthem. FEhintscan nowhandlesvisible standalone/nested
  icons,trigger/shoulder glyph aliases,knownworldmap IDs andindexedarrow
  objects atlivepositions. Hiddenparents skipped;unknownsmallglyphs logged/
  blocked instead of guessingA. Broaderglyphcoverage stillrequiresdevicecheck.
  Fixedold tap timeout clearingnewpendingtap andold releaseclearingnewpress.
  Syntheticgesture/actualwalker hostchecks,build,ZIP/signature/104shaderspass.
  `ios/build/NFSMW-0.5.2-test5-menu-controls-r2.ipa`,SHA256
  `e18f5df949c62555114cd93c0db3ec6e08c7f1810c3ff953af9476ac0b84979e`,
  UUID `D6276DAD-8512-3C1C-BAF7-72F84964472D`,30154542bytes;
  bundle0.5.1/build9 remains. Earlierinternalmenu-touch-polishIPA ispreview,
  not the finalhand-off. Newhostcheck python3 tools/ios/test_menu_touch.py.
  Nextmainmenuhelddrag/bothdirections,options<>controls,ABXYlabel/iconhints,
  mapLT/RT/categoryarrows,QuickRaceicon-onlyLT/RT,cancel/background/returnto
  driving. Sendlogforunrecognizedglyphs;noExtraArgsneeded. Recheckdefault
  navigationdirectionandliveinvert toggle. No timing/profile/SDKsourcechanges.
  Backlogfiveuser-confirmedbugsclosed,historyretained. Preservedissue11note,
  HANDOFF,SDKwork. No push/tag/versionbump/release.

- **October31:backlog review requested before choosing next changes.**
  Stefan asks for remaining backlog and suggestsMaxmovesallthreads toEcores.
  Clarified implementationrequestsQoS,notcoreaffinity;MaxDefault/EcoUtility/
  BalanceddrivingUserInitiated observed,butphysicalplacementunmeasured.
  Reviewedbacklogagainst0.5.0/0.5.1changelog/latestcheckpoint:historicalpending
  touch/ring/menu fixes mustnotbe presentedasnewwork. Next:userchoosesnewideas;
  keep profile/unchanged-qualitycost audit ascurrentpriority unlessredirected.
  No source/build/IPA/push thisreview. Preserveissue11note,HANDOFF,SDKwork.

- **October31:live profiles accepted on17PM;test4/log21 validates sixpairs.**
  Allsixprofile requests,mask00,no FAILED;selfQoS adoption/nativeentrysamples
  followEcoUtility,MaxDefault,BalanceddrivingUserInitiated. LastEco53.2–57.6fps,
  finalBalancedreturns60.0;thermalnominal. Archive/hash/detailedtimingsTECHNICAL.
  This validatesfunctional switching,notenergysavings orphysicalcoreplacement.
  CurrentMaxremovesUtility butDefaultQoS isbelowBalancedboost;keepdistinction
  explicit inprofileaudit. Nextremainingcoverage:tablet6+Epolicy,profileswith
  FPSchanges/background/explicitoverrides;thenmatchedbaselineunchanged-quality
  CPU/GPUcost audit. No code/newIPA thisanalysis. Both0.5.2featuresdeviceconfirmed
  on17PM;broadercoveragepending,no releaseauthorization. Preserveissue11note,
  HANDOFF,SDKwork;no push/tag/versionbump. Test4remainslatestIPA.

- **October31:test4 fixes missing in-game Performance row;profile test pending.**
  Stefan couldn't find profiles. Log20 proves newtest3 backend present (57
  live-profile markers,no failures); source Keys() omitted performance_mode.
  Added row besidefps_cap;already-defined shared choices/liveChoose path reused.
  Build/ZIP/signature/shader checks pass,both SDKdylibsidenticaltotest3.
  `ios/build/NFSMW-0.5.2-test4-profile-menu.ipa`,SHA256
  `a16ef0740b9a05804f663aa9a9077bdbfa5b8040db59b816eeb36a8878a41bf9`,
  UUID `662D52AD-B74A-3BA7-B11F-FBDF4BA9F270`,30140434bytes;
  bundle0.5.1/build9. Next same sixprofile transition test,now via visible
  Performance row. No priority-policy change;no claim of completedliveprofile
  validation. Archive/path/hash TECHNICAL. Preservedissue11/HANDOFF/SDKwork.
  No push/tag/release. Previoustest3 was unusable for profile selection due
  missingrow,not userinstallerror;record that limitation for future agents.

- **October31:0.5.2 test3 live performance profiles implemented;device check next.**
  Stefan approves live profiles for convenience/next optimization pass. Shared
  launch/live resolver retains existing phone/tablet policies and per-flag Extra
  Args/config/environment overrides. Guest+command threads adopt own QoS at
  start/wait/yield boundaries;main also polls existing main-loop hook. Old adaptive
  worker overrides/late history reset on policy epoch. Render/demand-pipeline
  work carries current QoS on unchanged serial queues. Host/audio/display work
  excluded. No visual quality or timing algorithm changes;no core-affinity claim.
  NewSDKpatch `python3 tools/ios/patch_ios_live_profiles.py` afterutility/sleep
  patches;status10/10. Addedlast inprepare_sdk list. Preserve siblingSDKwork.
  Host98304policy/override round trips,actualcallback TLS/wake tests,SDKpatch
  transaction/revert/idempotency and existingtiming tests pass;build/packagepass.
  `ios/build/NFSMW-0.5.2-test3-live-profiles.ipa`,SHA256
  `452b7e4977baef9d5021033cc9f94e770d78dd01ba88bedf07d28f3948c2a04f`,
  UUID `B7208F04-DE4E-3A1D-AA41-B8D922A9077E`,30140532bytes;
  bundle remains0.5.1/build9,no release. Next coldlaunchBalanced60/1x,noExtraArgs,
  auto capsOFF;Balanced->Eco->Max->Balanced->Max->Eco->Balanced,drive15–20s
  each afterpause/select/resume. Sendlog;checkpriority adoption/failures,pacing,
  workers and override cleanup. Then Eco40/120/60 and background/resume.
  Dormant threads adopt uponwaking;busy guest withno safe point delays adoption;
  real-device scheduling/performance overhead stillunmeasured. Don't claim savings.
  Newhostcheck PYTHONPYCACHEPREFIX=/tmp/nfsmw-python-cache python3
  tools/ios/test_performance_profiles.py. Normalbuildcommandunchanged.
  Preservedissue11checkpointnote,HANDOFF,siblingSDKwork;no push/tag/versionbump.

- **October30:live FPS matrix accepted;test2 cleans labels/capability choices.**
  Stefan reports no issues;log19 confirms all12directed cap transitions,guestHz
  and realtime policy correct. Archive/hash TECHNICAL. Removed experimental
  labels and obsolete speed-warning text. Shared launcher/in-game choices now
  show40/120 only when main screen maximumFramesPerSecond>=120;unsupported
  saved40/120 values resolve60 (Battery mode stillforces30). Extra Args remain
  explicit overrides;no timing/SDK changes this turn. Build/package checks pass.
  `ios/build/NFSMW-0.5.2-test2-fps-menu.ipa`,SHA256
  `eaf782204eefd251a2344909cbc967d4b74174472cc6888e5166ad118020de24`,
  UUID `896BB62D-ABD5-35FD-887F-C15A08AFBFF7`,30135895bytes;
  bundle still0.5.1/build9. Next:live performance profiles;menu filtering on60Hz
  hardware and background/auto-cap checks remain validation coverage items.
  No full FPS matrix rerun needed for label-only/capability change on17PM.
  Preserved issue11note,HANDOFF,siblingSDKwork. No push/tag/release.

- **October30:0.5.2 test1 live-FPS switching built;device validation next.**
  Stefan agrees to implementation order. All30/40/60/120 choices now live in
  options,battery state supports all four;auto caps still only40/60. SDK worker
  updates guest rate/phase/realtime interval and high-rate flag;swap history
  resets/waits abort across cap changes. Display publication/Metal40 ownership
  and world-clock debt reset.120Hz simulation/0.5.1 timing preserved.
  SDK changes reproduced by `python3 tools/ios/patch_ios_live_fps.py` (apply LAST
  after existing timing patches),included last in prepare_sdk list. Status3/3.
  Earlier SDK patch scripts already reported superseded blocks missing BEFORE
  this work;full prepare_sdk reapply on this heavily patched tree not attempted.
  See TECHNICAL for observations/tests. No SDK tracked files staged in app repo.
  `ios/build/NFSMW-0.5.2-test1-live-fps.ipa`,SHA256
  `3c69c6a19d780d10bec953a03bd78f2f18425be65507d5f9b796310a8a6ac40e`,
  UUID `5DF4F2C5-0634-360E-B867-C33BEE325BBB`,30135229bytes.
  Bundle remains0.5.1/build9 intentionally;filename identifies trial. No release.
  Next: device cap matrix inTECHNICAL,then implement live profiles only after
  cap transitions accepted. No Extra Args needed for basic test;optional existing
  frame trace/camera/tick diagnostics for comparisons. No stress resolutions.
  Preserved pre-existing issue11 note,HANDOFF,siblingSDKwork;own SDK edits via
  new tracked patchscript only. No push/tag/version bump this turn.
  New host check: PYTHONPYCACHEPREFIX=/tmp/nfsmw-python-cache python3
  tools/ios/test_live_fps_patch.py; existing timing checks/build command unchanged.

- **October30:0.5.1 released by Stefan;0.5.2 live-settings work prioritized.**
  User confirms update live (not independently queried). Promote existing
  all-cap/profile backlog entries to active; add profile audit, resumed
  unchanged-quality optimization pass and PC-style graphics/presets request.
  Source review identifies startup guest-clock interval/120flag/realtime policy
  and cached QoS/thread/queue state as actual runtime transition work. Removing
  menu guards alone is insufficient. TECHNICAL has design/dependencies/checks.
  Next implementation: shared runtime cap transition, then shared launch/live
  performance policy with Extra Args precedence, each device-checked before
  stacking. No feature code/newIPA/version bump this planning/source-audit turn.
  0.5.1 timing baseline retained; no new push/tag/release authorization.
  Preserved pre-existing issue11 note,HANDOFF and siblingSDK modifications;
  other-agent d5d3e1d issue13 diagnosis read and retained without reopening.

- **October 30: GitHub issue 13 disc-startup failure diagnosed (no source change).**
  Attached `/Users/bep1s/Downloads/nfsmw-2.log` archived in Debug/30 October
  2026 as `nfsmw_issue13_ipad_pro_m4_disc_startup.log`; hash/details TECHNICAL.
  Two launches: Black Edition-named image mounts but lacks accessible root
  `default.xex`; regular USA-named image fails GDFX magic verification (-30).
  Footprints 208/182 MiB, reported headroom 7984/8010 MiB: no memory-pressure
  evidence for these failures. Wrong-platform/incomplete/unsupported images
  are hypotheses, not identified from filenames. Next: reporter verifies USA
  Xbox 360 dump, root default.xex, complete local copy/file size/hash; then
  retests with that selected image. D-015 tracks report and startup-error UX.
  No code/build/device test, GitHub comment, push, tag or release this session.
  Preserved pre-existing issue11 checkpoint note uncommitted (another session's
  work), untracked local HANDOFF_CHATGPT.md and sibling SDK changes.

- **October 30: GitHub authentication restored;0.5.1 changes pushed.**
  Stefan authenticated and asked whether30/120 fixes included: yes,both are
  compiled into final0.5.1/build9 along with40 pacing and14PM60 fix.
  `git push origin main` exit0,remote advanced4e2ac87->223623a. This record
  follows as a documentation commit. Next: Stefan smoke-tests final namedIPA
  without diagnostic args and creates tag/release; agent has not published.
  Preserve unrelated issue11 checkpoint note/HANDOFF. No code/build changes.

- **October 30: push blocked by missing GitHub credentials on new laptop.**
  Release preparation committed26e41c4; `git push origin main` failed:
  could not read Username for HTTPS/Device not configured. gh auth status fails
  with invalid token, including unsandboxed check; ~/.ssh absent. Remote main
  remains4e2ac87fb27af677884d917198b62831a581bedb. No changes pushed/tagged/
  published. User needs gh auth login -h github.com then gh auth setup-git;
  next agent action is retry authorized git push origin main and verify remote
  matches HEAD. No new permission needed. FinalIPA is ready at path below.

- **October 30: 0.5.1/build9 release preparation approved; push authorized.**
  Stefan requests both live-switching items parked in backlog, removal of stress
  resolutions and all0.5.1 changes pushed for him to release. Backlog now has
  separate entries. Removed stress CMake flag/UI choices/8x renderer override;
  old numeric settings >2x reset to1x on load, native selection preserved.
  Promoted accepted Metal40 presentation defaultON; all diagnostic flags stayOFF.
  Default120Hz simulation and both confirmed timing fixes retained. Changelog/
  README/version updated. Final named IPA `ios/build/NFS-Most-Wanted-0.5.1.ipa`,
  SHA256 `e00b03cb68589e9517a8a44b204540d9fae016b68ba18367d87780362d6402c9`,
  UUID `4A4C9469-32E6-3BE6-AEAB-06A13C96D222`,30134223bytes.
  SDK/generated status,host tests,build,signature,ZIP,104shader comparisons pass.
  Test10 device acceptance precedes packaging; finalIPA itself still needs normal
  fresh-container smoke test. Remaining extreme managed40 oversupply recorded,
  not claimed fixed. Push main only; Stefan handles tag/release/asset upload.
  Remove six diagnostic/test Extra Args for normal use (frame_ticks2/default
  Metal40 already apply). Preserve issue11 note/HANDOFF outside commit.
  Next: user smoke-tests named0.5.1IPA and publishes update. No agent tag/release.

- **October 30: test10 accepted; log18 confirms30 steps and120 catch-up.**
  Stefan:30 great,120 slowdown fixed,40/60 still fine. At120 return1x throughput
  ~89–99fps with GPU~9–10ms, thermal nominal, render QoS User Initiated; no
  evidence of Utility demotion, physical core placement unknown. Game clock
  still tracks real time.30 selected1380updates:1376full33.3ms,4catch-up;
  no half steps. Full measurements/log hash TECHNICAL. No new IPA this turn.
  Next release work: review remaining managed40 stress oversupply, opt-in/default
  promotion and remove stress choices from final normal-resolution candidate
  when authorized; no version/push/tag/release yet. User asks about live caps/
  profiles: guest vblank initialization, not simulation rate, currently blocks
  30/60<->40/120; profiles are launch-only. Record as separate future work,
  outside the two-fix hotfix. Keep120Hz simulation. Preserved issue11/HANDOFF.

- **October 30: test10 corrects30 world quantum and120 input catch-up duration.**
  Stefan approves both remaining fixes, hoping to close smoothness work. Log17
  camera trace archived; uneven steps confirmed, estimator180-degree artifacts
  must not be treated as real camera jumps (TECHNICAL).30 driving now consumes
  two guest60Hz vblanks/world frame; legacy catch-up/resync uses ~66.67ms duration
  rather than four periods regardless of guest rate.120Hz simulation retained;
  managed40 path unchanged. Host policy/engine patch checks and build pass.
  `ios/build/NFSMW-0.5.0-test10-30-120-world-clock.ipa`,SHA256
  `7bb64198f0b613645d628746e1bdf88df7dc24e5b7a33d147172bedcf676f26d`,
  UUID `A41DC73D-F563-3062-B68D-4E221763EF64`,0.5.0/build8.
  Next: same six args including camera trace;30cap1x30–60s turning, then120cap
  1x/5x/1x race clock comparison; short40/60 regression. No device result yet;
  cannot declare definitive fix. Keep stress choices in test10; configuredOFF
  afterward for future builds, genericIPA/cache app still stress until rebuild.
  Managed40 oversupply remains open/defaultOFF. No release/version/push/tag.
  Preserved issue11 checkpoint note,HANDOFF and SDK work. New host check:
  `python3 tools/ios/test_frame_clock_policy.py`; normal build procedure unchanged.

- **October 30: test9 log16 reveals 120 clock ceiling and uneven30 world steps.**
  Stefan says caps generally good,120 still slows; asks to check30 camera/world
  before removing stress choices for final0.5.1. Keep test resolutions available.
  Engine66.667ms correction active at30/60/120;120 input clock still bounded by
  four8.334ms periods, resyncing/discarding debt under load. Selected stress
  clock gives48.487s/60.630s host; engine timing29.788s/35.781s host (different
  windows).30 shown gaps538/540 at33.3ms but engine steps include16.7/50/66.7ms;
  no camera trace, so camera smoothness unproven. Next: correct120 input-clock
  catch-up duration while retaining120Hz simulation; inspect30 camera trace
  with --nfsmw_native_camera_log=true on existing test9. Detailed windows and
  limitations TECHNICAL. No code/build/default/release change this analysis.

- **October 30: test9 restores original catch-up allowance across all caps.**
  Stefan explicitly approved applying the correction across the board, keeping
  default120Hz simulation. Removed managed40/caller/menu/frame-mode gates from
  local cap correction; only nonzero flag, actual1/120 budget unit and valid
  positive limit are corrected. Original1/60 and separate20ms branch unchanged.
  World-step diagnostic now covers driving at all caps/renderers (still opt-in).
  Built `ios/build/NFSMW-0.5.0-test9-all-caps-catchup.ipa`, SHA256
  `1e387cda34a0eadf215b7a1084cce5b5c37ffd18da39f32a4b690845521a1d1b`,
  UUID `DAAF1A3E-8720-3679-ABB6-B859A1567310`,0.5.0/build8.
  Host tests/build/ZIP/signature/104-shader comparisons passed; details TECHNICAL.
  Next:60 cap1x/5x/1x race clock comparison, then short30 and120 checks and40
  regression with same five arguments. Device result pending. Managed40 remains
  opt-in; its separate stress oversupply remains open. No release/version bump.
  Stress configured ON for artifact then OFF for future builds; generic IPA/cache
  app still stress until rebuilt. Pre-existing issue11 note/HANDOFF preserved.

- **October 30: 60-cap stress test confirms perceived slowdown below30.**
  Stefan reports5x slow motion, above30 mostly fine. Log15 archived (TECHNICAL).
  Selected5x360updates average26.58 updates/s; supplied13.522s vs13.542s host,
  so incoming clock catches up.197steps exceed34ms. Downstream trace is40-only,
  so clamp loss at60 remains inferred from source plus user report, not directly
  measured. Next correction to review: preserve original catch-up duration at60
  with120Hz simulation retained; use downstream diagnostics at60 to validate.
  No code/IPA/default changes this turn; preserved issue11 note and HANDOFF.

- **October 30: 60 fps overload review requested.** Stefan reiterates that
  120 Hz simulation is deliberately the default at all caps for smooth motion;
  retain it. Source review: 60 retains legacy debt/catch-up clock and the
  shared-step-dependent engine cap (typically33.33 ms with budget4/120).
  Test8 cap restoration is managed40 only. Next useful device check: 60 fps
  race at1x, then stress to45–55 and below30 fps, then1x; compare race clock
  to real time. Occasional >33 ms steps can be clipped even above30 average.
  Actual60 overload result remains unmeasured; no source change this turn.

- **October 30: test8 accepted by Stefan; log14 archived and analyzed.**
  “Everything worked as intended” on the ongoing 17 Pro Max test. Effective
  engine limit66.667 ms confirmed. 1x engine time/host time ~100% before and
  after5x. Full captured5x batches advance43.317s engine/41.301s host (~104.9%);
  later subset ~107.5%. User-perceived slowdown resolved, but prior render-slot
  overcompensation remains measurable; do not call timing exact under all loads.
  Evidence: Debug/29 October 2026/nfsmw_iphone_17pm_14_metal_display_40_test8_catchup_limit.log
  (full path/hash/settings/measurements in TECHNICAL). Next: review remaining
  overload accounting before default promotion and make a normal-resolution
  release candidate when authorized. Experiment remains OFF; no build, version,
  push, tag or release this turn. Preserved issue11 note and HANDOFF uncommitted.

- **October 30: test8 restores the managed-40 catch-up allowance; device check pending.**
  Stefan approved the correction. The measured main-loop driving path now
  retains the original 66.67 ms cap with 120 Hz simulation (previously 33.33 ms).
  Other callers, caps, menus, unmanaged output and the 20 ms budget branch
  retain their limits. Experimental Metal 40 remains OFF by default; the
  confirmed 60 fps fix is unchanged. No release/version promotion.
  Built `ios/build/NFSMW-0.5.0-metal-display-40-test8-catchup-limit.ipa`,
  SHA256 `4b0d0c915c0610a644c0c72330de843ea51719b0260d197a7629fa2877753c5c`,
  UUID `8899C41D-E22F-3268-905A-ED3107A80A63`, still 0.5.0/build 8.
  Build, 576 scope cases, hook validation, ZIP/signature and 104 shader checks
  passed. TECHNICAL records the first build failure and remaining limitations.
  Next: cold LiveContainer, same five diagnostic arguments, Balanced/40,
  Low Power Mode and MetalFX off; race 20–30 s at 1x, 30 s at 5x, then restore
  1x. Compare race clock with real time and send log. Check effective limit,
  output/host time and motion; prior log12 time oversupply remains unresolved.
  Stress resolutions were ON for this artifact, then configured OFF for future
  builds. Current NFSMW.ipa/cache app still contain stress choices until rebuilt.
  Preserved pre-existing issue11 checkpoint note and untracked HANDOFF_CHATGPT.md;
  excluded both and all sibling SDK changes from this session commit.
  Build: from ios, configure `cmake --preset ios -DNFSMW_RESOLUTION_STRESS_TEST=ON`,
  then `cmake --build --preset ios --target ipa -j 6`; preserve named IPA before
  configuring stress OFF. Host check: `PYTHONPYCACHEPREFIX=/tmp/nfsmw-python-cache
  python3 tools/ios/test_world_step_limit.py`.
  Codegen still applies patch_game_world_step_trace.py. When updating an existing
  test7 generated tree, revert using the test7 script before applying this version
  (done locally); fresh code generation also works. Partial patches fail closed.

- **October 30: log13 confirms the engine clamp causes below-cap slowdown.**
  Archived17pm_13_test7_world_step log (fullpath/hash inTECHNICAL).
  All1380samples:33.333mslimit,flag2,budget4,main-loopcaller823AFE64.
  Selected1x engineoutput12.001s/12.000shost,no clamp;5xoutput14.567s/
  19.814shost (~73.5%),308/480updatesclipped. Input supplies~102.2%,
  so increasing suppliedtime is not thefix. Next scopedmanaged40driving
  correction:preserve originalelapsed catch-upbudget independently of
  120Hzsimulationstep,then1x/5x engineoutput comparison. Priorlog12
  accountingoversupply also remains to assess. No sourcefix/newIPA this
  analysis turn;test7stilldiagnostic,60fixretained,no0.5.1promotion.

- **October 30: test7 downstream world-time diagnostic built and verified.**
  Stefan approved the diagnostic after test6 still slowed below40.
  New [world-step] records incoming/accumulated/capped/quantized time,
  runtime flag/budget, caller and render-assignment sequence. Existing
  `nfsmw_frame_ticks_log` enables it; diagnostic and Metal experiment
  default OFF. Timing algorithm and60fix unchanged. Codegen applies new
  patch automatically; all old postpatches verified. Full new-laptop cache,
  current hostCLI and exact shader bundle restored; generated sources are
  now patched/build-ready. See TECHNICAL for host-only shim/build commands
  and correction of earlier unproven source-partition mismatch claim.
  `ios/build/NFSMW-0.5.0-metal-display-40-test7-world-step-diag.ipa`,
  SHA256 4baf6442ad7f51e12a8a98da8871d1999402b5219587c9cb90c65fb52e778176,
  UUID 6C6B1D1E-C437-35DC-9F56-813F07CEE650. Build/ZIP/signature/104same shaders pass;
  both SDKdylibs rebuilt with newtoolchain and differ fromtest6.
  Next cold17ProMax/Balanced40/Low Power Modeoff/MetalFXoff: same five
  test6args (TECHNICAL),20-30s1x then30s5x race,restore1x,skip8x,sendlog.
  Measure activecap/caller/actual output and world/rendercounts before
  scopedcorrection. No device result/fix/defaultpromotion/versionbump.
  Stressbuild option cache resetOFF; rebuild before normalcandidate since
  NFSMW.ipa/cacheapp stillcontainstresschoices. No push/tag/release.
  Pre-existing issue11note/HANDOFF/SDKwork preserved and notstaged.

- **October30: race repeat stillslow; downstreamsimulationcap candidate found.**
  Archived17pm_12_test6_race_slowdown log (fullpath/identity inTECHNICAL).
  Stefan confirms everythinga bitslower at~26fps;no numericaltimerreadings.
  Late1380clockupdates give70.032s over56.368sraw (124.2%):test6accounting
  notvalidated,notrelease-ready. Rawengineinspection finds sub_823C6500
  clamp uses4*sharedstep in onebranch;120Hzpatch changes66.67->33.33ms
  initialbudget,consistentwithslowdown below30fps. Runtimeflag/multiplier
  mustbeobserved,notassumed. Nextnarrow actualworldstep/clampdiagnostic
  and reconcileworldupdatesvsrenderframes;preservesteady40/60fix.
  No need more sameuninstrumentedtests. No newsource/build/default/release.
  Ignoredgeneratedsources restored FORINSPECTIONONLY viaoldCLI;notpatched,
  functiongroupingdiffers fromhardcodedpatchpaths. Beforebuild restore
  matchingCLI/fullpostpatchprocedure andmissingcache/shaders. Privateimage
  ignoredios/build/managed40-inspection-image.bin. Fullfailedattempts and
  findings inTECHNICAL. Existingissue11/HANDOFF/SDKwork preserved.

- **October30: 17 Pro Max test6 stress log analyzed; race-timer repeat next.**
  Archived nfsmw_iphone_17pm_11_metal_display_40_test6_resolution_stress.log.
  1x/3x steady40 and25ms shown gaps;5x~21.9fps/GPU50.73ms.
  Selected360 world updates give16.297s over15.608s raw(~104.4%),so
  compensation active;does NOT establish actual physics speed. Stefan
  suspects slowlogic,unclear5xvs8x;requested race-seconds retest. Nextsame
  IPA/fiveargs,Balanced40:compare race-timer advance over30externalseconds
  at1x then5x,exclude menus/settling,observe carmotion,restore1x,skip8x.
  8xblackpicture/termination,peak5916MiB near6144limit;memorypressure
  plausible,unproven;outsidehotfixscope. Audio48kHz/0gaps unaffected.
  No new source/build/default/release. If repeat disagrees with supplied
  time,inspect downstream world/physics consumption and frame association.
  New laptop missing buildcache/generated89.cpp;restore before newbuild.
  Pre-existing issue11 note/HANDOFF/SDK changes preserved uncommitted.

- **October30: test6 resolution-stress IPA ready; 14 Pro Max unavailable.**
  Stefan returned the phone and requested temporary choices up to8x to
  force GPU-limited output on another device; hopes to release tomorrow,
  which is not permission to publish. Build-only CMake option
  `NFSMW_RESOLUTION_STRESS_TEST` defaults OFF; ON adds2.5/3/4/5/6/8x
  launcher/in-game choices and raises native numeric ceiling4->8.
  Configure from ios with `cmake --preset ios -DNFSMW_RESOLUTION_STRESS_TEST=ON`,
  then normal ipa build. Cache reset OFF after preserving test artifact;
  rebuild before any normal candidate (current NFSMW.ipa is the stress IPA).
  `ios/build/NFSMW-0.5.0-metal-display-40-test6-resolution-stress.ipa`,
  SHA256 d3888a5a007e3a6c4f1f0cf02c81b377928cbc0460459199a4ccd1dccf792bf4,
  UUID54E550CB-F57B-3BE1-94DF-19B90F9987E0. Build/ZIP/signature/shaders pass.
  Next same five test6 args,Balanced40,Low Power Mode off:1x baseline,
  raise gradually only until below40,restore1x;device/OS with log.
  Return scale to1x before normal builds because settings persist.
  No device result;missed-slot correctness/lifecycle/other-device40/60
  checks still pending;experiment defaultoff,no release/version bump.

- **October30: native chase(log10) confirms below40 slow motion; test6 built.**
  Archived nfsmw_iphone_14pm_10_metal_display_40_native_heavy_chase.log.
  Native1.792x heavy chase drops27-32fps,GPU~33-39ms;780 world updates
  give19.516s over25.872s raw (~75.4%). Test5 cannot ship unchanged.
  Added managed target-slot accounting: preserve steady40 full steps,
  compensate actual skipped assigned slots under load,carry fractions so
  phase jitter cancels;bounded catch-up/reset on menus/lifecycle/loading.
  Host29000slot,3000grid,24000legacy differential,36000clock model checks
  passed with sanitizers where applicable;build/ZIP/signature passed.
  `ios/build/NFSMW-0.5.0-metal-display-40-test6.ipa`,SHA256
  427b5631ebbf623a42d2dfd606fab8834afc963bc9251e38b8c89907d526b3b5,
  UUID9CB9776E-983A-3EEF-BC44-0A5DBFE842B8. Next samefive diagnostic args:
  1x smoothness then native heavy below40/game-speed check,restore1x.
  No device result yet;other-device/menu/resume tests still pending.
  Experiment default off,60fix intact,0.5.1 not ready/no release.

- **October30: test5 steady40 successful on14 Pro Max (log9).** Stefan:
  "felt like heaven in terms of everything". Archived
  nfsmw_iphone_14pm_9_metal_display_40_test5_smooth.log in Debug/29October.
  Selected1980 world steps full~25.02ms,1978/1980 shown gaps25ms;given/
  raw elapsed ratio99.95%,no steady repeat-strip samples. Known-good IPA
  remains test5-world-step,f918c1df...,UUIDBB804486-977E-3A1C-A832-4BFF813E5FD5.
  Next before default0.5.1: short heavier-resolution run to assess genuine
  below40/game-speed behavior (fixed steps may slow simulation there),
  menu30/pause/background-resume and another owned ProMotion40/60 check.
  Then enable intended40 defaults,diagnostics off,0.5.1/build9 and verified
  clean candidate; no push/tag/release without explicit go. No source/build
  changes or promotion this turn. 60 fix confirmed;0.5.1 scope only2 fixes.

- **October30: log8 confirms world-step mismatch; test5 built.**
  Archived nfsmw_iphone_14pm_8_metal_display_40_world_diagnostic.log.
  mode2 confirmed (existing default since0.4.2,not2ticks).2280 shown gaps
  all25ms; world steps1901x25.02,180x33.36,160x16.68,37x8.34,2x25.05ms.
  No steady sampled-strip repeats. Test5 gives one full managed40 frame
  duration per driving update; legacy paths/menus/30/60/120 preserved.
  Host24000 legacy differential +2280 recorded-interval checks passed;
  build/ZIP/signature passed. `ios/build/NFSMW-0.5.0-metal-display-40-test5-world-step.ipa`,
  SHA256 f918c1dfd21a9286fb0af94c73691c9dbd209600f0b5e2f387abec29d04254b9,
  UUIDBB804486-977E-3A1C-A832-4BFF813E5FD5. Next same14PM/Balanced/1x/40
  cold chase with same five diagnostic arguments. Check motion + game speed,
  then genuine below40/missed-frame behavior before promotion (fixed-step
  branch can slow simulation under sustained frame drops). Experimental
  default still off,60fix intact,0.5.1 not ready/no release.

- **October 30: original-world-time trial feels worse; diagnostic test4
  built.** Archived nfsmw_iphone_14pm_7_metal_display_40_frame_ticks_off_worse.log.
  All1440 selected shown gaps25ms; user judder worsens, so restore mode2.
  New default-off `nfsmw_frame_ticks_log` observes raw/given world update
  time, quantum/debt/host gap; no timing/presentation behavior change.
  24000-return host differential, build/ZIP/signature passed. Test IPA
  `ios/build/NFSMW-0.5.0-metal-display-40-test4-diag.ipa`, SHA-256
  68e859cd2e645e3c25439344bdcc544afd9eb33234b8fd86d82a803c50d7ef05,
  UUID542EEA4F-55E5-35D4-9FD7-A407F0100234. Next same14 Pro Max
  Balanced/1x/40 cold run, Low Power Mode off, replace Extra Args with
  metal_display_40=true, frame_trace=true, frame_ticks=2,
  frame_ticks_log=true, native_repeat_log=true (full nfsmw_ prefixes in
  TECHNICAL); remove camera override. Correlate world steps/strip repeats
  with presentation. 40 unaccepted/default off; 60 fix remains; no release.

- **October 30: test3 still has perceived stuck frames about every 5 s.**
  Archived nfsmw_iphone_14pm_6_metal_display_40_test3_stuck_frames.log in
  Debug/29 October. Guest grid ~8.34 ms confirmed; 1437/1440 selected
  shown gaps 25 ms, no repeating 5 s presentation stalls established.
  Camera rotation unevenness is inconclusive for full-frame freezes.
  Next: SAME test3 IPA/40 settings/diagnostic flags, add only
  `--nfsmw_frame_ticks=0`, cold launch, same ~1 min chase to isolate
  world-frame clock correction. Temporary trial only; preserve default2
  and confirmed 60 fix globally. No new source/build this turn. 40 still
  unaccepted/default off, 0.5.1 not ready for release.

- **October 30: 40 test2 starts but feels worse; guest-clock correction
  built as test3 (default off).** Archived
  `Debug/29 October 2026/nfsmw_iphone_14pm_5_metal_display_40_test2_worse.log`.
  Screen cadence improved (1435/1440 shown gaps 25 ms) but swap->shown
  mean rose 27.42 -> 63.63 ms in selected windows; Stefan mostly felt more
  world jerking, some input delay. Display link reported 80 Hz: legacy
  integer split can publish 80/160 Hz instead of guest 120. Test3 fixes
  only the experimental guest grid, deriving three guest ticks per system
  40 fps slot; keeps two-frame latency/presentation unchanged. 3000 host
  arithmetic checks, build/ZIP/deep strict signature passed; same shaders
  and SDK dylibs. `ios/build/NFSMW-0.5.0-metal-display-40-test3.ipa`,
  SHA-256 06e1b78301b5ed3bf2d2a475d4f0350c1c5d7aa39c59e9e63bcff6e563950b97,
  UUID 29F35A9F-1923-38A5-A256-AAD17E3CAE3F. Next: same 14 Pro Max
  Balanced/1x/40 cold test, Low Power Mode off, metal_display_40 and
  frame_trace true, add `--nfsmw_native_camera_log=true` to measure world
  motion too. Observe smoothness/latency. No 40 fix accepted, default
  change, 0.5.1 bump or release; confirmed 60 fix remains intact.

- **October 30: 40 fps experiment crashed twice at startup; documented
  API misuse corrected, test2 built.** Archived
  `Debug/29 October 2026/nfsmw_iphone_14pm_4_metal_display_40_crash.log`.
  Managed branch wrongly used timed present; Apple explicitly prohibits
  timed presentation on CAMetalDisplayLink drawables (assert). Replaced
  with plain command-buffer present (forwards plain drawable.present after
  GPU scheduling); estimated display time is diagnostic only, stale checks
  now use targetTimestamp submission deadline. No .ips/boot stack supplied:
  concrete API defect found, exact crash stack not proven by buffered log.
  `ios/build/NFSMW-0.5.0-metal-display-40-test2.ipa`, 0.5.0/8, SHA-256
  87ea6d83729966b2704889271de251a4e2a315ce5700fcf801337b04dd8778f5,
  UUID 9AC76DA4-519A-3A7D-91A6-146C0DEBE6D7. Build/ZIP/deep strict
  signature passed; shaders and SDK dylibs unchanged versus failed test1.
  Next: same 14 Pro Max Balanced/1x/40, Low Power Mode off, cold launch
  with `--nfsmw_native_metal_display_40=true --nfsmw_native_frame_trace=true`.
  First confirm startup, then chase/cadence/latency; if it still crashes,
  get .ips and Documents/logs/boot.txt. Experimental flag still default
  false, 60 fix intact; no rollout/version bump/push/tag/release.

- **October 30: approved 40 fps Metal display-link experiment built,
  default off; device test pending.** Stefan: worth trying after design
  review. New `--nfsmw_native_metal_display_40=true` (restart required)
  enables system drawables and presentation timestamps on the primary
  layer at cap 40 only. Existing guest display link/vblank, world timing,
  QoS and 60 fix retained. Bounded mailbox and render-frame leases protect
  drawable ownership; main thread does not wait for rendering, acquisition
  wait on render queue is bounded to 100 ms (no nextDrawable fallback while
  link owns layer). Cap/background transitions invalidate updates and wake
  waits. Test IPA `ios/build/NFSMW-0.5.0-metal-display-40-test.ipa`, 0.5.0/8,
  SHA-256 bad106dc1a6ee3707710c3a83df4abd8bbde2424bde09fa5c03ef7cc9cf62f43,
  UUID 4A2222D3-4733-3082-B290-16B8A8309473. Build/ZIP/deep strict
  signature passed, 104 payload shader libraries unchanged. Next: iPhone
  14 Pro Max, Balanced/1x/40, Low Power Mode off, cold launch with that
  flag and `--nfsmw_native_frame_trace=true`; 1-2 min same chase. Compare
  shown gaps/latency and [metal-display-40] logs. If improved, test menu
  30, pause/background/resume and another ProMotion device. No runtime
  validation, 40 default change, version bump, push/tag/release yet.

- **October 30: fresh 14 Pro Max 40 trace analyzed; design review pending.**
  Archived full three-launch log as
  `Debug/29 October 2026/nfsmw_iphone_14pm_3_40fps_trace.log`.
  Previous Balanced/60 chase confirmed 59.7-60.0 fps in 10 full windows.
  Latest 40 run holds 39.9-40.0 fps, 120 Hz reported, QoS boosted; 2220
  measured swap gaps mean 25.027 ms (sd .747), shown 25.020 (sd 2.870),
  recurring 20.8/20.9 and 29.2 ms pairs. Proposed default-off 40-only
  CAMetalDisplayLink drawable/timestamp integration. Stefan chose
  "Review the design first"; next: review/approval before any 40 source
  change or build. Detailed lifecycle, latency, isolation and validation
  design in TECHNICAL. No further 60 change; 0.5.1 scope unchanged.

- **October 30: D-014 default fix confirmed on iPhone 14 Pro Max.**
  Stefan ran a ~1 min chase at Balanced on the new IPA without issues;
  previously the cycling appeared sooner. User-reported result, no log
  supplied for this run. Other-device 60 fps and short 30 checks remain.
  0.5.1 scope: only this fix and 40 fps pacing (Stefan). Current 40 path
  already unpaced; requested fresh current-build 40 trace, Low Power Mode
  off, device identified. Next: analyze it before choosing a source change;
  previous wider-delay/minimum-duration experiments failed. Old unpaced
  trace confirms residual display unevenness despite near-even swaps.
  No new 40 source change/build, version bump or release yet.

- **October 30: D-014 default fix approved, built; device check pending.**
  Stefan: fix 14 Pro Max permanently first, then tackle 40 fps pacing.
  `native_renderer.mm`: 60 fps now presents when ready by default; 30 fps
  keeps scheduled presentation. Existing master `nfsmw_native_present_at_time`
  stays true; new `nfsmw_native_present_at_time_60` defaults false (both true
  restores the old 60 path for diagnosis). Trace remains default false;
  40/120, QoS, world timing and simulation unchanged. Test IPA:
  `ios/build/NFSMW-0.5.0-14pm-60fps-fix.ipa` (0.5.0 / 8, SHA-256
  d56bcfeab2324b41b0d7632999067444cfeed6ad2f12288c01be3d5eb3699208,
  UUID D7D325E7-784F-36DD-94BA-96D226418869). Build, ZIP, deep strict
  codesign passed; 104 actual payload metallibs unchanged (208 ZIP entries
  counts AppleDouble metadata too). Next: Stefan tests cold at 60 with
  the two workaround/trace arguments removed, Max first, then Balanced;
  short 30/menu check and other devices before a release. Then current
  40 fps trace (separate change after validation). No push/tag/release.

- **October 30: D-014 workaround confirmed by Stefan and follow-up log.**
  Disabling scheduled presentation removed the iPhone 14 Pro Max cycling:
  Max, native 1x/60, eleven full steady-world windows at 59.6-60.0 fps.
  Archived as `Debug/29 October 2026/nfsmw_iphone_14pm_2_present_at_time_off.log`.
  Presentation pacing is now the leading cause; no permanent source fix or
  default change made. Next if resumed: design a scoped presentation fix;
  keep the working Extra Args workaround meanwhile. October 30 discussion:
  recommend disabling scheduled presentation at 60 by default, initially
  retaining tested 30 behavior; not implemented. Trace already defaults
  off. Current 40 cap already bypasses scheduled presentation: next is a
  fresh current-build 40 trace before another pacing change. Full evidence below
  in TECHNICAL. New standing rule: archive supplied test evidence.

- **October 30: iPhone 14 Pro Max 60/~40 cycling investigated (D-014),
  no source change.** Supplied log proves it happens with Max (adaptive
  and Utility off), and Balanced stays boosted during driving. GPU time
  crosses the 16.67 ms budget; exact 40 is alternating 16.7/33.3 ms
  presentation. Neither an intentional 40 cap nor D-012's return to
  Utility. Proposed next: Max, same stationary scene if possible,
  `--nfsmw_native_present_at_time=false --nfsmw_native_frame_trace=true`,
  cold launch, 2-3 min and log to isolate presentation feedback from GPU
  cost/clock variation. Existing switches; no build required. GPU clocks
  and thermal throttling remain unmeasured. Evidence in TECHNICAL/BACKLOG.

- **October 30: Codex catch-up complete; no source change or device test.**
  Reviewed release history through `main` 4e2ac87, the checkpoint, backlog,
  technical evidence, release procedure, implementation changes and the
  local `dev-0.5` feature inventory. Latest release evidence (TECHNICAL,
  October 29 "0.5.0 published") supersedes older pending paragraphs:
  D-013 was confirmed by Stefan before publication; the final released IPA
  SHA-256 begins `a3e285c8`, not the earlier `1f2bae93` build. No new source
  work approved in this catch-up. Next: Stefan's chosen task; existing plan
  remains issue follow-up and 0.6.0 work on `dev-0.5`, with the visual bugs
  deferred. Preserved pre-existing uncommitted issue 11 analysis immediately
  below (belongs to another session; intentionally excluded from this
  session's commit), untracked `HANDOFF_CHATGPT.md`, and all sibling SDK
  modifications/submodule state. No build, push, tag or release performed.

- **October 29: issue 11 (iPhone 11 / A13, iOS 26.6, LiveContainer, 0.4.2,
  native renderer) analyzed, no code change.** Logs in Debug/29 October 2026
  (`*_issue11_iphone11_ios26.6_native_frontend_kill.*`). The app's limit is
  only 2098 MiB (LiveContainer's signing, no increased-memory-limit; Stefan's
  phone: 6144). Both runs die 2-4 s into "loading the frontend" (~630 MiB);
  nfsmw.log ends mid-line (2 s buffer), boot.txt has no fatal-signal line, so
  a SIGKILL (jetsam or watchdog), not a crash we catch. Run 2 already had 186
  MiB compressed at 626 MiB (system short of memory). Frontend alone (~1 GB
  on Stefan's phone) should fit; a race (1.6-2.2 GB) cannot, which matches
  issue 10 (iPhone 11, crash at race start). Proof needed: the user's
  JetsamEvent .ips. Proposed (awaiting Stefan): memory-pressure line in
  boot.txt + log flush, and a low-memory profile when the limit is < ~3 GB.

- **October 29: 0.5.0 (build 8) released: `main` pushed, tag v0.5.0,
  GitHub release with `NFS-Most-Wanted-0.5.0.ipa` (Stefan's go).** Earlier: Today's 0.4.3 work released as 0.5.0 (Stefan); `dev-0.5` work
  is now 0.6.0. `ios/build/NFS-Most-Wanted-0.5.0.ipa` (SHA-256 1f2bae93...),
  also on the iCloud Desktop. Remaining visual bugs (D-006 leaves picture,
  loading twitch, race-end HUD zoom) deferred to a later session; D-013
  (post-race photo: controls stayed, no touch) fixed for 0.5.0 at Stefan's
  request, untested. Next: issue replies (Stefan), then 0.6.0 on `dev-0.5`.

- **October 29: 0.4.3 Performance setting (D-012), local main, not pushed.**
  Threads stay boosted while driving (no Utility in the world), faster late
  detection, launcher Graphics "Performance": Eco (all Utility; default with
  Battery mode) / Balanced (default; original behaviour with 6+ efficiency
  cores, the M-series iPads) / Max (no Utility); audio and vblank threads
  untouched. Issue templates for bug and performance reports.
  `ios/build/NFS-Most-Wanted-0.4.3.ipa` (SHA-256 5f467ae5...), also on the
  iCloud Desktop. Next: Stefan's run and the 15 min A/B against the previous
  0.4.3 IPA (612b799a).

- **October 29: IPA170 `ios/build/NFSMW-ipad-thumbs-170.ipa` (IPA167, the ring fix confirmed in IPA168, iPad DRIVE layout in the thumb zones with Stefan's D-pad spot; local main,
  not pushed), not yet run.** Stefan approved 120 Hz simulation by default
  with its switch removed (camera logs: at sim 60 the first ~15 s of a
  pursuit moved the world on 2 of 3 frames; TECHNICAL Oct 29) and the
  pursuit heat ring moved with the heat badge. Ring and circle prompt
  confirmed by Stefan on iPad and iPhone (IPA168); iPad layout his (IPA170).
  Done for now; not pushed.
- **October 29: D-011 diagnostic build `ios/build/NFS-Most-Wanted-0.4.2-diag1.ipa`
  on local branch `diag-ios26-native-crash` (off `main` 0.4.2; not for
  `main`, not pushed).** For the iOS 26 crash in AGX `drawIndexedPrimitives`
  on the first native frames (GitHub report): Metal API validation from the
  start of `main()` (stderr into `Documents/logs/native_diag.txt`) and a
  synced per-draw state log of the first 5 frames with `MISMATCH` flags.
  Off with `--nfsmw_diag_metal_validation=false` /
  `--nfsmw_diag_draw_log=false` in extra_args.txt. Stefan's iOS 27 smoke
  test passed (validation active, 0 MISMATCH). The user's iOS 26 run with
  validation on did not crash (17 fps). With validation off it crashed;
  cause found (iOS 26 reuses the encoder address, the per-encoder state
  caches compare addresses; TECHNICAL Oct 29). Fix approved and built:
  `ios/build/NFS-Most-Wanted-0.4.2-diag2.ipa` (fix + draw log, validation
  off by default; also on the iCloud Desktop). Confirmed on iOS 26 (Oct 29).
  Then (Stefan's go) only the fix went onto `main` as 0.4.3 (build 7):
  `ios/build/NFS-Most-Wanted-0.4.3.ipa`. Also in 0.4.3 (approved): Audio
  switch "Play sound in silent mode" (default off; Stefan: works) and
  LSSupportsGameMode (untested, no free sideload slot).
  Minimap fix (approved, Oct 29): IPA138 `ios/build/NFSMW-minimap-138.ipa`,
  confirmed by Stefan on iPhone (TECHNICAL Oct 29, BACKLOG minimap entry).
  Custom HUD (D-006, Stefan approved the log-first plan Oct 29): IPA139
  `ios/build/NFSMW-ui-log-139.ipa` logs every screen up in the world
  (`[ui] screens:`) and each one's object tree (`[ui-tree]`). Next: Stefan
  ran it on iPad (bust TV overlay = BUSTED_OVERLAY.fng, race-end one =
  InGamePhotoMaster.fng). IPA140 (size 1 while they are up): bust fixed,
  HUD flashes at size 1 at a race's end. IPA141
  `ios/build/NFSMW-hud-fit-full-141.ipa`: those packages and the asphalt
  picture drawn at size 1 and the full width (iPhone): photo screen text
  missing and a growing image, reverted at Stefan's request. IPA142
  `ios/build/NFSMW-hud-pursuit-142.ipa`: IPA140's overlays plus the
  pursuit pieces ("PURSUIT CTS" with the speedometer, infraction lines
  moved again after the game's script). Next: Stefan tests the chase at
  70%. IPA142: PURSUIT CTS right, infraction rows flash; IPA143
  `ios/build/NFSMW-hud-rows-143.ipa` moves such rows' children instead
  (confirmed by Stefan). On the iPhone it lost the busted/evade marker and
  the loading screen / asphalt picture bled on all sides (HD title-safe and
  wide scene); IPA144 fixed the bar, nearly the loading screen, and broke
  the pause menu (asphalt picture fit). IPA145
  `ios/build/NFSMW-hud-fade-grow-145.ipa`: asphalt picture left alone,
  fades 10% larger: no bleed on either device, the loading pieces twitch
  a little (known issue). IPA146 `ios/build/NFSMW-hud-backdrop-146.ipa`:
  the pause backdrop scaled as whole groups (pause fixed). IPA147
  `ios/build/NFSMW-hud-photo-147.ipa`: the results' leaves picture
  (InGamePhotoMaster image) covers the iPhone screen; the song box is put
  back under the pause menu: the leaves were not that image, removed in
  IPA148 `ios/build/NFSMW-hud-148.ipa`; IPA149
  `ios/build/NFSMW-hud-backdrop-149.ipa` draws the backdrop 15% larger for
  the leaves' iPhone margins: no effect, removed. Customize HUD editor
  (Stefan's spec, outlines): IPA150 `ios/build/NFSMW-hud-editor-150.ipa`
  works on the iPhone (Stefan; outlines match the drawn HUD). Stefan
  (Oct 29): HUD done for now. Touch controls (Stefan's plan, Oct 29, 4
  steps, each its own IPA; BACKLOG "Touch controls overhaul"): step 1,
  steering modes, IPA151 `ios/build/NFSMW-touch-steering-151.ipa`, built,
  not run; step 2, icons / hit areas / idle dimming, IPA152
  `ios/build/NFSMW-touch-look-152.ipa` (also on iCloud Desktop), built,
  not run; step 3 first part, menu swipe/tap, IPA153
  `ios/build/NFSMW-touch-menus-153.ipa` (steps 1-3; on iCloud Desktop
  instead of IPA152), built, not run; Stefan tests them together
  (TECHNICAL Oct 29). Step 3 still open: a tap on a prompt presses that
  button (needs each screen's prompt positions). Stefan (Oct 29): IPA153
  all works as expected. He asked for D-pad buttons (map, SMS, Blacklist,
  enter/engage, race/pursuit details) shown only when they apply: IPA154
  `ios/build/NFSMW-touch-dpad-watch-154.ipa` (iCloud Desktop) has the four
  buttons always shown plus a `[hud-watch]` diagnostic to find the HUD's
  signs of free roam / race / pursuit / event circle. Stefan's IPA154 run
  (`Debug/29 October 2026/ipa154_hud_watch_iphone/`) gave the circle
  prompt and the race markers: IPA155 `ios/build/NFSMW-touch-context-155.ipa`
  (iCloud Desktop) shows ENTER only in a circle, MAP/SMS only outside
  races, and fixes the log bloat; built, not run. Pursuit not seen in the
  run (buttons as in free roam). Circle prompt ring fix (Stefan, "now"):
  IPA156 `ios/build/NFSMW-hud-prompt-156.ipa` (iCloud Desktop, includes
  IPA155), built, not run. Stefan asked for an Extra arguments field in
  the launcher: IPA157 `ios/build/NFSMW-extra-args-157.ipa` (iCloud
  Desktop, includes IPA156), built, not run. Next: his pursuit run with
  `--nfsmw_hud_watch=true`. Stefan's IPA157 pursuit run (challenge
  series; `nfsmw_ipa157_pursuit_iphone.log`, `ipa157_pursuit_IMG_4066/67`):
  context "race" in the pursuit (only LIST shown, which does nothing
  there), map missing, DRIVE controls flashed at start; up = details in
  races and pursuits. IPA158 `ios/build/NFSMW-touch-pursuit-158.ipa`
  (iCloud Desktop): STATS on up in race/pursuit events, MAP always, held
  controls kept through context changes, PAD layout at start. Open: the
  infraction ring at the top middle (where the game puts it; to compare
  with Custom HUD off), free-roam pursuits untested. Stefan's IPA158 runs
  (`nfsmw_ipa158_a_iphone.log` free-roam pursuit, `_b_` challenge
  pursuit with Custom HUD off): free-roam pursuit kept free-roam buttons,
  no map in races or challenge pursuits; the infraction ring is at the
  same place with Custom HUD off (the game's own). IPA159
  `ios/build/NFSMW-touch-actions-159.ipa` (iCloud Desktop): pursuit
  detection (FD9152B1), map rules, the four D-pad buttons as one group in
  the touch editor, hud_layout never empty. Stefan's IPA159 run
  (`nfsmw_ipa159_pursuit_iphone.log`, `ipa159_IMG_4068-4072.png`): editor
  showed a plain D-pad, SMS screens kept DRIVE controls, free-roam pursuit
  not detected (FD9152B1 not shown in it), same icon for race and shop
  circles, no darkened backdrop on map / Blacklist / SMS (pause has it).
  IPA160 `ios/build/NFSMW-touch-actions-160.ipa` (iCloud Desktop): editor
  draws the four, SMS packages as menus, `[hud] circle prompt` words
  logged for the icon. Asked Stefan: a free-roam pursuit with
  `--nfsmw_hud_watch=true`, and the backdrop with Custom HUD off. Stefan:
  backdrop present with Custom HUD off (BACKLOG, ours); his layout as the
  default for all, adapted to iPad; editor in the in-game options. His
  IPA160 run (`nfsmw_ipa160_circles_pursuit_iphone.log`): pursuit sign =
  the busted/evade bar labels, circle icon word. IPA161
  `ios/build/NFSMW-touch-defaults-161.ipa` (iCloud Desktop): Stefan, all
  three work. CAM / PAUSE covered the mirror: IPA162
  `ios/build/NFSMW-touch-top-row-162.ipa` puts PAD, CAM, PAUSE, HIDE in
  one row at the top (his choice): Stefan "looks fresh". Step 4, drag
  race layout: IPA163 `ios/build/NFSMW-touch-drag-163.ipa` (iCloud
  Desktop): works (Stefan); nitrous over gas, brake in its place. Step 3b
  (tap a button hint): hints found by name/shape, IPA164
  `ios/build/NFSMW-touch-hints-164.ipa` logs `[touch-hint]` (texture per
  hint) to build the texture -> button table; only BACK_BUTTON = B known.
  Stefan's IPA164 taps (`nfsmw_ipa164_hint_taps_iphone.log`) gave the
  table; IPA165 `ios/build/NFSMW-touch-hints-165.ipa`: "most if not all
  work" (Stefan). World map unusable (no cursor, zoom, categories): IPA166
  `ios/build/NFSMW-touch-map-166.ipa`: works (Stefan). Stefan (Oct 29):
  touch controls done for now; CHANGELOG 0.4.3 touch entries merged into
  one "Touch controls, redesigned" entry and README Features / Controls
  rewritten. Open from this thread: the missing menu backdrop with Custom
  HUD on (BACKLOG). Then: the on-screen touch controls, then
  the game-timing judder; push/release of these local commits on his go. Known issues
  in TECHNICAL Oct 29 (IPA148). Next after the HUD (Stefan): each HUD element movable from the
  pre-launch and in-game menus; then the timing thread, then touch
  controls.
  Still open: iPhone side bars on the bust overlay and asphalt
  picture, the iPad loading screen's short bleed, the judder Stefan felt
  (not in the pacing log) (TECHNICAL Oct 29, D-006).
  Next: Stefan's device check,
  then tag/push/release on his go (docs/RELEASING.md); ask the issue 4/7
  reporters to try it.

- **October 28: 0.4.2 prepared on local branch `touch-overlay-native` (off
  `main`), not merged, tagged or pushed (waiting for Stefan).** Fixes: the
  60 fps world judder (D-005: the game's main loop timed frames unevenly; each
  frame now gets one display period, `patch_game_frame_ticks.py` +
  `frame_clock.cpp`, cvar `nfsmw_frame_ticks`, IPA124 confirmed on iPad and
  iPhone), touch controls drawn into the native frame (IPA111), UTF-16
  extra_args.txt (IPA113). Day's dead ends removed (TECHNICAL Oct 28 cleanup).
  Later the same evening: 40 fps (120 Hz simulation, frames shown when
  ready at the 40 cap), Battery mode 30/40, menu/warm 30 at the 40 cap,
  Custom HUD switch; RC7 built. Stefan (via the coordinator): before 0.4.2
  ships, the Black Edition save fix (thread "Repair saves damaged by Black
  Edition change", same branch) is added and tested. Next: RC7 checks, then
  that fix, then merge/tag/publish on Stefan's go.
  Oct 28, damaged-career fix (GitHub issue 8, BACKLOG D-010): cause is a
  player ID check in the save loader, not Black Edition. IPA134
  `ios/build/NFSMW-save-id-136.ipa` loads such careers with the device's ID;
  the CE05 change (IPA132) is reverted. IPA137 also puts the side file
  back when only the overflow slots match. Confirmed by Stefan (Oct 29):
  the user's NAME loads with its cars. Next: 0.4.2 release on Stefan's go.

- **October 27: 0.4.1 released to GitHub (Stefan: "push it", iOS 18 marked
  experimental).** `release-0.4.1` fast-forwarded into `main`, tagged
  `v0.4.1`, both pushed. Release IPA `ios/build/NFS-Most-Wanted-0.4.1.ipa`
  = IPA110 (no code change after it), SHA-256
  f07918eda76d983728fd6c9954ea9fb6126cdd82bcd817cfde6633c83d905526. README:
  iOS 18 experimental. Next: Stefan publishes the GitHub release from
  the tag; 0.5 continues on `dev-0.5` (rebase or merge 0.4.1 into it, and
  build it with the iOS 18 target and shader set).
- **October 27: 0.4.1 fixes on local branch `release-0.4.1` (off `main`,
  e0151ce; Stefan approved both, ported from SpeedBreaker, GPL-3.0). Not
  pushed. IPA109 (`ios/build/NFSMW-0.4.1-audio-pacing-109.ipa`, version
  0.4.1 / 5) awaits Stefan's device test.** (1) D-004 engine sound fade:
  `ios/src/game_audio_budget.cpp` stops EA SND's mixer CPU budget from
  expelling voices (cvar `nfsmw_ea_cpu_budget`, default off = fix on).
  (2) D-005 pacing: SDK patch `tools/ios/patch_ios_vblank_realtime.py`
  (in `prepare_sdk.py`, applied) gives the "GPU VSync" thread Mach
  real-time priority (cvar `ios_vblank_realtime`, default on); the existing
  present-at-time pacing (`nfsmw_native_present_at_time`, already on at the
  30/40/60 caps below the display rate, off at 120) gets a watchdog that
  turns it off for the session when over 60 of 300 paced frames are shown
  4 ms+ early or never. Unchanged: `ios_vblank_lock_60` (on),
  `ios_display_120_at_60` (off); Battery mode only changes the cap, which the
  pacing follows. Next: Stefan's long race (engine sound; look for
  `[ea-budget]` and `[ios-vblank] real-time priority ... set` in the log) and
  60 fps evenness on the iPad and iPhone 17 Pro Max; then release 0.4.1 per
  RELEASING.
- **October 27: IPA109 iPhone run ok (TECHNICAL). Stefan approved two more
  0.4.1 items: GitHub #5 (D-010) and iOS 18 support (D-011), in IPA110
  (`ios/build/NFSMW-0.4.1-ios18-110.ipa`).** Build note: the build dir was
  reconfigured with `cmake --preset ios` (target 18.0, full rebuild) and the
  shader cache rebuilt with `sh tools/native/build_shaders.sh -` (IOS_MIN
  default now 18.0); the iOS 26 libraries are kept in
  `~/Library/Caches/nfsmw-ios/shaders/lib.ios26-ipa109`. Next: Stefan checks
  IPA110 on iOS 27; iOS 18 testers from GitHub; README at release.
- **October 27: README rewritten for 0.4.0 on `main` (Stefan asked; draft
  approved before commit).** It still described 0.1.0 (MoltenVK only, no save
  manager). Now: iOS 26+ stated at the top, native Metal renderer, save manager
  and iCloud sync, Xbox 360/PC save import, launcher tabs and in-game options,
  battery work, known issues from BACKLOG (D-003/4/5/6, red movie frame) and
  0.5.0 plans. Build, How it works, Credits and Legal unchanged apart from the
  pointer to AGENTS.md. No measured numbers added beyond those in CHANGELOG.
- **October 27: 0.4.0 built and tagged (Stefan approved steps 1-4 of
  RELEASING; he publishes the GitHub release himself).**
  `ios/build/NFS-Most-Wanted-0.4.0.ipa`, SHA-256
  685328f8ceb4c96fc2a2e9cace64ceacc1c0cd59926752071903f12efbee54ca. Next:
  Stefan creates the release from tag v0.4.0; then 0.5 on `dev-0.5`.
- **October 27: Stefan's tester confirmed Xbox 360 save import; Stefan
  approved the push: `frame-pacing-60` pushed to origin (new branch). Not yet:
  merge to `main`, version bump, tag, GitHub release (docs/RELEASING.md).**
- **October 27: PC save import added to 0.4.0 (Stefan approved).**
  Brought over from `dev-0.5` (converter, Import hook, README credit) without
  the 0.5 Extra Options. IPA108 (`NFSMW-pc-save-import-108.ipa`). Build note:
  `ios/generated/` is shared by both branches; the 0.5 `heat` edit was taken
  out of `nfsmw_recomp.51.cpp` for this build. Back on `dev-0.5`, run
  `python3 tools/ios/patch_game_extra_options.py` before building.

- **October 27: 0.5.0, branch `dev-0.5` (local).** PC vs Xbox 360 file
  comparison done (TECHNICAL, Oct 27; BACKLOG "PC mods"). Stefan: Extra
  Options first. Feature list of both PC code mods with estimated effort:
  [MOD_FEATURES.md](MOD_FEATURES.md). Stefan approved the first batch.
  IPA104 (`NFSMW-extra-options-104.ipa`): Speedbreaker, infraction speeds,
  impound strikes, heat override (launcher Extras tab). Untested. Next:
  Stefan tests IPA104; starting cash and the bounty fixes still to find.
  IPA105 (`NFSMW-pc-saves-105.ipa`): PC save import (converter
  `ios/src/save_convert.cpp`): crashed loading the save (wrong byte order
  of a count); IPA106 loaded it but
  crashed after My Cars (a template car handle left in); IPA107
  (`NFSMW-pc-saves-107.ipa`) converts those too: works (Stefan, first
  look). Next: Stefan's go to bring it to `frame-pacing-60` for 0.4.0. Stefan (Oct 27): if it
  works, it goes into 0.4.0 too (bring those files and the import hook over
  to `frame-pacing-60` only then).
- **October 27: save manager rework, step 1, IPA98
  (`NFSMW-save-sync-98.ipa`), branch `frame-pacing-60` (local).** Stefan
  approved a 3-step plan: (1) the record-pool extras file is part of the save
  everywhere and saves go to iCloud right after the game writes them (D-008);
  (2) a simpler save screen; (3) import of .zip, Xenia folders and Xbox 360
  CON files. Step 1 confirmed by Stefan (sync works). IPA99
  (`NFSMW-save-cloud-delete-99.ipa`): sync 3 s after a save; delete for saves
  only in iCloud (confirmed by Stefan). IPA100
  (`NFSMW-save-redesign-100.ipa`): step 2, one Careers list. Untested. Next:
  IPA100 confirmed by Stefan. IPA101 (`NFSMW-save-import-101.ipa`): step 3,
  import of .zip, Xenia folders, Xbox 360 CON files and bare save files; and
  120 Hz simulation off by default, its switch in Advanced. Untested. Next:
  Stefan tests an imported internet save. IPA102
  (`NFSMW-achievement-sync-102.ipa`): achievements merged across devices
  through the iCloud folder (D-009), confirmed (Vic shows after the manual
  restore). Import: Stefan's tester will test it. Save progress decoding
  deferred by Stefan. IPA103 (`NFSMW-motion-blur-103.ipa`): Motion blur
  switch (launcher and in-game, live; key `motion_blur`, cvar
  `nfsmw_motion_blur`, default on). Untested. Next: Stefan compares the
  60 fps judder (D-005) with motion blur on and off; then cars/career/
  challenge progress in the save list.
- **October 26 (night): in-game options menu, IPA67
  (`NFSMW-ingame-options-67.ipa`), branch `in-game-options` (local, off
  `battery-optimization`; Stefan approved the design: gear for touch, L3+R3
  for controllers, graphics settings only).** Built, not yet run on device.
  Next: Stefan's device test (checklist in TECHNICAL, Oct 26 in-game
  options); then Extra Options in the menu once they are complete.
  IPA67 live settings confirmed by Stefan. **IPA68
  (`NFSMW-battery-30fps-68.ipa`): Battery mode also sets 30 fps** (his
  request); not yet run. **IPA69 (`NFSMW-reflection-size-69.ipa`): adds the
  "Reflection and mirror resolution" setting (launcher and in-game, live).**
  Not yet run. Open check: launcher shows the menu's values after a relaunch.
  Stefan (Oct 26): the in-game menu is good enough for now; branch
  `in-game-options` stays local (not merged or pushed). Next QoL items are
  separate: movable HUD, save manager, pre-launch menu redesign.
- **October 26: movable/resizable HUD, step 1, IPA70
  (`NFSMW-hud-layout-70.ipa`), branch `claude/project-thread-w9st63` (local,
  off `in-game-options`).** Stefan approved the plan: step 1 = HUD size plus
  minimap and speedometer position as settings (launcher and in-game, live);
  step 2 = a drag/pinch editor on screen. Built, not yet run. Next: Stefan's
  device test (TECHNICAL, Oct 26 HUD layout); then step 2.
  IPA70 on device (Stefan): size and positions work and stay put across
  races, but the size moved the sides inward/outward, and the race
  position/progress element moves with the speedometer. **IPA71
  (`NFSMW-hud-anchors-71.ipa`): each side now scales about its own middle;
  logs the right group's layout** to find that race element. Not yet run.
  IPA71 on iPad (Stefan): the size broke the sides apart (they are more
  objects than the two groups), and speedometer up pushes the race standings
  off the top. **IPA72 (`NFSMW-hud-tree-72.ipa`): size back to IPA70's;
  logs the HUD package's whole object tree (`[hud-tree]`)** for per-element
  positions. Not yet run. IPA72 log: no `[hud-tree]` (my bug: skipped
  while every HUD setting is at default). **IPA73 (`NFSMW-hud-tree-73.ipa`):
  the tree logged once per HUD package whatever the settings; `[post]` log
  line for the post-processing switch** (Stefan: it does nothing, and it is
  not in the in-game menu). Not yet run. IPA73 log: tree mapped (TECHNICAL);
  post-processing hook runs and clears the byte, yet nothing changes.
  **IPA74 (`NFSMW-hud-elements-74.ipa`): minimap, speedometer and race info
  (top right) move on their own; new Race info rows.** Size stays the whole
  HUD about the middle (IPA70). Not yet run. IPA74 (Stefan): elements move
  correctly; he wants the size to keep the default margins, and the safe
  zone as its own slider. **IPA75 (`NFSMW-hud-safe-zone-75.ipa`): each
  element scales about its own middle; new HUD safe zone (80-110%).** Not
  yet run. IPA75 (Stefan): still parts of each element (dial face, ring,
  heat icon) do not keep the margins. **IPA76 (`NFSMW-hud-scale-76.ipa`):
  the pieces' offsets no longer change when a pause screen comes and goes.**
  Not yet run. IPA76 (Stefan): pieces stay together now, but the margins
  still change (closer to the middle at min, to the edges at max) and the
  mirror goes half off the top at max. **IPA77 (`NFSMW-hud-corners-77.ipa`):
  each element keeps its outer corner (not its middle); the mirror's frame
  and picture keep their top margin.** Not yet run. IPA77 (Stefan): works
  in free roam; crashed when a race started. **IPA78
  (`NFSMW-hud-race-fix-78.ipa`): the HUD pieces are found again when a new
  HUD replaces the old one; pointers checked before use.** Not yet run.
  IPA78 (Stefan): works; at the smallest size the picture bleeds through
  the black loading screen before a race. **IPA79 (`NFSMW-hud-fade-79.ipa`):
  the size is not applied while a full-screen fade package is up.** Not yet
  run. IPA79 (Stefan): loading screen fine, but in the race the HUD was at
  full size and pushed off the screen (FadeScreen.fng stays pushed).
  **IPA80 (`NFSMW-hud-fade-hold-80.ipa`): the size is held back for 3 s
  after the world starts, a fade comes or a new HUD is built.** Not yet run.
  IPA80 (Stefan): works as described, but the 3 s at full size do not look
  nice. **IPA81 (`NFSMW-hud-fade-fit-81.ipa`): no hold; the fade package's
  full-screen images are drawn at full size whatever the HUD's size.** Not
  yet run. IPA81 (Stefan): still bleeds; the log shows the black screen is
  inside a group. **IPA82 (`NFSMW-hud-fade-fit-82.ipa`): wide images in
  groups too.** Not yet run. IPA82 (Stefan): bleed shorter, still at the
  loading screen's end; the song box (EA Trax) ignores the safe zone; the
  radar detector's arcs sit too low. **IPA83 (`NFSMW-hud-overlays-83.ipa`):
  size 1 while the black screen is fully up; EA_Trax.fng kept at the safe
  zone; the middle group's top pieces go with the mirror, bottom ones with
  the bottom edge.** Not yet run. IPA83 (Stefan): the whole race HUD at full
  size and off screen (the fade's alpha stays 255 all race). **IPA84
  (`NFSMW-hud-overlays-84.ipa`): that hold removed; song box and radar arcs
  kept.** IPA84 (Stefan): all good apart from the short bleed; **HUD
  declared finished for now (Stefan, Oct 26): functional, not its final
  form; kept in the backlog.** Next: post-processing. **IPA85
  (`NFSMW-no-post-85.ipa`): Post-processing off now skips the game's post
  chain (bloom, colour filter, vignette); the switch is in the in-game menu
  too (live).** IPA85 on iPad (Stefan): looks as no post-processing should.
  Both QoL items of this branch done; branch stays local, not pushed.
  Next (Stefan): the uneven 60 fps frame pacing, on local branch
  `frame-pacing-60` (from this one). **IPA86 (`NFSMW-pacing-60-86.ipa`): the
  60 cap's guest vblank locked to the display refresh like 30/40 (cvar
  `ios_vblank_lock_60`, default on; A/B with Extra Args
  `--ios_vblank_lock_60=false`) and a log line per off-grid frame.** IPA86
  (Stefan): no change; the stutter pairs follow the FPS counter's 0.5 s text
  updates and vanish with the counter off. **IPA87
  (`NFSMW-fps-counter-87.ipa`): the counter no longer masks or re-frames on
  each update.** IPA87 (Stefan): worse, double text. **IPA88
  (`NFSMW-fps-in-frame-88.ipa`): the counter drawn into the game's frame by
  the native renderer; the label hidden.** IPA88 (Stefan): counter pairs
  gone; counter blurry at 1x; race start still choppy. **IPA89
  (`NFSMW-sharp-counter-89.ipa`): counter at the frame's resolution.** Next:
  Stefan's Instruments trace of a race start on IPA89. Trace: the screen gets
  an even 60; Stefan: the whole screen judders at the race start. **IPA90
  (`NFSMW-swap-periods-90.ipa`): diagnostic `[native] swap periods`; counter
  back at screen scale.** IPA90: swap periods even; choppiness random through
  the race. **IPA91 (`NFSMW-120hz-at-60-91.ipa`): the 60 cap asks the display
  for a steady 120 Hz (`ios_display_120_at_60`).** IPA91: delivery perfect
  (every frame 16.7 ms apart), still "skipping frames": content-side. Next
  (Stefan OK'd): find the game's frame-time code. **IPA92
  (`NFSMW-repeated-frames-92.ipa`): logs frames that repeat the previous
  picture (`[native] content`).** IPA92: none repeat; the remaining
  choppiness is unexplained and parked. **IPA93
  (`NFSMW-pacing-cleanup-93.ipa`): counter fix kept; 120 Hz at 60 and the
  frame-timing logs off by default.** Oct 27: 120 Hz simulation removes the
  judder at 60 fps at no measurable CPU cost. **IPA94
  (`NFSMW-sim-120-default-94.ipa`): 120 Hz simulation by default.** Next: a
  longer play test. Next: a sharp counter on
  its own layer (backlog D-005). New D-006
  (race-finish background letterboxed).

- **October 26 (evening): iPhone Time Profiler on IPA63 (police chase, 1x/40).**
  App CPU ~0.8 core at 37.8 fps: game threads ~45%, GPU Commands 155 ms/s
  (`Record()` ~2.9 ms/frame), render queue ~180 ms/s. No single large waste
  left; top lines are per-draw cache lookups (attribute ~23 ms/s, GPU buffer
  ~17) and `adaptive_qos::OnMainLoop` 8 ms/s (an atomic per call). Proposals
  A-D in TECHNICAL (Oct 26, Time Profiler), together ~5-6% of app CPU.
  **IPA64 (`NFSMW-lookup-caches-64.ipa`): A-C built (D dropped, no saving)
  and profiled:** attribute misses 18% -> 3%, both cache maps' shares halved
  or better; `OnMainLoop` now only call overhead. ms/s not comparable (IPA63
  window boosted on P cores, IPA64 mostly Utility on E cores). Next, if
  wanted: the battery-% chase on IPA64; cool-start A/B (IPA53 vs IPA52) open.
- **October 26: iPad GPU cost per setting (IPA64 test race).** GPU ms/frame:
  1x/60 5.9, 1.5x/60 10.2, 2x/60 14.2 (~85-90% busy), 1.5x/120 6.1 at a
  higher clock (the heat). All held their cap. Lead: the six 320x256 passes
  scale with resolution (TECHNICAL, Oct 26 iPad race). They are the
  environment cube: **IPA65 (`NFSMW-reflections-1x-65.ipa`) keeps them at 1x**
  (`--nfsmw_native_scale_reflections`, default false). IPA65 run: did not
  apply (the cube is filled by 2D face resolves); fixed in **IPA66
  (`NFSMW-reflections-1x-66.ipa`): applied on iPad 1.5x/60, ~1 ms/frame GPU
  saved (~10%); the rear-view mirror (it shows the cube) is softer.**

- **October 26 (later): sun fixed in IPA63 (`NFSMW-sun-fix-63.ipa`),
  confirmed by Stefan on iPad (fades with cover).** The game ends each sun query at begin-0x20; answers were filed under
  the begin address and some unmarked ends opened runaway queries. Test: sunny
  weather, sun behind overpasses/buildings should hide it; the stats line
  should show answers of 0. Halo around thin objects and the bus-terminal glass
  are parked by Stefan (Vulkan shows them too; maybe the 360's own look).

- **October 26: the environment cube is not black.** The rear-view mirror is
  the cube times a brightness (ps 8436534c) and shows the scene, so the black
  IPA60/61 snapshots are a readback artefact; the battery-switch A/B below is
  dropped. Glass: the cube's real content is too strong. Sun: flicker fixed,
  but never hidden (0 of ~860k answers are 0). Plane run: ~2+ h LPM, 72%->35%.
  IPA62 built (approved, not run): SNAP frames log each occlusion query's
  draws and counts; `--nfsmw_native_test_no_envcube_world=true` gives world
  shaders (not car paint, not the mirror) a black cube. Test: SNAP with the sun
  behind an overpass; drive past the bus terminal with and without the switch.
  TECHNICAL Oct 26.

- **October 25 (late): billboard flicker and glass parked by Stefan.** Seen
  on Vulkan too and since the start. Negative: polygon offset (IPA56, kept),
  shader invariance (IPA57, removed), exact shader math (IPA58, kept: no GPU
  cost). Found: the environment cube faces (320x256 pass) and the 200x90 blur
  render all black in every snapshot, even with no depth test (IPA61); glass
  and other reflective draws read that cube. Untested next step: A/B with
  `--nfsmw_battery_optimizations=false --nfsmw_native_constant_copies=false
  --nfsmw_native_transform_copies=false` (Stefan doubts it; the terminal glass
  may also be the 360's own look). Tools: `--nfsmw_native_dump_manual=true`
  (SNAP button, IPA60). Latest build IPA61 (`NFSMW-cube-test-61.ipa`).

- **October 25: IPA55 (`NFSMW-texture-flips-55.ipa`) run.** While the billboard
  flashed, 0 textures changed fetch constant, size/mips or content between
  frames: not the texture cache. Stefan: it is a dark grey layer flickering
  (z-fighting). **IPA56 (`NFSMW-depth-bias-56.ipa`) built, not run:** applies
  the game's polygon offset, logs `[native] depth:` counts, drops the texture
  log and repeated settings lines; Stefan: still the same. **IPA57
  (`NFSMW-invariance-57.ipa`) built, not run:** shaders rebuilt with
  `-fpreserve-invariance`: still the same. **IPA58 (`NFSMW-exact-math-58.ipa`)
  built, not run:** shaders with exact math (`-fno-fast-math
  -ffp-contract=off`). Next: the same billboard, and GPU ms.

- **October 25: IPA54 sun test log read.** 6-7 occlusion queries per line,
  none ever answered 0, counts 65k-7.8M: the game always sees them as visible,
  so a too-low count is ruled out. If the sun still never shows in open sky,
  next: find which query is the sun and how the game uses its count (TECHNICAL
  Oct 25).

- **October 24 night: sun flicker traced to the occlusion answer; IPA54 built
  (`NFSMW-sun-occlusion-54.ipa`), not run.** Stefan's IPA53 extra-args test:
  sky reorder off did not help, native occlusion counting on stopped the flicker
  and hides the sun behind geometry. IPA54 makes `nfsmw_native_occlusion` default
  on and logs the sun query answers. **Next: an IPA54 run in sunny weather,
  checking the sun appears in open sky (log line `occlusion queries`).** Audio
  glitches and flashing textures recorded in BACKLOG (D-004, new entry).

- **October 24 night: IPA53 run looked worse by battery % (~30-40 %/h) and
  hotter, but its counters are all equal or better than IPA52 (CPU ~100% vs
  127%, fewer ring timeouts, 39.95 fps, 2 in-play hitches); it was the 7th
  back-to-back run.** Treated as inconclusive. Next: cool-down A/B (IPA53 default
  vs `--ios_ring_wait_ms=8 --nfsmw_native_fast_index_fingerprint=false`, i.e.
  IPA52 behaviour) on a fresh, cool phone. Sun flicker/occlusion updated in
  BACKLOG.

- **October 24: IPA53 (Stefan approved backlog 2 and 3). Built, not run.** Ring
  wait capped at half a frame of the fps cap (`--ios_ring_wait_ms=0` default;
  12.5 ms at 40, 8.3 at 60, 4.2 at 120, follows Battery mode's 30); index-buffer
  fingerprint in four lanes (`--nfsmw_native_fast_index_fingerprint=true`).
  `Record()` itself not changed: needs a line-level profile first. **Next: the
  same police chase on IPA53 (~10 min, battery %, log) vs IPA52's ~22 %/h.**

- **October 24 night: IPA52 gives the first clear iPhone saving without Low Power
  Mode.** Police chase 23:11-23:22, Low Power Mode off, 1x/40: 79 -> 75% = ~22 %/h
  (16-27 with +-1 point) vs IPA51 ~30, IPA48 ~33, Low Power Mode ~17; 39.96 fps,
  6 hitches, thermal nominal throughout; Stefan: cooler than the old Low Power
  Mode runs. Ring-space waits 104/s (was 709/s), CP yields 164/s (was 908/s).
  One run: needs a repeat and the iPad. Next: wider test, then the ranked list in
  BACKLOG (frame-relative ring cap first).

- **October 24: IPA52 cuts the two polls found in the pursuit trace (Stefan
  approved). Built, not run.** `--ios_ring_wait_ms=8` (was 1): the main thread's
  ring-space wait sleeps up to 8 ms; the CP already wakes it exactly when it
  publishes the read pointer. `--ios_cp_idle_spins=4` (was 64): GPU Commands
  yields 4 times, not 64, before its event wait. Logs `[ring-wait]` and
  `[cp-idle]` every 10 s. Main-loop 0.14 ms sleeps left alone (game timing).
  **Next: Stefan's pursuit (smoothness) and ~10 min / test race drain on IPA52
  vs IPA51, with the log.**

- **October 24 evening: iPhone traces on IPA51** (TECHNICAL Oct 24 evening).
  Power Profiler, Low Power Mode off, race: ~42.5 %/h estimated system drain; the
  Low Power Mode arm could not be recorded (Low Power Mode drops the wireless
  link). Pursuit System Trace: Main XThread blocked ~78%, in ~709 short lock
  waits/s (mostly timeouts, ~103 wakes/s from GPU Commands) plus 236 tiny sleeps/s
  in the main loop; GPU Commands yields ~908 times/s in `WorkerThreadMain`.
  **Proposed (not approved): replace these polls with real blocking waits.**

- **October 24: IPA51 is the test baseline (not a release candidate).** Defaults:
  `--ios_display_match_cap=false` (old 60/120/60 Hz), adaptive boost back to IPA48
  (`user_initiated`, holds up to 240 s, all guest threads + render queue); the
  IPA49/IPA50 alternatives stay as switches. Built, not run. **Next: Stefan's
  wireless profiling on IPA51: Power Profiler pair of the full test race, Low
  Power Mode off then on, and one Time Profiler (Record Waiting Threads) in a
  pursuit.** 0.4.0 held (working rules).

- **October 24: IPA50 display match saved nothing (~30 %/h, as IPA49).** iOS gave
  the link 30 Hz for a 40 Hz request and presented on a 60 Hz pattern (the same
  2/4-refresh gaps as Low Power Mode), so the display matched Low Power Mode's and
  drain did not move. Neither QoS (IPA49) nor the refresh rate (IPA50) explains Low
  Power Mode's halving; what remains is its clock caps (CPU time per second was
  ~198% of a core in Low Power Mode vs ~145% here: same work, slower clocks).
  **Proposed next (not approved), ranked: (1) recommend Low Power Mode in Battery
  settings; (2) less CPU work per frame: the main-loop poll wait, then
  `Fingerprint`/`Record`; (3) half-precision shaders (GPU; Stefan's priority);
  (4) `--ios_display_match_cap` back to default false (no gain, 40 fps on a 60 Hz
  pattern judders).** Audio: stutters from 17:52 match XMA resets doubling.

- **October 24: IPA50 asks the display for the cap's rate (Stefan approved,
  extended to every cap): `--ios_display_match_cap=true` (default) -> 30 Hz at
  30, 40 Hz at 40, 60 Hz at 60; 120 unchanged. Built, not run.** The guest vblank
  keeps 60/120 Hz by splitting each published refresh. Battery mode's 30 fps cap
  changes follow. New `[display] refresh now N Hz` and `[xma-voices]` (5 s stream
  feed/reset/stopped summaries, SDK patch `patch_ios_xma_voice_log.py`, applied).
  IPA49 adaptive defaults unchanged. **Next: run A on IPA50, normal mode, 1x/40,
  ~10 min with a pursuit; battery % and times; note audio stutter / engine fade
  times. Check `[display] refresh now 40 Hz` and smooth pacing.**

- **October 24: IPA49 run A (gentler boost) saved nothing measurable:** 61 -> 56%
  in ~10 min = ~30 %/h (24-37) vs ~33 normal IPA48 and ~17 Low Power Mode; 39.8
  fps; phone hotter, thermal fair at the end. `[cpu]` fell to ~150% of a core, so
  CPU time is not what Low Power Mode saves. New lead: the 40 cap runs the display
  at 120 Hz in normal mode, 60 Hz in Low Power Mode (pacing lines). Audio: stutters
  at 17:32 and the 17:27 engine fade are game-side (silent blocks, XMA resets), not
  output underruns (TECHNICAL Oct 24). **Next (proposal, not approved): a build
  that asks for 40 Hz at the 40 cap (`--ios_display_40hz`-style switch), A/B
  against IPA49/IPA48 in normal mode.**

- **October 24: IPA49 makes the adaptive boost tunable (Stefan approved the
  lower-clock experiment). Built, not run on a device.** New default boost:
  Default QoS (not User Initiated), holds up to 20 s (not 240), the 3 busiest guest
  threads plus the render queue (not all). `--ios_adaptive_qos_ipa48=true` restores
  IPA48. `[cpu]` lines now end with Low Power Mode and thermal state.
  **Next: Stefan's run A on IPA49 (no Extra Args, Low Power Mode off, 1x/40,
  ~10 min with a pursuit, start/end battery % and times); compare with today's
  ~33 %/h (normal) and ~17 %/h (Low Power Mode) and check 40 fps holds.**

- **October 24: Low Power Mode on IPA48 about halves the iPhone drain at 1x/40.**
  `nfsmw_ipa48_battery_test_iphone.log` (17:02:44-17:13:05, heavy pursuit, same
  settings, no Extra Args): 66 -> 63% = ~17 %/h (12-23 with +-1 point) vs ~33 %/h
  (28-39) without it earlier today; 39.4 vs 39.95 fps, more single late frames
  (~5/min vs ~1/min in gameplay). Stefan: fps "99% the same". Inference: the
  40 fps workload fits lower clocks, so the OS's normal clock choice for our
  User Initiated holds costs energy we don't need. Next idea (BACKLOG, not
  approved): log Low Power Mode/thermal state, then a lower-clock experiment.
  Audio crackles (D-003) parked by Stefan (minor, inconsistent).

- **October 24: IPA48 fixed the iPhone pursuit stutter (D-002, Stefan: "didn't
  slow down anymore during the chase").** `nfsmw_ipa48_chase_iphone.log`: 39.95
  fps over 12,600 pursuit frames, 10 guest threads raised at each User Initiated
  hold, 7 swap gaps 41-107 ms in ~8.7 min of pursuit. Battery 72 -> 66% in 10.9
  min (~33 %/h, coarse). New: AirPods crackles (police chatter) and the
  engine-sound fade seen again on IPA47, both in BACKLOG (audio section);
  evidence in TECHNICAL October 24. No source change approved for them yet.

- **October 24: pursuit stutter traced to QoS placement; IPA48 built, untested
  (`--ios_adaptive_qos_workers=true`, default true).** Game Performance trace
  (IPA46, iPhone 17 Pro Max, 1x/40): Trace A 40.0 fps steady; Trace B (police
  pursuit) 22 fps in a 20 ms / 80 ms two-step. GPU 15.5 ms p50 in B, not
  limiting. During the gaps XThreadDF1B (Utility, E cores 0-3 only) was Preempted
  69% while Main XThread (User Initiated via adaptive QoS, P cores 4-5) was
  Blocked 62% with ~2,300 idle wakeups/s (~6x A). Inference: adaptive QoS raising
  only main/GPU while guest workers stay at Utility makes a cross-cluster
  critical path. IPA48 raises the other guest threads (QoS override) and the
  native render queue together with main/GPU. Evidence: TECHNICAL October 24.
  Pursuit on IPA48 held 40 (entry above). Remaining D-002 follow-ups (poll wait,
  encode cost) are optional; half precision and the batched power measurement
  follow.

- **IPA44: adaptive QoS for the iPhone (`--ios_adaptive_qos=true`, default
  false).** Next: iPhone race with `--ios_utility_qos_guest=true
  --ios_adaptive_qos=true`; IPA43 also carries the iOS 26 shader rebuild.
  iPhone not smooth enough; IPA45 tightens it and makes the 120 cap use adaptive
  QoS on 6-E-core iPads. GPU candidates listed (half precision first).
  IPA46: adaptive default on below 6 E cores. Cap 40 iPhone: Utility held, 40
  fps steady. **Next session: half-precision shaders (top of backlog), then the
  batched end-of-work power measurement (no Extra Args on either device:
  guest Utility is default everywhere from IPA47).**

- **Direct draw path (Stefan chose it, Oct 22): P0 census built (IPA38,
  `--ios_packet_census=true`).** Design phases P0-P3 in TECHNICAL Oct 22.
  Census done (iPhone race): ~17k type-0 + ~17k NOP packets, ~220k register
  words, ~2.4k draws per frame. P1a (CP fast runs, `--ios_cp_fast_runs=true`)
  visual check passed; default on in IPA40. P1b/P2 assessed as <1% each:
  recommended to stop the direct path there. Measurement batched to the end.
- IPA41: native GPR save/restore helpers (`--nfsmw_native_gpr_helpers=true`,
  default false). Next: a race with it on; Extra Args: iPad only that flag,
  iPhone that plus `--ios_utility_qos_guest=true`; delete the rest.
  Race passed on iPhone; default on in IPA42 (log `[gpr-helpers]`). Extra Args
  now: iPad none, iPhone `--ios_utility_qos_guest=true` only.

- **IPA36: fix for the iPhone null-call crash near the safehouse** (deferred-call
  queue ordering, `patch_game_deferred_queue.py`). Not device-tested. Next: iPhone
  play to the safehouse on IPA36; then the pending IPA35/36 two-launch stutter
  check and the iPhone `--ios_utility_qos_guest=true` power pair.
- IPA37 adds exact renderer bookkeeping trims, fused upload sizing default on,
  and line tables + dSYM so the next device trace maps to source lines. Next:
  iPhone profiler on IPA37, then trim the top lines.

- **IPA27 matched pair (Oct 21): both Utility flags ON cut estimated drain
  33.66 -> 25.70 pp/h (-23.6%) and CPU impact -57% at 1.5x/60, equal 32%
  brightness, Nominal thermals.** GPU impact +21%; small extra FPS dips
  (57-59.4 summaries, seen only while recording per Stefan).
- **Both Utility flags are now default true (IPA28, Oct 21, Stefan approved).**
  iPhone 17 Pro stuttered badly with it (45-55 fps, 4 E cores). IPA29 turns it
  on by default only with >= 6 efficiency cores (`[utility-qos]` log line).
  IPA29 confirmed: iPhone 4 E cores/off, smooth 60; iPad 6/on, smooth 60.
  iPhone with `--ios_utility_qos=false --ios_utility_qos_guest=true` (Oct 21,
  run_3_iphone.log): smooth Quick Race, 17/20 summaries >= 59.5; power not yet
  measured. Step 3 investigated (Oct 21): proposals A (early command-buffer
  commit, aimed at the +21% GPU impact) and B (per-frame fingerprint memo)
  approved and implemented as default-off switches in IPA30, together with
  five experiments made default (render utility, attribute lookup, GPU lookup
  hash, lazy diagnostics, transform copies). Next: iPhone/iPad correctness lap,
  then A+B ON vs OFF power pair on the iPad. IPA30 checks: defaults OK on both;
  B cuts fingerprints ~75%; A never fired (threshold), fixed in IPA31. Next:
  IPA31 lap showing early commits, then one A+B power run vs the Oct 21 ON arm.
  Done: A+B 25.41 vs 25.70 pp/h (-1.1%, noise level); A no GPU benefit. Proposal:
  B default on (IPA32), A stays off. GPU candidates without lower resolution
  ranked in latest TECHNICAL entry. Next: one pursuit on IPA32 with
  `--nfsmw_native_cost_probe=true` to rank shader GPU costs; 1 and 3 backlogged.
  Done: shadow casters 0.91, trees 0.90, fences/plants 0.76 ms of ~10.1 ms.
  Shadow-caster variant implemented (IPA33, `nfsmw_native_shadow_caster_variant`,
  default false). Probe run: shadows identical, frame GPU -11% but not
  attributable (caster delta unchanged). Default on from IPA34 (equivalent by
  construction). It exposed the synchronous pipeline-archive save (two big
  stutters); IPA35 saves in the background to a new file. iPhone baseline
  37.6 pp/h, CPU impact 21.0; heat drops it to ~20 FPS after ~9 min. Next: iPhone
  guest-only Utility run (`--ios_utility_qos_guest=true`) on IPA35.

- **IPA25 built: `--ios_utility_qos=true` (default false) runs the game main
  and GPU command threads at Utility QoS** (approved Oct 20). Not device-tested.
  Next: short correctness check, then a matched 1.5x/60 LPM-OFF power pair
  toggling only this flag. Details in latest TECHNICAL entry.
  IPA25 froze after the movie skip because it shipped WITHOUT the native shader
  libraries (empty NFSMW_NATIVE_SHADERS_DIR); withdrawn. Use IPA26 (same source,
  shaders included). IPA26 short check passed (2-lap race, 60 fps, flag ON);
  One ON power arm vs Oct 19 pair: drain 31.26 vs 33.33 pp/h (-6%), CPU impact
  -29%, FPS held; brightness 29% vs 35% confounds. Next: same-day OFF arm at
  the same brightness, then decide on making it default.
- **IPA27 adds `--ios_utility_qos_guest=true`** (default false): the remaining
  guest threads (a game worker and the audio decoder, still on P cores in the
  IPA26 trace) also at Utility. Not device-tested. Stack both flags for the
  next ON arm; OFF arm both false, same brightness (Auto-Brightness off).

- **LPM explanation (Oct 20):** in the matched 30 FPS pair, frame rate, refresh,
  GPU and display were equal; only CPU power fell (~61%) while CPU time rose, so
  LPM runs the same work at a lower clock ceiling (inferred). Apps cannot set
  clocks. Ranked app-side levers in latest TECHNICAL entry; top proposal is a
  default-false switch demoting the guest game/CP threads to Utility QoS,
  never tested before (only the render queue was). Awaiting Stefan's approval.

- Retention clarification: keep accepted/default-on optimizations enabled and
  retain recent experiments for accumulated testing. Not every recent shortcut
  has demonstrated lower total CPU work: the four-change pair was 110.114% ON
  versus 109.074% OFF of one core, with gameplay variance. No measured energy
  win does not rule out CPU power; the matched LPM comparison used more CPU
  time while consuming substantially less estimated device power. Do not
  discard stable changes solely for an inconclusive small battery comparison,
  or promote experimental defaults solely on assumed CPU savings. No source,
  flags, compiled defaults or next diagnostic approval changed by this question.

- **Three-axis investigation completed; next recommendation is an opt-in
  frame-flow/copy-eligibility diagnostic, awaiting source approval.** User
  approved investigation of scheduling, redundant graphics stages and GPU
  traffic. No source change/diagnostic build approved or made. Existing trace
  lacks blocked/runnable/wakeup/deadline data. A new optional diagnostic would
  measure guest/CP/render/GPU/presentation timing and compatible copy stages;
  no quality, cap, QoS or resource-operation change. Exact four-file scope and
  validation in latest TECHNICAL entry. GPR prototype remains held.
- New CPU union: identified guest graphics/constant prep plus packet handling
  outside native draw/swap is 9.13 /8.09% app CPU, only partly removable. Do not
  describe all guest CPU or CP inclusive work as translation overhead.
- GPU: 105 profiles/arm: main scene/reflection/shadow ~73% sampled span; color
  resolves+cube assembly ~0.35 ms (~8%), only partly eligible. Depth audit: 315
  snapshots/arm has ZERO unchanged candidates; artificial splits ZERO and
  discard-unread already active. Pool checkouts ~99.95% reused. Do not repeat
  those implemented/ruled-out experiments. Candidate image-preserving changes
  need versioned color snapshots / reflection intermediate liveness proof.
- Public CAMetalDisplayLink is a possible deadline-aware native pacing path;
  energy gain unproven, guest vblank/atTime presentation need careful migration.
  Sustained Execution is a conditional platform lead, not the main solution.
  **User confirms free LiveContainer signing; Game Mode appears only with shared
  app +LiveContainer2. Main plan must serve ordinary free-signing users without
  that workaround.** Host entitlements govern; no entitlement/host change made.
- **User requests strategy reassessment before the GPR prototype.** Recent
  changes have not demonstrated substantial battery savings. Hold the unapproved
  helper proposal; the three-axis follow-up above prioritizes the much
  larger LPM/system-policy clue and higher-ceiling redundant work. Prior matched
  30 FPS LPM comparison estimated ~44% lower drain; no established app equivalent
  or1.5x/60 extrapolation. No claim that the port is already fully optimized.
  Latest TECHNICAL entry records evidence, limits and revised priorities. No
  new implementation, device test or generic repeat pursuit A/B approved.
- **Broader CPU audit complete; next proposal is a guarded GPR save/restore
  prototype, currently held/unapproved pending strategy reassessment.** IPA24 paired trace: helper bodies 3.805 /4.318%
  app CPU self (ON/OFF), plus separately sampled link stubs 0.762 /0.681%.
  Full 4.6–5.0% pool is NOT recoverable or a battery-saving estimate. All 36
  generated save/restore functions (GPR14..31) exactly match simple fixed stack
  operations. Translate the ordinary stack once, keep identical ordered writes,
  GPR/LR state and original unusual-address fallback. Host measurement must
  include guard/OFF dispatch overhead before any new IPA. No optimization code,
  new flag, benchmark or build exists yet; only structural inspection passed.
- Proposed files: new `ios/src/game_gpr_helpers.{h,cpp}` and
  `tools/ios/test_game_gpr_helpers.py`; integration in `ios/CMakeLists.txt` and
  startup logging in `ios/src/ios_main.mm`. Use strong overrides of existing
  weak entries, original __imp fallback; no generated or SDK source changes.
  Proposed independent flag `nfsmw_native_gpr_helpers`, default false, not yet
  available. Exact semantics, ranking and host/device gates in newest TECHNICAL.
- Audit also confirms old game-thread Capture parsing is bypassed; native-only
  constant writes already use bulk paths. Record's constant memcmp call sites
  cover only 0.085 /0.110% app CPU here. A general guest/PM4 bypass needs much
  more ordering/state proof. No next implementation approved, no extra trace
  needed before the proposed host prototype. Existing SDK local work preserved.

- **IPA24 four-change power A/B analyzed**, October 19, same Challenge Series
  pursuit restarted in both arms (user confirmed). ON first, OFF second; both
  exact IPA24 UUID, 1.5x/60, constant35% brightness, Nominal thermals. Equal
  guarded/event-elapsed527.535 s: estimated drain **34.1868 /33.3576 pp/hour**
  (ON/OFF), CPU110.114 /109.074% one core, GPU4.299 /4.305 ms. ON estimates
  2.49% more drain; retired instructions1.79% higher and sampled last-frame
  draws3.00% higher. **No demonstrated saving; not a proven causal regression.**
  Same-event attempts help but do not make pursuits deterministic. Full methods,
  diagnostic exclusion, CPU samples and limits are in the latest TECHNICAL entry.
- Pipeline shortcut reduces original hash/find samples74.2%, but added equality
  consumes most of that; combined region2.825 /2.959 CPU s over527.535 wall s.
  Do not turn the hash-only improvement into a whole-game energy claim.
- Retain IPA21–24 as experimental/default false; earlier changes/defaults stay
  unchanged. No new IPA or source change. The larger-work audit is complete;
  proposed GPR helper prototype and approval boundary are above. No second arm
  or repeated tiny A/B is required before that host work.
- Inputs now under `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/19
  October 2026/`: `nfsmw_run_1_ipad.log` and `power_profiler_1_ipad.trace`.
  Three OFF gameplay watchdog/semaphore dumps are documented; frames continue
  progressing and excluding matched +/-5 s windows preserves the power result's
  direction. Do not reopen the parked iPhone or GPU capture investigation.
- Startup HEAD `cdd04b2`; branch `battery-optimization`; only intentionally
  untracked `HANDOFF_CHATGPT.md`, preserved. Explicit workdir is required after
  repository move; old Documents/GitHub cwd no longer exists.

- Latest build: **IPA24**, `ios/build/NFSMW-battery-pipeline-lookup-24.ipa`.
  Optional exact last-ready pipeline lookup, borrowing the existing owning map
  node. No nil/pending/failed result cache; full original field equality and
  miss path retained. Actual Get/Finish differential tests, ASan/UBSan and -O3,
  iOS build, ARM64 inspection, ZIP CRC, strict deep codesign, unchanged 104 Metal
  libraries and 2 SDK dylibs passed. New flag defaults false.
- **IPA24 initial iPad correctness check passed**: October 18
  `nfsmw_run_6_ipad.log`, user reports "everything is fine". Renderer build
  20:14:16; last-ready-entry shortcut and preceding changes ON. Scale 1.5/cap 60,
  MetalFX/FXAA OFF, no LPM suffix. All 13 guarded summaries 60 FPS; pacing 0/3,900,
  all 39 thermal observations Nominal. No gameplay errors or GPU failures;
  two startup/menu watchdog groups precede driving. Final partial log line
  ignored. No repeat short check or new build needed.
- The matched IPA21–24 four-change power comparison is now complete; see
  the current result above. Both arms are in the supplied trace. These changes
  remain experimental, compiled defaults unchanged; no energy win established.
  No next source implementation approved; parked diagnostics stay parked.
- **IPA23 initial iPad correctness check passed**: October 18
  `nfsmw_run_5_ipad.log`, user reports "still looks jsut fine". Renderer build
  19:48:54; target lookup mode confirms frame-local last target, earlier flags
  retained. Scale 1.5 / cap 60, MetalFX/FXAA OFF, no LPM suffix. All 12 guarded
  summaries report 60 FPS; pacing 0/3,600, all 33 thermal observations Nominal;
  no error-level/GPU-failure messages. Detailed sample/limits below.
- Keep `--nfsmw_native_target_lookup=true` with the accumulated Extra Args,
  including fused sizing and bulk attribute comparison. Compiled default stays
  false. No repeat short run, new build or tiny-change power A/B needed for
  this result. Sustained stability and energy benefit remain unproven.
- IPA24's source target is ~0.6935% app CPU self in the existing IPA22 chase
  profile, not all recoverable. Host repeated-key Get fixtures improve 12–18%;
  synthetic late-field all-miss case regresses 18.6%. No universal/device gain
  claim. Detailed fixture failure/correction, tests and timings recorded below.
  The accumulated **IPA21–24 four-change batch** was measured October 19,
  retaining earlier experiments/settings in both arms; result above. Only
  fused_upload_sizing, attribute_bulk_compare, target_lookup and pipeline_lookup
  changed after cold restarts; the master battery flag was retained ON.
  No next source optimization approved; iPhone issue stays parked.
- **IPA22 initial iPad correctness check passed**: October 18
  `nfsmw_run_3_ipad.log`, user reports "still no issues". Renderer build
  19:11:46, base + bulk 32 comparison/front cache ON, fused sizing and prior
  experiments retained. Scale 1.5 / cap 60, MetalFX and FXAA OFF; no Low Power
  Mode suffix. All 11 guarded complete summaries report 60 FPS; pacing 0/3,300
  off-grid, all 33 thermal samples Nominal, no error-level/GPU-failure messages.
- Keep `--nfsmw_native_attribute_bulk_compare=true` with the accumulated
  experimental stack for later measurement. Compiled default remains false;
  no isolated CPU/energy gain is established. No repeat short run or new build
  needed for this result. Sustained stability remains unproven.
- Earlier IPA22 profile analyzed: October 18 `nfsmw_run_4_ipad.log` plus
  `Power_Profiler_2_ipad.trace`, 1.5x/60, all accumulated flags ON, brightness 34%,
  nominal thermals. User confirms last gameplay stretch is a chase. Actual
  recording 19:23:41.755–19:33:48.860 also includes earlier unclassified play;
  primary guarded chase is 19:28:53.813–19:33:43.860 (290.047 s), not ten minutes.
- Primary chase: modeled whole-device drain 31.956 battery points/hour;
  CPU/GPU/display impact 11.088 / 2.273 / 5.731 (not watts/additive), network 0.
  57 complete summaries all 60 FPS; pacing 20/17,100, worst 8.3 ms. No errors in
  guarded chase/GPU failures; earlier watchdog/semaphore diagnostics are
  recorded separately. No matched OFF arm, so no batch energy claim.
- CPU priority remains justified. Render task 35.77% inclusive CPU, already
  99.97% on E cores; guest functions 26.52% self, Record 5.37% self. Fractions
  overlap and are CPU samples, not energy savings. See TECHNICAL.md for detail.
- IPA23 targets two primary map lookup sites accounting for 98.6% of target-
  map self work (~1.04% app CPU total) in that profile. Host repeated-target
  timings improve, but all-miss layouts still regress; no universal speedup
  or full recovery of the sampled region is claimed. Current implementation
  uses borrowed node identity after the owned-key prototype's miss penalty.
  Exact tests/results and negative findings are in the work log and TECHNICAL.md.
  Pipeline lookup (~0.69% main hash/find self) is secondary; broader guest/PM4
  bypass needs evidence and ordering analysis. iPhone issue remains parked.
- IPA21's initial iPad correctness check passed (`nfsmw_run_2_ipad.log` on
  October 18). Keep fused sizing ON for accumulated tests; its compiled default
  remains false. IPA22's new comparison also defaults false and requires
  attribute lookup ON. Host timings are favorable in five synthetic layouts;
  no isolated device CPU/energy improvement is established for either change.
- Previous matched Low Power measurement: the two runs in
  `/Users/bep1s/Desktop/debug/18 October 2026/Power_Profiler_1_ipad.trace`, paired
  with `nfsmw_run_1_ipad.log` in the same folder. Both arms have been analyzed;
  no second file or repeat comparison is needed for this pair.
- IPA20, 0.85x, explicit 30 FPS, Battery mode settings, all previous experiments
  and GPU lookup counters ON. Brightness is 34% in both arms, thermals Nominal.
- Ten minutes Low Power Mode ON: estimated whole-device drain **13.612 battery
  percentage points/hour**. Ten minutes OFF: **24.540**. Guarded gameplay gives
  13.856 versus 24.879; a continuing pursuit gives 13.646 versus 24.670.
- Observed saving is about **45% in this comparison**, with modeled CPU impact
  about 61% lower, GPU impact similar. This is not a code-batch attribution or
  proof of the same saving at normal fidelity/60 FPS. CPU operating point is a
  leading explanation; clock/voltage changes were not directly measured.
- CPU time was higher ON, about 91.4% versus 59.2% of one core in guarded
  gameplay, despite lower power. Running samples remained predominantly on P
  cores in both arms. Moving everything to E cores does not explain this result.
- The user recalls all events being Challenge Series pursuits; do not label
  them races from post-event menu names. Workloads evolve and order was ON
  then OFF. Charging tables were empty; cable state was not independently
  verified. Full methodology, limits and numbers are in TECHNICAL.md.
- Flight reference: 95 minutes, battery 75% to 55%, Battery mode/30 FPS plus
  system Low Power Mode, low brightness in a dark cabin, no observed FPS drops.
  No log; exact experimental arguments uncertain. About 12.6 points/hour.
- iPhone event loading is **resolved for now / monitor**, parked by explicit
  user request. No cause or fix was established. Do not resume its isolation
  tests. Offline-only failure has not been reproduced.

## Controls and implementation status

The master `--nfsmw_battery_optimizations=true` defaults ON and rewrites five
individual controls after parsing: cube deduplication, bulk constants,
geometry reclamation, vertex-fetch layout cache and compressible resolves.
To turn those off, set the master false; individual false arguments alone
are overwritten. Group OFF restores historical elevated guest/CP priority
only above 40 FPS; at 30/40 both arms leave it off. The launcher priority option
is retired and `ios_thread_qos` is ignored.

| Independent control | Compiled default | Current evidence |
|---|---|---|
| `nfsmw_native_constant_copies` | true | Guarded guest copy patch; differential host checks, iPad/device checks; no isolated energy claim |
| `nfsmw_native_texture_masks` | true | Conservative shader-slot pruning; large reduction in slot visits, no quality issue reported |
| `nfsmw_native_draw_arena` | true | Per-frame PMR storage; allocation count reduced; GPU/frame ownership preserved |
| `nfsmw_native_render_utility` | true (IPA30) | Render queue largely on E cores; earlier 60 FPS whole-device power unchanged; short iPhone load passed |
| `nfsmw_native_attribute_lookup` | true (IPA30) | Bounded entry front cache, content validation unchanged; iPad correctness passed |
| `nfsmw_native_transform_copies` | true (IPA30) | Guarded scalar transfers, bit-exact differential tests and iPad checks; energy gain unproven |
| `nfsmw_native_lazy_diagnostics` | true (IPA30) | Skips unused normal-frame metadata/labels, preserves snapshots and residency; iPad check passed |
| `nfsmw_native_gpu_lookup_hash` | true (IPA30) | Cache hit rate improved ~57.2% to ~74.0%; device CPU/power gain not established |
| `nfsmw_native_gpu_lookup_slots_log2` | 14 (IPA64) | GPU buffer direct cache 16,384 slots (12 = old 4,096); not device-tested |
| `nfsmw_native_attribute_lookup_sets_log2` | 14 (IPA64) | Attribute front cache 16,384 sets (12 = old 4,096; 18% misses in the IPA63 chase); not device-tested |
| `nfsmw_native_scale_reflections` | false (IPA65) | Environment cube faces stay at 1x; not device-tested |
| `nfsmw_native_gpu_lookup_stats` | false | Diagnostics only; enable consistently when comparing coverage |
| `nfsmw_native_fused_upload_sizing` | true (IPA37) | IPA21: host/build checks and initial iPad 1.5x/60 correctness passed; device energy gain unproven |
| `nfsmw_native_attribute_bulk_compare` | false | IPA22: exact base + 32-byte front-key equality; all four host switch configurations/build checks and initial iPad 1.5x/60 correctness passed; energy benefit unproven; requires attribute lookup ON |
| `nfsmw_native_target_lookup` | false | IPA23: host/build checks and initial iPad 1.5x/60 correctness passed; energy gain unproven; miss-heavy cost documented |
| `ios_utility_qos_guest` | on on every device (IPA47) | Utility QoS for all other guest threads; Oct 21 pair -23.6% drain with the flag below |
| `ios_utility_qos` | on with >= 6 E cores (IPA29) | Utility QoS for game main + GPU command threads |
| `nfsmw_native_fingerprint_memo` | true (IPA32) | IPA30 proposal B: per-frame fingerprint memo for non-dynamic regions; not device-tested |
| `nfsmw_native_shadow_caster_variant` | true (IPA34) | ps 4fbaecfb without its cut-out where c1.x is 0; shadows identical, energy unproven |
| `nfsmw_native_gpr_helpers` | true (IPA42) | native guest register save/restore helpers; iPhone race passed, gain unmeasured |
| `ios_adaptive_qos` | on below 6 E cores, or >= 6 E above 60 fps (IPA46) | Utility for main/CP while frames are on time; iPhone at 60 settles at full speed |
| `nfsmw_native_early_commit` | false | IPA30 proposal A: commit finished passes early; not device-tested |
| `nfsmw_native_pipeline_lookup` | false | IPA24: host/build and initial iPad 1.5x/60 correctness passed; energy gain unproven; late-mismatch cost documented |

These are independent switches; clearing Extra Args does not enable the five
older default-false experiments. Most recent iPad profiling had them ON.
Keep test arguments/settings fixed when adding the new flag; don't silently
convert between defaults and the accumulated experimental stack.

## Build references and experiment

IPA47 (guest Utility default everywhere): `ios/build/NFSMW-battery-guest-utility-default-47.ipa`.
UUID `E67B131A-6620-3978-8D16-AB741FA96B32`; SHA256
`4abe8f7a501e49c59c2baea2f679a329f7baf9d855395ef53f4d541f14007e57`.

IPA46 (adaptive default below 6 E cores): `ios/build/NFSMW-battery-adaptive-default-46.ipa`.
UUID `C60ADFE5-E2BA-319E-8715-3BF3AC5CDBEC`; SHA256
`e53538ebb055566abff989b0e4a9c3d9e13d956f02d7f7006233bf8e89e11798`.

IPA45 (cap-aware QoS, tighter adaptive): `ios/build/NFSMW-battery-qos-cap-aware-45.ipa`.
UUID `3D31A4DB-CA99-3D00-B23F-EFCE6EADF310`; SHA256
`a89e2776d77938f9740657d7a3b8e4d8df722b14e9980528187ee8e40e0faec9`.

IPA44 (adaptive QoS switch): `ios/build/NFSMW-battery-adaptive-qos-44.ipa`.
UUID `145F69E6-0EA9-3207-85BA-7D87F64413D8`; SHA256
`e4f5d178c4cf83a443f5e139adc648ecfd69fbc3e9e3928f60188a94125ec36b`.

IPA42 (GPR helpers default): `ios/build/NFSMW-battery-gpr-default-42.ipa`.
UUID `5C6A9AF4-41C0-33C3-94E3-964C285291D7`; SHA256
`1781118ace622b3b3a356238a06408f5796a644e841637b10ea0ce8733793500`.

IPA41 (GPR helpers switch): `ios/build/NFSMW-battery-gpr-helpers-41.ipa`.
UUID `0CEBC0F6-811F-3547-865C-C345953E4273`; SHA256
`c49270cf225398eae76720fc0427ec3b6efe5ea593d315e5e99e645265b827e3`.

IPA40 (CP fast runs default): `ios/build/NFSMW-battery-cp-fast-runs-default-40.ipa`.
UUID `32FD84F2-2FE2-3492-B1E5-67E3AD6D9388`; SHA256
`3296d281f638e0e1e3061897936ffaa24b4df5f9ea933ed9a5e3616ff393b420`.

IPA39 (CP fast runs): `ios/build/NFSMW-battery-cp-fast-runs-39.ipa`.
GPU plugin UUID `7BC3CF79-94F8-39EB-B333-7174107B362E`; SHA256
`334fc422a32af5ad424a8f2eef514f8c8f49f32747246987893d68aeb94167c9`.

IPA38 (PM4 census): `ios/build/NFSMW-battery-pm4-census-38.ipa`.
UUID `83839B57-2037-347F-BD4C-310AEB0B51BF`; SHA256
`bf0bd4b08f5ec3660c35e579e3fd4424c9f8472496cdc99b7e5994fc240f56b2`; dSYM beside it.

IPA37 (bookkeeping trims, line tables): `ios/build/NFSMW-battery-target-memo-37.ipa`.
UUID `353B6258-10CB-347B-91AB-38E4DCAB69BC`; SHA256
`774badbd173be121227419f22059522b0171d6e4f71d9b8ddaef46340b7c6654`; dSYM beside it.
Keep each test IPA's dSYM (`xcrun dsymutil <app>/NFSMW -o <ipa name>.dSYM`).

IPA36 (deferred-queue crash fix): `ios/build/NFSMW-battery-queue-fix-36.ipa`.
UUID `D8A19FC2-C3A9-3E63-AA24-47E9EAF8D600`; SHA256
`41398761a0c0cb8851b15fb54576b77370535a4f48fdcb3e2b08cce77f235429`.

IPA35 (background pipeline-archive save): `ios/build/NFSMW-battery-pipeline-save-35.ipa`.
UUID `EC48DBCA-637F-3BA7-841D-C28D8B1B6EDF`; SHA256
`50b0f8419dfb7d2ba89ef9239135ee4a72a227063395abdf0f0a51a33304d1da`.

IPA34 (shadow-caster variant default): `ios/build/NFSMW-battery-shadow-caster-default-34.ipa`.
UUID `36D129D7-74A9-3D18-A33C-9E9B4DD91D77`; SHA256
`f86bceb52fea01c9d7135371bf9ab5917f9f2a5620bb9c7a97f8df8d088f83f2`.

IPA33 (shadow-caster variant switch): `ios/build/NFSMW-battery-shadow-caster-33.ipa`.
UUID `516A4623-1FCF-3AD4-B994-4939E6ABA39E`; SHA256
`080f5418db319dc276aa2f5828a8e9519e2e01a4f6257e30272dc81cfc4ad6a4`.
Its NativeShaders include the rewritten ps_4fbaecfb (rebuild shaders with the
updated build_shaders.sh to reproduce).

IPA32 (fingerprint memo default): `ios/build/NFSMW-battery-memo-default-32.ipa`.
UUID `5D1534C8-183D-3D26-84B4-F178ADB0FDC4`; SHA256
`1f4990de76be2b6bd59b629741591bf8ba5cdf52bc00c6bd47ce27da000802af`.

IPA31 (early-commit threshold fix): `ios/build/NFSMW-battery-early-commit-fix-31.ipa`.
UUID `9AEF39D1-5E2D-3902-A6F0-E687F0F36DD4`; SHA256
`2f09dae9f714acbe8586436032403af2c260c738a9a1a422acce99bc7034ff85`.

IPA30 (five defaults + A/B switches): `ios/build/NFSMW-battery-defaults-early-commit-30.ipa`.
UUID `5E8C4D54-6722-3B1C-95FD-3B23FFA00AAD`; SHA256
`0f24555d5ae48cae59616ec4592865317ad0509b61b7106ad6a8ca85fcee185c`.

IPA29 (Utility QoS default only with >= 6 E cores): `ios/build/NFSMW-battery-utility-ecores-29.ipa`.
UUID `DDF5F784-C577-3AA9-8115-FF5769EB088B`; SHA256
`ea7e301e241b4ba9bab77588888cf08f06cab8431a666498cca4209255c6fe4e`.

IPA28 (Utility QoS default on): `ios/build/NFSMW-battery-utility-default-28.ipa`.
UUID `8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1` (runtime `C4710F54-F0DE-3948-83FC-1B75F230B23D`);
SHA256 `ce31d0a89fd44ac19d34ed763f6ec8abece1871506dbe3e078004eafbe6866d8`.

IPA27: `ios/build/NFSMW-battery-utility-qos-guest-27.ipa`.
UUID `8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1` (runtime `1FAE8DDC-9FAE-3CF3-962C-DB86037B1E89`);
SHA256 `f534f92f1456229906719dafd12b4242cc1940ac548a078a2b4b412efdc6ccdf`.

IPA26: `ios/build/NFSMW-battery-utility-qos-26.ipa`.
UUID `8EB9B0F3-21DB-31FB-B9BD-351BB7FC08C1`; SHA256
`1f5b7c3d1b7e54619346bd8386b5d0484b0a55a9d588f7ec738926ee340761c0`.
IPA25 (same source) is withdrawn: no native shader libraries packaged.
SDK patch `tools/ios/patch_ios_utility_qos.py`.

IPA24: `ios/build/NFSMW-battery-pipeline-lookup-24.ipa`.
UUID `6E360E6A-9918-3D39-B4FE-70B755E02D30`; SHA256
`7adc3d1885b29f7921e72b2f80a4b6bed50e55deffc2fe48a3bfb5365af367a9`.
Implementation and fixture: local source commit `9474672`.

IPA23: `ios/build/NFSMW-battery-target-lookup-23.ipa`.
UUID `18262CD0-8C95-3E09-B2C1-26931A50BED2`; SHA256
`dd300305e12bc45adf890a505e2a2978fd3ed350b833859e7500d7c8f564b644`.
Final version borrows the existing map node; the owned-key prototype was not
issued. Implementation and fixture: local source commit `5e612c8`.

IPA22: `ios/build/NFSMW-battery-attribute-bulk-22.ipa`.
UUID `3CDAD6C3-51F9-372C-B7C5-DB5B3FBF1640`; SHA256
`88dd71bf9d4e379e682ea6ac168211c6d3f90b06285ca32efe90030a392ee7c7`.
The final implementation uses a base-address rejection followed by a 32-byte
comparison, not the superseded full-40-byte prototype. Implementation, fixture
and validation record: local commit `7b848b1`.

IPA21: `ios/build/NFSMW-battery-upload-sizing-21.ipa`.
UUID `BB547F91-F458-34B1-856F-BED78713E517`; SHA256
`8663dd8a610febf1d4461cfe5898e0b884f4e562f214d11ca4a5af01fe484a9e`.
Implementation and validation fixture: local source commit `2463b16`.
This is the final build with the budget helpers forced inline. The provisional
build produced during development was replaced before handoff; its UUID
`161393D6-CBA1-38ED-A7D3-29A75747C2A0` identifies the superseded version.

IPA20: `ios/build/NFSMW-battery-gpu-lookup-hash-20.ipa`.
UUID `2CD6D542-84B7-3379-BB26-DAE64A642F64`; SHA256
`311ddbcc7ae6c75c23f3bb57f63e152f0c52757aeb78203d84a9a4c3e6161648`.
Its source change was committed as `da5617b`; later commits through `03da344`
are documentation. See TECHNICAL.md for previous IPA IDs and tests.

Current approved implementation: exact last-successful ready-pipeline lookup.
Production: `ios/src/native_renderer.mm`; fixture:
`tools/native/test_pipeline_lookup.py`, comparing actual extracted Get/Finish
with Git reference 8623510 plus immutable miss/Collect source guards. Cache
stores one borrowed ready-map node, no extra PSO owner; fields compared by the
original equality operator, with original failure/pending/async behavior. Mode
selected once per RenderFrame; earlier experiments and shader/resource policies
intact. New default false. This is incremental CPU work, not a proven energy win.

### October 18 — approved sizing experiment work log

- User approved implementing the combined sizing pass and explicitly requested
  persistent Markdown documentation for cross-session/agent handoff.
- Added a current-state index here and linked it from README and root AGENTS.md /
  CLAUDE.md entry points; detailed prior observations and tests remain in
  TECHNICAL.md rather than being discarded.
- Added the optional fused sizing path and periodic `[native] upload sizing`
  mode identification. One draw traversal ON; original two traversals OFF.
- `python3 tools/native/test_upload_sizing.py` passed **2,011 frames** with
  ASan/UBSan, using extracted production layouts and source reference 03da344.
  Both switch arms match exact original budgets, preserve relevant input,
  bound worst-case aligned uploads, and have the expected traversal counts.
- Initial timing overlapped compilation and was noisy. A warmed benchmark
  then found a slowdown in some synthetic layouts. ARM64 inspection found
  the shared constants-budget lambda outlined into a call per draw in both
  paths. Added always_inline to both budget lambdas and reran checks/build.
- Final `python3 tools/native/test_upload_sizing.py --benchmark` passed at
  -O3. Seven alternating trials, 2,000 iterations, 2,700 synthetic draws/frame:
  fused median 19.212 / 38.127 / 37.955 microseconds versus original
  26.944 / 49.910 / 42.676 at 0% / 20% / 100% fresh geometry. About 11–29%
  improvement for this sizing fixture only; no whole-app/device energy claim.
  Current OFF medians were 26.897 / 52.877 / 43.328 microseconds; no claim of
  identical machine code or universally identical OFF-path timing.
- Final iOS build passed with existing FPSCR/UIScreen warnings. Inspection
  confirms one draw loop ON, two OFF, and no outlined budget helper calls.
  Source after sizing through encoding/ownership up to the summary entry is
  byte-identical to 03da344. ZIP CRC and strict deep codesign passed; all 104
  actual Metal libraries are byte-identical to IPA20 (exclude __MACOSX entries).
- Only native_renderer.mm changed production behavior; the SDK and shader
  sources were not changed. Exact outputs and limits are in TECHNICAL.md.
- Device validation remains pending. Intended next step is one short iPad
  correctness run with the new flag ON, same existing settings/arguments.
  Do not request another long Low Power Mode A/B for this small change.

### October 18 — first IPA21 device result

- After the user asked to return to their usual graphics, the correctness test
  was explicitly changed to Battery mode OFF, 1.5x, 60 FPS, system Low Power
  Mode OFF. This was not intended as a power comparison with the 30 FPS traces.
- Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_2_ipad.log`.
  User reports "everything looks fine". Renderer build is Oct 18 18:16:30;
  mode line confirms fused single traversal. All prior experimental controls,
  including lookup statistics and Utility rendering, remain enabled.
- Gameplay spans 18:52:15.356–18:53:32.567 (77.211 seconds), ending when the
  app resigns active. Five-second transition guards and complete-window rules
  yield 13 summaries / 3,900 frames, each reporting 60 FPS. All 34 thermal
  observations are Nominal; memory reports have no Low Power Mode ON suffix.
- Median recording 1.45 ms, render encoding 13.90 ms (includes drawable waits),
  GPU 10.03 ms; six eligible CPU intervals average 87.33% of one core. These
  metrics do not isolate the sizing calculation or prove an optimization gain.
- Pacing: 16/3,900 off-grid intervals, worst deviation 4.2 ms. A 41.6 ms swap
  hitch immediately after entering driving included 235 texture decodes /
  about 60 MiB and is outside the guarded sample. No GPU failure or gameplay
  error-level lines. Watchdog/semaphore diagnostics appear only before driving.
- Initial correctness/visual check passed. Keep the flag ON for subsequent
  stacked tests, default false. No long A/B, another build or repeat short run
  is needed for this result. Sustained stability and device energy benefit
  remain unproven. The iPhone issue remains parked; no new source change.

### October 18 — next-target audit after IPA21 validation

- Existing profile's attribute front-cache selector/key-check region accounts
  for about 1.17% / 1.09% of active app CPU in the Low Power ON/OFF arms.
  ARM64 performs a chain of field comparisons at each of two possible slots.
  These shares include other lookup work; not all is removable.
- Temporary probe changed only front-slot equality to a full 40-byte memcmp;
  backing-map equality, keys, set selector, replacement and validation remain
  unchanged. The current AttributeKey has unique object representations and
  no padding on this target; static assertions passed. Preserve such guards
  if implementing this, rather than applying raw byte equality to arbitrary
  structs. Every identity field still participates.
- Reused the extracted production cache/sweep fixture under ASan/UBSan. Both
  original and candidate passed nine-field identity, collisions, same-frame
  source mutation, rehash, sweep/reinsert and ownership tests, including
  90,000 changing-key pairs. Matching lookup counters/checksums were preserved.
- Seven alternating -O3 trials, 3,686,400 lookups each: original median
  66.64 ms, candidate 32.78 ms (about 50.8% faster in this one host workload).
  Ranges 64.46–98.44 / 30.45–65.35 ms show timing variability. This is not a
  replay of device addresses, a whole-renderer gain or an energy result.
- Proposed production scope: native_renderer.mm plus extending
  tools/native/test_attribute_lookup.py and the Markdown records. Use an
  independent default-false comparison switch, preserve original scalar
  comparison, test hit-heavy and miss/collision-heavy layouts, and inspect
  optimized ARM64 before a new build. Then one short iPad correctness run.
- Additional leads deferred: motion-only geometry hashing runs even when no
  temporal/debug consumer is active, but its sampled arithmetic regions total
  only ~0.08% app CPU. Repeated frame-buffer gpuAddress getters total roughly
  0.09–0.11% including dispatch/accessor symbols. Neither warrants priority
  over the key checks. Fingerprints remain required for mutation detection;
  no content-validation skipping or write-watch revival is proposed.
- No app source, control defaults or build changed in this audit. Temporary
  scripts/results use /tmp/nfsmw_key_compare* and /tmp/nfsmw_oct18_record_pcs*;
  essential results are persisted here. Await approval before implementation.

### October 18 — approved IPA22 attribute comparison experiment

- User approved the proposal. Added default-false restart-only
  `nfsmw_native_attribute_bulk_compare`, requiring attribute lookup ON. Its log
  identifies `base + bulk 32 bytes` or `scalar fields`, plus front-cache state.
- Initial full-40-byte production candidate passed correctness, but wider host
  benchmarks exposed early-base mismatch regression: 50.18 ms scalar versus
  54.66 ms bulk. Large-miss was also slightly slower (114.21 / 116.83 ms).
  Preserve this negative result; the earlier one-layout 51% gain was not general.
- Refined the approved change to reject different base addresses first and
  bulk-compare the remaining eight fields. Complete 40-byte identity remains
  required. No padding or alternate representations are permitted by static
  assertions; backing-map equality and mutation validation are unchanged.
- `python3 tools/native/test_attribute_lookup.py --benchmark` passed all four
  lookup OFF/ON × comparison OFF/ON configurations under ASan/UBSan and -O3.
  Coverage includes nine fields, every one of 320 bits, collision/fallback,
  rehash, same-frame mutation, live updates, actual sweep invalidation,
  reinsertion, ownership and 90,000 changing-key pairs per configuration.
- Seven alternating trials, 3,686,400 timed lookups per layout: scalar / final
  bulk medians in ms: small-hit 20.68 / 15.87; mixed 47.37 / 34.65; large-miss
  108.38 / 102.38; same-set 53.11 / 51.84; early-miss 49.66 / 47.95. All matching
  checksums/counters. These synthetic lookup gains (~2–27%) are not app or
  device energy gains. Full detail and prototype results are in TECHNICAL.md.
- Final iOS build passed with 13 existing FPSCR/UIScreen warnings. ARM64 shows
  both paths inline in Record, with base rejection then four 64-bit compare /
  conditional-compare operations in bulk mode. No comparison helper/library
  calls in either slot; scalar branch chain retained. ZIP CRC, signed-app
  executable match, strict deep codesign and all 104 unchanged Metal libraries
  against IPA21 passed. SDK and shaders were not edited.
- Packaging initially reached Python's unavailable hashlib.file_digest API;
  reran using streaming SHA256 successfully. A documentation patch context
  mismatch was corrected without changing the built source. Neither affected
  the app. An earlier full-40-byte build was superseded before named delivery.
- Device validation is pending with the settings/arguments above. Keep the new
  default false until results; no additional source optimization is approved.
- Implementation, expanded fixture and validation documentation committed locally
  as `7b848b1` on `battery-optimization`; no push. HANDOFF_CHATGPT.md remains
  untouched/untracked. Device validation is the next action.

### October 18 — first IPA22 device result

- Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_3_ipad.log`;
  user reports "still no issues". Renderer built Oct 18 19:11:46, consistent
  with final IPA22. New comparison logs base + bulk 32 with front cache ON;
  fused sizing, higher-bit GPU selector/statistics, Utility queue, lazy
  diagnostics, draw arena, texture masks, native copy patches and master
  group remain ON. No restart-only option was silently omitted.
- Log confirms scale 1.500 / cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0.
  Requested test was Battery mode OFF / system Low Power Mode OFF; no LPM
  suffix appears in the memory reports. No brightness/power trace provided.
- Driving 19:17:07.563 to background 19:18:18.581 (71.018 s). Applying five-second
  transition guards and requiring whole five-second windows gives 11 summaries /
  3,300 frames, all 60 FPS. Pacing 0/3,300 off-grid, worst 0.0 ms; all 33 thermal
  observations Nominal. No error/critical-level or GPU failure messages.
- Median recording 1.62 ms, encoding 9.56 ms (includes drawable waits), GPU 8.57 ms.
  Five wholly eligible 10 s CPU windows 81/81/91/100/89%, mean 88.4% of one core.
  Last-frame draw counts average 2,388.73 (not average draws over every frame).
  Attribute front-cache counters total 23,417,964 hits / 2,809,215 misses / 0 bypasses
  across guarded windows. These do not isolate key-comparison cost or establish
  a gain against IPA21; scene and sample variability prevent that inference.
- Initial loading hitch 41.5 ms shortly after driving contains 238 texture decodes,
  61,559 KiB / 32.0 ms; outside the guarded sample. Background transition produces
  301.5 ms encode with 295.8 ms drawable wait; exclude it and the following 56.8 FPS
  summary from gameplay performance. File-probe warnings persist; two traffic
  asset probes occur during driving, with no reported fault. Battery reports
  stay 65% throughout; quantized short-run readings cannot measure energy gain.
- Initial visual/correctness check passed; preserve the flag ON for accumulated
  testing and default false in source. No source/build change, no repeated
  test requested, no push. Sustained stability and device energy benefit remain
  pending. No further source optimization is approved by this log submission.

### October 18 — next measurement recommendation after IPA22 check

- User asks what comes next. Reviewed remaining candidates and existing power/
  CPU summaries. Last detailed profile is IPA20 at 0.85x / 30 FPS; IPA21 fused
  sizing and IPA22 bulk key comparison have since passed initial iPad checks.
  Their host timings do not establish app/device energy benefit.
- Old active profile has Record self5.394% /4.979%, RenderFrame self5.744% /
  7.495%, sub_82699100 self2.384% /2.027%, fingerprint self1.126% /1.025%
  (Low Power ON/OFF). Guest share remains broad, but prior small-copy paths
  already exist; don't infer all of it is waste or repeat completed patches.
  Fingerprints remain necessary. Previously deferred micro-work such as
  motion hashes and repeated GPU-address queries is only ~0.08–0.11% app CPU
  in that profile; no new implementation justified from these totals alone.
- Recommend a single current-build 8–10 minute recording at 1.5x /60 FPS,
  Battery mode and system Low Power Mode OFF, same accumulated flags including
  comparison and fused sizing ON, fixed manual brightness, unplugged wireless
  recording. Reuse the working Power Profiler + Time Profiler + Thermal State
  template. Usual race then pursuit; provide approximate transition timestamp
  and game log. No OFF arm or new build requested.
- This is a current-workload diagnostic to rank game-code, renderer and GPU
  effort; it cannot measure the optimization batch's gain against older traces
  with different resolution/FPS/content. Later energy attribution requires
  matched settings/workloads. No code, control defaults, SDK, IPA or parked
  diagnostics changed. Recommendation saved; recording pending user action.

### October 18 — IPA22 current power recording reviewed

- Inputs: October 18 `nfsmw_run_4_ipad.log` / `Power_Profiler_2_ipad.trace`.
  Trace UUID matches IPA22; all experimental controls confirmed ON. User
  confirms only final stretch as a chase; it overlaps about five minutes of
  the ten-minute recording. Split phases rather than mislabeling the earlier
  event or assuming ten chase minutes. Five-second guards at gameplay and
  recording boundaries leave 290.047 s primary sample. Detailed methods,
  inputs, model scores, CPU shares, instruction ranges and caveats saved in
  TECHNICAL.md. Exports and local analysis passed; no code or IPA changes.
- Constant 34% brightness, whole trace Nominal; charging table empty, GPU/clock
  tables have no rows. Modeled chase drain 31.956pp/hour, CPU impact11.088 vs
  GPU 2.273, display 5.731, network 0. These are not watts/additive shares and
  cannot attribute gains against earlier differently configured recordings.
- Primary chase 57 summaries at 60 FPS, 20/17,100 off-grid with 8.3 ms worst,
  medians recording 1.88 ms / encoding 5.10 ms including waits /GPU 4.08 ms;
  CPU log mean 94.36% of one core. No primary error-level lines or GPU failures.
  Earlier 19:28:15 watchdog/recovery is documented without inferring a confirmed
  image freeze; do not reopen parked phone isolation from it.
- Render task 35.77% inclusive, 99.97% of running weight on E cores already;
  game guest functions 26.52% self, Record 5.37% self, RenderFrame main 7.80% self.
  IOKit hot leaf resolves to user-client trap under command submission, not
  evidence of a removable spin loop. Repeating core-priority work is not next.
- Next proposed target-reference reuse removes some repeated string-tree
  searches while returning the existing live target. Total target operator[]
  self 1.042%, split encoding 1674 ms / setup 1067 ms / other 39 ms. Original maps, resource
  calls, target identity/resizing and ordering remain required. Full source
  scope and validation plan in TECHNICAL.md; no implementation yet. Await
  approval. No additional trace requested; preserve all current args meanwhile.

### October 18 — approved IPA23 target lookup work in progress

- User approved target-reference reuse. Added independent default-false
  `nfsmw_native_target_lookup` and separate frame-local caches for setup and
  encoding, only at the two identified primary-target call sites. MRT lookup,
  map order/identity, resize, resolves, resource operations and shaders unchanged.
- First implementation held an owned key string plus a pointer to the live
  Target, with original operator[] fallback. Extracted helper passed both OFF
  and ON under ASan/UBSan and -O3, 720,102 checks per arm: exact keys, temporary
  inputs, map insertion, mutations, resource rebinding/ownership, MRT aliases,
  separate traversals and 2,000 randomized frames.
- Seven alternating host trials, 4.8 million timed lookups in each workload:
  original/OFF/ON medians ms: one-target40.654/40.540/14.345;
  runs43.237/43.224/17.934; short-runs46.811/45.751/23.562;
  alternating42.623/42.576/51.428; many-targets95.818/101.683/116.694;
  long-keys58.420/58.601/31.241. Matching checksums/draw updates/map sizes.
  Miss-heavy regression is real in this fixture; no universal speedup claim.
- Refined the cache to borrow the map node's full key and live value together.
  ON miss uses try_emplace(requested) with no mapped arguments, equivalent to
  the default insertion of operator[], and avoids copying a second key. OFF
  still calls original operator[]. Map owns all objects; pointers remain valid
  across insertions; caches never cross traversal/frame boundaries. This is
  within the approved exact-lookup reuse scope, not a new identity policy.
- Also moved randomized fixture map-clears to the beginning of each frame,
  after previous caches are destroyed, to model the stated lifecycle precisely.
  Final extracted tests/benchmarks running; iOS build and device check pending.

### October 18 — IPA23 final host/build validation

- Refined borrowed-node helper passed `python3 tools/native/test_target_lookup.py
  --benchmark`: OFF and ON under ASan/UBSan (-O1) and again at -O3, 720,102 checks
  per configuration, two traversals over 2,000 randomized frames. Actual helper
  extracted from renderer; the fixture uses CPU stand-ins for mutable Target
  fields/resources and checks intended integration sites. It does not test
  actual Metal resizing/rendering; that requires the pending device run.
- Seven alternating trials / 4.8 million timed calls each; original/OFF/ON
  median ms: one-target40.652/41.035/13.901; runs43.246/43.117/17.504;
  short-runs45.591/45.946/23.986; alternating43.467/43.470/49.813;
  many-targets103.638/95.403/106.385; long-keys57.507/57.495/30.348.
  All checksums, draw updates and entry counts match. ON gains ~47–66% versus
  current OFF in repeated-target fixtures, but costs ~15% on alternating /12%
  on many-targets fixtures. Control timing varies; this is not a device-address
  replay, app-wide gain or energy result. Retain default false pending device.
- Final iOS build passed with 13 existing FPSCR/UIKit warnings. ARM64 retains
  inline helper logic at both sites: full length/byte equality; hit returns
  existing node's live Target and branches around tree lookup. String equality
  uses a byte-compare call; don't claim the entire hit is call-free. OFF and
  ON-miss reach the same default-insertion tree routine. No outlined custom
  TargetLookupCache or flag helper call per draw; flag selected once/frame.
- ZIP CRC, strict deep codesign, packaged executable equality to signed app,
  all 104 .metallib payloads and bundled dylibs identical to IPA22 passed.
  UUID/SHA256 above. Only native_renderer.mm changes production behavior;
  SDK, guest and shaders unchanged. No provisional named IPA23 was delivered.
- Log identifies `[native] target lookup: frame-local last target` when ON,
  `original map` OFF, with exact-key/live-target/restart wording. Keep prior
  flags and add only `--nfsmw_native_target_lookup=true` for one short normal
  settings iPad check. No stacked next implementation, repeat power recording,
  push or release. Device visual/stability and energy validation pending.
- IPA23 source, fixture and evidence committed locally as `5e612c8` on
  `battery-optimization`. No push; original HANDOFF_CHATGPT.md remains
  untouched/untracked. Initial iPad device check is the next action.

### October 18 — first IPA23 iPad validation passes

- Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_5_ipad.log`
  (1,544 lines), user reports "still looks jsut fine". Renderer build Oct 18
  19:48:54; periodic mode confirms frame-local last-target lookup. Previous
  fused sizing, bulk attribute comparison/front cache, mixed GPU selector and
  counters, Utility queue, lazy diagnostics, copy patches, masks, arena and
  master group retained. No production changes or new IPA in this analysis.
- Settings logged: scale 1.500 / cap 60, MetalFX OFF, FXAA OFF, forced MSAA 0.
  Requested Battery mode and system Low Power Mode OFF; no LPM suffix appears.
  No brightness/power trace accompanies this short correctness run.
- Driving 20:01:56.374 to background 20:03:10.142 (73.768 s). Five-second guards
  with complete five-second summary windows give 12 summaries / 3,600 frames,
  all 60 FPS. Pacing 0/3,600 off-grid, worst 0.0 ms; all 33 thermal samples Nominal.
  No error/critical lines or GPU failures. Six file-probe warnings occur in
  guarded gameplay; no associated visual/stability problem reported.
- Median recording 1.455 ms, encoding 7.51 ms (includes drawable waits), GPU 4.12 ms.
  Five wholly eligible 10 s CPU intervals 82/78/80/96/90%, mean 85.2% of one core,
  median 82%. Mean last-frame draws 2,376.5 (not mean of every frame). Different
  scenes/samples from IPA22 prevent isolated speed or energy attribution.
- Loading hitch 41.7 ms just after entering driving contains 241 texture decodes,
  61,673 KiB / 31.9 ms; outside guard. After backgrounding, encoding 282.9 ms includes
  275.3 ms drawable wait; exclude transition. Battery reports 55% then 50% in a
  single coarse step; this short, uncontrolled integer reading is not evidence
  of an optimization gain or regression. Do not extrapolate its delta/hour.
- Initial visual/correctness check passes. Keep new flag ON for accumulated
  testing, default false. No repeated check/build/new power trace requested.
  Sustained stability and energy gain unproven; no next implementation approved.
  All findings saved here and in TECHNICAL.md. No push or release.

### October 18 — next proposal after IPA23 validation

- User asks "next?". Rechecked unchanged PipelineCache ready lookup in current
  source against UUID-matched IPA22 profile: confirmed-chase hash/find region
  0x10007b998..0x10007bc00 (exclusive) is 1,850 ms / 266,762 ms = 0.6935% app CPU self.
  This excludes ARC/callees and other pipeline work; not wholly recoverable.
- Get hashes/searches ready_ before the later encoder-state check suppresses
  redundant setRenderPipelineState calls. A previous-ready-entry fast path can
  avoid the search on consecutive exact keys without removing any draw/state
  operation. Current ready_ inserts successful non-nil PSOs, never erases them,
  and preserves existing entries on duplicate compilation. Node addresses
  survive rehash; only the serial renderer updates ready_ via Get/Collect.
- Proposed independent default-false pipeline-lookup switch, read once per
  RenderFrame and passed into Get. Compare all PipelineKey fields using its
  existing operator==; do not reuse raw 40-byte attribute-key comparison,
  because PipelineKey has bool/padding. Borrow ready map node, not another
  strong PSO copy. Update fast path only after a successful ready-map lookup;
  no caching nil, failures or compilation-pending returns. Original miss path,
  failed out-parameter behavior, warmup/collection and ownership preserved.
- Production scope: native_renderer.mm only; add
  tools/native/test_pipeline_lookup.py plus documentation. Validate full keys,
  hits/misses, failed/pending-to-ready transitions, duplicate completion,
  rehash/stable live entries and original fallback. Benchmark repeated and
  all-miss workloads including switch overhead, inspect ARM64, retain default
  false and get short device check if evidence supports a build.
- No new source, IPA or device measurement made/requested. This is another
  modest CPU opportunity, not a large battery reduction claim. Recommend one
  matched accumulated-batch power comparison after this step rather than
  continuing an unlimited chain of micro-optimizations. Await implementation
  approval. Archive persistence and capture remain separate parked work.

### October 18 — approved IPA24 ready-pipeline experiment in progress

- User approved last successful ready-entry reuse. Added independent default-
  false `nfsmw_native_pipeline_lookup`, selected once/frame and passed to Get.
  Templated pointer-only cache borrows the existing owning ready-map node;
  exact existing field equality, no padded-object byte comparison. Successful
  ready-map results alone populate it; pending/failure paths unchanged.
- Added tools/native/test_pipeline_lookup.py. It extracts actual production
  key/helper/Get/Finish and compares to Get from Git 8623510, with Foundation
  stand-ins for Metal compilation. Source guards enforce unchanged entire
  miss suffix, Finish and Collect, plus sole caller/frame-mode integration.
- Initial fixture had two bugs: a stand-in class reused Metal's runtime class
  name, and randomized rehash doubled without a bound. Stopped the owned test
  PID 57211, renamed descriptor stand-in and bounded rehash 256–1280. Stopping
  required sandbox escalation; it succeeded. This is a fixture failure, not
  an application run/crash. Preserve this result; reran corrected validation.
- Corrected OFF/ON tests passed at -O1 ASan/UBSan and again at -O3, 60,456
  differential checks/configuration. Tests include all 11 key fields, collisions,
  rehash, incoming failed-output preservation, actual sync success/failure/
  exception, missing descriptor, async demand/warm/publish/duplicate completion,
  failed-to-ready precedence, 500 frames/60,000 randomized requests and weak-
  reference proof of no second cached PSO owner.
- Seven alternating host trials /4.8 million timed requests each, original /
  OFF /ON medians ms: one102.234/103.070/88.889; runs108.969/110.001/90.274;
  short-runs121.873/124.658/109.204; alternating136.693/139.533/139.544;
  many138.065/140.929/141.491; late-mismatch125.129/127.886/151.610.
  Matching checksums/ready counts/zero compiles. About 12–18% faster versus OFF
  in repeated-key fixtures, negligible change on two early-mismatch layouts,
  ~18.6% slower when late fields differ every request. No universal/app/device
  speed or energy claim. Retain default false; iOS build now underway.

### October 18 — IPA24 final validation and delivery

- Corrected fixture completed successfully: actual Get/Finish OFF/ON at -O1
  ASan/UBSan and -O3, 60,456 differential checks per configuration. Method
  suffix/Finish/Collect unchanged against 8623510; helper field equality and
  shared map-owner semantics retained. Foundation stand-ins test ARC and
  control transitions, not actual Metal compilation or GPU rendering.
- Optimized iOS shows helper/Get fully inline in RenderFrame. Flag is loaded
  once/frame; chain compares all 11 fields, including bool as one byte, and
  matching entry jumps past hash/find. No custom helper/Get call per draw.
  Original ready-map search remains for OFF and mismatches. Cache hit returns
  same owned PSO; no extra reference stored. No source edit after passing tests.
- Build passed with 13 existing FPSCR/UIKit warnings. ZIP CRC and strict deep
  codesign passed; packaged executable matches signed cache app; all 104 Metal
  libraries and both SDK dylibs byte-identical to IPA23. UUID/SHA256 above.
  Source scope native_renderer.mm only; SDK, guest, shaders/defaults untouched.
- Log `[native] pipeline lookup: last ready entry` ON, `original map` OFF,
  exact-key/ready-only/restart wording. Device check pending: one short normal
  iPad event with new flag ON and all old flags kept. No push/release.
- After correctness, use accumulated four-change comparison, not another
  isolated tiny A/B or new cache proposal. Keep 1.5x / 60 FPS, brightness,
  system LPM OFF, Battery mode OFF, old experimental stack and comparable
  gameplay fixed. Four independent restart-only flags all ON versus all OFF;
  master battery group unchanged. Energy improvement remains unproven.
- Source, extracted Objective-C++ fixture and validation record committed locally
  as `9474672` on `battery-optimization`. No push; HANDOFF_CHATGPT.md remains
  untouched/untracked. Initial IPA24 device check is next.

### October 18 — IPA24 first device validation and batch measurement protocol

- Input: `/Users/bep1s/Desktop/debug/18 October 2026/nfsmw_run_6_ipad.log`;
  user reports "everything is fine". 2,742 lines, last timestamp line partial;
  use 2,741 complete timestamp lines. Renderer built Oct 18 20:14:16, consistent
  with IPA24. All 23 pipeline-mode observations identify last ready entry.
  Target reuse, bulk comparison/front cache, fused sizing and prior stack ON.
- Driving 20:21:32.432 to background 20:22:51.576 (79.144 s). Five-second guards
  give 20:21:37.432–20:22:46.576; accept complete five-second metric/pacing
  windows and ten-second CPU intervals inside them. 13 summaries/3,900 frames,
  all 60 FPS, pacing 0/3,900, worst 0.0 ms. All 39 thermal observations Nominal.
- Median sampled recording 1.49 ms, encoding 8.64 ms (includes drawable waits),
  GPU 4.12 ms. Six CPU windows 81/80/92/96/100/81%, mean 88.33%, median 86.5% of
  one core. Mean last-frame draws 2,396.62. Differences from prior short scenes
  cannot isolate the shortcut or establish regression/gain.
- No error-level messages during driving or GPU failures anywhere. Two
  watchdog/semaphore groups at 20:21:09.460 and 20:21:26.508 are before driving;
  don't call the whole file error-free or reopen parked phone isolation.
  Loading hitch 41.2 ms at 20:21:32.500 includes 243 texture decodes / 61,871 KiB /
  32.3 ms and lies outside guarded gameplay. Battery logs stay 50%, no power
  trace supplied; this is correctness, not an energy measurement.
- Initial visual/correctness check passes. No source/build changes or repeated
  short test needed. All four recent flags remain default false and test ON.

Recommended next test, same IPA24 in both arms (not performed yet):
1. Preserve all earlier Extra Args and settings. Replace only the four existing
   entries below with false, avoiding duplicate true/false entries. Keep master
   battery group, attribute lookup and other prior experiments unchanged.
2. Fixed 1.5x / 60 FPS, Battery mode OFF, system Low Power Mode OFF, same manual
   brightness, connectivity and starting thermal state; unplugged via working
   wireless recording. Same Challenge Series pursuit from its beginning.
3. Record 8–10 minutes of chase using the working Power Profiler + Time Profiler
   + Thermal State template, starting the recording once gameplay begins. Save
   game log too. Avoid mixed events/menus so most time is comparable gameplay.
4. Change the same four entries to true, fully force-quit LiveContainer and
   repeat the same pursuit/conditions and recording. Cold restart both arms.
   Let the device return to a comparable thermal state before the second run.

```
--nfsmw_native_fused_upload_sizing=false
--nfsmw_native_attribute_bulk_compare=false
--nfsmw_native_target_lookup=false
--nfsmw_native_pipeline_lookup=false
```

This measures the recent four-change batch, not the entire battery branch.
Do not change nfsmw_battery_optimizations or clear Extra Args. Full independent
switch names matter; the master does not control these. Compare model power,
CPU instruction/running work, FPS/pacing and thermal/brightness coverage. Chase
variation and run order still limit inference; one inconclusive pair does not
justify discarding individually correct changes. No new recording requested
for just one tiny change, no push/release or next source approval.

- User then said "continue" after the validation update. Next action is to
  carry out the documented same-build batch comparison; provide OFF/ON
  instructions and await paired logs/traces. No arm has been recorded/analyzed
  yet, and no additional source implementation was requested.


October31 interface check command (host only; synthetic interface inventory,
actual selector): `python3 tools/ios/test_lan_interface.py`. No runtime flag;
hosting prefers active private hotspot bridge, falls back to en0 Wi-Fi.


### Experimental original-PC LAN investigation (multiplayer only)

These are diagnostic/experimental tools, not accepted PC cross-play. Requires
original Windows game hosting a LAN room and server.dll/server.cfg. On the PC
with Python3, run from this checkout (replace192.168.1.10 with actualPCIP):

```sh
python tools/ios/pc_lan_probe.py --audit "C:/Games/Most Wanted"
python tools/ios/pc_lan_probe.py --directory 192.168.1.10 --profile xbox
python tools/ios/pc_lan_bridge.py --bind 192.168.1.10 --pc-host 192.168.1.10 --seconds 600
```

Phone launcher Join that PCIP, distinct name, then XboxLive/QuickMatch. Keep
native PC LAN host/game active. Bridge exits after600s, Ctrl-C stops earlier.
PC directory9900 is untouched; bridge usesTCP30960/TCP+UDP10902 on --bind only.
Phone lobby connects DIRECTLY to originalPC9900. Bridge preflight only verifies
host directory health and reserves names among bridge clients; cannot detect
names of clients that bypass bridge. Use unique names. No packet injection or
race translation. Preserve both logs/capture if lobby/race fails; do not expose
these services publicly. No compatibility promise based on a visible lobby.

Host checks:
`PYTHONPYCACHEPREFIX=/private/tmp/nfsmw-pc-python-cache python3 tools/ios/test_pc_lan_probe.py`.
Passive originalPC discovery capture (one bounded60s maximum):
`python tools/ios/pc_lan_probe.py --listen 30` listens UDP9999, prints validated
384-byte gEA announcements, does not broadcast a fabricated host.

Mac original-DLL-only test reproduction (no PC racer): create disposable
CrossOver bottle `'/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/Multiplayer/nfsmw-pc-crossplay-bottle'` with cxbottle --create
--template win10_64; APFS clone original folder to /private/tmp gamecopy; build
own PE with `python3 tools/ios/pc_lan_server_harness.py --dll '/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/Multiplayer/nfsmw-pc-crossplay-game/server.dll' --output '/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/Multiplayer/nfsmw-pc-crossplay-game/pc_server_probe.exe' --seconds 30`.
Run CrossOver wine --bottle thattemporarypath --no-gui --workdir gamecopypath
pc_server_probe.exe. Needs copied server.cfg in working directory. Probe actual
bindIP from Wine log (not127.0.0.1: DLL may bind LAN only). All source game files
read-only; don't repurpose existing BeamNG bottle. No system settings changes.


### Preview6 native PC test and checks

The older Pythonbridge ZIP is diagnostic history; preview6 does not require it.
Create/keep a LAN room open in original PC Most Wanted; on iOS Join/Search (or
manual currentPCIPv4), launchXboxLive→QuickMatch. UsesoriginalPC TCP9900. New
adapter listensONLY127.0.0.1:30960 onthephone. Do notenter127.0.0.1 yourself.
LANenabledonlythroughHost/Join; singleplayerstilloff. PCmodeautodetected byvalid
native9900directory. Searchalsoqueriesmobile30960 whenUDPmobilehostsfound,
4sTCPbudget/64concurrentprobes, maxnearby/24. No restrictedmulticastentitlement.
OfflinePCmode startswith emptyXbox-stylelocalLANhistory; noofficial/PCaccount
history claimed, norecordsuploaded. NativePCroomfilters/session/raceformats
remainnextgate, noforcedversion/contentconversion.
`python3 tools/ios/test_pc_gateway.py` exercisesactualC++adapter withASan/UBSan.
`python3 tools/ios/test_lan_setup.py` includesPCpreflightwithout10902.
Existingmultiplayer.py nowalso tests fragmented/tabseparatednative9900reply.
Buildremainsisolatedcmake--build/Users/bep1s/Library/Caches/nfsmw-ios/build-0.6--targetipa.

### Preview7 PC room filter regression

Alongside the preview6 checks, run:

```sh
python3 tools/ios/test_pc_room_filter.py
python3 tools/ios/test_pc_gateway.py
```

The first requires the ignored generated USA code and compiles its actual
sub_82546178 with bounded memory/dependency stubs. It tests version rejection
before QoS and acceptance after the captured PC tag alias, not a real peer.
The gateway check needs permission for bounded local TCP listeners. Both use
ASan/UBSan. Build uses the existing isolated IPA command; install the uniquely
named preview7 IPA, leave the PC in an existing LAN room, select Quick Match.

### Preview8 PC session/address decoder check

```sh
python3 tools/ios/test_pc_session.py
```

Requires ignored generated USA files. Compiles the actual session decoder
sub_82826978 and address decoder sub_82826890 against bounded memory, ASan/UBSan.
Checks PC host IP/MAC, separate Binary7 block boundaries/key/ID, stable lobby
updates, different game identities, existing session and unknown address
preservation. Run alongside gateway, room-filter and preflight checks above.
No real peer, PC racer or race is emulated by this check. Existing isolated IPA
build command unchanged. Preview8 device flow same as preview7; observe peer
connection before starting a race. No PC-side helper.

### Preview9 PC transport hook check

```sh
python3 tools/ios/test_pc_udp.py
```

Compiles actual USA game_pc_udp.cpp with bounded guest memory/capture stubs,
ASan/UBSan. Checks captured 8byte headers both ways, unchanged payload/original
send buffer, retry/error return and stack preservation; bypasses LANoff,
nonselected mobile peer, non-CommUDP caller, voice/other port, short packets.
Only original PC endpoint passed to native PC Start is eligible; Stop clears
it atomically. Native adapter remains required for this transport experiment.
No SDK source patch or codegen step added; existing isolated build command.
Check executable nm shows strong sub_8282A4F0/sub_8282A5A0 and original __imp__
entries. Device handshake and race remain acceptance tests, not host stubs.

### Preview10 handshake ID regression

Existing test_pc_udp.py now covers the captured PC opcode5 listener ID,
subsequent INIT mapping, local-ID reply mapping and DATA ACK preservation.
test_pc_gateway.py covers endpoint isolation and Start/Stop ID-cache clearing.
Existing build command unchanged. Observe `[pc-udp] PC listener connection ID
learned` in boot and nonzero matching ID in actual outgoing UDP wire capture.
Success still requires the game's real handshake and race, not a trace line.

### Preview11 PC race-loader diagnostics

```sh
python3 tools/ios/test_pc_race.py
python3 tools/ios/test_pc_udp.py
```

Existing isolated build command unchanged. Diagnostic factory hook only runs
with nativePCadapter active and callerLR82474944; cap8calls, log before/after
original without replacing result. Header hooks log max32initial packets per
RX/TX when length33–2048, complete normalized guest header and original payload.
With Logging enabled obtain BOTH boot.txt and nfsmw.log after a PC race load;
boot contains [pc-race]/[pc-packet] lines absent from normal96byte kernel dumps.
This is a diagnostic build, not a crash fix. No mobile/gameplay result changes.

### Preview12 PC native car field regression

```sh
python3 tools/ios/test_pc_car.py
```

Compiles actual USA game_pc_car.cpp hooks with original bitstream capture
stubs andASan/UBSan. Captured4bytecarID plus typed408byte customization map,
roundtrip/padding/handle/savedbuffer preservation, PCoff/othercallsite/bitwidth
bypass. Unexpectedreadlength retained/logged, not falsely claimed protected
from originaldecoder's unchecked length. Existing isolatedbuild unchanged;
no new codegeneration/SDK patch. Observe [pc-car] conversion and [pc-race]
factory results inboot after PCrace load. Existing rawpacketdiagnostics kept.
