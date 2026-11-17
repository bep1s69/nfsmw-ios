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

- November14 (Stefan, latest): finish processing current Desktop power pair and
  prepare shared-record handoff back to Claude. Current power testing conditions
  differ from earlier sessions: compare ONLY this pair, never against prior power
  recordings, and do not add its percentage to older savings. Archive/verify/
  delete supplied Desktop inputs as usual. No new implementation/build during
  handoff preparation.


- November14 (Stefan, latest): target the lowest sustainable energy/operating
  level that preserves the selected resolution and FPS across ALL supported
  devices. Prefer efficiency cores and lower operating clocks where deadlines
  allow; scheduling must adapt to device/cap/workload, with performance headroom
  when required. Core placement/clock requests are not themselves proof of lower
  power; use measured pacing/audio/energy. No claim all algorithms are exhausted.


- November14 (Stefan, latest): consolidate tested/proven changes as defaults and
  shift active optimization work to scheduling, thread dependencies, multithreading
  and QoS while preserving current FPS/visuals/audio. Pause further CPU/GPU shader/
  cache micro-optimization audits; supersedes GPU-only priority/normalmapped next
  action. Promote accepted configurations, not merely tested or negative trials.
  No assertion that all possible CPU/GPU optimizations are exhausted.


- November14 (Stefan): agrees to prioritize GPU investigation; CPU is acceptable
  for now. Preserve current performance/visuals, use existing evidence first.
  This is a priority decision, not proof the CPU has reached its ceiling.

- November14 (Stefan, latest): also DELETE supplied Desktop traces after archival
  and per-file size/SHA256 verification, just like Desktop game logs. This
  supersedes preserving those Desktop trace originals. Never delete before
  successful verification; keep dated Debug archives and non-Desktop originals.


- November 11 (Stefan, latest): ALWAYS delete the game log he provides on the
  Desktop after copying it to the capture-date Debug folder and verifying
  archived bytes/hash. This is now a standing instruction for supplied Desktop
  logs, superseding the earlier dev122 per-file-only interpretation. Never
  delete before successful archival/verification; preserve traces and archives.


- November 11 (Stefan): logs/traces must be saved into the dated local Debug
  folder, not left only in chat attachments/Desktop/Downloads. Archive and
  hash-verify received evidence before analysis and document its exact path.
  Use the capture's Europe/Bucharest calendar date; create the new date folder
  after midnight. Preserve originals and earlier dated archives. November11
  audit verified all7recent dev115–118 inputs in November10; dev119 midnight
  trace/log copied and verified into November11. Don't claim those earlier
  files were missing/lost or silently move their originals.

- November 11 (Stefan): wait until he is back at his Mac for the next dev119
  check; he offers Time Profiler and Power Profiler. Supersedes requesting
  another phone Detailed capture now. First inspect Time Profiler+game log;
  only use one same-sitting power A/B when CPU/correctness supports it.

- November 10 (Stefan): approved continuing the larger draw-data/geometry
  handoff work after dev118 analysis. Preserve current validation/performance;
  continue isolated local trial, no push/merge/release.

- November 10 (Stefan, latest): currently has no laptop access. Use phone-only
  Performance Trace collection; do not require a tethered Mac/Instruments run.
  Screenshot offers System Activity (Detailed)/(Summary), Power Profiler and
  Lookback Collection, ordinary LiveContainer monitored.

- November 10 (Stefan): from the next build onward add master game-audio mute,
  preferably also toggleable from the in-game menu, for listening to personal
  music without adjusting every original game volume. Continue battery work.

- November 10 (Stefan): dev115 picture/gameplay looked normal except heavy
  freezes. Prepare graphics pipelines before launching the game rather than
  interrupting gameplay. This explicitly reopens the archive/warmup work for
  the observed freezes; preserve caches/data and avoid another battery test
  until this correctness/performance problem is addressed.

- November 10 (Stefan): approved starting the concrete stage-1 native frame
  ownership/Metal command-reuse implementation. Work stays isolated on
  `codex/native-frame-command-reuse`, default-off trial; preserve current
  FPS/pacing/visuals and validate CPU work before another battery pair.
  No push, merge or release authorized.

- November 10 (Stefan, latest): reduce battery use as far as practical while
  preserving current performance and visuals. A longer project changing more
  of the game toward a native iOS port is acceptable; remove Xbox 360
  compatibility work where feasible. Approved the renderer source-level
  design/feasibility pass. Current concrete proposal and staging:
  docs/NATIVE_D3D_PLAN.md. This supersedes treating native-D3D as permanently
  parked for lack of interest; no specific implementation approved yet.

- November 10 (Stefan): iPhone at the 40 cap runs on the efficiency cores
  (Eco-like, almost perfect as measured Nov 9). He does not accept that 60
  cannot be improved: proposed next is promoting one thread at a time to the
  performance cores (smallest set that holds 60); native D3D layer remains
  the large later lever. Awaiting his OK for dev113.

- November 10 (Stefan): power tests must be few. Use one A/B pair in one
  sitting (within-sitting spread ~0.5 %/h); never compare runs from
  different sittings.

- November 9 (Stefan): abandon the Eco/Balanced/Max performance profiles
  (clunky, do not work as expected). New target for battery work: hold the
  selected FPS cap (30/40/60/120) consistently with the least power, scaling
  automatically. No code changes until the measurements support a design.

- November 6 (Stefan): ship 0.6.0 at dev107 scope. Battery and thermal
  work is done for this release. The RAM reduction is demonstrated on
  tested hardware. Leave low-RAM compatibility testing to players with
  those devices. Onboarding is accepted and both menus ship as an interim
  design ahead of 1.0. Defer free camera and remaining Extra Options.

- November 6 (Stefan): approved the step 4 menu and onboarding design.
  Invert menu swipes by default and give Longest battery a 30/40 fps choice.
  Keep Half rate as the default for Longest battery, with Every frame
  selectable on its card. The rear-view mirror cadence is still unverified.

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
cmake --build /Users/bep1s/Library/Caches/nfsmw-ios/build-0.6 --target ipa -j 12
```

Current branch uses `/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk` and
`build-0.6`, as did dev125. The ordinary preset/cache `build` is stale for this
branch: November13 regeneration correctly rejected its shared SDK. Do not bypass
that guard or patch the shared SDK. The historically documented build directory
was `/Users/bep1s/Library/Caches/nfsmw-ios/build`;
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

## Claude note — November 16, 2026 (read-only, scheduling start)

Stefan approved continuing with device-adaptive scheduling. Log review of the
dev129 power pair (`14 November 2026/dev129_reference_vs_render_utility_power_nfsmw.log`):
run B's User Initiated escalation at 17:37:07.018 is a cap-controller artefact,
not trial feedback. Driving began 17:37:06.958 with m already at the start level
(Default), so the dev110 start reset did not clear the late window; world-entry
hitches (frame 1685: 231.1 ms, 167 textures decoded, under the 250 ms stall
filter) supplied the 3 late frames 30 ms after the drive started, and the level
cannot step down while driving. Run A did not get 3 late frames at its start and
stayed Default. Run B was therefore UI main/CP/workers + Utility render, against
A's Default everywhere; the -11.5% stays unattributed. Proposed next step (awaiting
Stefan): clear the late window and ignore hitch frames for ~2 s at every drive
start, then design per-role levels (main, GPU commands, workers, render, audio)
raised by stage attribution instead of one shared mode. No code change yet.

dev130 (Stefan approved step 1, Nov 16): `nfsmw_drive_start_grace_ms` (default
2000, 0 = dev129) in the cap controller: each drive start clears the late window
and ignores late frames for the grace period, whatever level loading left. Log
lines `[scheduling] dev130 drive-start grace` (startup) and `[cap-controller]
driving: late frames ignored for N ms`. Render Utility trial unchanged and still
opt-in. `tools/ios/test_render_qos_trial.py` PASS (baseline check now strips the
dev130 hunks). build-0.6 ipa exit 0, deep codesign pass, marker string in binary.
IPA `ios/build/NFSMW-0.6.1-dev130-drive-start-grace.ipa`, SHA256
2ca156caf00ad29a9e9169be2830da730c0f950b1c1ce5dee1c7bfaaa06513a1, copied to
Desktop (dev129 removed from Desktop, kept in ios/build). Next: Stefan checks
that drives start at Default without an early User Initiated jump; then
same-build power pair trial OFF/ON with matched brightness.

dev130 device check (Nov 16, iPhone, log archived as `16 November 2026/
dev130_drive_start_and_40fps_nfsmw.log`, SHA256 2d452cff...6a72, Desktop copy
deleted after verification): drive 13:37:01.557-13:38:49.292 at 60 started at
Default with the 2000 ms grace and never stepped up (108 s); pacing 0-4 of 300
off-grid, CoreAudio 0 gaps. Step 1 works.
Same log, Nov 16 00:34-00:57 session (dev129, render trial on but inert at 40):
the two visible drop bursts (00:45:52 pacing 57/300, worst 116.7 ms; 00:54:15
56/300) coincide with system-wide paging ("system VM in 1.1 s: 1822 swap-ins,
8702 compressions"; 1883 swap-ins at 00:54) while the game's footprint stayed
~1.45-1.55 GiB with ~4.6 GiB headroom: memory reclaim by iOS, not game load or
the controller. CoreAudio reported 0 gaps all session, so the audio fault is not
output starvation; unattributed pending Stefan's timing/description. Vigilante
"5 s no register moved" alerts at 00:40:39/00:46:22 fired during perfect pacing
(false positives).

dev130 render-trial power pair (Nov 16, iPhone 17 Pro Max, same sitting, both
dev130, 60 cap/1x/no AA/MetalFX off, brightness 27% in BOTH traces (fixed),
no charging rows, thermal Nominal). Archive: `16 November 2026/dev130 render
trial power pair/` (two .aar SHA 43f21e72.../a63a9d29..., nfsmw.log SHA
3ebafee9...; Desktop originals deleted after verification; extracted .atrc).
A trial OFF trace 13:45:42.284 (drive 13:45:47.870-13:49:00.415); B trial ON
(`--nfsmw_render_utility_trial=true`, cold restart) trace 13:53:27.941 covering
B's SECOND drive 13:53:30.188-13:56:51.627. Windows: drive start +15 s to drive
end. Parser: xctrace export SystemPowerLevel / ProcessSubsystemPowerImpact,
duration-weighted (scratch pp.py/sub.py).

| | A OFF | B ON (all) | B before UI | B after UI |
|---|---:|---:|---:|---:|
| system drain %/h | 37.43 | 30.30 | 35.27 | 26.73 |
| LiveContainer CPU impact | 28.52 | 19.29 | 24.69 | 15.42 |
| GPU impact | 4.14 | 4.29 | 4.51 | 4.12 |
| display impact | 2.00 | 2.00 | 2.00 | 2.00 |
| instructions G/s | 8.67 | 8.84 | 9.02 | 8.72 |

-19.0% system drain with brightness, GPU and instruction rate matched; nearly
all CPU. A stayed Default all drive; B started Default and stepped up to User
Initiated while driving at 13:55:03.175 (3 late frames, genuine, not loading),
and the lowest drain came after that (main/CP/workers UI + render Utility).
Pacing both clean (0-1/300 typical). Log "% of a core" rose in B (inflated by
slower cores; consistent with more work on E cores, not measured here).
Remaining confounds: fixed order A then B; B is its launch's second drive.
Hypothesis (unproven): encoding on Utility frees P-core time for the frame
threads and lowers the cluster's operating point. Proposed next: dev131 makes
the render Utility trial default and adds an opt-in "drive starts at User
Initiated with render Utility" variant; one pair with the variant FIRST.

dev131 (Stefan approved, Nov 16): `nfsmw_render_utility_trial` default TRUE
(false = dev130 behaviour); new opt-in `nfsmw_drive_start_user_initiated`
(default false, restart): where a drive's start level is Default, it starts and
stays at User Initiated. Startup markers `[scheduling] dev131 ...`. Test
`test_render_qos_trial.py` PASS (baseline strip extended). Build exit 0, deep
codesign pass, marker in binary. IPA `ios/build/NFSMW-0.6.1-dev131-render-utility-default.ipa`
SHA256 5cb8007d152adcc50b7bcc2c578f06e4790a6de449794bd02c8e8ca4e037766c, on
Desktop (dev130 removed from Desktop). Requested pair, same sitting/brightness:
run 1 `--nfsmw_drive_start_user_initiated=true`, run 2 empty Extra Args.

dev131 pair result (Nov 16 14:06-14:13, iPhone 17 Pro Max, brightness 26% both,
no charging rows, Nominal). Archive `16 November 2026/dev131 drive-start UI power
pair/` (.aar SHA 3c8d6d03.../59c96510..., nfsmw.log ffee4c2d...; Desktop copies
deleted after verification). Windows drive start +15 s to drive end.

| | run 1 variant ON (UI whole drive) | run 2 dev131 default |
|---|---:|---:|
| system drain %/h | 23.7 | 24.0 (Default part 24.5, after UI step 23.7) |
| CPU impact | 14.01 | 14.51 |
| GPU impact | 3.96 | 3.82 |
| instructions G/s | 8.69 | 8.79 |

Variant -1.2%, within noise: no reason to add it; stays opt-in/off. Run 2
stepped up to UI at 14:11:48 (genuine late frames) and its UI part equals run 1.
Pacing clean in both (no 300-frame window with more than 5 off-grid). Absolute
levels (~24 %/h) are far below the 13:45 pair (30-37) one hour earlier, so the
sitting-to-sitting drift rule holds; do NOT combine across sittings. Decision:
keep dev131 defaults (Default drive start, render Utility during boosts).
Next: device-adaptive confirmation, render trial OFF/ON pair on iPad and at
other caps (120, 30/40 where the trial is inert by design).

dev131 iPad pair (Nov 16 14:19-14:26, iPad Pro M4, 6 E cores, 1.5x/60, brightness
27% both, no charging rows, Nominal). Archive `16 November 2026/dev131 iPad
render trial power pair/` (.aar 1cd835bf.../bfc37b42..., nfsmw.log d5602bcf...;
Desktop copies deleted after verification). Run 1 trial OFF 22.89 %/h (CPU 4.68,
GPU 2.77, display 5.32, 8.41 G instr/s); run 2 default/trial ON 22.76 (4.71, 2.78,
5.28, 8.51). Both drives stayed at the 6-E-core start level Low (Utility) with no
step-up, so the trial (acts only at boost levels) never engaged: effectively an
A/A check, -0.6% noise, pacing clean (no window over 5 off-grid). Conclusion:
iPad at 60 already runs everything on Utility; the dev131 default is harmless
there. The lever matters on 4-E-core iPhones (Default start at >40). Remaining
device-adaptive gap: 120 cap (iPhone Default/UI, iPad Default) untested.

dev131 iPhone 120 pair (Nov 16 14:36-14:46, iPhone 17 Pro Max, 1x, brightness 27%
both, no charging rows). Archive `16 November 2026/dev131 iPhone 120 render trial
power pair/` (.aar 5ff2ac69.../7bc0df6f..., nfsmw.log cc0b5db7...; Desktop copies
deleted after verification). Run 1 trial OFF: drive 14:36:56-14:40:16, Default
then UI from 14:38:45 (genuine). Run 2 trial ON (default): drive 14:42:54-14:46:08,
UI from 14:42:56.881 (2.75 s in, just after the grace) for the whole drive;
thermal Fair for the trace's last 46 s (run 1 Nominal throughout).

| | run 1 OFF | (Default part) | (UI part) | run 2 ON |
|---|---:|---:|---:|---:|
| system drain %/h | 44.37 | 47.2 | 41.46 | 40.76 |
| CPU impact | 23.92 | 27.06 | 20.68 | 22.93 |
| GPU impact | 12.87 | 12.68 | 13.07 | 10.25 |
| instructions G/s | 16.09 | | | 14.96 |
| fps mean (from pacing windows) | 117.9 | | | 110.2 (114.9 then 105.8) |

At 120 the trial did NOT hold the cap: mean 110 fps, falling to ~106 as thermal
reached Fair; the lower drain (-8%) mostly follows ~7% less rendered work (GPU
-20%, instructions -7%). Run 1's UI part (render at UI) held ~120 at 41.5 %/h.
Confounds: fixed order (ON second and hotter). Per Stefan's rule (preserve FPS),
the trial is not acceptable at 120 as is. Proposed dev132: limit render Utility
to caps 41-60 (render follows the boost above 60).

dev132 (Stefan approved, Nov 16): RenderQos trial condition now cap 41-60 only;
above 60 render follows the boost again (pre-dev131). Test PASS (64 changed cases,
caps above 60 asserted unchanged). Build exit 0, deep codesign pass, marker
"caps 41-60 since dev132" in binary. IPA `ios/build/NFSMW-0.6.1-dev132-render-utility-41-60.ipa`
SHA256 c19fafe1017b58c88e09f8080b4156e5e91840db2148fc6c8fda00b4f3b93a60, on Desktop
(dev131 removed from Desktop, kept in ios/build). Optional check: a 120 drive
should hold ~120 fps as dev131 trial-off did.
Stefan (Nov 16): short dev132 iPhone drive at 120 held 120. Pending: test on an
iPhone 14 Pro Max when available (older SoC; check 60 holds with render Utility).
iPhone 14 Pro Max check (Nov 16 21:36-21:43, dev171 build with dev132 scheduling
defaults, 1x/60, no Extra Args; log `16 November 2026/dev171_iphone14promax_nfsmw.log`,
SHA256 586545b6...17ca). Stefan: held 60 for the most part, some drops in the police
chase, moderate heat; he counts it as a pass. Log: 4 E cores, every drive started at
Default with the grace, one genuine step to User Initiated in a pursuit (21:39:50),
render on Utility during boosts as designed. Per-minute mean fps 59.1-59.8 while
driving; the chase dip (21:40, min 40 fps) is the BUSTED transition: one 475.7 ms
encode at 21:40:13 (BUSTED_OVERLAY.fng up 21:40:14.9), not scheduling; 326.5 ms at
21:40:28 is the post-pursuit transition. CORRECTION (same day): a missing shader
does not compile or stall; NativeDraw skips that draw (`!d.vs || !d.ps` ->
skipped_shader). vs 5595c163168c74ef + ps 8c8b535864c59f03 ("vte" rectangle/2D
shader), 672 indices, target 640, drawn once at the bust: one 2D element of the
busted effect is not drawn. Seen in 15 logs since Oct 21 on every device (with
vs 568a011c39fb416c in 16); never investigated, not related to the hitch. Thermal mostly
Fair, Serious only at 21:42:49-55 after the last drive. CoreAudio no gap windows.
Follow-up candidate: find why vs 5595c163/568a011c have no library and whether the skipped busted-screen draw is visible.

dev133 (Stefan asked, Nov 16): right stick camera while driving (not in drag
races, where it shifts gear); camera_look.cpp wraps the game's XInputGetState
sub_8262D6B8, details in TECHNICAL.md "November 16: right stick camera".
Options Controls > Controller (`nfsmw_stick_look` on, `nfsmw_stick_look_speed` 1).
Build exit 0, both wrappers T in camera_look.cpp.o, `unzip -tq` ok. IPA
`ios/build/NFSMW-0.6.1-dev133-right-stick-camera.ipa` SHA256
5249069db96227e8184fded9a0a489bfbd23e8916ad7060b22afb7461206359e, on Desktop
(dev132 removed from Desktop, kept in ios/build). Pending: Stefan's controller
test (free roam, a normal race, a drag race shifting). Not run on a device yet.

dev134 (Stefan, Nov 16, after testing dev133): the right stick now points the
camera (toward you = front, left = car's right side) and it snaps back on
release; speed option removed. IPA `ios/build/NFSMW-0.6.1-dev134-right-stick-points-camera.ipa`
SHA256 7b988bb156d9cfe8b51ee82472173513b5b4c35e569fca4603cdea850a41e74c, on Desktop. Pending: Stefan's test, especially whether left/right
match his description (one sign flip if swapped).

dev135 (Stefan, Nov 16: dev134 works as expected): the rear-view mirror is
hidden while the free look is turned more than 20 degrees away (it showed the
view ahead). IPA `ios/build/NFSMW-0.6.1-dev135-look-hides-mirror.ipa` SHA256
23b41db9666ff901063169949a7f8c7fa79a39bcced6c64069baca7a433b612a, on Desktop. Pending: Stefan's test (mirror frame and picture both gone
while looking, back on release).

dev136 (Stefan, Nov 16: dev135 hid the mirror picture, not its frame): the
frame now gets the FE hidden flag instead of a move. IPA
`ios/build/NFSMW-0.6.1-dev136-mirror-frame-hidden.ipa` SHA256 a48d0815021acadf5044adf0f4e351918d575e103ce04b6acb69b1f0d002ef92, on Desktop.
Pending: Stefan's test; if the frame still shows, his log's `[hud] mirror frame`
lines tell whether the object was found.

dev137 (Stefan, Nov 16: dev136 frame still shown): the hidden flag goes on
the mirror frame and all its children (the two image halves). IPA
`ios/build/NFSMW-0.6.1-dev137-mirror-frame-children-hidden.ipa` SHA256 4e9f9ccc53dde13990b50d13062e396d97cdb08bbe837a3e58272b90e48d46aa,
on Desktop. Pending: Stefan's test; a log that reaches driving shows
`[hud] mirror frame ... objects flagged`.

dev138 (Stefan, Nov 16: stick camera choppy): the stick camera eases to the
stick angle (50 ms) instead of jumping; includes dev137's mirror frame change.
IPA `ios/build/NFSMW-0.6.1-dev138-smooth-stick-camera.ipa` SHA256 7f090e6063d1f4cd655ac88964d131341bf20bfbbc8cdeba8cd201c99df241a9, on
Desktop. Pending: Stefan's test of both (smoothness, mirror frame hidden).

dev139 (Stefan, Nov 16: frame still shown; log proves the hidden flag was set
on all 4 frame objects): the frame's objects also get alpha 0 and the
0x00400000 bit. IPA `ios/build/NFSMW-0.6.1-dev139-mirror-frame-alpha.ipa`
SHA256 69b59832bdc4fa7e168fe8e6545f513c23d520537a26f6efaf83c67ad182fae0, on Desktop. If this fails too, next is skipping the frame's draws
in the native renderer, or leaving the frame.

Stefan (Nov 16): dev139 confirmed: smooth stick camera, mirror fully hidden
while looking. Right stick camera done (unpushed, no release yet).

## November 17, 2026 — dev192 iPhone race Time Profile: ARC traffic gone; sim 60 halves the world thread (confounded)

Stefan, iPhone 17 Pro Max, dev192, cap 60, race, Extra Args
`--nfsmw_sim_rate=60 --nfsmw_native_reflection_divisor=3
--nfsmw_native_mirror_every=2` (log: sim step count the game's 60; ~450-576
draws a frame not rendered). Archive `Debug/17 November 2026/
dev192_iphone_race_time_profile.trace` (tree SHA256 38de68ce...) and
`dev192_iphone_race_time_profile_nfsmw.log`; Desktop copies deleted after
verification. Trace 09:49:08, 140 s, all driving; window 5-135 s. Reference:
Nov 14 dev129 iPhone Time Profile (same device, 1x, cap 60, sim 120, no
skips, different content), window 10-125 s. Same parser.

| ms of CPU per second | dev129 (Nov 14) | dev192 |
|---|---:|---:|
| app | 1249 | 802 |
| render queue | 499 | 315 |
| render queue retain/release/autorelease | 86 (17.2 %) | 9 (2.9 %) |
| render queue objc_msgSend | 3.7 % | 3.9 % |
| world thread (XThreadDB33 / XThread973F) | 184 | 93 |
| world: sub_82468148 / sub_823A2348 inclusive | 53 / 56 | 18 / 20 |
| Main XThread | 202 | 147 |
| GPU Commands | 202 | 136 |
| guest audio | 101 | 57 |

Measured: dev192 removed the reference counting (objc_autoreleaseReturnValue
0.0 %, retain/release 86 -> 9 ms/s, ~77 ms/s, ~6 % of the old app total);
this one is attributable (share of the queue, independent of content).
The rest of the drop is confounded (race vs earlier content, pass skips,
sim 60): the world thread's two large subtrees fell to about a third and the
thread to half, consistent with half the simulation steps; a same-race sim
60/120 pair is still needed to size it.

## November 17, 2026 — sim 60 retried on dev192 (iPhone, donut test)

Stefan retried `--nfsmw_sim_rate=60` on dev192 at cap 60: motion "honestly
just fine", including the donut test that first showed the world-update
problem in October. He wants more testing (advanced camera logs) after
sleeping; if it holds, 120 Hz simulation would only be needed at the 120
cap. Log `Debug/17 November 2026/dev192_iphone_60_sim60_donut_nfsmw.log`
(Desktop copy deleted after SHA256 check): `[extra-options] sim step count:
the game's 60`, pacing 0-2 off per 300 in most windows. `[cpu]` lines
(10 s windows, % of a core, inflated on E cores): total 134, world thread
(XThread11E0B) 18.3 %; dev190 race at 120 Hz: total 134, world 19.3 %;
dev189 race: 141, world 16.7 %. Different content (donut vs races), so no
saving is visible at this resolution; sizing needs a same-content pair
(Time Profiler or Power Profiler), sim 60 vs 120. dev192 itself: no crash
or picture report in this run.

Race part of the same log (drive 02:21:28-02:23:52, before the donut test),
`[cpu]` 10 s windows, sum of the unnamed render-queue threads among the top 8
(% of a core): dev192 race 38 %, dev190 race (pass skips) 36 %, dev189 race B
48 %, race A 47 %, race A untraced 42 %. Totals 135 / 134 / 141 / 160 / 142;
draws 2074 / 1421 / 2250 / 2272 / 2055; `rendering ms/frame` 14.7 / 13.9 /
15.0 / 15.2 / 15.6. So the render queue's CPU is ~10 points of a core (~20 %)
lower than the dev189 races at similar draw counts, consistent with dev192
removing ARC traffic; confounds: different races, sim 60 on, coarse
sampling. A same-race Time Profiler pair (dev192 vs dev191) would confirm.
CORRECTION (Stefan, same night): the dev192 run also had
`--nfsmw_native_reflection_divisor=3 --nfsmw_native_mirror_every=2` (log:
~485-600 draws a frame not rendered in the race). The `N of N draws` count in
the `[native] frame` line is recorded draws, not rendered ones (dev190's 1421
was a different race, not the skip effect; the dev190 table above is wrong
on that row). So the dev192 race combines pass skips (cube+mirror), sim 60
and the ARC change; vs dev190 (all three skips incl. shadow, ARC traffic
still there): render queue 38 vs 36 %. The ARC change alone is NOT shown by
these logs. Needed: same race, same Extra Args, dev192 vs dev191 (or a Time
Profile of dev192: objc_autoreleaseReturnValue gone from the render queue).

## November 17, 2026 — handoff notes for the next session (CPU/GPU cuts)

Open, in the order suggested:
1. dev192 device check (picture, no crash; then one pursuit Time Profile to
   confirm objc_autoreleaseReturnValue left the render queue).
2. Guest-side pass cadence (cube faces, mirror): run dev191's
   `--nfsmw_diag_resolve_callers=true` (still in dev192) for 20 s of driving;
   the `[resolve-callers]` lines give the guest call chains per resolve. The
   per-view resolve is probably sub_8245D788 (destination and face from a
   struct). Find the function that renders one cube face / the mirror view
   above it and skip its call on the frames the host keeps the old copy
   (host side: `nfsmw_native_reflection_divisor`, `nfsmw_native_mirror_every`
   already keep the copies). The shadow map must NOT be skipped (dev190: the
   car's shadowing lags, reads as 30 fps).
3. Correction to the dev190 reading: `rendering ms/frame` in the `[native]
   frame` line is not CPU time alone, so "-36 % draws gave only -7 %" does not
   prove skipped draws are cheap for the render queue; only a same-race Time
   Profile or `[cpu]` pair can size it.
4. Render thread spin: the game's render thread (Main XThread, sub_82441B60)
   runs the deferred queue through sub_823C8290 and, when it has caught up
   with the producer (world thread) before the frame's end flag, loops
   calling it with a count of 0 (loc_82441C04). In the dev176 profile the
   loop's own cost is ~13 % of that thread (sub_823C8290 self 4.0,
   __savegprlr_29 2.9, __restgprlr_29 2.5, sub_82441B60 self 1.9, OnMainLoop
   1.7), ~21 ms/s on the iPad. A wake per pushed entry would ping-pong; a
   short timed wait (or a wait until N entries or the end flag) is the
   candidate, with pacing to be checked. Small (≈1.7 % of app CPU).
5. Remaining render queue ObjC traffic (objc_msgSend 2 %, direct retains),
   IOGPU resource list adds (~4.4 % of the queue), Frame::~Frame 2.8 %.
6. Game mixer functions on the guest audio thread (list above), only if a
   native rewrite of one loop is small.
Rejected/dropped today: sim 60 (Stefan), shadow-map skipping, PCM cache,
workers at Utility at iPhone 60 (no saving).

## November 17, 2026 — Nov 16 pursuit Time Profile re-read; dev192 unretained lookups

Stefan's answers to the candidate list: (1) sim 60 rejected (it broke world
and camera refreshes, unrelated to pacing); (2) guest-side pass cadence:
for Opus tomorrow (dev191 diagnostic flag stays in the build); (3) use the
existing profiles; (4), (5) approved; (6) mirror-off as an option if worth it.

Profile: `Debug/16 November 2026/dev176_pursuit_busted.trace` (iPad Pro M4,
1.5x, cap 60, pursuit), `xctrace export` time-profile, 15-195 s, parser in
the session scratchpad (per thread totals, self, inclusive, caller pairs).
App 1.24 cores. Per thread ms/s: render queue (unnamed wq threads) 586,
world XThreadD80B 195, Main XThread 166, GPU Commands 157, guest audio
XThread10807 88, UIKit main 38.
- Render queue: RenderFrame self 12.6 %; `objc_autoreleaseReturnValue` self
  8.8 % (all reached from RenderFrame by tail calls: functions returning
  Objective-C objects by value per draw), objc_retain_x8 2.1, _x20 1.8 (in
  PipelineCache::Get), objc_msgSend 2.1, objc_release_x21 1.1: ~17 % of the
  queue (~100 ms/s, ~8 % of app CPU) in reference counting. AGX
  drawIndexedPrimitives 7.0, encoder creation 4.0 + 3.5, IOGPU resource list
  adds ~4.4, memmove 3.2, Frame::~Frame 2.8. HUD AI Upscale 8.0 % in this
  dev176 trace (repeated requests, fixed in dev177/181).
- Guest audio: FFmpeg decode only ~15 % (decode_frame 5.2, ff_wma_run_level
  4.4, split_radix_permutation 3.8, imdct 1.2); the rest is the game's own
  mixer (sub_82602FC8 7.2, sub_82606698 6.1, sub_825E1178 4.7, sub_826045B8
  3.9, sub_825CCE90 3.7, ...). A decoded-PCM cache would save ~1 % of app
  CPU: candidate 4 dropped.
- Main XThread: sub_82699100 self 16.9 % (callers sub_8244EBF0 10.9,
  sub_8244F680 4.1), __savegprlr_29 4.2 (2.9 from sub_823C8290) and
  __restgprlr_29 3.9 (2.5 from sub_82441B60), sub_82453768 4.9.
- GPU Commands: Record self 45.1 %, FrameOwners 7.2, Fingerprint 3.8.

dev192 (output-identical): `PipelineCache::Get`, `GpuBufferFor`,
`GpuBufferForGeometry` return unretained `void*` (their caches keep the
objects), their callers and the per-draw depth-stencil state use
`__unsafe_unretained` locals, `GeometryGpuBinding::buffer` unretained (per
frame; the buffer cache is swept before encoding), a pipeline made twice
returns the kept one. IPA `ios/build/NFSMW-0.6.1-dev192-unretained-lookups.ipa`
(Desktop; dev191 to Trash). Not run on a device. Check: picture and no crash
in a race and menus; `rendering ms/frame` in the log; a Time Profiler run
should show objc_autoreleaseReturnValue gone from the render queue.
Next candidates on the same profile: __savegprlr/__restgprlr_29 inlined in
sub_823C8290 / sub_82441B60 (main loop, ~5 % of the main thread), the
remaining ObjC traffic in RenderFrame (objc_msgSend 2 %, retain_x8 1.35 %
direct), IOGPU resource list adds, the game mixer's top functions.

## November 17, 2026 — candidate list for "hacky" cuts; dev191 resolve-caller diagnostic

Stefan: the dev189/dev190 races were different tracks (comparison above is
indicative only). He wants Fable used for finding and first implementations;
later interpretation/changes by Opus. Candidates given to him, by expected
size (estimates from the Nov 10 dev110 profile, not measured):
1. Simulation 60 instead of 120 steps/s (`--nfsmw_sim_rate=60`, exists; world
   thread ~20 % of app CPU; 120 became default in October for uneven 60 fps
   motion, before the frame pacing fixes). Stefan asked to try it.
2. Cube face / mirror cadence inside the game (draws never issued).
3. Render queue's per-frame fixed cost (dev190: -36 % draws, -7 % time; the
   log shows ~7700 resource entries declared per frame, "full list on every
   encoder"); needs a Time Profiler trace.
4. Decoded-PCM cache for looping XMA streams (audio decode ~10 % of CPU).
5. Native rewrites of hot guest functions (sub_82699100).
6. The game's own mirror option off, if it removes the pass.

dev191: `--nfsmw_diag_resolve_callers=true` logs each distinct guest call
chain reaching D3D Resolve (sub_82592340, hook in native_draw_census.cpp):
flags r4, destination texture r6 (+ words at +24/+32/+36), face r9, up to 12
return addresses (360 ABI: saved LR at back chain - 8). Static callers of
Resolve: sub_82214CD8, sub_82222B60/D40/E70/FA0, sub_822234F0, sub_82224AA0,
sub_8243BF18, sub_8245D788 (face and destination from a struct: the likely
per-view target resolve), sub_82598DD0, sub_82599488. IPA
`ios/build/NFSMW-0.6.1-dev191-resolve-callers-diag.ipa` (Desktop; dev190 to
Trash). Wanted: 20 s of driving with the flag, then the log.

