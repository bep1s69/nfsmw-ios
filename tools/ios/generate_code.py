#!/usr/bin/env python3
"""
Generates the game's C++ for iOS, on the Mac, with the iOS SDK's codegen.

    python3 tools/ios/generate_code.py
    python3 tools/ios/generate_code.py --xex /path/to/default.xex

Needs:
  - the iOS SDK prepared:  python3 tools/ios/prepare_sdk.py
  - your default.xex in    assets/game_root/default.xex
                           (python3 tools/fase1_extraer.py "<your>.iso" --solo-xex)
  - cmake and ninja (brew install cmake ninja) and Xcode's clang.

Leaves the result in ios/generated/default (ignored by git: ios/.gitignore).
As soon as it exists, ios/CMakeLists.txt builds the app WITH the game instead
of only the probe.


WHY NOT tools/android/generar_codigo.py
=======================================

It builds the rexglue CLI for Windows or Linux only, and it writes to
app/generated-android. The CLI itself builds fine on macOS from the iOS SDK
tree, with the SDK's own mac-arm64 preset (the iOS patches only act when
CMAKE_SYSTEM_NAME is iOS). It is a Mac program: it only writes C++.

The codegen templates are compiled into the CLI, and the iOS tree has the
same template as Android's (hells-gate's ARM64 barriers), so the code is the
same text Android's generator would produce for the same XEX.


THE GAME EDITION
================

Every default.xex is a different program, and the project's addresses
(overrides.toml, huecos.toml, the C++ hooks) are those of PAL Spain. As on
Android, the edition is detected first (tools/ediciones/ediciones.py) and, if
it is not the reference one, those addresses are translated with that
edition's table. The result is recorded in ios/generated/edicion.json, which
ios/CMakeLists.txt reads: the game's language and country, and whether the
hooks need translating. An app is for ONE edition: the one of the ISO it was
generated from.


THE RESULT IS THE GAME
======================

ios/generated/ holds the game, translated. It is ignored by git and the app
built with it is for your own devices only.
"""

import argparse
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "common" / "codegen"  # the manifest's folder
XEX = ROOT / "assets" / "game_root" / "default.xex"
GENERATED = ROOT / "ios" / "generated"

sys.path.insert(0, str(ROOT / "tools" / "ediciones"))
import ediciones  # noqa: E402


def fail(msg):
    sys.exit(f"[ERROR] {msg}")


