#!/usr/bin/env bash
# Verify bundled dylibs are loadable on macOS 10.13 (no LC_BUILD_VERSION-only binaries).
set -euo pipefail

APP_PATH="${1:-}"
if [[ -z "$APP_PATH" || ! -d "$APP_PATH" ]]; then
  echo "Kullanim: $0 path/to/S3MANAGER.app" >&2
  exit 1
fi

FRAMEWORKS="$APP_PATH/Contents/Frameworks"
if [[ ! -d "$FRAMEWORKS" ]]; then
  echo "Frameworks dizini yok: $FRAMEWORKS" >&2
  exit 1
fi

fail=0
while IFS= read -r -d '' dylib; do
  if otool -l "$dylib" 2>/dev/null | grep -q 'cmd LC_BUILD_VERSION'; then
    if ! otool -l "$dylib" 2>/dev/null | grep -q 'cmd LC_VERSION_MIN_MACOSX'; then
      echo "UYARI: $dylib yalnizca LC_BUILD_VERSION iceriyor (macOS 10.13 yukleyemez)" >&2
      fail=1
    fi
  fi
done < <(find "$FRAMEWORKS" -name '*.dylib' -print0)

if [[ "$fail" -ne 0 ]]; then
  echo "Legacy macOS uyumluluk dogrulamasi basarisiz." >&2
  exit 1
fi

echo "Legacy macOS uyumluluk dogrulamasi gecti."