## November 17, 2026 — dev190 pass-skip trial, first iPhone race

Log `Debug/17 November 2026/dev190_iphone_60_pass_skip_trials_race_nfsmw.log`
(SHA256 182eff2c365e...), iPhone, cap 60, race, all three trials on
(divisor 3, mirror 2, shadow 2), Default all drive, pacing 0 off per 300 in
most windows. 650-1070 (typically ~780) draws a frame not rendered.
Averages over the drive's `[native] frame` lines, vs the dev189 race B
(different launch and sitting, so indicative only):

| | dev190 trials | dev189 race B |
|---|---:|---:|
| draws rendered/frame | 1421 | 2236 |
| recording ms/frame (game thread) | 3.57 | 3.83 |
| rendering ms/frame (render queue) | 13.90 | 14.98 |
| GPU ms/frame | 11.51 | 12.45 |
| `[cpu]` % of a core | 134 | 141 |

-36 % draws rendered but only ~7-8 % render queue and GPU time and ~5 % CPU:
the render queue's cost is mostly per frame, not per skipped draw, and the
game thread and Record still handle every draw. Stefan: effects noticeable
but acceptable; under shadows his car felt like 30 fps while the world was
60 (the shadow map kept from the frame before lags the car's own movement by
a frame every other frame). Shadow skipping rejected as is. He would accept
cube/mirror cadence as an optional switch if the savings are large.

## November 17, 2026 — new direction: fewer draws (dev190 pass-skip trials)

Stefan (Nov 17): shift back to cutting CPU/GPU time, "hackier" ways allowed
(supersedes the Nov 14 pause on CPU/GPU cuts for now). Draw census from the
dev189 race log (`[native] guest culling target` lines, 300 frames at 60,
iPhone): shadow map d030 674 draws/frame, main scene d468 975, cube faces
d7c0 798, rear-view mirror d71a 350, HUD ~68; ~2870 in all, so the main
picture is ~34 % of the draws. Every draw costs the game thread, Record (GPU
Commands) and the render queue; earlier passes (dev115-126) made draws
cheaper, none removed draws. GPU shares (Nov 14): main 42 %, cube 17-19 %,
shadow 10-11 % + 5 % copies.

