"""Merkezi ayarlar dialogu — bağlantı, metadata, görünüm, günlük, yardım."""
import configparser
import os
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTabWidget, QWidget, QScrollArea,
    QPlainTextEdit, QRadioButton, QMessageBox, QApplication,
)

from src.config.settings import Settings
from src.ui.qt.dialogs import LoginDialog
from src.ui.qt.styles import apply_app_theme, apply_dialog_elevation, current_theme_mode, update_dialog_elevation
from src.ui.qt.upload_metadata_panel import UploadMetadataPanel
from src.ui.qt.incomplete_uploads_panel import IncompleteUploadsPanel
from src.utils.log_viewer import read_log_tail
from src.utils.paths import get_config_dir, log_file_path
from src.version import __version__, GITHUB_REPO


def _mask_access_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        return "kayıtlı değil"
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"


def _open_local_folder(path: Path):
    path = Path(path)
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    url = QUrl.fromLocalFile(str(path.resolve()))
    if not QDesktopServices.openUrl(url):
        if os.name == "nt":
            os.startfile(str(path))  # noqa: S606
        else:
            QDesktopServices.openUrl(url)


class ConnectionTab(QWidget):
  """Bağlantı bilgisi — salt okunur + düzenleme aksiyonları."""

  def __init__(self, settings: Settings, on_edit_connection, parent=None):
    super().__init__(parent)
    self.settings = settings
    self._on_edit_connection = on_edit_connection
    self._build_ui()
    self.refresh()

  def _build_ui(self):
    outer = QVBoxLayout(self)
    outer.setContentsMargins(8, 8, 8, 8)
    outer.setSpacing(10)

    scroll = QScrollArea()
    scroll.setObjectName("SettingsScrollArea")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    body = QWidget()
    body.setObjectName("SettingsScrollContent")
    layout = QVBoxLayout(body)
    layout.setSpacing(10)

    warning = QLabel(
      "Kimlik bilgileri düz metin olarak config.ini dosyasında saklanır. "
      "Paylaşımlı veya güvensiz ortamlarda dikkatli olun."
    )
    warning.setObjectName("SettingsInfoLabel")
    warning.setWordWrap(True)
    layout.addWidget(warning)

    form = QFrame()
    form.setObjectName("FormFrame")
    form.setAutoFillBackground(True)
    form_layout = QVBoxLayout(form)
    form_layout.setContentsMargins(16, 16, 16, 16)
    form_layout.setSpacing(8)

    config_dir = get_config_dir()
    self._fields = {}
    rows = [
      ("Config dizini", str(config_dir)),
      ("Config dosyası", str(self.settings.config_file)),
      ("Bucket", ""),
      ("Bölge", ""),
      ("Endpoint", ""),
      ("Access Key", ""),
      ("Secret Key", "****"),
    ]
    for label_text, _ in rows:
      form_layout.addWidget(QLabel(label_text + ":"))
      field = QLineEdit()
      field.setReadOnly(True)
      field.setAutoFillBackground(True)
      form_layout.addWidget(field)
      self._fields[label_text] = field

    layout.addWidget(form)

    btn_row = QHBoxLayout()
    self.btn_edit = QPushButton("Bağlantıyı düzenle")
    self.btn_edit.setObjectName("SecondaryButton")
    self.btn_edit.clicked.connect(self._edit_connection)
    self.btn_open = QPushButton("Config klasörünü aç")
    self.btn_open.setObjectName("SecondaryButton")
    self.btn_open.clicked.connect(lambda: _open_local_folder(config_dir))
    btn_row.addWidget(self.btn_edit)
    btn_row.addWidget(self.btn_open)
    btn_row.addStretch()
    layout.addLayout(btn_row)

    layout.addStretch()
    scroll.setWidget(body)
    outer.addWidget(scroll)

  def _edit_connection(self):
    self._on_edit_connection()
    self.refresh()

  def refresh(self):
    config_dir = get_config_dir()
    self._fields["Config dizini"].setText(str(config_dir))
    self._fields["Config dosyası"].setText(str(self.settings.config_file))

    bucket = region = endpoint = key = ""
    if self.settings.config_file.exists():
      config = configparser.ConfigParser()
      config.read(self.settings.config_file)
      if "digitalocean" in config:
        section = config["digitalocean"]
        bucket = section.get("bucket", "").strip()
        region = section.get("region", "").strip()
        endpoint = section.get("endpoint", "").strip()
        key = section.get("spaces_key", "").strip()

    self._fields["Bucket"].setText(bucket or "—")
    self._fields["Bölge"].setText(region or "—")
    self._fields["Endpoint"].setText(endpoint or "—")
    self._fields["Access Key"].setText(_mask_access_key(key))
    self._fields["Secret Key"].setText("****" if key else "kayıtlı değil")


