"""Alt transfer geçmişi paneli."""
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QListWidget, QListWidgetItem


class TransferPanel(QFrame):
    """Tamamlanan ve devam eden yükleme/indirme kayıtları."""

    MAX_ITEMS = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TransferPanel")
        self.setMaximumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(4)

        header = QLabel("Transferler")
        header.setObjectName("TransferPanelTitle")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("TransferList")
        layout.addWidget(self.list_widget)

    def add_entry(self, kind: str, name: str, status: str):
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = {"upload": "↑", "download": "↓"}.get(kind, "•")
        item = QListWidgetItem(f"{ts}  {prefix} {name} — {status}")
        if status in ("tamamlandı", "hata", "iptal"):
            item.setForeground(Qt.gray)
        self.list_widget.insertItem(0, item)
        while self.list_widget.count() > self.MAX_ITEMS:
            self.list_widget.takeItem(self.list_widget.count() - 1)
