# Changelog

## Unreleased

- **Options while playing.** In a menu or the pause screen, tap the gear at
  the top right (or press L3+R3 on a controller) to change the render
  resolution, MetalFX, the 30/60 fps cap, anti-aliasing and the battery
  settings without restarting. Settings that need a restart (40/120 fps, MSAA)
  are marked "next launch".

- **HUD size and position.** New HUD settings (launcher Graphics tab and the
  options while playing): the race HUD's size and safe zone (how close to
  the screen's edges it sits), and the minimap, the
  speedometer and the race info (standings, laps, times) moved left, right,
  up or down on their own.

- **Post-processing switch fixed.** Turning it off now really removes the
  colour filter, bloom and vignette; it can also be changed while playing.

- **Battery mode now caps the game at 30 fps**, along with its other savings.

- **New setting: reflection and mirror resolution.** The reflections on the
  cars and the rear-view mirror are drawn at the Xbox 360's size (the default,
  lighter) or follow the render resolution (a sharper mirror).

- **About a quarter less battery drain while playing**, with the same picture,
  resolution and frame rate: the game's threads ask iOS for a lower priority,
  so the CPU runs at cheaper speeds (measured on an iPad Pro M4 at 1.5x / 60 fps).
  On by default on devices with at least 6 efficiency cores (M-series iPads);
  off on iPhones, where it made the game stutter.
  Override with `--ios_utility_qos=true|false --ios_utility_qos_guest=true|false`.

- **Smoother police pursuits on iPhones.** Pursuits dropped to about 22 fps
  because some game threads stayed on the slow cores when the game sped the
  others up; now they all speed up together. Turn off with
  `--ios_adaptive_qos_workers=false`.
- **Less battery and heat on iPhones in pursuits:** the game and GPU threads now
  sleep while they wait instead of checking hundreds of times a second. An
  iPhone 17 Pro Max police chase at 1x / 40 fps went from about 30 to about 22 %
  battery an hour, cooler, still at 40 fps (one test so far). Undo with
  `--ios_ring_wait_ms=1 --ios_cp_idle_spins=64`.
- **The sun no longer flickers or shines through buildings and tunnels** with
  the native renderer: it counts how much of the sun is visible again. Turn off
  with `--nfsmw_native_occlusion=false`.
<!-- Not for release as they stand (October 24 tests: no battery saving):
     --ios_display_match_cap (screen at the cap's rate) and the IPA49 gentler
     boost (--ios_adaptive_qos_ipa48 restores the tested one). See BACKLOG. -->

## 0.3.0

- **Fixes for freezes.** The freeze after leaving the safehouse (and in some
  tollbooth races): the picture stopped while music and controls went on. And
  a rare black-screen hang at boot.
- **iOS 26 works with the native renderer.** It froze on the last movie frame
  or showed a black screen with only sound and controls: the game's shaders
  were built for iOS 27 only.
- **Invisible cars in career with Black Edition on.** Black Edition needs more
  car records than the game's table holds, and the extra ones were not saved
  with the career. They are now kept beside the save (from this version on:
  careers already affected keep their invisible cars).
- **HDMI and AirPlay.** An external display shows the game by itself, full
  size, while the phone keeps the touch controls.
- **MetalFX** (native renderer): temporal upscaling with the game's motion,
  to the screen, lighter, or anti-aliasing only. FXAA, MSAA where the game draws
  without it, and the game's own mip levels.
- **Battery and heat.** Battery mode (lower resolution, half-size shadows, car
  reflections updated less often), 30 fps in menus and pause, 30 fps when warm
  or on Low Power, 0.75x when hot, each also on its own. Less CPU spent waiting,
  no idle 120 Hz screen refresh, steadier frame pacing.
- **Touch controls switch by themselves** between the Pad layout in menus and
  the Drive layout while driving (with a small D-pad for free roam).
- **11" iPads**: 4:3 fills the screen. "Stretch to full screen" is gone.
- Extra Options: Quick Race laps, opponents, traffic and weather.
- Save manager: saves, backups, export and import, iCloud Drive sync, cash and
  bounty per save.

### Known issues

- Skipping a movie can turn its last frame red for a moment.

## 0.2.0

- **Native Metal renderer, on by default.** The game is drawn by its own
  shaders translated to Metal instead of an emulated Xbox 360 GPU: much faster,
  with a render resolution setting (1x to 2x, or the screen's own).
- **No Vulkan when the native renderer is on.** MoltenVK is not started at all:
  about 700 MB less memory in a race, faster start. The movies are drawn
  natively too.
- Older GPUs: runs on A16 iPhones (iPhone 14 Pro / Pro Max) and M1 iPads, which
  have no DXT texture support in Metal (expanded on the GPU) and showed a black
  3D scene before.
- Audio: clean menu sounds, low latency, and no more cut-outs in police chases.
- Keyboard controls (Magic Keyboard or any hardware keyboard), customizable.
- Customizable touch controls: move and resize every control, overall size
  and opacity, for both the Pad and the Drive layouts.
- New launcher with tabs (Game, Graphics, Controls, Audio, Advanced); settings
  only the emulated renderer uses are greyed out while the native one draws;
  the version and build are shown at the bottom.
- Graphics fixes: tuning shop car reflections, mirror, shadows, reflections,
  movies kept at 16:9 on wide screens; anisotropic filtering, MSAA and a shadow
  quality setting.
- Extra Options: Skip movies.
- Display Zoom (iPad "More Space") no longer flickers.

## 0.1.0 (first release)

The first public release of the iOS port. Built from the USA Xbox 360 edition.

- The whole game, natively on iPhone and iPad (iOS / iPadOS 26+), installed
  with SideStore and LiveContainer.
- Settings screen before the game: ISO selection, achievement list, Extra
  Options, display, touch controls, graphics, advanced and logging settings.
- Black Edition content, with a fix for the career freeze it caused (the game's
  record pool enlarged from 75 to 150 entries).
- Extra Options ports: selectable marker count after a rival (1-6), purchased
  car limit (1-25), Old Bridge road opened.
- Frame rate caps 30, 40, 60 and 120, paced to the display (ProMotion at 40 and
  120).
- Aspect ratios: 16:9; 4:3 HD and SD with the game's own 4:3 HUD and a sharper
  960x720 scene; 19.5:9 with a wider view and the HUD at the screen edges.
- Touch controls: full gamepad and a driving layout (with look back), switched
  at the top of the screen; hidden automatically with a controller.
- Controller support (Xbox, PlayStation, MFi).
- App switching, screenshots and Control Center handled without losing the
  game.
- GPU emulation performance work for MoltenVK: batched uploads and occlusion
  queries, cheaper texture invalidation, descriptor reuse, shader contraction,
  limited resolve readback, display-locked vblank.
- A Logging switch to turn all logs off.
