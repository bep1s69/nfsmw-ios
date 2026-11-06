# Changelog

## 0.6.0 (in development, branch dev-0.5)

- **Redesigned launcher and in-game options.** Dark menus share the
  same categories, compact summaries and a details button. Use the
  controller to navigate the launcher and in-game options. The launcher
  title stays fixed above a distinct, compact tab strip.
- **Car selector touch controls.** Tap a neighboring car in My Cars to
  move focus. Swipe up or down over the car in Quick Race and multiplayer
  Change Car. Options sidebar labels stay on one line.

- **First-launch setup and presets.** Choose controls and graphics or keep
  your settings. Longest battery offers 30 fps or 40 fps on supported
  displays, with half-rate or every-frame car reflections. Its settings
  remain editable. Menu swipes are inverted by default.

- **Old renderer settings removed.** The native Metal renderer always draws
  the game now; its on/off switch, the "No emulated renderer" switch, the
  whole Emulated renderer section and "Scaling to the screen" (FSR/CAS) are
  gone from the launcher. They keep the values they had by default.
- **Important for 3 GB RAM devices (and older iPhones under LiveContainer):
  much less memory use. Testing on those devices is needed.** A race used to
  peak at about 1.75 GB on an iPhone 17 Pro Max; it now peaks at about
  1.33-1.40 GB. That may be enough for devices where iOS allows the app only
  2-3 GB (e.g. iPhone 11 under LiveContainer, GitHub #10/#11), but nobody has
  tried one yet. If the game still closes on such a device, please send
  `logs/boot.txt`: it now records the app's memory limit and any low-memory
  warning. What changed (dev95-dev100):
  - Sound: a decoder only for the sounds playing, not one for each of the
    320 streams from the start (about 180 MB less at startup, ~70 MB in a
    race).
  - The pipeline cache (which keeps race starts smooth) is let go once the
    game's pipelines are ready and reopened only for a new one (~150 MB).
  - Touch controls: no whole-screen scratch picture per redraw (~29 MB).
  - When iOS warns that memory is low, unused textures and buffers are
    dropped.
  - For testers: Extra Args `--nfsmw_diag_alloc_trace=true` writes where the
    largest memory blocks come from to `logs/allocs.txt`.

- **Golf engine sound no longer cuts out (GitHub #15).** Mono sounds such
  as engines keep playing when their stream briefly runs dry, instead of
  dropping a moment of sound about once a second (dev94).

- **Simpler Display menu.** Screen shape is "Fit this screen" (this device's
  own shape) or "16:9 (Xbox 360)". Render resolution choices show the exact
  pixels they draw on your device, e.g. "Native · 2868×1320" (dev93).

- **iPhone Duo inner screen, experimental (GitHub #14).** The game looked for
  its window on the device's "main" screen, which on a foldable can be the
  other panel, and showed nothing on the inner screen. It now uses the screen
  its own window is on, and the picture is redrawn to fit when you fold or
  unfold. Limitations: not tested on a Duo yet; the game's shape is chosen
  when it starts (from the panel it is started on) and does not change while
  it runs, so after folding or unfolding the picture keeps that shape with
  black bars; restart the game to fit the other panel. A screen narrower than
  16:9 gets the game's 4:3 mode, the closest it has (dev92).

- **Less CPU work by default.** Five savings that were opt-in are now on:
  skipping picture copies nothing reads, honoring the game's face culling,
  handing the scene picture over instead of copying it, cheaper foliage
  alpha tests, and audio waits that sleep instead of checking every 1 ms.
  dev91 adds four more: cached draw recording and target, pipeline and
  attribute lookups. No battery gain was proven for them; they only cut
  work (dev90, dev91).

- **Lighter touch controls on the GPU.** The on-screen controls are now drawn
  only where they are, not over the whole screen every frame: about 0.7 ms
  less GPU work a frame on an iPhone 17 Pro Max at native resolution (dev77).

- **Lighter trees.** The soft edges of trees no longer re-shade the pixels
  their solid part already drew; same picture, a little less GPU work (dev79).

- **Longer battery at 30 fps.** Balanced at the 30 fps cap now runs the game
  on the efficiency cores on every device, and moves back to the fast cores
  by itself if frames start arriving late (about 23 % less drain on an iPhone
  17 Pro Max). Needs testing on older devices (dev75).

- **MetalFX option removed.** It used more battery than rendering at the
  screen's full resolution (43 vs 34 %/h on an iPhone 17 Pro Max at 60 fps).
  Saved MetalFX settings are ignored (dev75).

- **Smoother Balanced mode on iPads.** Balanced now gives the game's main and
  GPU threads the fast cores while driving on every device, as on iPhones;
  M-series iPads used to keep them on the efficiency cores (dev51).

- **Smooth camera on the iPad.** The 120 Hz simulation now counts its steps
  correctly and keeps frames off a timing boundary that made the iPad's camera
  move unevenly. The game runs 0.012% fast, which is not noticeable (dev50).

- **Edit test options full screen.** Extra arguments in the launcher now open
  in a full-screen editor, one option per line. Needs device testing (dev47).

- **Stop a crash loop after launch.** A damaged shader cache could close the
  game about 15 seconds after every start. The game now discards that cache
  after one failed save and rebuilds it. Needs device testing (dev46).

- **Test skipping the scene picture copy.** Add an optional trial that hands
  the finished scene image straight to the effects that read it instead of
  copying it each frame. The iPhone test skipped the copy on every driving
  frame with no visible change; off by default while savings are unmeasured.

- **Test native face culling.** Add an optional trial that honors the game's
  face-culling requests for supported geometry. The iPhone visual check passed;
  disabled by default while performance and energy benefits remain unmeasured.


- **Reduce rendering setup work.** Update frame resource lists incrementally
  while preserving every encoder's resource declarations. Correctness and
  reduced list construction work are confirmed on iPhone; energy gains remain
  unmeasured.

- **Use smaller rendering uploads.** Remove unused padding from shared draw
  data without changing the picture. The tested iPhone run used roughly half
  the upload-buffer capacity; battery and thermal gains are not yet measured.

- **Show later joiners on the PC.** A phone host now refreshes the PC's room
  player count when someone joins or leaves, so the PC lists everyone. Needs
  device testing (preview18).

- **Play on LAN with one option.** “Play on this Wi-Fi” replaces Host, Join and
  Host for PCs. Signing in to Xbox Live in the game joins a nearby phone or PC
  lobby, or hosts one if there is none. Join by address remains as a fallback.

- **Mix PCs and phones in one room.** A phone-hosted lobby now accepts iPhones,
  Android phones and up to three original PC games at once. Every iPhone in the
  room translates race data for each PC separately. Android and PC players
  cannot race together. Needs device testing (preview17).

- **Refresh the host's player count.** Keep the LAN room's displayed count in
  sync with its parsed member list before refreshing the frontend. The iOS
  host now shows the PC guest's name, confirmed on device in preview16.

- **Race against a PC guest.** Preview15 now reaches gameplay with iOS hosting
  and the original PC game joining, without extra PC software. Both hosting
  directions have worked on device. Phone-hosted finishes and rematches still
  need testing; missing guest names on the phone remain open.

- **Test the first PC guest handshake.** Read the mobile host's listener ID
  before matching the first PC request, targeting a room join that receives
  requests but never replies. Reverse racing still needs device testing.

- **Retry PC discovery when broadcast fails.** Experimental PC hosting now also
  sends lobby announcements directly to nearby LAN devices. Targets the logged
  iOS broadcast failure; discovery on a real PC still needs testing.
- **Validate PC-hosted races and rematches.** A long session survived an idle
  period, completed on PC, returned both devices to the room and started another
  race successfully in preview13.

- **Test hosting for PCs.** Add a separate experimental two-player hosting
  option that advertises a native PC LAN lobby and adapts PC guest connections
  inside the app. No extra PC script or modification. Reverse-direction play
  still needs device testing. Builds on victorgbd's directly reused Android
  server and C++ adaptation, credited below.

- **Play against a PC LAN host.** First on-device iOS/PC gameplay test succeeded
  with native PC discovery and no PC helper script. Both cars loaded and the
  session ran until the player quit. Full race results and rematches remain
  to be tested before release.

- **Translate PC car setup records.** Correct the car ID and numeric customization
  fields exchanged with PC, targeting the remote-car creation failure during
  race loading. Uses the existing PC save-conversion field map credited to
  sprintstate and dbalatoni13. PC race completion still needs device testing.

- **Record PC race-loading failures.** Add bounded factory and packet diagnostics
  after PC/iOS connections reached race loading and crashed. This diagnostic
  build preserves game behavior and does not yet fix the race-loading crash.

- **Match the PC listener’s connection ID.** Translate handshake identifiers
  between iOS and the selected PC host. The header-only test still timed out;
  the identifier adaptation needs device confirmation.

- **Test PC race packet headers.** Adapt the two transport-header fields for
  the selected PC host. iOS now exchanges race packets with PC, but the peer
  handshake still times out; this experiment needs device confirmation.

- **Prepare PC peers for the connection test.** Translate PC LAN addresses and
  provide the local Xbox session record required after joining a PC room.
  PC rooms and live car/track updates now work on device; racing is unverified.

- **Show PC rooms in the multiplayer test.** Adapt the observed PC room build
  tag for the iOS room browser. Login and directory discovery now work on device;
  joining and racing with PC still need testing. No PC helper script required.

- **Test joining PC LAN hosts directly.** Finds the original PC game's LAN
  directory without a PC helper script. Handles the different persona field
  and unavailable Xbox history query inside iOS. PC room joining and racing
  still need device testing; PC mode uses empty local LAN history.

- **Choose the address for the joined network.** Joining uses the local address
  selected by the route to the host, including when Wi-Fi and hotspot coexist.

- **Use the hotspot address while hosting.** Prefer the active Personal Hotspot
  interface when Wi-Fi is also connected, so hotspot guests receive the host's
  address on their network. Android device retest pending.

- **Fix a crash when another player connects.** Keep a copy of the game's
  temporary receive-buffer descriptors until the packet arrives. The hotspot
  test reached both devices before exposing this memory overwrite. The fix
  passes regression checks and a two-device iPhone/iPad hotspot race test.

- **Find hosts when UDP discovery fails.** iOS now explicitly binds its
  discovery socket and falls back to the existing EA TCP directory protocol.
  Android and Python hosts need no changes. Discovery diagnostics go to boot.txt.
  Two-player iPhone/iPad racing confirmed over Personal Hotspot and Wi-Fi.

- **Clearer multiplayer setup.** A dedicated Host/Join screen finds nearby
  hosts, shows which lobby you are connected to, chooses a player name and
  explains who creates the race. Joining this device's own address is blocked.
  Ordinary Play always starts single-player. Uses victorgbd's existing LAN
  discovery and lobby protocol; device testing of this flow is pending.

- **LAN multiplayer preview.** Adds hosting and joining for iPhone/iPad play and
  Android compatibility testing. Based directly on [victorgbd's Android LAN
  implementation](https://github.com/victorgbd/NFSMW-Recompiled-Mobile) and
  [nfsmw-server-lan](https://github.com/victorgbd/nfsmw-server-lan). The networking
  code and C++ lobby adaptation are copied/adapted from that work; credit for
  the original implementation and adaptation belongs to victorgbd. This port
  adds Darwin integration, the USA hook and its launcher controls. Device
  cross-play testing is pending.


- **More Extra Options** (Extras tab): Speedbreaker refill time, refill
  speed and weight; the speeds for Speeding, Excessive Speeding and Reckless
  Driving; impound strikes of a new car and the most a car can reach; and a
  heat level override (lowest and highest heat in every event).
- **Even more Extra Options:** game speed, the fewest laps and opponents for
  a Quick Race, the most laps and opponents of a random race, and rain drift,
  fall speed and gravity.
- **Cheats from the Xbox 360 prototype's debug menu:** infinite nitrous,
  infinite Speedbreaker and no cops, plus all cops shown on the minimap.
- **Change heat while playing.** The in-game menu's Change heat has − and +
  buttons that lower or raise the pursuit's heat by one level (beyond an
  event's own limit only with Heat level override on). The heat override's lowest and
  highest heat now offer every level from 1 to 10.
- **Keyboard keys that know where you are.** Menus and driving have their
  own keys (Settings > Keyboard controls shows both lists): Enter accepts
  and Esc goes back in menus, Space is the handbrake and Esc pauses while
  driving. Menu hints show the key to press while you use the keyboard; a
  controller button or a touch brings the usual icons back.
- **Mouse look.** With keyboard controls, the mouse or trackpad turns the
  chase camera around the car while driving (pointer locked while driving,
  free in menus); it swings back behind the car when you stop. Speed and
  invert (on by default) in the Keyboard settings. On touch, swipe on the
  screen where there is no control.
- **Showcase by touch.** Drag to turn the car as far as your finger moves,
  pinch to zoom. New Extra Option: Unlimited showcase camera.
- **Keys for the Actions.** While driving, 1 resets the car, 2 toggles auto
  drive, 3 and 4 lower and raise the heat; change them under Keyboard
  controls > Actions.
- **In-game menu with tabs.** Extras, Graphics, Controls and Actions, each
  grouped as in the launcher; L1/R1 switch tabs on a controller. Actions has
  Change heat, Auto drive, Reset car (back on its wheels) and Teleport to
  69 places in the city.
- **More Extra Options:** no rev limiter, unlock everything, skip the career intro, world
  animation speed and nitrous trail length.
- **Extra Options in the in-game menu.** Every Extra Option except the Old
  Bridge road can be changed while playing (gear or L3+R3) and applies at
  once; race limits and traffic show from the next race.

## 0.5.2

> **Please read this before playing.** This update changes how you play
> **again**: menus now react to what you actually touch. Tap the button,
> row, arrow or icon you want, and swipe on the list or picker you want to
> move through. Tapping empty space no longer presses Accept, and swiping on
> empty space no longer moves the selection. You can bring back the 0.5.1
> behaviour, or mix the two, with the switches listed under "Your options"
> below.

### Menus: touch what you want

- **Tap buttons and hints.** The on-screen button hints (Accept, Back, the
  LT/RT and LB/RB hints, the left/right and up/down arrows) are now buttons:
  tap one to press it.
- **Tap rows and events.** Tapping a menu row, option or event selects it.
  Tap a selected event again to start it. Profiles are only selected by a
  tap; confirm with Accept so you cannot load the wrong one by accident.
- **Tap popup choices.** Yes/No and other popup choices, including the alias
  confirmation, can be tapped directly.
- **Swipe where it scrolls.** Swipe up or down on a list to move through it,
  and left or right on a selector or carousel. This covers the main lists,
  options, the save and profile lists, the Rap Sheet and its Rankings, the
  car category and car pickers, the track picker, the world map and the
  Blacklist (swipe on the rival's photo, or tap its up/down arrows).
  Keep your finger down to keep moving through entries.
- **Look around cars.** Drag in the car showcase to turn the camera.
- **Startup.** Tap to skip the startup movies and to get past Press Start.
- **Two fingers to go back.** A short two-finger tap presses Back, as before.
- **Full gamepad.** The PAD button still brings the complete on-screen
  gamepad back for a menu; a button on it returns to gestures.

### Your options

All of these are in the launcher's Settings; the first three are also in
the in-game settings and take effect right away:

- **Tap and swipe anywhere** (off by default): on, a tap on empty space
  presses Accept and a swipe anywhere moves the selection, like 0.5.1. The
  new taps on buttons, rows and popup choices keep working.
- **Two-finger tap to go back** (on by default): turn off if you trigger
  Back by accident. Independent of the switch above.
- **Invert menu swipes** (off by default): reverses the swipe direction in
  menus. World-map dragging is not affected.
- **Swipe and tap in menus** (on by default): off shows the full gamepad in
  menus instead of gestures, as before 0.5.0.

### Performance and frame rate, live

- **Switch performance profiles while playing.** Eco, Balanced and Max now
  apply immediately from the in-game settings, without relaunching. Any
  explicit scheduling overrides you set are kept.
- **Change the frame-rate cap while playing.** Switch between 30, 40, 60 and
  120 fps in the in-game settings without relaunching. 40 and 120 appear
  only on 120 Hz displays and are no longer labelled experimental.

### Audio

- **Keep your music playing.** A new Audio setting lets music from other
  apps keep playing alongside the game.

## 0.5.1

- **Steady 60 fps on iPhone 14 Pro Max.** Fixed presentation scheduling that
  could repeatedly pull the game down to about 40 fps.
- **Smoother frame pacing and world motion.** Improved 40 fps presentation,
  aligned 30 fps world updates with complete frames, and restored the original
  catch-up allowance during frame-rate drops, including at the 120 fps cap.
  The smoother 120 Hz simulation remains enabled at every cap.

## 0.5.0

> **Please read this before playing.** This update changes how you play:
> **the touch controls work differently now**: menus are driven by swiping
> and tapping instead of an on-screen gamepad, steering uses a joystick that
> appears under your thumb, and the D-pad's actions show up as buttons only
> when they do something. Everything is explained under "Touch controls,
> redesigned" below. If you were on iOS 26 and only got a crash or a black
> screen with the native renderer, try it again: that is fixed too.

Everything planned for 0.4.3, released as 0.5.0 because of how much it
changed (the earlier 0.5.0 plans, more Extra Options, Widescreen Fix
features and PC mods, are now 0.6.0). Most important first.

### No more crash on iOS 26 with the native renderer

The game crashed a second or two after Play on iOS 26 with the native Metal
renderer. iOS 26 reuses an internal ID the renderer relied on to tell its
drawing steps apart, so some steps were left without their settings and the
graphics driver crashed. They are now always set up. Confirmed on an iPhone
17 Pro Max with iOS 26.7.2. This likely also fixes the native black screen on
iOS 26 ([issue 4](https://github.com/bep1s69/nfsmw-ios/issues/4),
[issue 7](https://github.com/bep1s69/nfsmw-ios/issues/7)): please report
back if it does not.

Thanks to [Vipe95](https://github.com/Vipe95) for running the diagnostic
builds and sending the logs that found it.

### Touch controls, redesigned

Built with the Android port as the model, and tested by playing through free
roam, races, pursuits, drag races and every kind of menu.

**In menus: swipe and tap, no gamepad in the way.**

- In menus, pause screens, the post-race screens and SMS screens the
  on-screen gamepad is gone.
- **Swipe** to move through a menu: it works like pushing the stick that
  way, for as long as your finger stays down.
- **Tap anywhere** to accept (A). **Tap with two fingers** to go back (B).
- **Tap one of the game's own button hints** ("B Back", "A Read", "Y Delete",
  "X Toggle Icon Visibility"...) and that button is pressed. This also works
  on the photo at the end of a race: tap Continue, Race Stats or Restart.
- **World map:** a swipe moves the cursor, the LT / RT pictures zoom, and the
  arrows next to the category change it.
- The **PAD** button brings the full gamepad back for that menu if you need
  it. Touch controls › Swipe and tap in menus turns all of this off.

**Steering your way.** A new Steering setting, in the launcher and in the
in-game options:

- **Dynamic joystick** (the new default): it appears wherever your thumb
  lands in the bottom-left quarter of the screen and fades out when you lift
  it.
- **Fixed steering circle**, as before.
- **Two buttons** for left and right.

**The D-pad's actions as buttons, only when they apply.** The small D-pad is
now up to four buttons, shown only when the game would do something with
them:

- In free roam: the world map, SMS messages and the Blacklist, plus a button
  to enter (a flag in a race's circle, a door in a shop's or safehouse's)
  while you are in one.
- In a free-roam pursuit: the pursuit's details and the map.
- In races and pursuit challenges: the details only.

They follow what the HUD shows, so they appear and disappear on their own;
anything you are holding (gas, steering) stays held when they change.

**A drag race layout.** In a drag race the controls switch to their own
layout: lane change left and right and shift down and up on the left, the
gas with nitrous above it on the right, the brake beside them.

**A cleaner look and a new default layout.**

- Icons instead of words (a flame for nitrous, pedals, a stopwatch for
  speedbreaker...).
- Touch areas larger than what is drawn: a touch between two buttons goes to
  the nearer one.
- The controls dim after 3 seconds without a touch, so they hide less of the
  road (Touch controls › Dim when not touched).
- By default nitrous and look back sit above speedbreaker and handbrake, the
  D-pad buttons above the shift buttons, and camera and pause share the top
  row with PAD and HIDE, above the rear-view mirror. The same layout scales
  to the iPad, where the driving controls are gathered into the bottom
  corners, within thumb reach.
- A layout you saved before is kept.

**Customize touch controls, also while playing.** The editor has Pad, Drive
and Drag tabs; the four D-pad buttons move and resize together, and the
dynamic joystick's area is shown. It opens from the launcher and from the
in-game options (the gear in pause screens, or L3+R3), where changes apply as
soon as you close it.

**Fixes.** The driving controls no longer flash up while the game starts,
and no longer stay over the race-finished photo.

### Smoother play

- **Steadier frame rate while driving.** The game moved its threads to the
  phone's efficient CPU cores once frames had been on time for a while, and
  on some iPhones the frame rate then sank from 60 to 40 in the middle of a
  race. They now stay on the fast cores while you drive; menus and loading
  still save power.
- **New Performance setting** (Graphics tab), which CPU cores the game's
  threads ask for:
  - **Eco**: the efficient cores always, for battery life over smoothness.
    The default when Battery mode is on.
  - **Balanced** (the default): efficient cores in menus and loading, fast
    cores while driving. On iPads with 6 or more efficient cores (M-series)
    Balanced keeps their original, tested behaviour.
  - **Max**: the fast cores always, for the steadiest frame rate.

  Sound and the screen's timing keep their own priority in every mode, and
  iOS takes the setting as a hint, not a fixed choice of cores.
- **Smoother start to races and pursuits.** For the first seconds of a race
  or chase the world could move on only two of every three frames, so it
  looked like 40 fps while the counter said 60. The game now always moves
  its world 120 times a second, which removes it; the "120 Hz simulation"
  switch is gone from Advanced.

### Customize HUD

With Custom HUD on, a new editor (in the launcher and in the in-game options)
shows the HUD's parts as outlines on a screen of your device's shape: drag
each where you want it, make it smaller or bigger, and set the whole HUD's
size and safe zone, with separate tabs for races and pursuits. It replaces
the HUD size, safe zone and position settings.

### HUD fixes

- **Minimap stays in place.** After leaving the safe house again, finishing
  or restarting a race, the map and its icons could be drawn inward from the
  minimap's ring. Fixed (also with Custom HUD off).
- **Full-screen overlays at full size.** With a smaller HUD, the TV-style
  picture when you're busted and at the end of a race was shrunk with it;
  both are full size again, and the autosave icon stays in the HUD's corner.
  In chases, the pursuit points stay above the speedometer and the
  infraction list stays under its badge. On the iPhone the loading screen
  fills the screen.
- **Heat ring back around the heat badge.** In pursuits with a smaller HUD
  size, the spinning ring (and the shop / event circle prompt) sat off to
  the side of the heat level badge.
- **The circle prompt stays put.** With Custom HUD, the icon over the road in
  an event, shop or safehouse circle (and its spinning ring) moved with the
  infractions list, and the ring flashed between two places. It now stays
  where the game puts it, at the top middle.

### Other additions

- **Sound in silent mode, if you want it.** Audio tab › "Play sound in
  silent mode". Off (the default) keeps the usual behaviour: the game is
  quiet when the phone's silent switch is on.
- **Game Mode for directly installed copies.** The app now asks iOS for Game
  Mode when it is sideloaded with a certificate (LiveContainer has its own
  Game Mode handling).
- **Extra arguments in the launcher.** Advanced tab › Extra arguments:
  options for testing (e.g. `--nfsmw_hud_watch=true`), separated by spaces,
  without editing Documents/extra_args.txt. They win over both.
- **Bug and performance report templates** on GitHub: they ask for your
  device, iOS version, how the app is installed, your settings and the log,
  so problems can be found faster.

### Smaller fixes

- **Custom HUD off: one setting no longer lost.** The empty HUD layout took
  the next launch option (GPU frame capture) as its value.
- **Smaller logs.** Two of the HUD's overlays took turns being logged in
  full every frame, which filled several 5 MB logs in a few minutes. Each is
  now logged once.

### Known issues

- On the iPhone the asphalt-and-leaves picture behind the race results does
  not reach the screen's sides.
- The loading screen's pieces twitch slightly.
- At the end of a race some HUD elements zoom in (most visible on the iPad).

## 0.4.2

- **"Appears to be damaged" careers load.** A career saved on another device
  or install carries another player ID, and the game refused it as damaged
  although the file was fine. It now loads, and is saved with this device's
  ID from then on.

- **Black Edition cars no longer invisible after loading a career.** The
  extra car records kept beside a save were only put back if the career
  matched them exactly, so one changed record left the cars invisible and
  without their upgrades. They now come back whenever the records that need
  them match.

  Thanks to [Lunquell](https://github.com/Lunquell) for reporting these
  ([issue 8](https://github.com/bep1s69/nfsmw-ios/issues/8)) and sending the
  save files and logs that found them.

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
