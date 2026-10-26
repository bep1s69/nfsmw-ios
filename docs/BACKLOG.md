# Development backlog

Single list of open bugs, parked investigations and feature ideas, shared by
every agent (Claude, ChatGPT Codex) and by Stefan. Each entry: status, devices
and build seen on, evidence paths (current logs live in
`~/Developer/Debug/Most Wanted (2005) Debug/<date>/`),
what is known versus inferred, and the next step. Update the status here when
an item is fixed (and add the fix to `CHANGELOG.md`) instead of deleting it.

Status words: **open** (not started), **active** (being worked on),
**parked** (deferred by Stefan), **monitor** (not reproduced since),
**fixed in x.y.z**.

Keep assigned IDs stable (`B-xxx` blockers, `D-xxx` defects); give new items the
next free number in their series. Update existing entries, including the legacy
unnumbered entries below, instead of opening duplicates.

## Open bugs

### D-001 Null call crash near the first safehouse (iPhone) — monitor

Since 2026-10-12; Oct 22 iPhone logs `22 October 2026/nfsmw_crash_iphone.log`,
`nfsmw_crash_2_iphone.log`: lr 0x823C82F8, r4 0. Deferred-call queue publication
race; fix in IPA36 (`tools/ios/patch_game_deferred_queue.py`). Oct 22
`22 October 2026/nfsmw_run_2_iphone.log` (22:23:22-22:26:30, 1x, guest Utility):
the race that crashed completed, no invalid-call/FATAL. One run of an
intermittent crash: keep monitoring. Details in TECHNICAL.md, October 22.

### D-002 Police-pursuit stutter on the iPhone (22 fps, 20/80 ms) — fixed in IPA48 (iPhone pursuit), wider test pending

iPhone 17 Pro Max, IPA46, 1x/40: about 22 fps in pursuits. October 24 trace
(TECHNICAL October 24): guest worker XThreadDF1B at Utility preempted 69% of each
80 ms gap while the main thread waited; GPU not limiting. IPA48
(`--ios_adaptive_qos_workers=true`) raises the guest workers and render queue
with adaptive QoS. October 24 IPA48 pursuit: 39.95 fps, no slowdown (Stefan),
battery 72 -> 66% in 10.9 min. Still to check: other devices (4-E-core iPads, older
iPhones) and longer sessions. Optional follow-ups:
- Main-loop poll wait -> blocking wait. Main XThread woke ~2,300 times/s in B.
  Oct 24 System Trace found it: 709 short `sys_ulock_wait2`/s in `sub_82593A58` /
  `sub_825A3EC8` (mostly timeouts; only GPU Commands wakes it) and 236 tiny
  sleeps/s in `sub_82441B60`; GPU Commands spins with `MaybeYield` 908 times/s.
  The wait is the existing ring-space hook (already woken exactly by the CP);
  IPA52 raises its cap to 8 ms (`--ios_ring_wait_ms`) and cuts the CP idle spin
  to 4 yields (`--ios_cp_idle_spins`). **Proven on the iPhone pursuit, pending a
  repeat and the iPad:** ~22 %/h vs ~30 (IPA51), cooler, 39.96 fps (TECHNICAL Oct
  24 night).
- Encode cost: `Record()` + `Fingerprint()` are ~35% of GPU Commands; render
  workers ~19 ms/frame in B. Memoize/skip `Fingerprint` for repeated draws, fewer
  encoders per frame. A few ms per frame; after the QoS fix.

### D-003 Small audio crackles on AirPods, mostly in police radio chatter — open

iPhone 17 Pro Max, IPA48, October 24 (`nfsmw_ipa48_chase_iphone.log`); no pattern
found by ear. No output underruns in the log (0 gaps/drops). Candidates, both much
more active in the pursuit (TECHNICAL October 24): the instant-attack limiter in
`coreaudio_driver.mm` (up to 100% of samples turned down, -6.6 dB) and about 200
XMA stream resets per second with decoded output dropped (`[xma-resets]`).
October 24 IPA49: heavy stutter at 17:32 (39 sudden drops in 5 s, one every
~100 ms, peaks to -0.2 dB), output still clean; game-side silent blocks, likely XMA
stream resets. Occurs in every mode, most in Low Power Mode (167 per run).
Parked (Stefan, October 24: minor and inconsistent). When resumed: compare
against the phone speaker, then a test build with a smoother limiter or a lower
mix gain, then the XMA reset path if the crackles stay.

