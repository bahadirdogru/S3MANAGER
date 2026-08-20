#!/usr/bin/env bash
# Build libintl.8.dylib with macOS 10.13 deployment target (no LC_DYLD_CHAINED_FIXUPS).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PREFIX="$ROOT/.python-legacy/libintl"
LIBINTL="$PREFIX/lib/libintl.8.dylib"

if [[ -f "$LIBINTL" ]]; then
  echo "Legacy libintl zaten kurulu: $LIBINTL"
  exit 0
fi

GETTEXT_VERSION="0.22.5"
WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

echo "gettext ${GETTEXT_VERSION} derleniyor (min macOS 10.13)..."
curl -fsSL "https://ftp.gnu.org/gnu/gettext/gettext-${GETTEXT_VERSION}.tar.xz" \
  | tar -xJ -C "$WORK"

cd "$WORK/gettext-${GETTEXT_VERSION}"

export MACOSX_DEPLOYMENT_TARGET="10.13"
export CFLAGS="-mmacosx-version-min=10.13 -O2"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="-mmacosx-version-min=10.13 -Wl,-no_fixup_chains"

./configure \
  --prefix="$PREFIX" \
  --enable-shared \
  --disable-static \
  --disable-java \
  --disable-csharp \
  --disable-docs \
  --disable-native-java \
  --without-git \
  --without-cvs \
  --without-emacs \
  --without-xz \
  --with-included-gettext \
  --with-included-glib \
  --with-included-libcroco \
  --with-included-libunistring \
  --quiet

make -j"$(sysctl -n hw.ncpu 2>/dev/null || echo 2)"
make install

if [[ ! -f "$LIBINTL" ]]; then
  echo "libintl derlemesi basarisiz: $LIBINTL" >&2
  exit 1
fi

install_name_tool -id "@rpath/libintl.8.dylib" "$LIBINTL"
echo "Kuruldu: $LIBINTL"
