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

### D-014 iPhone 14 Pro Max cycles between 60 and ~40 fps — fixed for 0.5.1, iPhone confirmed (October 30)

Stefan reports repeated 20-30 s cycles at native 1x/60 on this phone only,
including Balanced and Max. Log: `/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/29 October 2026/nfsmw_iphone_14pm.log`;
recent runs are October 30 00:15-00:23, build Oct 29 22:38:47; OS/install
method not established from this analysis. Distinct from D-012: Balanced
stays boosted while driving and Max confirms adaptive/Utility off; render
entry samples stay User Initiated (Balanced) / Default (Max). GPU times
rise above the 16.67 ms budget during drops, return below it with 60 fps.
An exact 40 window is 150 x 16.7 ms + 150 x 33.3 ms, not even 25 ms.
Low Power Mode and app auto caps off; drops start with thermal nominal.
GPU clock/power variation or workload plus presentation feedback are
hypotheses; no clock measurement or causal proof. Next: same scene on Max,
stationary if reproducible, cold launch with only
`--nfsmw_native_present_at_time=false --nfsmw_native_frame_trace=true`
added, 2-3 min; compare with this log. No source change approved or made.
Details: TECHNICAL October 30 D-014 analysis.

October 30 follow-up: Stefan says the issue is fixed with the proposed
arguments. Archived `nfsmw_iphone_14pm_2_present_at_time_off.log` beside the
original (same Debug/29 October folder). Max; 11 full steady-world frame
windows 59.6-60.0 fps, no ~40 plateau, presentation summaries unpaced.
This strongly implicates scheduled presentation; no permanent code fix.
Next: retain workaround, then scoped pacing-fix design if requested.

October 30: Stefan approved the default fix before 40 fps work. Built
`ios/build/NFSMW-0.5.0-14pm-60fps-fix.ipa`: scheduled presentation at 60
requires a new default-false `nfsmw_native_present_at_time_60`; the old
master remains true and 30 keeps its tested behavior. Remove the workaround
and trace arguments for the device check (Max, then Balanced, 1x/60).
No new device result yet; runtime evidence remains the successful manual
workaround. 40 unchanged; next after validation is its current-build trace.

Stefan confirmed the default fix: ~1 min chase at Balanced, no issues
(previously appeared sooner). No new log supplied; device/OS/settings
beyond that report not independently checked. Other devices still need a
short 60 fps regression check; scheduled presentation changed on all at 60.
Stefan limits 0.5.1 to this fix and 40 fps pacing.

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

### D-004 Engine sound almost disappears — fix in 0.4.1 (IPA109), pending device test

October 27, IPA109 (`release-0.4.1`): cause found by SpeedBreaker v0.1.8 (same
USA disc): EA SND's mixer CPU budget (sub_82601528, mftb-timed, 3-block
average against 90 % of a 256-sample block) calls sub_82601788 when over,
which expels the lowest-priority voices for good (engine/turbo/skid loops
restart only at a gear change). One late OS wake of the mixer thread trips it.
`ios/src/game_audio_budget.cpp` makes sub_82601788 a no-op (cvar
`nfsmw_ea_cpu_budget`, off; on calls the original) and logs `[ea-budget]` at
most once a minute. Fits the XMA reset bursts below (inference). Next: Stefan's
long race on IPA109; a `[ea-budget]` line at the time a fade used to happen
would confirm.

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

### D-005 Uneven 60 fps frame pacing / world judder — FIXED in 0.4.2 (even game frame time, IPA124; touch-control spikes IPA111; FPS counter IPA88)

October 27, IPA109 (0.4.1, pending device test): the guest vblank thread now
has Mach real-time priority (`ios_vblank_realtime`, from SpeedBreaker v0.1.4,
where that thread woke up to 9 ms late on macOS) and the present-at-time
pacing has a session watchdog. See DEVELOPMENT_PROGRESS, October 27.