### D-004 Engine sound almost disappears — reoccurred (IPA47)

Stefan heard the engine sound fade almost completely again during an IPA47 run
(October 24, no timestamp, no log). Nothing related stood out in the IPA48 log.
Next: note the time when it happens and keep that log.
October 24 IPA49 (`nfsmw_ipa49_battery_test.log`), Stefan: ~17:27. The log has the
run's largest XMA reset burst at 17:27:21 (556 resets on 116 contexts in a second)
and XMA decode time down to a quarter for ~40 s after it. Inference: many voices,
possibly the engine banks, reset at once and do not restart. Next: find which
contexts (the `most:` ids) belong to the engine, and log when a voice is reset
without restarting. IPA50 adds `[xma-voices]` (stopped-after-reset contexts with
input addresses, every 5 s). IPA50 run: the addresses are per-context rings
(0x0A28C000 + id x 0x1000), not banks; engine identification needs another
signal (e.g. which voices the game starts from the engine banks). No fade that run.
October 24 night IPA53 (`nfsmw_ipa53_sun_issues.log`), Stefan: a robotic "boop"
at ~00:12 and many glitches with the engine bug at ~00:15 (Low Power Mode on from
~00:11; it was on in his earlier glitch runs too, so not ruled out). Output clean
(0 gaps). XMA resets per minute rose from ~1-6k to 9.6k/13.5k/14.1k/11.0k at
00:12-00:15, with `[xma-voices]` showing all 256 streams fed and 2-5 bursts of
300+ resets/s per 5 s. Inference: every XMA context in use at once; check
whether 256 is a context limit the game runs into.

### iOS 26 black screen with the native renderer on 0.3.0 — fix built (IPA43), untested

Oct 22: the 3 iOS-27-only libraries were the stale `ps_af393d4c46af230c_dbg1-3`
bring-up variants; rebuilt for iOS 26 and build_shaders.sh now rebuilds or fails
on any library not built for the minimum iOS. Needs an iOS 26 device check; not
proven to be the black screen's cause.


Reported October 15, 2026 on an iPhone (A19 Pro, iOS 26.6.2) with the released
0.3.0 IPA. Log:
`~/Desktop/debug/15 October 2026 Onwards/nfsmw_ios26_metal_black_screen_0.3.0.log`.
It reports `shader library ps_af393d4c46af230c_dbg2.metallib not loaded:
... deployment target (0x00020009) that is not supported on this OS` and
`3 shader libraries could not be loaded on iOS 26.6.2`. The 0.3.0 fix (shaders
built with `-mios-version-min`) therefore missed at least the `_dbg2` variants.
Inferred cause: stale libraries in the shader cache or a build path that skips
the minimum version. Next step: check `build_shaders.sh` and the minimum OS of
every `.metallib` in the IPA (`xcrun metal-objdump` / `otool -l`). Not
investigated during the October 16–18 battery work.

### iPad Pro M4 battery drain — active

