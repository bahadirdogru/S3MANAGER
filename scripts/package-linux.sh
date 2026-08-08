#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.1.0}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "S3MANAGER paketleniyor (Linux) v${VERSION}..."

bash "$ROOT/scripts/build.sh"

OUT_DIR="$ROOT/dist/S3MANAGER"
if [[ ! -d "$OUT_DIR" ]]; then
  echo "Build ciktisi bulunamadi: $OUT_DIR" >&2
  exit 1
fi

TAR_PATH="$ROOT/dist/S3MANAGER-${VERSION}-linux-x86_64.tar.gz"
rm -f "$TAR_PATH"
tar -czf "$TAR_PATH" -C "$ROOT/dist" S3MANAGER
echo "tar.gz: $TAR_PATH ($(du -sh "$TAR_PATH" | cut -f1))"

APPDIR="$ROOT/dist/S3MANAGER.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -a "$OUT_DIR" "$APPDIR/usr/bin/S3MANAGER"

cat > "$APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/bin/S3MANAGER/S3MANAGER" "$@"
EOF
chmod +x "$APPDIR/AppRun"

cp assets/icon.png "$APPDIR/s3manager.png"

cat > "$APPDIR/S3MANAGER.desktop" << EOF
[Desktop Entry]
Type=Application
Name=S3MANAGER
Comment=DigitalOcean Spaces Desktop Manager
Exec=S3MANAGER
Icon=s3manager
Categories=Network;FileTransfer;Utility;
Terminal=false
EOF

ln -sf S3MANAGER.desktop "$APPDIR/usr/bin/S3MANAGER.desktop"
ln -sf ../s3manager.png "$APPDIR/usr/bin/.DirIcon"

APPIMAGETOOL="$ROOT/dist/appimagetool-x86_64.AppImage"
if [[ ! -f "$APPIMAGETOOL" ]]; then
  wget -q -O "$APPIMAGETOOL" \
    "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
  chmod +x "$APPIMAGETOOL"
fi

APPIMAGE_PATH="$ROOT/dist/S3MANAGER-${VERSION}-linux-x86_64.AppImage"
rm -f "$APPIMAGE_PATH"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE_PATH"
chmod +x "$APPIMAGE_PATH"
echo "AppImage: $APPIMAGE_PATH ($(du -sh "$APPIMAGE_PATH" | cut -f1))"
