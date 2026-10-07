#!/usr/bin/env python3
"""
Let the app pause the GPU emulation while iOS has it in the background.

    python3 tools/ios/patch_ios_pause.py            apply
    python3 tools/ios/patch_ios_pause.py --status
    python3 tools/ios/patch_ios_pause.py --revert

Touches include/rex/system/interfaces/graphics.h.


WHY
===

iOS does not let a background app submit GPU work: Metal command buffers
committed from the background fail, and MoltenVK reports the device as lost.
parche_pausa already releases the window surface when SDL says the app is
going to the background (that part is not Android-only), but the command
processor keeps translating the game's GPU commands and submitting them.

The SDK already knows how to stop it: GraphicsSystem::Pause() suspends the
command processor's thread after its current command, and Resume() lets it go
on. But GraphicsSystem lives inside the GPU plugin (librexgpu-xenos.dylib),
which the app does not link, and the app only holds the IGraphicsSystem
interface, which has neither.

So Pause() and Resume() are declared on the interface, virtual and doing
nothing by default. GraphicsSystem's existing methods have the same signature
and become the overrides without any change to the plugin's source. They go
at the END of the class so the slots of every existing virtual stay where they
were; the runtime and the plugin are built from the same tree anyway.

The app calls them (ios/src/game_app.cpp) on SDL_EVENT_WILL_ENTER_BACKGROUND
and SDL_EVENT_DID_ENTER_FOREGROUND.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from patch_engine import run  # noqa: E402

ANCHOR = '''  virtual void Shutdown() = 0;
};

}  // namespace rex::system
'''
NEW = '''  virtual void Shutdown() = 0;

  // LOCAL PATCH - iOS: stop and restart the GPU command processor. iOS does not
  // let a background app submit GPU work. GraphicsSystem (in the GPU plugin)
  // already has Pause()/Resume() with this signature, so they override these
  // (tools/ios/patch_ios_pause.py). At the end, so no existing slot moves.
  virtual void Pause() {}
  virtual void Resume() {}
};

}  // namespace rex::system
'''

BLOCKS = [
    ("include/rex/system/interfaces/graphics.h", "Pause()/Resume() on IGraphicsSystem", ANCHOR,
     NEW),
]

if __name__ == "__main__":
    sys.exit(run("ios_pause", BLOCKS))
