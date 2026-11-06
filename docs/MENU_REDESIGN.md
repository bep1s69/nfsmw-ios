# Menu redesign: groundwork and handoff

Written November 6, 2026 (dev100, branch `dev-0.5`) as groundwork for the 0.6.0
menu redesign (BACKLOG 0.6.0 roadmap item 3). This is the plan to follow; it
does not change the menus. Read AGENTS.md and DEVELOPMENT_PROGRESS.md first.
Propose each visible change to Stefan before building it.

## Stefan's requirements so far

- November 2: the in-game options mirror the launcher 1:1, minus what cannot
  change while the game runs.
- November 6, Display: only two screen shapes, "Fit this screen" and
  "16:9 (Xbox 360)"; resolution choices labelled with real pixels (W×H of
  scene × scale, `ScaleChoiceTitle`). Keep this as it is (TECHNICAL,
  "November 6: dev93 ... Display menu").
- Profiles (Performance: Eco / Balanced / Max) need new wording and a
  behaviour overhaul; what each really does is still open (BACKLOG "Audit
  actual effects of Eco/Balanced/Max profiles").
- Battery mode is to be reworked (planned; details from Stefan still to come).
- November 6 (Stefan): a main focus is making both menus **much prettier**,
  with a **first-launch onboarding** (below) shown to everyone the first time
  they open the new update, and **removing irrelevant settings** altogether,
  including everything for the old (emulated, Vulkan) renderer.
- Keep the PC-style graphics preset idea in mind (BACKLOG "Comprehensive
  PC-style graphics menu and quality presets"), but do not build it as part of
  this redesign unless Stefan asks.

## How the menus work today

Two native UIKit screens. Both are `UITableView`s with a segmented control for
tabs, built from one settings table, saved to `Documents/settings.json`.

**Launcher** (`ios/src/launcher.mm`, 2347 lines, shown before the game window
exists; `Run()` returns the ISO when Play is tapped):
- `Sections()` (line ~349) is the whole settings table: `Section {title,
  footer, options, tab}`, `Option {key, type, title, summary, default,
  choices}`, types switch, choice, text (Extra arguments), link (opens a
  screen).
- 6 tabs (`enum Tab`, `TabTitles()`): Game, Extras, Graphics, Controls, Audio,
  Advanced. The Game tab adds two fixed sections in front (ISO list,
  Achievements).
- Rules spread over helper functions: `EmulatorOnly()` / `NativeOnly()`
  (greyed out per renderer), `BatteryValue()` (values Battery mode forces;
  row says "Set by Battery mode"), `HudDefault()` (locked while Custom HUD is
  off), `Value()` (saved value or default or Battery value), `Arguments()`
  (settings to `--cvar=value` game arguments).
- Nav bar: Reset (left), Play (right). Footer: About (version and build).
- Linked screens: Save manager (`save_manager.mm`), Host or join
  (`multiplayer/lan_setup.mm`), Customize HUD (`hud_editor.mm`), Customize
  touch controls (`touch_controls.mm`, layout editor), Customize keyboard
  (`NFSKeyBindsController`, in launcher.mm), Achievements
  (`NFSAchievementsController`), Extra arguments editor.
- Touch only: no controller navigation in the launcher.

**In-game options** (`ios/src/ingame_options.mm`, 756 lines; a sheet over the
game opened from the gear in menus/pause screens or L3+R3):
- Gets its rows through `launcher.h`: `Groups(keys)` returns the launcher's
  rows grouped by its tab and section. Tabs shown: Extras, Graphics, Controls
  (whatever the listed keys fall into) plus its own Actions tab (Change heat,
  Reset car, Teleport, Auto drive; Debug car customize is compiled out).
- Its own hand-kept lists, which are what drifts:
  1. `Keys()`: the 65 settings it shows.
  2. `NativeOnlyKey()`: a second, shorter copy of the launcher's `NativeOnly`.
  3. `LiveFlags()`: cvar names that apply at once (by game argument name, not
     setting key).
  4. `waitsForLaunch` / `anythingWaits`: special cases for fps cap and MSAA;
     everything else not in `LiveFlags` is "applies at next launch".
- Nav bar: Customize HUD, Touch controls, Keyboard (left), Done (right). On an
  iPhone in landscape this is crowded.
- Controller: D-pad rows, left/right/A change, L1/R1 tabs, B or L3+R3 close.
  Game input is blocked while open (`BlocksGameInput`).

## Problems to fix

1. (Fixed in dev101.) **Four hand-kept lists in the in-game sheet** duplicate facts that belong
   to each setting. A new launcher setting does not appear in game unless
   someone remembers `Keys()` and `LiveFlags()`; this is why "mirror 1:1"
   keeps drifting.
2. **launcher.mm mixes everything**: the settings catalogue, value rules,
   argument building, key binding tables and six view controllers.
3. **Tabs are uneven**: Graphics holds renderer, display, frame rate, battery,
   profiles, HUD and quality; Advanced mixes real choices (Read the ISO in
   pieces) with diagnostics and emulated-renderer switches; Game holds ISO,
   achievements, saves and multiplayer.
4. **Battery mode is a switch that silently locks 13 rows** (`BatteryValue`)
   and also rewrites the fps cap. The rows only say "Set by Battery mode".
5. **Profiles are worded as implementation** ("which CPU cores the game's
   threads ask for").
6. **Live vs next launch is not shown per row** in game until after a change.
7. **Long summaries** (several lines each) make the lists very tall; most
   people need one line plus a details view.
8. **In-game nav bar** has three customize buttons; they belong in the
   Controls / Graphics tabs as rows.
9. **No controller navigation in the launcher** (the in-game sheet has it).

## Proposed structure

Same tabs in both menus, in the same order. The in-game sheet leaves out the
Play tab and anything marked launch-only, and adds Actions.

| Tab | Launcher contents | In game |
|---|---|---|
| Play | ISO, Saves, Achievements, Multiplayer | — |
| Display | Screen shape, Render resolution, Frame rate cap, Show FPS | yes |
| Battery | Battery mode / profile (reworked), 30 fps when warm, 30 fps in menus, 0.75x when hot | yes |
| Graphics | Anti-aliasing, anisotropic, shadows, reflections, post-processing, motion blur, scaling | yes |
| HUD & Controls | Custom HUD + Customize HUD, Touch controls + Customize, Keyboard + Customize, mouse/swipe look | yes (Customize rows replace the nav bar buttons) |
| Gameplay | Today's Extras: Career, Speedbreaker, Police, Quick Race, Weather | yes |
| Audio | Silent mode, Mix others, Stream reset | yes |
| Advanced (or Developer) | What is left after "Settings to remove": diagnostics, Extra arguments | no |
| Actions | — | Pursuit, Driving |

Each row: title, value, a one-line summary; the full text in a details
popover or footer. Status shown on the row, not only after a change: "Set by
Battery mode", "Native renderer only", "Applies at next launch" (in game).

Exact tab names and what goes where are proposals for Stefan to approve.

## Look and feel

Today both menus are stock grouped `UITableView`s with long grey text. Goal:
a menu that looks like part of the game. Proposal for Stefan to approve with
mockups before building:
- Dark theme always (the game is dark), one accent colour, the game's logo or
  a blurred screenshot behind the launcher, large Play button.
- Rows: icon, title, current value on the right, one short line under it;
  the long explanation in a details sheet (info button).
- Tabs as a sidebar on iPad / wide iPhone landscape, a tab bar or scrolling
  chips on narrow screens, instead of a 6-9 segment control.
- Status as small badges ("Battery mode", "Next launch").
- The in-game sheet uses the same components, translucent over the game.
- Controller: visible focus ring, L1/R1 tabs, B back (both menus).

## First-launch onboarding

Shown once to everyone: on a fresh install and on the first launch of the
update that adds it, including existing players. Kept in settings.json as
`onboarding_version` (absent = never seen); Stefan can re-open it from the
launcher ("Set up again"). Existing players keep their settings unless they
choose otherwise on a page. Proposed pages (each skippable):
1. Welcome: what the app is, where the ISO goes (shows "found" when it is).
2. Controls: Touch / Controller / Keyboard and mouse (sets `touch_controls`,
   `keyboard`, `mouse_look`; touch steering style with a picture).
3. Look and performance: a few named starting points that set a group of
   settings at once (for example "Longest battery", "Balanced", "Best
   looking"), with "Keep my current settings" for existing players. Exact
   values come from the profile and Battery mode decisions below.
4. Saves: iCloud sync and import from another device (links to the save
   manager).
5. Done: Play.
Stefan's words "settings based on resets": read here as starting presets
(page 3); to confirm with him.

## Settings to remove

Stefan (November 6): remove everything for the old renderer. The native Metal
renderer is the default (`native_renderer` and `no_vulkan` default true).
Before removing, check and record:
- the launcher falls back to the emulated renderer when a build has no native
  shaders (`native_renderer` summary): every IPA ships them, so make the
  native renderer always on and treat missing shaders as a startup error;
- `one_pass` also sets `nfsmw_render_sin_mosaico` (a game patch, not only
  Vulkan) and `occlusion` sets `occlusion_query_enable`: check whether the
  native path depends on them before fixing their values;
- MSAA (`gpu_sin_msaa`, `gpu_msaa_muestras`) and `swap_post_effect` are the
  emulated renderer's; the native one uses `nfsmw_native_force_msaa` /
  `nfsmw_native_fxaa`.
Rows to remove from the menus (their current default values keep being passed
where something still reads them): `native_renderer`, `no_vulkan`, the whole
Emulated renderer section (`async_submits`, `one_pass`, `edram_fsi`,
`widen_kb`, `occlusion`, `exposure`, `memexport`, `pages`, `mvk_profiling`),
`scaling` (FSR/CAS, emulated only). Removing the Vulkan/MoltenVK code from the
SDK and the build is a separate, larger step (memory and app size gain) and
needs its own plan. Also review for removal or a Developer switch: Diagnostics
(`gpu_capture`, `cost_probe`, `motion_debug`, `heat_scale_test`,
`detailed_log`), `iso_stream`, `audio_starve_reset`, Extra arguments.

## Shared components (to build first, no visible change)

- **Per-setting flags in the catalogue**: add to `Option` something like
  `uint32_t flags` with `kInGame`, `kLive`, `kNativeOnly`, `kEmulatedOnly`,
  `kLaunchOnly`, plus the cvar(s) it produces if needed for `kLive`.
  `BatteryValue` and `HudDefault` can stay tables. Then delete `Keys()`,
  `NativeOnlyKey()`, `LiveFlags()` and the `EmulatorOnly`/`NativeOnly` sets.
  Keep `anythingWaits` working from the argument diff, with the live set
  derived from the flags.
- **One cell builder** (`settings_ui.{h,mm}`): switch / choice (UIMenu
  button) / link / text cells, lock and status text, used by both screens.
  Today each screen builds its own cells (launcher `cellForRowAtIndexPath`
  ~line 1919, in-game ~line 489).
- **Catalogue split**: move `Sections()`, `Value()`, `BatteryValue()`,
  `HudDefault()`, `Arguments()`, `AutoAspect()`/`FitSceneWidth()`/
  `ScaleChoiceTitle()` and the key bind tables to `settings_catalog.{h,mm}`;
  launcher.mm keeps the view controllers. `launcher.h`'s current functions
  (`Rows`, `Groups`, `SettingValue`, `SetByBatteryMode`, `HudLocked`,
  `ArgumentsFor`) keep their signatures so the call sites in
  `ingame_options.mm`, `keyboard_context.cpp`, `ios_main.mm` do not change.
- **Controller focus helper** shared by both screens (the in-game sheet's
  `controllerUp:down:left:right:a:` logic), so the launcher gets controller
  navigation.

## File map

| File | Role |
|---|---|
| `ios/src/settings_catalog.mm` / `.h` | Settings catalogue, flags, value rules, arguments, key bind tables (dev102) |
| `ios/src/launcher.mm` / `.h` | Launcher UI, key binds UI, achievements UI; launcher.h is the in-game sheet's view of the catalogue |
| `ios/src/ingame_options.mm` / `.h` | In-game sheet, gear, L3+R3, controller navigation, live apply, Actions |
| `ios/src/hud_editor.mm` | Customize HUD (both screens) |
| `ios/src/touch_controls.mm` | Touch overlay and its layout editor |
| `ios/src/save_manager.mm` | Save manager screen |
| `ios/src/multiplayer/lan_setup.mm` | Host or join screen |
| `ios/src/battery.mm`, `performance_profile.h` | What Battery mode / caps / profiles do at run time |
| `ios/src/native_renderer.mm` (`NativeSettingsChanged`) | Live graphics settings |
| `ios/src/game_scene_size.cpp` | Screen shape, scene width, HUD |
| `ios/src/game_extra_options.cpp` | Gameplay (Extra Options) cvars |
| `ios/src/keyboard_context.cpp` | Uses the key bind settings |

## Step-by-step plan

Each step is its own commit with the record updated (DEVELOPMENT_PROGRESS,
TECHNICAL, BACKLOG, CHANGELOG when visible). Run
`python3 tools/ios/patch_game_extra_options.py` before every build; build per
DEVELOPMENT_PROGRESS (dev-0.5 against the multiplayer SDK, `build-0.6`).

0. **Baseline**: record the game arguments for default settings and for a
   settings.json with Battery mode on and a few Extras changed (for example
   a small debug log of `ArgumentsFor` at launch). Every refactor step below
   must produce identical arguments and the same in-game row list.
1. **Flags in the catalogue** — DONE in dev101 (November 6). `Option` has
   `flags` (`kInGame`, `kInGameNative`, `kNativeOnly`, `kEmulatedOnly`) and
   `live` (the cvars that apply at once in game, "a,b"). launcher.h exports
   `InGameKeys()`, `InGameNeedsNative()`, `LiveCvars()`; ingame_options.mm
   has no lists of its own. To show a new setting in game: add `kInGame` and
   its live cvars on the row; nothing else.
1b. **Remove the old renderer's settings** (section above).
2. **Split the catalogue** — DONE in dev102 (November 6).
   `ios/src/settings_catalog.{h,mm}` (namespace `nfsmw::catalog`): option
   types and flags, `Sections()`, value rules, screen shape/resolution titles,
   key bind tables, settings.json, `Arguments()`. launcher.mm (1241 lines,
   was 2347) keeps the view controllers and launcher.h's functions.
3. **Shared cell builder** used by both screens (no visible change, or only
   identical-looking cells).
4. **Look and feel + new tab layout** (mockups to Stefan first), then the
   **onboarding** on the same components. New tab layout in the launcher, then the same in the in-game sheet;
   customize rows replace the in-game nav bar buttons; per-row status text;
   short summaries with details. Show Stefan screenshots before building the
   IPA.
5. **Controller navigation in the launcher** using the shared helper.
6. **Profiles and Battery mode**: only after Stefan decides the wording and
   behaviour (and after the profile audit). Leave the switch working until
   then.
7. Device check on iPhone and iPad (touch, controller, keyboard), both menus,
   Battery mode on/off, native and emulated renderer.

## Open questions for Stefan

- Tab names and grouping above.
- Profiles: new names and what each should do.
- Battery mode: a switch, a preset next to Balanced/Quality, or a profile.
- Should Extra arguments and Diagnostics stay visible to everyone, or move
  behind a "Developer" switch?
- Onboarding: what "settings based on resets" means (starting presets?), and
  which pages he wants.
- Look: approve mockups before any build.

## Settings inventory (generated from launcher.mm, dev100)

Flags (now the `flags` field, dev101): *in game* = `kInGame`; *native only* / *emulated only* =
greyed with the other renderer; *Battery mode* = forced by `BatteryValue`.
Live vs next launch: see `LiveFlags()` and `waitsForLaunch` in
ingame_options.mm (by cvar name).

| Tab | Section | Key | Type | Title | Flags |
|---|---|---|---|---|---|
| Game | Saves | `saves` | link | Save manager |  |
| Game | Multiplayer | `multiplayer_setup` | link | Host or join a game |  |
| Extras | Career | `marker_count` | choice | Markers after beating a rival | in game |
| Extras | Career | `car_limit` | choice | Cars you can buy | in game |
| Extras | Career | `no_rev_limiter` | switch | No rev limiter | in game |
| Extras | Career | `showcase_unlimited` | switch | Unlimited showcase camera | in game |
| Extras | Career | `unlock_all_things` | switch | Unlock everything | in game |
| Extras | Career | `skip_career_intro` | switch | Skip the career intro | in game |
| Extras | Career | `skip_movies` | switch | Skip movies | in game |
| Extras | Career | `old_bridge` | switch | Open the road to the Old Bridge |  |
| Extras | Career | `impound_strikes` | choice | Impound strikes of a new car | in game |
| Extras | Career | `impound_strikes_max` | choice | Most impound strikes | in game |
| Extras | Speedbreaker | `infinite_speedbreaker` | switch | Infinite Speedbreaker | in game |
| Extras | Speedbreaker | `infinite_nos` | switch | Infinite nitrous | in game |
| Extras | Speedbreaker | `sb_recharge_time` | choice | Refill time | in game |
| Extras | Speedbreaker | `sb_recharge_speed` | choice | Refill speed | in game |
| Extras | Speedbreaker | `sb_mass` | choice | Weight while slowed | in game |
| Extras | Police | `no_cops` | switch | No cops | in game |
| Extras | Police | `show_non_pursuit_cops` | switch | Show all cops on the minimap | in game |
| Extras | Police | `heat_override` | switch | Heat level override | in game |
| Extras | Police | `heat_min` | choice | Lowest heat | in game |
| Extras | Police | `heat_max` | choice | Highest heat | in game |
| Extras | Police | `speeding_limit` | choice | Speeding | in game |
| Extras | Police | `excessive_speeding_limit` | choice | Excessive speeding | in game |
| Extras | Police | `reckless_driving_limit` | choice | Reckless driving | in game |
| Extras | Quick Race | `laps_max` | choice | Most laps | in game |
| Extras | Quick Race | `opponents_max` | choice | Most opponents (experimental) | in game |
| Extras | Quick Race | `laps_min` | choice | Fewest laps | in game |
| Extras | Quick Race | `opponents_min` | choice | Fewest opponents | in game |
| Extras | Quick Race | `random_laps_max` | choice | Random race: most laps | in game |
| Extras | Quick Race | `random_opponents_max` | choice | Random race: most opponents (experimental) | in game |
| Extras | Quick Race | `world_animation_speed` | choice | World animation speed | in game |
| Extras | Quick Race | `nos_trail_repeat` | choice | Nitrous trail length | in game |
| Extras | Quick Race | `game_speed` | choice | Game speed (experimental) | in game |
| Extras | Quick Race | `traffic_low` | choice | Traffic at Low | in game |
| Extras | Quick Race | `traffic_medium` | choice | Traffic at Medium | in game |
| Extras | Quick Race | `traffic_high` | choice | Traffic at High | in game |
| Extras | Weather | `always_rain` | switch | Always rain | in game |
| Extras | Weather | `rain_amount` | choice | Rain amount | in game |
| Extras | Weather | `rain_intensity` | choice | Rain intensity | in game |
| Extras | Weather | `rain_drop_size` | choice | Drop size | in game |
| Extras | Weather | `rain_crossing` | choice | Rain drift | in game |
| Extras | Weather | `rain_fall_speed` | choice | Rain fall speed | in game |
| Extras | Weather | `rain_gravity` | choice | Rain gravity | in game |
| Extras | Weather | `road_reflection` | choice | Wet road reflection | in game |
| Graphics | Renderer | `native_renderer` | switch | Native Metal renderer |  |
| Graphics | Renderer | `no_vulkan` | switch | No emulated renderer (no Vulkan) | native only |
| Graphics | Renderer | `async_pipelines` | switch | Compile pipelines in the background | native only |
| Graphics | Display | `aspect` | choice | Screen shape |  |
| Graphics | Display | `scale` | choice | Render resolution | in game, Battery mode |
| Graphics | Display | `fps_cap` | choice | Frame rate cap | in game |
| Graphics | Display | `auto_cap` | switch | 30 fps when warm or on Low Power | in game, Battery mode |
| Graphics | Display | `menu_cap` | switch | 30 fps in menus and pause | in game, Battery mode |
| Graphics | Display | `heat_scale` | switch | 0.75x when hot | in game, native only, Battery mode |
| Graphics | Display | `battery_mode` | switch | Battery mode | in game, native only |
| Graphics | Display | `performance_mode` | choice | Performance | in game |
| Graphics | Display | `show_fps` | switch | Show FPS |  |
| Graphics | HUD | `hud_custom` | switch | Custom HUD | in game |
| Graphics | HUD | `hud_editor` | link | Customize HUD |  |
| Graphics | Graphics | `antialiasing` | choice | Anti-aliasing | in game, Battery mode |
| Graphics | Graphics | `anisotropic` | choice | Anisotropic filtering | Battery mode |
| Graphics | Graphics | `shadow_size` | choice | Shadow quality | Battery mode |
| Graphics | Graphics | `shadow_scale` | choice | Shadow map drawing size | in game, native only, Battery mode |
| Graphics | Graphics | `reflection_rate` | choice | Car reflections | in game, native only, Battery mode |
| Graphics | Graphics | `reflection_size` | choice | Reflection and mirror resolution | in game, native only, Battery mode |
| Graphics | Graphics | `postprocessing` | switch | Post-processing | in game, Battery mode |
| Graphics | Graphics | `motion_blur` | switch | Motion blur | in game, Battery mode |
| Graphics | Graphics | `scaling` | choice | Scaling to the screen | emulated only, Battery mode |
| Controls | Touch controls | `touch_controls` | switch | Touch controls |  |
| Controls | Touch controls | `touch_layout` | link | Customize touch controls |  |
| Controls | Touch controls | `touch_steering` | choice | Steering | in game |
| Controls | Touch controls | `touch_idle_opacity` | choice | Dim when not touched | in game |
| Controls | Touch controls | `touch_menu_gestures` | switch | Swipe and tap in menus |  |
| Controls | Touch controls | `touch_menu_empty_accept` | switch | Tap and swipe anywhere | in game |
| Controls | Touch controls | `touch_menu_two_finger_back` | switch | Two-finger tap to go back | in game |
| Controls | Touch controls | `touch_menu_invert` | switch | Invert menu swipes | in game |
| Controls | Touch controls | `touch_look` | switch | Swipe to look around | in game |
| Controls | Touch controls | `touch_look_speed` | choice | Swipe look speed | in game |
| Controls | Touch controls | `touch_auto_layout` | switch | Switch layouts by themselves |  |
| Controls | Keyboard | `keyboard` | switch | Keyboard controls |  |
| Controls | Keyboard | `mouse_look` | switch | Mouse look |  |
| Controls | Keyboard | `mouse_look_speed` | choice | Mouse look speed | in game |
| Controls | Keyboard | `mouse_look_invert` | switch | Invert mouse look | in game |
| Controls | Keyboard | `keyboard_bindings` | link | Customize keyboard controls |  |
| Audio | Audio | `audio_silent_mode` | switch | Play sound in silent mode |  |
| Audio | Audio | `audio_mix_others` | switch | Keep other music playing |  |
| Audio | Audio | `audio_starve_reset` | switch | Audio stream reset |  |
| Advanced | Performance | `iso_stream` | switch | Read the ISO in pieces |  |
| Advanced | Emulated renderer | `async_submits` | switch | Asynchronous GPU submission | emulated only |
| Advanced | Emulated renderer | `one_pass` | switch | Single-pass scene | emulated only |
| Advanced | Emulated renderer | `edram_fsi` | switch | EDRAM in the pixel shader (experimental) | emulated only |
| Advanced | Emulated renderer | `widen_kb` | choice | CPU write invalidation (experimental) | emulated only |
| Advanced | Emulated renderer | `occlusion` | switch | Occlusion queries | emulated only |
| Advanced | Emulated renderer | `exposure` | switch | Accurate exposure | emulated only |
| Advanced | Emulated renderer | `memexport` | switch | Memexport readback | emulated only |
| Advanced | Emulated renderer | `pages` | switch | Refresh GPU-written pages | emulated only |
| Advanced | Emulated renderer | `mvk_profiling` | switch | MoltenVK profiling | emulated only |
| Advanced | Diagnostics | `logging` | switch | Logging |  |
| Advanced | Diagnostics | `detailed_log` | switch | Detailed log |  |
| Advanced | Diagnostics | `gpu_capture` | switch | GPU frame capture (experimental) |  |
| Advanced | Diagnostics | `cost_probe` | switch | GPU cost per shader | native only |
| Advanced | Diagnostics | `motion_debug` | switch | Show motion vectors | native only |
| Advanced | Diagnostics | `heat_scale_test` | switch | Test 0.75x when hot | native only |
| Advanced | Diagnostics | `extra_args` | text | Extra arguments |  |
