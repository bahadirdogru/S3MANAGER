#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON=""
for candidate in python py python3; do
  if command -v "$candidate" &>/dev/null && "$candidate" --version &>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "Hata: calisan bir Python bulunamadi (python, py veya python3)." >&2
  exit 1
fi

if [[ ! -d venv ]]; then
  echo "venv olusturuluyor..."
  "$PYTHON" -m venv venv
fi

if [[ -f venv/Scripts/activate ]]; then
  # shellcheck disable=SC1091
  source venv/Scripts/activate
elif [[ -f venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
else
  echo "Hata: venv aktivasyon dosyasi bulunamadi." >&2
  exit 1
fi

echo "Bagimliliklar kuruluyor..."
pip install -q -r requirements.txt

echo "S3MANAGER baslatiliyor..."
python src/main.py
