# NFSMW Recompiled for iOS

**Need for Speed: Most Wanted (2005), Xbox 360, running natively on iPhone and iPad.**

This is not an emulator. The game's PowerPC code is translated ahead of time into
C++ and compiled for Apple's arm64 chips with the
[ReXGlue SDK](https://github.com/rexglue/rexglue-sdk). The SDK supplies everything
around the game's code: the Xbox 360 kernel calls, the file system, audio, input,
and a translation of the console's Xenos GPU to Vulkan, which runs on Metal
through MoltenVK.

> **You need your own copy of the game.** The app on the
> [Releases](https://github.com/bep1s69/nfsmw-ios/releases) page contains no game
> files: no textures, models, sounds, music, videos or tracks. It reads all of
> them from your own ISO of the USA Xbox 360 game. This repository contains no
> game files and no translated game code. See [Legal](#legal).

Version **0.3.0** (see [CHANGELOG.md](CHANGELOG.md)). The game is playable start
to finish, but there is a lot still to do before anything could be called 1.0.

---

## Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installing and first start](#installing-and-first-start)
- [Building it yourself](#building-it-yourself)
- [The settings screen](#the-settings-screen)
- [Controls](#controls)
- [Performance](#performance)
- [Known issues and limitations](#known-issues-and-limitations)
- [Planned](#planned)
- [Feedback](#feedback)
- [How it works](#how-it-works)
- [Credits](#credits)
- [Legal](#legal)

## What it does

- **The whole game**: career, quick races, challenge series, pursuits, free roam,
  saves, achievements. **Black Edition content** is on by default (with a fix
  for the career freeze it caused, see [docs/TECHNICAL.md](docs/TECHNICAL.md)).
- **60 fps** on an iPad Pro M4 in nearly all of the game at 16:9; frame rate caps
  of **30, 40, 60 and 120** (40 and 120 use the 120 Hz ProMotion display; 120 is
  experimental, see [Performance](#performance)).
- **Aspect ratios**: 16:9; the game's own **4:3** mode, rendered at 960x720
  instead of its 640x480; and **19.5:9** (iPhone) at 1560x720, with a wider
  view and the HUD moved out to the screen edges.
- **A settings screen before the game starts**: display, graphics, controls,
  Extra Options, the achievement list, and the ISO to play.
- **Extra Options**, ported from the PC mod: choose up to 6 markers after
  beating a Blacklist rival, raise the number of cars you can buy, open the
  road to the Old Bridge.
- **Touch controls**: a full gamepad layout, and a driving layout (steering
  wheel, gas and brake pedals, nitrous, speedbreaker, handbrake, gear shift,
  camera, look back, reset, pause), switched with a button at the top. They
  hide themselves when a controller connects.
- **Controllers**: Xbox, PlayStation and MFi controllers through iOS.
- **Achievements**: the game's 360 achievements, tracked and listed with
  their icons on the settings screen.
- Survives app switching, screenshots and Control Center (pauses the GPU in
  the background, recovers the screen when you come back).

## Requirements

**The game**: an ISO of *Need for Speed: Most Wanted* for Xbox 360, **USA
edition** (title ID `454107D9`), dumped from your own disc. Other editions are
not supported by the iOS build yet.

**To play**: an iPhone or iPad on **iOS / iPadOS 26 or later** with an Apple
chip of the last few years (tested on an iPad Pro M4 and an iPhone 17 Pro
Max), and [SideStore](https://sidestore.io) with
[LiveContainer](https://github.com/LiveContainer/LiveContainer) to install the
app without a paid developer account. Reports from other devices are very
welcome (see [Feedback](#feedback)).

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
4. Open the app again: the settings screen shows the ISO it found. Press
   **Play**.

What the app keeps in its `Documents` folder:

| | |
|---|---|
| `*.iso` | The game (with more than one, the settings screen lets you pick) |
| `data/` | Your saves and the game's settings |
| `settings.json` | The settings screen's choices |
| `achievements/` | The achievement list and icons the settings screen shows |
| `logs/nfsmw.log`, `logs/boot.txt` | The log and the startup trace (Settings > Advanced > Logging) |
| `extra_args.txt` | Optional: extra options, one per line, for testing |

## Building it yourself

For the battery branch's current checkpoint, experiments, measurements and
handoff instructions, read [Development progress](docs/DEVELOPMENT_PROGRESS.md).
Update that document when continuing development so work can resume across sessions.

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

## The settings screen

Every option has a short explanation on screen. The defaults suit normal play.

- **Game**: Black Edition content.
- **Extra Options**: markers after beating a rival (1-6), cars you can buy
  (1-25), Old Bridge road, and an experimental 120 Hz simulation (see
  [Known issues](#known-issues-and-limitations)).
- **Display**: resolution (Retina or point resolution), frame rate cap
  (30/40/60/120), aspect ratio (16:9, 4:3 HD, 4:3 SD, 19.5:9), sharper 4:3
  scene, stretch to full screen, FPS counter.
- **Touch controls**: on or off.
- **Graphics**: anti-aliasing (off, MSAA 2x/4x), scaling filter,
  post-processing, anisotropic filtering, internal resolution (1x/2x).
- **Advanced**: GPU emulation switches that trade accuracy for speed, logging,
  and tools for measuring performance. Leave them at their defaults unless you
  are testing something.

## Controls

With a controller, the game's own Xbox 360 controls (control type 1):

| Action | Button | Action | Button |
|---|---|---|---|
| Accelerate | RT | Brake / reverse | LT |
| Steer | Left stick | Shift up / down | Right stick up / down |
| Nitrous | B | E-brake | A |
| Speedbreaker | X | Look back | LB |
| Change camera | RB | Reset car | Back |
| Pause | Start | | |

On the touch screen, the **DRIVE / PAD** button at the top switches between
the driving layout and the full gamepad (menus need the gamepad), and
**HIDE** hides the controls. The steering circle steers left and right only,
and returns to the centre when you let go.

## Performance

Measured on an **iPad Pro M4** (13", iPadOS 27):

| | |
|---|---|
| Menus | 60 fps (120 at the 120 cap) |
| Races, free roam, pursuits, 16:9, 1x | 60 fps nearly everywhere; the heaviest police chases can dip into the 50s |
| 4:3 (960x720), 120 cap | ~100-120 fps in lighter parts of a race, ~80-90 in the heaviest |
| 30 and 40 fps caps | Smooth, paced to the display |
| Internal resolution 2x | Much heavier: roughly 20-40 fps depending on the aspect ratio |

On an iPhone 17 Pro Max the game also holds 60 fps at 19.5:9.

The game was made for 30-60 fps on the Xbox 360. At 120 it runs its world at
60 steps a second, so 120 is smoother to look at but not yet to drive; making
120 stable and the simulation follow it is the main performance work planned.

## Known issues and limitations

- **USA edition only** for now (the address tables for other editions exist in
  `tools/ediciones/`, but the iOS-specific game patches are written for USA).
- **19.5:9**: the rear-view mirror's picture is wider than its frame, and the
  intro and story videos are stretched to the full width instead of showing at
  16:9.
- **120 fps cap**: not a stable 120 in heavy parts of races. The **120 Hz
  simulation** option is an untested experiment: it changes a value the game
  shares with other systems, and may make parts of the game run too fast or
  too slow.
- **Switching apps**: the game pauses its GPU work while in the background and
  resumes when you return. This was reworked several times and is still being
  tested; if you come back to a black screen or the app closes, please report
  it with the log.
- **Sun glare**: the occlusion queries behind it were made cheaper; whether the
  glare still fades correctly when the sun is hidden is still being checked.
- **Touch controls**: the layouts cannot be edited yet, and there is no tilt
  steering.
- **No Xbox Live** (online modes, leaderboards). The game's single-player modes
  are all there.
- **Internal resolution 2x** is very demanding (the GPU emulation's resolves
  scale with it).
- English only (the language of the USA edition).

## Planned

In no particular order, and without promises:

- A stable **120 fps** in races: the GPU emulation still copies guest memory and
  render targets more than it needs to; then a proper higher **simulation
  rate** (like the PC Widescreen Fix's SimRate).
- **19.5:9** polish: the mirror picture and the videos at their native 16:9.
- **Customisable touch controls** (positions, sizes, opacity).
- A **save manager** in the settings screen.
- More **Extra Options** and **Widescreen Fix** features.
- Support for more game **editions**.
- Looking into whether a port of the PC version (see
  [nfs-most-wanted-mac](https://github.com/elforeign/nfs-most-wanted-mac), a
  native recompilation for macOS) could be a better base on iOS.

## Feedback

This is a first release, and it has only been tested on two devices. Reports
are what will make it better:

- **Your device** (model, iOS version) and whether the game runs.
- **Performance**: the frame rate in menus, races and pursuits, with the
  settings you used (turn on Display > Show FPS).
- **Problems**: what happened and where, ideally with the log
  (`Documents/logs/nfsmw.log`, with Settings > Advanced > Logging on).

Open an [issue](https://github.com/bep1s69/nfsmw-ios/issues) with them.

## How it works

[docs/TECHNICAL.md](docs/TECHNICAL.md) describes the port in detail: how the
SDK is prepared and patched for iOS (every patch, what it changes and why,
with the measurements behind it), the guest memory on iOS, the app's
lifecycle, the touch controls, the 4:3 and 19.5:9 modes, the Extra Options
ports, and the Black Edition career fix.

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