The battery-optimization branch exists for this. Current state, measurements
and next step are in the [checkpoint](DEVELOPMENT_PROGRESS.md#current-checkpoint--october-19-2026).
First report: `nfsmw_ipad_session_insane_battery_drain_sun_flickering.log`
(October 15, ~26 minutes, 50% to 25%, 60 cap, MetalFX temporal to 2064x1548).
October 19 matched pursuit comparison complete: both IPA24 arms supplied and
user confirms same pursuit restarted, ON then OFF. Equal guarded527.535 s:
estimated drain34.1868 /33.3576 pp/hour, CPU110.114 /109.074% one core, GPU
4.299 /4.305 ms. No demonstrated energy saving for the four-change batch;
workload variation prevents a causal regression claim. Four flags remain
experimental/default false. Three-axis follow-up complete: identified guest
front/packet stages cover 9.13 /8.09% app CPU, only partly removable; color/cube
copies ~0.35 ms GPU (~8% span) need exact compatibility/lifetime proof. No unchanged
depth snapshots (315/arm), artificial splits 0; pooling/discard-unread already work.
Next proposed source work is an opt-in frame-flow/copy-eligibility diagnostic in
four app files, then a focused scheduling trace to investigate the LPM result.
October 20: LPM gain traced to CPU operating point only (GPU/display/FPS
equal); Oct 21 IPA27 pair: drain -23.6%, CPU impact -57%; default on from IPA28; iPhone stuttered (45-55 fps), so IPA29 enables it only with >= 6 E cores. Device check pending.
Await approval; no new source/build/test. GPR prototype remains held. Native
Metal display-link pacing and versioned copy removal are candidates, not proven
energy wins. Free LiveContainer signing and ordinary user workflow are required;
Game Mode currently needs shared-app +LiveContainer2 per Stefan, so do not make
the main plan depend on that or a paid host entitlement. Full evidence, platform
sources, proposal and gates in latest TECHNICAL/checkpoint.
October 25 (Stefan, iPhone, plane): ~2+ h in Low Power Mode, 72% to 35%
(~17 %/h), IPA54-line build, default settings. TECHNICAL Oct 26.

### iPad Pro M4 sun flickering — fixed (flicker IPA54, occlusion IPA63; iPad confirmed Oct 26)

Seen in the same October 15 session as the battery drain (MetalFX temporal to
the screen, 1x then 1.5x, MSAA up to 4x). Not investigated yet. Possibly related
to MetalFX temporal's missing motion for the sky (inferred, unverified).
October 24 (Stefan, iPhone, IPA48-53, MetalFX off): since the skybox change the
sun flickers constantly whenever the weather shows it; it is still drawn through
buildings and tunnels (occlusion never hides it, unchanged from before); its
reflection flickers too and stays visible even fully inside a tunnel. Next:
check how the sun/flare visibility is decided (occlusion query or depth read in
the native renderer) and what the skybox change altered; compare with the
emulated renderer.
October 24 night (IPA53 extra-args test, `nfsmw_ipa53_sun_issues.log`):
`--nfsmw_native_sky_last=false` did not stop the flicker;
`--nfsmw_native_occlusion=true` did, and the sun no longer shows through
geometry. So the flicker is the sun glare's query answer, not the sky reorder:
with native counting off the game got the emulated renderer's answers, whose
draws are skipped. The Oct 12 reason for turning counting off (the safehouse
null-call crash) was the deferred-queue race fixed in IPA36. IPA54 makes
`nfsmw_native_occlusion` default on and logs the answers every 300 frames
(`[native] occlusion queries since the last line`). Open: in ~10 min with
counting on Stefan never saw the sun in the sky (weather, or a count too low:
the new line answers it). The sun in the car reflection (IMG_3949/3950) does not
use the query; likely the cube map seeing the sun behind the camera (inferred),
which also explains it in tunnel reflections.
October 25 (IPA54 run, `nfsmw_ipa54_sun_test.log`): 6-7 query addresses per
300 frames, none ever answered 0, counts 65k to 7.8M (above a full 1280x720
frame, so overlapping draws/passes add up). The answer is not too low; if the
sun still never shows in open sky, next check which address is the sun and how
the game turns the count into glare (ratio or threshold). See TECHNICAL Oct 25.
October 26 (long playthrough Oct 25, IMG_3975-3977): flicker gone; the sun
shows in sunny weather but is never hidden (drawn over overpasses, through
trees). ~860k answers on 8 addresses, still none 0; 05D81600 never under ~3
full frames, up to 31. Status: flicker fixed, occlusion still wrong. Next
(proposed): on SNAP frames, log each query's bracketed draws (pass, ps,
depth state, draw count, GPU count) to find the sun's query and why it never
reaches 0. Built as IPA62, untested. See TECHNICAL Oct 26.
IPA62 iPad run: GPU counts are right (mostly 0); answers were filed under the
begin address while the game reads begin-0x20, and unmarked ends opened
runaway queries. Fix built as IPA63; Stefan, iPad, Oct 26: the sun fades in
and out with cover; ~99k of ~127k answers are 0. Fixed.

