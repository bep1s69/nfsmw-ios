#!/usr/bin/env python3
"""
Prepares the ReXGlue SDK tree for building the iOS port.

    python3 tools/ios/prepare_sdk.py
    python3 tools/ios/prepare_sdk.py --sdk /other/path/rexglue-sdk-ios
    python3 tools/ios/prepare_sdk.py --status

Leaves an SDK v0.10.0 in ../rexglue-sdk-ios, SEPARATE from the Windows and
Android ones. Safe to run as often as needed: every step checks whether it is
already done before touching anything.


WHY IT STARTS FROM THE SAME SDK AS ANDROID
==========================================

The stock SDK already knows macOS (mac-arm64 presets, MoltenVK, CAMetalLayer,
16 KB pages), and on iOS TARGET_OS_MAC is 1 as well, so almost all of that
applies as is. But the stock codegen template emits NO memory barriers on
ARM64 (sync/lwsync/eieio become nothing), and hells-gate's Android patch does.
Everything else in that patch sits behind REX_PLATFORM_ANDROID and does
nothing on Apple.

So this tree is the Android one (steps 1, 3 and 5 of
tools/preparar_sdk.py, imported from there without changing it) plus
the iOS bits on top. With the same template, the generated code is the SAME
text as Android's.


THE STEPS, IN ORDER
===================

1. Clone rexglue-sdk at v0.10.0, with submodules (as Android does).
   Repair the symlinks, also as Android does: the clone uses
   core.symlinks=false and libmspack leaves its links as text files.
2. hells-gate's Android SDK patch, downloaded from THEIR repo (as Android
   does; see there why it is not in this repository).
3. This project's patches: the SAME list in the SAME order as Android, so
   each anchor finds what the previous ones left. parche_turnip is included:
   with no libadrenotools clone (none here) and behind REX_PLATFORM_ANDROID,
   it does nothing on iOS.

   EACH ONE IS APPLIED ONLY ONCE, and recorded in
   .nfsmw-ios/project-patches.applied. Re-running them over a prepared tree is
   NOT safe: parche_tiempos inserts its block in the middle of parche_fps's,
   so a re-run of parche_fps no longer sees its block whole and inserts it
   again ("redefinition of 'nfsmw_fps_invitado'" in
   vulkan/command_processor.cpp). tools/preparar_sdk.py has the same
   problem. So only the patches not yet recorded are applied here: ones added
   at the end of Android's list go in on the next run.
4. MoltenVK v1.4.1 for iOS, the exact version the SDK's thirdparty/moltenvk
   submodule pins, from Khronos' release (MoltenVK-ios.tar), into
   .nfsmw-ios/MoltenVK. The app ships it as MoltenVK.framework.
5. The iOS patches (tools/ios/patch_ios_*.py, IOS_PATCHES below).

Then: build from ios/ (see ios/README.md).
"""

