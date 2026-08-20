#!/usr/bin/env bash
# Replace incompatible bundled dylibs (e.g. Homebrew libintl with LC_DYLD_CHAINED_FIXUPS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
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

has_chained_fixups() {
  otool -l "$1" 2>/dev/null | grep -q 'cmd LC_DYLD_CHAINED_FIXUPS'
}

needs_libintl() {
  local binary="$1"
  otool -L "$binary" 2>/dev/null | grep -q 'libintl'
}

LIBPYTHON="$FRAMEWORKS/libpython3.10.dylib"
LIBINTL_DST="$FRAMEWORKS/libintl.8.dylib"
LIBINTL_SRC="$ROOT/.python-legacy/libintl/lib/libintl.8.dylib"

replace_libintl=false
if [[ -f "$LIBINTL_DST" ]] && has_chained_fixups "$LIBINTL_DST"; then
  replace_libintl=true
fi
if [[ -f "$LIBPYTHON" ]] && needs_libintl "$LIBPYTHON"; then
  replace_libintl=true
fi

if [[ "$replace_libintl" == "true" ]]; then
  echo "10.13 uyumlu libintl yerlestiriliyor..."
  bash "$ROOT/scripts/build-macos-legacy-libintl.sh"
  cp "$LIBINTL_SRC" "$LIBINTL_DST"
  install_name_tool -id "@rpath/libintl.8.dylib" "$LIBINTL_DST"

  if [[ -f "$LIBPYTHON" ]]; then
    while IFS= read -r old_path; do
      [[ -z "$old_path" ]] && continue
      install_name_tool -change "$old_path" "@rpath/libintl.8.dylib" "$LIBPYTHON"
    done < <(otool -L "$LIBPYTHON" | awk '/libintl/{print $1}')
  fi
fi

# Remove libintl if nothing in the app references it.
if [[ -f "$LIBINTL_DST" ]]; then
  referenced=false
  while IFS= read -r -d '' macho; do
    if needs_libintl "$macho"; then
      referenced=true
      break
    fi
  done < <(find "$APP_PATH" \( -name '*.dylib' -o -perm -111 \) -type f -print0 2>/dev/null)

  if [[ "$referenced" == "false" ]]; then
    echo "Kullanilmayan libintl kaldiriliyor..."
    rm -f "$LIBINTL_DST"
  fi
fi

echo "Legacy dylib duzeltmesi tamamlandi."
