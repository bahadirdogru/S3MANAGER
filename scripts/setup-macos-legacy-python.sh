#!/usr/bin/env bash
# Install python.org 3.10.11 (x86_64) for macOS 10.13+ PyInstaller builds.
# python-build-standalone x86_64 targets 10.15+ and may pull incompatible dylibs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_ROOT="$ROOT/.python-legacy"

PYTHON_VERSION="3.10.11"
PKG="python-${PYTHON_VERSION}-macos11.pkg"
PKG_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/${PKG}"

PYTHON_BIN="$INSTALL_ROOT/python/bin/python3.10"
if [[ -x "$PYTHON_BIN" ]]; then
  echo "Legacy Python zaten kurulu: $PYTHON_BIN"
  "$PYTHON_BIN" --version
  exit 0
fi

if [[ "$(uname -m)" != "x86_64" ]]; then
  echo "Legacy Python kurulumu yalnizca x86_64 icin: $(uname -m)" >&2
  exit 1
fi

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "python.org ${PYTHON_VERSION} indiriliyor..."
curl -fsSL "$PKG_URL" -o "$WORK/${PKG}"

echo "PKG aciliyor..."
mkdir -p "$WORK/xar" "$WORK/root"
xar -xf "$WORK/${PKG}" -C "$WORK/xar"

while IFS= read -r -d '' payload; do
  echo "Payload: $payload"
  (cd "$WORK/root" && cat "$payload" | gunzip -dc | cpio -i -d 2>/dev/null)
done < <(find "$WORK/xar" -name Payload -print0)

FRAMEWORK_SRC="$(find "$WORK/root" -type d -path '*/Python.framework/Versions/3.10' | head -1)"
if [[ -z "$FRAMEWORK_SRC" ]]; then
  echo "Python.framework bulunamadi (PKG icerigi):" >&2
  find "$WORK/root" -maxdepth 6 -type d 2>/dev/null | head -40 >&2 || true
  exit 1
fi

FRAMEWORK_ROOT="$(dirname "$(dirname "$FRAMEWORK_SRC")")"
rm -rf "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT/python/bin" "$INSTALL_ROOT/Frameworks"
cp -R "$FRAMEWORK_ROOT" "$INSTALL_ROOT/Frameworks/Python.framework"
ln -sf "../Frameworks/Python.framework/Versions/3.10/bin/python3.10" "$INSTALL_ROOT/python/bin/python3.10"

PYTHON_BIN="$INSTALL_ROOT/python/bin/python3.10"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "python3.10 calistirilamiyor: $PYTHON_BIN" >&2
  exit 1
fi

echo "Kuruldu: $PYTHON_BIN"
"$PYTHON_BIN" --version

LIBPYTHON="$INSTALL_ROOT/Frameworks/Python.framework/Versions/3.10/lib/libpython3.10.dylib"
if [[ -f "$LIBPYTHON" ]]; then
  echo "libpython: $LIBPYTHON"
  otool -L "$LIBPYTHON" | head -12 || true
fi
