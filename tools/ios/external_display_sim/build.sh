#!/bin/sh
# Builds the external display harness (harness.mm) for the iOS Simulator and
# installs it on a simulator. The app's Info.plist is the game's own
# (ios/Info.plist.in, with its scene manifest), filled in for the harness.
#
#   tools/ios/external_display_sim/build.sh <simulator-udid> [build-dir]
#
# Then, with the simulator booted (display 2 is its external screen):
#   xcrun simctl io <udid> screenConfig --display=2 geometry 1920x1080@1
#   SIMCTL_CHILD_HARNESS_PLAY=8 xcrun simctl launch --console-pty <udid> org.nfsmw.external-display-harness
#   xcrun simctl io <udid> screenConfig --display=2 power on     # plugged in
#   xcrun simctl io <udid> screenshot --display=2 display.png
#   xcrun simctl io <udid> screenConfig --display=2 power off    # unplugged
# harness.mm lists its HARNESS_* switches. The Simulator shows nothing on its
# external screen for an app without a scene there: it cannot tell mirroring
# from black.
set -eu
UDID=${1:?simulator udid}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
OUT=${2:-$(mktemp -d "${TMPDIR:-/tmp}/nfsmw-external-display.XXXXXX")}
APP="$OUT/ExternalDisplayHarness.app"
rm -rf "$APP"
mkdir -p "$APP"
SDK=$(xcrun --sdk iphonesimulator --show-sdk-path)
ARCH=$(uname -m)
xcrun --sdk iphonesimulator clang++ -std=c++20 -x objective-c++ -fobjc-arc -Wall -Werror \
  -target "$ARCH-apple-ios18.0-simulator" -isysroot "$SDK" -I "$ROOT/ios/src" \
  "$HERE/harness.mm" "$ROOT/ios/src/external_display.mm" -x c++ "$ROOT/ios/src/boot_trace.cpp" \
  -framework UIKit -framework Metal -framework QuartzCore -framework Foundation -framework CoreGraphics \
  -o "$APP/ExternalDisplayHarness"
sed -e 's/@NFSMW_DISPLAY_NAME@/External display harness/g' \
    -e 's/@NFSMW_EXECUTABLE@/ExternalDisplayHarness/g' \
    -e 's/@NFSMW_BUNDLE_ID@/org.nfsmw.external-display-harness/g' \
    -e 's/@NFSMW_VERSION@/1.0/g' -e 's/@NFSMW_VERSION_CODE@/1/g' -e 's/@NFSMW_IOS_MIN@/18.0/g' \
    -e 's/<string>iPhoneOS<\/string>/<string>iPhoneSimulator<\/string>/' \
    "$ROOT/ios/Info.plist.in" > "$APP/Info.plist"
plutil -lint "$APP/Info.plist" >/dev/null
codesign -s - "$APP" >/dev/null 2>&1 || true
xcrun simctl install "$UDID" "$APP"
echo "installed $APP on $UDID"
