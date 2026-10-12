#!/bin/bash
# Builds Cubegen.app (SwiftUI + SceneKit, no Xcode project needed) - like the robot generator's RobotViewer.app.
#   app/build.sh [output dir]     default: ../output/app
# Needs: Xcode command line tools (swiftc), ImageMagick (app icon and UI icons, app/make_icons.sh).
# The app runs the cubegen package it carries (Contents/Resources/python/cubegen) with Python 3.9+ from Homebrew, python.org or the command line tools;
# Blender and ImageMagick are found like on the command line (`python3 -m cubegen doctor`).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT="${1:-$ROOT/output/app}"
APP="$OUT/Cubegen.app"
BUILD="$HERE/.build"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$ROOT/cubegen/__init__.py")"
MIN_MACOS=13.0
mkdir -p "$BUILD" "$OUT"

echo "> compiling Cubegen $VERSION (universal: arm64 + x86_64, macOS $MIN_MACOS+)"
for arch in arm64 x86_64; do
  swiftc -O -parse-as-library -swift-version 5 -target "$arch-apple-macos$MIN_MACOS" \
    -framework SwiftUI -framework SceneKit -framework AppKit \
    "$HERE"/Sources/*.swift -o "$BUILD/Cubegen-$arch"
done
lipo -create "$BUILD/Cubegen-arm64" "$BUILD/Cubegen-x86_64" -output "$BUILD/Cubegen"

echo "> bundling $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/python"
cp "$BUILD/Cubegen" "$APP/Contents/MacOS/Cubegen"
# the generator itself: the package without caches (same files as the Blender add-on bundle)
rsync -a --exclude "__pycache__" --exclude "*.pyc" "$ROOT/cubegen" "$APP/Contents/Resources/python/"

if command -v magick >/dev/null; then
  "$HERE/make_icons.sh" "$APP/Contents/Resources"   # UI icons (view_*, action_*, category_*, cube)
  ICONSET="$BUILD/AppIcon.iconset"
  rm -rf "$ICONSET" && mkdir -p "$ICONSET"
  # an isometric cube in the game's hazard orange with a cyan glow edge, on the dark UI background
  magick -define png:exclude-chunks=date,time -size 1024x1024 xc:none \
    -fill "#1e1e24" -draw "roundrectangle 0,0 1023,1023 190,190" \
    -fill "#f2a64a" -draw "polygon 512,170 812,343 512,516 212,343" \
    -fill "#d0782a" -draw "polygon 212,343 512,516 512,862 212,689" \
    -fill "#9c5418" -draw "polygon 812,343 512,516 512,862 812,689" \
    -fill none -stroke "#39d0ff" -strokewidth 18 -draw "polyline 212,343 512,516 812,343" \
    -draw "line 512,516 512,862" "$BUILD/icon_1024.png"
  for s in 16 32 64 128 256 512; do
    magick "$BUILD/icon_1024.png" -resize ${s}x${s} "$ICONSET/icon_${s}x${s}.png"
    magick "$BUILD/icon_1024.png" -resize $((s * 2))x$((s * 2)) "$ICONSET/icon_${s}x${s}@2x.png"
  done
  iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/AppIcon.icns"
fi

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Cubegen</string>
  <key>CFBundleDisplayName</key><string>Cubegen – Cube Escape Model Generator</string>
  <key>CFBundleIdentifier</key><string>com.cubeescape.cubegen</string>
  <key>CFBundleExecutable</key><string>Cubegen</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>$VERSION</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>$MIN_MACOS</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSPrincipalClass</key><string>NSApplication</string>
</dict>
</plist>
PLIST

codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || echo "warning: ad-hoc signing failed"
echo "> done: $APP"
