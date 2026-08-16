#!/usr/bin/env python3
"""Capture UI screenshots for docs/screenshots/. Run: python scripts/capture_screenshots.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from src.ui.qt.main_window import MainWindow
from src.ui.qt.settings_dialog import SettingsDialog
from src.ui.qt.styles import apply_app_theme
from src.config.credentials import CredentialsManager

OUT = ROOT / "docs" / "screenshots"

DEMO_FOLDERS = [
    {"name": "images", "path": "projects/website/images/", "type": "folder"},
    {"name": "documents", "path": "projects/website/documents/", "type": "folder"},
    {"name": "backups", "path": "projects/website/backups/", "type": "folder"},
    {"name": "static", "path": "projects/website/static/", "type": "folder"},
]

DEMO_FILES = [
    {
        "name": "hero-banner.png",
        "path": "projects/website/images/hero-banner.png",
        "type": "file",
        "size": 245760,
        "last_modified": "2026-08-15T14:30:00",
    },
    {
        "name": "index.html",
        "path": "projects/website/index.html",
        "type": "file",
        "size": 8192,
        "last_modified": "2026-08-14T09:15:00",
    },
    {
        "name": "styles.css",
        "path": "projects/website/static/styles.css",
        "type": "file",
        "size": 4096,
        "last_modified": "2026-08-13T16:45:00",
    },
    {
        "name": "readme.md",
        "path": "projects/website/documents/readme.md",
        "type": "file",
        "size": 2048,
        "last_modified": "2026-08-12T11:20:00",
    },
    {
        "name": "backup-2026-08-01.zip",
        "path": "projects/website/backups/backup-2026-08-01.zip",
        "type": "file",
        "size": 5242880,
        "last_modified": "2026-08-01T03:00:00",
    },
]


def inject_demo(win: MainWindow):
    win.current_path = "/projects/website/"
    win.model.set_items(DEMO_FOLDERS, DEMO_FILES)
    for item in win.model.items:
        if item.get("type") == "file":
            acl = "public-read" if item["name"] == "hero-banner.png" else "private"
            win.model.set_acl(item["path"], acl)
    win.update_breadcrumb()
    win.connection_indicator.set_status(
        True,
        "Bağlı: demo-bucket (fra1)\nTıklayın: Bağlantı ayarları",
    )
    win._set_status_activity("")


def setup_preview_demo(win: MainWindow):
    pp = win.preview_panel
    pp.lbl_title.setText("hero-banner.png")
    pp.lbl_meta.setText("Boyut: 240 KB · Tarih: 15 Ağu 2026 · public-read")
    pp.btn_download.setEnabled(True)
    pp.btn_share.setEnabled(True)
    pp.btn_properties.setEnabled(True)
    pp.lbl_placeholder.setVisible(False)
    pp.text_view.setVisible(False)
    pixmap = QPixmap(str(ROOT / "assets" / "icon.png"))
    pp.image_label.setPixmap(
        pixmap.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    )
    pp.image_label.setVisible(True)


def grab(widget, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    widget.grab().save(str(path))
    print(f"Saved {path}")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)

    # Gerçek bağlantıyı atla — demo verisi korunur
    CredentialsManager.get_credentials = lambda self: None

    win = MainWindow()
    win._update_worker = None
    inject_demo(win)
    setup_preview_demo(win)
    win.splitter.setSizes([720, 420])
    win.resize(1240, 800)
    win.show()

    settings_dlg = None

    def step_dark():
        inject_demo(win)
        setup_preview_demo(win)
        apply_app_theme("dark", settings=win.settings, persist=False)
        win.theme_switch.set_mode("dark")
        QTimer.singleShot(800, lambda: grab(win, OUT / "main-dark.png"))

    def step_light():
        apply_app_theme("light", settings=win.settings, persist=False)
        win.theme_switch.set_mode("light")
        QTimer.singleShot(800, lambda: grab(win, OUT / "main-light.png"))

    def step_preview():
        apply_app_theme("dark", settings=win.settings, persist=False)
        win.theme_switch.set_mode("dark")
        win.splitter.setSizes([680, 460])
        setup_preview_demo(win)
        QTimer.singleShot(800, lambda: grab(win, OUT / "preview.png"))

    def step_settings():
        global settings_dlg
        settings_dlg = SettingsDialog(win)
        settings_dlg.tabs.setCurrentIndex(4)
        settings_dlg.resize(720, 520)
        settings_dlg.show()
        QTimer.singleShot(900, lambda: grab(settings_dlg, OUT / "settings.png"))

    def finish():
        if settings_dlg:
            settings_dlg.close()
        app.quit()

    QTimer.singleShot(1500, step_dark)
    QTimer.singleShot(3500, step_light)
    QTimer.singleShot(5500, step_preview)
    QTimer.singleShot(7500, step_settings)
    QTimer.singleShot(9000, finish)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
