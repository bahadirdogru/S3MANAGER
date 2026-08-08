"""Uygulama yolu yardımcıları (geliştirme ve PyInstaller frozen)."""
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Kaynak kökü: geliştirmede proje kökü, frozen'da _MEIPASS."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def get_config_dir() -> Path:
    """Kullanıcı config dizini; eski ~/.pydamlaspace otomatik taşınır."""
    new_dir = Path.home() / ".s3manager"
    old_dir = Path.home() / ".pydamlaspace"
    if not new_dir.exists() and old_dir.exists():
        shutil.move(str(old_dir), str(new_dir))
    return new_dir


def user_data_dir() -> Path:
    return get_config_dir()


def log_file_path() -> Path:
    return user_data_dir() / "app.log"
