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
  user's approval. IPA22's approved comparison experiment is implemented and
  initially device-validated; no subsequent source change is approved yet.
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

- Latest build: **IPA22**, `ios/build/NFSMW-battery-attribute-bulk-22.ipa`.
  Approved and implemented exact attribute-key comparison: reject a different
  base address, then compare the remaining 32 bytes in bulk. Original scalar
  control remains; front-cache content validation and rendered inputs unchanged.
  All four lookup/comparison switch configurations passed host correctness
  checks at ASan/UBSan and -O3. Final iOS build, ARM64 inspection, ZIP CRC,
  strict deep codesign and 104 unchanged Metal libraries passed.
- **IPA22 initial iPad correctness check passed**: October 18
  `nfsmw_run_3_ipad.log`, user reports "still no issues". Renderer build
  19:11:46, base + bulk 32 comparison/front cache ON, fused sizing and prior
  experiments retained. Scale 1.5 / cap 60, MetalFX and FXAA OFF; no Low Power
  Mode suffix. All 11 guarded complete summaries report 60 FPS; pacing 0/3,300
  off-grid, all 33 thermal samples Nominal, no error-level/GPU-failure messages.
- Keep `--nfsmw_native_attribute_bulk_compare=true` with the accumulated
  experimental stack for later measurement. Compiled default remains false;
  no isolated CPU/energy gain is established. No repeat short run or new build
  needed for this result. Sustained stability remains unproven. Next action is
  further investigation/proposal or a meaningful accumulated measurement;
  obtain approval before another source change. iPhone issue remains parked.
- IPA21's initial iPad correctness check passed (`nfsmw_run_2_ipad.log` on
  October 18). Keep fused sizing ON for accumulated tests; its compiled default
  remains false. IPA22's new comparison also defaults false and requires
  attribute lookup ON. Host timings are favorable in five synthetic layouts;
  no isolated device CPU/energy improvement is established for either change.
- Latest completed measurement: the two runs in
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

These are independent switches; clearing Extra Args does not enable the five
older default-false experiments. Most recent iPad profiling had them ON.
Keep test arguments/settings fixed when adding the new flag; don't silently
convert between defaults and the accumulated experimental stack.

## Build references and experiment

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

Current approved implementation: exact bulk comparison of attribute front-cache keys.
Production source: `ios/src/native_renderer.mm`; regression/benchmark fixture:
`tools/native/test_attribute_lookup.py`. The fixture extracts production key,
lookup and sweep code. Comparison is base8 + remaining32 bytes with static
representation guards; map equality, content fingerprints, two-way selection,
replacement, ownership, sweep, shaders and GPU resource operations are preserved.

The profile's selector/key-check region accounts for ~1.17% / 1.09% of active
sampled app CPU; this includes other work and is not fully recoverable. This is
an incremental CPU optimization, not evidence of a large total energy saving.
The prior fused sizing implementation remains intact and independently gated.

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