### Textures flashing — open (since the Vulkan renderer)

Stefan, October 24: some textures flash, seen since the Vulkan renderer days,
so not specific to the native renderer.
`Most Wanted (2005) Debug/24 October 2026/ScreenRecording_10-25-2026 00-09-10_1.mp4`.
October 25 (frame diff of that 7 s clip, car standing still, 40 fps): the only
flashing in the game image is the player car's roof/body reflection, which
changes brightness and pattern from frame to frame (e.g. 0.10-0.30 s), plus
single cells in the top-right sky. The world textures stay stable. Same family
as the flickering sun reflection (inferred: the car's environment map is
unstable from frame to frame).
Stefan: the flashing he means is the billboard at the top left ("Get in the
Zone"), and many textures like it. Crops every 0.25 s: the billboard switches
between sharp and blurry (a lower mip or lower-resolution copy) while the car
stands still; the tree and the sky stay sharp. So it is mip/resolution flipping,
not brightness. Suspects (unverified): the fetch constant's mip range or LOD
bias changing per draw/frame, or two cached copies of the texture (full and
mips-only/low-res) bound alternately. Next (proposed, not done): log per texture
address when the bound size or mip range differs from the last bind. Built as
IPA55 (`nfsmw_native_texture_flip_log`). Run Oct 25: 0 textures changing while
the billboard flashed, so not the texture cache; next suspect two textures or
models alternating (LOD). See TECHNICAL Oct 25.
Stefan then described it as a dark grey layer flickering over the billboard,
worse when moving: z-fighting. The native renderer ignored the polygon offset;
IPA56 applies it (`nfsmw_native_depth_bias`): still the same. IPA57 (shader
invariance): still the same. IPA58 compiles the shaders with exact math (no
fast math, no contraction; 0.1.0 had dropped precise math from pixel shaders
for speed): still the same. Parked Oct 25 by Stefan; state in
DEVELOPMENT_PROGRESS (environment cube and 200x90 blur render black; A/B
without the CPU-side experiments not yet done).
October 26: the cube is **not** black on screen: the rear-view mirror's
shader (ps 8436534c) is the environment cube times a brightness, and the mirror
shows the scene behind (IMG_3975/3977). The black snapshots are a readback
artefact. So the bus-terminal glass shows the cube's real content (trees) too
strongly compared with the 360's faint reflection; the battery-switch A/B is
dropped. Next (proposed): a test switch that gives the glass shaders a black
cube, to see whether the harsh trees come from the cube term. Built as IPA62
(`--nfsmw_native_test_no_envcube_world=true`). Run: glass unchanged, so the
trees are not from the cube. **Parked Oct 26 by Stefan**, together with a halo
around thin objects (gas price sign, spoiler when moving, antennae): both also
on Vulkan, possibly the 360's own look. TECHNICAL Oct 26.

### Red last frame when skipping a movie — open (known issue in 0.3.0)

Skipping an FMV can turn its last frame red for a moment. Stefan asked to leave
it for now.

### Dim band near the right edge below 1x — open

About 5 guest pixels inside the right edge, only at 0.85x/0.75x. Likely a
scaled small post-effect target's last column (rounding, inferred). Evidence:
`~/Desktop/debug/14 October 2026/12th_run_small_gray_bar.png` and
`nfsmw_12_th_run_battery_0.75x.log`. Investigate with `nfsmw_native_dump`.

## Parked investigations

### iPhone event-loading freeze — monitor

Parked at the user's request on October 18, 2026. It no longer blocks battery
optimization. No cause or code fix was established. IPA20 has since loaded
events with all optimizations disabled, Utility alone, the compiled defaults,
and defaults plus the mixed GPU buffer selector. The requested offline check
also reached gameplay, although radio state is not recorded in the log.
The previously failing all-experiments-ON configuration has not been reverified.

If it recurs, preserve the exact Extra Args, graphics settings, device/network
state and complete launch log before changing settings. Compare the guest
request-completion wait and renderer progress against the earlier failure.
Evidence and individual loading checks are in [TECHNICAL.md](TECHNICAL.md).
Do not resume the isolation sequence unless the issue returns or the user asks.

### Pipeline archive persistence — active (Oct 21)

Oct 21: the shadow-caster library change caused two multi-second stutters
(synchronous saves after new pipelines). IPA35 saves in the background to a new
file then renames; awaiting device check that the stutters are gone and the
misses do not recur next session.


Defer to a future session as requested. A synchronous archive save previously
coincided with a roughly 2.667-second stall. Investigate persistence scheduling
and ownership separately from battery changes.

### Native GPU capture — parked

The capture button investigation is parked. Revisit the native renderer's
capture freeze/crash separately; do not make it a prerequisite for ordinary
Power Profiler or CPU investigations.

## Feature ideas

- **In-game options menu (Stefan, Oct 26; 0.4.0 QoL). Status: built in IPA67
  (`NFSMW-ingame-options-67.ipa`); live settings confirmed on device by
  Stefan (Oct 26); IPA68 Battery mode 30 fps, IPA69 reflection/mirror
  resolution setting. Stefan: good enough for now (Oct 26).** Graphics only
  for now (Extra Options are not complete yet, Stefan). Opened from menus and
  pause screens with a gear (top right) or L3+R3. Live: render resolution,
  MetalFX modes, 30/60 cap, FXAA, shadow drawing size, car reflections, auto
  cap, menu cap, 0.75x when hot, Battery mode; next launch: 40/120 fps, MSAA
  and launch-only values Battery mode sets. Next: device test (TECHNICAL,
  Oct 26 in-game options); later Extra Options in it. Separate later items:
  Post-processing switch did nothing (Stefan, Oct 26): the byte only picked
  the visual treatment's branching technique. IPA85 skips the post chain
  (sub_82442310's view byte +9) and adds the switch to the in-game menu;
  waiting for the device test.
  Movable/resizable HUD: functional and declared finished for now (IPA84,
  Stefan Oct 26): size, safe zone, minimap/speedometer/race info positions,
  launcher and in-game, live. Open, not final: (1) the picture shows through
  for a moment at the end of the loading screen at small sizes (what hides
  FadeScreen.fng's black screen is unknown: its alpha stays 255); (2) a
  drag/pinch editor on screen (step 2); (3) element corners are estimates
  from the IPA73 tree; (4) only iPad 4:3 tested. Save manager, pre-launch menu redesign, trainer-style
  menu idea.

- **After IPA52 (Oct 24 night), ranked, none approved:** (1) repeat run + iPad
  check of IPA52; (2) frame-relative ring-wait cap (~half a frame; 70 timeouts/s
  left at 8 ms) - built in IPA53; (3) `Fingerprint`/`Record` encode cost (~35% of
  GPU Commands) - IPA53 speeds up the index fingerprint; line-level profile done
  Oct 26 (TECHNICAL, IPA63 Time Profiler): spread over per-draw lookups,
  proposals A-D (~5-6% of app CPU together); A-C built in IPA64 (D dropped),
  profiled Oct 26: lookups cut as intended, battery effect unmeasured;
  (4) half-precision shaders; (5) re-test IPA49 Default-QoS boost and IPA50
  display match now that threads can idle; (6) main-loop 0.14 ms sleeps (only with
  care, game timing); (7) Low Power Mode hint text.

- **Battery next steps after the Oct 24 iPhone runs (ranked, saved for later by
  Stefan; none approved).** QoS (IPA49) and the display rate (IPA50) did not move
  the drain (~30 %/h); Low Power Mode halved it (~17 %/h), so what is left is its
  clock caps. (1) Recommend Low Power Mode in the Battery settings text. (2) Turn
  `--ios_display_match_cap` back to default false (no gain; 40 fps on a 60 Hz
  pattern is less even). (3) Main-loop poll wait (~2,300 wakeups/s in pursuits):
  one Instruments capture with Record Waiting Threads to find the call site, then a
  blocking wait. (4) `Fingerprint`/`Record` encode cost (~35% of GPU Commands).
  (5) Half-precision shaders (below). (6) Restore the IPA48 boost as the default:
  done in IPA51, with (2). 0.4.0 is held until it has more than battery tweaks
  (Stefan, Oct 24); new features belong in this list.

- **HIGHEST PRIORITY (Stefan, Oct 22): half-precision shader math.** Convert
  translated pixel-shader arithmetic to half precision where it cannot change
  the 8-bit result; the largest remaining GPU lever on Apple GPUs (the Xbox
  shaders run full 32-bit). Not bit-identical: needs per-shader analysis and
  snapshot comparison (nfsmw_native_dump), heavy shaders first (cost probe:
  4fbaecfb, 27d82ea0, 684f4711). See TECHNICAL Oct 22 GPU view.
  Oct 24 analysis (TECHNICAL, late Oct 24): the three top shaders have almost
  no arithmetic (caster writes a constant, trees 3 multiply-adds, fences' shadow
  compares must stay 32-bit); their cost is fill/overdraw/fetches, so half
  precision is expected to gain little. Awaiting Stefan's choice of next step.

- Low Power Mode headroom (Oct 24): on the iPhone at 1x/40 it halved the drain
  (~17 vs ~33 %/h) for ~1% fps (TECHNICAL Oct 24). Ideas, not approved: (1) log
  `NSProcessInfo.lowPowerModeEnabled` and thermal state in `[cpu]` (done in
  IPA49; `[memory]` lines already had both); (2) lower-clock experiment for
  adaptive holds (IPA49 switches; run A ~30 %/h, no saving): User Initiated only for the
  threads on the critical path, or Default instead of User Initiated, or shorter
  holds, measured against a matched Low Power Mode run; (3) suggest Low Power Mode
  in the Battery settings text; (4) at the 40 cap ask for 40 Hz instead of
  120 Hz (Low Power Mode runs the display at 60 Hz, normal mode at 120; TECHNICAL
  Oct 24 IPA49 entry). Built in IPA50 for every cap (`--ios_display_match_cap`):
  iOS gave a 60 Hz pattern for 40 (as Low Power Mode) and the drain did not change
  (~30 %/h). Proposed: default false again. (5) Since QoS and display gave nothing,
  Low Power Mode's remaining saving is clock caps: cut work per frame (main-loop
  poll wait, Fingerprint/Record, half precision) or recommend Low Power Mode.

- iPhone adaptive QoS (Oct 22): Utility for the main/GPU command threads while
  CPU frame work has headroom, normal QoS near the budget. The main open battery
  lever on 4-E-core phones (iPhone CPU impact 21.0 vs display 2.0, Oct 21).

- Older devices (Oct 22, Stefan's goal: as cheap as possible, e.g. iPhone 13 Pro
  Max / A15, 2 performance + 4 efficiency cores). Plan, by expected gain: (1) a
  device-chosen default profile for older chips (= Battery mode chosen
  automatically; polishing work, parked by Stefan Oct 22), (2) renderer CPU trims
  driven by line-level traces (IPA37 has line tables), (3) a direct guest-to-native
  draw path that skips PM4 packet building/decoding (ACTIVE from Oct 22 at
  Stefan's choice; envelope 9.3% iPhone CPU, realistic ~4-6%; high risk), (4) GPU: resolve-copy avoidance, leaner
  shader translation. Needs an older test device to measure; none available yet.

- GPU, image-identical (Oct 21, kept for later by Stefan): avoid whole-surface
  color resolve copies by keeping the source as the snapshot when it is not
  written again (versioned targets; ~0.3-0.6 ms of a 4.35 ms sampled span,
  partly eligible).
- Memory, image-identical (Oct 21, Stefan: worth it for older devices):
  memoryless storage for attachments cleared and discarded within one pass.
  Little energy expected (unread attachments are already discarded); the
  benefit is lower memory footprint on devices with less RAM.

- Battery-mode-only savings still open (visual changes allowed only there):
  cheaper reflection cube, lower post-effect resolution. See
  `HANDOFF_CHATGPT.md` and the checkpoint before starting.
