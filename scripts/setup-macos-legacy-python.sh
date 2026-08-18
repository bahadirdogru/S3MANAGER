#!/usr/bin/env bash
# Install python-build-standalone (x86_64) for macOS 10.13+ compatible PyInstaller builds.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL_ROOT="$ROOT/.python-legacy"

# Pinned release — targets macOS 10.13+ (see python-build-standalone docs).
PBS_TAG="20241016"
PBS_ARCHIVE="cpython-3.10.15+${PBS_TAG}-x86_64-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/${PBS_ARCHIVE}"

PYTHON_BIN="$INSTALL_ROOT/python/bin/python3.10"
if [[ -x "$PYTHON_BIN" ]]; then
  echo "Legacy Python zaten kurulu: $PYTHON_BIN"
  "$PYTHON_BIN" --version
  exit 0
fi

echo "python-build-standalone indiriliyor (${PBS_ARCHIVE})..."
rm -rf "$INSTALL_ROOT"
mkdir -p "$INSTALL_ROOT"
curl -fsSL "$PBS_URL" | tar -xz -C "$INSTALL_ROOT"

if [[ ! -x "$PYTHON_BIN" ]]; then
  # Fallback: locate python3.10 in extracted tree
  PYTHON_BIN="$(find "$INSTALL_ROOT" -type f -name 'python3.10' | head -1)"
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "python3.10 bulunamadi: $INSTALL_ROOT" >&2
  exit 1
fi

echo "Kuruldu: $PYTHON_BIN"
"$PYTHON_BIN" --version

LIBPYTHON="$(find "$INSTALL_ROOT" -name 'libpython3.10.dylib' | head -1)"
if [[ -n "$LIBPYTHON" ]]; then
  echo "libpython: $LIBPYTHON"
  otool -L "$LIBPYTHON" | head -10 || true
fi
