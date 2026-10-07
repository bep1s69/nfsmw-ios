# Changelog

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
