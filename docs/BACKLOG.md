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

### iOS 26 black screen with the native renderer on 0.3.0 — open

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
equal); IPA26 (`--ios_utility_qos=true`): one arm shows -29% CPU impact, -6% drain vs Oct 19 OFF (brightness confound); needs a same-day OFF arm.
Await approval; no new source/build/test. GPR prototype remains held. Native
Metal display-link pacing and versioned copy removal are candidates, not proven
energy wins. Free LiveContainer signing and ordinary user workflow are required;
Game Mode currently needs shared-app +LiveContainer2 per Stefan, so do not make
the main plan depend on that or a paid host entitlement. Full evidence, platform
sources, proposal and gates in latest TECHNICAL/checkpoint.

### iPad Pro M4 sun flickering — open

Seen in the same October 15 session as the battery drain (MetalFX temporal to
the screen, 1x then 1.5x, MSAA up to 4x). Not investigated yet. Possibly related
to MetalFX temporal's missing motion for the sky (inferred, unverified).

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

### Pipeline archive persistence — parked

Defer to a future session as requested. A synchronous archive save previously
coincided with a roughly 2.667-second stall. Investigate persistence scheduling
and ownership separately from battery changes.

### Native GPU capture — parked

The capture button investigation is parked. Revisit the native renderer's
capture freeze/crash separately; do not make it a prerequisite for ordinary
Power Profiler or CPU investigations.

## Feature ideas

- Battery-mode-only savings still open (visual changes allowed only there):
  cheaper reflection cube, lower post-effect resolution. See
  `HANDOFF_CHATGPT.md` and the checkpoint before starting.
