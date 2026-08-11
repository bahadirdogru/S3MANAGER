"""Sürükle-bırak destekli dosya ağacı görünümü."""
import os

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QTreeView


class FileTreeView(QTreeView):
    """Yerel dosyaları ana pencereye bırakarak yükleme."""

    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeView.DropOnly)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and os.path.exists(local):
                paths.append(os.path.normpath(local))
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()