Stefan, Oct 26: at the 60 cap the counter stays at 60, but some moments feel
choppier than others; 40 does not do it. iPad race logs (IPA64/73/82) show
2-6 of every 300 frames shown as a 25 + 8 ms pair instead of 16.7 + 16.7:
the free-running 60 Hz guest vblank drifts against the display (the drift
fixed at 30/40 in `patch_ios_vblank_display`). IPA86 locks the 60 cap too
(`ios_vblank_lock_60`): no change. The pairs follow the on-screen FPS
counter's 0.5 s text updates; with the counter off they are gone. IPA87
(cheaper label updates) was worse and drew double text; IPA88 draws the
counter into the game's frame: its pairs gone (IPA88). Left: the race
start's choppiness (texture decode hitches and 33 ms misses); next: an
Instruments trace of the race start (IPA89): the screen gets an even 60.
Stefan: the whole screen judders. IPA90: the game's swap periods are even (sd ~0.45
ms) and choppiness is random through the race. IPA91 (steady 120 Hz display): every
frame shown on the 16.7 ms grid, still "skipping frames": the content's
motion is uneven. IPA92: no repeated frames (fixed-step hypothesis ruled
out). Parked Oct 26 (Stefan): IPA93 keeps the counter fix, turns the 120 Hz
at 60 and diagnostics off. If resumed: race at the 120 cap to tell
perception from content; then the game's timebase reads (~80 inline mftb,
no frame-time function found yet). Oct 27: 120 Hz simulation removes the judder at
60 fps (Stefan) at no measurable CPU cost; only the chase-camera picture
judders, the mirror stays smooth. IPA94 makes 120 Hz simulation the
default; next: a longer play test. Alternative not tried: feed the game's
60 Hz step exactly one tick per frame.
Oct 28 (iPhone, IPA110, 1x/60): with the touch overlay disabled, donuts give
0 of 300 frames off the grid and no Metal HUD spikes, yet Stefan still feels
the judder (TECHNICAL Oct 28). Touch-overlay redraws are a separate cause
of real 33 ms spikes (fixed in IPA111: drawn into the native frame).
Oct 28 later (TECHNICAL Oct 28): measured with a camera log (IPA117,
`nfsmw_native_camera_log`): in stretches the game's camera steps 2x / 0, or
runs one step ahead for 1-3 frames; every frame is new and on time. Not
fixed by: exact per-frame clock (IPA112-114, 118), swap waiting for the
vblank (IPA119: halves the fps), tick remainder carry (IPA120, A/B no
effect), ISO read-ahead (IPA116). Rate depends on the session's warm-up
(12-22% of frames right after a device restart, ~0% an hour later). Next:
find which thread updates the camera vs which draws it (ordering race?).
IPA122 found the cause: the game's main loop runs frames of 13.5/19.5 ms
alternating and 30-45 ms stalls with quick catch-up frames (paced by GPU
queue back-pressure), and the world steps by those times while the screen
shows one frame per refresh. IPA124 (`nfsmw_frame_ticks` 2, default) gives the
world one display period per frame: iPad camera judder 0.05% of frames, iPhone
0 in 4080, Stefan: no judder at any of the old spots. Fixed in 0.4.2. Also open: a sharp counter on its
own layer (the in-frame one is soft at low render scales).
Oct 29: Stefan reports a low-frame-rate feel for the first 20-30 s of races
and pursuits; logs show even 60 fps presentation then (TECHNICAL Oct 29,
"race/pursuit start"). Camera log (TECHNICAL Oct 29, "start judder runs"):
for ~15 s the world moves on 2 of 3 frames at sim 60; sim 120 removes the
still frames (Stefan: much better). IPA167: 120 Hz simulation by default, switch removed (not yet run).

### Customize HUD editor — in progress (IPA150)

Stefan, Oct 29: replace the HUD rows with a visual editor (pre-launch and
in-game): every element shown, Race / Free roam and Pursuit tabs, drag each
anywhere without overlapping, master sliders for size and safe zone, a size
per element. IPA150 does it with outlines (TECHNICAL Oct 29); Stefan:
works on the iPhone. Later:
pictures of the elements instead of outlines.

### D-006 HUD/scene-size regressions on the iPad (race finish, cutscene overlays, pop-ups) — open

Stefan, Oct 26 (IPA91): the asphalt-and-leaves picture behind the race
results shows bars top and bottom on the iPad (it filled the screen
before; on 19.5:9 iPhones it bled at the sides). Screenshot
`Debug/26 October 2026/ipa_91_finish_race_wrong_aspect_ratio.png`. Likely
from the HUD/scene-size work (IPA70-85); not investigated.

Stefan, Oct 27: more screens look wrong since the HUD changes, probably only
at 70% HUD size (the only value he tested on the iPad besides the default,
which looks fine): the end-of-race screen, the TV-style
overlay in the intro cutscene, the pursuit cutscenes, and the bounty and
infraction pop-ups. Inference: the HUD size/safe-zone scale also reaches
full-screen FNG elements that should stay at full size. Next: compare each
at 100% and 70% HUD size, then exclude those screens from the HUD scale.

Oct 29 (from the code, not yet confirmed in a log): the HUD size is applied
to the frontend's one shared matrix (sub_82453768 hook) whenever
game_state.cpp says driving, so every package drawn while driving shrinks,
not only the HUD. Candidates by name (PC files): Chyron_IG.fng (TV
overlay), Infractions.fng, BUSTED_OVERLAY.fng, InGameBackground.fng. Also
latent: the fade fit uses the setting, not the size in effect. Stefan also
sees misplaced pieces during chases. IPA139 logs every screen and its
pieces (TECHNICAL Oct 29); the fix follows its log.
IPA139 log: the bust and race-end TV overlays (BUSTED_OVERLAY.fng,
InGamePhotoMaster.fng) were drawn at 70%; IPA140 draws them at full size and
keeps the autosave icon at the corner (not yet tested). Still open: pieces
misplaced in chases and the bounty/infraction pop-ups (inside the HUD
package).
IPA140 (Stefan): bust fixed; at a race's end the HUD flashed at size 1.
IPA141 fits those packages and InGameBackground.fng instead (size 1, full
width on the iPhone); pursuit pieces (infraction list mid-left, "PURSUIT
CTS" mid-right at 70%) wait for its log.
IPA141 broke the photo screen (missing text, growing stripes): reverted to
IPA140's behaviour. IPA142 moves "PURSUIT CTS" with the speedometer and
re-moves the infraction lines after the script places them (not yet
tested). IPA142: PURSUIT CTS fixed, the rows flashed; IPA143 moves the
rows' children instead (Stefan: fixed). iPhone: marker of the
busted/evade bar lost, loading screen and asphalt picture bleed on all
sides; IPA144 fixed the bar; IPA145 fills the loading screen (not yet
tested). The asphalt picture's iPhone side margins stay open (fitting it
broke the pause menu, which uses the same package). IPA146 scales its
groups whole instead (pause fixed); IPA147 covers the iPhone screen with
the results' leaves picture (InGamePhotoMaster.fng) and fixes the song box
under the pause menu: wrong picture, removed in IPA148. Known issues: the
leaves picture's iPhone side margins (package unknown, perhaps
PostRace_Results.fng), the song box at full size under the pause menu, the
loading screen's slight twitch. IPA149 (15% larger backdrop) did not reach
the leaves either: removed; their iPhone margins stay a known issue. Known issue: the loading screen's
pieces twitch slightly since IPA145. Open: iPhone side bars on BUSTED_OVERLAY and InGameBackground
(the widescreen layout, not the HUD size).

