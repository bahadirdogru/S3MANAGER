#!/usr/bin/env bash
# Verify Intel macOS bundle does not contain real PySide6/Qt6 alongside PySide2.
set -euo pipefail

APP_PATH="${1:-}"
if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "Kullanim: $0 path/to/S3MANAGER.app" >&2
  exit 1
fi

CONTENTS="$APP_PATH/Contents"
FRAMEWORKS="$CONTENTS/Frameworks"
RESOURCES="$CONTENTS/Resources"

fail=0

check_absent() {
  local pattern="$1"
  local label="$2"
  local matches
  matches="$(find "$APP_PATH" -iname "$pattern" 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    echo "HATA: $label bulundu (Intel build yalnizca PySide2/Qt5 icermeli):" >&2
    echo "$matches" >&2
    fail=1
  fi
}

# Real PySide6 / Qt6 must not be bundled (shim is pure Python under Resources).
check_absent "shiboken6*" "shiboken6"
check_absent "libPySide6*.dylib" "libPySide6"
check_absent "PySide6.abi3.so" "PySide6.abi3.so"
check_absent "Qt6Core.framework" "Qt6Core.framework"
check_absent "Qt6Gui.framework" "Qt6Gui.framework"
check_absent "Qt6Widgets.framework" "Qt6Widgets.framework"

# PySide2 / Qt5 should be present.
has_pyside2=0
if find "$APP_PATH" \( -iname 'libshiboken2*.dylib' -o -iname 'libpyside2*.dylib' \) -print -quit 2>/dev/null | grep -q .; then
  has_pyside2=1
fi

if [[ "$has_pyside2" -eq 0 ]]; then
  echo "HATA: PySide2 binary bulunamadi (libshiboken2/libpyside2)." >&2
  fail=1
fi

# Smoke launch: runtime hook conflict fails immediately on stderr.
BIN="$CONTENTS/MacOS/S3MANAGER"
if [[ -x "$BIN" ]]; then
  stderr_file="$(mktemp)"
  "$BIN" 2>"$stderr_file" &
  launch_pid=$!
  sleep 3
  if kill -0 "$launch_pid" 2>/dev/null; then
    kill "$launch_pid" 2>/dev/null || true
    wait "$launch_pid" 2>/dev/null || true
  else
    wait "$launch_pid" 2>/dev/null || true
  fi
  if grep -q "run-time hook for 'PySide6'" "$stderr_file"; then
    echo "HATA: PySide6 runtime hook cakismasi algilandi." >&2
    cat "$stderr_file" >&2
    fail=1
  fi
  rm -f "$stderr_file"
fi

if [[ "$fail" -ne 0 ]]; then
  echo "Intel macOS bundle dogrulamasi basarisiz." >&2
  exit 1
fi

echo "Intel macOS bundle dogrulamasi gecti (PySide2 only, PySide6/Qt6 yok)."