def reference_manifest(out_dir, xex):
    """
    For the reference edition (PAL Spain) nothing is translated, but the
    manifest still has to live outside app/ and write to ios/generated: the
    Android manifest and the project's TOMLs, copied with the paths rewritten,
    as ediciones.aplicar does for the other editions.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for rel in ediciones.CODEGEN:
        shutil.copyfile(ROOT / rel, out_dir / pathlib.Path(rel).name)

    def from_out(path):
        return os.path.relpath(path, out_dir).replace(os.sep, "/")

    text = (ROOT / ediciones.MANIFIESTO).read_text(encoding="utf-8")
    for old, new in [
        ('game_root = "../assets/game_root"', f'game_root = "{from_out(xex.parent)}"'),
        ('file_path = "../assets/game_root/default.xex"', f'file_path = "{from_out(xex)}"'),
        ('out_directory_path = "generated-android/default"',
         f'out_directory_path = "{from_out(out_dir.parent / "default")}"'),
    ]:
        if text.count(old) != 1:
            fail(f"{ediciones.MANIFIESTO} has changed: cannot find '{old}'")
        text = text.replace(old, new)
    manifest = out_dir / pathlib.Path(ediciones.MANIFIESTO).name
    manifest.write_text(text, encoding="utf-8")
    return manifest


def build_cli(sdk):
    for tool in ("cmake", "ninja", "clang++"):
        if not shutil.which(tool):
            fail(f"Cannot find '{tool}' in PATH (brew install cmake ninja; Xcode for clang).")
    if platform.system() != "Darwin":
        fail("The generator runs on a Mac (Apple Silicon or Intel).")
    preset = "mac-arm64" if platform.machine() == "arm64" else "mac-amd64"
    print(f"== rexglue CLI from the iOS SDK ({preset})")
    if subprocess.run(["cmake", "--preset", preset], cwd=sdk).returncode != 0:
        fail("Configuring the SDK for the Mac failed.")
    if subprocess.run(["cmake", "--build", f"out/build/{preset}", "--config", "Release",
                       "--target", "rexglue"], cwd=sdk).returncode != 0:
        fail("The rexglue CLI does not build.")
    exe = sdk / "out" / preset / "Release" / "rexglue"
    if not exe.is_file():
        candidates = sorted((sdk / "out").rglob("rexglue"), key=lambda p: p.stat().st_mtime,
                            reverse=True)
        candidates = [c for c in candidates if c.is_file() and os.access(c, os.X_OK)]
        if not candidates:
            fail(f"Built, but cannot find the rexglue executable under {sdk / 'out'}")
        exe = candidates[0]
    return exe


def main():
    ap = argparse.ArgumentParser(description="Generates the game's code for iOS.")
    ap.add_argument("--sdk", default=str(ROOT.parent / "rexglue-sdk-ios"))
    ap.add_argument("--xex", default=str(XEX),
                    help="your ISO's default.xex (default assets/game_root/default.xex)")
    ap.add_argument("--rexglue", default=None,
                    help="an already built rexglue CLI FROM THE iOS SDK; without it, it is "
                         "built (or checked up to date) first")
    args = ap.parse_args()
    sdk = pathlib.Path(args.sdk).resolve()
    xex = pathlib.Path(args.xex).resolve()
    out = GENERATED / "default"

    if not (sdk / ".nfsmw-ios" / "project-patches.applied").is_file():
        fail(f"No iOS SDK prepared in {sdk}.\n        Run first: python3 tools/ios/prepare_sdk.py")
    if not xex.is_file():
        fail(f"Cannot find {xex}.\n        Extract it from your ISO: "
             f"python3 tools/fase1_extraer.py \"<your>.iso\" --solo-xex")

    # The edition first: if it is not supported, better to know before
    # building the CLI.
    print("== Game edition")
    info = ediciones.detectar(str(xex))
    reference = info["tabla"] == ediciones.datos()["referencia"]
    print(f"[ok] {info['nombre']} ({info['id']}), language {info['idioma']}, "
          f"country {info['pais']}")
    if "aviso" in info:
        print(f"     {info['aviso']}")
    edition_dir = GENERATED / "edicion"
    shutil.rmtree(edition_dir, ignore_errors=True)
    if reference:
        manifest = reference_manifest(edition_dir, xex)
    else:
        print(f"     addresses translated with tools/ediciones/{info['tabla']}/direcciones.tsv")
        manifest = ediciones.aplicar(info["tabla"], edition_dir,
                                     xex=pathlib.Path(os.path.relpath(xex, APP)).as_posix())

    rexglue = pathlib.Path(args.rexglue).resolve() if args.rexglue else build_cli(sdk)
    if not rexglue.is_file():
        fail(f"Cannot find {rexglue}")
    print(f"[ok] {rexglue}")

    print("\n== Codegen")
    if subprocess.run([str(rexglue), "codegen", manifest.name], cwd=manifest.parent).returncode:
        fail("The codegen failed. See its output above.")
    if not (out / "sources.cmake").is_file():
        fail(f"The codegen finished but there is no {out / 'sources.cmake'}")

    # Black Edition content needs a larger record pool: edits to the generated
    # code (patch_game_pool.py, ios/src/game_pool.cpp). USA addresses only.
    if info["tabla"] == "usa":
        print("\n== Record pool")
        pool = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_pool.py")), "--dir", str(out)])
        if pool.returncode:
            fail("patch_game_pool.py failed. See its output above.")
        # Extra Options features (patch_game_extra_options.py,
        # ios/src/game_extra_options.cpp).
        extra = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_extra_options.py")), "--dir", str(out)])
        if extra.returncode:
            fail("patch_game_extra_options.py failed. See its output above.")
        print("\n== Native constant copies")
        copies = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_constant_copies.py")), "--dir", str(out)])
        if copies.returncode:
            fail("patch_game_constant_copies.py failed. See its output above.")
        print("\n== Native transform copies")
        transforms = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_transform_copies.py")), "--dir", str(out)])
        if transforms.returncode:
            fail("patch_game_transform_copies.py failed. See its output above.")
        print("\n== Deferred-call queue ordering")
        queue = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_deferred_queue.py")), "--dir", str(out)])
        if queue.returncode:
            fail("patch_game_deferred_queue.py failed. See its output above.")
        print("\n== Main loop tick count")
        ticks = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_frame_ticks.py")), "--dir", str(out)])
        if ticks.returncode:
            fail("patch_game_frame_ticks.py failed. See its output above.")
        world_step = subprocess.run([sys.executable, str(pathlib.Path(__file__).with_name(
            "patch_game_world_step_trace.py")), "--dir", str(out)])
        if world_step.returncode:
            fail("patch_game_world_step_trace.py failed. See its output above.")

    # Which edition this code is for: ios/CMakeLists.txt reads it (the game's
    # language and country, and whether the hooks need translating).
    with open(GENERATED / "edicion.json", "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"id": info["id"], "nombre": info["nombre"], "tabla": info["tabla"],
                   "referencia": reference, "idioma": info["idioma"], "pais": info["pais"],
                   "sha256": info["sha256"]}, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    n = sum(1 for _ in out.glob("*.cpp"))
    print(f"\n[ok] {n} .cpp files in {out}, edition {info['nombre']}")
    print("     Next: cd ios && cmake --preset ios && cmake --build --preset ios --target ipa")
    return 0


if __name__ == "__main__":
    sys.exit(main())