class AppearanceTab(QWidget):
  """Tema seçimi — toolbar ThemeSwitch ile senkron."""

  def __init__(self, main_window, parent=None):
    super().__init__(parent)
    self._main = main_window
    self._build_ui()
    self.sync_theme_from_toolbar(self._main.theme_switch.mode())

  def _build_ui(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    hint = QLabel("Uygulama temasını seçin. Değişiklik önizlemesi anında uygulanır; Kaydet ile kalıcı olur.")
    hint.setObjectName("SettingsInfoLabel")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    form = QFrame()
    form.setObjectName("FormFrame")
    form.setAutoFillBackground(True)
    form_layout = QVBoxLayout(form)
    form_layout.setContentsMargins(16, 16, 16, 16)
    form_layout.setSpacing(10)

    self.radio_dark = QRadioButton("Koyu tema")
    self.radio_light = QRadioButton("Açık tema")
    self.radio_dark.toggled.connect(self._on_radio_toggled)
    self.radio_light.toggled.connect(self._on_radio_toggled)
    form_layout.addWidget(self.radio_dark)
    form_layout.addWidget(self.radio_light)
    layout.addWidget(form)
    layout.addStretch()

  def selected_mode(self) -> str:
    return "light" if self.radio_light.isChecked() else "dark"

  def _on_radio_toggled(self, checked: bool):
    if not checked:
      return
    mode = self.selected_mode()
    apply_app_theme(mode, settings=None, persist=False)
    self._main.theme_switch.set_mode(mode, emit=False)

  def sync_theme_from_toolbar(self, mode: str):
    normalized = "light" if str(mode).strip().lower() == "light" else "dark"
    self.radio_dark.blockSignals(True)
    self.radio_light.blockSignals(True)
    self.radio_dark.setChecked(normalized == "dark")
    self.radio_light.setChecked(normalized == "light")
    self.radio_dark.blockSignals(False)
    self.radio_light.blockSignals(False)


class LogTab(QWidget):
  """Uygulama günlüğü önizleme."""

  def __init__(self, parent=None):
    super().__init__(parent)
    self._log_path = log_file_path()
    self._build_ui()
    self.refresh_log()

  def _build_ui(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)

    path_label = QLabel(f"Log dosyası: {self._log_path}")
    path_label.setObjectName("SettingsInfoLabel")
    path_label.setWordWrap(True)
    layout.addWidget(path_label)

    self.log_view = QPlainTextEdit()
    self.log_view.setObjectName("LogViewer")
    self.log_view.setReadOnly(True)
    self.log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    layout.addWidget(self.log_view)

    btn_row = QHBoxLayout()
    btn_refresh = QPushButton("Yenile")
    btn_refresh.setObjectName("SecondaryButton")
    btn_refresh.clicked.connect(self.refresh_log)
    btn_open = QPushButton("Log klasörünü aç")
    btn_open.setObjectName("SecondaryButton")
    btn_open.clicked.connect(lambda: _open_local_folder(self._log_path.parent))
    btn_copy = QPushButton("Panoya kopyala")
    btn_copy.setObjectName("SecondaryButton")
    btn_copy.clicked.connect(self._copy_to_clipboard)
    btn_row.addWidget(btn_refresh)
    btn_row.addWidget(btn_open)
    btn_row.addWidget(btn_copy)
    btn_row.addStretch()
    layout.addLayout(btn_row)

  def refresh_log(self):
    text = read_log_tail(self._log_path)
    if not text:
      text = "(Log dosyası boş veya henüz oluşturulmamış.)"
    self.log_view.setPlainText(text)
    self.log_view.moveCursor(QTextCursor.MoveOperation.End)

  def _copy_to_clipboard(self):
    QApplication.clipboard().setText(self.log_view.toPlainText())


class HelpTab(QWidget):
  """Sürüm, güncelleme ve lisans bilgisi."""

  def __init__(self, on_check_updates, parent=None):
    super().__init__(parent)
    self._on_check_updates = on_check_updates
    self._build_ui()

  def _build_ui(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    title = QLabel(f"S3MANAGER {__version__}")
    title.setObjectName("DialogTitle")
    layout.addWidget(title)

    releases_url = f"https://github.com/{GITHUB_REPO}/releases"
    btn_releases = QPushButton("GitHub Releases")
    btn_releases.setObjectName("SecondaryButton")
    btn_releases.clicked.connect(
      lambda: QDesktopServices.openUrl(QUrl(releases_url)),
    )
    layout.addWidget(btn_releases)

    btn_check = QPushButton("Güncellemeleri Kontrol Et")
    btn_check.setObjectName("SecondaryButton")
    btn_check.clicked.connect(lambda: self._on_check_updates(manual=True))
    layout.addWidget(btn_check)

    license_text = QLabel(
      "Bu yazılım GNU General Public License v3.0 (GPL-3.0) altında dağıtılır.\n"
      f"Kaynak: https://github.com/{GITHUB_REPO}"
    )
    license_text.setObjectName("SettingsInfoLabel")
    license_text.setWordWrap(True)
    layout.addWidget(license_text)
    layout.addStretch()


class SettingsDialog(QDialog):
  """Tab'lı merkezi ayarlar dialogu."""

  def __init__(self, main_window, parent=None):
    super().__init__(parent or main_window)
    self._main = main_window
    self.settings = main_window.settings
    self._original_theme = self.settings.load_theme_mode()
    self.setWindowTitle("Ayarlar")
    self.setObjectName("ElevatedDialog")
    self.resize(640, 520)
    self._build_ui()
    apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

  def _build_ui(self):
    layout = QVBoxLayout(self)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)

    title = QLabel("Ayarlar")
    title.setObjectName("DialogTitle")
    layout.addWidget(title)

    self.tabs = QTabWidget()
    self.tabs.setObjectName("SettingsTabWidget")

    self.connection_tab = ConnectionTab(
      self.settings,
      on_edit_connection=self._edit_connection,
    )
    self.metadata_panel = UploadMetadataPanel()
    self.metadata_panel.load_settings(self.settings.load_upload_metadata_settings())
    self.appearance_tab = AppearanceTab(self._main)
    self.log_tab = LogTab()
    self.maintenance_panel = IncompleteUploadsPanel(
      client=getattr(self._main, "spaces_client", None),
    )
    self.help_tab = HelpTab(on_check_updates=self._main.check_for_updates)

    self.tabs.addTab(self.connection_tab, "Bağlantı")
    self.tabs.addTab(self.metadata_panel, "Yükleme Metadata")
    self.tabs.addTab(self.appearance_tab, "Görünüm")
    self.tabs.addTab(self.log_tab, "Günlük")
    self.tabs.addTab(self.maintenance_panel, "Bakım")
    self.tabs.addTab(self.help_tab, "Yardım")
    layout.addWidget(self.tabs)

    actions = QHBoxLayout()
    btn_cancel = QPushButton("İptal")
    btn_cancel.setObjectName("SecondaryButton")
    btn_cancel.clicked.connect(self._cancel)
    btn_save = QPushButton("Kaydet")
    btn_save.clicked.connect(self._save)
    actions.addWidget(btn_cancel)
    actions.addStretch()
    actions.addWidget(btn_save)
    layout.addLayout(actions)

  def sync_theme_from_toolbar(self, mode: str):
    normalized = "light" if str(mode).strip().lower() == "light" else "dark"
    self._original_theme = normalized
    self.appearance_tab.sync_theme_from_toolbar(mode)
    self.maintenance_panel.apply_theme()
    update_dialog_elevation(self)

  def _edit_connection(self):
    dlg = LoginDialog(self._main, on_connect=self._main.on_connected)
    dlg.exec()
    self.connection_tab.refresh()

  def _revert_theme_preview(self):
    mode = self._original_theme
    apply_app_theme(mode, settings=None, persist=False)
    self._main.theme_switch.set_mode(mode, emit=False)
    self.appearance_tab.sync_theme_from_toolbar(mode)

  def _cancel(self):
    self._revert_theme_preview()
    self.reject()

  def _save(self):
    new_meta = self.metadata_panel.get_settings()
    if not self.settings.save_upload_metadata_settings(new_meta):
      QMessageBox.warning(self, "Hata", "Metadata ayarları kaydedilemedi.")
      return

    mode = self.appearance_tab.selected_mode()
    apply_app_theme(mode, settings=self.settings, persist=True)
    self._main.theme_switch.set_mode(mode, emit=False)
    self._original_theme = mode

    upload_dlg = getattr(self._main, "upload_dlg", None)
    if upload_dlg:
      upload_dlg.metadata_settings = new_meta

    self.accept()

  def closeEvent(self, event):
    if self.result() != QDialog.DialogCode.Accepted:
      self._revert_theme_preview()
    super().closeEvent(event)
