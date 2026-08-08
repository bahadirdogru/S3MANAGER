from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal
from datetime import datetime
import os

from src.utils.helpers import format_file_size, format_date


class FileModel(QAbstractItemModel):
    """Model for DigitalOcean Spaces file listing with lazy append support."""

    request_next_page = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.items = []
        self.headers = ["İsim", "Boyut", "Tarih", "İzin"]
        self._has_more_pages = False
        self._loading = False
        self._acl_cache: dict[str, str] = {}
        self._pending_acl: set[str] = set()

    def begin_loading(self):
        self.beginResetModel()
        self.items = []
        self._acl_cache.clear()
        self._pending_acl.clear()
        self._has_more_pages = False
        self._loading = True
        self.endResetModel()

    def set_has_more(self, has_more: bool):
        self._has_more_pages = has_more
        if not has_more:
            self._loading = False

    def append_items(self, folders, files, first_page: bool = False):
        new_items = []
        for f in sorted(folders, key=lambda x: (x.get('name') or '').lower()):
            if not f.get('name') or not f['name'].strip():
                f['name'] = f.get('path', '(isimsiz)').rstrip('/').split('/')[-1] or '(isimsiz)'
            new_items.append(f)
        for f in sorted(files, key=lambda x: (x.get('name') or '').lower()):
            if not f.get('name') or not f['name'].strip():
                f['name'] = os.path.basename(f.get('path', '')) or '(isimsiz)'
            new_items.append(f)

        if not new_items:
            return

        if first_page and not self.items:
            self.beginResetModel()
            self.items = new_items
            self.endResetModel()
            return

        start = len(self.items)
        self.beginInsertRows(QModelIndex(), start, start + len(new_items) - 1)
        self.items.extend(new_items)
        self.endInsertRows()

    def set_items(self, folders, files):
        """Full replace — used by cache restore."""
        self.beginResetModel()
        self._acl_cache.clear()
        self._pending_acl.clear()
        self.items = []
        for f in sorted(folders, key=lambda x: (x.get('name') or '').lower()):
            if not f.get('name') or not f['name'].strip():
                f['name'] = f.get('path', '(isimsiz)').rstrip('/').split('/')[-1] or '(isimsiz)'
            self.items.append(f)
        for f in sorted(files, key=lambda x: (x.get('name') or '').lower()):
            if not f.get('name') or not f['name'].strip():
                f['name'] = os.path.basename(f.get('path', '')) or '(isimsiz)'
            self.items.append(f)
        self._loading = False
        self.endResetModel()

    def set_acl(self, path: str, acl: str):
        self._acl_cache[path] = acl
        self._pending_acl.discard(path)
        for row, item in enumerate(self.items):
            if item.get('path') == path and item.get('type') == 'file':
                idx = self.index(row, 3)
                self.dataChanged.emit(idx, idx, [Qt.DisplayRole])
                break

    def mark_acl_pending(self, paths: list[str]):
        for p in paths:
            self._pending_acl.add(p)

    def canFetchMore(self, parent=QModelIndex()) -> bool:
        return not parent.isValid() and self._has_more_pages

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid() or not self._has_more_pages:
            return
        self.request_next_page.emit()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.items)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        item = self.items[row]

        if role == Qt.DisplayRole:
            if col == 0:
                return item['name']
            if col == 1:
                if item['type'] == 'file':
                    return format_file_size(item.get('size', 0))
                return ""
            if col == 2:
                mod = item.get('modified')
                if isinstance(mod, datetime):
                    return format_date(mod)
                return str(mod) if mod else "-"
            if col == 3:
                if item.get('type') != 'file':
                    return ""
                path = item.get('path', '')
                if path in self._pending_acl:
                    return "..."
                acl = self._acl_cache.get(path, item.get('acl', 'unknown'))
                return "🔓" if acl == 'public-read' else "🔒"

        if role == Qt.DecorationRole and col == 0:
            from PySide6.QtWidgets import QApplication, QStyle
            style = QApplication.style()
            if item['type'] == 'folder':
                return style.standardIcon(QStyle.SP_DirIcon)
            return style.standardIcon(QStyle.SP_FileIcon)

        if role == Qt.TextAlignmentRole:
            if col == 0:
                return Qt.AlignLeft | Qt.AlignVCenter
            if col == 3:
                return Qt.AlignCenter
            return Qt.AlignRight | Qt.AlignVCenter

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def index(self, row, column, parent=QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        return self.createIndex(row, column)

    def parent(self, index):
        return QModelIndex()

    def get_item(self, index):
        if index.isValid():
            return self.items[index.row()]
        return None

    def file_paths_needing_acl(self, row_indices: list[int]) -> list[str]:
        paths = []
        for row in row_indices:
            if 0 <= row < len(self.items):
                item = self.items[row]
                if item.get('type') == 'file':
                    path = item.get('path', '')
                    if path and path not in self._acl_cache and path not in self._pending_acl:
                        if item.get('acl') == 'unknown':
                            paths.append(path)
        return paths
