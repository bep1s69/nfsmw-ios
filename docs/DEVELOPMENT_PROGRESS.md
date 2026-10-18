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
- [Backlog](BACKLOG.md): parked iPhone loading issue, pipeline archive persistence
  and GPU capture. Do not reopen those during battery work unless requested or
  the issue recurs.
- `../HANDOFF_CHATGPT.md`: the original October 15 architecture/history handoff,
  present locally but intentionally untracked. Do not overwrite or stage it.
- Previous battery investigations, before repeating an experiment:
  `/Users/bep1s/Desktop/debug/14 October 2026/BATTERY_FINDINGS.md` and
  `/Users/bep1s/Desktop/debug/14 October 2026/BATTERY_OPTIMIZATION.md`.

## Working rules

- Work locally on `battery-optimization`; do not push, publish, tag or release
  without explicit permission. Local commits are authorized.
- Preserve Stefan Stoica's existing Git author configuration; add no attribution
  lines. Do not commit game assets, generated game code, logs, traces or IPAs.
- Investigate and explain new source changes before implementation; obtain the
  user's approval. IPA23 target lookup reuse is implemented and its initial
  iPad check passed. No subsequent source change is approved yet.
- Preserve default visual fidelity, stability and functionality. Quality
  reductions belong only in optional Battery mode or its settings.
- Make isolated changes. Validate on device before stacking another source
  change. Small experiments get short correctness runs; accumulate them for
  meaningful power comparisons rather than demanding repeated tiny race A/Bs.
- Preserve user-owned and pre-existing changes, especially the heavily patched
  sibling SDK. No SDK source edits are required for the current experiment.
- Persist observations and results in Markdown as explicitly requested on
  October 18, including inconclusive/failed tests and pending device validation.

## Workspace and build

Main repository: `/Users/bep1s/Documents/GitHub/nfsmw-ios`.
SDK: `/Users/bep1s/Documents/GitHub/rexglue-sdk-ios`, also on the battery branch,
with extensive pre-existing local platform patches and submodule changes.
The Android reference repository is the sibling `NFSMW-Recompiled-Mobile`.

Build from the main repository's `ios` directory:

```sh
cmake --build --preset ios --target ipa -j 6
```

The actual build directory is `/Users/bep1s/Library/Caches/nfsmw-ios/build`;
compiled shaders are in the sibling cache `shaders` directory. The IPA is
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

## Current checkpoint — October 18, 2026

- Latest build: **IPA23**, `ios/build/NFSMW-battery-target-lookup-23.ipa`.
  Approved optional last-target reuse in frame setup and encoding. Two local
  caches borrow the map-owned full key and live Target; no resource copies.
  Original map lookup remains when OFF; ON miss has equivalent default
  insertion via try_emplace. Host OFF/ON correctness under ASan/UBSan and -O3,
  final iOS build, optimized ARM64, ZIP CRC, strict deep codesign and unchanged
  104 shader libraries / bundled dylibs passed. New flag defaults false.
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
- Next proposed experiment: reuse the last successfully resolved ready pipeline
  on an exact full PipelineKey match, ahead of ready_.find. Existing profile
  attributes 0.6935% app CPU self to that hash/find block (not all recoverable).
  Borrow the existing map node; cache no nil/failed/pending results. Preserve
  async compilation, collection, failure semantics, PSO ownership and all draw
  state. Use field equality, not raw memcmp: PipelineKey contains bool/padding.
  Independent default-false switch, original fallback, targeted differential
  tests/miss-heavy benchmarks and ARM64 inspection before a gated build.
  **Await approval; no source change/new build/test recording yet.** After its
  correctness check, recommend measuring the accumulated IPA21–24 batch with
  matched settings before adding more small caches. iPhone issue stays parked.
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
- Current IPA22 profile analyzed: October 18 `nfsmw_run_4_ipad.log` plus
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
| `nfsmw_native_render_utility` | false | Render queue largely on E cores; earlier 60 FPS whole-device power unchanged; short iPhone load passed |
| `nfsmw_native_attribute_lookup` | false | Bounded entry front cache, content validation unchanged; iPad correctness passed |
| `nfsmw_native_transform_copies` | false | Guarded scalar transfers, bit-exact differential tests and iPad checks; energy gain unproven |
| `nfsmw_native_lazy_diagnostics` | false | Skips unused normal-frame metadata/labels, preserves snapshots and residency; iPad check passed |
| `nfsmw_native_gpu_lookup_hash` | false | Cache hit rate improved ~57.2% to ~74.0%; device CPU/power gain not established |
| `nfsmw_native_gpu_lookup_stats` | false | Diagnostics only; enable consistently when comparing coverage |
| `nfsmw_native_fused_upload_sizing` | false | IPA21: host/build checks and initial iPad 1.5x/60 correctness passed; device energy gain unproven |
| `nfsmw_native_attribute_bulk_compare` | false | IPA22: exact base + 32-byte front-key equality; all four host switch configurations/build checks and initial iPad 1.5x/60 correctness passed; energy benefit unproven; requires attribute lookup ON |
| `nfsmw_native_target_lookup` | false | IPA23: host/build checks and initial iPad 1.5x/60 correctness passed; energy gain unproven; miss-heavy cost documented |

These are independent switches; clearing Extra Args does not enable the five
older default-false experiments. Most recent iPad profiling had them ON.
Keep test arguments/settings fixed when adding the new flag; don't silently
convert between defaults and the accumulated experimental stack.

## Build references and experiment

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

Current approved implementation: reuse the last exact primary target lookup
independently in the frame-setup and encoding traversals. Production source:
`ios/src/native_renderer.mm`; fixture: `tools/native/test_target_lookup.py`.
The extracted helper retains full string equality, returns the live map-owned
Target and relies on no erasure during a traversal (true of current renderer).
Two cache instances never carry state across frames. No map replacement,
resource snapshots, shader/guest/SDK edits, rendering policy or default changes.

This is an incremental CPU optimization. The sampled target operator[] region
is ~1.04% of app CPU in the confirmed chase, not a promised energy saving.
Previous independent experiments are intact. Test repeated and changing targets;
all-miss cache overhead must remain part of the evaluation.

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
