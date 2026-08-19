#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SPEC="${SPEC:-s3manager.spec}"
REQ_FILE="${REQ_FILE:-requirements.txt}"
LEGACY_MACOS="${S3MANAGER_LEGACY_MACOS:-0}"

echo "S3MANAGER derleniyor (onedir) — spec: ${SPEC}..."

PYTHON_BIN="python3"
if [[ "$LEGACY_MACOS" == "1" ]]; then
  bash "$ROOT/scripts/setup-macos-legacy-python.sh"
  PYTHON_BIN="$ROOT/.python-legacy/python/bin/python3.10"
  if [[ ! -x "$PYTHON_BIN" ]]; then
    echo "Legacy Python bulunamadi: $PYTHON_BIN" >&2
    exit 1
  fi
  echo "Legacy Python: $PYTHON_BIN"
  rm -rf venv
fi

if [[ ! -f venv/bin/activate ]]; then
  echo "venv bulunamadi. Olusturuluyor..."
  "$PYTHON_BIN" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

if [[ "$LEGACY_MACOS" == "1" ]]; then
  # requirements-dev.txt pulls PySide6 via requirements.txt; Intel build must use PySide2 only.
  pip install -q -r "$REQ_FILE"
  pip install -q "pyinstaller>=6.0"
else
  pip install -q -r "$REQ_FILE" -r requirements-dev.txt
fi

pyinstaller "$SPEC" --clean --noconfirm

OUT_DIR="$ROOT/dist/S3MANAGER"
OUT="$OUT_DIR/S3MANAGER"
if [[ -f "$OUT" ]]; then
  SIZE=$(du -sh "$OUT_DIR" | cut -f1)
  echo "Basarili: $OUT_DIR ($SIZE)"
elif [[ -d "$ROOT/dist/S3MANAGER.app" ]]; then
  OUT_DIR="$ROOT/dist/S3MANAGER.app"
  echo "Basarili: $OUT_DIR"
  if [[ "$LEGACY_MACOS" == "1" ]]; then
    bash "$ROOT/scripts/verify-macos-legacy-binary.sh" "$OUT_DIR"
    bash "$ROOT/scripts/verify-macos-x86_64-bundle.sh" "$OUT_DIR"
  fi
else
  echo "Cikti bulunamadi (dist/S3MANAGER/S3MANAGER veya .app)" >&2
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "Hata: zip komutu bulunamadi. Lutfen zip paketini kurun." >&2
  exit 1
fi

ZIP_PATH="$ROOT/dist/S3MANAGER.zip"
rm -f "$ZIP_PATH"
(
  cd "$ROOT/dist"
  if [[ -d S3MANAGER ]]; then
    zip -rq S3MANAGER.zip S3MANAGER
  elif [[ -d S3MANAGER.app ]]; then
    zip -rq S3MANAGER.zip S3MANAGER.app
  fi
)
ZIP_SIZE=$(du -sh "$ZIP_PATH" | cut -f1)
echo "Arsiv: $ZIP_PATH ($ZIP_SIZE)"
