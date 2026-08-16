"""Nesne metadata ve ACL düzenleme dialogu."""
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QRadioButton, QMessageBox, QPlainTextEdit,
)

from src.services.spaces_client import SpacesClient
from src.ui.qt.styles import apply_dialog_elevation, current_theme_mode


def _metadata_to_lines(metadata: Dict[str, str]) -> str:
    if not metadata:
        return ""
    return "\n".join(f"{k}={v}" for k, v in sorted(metadata.items()))


def _lines_to_metadata(text: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        if key.lower().startswith("x-amz-meta-"):
            key = key[11:]
        result[key] = value.strip()
    return result


class ObjectPropertiesDialog(QDialog):
    """Tek dosya için Content-Type, Cache-Control, özel metadata ve ACL."""

    def __init__(self, parent, client: SpacesClient, key: str, name: str):
        super().__init__(parent)
        self.client = client
        self.key = key
        self._name = name
        self._saved_acl = "private"
        self.setWindowTitle(f"Özellikler — {name}")
        self.setObjectName("ElevatedDialog")
        self.resize(520, 480)
        self._build_ui()
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))
        self._load()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel(f"Özellikler: {self._name}")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        form = QFrame()
        form.setObjectName("FormFrame")
        form.setAutoFillBackground(True)
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        form_layout.addWidget(QLabel("Content-Type:"))
        self.entry_content_type = QLineEdit()
        form_layout.addWidget(self.entry_content_type)

        form_layout.addWidget(QLabel("Cache-Control:"))
        self.entry_cache_control = QLineEdit()
        self.entry_cache_control.setPlaceholderText("boş = gönderilmez")
        form_layout.addWidget(self.entry_cache_control)

        form_layout.addWidget(QLabel("Özel metadata (satır başına anahtar=değer):"))
        hint = QLabel("Örnek: author=mehmet — x-amz-meta- öneki otomatik eklenir.")
        hint.setObjectName("SettingsInfoLabel")
        hint.setWordWrap(True)
        form_layout.addWidget(hint)
        self.entry_metadata = QPlainTextEdit()
        self.entry_metadata.setPlaceholderText("author=isim\nversion=2")
        self.entry_metadata.setMaximumHeight(100)
        form_layout.addWidget(self.entry_metadata)

        form_layout.addWidget(QLabel("Erişim (ACL):"))
        acl_row = QHBoxLayout()
        self.radio_private = QRadioButton("Private")
        self.radio_public = QRadioButton("Public-read")
        self.radio_private.setChecked(True)
        acl_row.addWidget(self.radio_private)
        acl_row.addWidget(self.radio_public)
        acl_row.addStretch()
        form_layout.addLayout(acl_row)

        layout.addWidget(form)

        actions = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self._save)
        actions.addWidget(btn_cancel)
        actions.addStretch()
        actions.addWidget(btn_save)
        layout.addLayout(actions)

    def _load(self):
        try:
            meta = self.client.head_object(self.key)
            self.entry_content_type.setText(meta.get("content_type") or "")
            self.entry_cache_control.setText(meta.get("cache_control") or "")
            self.entry_metadata.setPlainText(_metadata_to_lines(meta.get("metadata") or {}))
            acl = self.client.get_object_acl(self.key)
            self._saved_acl = acl
            if acl == "public-read":
                self.radio_public.setChecked(True)
            else:
                self.radio_private.setChecked(True)
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Özellikler yüklenemedi:\n{e}")

    def result_acl(self) -> str:
        return "public-read" if self.radio_public.isChecked() else "private"

    def _save(self):
        content_type = self.entry_content_type.text().strip()
        cache_control = self.entry_cache_control.text().strip()
        metadata = _lines_to_metadata(self.entry_metadata.toPlainText())
        acl = self.result_acl()
        try:
            self.client.update_object_metadata(
                self.key,
                content_type=content_type or "",
                cache_control=cache_control,
                metadata=metadata,
            )
            if acl != self._saved_acl:
                self.client.put_object_acl(self.key, acl)
            self._saved_acl = acl
            self.accept()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Kaydedilemedi:\n{e}")
