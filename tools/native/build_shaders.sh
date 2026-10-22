#!/bin/sh
# NFSMW's shaders as native Metal libraries for iOS, from your own game files.
#
#   sh tools/native/build_shaders.sh GAME.iso [OUT_DIR]
#   sh tools/native/build_shaders.sh - [OUT_DIR]   (containers already in OUT_DIR)
#
# 1. tools/native/nfsmw_shader_containers.py: the shader containers from
#    NFS/ZZDATA0.BIN, rewritten in the layout XenosRecomp reads.
# 2. tools/xenosrecomp (MIT, hedge-dev's XenosRecomp in the Metal-capable
#    lineage used by Theft4/MCLA 4iOS, with NFSMW fixes): one source per
#    shader that compiles as Metal with -D__air__.
# 3. tools/native/rewrite_shadow_filter.py: the soft-shadow filter's 9
#    fetches as one call (4 gathers; see shader_common.h).
#    tools/native/rewrite_shadow_caster_alpha.py: the shadow caster's cut-out
#    behind specialization bit 12 (compiled out where c1.x is 0).
# 4. xcrun metal: one .metallib per shader, named vs_/ps_<microcode hash>.
# 5. tools/native/constant_ranges.py: the float constants each shader reads
#    (lib/constant_ranges.txt), so the renderer handles only those.
# 6. tools/native/texture_masks.py: conservative texture-slot metadata.
#
# Output (default ~/Library/Caches/nfsmw-ios/shaders): containers/, msl/,
# air/, lib/. Nothing derived from the game goes into the repository.
#
# The libraries are built for the app's oldest iOS (IOS_MIN, default 26.0, as
# CMAKE_OSX_DEPLOYMENT_TARGET in ios/CMakePresets.json). Without it the metal
# compiler targets its SDK's own iOS (Xcode 27: iOS 27), and iOS 26 cannot load
# them: the movies (shaders compiled on the device) played, then nothing drew.
set -eu
iso=${1:?usage: build_shaders.sh GAME.iso [OUT_DIR]}
out=${2:-"$HOME/Library/Caches/nfsmw-ios/shaders"}
repo=$(cd "$(dirname "$0")/../.." && pwd)
sdk=${REXGLUE_SDK:-"$repo/../rexglue-sdk-ios"}
tool="$out/bin/xenosrecomp"
ios_min=${IOS_MIN:-26.0}

mkdir -p "$out/bin" "$out/msl" "$out/air" "$out/lib"
clang++ -std=c++20 -O2 -Wno-switch -Wno-unused-variable -Wno-null-arithmetic -fms-extensions \
  -I"$sdk/thirdparty/fmt/include" -include "$repo/tools/xenosrecomp/pch.h" \
  "$repo/tools/xenosrecomp/shader_recompiler.cpp" "$repo/tools/xenosrecomp/main.cpp" -o "$tool"

if [ "$iso" != "-" ]; then
  python3 "$repo/tools/native/nfsmw_shader_containers.py" --iso "$iso" "$out/containers"
fi

translated=0
compiled=0
failed=""
for container in "$out"/containers/*.bin; do
  name=$(basename "$container" .bin)
  if ! "$tool" "$container" "$out/msl/$name.hlsl" "$repo/tools/xenosrecomp/shader_common.h"; then
    failed="$failed $name(translate)"
    continue
  fi
  translated=$((translated + 1))
  python3 "$repo/tools/native/rewrite_shadow_filter.py" "$out/msl/$name.hlsl" | grep -v " 0 blocks" || true
  python3 "$repo/tools/native/rewrite_shadow_caster_alpha.py" "$out/msl/$name.hlsl" | grep -v ": 0 shadow" || true
  cp "$out/msl/$name.hlsl" "$out/air/$name.metal"
  if xcrun -sdk iphoneos metal -w -O2 -std=metal3.1 -D__air__ \
       -mios-version-min="$ios_min" -c "$out/air/$name.metal" -o "$out/air/$name.air" &&
     xcrun -sdk iphoneos metal -mios-version-min="$ios_min" "$out/air/$name.air" -o "$out/lib/$name.metallib"; then
    compiled=$((compiled + 1))
  else
    failed="$failed $name(metal)"
  fi
done
cp "$out/containers/vertex_inputs.txt" "$out/lib/"
python3 "$repo/tools/native/constant_ranges.py" "$out/msl" "$out/lib/constant_ranges.txt"
python3 "$repo/tools/native/texture_masks.py" "$out/msl" "$out/lib/texture_masks.txt"
echo "$translated translated, $compiled Metal libraries in $out/lib"
# Every library in lib/ goes into the app, including hand-built bring-up
# variants (ps_<key>_dbgN, from their own .metal in air/): any built for a newer
# iOS than $ios_min does not load there (on iOS 26: "3 shader libraries could
# not be loaded"). Rebuild those from air/ and fail if one still differs.
for lib in "$out"/lib/*.metallib; do
  target=$(strings -a "$lib" | grep -o -m1 'apple-ios[0-9.]*' || true)
  case "$target" in
    apple-ios"$ios_min"*) ;;
    *)
      name=$(basename "$lib" .metallib)
      if [ -f "$out/air/$name.metal" ] &&
         xcrun -sdk iphoneos metal -w -O2 -std=metal3.1 -D__air__ -mios-version-min="$ios_min" \
           -c "$out/air/$name.metal" -o "$out/air/$name.air" &&
         xcrun -sdk iphoneos metal -mios-version-min="$ios_min" "$out/air/$name.air" -o "$lib"; then
        echo "rebuilt $name for iOS $ios_min (was ${target:-unknown})"
      else
        failed="$failed $name(ios-version)"
      fi
      ;;
  esac
done
if [ -n "$failed" ]; then
  echo "failed:$failed"
  exit 1
fi
