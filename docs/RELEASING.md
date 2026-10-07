# Releasing

What to do for each release, so every published `.ipa` is built the same way.

1. **Version.** Set `NFSMW_VERSION` and bump `NFSMW_VERSION_CODE` in
   `ios/CMakeLists.txt`; add the release to `CHANGELOG.md`; update the version
   line near the top of `README.md`.
2. **Clean, current SDK.** `python3 tools/ios/prepare_sdk.py --status`: every
   patch applied. Diagnostic patches stay **off by default**
   (`ios_texture_stats`, `ios_dispatch_stats`, `ios_shared_stats`,
   `ios_hot_pages`).
3. **Generated code from the USA ISO**, with the game patches:
   `python3 tools/ios/generate_code.py`, then
   `python3 tools/ios/patch_game_pool.py --status` and
   `python3 tools/ios/patch_game_extra_options.py --status` both fully applied
   (CMake refuses to build USA code otherwise).
4. **Build**: `cd ios && cmake --preset ios && cmake --build --preset ios --target ipa`.
5. **Check the app**: `codesign --verify --deep --strict` on the built
   `NFSMW.app`; `plutil -p NFSMW.app/Info.plist` shows the bundle id
   `com.bep1s.nfsmwios`, the name and the version. Install it on a device with a
   fresh container and play a race: the settings screen's defaults are the
   ones players get.
6. **Name it** `NFS-Most-Wanted-<version>.ipa` and note its SHA-256
   (`shasum -a 256`).
7. **Check what is committed**: `git status --ignored` lists `ios/generated/`,
   `assets/` and every `.ipa` as ignored; no game file, generated C++, log or
   capture is tracked.
8. **Tag and publish**: `git tag v<version>`, push the tag, and create the
   GitHub release from it with the CHANGELOG entry as its notes, the SHA-256,
   and the `.ipa` attached. Only the `.ipa`: never an ISO, XEX, extracted game
   file or the generated C++.
