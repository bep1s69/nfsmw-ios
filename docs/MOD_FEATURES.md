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

**Effort is an estimate from the setting's description, not from looking at
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
| Black Edition | ExOpts ForceBlackEdition | Black Edition switch (D-007) |
| Higher simulation rate | WSF SimRate (old ini) | 120 Hz simulation, Advanced |
| Frame rate cap | WSF FPSLimit | Display settings |
| Anti-aliasing | WSF AntiAliasing | FXAA, MSAA |
| Shadow resolution | WSF ShadowResolution | shadow drawing size |
| Widescreen HUD | WSF Scaling, HudAspectRatioConstraint | 19.5:9 mode, movable HUD |

## Easy (recommended first)

- Race setup: LapControllers (min/max laps, KO laps), OpponentControllers
  Minimum/Maximum/RandomRace, TrafficControllers Low/Medium/High.
- Career numbers: StartingCash, ImpoundStrikesCount,
  MaximumImpoundStrikesCount.
- Speedbreaker: SBRechargeTime, SBRechargeSpeedLimit, SBMassMultiplier.
- Pursuit: HeatLevelOverride with Minimum/MaximumHeatLevel; SpeedingLimit,
  ExcessiveSpeedingLimit, RecklessDrivingLimit; ShowPursuitCops,
  ShowNonPursuitCops (minimap).
- Fixes (first check the bug exists on the Xbox 360): HelicopterBountyFix,
  ZeroBountyFix, DDayFix, BustedNISFix.
- World: GameSpeed, CarScale, WorldAnimationSpeed, AlwaysRain and the
  Weather rain values, NosTrailRepeatCount, NoRevLimiter.
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
