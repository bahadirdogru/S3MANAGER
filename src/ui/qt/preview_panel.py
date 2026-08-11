"""Sağ panel dosya önizleme widget'ı."""
import os
from typing import Optional, Callable

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QTextEdit, QPushButton,
    QHBoxLayout, QScrollArea,
)

from src.utils.helpers import format_file_size, format_date

_IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico'}
_TEXT_EXTS = {'.txt', '.json', '.html', '.htm', '.css', '.js', '.xml', '.md', '.log', '.csv', '.yaml', '.yml', '.py', '.ini', '.cfg'}
_PREVIEW_MAX_BYTES = 5 * 1024 * 1024


class PreviewLoadWorker(QThread):
    loaded = Signal(object, object, bytes)
    error = Signal(str)

    def __init__(self, client, key: str):
        super().__init__()
        self.client = client
        self.key = key

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            meta = self.client.head_object(self.key)
            if self.isInterruptionRequested():
                return
            ext = os.path.splitext(self.key)[1].lower()
            data = b''
            if ext in _IMAGE_EXTS or ext in _TEXT_EXTS:
                data = self.client.get_object_bytes(self.key, max_bytes=_PREVIEW_MAX_BYTES)
            if not self.isInterruptionRequested():
                self.loaded.emit(meta, ext, data)
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


class PreviewPanel(QFrame):
    """Tek dosya seçildiğinde metadata ve içerik önizlemesi."""

    download_requested = Signal()
    share_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("PreviewPanel")
        self._client = None
        self._worker: Optional[PreviewLoadWorker] = None
        self._current_key: Optional[str] = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.lbl_title = QLabel("Önizleme")
        self.lbl_title.setObjectName("PreviewTitle")
        layout.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("Dosya seçin")
        self.lbl_meta.setObjectName("PreviewMeta")
        self.lbl_meta.setWordWrap(True)
        layout.addWidget(self.lbl_meta)

        btn_row = QHBoxLayout()
        self.btn_download = QPushButton("İndir")
        self.btn_share = QPushButton("Paylaş")
        self.btn_download.setEnabled(False)
        self.btn_share.setEnabled(False)
        self.btn_download.clicked.connect(self.download_requested.emit)
        self.btn_share.clicked.connect(self.share_requested.emit)
        btn_row.addWidget(self.btn_download)
        btn_row.addWidget(self.btn_share)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("PreviewScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setAlignment(Qt.AlignCenter)

        self.content_host = QWidget()
        self.content_layout = QVBoxLayout(self.content_host)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setAlignment(Qt.AlignCenter)

        self.lbl_placeholder = QLabel("Önizlemek için tek bir dosya seçin")
        self.lbl_placeholder.setObjectName("PreviewPlaceholder")
        self.lbl_placeholder.setAlignment(Qt.AlignCenter)
        self.lbl_placeholder.setWordWrap(True)
        self.content_layout.addWidget(self.lbl_placeholder)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setVisible(False)
        self.content_layout.addWidget(self.image_label)

        self.text_view = QTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setVisible(False)
        self.content_layout.addWidget(self.text_view)

        self.scroll.setWidget(self.content_host)
        layout.addWidget(self.scroll, 1)

    def set_client(self, client):
        self._client = client

    def clear(self):
        self._stop_worker()
        self._current_key = None
        self.lbl_meta.setText("Dosya seçin")
        self.btn_download.setEnabled(False)
        self.btn_share.setEnabled(False)
        self._show_placeholder("Önizlemek için tek bir dosya seçin")

    def show_file(self, key: str, name: str):
        if not self._client or not key:
            self.clear()
            return
        if key == self._current_key and self._worker and self._worker.isRunning():
            return
        self._stop_worker()
        self._current_key = key
        self.lbl_title.setText(name)
        self.lbl_meta.setText("Yükleniyor...")
        self.btn_download.setEnabled(True)
        self.btn_share.setEnabled(True)
        self._show_placeholder("Yükleniyor...")

        self._worker = PreviewLoadWorker(self._client, key)
        self._worker.loaded.connect(self._on_loaded)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop_worker(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(2000)
        self._worker = None

    def _show_placeholder(self, text: str):
        self.lbl_placeholder.setText(text)
        self.lbl_placeholder.setVisible(True)
        self.image_label.setVisible(False)
        self.text_view.setVisible(False)

    def _clear_content(self):
        self.lbl_placeholder.setVisible(False)
        self.image_label.clear()
        self.image_label.setVisible(False)
        self.text_view.clear()
        self.text_view.setVisible(False)

    @Slot(object, object, bytes)
    def _on_loaded(self, meta, ext, data: bytes):
        lm = meta.get('last_modified')
        lm_str = format_date(lm) if lm else '-'
        size = format_file_size(meta.get('content_length', 0))
        ctype = meta.get('content_type') or '-'
        self.lbl_meta.setText(f"Boyut: {size}\nTür: {ctype}\nDeğişiklik: {lm_str}")

        self._clear_content()
        if ext in _IMAGE_EXTS and data:
            image = QImage.fromData(data)
            if not image.isNull():
                pix = QPixmap.fromImage(image)
                max_w = max(self.scroll.width() - 24, 200)
                if pix.width() > max_w:
                    pix = pix.scaledToWidth(max_w, Qt.SmoothTransformation)
                self.image_label.setPixmap(pix)
                self.image_label.setVisible(True)
                return
        if ext in _TEXT_EXTS and data:
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                text = data.decode('latin-1', errors='replace')
            if len(data) >= _PREVIEW_MAX_BYTES:
                text += "\n\n… (önizleme kısaltıldı)"
            self.text_view.setPlainText(text)
            self.text_view.setVisible(True)
            return
        if ext == '.pdf':
            self._show_placeholder("PDF önizleme desteklenmiyor.\nİndirerek görüntüleyin.")
            return
        self._show_placeholder("Bu dosya türü için önizleme yok.\nİndirerek açabilirsiniz.")

    @Slot(str)
    def _on_error(self, msg: str):
        self.lbl_meta.setText(f"Hata: {msg}")
        self._show_placeholder("Önizleme yüklenemedi")
