# NFSMW Recompiled for iOS

**Need for Speed: Most Wanted (2005), Xbox 360, running natively on iPhone and iPad.**

**Requires iOS / iPadOS 26 or later; iOS / iPadOS 18 is experimental (untested).**

This is not an emulator. The game's PowerPC code is translated ahead of time into
C++ and compiled for Apple's arm64 chips with the
[ReXGlue SDK](https://github.com/rexglue/rexglue-sdk). The SDK supplies everything
around the game's code: the Xbox 360 kernel calls, the file system, audio and
input. The picture is drawn by the game's own shaders translated to **Metal**
(the native renderer, on by default); the SDK's emulated Xenos GPU on Vulkan,
through MoltenVK, is still there as a fallback.

> **You need your own copy of the game.** The app on the
> [Releases](https://github.com/bep1s69/nfsmw-ios/releases) page contains no game
> files: no textures, models, sounds, music, videos or tracks. It reads all of
> them from your own ISO of the USA Xbox 360 game. This repository contains no
> game files and no translated game code. See [Legal](#legal).

Version **0.4.2** (see [CHANGELOG.md](CHANGELOG.md) for what changed in each
release). The game is playable start to finish, and we are getting closer to a
1.0 release.

---

## Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installing and first start](#installing-and-first-start)
- [Saves](#saves)
- [Building it yourself](#building-it-yourself)
- [The launcher and in-game options](#the-launcher-and-in-game-options)
- [Controls](#controls)
- [Performance and battery](#performance-and-battery)
- [Known issues and limitations](#known-issues-and-limitations)
- [Planned](#planned)
- [Feedback](#feedback)
- [How it works](#how-it-works)
- [Credits](#credits)
- [Legal](#legal)

## What it does

- **The whole game**: career, quick races, challenge series, pursuits, free roam,
  saves, achievements. **Black Edition content** is always on: its cars in
  Quick Race and the 70th Challenge Series event.
- **Native Metal renderer** with a render resolution setting (1x to 2x, or the
  screen's own), **MetalFX** upscaling or anti-aliasing, FXAA and MSAA.
- **Frame rate caps of 30, 40, 60 and 120** (40 and 120 use the 120 Hz
  ProMotion display).
- **Aspect ratios**: 16:9; the game's own **4:3** mode at 960x720 instead of
  its 640x480; and **19.5:9** (iPhone) with a wider view and the HUD at the
  screen edges.
- **A launcher before the game starts** and **options while playing** (the gear
  at the top right, or L3+R3): resolution, MetalFX, anti-aliasing, motion blur,
  post-processing, HUD size and position, battery settings and more, many of
  them changed without restarting.
- **A save manager**: careers with their cash and bounty, backups, export and
  import (including **Xbox 360 and PC saves**), and **iCloud Drive sync**
  between your devices, achievements included.
- **Extra Options**, ported from the PC mod: markers after beating a Blacklist
  rival (1-6), cars you can buy (1-25), the Old Bridge road, Quick Race laps,
  opponents, traffic and weather, skip movies.
- **Touch controls**: a gamepad layout for menus and a driving layout, switched
  automatically; every control can be moved and resized. They hide themselves
  when a controller connects.
- **Controllers** (Xbox, PlayStation, MFi) and **keyboards** (customizable).
- **External displays** (HDMI, AirPlay): the game alone on the big screen, the
  touch controls on the device.
- **Battery mode** and automatic savings when the device is warm or on Low
  Power Mode.
- Survives app switching, screenshots and Control Center.

## Requirements

**The game**: an ISO of *Need for Speed: Most Wanted* for Xbox 360, **USA
edition** (title ID `454107D9`), dumped from your own disc. Other editions are
not supported by the iOS build yet.

**To play**: an iPhone or iPad on **iOS / iPadOS 26 or later**. iOS / iPadOS 18 is
experimental since 0.4.1: the app installs there, but nobody has tested it yet;
reports welcome. Tested on an
iPad Pro M4 and an iPhone 17 Pro Max; A16 iPhones (iPhone 14 Pro / Pro Max) and
M1 iPads also run it. Install with [SideStore](https://sidestore.io) and
[LiveContainer](https://github.com/LiveContainer/LiveContainer), no paid
developer account needed. Reports from other devices are very welcome (see
[Feedback](#feedback)).

**To build it yourself** (optional; a Mac is required):

| What | Notes |
|---|---|
| A Mac with Apple Silicon or Intel | macOS with **Xcode 27** installed and selected (`sudo xcode-select -s /Applications/Xcode.app`), license accepted |
| `brew install cmake ninja` | CMake 3.25 or newer |
| Python 3.9+ and Git | For the scripts |
| ~25 GB free disk space, 16 GB RAM recommended | The SDK, the generated code and the build |

## Installing and first start

1. Download `NFS-Most-Wanted-<version>.ipa` from the
   [Releases](https://github.com/bep1s69/nfsmw-ios/releases) page (or
   [build it yourself](#building-it-yourself)).
2. Import it into LiveContainer (LiveContainer signs it with its own
   certificate). Open the app once.
3. Copy your **ISO** into the app's `Documents` folder with the Files app or
   Finder. Inside LiveContainer that is LiveContainer's folder,
   `Data/Application/<the app's folder>/Documents`.
4. Open the app again: the launcher shows the ISO it found. Press **Play**.

What the app keeps in its `Documents` folder:

| | |
|---|---|
| `*.iso` | The game (with more than one, the launcher lets you pick) |
| `data/` | Your saves and the game's settings |
| `settings.json` | The launcher's choices |
| `achievements/` | The achievement list and icons the launcher shows |
| `logs/nfsmw.log`, `logs/boot.txt` | The log and the startup trace (Advanced > Logging) |
| `extra_args.txt` | Optional: extra options, one per line, for testing |

## Saves

The save manager (in the launcher) lists your careers with their cash, bounty,
and when and on which device each was last saved.

- **Sync between devices**: choose a folder in your iCloud Drive and saves are
  copied there shortly after the game saves. When another device has a newer
  save, the career says so and offers to use it. Achievements follow too.
- **Import**: an Xbox 360 save file, a Xenia save folder or .zip, a .zip
  exported from the app, or a **PC save** (v1.3, converted to the Xbox 360
  layout; needs one career of this game on the device already).
- **Backups and export**, and deleting saves, including ones only in iCloud.

## Building it yourself

To continue development, start with
[Development progress](docs/DEVELOPMENT_PROGRESS.md): the current checkpoint,
working rules, build procedure and backlog.

Clone this repository next to where the SDK will go (the SDK is prepared in
`../rexglue-sdk-ios`, beside the repository):

```sh
git clone https://github.com/bep1s69/nfsmw-ios.git
cd nfsmw-ios

# 1. The SDK: clones ReXGlue at the pinned version, applies this project's
#    patches and fetches MoltenVK. Once.
python3 tools/ios/prepare_sdk.py

# 2. The game's executable, from your ISO, into assets/game_root/default.xex
python3 tools/fase1_extraer.py "/path/to/your/NFSMW-USA.iso" --solo-xex

# 3. The game's code, translated to C++ into ios/generated/ (a few minutes)
python3 tools/ios/generate_code.py

# 4. The app
cd ios
cmake --preset ios
cmake --build --preset ios --target ipa      # -> ios/build/NFSMW.ipa
```

The first build takes a while (on an M-series Mac, 20-40 minutes): the whole SDK
and 133 generated files, each of which can take more than 2 GB of RAM to
compile. Later builds only recompile what changed. The build folder is
`~/Library/Caches/nfsmw-ios/build`, outside the repository on purpose (iCloud
Drive tags files in `~/Documents` with attributes that `codesign` refuses).

Everything the scripts do, and why, is in [docs/TECHNICAL.md](docs/TECHNICAL.md).

## The launcher and in-game options

The launcher has six tabs: **Game**, **Extras**, **Graphics**, **Controls**,
**Audio** and **Advanced**. Every option has a short explanation on screen, and
the defaults suit normal play. Settings only the emulated renderer uses are
greyed out while the native one draws. **Advanced** holds the GPU and
performance switches for testing; leave them at their defaults unless you are
testing something.

While playing, in a menu or the pause screen, tap the gear at the top right (or
press L3+R3 on a controller) to change the render resolution, MetalFX, the
30/60 fps cap, anti-aliasing, motion blur, post-processing, the HUD and the
battery settings. Settings that need a restart (40/120 fps, MSAA) are marked
"next launch".

## Controls

With a controller, the game's own Xbox 360 controls (control type 1):

| Action | Button | Action | Button |
|---|---|---|---|
| Accelerate | RT | Brake / reverse | LT |
| Steer | Left stick | Shift up / down | Right stick up / down |
| Nitrous | B | E-brake | A |
| Speedbreaker | X | Look back | LB |
| Change camera | RB | Reset car | Back |
| Pause | Start | Options while playing | L3+R3 |

On the touch screen the layout switches by itself: the gamepad in menus, the
driving layout (steering, pedals, nitrous, speedbreaker, handbrake, gears,
camera, look back, reset, pause) while driving, with a small D-pad in free
roam. Every control can be moved and resized, with an overall size and
opacity, in the Controls tab. Keyboard keys can be changed there too.

## Performance and battery

On an **iPad Pro M4** and an **iPhone 17 Pro Max** the game holds **60 fps**
in nearly all of the game at 1x. The 30 and 40 fps
caps are smooth and paced to the display. Higher render resolutions and the
120 fps cap are heavier.

Battery work in 0.3.0 and 0.4.0: Battery mode (30 fps, lower resolution, lighter
shadows and reflections), 30 fps in menus and pause, 30 fps when warm or on Low
Power Mode, and lower thread priorities that cut the drain while playing by
about a quarter on M-series iPads. On iPhones, the game's threads now sleep
while they wait, so pursuits use less battery and run cooler.

## Known issues and limitations

- **USA edition only** for now (the address tables for other editions exist in
  `tools/ediciones/`, but the iOS-specific game patches are written for USA).
- **60 fps frame pacing** on the iPad is not perfectly even yet; turning off
  motion blur or post-processing helps.
- **120 fps cap**: not a stable 120 in heavy parts of races. The **120 Hz
  simulation** switch (Advanced, off by default) did not remove the judder at
  60 fps.
- **HUD and scene size** can be wrong on the iPad in a few places (race finish,
  some cutscene overlays and pop-ups).
- **Audio**: small crackles on AirPods, mostly in police radio chatter; the
  engine sound can occasionally almost disappear.
- Skipping a movie can turn its last frame red for a moment.
- **No Xbox Live** (online modes, leaderboards). The game's single-player modes
  are all there.
- English only (the language of the USA edition).

## Planned

In no particular order, and without promises:

- **0.5.0**: more **Extra Options** and **Widescreen Fix** features, and
  features from PC mods.
- Even **60 fps** frame pacing, then a stable **120 fps** and a proper higher
  **simulation rate** (like the Widescreen Fix's SimRate).
- More battery savings.
- Support for more game **editions**.

## Feedback

Reports are what will make it better:

- **Your device** (model, iOS version) and whether the game runs.
- **Performance**: the frame rate in menus, races and pursuits, with the
  settings you used (turn on the FPS counter).
- **Problems**: what happened and where, ideally with the log
  (`Documents/logs/nfsmw.log`, with Advanced > Logging on).

Open an [issue](https://github.com/bep1s69/nfsmw-ios/issues) with them.

## How it works

[docs/TECHNICAL.md](docs/TECHNICAL.md) describes the port in detail: how the SDK
is prepared and patched for iOS (every patch, what it changes and why, with the
measurements behind it), the guest memory on iOS, the app's lifecycle, the
native Metal renderer, the touch controls, the 4:3 and 19.5:9 modes, the Extra
Options ports, and the Black Edition career fix.

Layout of this repository:

| | |
|---|---|
| `ios/` | The iOS app: `src/` (launcher, touch controls, audio, game hooks, iOS fixes), the CMake build, `Info.plist` |
| `common/` | The game-side code and code-generator configuration shared with the original project (`src/`, `codegen/`) |
| `tools/ios/` | Preparing the SDK for iOS, generating the code, and every iOS patch to the SDK and the generated code |
| `tools/parche_*.py`, `tools/preparar_sdk.py` | The original project's patches to the SDK, which the iOS build applies first |
| `tools/ediciones/` | Edition detection and the address tables between editions |
| `tools/fase1_extraer.py` | Extracts `default.xex` from an ISO |

Much of this project was written with an AI coding assistant (Claude Code),
directed and tested on real devices by its maintainer. The technical document
records what was measured; trust the numbers, and review the code before
reusing it.

## Credits

This port stands on a lot of other people's work.

**The projects it comes from**

- [victorgbd/NFSMW-Recompiled-Mobile](https://github.com/victorgbd/NFSMW-Recompiled-Mobile):
  the Android port this iOS port started from, with its SDK patches, its game
  hooks and its edition tables.
- [madelrandel-blip/NFSMW-Recompiled](https://github.com/madelrandel-blip/NFSMW-Recompiled):
  the original recompilation of the game.
- [StevensND/nfsmw-nx](https://github.com/StevensND/nfsmw-nx): the Switch port;
  the single-pass scene renderer hook comes from it.

**What it is built on**

- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) by Tom Clay, and
  [Xenia](https://xenia.jp/), the Xbox 360 emulator it descends from.
- [XenonRecomp](https://github.com/hedge-dev/XenonRecomp): the static
  recompilation approach.
- [MoltenVK](https://github.com/KhronosGroup/MoltenVK) (Vulkan on Metal),
  [SDL3](https://libsdl.org), and the libraries the SDK bundles (FFmpeg,
  glslang, SPIRV-Tools, spdlog, fmt and others), each under its own license.
- [hells-gate-recomp-android](https://github.com/deivid22srk/hells-gate-recomp-android)
  by deivid22srk: SDK patches for arm64, downloaded at build time (they declare
  no license, so they are not included here).

**Mods it ports features from**

- [Extra Options](https://nfsmods.xyz/mod/43) by ExOptsTeam
  ([source](https://github.com/ExOptsTeam/NFSMWExOpts)).
- [Widescreen Fix](https://github.com/ThirteenAG/WidescreenFixesPack) by
  ThirteenAG: the reference for the widescreen HUD and the simulation rate.
- [NFS MW Save Editor](https://github.com/sprintstate/nfs-mw-save-editor) by
  sprintstate (GPL-3.0): the PC and Xbox 360 save layouts behind PC save
  import, with the [nfsmw decompilation](https://github.com/dbalatoni13/nfsmw)
  (CC0) for the car database.

**Testing and bug reports**

- [Lunquell](https://github.com/Lunquell): reported the "appears to be
  damaged" career bug ([issue 8](https://github.com/bep1s69/nfsmw-ios/issues/8))
  and sent the save, its side file and the logs that found it.

**Installing**

- [SideStore](https://sidestore.io) and
  [LiveContainer](https://github.com/LiveContainer/LiveContainer).

## Legal

**What this repository contains**: only this project's own code,
configuration, scripts and documentation. No game files, no `default.xex`, and
not the C++ the code generator produces from the game. `.gitignore` keeps all
of these out.

**What the released app contains**: the game's program code, translated ahead
of time from PowerPC to arm64 and compiled into the app, as other static
recompilation projects ship theirs. It contains **none** of the game's assets:
no textures, models, sounds, music, videos, text or tracks. The app does not
download anything; it reads the game's data from an ISO you provide.

**You must own the game.** Use an ISO dumped from your own disc of the USA
Xbox 360 edition. Do not ask for, or share, ISOs or game files in this
project's issues or discussions.

This project is licensed under the **GNU General Public License v3.0** (see
[LICENSE](LICENSE)), like the project it is based on. The ReXGlue SDK is BSD
3-Clause and is a separate work with its own terms.

This is an unofficial fan project. It is not affiliated with, endorsed by, or
connected to Electronic Arts, Microsoft, Xbox or Apple, or the maintainers of the
projects it builds on. *Need for Speed* and *Most Wanted* are trademarks of
Electronic Arts Inc. BMW is a trademark of BMW AG.
