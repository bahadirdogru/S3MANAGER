"""PyInstaller entry for Intel macOS (PySide2 + PySide6 shim). Development uses src/main.py directly."""

import sys
from pathlib import Path

_SHIM_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _SHIM_ROOT.parent.parent

if str(_SHIM_ROOT) not in sys.path:
    sys.path.insert(0, str(_SHIM_ROOT))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.main import main

if __name__ == "__main__":
    main()
