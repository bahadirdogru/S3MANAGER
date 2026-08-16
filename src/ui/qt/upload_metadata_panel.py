"""Yükleme metadata ayarları form paneli."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox,
)

from src.utils.object_metadata import (
    UploadMetadataSettings,
    DEFAULT_INLINE_EXTENSIONS,
    DEFAULT_ATTACHMENT_EXTENSIONS,
    parse_extension_list,
)


class UploadMetadataPanel(QWidget):
    """Metadata ayar formu — SettingsDialog sekmesi veya dialog içinde."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        hint = QLabel(
            "Yükleme sırasında Content-Type, Content-Disposition ve isteğe bağlı "
            "Cache-Control otomatik atanır."
        )
        hint.setObjectName("UploadSummaryLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFrame()
        form.setObjectName("FormFrame")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(10)

        self.chk_enabled = QCheckBox("Otomatik metadata etkin")
        form_layout.addWidget(self.chk_enabled)

        form_layout.addWidget(QLabel("Cache-Control (boş = gönderilmez):"))
        self.entry_cache_control = QLineEdit()
        self.entry_cache_control.setPlaceholderText("örn. public, max-age=3600")
        form_layout.addWidget(self.entry_cache_control)

        form_layout.addWidget(QLabel("Metin charset:"))
        self.entry_charset = QLineEdit()
        self.entry_charset.setPlaceholderText("utf-8")
        form_layout.addWidget(self.entry_charset)

        form_layout.addWidget(QLabel("Inline uzantılar (virgülle ayrılmış):"))
        self.entry_inline = QLineEdit()
        form_layout.addWidget(self.entry_inline)

        form_layout.addWidget(QLabel("Attachment uzantılar (virgülle ayrılmış):"))
        self.entry_attachment = QLineEdit()
        form_layout.addWidget(self.entry_attachment)

        layout.addWidget(form)

        btn_row = QHBoxLayout()
        self.btn_reset = QPushButton("Varsayılana Dön")
        self.btn_reset.setObjectName("SecondaryButton")
        self.btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(self.btn_reset)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_settings(self, settings: UploadMetadataSettings):
        self.chk_enabled.setChecked(settings.enabled)
        self.entry_cache_control.setText(settings.cache_control)
        self.entry_charset.setText(settings.text_charset)
        self.entry_inline.setText(settings.inline_extensions_csv())
        self.entry_attachment.setText(settings.attachment_extensions_csv())

    def _reset_defaults(self):
        self.load_settings(UploadMetadataSettings())

    def get_settings(self) -> UploadMetadataSettings:
        inline_raw = self.entry_inline.text().strip()
        attachment_raw = self.entry_attachment.text().strip()
        return UploadMetadataSettings(
            enabled=self.chk_enabled.isChecked(),
            cache_control=self.entry_cache_control.text().strip(),
            text_charset=self.entry_charset.text().strip() or "utf-8",
            inline_extensions=(
                parse_extension_list(inline_raw) if inline_raw else set(DEFAULT_INLINE_EXTENSIONS)
            ),
            attachment_extensions=(
                parse_extension_list(attachment_raw)
                if attachment_raw
                else set(DEFAULT_ATTACHMENT_EXTENSIONS)
            ),
        )
