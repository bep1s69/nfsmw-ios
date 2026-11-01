# PC mod features: what to port

Every setting of the two PC code mods, sorted for the iOS port (branch
`dev-0.5`). Sources, read October 27, 2026: Extra Options
`NFSMWExtraOptionsSettings.ini` (ExOptsTeam/NFSMWExOpts, master; 118 keys)
and Widescreen Fix `source/NFSMostWanted.WidescreenFix/settings.json`
(ThirteenAG/WidescreenFixesPack, master; 33 settings).

These mods patch `speed.exe`, so none of them loads on iOS. Each feature is
re-found in the Xbox 360 code and built in as a switch (launcher, in-game
menu, Extra Args), as in `ios/src/game_extra_options.cpp`. File-based mods
(VLT, textures, cars) are a separate step (BACKLOG, "PC mods on the port").

Done rows checked against the cvars in `ios/src` (October 27, after Stefan
pointed out laps, opponents and always rain already existed). **Effort is an estimate from the setting's description, not from looking at
the Xbox code**, except for the rows marked done. Easy = one constant or
compare, like the marker count. Hard = new menu entries, a touch control for a
PC hotkey, or a renderer change. Status changes go here, with evidence in
TECHNICAL.

## Done

| Feature | Mod setting | Where |
|---|---|---|
| Markers after a rival (1-6) | ExOpts SelectableMarkerCount | `game_extra_options.cpp` |
| Cars you can buy (1-25) | ExOpts PurchasedCarLimit | same |
| Old Bridge road | ExOpts RemoveOldBridgeBarrier | same |
| Skip movies | ExOpts SkipMovies | same (`nfsmw_skip_movies`) |
| Quick Race laps (max 1-127) | ExOpts LapControllers Maximum | same (`nfsmw_laps_max`) |
| Quick Race opponents (max 1-6) | ExOpts OpponentControllers Maximum | same (`nfsmw_opponents_max`) |
| Traffic density per level | ExOpts TrafficControllers Low/Medium/High | same (`nfsmw_traffic_*`) |
| Rain values | ExOpts Weather GeneralRainAmount, RainSize, RainIntensity, RoadReflectionAmount | same (`nfsmw_rain_*`, `nfsmw_road_reflection`) |
| Always rain | ExOpts AlwaysRain | same (`nfsmw_always_rain`) |
| Speedbreaker (IPA104, untested) | ExOpts SBRechargeTime, SBRechargeSpeedLimit, SBMassMultiplier | `nfsmw_sb_*` |
| Infraction speeds (IPA104, untested) | ExOpts SpeedingLimit, ExcessiveSpeedingLimit, RecklessDrivingLimit | `nfsmw_*_limit` |
| Impound strikes (IPA104, untested) | ExOpts ImpoundStrikesCount, MaximumImpoundStrikesCount | `nfsmw_impound_strikes*` |
| Heat override (IPA104, untested; clamp only) | ExOpts HeatLevelOverride, Minimum/MaximumHeatLevel | `nfsmw_heat_*` |
| Rain crossing, fall speed, gravity (dev2, untested) | ExOpts Weather RainCrossing, RainSpeed, RainGravity | `nfsmw_rain_crossing`, `_fall_speed`, `_gravity` |
| Game speed (dev2, untested) | ExOpts GameSpeed | `nfsmw_game_speed` (wraps sub_82472F38) |
| Quick Race minimum laps/opponents (dev2, untested) | ExOpts LapControllers/OpponentControllers Minimum | `nfsmw_laps_min`, `nfsmw_opponents_min` (1 and up; the PC's 0 opponents not allowed) |
| Random race laps/opponents (dev2, untested) | ExOpts LapControllers/OpponentControllers RandomRace | `nfsmw_random_*_max` (wraps sub_822C4E68) |
| Show non-pursuit cops on the minimap (dev3, untested) | ExOpts ShowNonPursuitCops | `nfsmw_show_non_pursuit_cops` (prototype flag, USA 0x82A2C5FA) |
| Infinite NOS, infinite Speedbreaker, No Cops (dev3, untested) | none (Xbox 360 prototype debug menu) | `nfsmw_infinite_nos`, `nfsmw_infinite_speedbreaker`, `nfsmw_no_cops` |
| Unlock all things, skip career intro (dev7, untested) | ExOpts UnlockAllThings, SkipCareerIntro | USA debug bytes 0x82A2CE00-02 (via the prototype's menu) |
| World animation speed, NOS trail length (dev7, untested) | ExOpts WorldAnimationSpeed, NosTrailRepeatCount | 0x828F9DF8, 0x828F89AC |
| Auto drive (dev7, untested; Actions tab) | ExOpts AutoDrive hotkey | toggle byte 0x82A2BD93 (prototype Toggle AI Control) |
| Movies at 16:9 | WSF FMVWidescreenMode (part) | `nfsmw_native_movie_16_9` |
| Black Edition | ExOpts ForceBlackEdition | Black Edition switch (D-007) |
| Higher simulation rate | WSF SimRate (old ini) | 120 Hz simulation, Advanced |
| Frame rate cap | WSF FPSLimit | Display settings |
| Anti-aliasing | WSF AntiAliasing | FXAA, MSAA |
| Shadow resolution | WSF ShadowResolution | shadow drawing size |
| Widescreen HUD | WSF Scaling, HudAspectRatioConstraint | 19.5:9 mode, movable HUD |

## Easy (recommended first)

- Race setup leftovers: UnfreezeKO (the knockout's laps = opponents store is
  sub_82560C78 `stb r10,104(r11)`; the PC's second edit, which unlocks the
  laps row for knockouts, 0x7ACF83, a virtual call, is not found on the 360
  yet).
- StartingCash: harder than expected. The PC's spot (a function that adds
  10000 to the career's cash, +12) exists on the 360 (sub_822C26E0) but
  nothing calls it; the career default (sub_822C17F8, cash 0) has no direct
  caller either (inlined). A new-career hook is still to be found.
- Pursuit: ShowPursuitCops (on by default in the game; the prototype's
  flag, 0x82945216, has no reader found at that address yet). Hide GPS arrow
  (prototype 0x82A80C8E, same) and Max Cop Cars (prototype 0x82A80C7C, read
  in 0x82129980 = USA sub_82118F80, the read itself not aligned yet).
- Fixes (first check the bug exists on the Xbox 360): HelicopterBountyFix,
  ZeroBountyFix (heat 10 and above; matters only with the heat override
  above 5), DDayFix, BustedNISFix.
- World: CarScale, WorldAnimationSpeed, NosTrailRepeatCount, NoRevLimiter
  (PC vtable slots 0x8AB78C/0x8AC034, functions returning 1; 360 vtables not
  found yet).
- HUD/misc: ShowHUDOnLookBack, ShowPercentOn1LapRaces,
  UnlockBurgerKingChallenge, SkipMovies, SkipCareerIntro, ReplayBlacklistRaces.
- WSF: FOVFactor, GRAPHICS.RainDropletsScale, CAMERA.ReturnDelay/ReturnSpeed,
  GAMEPAD stick deadzones.

## Hard

- PC hotkey cheats need a touch button or menu entry each: HeatLevelHack /
  ChangeHeatLevel, ToggleCops, CopLights, Headlights, FreezeCar,
  FreezeCamera, UnlockAllThings, AutoDrive, EnableSaveLoadHotPos,
  WorldMapAnywhere, SkipTrackAnywhere, EnableMaxPerformanceOnShop.
- Menus and lists: ShowMoreCarCategories, ShowSpecialVinyls,
  ShowDebugCarCustomize, ShowDebugEventID, ShowHiddenTracks,
  BetterRandomRaces, RandomizeCount, ShowAllCarsInFE, MaximumBlacklistRival,
  ChallengeSeriesBlacklist, AllowLongerProfileNames (iOS keyboard),
  ShowLanguageSelectScreen, ShowSubs / WSF Subtitles.
- AI and handling: MaxUniqueOpponentCars, MoreCarsForOpponents,
  CarbonStyleRandomCars, PursuitActionMode, BetterHandlingWithFlatTires,
  NoCatchUp (experimental on PC).
- Cameras: EnableHiddenCameraModes, EnableDebugCamera (+ turbo speeds),
  ShowcaseCam InfiniteZoom/InfiniteRotation/AlwaysEnable,
  CarSelectTireSteerAngle, WSF FreeLook (touch drag) and InvertLook /
  OnlyAllowHorizontalStickMovement.
- Rendering: ForceCarLOD, ForceTireLOD, RemoveNeonBarriers,
  ShowBustedScreenFrame, UncensoredBustedScreen, WSF FMVWidescreenMode and
  CutsceneBorders (backlog: 19.5:9 videos), SoftShadows, Sharpness.
- Expert/experimental on PC: ImmobileCollisionsFix, CarSkinFix,
  SplashScreenTimeLimit.

## Not useful on iOS

PC-only or already how the Xbox 360 game works: ShowOnline,
ShowOnlineOpts, AllowMultipleInstances, ExpandMemoryPools, DoScreenPrintf,
ShowMessage, DisableTakeover, AwardedCash (needs an NFSU2 PC save),
DisappearingWheelsFix (PC window focus), ExperimentalSplitScreenFix,
EnableSound/EnableMusic (volume settings exist), ForceMaximumFSAALevel
(MSAA setting), ShowTimeOfDay (check: the Xbox menu may already have it);
WSF ConfineCursor, MouseSensitivity, WindowMode, GraphicsAPI, D3D9on12,
HideAABug, CustomUserFilesDirectoryInGameDir, PortableSettings, GamepadIcons,
ConsoleGamma, Language/TextLanguage (the ISO's language), SkipIntro (check
against the existing launch flow).
