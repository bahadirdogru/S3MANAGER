#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.1.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ARCH="$(uname -m)"
case "$ARCH" in
  arm64)
    SUFFIX="macos-arm64"
    SPEC="s3manager.spec"
    REQ_FILE="requirements.txt"
    ;;
  x86_64)
    SUFFIX="macos-x86_64"
    SPEC="s3manager-macos-x86_64.spec"
    REQ_FILE="requirements-macos-x86_64.txt"
    export MACOSX_DEPLOYMENT_TARGET="${MACOSX_DEPLOYMENT_TARGET:-10.13}"
    export S3MANAGER_LEGACY_MACOS=1
    ;;
  *)
    echo "Desteklenmeyen mimari: $ARCH" >&2
    exit 1
    ;;
esac

echo "S3MANAGER paketleniyor (macOS ${ARCH}) v${VERSION}..."

ensure_icns() {
  if [[ -f assets/icon.icns ]]; then
    return
  fi
  if [[ "$(uname)" != "Darwin" ]]; then
    echo "assets/icon.icns bulunamadi ve macOS disinda uretilemiyor." >&2
    exit 1
  fi
  echo "icon.icns uretiliyor..."
  ICONSET="assets/icon.iconset"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  for size in 16 32 128 256 512; do
    d=$((size * 2))
    sips -z "$size" "$size" assets/icon.png --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
    sips -z "$d" "$d" assets/icon.png --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o assets/icon.icns
  rm -rf "$ICONSET"
}

ensure_icns
SPEC="$SPEC" REQ_FILE="$REQ_FILE" bash "$ROOT/scripts/build.sh"

APP_PATH="$ROOT/dist/S3MANAGER.app"
if [[ ! -d "$APP_PATH" ]]; then
  echo "S3MANAGER.app bulunamadi: $APP_PATH" >&2
  exit 1
fi

STAGING="$ROOT/dist/dmg-staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

DMG_PATH="$ROOT/dist/S3MANAGER-${VERSION}-${SUFFIX}.dmg"
rm -f "$DMG_PATH"
hdiutil create -volname "S3MANAGER" -srcfolder "$STAGING" -ov -format UDZO "$DMG_PATH"
rm -rf "$STAGING"

echo "DMG: $DMG_PATH ($(du -sh "$DMG_PATH" | cut -f1))"
