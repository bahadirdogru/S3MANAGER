"""Uygulama yolu yardımcıları (geliştirme ve PyInstaller frozen)."""
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Kaynak kökü: geliştirmede proje kökü, frozen'da _MEIPASS."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def user_data_dir() -> Path:
    return Path.home() / ".pydamlaspace"


def log_file_path() -> Path:
    return user_data_dir() / "app.log"