dev190, all default off (restart required), in RenderFrame (saves the render
queue's CPU and the GPU; the game thread and Record still handle the draws):
- `--nfsmw_native_reflection_divisor=3` (2-6): one in N cube faces a frame.
- `--nfsmw_native_mirror_every=2`: the mirror's scene every 2nd frame, its
  kept resolve bound in between (image in a quad: no geometric mismatch).
- `--nfsmw_native_shadow_every=2`: the shadow map every 2nd frame; the kept
  depth copy is sampled with the current frame's shadow matrix, so shadows of
  things moving relative to the car may shimmer (to be judged by eye).
Log line every 600 frames: `[native] passes left out (dev190): ... N draws a
frame not rendered`. Compare `rendering ms/frame` and `GPU ms/frame` in the
`[native] frame` lines. IPA `ios/build/NFSMW-0.6.1-dev190-pass-skip-trials.ipa`
(Desktop; dev189 moved to Trash). Not run on a device.
Next if the picture is accepted: the same cadence in the game itself (guest
call-stack diagnostic at the cube/mirror/shadow resolves to find the pass
functions), which also removes the game thread's and Record's share. Other
candidates: decoded-PCM cache for looping XMA streams (audio decode ~10 % of
app CPU, Nov 10), native rewrites of hot guest functions (sub_82699100 14.6 %
of the main thread), Sharp HUD pass 0.81 ms at 2926x1317.

## November 17, 2026 — iPhone 60 workers-at-Utility race power pair: no saving, stays off

Stefan, iPhone 17 Pro Max, dev189, cap 60, race, brightness 15 % both, no
charging rows, thermal Nominal both. Archive `Debug/17 November 2026/dev189
iPhone 60 workers Utility race power pair/` (two .aar, `extracted/`,
nfsmw.log; Desktop copies deleted after SHA256 check). Windows: drive start
+15 s to drive end -5 s.

| | A `--ios_adaptive_qos_workers=false` | B default |
|---|---:|---:|
| system drain %/h | 21.73 | 21.73 |
| LiveContainer CPU impact | 19.11 | 19.80 |
| frame threads | Default 6 s, then UI (late; down at 01:36:38, late again, latched) | UI whole drive (learned from A) |
| hitch seconds / pacing mean, max per 300 | 22 / 1.5, 6 | 2 / 0.4, 3 |

A's untraced first race had no hitches (0.3 mean). Confound: A raised the
learned start level for 60 to User Initiated, so B started at UI; the pair
compares workers Utility vs UI with frame threads at UI in both. Result:
identical drain, A less smooth; Stefan felt B hotter (not in the thermal
state). Decision per Stefan's rule (default only if favourable): default
unchanged, workers follow the boost.

## November 17, 2026 — dev188 iPhone 60 workers A/B (log only); dev189 backdrop plain

Log `Debug/17 November 2026/dev188_iphone_60_workers_ab_pursuits_nfsmw.log`
(SHA256 2d081f2e..., Desktop copy deleted). Launch A 01:19:49
`--ios_adaptive_qos_workers=false` (log: "guest workers and render queue stay
at Utility"), two pursuits; launch B 01:24:44 default ("follow the mode"), one
pursuit. Both at Default the whole time (UI only in the last second at the
bust). Pacing: A 0-3 off per 300, B 0-4 off per 300. Hitch lines in the
drives: A1 one event at 01:21:41 (encode waiting 43.8 ms for a drawable, two
lines; the two hitches Stefan saw), A2 one at the pursuit's end, B one at
its start. So workers at Utility still hold 60; no Power Profiler traces, so
the energy question is open ("% of a core" is inflated on E cores: A 165-180,
B 152). Next: the same pair with Power Profiler.

Stefan: the title screen backdrop (M3 GTR with police) still upscaled and
oily on the iPhone, fine on the iPad. Log: `1024x512 from disk` (a runtime
`_a5` cache copy): the photo rule (over 1500 colours) did not catch it.
dev189: textures of 1024x512 and larger always keep the original texture
(before prepared/cached copies are looked up, and in Upscale). IPA
`ios/build/NFSMW-0.6.1-dev189-backdrop-plain.ipa` (Desktop, dev188 removed).

## November 17, 2026 — dev188 scheduler rules checked against the best results

Stefan: make the new scheduler match the best earlier results in every
scenario first. Best measured per scenario and what dev188 does:
- iPad (6+ E cores) 60: Nov 4 dev62 frame threads at Utility, no boost (24.0
  vs ~28 %/h, smooth); Nov 9 Eco = Balanced 22.7-24.0. Rule: start Utility,
  step up only on 12 late of 60 (dev185). Matches.
- iPad 30/40: Nov 9 Eco 40 (frame threads + render queue Background, low
  workers Background, audio Utility) 12.4/13.3 vs Balanced 17.5/17.8, "felt
  perfectly normal". Rule: same classes. Matches.
- iPhone 60/120: Nov 9 Default-class boost 34.0 vs UI 38.6, perfect; Nov 10
  controller (Default start) -4.7 % vs 0.6.0. Mismatch found: the dev179
  learned level could take it below Default after a calm drive (dev108
  probing below Default hitched). Fixed: the learned level only adds above
  the measured start level (Default on phones at 60/120, Low elsewhere).
- iPhone 40: Nov 9 Eco 40 (Utility, no boost) 17.4/17.5, median 39.5-39.7,
  "almost perfect". Rule: Utility, 12 late of 60. Matches once the dev185
  learned Default is gone: stored levels reset (new key `qos_start_level2`).
- iPhone 30: Nov 5 dev75 E30 (frame threads + render queue Background) 10.8
  vs 14.0 %/h. dev187 rule. Matches; dev188 also lifts the render queue to
  Utility with the frame threads at the Background -> Utility step.
IPA `ios/build/NFSMW-0.6.1-dev188-best-results-rules.ipa` (Desktop, dev187
removed).

## November 17, 2026 — dev187 iPhones at 30 on Background, with a Utility step

Stefan asked for Background at 30 on iPhones (Nov 5 dev75 measured iPhone
E30 10.8 vs A30 14.0 %/h, smooth). `performance_profile.h` mode 3: frame
threads at Background for any device at caps <= 30 (iPads with 6+ efficiency
cores keep Background at <= 40 as before); guest workers, the audio thread
among them, stay at Utility (LowWorkers unchanged), so the dev185 audio gaps
cannot recur. `adaptive_qos.cpp`: when late at Low while Low is Background,
the controller first relaxes Low to Utility (`background_relaxed`, still the
efficiency cores in practice, higher priority), resets the late window, and
only then steps to Default and User Initiated. The relaxation holds until the
cap changes. Answers Stefan's question: an older iPhone that can't hold 30 on
Background goes Background -> Utility -> Default -> User Initiated. IPA
`ios/build/NFSMW-0.6.1-dev187-phone30-background.ipa` (on Desktop, dev186
removed). Wants: one 30 fps iPhone race (smoothness, CoreAudio gaps).

## November 17, 2026 — dev186 iPhone at 40 and 30

`Debug/17 November 2026/dev186_iphone_40_then_30_nfsmw.log`, same race
twice. Low is Utility again. 40 fps: started at the learned Default (learned
in the dev185 Background run), no step during the drive, pacing 0-6 off per
300 after the start (76 during load), no CoreAudio gaps; the drive lasted
~119 s, just under the 120 s calm rule, so the start level stayed Default.
30 fps: Low (Utility) from the start, never stepped up, pacing 0-2 off after
the start (45 at load), no audio gaps.

## November 17, 2026 — dev185 iPhone at 40: Background broke it; dev186

Stefan: the iPhone no longer holds 40 on the efficiency cores, with audio
stutters. Log `Debug/17 November 2026/dev185_iphone_40fps_nfsmw.log`: cap 40,
`Low is Background`, the audio thread "follows the boost" (so it sat at
Background too): 77 CoreAudio gaps in the 5 s window at 00:49:55; driving
stepped up twice on 12 late of 60; pacing up to 78/56 off per 300 in places;
learned Default for cap 40. Before dev179 the iPhone's Low at 40 was Utility
(the Nov 9-10 Eco 40 result: efficiency cores, smooth), and the good Nov 4
iPad profile was Utility too. Background (lowest priority, E cores only) was
the regression. dev186: `nfsmw_low_background` default false (Low = Utility
again, as before dev179); kept: learned start levels, calm step-down while
driving, iPad tolerant Low. IPA `ios/build/NFSMW-0.6.1-dev186-low-utility-again.ipa`.

## November 17, 2026 — dev184 Sharp HUD off; dev185 iPad tolerant Low

`Debug/17 November 2026/dev184_ipad_sharp_hud_off_nfsmw.log` (archived,
Desktop copy deleted): Sharp HUD off, same outcome: Low at drive start, up
to Default after ~9 s (00:37:26), calm step-down 00:37:41, up 00:37:52, down
00:38:07, late again at once -> latched Default; learned Default. So Sharp
HUD is not the reason. Stefan asked whether the iPad really held 1.5x / 60
on the efficiency cores before: yes per the record: Nov 3 dev50 System
Trace (iPad Pro M4): Balanced ran GPU Commands, Main XThread and the guest
workers essentially entirely on E cores (same work ~1.8-1.9x the core time
of P); Nov 4 dev62 restored that tablet profile (Utility, no adaptive boost
below 120): 24.0 vs 28 %/h, smooth for Stefan. The difference now: the cap
controller steps up on 3 late frames of 60, the old tablet profile never
boosted. dev185 (`nfsmw_ipad_tolerant_low`, default true): on 6+ E-core iPads
at caps up to 60, Low steps up only when 12 of the last 60 frames were late
(the 30/40-cap rule). Boost scope (answer to Stefan): a step up raises the
two frame threads (Main XThread, GPU Commands) and the guest workers
together (`ios_adaptive_qos_workers` default true); the render queue follows
its own rule (Utility at 41-60 fps); the UI main thread is not touched.
IPA `ios/build/NFSMW-0.6.1-dev185-ipad-tolerant-low.ipa`, on Desktop.

## November 17, 2026 — dev183 iPad run

Archived (verified, Desktop copies deleted): `Debug/17 November 2026/
dev183_ipad_nfsmw_1.log`, `dev183_ipad_PowerProfiler_26-11-17_002845_to_26-11-17_003105.aar`.
Recorded drive 00:28:47-00:31:03 (139 s, 27% brightness, Nominal): 27.66 %/h
whole, 27.65 (15 s to end-5 s); pacing 0-2 off per 300 after the start
(97 at the start). That drive started at the learned Default and stayed
there (the calm step-down never goes below the drive's start level), then
learned Low again. The drive before (00:26:41-00:28:40) shows the real
limit: started Low, stepped up after 30 s, calm step-down to Low at
00:26:56, late again 7 s later at 00:27:03 and latched at Default. So at
1.5x / 60 the iPad does not hold 60 on the efficiency cores alone (Background)
for long; the learned level alternates Default/Low between drives. Same-sitting
comparisons with the earlier dev181 runs (27% brightness): Default start
29.0, Background start with one step-up 27.8, this Default drive 27.7 %/h:
little energy difference between the levels at this load.

## November 17, 2026 — dev184: free look back to dev178

Stefan (dev183): the free look is still affected by speed and elevation; it
was best with dev177's behaviour (before the dev180 change). dev184 restores
`camera_look.cpp` exactly as in dev178/dev179 (6ff25a0: car-matrix search
with the 10-unit window, forward row per frame, 0.2 s fade back to the chase
camera); dev180's 3-unit window and dev182's changes are dropped. Everything
else as dev183 (efficiency-core controller with calm step-down). IPA
`ios/build/NFSMW-0.6.1-dev184-camera-dev178.ipa`, on Desktop.

## November 17, 2026 — dev183: back down to the efficiency cores while driving

Stefan: the iPad used to run on the efficiency cores only and now still ends
up on the performance cores. From the dev181 log: once a drive stepped up
(e.g. run B at 00:07:45 right after the recording-start GPU hitch) it stayed
there for the whole drive (no step-down while driving since dev109), and one
brief step-up taught the learned start level Default. dev183:
- `nfsmw_drive_step_down` (default true): while driving, one level down after
  15 s (6+ efficiency-core iPads) or 30 s (phones) without a late frame; if
  late again within 10 s, back up and latched for the rest of the drive.
- learning raises the start level only if the drive spent over a third of
  its time above its start level.
IPA `ios/build/NFSMW-0.6.1-dev183-calm-step-down.ipa` (includes dev182's
camera fixes), on Desktop.

## November 17, 2026 — dev181 iPad power runs; dev182 steady free look

Archived (verified, Desktop copies deleted): `Debug/16 November 2026/
dev181_runA_PowerProfiler_235525_235749.aar`, `Debug/17 November 2026/
dev181_runB_PowerProfiler_000740_000956.aar` and
`Debug/17 November 2026/dev181_power_pair_nfsmw.log` (iPad Pro M4, both
sessions). Brightness 27% both, thermal Nominal. Run A (23:55:25, 144 s):
29.17 %/h whole, 28.99 (15 s to end-5 s); learned start level was Default
(from a 4 s drive at 23:45 that stepped up), so A drove at Default; after
its 140 s drive the learned level went back to Low. Run B (00:07:40, 136 s):
27.62 / 27.84 %/h; the log shows `Low is Background` and no learned-level
lines: `--nfsmw_qos_learn=false` took effect but `--nfsmw_low_background=false`
did not (B = efficiency cores from the start, no learning), one driving
step to Default at 00:07:45. So not the planned old-vs-new pair; observed B
(Background start) ~4% lower than A (Default start), same sitting, not a
causal result. The ~40 fps dip at B's start: GPU frames 45-65 ms at
00:07:39 (recording starting), not CPU.
Stefan: since dev180 the free look got worse: elevation again and left/right
jitter with the stick held down. Causes: (1) dev180's 3-unit window also
validated the cached path, so while the sprung look-at point drifted the
fixed camera dropped out (and re-searched); (2) the forward row's sign was
re-decided each frame from the view direction, which reverses when looking
back. dev182: 3 units only when searching, 12 for a found path; forward row
and sign kept while looking. IPA `ios/build/NFSMW-0.6.1-dev182-look-steady.ipa`.

## November 16, 2026 — dev181 confirmed: orbs good

Stefan: the orbs look right now. Remaining for 0.6.1: iPad/iPhone power pair
on dev181 (efficiency-core levels vs `--nfsmw_low_background=false
--nfsmw_qos_learn=false`), then CHANGELOG and push.

## November 16, 2026 — dev181: orb-like art caught

Stefan (dev180 screenshots `IMG_0387/0388`, Sharp HUD on/off): the pause
menu's orb is still a hard disc. On the disc the orb is most likely
FRONTB's 32x32 HIGHLIGHT: 1.61% of neighbours differ by >40 (just above the
1% soft rule) but 0.00% by >80; icons and text measure 1.68-15.66% at >80
(COPS_ICON 15.66, RADAR_ICON 1.87, PDA_BACKING 1.68). dev181: soft also when
under 0.3% differ by >80 (FX_SMK01_BLEND 0.47 stays AI). Cache names bumped
(prepared `_v4`, runtime `_a5`, preparation version 4) so earlier AI copies
are not reused; no manual cache clearing needed. IPA
`ios/build/NFSMW-0.6.1-dev181-orbs-plain.ipa`, on Desktop.

## November 16, 2026 — dev179 iPad log; dev180 soft art uses the original

Archived `Debug/16 November 2026/dev179_run1_nfsmw.log` (Desktop copy
deleted). iPad: Low is Background; first drive escalated to Default ~4 s in
(23:37:53, after the 2 s grace), so the learned start level for cap 60
became Default after a 10 s drive; pacing then 0-2 off per 300 for the rest.
Whether that escalation was a real need or a load hitch is open; a calm
120 s drive will try Low again. The car-matrix search also found
`mover+24 > +40 +5b0` with the 10-unit window (possibly another car):
dev180 narrows the search window to 3 units of the look-at point.
Stefan: the glow orbs behind menu items (also on Blacklist race selection
and the cop-takedown HUD overlay) still look very bad: soft art kept the
MetalFX spatial copy. dev180: textures judged soft or photographic go back
to the original texture (`Result::plain`, bound from the next frame). IPA
`ios/build/NFSMW-0.6.1-dev180-orbs-original.ipa`, on Desktop.

## November 16, 2026 — dev179: efficiency cores first, learned per device

Stefan: use the efficiency cores as much as possible on iPad and iPhone,
adapting per device (older iPhones included). dev179 (`adaptive_qos.cpp`):
- `nfsmw_low_background` (default true): under the cap controller the Low
  level is Background QoS (efficiency cores only) for the frame threads and
  guest workers at every cap (was Utility above 30, which iPadOS ran ~91% on
  P cores in the dev176 trace).
- `nfsmw_qos_learn` (default true): the driving start level is learned per
  device and cap (CFPreferences `nfsmw.qos_start_level.cap<N>`): first drive
  starts at Low; the highest level a drive needed becomes the next start; a
  drive of 120 s+ that never stepped up lowers it one level. No probing while
  driving (the existing up-on-3-late-of-60 rule and the 2 s drive-start
  grace stay). Logs: `[cap-controller] learned start level ...`.
Risk: a device that needs Default/User Initiated sees a short step-up at the
start of its first drive (and after a calm long drive lowers it again).
IPA `ios/build/NFSMW-0.6.1-dev179-ecores-learned-levels.ipa`, on Desktop.
Needs: pacing check + power pair on both devices (vs dev178 or with
`--nfsmw_low_background=false --nfsmw_qos_learn=false`).

## November 16, 2026 — iPad core placement in the pursuit trace

dev176 iPad Pro M4 pursuit trace, all samples: P 1,462,178 / E 1,198,245
(55% / 45%). XThreadD80B 375,004 P / 33,058 E, Main XThread 325,405 / 33,667,
GPU Commands 305,519 / 30,508: the three main game threads ~91% on P cores;
render-queue and helper threads mostly on E. So the iPad's `[cpu]` % is
mostly real P-core time (not E-core inflation), consistent with Stefan's
"warmer than it used to be at 60 / 1.5x". Proposed: in the iPad power pair,
add a run that pushes the game threads harder toward E cores (lower QoS /
Background at 60 on the iPad), checking pacing.

## November 16, 2026 — dev177 free-roam run; dev178 smooth return

Archived (verified, Desktop copies deleted): `Debug/16 November 2026/
dev177_freeroam_nfsmw.log` and `dev177_freeroam.trace` (tree hash
c1ba0cf4...4e2c). dev177 found the matrix in free roam via the search
(`mover+250 > +fc +540`) and engaged (`5.45 behind, 1.08 up, look-at 1.07
up`). Stefan: returning from free look eased back then jumped to the chase
camera's own position. dev178: the car-fixed camera fades out over 0.2 s
after the look returns to straight behind (eye and look-at blended with the
chase camera's); averaging only while fully released. First-minute drops:
world-load texture bursts (300+ textures, 40 MB decoded at 23:23:44) and
loading hitches; the AI path only loaded prepared/disk copies. Log CPU in
free roam 1.35-1.67 cores (Main XThread 31-39%, GPU Commands 25-32%,
XThreadCD07 19-26%), the dev176 pursuit 1.05-1.4: no pursuit-specific CPU
growth seen between the two runs (different scenes; Time Profiler
comparison pending). IPA `ios/build/NFSMW-0.6.1-dev178-look-blend-back.ipa`.

## November 16, 2026 — dev176 iPad pursuit trace; dev177

Stefan (standing rule, again): delete Desktop logs/traces once archived and
verified. Archived: `Debug/16 November 2026/dev176_pursuit_busted_nfsmw.log`
(SHA256 073d16b4...512a) and `dev176_pursuit_busted.trace` (iPad Pro M4,
Time Profiler 204 s; tree hash a73d0840...68c5), Desktop copies deleted.
Challenge Series pursuit, busted at the end on purpose.
Camera: in this pursuit the free look moved with speed/slopes again: no
`[look] fixed` line, the dev176 path (mover+0x250 -> +0x4) did not hold
there. dev177: the car matrix path is searched like the probe (mover
pointers, one or two levels, position within 10 of the look-at with three
unit rows), cached per mover, re-searched every 3 s while missing;
`[look] car matrix: mover+X > +Y +K` logged.
Trace (pursuit part, after 40 s): XThreadD80B ~31.6 s of samples (game
simulation: sub_823AFE20 / sub_823B0008 / sub_8261A318 inclusive), Main
XThread ~26.9 s (sub_82699100 self 4.5 s), GPU Commands ~25.5 s (Record
self 11.8 s), render queue blocks on workqueue threads (~20 s, ~14 s, ~14 s:
RenderFrame), audio XThread10807 ~14 s (XMA / WMA decode). Log [cpu]: ~105-
140% of a core in the pursuit. Not yet split pursuit vs free roam (no
baseline in this trace). Found: `hud_upscale::Upscale` 17.6 s of samples,
mostly in the first ~30 s (tid at ~63% of a core): -[MLMultiArray
dataPointer] called per value; and textures kept plain (soft/photo) were
re-judged each time. dev177 reads the output pointer once and remembers the
plain verdicts (by pixel hash). A likely part of the iPad warmth with Sharp
HUD on. IPA `ios/build/NFSMW-0.6.1-dev177-look-search-ai-cpu.ipa`.

## November 16, 2026 — dev176 confirmed: free look fixed to the car

Stefan: fixed now, both for elevation changes and the speed-related zoom.
Fixed free look done for 0.6.1 (`nfsmw_look_fixed_orbit` default true; probes
`nfsmw_look_probe` / `nfsmw_fov_probe` default off). Remaining for 0.6.1:
pursuit cost analysis (needs a pursuit Time Profiler + log), power check (iPad
pair + iPhone baseline), then CHANGELOG and push.

## November 16, 2026 — dev175 result: the fixed look never engaged; dev176

Stefan: busted text overlay still shows when busted, so the missing vs
5595c163 is left alone for good. dev175 log
(`Debug/16 November 2026/dev175_fov_probe_nfsmw.log`): no `[look] fixed to
the car` line at all: dev173-175 read the matrix at [mover+0x250]+0x24, but
the dev172 probe's path was mover+0x250 -> +0x4 -> object (+0x54 position),
so the check failed and the old sprung orbit ran. The FOV probe found no
clear field of view (mover+0x198 ~1.0 is a direction component; the u16 hits
are float high halves; 82c42230+0x70..0x7c floats 1.0-1.86 unidentified).
dev176 follows both pointers (safe reads); FOV probe default off again. IPA
`ios/build/NFSMW-0.6.1-dev176-look-fixed-pointer.ipa`, on Desktop.

## November 16, 2026 — dev174 results; dev175 field-of-view probe

Stefan (dev174, iPhone): got busted; `missing_vs_5595c163168c74ef.bin` (468
bytes, 117 dwords, host order) archived in `Debug/16 November 2026/` with
`dev174_busted_nfsmw.log`; its masked FNV key is 5595c163168c74ef (verified).
Four vfetches from fetch constant 95, stride 12 dwords: float3 at 0 (r6),
float2 at 3 (r2), float3 at 6 (r1), float3 at 9 (r0). None of the 98 game
vertex containers has the same input layout, so no container to borrow; a
hand-built 0x11 container needs vertex elements, a constant table and
interpolators matching ps 8c8b535864c59f03 (not done; effort vs one 2D piece
of the busted overlay to be weighed with Stefan).
Camera: Stefan says the car-fixed free look still moves with gear shifts and
acceleration/deceleration. With the eye and look-at now on the car's own
matrix, the remaining motion is most likely the game's speed zoom (field of
view; not in the look-at call). dev175: `[look] fixed to the car` once when
engaged; `[fov-probe]` (`nfsmw_fov_probe`, default true for now) every 0.5 s
lists fields of the mover and the objects it points to that changed and look
like a field of view (u16 binary angle 9000-19000, or float 40-110 degrees /
0.7-1.9 rad). IPA `ios/build/NFSMW-0.6.1-dev175-fov-probe.ipa`, on Desktop.

## November 16, 2026 — missing busted-overlay shader: dev174 dump

Stefan asked to fix the missing shaders. All Debug logs: `no shader library`
for vs 5595c163168c74ef (missing) + ps 8c8b535864c59f03 in 15 logs (the
busted overlay's 2D draw, skipped); the 568a011c / d1a204bd / others "missing"
only in 4 old logs (older shader builds), not now. The decrypted image
(rexglue `NFSMW_DUMP_IMAGE`, scratch only) holds 3 old-format containers (the
movie player's vs acc15ef6157ec934, ps 2d2462de73d283de and one more ps), not
5595c163: it is raw microcode (D3D-built or embedded without a container),
so the ZZDATA0 container path cannot build it. dev174 writes a missing
vertex shader's microcode once to `Documents/logs/missing_vs_<key>.bin`
(`[native] missing vertex shader ... written`), to wrap and translate offline.
IPA `ios/build/NFSMW-0.6.1-dev174-missing-shader-dump.ipa`, on Desktop.

## November 16, 2026 — dev172 found the car's matrix; dev173 car-fixed free look

dev172 log (`Debug/16 November 2026/dev172_look_probe2_nfsmw.log`, iPhone,
21 probe lines): `[mover+0x250]+0x54` is a position ~0.5 below the look-at
point with three unit rows before it (`MATRIX`), consistent every line (also
`[mover+0x250]+0xfc`+0x540). dev173 (`camera_look.cpp`,
`nfsmw_look_fixed_orbit` default true; probe now default off): rows read
safely from `[mover+0x250]+0x24` (16-byte rows, position +0x54); up = the
row with the largest world z, forward = the other row along the chase view.
While not looking the eye's back/up offsets in the car frame and the look-at
point's height are averaged (1 s); while looking the eye = car + (behind
turned by the yaw about the car's up) x back + up x height, the look-at =
car + up x its height (the game's target restored after the call: it may be
the mover's sprung state). Falls back to the old orbit if the matrix is not
found. Also renamed the preparation screens: "Caching shaders" (was
"Preparing graphics") and "Caching sharp HUD textures". Stefan's next ask:
the missing vertex shaders (5595c163168c74ef, 568a011c; coordinator note,
local commit fa2ac6a). IPA `ios/build/NFSMW-0.6.1-dev173-car-fixed-look.ipa`.

## November 16, 2026 — dev171 14 Pro Max result; dev172 safer, deeper probe

Stefan's iPhone 14 Pro Max run on dev171 (log archived by the other thread:
`Debug/16 November 2026/dev171_iphone14promax_nfsmw.log`): mostly 60 fps,
some drops in the police chase, moderate heat; Stefan counts the 14 Pro Max
performance test as passed. `[look-probe]` (60 lines): the only position near
the look-at point is the mover's own +0x140; its pointers within 64 MB all
lead back into the mover (+0x94/+0x98/+0x9c/+0x10c/+0x24c), no car matrix.
dev172: every guest pointer in the mover's first 0x400 bytes, and in the
first 0x100 bytes of each object it points to (two levels, up to 600
objects), is read with `vm_read_overwrite` (an unmapped page is an error, not
a crash) and searched over 0x600 bytes for a position within 10 units of the
look-at point, "MATRIX" when three unit rows precede it. IPA
`ios/build/NFSMW-0.6.1-dev172-look-probe2.ipa`, on Desktop.

## November 16, 2026 — 0.6.1 scope grows; dev171 look probe

Stefan: no rush; the fixed free-look camera, pursuit cost reductions and the
power check all go into 0.6.1 (not 0.6.2). dev171: `[look-probe]` every 3 s
in a chase view (`nfsmw_look_probe`, default true for now): the
CubicCameraMover's own floats within 8 units of the look-at point, and the
objects its fields point to (pointers within 64 MB of the mover) holding
such a position, marked "matrix" when three unit-length rows precede it.
Risk: reading a pointed-to object that is not mapped would crash (bounded
range, diagnostic only). IPA `ios/build/NFSMW-0.6.1-dev171-look-probe.ipa`.

## November 16, 2026 — dev169 reverted; fixed free look is 0.6.2's first item

Stefan: revert the last camera change and put the fixed free-look camera
first in the 0.6.2 backlog (BACKLOG feature ideas). dev169's commit reverted;
camera behaviour = dev168 (instant look-back entry, smooth otherwise).

## November 16, 2026 — dev169 result: no visible change

Stefan: the free-look camera still moves in/out with gear shifts and changes
angle with elevation. Reading (inferred): the hook only has the chase
camera's eye and look-at point; the look-at point is the CubicCameraMover's
sprung target (it lags the car on acceleration) and slopes are world-relative,
and the speed FOV zoom is separate. A car-attached orbit needs the car's
matrix (the mover's target pointer, offsets unknown on the 360) and the FOV
for the zoom: a few diagnostic builds. Proposed: after 0.6.1 (dev169's held
distance/pitch kept, harmless), awaiting Stefan.

## November 16, 2026 — dev169: free look orbits at a fixed distance and height

Stefan: free look should not follow the chase camera's distance/height
changes (uphill it dropped toward the road so the view behind showed the
ground; acceleration and gear shifts moved it). dev169 (`camera_look.cpp`,
cvar `nfsmw_look_fixed_orbit`, default true): the chase camera's distance and
pitch are averaged (2 s time constant) while not looking; while looking, the
camera orbits the car at those held values (yaw still from the chase
camera's direction plus the stick/mouse angle). IPA
`ios/build/NFSMW-0.6.1-dev169-fixed-orbit-look.ipa`, on Desktop.

## November 16, 2026 — dev168: look-back smooth after the snap; release held

Stefan: in dev166/167 the look-back zone snapped every frame (jittery while
moving the stick there); only entering it (and releasing from it) should
snap, the full 360 degrees otherwise easing. dev168 does that. Also the
`[hud-split]` diagnostic (160 lines every 20 s) is now default off. Release
held until power profiles on iPad and iPhone: Stefan feels the iPad warmer
than it used to be at 60 fps / 1.5x. Suspects introduced today (unmeasured):
iPad scheduled presents at 60 (`nfsmw_native_present_at_time_60_ipad`),
Sharp HUD if on, the hud-split log. Proposed same-sitting iPad pair: dev168
default vs `--nfsmw_native_present_at_time_60_ipad=false` (Sharp HUD and
MetalFX off in both). IPA `ios/build/NFSMW-0.6.1-dev168-lookback-smooth.ipa`.

## November 16, 2026 — dev167 accepted; 0.6.1 candidate

Stefan: much better; the title screen background (same oily look) is plain
again too; no photo model (not worth ~30 MB). dev167 = 0.6.1 candidate on
branch `claude/project-thread-dph4wh` (unpushed). Remaining before release:
Stefan's iPhone 14 Pro Max performance test, then CHANGELOG, push to main
(PRs #17, #19, #20 close by their commits), Stefan tags and replies on GitHub.

## November 16, 2026 — dev167: photographic art kept plain

Stefan: the Blacklist members' portraits look too soft and oily with Sharp
HUD (the anime-art network paints photos). dev167: textures with over 1500
distinct colours (5 bits per channel, visible pixels) skip the network and
keep the MetalFX spatial copy. On the disc's FrontEndTextures only 3 of 394
are flagged (ENDGAME 2199, DEMO_SPLASH 2089, POST_BUSTED_BACKING 1595; next
GRAF_01 585). The portraits are not in the AOT packs (drawn at runtime);
expected to be flagged there (DXT photos, unverified). Caches renamed (`_v3`,
`_a4`), preparation version 3. A photo-trained model (Real-ESRGAN x4plus) is
the alternative if plain is not enough. IPA
`ios/build/NFSMW-0.6.1-dev167-photos-plain.ipa`, on Desktop.

## November 16, 2026 — dev166: instant look-back; soft art kept plain

Stefan: dev165 splat fixed. (1) Right-stick look-back (stick down) should be
instant; left/right keep the easing. dev166 `camera_look.cpp`: a held stick
within 30 degrees of straight back sets the yaw at once, and releasing from
there snaps forward at once. (2) Sharp HUD: the pause menu's glow behind the
selected item became a hard disc (`dev165_IMG_0385/0386.png`, sharp HUD
off/on). The network makes flat colours with crisp edges; soft art (under 1%
of neighbouring pixels differing by more than 40 in alpha or luminance) now
skips it and keeps the MetalFX spatial copy. Checked on the disc: all 23
HudTexturesSingleRace textures stay AI (1.6-21.6% hard), GRAD_1 0.0% and
FX_GLOW01_ADDITIVE 0.24% are soft. Prepared files renamed `_v2` and the
preparation version bumped to 2 (re-runs once); runtime cache `_a3`. IPA
`ios/build/NFSMW-0.6.1-dev166-lookback-soft-glow.ipa`, on Desktop.

## November 16, 2026 — dev164 iPad splat (Sharp HUD, no MetalFX); dev165

Log `Debug/16 November 2026/dev164_ipad_splat_nfsmw.log`, screenshot
`dev164_ipad_splat_IMG_0384.png` (black splat during a pursuit camera,
MetalFX off, Sharp HUD on). `[hud-tex]`: ps ed7d7eea75715d08 at draw 1877
binds the scene and its blur chain resolves (960x720, 480x360, 240x180,
120x90) plus a 256x256 RGBA8 texture: another visual treatment's post
composite (not 20710a9a), so the frame took the menu rule (trailing
depth-off draws) and the composite's mask texture was replaced. dev165: a
draw that binds any resolve is a post effect; its textures are never
upscaled or replaced (`hud_keep`), whatever the split. IPA
`ios/build/NFSMW-0.6.1-dev165-post-mask-fix.ipa`, on Desktop.

## November 16, 2026 — dev164: which textures get upscaled (audit)

Stefan: make sure no in-game (world, car, police) textures are upscaled.
Audit of `[hud-tex]` in dev161-163 logs: only ps 2d8bf2c63ddd2608 (HUD/FE
2D, 142-229 textures), 8436534cfafcc0eb (mirror frame), fe90661a7df6f953
(1-2, 2D) and 2d2462de73d283de (the movies' picture, 6-36). By design only
draws on the split HUD target after the post group (races) or the trailing
depth-test-off run (menus) are considered, and only those draws bind the
replacements; world draws (depth test on, scene target) never do; AOT reads
only the UI packs. Found: movie frames (a new texture each frame) were being
upscaled and sent to the network each frame. dev164 skips ps 2d2462de. IPA
`ios/build/NFSMW-0.6.1-dev164-no-movie-upscale.ipa`, on Desktop.

## November 16, 2026 — dev163 iPhone power run 2 (baseline, 1.5x MSAA 4x)

`Debug/16 November 2026/dev163_iphone_PowerProfiler_182733_182922.aar` +
`dev163_iphone_power2_nfsmw.log`: 109.2 s, brightness 46-48%, Nominal;
estimated drain 36.94 %/h whole, 36.18 (15 s to end-5 s). Settings: scale
1.5, MetalFX off, forced MSAA 4, Sharp HUD on, cap 60. GPU frames 5-9 ms in
calm driving, 14-19 ms in the pursuit (fully attributed, unattributed ~0.02):
scene 2400x1080 MSAA4 5.57, cube faces 1.92, shadow 1.71, post 1.15, HUD
layer 0.82 ms. Pacing 0-232 of 300 off (worst in the pursuit). Stefan felt
lag near the police: GPU over the 16.7 ms budget there. Suggested headroom:
MSAA 2x, half-rate reflections, Sharp HUD off, 1.25x.

## November 16, 2026 — dev163: Eco / Balanced / Max gone from the menus

Stefan: remove every mention of the old performance profiles before the
release. dev163: Battery tab "Performance" row removed (launcher and in-game,
same catalog); the presets no longer set `performance_mode`; the launcher no
longer passes `--nfsmw_performance_mode` / `_source` (cap controller default,
Nov 9; saved choices ignored); first-launch "Longest battery" summary now
"Lower render resolution, half-rate reflections, 30 fps when warm." IPA
`ios/build/NFSMW-0.6.1-dev163-no-profile-menus.ipa`, on Desktop.

## November 16, 2026 — dev162 iPhone Power Profiler baseline (no comparison)

Stefan's on-device Power Profiler recording 18:15:54-18:17:25, archived
`Debug/16 November 2026/dev162_iphone_PowerProfiler_181554_181725.aar` with
the log `dev162_iphone_power_profiler_nfsmw.log`. Method: `aa extract`, then
`xcrun xctrace import` (.atrc -> .trace), SystemPowerLevel percent-per-hour
duration-weighted. 92 rows / 91.1 s, brightness 47%, thermal Nominal, no
charging rows. Estimated system drain 34.82 %/h (whole), 34.50 (10 s-end),
34.29 (15 s to end-5 s). Settings: scene 0.75, MetalFX Performance, target
0.75, cap 60. Baseline only (Stefan: not compared with older builds). Before
recording, target 0.75 pacing 0-5 of 300 off, GPU 7-9 ms; from ~15 s into
the recording GPU spans 20-28 ms and pacing 70-226 off: the recording also
captures Metal performance counters (metal-perf-overview tables): profiler
overhead is the likely cause (inferred, not isolated).

## November 16, 2026 — dev162 iPhone: MetalFX native target too heavy in races

Stefan: splat fixed; iPhone drops frames. Log
`Debug/16 November 2026/dev162_iphone_frame_drops_nfsmw.log` (MetalFX
Performance, target native, scene 0.75 = 1176x540 -> 2868x1317; thermal
nominal, LPM off): pacing 0-31 of 300 off in races (265/51 at load); GPU
spans 16-19 ms in races (attributed ~9 ms: scene 2.54, composite/post/HUD at
2926x1317 1.87, cube faces 1.33, shadow 0.82...; unattributed 6.5-10 ms,
mostly the untimed MetalFX encode). dev148/152 MetalFX runs: ~7 ms in menus
/ free roam, 14-15 ms in heavier scenes. Reading: MetalFX to the native
2868x1317 is the cost; proposed Target 0.75x on the iPhone (or default it
there); not related to the sharp-UI work.

## November 16, 2026 — dev161 MetalFX black splat; dev162 fix

Log `Debug/16 November 2026/dev161_metalfx_black_splat_nfsmw.log`: AOT works:
`[ui-prep]` FRONTB 394, HUDTEXRACE 23, INGAMEA 34, GLOBALA 5 (PhotoFinish /
Language / HUDS_Custom 0): 456 textures, 442 upscaled, 14 already there,
34.7 s on the iPad; in game the drawn textures matched prepared copies
(`prepared copy` lines). With MetalFX on, a black splat covered the middle of
the screen (`dev161_metalfx_black_splat_IMG_0383.png`): MetalFX splits at the
post composite, so the post group's draws (ps 36dac18d, a distortion map
read as data) had their textures replaced by upscaled pictures. dev162:
textures are upscaled/replaced only from the first draw after the post group
(`hud_tex_from`), whatever the split. IPA
`ios/build/NFSMW-0.6.1-dev162-metalfx-splat-fix.ipa`, on Desktop.

## November 16, 2026 — dev161 result

Stefan: "seems to work just fine"; Sharp HUD stays optional and off by
default (it is: `sharp_hud` default false; MetalFX preset default off). No
log received yet, so prepared-copy hash matches are unverified. 0.6.1 release
still waits for Stefan's iPhone 14 Pro Max performance test.

## November 16, 2026 — dev161: version 0.6.1 (12); sharp UI prepared ahead of time

Stefan: bump to 0.6.1, label Sharp HUD as AI upscaling, and do AOT now (the
14 Pro Max is not available yet). Version 0.6.1 / code 12 (d92a623); Display
row "Sharp HUD (AI upscaling, experimental)". AOT prototype on the Mac against
the USA ISO (`~/Downloads/Need for Speed - Most Wanted (USA).iso`, read only,
nothing extracted kept outside the session scratchpad): XDVDFS at 0xFD90000,
NFS/ZDIR.BIN little-endian 24-byte entries (hash, archive, sector in archive,
global sector, size, checksum), bStringHash x33 of the upper-case path;
FRONTB.LZC JDLZ 5,703,541 -> 25,297,188 bytes; texture packs 0xB3300000 with
name (0x33310001 +0x20), infos 0x33310004 (124 B: name +12, hash +36,
placement +48, size +56, width +68, height +70), Xenos format dword
0x33310005 (+20 of 32 B: format bits 0-5, endian 6-7, tiled 8), pixels
0x33320003 from the next 4 KB file boundary; decoded RGBA visually right
(METER_BACKING2 arc, COPS_ICON). Packs: FrontEndTextures (394), HudTexturesSingleRace
(23), HudTexturesGlobal, GlobalMessageTextures (5), PhotoFinish / Language /
HUDS_Custom (0 found with this layout yet).
dev161: `ios/src/ui_texture_prep.mm` does this in the app (decoded level 0
as the renderer's decoder writes it; key `hud_upscale::ContentHash`, also
computed by the renderer at decode as `Texture::content_hash`), upscales each
texture with the network (RGB and alpha) and saves
`Caches/HudUpscale/prepared/<hash>_WxH.png`; "Preparing sharp HUD" progress
screen after "Preparing graphics" when Sharp HUD or MetalFX is on, once per
version (`done_v1`). While playing, a texture with a prepared copy loads it
(with its fetch swizzle as a view) instead of running the network
(`[hud-ai] WxH prepared copy`). hud_upscale.mm and ui_texture_prep.mm moved to
the app target (not edition-specific). IPA
`ios/build/NFSMW-0.6.1-dev161-sharp-ui-aot.ipa`, on Desktop. Untested.

## November 16, 2026 — dev160 result: much better

dev160 iPad (log `Debug/16 November 2026/dev160_ui_ai_alpha_nfsmw.log`): 47
textures AI-upscaled, no GPU errors. Stefan: "much better now even without
relaunching"; still wants AOT. UI packs seen: FRONTEND/FRONTB.LZC,
FRONTEND/PLATFORMS/*, GLOBAL/HUDTEXRACE.BIN, GLOBAL/HUDTEXTURESPHOTOFINISH.BIN,
GLOBAL/GLOBALA.BUN, GLOBAL/INGAMEB.LZC, GLOBAL/DYNTEX.BIN,
LANGUAGES/LANGUAGETEXTURES.BIN. AOT needs ZDIR/ZZDATA lookup, LZC
decompression, TPK parsing and 360 texture decode. Proposed: ship the
runtime version in 0.6.1 (Sharp HUD off by default, experimental), AOT for
0.6.2; awaiting Stefan.

## November 16, 2026 — dev159 result; dev160 network on alpha too

dev159 iPad (log `Debug/16 November 2026/dev159_ui_ai_nfsmw.log`, screenshots
`dev159_IMG_0380-0382.png`): no GPU errors; 27 textures AI-upscaled (21 of
them 32x32, 64x64 x15, 640x360 x6 ...). Stefan: better but not perfect;
tooltips and text still low-res, speedometer not good enough. Reading: text
and many icons carry their shape in alpha (white texture, glyphs in alpha),
which dev156-159 only scaled bilinearly. dev160 runs the network on the alpha
as grey too when alpha varies (2x the work for those); cache files renamed
`_a2.png` so dev159's are not reused. IPA
`ios/build/NFSMW-0.6.1-dev160-ui-ai-alpha.ipa`, on Desktop.

## November 16, 2026 — dev158 freeze (GPU page fault), dev159 fix

dev158 iPad (log `Debug/16 November 2026/dev158_title_freeze_nfsmw.log`):
froze on the title screen. The AI path worked: model ready in 1475 ms;
32x32 in ~20 ms, 128x128 93 ms, 256x256 265 ms, 640x360 ~790 ms per
texture (tiles), PNG cache hit seen. 7 ms after the first AI texture was
swapped in: `kIOGPUCommandBufferCallbackErrorPageFault`, then every command
buffer ignored (freeze). Cause: textures made mid-frame were bound through
the argument heap the same frame, but residency::Add only takes effect when
the queue applies the set before the next frame (and dropped/replaced
textures were released while frames in flight could still read them).
dev159: new spatial and AI textures bound from the next frame
(`ready_from`, `next_from`), replaced ones kept, cleared entries kept 4
frames. Stefan: wants AOT preparation of all UI textures (plan in BACKLOG).
IPA `ios/build/NFSMW-0.6.1-dev159-ui-ai-residency-fix.ipa`, on Desktop.

## November 16, 2026 — dev157 result; dev158 fixed tile model, menus

dev157 iPad log (`Debug/16 November 2026/dev157_hud_ai_log_nfsmw.log`): model
found in the app (LiveContainer path fine), setting on, requests 512x512 /
32x32 / 128x128 at 17:39:32, then no "model loaded" in the remaining 32 s:
Core ML was still loading/compiling the 25 enumerated shapes. Stefan's idea:
upscale every texture that is not part of the 3D world. dev158:
model reconverted with one fixed input (1,3,128,128) -> (1,3,512,512);
`hud_upscale.mm` tiles any texture 8-1024 px (112 px cores + 8 px repeated
margins), averages the 4x colour to 2x, bilinear alpha; the model loads in
the background as soon as the sharp HUD or MetalFX is active
(`[hud-ai] model ready in N ms`). New split rule for frames without the post
composite (menus, garage, loading): the trailing run of depth-test-off draws
on the displayed target goes to the HUD target (3D car before it keeps the
render scale); their textures are upscaled too. IPA
`ios/build/NFSMW-0.6.1-dev158-ui-ai-tiles.ipa`, on Desktop.

## November 16, 2026 — dev156 result: AI path never ran; dev157 log

iPad log `Debug/16 November 2026/dev156_hud_ai_nfsmw.log`: 42 spatial HUD
copies made, but no `[hud-ai]` line at all (no model load, no request, no
failure): the network never ran, so Stefan's "no difference" says nothing
about it yet. Stefan also wants all UI upscaled (main menu items, tooltips,
the maps). dev157 logs whether the model is in the app (path, bundle), the
setting, the first requests and failures. IPA
`ios/build/NFSMW-0.6.1-dev157-hud-ai-log.ipa`, on Desktop.

## November 16, 2026 — dev156: neural-network HUD textures (trial)

Stefan approved trying it now and the downloads: converter venv
`~/Library/Caches/nfsmw-ios/ml-venv` (pip torch 2.8.0, coremltools 9.0),
model `~/Library/Caches/nfsmw-ios/ml-model/RealESRGAN_x4plus_anime_6B.pth`
(17938799 bytes, SHA256 f872d837d3c90ed2e05227bed711af5671a6fd1c9f7d7e91c911a61f155e99da,
xinntao/Real-ESRGAN v0.2.2.4, BSD-3). `tools/ml/convert_realesrgan.py`
(own RRDBNet 6 blocks, strict load of params_ema) -> `HudUpscale.mlpackage`
(fp16 mlprogram, iOS 17, enumerated input shapes 32-512 powers of two,
8.7 MB; edge check 0.0 / 0.9995). CMake `NFSMW_HUD_UPSCALE_MODEL` (default
that cache path; not in git) compiles it into the app (HudUpscale.mlmodelc).
`ios/src/hud_upscale.mm`: when the sharp HUD makes a MetalFX spatial copy,
the RGBA8 copy is read back at command-buffer completion; a serial Utility
queue hashes it (FNV-1a), loads `Caches/HudUpscale/<hash>_WxH.png` or runs
the model (4x RGB, averaged to 2x; alpha bilinear 2x) and saves the PNG; the
render thread swaps the result in for the spatial copy (`[hud-ai]` log).
cvar `nfsmw_native_hud_ai` (default true). Needs Display > Sharp HUD or
MetalFX. IPA `ios/build/NFSMW-0.6.1-dev156-hud-ai-upscale.ipa` (model
bundled), on Desktop. Untested.

## November 16, 2026 — dev155 result: HUD art is low-detail, not 1x targets

Log `Debug/16 November 2026/dev155_hud_texture_log_nfsmw.log`: 85 distinct
HUD textures, all plain (none a resolve), 32x32 to 512x512, formats 70/130/
132/134, ps 2d8bf2c63ddd2608 (one 256x64 under the mirror frame ps
8436534c). Stefan: speedometer and minimap still soft. So the art itself
limits sharpness; MetalFX spatial 2x adds no detail. Proposed: park an
on-device AI upscale (Core ML super-resolution once per texture, disk cache,
preload on the pipeline screen; no redistribution of game art) until after
0.6.1; keep HUD split + 2x textures automatic with MetalFX; Sharp HUD switch
default off (menu visibility: Stefan's call).

## November 16, 2026 — dev154 result; dev155 HUD texture log

iPad, 1.5x, Sharp HUD (log `Debug/16 November 2026/dev154_sharp_hud_textures_nfsmw.log`):
35 HUD textures upscaled within ~10 s of the race start (1-10 per frame, no
hitch attributable beyond the race-load frame). Stefan: speedometer and
minimap still look low-res. Hypotheses: (a) they are drawn into small
offscreen targets kept at 1x and sampled as resolves (skipped by the
upscaler); (b) MetalFX spatial 2x only sharpens edges, adds no detail.
dev155 logs `[hud-tex]` once per (address, size, ps): each HUD draw's
texture, plain or "resolve (not upscaled)". IPA
`ios/build/NFSMW-0.6.1-dev155-hud-texture-log.ipa`, on Desktop.

## November 16, 2026 — dev154: sharp HUD textures (trial)

Stefan: dev153 preset titles OK; try HUD texture upscaling now; 0.6.1 release
held until his iPhone 14 Pro Max performance test. No Xbox 360 HD pack known
(PC packs incompatible/third-party). dev154: when the HUD target is split
(`nfsmw_native_hud_split`, new Display switch "Sharp HUD", default off; always
with MetalFX), the HUD target's draws' plain 2D textures (8-1024 px, not
resolves, cubes or volumes) are upscaled once, 2x: copied to RGBA8, MetalFX
spatial (perceptual), then merged with the source's bilinear alpha; kept by
texture object (cleared past 768), at most 12 new per frame, own heap slots
with the original's sampler (heap capacity frame textures x3). cvar
`nfsmw_native_hud_textures` (default true). Log `[native] sharp HUD textures:
N upscaled`. Risks: shaders with unnormalized fetches would sample wrong
(none expected in FE), texture objects reused across frames assumed stable.
IPA `ios/build/NFSMW-0.6.1-dev154-sharp-hud-textures.ipa`, on Desktop.

## November 16, 2026 — dev153: iPad scheduled presents at 60; MetalFX titles

Test 1 (dev152 iPad, `--nfsmw_native_present_at_time_60=true`, log
`Debug/16 November 2026/dev152_ipad_present_at_time_60_nfsmw.log`): pacing
0-11 of 300 frames off the grid (was 56-169); Stefan: fixed apart from the
odd hitch. dev153: new `nfsmw_native_present_at_time_60_ipad` (default true)
schedules 60 fps presents on iPads only; phones unchanged (D-014). MetalFX
preset titles show the scene size on this device and target, raised to the
target / MetalFX's largest scale, marked "(MetalFX's limit)" (an iPad's
native target: Balanced to Ultra alike), Stefan's call delegated. Energy
baseline label fix included. IPA
`ios/build/NFSMW-0.6.1-dev153-ipad-pacing-metalfx-titles.ipa`, on Desktop.

## November 16, 2026 — dev152 iPad result; iPad 60 fps pacing next

Log `Debug/16 November 2026/dev152_ipad_metalfx_presets_nfsmw.log`. Native
target 2752x2064: Quality 960x720; Balanced, Performance and Ultra all
clamped to 927x695 (MetalFX's largest scale ~3x here), so they look alike.
Target 0.75x (2064x1548): Performance 720x540, Ultra 695x521. Memory flat
(1.0-1.8 GB). GPU frames ~7.5-9 ms (some 15 ms profiles). Two 5-6 s
"vigilante" stalls coincide with the in-game options menu (paused), then
recovered. The `energy baseline` line said "MetalFX off" with a preset (it
read the old cvar): label fixed in source (next build).
iPad pacing at 60 (cap 60, `[display] refresh now 60 Hz`): 56-169 of 300
frames off the 16.7 ms grid, gaps of 1 and 3 120 Hz refreshes (8.3/25 ms):
the panel composites at 120 Hz and unscheduled 60 fps presents (default since
D-014, Oct 30: `nfsmw_native_present_at_time_60` false) land on alternate
refreshes. First test proposed (no build): iPad, one race, Extra Args
`--nfsmw_native_present_at_time_60=true`.

## November 16, 2026 — dev152 iPhone result

Log `Debug/16 November 2026/dev152_iphone_metalfx_presets_nfsmw.log`: inputs
1568x720 / 1333x612 / 1176x540 / 966x443 (Ultra raised from 360p by the max
scale) to 2868x1317. GPU frames ~7.8-8.1 ms (Quality) to ~7.0 (Performance),
~6.7 (Ultra; few samples): MetalFX and the target-size composite/post/HUD
are a fixed cost. Stefan: all looked the same until Ultra Performance;
Performance the sweet spot on the iPhone. iPad not yet tested. Proposed:
MetalFX default off, Performance marked recommended after the iPad check.

## November 16, 2026 — dev152: Ultra Performance preset

Stefan: add Ultra Performance = 0.5x (360p). dev152 adds it; any preset's
base is raised to at least target / MetalFX's largest input scale for the
device (x1.01), so the scaler can always be made. IPA
`ios/build/NFSMW-0.6.1-dev152-metalfx-ultra-performance.ipa`, on Desktop.

## November 16, 2026 — dev151: MetalFX presets in 720p terms

Stefan wanted the three presets back (dev150 had only Off/On). dev151:
Off / Quality (scene at 1x, 720p) / Balanced (0.85x, 612p) / Performance
(0.75x, 540p), base relative to the game's 720p; a preset overrides Render
resolution; target Native or 0.75x; MetalFX only when the target is larger
(cvar value "on" still means: base = Render resolution). dev149 log archived
as `dev149_iphone_metalfx_presets_nfsmw.log` (2438x1119 -> 2868x1316). IPA
`ios/build/NFSMW-0.6.1-dev151-metalfx-presets-720p.ipa`, on Desktop.

## November 16, 2026 — dev150: MetalFX base = Render resolution

Stefan on dev149 (iPhone, Metal HUD: Quality input 2438x1119 -> 2868x1316):
the 0.85x should be of the game's 720p, not of the screen; live switching
works. dev150: "MetalFX upscaling" is Off / On; the scene is drawn at Render
resolution (0.85x 612p ... 2x 1440p of 720p), MetalFX to the target (Native
or 0.75x of it); only active when the target is larger than the render scale
(`MetalFxTemporal()`), else plain rendering. IPA
`ios/build/NFSMW-0.6.1-dev150-metalfx-base-render-res.ipa`, on Desktop.

## November 16, 2026 — dev148 result; dev149 MetalFX presets (step 3)

dev148, iPhone (log `Debug/16 November 2026/dev148_metalfx_nfsmw.log`):
memory flat (0.8-1.8 GB); `screen` at 1x (1568x720 -> 2868x1317): Stefan
"flawless", no HUD flicker, no car ghosting. `drawn` (1:1 at 1x) still looked
smeary vs MetalFX off: proposed to drop AA-only (temporal AA softness at 1x,
stretched 1.8x by the present pass; upscaling gives the same AA, sharper).
dev149: launcher and in-game Display rows "MetalFX upscaling" (Off / Quality
0.85x / Balanced 0.75x / Performance 0.5x, cvar `nfsmw_native_metalfx_preset`)
and "MetalFX target" (Native / 0.75x, `nfsmw_native_metalfx_target`), live
in game. With a preset the scene scale = screen scale x target share x
ratio (Render resolution ignored, heat cap still applies) and MetalFX's
output = screen x target share; the old `--nfsmw_native_metalfx` stays for
diagnostics. No AA-only choice. IPA
`ios/build/NFSMW-0.6.1-dev149-metalfx-presets.ipa`, on Desktop. Untested.

## November 16, 2026 — dev147 crash (leak), dev148 fix

Stefan, iPhone, dev147 at 1x with `--nfsmw_native_metalfx=screen` (and
`drawn`): crashed twice; log `Debug/16 November 2026/dev147_metalfx_crash_nfsmw.log`.
`MetalFX on the scene: 1568x720 to 2868x1317` worked, then Metal device memory
grew ~4.6 GB within ~20 s (footprint 6024 MiB, 120 MiB left): the scene's
per-frame copy (from the GPU pool) was replaced by the kept upscaled texture
and never retired (kept_resolves only retires what it replaces). dev148
retires the copy after encoding. Stefan's preference for the base: 0.85x or
0.75x of the target (for step 3 presets).
IPA `ios/build/NFSMW-0.6.1-dev148-metalfx-scene-leak-fix.ipa`, on Desktop.

## November 16, 2026 — dev147: MetalFX on the scene (MetalFX step 2)

Stefan: go for step 2; HD HUD textures noted in BACKLOG. dev147
(`nfsmw_native_metalfx_scene`, default true, only with `--nfsmw_native_metalfx`
= screen / lower / drawn; still no menu entry): the colour resolve the post
composite (ps 20710a9a) samples (largest one before it into one of its
textures) is upscaled by MetalFX temporal (jittered scene copy, this frame's
motion and depth) to the output scale (screen: `native_screen_scale`; lower:
0.75 of it; drawn: the render scale, 1:1 anti-aliasing) and registered as
that resolve's texture at that scale. The frame splits at the composite
(virtual `KEY|hud` target at the output scale): composite, post group with
the game's motion blur, mirror frame and HUD drawn at the output scale. The
old MetalFX on the finished picture is skipped then. Mip bias from scale /
output. Linear (buffer) resolve textures are not upscaled (warning once).
Log `[native] MetalFX on the scene: WxH to WxH`. IPA
`ios/build/NFSMW-0.6.1-dev147-metalfx-scene.ipa`, on Desktop. Untested.

## November 16, 2026 — dev146 result: works, off by default

Stefan (both devices): no flicker, works; little visible difference on the
iPad (the HUD's own textures are low resolution); unsure it is worth a default.
Logs `Debug/16 November 2026/dev146_ipad_hud_split_nfsmw.log`,
`dev146_iphone_hud_split_nfsmw.log`. GPU profiles: iPad (1.5x, HUD at 2.867,
2752x2064) race frames 9.7-11.9 ms with the HUD pass 0.8-1.4 ms; iPhone (1x,
HUD at 1.829, 2926x1317) HUD pass 0.2-1.0 ms; upscale pass <= 0.1 ms. Few
profiles (5 and 3), no power measurement. Decision proposed: default false;
used with MetalFX (step 2), where the upscale would otherwise blur the HUD.
Source default changed to false (not rebuilt).

## November 16, 2026 — dev145 logs; dev146 per-draw HUD split (MetalFX step 1b)

dev145 `[hud-split]` logs (`Debug/16 November 2026/dev145_ipad_hud_split_nfsmw.log`,
`dev145_iphone_hud_split_nfsmw.log`; iPhone at 1x). Same tail on both: post
composite ps 20710a9a2fef88e9 (blend off, full viewport), 20 x ps
36dac18d9d15b7a8 (post group), mirror frame ps 8436534cfafcc0eb, then HUD
draws (ps 2d8bf2c63ddd2608 ...; 67-86), final resolve. iPhone: own target
000_1600_0_d47c_s1 (67-87 draws, composite resolve -> 09689000 after the
composite, final -> 08dbb000); iPad: inside the scene target
000_960_0_d5e4_s1 (850-1700 draws; resolves -> 0983e000 before the
composite, final -> 0958c000). Stefan: iPhone presentation smooth, frames
16.67 ms apart apart from a few hitches.
dev146 (`nfsmw_native_hud_split`, default true; replaces dev144's
whole-target rule): below the screen's scale, draws from the first one after
the post group on the displayed target go to a virtual target `KEY|hud` at
the screen's scale (1 sample), which starts with the base target's picture
scaled up (bilinear, "sharp HUD: picture scaled up" pass); the displayed
resolve and later resolves of that target read it (`resolve_key`). Base
target's colour kept for the upscale; colour handoff off for both keys.
Log `[native] sharp HUD: from draw N on KEY at S`. `[hud-split]` log still
on. IPA `ios/build/NFSMW-0.6.1-dev146-hud-split.ipa`, on Desktop. Untested.

## November 16, 2026 — dev144 iPad result; dev145 HUD split diagnostic

dev144 on the iPad (1.5x, log `Debug/16 November 2026/dev144_ipad_sharp_hud_nfsmw.log`,
Metal HUD screenshot `dev144_ipad_metal_hud_IMG_0379.png`): the rule only
applied to menu frames (`000_960_0_d5e4_s1 at 2.867`); in races it was off.
On the iPad the game draws post and HUD into the scene target itself (no
separate post target, as the Nov 5 pass table showed), so race frames have
>600 draws there; transition frames dropped under 600 and flipped the target
to native and back (Stefan saw split-second sharp frames; target remakes).
Race pacing: 85-150 of 300 frames 25/8 ms apart on the 120 Hz panel (the
Metal HUD spikes); dev144 was off in races, so not its cause (inferred; pre-
existing status unverified). dev145: `nfsmw_native_hud_full_res` default
false; new `[hud-split]` log every 20 s (displayed target's last 160 draws:
index, ps, vs, px/vp, blend, depth, viewport, count; its resolves) to find a
per-draw split point that works on both devices.
IPA `ios/build/NFSMW-0.6.1-dev145-hud-split-log.ipa`, on Desktop.

## November 16, 2026 — dev144: sharp HUD below the screen's scale (MetalFX step 1)

Stefan approved the MetalFX return plan (motion blur stays on). Step 1, dev144:
`nfsmw_native_hud_full_res` (default true). The displayed target (source of
the frame's last colour resolve; post composite PS 20710a9a, then HUD/menus,
d47c on the iPhone) is made at the screen's scale (`native_screen_scale`)
when that is above the render scale, the target is 640+ wide, has at most 600
draws (not the scene itself) and is not an MRT second target. The post
composite samples the lower-scale scene image (an upscale where the present
pass did it before); the HUD is drawn at screen pixels. Log line
`[native] sharp HUD: displayed target KEY at S (scene R)`. Expected cost: the
post/HUD pass at native size (iPhone d47c ~2 ms at native, Nov 5). Next
(step 2): MetalFX at the scene's resolve into this target, motion blur kept.
IPA `ios/build/NFSMW-0.6.1-dev144-sharp-hud.ipa`, on Desktop. Untested.

## November 16, 2026 — dev143 fixes iPad HDMI mirroring (Stefan confirmed)

Stefan: "this change seems to have fixed it". Log
`Debug/16 November 2026/dev143_ipad_hdmi_mirroring_fixed_nfsmw.log`: external
pacing lines show the monitor's frames 16.7 ms apart, 0 dropped, 0 skipped
(see counts below the heading in TECHNICAL if added later). Reading: dev142's
monitor-clock timing plus room for a third waiting frame (skips at 2 were
the 49 fps dips, inferred) together fix GitHub #21's HDMI drops.

## November 16, 2026 — dev142 result, dev143 external pacing stats

dev142 on the iPad mirroring to the 1440p monitor (log
`Debug/16 November 2026/dev142_ipad_hdmi_mirroring_choppy_nfsmw.log`):
`[display] timing from the external display (max 60 Hz)` and 2560x1440 output
confirmed, but Stefan still saw general choppiness and ~49 fps dips. The
`[native] pacing` line measures only the iPad's layer, so the monitor's own
cadence was unknown. dev143: `[native] external pacing` line every 300
external frames (presentedTime gap buckets, dropped, skipped before drawing)
and the skip threshold raised from 2 to 3 frames waiting
(`nfsmw_native_external_queue`, 1-3). Stefan parked MetalFX until external
displays work; when MetalFX returns, keep the game's motion blur on.
IPA `ios/build/NFSMW-0.6.1-dev143-external-pacing-stats.ipa`, on Desktop.

## November 16, 2026 — dev141 iPad HDMI mirroring: uneven frames (GitHub #21 reproduced)

Stefan, iPad, monitor set to mirroring: #20's path engaged (scene
ExternalDisplayNonInteractive, `external display: ... 2560x1440 pixels`, so the
1440p setting applied to the drawable). The game still renders 1920x1080
(internal scale 1.5x); the drawable is upscaled. While driving, pacing went
from 0 to 67-155 of 300 frames off the 16.7 ms grid with 8.3/25 ms gaps
(1:/3: refresh gaps), worst 8-12 ms; GPU 7.6 ms per frame, LPM off, no
memory pressure. Inferred cause: pacing (CADisplayLink, guest vblank lock)
follows the iPad's own display while frames are presented on the monitor,
which has its own vsync clock; the beat between them gives the uneven frames
and the FPS dips (~49). dev142 (approved by Stefan): with the picture on an external
display, the CADisplayLink (and so the guest vblank) is created from that
screen (`display::FollowScreen`, cvar `nfsmw_native_external_display_timing`,
default true); back to the device's screen when the display goes. Log line
`[display] timing from the external display`. The `[native] pacing` stats
still measure the device's layer, so judge the monitor by eye / FPS counter.
IPA `ios/build/NFSMW-0.6.1-dev142-external-display-timing.ipa`, on Desktop.
Log `Debug/16 November 2026/dev141_ipad_hdmi_mirroring_fps_drops_nfsmw.log`.

## November 16, 2026 — dev141: iPad app window on an extended display

Stefan, dev140 on the iPad, USB-C monitor in extended mode, game opened only
on the monitor: LiveContainer and the launcher showed there, the game picture
stayed black, audio ran. Log `Debug/16 November 2026/dev140_ipad_external_display_black_nfsmw.log`:
the app's own scene is on the 5120x2880 screen ("the app's, not on the main
screen"), no `[external]` lines (#20 not involved). Cause (inferred): the SDL
scene filter in `patch_ios_sdl_scene.py` (since eb2c435/014a034, before the
PRs) kept only scenes on `UIScreen.mainScreen`, so SDL's window had no scene.
dev141: scenes on the device's screen as before; if none, application-role
scenes elsewhere. SDK re-patched. IPA
`ios/build/NFSMW-0.6.1-dev141-ipad-monitor-window.ipa`, on Desktop. Pending:
Stefan's iPad monitor retest. May also be the remaining iPhone Duo cause (#14).

## November 16, 2026 — dev140: contributor PRs merged for 0.6.1

Branch `claude/project-thread-dph4wh` (off `codex/native-frame-command-reuse`
c4aca5a, local, unpushed) merges GitHub PRs #19 (itsAllexB, 16:9 + MSAA in one
pass), #20 (itsAllexB, external display alone on a monitor/TV) and #17
(Lieforse, PAL Europe edition), keeping their commits so the PRs close when
this reaches main. Conflicts: TECHNICAL.md (both entries kept) and the USA
source list in ios/CMakeLists.txt (dev line's extra files kept, #17's
per-edition structure kept). SDK: `patch_ios_sdl_scene.py` applied to
nfsmw-multiplayer-sdk (2 new app-delegate blocks). IPA
`ios/build/NFSMW-0.6.1-dev140-contributor-prs.ipa` (USA build), on Desktop.
Pending Stefan: 16:9 + MSAA on the phone, HDMI monitor (picture, FPS counter),
USA boot. Not checked: a PAL Europe build. The dev line's post-0.6.0 USA
patches (register batches, constant descriptors, camera look, ...) are not in
#17's `desde_usa.tsv`, so a pal_eu build may need address additions.

## Current checkpoint — November 14, 2026

**CLAUDE HANDOFF — dev129 power pair processed; promising observation, trial remains opt-in.**
Stefan explicitly hands continuation back to Claude after this analysis. Current
priority: device-adaptive scheduling/thread dependencies/QoS for minimum energy at
selectedresolution/FPS across supported devices; shader/cache microtrials paused.
Read AGENTS then this checkpoint/BACKLOG/latest TECHNICAL. Worktree remains
`codex/native-frame-command-reuse`; no push/merge/release. Latest implementation
613976c; Desktop delivery9d898a6; priorCPU mechanism8d770b4. No app/SDK/code changes
in this handoff turn. HANDOFF_CHATGPT.md is pre-existing UNTRACKED, preserve it.
Matching BACKLOG remains ignored/local; essential state is committed here/TECHNICAL.

**IMPORTANT COMPARISON RULE:** Stefan says CURRENT power conditions differ from
all previous sessions. This analysis compares run1OFF vs run2ON ONLY. Do NOT compare
absolute drain with dev125/oldcontroller/profile runs or combine savings percentages.

Same-session iPhone17ProMax/iOS27.3, dev129 startup markers,1x60/noAA/MetalFXoff,
accepted ownership/preparedON/directdraws, both normal/uninterrupted (user), both
unplugged/LPMoff (user), Nominal throughout. A17:33:13.892–17:36:03.554/169.662230s;
B17:37:05.164–17:39:55.431/170.267478s. Preselected primary15–160s before means:

| Current pair only | A trial OFF | B trial ON |
|---|---:|---:|
|Estimated system drain, percentage points/hour|40.67904|36.00789|
|Trace brightness|32%|35%|
|Median logged FPS|60|60|
|Primary off-grid frames /8400|2|5|
|Primary audio gaps|0|0|
|Render entry QoS,8400samples|Default|Utility|

Observed drain-4.67115points/hour/-11.48295%relative; sensitivity10–160/-11.40484%,
30–160/-11.85051%. **NOT an isolated causal saving:** brightness mismatches,
instruction rateB-5.457%, work proxies differ (prepared sites-2.295%,last-draw
snapshots-3.917%,GPUsummary+0.445%), fixed OFFthenON order. Don't normalize brightness
or instruction counts into a claimed corrected percentage. No netCPU/frequency or
all-device conclusion. Earlier99.97%E rendering CPU result is separate mechanism
evidence, NOT an E-core measurement in these power runs.

New scheduling lead: A remains controllerDefault in captured driving; B escalates
UserInitiated at17:37:07.018 (60ms after game-driving signal), holds there. Rendering
still Utility. Other policies/source unchanged, but effective guest/main/CP boost
states differ via controller feedback. Do not say only render's effective QoS
changed. Inspect early lateness/reset/feedback evidence before designing per-role
promotion; no automatic lowering/probing while driving (old negative evidence).
This is next SOURCE question for Claude, not a diagnosis or permission to force E
cores. Trial remains opt-in/defaultfalse; no additional test/build launched now.
If causal confirmation/default promotion needed, smallest follow-up is same-build
pair with identical brightness/conditions and workload controls, not old-session
comparison. Don't automatically demand another capture before reviewing artifacts.

**Current artifact/defaults:** Desktop AND repo
`NFSMW-0.6.1-dev129-accepted-defaults-render-qos.ipa`,30771474bytes,
SHAc8deb10662e98bfd9a1587f615b64790a5da1a5a72332ebf1b60717eb211d336.
ExpectedmainUUIDE62BE4C2-B861-3012-B59D-B786A6B9AA5D/runtime2BF028C3/GPUF35FCE03;
exact identities verified in previousCPU trace/artifact, powertrace has no UUID
symbol stores (identified via startup build/dev129/effectiveflags). No rebuild.
EmptyExtraArgs=acceptedbaseline. ONLY `--nfsmw_render_utility_trial=true` enables
trial (coldrestart); false returnsbaseline. OriginaltenB flags redundant. Full
compiled-default list/tests/bundle0.6.0code11/isolation/build instructions below.

**Evidence archived/deleted:** November14Debug
`dev129_reference_vs_render_utility_power.trace`183files10852414bytes,
treeSHA85e4dc45bc5cb190d0437b5bdc3efcfa69f6da0a34d545cce76839cac4f2339f;
matching `_nfsmw.log`1965650bytes/SHAfef63981dbcf542d8cb915e93f10cc23365152edf4c3f6a7478ffb00d498e686.
BothDesktoporiginals deleted AFTER per-file verification; postexporthashes unchanged.
Full exactpaths, outliers, limitations, commands in latest TECHNICAL entry.
Private audit `ios/build/dev129-render-qos-power-20261114/`:window-plan/manifest/
TOC,2powerexports/splitlogs,comparison.json,analysis-summary.json,postexportverify,
reproduciblearchive/analyze-logs/compare scripts. No power retest currently pending
from Codex; Claude reviews this handoff and picks next work with Stefan.

Previous CPU mechanism checkpoint (power-pair request now fulfilled above):

**Latest: dev129 render-Utility mechanism/device check PASS; energy pending.**
Stefan says picture/controls/audio normal and capture uninterrupted. Received
Desktop Untitled.trace + Pasted2026-11-14at4.15.47PM.log; archived/hashverified in
November14Debug, then both originals deleted per standing rule; post-export hashes
unchanged. Trace16:12:39.293–16:14:50.249+02/130.956455s, iPhone17ProMax/iOS27.3,
TimeProfilerHIGH100us, exact129main/runtime/GPU UUIDs. TrialON, accepteddefaults
ON/directdraws,1x60/MetalFXoff/FXAAoff/MSAA0,Nominal throughout. Second driving starts
1.813s into capture, no subsequent interruption, background after capture.

Preselected primary8–110s:1,307,796running samples/130,779.6ms appCPU. Broad render
worker bucket83.840%E-core samples (includes shared dispatch-worker overhead/other
work); EXACT RenderFrame symbol scope39,538.3ms/99.970%E, only11.8ms P samples.
Early8–50s exact RenderFrame99.981%E. Main/GPUCommands/guestframe worker still
mostly P; no new policy for them. This establishes placement on tested device,
NOT clock reduction or net energy saving; CPU time can grow on slower cores.
Old dev125 broad render9.7%E is historical context only, not matched causal delta.

24complete guarded pacing/FPS/audio windows:7200frames,9offgrid(worst83.3ms),
20x60.0/3x59.9/1x58.6FPS,24audio windows0gaps.7200/7200render-entry Utility.
One83.3ms miss window16:13:37 has elevated VMcompression/page-ins too; correlation
only, cannot attribute to QoS or memory without wait data/control. No captured GPU
errors/pipeline misses; backgroundGPUpermission errors start after capture. Keep
trial OFF by default pending same-build energy/pacing control; no newIPA/code now.

**Historical requested power pair now processed above.** No further TimeProfiler
or old-session comparison needed. Trial remains defaultfalse pending stronger
causal/device-wide acceptance; scheduling continuation is handed to Claude.

Full evidence TECHNICAL and ignored audit `ios/build/dev129-render-qos-profile-20261114/`
archive-manifest/toc/time-profile/thermal/profile-inspection/control-health/
primary8–110/early8–50/analysis-summary/post-export verification. Matching ignored
BACKLOG updated; HANDOFF pre-existing untracked preserved. No push/merge/release.

Previous implementation checkpoint (artifact/defaults remain current):

**Latest: dev129 accepted renderer defaults + opt-in rendering QoS trial built.**
Stefan redirected work from marginal CPU/GPU source tweaks to scheduling/thread
use. Three compiled defaults now match accepted dev125 B: command_reuse=true,
command_encoding=false, prepared_geometry=true. Existing geometry_handoff/
owner_index=true, repeat_counter/register_batches/register_flushes/descriptor_runs
false retained. vfetch_cache remains effectively ON via default-on battery group;
its raw fallback false and group opt-out unchanged. Explicit Extra Args still win
for the newly promoted flags; old nine-line B list is redundant on this build.
Accepted evidence is group-level dev125 same-build iPhone power pair ~7.28% lower
estimated drain/60FPS medians (limits below), not a separate gain from promotion.

New restart-only `--nfsmw_render_utility_trial=false` default OFF. True keeps only
native encoding work at Utility during cap-controller boosts when cap>40,
render Utility enabled, adaptive/worker boosts active. Guest/main/CP/audio policies,
queue order, dependencies and 30/40 behavior unchanged. Explicit
`--nfsmw_native_render_utility=false` disables trial effect. No affinity/core pinning
or guaranteed E-core placement. Existing per300frame actual render-entry QoS counts
and encode/pacing/audio reports suffice; no added hot-path telemetry.

Tests PASS: original command/ownership eight-mode gates, actual native command
cache/lifetime/state ordering, prepared geometry90kcomparisons per variant/on-off,
render selector36864states each flag off/on (0/192changed); all remaining scheduler
source identical to d805bce. Build-0.6 ipa -j12 exit0/6.502914917s final; ZIP and
strict deep codesign pass. All109NativeShaders files incl104metallibs/seed AND both
SDK libraries byte-identical128. No shader/SDK/default scheduler rewrite.
Retained `ios/build/NFSMW-0.6.1-dev129-accepted-defaults-render-qos.ipa`,30771474bytes,
SHAc8deb10662e98bfd9a1587f615b64790a5da1a5a72332ebf1b60717eb211d336.
MainUUIDE62BE4C2-B861-3012-B59D-B786A6B9AA5D; runtime2BF028C3-7030-3218-AB7E-53C59017F379,
GPUF35FCE03-AE0C-3B71-82A1-B365C5438C4F. Bundle remains0.6.0/code11 as prior devIPAs.
November14 follow-up: Stefan requested Desktop delivery; dev129 copied to Desktop
and verified30771474bytes/SHAabove. Existing Desktop128 preserved, no Trash or
deployment. Audit desktop-delivery.json. Next device trial remains below.

**Historical device gate, now completed above:** render Utility trial at1x60.
Placement confirmed; same-build power/pacing acceptance remains pending. No further
identical CPU recording needed; dev129 artifact/settings below remain current.

Repro/audit `ios/build/accepted-defaults-scheduling-20261114/` build/verification/
artifact/scheduling-audit/validation JSONs. New test command
`python3 tools/ios/test_render_qos_trial.py`; established build command/configuration
unchanged (isolated SDK and named128shader folder). TECHNICAL exact results/limits;
matching ignored BACKLOG updated, pre-existing HANDOFF remains untracked.

Prior source-audit checkpoint (superseded as active direction):

**Latest: fence vertex source/compiler/host cost audit complete; no rollout.**
Found pair-specific unused auxiliary specular export (VS5c1d4bce TEXCOORD6,
paired PS684f overwrites its incoming value before use). Private host candidate
clears that export; no lighting/fog approximation. Linked Mac g14s __text falls
7928->7146bytes (main symbol5624->4842); this is code size, NOT execution savings.
Compiler also emits a constant program; don't assume all uniform source math is
repeated per vertex. No supported native ISA disassembly obtained.

Original/candidate actual shader pair:111 exact RGBA/depth image checks pass,
2,174,976pixels including16aux-light masks/shadows on-off.28ordinary host cost
cases show no clear total GPU benefit;12geometry-heavy stress cases show candidate
at most1.18% faster, unchanged control varies up to1.42%. Too marginal to justify
renderer variants/PSO selection/new IPA. Candidate PARKED/unshipped; cannot clear
this VS export globally without proving every linked pixel shader ignores it.
Mac evidence only, no accepted iPhone power/performance gain or ceiling claim.

**Historical next target, now deferred by Stefan:** normalmapped fragment source
audit. Fence prepass/specular export and further shader/cache microtrials remain
parked while scheduling is the active priority. No accepted benefit from them.

Private reproducibility/evidence `ios/build/fence-vertex-audit-20261114/`, including
`audit-summary.json` source/input/artifact hashes and preserved original depth-gate
costs (restored byte-identical after temporary output-path collision). TECHNICAL
exact outcomes/failures/limits; ignored BACKLOG updated. HANDOFF remains untracked.

Previous completed source gate:

**Latest: foliage profitability-admission source gate completed; approach parked.**
No cheap reliable selector established. Cached homogeneous position bounds could
be accumulated on validated decode and projected with a bounded per-draw cost,
so absence of bounds alone does NOT prove high CPU cost or impossibility. However,
overlapping bounds/far-to-near order/alpha histograms cannot lower-bound actual
hidden alpha-surviving coverage: private counterexample has identical metadata
but56 vs0 removable shaded samples. No production selector or cost estimate accepted.
Historical October21 iPad main-state census:491/7159fence draws meet necessary
alpha-on/LE-write/replacement/full-mask states (not sufficient admission/current
coverage). November2 snapshot groups omit alpha/order/positions; cannot recover
real profitable groups from them. No new phone capture needed to repeat this gate.

**Historical next gate, now completed above:** fence vertex source/compiler/cost
audit. Its32.95%weighted vertex occupancy in the short128window is not a promised
saving. No accepted optimization/energy benefit or proof of a ceiling.
Do not continue adding foliage prepass machinery or benchmark synthetic layouts
without new real qualification evidence. Dev128/B/descriptorfalse unchanged.
No runtime/SDK/shader/cache/flag/IPA change, no new phone request, no push/release.
Private audit `ios/build/foliage-admission-audit-20261114/audit.py` + `audit.json`;
TECHNICAL records exact source constraints, input hashes/counts and model limits.
Existing ignored BACKLOG updated; pre-existing HANDOFF remains untracked.

Previous completed host gate:

**Latest: local foliage GPU gate completed; general rollout rejected.**
Stefan approved this host-only gate. New reproducible tools:
`tools/native/test_foliage_depth.py` and `tools/native/foliage_depth_fixture.mm`.
Actual dev128 tree/fence VS+PS, hash-locked private inputs, synthetic geometry/
textures/constants on Apple M2 Pro: 79 cases / 1,388,544 pixels match exact RGBA
and depth bits. This does not establish game-scene/iPhone equivalence. Tests
cover complementary edges, ties, filtering/mips, perspective, mixed ordinary
opaque draws, depth-only/strictLESS boundaries; no production admission collector.

36 cost cases include extra geometry/texture/encoding work. Dense far-to-near
fences repeatedly look cheaper; near-to-far/tree cases can regress substantially
and CPU encoding grows. Short timing control falsely showed a 34.7% benefit for
identical GPU work. Longer batches (20ms target, cap512 frames, 7 alternating
pairs) still show identical-stream -13.8% to +5.8% variation; small differences
are inconclusive, precise percentages are not accepted savings. No iPhone energy
or game-wide gain proved. Do not ship a generic foliage depth phase.

**Historical next gate, now completed above:** investigate cheap conservative
profitability admission before game integration; not established, approach parked.
No revival of packed-mesh/G2/write-watch shortcuts.
Dev128 and established B/descriptor=false stay unchanged, no new flag/default/
shader cache/runtime/SDK change or IPA. Detailed results and limitations in
TECHNICAL; private reproducible artifacts `ios/build/foliage-depth-gate-20261114/`.
Matching ignored BACKLOG updated; pre-existing untracked HANDOFF preserved.
No push, merge or release.

Previous device attribution checkpoint (still valid):

**Latest: dev128 device naming gate PASS; foliage localized, no energy win claimed.**
User says picture/controls/audio all felt normal. Captured main1463E873/runtime
2BF028C3/GPUF35FCE03 UUIDs match128. Nov14 02:00:45.940–02:01:17.236+02,
31.296220s, sameiPhone17ProMax/iOS27.3/Instruments27.2, ShaderTimelineENABLED/
PerformanceLimiters/defaultstate. B/newdescriptorfalse/1x60/noAA/MetalFXoff,
111shaders loaded,223known-state pipelines prepared beforegame. Last driving
02:00:42.913(3.027s before capture; earlier driving/restarts outside), none during.
Nominal throughout,0captureerrors/pipelinemisses;5completepacinggroups1500frames
1off-grid(worst16.7ms),5completeaudio windows0gaps. Not an unprofiled performance
or battery comparison. No default/cache/source changes or newIPA this session.

IMPORTANT sampling limit: rawshader intervals160998span ONLY0.537279459–
3.495940334s of31.296s trace. Do not extrapolate shader percentages to whole run.
Compiled metadata3136rows,290material-named rows, app323unique code ranges.
Initial preselected1–30s frame context1683frames/137300joinedprofilerrows retained;
FINAL aligned support1–3.495940334s/149completeappframes/136398joinedrows, dominant
RenderCommand24 fragment58774rows. Currentmain-scene inference from pass shape/
cost/source order, not explicit target label. PC->compiled name->material now
works, grouping variants (not guessing alpha states from program IDs):
treePS27d82ea0 24.923%weighted fragmentoccupancy(29.491%rows), fence/plant684f
22.544%(23.347%), normalmapped d1a189fd13.652%, carpaint2442daf212.321%.
Tree+fence47.47%weighted in sampledmain region, NOT wholeGPU/time/energy savings.
Main source stage intervals aligned fragment356.22ms/vertex216.01ms across149;
stages may overlap, profiler weights are occupancy, never additive wall time.

**Historical proposal, now tested above:** bounded foliage alpha/depth phase,
retaining original colour/alpha tests and complementary edge order. Existing
TreeEdgeDepth/early-alpha remain ON; November2 zero-alpha microtrial parked.
Single-pixel model and host image tests support only modeled safe segments;
actual game eligibility/profitability remain unproved. No generic prepass,
shadow quality/cadence changes, deleting complementary passes or blind reorder.

BothDesktopinputs archived/hashverified then deleted, postexportreverified:
Debug/14November2026/dev128_iphone_gpu_shader_timeline.trace695files848291043bytes,
treeSHA38880971209fbe77132c2dc845dfbd73a82755fc7e9b059c095d782eb0e14ab6,
matchinglog894782bytes/SHA40b36e4459ba941e16eea727be80c2571e90dc8a1cb625bc275f4fe4e0183540.
Private audit ios/build/dev128-gpu-profile-20261114/ exports/parsers/alignedranks/
materialgroups/model/loghealth/imageidentity/manifests; TECHNICAL exactpaths/limits.
Owntracked evidence docs committed locally, matching ignored BACKLOG updated,
HANDOFF pre-existing untracked preserved. No push/merge/release.


**Latest: dev128 compiled-entry naming implemented, validated and delivered.**
Stefan approved implementation. tools/native/name_shader_entries.py mechanically
renames base/motion entries to nfsmw_STAGE_KEY[/_motion] AFTER existing shader
rewrites. Identifier substitution exact-reversible, idempotent, rejects malformed
keys/mixed naming/missing base. No shaderBody/math/interface/constant/spec edits.
NativeShaderFunction helper selects named entry if present, otherwise legacy
shaderMain/Motion; a present entry's specialization failure stays failed, never
silently legacy. Used for load/alpha/motion variants; flags/keys/internal shaders
unchanged. All101normal libraries regenerated in isolated audit cache,3debug
libraries retained legacy/byte-identical. All5metadata files unchanged127;104libs/
109files total. iOS18/exact-math flags retained. Original live shader cache intact.

Checks:4Python naming tests,24loader state combinations/72GPUdispatches on Mac,
legacy/named/mixed preference+injected failclosed/nil/missingmotion PASS;
6realPS/VS families x24base/motion/spec/gather=144interface comparisons PASS.
All101iOS translate+compile/link PASS35.991563375s; appcompile/link PASS17.491s,
configure/package PASS1.479/7.027s. ZIP/codesign pass, shader names/metadata/oldcache
hashes checked. Runtime only__TEXT,__cstring build-watermark section changed;
all other runtime sections including machine code identical127, GPUlib identical.
NewmainUUID1463E873-BD01-3F0C-B39C-0B64E846597B/runtime
2BF028C3-7030-3218-AB7E-53C59017F379/GPUF35FCE03 unchanged.

Retained ios/build/NFSMW-0.6.1-dev128-compiled-shader-names.ipa30771377bytes,
SHAd8c100d97b65462a88191561440c4cd390653bbf07f2c3b6d65af7cc0b26ec5c,
bundle0.6.0/code11. Verified Desktop copy; Desktop127 moved toTrash after Stefan
explicitly approved exact128/127 operations following auto-review rejection.
Stable/repositoryIPAs preserved, no unresolved delivery approval.
Private audit ios/build/dev128-compiled-shader-names-20261114/ retains source/
library manifests, original containers/generatedsources, tests/build/verification/
unpackedapp/delivery. No game-derived contents tracked. Owncode/CHANGELOG/docs
locally committed, ignored matching BACKLOG updated, HANDOFF preserved untracked.

**Next ONE phone input:** install128 preserving data/caches; allow graphics
preparation before gameplay, warm drive~1minute. Keep B and descriptorfalse;
nativeGPUcapture/costprobeOFF/loggingON/DetailedOFF. Same InstrumentsMetalSystem
Trace with ShaderTimelineENABLED/PerformanceLimiters/defaultstate,7–12s active
scene/pursuit plusmatchinglog. This is specifically to accept compiled material
names in driver profiler, not a repeat128power/CPU A/B or claim GPU saving.
Host interface/source checks do NOT prove device picture/performance or profiler
names. First verify newUUID/nonzero raw profiler intervals and key-bearing names;
if valid, map dominant pass programs to material/source/state; if naming still
absent diagnose rather than ask for identical reruns. No battery benefit claimed.

**Build procedure update:** ordinary live cache remains legacy and loader accepts
it. Current build-0.6 configured NFSMW_NATIVE_SHADERS_DIR to ABSOLUTE repository
`ios/build/dev128-compiled-shader-names-20261114/shaders/lib` (keep this ignored
folder; no /tmpdependency). Named-cache regeneration: normal build_shaders.sh
now applies name_shader_entries.py; use a new output folder and retain old debug
libraries/camera_constants and pipeline seed as checked, then explicitly configure
the shader directory. Do not regenerate the live cache in place or clear device
caches for naming. Full exact commands/failures/limits TECHNICAL below. No new
runtime flag/default, no SDK source edits, push/merge/release.


**Latest: dev127 trace analyzed; real profiler intervals present, material names
still missing.** Desktop12.224187s MetalSystemTrace Nov14
01:20:20.146–01:20:32.370+02, iPhone17ProMax/iOS27.3(24C5037i), Instruments27.2;
ShaderTimelineENABLED/PerformanceLimiters/defaultstate verified. ExactmainUUID
F0B0327E/runtime96738934/GPUF35FCE03 verified in exported image samples. B/new
flagfalse/1x60/noAA/MetalFXoff confirmed; driving68.273s before capture, no logged
restart/background within. Nominal throughout,0captureerror-level lines;
2complete in-capture pacing groups600frames0off-grid and2completeaudio windows
0gaps. No new subjective user report inferred.

663tracefiles/414659087bytes archived to capture-date14November Debug/
dev127_iphone_gpu_shader_timeline.trace, matchinglog940656bytes. Every file/log
size+SHA verified before BOTH Desktop inputs deleted, and again after exports.
Archive treeSHAb9103a3bb118d74851d9ab27e6084c45df04dc62a5c200a16417ace11e171153;
logSHAe3c8763ef6811348eee03cb57566cfa3e89f46b3bb87f18a7a3628d72b63abda.
Full paths/manifests in TECHNICAL/private ios/build/dev127-gpu-profile-20261114/.

148899raw gpu-shader-profiler-interval rows,3051compiled-shader metadata rows;
rawPCsample/derivedMetalShaderTimeline tables empty, so don't call whole trace
empty.1–11s complete-frame window599appcommandbuffers,111005profiler rows joined
byGPUsubmissionID+timeoverlap, PC mapped to323unique appshader ranges. Dominant
RenderCommand24 fragment3.061ms/frame/vertex1.500ms/frame; separate stage durations,
not additive wall time. Main-scene identity is strong pass-order/timing inference,
not an explicit target label. Six anonymous programs69.19%duration-weighted
fragment profiler share there;3.43%weight unmapped. Shares are sampled occupancy,
NOT shader/energy savings or material identities. Counters export had88definitions
but0profile rows, no measured ALU/bandwidth-limiter diagnosis claimed.

**Correction:** all app compiled names remain generic shaderMain/Motion; function
label field empty. Dev127 label assignments compiled but DID NOT solve actual
Instruments identification. CHANGELOG wording corrected; no request to repeat
same capture. Do not guess material keys from numeric IDs/byte lengths/drawcounts.
Offline prototype renaming COMPILED entry points for tree/road/car sources passes
3Maccompile+links, exact inverse-rename source equality, and Metal-library loading
exposes both expected unique base/motion names with oldshaderMain absent. This
is a local feasibility proof, NOT yet iOS profiler acceptance or game integration.
No live cache/shader/default/app/SDK changes or newIPA in this session.

**Next:** implement source naming in shader build pipeline and compatible loader
(named entry first, legacy fallback), validate interfaces/constants/variants and
isolated regenerated libraries before delivery/another phone request. Keep exact
math, shader algorithms, textures/graphics, startup preparation and B unchanged;
do not clear caches, enable native CAPTURE or repeat omission/power matrix.
Production named entries NOT IMPLEMENTED yet; user need not record again now.
Private prototypes/results/scripts retained. Own evidence/CHANGELOG committed
locally, matching ignored BACKLOG updated, pre-existing HANDOFF preserved;
no push/merge/release. No battery reduction established by this diagnostic run.


**Latest: dev127 GPU shader labels built, verified and delivered.** Main-scene
material attribution remains the gate. Existing41 trace shader-list export has
3365compiled metadata rows but0shader-profiler samples/0interval rows (Shader
Timeline disabled); material identities are not timings. Current base functions
are named, but PixelVariant/MotionVariant dropped labels, yielding generic
shaderMain/shaderMainMotion entries. Renderer now labels specialized functions
ps_KEY alphaSPEC / ps_or_vs_KEY alphaSPEC motion; no shader logic, variant key,
render order/target/args/default changes. Runtime/GPU and all109shaderfiles/
104metallibs byte-identical126. No battery improvement claimed from labels.

Built with documented build-0.6 ipa -j12: exit0/21.022301459s; ZIP/codesign checks
pass. Retained ios/build/NFSMW-0.6.1-dev127-gpu-shader-labels.ipa30768958bytes,
SHAcbb1e7db52838b8918867c746d2b94fbc9e52c572230b86f3e20ba644e6fbb9a,
mainUUIDF0B0327E-ED8D-3D4E-A57D-2FB3A950A603. Bundle0.6.0/code11 unchanged;
runtime96738934/GPUF35FCE03 unchanged. Private audit
`ios/build/gpu-material-attribution-20261114/` retains exports/build/artifact/
signing/delivery checks. Desktop127 copy SHAverified; Desktop126 moved to Trash,
stable unchanged. Initial auto-review rejected transfer/trash; no action ran.
User then explicitly approved exact actions, retry succeeded. No approval pending.

**Next ONE targeted input:** install127 preserving game data/caches, retain B+
`--nfsmw_native_descriptor_runs=false`. Native GPU frame capture and GPU cost per
shader OFF, normal loggingON/Detailed logOFF. In Mac Instruments choose Metal
System Trace targeting iPhone LiveContainer; Recording Options/Metal Application:
GPU Counter Set Performance Limiters, Shader Timeline ENABLED, default induced
GPU state. Warm drive about1minute, record only7s ordinary active scene/pursuit;
save trace+matchinglog to Desktop. Not another TimeProfiler/power A/B. High CPU
sampling irrelevant. Shader Timeline supplies sampled material execution, not
exact isolated draw cost. Existing long enabled traces were unusable; short
recording success here is NOT guaranteed. First inspect rows/settings/newUUID;
if empty, stop and diagnose that file, no automatic repeat matrix. If valid,
map main-pass fragment samples to shader/state/source before optimization.

Native in-game CAPTURE remains parked (known freeze/crash), not prerequisite.
Do not substitute it for Instruments or revive broad draw-omission cost probe,
which alters output across passes. Current31sample pass ranking remains context;
old complementary tree passes, rain-dependent road inputs and failed depth
handoff remain constraints. Source labels compile/package verified only; actual
on-device Instruments naming/recording acceptance pending. Own code/CHANGELOG/
shared docs committed locally; matching ignored BACKLOG updated/not staged,
HANDOFF pre-existing untracked preserved; no push/merge/release.


**Latest: GPU audit started; current126 pass ranking replaces old41 timing lead.**
User agrees GPU deserves priority. CPU/source trials remain parked, B retained,
newdescriptorfalse. Existing OFF/ON logs have16/15periodic GPU profiles in8–85s.
Means OFF/ON: main d4683.711/2.671ms (~41.86/41.26%incremental attribution),
cube-face d7c01.542/1.253ms (~17.40/19.35%), shadow d0300.994/0.632ms
(~11.22/9.76%). Main-scene+reflection/shadow work is first priority. These are
sparse pass timestamp increments, not shader-only execution, GPU utilization,
power fractions or causal OFF/ON deltas. Absolute differences confounded; do
not attribute them to descriptor flag. All colour-copy blits0.342/0.256ms(~4%),
so handoff extension is secondary, not a replacement main-scene target.

Current log confirms color handoff ON but0copies saved:15summaries/arm, scene
planner rejects mirror shader8436534c; other candidates fail layout. Source
mirrors use a separately scaled/shifted viewport, which existing extent proof
omits. Do NOT remove guard; accepting mirror may still fail layout/extent.
Dead stores already discarded; shadow-depth handoff remains parked (wrong
picture), distortion post copy remains required. No safe bandwidth rewrite
proved by enabled-but-unused handoff census.

Recovered baseline pixel sources2442daf2(car paint) and8436534c(mirror) from
localISO with existing host translator into ignored audit. Car body1x2D/1x3D/
1xShadow9/1xcube; mirror1x2Dalpha/1xcube. No duplicate fetch identified. Existing
shadow gathers/alpha specializations already implemented, broad fast-math stays
unsafe. Old snapshot tree348/fence330/car170draws is only historical inventory,
not per-shader cost/current workload. Current profiles identify PASSES, not which
materials dominate within them; that attribution remains missing.

**Next:** bounded main-scene shader/coverage investigation must address that
missing material attribution before proposing a rewrite; inspect existing scene
shader/state artifacts and define the smallest pass-specific diagnostic only if
needed, with its exact question/overhead. No repeated omission/power matrix or
blind shader changes. No new capture requested or app/SDK/build/default changed.
Private audit ios/build/gpu-source-audit-20261114/ has parser/ranking, historical
inventory, source/artifact hashes and recovered sources; TECHNICAL details limits
and unsuccessful VS lookup. Own tracked evidence docs committed locally; ignored
BACKLOG updated, HANDOFF remains pre-existing untracked; no push/merge/release.


**Latest follow-up: remaining opportunities reviewed; no new switch/build proposed.**
After parking descriptor runs, user asks what else is possible. Existing OFF
8–85s report has Record5287ms self/8940ms named-inclusive union of73692ms app
(~7.17%/~12.13%); writer/CP union5518ms(~7.49%). These overlap and are CPU
attribution envelopes, NOT removable cost, additive savings or power fractions.
G2/packed-mesh remain parked; another matcher/fingerprint cache is not the next
step. Source confirms constants already compare/copy shader-used ranges and
upload once per consecutive distinct set. Guest culling alreadytrue in source
and current log; old D-018 defaultfalse backlog text is historical, not a new
switch to enable. Current full-target scissor has documented untiled semantics;
do not enable dormant guest-tile scissors as an optimization.

**Next recommended bounded investigation:** GPU shader/main-scene and render-
target memory-traffic source audit using existing captures/private shader sources
and current pass graph. Identify a specific output-preserving redundant operation
or intermediate traffic before proposing implementation or another device capture.
Historical dev41 dominant fragment encoder~6.3ms/~57%active GPU is only a lead,
not a measurement of current126 pass mix. Audit shader liveness/repeated fetches
and target producer/consumer/load/store lifetimes; no generic prepass/reordering,
precision/quality reduction or presumed dry-road removable work. If existing
artifacts cannot attribute a target, say so before requesting a narrowly justified
capture. CPU Record full-body decomposition is a secondary source lead, excluding
parked lifetime/cache proposals; no proven safe rewrite ready. Timer/wake cuts
already have negative power evidence; XMA replacement remains high effort with
unproven return. No new test requested/code/default/IPA changed. Established B
retained, descriptorfalse. TECHNICAL records evidence and limits. Own tracked
notes committed locally; ignored BACKLOG updated, pre-existing untracked HANDOFF
preserved, no push/merge/release.


**Latest: same-build dev126 OFF control analyzed; descriptor-run trial PARKED.**
The user forgot High sampling. Actual Running sample weights are1ms OFF versus
100us ON; weighted aggregate CPU remains usable, raw sample counts are not a
comparison. No repeat requested solely to rescue this marginal trial. Same main/
runtime/GPU UUIDs as ON, new flagOFF/no sampled reports, oldcopyON and B/graphics
controls unchanged. OFF Nov14 00:33:54.136–00:35:24.830+02,90.694416s,
iPhone17ProMax/iOS27.3; Nominal throughout. Near-start pursuit restart+1.667s,
then no logged later restart. Guarded4800fully summarizedframes median60FPS,
0audio gaps,1off-grid/4800(worst4.2ms). No error-level/GPU errors in trace; one
watchdog RECOVERY warning+0.590s belongs to pre-capture watchdog dumps, before
recorded driving/analysis guard. No new user subjective-normal report inferred.

Same preselected8–50/8–85s, helper-inclusive target union (ON includes missing-
parent helpers): OFF1773.0/2959.0ms versus ON1771.3/3886.2ms (-0.096%/+31.335%).
Whole-app OFF41838/73692 versus ON46661.5/105925.2ms (+11.529%/+43.740%). Short
window target effectively flat; longer comparison unsupported as a causal win
or regression: live-work/core placement, OFF earlier warm-up and10x sampling
frequency/overhead differ. Do not normalize by app/other workers to manufacture
a saving. No practical net CPU/energy benefit demonstrated; no power acceptance.

**Decision/next:** keep `--nfsmw_native_descriptor_runs=false` (already default),
park this trial under the agreed stop rule; no new IPA, redo, power pair or
expanding capture matrix. Retain established Run B and its separately qualified
~7.28%group power observation. This does not establish a global optimization
ceiling. Before any further implementation or device test, reassess larger
remaining source costs against existing evidence and identify meaningful safely
removable work; do not automatically reopen G2/packed-mesh/micro-cache rounds.
No app/source/default/build changes this session.

OFF Desktop Untitled.trace/log archived and verified then deleted, including
post-export recheck: capture-date Debug/14 November2026/
dev126_iphone_pursuit_time_profile_off.trace (277files/70276382bytes, treeSHA
3feee7f254ffc07e8bdb072bae4a5f1670a05f16289b3ce668e794eab4d5a8f4), matching
_off_nfsmw.log1143826bytes/SHA
d0e6d19e123338c8d8e175881ca7adb561b0d1e629bd49f3e2e535fd52a178c7.
Private audit ios/build/dev126-off-time-profile-20261114/ retains complete
manifests, exports, scripts, weighted results and comparison.json. Full absolute
archive paths/commands/limitations TECHNICAL. Own three tracked evidence docs
committed locally; existing matching private ignored BACKLOG updated/not staged.
Pre-existing untracked HANDOFF_CHATGPT.md preserved; no push/merge/release.

Earlier ON-only checkpoint follows as history; its requested OFF control is now
complete and its pending next action is superseded above.


**Latest: dev126 ON device check analyzed; correctness/coverage PASS, CPU
benefit INCONCLUSIVE.** User says everything felt fine. Main079971D1/runtime
96738934/GPUF35FCE03 captured UUIDs match retained126; descriptor flagON, oldcopyON,
same B ownership/index/prepared/fetchON, encoding/repeat/registerOFF. Graphics
all25baseline lines1x/60/MetalFXoff/FXAAoff/MSAA0, auto/controller/group unchanged.
Capture Nov13 23:57:56.860–23:59:28.759+02,91.899121s, iPhone17ProMax/iOS27.3,
High100us. Driving+1.915s, no restart in log; background1.057s AFTER stop.
4800fully summarized guardedframes all60FPS,0audio gaps,1off-grid/4800(worst4.2ms),
no errors/watchdogs/GPU errors INSIDE capture, Nominal throughout. Startup997error
lines are two watchdog/semaphore dumps before recording; after-background61.4ms
GPU hitch is outside capture. No attribution/new bug investigation from those.

16complete guarded sampled-report intervals:14946sampled invocations counted ONCE,
55852VS+PSruns/113482native descriptors,0partial/refused/fallback/invalid. This is
sampled reach, not proof all possible inputs accepted. Most runs single (~65%VS/
91%PS); CPU gate still matters despite perfect observed admission.

Correct CPU scope is UNION(82699100 wrapper/body OR ALL descriptor helpers),
including helper samples whose parent unwinds to unknown. Do NOT report apparent
44%self drop or26.85%named-parent drop as saving: work moved to outlined helpers.
Primary preselected8–50s42s: dev1251988.5 vs1261771.3ms(-10.92%target); wholeapp
51988.2vs46661.5(-10.25%), target share3.825vs3.796%essentiallyflat. Common8–85s77s:
3686.1vs3886.2ms(+5.43%target), app104941.3vs105925.2(+0.94%). Parent-missing helper
316.8/676.0ms INCLUDED, Report1.7/3.5ms INCLUDED. Same graphics and similar work
proxies, but historical different-build/sitting/live pursuit and core/clock
confounds; no useful net CPU/energy acceptance/default promotion yet.

**Next:** ONE SAME dev126 OFF reference, cold restart, replace only the new line
with `--nfsmw_native_descriptor_runs=false`, keep remaining B/settings unchanged.
90–120s comparable uninterrupted pursuit, TimeProfiler+log. No new IPA/power
profile or expanding matrix. This control has a concrete purpose: isolate runtime
trial from historical125/build/layout and scene variability. If still mixed,
park/disable rather than keep requesting traces to rescue it. Established B stays
working reference; no code/flag defaults changed this analysis.

Received Desktop Untitled.trace/nfsmw.log archived under capture-date Nov13 Debug:
dev126_iphone_pursuit_time_profile.trace (293files/125342993bytes,
treeSHAa4b0c45eae8018ec38730ca53ceda73c99e41426ff340b126c736b1c359b0cde)
and matching _nfsmw.log847816bytes/SHA
b9e0e10da9eec5fd570d018090eb64ca1b92943ebe653ababf06b355eb81a31a.
BOTH Desktop copies deleted ONLY after verification per latest standing rule;
all293archive files/log reverified after exports. Debug originals remain intact.
Audit ios/build/dev126-time-profile-20261114/ (analysis date14, capture date13),
comparison.json final corrected result; earlier target-cpu.log has parent-only
intermediate metrics, not accepted speedup. Full paths/methods/limits TECHNICAL.
Own evidence docs committed locally; ignored private BACKLOG updated/not staged,
pre-existing untracked HANDOFF preserved, no app/SDK/build/IPA/push/merge/release.

Earlier dev126 delivery checkpoint below is historical; its pending ON check is
completed, next is the single same-build OFF reference above.

**Latest: dev126 descriptor-run trial implemented, checked, signed, delivered.**
Stefan approved device trial. New restart-only defaultfalse
`nfsmw_native_descriptor_runs`; separate from battery group/old copy flag.
Production core ios/src/game_constant_descriptors.h/.cpp, exact two full-run
patch tools/ios/patch_game_constant_descriptors.py after oldcopy patch. Core
unchanged from host prototype; old tools header now compatibility include.
Refused run's backedge bypasses admission for ALL remaining fallback descriptors;
completed prefix resumes at correct cursor. OFF bypasses sampler and core.
About1/1024 WHOLE guest invocations sampled (atomic sequence+mixed selector);
local counts initialized only on samples, merge/report about5s only when sampled.
Coverage is sampled; fallback count based on entry span, not per-fallback-loop
instrumentation. Startup logs new flag/dev126; no default promotion.

PASS5428 five-arm original/current/core/installedOFF/installedON full-state cases
ASan/UBSan,26unchanged core rejections; sampled counters/one-admission suffix,
old patch coexistence/apply/idempotence/status/revert/failure atomicity checked.
Installed -O2 5420non-injected cases plus64casesx7 cost matrix. ON multi4–64runs
~38–55%cheaper hot/~39–54%rotating32fixtures INCLUDING sampling/admission, but
supported singles -29.77%to+10.72% and first-refused singles+14.86%to+65.84%.
OFF case-median deltas -15.946..+18.675ns/run (single -2.172..+3.839), no exact
zero-overhead or whole-app/device power claim. Host Report is stubbed; actual
mutex/clock/log only validated by iOS compile/link. Need real coverage/CPU check.

Build incremental exit0,25.844338s, isolated build-0.6/SDK, -j12; ZIP CRC/deep
strict codesign pass.104metallibs/all109NativeShaders files incl seed identical
125. GPU library byte-identical. Runtime rebuilt due UI build watermark only:
12cstring bytes differ, ALL other file-backed sections/machine code identical;
UUID/signature changed. No SDK source edits; canonical SDK/reference status
unchanged. Keep new runtimeUUID for next symbolication, not dev125's.

Retained ios/build/NFSMW-0.6.1-dev126-descriptor-runs.ipa,30768156bytes,
SHA25607053a93bffa1ce07ce40527f6a54fb78c0b9fa96d711c4004c80b77c3ffe83a,
mainUUID079971D1-3C90-31C1-8074-D77D7DC23BCF,
runtime96738934-2740-375A-A2EC-587CF040296C,GPUF35FCE03-AE0C-3B71-82A1-B365C5438C4F.
Verified same IPA on iCloud Desktop; older dev125 Desktop IPA moved to Trash,
stable0.6.0 hash unchanged; retained ios/build IPAs preserved.
Audit ios/build/dev126-descriptor-runs-20261113/ contains tests, cost JSON, build
attempts, extracted signed app, artifact/delivery/source verification and runtime
section comparison. Stale shared-cache build failure preserved, not hidden.

**Next:** install dev126 preserving game data/caches, cold force-quit/restart
LiveContainer with the SAME complete B controls plus
`--nfsmw_native_descriptor_runs=true`. One uninterrupted90–120s same-style pursuit,
TimeProfiler+nfsmw.log, report picture/controls/audio/pacing. Keep60/1x/noAA/
MetalFXoff/auto and other controls unchanged. No new power pair yet. Check startup
flagON/dev126/UUID, sampled native/fallback coverage, full82699100 CPU including
sampling/report overhead and adjacent unchanged workers/FPS. Rollback is the one
new flagfalse; existingB remains reference. Do not imply device benefit from host.

Reproduction after USA codegen: oldcopy patch first, then
`python3 tools/ios/patch_game_constant_descriptors.py` (--status/--revert supported;
revert new before reverting old). generate_code.py applies this order, CMake
refuses missing/changed edits. New production check:
`python3 tools/ios/test_game_constant_descriptors.py --output ios/build/dev126-descriptor-runs-20261113`
with --benchmark for installed CURRENT/OFF/ON cost test. Base host gate remains
compatible with already-applied production patch. Build uses isolated command
above; do not use stale ordinary preset. No unrelated SDK source modifications.

Own code/tests/checkpoint/evidence/CHANGELOG locally committed, private ignored
BACKLOG updated but not staged; pre-existing untracked HANDOFF preserved. No
push/merge/release. Prior November12 host-only entries below are historical.

**Latest: full descriptor-run HOST prototype completed after Stefan's approval.**
New tools/native/constant_descriptor_candidate.h is HOST-ONLY, no game includer;
new test_constant_descriptor_run.py extracts exact full original and current USA
826991D8/8269933C runs (setup/copy/dirty-mask/loop), not only short vector copies.
Bounded64 descriptors, ordinary aligned ranges, exact bank/descriptor checks;
unknown/alias cases use current path. False may follow a completed prefix:
resume at ctx.r11, never restart. Preserves full PPC state/stack/memory; metadata
lookup reloaded each descriptor so prior writes can change later selections.

ASan/UBSan PASS5428 three-arm full-loop comparisons,26unchanged rejections,
late-prefix resumption; raw widths/indices0–1023,1–64runs,65/emptyfallback,
copy overlap, stack sources, unaligned sources, mutable lookup/dirty aliases,
and injected post-copy descriptor changes. Keeps the original later descriptor
reload before dirty-state calculation (found during source review).
Final -O2 PASS5420 non-injected checks and64costcases x7rotating-arm trials,30000runs/arm.
Synthetic supported4–64runs41.86–55.91%cheaper than CURRENT hot,39.32–54.43%cheaper
with32rotatingfixtures; supported1run5.35–33.86%cheaper hot. Rejected single runs
add20.43–62.31%scoped overhead; prefix fallback4+ can still win10.62–28.46%.
Do not average cases or multiply by old1.79%app envelope to claim CPU/energy gain.
Real eligibility/run-length/mutation distribution still unknown. No recorded
pursuit replay/full function/CP/GPU or device validation performed.

**Next:** host result justifies production integration as independent default-OFF
trial with exact source guards/rollback and coverage/fallback diagnostics, then
ONE correctness+Time Profiler/log device run under unchanged B controls. No power
pair until practical CPU/correctness supports it. Need check default-OFF admission
cost when integrating; no new game flag/patch/IPA exists YET. This is a positive
host feasibility result, not accepted default/ship/energy result. Don't redo G2,
asset immutability assumptions or existing two-copy patch. Audit ios/build/
constant-descriptor-gate-20261112/{sanitized-reload.log,benchmark-reload.log,
host-costs-reload.json,cost-summary.json,inputs-reload.json}; earlier logs preserved.

Reproduce from repo root (requires existing USA codegen and adjacent SDK):
`python3 tools/native/test_constant_descriptor_run.py --output ios/build/constant-descriptor-gate-20261112`
then the same command with `--benchmark` for the -O2 cost matrix. Generated
fixture source/binaries belong in ignored output, not tracked/proprietary code.

This session changes tools/tests/docs only, B/game/SDK/codegen/IPA unchanged.
Own tracked work locally committed; ignored private BACKLOG updated, pre-existing
untracked HANDOFF preserved. No CHANGELOG for host-only prototype; no push/merge/
release. Host test command below/TECHNICAL, no app build procedure change.


**Latest: parent asset lifecycle follow-up completed; native packed-mesh fast
path PARKED.** Generic relocation823B0578 ->823B04B8 calls unload823B0398,
overlap-safe move82157F38, then reload823B0308 with global delta82A2CC18.
Typed dispatch823B0280/823B01F8 and loaded-image callback node8290818C identify
80134000 ->8221AEC8/8221AF90 ->8221A5D8/8221ACE0. Alternate streamed callbacks
8221B038/8221B0C0 also reach those parent boundaries;824F5938/824F5790 show another
move/reload route. Load/unload sampled DURING pursuit (11.1/2.8ms in102s), and
generic asset movement sampled too; not proof this particular mesh moved or was
mutated. Registration cannot be startup-only. Parent hooks handle known lifecycle,
but do NOT prove all raw alias writes or attribute this class's async CP cost.
Do not keep doing another round of the same mesh ownership audit without new
write-coverage/cost evidence. No native registry/fast path/diagnostic IPA justified.

**Next bounded target, already localized offline:** shader/state constant commit
82699100 self1701.2/51988.2ms=3.2723%appCPU (extended2.9859%). UUID/SHA reverified;
787leafPCs symbolicated. Two descriptor loops' source attribution930.6ms=1.7900%
appCPU, including332.4ms on EXISTING native-copy call lines (nested, not additive).
They still perform descriptor walks/spills/reloads/dirty masks; not wholly waste.
Next HOST-only actual full-loop reference/current/candidate differential and
cost gate for a native descriptor-run path, preserving ordering/alias fallbacks,
PPC GPR/vector/CR/XER/stack/dirty state. Do not repeat the old two-copy patch or
revive register transport/G2. Stop if full cost including guards/fallback is not
consistently useful; no app patch/build or phone recording before evidence.
Audit ios/build/asset-lifetime-audit-20261112/:23function extracts, image-tables,
profile-boundaries, constant PC/source groups, scripts and input hashes.

Run B unchanged; no app/SDK/generated-source/flag/build/IPA change this session.
Source/evidence docs locally committed; ignored private BACKLOG updated,
pre-existing untracked HANDOFF preserved. No push/merge/release.

Earlier mesh-audit checkpoint below is historical; its pending parent audit is
now completed/parked rather than the next action.


**Latest source continuation: packed-mesh resource boundary audited.** Identified
asset load8221A5D8 -> mesh fixup8243D8D0 -> vertex/index header82691BB0/82691C18;
render82452528 -> bind8258D770/8258D868 -> fetch flush825A2B88;
asset unload8221ACE0 -> mesh retirement8243DE48. This is a packed-mesh candidate,
NOT proof of static/world-only/immutable classification. Headers borrow raw chunk
memory, not ownership of immutable native storage. Header constructor hooks alone
miss already-fixed/reloaded paths; load/relocation/address reuse need generations.
Direct writes/aliases and generic lock/unlock remain unproved, so current content
checks cannot safely be removed. Native CP draw interface lacks resource IDs and
write generations; load/bind/unload notifications alone do not solve that gap.

Cost gate: existing dev125 primary42s all Fingerprint self341.2/51988.2ms=0.6563%
appCPU; extended102s1431.7/145414.5=0.9846%. This includes textures/all classes,
not just candidate geometry; no battery percentage inferred, inline/caller cost
not covered by this self bound. Reject fingerprint-ONLY new registry/cache for now;
not a verdict against full native asset preparation. Wider attribute-preparation
self2218.2ms includes validation/decode/collection, not wholly removable.
Audit ios/build/static-geometry-audit-20261112/audit-summary.json with16hashed
function extracts and56575-function direct-call index. Details/next gate TECHNICAL.

**Next source action:** resolve ownership/relocation/alias writes at the parent
asset boundary8221A5D8/8221ACE0 (not another per-draw cache), and attribute this
class's wider preparation cost from existing evidence before proposing full native
asset conversion. No proven immutable class or accepted implementation yet. If
those cannot be established, park this class and choose another measured cost;
do not build a shadow-only diagnostic IPA or request another phone run by default.
Run B unchanged, G2 parked. This session source/evidence only, no code/build/test/
IPA/SDK changes. Local docs commit; ignored private BACKLOG updated, pre-existing
untracked HANDOFF preserved. No push/merge/release.


**Latest: consolidated dev125 power A/B analyzed.** Same-sitting iPhone 17 Pro
Max/iOS 27.3 pair supports keeping B as the working configuration on this phone:
primary 15–175s estimated system drain A40.0569 vs B37.1388 percentage points/hour,
**7.28% relatively lower** (2.9181 points/hour). Preselected sensitivity windows
10–170s and30–170s show6.70% and6.87% lower. Both60FPS medians, no audio gaps;
user says normal/uninterrupted, unplugged/LPMoff. Brightness27% and thermalNominal
measured both. Positive group-level ENERGY observation now exists; supersedes
older absence-of-power-evidence wording below. This is NOT measured CPU time:
CPU-associated impact14.0%lower, total instruction rate essentiallyequal(+0.07%),
GPU-associated impact5.0%higher. No global ceiling established.

A command_reuse=false/prepared_geometry=false; B bothtrue. BOTH encodingfalse,
repeat_counterfalse, geometry_handofftrue, owner_indextrue, vfetch_cachetrue,
register_batchesfalse/register_flushesfalse; same dev125 markers and graphics
1x/cap60/MetalFXoff/FXAAoff/MSAA0. This isolates active flag group in same build,
not unconditional hooks/layout changes or pristine pre-pass renderer. Do not
add7.28% to earlier controller4.67% or promise this exact gain to all players.
Nonidentical pursuits/order/core-clock/warm-up remain confounds (B had earlier
~28s driving before recorded restart); positive direction persists trimmed windows.

**November12 follow-up flag advice:** keep the complete nine-line B list in
TECHNICAL (same as A except command_reuse/prepared_geometrytrue). Geometry
handoff/owner_index/vfetch remaintrue; no separate marginal energy percentage
established by this pair. Encodingfalse is essential because its compiled default
is true; repeat counter is diagnostics, not draw skipping; register batches and
flushes have no demonstrated net gain, remainfalse. Residency only affects ICB
encoding here, no useful extra toggle while encodingOFF. Existing default-on
optimizations need no duplicate arguments. No enable-all recommendation.
Next concrete proposed investigation: one static geometry class create/update/
retire/alias source audit against existing dev125 CPU costs; identify exactly
which validation/copy/ownership work could safely disappear before code or build.
If authoritative write coverage or meaningful removable cost cannot be shown,
reject that candidate without another phone capture. No guaranteed gain promised.

**Next:** retain B for ongoing play; no new IPA or repeated phone/Mac capture is
needed for this result. Phone-only Power Profiler is optional convenience, not
preferred over these usable Mac recordings. Keep ICB/register trialsOFF and G2
parked. Further implementation requires a concrete measured recurring-cost
proposal, not another cache by default; native resource ownership remains a
candidate requiring source coverage. No compiled-default promotion this session.

Evidence archived in November12 Debug: dev125_reference_vs_trial_power_180134_180637.trace
and dev125_reference_vs_trial_power_nfsmw.log. Full paths/hashes and caveats in
TECHNICAL. Audit ios/build/dev125-power-pair-20261112/. Archived183tracefiles and
log reverified; supplied Desktop log deleted only after archive verification.
Desktop trace not deleted by agent; unavailable at final recheck (archive intact).
Analysis-only session, own tracked evidence docs committed locally; private ignored
BACKLOG updated but not staged, pre-existing untracked HANDOFF preserved.
No app/SDK/source/flags/IPA/push/merge/release changes.

Earlier retrospective checkpoint retained as historical context:

**November12 retrospective requested by Stefan (latest scope):** step back and
assess cumulative CPU results/optimization ceiling before more implementation.
Audit native pass as dev115–125/G2, starting November10; separate preceding
controller/dev111–112 tests. YES genuine LOCAL CPU reductions supported:
dev118 command Batch~33–35%lower/disappearing sort work; dev121 SAME-build
Capture2614.7->2229.6ms(-14.73%),storage1298->825(-36.44%),lifecycle UNION
2306.8->2041.4(-11.51%) over102s despite~10%higher reported nearby draw work;
dev125 named prepared cache340.6->229.1ms(-32.74%) over42s. These are distinct
component denominators, NOT cumulative app savings. Much wins reduce machinery
ADDED earlier in this same pass; cannot claim they beat pre-pass direct renderer.

Net cumulative whole-app CPU/battery benefit remains NOT established. dev119
historical graphics+0.82%, dev121 samebuild app+6.17%withmore work, dev124 samebuild
app essentiallyflat, dev125 app-1.69%withdraws-2.47%; not causal net percentages.
Register transport lacks netCPU proof/currentOFF; G2 failed full hostgate/parked.
Pipeline warmup/mute are separate UX/features, not proven steady-stateCPU savings.
Earlier controller CONFIGURATION observed~4.67%relative lower drain/60FPS medians,
workload/effective-switch confounded; neither erase nor credit to nativepass.

Latest VERIFIED dev125 run uses ownership/geometry/reusableindex/preparedON,
encodingOFF/registerbatchesOFF/registerflushesOFF; G2 never in game. Therefore
ICB-only resource-declaration win is dormant in that configuration. Full graphics
settings WERE logged: energy-baseline lines across9dev120–125logs all1x/60,
MetalFXoff/FXAAoff/MSAA0. Earlier wording that graphics inventory was not printed
was too broad; ExtraArgs not fully printed, but these controls confirmed. Remaining
workload/core-placement/clock confounds are real; no imagined resolution mismatch.

NO evidence of global optimization ceiling. Diminishing returns demonstrated for
these particular cache/list approaches, not exhaustion of simulation/audio/GPU/
resource-lifetime algorithms. Already ARM64/Metal; more-native label no guarantee.
Latest Record13.31%appCPU, graphicsCPU43.98%, main/world/audio~50% (overlap when
using nested scopes, none wholly removable); CPU shares are not power shares.
No defensible remaining battery percentage yet. Current result is neither zero
possible benefit nor demonstrated large headroom. Audit ios/build/
cumulative-battery-review-20261112/review.json; detailed scorecard TECHNICAL.

**Next on continuation:** establish frozen original/reference vs accepted active
configuration and compare cumulative effect before another architecture proposal.
Existing dev125 fallback flags can isolate the active trial group, but do NOT
remove unconditional layouts/hooks or reproduce pristine pre-pass executable.
A proper pre-pass comparison needs verified retained original/current artifacts
and matched settings/work; not adding per-scope percentages or more uncontrolled
pursuits. No new user recording/build requested during this review, preserve
one-pair limit if a later justified power check. G2 remains parked; deeper native
resource work a candidate, not an automatic next rewrite after this step-back.
Own evidence docs committed locally, HANDOFF/private ignored BACKLOG preserved;
no code/flags/SDK/IPA/push/merge/release.

**November12 bounded G2 gate COMPLETED, G2 PARKED (latest):** Stefan approved
stable-only implementation/testing. Added HOST-ONLY tools/native/
stable_bindings_candidate.h and test_stable_binding_record.py, not game code.
Bounded512bundles/512hints/8probes per frame,6–16known decoded non-dynamic inputs,
exact current captured versions/location/integer/nonfresh checks, matching-prefix
restoration and same-frame cohort block on changes. Original per-input Capture/
fingerprint/memo/decode/failure statements unchanged. Allocation failure retains
original list; stale epochs checked before borrowed data. Optional immutable
location index preserves LAST-match/unknown-location fallback.

Actual complete Record vertex body vs reference/OFF/ON, real fetch parsing/layout
cache/Fingerprint/DecodeElement/memo/MotionMix, actual Attribute/Draw/FrameOwners/
arena:3000historical draws/arm/memoON+OFF pass ASan/UBSan, integer/remap/shape/data
writes, exact owner order/stats, eviction retention. Actual late bounds failure
after matching prefix in memoOFF publishes no partial draw or hit/build. Header
capacity/selector reuse/stale frame/fresh/dynamic/prefix/allocation tests pass.
Inverse source-edit equality guard preserves validation and all3Capture sites.
Index ranges supplied, little-endian synthetic layouts; no index/texture/state/
Metal/GPU execution or device-performance proof.

Full72case cost gate includes selection/cache initialization/collection/fallback/
consumer/teardown,7alternating3armtrials/20000draws with3000draw frame boundaries,
all-active ANDone-active consumers. Current memoON stable6/allactive/32meshes
4.356->4.268ms(-2.02%),9 5.574->5.412(-2.91%);512meshes6 5.375->5.643(+4.99%),
9 7.492->7.620(+1.71%). One-active stable often~2.5–6.6%slower, writes often lose;
OFF path also small overhead. Unindexed list reuse alone loses. Prior isolated
12–24%model win DOES NOT survive full gate. REJECT implementation for rollout;
no more G2 cache/matcher tuning, IPA or phone/power recording. Current game and
defaults untouched. Audit ios/build/g2-stable-record-20261112 (fixture failures
retained). Header kept OUT of ios/src/CMake glob, only host fixture includes it.
Host command python3 tools/native/test_stable_binding_record.py [--benchmark],
macOS/Xcode, reads existing isolated SDK xenos enum; documented limitations above.

**Next larger SOURCE action:** map authoritative create/update/retire and alias
coverage for ONE geometry resource class before native resource-version work.
Existing decoded/GPU caches already work; do not add another heuristic cache or
trust addresses/age/write_watch. Only proved resource ownership/write coverage
can retire repeated guest-resource validation/conversion safely; unknown/dynamic
data keeps reference. No blind whole-engine rewrite or another G2 trial. No new
user recording needed now; recent native battery reduction remains unproven.
Own host tool/header/docs committed locally; HANDOFF/private ignored BACKLOG/
otherrepochanges preserved, no push/merge/release.

**November12 G2 source/host feasibility started after Stefan "continue" (latest):**
Added HOST-ONLY tools/native/test_geometry_bundle_feasibility.py; no game change,
flag/default/newIPA/device request. Extracts actual Attribute/Draw/Frame/FrameOwners/
DrawArena types, compares modeled original handoff with optimistic bundle and
CAPTURE-PRESERVING bundle, including matching/list construction/draw append/
active-location lookup/teardown. Common validation/decoding, mesh-key selection,
actual Record/Metal/GPU/power NOT executed. Mesh identities supplied, production
capacity/admission/failed-input path not implemented. Do NOT treat as production
integration, full Record test or battery gain.

Source finding: current cache entry can change between validated inputs, including
same entry/aliased data; earlier input must retain its decoded version and original
Capture timing/failure effects. Therefore general "capture only on bundle miss"
is NOT established safe; optimistic arm numbers cannot justify a build. Conservative
arm retains every input Capture into temporary frame handles; fresh mask stays
per draw, exact current version/metadata equality, LAST duplicate location wins.
ASan/UBSan10000historicaldraws x32locations vs BOTH prototypes pass, frame lifetime/
version/metadata/fresh checks pass; -O2 benchmark30cases7alternating3armtrials pass
with equal consumption checksums. Stable6/9input32/512meshes capture-preserving
stage12–24%lower host time; changing4/6/9input cases~10–23%WORSE at those sizes.
1input also loses (outside currentG1 eligibility);16input stress not representative
of known game layouts. Full table/negative results TECHNICAL/audit.

**Next SOURCE gate, no new recording:** general G2 rollout FAILS cost gate.
Only evaluate bounded stable-only admission/fallback against ACTUAL Record's
validation/capture/failure timing and all consumers before production changes;
unknown/changing/missing/prepared-ineligible paths reference. Require complete
candidate cost including collector/selector/fallback and check source-level
snapshot/lifetime semantics; don't extrapolate optimistic free-input model.
If real stable-only benefit too small, park rather than ship another micro-trial.
Resource-version audit found no demonstrated authoritative write coverage; existing
write_watch=false documented stale-data history is NOT a switch to enable.
Current SDK callbacks/hot-page patches were READ ONLY; source comment/history is
not a new device reproduction or proof current callbacks necessarily fail.
Deep native resource ownership remains separate larger work, not solved by bundle.

Audit ios/build/g2-binding-feasibility-20261112 incl all sanitizer/model/final
conservative timings+30case JSON. Host command python3 tools/native/
test_geometry_bundle_feasibility.py [--benchmark], macOS+Xcode Foundation/Metal,
-O1ASan/UBSan default/-O2benchmark. No build-procedure changes. Own host tool/docs
committed locally; HANDOFF/private ignored BACKLOG/otherrepochanges preserved.
No push/merge/release.

**November12 power-strategy review (latest direction):** Stefan asks whether
changes add up and how to reduce power at unchanged performance. Re-audit finds
prior answer "not yet demonstrated" was too broad for ALL project history:
November10 alternating controller configuration29%/h ->27.56%/h (~4.67%relative),
60FPS medians, direction robust to common trimming; pursuit instructions/work
and effective switches confound isolated controller attribution. This is an
observed configuration gain, NOT proof of recent native trials or cumulative gain.
Do not erase that earlier positive evidence or repeat its low-yield tests.

Current dev125 source audit: nativeARM64+Metal already active, converted arrays
and GPU buffers ALREADY cached. A generic "make native/cache vertices" promise
is insufficient. Latest42s sample draw preparation13.31%appCPU, graphics threads
43.98%, writer/CP union8.05% (CPUcost envelopes, NOT energy shares or all removable;
scopes overlap). G1 named cache only0.441%. Next source work must justify a larger
class of eliminated work: evaluate completed binding reuse AND resource creation/
update/version ownership so repeated guest-state preparation/copies/conversion/
validation can be retired only with reliable write coverage. G2 remains a bounded
candidate, not automatic next IPA or guaranteed meaningful battery improvement;
reject if whole handoff savings small or consumed by new matching. Immutable/
known-version data first; unknown/dynamic writes retain current validation.

Power acceptance: fixed current FPS/pacing/latency/image/gameplay, one frozen
reference/configuration and most-repeatable practical workload; no adding scope
percentages or crediting fewer rendered/simulated frames. Use existing captures
and SOURCE/full-path host gate now, no more matcher/phone/power requests now.
For a supported consolidated candidate, ONE same-sitting power A/B per existing
user limit, fixed brightness/charging/thermal/settings and enough frame/audio/
workload evidence to judge comparability; inconclusive is not a win. CPU time
selects code targets; CPU/GPU/display power impacts must not be treated as watts
or divided to infer physical power fractions. If GPU cost dominates, equivalent
shader/pass/memory-traffic work needs its own identified evidence, not a blind
quality reduction or reopening parked captures/defects. Scheduling stays
cap-aware; don't blindly move critical work to efficiency cores. No percentage
battery promise, new code/flags/build/IPA in this review.

**November12 dev125 G1b device ANALYZED (latest):** exact UUID
DA395111-4E8D-3287-9E24-964EF81886F4, preparedON/table4632KiB, BOTH register
flagsOFF, ownershipON/encodingOFF/repeatOFF/indexreusable confirmed. Stefan
reports normal picture/controls/audio and uninterrupted recording. iPhone17ProMax/
iOS27.3, High100us;121.179028s00:36:17.135–00:38:18.314+02. Driving begins
1.829s into trace;8s skip avoids loading. Background transition2.435s AFTERend.
Original November11 trace preserved; verified capture-date trace+log archived
Debug/12 November 2026/dev125_iphone_pursuit_time_profile.trace and matching
_nfsmw.log. Log769425bytes/SHAfee0e2971d470d440cfd73efd42bc40a76e93d3d9e90d89ac20c667be7e95925,
302trace files/172440477bytes. Desktop log arrived during initial inspection,
then archived/verified/deleted per standing rule; post-export inputs unchanged.

6600guardedCPU-owned/ICB0 frames,21summaries60/one59.9FPS,0audio gaps/logged
errors/watchdogs/GPUerrors, thermal nominal/peak1771MiB.56.84%equivalent
attribute lookups skipped,74.26%eligible hits. Compact matcher local device
gate positive: common8–50s namedcache229.1vsdev124firstON340.6ms(-32.74%),
Find199.6vs306.9(-34.96%), eligible probes-3.33%; approximate per-probe Find
weight-32.72% (counter phases, not exact cycle cost). NearbyGPU7.431vs7.500ms,
Pshare89.47vs89.18%. Wholeapp51988.2vs52883.8ms(-1.69%), Record6918.2vs7041.3
(-1.75%) withdraws-2.47%; Recordself4168.6vs4182.9(-0.34%). Thus LOCAL matcher
improvement supported, full renderer/CPU/battery acceptance NOTpassed. Do not
credit big gains against heavier thirddev124 run (differentGPU/placement).

**Next SOURCE boundary:** CLOSE G1/G1b phone capture/matcher tuning round. No
more ON/OFF pursuit/power matrix now; keep trial/defaultsOFF pending practical
net acceptance. Evaluate G2 frame-owned immutable vertex-binding bundles so
repeated validated geometry can reuse completed attribute records/ownership
handoff across passes, rather than rebuilding every attribute list per draw.
Keep ALL original mutable buffer/index/dynamic/UP/decoded-version checks and
failure order; changed versions publish new frame-owned bundle, never reuse
merely by address/cache hit. Distinguish per-draw fresh flags from shared data;
rectangles/unsupported/failure paths original. No pointers into erasable cache
or mutable descriptions may escape to GPU. Source/reference/lifetime and FULL
handoff hit/cold/churn host cost gate before another IPA/recording; reject if
bundle matching consumes savings. Native plan G2 is feasibility boundary,
NOT implementation or claimed saving. Larger source lead: Recordself4.169s
(8.02%app) vs new named cache0.229s(0.441%app); exact dev125 PC map retained.
No new G2 code/flag/build/IPA this analysis. Audit ios/build/dev125-time-profile-20261112.
Own evidence docs committed locally; HANDOFF/private ignored BACKLOG preserved;
no push/merge/release. Existing dev125 build retained, no default promotion.

**November12 third dev124 ON capture analyzed (latest evidence):** Stefan says
normal and uninterrupted. Despite filename/location, both trace UUID and log
confirm OLD dev124 BF5FD4C9-F7F4-3D73-8244-43777D00E9BE/preparedON/table5016KiB,
not dev125. BOTH register flagsOFF, ownershipON/encodingOFF/repeatOFF/indexreusable.
Capture00:20:37.887–00:22:38.112+02 (120.224704s), iPhone17ProMax/iOS27.3,
High100us. Original November11 path preserved; capture-date verified copy and
log archived to Debug/12 November 2026/dev124_iphone_pursuit_time_profile_3.trace
and matching _nfsmw.log. Log822921bytes/SHA80724018dff6e91b78fa7d87f30bad894740b989fd48e9c6a8661c994f14403f;
Desktop source deleted ONLY after verification. Both trace copies/log unchanged
after export,300trace files/175996994bytes. Details/hash/audit TECHNICAL.

6900guardedCPU-owned/ICB0 frames,21summaries60/one59.9/one59.6FPS,0audio gaps,
0logged errors/watchdogs/GPUerrors, thermal nominal/peak1665MiB. Fullguard
56.78%equivalent attribute lookup calls avoided,74.04%eligible hits. CPU8–110s
named cache1147ms/161298.6ms app (0.711%), Find90.40%of named cache. Common8–50s
CPU66279.9ms vs priorON52883.8/OFF52909.9, Record10189.9vs7041.3/7031.7;
but GPU14.276vs7.500/7.511ms and Pshare77.88vs89.18/88.62%, unchanged workers
also higher. No causal CPU/energy result; do not credit or blame dev125.

**Next unchanged:** dev125 already signed/on Desktop; install it preserving
settings/caches, preparedtrue/BOTHbatchfalse+coldrestart, prior owner-only controls.
ONEdev125 correctness/TimeProfiler+log, no more dev124 repetitions/power matrix.
Use startup dev125 and UUID DA395111-4E8D-3287-9E24-964EF81886F4/table4632KiB
to verify the NEW matcher. No code/build/newIPA this analysis; no default promotion.
Audit ios/build/dev124-third-time-profile-20261112. Source delivery below remains
current. Own evidence docs committed locally, HANDOFF/private ignored BACKLOG
preserved as before; no push/merge/release.

**November12 dev125 G1b IMPLEMENTED, checked and delivered (current):**
Stefan approved the compact matching step. Prepared geometry remains defaultOFF
(restart-only `nfsmw_native_prepared_geometry`); BOTH register batching flags
remain OFF. Same2048 descriptions/probation/generation/hash/identity semantics.
Probe headers now separate from large descriptions; contiguous unique USED
fetch pairs compare BOTH words once. Redundant per-input binding/location/size
fields removed, metadata table5016 ->4632KiB, no validator/decoded data/frame
ownership changes. Existing full Record normalization and six original helper
body guards pass unchanged. No SDK/shader/seed modifications.

Actual production compact AND dev124 preparations each checked against original
for90,000draws/mode ON/OFF under ASan/UBSan and -O2. New checks mutate both words
of every unique used binding, including non-anchor and slots63/64/95; repeated
slots deduplicate, unused pairs preserve hits. Existing sweep/lazy node/physical
map/alias/mutable versions/lifetime/probation/collision/bypass tests retained.
All11regression commands exit0. Host alternating7trial medians, uncontended
final run: shared-binding matching/fill19–32%lower than dev124; complete measured
preparation repeated4/6/9-input cases~1–7%lower than dev124 (matrix TECHNICAL).
Small bypass and no-hit8192mesh churn still cost more than original in most
cases. These EXCLUDE validation/GPU and are NOT device CPU/battery acceptance.

Signed retained ios/build/NFSMW-0.6.1-dev125-compact-matching.ipa,30756555bytes,
SHA25688aa7c0c7e70b236d176c337258370654bae468933dfd46074b94be0b5e0e2e5,
UUID DA395111-4E8D-3287-9E24-964EF81886F4, bundle0.6.0(11).
Existing build-0.6 ipa -j12 exit0; ZIPCRC/strict deep codesign pass.104metallibs,
pipeline seed and BOTH SDK dylibs byte-identical dev124 (no badge rebuild).
Desktop copy byte/SHA verified; ONLY old Desktopdev124 moved to Trash. Stable
0.6.0 Desktop SHA unchanged, all retained ios/build IPAs preserved. No game launch.
Audit ios/build/dev125-compact-matching-20261112 contains raw tests/timings,
failed initial baseline-fixture attempt, artifact/delivery manifests and build.

**Next:** install dev125 preserving caches/settings; cold restart with
`--nfsmw_native_prepared_geometry=true --nfsmw_native_register_batches=false
--nfsmw_native_register_flushes=false`, other dev124 owner-only controls unchanged
(reuseON/encodingOFF/repeatOFF/ownerindexON/vfetchON,1x60/MSAA0/FXAAoff/MetalFXoff).
ONE90–120s pursuit Time Profiler+game log can now check correctness/FPS and
whether the host matching reduction survives on device. Do not request a power
matrix or promote defaults yet. Compare matching cost/Record at similar work,
not raw whole CPU between uncontrolled pursuits. If no practical net improvement,
close G1 tuning rather than ask for repeated unmatched runs; use existing source
attribution to choose a larger remaining recurring cost. Archive any provided
Desktop log and verify before deleting it under the standing rule.

Own session changes committed locally; preexisting untracked HANDOFF preserved.
Private ignored BACKLOG updated but deliberately not staged. Preexisting changes
in canonical SDK and NFSMW-Recompiled-Mobile preserved/uncommitted, not included.
No push/merge/release.



**November11 dev124 G1 SAME-build OFF reference ANALYZED (latest):** exact
UUIDBF5FD4C9-F7F4-3D73-8244-43777D00E9BE, preparedOFF/BOTHbatchingOFF and
other owner-only/vfetch/graphics controls verified, High100us same asON.
Desktop log archived/byte+SHA verified then deleted per standing rule:
November11Debug/dev124_iphone_pursuit_time_profile_2_nfsmw.log,786545bytes,
SHA846fd1e4722433aa8495d371dde41e6dcd10c8c4d90314aa7d406dc25d97663f.
Trace300files/158218638bytes, tree33c091bc995761470d12dd57acb46e0fc164c2684c553f42fb90e44c9df6fda2,
unchanged after export. Same app/runtime/GPU UUIDs verified. No app/SDK/build
or analyzer source change; no new IPA. Additional OFF subjective feedback not
supplied, log has no capture-time errors/watchdogs/audio gaps.

Reference also pauses59.700–63.612s (reason not reported); common primary
8–50s chosen BEFORE CPU results to avoid both runs' interruptions. Each primary
has7full300-frame windows2100CPU-owned/ICB0/ALL60FPS. OFF fullguard6600frames,
20x60/1x59.9/1x56.1;56.1window ends62.911s DURINGpause, not steady cache
regression.21audio windows0gaps, thermal nominal/peak1586MiB. No power capture.

Closest comparison yet, but not deterministic replay: ON vsOFF app52883.8 vs
52909.9ms(-0.049%), Record7041.3 vs7031.7(+0.137%) over42s; graphics-1.06%.
ON reported draws+3.364%, equivalent lookup sites+3.452%, ownerlookups+1.42%,
GPU7.500vs7.511ms; Pshare89.18vs88.62%. Approx Record/reported draw-3.12%,
not precise causal gain (300-frame phases/work mix/stackless differ). Newcache
removes54.695%lookup calls in common primary, but net whole CPU is essentially
flat; no battery acceptance/default promotion. Post74–100sON CPU-7.89%, butGPU
12.25vs14.37ms/different placement, not credited to geometry.

Source evidence same binary: remaining AttributeEntryFor call-line3246
716.9msOFF ->401.2msON (315.7ms lower); named newcache340.6msON (Find306.9).
Their rough diagnostic proxy741.8vs716.9ms scales with extra lookup workload,
consistent with matching cost consuming much of avoided work. Sampling skid/
inlining makes this a lead, not exact overhead subtraction. Recordself4321.8
OFF/4182.9ON, preferredPC union symbolicated via exact dev124 binary/objects.

**Next SOURCE action:** close capture/reference round; NO further phone/power
recordings now. Keep prepared_geometry=false, BOTHbatchingfalse, other owner
trial controls as before. Implement/design compact contiguous used-binding
identity and deduplicate repeated interleaved fetch pairs for prepared matching;
move hot state/key away from full payload/strided records. Preserve EXACT
identity/full shader hash/map/range checks, all used fetch words, cold/probation/
sweep generations, original content validation/lifetimes. Retire duplicate key
storage rather than grow cache. Actual reference differential/host cost gate
before live build. G1 remains useful plumbing/operation reduction, current net
CPU/energy gain UNPROVEN. Don't ask for another unmatched pursuit matrix.
No compact-key implementation/newIPA yet in this analysis session.

Audit ios/build/dev124-reference-time-profile-20261111 incl raw exports,
logs/source-PCs/comparison/proxy JSON; detailed controls/limits TECHNICAL.
Shared records/private ignored BACKLOG updated; own docs locally committed.
Preexisting HANDOFF untracked preserved, no push/merge/release.



**November11 dev124 G1 device ANALYZED (latest):** Stefan reports everything
normal, bust/restart in middle and suspects cops caused heavier ending.
ExactUUIDBF5FD4C9-F7F4-3D73-8244-43777D00E9BE, preparedON/BOTHbatchingOFF/
reuseON/encodingOFF/repeatOFF/indexreusable/vfetchON verified. Log844052bytes
archived/hash-verified in November11Debug as
dev124_iphone_pursuit_time_profile_nfsmw.log, SHA256
27517b58619ef4400da3987d2131262d236f6b4b7c7d7b7b81845c51de233f56;
THEN Desktop/nfsmw.log deleted. New standing rule above applies to FUTURE
provided Desktop logs after successful verified archival. Trace298files/
149788301bytes unchanged after export, manifest next to trace.116.522662s,
100us sampling, iPhone17ProMax/iOS27.3. No new app/SDK/IPA change this analysis.

Log pause62.623s/resume65.659s, CPU1s-bin spike63s=2022.2ms weight; late
peak111s=2030.5ms. Main analysis pre8–55s (47s), post74–100s (26s), restart/
settle55–74s and tail100–116.522662s separately. GPU rise starts~85s, not
only last10s; NPC cause remains user inference. No attribution of known
restart spike to renderer bug. Full guarded6300CPU-owned/ICB0,19x60/1x59.9/
1x59.8FPS;21audio windows0gaps,0budget/binding fallbacks,4off-grid frames/
6300(worst16.7ms). Clean selected3600frames ALL60FPS.0trace watchdog/error/
GPU errors, thermal nominal/peak1767MiB. Pre-trace7s startup watchdog recovered;
no recurring capture-time freeze, no parked stutter defect reopened.

Concrete operation reduction: pre8–55s15,547,949attribute lookups avoided,
53.9738%of same-run equivalent sites;71.45%eligible description hits. Post
54.2756%lookups avoided/73.70%eligible hits. Full guarded40,018,878lookups
avoided/54.9464%,73.35%eligiblehits. These are calls, NOT CPU/battery savings.
Named cache paths pre381.8ms=0.6429%app, Find343.9ms=90.07%named cache union.
Includes useful prep and misses, excludes inlined setup; not exact added cost.
Same relative47s vs dev122 app+38.29%, graphics+40.98%, Record+47.54%, but
other guest workers+33–46%, drawcount+4.22%, placement differs; dev122 C0ON,
so not matched geometry control/no net CPU or energy acceptance. Both use
100us sampling; stackless~5.06/5.13%, not a gross resolution difference.

**Next:** ONE SAME dev124 reference Time Profiler+log, change ONLY
`--nfsmw_native_prepared_geometry=false`, COLD restart. Keep BOTHbatchingfalse,
reuse/indextrue/encodingfalse/repeatfalse/vfetchtrue/1x60/MSAA0/FXAAoff/
MetalFXoff, same audio/controller, samplingHigh100us, roughly90–120s pursuit.
No new IPA/power pair. Concrete reason for reference now: useful device reach
proved, but cache Find itself costs measurable CPU; need net preparation cost
against SAME binary's original branch before more source work/default changes.
Compare per-draw/call workload+Record/source-line cache costs as well as whole
CPU; don't repeatedly re-record if pursuit/placement remains unmatched. If
reference doesn't support net gain, next source candidate is compact/deduped
binding identity for Find (90%named cost), not larger table/looser validation.
DefaultOFF stays. Preserve current matching object/build until this reference.

Analysis tool adds exact prepared-cache method scopes including demangled
return-type names and non-double-counted union, fixturesPASS. Current pre
profile's prior totals/threads/ranking weights/scopes rechecked against pre-change
analyzer (inclusive equal-weight tie ordering can vary by Python hash seed). Audit ios/build/dev124-time-profile-20261111, exact evidence TECHNICAL.
Shared records/private ignored BACKLOG updated; own analysis/docs locally
committed. HANDOFF preserved untracked, no push/merge/release.



**November11 dev124 prepared native geometry IMPLEMENTED/BUILT (latest):**
Stefan approved the proposed geometry source step. New restart-only
`nfsmw_native_prepared_geometry=false` (default OFF) caches vertex-description
preparation and lazy attribute-cache handles across repeated draws. It does NOT
cache decoded arrays/validation results/Draws/index conversion or frame/GPU
ownership. Full shader+microcode hash/dwords, physical-map base, actual vertex
range and all used fetch pairs match; source validation still original. Two-way
bounded2048descriptions/5016KiB only when first eligible draw occurs; cold key
must repeat before preparation, inputs<4/>16 and exceptional/legacy/no-layout
paths bypass. Sweep/purge invalidates generations BEFORE any cache-node erase.
All metadata CP-thread-only; render logs read per-Frame counters, not table.

90,000actual preparation comparisons per enabled/disabled process ASan/UBSan
PASS, node/lifetime/sweep/collision/probation/alias/exceptional cases PASS.
Complete Record guard allows ONLY explicit preparation edits, validation/
decoding/index/state/ownership byte-identical.11existing regression commands
PASS after narrow guards/old FrameRef fixture repairs (failures TECHNICAL).
Host seven-trial repeated4–9input/512mesh preparation3.760–9.303ms reference vs
2.470–4.318ms trial depending case (exact matrix TECHNICAL); cold8192mesh cases
can lose, small-input cases original path plus eligibility cost. NOT full
Record/phone CPU/energy savings. Existing vfetch cache must beON for eligibility
(verified ON in prior dev123 settings); do not silently change that default.

Signed `ios/build/NFSMW-0.6.1-dev124-prepared-geometry.ipa`,30756575bytes,
SHA2561b9f49e45c218204cdabac9037db9d15acc3a0287f5a37994e3606acfac9bbb7,
ARM64 UUIDBF5FD4C9-F7F4-3D73-8244-43777D00E9BE,bundle0.6.0(11).
ZIP/signature PASS,104metallibs+pipeline seed and GPU SDK byte-identical dev123.
CMake header glob reconfigured SDK build badge: runtime initialized sections
unchanged except11cstring bytes of version/timestamp, executable __text equal;
no SDK source edits. RuntimeUUIDE00FBEDA-A8C8-3CD8-AD6F-8B4CFB0B3660. Desktop
copy verified; only Desktopdev123 moved to Trash. Stable Desktop IPA was absent
before delivery; restored exact retained stable copy per standing keep-stable
rule, SHA unchanged cbc7ebc85010573a49f1a580fcf70db610ce6bdfb51fd872df533bcdc7641285.
All ios/build copies preserved. No device/game launch by agent.

**Next:** ONE90–120s pursuit Time Profiler+nfsmw.log on dev124, cold restart,
same owner-only settings/reusetrue/encodingfalse/repeatfalse/indextrue, vfetch
cachetrue, 1x60/MSAA0/FXAAoff/MetalFXoff, same audio/controller. Explicitly set
`--nfsmw_native_register_batches=false --nfsmw_native_register_flushes=false
--nfsmw_native_prepared_geometry=true`. First check image/audio/FPS, prepared
hits/misses(cold subset)/bypasses/lookups avoided and footprint. Device gain
unproven. Do NOT attribute a dev123 BOTH-batchingON -> dev124 batchingOFF CPU
change to prepared geometry. Same dev124 preparedfalse reference available if
later justified, don't request now. No power pair until meaningful CPU gate.

Audit `ios/build/dev124-prepared-geometry-20261111/`; exact boundaries, failed
attempts, matrix, artifact/SDK comparison and fixture limits in TECHNICAL.
Own code/tests/shared docs committed locally, private ignored BACKLOG updated
not staged; preexisting untracked HANDOFF preserved. Read-only rexglue-sdk-ios
status showed existing unrelated modified/untracked files; none written/staged/
committed by this session. Prepared SDK source untouched. No push/merge/release.



**November11 dev123 C1 device ANALYZED (latest):** Stefan confirms picture,
controls/audio normal. CorrectUUID5CC1ECB2-620D-3859-8718-3FD467D59843 and BOTH
batch/flush switchesON verified; prior owner-only controls unchanged. Desktop
nfsmw.log archived/hash-verified as November11Debug/
dev123_iphone_pursuit_time_profile_nfsmw.log,778303bytes,
SHA2566a8659a66f432c330df6507beea22e2b6b2eaac2dd3f296389c04dbe4f244a18.
Desktop original PRESERVED (previous deletion request was per-file dev122).
Trace282files/74854835bytes unchanged after export; manifest in same Debug
folder. iPhone17ProMax/iOS27.3;98.685518s,1ms sampling (dev122100us).

18full guarded300-frame windows5400CPU-owned/ICB0,16x60/2x59.9FPS,0binding/
budget fallback,17audio windows0gaps,2/5400off-grid(worst16.7ms). No trace-time
watchdog/error/GPU/token errors, thermal nominal/peak1669MiB. One pre-trace
loading watchdog recovered21:42:59.106;54backgroundGPU warnings only after
stop+scene resign. User acceptance for this pursuit, not all content/devices.
C1+C0 handles360862079words/1894405batches,10.61runs/batch,350.82batches/frame;
22.8869%reported range words vs C0~1.48%, functional reach improvement.
96.6488%ring byte reduction HANDLED subset only. Pending<=613, lifetimepeak1792/
2048;26005capacity PREP attempts mix append splits/reservation failure (not
lost commands; existing counter cannot separate). Do not increase pool blindly.

82s8–90s CPU comparison vs dev122: app74107.3->115662ms(+56.07%), graphics
32104.3->53862(+67.77%), writer/CP5774.1->9397(+62.74%). Nearby drawcount+2.45%,
ownerlookups+6.07%, GPU7.564->13.367ms; P-core share92.95->80.42%, unchanged
main/world/audio work also44–54%higher. Sampling100us->1000us, stackless4.94->
1.28%. NOT a controlled CPU regression/saving or energy result. Named batch
union133.6->1583ms(0.1803->1.3686%app); includes useful copies, no exact overhead
or net saving. Updated analyzer includes Collector/Publish/outerSELF; explicitly
--register-flush-hooks for verified C1 builds, because older original weak
outer aliases can share name. Entire outer inclusive4283ms includes original
work, excluded from helper union. Existing control totals/threads/old scopes
exactly unchanged on rerun8–110. Fixtures PASS; no app/SDK/IPA changes.

**Next SOURCE proposal:** close C1 correctness/coverage round, retain plumbing
and defaultOFF; normal play BOTH register_batches=false/register_flushes=false
+coldrestart, other owner-only settings unchanged. No further phone recording/
power pair now. Audit reusable prepared native geometry descriptions within
Record above existing per-attribute lookup; preserve exact source validation,
dynamic/UP handling, cache-sweep generation and frame/GPU ownership. Current
Record16873ms=14.59%app inclusive,9970ms self (not wholly removable). ExactUUID
atos of1053selfPCs maps hot lookup3138=1345ms, local destruction3334=514,
append3587=742; disassembly confirms lookup/load and refcount release sites.
Source-line groups are approximate/skid/inline, not exact removable costs.
This is a proposed larger native geometry source step, no new implementation/
IPA yet. Do not call C1 a measured battery optimization or repeat an uncontrolled
pursuit matrix. GPU main pass remains substantial; sparse pass timings identify
no safe shader simplification yet, no GPU-capture investigation reopened.

Evidence/audit `ios/build/dev123-time-profile-20261111/`; exact counts/settings/
limits in TECHNICAL. Shared tracked records and analysis tool/tests committed
locally; ignored private BACKLOG updated but not staged. Preexisting untracked
HANDOFF_CHATGPT.md preserved/excluded. No push/merge/release.



**November11 dev123 C1 compatible register flushes IMPLEMENTED/BUILT (latest):**
Stefan agreed to continuing the C1 source work. Actual outer825A3EC8 comparison
and host cost gate preceded live hooks. New restart-only
`nfsmw_native_register_flushes=false` (default OFF) aggregates only the audited
register-only suffix, after original vertex/shader helpers. Existing C0
`nfsmw_native_register_batches=false` remains independent/default OFF. C1 skips
estimated<128words or<2bank groups; these still use original emitters/C0 when
enabled. Original outer function retains dirty-mask/CPU sentinel writes. New
fetch825A2968 hook checks exact825A3FD0/source1152/192words, special8-byte
alignment. Append to privately owned1024word/32run batches only, preserve
chronological descending/repeated register order; capacity commits PREFIX then
tries current call, unknown/slow helpers run with collector suspended. No
replay/Ready mutation/whole-frame rewrite. TLS/nested/exception restoration;
unexpected ring-pointer/limit mutation while pending aborts rather than
silently reorders. Same2048slot pool/ordered SDK consumer, no SDK edits.

Host ASan/UBSan actual outer/emitter/app/CP differential1200cases per mode,
existing9regression commands PASS; source suffix call inventory guarded.
Prefix shader/vertex and segment-helper bodies are stand-ins, CP range override
is real but base WriteRegister effects mocked: hardware/whole-game correctness
still needs device run. Host seven-trial mixed cases original5.944–13.452ms,
C1+C0 5.347–11.385ms/10000; versus C0 results MIXED (-0.65%to+9.43% benefit,
not uniform); sparse admission adds~8ns/flush, so no claim of net device gain.
Detailed matrix/fixture failures and fixes in TECHNICAL, audit ignored
`ios/build/dev123-register-flushes-20261111/`. No energy claim.

Signed `ios/build/NFSMW-0.6.1-dev123-register-flushes.ipa`,30752007bytes,
SHA2561002204fd4d3676be80de55d364c22ac0ef34f2fa08051ec42a9677d1f7ae931,
ARM64 UUID5CC1ECB2-620D-3859-8718-3FD467D59843, bundle0.6.0(11).
ZIP CRC/strict deep signature/four strong hooks+originals PASS;104metallibs,
pipeline seed and BOTH SDK dylibs byte-identical dev122. Desktop IPA copy
hash-verified; ONLY prior Desktopdev122 moved to Trash; stable0.6.0 and all
`ios/build` copies preserved. No game launch/phone run by agent.

**Next:** one90–120s pursuit Mac Time Profiler+game log on dev123, cold restart,
retain dev122 owner-only settings/indextrue/reusetrue/encodingfalse/repeatfalse,
1x60/MSAA0/FXAAoff/MetalFXoff, same audio/controller conditions. Explicitly set
`--nfsmw_native_register_batches=true --nfsmw_native_register_flushes=true`.
First validate image/audio/FPS and new flushes/collected/sparse/capacity/pending
counters; compare reach against dev1221.4766%range words and profile costs,
including Collector/Publish/new outer hook (old exact Try-only scopes aren't
total C1 work). Do not infer energy gain from bytes, moved work or unmatched
pursuit totals. No power matrix until meaningful CPU/correctness gate. Normal
play/reference can use BOTH false + cold restart; same-build C0 control keeps
batchestrue/flushesfalse if later needed, don't request it yet.

Records/private ignored BACKLOG updated, CHANGELOG notes trial; own session
changes committed locally, no push/merge/release. Preexisting untracked
HANDOFF_CHATGPT.md preserved/excluded. BACKLOG intentionally remains ignored,
not force-added; build/test artifacts remain ignored local files.


**November11 dev122 C0 device run ANALYZED (latest):** Stefan reports nothing
looked off. FINAL UUIDBE5997C9-2607-39C4-91AC-3C2AB53739CA verified; register
batchesON/reuseON/encodingOFF/repeatOFF/indexreusable/geometryON. Trace already
in November11Debug; timestamp-named Desktop log copied/hash-verified there as
dev122_iphone_pursuit_time_profile_nfsmw.log,923292bytes. THEN deleted only
Desktop/Pasted2026-11-11at6.34.37PM.log as explicitly requested.315trace files/
155734035bytes unchanged after export. Archive/deletion/hash details TECHNICAL.

26guarded300-frame windows7800CPU-owned/ICB0,24x60.0/2x59.9FPS,0binding/budget
fallbacks;35audio windows0gaps,0watchdogs/foreground GPU or invalid-token errors.
68GPU background-permission warnings only after stop/scene resign. Peak1613MiB,
thermal nominal; user normal-picture/gameplay acceptance for THIS run only.
C0 correctly consumed54149vs54146produced across selected windows (carry/
concurrent sampling),0capacity fallback, pending<=10/peak18 out of2048slots.
54,146batches carry32,405,288words,130,112,996original ring bytes replaced by
1,420,580token bytes (98.91%fewer for HANDLED batches). Only6.94batches/frame,
0.0698%hook calls/1.4766%reported range-word volume;77,503,266small fallbacks.
Do NOT call98.91%a whole-stream or energy saving. Correct transport, low reach.

Same102s8–110s vs dev121 reusable control: app112772.8->100709.9ms (-10.70%),
graphics50863.4->44234.1 (-13.03%), writer/CP8503.8->7757.7 (-8.77%). Other
main/world/audio workers also lower; P-core share81.88->89.45%, nearby GPUms
12.964->8.320 and owner lookups differ despite similar drawcount. Not controlled
causal CPU/battery improvement. New named batch union182.1ms=0.1808%app,
producer166.6/consumer15.4 (overlaps/inline limits, useful work included, not
all incremental overhead). No energy claim or power gate passed.

**Next SOURCE action:** close current correctness/coverage gate, no additional
recording/power matrix now. Keep C0 default OFF; for normal play restore
`--nfsmw_native_register_batches=false`+cold restart while retaining other trial
settings (owner_index=true/reuse=true/encoding=false/repeat=false). Preserve
implemented transport/reference switch. Design higher-coverage compatible
state-flush aggregation (C1) before new hook changes: identify contiguous
ordered state windows/barriers in825A3EC8, prove capacity/source snapshots and
CPU-visible dirty-mask side effects; unknown/segment/foreign operations cannot
be silently moved or replayed. Never append to an already-published batch or
lower small-VMX threshold blindly (host negative result stands). Differential
against actual outer flush/CP order and benchmark aggregate path before live
build; current C0 is not full native D3D or a measured battery optimization.
This is SOURCE feasibility/implementation boundary work, no C1 code/newIPA yet.

Analysis tool adds exact C0 producer/consumer/helper union; fixtures PASS,
control totals/threads/prior scopes exactly unchanged. Shared records/private
BACKLOG updated; HANDOFF preserved untracked; local commit/no push/release.
Earlier device-capture requests below fulfilled.


**November11 dev122 C0 register batches IMPLEMENTED/BUILT (latest):** Stefan
approved implementation. New restart-only `nfsmw_native_register_batches=false`
(default OFF, independent of frame/ICB controls) overrides only two USA emitter
entries at10proved ordinary825A3EC8 callsites with matching base/source bounds.
Owned BE dirty spans, bounded2048-slot pool, unique tickets/Ready/acquire/release,
explicit ARM64 Ready-before-ring fence. CP private NFRB NOP consumes existing
virtual range writes in order; shaders/draws/resolves/queries/waits/swap/Record
stay original. Unsupported/small/slow-segment/alias-boundary/capacity cases
fall back BEFORE guest mutation. Invalid published token aborts buffer processing
with error, never silently skips omitted state. Source read uses generated
REX_RAW_ADDR, including high-physical host skew. Pool ~9MiB, process lifetime,
no slot overwrite/wait/purge while in flight. No hot switching; cold restart.

Scalar gate>=32dirty words; grouped>=256. Earlier host tests showed token path
slower for16/64word grouped runs; those now stay original. Host fixtures execute
actual generated scalar/VMX emitters, app hooks and SDK NOP/type0/native-range
methods; sanitizer/lifetime/ABA/fallback/alias tests pass (264native tokens consumed in host bridge).
Seven existing renderer/control/frame/cache/preparation fixtures pass. Actual
ARM64 object shows dmb ish before token stores. This is functional/host component
evidence, not device correctness/FPS/battery acceptance. Details, fixture fix
and build failure preserved in TECHNICAL.

FINAL `ios/build/NFSMW-0.6.1-dev122-register-batches.ipa`,30739379bytes,
SHA256 `d9c9a643604468357af87f80be8290569a6f7f1bb51324f0dc4dfbe8e4c7ca66`,
UUID `BE5997C9-2607-39C4-91AC-3C2AB53739CA`. Signature/ZIP/package-exe pass;
104metallibs+223key seed identical dev121. Both SDK dylibs rebuilt with new
consumer/export. Final iCloud Desktop copy hash-verified, Desktop dev121 moved
to Trash only, stable0.6.0/ios-build copies retained. Two earlier same-name
interim builds superseded before session completion; TECHNICAL records UUIDs.

Build requirement: new `tools/ios/patch_ios_register_batches.py` added to
prepare_sdk.py; apply/revert/status3blocks tested. Prepared local SDK modified
ONLY by these blocks (not Git repo), before/after hashes recorded. Command:
`NFSMW_SDK=/Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk python3
tools/ios/patch_ios_register_batches.py` (then --status must show3of3).
CMake enforces this for USA. Private USA return-PC helper header excluded from
reference-edition translator; original generated emitter code unchanged.
Build isolated build-0.6 target ipa -j12 as before. No canonical SDK tree edits.
Tests `python3 tools/native/test_register_batches.py` and
`python3 tools/native/test_register_batch_bridge.py` (optional --benchmark,
host only). SDK bridge fixture normalizes patch state, roundtrips copies;
never reverts live SDK. No full SDK prepare/reset or generated-code rewrite.

**Next device gate:** install FINAL dev122 preserving settings/cache. Cold
restart LiveContainer with reuse=true, encoding=false, repeat=false,
owner_index=true and NEW `--nfsmw_native_register_batches=true`;1x/60,
same controller/audio (muteOFF requested). One~90–120s pursuit+Mac Time Profiler
and nfsmw.log checks visual/pacing/audio, active batches/consumption, fallback,
bytes/pending and CPU together. Expect dev122/register batchesON and periodic
[register-batches] lines; many small fallbacks NORMAL. No power matrix. If
produced0 or CPU/correctness poor, inspect gates before more recording. False
+ cold restart restores original emitters in SAME build. Archive/hash incoming
evidence by date before analysis. This is partial packet-building bypass,
not CP retirement/full native producer or demonstrated7%CPU/energy saving.
Shared records/CHANGELOG/private BACKLOG updated; HANDOFF preserved untracked.
All own work committed locally; no push/merge/release. Earlier next-source
audit/implementation proposals below superseded by this trial.


**November11 compact direct-producer audit COMPLETE (latest):** Stefan approved
starting source work after same-build index result. Audited old native-d3d
N1b/c/d/N2a evidence and current generated USA/CP/native backend; no old branch
checkout/merge. Full normal-draw bypass unsafe/incomplete: shader/query/resolve/
indirect/writeback/predication/swap remain ordered users; query8258E830 lies
outside prior8259–825Asearch range. Active SDK plugin is NativeCommandProcessor,
not Vulkan; current prepared SDK retains inert old marker support only.

Concrete first slice C0 documented in NATIVE_D3D_PLAN: replace selected ordinary
825A3EC8 calls to scalar825A28A8/grouped825A2A60 with OWNED dirty-register
batches, consumed in order by existing CP via private token. Keep all other
packets and existing Record thread/validation/resource reads. No full-state
N2a copies. Reserve bounded host/ring capacity, publish Ready BEFORE token,
never overwrite live slots, fallback BEFORE skipping original writer. Emitters
use device+4 boundary; draws check+8. No post-publication silent fallback or
whole-frame replay assumption. Small/unknown/boundary cases remain original.

New offline `tools/analysis/audit_d3d_producer.py`, invocation:
`python3 tools/analysis/audit_d3d_producer.py --generated ios/generated/default
--sdk /Users/bep1s/Developer/GitHub/nfsmw-multiplayer-sdk --output
ios/build/direct-producer-audit-20261111/inventory.json`.
Add --all-functions for whole generated source. Tests:
`python3 tools/analysis/test_d3d_producer_audit.py` exit0. Hashes131generated
files; narrowed[82580000,825B0000)1547functions/221literal-store candidates,
full56338functions/265candidates. Conservative literal candidates are NOT
runtime coverage or proved ring destinations; no result permits skipping
unmapped packets. Detailed operation ledger/contract/test gates in planC0;
source hashes/results/limits in TECHNICAL. No proprietary source copied tracked.

**Next SOURCE action:** implement/test C0 dirty-run builder, immutable bounded
batch ownership/ticket lifecycle and before-commit fallback against actual
emitter output/CP side effects, BEFORE wiring live hooks/SDK token handler.
Default-off restart-only route proposed, not implemented yet. Then wire only
proved callsites with reproducible SDK patch/tests/build; no new diagnostic
capture-only lap. Full direct producer/CP retirement remains later, not solved
by C0. No battery claim from7%writer/CP envelope; no more recordings/power now.
Dev121 remains current; owner_index=true/reuse=true/encoding=false/repeat=false
for working trial, no runtime/generated/SDK changes or new IPA this audit.
Shared records/private BACKLOG updated; HANDOFF preserved untracked. Local
commit/no push/merge/release. Prepared nfsmw-multiplayer-sdk is not a Git repo;
exact read-only source hashes recorded instead. Earlier next-audit requests
below fulfilled.


**November11 dev121 SAME-build reference analyzed (latest):** new
dev121_iphone_pursuit_time_profile_2.trace/log archived in November11Debug.
Both traces directly match final UUID51A45FAA-EFEB-3340-BD44-A120E3D0240E;
new log confirms owner_index REFERENCE, reuseON/encodingOFF/repeatOFF/geometryON,
flat capacity0. Trace311files/133811880bytes unchanged after export; Desktop log
797781bytes archived/hash-verified after temporary pasteboard path expired.
22guarded300-frame windows6600CPU-owned/ICB0,22x60.0FPS,31audio windows0gaps,
0watchdogs/foreground GPU errors.194background-permission warnings begin after
scene resign, partly within trace tail; all outside selected CPU interval.

Use8–110s/102s on BOTH dev121 modes (reference trace only117.13s, background
at115.254s). Reference->reusable Capture2614.7->2229.6ms (-14.73%), named
storage1298.0->825.0 (-36.44%), lifecycle union2306.8->2041.4 (-11.51%).
Capture share2.46->1.98%app, storage1.22->0.73%. Supports keeping allocation
change, a smaller local effect than the historic dev120 comparison implied.
Wholeapp106223.7->112772.8ms (+6.17%reusable), combinedgraphics48642.2->
50863.4 (+4.57%). Reusable pursuit has ~10%more nearby draw/owner-lookup work;
other workers also differ. Reference CPU remains much lower than midday
historic dev120: the earlier29%drop is NOT attributable to this index. No
causal net app CPU win or battery-saving percentage established. Do not compare
new102s totals directly with old112s, add overlapping scopes, or normalize
all CPU by drawcount to manufacture a win.

**Next action:** stop this round of profiling; no more user capture/power pair
requested now. Restore `--nfsmw_native_owner_index=true` and cold restart,
keeping reuse=true/encoding=false/repeat=false and existing settings for trial.
Retain dev121 as working build/default-off reuse, not a release acceptance.
Next SOURCE step: bounded audit/design of compact direct D3D producer in
NATIVE_D3D_PLAN sectionC (remove guest writer/PM4 decode round trip, not another
small hash-table tweak). New reference writer/CP union7514.5ms/7.07%app is a
scope envelope, not fully removable saving. Inventory ordered draw/resolve/
clear/query/fence/writeback/swap operations, mutable resource snapshot lifetimes
and safe drained-frame fallback before implementing hooks. Reuse old N1/N2a
negative evidence; do not bypass validation or queue mutable state by pointer.
No new native producer implementation/IPA this analysis session; no energy gate
passed or broader default change. Shared records/private BACKLOG updated,
HANDOFF preserved untracked, local commit only/no push/merge/release. Earlier
reference-capture requests below fulfilled; do not repeat them.


**November11 dev121 device profile ANALYZED (latest):** final UUID
51A45FAA-EFEB-3340-BD44-A120E3D0240E directly verified; owner index reusable,
reuseON/encodingOFF/repeatOFF/geometryON. Trace already in November11Debug;
Desktop/nfsmw.log archived/hash-verified there as
dev121_iphone_pursuit_time_profile_nfsmw.log (836412bytes).297trace files/
153597954bytes unchanged after export. Original pasteboard path expired;
Stefan supplied Desktop copy, now safely archived. Exact hashes/paths TECHNICAL.

26guarded300-frame summaries7800CPU-owned/0GPU-context frames,26x60.0FPS,
0GPU>45ms,0binding/budget fallbacks;35audio windows0gaps,0watchdogs or
foreground GPU errors.54background permission warnings only after trace stop/
scene resign. Peak flat lookup384KiB per CPU frame store (not whole pool),
peak process1639MiB/thermal nominal; no matched memory saving asserted.

112s8–120s vs dev120: Capture4288.2->2397.9ms (-44.08%), named frame-storage
2260.8->871.4 (-61.46%), lifecycle union3859.5->2150.7 (-44.28%). Capture
share of app2.501%->1.969%, storage1.319%->0.716% supports retaining this
bounded optimization. App171464.2->121763.7ms (-28.99%), combinedgraphics
81364.5->54610.3 (-32.88%), but unchanged world/main/audio workers also
~27–31%lower and P-core sample share76.62%->82.32%. Nearby complete log
windows drawcount/frame-0.56%/ownerlookups+0.57%, similar but not exact replay.
Broad drop exceeds scope of owner-index change: do NOT credit all29%to it,
predict29%battery saving, or declare causal net CPU/energy win. Frequency/
scheduling/other workload effects are possible inferences, not measured clocks.

**Next device action:** keep SAME final dev121 and all settings/args; change
ONLY `--nfsmw_native_owner_index=false`, cold restart LiveContainer, preserve
caches. Record one~2-minute Mac Time Profiler pursuit+nfsmw.log with same1x/60,
controller/audio (muteOFF requested), reuse=true, encoding=false, repeat=false,
geometry/residency on. This reference within same build checks whether broad
CPU drop repeats with node index and isolates local Capture/cleanup benefit.
Prefer nearby same-sitting/same route/conditions; current dev121 true capture
is comparison anchor. Expect startup owner index reference and zero flat KiB,
CPU ownership still active/0ICBs. No new IPA/code change or power recording now.
Restore owner_index=true+cold restart after reference. Archive received files
by capture date before analysis. Shared records/private BACKLOG updated;
HANDOFF remains preexisting untracked, preserved. Local commit/no push/release.
Older next-run/build proposals below are historical.


**November 11, dev121 reusable frame-owner index BUILT (latest):** Stefan
approved the next ownership allocation change. `nfsmw_native_owner_index=true`
(restart-only, within default-off reuse) selects a contiguous pointer->ordinal
index retained across frame Clear; false restores node-based reference index.
Deque/shared-owner release, borrowed reference addresses, ordinals, generation
checks, guest validation and entire draw loop retained. All three owner roles
use selected index independently of GPU encoding/geometry-handoff switches.
No GPU command-cache change. Startup logs selector;300-frame geometry summary
adds peak retained flat lookup KiB for ONE CPU frame store (all3roles, not total
process/pool footprint). Up to3pooled stores retain capacity until pool purge.

Host ASan/UBSan collision/growth/differential/poisoned-hint/address-reuse/
release/pool-epoch fixture PASS. Seven existing geometry/control/frame/draw/
command/GPU/attribute regressions PASS. Focused30warmed4096-owner frames:
123330->450heap allocations (99.635%fewer),128KiBflat capacity per tested
owner table. Seven optimized host trials, alternating order: median4.960->
1.999ms. These are component-only host results, not device CPU/FPS/energy.
Record/draw-loop source guards unchanged from dev120. iOS/signature/archive
verification pass; artifact identity/delivery in TECHNICAL below.

Final IPA `ios/build/NFSMW-0.6.1-dev121-owner-index.ipa`,30743730bytes,
SHA256 `ad5655b0e0bea9b8cfe30126f9da0288893479403aced7f8fb6abac974bc59dc`,
UUID `51A45FAA-EFEB-3340-BD44-A120E3D0240E`. Final Desktop copy hash-verified;
only Desktop dev120 moved to Trash, stable0.6.0/ios-build copies preserved.
107shader/SDK/seed assets identical dev120. Earlier same-name pre-indent build
superseded before completion (TECHNICAL records both identities).

**Next action:** install Desktop dev121 preserving caches/settings. Keep
`--nfsmw_native_command_reuse=true --nfsmw_native_command_encoding=false
--nfsmw_native_repeat_counter=false`; add
`--nfsmw_native_owner_index=true` (already default). Cold restart LiveContainer.
Keep1x/60/geometry-handoff/residency defaults, matching controller/mute settings
(muteOFF requested). One roughly2-minute Mac Time Profiler pursuit+nfsmw.log
checks CPU ownership capture/cleanup, retained capacity, FPS/audio/correctness.
No Power Profiler yet. To compare old allocation path in SAME IPA set
owner_index=false and cold restart; no need reinstall dev120. Analyze first
optimized run before requesting further captures. Capture scope2.50%app from
dev120 is not wholly removable; net CPU/battery improvement still unproven.
Shared records/private ignored BACKLOG updated; HANDOFF remains preexisting
untracked and preserved. Local commit only, no push/merge/release. Historical
next-source proposals below superseded by this built trial.



**November 11, dev120 owner-only Mac profile ANALYZED (latest):** supplied trace
already in Debug/11 November2026; Desktop12.19.57PM log copied/hash-verified
there as dev120_iphone_pursuit_time_profile_nfsmw.log before analysis.292trace
files/178759912bytes unchanged after export; log922461bytes. Exact manifests,
hashes, commands and selection in TECHNICAL. Trace directly matches dev120
UUID E7740732-C19B-3EE6-9994-3680BB4F9107, iPhone17ProMax/iOS27.3,
132.871634s high-rate100us,12:15:36.211–12:17:49.082+02:00.

Control works on device: preparation223normal/0ICBkeys,420ms before game;
reuse ON/encoding OFF/repeat OFF/geometry ON/incremental residency flag.
26fully-driving300-frame log windows7800CPU-owned/0GPU-context frames,
0ICBdraws/runs,58.19%owner hints/61.05%GPU-binding reuse,0fallbacks.
FPS25x60.0/1x59.8,35audio windows0gaps,0watchdogs/foreground GPU errors.
87background-permission warnings begin after scene resign and trace stop.
Peak1809MiB/thermal nominal; different pursuit, no matched memory conclusion.
Mute/controller state not independently logged; no subjective visual acceptance
supplied. Other logged graphics controls1x/60/MetalFXoff/FXAAoff/MSAAforced0.

Same8–120s/112s fully-driving selection vs dev119: app sampleweight
164920.2->171464.2ms (+3.97%); GPU Commands29614.9->34196.5 (+15.47%);
render queue50160.6->47168.0 (-5.97%); combined79775.5->81364.5 (+1.99%).
Named command paths8133.3->69.2ms (empty Batch/housekeeping remains),
AGXself3799.4->5143.5; Record22965.0->26575.3 (+15.72%). Main/world/audio
work also higher; nearby complete summaries show more draw work. Different
pursuits, not a controlled causal A/B: do NOT conclude ownership/direct draws
win, ICBs intrinsically fail, or battery worsened/improved by these percentages.
Combinedgraphics also+2.83%vs historical dev110. No demonstrated net saving.

**Next source action, no new recording requested:** inspect/replace per-frame
node allocations in FrameOwners identity index with a reusable flat index,
keeping owner release at Clear, stable borrowed refs/ordinals, unique generation
checks, all guest validation and pool purge semantics. Current named Capture
4288.2ms (2.50%app) and storage/cleanup churn identify a bounded target;
Capture includes useful work, not wholly removable. Host differential/lifetime,
collision/growth/address-reuse and allocation-count comparison against current
unordered_map first; only package if supported, keeping reference comparison.
Use dev120 owner-only as development control, no default changes/new IPA this
analysis session. No further power matrix. Private ignored BACKLOG updated;
preexisting untracked HANDOFF preserved. Shared records committed locally,
no push/merge/release. Older next-run requests below superseded by this result.



**November 11, dev120 encoding control BUILT / next device check:** Stefan
approved the independent command-encoding diagnostic. Added restart-only
`nfsmw_native_command_encoding=true` within the default-off command-reuse
trial. False skips ICB pipeline preparation/collection/report and context
acquisition, using the existing direct Metal draw loop. CPU frame ownership
and geometry handoff remain independently selected; no validation/draw-loop
changes. Default true preserves dev119 behavior. This is attribution tooling,
not a demonstrated CPU/battery improvement.

Delivered `ios/build/NFSMW-0.6.1-dev120-encoding-control.ipa` and hash-verified
copy on iCloud Desktop. SHA256
`ceac412bac47de1f8e820416ff6c789ba8cc3057adda0a8804a39f7b1f2a02f2`,
UUID `E7740732-C19B-3EE6-9994-3680BB4F9107`. Host control tests cover all eight
reuse/encoding/geometry combinations and exclusions; geometry, command-cache,
preparation fixtures pass. Build/signature/ZIP verification pass; details and
limits below in TECHNICAL.104 metallibs, two SDK dylibs and223-key seed match
dev119. Older Desktop dev119 moved to Trash; stable IPA/cache copies retained.

**Next action:** install dev120 preserving settings, cold restart LiveContainer
with Extra Args `--nfsmw_native_command_reuse=true
--nfsmw_native_command_encoding=false --nfsmw_native_repeat_counter=false`.
Leave geometry handoff/residency on (defaults), same1x/60/controller/audio mute
OFF as dev119. Record one roughly2-minute Mac Time Profiler pursuit and game
log. Expect CPU-owned frames/geometry reuse active, cached command encoding
off, zero GPU command contexts/ICB draws; normal pipelines still prepared.
Archive received evidence immediately by capture date, verify correctness and
compare CPU rates/scopes before requesting power. Set encoding=true and cold
restart to restore full trial in this same IPA if needed. No device run or
CPU/energy savings yet. Historical proposals below are superseded by this
built diagnostic. Preexisting untracked HANDOFF_CHATGPT.md is preserved;
private ignored BACKLOG updated locally. No push/merge/release.


**November 11, dev119 Mac Time Profiler analyzed / archive audit completed:**
Stefan's original trace remains in Debug/10 November 2026 as supplied. A
payload-verified copy and matching midnight log now live in Debug/11 November
2026/dev119_iphone_pursuit_time_profile.trace and
dev119_iphone_pursuit_time_profile_nfsmw.log. Trace296files/163805853bytes;
log986972bytes. Audit rehashed all338entries from the prior November10 manifest
(including17power archives/17extractions/11logs), plus7later dev115–118 inputs:
NONE missing/changed. Earlier captures stay in November10 by date. Exact
hashes/trace manifest digest/paths in TECHNICAL; no original moved/deleted.

Time Profiler128.779572s,00:25:09.815–00:27:18.595+02:00,iPhone17ProMax,
iOS27.3(24C5037i),100us high sampling,LiveContainer12052, actual dev119 UUID
689F21D8-EEF3-39E8-A727-D0D8398D287D in trace. No inferred game image mapping
needed. Full guarded driving logs6900frames show owner hints59.47%, GPU
binding reuse62.34%,0binding/budget fallbacks;96.73%fewer command-resource API
calls vs reference for same run counts. FPS20x60.0/2x59.9/1x59.8;33audio
windows0gaps,0watchdogs/foreground GPU errors.65background permission warnings
occur only after scene resign19.622, outside trace/CPU selection. Memory peak
1638MiB/thermal nominal; not a matched memory saving or subjective acceptance.

Primary8–120s (112s fully driving) vs historical dev110 same-duration high-rate
selection: app sampleweight170932.0->164920.2ms (-3.52%), but GPU Commands+
native render queue79126.3->79775.5ms (+0.82%, effectively flat). World/main/
audio workers also differ, so don't attribute lower whole-app number to renderer.
Record25466.2->22965.0ms,AGX self5708.2->3799.4ms,Draw destruction4929.3->
1007.4ms. More complete named draw/frame/storage lifecycle UNION4930.6->3310.3ms:
some cleanup moved into frame storage, not all eliminated. New command paths
8133.3ms(4.93%app), owner Capture3670.6ms(2.23%); overlapping/inlined scopes,
not entirely incremental/removable. No causal net graphics CPU/energy gain
demonstrated; no same-sitting power A/B justified yet. Compare CPU by rates,
not these totals against the shorter phone traces.

**Next source decision:** separate frame ownership/geometry handoff from GPU
ICB command encoding (currently coupled by command_reuse). Proposed bounded
diagnostic flag gates ONLY ICB pipeline preparation/acquisition/encoding,
leaves frame pool/geometry handles active, default preserving dev119 behavior.
This allows owner-only direct Metal vs full trial in the same build/settings.
It is a proposal, NOT implemented/new IPA or proof ICBs inherently cannot help.
Use existing direct fallback and actual control/lifetime tests. Don't launch
another optimization or power matrix on the whole-app -3.52% number. Current
working build stays dev119/default-off reuse; no new recording requested now.
Offline analysis helper adds named lifecycle/owner/GPU selection scopes and
overlap-safe union; tests/totals regression pass. Local docs/tools commit,
no push/merge/release; HANDOFF preserved, private BACKLOG updated.

**November 10, dev119 BUILT — first frame geometry-handoff slice:**
New default-ON restart-only `nfsmw_native_geometry_handoff` within default-OFF
command reuse. After existing validation, cached vertex/index arrays are
captured directly into frame owner tables using generation+identity hints.
FrameRef carries the owner ordinal in its existing raw-pointer word (still
32bytes); repeated cached draws avoid shared-owner transfers and owner-map
lookups. Fresh/rectangle values captured explicitly, later geometry Pin loop
removed in new arm. Constant/history and ALL existing validation unchanged.
Reference flag false restores dev118 ownership/selection behavior.

Renderer uses two per-frame strong GPU-binding arrays indexed by vertex/index
owner ordinals. First persistent selection goes through original GpuBufferFor
(same allocation/upload/stamps); repeats use resolved binding; nil failures
retry. Fresh data still uses original upload path. SweepGpu remains before
binding creation, submission ID fixed within frame. No cross-frame binding
reuse or producer/PM4 change. This is the first structural slice, not the whole
Record10.4%removed. Per-decoded-cache-entry hint adds24bytes; per-frame GPU
binding slot16bytes/owner; device memory/performance remains to check.

Host ASan/UBSan pass: new test_geometry_handoff.py (actual handles, 10000borrowed
captures/1map lookup/no extra shared owners; replacement, deque growth, stale
hint, pool/placement-new generation, 30000reference differential cases; complete
Record validation-body allowlist guard vs317ea68, original GpuBufferFor/Sweep
unchanged). Extended GPU-buffer fixture:10000repeated selections ->1original
lookup/upload, replacement, roles, nil retry, reference fallback, next-frame
stamps and strong lifetime; all4selector/stats configurations pass. Frame
storage, actual Draw/Frame/constant snapshots, command cache and attribute
lookup tests pass. Fixture failures/corrections preserved in TECHNICAL.

IPA ios/build/NFSMW-0.6.1-dev119-geometry-handoff.ipa,30731764bytes,
SHA256 `aa976ec4347d5c1af56bb32586fe51440c0a38d0104f27f548a2c233fd586292`,
UUID `689F21D8-EEF3-39E8-A727-D0D8398D287D`, bundle0.6.0(11).
Isolated NFSMW then ipa -j12 both exit0,10existing compile/link warnings;
ZIP/signature/cache-app equality pass.104shader libraries,BOTH SDK dylibs and
223-key catalog byte-identical dev118. On iCloud Desktop; older Desktop
dev118 in Trash, stable/all ios/build copies preserved. No release/push/merge.

**Next (November11 update):** Stefan will wait until back at his Mac and can
provide Time Profiler and Power Profiler. Do not request another phone capture
in the meantime. Start with dev119 Time Profiler+nfsmw.log and subjective
correctness, same existing settings/args below; then assess whether a single
same-sitting Power Profiler A/B is warranted. Handoff=false vs true in the
SAME dev119 build isolates this change, with reuse/residency held on; don't
treat one enabled power trace as savings evidence. Prior phone option below
remains historical fallback, superseded by his current preference.
Install over existing data/settings/args
`--nfsmw_native_command_reuse=true --nfsmw_native_repeat_counter=false`.
New handoff/residency flags default on in trial; no extra enabling args needed.
One short phone System Activity (Detailed) capture during already-loaded pursuit
(~30–40s is enough to obtain the observed~32s traces), ordinary LiveContainer,
same1x/60graphics/controller/mute OFF, return trace+nfsmw.log and picture/audio/
pacing observations. Confirm dev119/handoff ON and active-frame/owner-hint/GPU
reuse counters; inspect Record/refcount/Pin/GPU selection work and memory.
If incorrect restart with --nfsmw_native_geometry_handoff=false as reference.
No new power A/B yet, no host-count-to-battery claim. Device CPU/energy/visual
acceptance pending. Do not skip validation or revive failed dev112 draw-order
memo; direct D3D remains later stage. HANDOFF preserved; private BACKLOG updated.

**November 10, dev118 device/profile result — local improvement confirmed, no net battery claim:**
Newest trace actually Downloads/trace_2026-11-10-232127.atrc.tgz, archived with
matching log as Debug/10 November 2026/dev118_system_activity_detailed_232127*.
32.224895s,23:21:27.967–23:22:00.192+02:00,V54AP/iOS27.3(24C5037i).
dev118/reuse ON/repeat OFF/residency incremental,1x/60.309pipelines all archive
hits,374ms preparation,no later save/GPU error/watchdog. One50-gap audio window
straddles loading/driving transition; steady selected CPU windows exclude it.
No explicit subjective picture/mute acceptance supplied. Full log17guarded
300-frame windows FPS13x60.0,59.4/59.2/59.8/59.9,0GPU>45ms reports.

Actual command resource calls61564 vs2565772 the reference would issue for the
SAME run/single counts across5100frames:97.6006%fewer API calls (not energy).
Primary CPU10–30s,25883samples/ms weight,387stackless:Batch named384ms/1.484%
vs dev116574ms/2.286%; ~33.1%less targeted sampled work. Driving-relative8–24s
alignment:305ms vs469ms,~35.0%less; total app sampleweight20282vs20325ms,
essentially unchanged. Primary total25883vs25110ms is3.08%higher; do not omit
that differing-window result. Record remains~10.4%,writer/CP~7.1%. Named batch-sort
samples156ms->0 in primary windows. Different live pursuits/profiler overhead
preclude causal net CPU or energy claims. Keep dev118 as trial working build;
command reuse stays default OFF. No new app change/IPA this analysis session.

**Next source work:** the larger Record draw-data handoff. Exact dev118 PC/line
follow-up finds attribute lookup/validation, transient attribute owners and a
second frame-pin traversal remain; don't treat its entire10.4% as removable.
Design a frame-owned geometry bundle/handle path that avoids repeated ownership/
lookup work while keeping ALL existing guest-byte/write-watch/fingerprint,
index/remap/endian, shader-layout and lifetime validation. Include the later
GpuBufferFor handoff in the design so work is removed rather than moved.
Read failed dev112 draw-order memo evidence first; this is not permission to
revive it or weaken validation. Size a concrete combined representation change
before coding, preserve direct D3D ordered producer plan (~7%bridge envelope)
as the larger next stage. No further capture/power pair requested now.

Reproducible exports now import large atrc ONCE via xcrun xctrace import into
ignored <audit>/imported.trace, then export toc/time-profile from that document.
Avoid repeated multi-minute implicit import for each table. Inputs, image-base
inference/callsite validation, exact-UUID system symbol matching and commands
in TECHNICAL. All derived files in ios/build/dev118-system-activity-20261110.
Local docs commit/no push; HANDOFF preserved, private BACKLOG updated.

**November 10, dev118 BUILT — incremental command resource residency:**
Continued the approved stage-1 trial after phone CPU analysis. Batch no longer
gathers/sorts all repeated command resources on every flush: a per-encoder flat
pointer set declares only newly encountered ICB/buffers, with per-binding last
pointer checks skipping common heaps/push storage lookups. A strong last-encoder
reference prevents allocator address reuse from inheriting declarations. Buffer
pins/GPU completion leases and draw/state/pass boundaries unchanged. Flat set
uses geometric contiguous storage, no per-resource heap-node allocation.

New default-ON restart-only `nfsmw_native_command_residency` acts ONLY within
default-OFF `nfsmw_native_command_reuse`. Set residency=false to restore old
gather/sort/declaration path without disabling command/frame reuse. Existing
trial args suffice; no new argument needed. New300-frame command-residency
summary logs actual useResources calls/resource entries for later verification,
explicitly not CPU/energy savings. Master mute/preparation/catalog retained.

Host actual-code ASan/UBSan tests pass: reference/incremental resource sets
match at every draw and bind/execute operations match across changing/nil/
duplicate bindings, nonadjacent runs, state flushes, singles, encoder A/B/A,
new buffers and encoder lifetime.100000flat-set operations match std set.
Synthetic100identical two-command runs:100calls/400entries reference vs1call/
4entries incremental, identical draws/resources; not a device performance result.
Existing ownership/operand/pin/budget/completion/purge and frame-storage tests
pass. Normal build-0.6 ipa -j12 exit0,10existing warnings; ZIP/signature pass.

IPA ios/build/NFSMW-0.6.1-dev118-command-residency.ipa,30736682bytes,
SHA256 `ff848e19285167f536169496699d458dc4916e82c4123aa10ea4bf9471f94201`,
UUID `1B6B7491-2554-389E-9A51-B67FEB15BE84`, bundle0.6.0(11).
104shader libraries, BOTH SDK dylibs and223-key catalog byte-identical dev117.
On iCloud Desktop; older Desktop dev117 in Trash, stable/all ios/build packages
preserved. Local branch/no push/merge/release; HANDOFF untouched.

**Next:** install over existing data, retain
`--nfsmw_native_command_reuse=true --nfsmw_native_repeat_counter=false`.
One~40s System Activity (Detailed) capture during an already-loaded pursuit,
ordinary LiveContainer monitored,1x/60/same graphics/controller/mute OFF.
This one run covers visual/pacing/audio check and targeted CPU follow-up; send
trace (AirDrop to Mac/Downloads works) plus nfsmw.log. Confirm dev118/incremental
startup and residency counters, reduced sort/declaration CPU in profile; do not
infer net CPU/energy benefit from different pursuit workloads or host fixture.
No battery A/B yet. If incorrect use --nfsmw_native_command_residency=false
after restart as reference, preserving all other trial controls. Device
correctness/CPU/memory/energy acceptance remains pending. Do not widen into
Store/pin/Record/producer rewrites before examining this bounded result.

**November 10, phone CPU trace analyzed — dev116, no further recording needed now:**
Stefan AirDropped trace_2026-11-10-224624.atrc.tgz to Downloads. Archive/log
preserved in Debug/10 November 2026 as dev116_system_activity_detailed_224624*
(TECHNICAL exact hashes/paths). Actual capture32.015214s,
22:46:25.259–22:46:57.274+02:00, all processes, iOS27.3(24C5037i), V54AP.
System Activity (Detailed) DOES contain usable1ms CPU samples. Game log is
dev116 (not dev117): reuse ON/repeat OFF,1x/60,309archive hits,419ms preparation,
no new pipeline save. dev117 mute remains untested by this evidence.

Primary trace10–30s window lies fully in driving:25110running LiveContainer
samples/25110ms statistical weight,338ms stackless(1.346%). Actual image
metadata omits manually loaded game/SDKs; offline symbol naming uses exact
dev116 IPA symbols with load bases inferred/corroborated at multiple callsites,
not device-provided image metadata. SDK UUIDs match log. System names restored
only at exact UUID/instruction-offset matches from existing dev110 export.
No substituted current binary/DWARF or nearest-PC system naming. Details and
mapping caveat in TECHNICAL; result is diagnostic, not a matched CPU/power A/B.

Sampled graphics footprints:Record10.48%appCPU, writer/packet union7.07%,
draw destruction0.44%, identifiable command-cache paths4.52% (includes
Batch::Flush2.29%; these overlap and do not include all inlined costs).
8–30s/12–28s sensitivity keeps Record10.40–10.43%, command paths4.50–4.52%,
batch2.23–2.27%. Source confirms each Batch::Flush gathers repeated buffer
pointers then sorts/uniques them for every run. This is concrete prototype
overhead to address before broadening the producer rewrite. Current capture
does NOT prove overall CPU/energy benefit or regression versus dev110.

**Next implementation:** make command-batch resource residency bookkeeping
incremental per Metal encoder, preserving every required buffer/ICB declaration,
Read/stage flags, draw/pass order, strong pins and GPU completion ownership.
Avoid full gather/sort of duplicate common bindings for every run; keep a
reference switch/actual production differential tests for resource sets and
encoder changes. Size remaining Store/pin work separately. Do not claim the
whole4.52% removable. Record/vertex work and direct D3D producer remain larger
later stages; no repeated tiny power matrix. No new capture requested until a
concrete new build exists. No app change/IPA this analysis session.

Offline tools: summarize_battery_exports.py profile now supports exact
--process LiveContainer (essential for all-process traces); new
symbolize_profile_images.py uses explicit UUID-checked image manifest and
optional exact-PC --reference. Tests pass, old dev1101744500sample totals and
graphics footprints unchanged. All exports/derived files local ignored
ios/build/dev116-system-activity-20261110. Local commit/no push; HANDOFF preserved.

**November 10, dev116 result / dev117 BUILT — master mute and first-install catalog:**
Supplied dev116 log/catalog archived in Debug/10 November 2026 as
dev116_iphone_command_reuse_on_nfsmw.log and dev116_native_pipeline_keys.bin.
All223normal+86ICB pipelines ready,0unavailable; preparation8899ms, including
archive save completed before SDL/runtime. No later pipeline-made/save reports,
0watchdog stalls/0GPU errors,35audio windows0gaps. This supports the upfront
preparation fix, not subjective freeze-free acceptance or energy savings.
Twenty-three fully driving guarded300-frame windows:66.64%ICB draws,
15.39draws/run,29.94%exact-key hits,0budget fallback,6900CPU/GPU-owned frames.
FPS summaries22x60.0,1x59.9,0GPU frames over45ms in those summaries.
Log ends mid-line; no crash or graceful exit inferred. Exact evidence TECHNICAL.

dev117 adds default-OFF hot `ios_audio_mute`, settings key audio_mute, Audio
row Mute all game audio in BOTH launcher and in-game gear/controller sheet.
Atomic final-output silence leaves the ring drain and audio semaphore timing
running; original game volumes untouched. For personal music also enable Keep
other music playing BEFORE launch (existing restart-only session option).
Mute does not disable guest mixing/XMA, and is not a battery optimization.

Catalog supplied:223unique48-byte records,10704bytes. dev117 bundles it locally
via new CMake FILEPATH `NFSMW_NATIVE_PIPELINE_KEYS` (empty default), so fresh
installs can prepare the same known normal/ICB combinations before gameplay.
New combinations/settings still require discovery. Catalog stays ignored/local.
Build procedure: configure existing isolated build with
`cmake -S ios -B /Users/bep1s/Library/Caches/nfsmw-ios/build-0.6 -DNFSMW_NATIVE_PIPELINE_KEYS="/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/10 November 2026/dev116_native_pipeline_keys.bin"`,
then usual `cmake --build /Users/bep1s/Library/Caches/nfsmw-ios/build-0.6 --target ipa -j 12`.
Clear option to omit seed; packaging removes stale bundled catalog first.
No shader rebuild/SDK source patch. Host `python3 tools/native/test_audio_mute.py`
(ASan/UBSan actual render callback drain/wrap/unmute/underrun/permit behavior)
and `python3 tools/native/test_pipeline_preparation.py` pass; build/signature/
ZIP/catalog inclusion pass. Device mute/menu/music check remains pending.

IPA ios/build/NFSMW-0.6.1-dev117-mute-pipeline-catalog.ipa,30734521bytes,
SHA256 `2a13a0b728ce04af1bd9537dcfff2d0ff825f890833fb1a63099643f283804cd`,
UUID `00CD3ABE-E13C-3307-8B18-01BB6C57D644`, bundle0.6.0(11).
On iCloud Desktop; older Desktop dev116 in Trash, stable/all ios/build copies
preserved.104metallibs and GPU SDK dylib match dev116; runtime only build-label
string section changed (TECHNICAL). Local branch/no push/merge/release.

**Next battery action (updated: Stefan has no laptop):** try one90–120s
iPhone1x/60 pursuit via phone Performance Trace, System Activity (Detailed),
ordinary LiveContainer monitored. Start/stop through Control Center after
graphics preparation and loading; share generated trace plus nfsmw.log.
This mode is a candidate for CPU investigation, NOT yet a verified replacement
for Time Profiler: inspect actual exported tables/stacks first. No Power
Profiler pair or waiting for Mac access required. Retain
`--nfsmw_native_command_reuse=true --nfsmw_native_repeat_counter=false`,
same graphics/controller settings, mute OFF for this CPU investigation to keep
audio comparable. No Power Profiler pair yet.
Locate actual costs in Record, frame ownership, command rebuild/encode, driver,
CP and destruction; ~70% command-key rebuilds mean batching activity alone
does not establish less CPU. Rendering wall time contains pacing/waits and must
not be substituted for CPU. Historical dev110 trace is contextual, not a matched
causal A/B. Use profile findings to select a concrete next renderer change;
do not advance to PM4 removal or claim battery gains on counters alone.
Preexisting untracked HANDOFF_CHATGPT.md preserved; BACKLOG private/ignored.

**November 10, dev116 BUILT — pre-game graphics preparation and archive-lock fix:**
Stefan reports dev115 looked normal except heavy freezes. Archived supplied
log as `Debug/10 November 2026/dev115_iphone_command_reuse_on_nfsmw.log`.
Reuse was genuinely active: eight fully driving300-frame windows (2s guards)
show58.1% of submitted draws in ICB runs,15.45draws/run,26.7% exact-key hits,
0budget fallback; all eight FPS summaries60.0. No GPU error;33audio windows
without gaps. Whole session has2watchdog stalls,6archive save completions,
process memory up to1900MiB. No CPU/power comparison; not a battery result.

Source/log evidence points to the existing archive save mutex: background
serialization holds it, while render-side Report/old warm-completion also
took it. dev116 Report uses try_lock and skips busy reporting; warm-completion
uses an atomic; Make leases prevent releasing/reopening an archive beneath
an in-progress add. Existing atomic-save/unfinished-save recovery retained.

New default-ON restart-only `nfsmw_native_prepare_graphics` presents a responsive
"Preparing graphics" screen after Play and effective arguments, before SDL/
guest threads. Normal known keys and eligible ICB variants (seeded from normal
keys even when the ICB list is empty) compile and cache-save completes there.
Archive memory can then be released before gameplay. Native reuse stays
default OFF; retain the existing trial args to exercise it. A completely fresh
install still needs a bundled known-key catalog for broad prewarm coverage:
optional NativeShaders/pipeline_keys.bin is supported but NOT bundled in this
IPA. New/unseen state combinations retain first-use discovery/fallback.
The app exports logs/native_pipeline_keys.bin for future local catalog seeding;
do not claim every possible pipeline is prepared on an empty installation.

IPA `ios/build/NFSMW-0.6.1-dev116-prelaunch-pipelines.ipa`,30,729,740bytes,
SHA256 `9afc589e420d7e732dd1f4f5009c8db32d767a0246ef8e5d3bf11c55df408fb3`,
UUID `A599B106-3668-3377-992D-59AD5B0A8BCF`. ZIP/signature/cache-app equality
pass;104shader libraries and both SDK dylibs byte-identical to dev115.
Bundle0.6.0(11), experiment filename0.6.1 as before. Build-0.6 ipa -j12 exit0,
7existing warning entries. On iCloud Desktop; older Desktop dev115 moved to
Trash, stable0.6.0 and all ios/build packages preserved.

**Next:** install over dev115 preserving data/settings/Extra Args
(`--nfsmw_native_command_reuse=true --nfsmw_native_repeat_counter=false`).
Check preparation screen then one normal pursuit and send nfsmw.log plus
logs/native_pipeline_keys.bin if available (portable metadata for first-install
seeding; no new measurement run needed to generate it). Expected preparation
log precedes SDL/runtime start, normal/ICB ready counts, then dev116 reuse on.
No new power recording requested. Device verification of the freeze fix,
startup UI, CPU benefit and battery benefit remains pending.

Host tests: `python3 tools/native/test_pipeline_preparation.py` (actual archive/
cache methods with stand-ins, ASan/UBSan: nonblocking Report under held mutex,
active-Make retention, save drain, cold-ICB seeding, capability variants,
dedup/malformed metadata, no first-Get recompile, pre-runtime ordering) and
existing pipeline-lookup differential test pass. Technical details/limits in
TECHNICAL. No shader rebuild/SDK patch needed; normal isolated IPA command.
Local work on codex/native-frame-command-reuse, no push/merge/release.
HANDOFF_CHATGPT.md preserved; private BACKLOG updated and intentionally ignored.

**November 10, dev115 BUILT — first native frame/command-reuse prototype:**
Branch `codex/native-frame-command-reuse` from afbb1ba. Stefan approved
implementation. Opt-in restart-only `nfsmw_native_command_reuse=false`:
frame-owned constant slabs and once-per-frame geometry owners; three
completion-owned GPU contexts with exact cached indexed commands and stable
buffer8 address records/heaps. Adjacent equal-state runs preserve the existing
pass/resolve/sky order. Single runs, unsupported/dynamic/query/internal/motion
draws and not-ready/failed ICB pipeline variants use direct drawing. Existing
CP producer/pacing/shaders/graphics settings stay in use. Repeated-draw
diagnostic now defaults OFF. This is a prototype, not a measured improvement.

IPA `ios/build/NFSMW-0.6.1-dev115-native-commands.ipa`, SHA256
`efd7321f35bf1f427f090e2f5f5d344c8224ea980295b187389945be316cbda9`,
UUID `5E0212D7-CC23-3A5B-9886-819726A5E3FF`. Bundle version remains0.6.0(11)
as in earlier dev builds; filename denotes the0.6.1 experiment. ZIP CRC,
strict deep codesign and packaged/cache executable equality pass.104/104
shaders byte-identical to dev114. One runtime dylib differs only in its build
label section (all code sections identical); see TECHNICAL. Final incremental
ipa build exit0,10 existing compiler/link warnings; no SDK source patch.

Copied/hash-verified to iCloud Desktop per standing rule; older dev114 Desktop
copy moved to Trash, stable0.6.0 preserved. All old IPAs remain in ios/build.

**Next: one initial device correctness run, not a power test.** Install dev115,
fully restart LiveContainer with existing settings/Extra Args retained and add
`--nfsmw_native_command_reuse=true --nfsmw_native_repeat_counter=false`
(avoid duplicate entries). Keep MetalFX
temporal off for the ICB path, as in the existing pursuit baseline; do not
change other graphics settings. Do a normal pursuit and send nfsmw.log,
noting picture, pacing and sound. Expected startup marker: dev115 reuse on;
every300frames `[native] command reuse:` gives CPU-owner/context coverage,
ICB/direct counts, run/single counts, hits/rebuilds and budget/pin/slab limits.
Some initial direct fallback during ICB PSO compilation is expected; no draw
is omitted merely because the trial variant is pending. No new baseline or
Power Profiler capture requested yet. After correctness and real mechanism
coverage, inspect CPU/pacing before choosing one power pair.

Validation commands added:
`python3 tools/native/test_native_frame_commands.py` and
`python3 tools/native/test_native_command_cache.py` (ASan/UBSan; actual helpers,
fake Metal objects, not GPU/pixel verification). Existing draw-arena fixture
now also checks the production constant snapshot lambda (5,000 draws, changing
ranges and slab overflow); pipeline lookup, culling and GPU-buffer regressions
pass after fixture maintenance. Standard build remains build-0.6 target ipa
-j12 with the isolated multiplayer SDK. Detailed failures/limits/paths in
TECHNICAL below; implementation status in NATIVE_D3D_PLAN.
No device run, measured CPU/battery result, push/merge/release. HANDOFF_CHATGPT.md
untouched/untracked. Private BACKLOG updated but intentionally ignored/uncommitted.

**November 10, native graphics feasibility/design pass complete:** Stefan
approved design and broadened the goal to a longer, more native iOS port while
preserving current performance/visuals. Restored and rewrote the existing
AGENTS-indexed `docs/NATIVE_D3D_PLAN.md` on the current branch; inspected old
native-d3d N0–N2a via git show, without merging its pre-cleanup history or
changing production code. Existing N2a validated device-state input for
98.2–99.0% of tested normal draws but intentionally retained the full PM4
stream and added copies; it did not test eliminating that work.

Refined today's existing dev110 profile: D3D writer + CP packet overhead union
6.675% app CPU; Record inclusive 14.84%; Draw destructor inclusive 2.871%;
AGX self 3.334%. These are overlapping scopes, not additive savings. A pure
packet bypass cannot promise the proposed 10% combined-project CPU ambition.
Extended the read-only parser with per-thread self tables and explicit
call-path groups. Results cached in
`ios/build/battery-audit-20261110/profile-design-summary.jsonl` and fully
recorded in TECHNICAL below. No new capture or device test requested.

**Concrete next implementation proposal:** one owned NativeFrame format,
completion-owned contexts and bounded cached Metal commands, initially fed by
the current CP. Stable buffer-8 address records allow fresh constants without
rebuilding every command; exact keys and adjacent equal-state runs preserve
order. Ordinary unsupported/dynamic/query/motion/internal draws stay direct.
Then replace the producer with direct D3D operations, handling resolve/query/
fence/writeback/swap ordering together. The plan defines ownership, fallback,
pipeline capability/cache changes, CPU/pacing/energy gates and later native
asset/audio/game-routine opportunities. Source-specific design is ready for
review; implementation/build remains next, not yet performed or approved.
No new runtime flags/default changes, IPA, SDK patch, push or release.
HANDOFF_CHATGPT.md remains untouched/untracked; private BACKLOG updated and
intentionally ignored/uncommitted. Older checkpoint entries below retain history.

**November 10, independent audit of the entire November 10 debug folder:**
Re-exported all 17 Power Profiler archives and the dev110 Time Profiler;
reviewed all 11 logs (including dev112's cumulative all.log), inventoried and
hashed 338 non-.DS_Store files including trace internals. No game/SDK changes,
IPA, device run, push or release. Reusable read-only parser:
`tools/analysis/summarize_battery_exports.py`; derived XML/JSON and manifest in
ignored `ios/build/battery-audit-20261110/`. Full results, reproducible export
commands and limits are in TECHNICAL's independent audit entry below.

The 60-fps controller configuration shows a modest repeatable observed saving
(28.92 -> 27.56 %/h, 4.67%, previous 10s trim), but the controller-only causal
effect is not isolated: dev111 switches differ in effective behavior and
instruction rates differ. Window selection changes the apparent dev111 result;
do not call the four short runs proof of zero effect or a universal 0.5 %/h
resolution. Retain the conservative decision to park dev111/dev112, without
another power test of those same implementations.

**Correction to dev114 interpretation:** texture identity compares CPU
`Texture` wrappers, not Metal texture allocations or contents. `TextureOf`
creates a new wrapper each frame for resolves; ~47% changed pointers do not
establish a texture-cache defect. Zero identical full draws does not reject
ICBs with dynamic constant buffers. Actual counter matching also omits pass
ordering, exact resource bindings and buffer offsets; it cannot certify safe
replay. Do not start a texture-churn fix or dismiss structural reuse from this
counter alone. Existing diagnostic default remains ON; use
`--nfsmw_native_repeat_counter=false` for any power run and turn it off in
source before the next normal build/release.

**Next meaningful action:** keep dev113's existing 40-fps check separate;
for materially better 60, propose a bounded renderer submission/storage
prototype that removes work across Record + Metal encoding rather than
moving frees or repeating tiny cache/QoS permutations. Existing iPhone profile
puts ~46.3% of app sampled CPU in command processing + native render workers;
this is a cost envelope, not recoverable savings. First show a material CPU
reduction with equivalent rendering, then spend one same-sitting power pair.
Native D3D remains a larger, higher-risk alternative. No implementation is
approved by this investigation request. Earlier checkpoint paragraphs below
are chronological history, superseded where this audit corrects them.
Pre-existing untracked HANDOFF_CHATGPT.md remains untouched. BACKLOG.md is
updated locally but remains ignored/uncommitted under the privacy rule.

**November 9, issue #18 reproduction (D-021):** new converted save, log and
IPS archived in `Debug/9 November 2026/issue18_reproduction/`. Exact released
0.6.0 UUID confirmed. Matching-binary disassembly identifies Lua's numeric-for
limit error, then exit cleanup hits DbgBreakPoint (SIGTRAP). Save checksums
all pass; cash 999,955,699 is in signed range. No demonstrated cash overflow,
autosave failure or low-memory kill. The original unconverted PC file is absent,
so source-state versus converter causality remains unresolved. Stefan cannot
obtain this original PC save and deferred further investigation until he chooses
to resume (November 9); D-021 is parked. Next on resumption: test other PC saves,
retaining originals and converted copies, and compare the same race on PC/iOS
where feasible. A Lua-error/context diagnostic remains a possible later step.
No scheduled test or new build requested.
No source/build/device run; do not disturb dev109 battery work below. Local
record update only, no push/comment/release. Private BACKLOG updated and
intentionally ignored/uncommitted; pre-existing HANDOFF_CHATGPT.md untouched.
See TECHNICAL's issue #18 reproduction entry for exact evidence and limits.

**November 10, dev114 result (iPad Pro M4, 60):** 0 % of draws repeat
exactly; VS constants (c0-c3 first) change in ~97 % of draws, textures in
~47 %. Only-constants draws ~45 %. Draw replay not worth starting on this
evidence (TECHNICAL, dev114 result). Open lead: why ~47 % of draws see a
different texture object each frame. Turn `nfsmw_native_repeat_counter` off
before the next build.

**November 10, dev114 BUILT (diagnostic): repeated-draw counter.**
`ios/build/NFSMW-0.6.1-dev114-repeat-counter.ipa` on iCloud Desktop (dev113
moved to Trash there; still in ios/build). `nfsmw_native_repeat_counter`
default on in this build only: turn off before any release. Next: Stefan runs
one normal pursuit and sends the log; read the `[native] repeat counter:`
lines and say whether draw replay is worth a post-0.6.1 project. Not for
power tests. dev113 40-fps pair still pending in its own thread.

**November 10, dev113 BUILT: iPhone 30/40 drive on the efficiency cores.**
`ios/build/NFSMW-0.6.1-dev113-iphone40-ecores.ipa` on iCloud Desktop. Proposed
0.6.1 battery scope: cap controller, iPhone 40 on E cores, touch auto-hide.
Open: optional repeated-draw counter to size a draw-replay project for 60.

**November 10, dev112 cuts reverted (no saving).** Micro-cuts are below test
resolution. Open choice for Stefan: iPhone at 40 on efficiency cores (Eco-like,
~−9 %/h, rare small dips). Shippable so far: cap controller + touch auto-hide.

**November 10, dev112 BUILT: attribute draw-order memo + XMA codec pool.**
dev111 switches back in source, default off. `ios/build/NFSMW-0.6.1-dev112-cpu-cuts.ipa`
on iCloud Desktop. Next: one A/B pair on the iPhone (A = both new switches
off). SDK patch: tools/ios/patch_ios_xma_codec_pool.py.

**November 10, controller confirmed:** −1.35 %/h (−4.7 %) vs 0.6.0 Balanced
at iPhone 60, alternating A/B, equally smooth. Next: CPU-work cuts (Record
attribute lookup, XMA codec reopen), each tested with one A/B pair.

**November 10, dev111 changes reverted (no saving in alternating A/B).**
Within one sitting the iPhone is repeatable to ~0.6 %/h but drifts ~9 %/h
between sittings: only alternating A/B counts. Next: controller vs 0.6.0
Balanced, alternating, on the iPhone.

**November 10, dev111 BUILT: audio thread at Utility, frame teardown on a
Utility queue.** From the dev110 iPhone Time Profiler (TECHNICAL November 10).
`ios/build/NFSMW-0.6.1-dev111-audio-low-async-free.ipa` on iCloud Desktop.
Next: iPhone pursuit at 60 with Power Profiler, audio check. Further
candidates: Record attribute lookup memo, XMA codec reopen.

**November 10, dev110 BUILT; QoS lever exhausted on the iPhone.** dev109 is
smooth, but a loading-screen boost carried into the drive; dev110 resets
to the start level when driving starts. Repeat A/B: Default saves only ~1–2
%/h over User Initiated at 60. Next: Time Profiler pursuit at 60 (iPhone) to
cut frame-thread CPU work so the efficiency cores can hold the cap.

**November 9, dev109 BUILT: cap controller without probing while driving.**
dev108 probed down while driving (hitches, no saving on the iPhone). dev109
holds each device's measured start level while driving and only steps down
in menus/pause/loading. `ios/build/NFSMW-0.6.1-dev109-cap-no-probing.ipa` on
iCloud Desktop. Next: iPhone pursuit at 60 and 40 with Power Profiler.

**November 9, dev108 BUILT: cap controller + touch auto-hide.** Replaces
the profiles (`nfsmw_cap_controller`, default on): frame threads step
Low/Default/User Initiated only while frames are late. Touch controls hide on
controller/keyboard input. `ios/build/NFSMW-0.6.1-dev108-cap-controller.ipa`
on iCloud Desktop. Next: Stefan's Power Profiler pursuits at 60 and 40 on both
devices. Menu still shows the old profile choice (ignored). TECHNICAL
November 9 dev108.

**November 9, power matrix done on both devices:** iPad Eco = Balanced at 60;
Eco 40 halves drain vs 60. iPhone Balanced's driving boost costs 14–15 %/h
at 60 for the same work, but Eco misses 60. Stefan dropped the profiles: the
new target is holding the cap with the least power. Next: Extra Args boost
trials (workers_count 1/2, level default) on an iPhone pursuit at 60. See
TECHNICAL November 9 iPhone matrix.

**November 9, 0.6.1 battery pass started (analysis only):** Stefan's
November 6–8 iPhone and iPad logs are archived under `Debug/9 November 2026/`.
Both high-drain sessions were long pursuits. GPU ms rose about 2x with fewer
draws, and fixed-size copies slowed the same way, so log GPU ms are likely
clock effects rather than an energy measure. Pursuit CPU roughly doubles and
is the lead. iPad Eco changed nothing visible. Watchdog alerts are
frontend/loading only. Next: read-only audit of Eco/Balanced/Max, then
Stefan's Power Profiler matrix on 0.6.0 (pursuit plus free roam). No source
change approved. See TECHNICAL November 9 (battery pass).

**November 9, issue #18 investigated (D-021, no fix yet):** modded PC save
report reviewed against the supplied November 7–8 log. No recorded crash
exception; all eight watchdog stall alerts recover. Final race rendering
is 60 fps with about 2 GiB reported memory headroom. Unlock everything was
on despite reported defaults, later off; causality unproven. Next: original
PC save, exported converted save, exact failing race/action and matching
iOS .ips; compare with Unlock everything off before choosing a fix.
See TECHNICAL November 9 for archived evidence, hash and limitations.
No source/build/device test or GitHub comment. Session changes are local
record updates only, no push/release. Private docs/BACKLOG.md updated but
intentionally ignored/uncommitted under the November 6 privacy rule;
pre-existing untracked HANDOFF_CHATGPT.md preserved untouched. The GitHub
Support purge follow-up below remains separate and outstanding.

**November 6, public backlog history rewritten:** Stefan approved removing
the backlog from public history. All GitHub branch and tag histories are
clean, and the active local development branch is based on cleaned main
(e403ff9). The private backlog stays local and ignored. All ten releases
and assets were preserved. GitHub still served the file through an old
direct commit SHA after the rewrite. Next: request GitHub Support removal
of retained objects and cached views, then recheck the old SHA. Avoid
merging any pre-rewrite local or external branches into cleaned history.

**November 6, private backlog:** Stefan requested removing the backlog
from GitHub and all mentions from README. GitHub main at 5e277fd has
the cleanup. Keep docs/BACKLOG.md local and ignored. Older GitHub
commits, refs and release snapshots remain historical exposure.
Next: confirm scope before any public history rewrite. The 0.6.0
release remains available.

**November 6, 0.6.0 published:** Stefan authorized publication.
GitHub main and v0.6.0 point to `7eb046c61692be3d2969df241bf6464ee7a5aa44`.
The latest stable release contains the verified dev107 IPA under the
release filename. Next: collect community low-RAM reports and review
free camera and remaining Extra Options for the next minor release.
See TECHNICAL for publication verification.

**November 6, 0.6.0 release candidate prepared:** Stefan accepted dev107
scope. `ios/build/NFS-Most-Wanted-0.6.0.ipa` is the tested dev107 package
under the release filename, with the same SHA256. README and release notes
reflect 0.6.0. Next: confirm publication, fast-forward main, tag v0.6.0 and
publish the prepared IPA and notes. No fresh-container smoke test was run
during packaging. No tag or push yet. Free camera and the other follow-ups
remain in BACKLOG.

**November 6, dev107 user checks:** Stefan confirmed the in-game Options
sidebar and My Cars taps are fixed and the car selector is good. Multiplayer
menus looked good on further inspection. Android compatibility was tested
and Stefan cites a GitHub performance review confirming iOS 18 works.
README now lists iOS/iPadOS 18 as the minimum. Next: review the remaining
0.6 scope (free camera, feasible Extra Options patches and battery work)
and verify onboarding, settings migration, and the new launcher across
devices. Dedicated low-RAM work still awaits a 2–3 GB device report.

**November 6, dev107 BUILT: car selector touch and Options sidebar.**
My Cars neighboring preview taps move focus inside the car scroller.
Quick Race and multiplayer Change Car accept vertical gestures over
the car preview. The Options sidebar uses single-line button titles
after Stefan reported severe wrapping in dev106. Host touch tests and
IPA checks passed. `ios/build/NFSMW-0.6.0-dev107-car-selector.ipa`
is on iCloud Desktop. Next: verify all three car selectors and the
Options sidebar on device. No dev107 device run here.

**November 6, dev106 BUILT: clearer, tighter tabs.** Stefan found
dev105's tabs blended into the surrounding UI and still had too much
padding. Both menus now have a distinct tab background and divider,
tighter spacing and a stronger, shorter active highlight.
`ios/build/NFSMW-0.6.0-dev106-tab-contrast.ipa` is on iCloud Desktop.
Next: check the strip and sidebar on iPhone and iPad along with the
remaining dev104 device checks. No dev106 device run here.

**November 6, dev105 BUILT: fixed launcher title and compact tabs.**
The dev104 iPhone recording shows the large navigation title moving
over the tabs when pulling down. Launcher now uses a fixed inline
title, and both menus use a shorter text tab strip or narrower sidebar
with only the selected tab tinted. IPA
`ios/build/NFSMW-0.6.0-dev105-compact-tabs.ipa` is on iCloud Desktop.
Next: verify title and tabs on iPhone and iPad, then continue the dev104
onboarding and controller device checks. No dev105 device run here.

**November 6, dev104 BUILT: redesigned menus and first-launch setup.**
`ios/build/NFSMW-0.6.0-dev104-menu-setup.ipa`, also copied to iCloud Desktop.
Longest battery offers 30/40 fps and half/every-frame car reflections;
defaults 30 and half. Menu swipes default inverted. Legacy Battery mode
is migrated to editable effective values. No device run. Next: verify
the new layout and controller on iPhone and iPad, first launch and upgrade,
and 30/40 fps with each reflection option. See TECHNICAL for build identity,
delivery and the CoreDevice check. The pre-existing untracked
HANDOFF_CHATGPT.md remains local.

**November 6, dev103 BUILT: old renderer's settings removed from the menus.**
Stefan's go-ahead. Rows gone: `native_renderer`, `no_vulkan`, `scaling`,
Emulated renderer section; `RetiredValue()` returns their old defaults (so
arguments for default settings are unchanged; a settings.json with the native
renderer off now gets it on). Presets drafted in MENU_REDESIGN.md. IPA
`ios/build/NFSMW-0.6.0-dev103-no-old-renderer-settings.ipa` (SHA256 4d5b54f88c6bdaf2225b4c981da474eab0ee9a78573360f41eb0b17e073ec23f).
Not run on a device. Next: Stefan tests dev103 and answers the presets and
open questions; Vulkan code removal from the SDK is a separate plan.

**November 6, dev102 BUILT: settings catalogue split out of launcher.mm (no
visible change).** Stefan: do the behind-the-scenes cleanup now. Plan step 2:
`ios/src/settings_catalog.{h,mm}` holds everything from "The options" to
`Arguments()`; launcher.mm 2347 -> 1241 lines. Every old line is present
unchanged in the new files (line-multiset check; only the default argument of
`KeyBindValue` moved to the header). IPA
`ios/build/NFSMW-0.6.0-dev102-settings-catalog.ipa` (SHA256 246efcbc68f43e0c53d9ac8551d421c2f4b13b857b36e8bf19e0111c3963abfd). Not run on
a device. Next cleanup (step 3, shared cell builder) or Stefan's open questions.

**November 6, dev101 BUILT: menu settings flags (no visible change).** Stefan
approved the refactor. Each launcher setting now carries `flags` (kInGame,
kInGameNative, kNativeOnly, kEmulatedOnly) and `live` cvars; the in-game
sheet's `Keys()`, `NativeOnlyKey()`, `LiveFlags()` and the launcher's two
renderer sets are gone (launcher.h: `InGameKeys`, `InGameNeedsNative`,
`LiveCvars`). Checked by a script against the old lists: 65 in-game keys, 6
in-game-native, 10 native-only, 10 emulated-only, 70 live cvars, all the same
(`nfsmw_native_metalfx` dropped: no argument sets it since dev75). IPA
`ios/build/NFSMW-0.6.0-dev101-menu-flags.ipa` (SHA256 ae4baac45d1486ce72048a14b5c01b2d7203bfc88e5ceb3f4f99cdb67f1941ea).
To check on device: in-game options show the same rows and tabs; changes
apply at once or say "next launch" as before. Stefan also asked (November
6) for much prettier menus, a first-launch onboarding for everyone on the
new update, and removing irrelevant settings incl. the old renderer's: added
to MENU_REDESIGN.md (Look and feel, Onboarding, Settings to remove); next
steps there wait for his answers to its open questions.

**November 6: menu redesign groundwork (docs only).** [MENU_REDESIGN.md](MENU_REDESIGN.md): how the launcher and in-game menus work, problems (four hand-kept lists in ingame_options.mm, launcher.mm doing everything, uneven tabs, Battery mode locking 13 rows, profile wording), proposed shared tabs, shared components, file map, step plan for Codex and the generated settings inventory. No code changed. Next: Stefan picks doc only or doc plus the no-visible-change flags refactor (step 1 of the plan); tab layout, profiles and Battery mode wait for his answers.

**November 6: low-RAM work paused (Stefan).** Changelog now has one entry,
"Important for 3 GB RAM devices", asking for tests on such devices. Next
low-RAM steps (later): low-memory mode once a 2-3 GB device report exists,
~170 MiB graphics outside the renderer's count, XMA decoder context size.

**November 6, dev100 on the iPhone (Stefan): touch controls fine.** Log
Debug/6 November 2026/dev100_touch_nfsmw.log: peak 1330 MiB. Asked Stefan
whether to build the low-memory mode now or wait for a 2 GB device report
(Claude leans to waiting: a race may already fit).

**November 6, dev100 BUILT: touch overlay without a transparency layer.**
`-[NFSTouchView drawNative]` applied the view's alpha (idle opacity 0.35)
with `CGContextSetAlpha` + `CGContextBeginTransparencyLayer`: a whole-screen
buffer per redraw (14.4 MiB, 2 persistent in the dev94 Allocations stats).
Now drawn at full alpha, then the dirty rectangle's premultiplied BGRA bytes
are scaled by alpha (same result as group opacity). IPA
`ios/build/NFSMW-0.6.0-dev100-touch-overlay-memory.ipa` (SHA256 1987e03dcb1558f7d9d51548755ebbec2e0f31fe63b9cd8fa61c7b7e04280135).
To check: touch controls look the same faded and pressed; `[memory]` lines.

**November 6, dev99 on the iPhone (Stefan): race starts fine, no stutter.**
Log Debug/6 November 2026/dev99_race_nfsmw.log: warm-up 223 pipelines in
347 ms, then "pipeline cache let go"; malloc 246 -> 138 MiB at that moment.
Race footprint ~1390 MiB, peak 1403 (dev94: ~1700, peak 1749), malloc
~260-300 MiB (dev94 ~580), graphics ~380 unchanged. A race now fits the
iPhone 11's 2098 MiB limit with ~700 MiB to spare (on this phone's settings).

**November 6, dev99 BUILT: pipeline archive let go after warm-up.** dev98
with the trace ran fine (Stefan; Debug/6 November 2026/dev98_*). allocs.txt:
the big startup blocks are Metal loading our binary archive inside
`PipelineArchive::Make` (11, 17, 25, 38, 50, 56 MiB growth; the 2 x 49.14
and 55.52 MiB persistent blocks), archive file 145376 KiB for 233 pipelines;
the 14.45 MiB ones are `CGContextBeginTransparencyLayer` in
`-[NFSTouchView drawNative]` (touch overlay, 2 persistent, ~29 MiB, next);
4 MiB x 13 and 128 KiB from `Memory::Initialize` (guest tables). dev97 check:
malloc at XEX load 27 MiB (dev94 212); race peak 1720 MiB (dev94 1749),
since ~173 XMA streams are fed in a race (`[xma-voices]`), each still with a
464 KiB decoder (~80 MiB; shrinking FFmpeg's xmaframes context is a later
option). dev99: cvar `nfsmw_native_release_pipeline_archive` (on): once the
warm-up finished, at a periodic report with no pipelines made and nothing to
save, the MTLBinaryArchive is released; a later miss reopens, adds, saves,
then it is released again. Make() takes a strong copy under the mutex.
IPA `ios/build/NFSMW-0.6.0-dev99-pipeline-archive-release.ipa` (SHA256 06ccf05f8085224cf95932c7a446b7987a375cafea07f8bd23ff49ca323ea81d).
To check: `pipeline cache let go` line, malloc drop of ~150 MiB, no new
stutter at race start.

**November 6, dev98 BUILT: allocation trace crash fixed.** Stefan: dev96/97
with `--nfsmw_diag_alloc_trace=true` crashed right at Play (boot.txt ends
after the limit line during SDL init, allocs.txt has only the image list,
nfsmw.log empty; Debug/6 November 2026/dev96_alloc_trace_crash_*). Cause,
reproduced on the Mac (exit 139): the hook's `thread_local` guard; the first
touch of a thread's TLS allocates and re-enters the hook. dev98 uses one
global atomic_flag (busy: skip). Same Mac test passes with stacks for malloc,
calloc, realloc and new. Includes dev97. IPA
`ios/build/NFSMW-0.6.0-dev98-alloc-trace-fix.ipa` (SHA256 1fcbe643ff891856cbceb2d621a931a67d2665b4d3a2b4a80ed682959be6110c).

**November 6, dev97 BUILT: XMA codec contexts on demand (~180 MiB).** Stefan's
"All Allocations" backtraces: the 464 KiB blocks are `av_mallocz` in
librexruntime (FFmpeg codec private data of the 320 XmaContexts, kept for
life); the 128 KiB ones are `av_buffer_alloc(128 KiB)` per context (inferred
from count 324 and Setup code; never read, packet data is xma_frame_) plus
transient native `Record()` vectors and CoreGraphics. New SDK patch
`patch_ios_xma_lazy_codec.py` (cvar `ios_xma_lazy_codec`, on): no codec or
packet buffer at Setup, codec made in PrepareDecoder, freed in Release (the
next user already reopened it via ResetDecoderState, so no extra opens).
Expected heap -145 MiB (464 KiB) and -40 MiB (128 KiB), less the live
contexts. Build note: patch scripts need `NFSMW_SDK=~/Developer/GitHub/nfsmw-multiplayer-sdk`.
IPA `ios/build/NFSMW-0.6.0-dev97-xma-lazy-codec.ipa` (SHA256 219a4a1b02ed2b57e748e8b2e80002cf96d95e8f61aa9bf7c6ce9aa5a6570532). To test:
audio everywhere (menu music, Golf engine, police radio), `[memory]` lines.

**November 6, dev96 BUILT: allocation-stack diagnostic.** dev95 launches fine
(Stefan). Allocations statistics (screenshots in Debug/6 November 2026):
heap 542 MiB; 320 x 464 KiB = 145 MiB, 2 x 49.14 + 55.52 + 2 x 14.45 MiB
(~180 MiB, startup), 324 x 128 KiB = 40 MiB. Their backtraces are empty
("Call stack limit reached", timestamp 0): the blocks predate the attach.
Stefan asked to pick 464/128 KiB blocks made during recording (All
Allocations). dev96 adds `--nfsmw_diag_alloc_trace=true` (off by default):
a malloc_logger hook writes image+offset stacks of blocks >= 4 MiB and the
first 8 of 464/128 KiB to logs/allocs.txt, with image load addresses for
atos. IPA `ios/build/NFSMW-0.6.0-dev96-alloc-trace.ipa` (SHA256 18693061a9224eaedc5baa606cebe2b6c4b68901dc9f87751d1f7c292ae9907d).

**November 6, dev95 BUILT: low-RAM work, steps 2 and 4 (Stefan approved the
4-step plan).** Stefan's iPhone trace and log
(Debug/6 November 2026/dev94_iphone_memory_trace.trace, `..._nfsmw.log`):
race peak 1749 MiB; malloc 212 MiB at XEX load, ~600 in the race; graphics
~370 MiB vs ~200 in the native renderer's own count (targets 74, resolves 35,
textures 60, vertex arena 32). The trace has no exportable Allocations table
(xctrace shows only logs/signposts), so Stefan was asked for Statistics and
inverted Call Tree screenshots. dev95: memory-pressure watch (dispatch source)
frees caches idle 30 frames (texture, attribute, index, GPU buffers), boot.txt
gets the limit + device RAM and a line per warning or when < 384 MiB is left,
with a log flush. IPA `ios/build/NFSMW-0.6.0-dev95-memory-pressure.ipa`
(SHA256 516829bd114d45a7e16652c75a1cc48a0e4c134f50164150a02882b0e921517f).
Caches are small, so expect tens of MiB, not the 2 GB fit. Next: step 1
low-memory mode (scale cap, smaller caches) once malloc is understood; step 3
the ~170 MiB of graphics memory outside the native renderer's count.

**November 6, dev94 on the iPhone (Stefan): Golf crackle gone, menu music
fine, no stuck or repeated snippets so far.** Keep `ios_xma_starve_keep_mono`
on; watch police radio and car sounds in longer play.

**November 6, dev94 BUILT: Golf, second guess.** dev93 test (Stefan): menu
music fine, Golf still crackles; log `dev93_golf_crackles_iphone_nfsmw.log`:
`[xma] starve 5 s: 46-288 resets, 0 looping streams kept`, so loop_count is
not the signal. Reset off is no option (launcher note: music cuts out). The
patch is now `patch_ios_xma_starve_mono.py` (cvar `ios_xma_starve_keep_mono`):
mono or looping streams skip the reset, stereo (music) still resets. IPA
`ios/build/NFSMW-0.6.0-dev94-golf-mono.ipa` (SHA256 561c40422893ae22aec82e331bf601596e6aab47460ef3605d776c15cab34cac).

**November 6, dev93 BUILT: Golf engine cut (#15, D-020) and the Display menu.**
Stefan's Golf log (Debug/6 November 2026/dev91_golf_engine_cut_iphone_nfsmw.log):
host output clean, XMA starve resets ~45/s; launcher "Audio stream reset" off
removed the cut (Stefan). New SDK patch `patch_ios_xma_starve_loops.py`
(cvar `ios_xma_starve_keep_loops`, on): streams with loop_count > 0 skip the
reset; `[xma] starve 5 s` counts resets vs kept loops. Guess, to test: Golf,
menu songs, police radio. Fallback: reset off by default. Display: Screen shape
is now Fit this screen / 16:9 only (old 4:3 and 19.5:9 values become Fit; Fit
wider than 16:9 uses the screen's own width at 720 in steps of 8, narrower
stays the game's 4:3 mode); render resolution titles show W×H for this device
and shape. Duo (dev92) ships in 0.6.0 as experimental (Stefan). IPA
`ios/build/NFSMW-0.6.0-dev93-golf-loops-fit-screen.ipa` (SHA256 ad27555db86ab78ec1f153cd8d69161458f7c58c3c79b0819052426bb45884f1).

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
