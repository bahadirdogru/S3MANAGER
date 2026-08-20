#!/usr/bin/env bash
# Verify bundled Mach-O files load on macOS 10.13 (no LC_DYLD_CHAINED_FIXUPS, minos <= 10.13).
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

check_macho() {
  local macho="$1"
  local label="$2"

  if otool -l "$macho" 2>/dev/null | grep -q 'cmd LC_DYLD_CHAINED_FIXUPS'; then
    echo "UYARI: $label LC_DYLD_CHAINED_FIXUPS iceriyor (macOS 10.13: load command 0x80000034)" >&2
    fail=1
  fi

  if otool -l "$macho" 2>/dev/null | grep -q 'cmd LC_BUILD_VERSION'; then
    if ! otool -l "$macho" 2>/dev/null | grep -q 'cmd LC_VERSION_MIN_MACOSX'; then
      echo "UYARI: $label yalnizca LC_BUILD_VERSION iceriyor (macOS 10.13 yukleyemez)" >&2
      fail=1
    fi
    local minos
    minos="$(otool -l "$macho" 2>/dev/null | awk '/cmd LC_BUILD_VERSION/{found=1} found && /minos/{print $2; exit}')"
    if [[ -n "$minos" ]]; then
      local major="${minos%%.*}"
      local minor="${minos#*.}"
      minor="${minor%%.*}"
      if [[ "$major" -gt 10 ]] || [[ "$major" -eq 10 && "$minor" -gt 13 ]]; then
        echo "UYARI: $label minos=${minos} (macOS 10.13 desteklenmiyor)" >&2
        fail=1
      fi
    fi
  fi
}

while IFS= read -r -d '' macho; do
  check_macho "$macho" "$macho"
done < <(find "$APP_PATH" \( -name '*.dylib' -o -path '*/MacOS/*' \) -type f -print0)

if [[ "$fail" -ne 0 ]]; then
  echo "Legacy macOS uyumluluk dogrulamasi basarisiz." >&2
  exit 1
fi

echo "Legacy macOS uyumluluk dogrulamasi gecti."
