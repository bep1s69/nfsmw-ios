# NFSMW Recompiled for iOS

**Need for Speed: Most Wanted (2005), Xbox 360, running natively on iPhone and iPad.**

**Requires iOS or iPadOS 18 or later.**

The Xbox 360 PowerPC code is recompiled ahead of time for Apple arm64 using
[ReXGlue](https://github.com/rexglue/rexglue-sdk). The port uses a native
Metal renderer for the game's shaders.

> **You need your own copy of the game.** The app on the
> [Releases](https://github.com/bep1s69/nfsmw-ios/releases) page contains no game
> files: no textures, models, sounds, music, videos or tracks. It reads all of
> them from your own ISO of the USA Xbox 360 game. This repository contains no
> game files and no translated game code. See [Legal](#legal).

**Version 0.6.0** adds LAN racing, redesigned menus with first-launch setup,
more Extra Options, and lower memory use. See the [changelog](CHANGELOG.md)
for the full release notes.

---

## Contents

- [What it does](#what-it-does)
- [Requirements](#requirements)
- [Installing and first start](#installing-and-first-start)
- [LAN multiplayer](#lan-multiplayer)
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
- **Native Metal graphics** with adjustable render resolution, FXAA and MSAA.
  Choose **Fit this screen** or the original **16:9** framing.
- **30, 40, 60 and 120 fps caps**. The 40 and 120 fps choices appear on
  supported 120 Hz displays.
- **LAN racing** on the same Wi-Fi, including mobile cross-play and
  experimental cross-play with the original PC game.
- **Shared launcher and in-game options** with controller navigation,
  first-launch setup, and editable performance presets.
- **A save manager**: careers with their cash and bounty, backups, export and
  import (including **Xbox 360 and PC saves**), and **iCloud Drive sync**
  between your devices, achievements included.
- **Extra Options**, ported from the PC mod: markers after beating a Blacklist
  rival (1-6), cars you can buy (1-25), the Old Bridge road, Quick Race laps,
  opponents, traffic and weather, plus in-game Actions such as resetting
  the car, changing pursuit heat and teleporting in free roam.
- **Touch controls** made for the phone: menus by swiping and tapping (tap a
  button hint to press it), a dynamic steering joystick, driving buttons that
  appear only when the game uses them, and a drag race layout. Every control
  can be moved and resized, also while playing. They hide themselves when a
  controller connects.
- **Controllers** (Xbox, PlayStation, MFi), rebindable menu and driving
  keys, keyboard button prompts, and mouse or touch camera look.
- **External displays** (HDMI, AirPlay): the game alone on the big screen, the
  touch controls on the device.
- **Longest battery preset** with a 30 or 40 fps cap and configurable
  reflection cadence, plus optional thermal and Low Power Mode adjustments.
- Survives app switching, screenshots and Control Center.

## Requirements

**The game**: an ISO of *Need for Speed: Most Wanted* for Xbox 360, **USA
edition** (title ID `454107D9`), dumped from your own disc. Other editions are
not supported by the iOS build yet.

**To play**: an iPhone or iPad on **iOS or iPadOS 18 or later**. Tested on an
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
4. Open the app again and select your disc under **Play**. First-launch
   setup covers the game disc, controls, performance presets and saves.
   If you are upgrading, you can keep your settings. Press **Play** when ready.

What the app keeps in its `Documents` folder:

| | |
|---|---|
| `*.iso` | The game (with more than one, the launcher lets you pick) |
| `data/` | Your saves and the game's settings |
| `settings.json` | The launcher's choices |
| `achievements/` | The achievement list and icons the launcher shows |
| `logs/nfsmw.log`, `logs/boot.txt` | The log and the startup trace (Advanced > Logging) |
| `extra_args.txt` | Optional: extra options, one per line, for testing |

## LAN multiplayer

Put all players on the same local network. On iPhone or iPad, open **Play →
Host or join a game → Play on this Wi-Fi** and follow the in-game sign-in
flow to find or create a LAN lobby. Allow Local Network access when prompted.
**Join by address** is available if discovery misses a host.

Compatible Android builds can join mobile LAN races. Cross-play with the
original PC game's LAN mode is experimental. PC and Android players
cannot race together in the same room.

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
working rules and build procedure.

Use a separate SDK and build directory for the multiplayer-enabled 0.6.0
tree. Keep your own USA disc dump outside version control.

```sh
git clone https://github.com/bep1s69/nfsmw-ios.git
cd nfsmw-ios

python3 tools/ios/prepare_sdk.py --sdk ../nfsmw-multiplayer-sdk
python3 tools/fase1_extraer.py "/path/to/your/NFSMW-USA.iso" --solo-xex
python3 tools/ios/generate_code.py --sdk ../nfsmw-multiplayer-sdk
python3 tools/ios/patch_game_extra_options.py

cmake --preset ios -S ios -B "$HOME/Library/Caches/nfsmw-ios/build-0.6" \
  -DNFSMW_SDK="$PWD/../nfsmw-multiplayer-sdk"
cmake --build "$HOME/Library/Caches/nfsmw-ios/build-0.6" --target ipa -j 12
# Output: ios/build/NFSMW.ipa
```

The first build takes a while (on an M-series Mac, 20-40 minutes): the whole SDK
and 133 generated files, each of which can take more than 2 GB of RAM to
compile. Later builds only recompile what changed. The build folder is
`~/Library/Caches/nfsmw-ios/build-0.6`, outside the repository on purpose (iCloud
Drive tags files in `~/Documents` with attributes that `codesign` refuses).

Everything the scripts do, and why, is in [docs/TECHNICAL.md](docs/TECHNICAL.md).

## The launcher and in-game options

The launcher has **Play**, **Display**, **Battery**, **Graphics**,
**HUD & Controls**, **Gameplay**, **Audio**, and **Advanced**. Each setting
shows its current value and a short summary. Open its info button for details.
You can run first-launch setup again from **Play → Set up again**.

While playing, open the gear from a game menu or pause screen, or press
**L3+R3**. In-game options show the applicable settings and add **Actions**
for game commands. Changes that need a restart show **Next launch**.
**HUD & Controls** also opens the HUD, touch layout, and keyboard editors.

The new menus are an improvement for 0.6.0. The visual design is still
being refined for 1.0.

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

### Touch

The touch controls change with what you are doing:

- **Menus and pause screens:** no buttons on screen. Swipe to move through
  supported lists and selectors, tap a row or a button hint, and use two
  fingers to go back (B). **Tap and swipe anywhere** enables the older
  empty-space gestures. Menu swipes are inverted by default. On the world
  map a swipe moves the cursor, the LT / RT pictures zoom, and the arrows
  change the category. The PAD button at the
  top brings the full gamepad back for that menu.
- **Driving:** steering on the left (a joystick that appears under your
  thumb anywhere in the bottom-left quarter, or a fixed circle, or two
  buttons: HUD & Controls → Steering), gears, gas, brake, nitrous, speedbreaker,
  handbrake, look back and reset. The D-pad's actions appear as buttons only
  when they do something: the map, SMS and the Blacklist in free roam, a
  button to enter a race, shop or safehouse when you are in its circle, and
  the race's or pursuit's details during one.
- **Drag races:** lane change, gears, gas, nitrous and brake.

Camera, pause, PAD and HIDE share the top row. The controls dim after a few
seconds without a touch (HUD & Controls → Dim when not touched) and hide themselves
when a controller connects; HIDE hides them by hand.

**Customize touch controls** (HUD & Controls, or the in-game options while
playing) moves and resizes every control, with Pad, Drive and Drag tabs, an
overall size and the opacity. Keyboard keys can be changed under HUD & Controls too.

## Performance and battery

On an **iPad Pro M4** and an **iPhone 17 Pro Max** the game holds **60 fps**
in nearly all of the game at 1x. The 30 and 40 fps
caps are smooth and paced to the display. Higher render resolutions and the
120 fps cap are heavier.

**Longest battery** defaults to 30 fps, reduced render resolution, and
half-rate car reflections. On supported displays, you can choose 40 fps
on the preset card. The card also offers every-frame reflections.
**Balanced** and **Best looking** provide other starting points, and
the individual settings remain editable.

On the iPhone 17 Pro Max, development testing brought peak race memory
from about **1,749 MiB** to **1,330–1,403 MiB**. Compatibility reports from
players on 2–3 GB devices are welcome, especially with LiveContainer.
A community report also confirms the native renderer ran on an
**iPhone 13 Pro with iOS 18.7.8** in version 0.5.1.
[Community performance report](https://github.com/bep1s69/nfsmw-ios/discussions/12).

Your own results are welcome: share them in the
[Performance reports](https://github.com/bep1s69/nfsmw-ios/discussions/12)
discussion (device, iOS, how it is installed, settings, fps, battery, and
your nfsmw.log if you can). If the
game runs badly on your device, use the
[Performance report](https://github.com/bep1s69/nfsmw-ios/issues/new?template=performance.yml)
issue template: it asks for what is needed to find out why.

## Known issues and limitations

- **USA edition only** for now (the address tables for other editions exist in
  `tools/ediciones/`, but the iOS-specific game patches are written for USA).
- **120 fps** depends on the device, render resolution, and scene.
- **iPhone Duo support** is experimental.
- **Low-memory devices** may still hit iOS memory limits, especially
  under LiveContainer.
- Some iPad HUD overlays can be misaligned. Skipping a movie can briefly
  show a red frame.
- LAN works over a local network. The original public Xbox Live service
  and leaderboards are unavailable.
- English only (the language of the USA edition).

## Planned

Free camera and further Extra Options are planned for a later minor
release. Menu polish continues toward 1.0.

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
native Metal renderer, the touch controls, screen fitting and HUD layout, the Extra
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
