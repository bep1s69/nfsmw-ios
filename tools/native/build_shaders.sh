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
# 4. xcrun metal: one .metallib per shader, named vs_/ps_<microcode hash>.
#
# Output (default ~/Library/Caches/nfsmw-ios/shaders): containers/, msl/,
# air/, lib/. Nothing derived from the game goes into the repository.
set -eu
iso=${1:?usage: build_shaders.sh GAME.iso [OUT_DIR]}
out=${2:-"$HOME/Library/Caches/nfsmw-ios/shaders"}
repo=$(cd "$(dirname "$0")/../.." && pwd)
sdk=${REXGLUE_SDK:-"$repo/../rexglue-sdk-ios"}
tool="$out/bin/xenosrecomp"

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
  cp "$out/msl/$name.hlsl" "$out/air/$name.metal"
  if xcrun -sdk iphoneos metal -w -O2 -std=metal3.1 -D__air__ \
       -c "$out/air/$name.metal" -o "$out/air/$name.air" &&
     xcrun -sdk iphoneos metal "$out/air/$name.air" -o "$out/lib/$name.metallib"; then
    compiled=$((compiled + 1))
  else
    failed="$failed $name(metal)"
  fi
done
cp "$out/containers/vertex_inputs.txt" "$out/lib/"
echo "$translated translated, $compiled Metal libraries in $out/lib"
if [ -n "$failed" ]; then
  echo "failed:$failed"
  exit 1
fi
