#!/usr/bin/env bash
# S3MANAGER test runner — venv kurulumu ve pytest + coverage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -d "venv" ]; then
    echo "venv oluşturuluyor..."
    python -m venv venv
fi

# shellcheck disable=SC1091
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

pip install -q -r requirements.txt -r requirements-dev.txt

echo "Testler çalıştırılıyor..."
pytest --cov=src --cov-report=term-missing "$@"