Stefan, Oct 29 (0.4.3, iPhone, `.../29 October 2026/0.4.3 Stefan iPhone
15min balanced/race_finished_screen.png`): the leaves picture is still
broken on the iPhone. With the loading-screen twitch and the HUD elements
zooming in at the end of a race (most visible on the iPad), these are the
three remaining large visual bugs (Stefan).

### D-007 Black Edition switch shows no visible change in game; street BMW M3 GTR — fixed (IPA96, iPad confirmed Oct 27)

Reported by Stefan Oct 27. The switch does take effect: every log since Oct 13
prints `[black-edition] bandera 0x82A2CE04 = 0x00000100`, and the career-start
pool overflow (fixed, see TECHNICAL) happens only with it on. What the flag
gates (read from the generated USA code, Oct 27): the write sets the byte at
`0x82A2CE06` to 1, part of a block of game option bytes at `0x82A2CE00`. About
16 functions read it. The clearest, `sub_822EA0E8` and `sub_822EAA60`, unlock a
car if it is normally unlocked OR (flag AND `sub_822EABD0(key)`), and
`sub_822EABD0` is a hardcoded list of 10 keys (0x02D642B8, 0x03D3401A,
0x03D8A6D1, 0x363A1FEA, 0x54653C71, 0x54655133, 0x582F21D9, 0x634D1BD2,
0xE1075862, 0xE115EAD0), the cars sold as downloads. So the flag only marks
those as owned; it adds no models. The keys did not match the PC car folder
names under the string hashes tried (bStringHash, Jenkins with 0xABCDEF00), so
which cars they are is not known yet. Likely why nothing shows: those cars are
already unlocked in Stefan's save, they only appear in some lists (Quick Race,
car lot), or their models are not on the disc (inferred, not checked).

Street M3 GTR: the Xbox 360 ISO is not on the Mac (only the encrypted
`default.xex`), so the disc's `CARS` folder was not checked. The street GTR is
the prologue car in every edition, so its model is almost certainly on the 360
disc (PC files have `CARS/BMWM3GTR` plus `CARS/BMWM3GTRE46`). Whether it can be
picked is game data and unlock logic, not missing content.

Oct 27 (later), disc checked (`~/Downloads/Need for Speed - Most Wanted (USA).iso`):
the 360 game packs its files in `NFS/ZZDATA*.BIN`, indexed by `NFS/ZDIR.BIN`
(24-byte entries sorted by bStringHash of the uppercase path with
backslashes). 1347 of the PC copy's 1420 paths are on the disc (missing: PC
movies, installers, some frontend platforms, `GLOBAL\INGAMEC.BUN`, locales).
All of `CARS\BMWM3GTR` (street), `CARS\BMWM3GTRE46` (race), `CAMARO`, `911GT2`
and `CORVETTEC6R` geometry and textures are present, so the content is on the
disc. Stefan (Oct 27): his normal save was only played with the switch off;
saves are not compatible between on and off; with it on there should be an
extra Challenge Series event, which is absent. `sub_822EAA60` also checks a
profile bit (word at +180 of the object at `0x82A2C684`, mask 0x2000) before
the flag, and compares against 6 keys built from strings in the encrypted XEX.

