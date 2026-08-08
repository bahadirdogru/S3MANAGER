#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "pyDamlaSpace derleniyor (onedir)..."

if [[ ! -f venv/bin/activate ]]; then
  echo "venv bulunamadi. Olusturuluyor..."
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

pip install -q -r requirements.txt -r requirements-dev.txt

pyinstaller pydamlaspace.spec --clean --noconfirm

OUT_DIR="$ROOT/dist/pyDamlaSpace"
OUT="$OUT_DIR/pyDamlaSpace"
if [[ -f "$OUT" ]]; then
  SIZE=$(du -sh "$OUT_DIR" | cut -f1)
  echo "Basarili: $OUT_DIR ($SIZE)"
elif [[ -d "$ROOT/dist/pyDamlaSpace.app" ]]; then
  OUT_DIR="$ROOT/dist/pyDamlaSpace.app"
  echo "Basarili: $OUT_DIR"
else
  echo "Cikti bulunamadi (dist/pyDamlaSpace/pyDamlaSpace veya .app)" >&2
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "Hata: zip komutu bulunamadi. Lutfen zip paketini kurun." >&2
  exit 1
fi

ZIP_PATH="$ROOT/dist/pyDamlaSpace.zip"
rm -f "$ZIP_PATH"
(
  cd "$ROOT/dist"
  if [[ -d pyDamlaSpace ]]; then
    zip -rq pyDamlaSpace.zip pyDamlaSpace
  elif [[ -d pyDamlaSpace.app ]]; then
    zip -rq pyDamlaSpace.zip pyDamlaSpace.app
  fi
)
ZIP_SIZE=$(du -sh "$ZIP_PATH" | cut -f1)
echo "Arsiv: $ZIP_PATH ($ZIP_SIZE)"
