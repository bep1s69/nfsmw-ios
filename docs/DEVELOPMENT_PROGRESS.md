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

Main repository: `/Users/bep1s/Developer/GitHub/nfsmw-ios`.
SDK: `/Users/bep1s/Developer/GitHub/rexglue-sdk-ios`, also on the battery branch,
with extensive pre-existing local platform patches and submodule changes.
The Android reference repository is the sibling `NFSMW-Recompiled-Mobile`.

Build from the main repository's `ios` directory:

```sh
cmake --build --preset ios --target ipa -j 6
```

The actual build directory is `/Users/bep1s/Library/Caches/nfsmw-ios/build`;
compiled shaders are in the sibling cache `shaders` directory. The build dir
must be configured with `-DNFSMW_NATIVE_SHADERS_DIR=$HOME/Library/Caches/nfsmw-ios/shaders/lib`;
if that cache entry is empty the IPA has no `NativeShaders` and every game draw
is skipped (IPA25). Check `unzip -l <ipa> | grep -c metallib` before handing off. The IPA is
copied into `ios/build/NFSMW.ipa`. CMake/Ninja is used; there is no Xcode project.
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

## Current checkpoint — October 22, 2026

- **October 25: IPA55 (`NFSMW-texture-flips-55.ipa`) run.** While the billboard
  flashed, 0 textures changed fetch constant, size/mips or content between
  frames: not the texture cache. Next (proposed): log textures that alternate
  frame to frame (two LOD models/textures).

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