Oct 27, fresh profile with the switch on (Stefan): the Challenge Series
event 69 (the Camaro one) is still missing. Decrypted XEX image
(`tools/ediciones/imagen.py`) names the 6 keys in `sub_822EAA60` (event
availability; keys are Jenkins hashes, init 0xABCDEF00, via `sub_8214AC28`):
`99.1.1` is always hidden; `21.1.1`, `21.2.1`, `21.2.2` and `19.9.70` are shown
only with the flag on; `19.8.31` needs `sub_823C5028(.., 3, 0)` and the profile
bit clear. `19.9.70` is the Black Edition challenge (the regular ones are
`19.8.1`..`19.8.69`), and it is in the 360 `GLOBAL\GAMEPLAY.LZC` (JDLZ; same
event IDs as the PC copy's `gameplay.bin`). So the data is on the disc and the
gate should pass with the flag on; something else drops it. Not identified:
the 10 keys of `sub_822EABD0` (no match among any string in the XEX,
attributes or gameplay files, Jenkins or bStringHash). Callers of the gate:
`sub_8255E670`, `sub_8225DA28`, `sub_8255C238`, `sub_8256A940`,
`sub_8226BBA0`. Hypothesis: a fixed-size table (like the record pool fixed
earlier) or a list builder that skips the event.

Next (needs Stefan's OK, temporary code): log `sub_822EAA60` calls and
results for `19.9.70` and its callers while opening the Challenge Series
menu, to see whether the event is asked about at all and what is returned.

**Cause (IPA95, iPad, Oct 27, `27 October 2026/nfsmw_ipa95_be_probe_ipad.log`):**
the Challenge Series list (`sub_8256A940`, call at 0x8256AA50) asks about all
70 events; `19.9.70` and `19.8.31` return 0, and the flag byte `0x82A2CE06`
reads 0 although the patch logged its write. The patch stores the host
`uint32_t` 0x00000100 on a little-endian CPU, so guest bytes CE04..CE07 become
00 01 00 00: it sets **CE05**, not CE06. Xenia's `be32` write gives 00 00 01 00.
The comment in `nfsmw_app.h` ("memory is big-endian, write as is") is wrong.
Result IPA96 (Stefan, iPad, Oct 27): all 70 Challenge Series events including
the Camaro one, Black Edition cars in Quick Race, career starts. Probe removed.
A save made with the switch off (BEPPY) also loads with it on and has all the
content, so Stefan asked to remove the switch: the launcher always passes
`--black_edition=true` (`extra_args.txt` can still override it).
CE05 is a different game setting (read e.g. in `sub_822CB*` at 0x822CBD68
while loading records): it, not Black Edition, is very likely what caused the
84-record pool overflow and the on/off save incompatibility. Proposed fix:
write the guest bytes explicitly (CE06 = 1, the rest 0), then retest the
Challenge Series count, Quick Race cars and career start; the pool fix can stay.

### D-009 Achievements do not follow the career to another device — fixed (IPA102; Vic restored by hand, confirmed Oct 27)

Stefan, Oct 27: Blacklist rival beaten on the iPhone (Vic, #13), save moved to
the iPad, the achievement stays locked there. Screenshot
`Debug/27 October 2026/broken_achievements.png`. Cause: unlocks are the SDK's,
per device (`Documents/data/achievements/<title>.toml`), not in the save.
IPA102 keeps the union of every device's unlocks in `<iCloud folder>/NFSMW
Achievements/` and merges both ways on every sync (launcher start, after a
game save). Achievements are therefore per player, not per save.
IPA102 result (Stefan, Oct 27): Vic missing on both devices. The iPad's
night-session log (`Debug/16 October 2026 - Battery Optimzation 2/
nfsmw_night_session_ipad.log`, 03:20:49) shows `Achievement unlocked:
00000003` on the iPad, but no device's file has id 3 now: the unlock was lost
after it happened (cause unknown; LiveContainer's data container changed
between Oct 16 and Oct 26 logs, 0066D757 -> 08BCB97E). Oct 27: id 3 added by
hand to the iCloud union file with the logged time (backup of the old file in
the session scratchpad). Lasting fix idea: re-derive the Blacklist
achievements from the save once its Blacklist progress is decoded.


### D-013 Race-finished screen keeps the driving controls; no touch navigation — fix in 0.5.0, untested

Stefan, Oct 29 (0.4.3, iPhone, screenshot in `.../29 October 2026/0.4.3
Stefan iPhone 15min balanced/race_finished_screen.png`): the touch driving
controls stay up on the race-finished screen; they should go and the screen
be navigated by touch (its prompts: A Continue, X Race Stats, Y Restart,
like the menu taps in the touch-controls plan). Cause: the photo screen,
`InGamePhotoMaster.fng`, was not in the menu list; added (TECHNICAL Oct 29).

### D-012 Frame rate sinks to 40 mid-race when adaptive QoS returns to Utility — fix in 0.4.3, untested

GitHub tester (iPhone 17 Pro Max, iOS 26): 60 fps until `[adaptive-qos] back
to Utility`, then a flat 40 for 36 s before the next boost; Stefan's logs
show the same returns. 0.4.3 keeps the threads boosted while driving, detects
late frames by the cap's budget within ~1 s, and adds Performance Eco /
Balanced / Max (TECHNICAL, Oct 29); with 6+ efficiency cores (M-series
iPads) Balanced keeps the original behaviour. Next: Stefan's A/B (fps and
battery) on the iPhone, then the tester's log.

### D-011 iOS 26: native renderer crashes on Play (GitHub report, 0.4.2) — fixed (0.4.3; diag2 confirmed on iOS 26 Oct 29)

iPhone 17 Pro Max, iOS 26.7.2: SIGSEGV at 0x9a0 inside AGX
`drawIndexedPrimitives` (the driver reads a null encoder state slot), from
`RenderFrame`, 1-2 s after Play. Pure Vulkan works there; native works on
iOS 27 (Stefan's 17 Pro Max). Evidence: `.ips` and log in
`/Users/bep1s/Developer/Debug/Most Wanted (2005) Debug/29 October 2026/`.
Diagnostic build `ios/build/NFS-Most-Wanted-0.4.2-diag1.ipa` (branch
`diag-ios26-native-crash`): Metal API validation and a synced per-draw log
in `Documents/logs/native_diag.txt` (switches `nfsmw_diag_metal_validation`,
`nfsmw_diag_draw_log`, both on). Stefan's iOS 27 smoke test passed (Oct 29,
validation active, no MISMATCH). User's iOS 26 run: no crash with
validation on (17 fps, the layer's cost), 0 MISMATCH. Next: same build with
`--nfsmw_diag_metal_validation=false`. That run crashed at frame 2 draw 5.
Cause: iOS 26 reuses the encoder address and the renderer's per-encoder
state caches compare addresses, so a new encoder misses its pipeline.
Fix (reset the caches at encoder creation) in test build
`ios/build/NFS-Most-Wanted-0.4.2-diag2.ipa`, confirmed on iOS 26 (Oct 29).
The fix alone is on `main` as 0.4.3 (`ios/build/NFS-Most-Wanted-0.4.3.ipa`).
Possibly also GitHub issues 4 and 7 (iOS 26 native black screen): unconfirmed. Details: TECHNICAL, Oct 29.

### D-010 Career "appears to be damaged" (GitHub issue 8) — fixed (IPA137, Stefan confirmed Oct 29)

Not Black Edition and not file damage (checksums and structure fine). The
loader `sub_822C3A60` compares the player ID saved after the gameplay section
(NAME: 2C9B8528) with word +8 of the object at 0x82A2C684 (Stefan's devices:
55ADA3B6) and fails if they differ (IPA133 probe). IPA134
(`ios/src/game_save_id.cpp`) writes the device's ID into the load buffer and
reruns the loader. Negative: setting CE05 (IPA132) and clearing the 13 record
slots past 75 did not help. Open: why the user's own device rejected a save
it wrote (ID changed between installs/versions?). Details: TECHNICAL, Oct 28.

### D-008 Save sync misses a newer save (iPad/iPhone) — fixed (IPA98, confirmed by Stefan Oct 27)

Stefan, Oct 27: when the only difference between the iPad and iPhone saves is a
Challenge Series event, the other device does not see the save as newer and
shows an older save date. Likely cause (inference from the code, not tested):
the extra record-pool entries are written to `Documents/save_extras/<save>.pool`
(`ios/src/game_pool.cpp`), outside the save folder, so the save manager's hash,
date, backups, export and iCloud copy all ignore that file. If the challenge
result lands there, the save looks unchanged. Second cause: changes are only
uploaded when the launcher opens, not when the game saves. Stefan also finds
the save manager UI unintuitive; a redesign and import of downloaded Xbox 360 /
Xenia saves are wanted (approved plan in DEVELOPMENT_PROGRESS, Oct 27).
IPA98 (TECHNICAL, Oct 27): the extras file is now hashed, dated, backed up,
exported, imported, uploaded, downloaded and deleted with its save, and a
sync runs 10 s after the game writes a save. Stefan (Oct 27): works. IPA99:
delay 3 s; saves only in iCloud can be deleted from iCloud in the app.
IPA100: save screen redesign (step 2). Wanted next (Stefan, Oct 27): cars
owned, career progress, Challenge Series progress and save date for every
save, including ones only in iCloud. Only cash and bounty are decoded; the
MC02 body has no readable section tags (a `Game` tag at 0x44, two `GrtB`), so
the rest needs before/after comparisons of backups.
IPA100 confirmed by Stefan (a re-done race shows the new save time). IPA101:
import accepts .zip, Xenia folders, Xbox 360 CON/LIVE/PIRS packages (the
SDK's STFS reader) and bare MC02 files; writes a header when none comes
with the save. Untested on device; no 360 package was available to test.
Unknown: whether the game accepts a save made on another profile.

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
Game Mode currently needs shared-app +LiveContainer2 per Stefan (0.4.3 adds
LSSupportsGameMode for certificate sideloading), so do not make
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

### D-0xx Touch controls overhaul — steps 1-2 and part of 3 built (IPA151-153), not tested

Stefan, Oct 29, with a video of the Android port (also an Xbox 360
recompilation; `Debug/29 October 2026/android_touch_controls.mp4`). Four
steps, one IPA each, each approved:
1. Steering setting: dynamic joystick (default; anywhere in the bottom-left
   quarter, fades out on release, not placed in the editor), fixed
   joystick, or two buttons. IPA151, not run yet.
2. Driving look: bigger hit areas than the drawn buttons, cleaner icons,
   controls dimmed while not touched (haptics and opacity exist). IPA152
   (with step 1), not run yet.
3. Menus without an overlay, as on Android: a swipe moves the left stick
   in that direction; a tap where the screen shows a button prompt
   ("B Back", "A Accept"...) presses that button. No separate Back button.
   Needs the prompts' screen positions from the game's menus. IPA153: no
   overlay, swipe = left stick, tap = A, two-finger tap = B (interim, until
   the prompts are found). Prompts move per screen (main menu / safehouse:
   B Back, A Accept bottom left; post-race: A Continue, X Race Stats,
   Y Restart bottom middle, `ipa144_iphone_IMG_4057.png`), so fixed tap
   areas will not do: find their FE objects (button icon images) in the
   pushed packages at run time, e.g. a diagnostic dump of the objects
   under a tap.
3c. (Stefan, Oct 29, after testing IPA153: all fine) the D-pad's driving
   actions as buttons, each only when it applies: ENTER (up: shop,
   safehouse, engage event) only inside an event / shop circle; MAP (left)
   always; SMS (right) and Blacklist (down) in free roam; down also shows
   the race's or pursuit's details during one. IPA154: the four buttons
   always shown; `[hud-watch]` log to find what tells the states apart (no
   separate HUD package for free roam or pursuits; HUD_Drag.fng for drag
   races). Screenshot: `ipa153_controls_screen_dpad_IMG_4065.png`.
   IPA155: ENTER only in a circle, MAP/SMS only outside races (TECHNICAL
   Oct 29); pursuits not identified yet (no pursuit in the IPA154 run).
4. Drag race layout: gas, shift up/down, nitrous, two lane-change buttons
   (how Android does it). IPA163: HUD_Drag.fng pushed = drag race (PC
   name, unverified on X360), DRAG layout; not run.

### D-0xx Circle prompt's spinning ring jumps below its icon — fix in IPA156, not tested

Stefan, Oct 29 (iPhone, IPA154, Custom HUD with the minimap moved to the
top left): in an event or safehouse circle, the prompt icon over the road
("which D-pad button to press") overlaps where the minimap was (fine with
his layout), and its spinning ring (like EA Trax's) alternates between
around the icon and ~1 cm below it. IPA154 [hud-watch]: the prompt is
3B1B624A (-5,-90) with 0A729B1B; at 20:16:52 the group 3345911D (3,-189)
with 35236DBE (-8,99) and D907EF51 / B996A84C (-8,100, flags 43000000 /
43800000) came up: likely the ring, under a parent at -189 + 99. Suspect
the HUD pieces' moving (game_scene_size.cpp MovePiece / AddPieces) moving
one of these objects on some frames only (as EA Trax was). Cause
(TECHNICAL Oct 29): both are top-left pieces, moved with Stefan's
infractions (-8,+100); 3345911D was "placed again by the game" and went
by_children, the ring's frames alternating. IPA156 leaves them out of the
pieces.

### D-0xx Custom HUD on: no darkened backdrop under the map, Blacklist and SMS — open

Stefan, Oct 29 (IPA159/160, iPhone): with Custom HUD on, the world map,
Blacklist (InGameReputationOverview) and SMS screens lack the dark layer
over the game (`ipa159_IMG_4068-4070.png`); the pause menu has it
(`_4072`). With Custom HUD off the SMS screen is darkened
(`ipa160_customhud_off_IMG_4073.png`). IPA159 ui-tree: WorldMapMain.fng's
dump at BE8D11C0 (the address InGameBackground.fng had) holds type 9
pictures (C51113EB, A8DE2158, C6AFDD7E, 254/510 x 540) like
InGameBackground's; the darkening is probably InGameBackground.fng (or a
HUD piece), changed by nfsmw_hud_fit_backdrop or the HUD's pieces when
Custom HUD is on. Not investigated.

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

- **Import PC saves (Stefan Oct 27; 0.4.0). Status: works (IPA108 build of
  this branch; the converter was developed and tested as IPA105-107 on
  `dev-0.5`, Stefan iPad: My Cars has the PC save's 89 cars, races and saving
  work).** Converter `ios/src/save_convert.cpp`; details and failed attempts
  in TECHNICAL (Oct 27, PC save import).

- **VERY HIGH PRIORITY (Stefan, Oct 27): motion blur switch.** An on/off
  setting for the game's motion blur (launcher and in-game options menu).
  Built in IPA103 (`NFSMW-motion-blur-103.ipa`; TECHNICAL, Oct 27 motion
  blur switch): the view's blur amounts read 0 while the visual treatment
  picks its technique and sets its blur. Untested. Stefan (Oct 27):
  Post-processing off also removes motion blur, and in a quick test the
  judder was gone; next: IPA103 with Post-processing on and Motion blur off,
  to tell the blur from the rest of the post chain. IPA103 with blur off
  (Stefan, Oct 27): blur gone, smoothness unclear to him; pacing log mostly
  0 of 300 frames off the grid. Switch works; judder link unproven.
  Stefan (Oct 27): also his next suspect for the 60 fps judder (D-005): the
  mirror, which has no motion blur, stays smooth. Next after the save manager.

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
  (sub_82442310's view byte +9) and adds the switch to the in-game menu.
  **Fixed in IPA85** (Stefan, iPad, Oct 26: looks as it should).
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

### D-0xx 40 fps cap: frames shown 16.7 / 25 / 33 ms apart on the iPhone — improved in 0.4.2 (no present-at-time pacing at 40; RC7), confirm

Oct 28 (iPhone 17 Pro Max, 120 Hz, 40 cap; IPA124 `nfsmw_ipa124_30_40_fps_tests.log`
and 0.4.2 RC2 `nfsmw_0.4.2rc2_tests_iphone.log`): `pacing: ~200 of 300 frames off
the 25.0 ms grid`, gaps in 120 Hz refreshes about one third each 2 / 3 / 4
(plus some 1). Every frame is new and the world steps are even since RC2
(120 Hz simulation at the 40 cap), but presentation itself is uneven at 40.
Stefan: 40 fps in Battery mode "great, not perfect". Same before RC2, so not
caused by the 0.4.2 changes. Next: look at the present-at-time pacing at the
40 cap (target from the last shown frame minus 2 ms; frames arriving around
the target).


October 30 follow-up (active for 0.5.1, Stefan): current source already
excludes cap 40 from scheduled presentation (RC7). The D-014 60 fps success
does not fix/validate residual 40 pacing. Next: cold current-build 40 run,
Low Power Mode off, `--nfsmw_native_frame_trace=true` (and presentation
false), to locate unevenness before/after GPU completion. Preserve the
RC4-RC7 negative results; do not repeat wider target margins or
minimum-duration presentation as an assumed fix. TECHNICAL October 30.

October 30 latest 40 test: archived
`Debug/29 October 2026/nfsmw_iphone_14pm_3_40fps_trace.log`. Latest launch
isolated from two preceding runs. iPhone 14 Pro Max, Balanced/1x/40,
Low Power Mode off, nominal; ~40 maintained, display/guest 120 Hz, boosted
render QoS. 2220 gaps: swap sd .747 ms, shown sd 2.870 ms, mean ~25;
shown bins 25.0:1613, 29.2:214, 20.9:170, 20.8:116, others 107.
Candidate: default-off 40-only CAMetalDisplayLink integration; Stefan
requested design review first. No 40 source change/build yet; next is
design approval. Full evidence/design in TECHNICAL October 30.

October 30: Stefan approved trying the reviewed design. Experiment built,
not device-tested: `ios/build/NFSMW-0.5.0-metal-display-40-test.ipa`.
`nfsmw_native_metal_display_40` defaults false; true selects system Metal
display-link drawable/target delivery at 40 only. Lifecycle/ownership
handoff and diagnostics added; 60 fix remains. Next: same 14 Pro Max
Balanced/1x/40 cold test with experiment + frame_trace true, then compare
pacing/latency before rollout. No claim of a 40 fix yet. Build identity,
failed compile and exact checks in TECHNICAL October 30.

October 30: experiment test1 failed twice before gameplay (archived
nfsmw_iphone_14pm_4_metal_display_40_crash.log). Found documented API error:
timed presentation asserts with CAMetalDisplayLink drawables. Corrected
to plain command-buffer present and proper submission-deadline filtering;
`ios/build/NFSMW-0.5.0-metal-display-40-test2.ipa` built, not run. Same
experiment/trace flags; next startup check then pacing/latency run.
Need .ips/boot.txt if termination persists. No 40 improvement validated;
keep experimental default off. Full evidence in TECHNICAL October 30.

October 30 test2 result: starts/plays, Stefan feels worse (mostly world
jerking, slight extra input lag). Archived nfsmw_iphone_14pm_5_metal_display_40_test2_worse.log.
Screen pacing 1435/1440 gaps at 25 ms, but swap->shown mean 63.63 ms vs
27.42 baseline selected windows. Ordinary display link reports 80 Hz;
integer guest-clock conversion can output 80/160 Hz, breaking intended
120 Hz grid. Test3 corrects only experimental guest grid from managed
system 40 cadence (3 ticks/slot), keeps latency 2 and plain presentation.
Built NFSMW-0.5.0-metal-display-40-test3.ipa; 3000 host arithmetic checks
passed, no device result yet. Next: same run + camera log. Stefan accepts
~one frame extra input delay for truly smooth motion; cadence alone is
not success. 40 fix remains unaccepted/default off; details in TECHNICAL.

October 30 test3: Stefan still feels a few stuck frames about every 5 s.
Archived nfsmw_iphone_14pm_6_metal_display_40_test3_stuck_frames.log.
Guest grid confirmed8.34 ms, 1437/1440 shown intervals25 ms; no recurring
5 s display-gap sequence established, camera rotation not conclusive for
full-picture freeze. Next existing-switch test: same test3/40/diagnostics,
add nfsmw_frame_ticks=0, cold same chase, then restore default2. Isolates
world timing, not a global reversal of the 60 fix. No new code/build and
no accepted 40 fix; see TECHNICAL October30 for measured limits.

October30 frame_ticks=0 trial (log7 archived) feels even worse; selected
1440 shown gaps all25ms. Restore mode2. Built test4-diag IPA with default-
off world-update time/debt logger;24000 host returns match prior code.
Next same40 run with mode2, world logger + existing repeat-strip/trace
flags, camera diagnostic removed. No timing behavior change or accepted
40 fix; full flags/build/evidence in TECHNICAL October30.

October30 log8: mode2 explicitly confirmed (existing0.4.2 default).2280
shown gaps all25ms but~16.5% world updates receive different time steps;
no steady repeated strips. Built test5-world-step trial: one full25.02ms
world step only in managed40 driving,unchanged legacy/other caps/menus.
Same diagnostic flags;next check smoothness/game speed. Must assess actual
below40 performance/missed-frame compensation before default: constant
steps can slow simulation at sustained<40. Not an accepted general fix.
Archive/build/tests in TECHNICAL October30.

October30 test5/log9: successful steady40 on14 Pro Max,Balanced1x.
Stefan "felt like heaven in terms of everything";world steps~25.02ms,
1978/1980 shown gaps25ms,given/raw time99.95%,no steady strip repeats.
Known-good test5 retained. Remaining before0.5.1 default: true under40
performance/game-speed behavior,menu30/background-resume and second
ProMotion40/60 regression check. Not yet a released/general-device fix;
full measurements/limitations and archive path in TECHNICAL October30.

October30 log10 heavy/native test: real27-32fps,GPU>25ms;world given/raw
ratio75.4% confirms test5 slow motion below cap. Not release-ready.
Built test6:managed assigned-target missed-slot compensation,phase jitter
fractions cancel,steady40 unchanged;host/sanitizer checks passed,no device
result yet. Next1x smoothness +native below40 game-speed comparison,same
five flags. Then lifecycle/other-device regression before0.5.1 default.
Archive/build/limits recorded in TECHNICAL October30.

October30: 14 Pro Max returned/unavailable. Stefan requested test-only
resolution choices up to8x for another device's overload test. Built test6
resolution-stress IPA (identity/commands in TECHNICAL and checkpoint),
build option defaultsOFF and cache resetOFF. Next1x then gradually raise
until below40,restore1x,same five diagnostics;report device/OS. No device
validation or release approval yet;remaining correctness checks unchanged.

October30 17 Pro Max stress result:1x/3x smooth40;5x~21.9fps,
worldclock compensation active (selectedgiven/raw104.4%). Actualsimulation
speedunproven;Stefan suspects slowlogic and will compare race timer with
30s externalstopwatch at1x/5x,sameIPA/args,skip8x,restore1x.8xblackpicture/
termination near6GiBprocesslimit,unproven cause;stressonly,outsidehotfixscope.
No defaultpromotion. SeeTECHNICAL for archive,measurements and limits.
If needed,nextinstrument actualworld consumption;newlaptop lacks generated
sources/buildcache and requiresrestoration beforeanotherbuild.

October30 race repeat(log12):Stefan confirms slowerlogic at~26fps.
Lateclockgive124.2%ofelapsed means no simplemissingtime atourhook.
Engineinspectionfoundconditionalaccumulatorcap4*sharedstep:120Hzpatch
halvesinitial66.67msbudget to33.33ms. Runtimebranch/multiplierunverified;
strongcandidate,notprovenfix. Nextactualclamp/tickconsumptiondiagnostic
plusworld/rendercountaccounting;test6notready,60fixretained. Rawgenerated
sources restoredforinspectiononly;matchingCLI/postpatches/cache needed
beforebuild. Evidence/failedrestorationcommands inTECHNICAL.

October30: Stefan approved the next diagnostic. Test7 built/verified,
`ios/build/NFSMW-0.5.0-metal-display-40-test7-world-step-diag.ipa`.
Default-off [world-step] via existing frame_ticks_log records incoming time,
activecap,post-cap/quantizedoutput,engineflag/budget,caller and renderseq.
Timing behavior remains test6;not a slowdownfix. NextcoldBalanced40 short
race1x then5x,samefiveargs,restore1x,skip8x;inspect actualdiscardedtime and
caller paths beforecorrection. Buildenv/shaders/codegen restored;all old
postpatches passed. No device result/defaultpromotion/release. Identity,
newtoolchain caveat and restorationcommands inTECHNICAL/checkpoint.

October30 test7/log13:engineclamp confirmed active33.333ms,flag2,budget4,
main-loopcaller823AFE64 throughout1380samples.1x~100%engine-time speed;
5x~73.5%,308/480updatesclipped despite~102%incomingtime. Nextscopefix
preservesoriginalelapsedcatch-upbudget separately from120Hzstep under
managed40driving,thenverifyactualengineoutput/host. Priorlog12accounting
mismatch stillrequirescoverage. No sourcefix/newIPA/defaultpromotion yet.

### D-0xx Minimap in the wrong place after a menu change — fixed in 0.4.3 (IPA138, confirmed Oct 29)

Stefan, Oct 27-28 (iPhone, 0.4.2 RC2): the minimap is sometimes drawn in the
wrong position after a menu change; fine in free roam and during the race,
wrong after the race ended. Screenshot `Debug/28 October 2026/IMG_4038.png`.
Likely in the movable/resizable HUD (game_scene_size.cpp, IPA70-85), not
investigated. Oct 29: also seen by a GitHub user after restarting a race
(`Debug/29 October 2026/IMG_4045_user_report_performance.png`), and by
Stefan after leaving the safe house a second time, with Custom HUD off.
Cause (inferred from code, TECHNICAL Oct 29): a rebuilt HUD's minimap at the
old one's address was taken for the old one, so the wide-scene shift was not
applied. Fix in IPA138; Stefan (iPhone, Oct 29): safe house exited twice and a race
finished, minimap stays in place.
