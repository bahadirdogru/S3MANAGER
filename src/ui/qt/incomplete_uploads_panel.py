"""Yarım kalan multipart yüklemeler paneli (Ayarlar Bakım sekmesi)."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView,
)

from src.services.spaces_client import SpacesClient
from src.ui.qt.styles import apply_item_view_palette
from src.utils.helpers import format_date


class IncompleteUploadsPanel(QWidget):
    """Multipart yüklemeleri listele ve iptal et."""

    def __init__(self, client: Optional[SpacesClient] = None, parent=None):
        super().__init__(parent)
        self.setObjectName("IncompleteUploadsPanel")
        self._client = client
        self.setAutoFillBackground(True)
        self._build_ui()
        self.apply_theme()

    def apply_theme(self):
        """QSS + palet — Windows tablo viewport düzeltmesi."""
        apply_item_view_palette(self.table)
        style = self.style()
        style.unpolish(self)
        style.polish(self)
        style.unpolish(self.table)
        style.polish(self.table)

    def set_client(self, client: SpacesClient):
        self._client = client
        self.refresh()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = QLabel(
            "Tamamlanmamış multipart yüklemeler depolama alanı kaplar. "
            "İptal edilen yüklemeler kalıcı olarak kaldırılır."
        )
        hint.setObjectName("SettingsInfoLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QTableWidget(0, 3)
        self.table.setObjectName("IncompleteUploadsTable")
        self.table.setAlternatingRowColors(True)
        self.table.setAutoFillBackground(True)
        self.table.setHorizontalHeaderLabels(["Dosya yolu", "Başlangıç", "Upload ID"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.setObjectName("SecondaryButton")
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_abort_one = QPushButton("Seçileni iptal et")
        self.btn_abort_one.setObjectName("SecondaryButton")
        self.btn_abort_one.clicked.connect(self._abort_selected)
        self.btn_abort_all = QPushButton("Tümünü iptal et")
        self.btn_abort_all.setObjectName("SecondaryButton")
        self.btn_abort_all.clicked.connect(self._abort_all)
        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_abort_one)
        btn_row.addWidget(self.btn_abort_all)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        self.table.setRowCount(0)
        if not self._client:
            return
        try:
            uploads = self._client.list_incomplete_multipart_uploads()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"Liste alınamadı:\n{e}")
            return
        self.table.setRowCount(len(uploads))
        for row, upload in enumerate(uploads):
            initiated = upload.get("initiated")
            ts = format_date(initiated) if initiated else "—"
            self.table.setItem(row, 0, QTableWidgetItem(upload.get("key", "")))
            self.table.setItem(row, 1, QTableWidgetItem(ts))
            item = QTableWidgetItem(upload.get("upload_id", ""))
            item.setData(Qt.UserRole, upload)
            self.table.setItem(row, 2, item)

    def _selected_upload(self) -> Optional[dict]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 2)
        if not item:
            return None
        return item.data(Qt.UserRole)

    def _abort_selected(self):
        upload = self._selected_upload()
        if not upload:
            QMessageBox.information(self, "Bilgi", "İptal edilecek yükleme seçin.")
            return
        self._abort_upload(upload)

    def _abort_all(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Bilgi", "Yarım yükleme bulunamadı.")
            return
        if QMessageBox.question(
            self,
            "Onay",
            f"{self.table.rowCount()} yarım yükleme iptal edilecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        uploads = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 2)
            if item:
                uploads.append(item.data(Qt.UserRole))
        for upload in uploads:
            self._abort_upload(upload, silent=True)
        self.refresh()
        QMessageBox.information(self, "Tamamlandı", "Yarım yüklemeler iptal edildi.")

    def _abort_upload(self, upload: dict, silent: bool = False):
        if not self._client:
            return
        key = upload.get("key", "")
        upload_id = upload.get("upload_id", "")
        if not key or not upload_id:
            return
        try:
            self._client.abort_multipart_upload(key, upload_id)
            if not silent:
                self.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Hata", f"İptal edilemedi:\n{e}")