import argparse
import importlib.util
import os
import pathlib
import subprocess
import sys
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _android():
    """tools/preparar_sdk.py as a module, untouched."""
    path = ROOT / "tools" / "preparar_sdk.py"
    spec = importlib.util.spec_from_file_location("preparar_sdk_android", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ANDROID = _android()

MOLTENVK_VERSION = "v1.4.1"  # = commit db445ff of the thirdparty/moltenvk submodule
MOLTENVK_URL = (f"https://github.com/KhronosGroup/MoltenVK/releases/download/"
                f"{MOLTENVK_VERSION}/MoltenVK-ios.tar")

# Order matters, as on Android: each one anchors on what the earlier ones left.
IOS_PATCHES = [
    "patch_ios_platform",
    "patch_ios_cmake",
    "patch_ios_paths",
    "patch_ios_memory",
    "patch_ios_waits",
    "patch_ios_pause",
    "patch_ios_sdl",
    "patch_ios_timing",
    "patch_ios_ui_tick",
    "patch_ios_aspect",
    "patch_ios_retina",
    "patch_ios_qos",
    "patch_ios_fault_log",
    "patch_ios_save_log",
    "patch_ios_touch_pad",
    "patch_ios_dump_image",
    "patch_ios_upload_batch",
    "patch_ios_vblank_grid",
    "patch_ios_shader_contraction",
    "patch_ios_occlusion_async",
    "patch_ios_fps_cap",
    "patch_ios_present_pacing",
    "patch_ios_vblank_display",
    "patch_ios_ui_tick_cap",
    "patch_ios_register_check",
    "patch_ios_texture_descriptors",
    "patch_ios_readback_limit",
    "patch_ios_suboptimal",
    "patch_ios_surface_reattach",
    "patch_ios_paint_suspend",
    "patch_ios_texture_stats",
    "patch_ios_narrow_invalidation",
    "patch_ios_occlusion_batch",
    "patch_ios_dispatch_stats",
    "patch_ios_shared_stats",
    "patch_ios_hot_pages",
    "patch_ios_async_copies",
    "patch_ios_type0_ranges",
    "patch_ios_resolve_stats",
    "patch_ios_iso_stream",
    "patch_ios_native_only",
    "patch_ios_semaphore_trace",
    "patch_ios_xma_canary",
    "patch_ios_mnk_modifiers",
    "patch_ios_native_present_skip",
]


def step(n, text):
    print(f"\n== {n}. {text}")


def moltenvk(sdk):
    dest = sdk / ".nfsmw-ios" / "MoltenVK"
    marker = dest / (MOLTENVK_VERSION + ".ready")
    if marker.exists():
        print(f"[ok] MoltenVK {MOLTENVK_VERSION} already there")
        return
    dest.mkdir(parents=True, exist_ok=True)
    tar = dest.parent / "MoltenVK-ios.tar"
    if not tar.exists():
        print(f"[..] Downloading MoltenVK {MOLTENVK_VERSION} for iOS")
        with urllib.request.urlopen(MOLTENVK_URL, timeout=300) as resp:
            tar.write_bytes(resp.read())
    with tarfile.open(tar) as t:
        t.extractall(dest)
    xcf = list(dest.rglob("dynamic/MoltenVK.xcframework"))
    if not xcf:
        sys.exit(f"[ERROR] The MoltenVK tar has no dynamic/MoltenVK.xcframework ({dest})")
    marker.write_text(str(xcf[0].relative_to(dest)) + "\n", encoding="utf-8")
    tar.unlink()
    print(f"[ok] MoltenVK in {xcf[0]}")


def project_patches(sdk):
    """The Android-list patches still missing, each one only once (see step 3)."""
    marker = sdk / ".nfsmw-ios" / "project-patches.applied"
    done = marker.read_text(encoding="utf-8").split() if marker.exists() else []
    full = ANDROID.PARCHES_PROYECTO
    pending = [p for p in full if p not in done]
    if not pending:
        print(f"[ok] All {len(full)} already applied")
        return
    last = max((full.index(d) for d in done if d in full), default=-1)
    for p in pending:
        if full.index(p) < last:
            print(f"[!!] {p} sits in the middle of Android's list and is applied after the "
                  f"ones that follow it: if it fails, prepare the SDK from scratch")
    # One at a time, recording each as it finishes: if one fails, the earlier
    # ones are already recorded and a re-run does not apply them again.
    # Android's parches_proyecto walks ITS list: it gets a one-item list and
    # is put back as it was.
    marker.parent.mkdir(parents=True, exist_ok=True)
    original = ANDROID.PARCHES_PROYECTO
    try:
        for p in pending:
            ANDROID.PARCHES_PROYECTO = [p]
            ANDROID.parches_proyecto(sdk)
            done.append(p)
            marker.write_text("\n".join(done) + "\n", encoding="utf-8")
    finally:
        ANDROID.PARCHES_PROYECTO = original


def ios_patches(sdk, status=False):
    env = dict(os.environ, NFSMW_SDK=str(sdk))
    for p in IOS_PATCHES:
        cmd = [sys.executable, str(ROOT / "tools" / "ios" / f"{p}.py")]
        if status:
            cmd.append("--status")
        r = subprocess.run(cmd, env=env, text=True, capture_output=True)
        out = (r.stdout + r.stderr).strip()
        if r.returncode != 0:
            print(out)
            sys.exit(f"[ERROR] {p} failed. The earlier ones are already applied; "
                     f"re-running this script is safe.")
        if status:
            print(out)
        else:
            first = next((l for l in out.splitlines() if l.startswith("[")), "")
            print(f"  {p:24s} {first}")


def main():
    ap = argparse.ArgumentParser(description="Prepares the ReXGlue SDK for iOS.")
    ap.add_argument("--sdk", default=str(ROOT.parent / "rexglue-sdk-ios"),
                    help="iOS SDK folder (default ../rexglue-sdk-ios)")
    ap.add_argument("--status", action="store_true", help="only report which patches are in")
    args = ap.parse_args()
    sdk = pathlib.Path(args.sdk).resolve()

    if args.status:
        if not (sdk / "CMakeLists.txt").exists():
            sys.exit(f"[ERROR] No SDK in {sdk}")
        # The project patches are applied once and recorded (step 3); their own
        # --estado would misreport here, because patch_ios_waits edits inside
        # three of their blocks. So the record is what is shown.
        marker = sdk / ".nfsmw-ios" / "project-patches.applied"
        done = marker.read_text(encoding="utf-8").split() if marker.exists() else []
        full = ANDROID.PARCHES_PROYECTO
        print(f"  project patches: {sum(p in done for p in full)} of {len(full)} applied (recorded)")
        for p in full:
            print(f"      {'yes' if p in done else 'NO':>3}  {p}")
        ios_patches(sdk, status=True)
        return 0

    step(1, f"SDK {ANDROID.SDK_TAG}")
    ANDROID.clonar(sdk)
    ANDROID.reparar_symlinks(sdk)
    step(2, "hells-gate's Android SDK patch: ARM64 barriers")
    ANDROID.aplicar_parches_ref(sdk)
    step(3, "This project's patches (Android's, same order, once each)")
    project_patches(sdk)
    step(4, f"MoltenVK {MOLTENVK_VERSION} for iOS")
    moltenvk(sdk)
    step(5, "iOS patches")
    ios_patches(sdk)

    print(f"\n[ok] SDK ready in {sdk}")
    print("     Next: build from ios/ (see ios/README.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
