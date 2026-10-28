# Changelog

## 0.4.2

- **"Appears to be damaged" careers load.** A career saved on another device
  or install carries another player ID, and the game refused it as damaged
  although the file was fine. It now loads, and is saved with this device's
  ID from then on.

- **Black Edition cars no longer invisible after loading a career.** The
  extra car records kept beside a save were only put back if the career
  matched them exactly, so one changed record left the cars invisible and
  without their upgrades. They now come back whenever the records that need
  them match. Thanks to Lunquell for reporting both (issue 8) and sending
  the save files and logs that found them.

- **Smooth motion at 60 fps.** The game world and camera could judder, as if
  running at 30 fps, even though the fps counter showed a steady 60: worst in
  places you visit for the first time and right after restarting the device.
  The game timed each frame unevenly and moved the world by those uneven
  steps while the screen showed the frames evenly. Each frame now moves the
  world by exactly one screen refresh.

- **Smoother 40 fps.** At the 40 fps cap the world moved in alternating short
  and long steps (the game's 60 Hz steps do not divide into 40), so it looked
  closer to 30 than the mirror and the map. The 40 cap now runs the game's
  simulation at 120 Hz: three even steps per frame.

- **Battery mode lets you choose 30 or 40 fps** (it always forced 30).

- **Custom HUD switch.** The HUD size and position settings now sit behind
  one Custom HUD switch, off by default: the game's own HUD unless you turn
  it on (your earlier changes come back when you do).

- **No more stutter from the touch controls.** Steering or pressing the
  on-screen controls made a frame arrive one refresh late, so donuts and
  quick steering stuttered. The controls are now drawn as part of the game's
  picture.

- **extra_args.txt saved as UTF-16 now works.** A file that went through
  the Mac (TextEdit, the clipboard) could be UTF-16, and every argument in it
  was ignored.

## 0.4.1

- **Engine sound no longer fades.** The game's sound engine dropped the
  engine, turbo and skid sounds when its mixing thread was held up for a
  moment, and they only came back at the next gear change. That no longer
  happens. Fix ported from SpeedBreaker (SpeedBreakerProject/speedbreaker).

- **Steadier 60 fps.** The thread that keeps the game's 60 Hz timing now
  runs at real-time priority, so it wakes on time; frame timing on 120 Hz
  screens turns itself off if the screen does not keep to it. From
  SpeedBreaker.

- **Accurate exposure Off is respected.** Turning it off in the launcher
  was undone at startup (GitHub issue #5); settings you choose are now kept
  even when they match the default.

- **iOS 18, experimental.** The app now installs on iOS / iPadOS 18 (it
  needed 26). Nobody has tested it on iOS 18 yet: reports welcome.

## 0.4.0

- **Import PC saves.** The save manager's Import also takes a save from the
  PC game (v1.3, the file inside the profile's folder, or a .zip of it): it
  is converted to the Xbox 360 layout. Needs one career of this game on the
  device already (its options are reused).

- **Motion blur switch.** Motion blur can be turned off in the launcher and
  in the in-game options; off, the picture stays sharp when driving fast.

- **Save sync between devices fixed.** Part of a Black Edition career was
  kept in a separate file the save manager ignored, so a newer save (for
  example one more challenge event) did not show as newer on the other
  device, and could arrive incomplete. That file now travels with the save
  everywhere, and saves are copied to your iCloud Drive folder shortly after
  the game saves, not only when the launcher opens.

- **Delete saves from iCloud.** A save that is only in iCloud can now be
  deleted from the save manager (tap it), instead of only downloaded.

- **Simpler save manager.** One list of careers. Each shows its cash, bounty
  and when and on which device it was last saved, including careers only in
  iCloud. When another device has a newer save, the career says so and
  tapping it offers "Use the save from iPad" first. Sync now is the button
  at the top right.

- **Import saves from the internet.** The save manager's Import button takes
  an Xbox 360 save file, a Xenia save folder or .zip, a .zip exported from
  the app, or the bare save file.

- **Achievements follow you between devices.** With an iCloud Drive folder
  chosen, an achievement unlocked on one device now shows as unlocked on the
  others too.

- **Black Edition content now actually turns on.** The switch set the wrong
  byte of the game's memory, so the content stayed hidden. Now the 70th
  Challenge Series event (the Camaro) and the Black Edition cars in Quick
  Race appear, and starting a career works. It is always on now: the
  launcher no longer has a switch for it.

- **Smoother frame pacing with the FPS counter on.** Each counter update
  delayed a frame, a small stutter up to twice a second; the counter is now
  drawn into the game's picture (a square dark box). At the 60 fps cap frames
  are also made in step with the screen's refresh, as at 30 and 40.

- **120 Hz simulation switch.** The game can move its world 120 times a
  second instead of 60 (Advanced tab, off by default; always on with the
  120 fps cap).

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
