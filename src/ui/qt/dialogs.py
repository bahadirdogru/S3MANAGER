import os
import time

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QFrame,
    QProgressBar, QScrollArea, QWidget, QRadioButton,
    QButtonGroup, QFileDialog, QMessageBox,
    QStackedWidget, QListWidget, QListWidgetItem,
    QTreeWidget, QTreeWidgetItem, QAbstractItemView,
    QApplication, QCheckBox,
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent

MAX_DISPLAY_FILES = 200
PROGRESS_UI_INTERVAL_MS = 150
from src.ui.qt.styles import (
    apply_dialog_elevation,
    current_theme_mode,
)
from src.config.settings import Settings
from src.services.spaces_client import SpacesClient
from src.utils.helpers import format_file_size
from src.utils.object_metadata import UploadMetadataSettings, preview_content_type
from src.utils.validators import (
    validate_spaces_key,
    validate_spaces_secret,
    validate_bucket_name,
    validate_endpoint,
    validate_region,
)
from src.utils.logging_config import get_logger

logger = get_logger('dialogs')


def _repolish_widget(widget):
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def _format_speed_mbps(speed_mbps: float) -> str:
    if speed_mbps <= 0:
        return ""
    if speed_mbps >= 100:
        return f"{speed_mbps:.1f} MB/s"
    return f"{speed_mbps:.2f} MB/s"


class LoginDialog(QDialog):
    """Dialog for entering DigitalOcean Spaces credentials"""
    def __init__(self, parent=None, on_connect=None):
        super().__init__(parent)
        self.on_connect = on_connect
        self.settings = Settings()
        self.credentials = None
        self.setWindowTitle("DigitalOcean Spaces Bağlantısı")
        self.setObjectName("ElevatedDialog")
        self.setFixedSize(520, 520)
        self.init_ui()
        self.apply_styles()
        self.load_saved_credentials()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        title = QLabel("DigitalOcean Spaces Bağlantısı")
        title.setObjectName("DialogTitleLarge")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        form_frame = QFrame()
        form_frame.setObjectName("FormFrame")
        form_frame.setAutoFillBackground(True)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)
        
        self.entries = {}
        fields = [("Spaces Key:", "key", True), ("Spaces Secret:", "secret", True), ("Bölge:", "region", False), ("Endpoint:", "endpoint", False), ("Bucket Adı:", "bucket", False)]
        
        for label_text, key, is_secret in fields:
            lbl = QLabel(label_text)
            lbl.setObjectName("DialogSubtitle")
            form_layout.addWidget(lbl)
            
            if key == "region":
                self.region_combo = QComboBox()
                self.region_combo.addItems(["nyc3", "sfo3", "sgp1", "ams3", "fra1", "blr1"])
                self.region_combo.currentTextChanged.connect(self.on_region_change)
                self.region_combo.setFixedHeight(36)
                form_layout.addWidget(self.region_combo)
            else:
                entry = QLineEdit()
                entry.setFixedHeight(36)
                if is_secret: 
                    entry.setEchoMode(QLineEdit.Password)
                form_layout.addWidget(entry)
                self.entries[key] = entry
        
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("StatusError")
        form_layout.addWidget(self.lbl_error)
        
        layout.addWidget(form_frame)
        
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_connect = QPushButton("Bağlan")
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_connect)
        layout.addLayout(btn_layout)

    def apply_styles(self):
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))
    def on_region_change(self, value):
        endpoint = self.settings.get_default_region_endpoint(value)
        self.entries['endpoint'].setText(endpoint)
    def load_saved_credentials(self):
        creds = self.settings.load_credentials()
        if creds:
            self.entries['key'].setText(creds.get('key', ''))
            self.entries['secret'].setText(creds.get('secret', ''))
            self.region_combo.setCurrentText(creds.get('region', 'nyc3'))
            self.entries['endpoint'].setText(creds.get('endpoint', ''))
            self.entries['bucket'].setText(creds.get('bucket', ''))

    def on_connect_clicked(self):
        creds = {
            'key': self.entries['key'].text().strip(),
            'secret': self.entries['secret'].text().strip(),
            'region': self.region_combo.currentText(),
            'endpoint': self.entries['endpoint'].text().strip(),
            'bucket': self.entries['bucket'].text().strip(),
        }
        for validator, value in (
            (validate_spaces_key, creds['key']),
            (validate_spaces_secret, creds['secret']),
            (validate_region, creds['region']),
            (validate_endpoint, creds['endpoint']),
            (validate_bucket_name, creds['bucket']),
        ):
            ok, msg = validator(value)
            if not ok:
                self.lbl_error.setText(msg)
                return

        self.btn_connect.setEnabled(False)
        self.lbl_error.setText("Bağlantı test ediliyor...")
        try:
            client = SpacesClient(**creds)
            success, err = client.test_connection()
            if not success:
                self.lbl_error.setText(err or "Bağlantı başarısız")
                self.btn_connect.setEnabled(True)
                return
        except Exception as e:
            self.lbl_error.setText(str(e))
            self.btn_connect.setEnabled(True)
            return

        if not self.settings.save_credentials(
            creds['key'], creds['secret'], creds['region'], creds['endpoint'], creds['bucket']
        ):
            self.lbl_error.setText("Kimlik bilgileri kaydedilemedi.")
            self.btn_connect.setEnabled(True)
            return

        self.credentials = creds
        if self.on_connect:
            self.on_connect(creds)
        self.accept()

class UploadProgressBar(QWidget):
    """Custom progress bar widget for uploads with detailed information"""
    def __init__(self, filename, filesize, parent=None):
        super().__init__(parent)
        self.setObjectName("UploadProgressCard")
        self.filename = filename
        self.filesize = filesize
        self.uploaded_bytes = 0
        self.start_time = None
        self.last_update_time = None
        self.last_uploaded = 0
        self.is_multipart = False
        self.multipart_parts = 0
        self.multipart_completed = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Top row: Filename, speed and percentage
        top_layout = QHBoxLayout()
        self.lbl_name = QLabel(filename)
        self.lbl_name.setObjectName("UploadFileName")
        self.lbl_speed = QLabel("")
        self.lbl_speed.setObjectName("UploadFileSpeed")
        self.lbl_speed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_percentage = QLabel("0%")
        self.lbl_percentage.setObjectName("UploadFilePct")
        self.lbl_percentage.setAlignment(Qt.AlignRight)
        top_layout.addWidget(self.lbl_name, stretch=1)
        top_layout.addWidget(self.lbl_speed)
        top_layout.addWidget(self.lbl_percentage)
        layout.addLayout(top_layout)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setFixedHeight(10)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)

        # Info row: Size, Speed, Status
        info_layout = QHBoxLayout()
        self.lbl_size = QLabel(f"0 / {format_file_size(filesize)}")
        self.lbl_size.setObjectName("ProgressMeta")

        sep = QLabel("•")
        sep.setObjectName("ProgressMeta")

        self.lbl_status = QLabel("Bekliyor...")
        self.lbl_status.setObjectName("ProgressMeta")

        info_layout.addWidget(self.lbl_size)
        info_layout.addStretch()
        info_layout.addWidget(sep)
        info_layout.addWidget(self.lbl_status)
        layout.addLayout(info_layout)
        
        # Multipart info (hidden by default)
        self.lbl_multipart = QLabel("")
        self.lbl_multipart.setObjectName("UploadMultipartInfo")
        self.lbl_multipart.setVisible(False)
        layout.addWidget(self.lbl_multipart)

    def update_progress(self, val, uploaded_bytes=0, speed_mbps=0.0, is_multipart=False, 
                       multipart_parts=0, multipart_completed=0, info=""):
        """Update progress with detailed information"""
        if self.start_time is None:
            self.start_time = time.time()
            self.last_update_time = self.start_time
            self.last_uploaded = 0
        
        # Update values
        self.uploaded_bytes = uploaded_bytes if uploaded_bytes > 0 else int(self.filesize * val)
        percentage = int(val * 100)
        current_time = time.time()
        
        # Calculate speed
        if speed_mbps > 0:
            speed_str = _format_speed_mbps(speed_mbps)
        else:
            # Calculate speed from time difference
            time_diff = current_time - self.last_update_time
            if time_diff > 0.1:  # Update every 100ms minimum
                bytes_diff = self.uploaded_bytes - self.last_uploaded
                if bytes_diff > 0:
                    speed_bps = bytes_diff / time_diff
                    speed_mbps = speed_bps / (1024 * 1024)
                    speed_str = _format_speed_mbps(speed_mbps)
                else:
                    speed_str = ""
                self.last_update_time = current_time
                self.last_uploaded = self.uploaded_bytes
            else:
                speed_str = self.lbl_speed.text()
        
        # Update multipart info
        self.is_multipart = is_multipart
        if is_multipart and multipart_parts > 0:
            self.multipart_parts = multipart_parts
            self.multipart_completed = multipart_completed
            self.lbl_multipart.setText(f"Multipart: {multipart_completed}/{multipart_parts} parça tamamlandı")
            self.lbl_multipart.setVisible(True)
        else:
            self.lbl_multipart.setVisible(False)
        
        # Update UI
        self.progress.setValue(percentage)
        self.lbl_percentage.setText(f"{percentage}%")
        self.lbl_size.setText(f"{format_file_size(self.uploaded_bytes)} / {format_file_size(self.filesize)}")
        self.lbl_speed.setText(speed_str)
        
        if info:
            self.lbl_status.setText(info)
        elif is_multipart:
            self.lbl_status.setText("Multipart yükleniyor...")
        else:
            self.lbl_status.setText("Yükleniyor...")
        self.lbl_status.setObjectName("ProgressMeta")
        _repolish_widget(self.lbl_status)

    def set_completed(self):
        """Mark upload as completed"""
        self.progress.setValue(100)
        self.lbl_percentage.setText("100%")
        self.lbl_size.setText(f"{format_file_size(self.filesize)} / {format_file_size(self.filesize)}")
        self.lbl_status.setText("✓ Tamamlandı")
        self.lbl_status.setObjectName("StatusSuccess")
        _repolish_widget(self.lbl_status)
        self.lbl_speed.setText("")
        self.lbl_multipart.setVisible(False)

    def set_error(self, msg):
        """Mark upload as error"""
        self.lbl_status.setText(f"✗ Hata: {msg}")
        self.lbl_status.setObjectName("StatusError")
        _repolish_widget(self.lbl_status)
        self.lbl_speed.setText("")
        self.lbl_multipart.setVisible(False)


class DropZoneFrame(QFrame):
    """Sürükle-bırak ve dosya/klasör seçim alanı."""

    paths_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZoneFrame")
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.lbl_hint = QLabel("Dosyaları buraya sürükleyin")
        self.lbl_hint.setObjectName("DropZoneHint")
        self.lbl_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_hint)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_select_files = QPushButton("📄 Dosya Seç")
        self.btn_select_folder = QPushButton("📁 Klasör Seç")
        btn_box.addWidget(self.btn_select_files)
        btn_box.addWidget(self.btn_select_folder)
        btn_box.addStretch()
        layout.addLayout(btn_box)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = []
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                paths.append(os.path.normpath(local))
        if paths:
            self.paths_dropped.emit(paths)
        event.acceptProposedAction()


class UploadMetadataSettingsDialog(QDialog):
    """Yükleme metadata ayarları dialogu."""

    def __init__(self, parent=None, settings: Settings = None):
        super().__init__(parent)
        self.settings = settings or Settings()
        self._result_settings: UploadMetadataSettings = self.settings.load_upload_metadata_settings()
        self.setWindowTitle("Yükleme Metadata Ayarları")
        self.setObjectName("ElevatedDialog")
        self.resize(560, 480)
        self.init_ui()
        self.apply_styles()
        self.metadata_panel.load_settings(self._result_settings)

    def init_ui(self):
        from src.ui.qt.upload_metadata_panel import UploadMetadataPanel

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Yükleme Metadata Ayarları")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        self.metadata_panel = UploadMetadataPanel()
        layout.addWidget(self.metadata_panel)

        actions = QHBoxLayout()
        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self._save)
        actions.addWidget(self.btn_cancel)
        actions.addStretch()
        actions.addWidget(self.btn_save)
        layout.addLayout(actions)

    def apply_styles(self):
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

    def _save(self):
        new_settings = self.metadata_panel.get_settings()
        if not self.settings.save_upload_metadata_settings(new_settings):
            QMessageBox.warning(self, "Hata", "Ayarlar kaydedilemedi.")
            return
        self._result_settings = new_settings
        self.accept()

    def result_settings(self) -> UploadMetadataSettings:
        return self._result_settings


class UploadFileList(QWidget):
    """Seçilen dosyaları liste veya klasör ağacı olarak gösterir."""

    remove_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_empty = QLabel("Henüz dosya seçilmedi")
        self.lbl_empty.setObjectName("UploadSummaryLabel")
        self.lbl_empty.setAlignment(Qt.AlignCenter)

        self.stack = QStackedWidget()
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("UploadFileList")
        self.list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_widget.setAlternatingRowColors(False)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setObjectName("UploadFileTree")
        self.tree_widget.setHeaderLabels(["Dosya", "Boyut", "Tür", ""])
        self.tree_widget.setColumnWidth(0, 260)
        self.tree_widget.setColumnWidth(1, 72)
        self.tree_widget.setColumnWidth(2, 160)
        self.tree_widget.setColumnWidth(3, 32)
        self.tree_widget.itemClicked.connect(self._on_tree_clicked)

        self.stack.addWidget(self.list_widget)
        self.stack.addWidget(self.tree_widget)

        layout.addWidget(self.lbl_empty)
        layout.addWidget(self.stack)
        self.lbl_truncated = QLabel("")
        self.lbl_truncated.setObjectName("UploadSummaryLabel")
        self.lbl_truncated.setVisible(False)
        layout.addWidget(self.lbl_truncated)

        self._show_empty()

    def _show_empty(self):
        self.lbl_empty.setVisible(True)
        self.stack.setVisible(False)
        self.lbl_truncated.setVisible(False)

    def _show_content(self):
        self.lbl_empty.setVisible(False)
        self.stack.setVisible(True)

    def _on_tree_clicked(self, item, column):
        if column == 3:
            path = item.data(0, Qt.UserRole)
            if path:
                self.remove_requested.emit(path)

    def _make_list_row(self, path: str, content_type: str = ""):
        name = os.path.basename(path)
        try:
            size = format_file_size(os.path.getsize(path))
        except OSError:
            size = "?"
        type_hint = f" · {content_type}" if content_type else ""
        item = QListWidgetItem()
        item.setData(Qt.UserRole, path)

        row = QWidget()
        row.setObjectName("UploadFileRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        lbl = QLabel(f"{name}  ({size}){type_hint}")
        lbl.setObjectName("UploadFileRowLabel")
        btn_remove = QPushButton("✕")
        btn_remove.setObjectName("SecondaryButton")
        btn_remove.setFixedSize(28, 24)
        btn_remove.clicked.connect(lambda checked=False, p=path: self.remove_requested.emit(p))
        row_layout.addWidget(lbl)
        row_layout.addStretch()
        row_layout.addWidget(btn_remove)
        item.setSizeHint(row.sizeHint())
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, row)

    def set_files(self, files: list, folder: str = None, content_types: dict = None):
        self.list_widget.clear()
        self.tree_widget.clear()
        content_types = content_types or {}
        if not files:
            self._show_empty()
            return

        self._show_content()
        display = files[:MAX_DISPLAY_FILES]
        hidden = len(files) - len(display)

        if folder and os.path.isdir(folder):
            self.stack.setCurrentWidget(self.tree_widget)
            for path in display:
                try:
                    rel = os.path.relpath(path, folder)
                    size = format_file_size(os.path.getsize(path))
                except (OSError, ValueError):
                    rel = os.path.basename(path)
                    size = "?"
                ctype = content_types.get(path, "")
                item = QTreeWidgetItem([rel, size, ctype, "✕"])
                item.setData(0, Qt.UserRole, path)
                self.tree_widget.addTopLevelItem(item)
            self.tree_widget.expandAll()
        else:
            self.stack.setCurrentWidget(self.list_widget)
            for path in display:
                self._make_list_row(path, content_types.get(path, ""))

        if hidden > 0:
            self.lbl_truncated.setText(f"... ve {hidden} dosya daha")
            self.lbl_truncated.setVisible(True)
        else:
            self.lbl_truncated.setVisible(False)


class UploadDialog(QDialog):
    """İki aşamalı dosya yükleme dialogu: seçim → yükleme → özet."""

    upload_started = Signal(list, str)
    cancel_requested = Signal()

    PHASE_SELECT = 0
    PHASE_UPLOAD = 1
    PHASE_SUMMARY = 2

    def __init__(self, parent=None, current_path="/"):
        super().__init__(parent)
        self.current_path = current_path
        self.settings = Settings()
        self.metadata_settings = self.settings.load_upload_metadata_settings()
        self.selected_files = []
        self.selected_folder = None
        self.progress_widgets = {}
        self._file_sizes = {}
        self._success_count = 0
        self._error_count = 0
        self._total_bytes = 0
        self._uploading = False
        self._cancelling = False
        self._overall_timer = QTimer(self)
        self._overall_timer.setSingleShot(True)
        self._overall_timer.setInterval(PROGRESS_UI_INTERVAL_MS)
        self._overall_timer.timeout.connect(self._update_overall_progress)

        self.setWindowTitle("Dosya Yükle")
        self.setObjectName("ElevatedDialog")
        self.resize(720, 640)
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title_row = QHBoxLayout()
        header = QLabel("Dosya Yükle")
        header.setObjectName("DialogTitle")
        self.lbl_overall_speed = QLabel("")
        self.lbl_overall_speed.setObjectName("UploadOverallSpeed")
        self.lbl_overall_speed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_overall_speed.setVisible(False)
        title_row.addWidget(header)
        title_row.addStretch()
        title_row.addWidget(self.lbl_overall_speed)
        root.addLayout(title_row)

        self.lbl_target = QLabel(f"Hedef: {self.current_path}")
        self.lbl_target.setObjectName("UploadSummaryLabel")
        root.addWidget(self.lbl_target)

        self.phase_stack = QStackedWidget()

        # --- Faz 1: Seçim ---
        select_page = QWidget()
        select_layout = QVBoxLayout(select_page)
        select_layout.setContentsMargins(0, 0, 0, 0)
        select_layout.setSpacing(10)

        self.drop_zone = DropZoneFrame()
        self.drop_zone.btn_select_files.clicked.connect(self.select_files)
        self.drop_zone.btn_select_folder.clicked.connect(self.select_folder)
        self.drop_zone.paths_dropped.connect(self._on_paths_dropped)
        select_layout.addWidget(self.drop_zone)

        self.lbl_summary = QLabel("Henüz dosya seçilmedi")
        self.lbl_summary.setObjectName("UploadSummaryLabel")
        select_layout.addWidget(self.lbl_summary)

        self.file_list = UploadFileList()
        self.file_list.setMinimumHeight(180)
        self.file_list.remove_requested.connect(self._remove_file)
        select_layout.addWidget(self.file_list, stretch=1)

        acl_row = QHBoxLayout()
        acl_row.addWidget(QLabel("Erişim İzni:"))
        self.rb_private = QRadioButton("🔒 Private")
        self.rb_public = QRadioButton("🔓 Public")
        self.rb_private.setChecked(True)
        self.rb_private.toggled.connect(self._update_summary)
        acl_row.addWidget(self.rb_private)
        acl_row.addWidget(self.rb_public)
        acl_row.addStretch()
        select_layout.addLayout(acl_row)

        metadata_row = QHBoxLayout()
        self.lbl_metadata_status = QLabel()
        self.lbl_metadata_status.setObjectName("UploadSummaryLabel")
        self.btn_metadata_settings = QPushButton("Ayarlar...")
        self.btn_metadata_settings.setObjectName("SecondaryButton")
        self.btn_metadata_settings.setFixedHeight(28)
        self.btn_metadata_settings.clicked.connect(self._open_metadata_settings)
        metadata_row.addWidget(self.lbl_metadata_status)
        metadata_row.addStretch()
        metadata_row.addWidget(self.btn_metadata_settings)
        select_layout.addLayout(metadata_row)
        self._update_metadata_status_label()

        select_btns = QHBoxLayout()
        self.btn_close_select = QPushButton("Kapat")
        self.btn_close_select.setObjectName("SecondaryButton")
        self.btn_close_select.clicked.connect(self.reject)
        self.btn_upload = QPushButton("📤 Yüklemeyi Başlat")
        self.btn_upload.setEnabled(False)
        self.btn_upload.clicked.connect(self.start_upload)
        select_btns.addWidget(self.btn_close_select)
        select_btns.addStretch()
        select_btns.addWidget(self.btn_upload)
        select_layout.addLayout(select_btns)

        self.phase_stack.addWidget(select_page)

        # --- Faz 2: Yükleme ---
        upload_page = QWidget()
        upload_layout = QVBoxLayout(upload_page)
        upload_layout.setContentsMargins(0, 0, 0, 0)
        upload_layout.setSpacing(10)

        upload_header = QFrame()
        upload_header.setObjectName("UploadHeader")
        header_layout = QVBoxLayout(upload_header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(8)

        self.lbl_upload_status = QLabel("Yükleniyor... 0 / 0 dosya")
        self.lbl_upload_status.setObjectName("UploadPhaseStatus")
        header_layout.addWidget(self.lbl_upload_status)

        overall_row = QHBoxLayout()
        overall_row.setSpacing(14)
        self.overall_progress = QProgressBar()
        self.overall_progress.setObjectName("UploadOverallProgress")
        self.overall_progress.setFixedHeight(14)
        self.overall_progress.setTextVisible(False)

        self.lbl_overall_pct = QLabel("0%")
        self.lbl_overall_pct.setObjectName("UploadOverallPct")
        self.lbl_overall_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        overall_row.addWidget(self.overall_progress, stretch=1)
        overall_row.addWidget(self.lbl_overall_pct)
        header_layout.addLayout(overall_row)
        upload_layout.addWidget(upload_header)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("UploadScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("UploadScrollContent")
        self.scroll_content.setAutoFillBackground(True)
        self.progress_layout = QVBoxLayout(self.scroll_content)
        self.progress_layout.setContentsMargins(8, 8, 8, 8)
        self.progress_layout.setSpacing(6)
        self.progress_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        upload_layout.addWidget(self.scroll, stretch=1)

        upload_btns = QHBoxLayout()
        self.btn_cancel_upload = QPushButton("İptal")
        self.btn_cancel_upload.setObjectName("SecondaryButton")
        self.btn_cancel_upload.clicked.connect(self._on_cancel_clicked)
        self.btn_close_upload = QPushButton("Kapat")
        self.btn_close_upload.setObjectName("SecondaryButton")
        self.btn_close_upload.clicked.connect(self._on_close_upload_clicked)
        upload_btns.addWidget(self.btn_cancel_upload)
        upload_btns.addStretch()
        upload_btns.addWidget(self.btn_close_upload)
        upload_layout.addLayout(upload_btns)

        self.phase_stack.addWidget(upload_page)

        # --- Faz 3: Özet ---
        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 40, 0, 40)
        summary_layout.addStretch()

        self.lbl_summary_result = QLabel("")
        self.lbl_summary_result.setAlignment(Qt.AlignCenter)
        self.lbl_summary_result.setObjectName("DialogSummaryResult")
        self.lbl_summary_result.setWordWrap(True)
        summary_layout.addWidget(self.lbl_summary_result)
        summary_layout.addStretch()

        summary_btns = QHBoxLayout()
        self.btn_close_summary = QPushButton("Kapat")
        self.btn_close_summary.setObjectName("SecondaryButton")
        self.btn_close_summary.clicked.connect(self.reject)
        self.btn_new_upload = QPushButton("Yeni Yükleme")
        self.btn_new_upload.clicked.connect(self._enter_select_phase)
        summary_btns.addWidget(self.btn_close_summary)
        summary_btns.addStretch()
        summary_btns.addWidget(self.btn_new_upload)
        summary_layout.addLayout(summary_btns)

        self.phase_stack.addWidget(summary_page)
        root.addWidget(self.phase_stack, stretch=1)

        # Geriye uyumluluk: main_window eski attribute adlarını kullanıyor
        self.btn_select_files = self.drop_zone.btn_select_files
        self.btn_select_folder = self.drop_zone.btn_select_folder
        self.btn_close = self.btn_close_select

    def apply_styles(self):
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

    def _enter_upload_phase(self):
        self._uploading = True
        self._cancelling = False
        self._success_count = 0
        self._error_count = 0
        self.phase_stack.setCurrentIndex(self.PHASE_UPLOAD)
        self.btn_cancel_upload.setEnabled(True)
        self.btn_cancel_upload.setText("İptal")
        self.btn_close_upload.setEnabled(True)
        total = len(self.progress_widgets)
        self.lbl_upload_status.setText(f"Yükleniyor... 0 / {total} dosya")
        self.overall_progress.setValue(0)
        self.lbl_overall_pct.setText("0%")
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(True)

    def _reset_selection_state(self):
        """Yeni yükleme için seçim listesini ve sayaçları sıfırla."""
        self.selected_files = []
        self.selected_folder = None
        self._success_count = 0
        self._error_count = 0
        self._cancelling = False
        self.file_list.set_files([], None)
        self._update_summary()

    def _enter_select_phase(self, *, fresh: bool = True):
        self._uploading = False
        self.phase_stack.setCurrentIndex(self.PHASE_SELECT)
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(False)
        self.clear_progress_area()
        if fresh:
            self._reset_selection_state()
        else:
            self._update_summary()
        self._set_selection_enabled(True)
        self.btn_upload.setEnabled(len(self.selected_files) > 0)

    def _enter_summary_phase(self, cancelled: bool = False):
        self._uploading = False
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(False)
        self.phase_stack.setCurrentIndex(self.PHASE_SUMMARY)
        total = len(self.progress_widgets) or (self._success_count + self._error_count)
        if cancelled:
            done = self._success_count + self._error_count
            self.lbl_summary_result.setText(
                f"Yükleme iptal edildi.\n{done} / {total} dosya işlendi "
                f"({self._success_count} başarılı, {self._error_count} hata)."
            )
        elif self._error_count == 0:
            self.lbl_summary_result.setText(f"✓ {self._success_count} dosya başarıyla yüklendi.")
        else:
            self.lbl_summary_result.setText(
                f"{self._success_count} başarılı, {self._error_count} hata "
                f"(toplam {total} dosya)."
            )

    def _set_selection_enabled(self, enabled: bool):
        self.btn_select_files.setEnabled(enabled)
        self.btn_select_folder.setEnabled(enabled)
        self.rb_private.setEnabled(enabled)
        self.rb_public.setEnabled(enabled)

    def _acl_label(self) -> str:
        return "🔓 Public" if self.rb_public.isChecked() else "🔒 Private"

    def _preview_remote_key(self, local_path: str) -> str:
        normalized = os.path.normpath(local_path)
        if self.selected_folder:
            try:
                return os.path.relpath(normalized, self.selected_folder).replace('\\', '/')
            except ValueError:
                return os.path.basename(normalized)
        return os.path.basename(normalized)

    def _content_types_for_files(self, files: list) -> dict:
        result = {}
        for path in files:
            remote_key = self._preview_remote_key(path)
            ctype = preview_content_type(path, remote_key, self.metadata_settings)
            if ctype:
                result[path] = ctype
        return result

    def _update_metadata_status_label(self):
        if self.metadata_settings.enabled:
            self.lbl_metadata_status.setText("Otomatik metadata: Açık")
        else:
            self.lbl_metadata_status.setText("Otomatik metadata: Kapalı")

    def _open_metadata_settings(self):
        dlg = UploadMetadataSettingsDialog(self, self.settings)
        if dlg.exec() == QDialog.Accepted:
            self.metadata_settings = dlg.result_settings()
            self._update_metadata_status_label()
            if self.selected_files:
                self.file_list.set_files(
                    self.selected_files,
                    self.selected_folder,
                    self._content_types_for_files(self.selected_files),
                )
            self._update_summary()

    def _total_size(self) -> int:
        total = 0
        for path in self.selected_files:
            try:
                total += os.path.getsize(path)
            except OSError:
                pass
        return total

    def _update_summary(self):
        count = len(self.selected_files)
        if count == 0:
            self.lbl_summary.setText("Henüz dosya seçilmedi")
        else:
            self.lbl_summary.setText(
                f"{count} dosya · {format_file_size(self._total_size())} · {self._acl_label()}"
            )
        self.btn_upload.setEnabled(count > 0 and not self._uploading)

    def _apply_selection(self, files: list, folder: str = None):
        seen = set()
        unique_files = []
        for path in files:
            normalized = os.path.normpath(path)
            if normalized not in seen:
                seen.add(normalized)
                unique_files.append(normalized)
        self.selected_files = unique_files
        self.selected_folder = folder
        self.clear_progress_area()
        self.file_list.set_files(
            unique_files, folder, self._content_types_for_files(unique_files),
        )
        self._update_summary()

    def _collect_files_from_paths(self, paths: list):
        """Sürüklenen path'lerden dosya listesi ve opsiyonel klasör kökü üret."""
        if len(paths) == 1 and os.path.isdir(paths[0]):
            folder = os.path.normpath(paths[0])
            files = []
            for root, _, fnames in os.walk(folder):
                for fname in fnames:
                    files.append(os.path.normpath(os.path.join(root, fname)))
            return files, folder

        files = []
        folders_seen = []
        for p in paths:
            p = os.path.normpath(p)
            if os.path.isdir(p):
                folders_seen.append(p)
                for root, _, fnames in os.walk(p):
                    for fname in fnames:
                        files.append(os.path.normpath(os.path.join(root, fname)))
            elif os.path.isfile(p):
                files.append(p)

        folder = folders_seen[0] if len(folders_seen) == 1 and len(paths) == 1 else None
        if len(paths) == 1 and os.path.isdir(paths[0]):
            folder = os.path.normpath(paths[0])
        elif len(folders_seen) == 1 and not any(os.path.isfile(x) for x in paths):
            folder = folders_seen[0]
        else:
            folder = None
        return files, folder

    def _on_paths_dropped(self, paths: list):
        files, folder = self._collect_files_from_paths(paths)
        if files:
            logger.info(f"Sürükle-bırak: {len(files)} dosya")
            self._apply_selection(files, folder)

    def _remove_file(self, path: str):
        path = os.path.normpath(path)
        if path in self.selected_files:
            self.selected_files.remove(path)
        if not self.selected_files:
            self.selected_folder = None
        self.file_list.set_files(
            self.selected_files,
            self.selected_folder,
            self._content_types_for_files(self.selected_files),
        )
        self._update_summary()

    def clear_progress_area(self):
        for path, widget in list(self.progress_widgets.items()):
            self.progress_layout.removeWidget(widget)
            widget.deleteLater()
        self.progress_widgets.clear()
        self._file_sizes.clear()
        self._total_bytes = 0

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Dosya Seç")
        if files:
            self._apply_selection([os.path.normpath(f) for f in files], folder=None)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            folder = os.path.normpath(folder)
            logger.info(f"Klasör seçildi: {folder}")
            files = []
            for root, _, fnames in os.walk(folder):
                for fname in fnames:
                    files.append(os.path.normpath(os.path.join(root, fname)))
            logger.info(f"Klasörden {len(files)} dosya eklendi")
            self._apply_selection(files, folder)

    def start_upload(self):
        logger.info("start_upload() çağrıldı")
        try:
            acl = "public-read" if self.rb_public.isChecked() else "private"
            valid_files = []
            self._total_bytes = 0
            self.clear_progress_area()

            self.scroll_content.setUpdatesEnabled(False)
            try:
                for path in self.selected_files:
                    try:
                        if not os.path.exists(path):
                            QMessageBox.warning(
                                self, "Uyarı", f"Dosya bulunamadı: {os.path.basename(path)}"
                            )
                            continue
                        normalized_path = os.path.normpath(path)
                        file_size = os.path.getsize(path)
                        self._file_sizes[normalized_path] = file_size
                        self._total_bytes += file_size
                        if normalized_path not in self.progress_widgets:
                            display_name = (
                                os.path.relpath(normalized_path, self.selected_folder)
                                if self.selected_folder
                                else os.path.basename(normalized_path)
                            )
                            w = UploadProgressBar(display_name, file_size)
                            self.progress_layout.addWidget(w)
                            self.progress_widgets[normalized_path] = w
                        valid_files.append(normalized_path)
                    except Exception as e:
                        QMessageBox.warning(
                            self, "Uyarı",
                            f"Dosya okunamadı: {os.path.basename(path)}\n{str(e)}",
                        )
            finally:
                self.scroll_content.setUpdatesEnabled(True)

            if not valid_files:
                QMessageBox.warning(self, "Uyarı", "Yüklenecek geçerli dosya bulunamadı.")
                return

            self._set_selection_enabled(False)
            self.btn_upload.setEnabled(False)
            self._enter_upload_phase()
            self.upload_started.emit(valid_files, acl)

        except Exception as e:
            logger.error(f"start_upload() hatası: {str(e)}", exc_info=True)
            QMessageBox.critical(self, "Hata", f"Upload başlatılamadı: {str(e)}")
            self._set_selection_enabled(True)
            self.btn_upload.setEnabled(len(self.selected_files) > 0)

    def _on_cancel_clicked(self):
        if not self._uploading or self._cancelling:
            return
        self._cancelling = True
        self.btn_cancel_upload.setEnabled(False)
        self.btn_close_upload.setEnabled(False)
        self.btn_cancel_upload.setText("İptal ediliyor...")
        self.lbl_upload_status.setText("İptal ediliyor...")
        QApplication.processEvents()
        self.cancel_requested.emit()

    def _on_close_upload_clicked(self):
        if self._uploading:
            self._on_cancel_clicked()
        else:
            self.reject()

    def closeEvent(self, event):
        if self._uploading:
            event.ignore()
            if not self._cancelling:
                self._on_cancel_clicked()
            return
        super().closeEvent(event)

    def on_upload_cancelled(self):
        if self.phase_stack.currentIndex() == self.PHASE_SUMMARY:
            return
        self._uploading = False
        self._cancelling = False
        self.btn_cancel_upload.setText("İptal")
        self.btn_cancel_upload.setEnabled(False)
        self.btn_close_upload.setEnabled(True)
        self._set_selection_enabled(True)
        self._enter_summary_phase(cancelled=True)

    def on_upload_finished(self):
        if self.phase_stack.currentIndex() == self.PHASE_SUMMARY:
            return
        self._uploading = False
        self.btn_cancel_upload.setEnabled(False)
        self.btn_close_upload.setEnabled(True)
        self._set_selection_enabled(True)
        self._enter_summary_phase(cancelled=False)

    def _find_progress_widget(self, path: str):
        normalized_path = os.path.normpath(path) if path else path
        if normalized_path in self.progress_widgets:
            return self.progress_widgets[normalized_path]
        for widget_path, widget in self.progress_widgets.items():
            if os.path.normpath(widget_path).lower() == normalized_path.lower():
                return widget
        return None

    def _schedule_overall_progress(self):
        if not self._overall_timer.isActive():
            self._overall_timer.start()

    def _update_overall_progress(self):
        if not self.progress_widgets or not self._total_bytes:
            return
        if self._cancelling:
            return
        total_uploaded = sum(w.uploaded_bytes for w in self.progress_widgets.values())
        pct = min(100, int(total_uploaded / self._total_bytes * 100))
        self.overall_progress.setValue(pct)
        self.lbl_overall_pct.setText(f"{pct}%")

        speeds = []
        for w in self.progress_widgets.values():
            txt = w.lbl_speed.text().replace(" MB/s", "").strip()
            if txt:
                try:
                    speeds.append(float(txt))
                except ValueError:
                    pass
        total_speed = sum(speeds) if speeds else 0.0
        self.lbl_overall_speed.setText(_format_speed_mbps(total_speed))

        done = self._success_count + self._error_count
        total = len(self.progress_widgets)
        self.lbl_upload_status.setText(f"Yükleniyor... {done} / {total} dosya")

    @Slot(str, float, str)
    def update_progress(self, path, val, info):
        widget = self._find_progress_widget(path)
        if widget:
            uploaded_bytes = int(widget.filesize * val) if val > 0 else 0
            widget.update_progress(val, uploaded_bytes, 0.0, False, 0, 0, info)
            self._schedule_overall_progress()

    @Slot(str, float, int, float, bool, int, int, str)
    def update_progress_detailed(
        self, path, val, uploaded_bytes, speed_mbps,
        is_multipart, multipart_parts, multipart_completed, info,
    ):
        widget = self._find_progress_widget(path)
        if widget:
            try:
                widget.update_progress(
                    val, uploaded_bytes, speed_mbps, is_multipart,
                    multipart_parts, multipart_completed, info,
                )
                self._schedule_overall_progress()
            except Exception as e:
                logger.error(f"update_progress_detailed() hatası: {str(e)}", exc_info=True)
        else:
            logger.warning(f"Progress widget bulunamadı: {path}")

    @Slot(str)
    def set_completed(self, path):
        widget = self._find_progress_widget(path)
        if widget:
            widget.set_completed()
            widget.uploaded_bytes = widget.filesize
            self._success_count += 1
            self._update_overall_progress()

    @Slot(str, str)
    def set_error(self, path, msg):
        widget = self._find_progress_widget(path)
        if widget:
            widget.set_error(msg)
            self._error_count += 1
            self._update_overall_progress()


class DownloadItemList(QWidget):
    """İndirilecek uzak öğeleri salt okunur listeler."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_empty = QLabel("İndirilecek öğe yok")
        self.lbl_empty.setObjectName("UploadSummaryLabel")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("UploadFileList")
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)
        layout.addWidget(self.lbl_empty)
        layout.addWidget(self.list_widget)

    def set_items(self, items: list):
        self.list_widget.clear()
        if not items:
            self.lbl_empty.setVisible(True)
            self.list_widget.setVisible(False)
            return
        self.lbl_empty.setVisible(False)
        self.list_widget.setVisible(True)
        for item in items:
            name = item.get('name', '?')
            if item.get('type') == 'folder':
                text = f"📁 {name}"
            else:
                size = format_file_size(item.get('size', 0))
                text = f"📄 {name}  ({size})"
            self.list_widget.addItem(text)


class DownloadDialog(QDialog):
    """Üç fazlı indirme dialogu: onay → indirme → özet."""

    download_started = Signal(list, str)
    cancel_requested = Signal()

    PHASE_SELECT = 0
    PHASE_DOWNLOAD = 1
    PHASE_SUMMARY = 2

    def __init__(self, parent=None, items=None, current_path="/"):
        super().__init__(parent)
        self.items = list(items or [])
        self.current_path = current_path
        self.local_dir = ""
        self.progress_widgets = {}
        self._file_sizes = {}
        self._success_count = 0
        self._error_count = 0
        self._total_bytes = 0
        self._downloading = False
        self._cancelling = False
        self._overall_timer = QTimer(self)
        self._overall_timer.setSingleShot(True)
        self._overall_timer.setInterval(PROGRESS_UI_INTERVAL_MS)
        self._overall_timer.timeout.connect(self._update_overall_progress)

        self.setWindowTitle("Dosya İndir")
        self.setObjectName("ElevatedDialog")
        self.resize(720, 640)
        self.init_ui()
        self.apply_styles()
        self._populate_items()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        title_row = QHBoxLayout()
        header = QLabel("Dosya İndir")
        header.setObjectName("DialogTitle")
        self.lbl_overall_speed = QLabel("")
        self.lbl_overall_speed.setObjectName("UploadOverallSpeed")
        self.lbl_overall_speed.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_overall_speed.setVisible(False)
        title_row.addWidget(header)
        title_row.addStretch()
        title_row.addWidget(self.lbl_overall_speed)
        root.addLayout(title_row)

        self.lbl_source = QLabel(f"Kaynak: {self.current_path}")
        self.lbl_source.setObjectName("UploadSummaryLabel")
        root.addWidget(self.lbl_source)

        self.phase_stack = QStackedWidget()

        # --- Faz 1: Onay ---
        select_page = QWidget()
        select_layout = QVBoxLayout(select_page)
        select_layout.setContentsMargins(0, 0, 0, 0)
        select_layout.setSpacing(10)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setObjectName("UploadSummaryLabel")
        select_layout.addWidget(self.lbl_summary)

        self.item_list = DownloadItemList()
        self.item_list.setMinimumHeight(180)
        select_layout.addWidget(self.item_list, stretch=1)

        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Hedef klasör:"))
        self.lbl_dest = QLabel("Henüz seçilmedi")
        self.lbl_dest.setObjectName("UploadSummaryLabel")
        self.lbl_dest.setWordWrap(True)
        self.btn_select_dest = QPushButton("📁 Klasör Seç")
        self.btn_select_dest.setObjectName("SecondaryButton")
        self.btn_select_dest.clicked.connect(self.select_dest_folder)
        dest_row.addWidget(self.lbl_dest, stretch=1)
        dest_row.addWidget(self.btn_select_dest)
        select_layout.addLayout(dest_row)

        select_btns = QHBoxLayout()
        self.btn_close_select = QPushButton("Kapat")
        self.btn_close_select.setObjectName("SecondaryButton")
        self.btn_close_select.clicked.connect(self.reject)
        self.btn_download = QPushButton("📥 İndirmeyi Başlat")
        self.btn_download.setEnabled(False)
        self.btn_download.clicked.connect(self.start_download)
        select_btns.addWidget(self.btn_close_select)
        select_btns.addStretch()
        select_btns.addWidget(self.btn_download)
        select_layout.addLayout(select_btns)
        self.phase_stack.addWidget(select_page)

        # --- Faz 2: İndirme ---
        download_page = QWidget()
        download_layout = QVBoxLayout(download_page)
        download_layout.setContentsMargins(0, 0, 0, 0)
        download_layout.setSpacing(10)

        download_header = QFrame()
        download_header.setObjectName("UploadHeader")
        header_layout = QVBoxLayout(download_header)
        header_layout.setContentsMargins(0, 0, 0, 10)
        header_layout.setSpacing(8)

        self.lbl_download_status = QLabel("İndiriliyor... 0 / 0 dosya")
        self.lbl_download_status.setObjectName("UploadPhaseStatus")
        header_layout.addWidget(self.lbl_download_status)

        overall_row = QHBoxLayout()
        overall_row.setSpacing(14)
        self.overall_progress = QProgressBar()
        self.overall_progress.setObjectName("UploadOverallProgress")
        self.overall_progress.setFixedHeight(14)
        self.overall_progress.setTextVisible(False)
        self.lbl_overall_pct = QLabel("0%")
        self.lbl_overall_pct.setObjectName("UploadOverallPct")
        self.lbl_overall_pct.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        overall_row.addWidget(self.overall_progress, stretch=1)
        overall_row.addWidget(self.lbl_overall_pct)
        header_layout.addLayout(overall_row)
        download_layout.addWidget(download_header)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("UploadScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("UploadScrollContent")
        self.scroll_content.setAutoFillBackground(True)
        self.progress_layout = QVBoxLayout(self.scroll_content)
        self.progress_layout.setContentsMargins(8, 8, 8, 8)
        self.progress_layout.setSpacing(6)
        self.progress_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        download_layout.addWidget(self.scroll, stretch=1)

        download_btns = QHBoxLayout()
        self.btn_cancel_download = QPushButton("İptal")
        self.btn_cancel_download.setObjectName("SecondaryButton")
        self.btn_cancel_download.clicked.connect(self._on_cancel_clicked)
        self.btn_close_download = QPushButton("Kapat")
        self.btn_close_download.setObjectName("SecondaryButton")
        self.btn_close_download.clicked.connect(self._on_close_download_clicked)
        download_btns.addWidget(self.btn_cancel_download)
        download_btns.addStretch()
        download_btns.addWidget(self.btn_close_download)
        download_layout.addLayout(download_btns)
        self.phase_stack.addWidget(download_page)

        # --- Faz 3: Özet ---
        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        summary_layout.setContentsMargins(0, 40, 0, 40)
        summary_layout.addStretch()
        self.lbl_summary_result = QLabel("")
        self.lbl_summary_result.setAlignment(Qt.AlignCenter)
        self.lbl_summary_result.setObjectName("DialogSummaryResult")
        self.lbl_summary_result.setWordWrap(True)
        summary_layout.addWidget(self.lbl_summary_result)
        summary_layout.addStretch()
        summary_btns = QHBoxLayout()
        self.btn_close_summary = QPushButton("Kapat")
        self.btn_close_summary.setObjectName("SecondaryButton")
        self.btn_close_summary.clicked.connect(self.reject)
        summary_btns.addStretch()
        summary_btns.addWidget(self.btn_close_summary)
        summary_btns.addStretch()
        summary_layout.addLayout(summary_btns)
        self.phase_stack.addWidget(summary_page)

        root.addWidget(self.phase_stack, stretch=1)

    def apply_styles(self):
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

    def _populate_items(self):
        self.item_list.set_items(self.items)
        self._update_summary()

    def _update_summary(self):
        count = len(self.items)
        if count == 0:
            self.lbl_summary.setText("İndirilecek öğe yok")
        else:
            total_size = sum(i.get('size', 0) for i in self.items if i.get('type') == 'file')
            dest = self.local_dir or "henüz seçilmedi"
            self.lbl_summary.setText(
                f"{count} öğe · {format_file_size(total_size)} · hedef: {dest}"
            )
        self.btn_download.setEnabled(bool(self.items and self.local_dir and not self._downloading))

    def select_dest_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "İndirilecek klasörü seçin")
        if folder:
            self.local_dir = os.path.normpath(folder)
            self.lbl_dest.setText(self.local_dir)
            self._update_summary()

    def setup_progress_widgets(self, tasks: list):
        self.clear_progress_area()
        self._total_bytes = 0
        self.scroll_content.setUpdatesEnabled(False)
        try:
            for task in tasks:
                local_path = os.path.normpath(task['local_path'])
                file_size = task.get('file_size', 0)
                self._file_sizes[local_path] = file_size
                self._total_bytes += file_size
                display_name = task.get('display_name') or os.path.basename(local_path)
                w = UploadProgressBar(display_name, file_size)
                self.progress_layout.addWidget(w)
                self.progress_widgets[local_path] = w
        finally:
            self.scroll_content.setUpdatesEnabled(True)

    def clear_progress_area(self):
        for widget in list(self.progress_widgets.values()):
            self.progress_layout.removeWidget(widget)
            widget.deleteLater()
        self.progress_widgets.clear()
        self._file_sizes.clear()
        self._total_bytes = 0

    def start_download(self):
        if not self.items or not self.local_dir:
            QMessageBox.warning(self, "Uyarı", "Öğe ve hedef klasör seçilmelidir.")
            return
        self.download_started.emit(self.items, self.local_dir)

    def _enter_download_phase(self):
        self._downloading = True
        self._cancelling = False
        self._success_count = 0
        self._error_count = 0
        self.phase_stack.setCurrentIndex(self.PHASE_DOWNLOAD)
        self.btn_cancel_download.setEnabled(True)
        self.btn_cancel_download.setText("İptal")
        self.btn_close_download.setEnabled(True)
        total = len(self.progress_widgets)
        self.lbl_download_status.setText(f"İndiriliyor... 0 / {total} dosya")
        self.overall_progress.setValue(0)
        self.lbl_overall_pct.setText("0%")
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(True)
        self.btn_select_dest.setEnabled(False)
        self.btn_download.setEnabled(False)

    def _reset_select_state(self):
        self.local_dir = ""
        self.lbl_dest.setText("Henüz seçilmedi")
        self._success_count = 0
        self._error_count = 0
        self._cancelling = False
        self._update_summary()

    def _enter_select_phase(self, *, fresh: bool = True):
        self._downloading = False
        self.phase_stack.setCurrentIndex(self.PHASE_SELECT)
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(False)
        self.clear_progress_area()
        if fresh:
            self._reset_select_state()
        else:
            self._update_summary()
        self.btn_select_dest.setEnabled(True)

    def _enter_summary_phase(self, cancelled: bool = False):
        self._downloading = False
        self.lbl_overall_speed.setText("")
        self.lbl_overall_speed.setVisible(False)
        self.phase_stack.setCurrentIndex(self.PHASE_SUMMARY)
        total = len(self.progress_widgets) or (self._success_count + self._error_count)
        if cancelled:
            done = self._success_count + self._error_count
            self.lbl_summary_result.setText(
                f"İndirme iptal edildi.\n{done} / {total} dosya işlendi "
                f"({self._success_count} başarılı, {self._error_count} hata)."
            )
        elif self._error_count == 0:
            self.lbl_summary_result.setText(f"✓ {self._success_count} dosya başarıyla indirildi.")
        else:
            self.lbl_summary_result.setText(
                f"{self._success_count} başarılı, {self._error_count} hata "
                f"(toplam {total} dosya)."
            )

    def _on_cancel_clicked(self):
        if not self._downloading or self._cancelling:
            return
        self._cancelling = True
        self.btn_cancel_download.setEnabled(False)
        self.btn_close_download.setEnabled(False)
        self.btn_cancel_download.setText("İptal ediliyor...")
        self.lbl_download_status.setText("İptal ediliyor...")
        QApplication.processEvents()
        self.cancel_requested.emit()

    def _on_close_download_clicked(self):
        if self._downloading:
            self._on_cancel_clicked()
        else:
            self.reject()

    def closeEvent(self, event):
        if self._downloading:
            event.ignore()
            if not self._cancelling:
                self._on_cancel_clicked()
            return
        super().closeEvent(event)

    def on_download_cancelled(self):
        if self.phase_stack.currentIndex() == self.PHASE_SUMMARY:
            return
        self._downloading = False
        self._cancelling = False
        self.btn_cancel_download.setText("İptal")
        self.btn_cancel_download.setEnabled(False)
        self.btn_close_download.setEnabled(True)
        self.btn_select_dest.setEnabled(True)
        self._enter_summary_phase(cancelled=True)

    def on_download_finished(self):
        if self.phase_stack.currentIndex() == self.PHASE_SUMMARY:
            return
        self._downloading = False
        self.btn_cancel_download.setEnabled(False)
        self.btn_close_download.setEnabled(True)
        self.btn_select_dest.setEnabled(True)
        self._enter_summary_phase(cancelled=False)

    def _find_progress_widget(self, path: str):
        normalized = os.path.normpath(path) if path else path
        if normalized in self.progress_widgets:
            return self.progress_widgets[normalized]
        for widget_path, widget in self.progress_widgets.items():
            if os.path.normpath(widget_path).lower() == normalized.lower():
                return widget
        return None

    def _schedule_overall_progress(self):
        if not self._overall_timer.isActive():
            self._overall_timer.start()

    def _update_overall_progress(self):
        if not self.progress_widgets or not self._total_bytes:
            return
        if self._cancelling:
            return
        total_done = sum(w.uploaded_bytes for w in self.progress_widgets.values())
        pct = min(100, int(total_done / self._total_bytes * 100))
        self.overall_progress.setValue(pct)
        self.lbl_overall_pct.setText(f"{pct}%")
        speeds = []
        for w in self.progress_widgets.values():
            txt = w.lbl_speed.text().replace(" MB/s", "").strip()
            if txt:
                try:
                    speeds.append(float(txt))
                except ValueError:
                    pass
        self.lbl_overall_speed.setText(_format_speed_mbps(sum(speeds) if speeds else 0.0))
        done = self._success_count + self._error_count
        total = len(self.progress_widgets)
        self.lbl_download_status.setText(f"İndiriliyor... {done} / {total} dosya")

    @Slot(str, float, int, float, str)
    def update_progress_detailed(self, path, val, downloaded_bytes, speed_mbps, info):
        widget = self._find_progress_widget(path)
        if widget:
            widget.update_progress(val, downloaded_bytes, speed_mbps, False, 0, 0, info)
            self._schedule_overall_progress()

    @Slot(str)
    def set_completed(self, path):
        widget = self._find_progress_widget(path)
        if widget:
            widget.set_completed()
            widget.uploaded_bytes = widget.filesize
            self._success_count += 1
            self._update_overall_progress()

    @Slot(str, str)
    def set_error(self, path, msg):
        widget = self._find_progress_widget(path)
        if widget:
            widget.set_error(msg)
            self._error_count += 1
            self._update_overall_progress()


class ShareDialog(QDialog):
    """Presigned URL paylaşım süresi seçimi."""

    def __init__(self, parent=None, filename: str = ""):
        super().__init__(parent)
        self.days = 3
        self.setWindowTitle("Paylaşım Süresi")
        self.setObjectName("ElevatedDialog")
        self.setFixedSize(420, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel(f"Paylaşım: {filename}" if filename else "Paylaşım süresi seçin")
        title.setObjectName("DialogTitle")
        title.setWordWrap(True)
        layout.addWidget(title)
        btn_layout = QHBoxLayout()
        btn_3 = QPushButton("3 Gün")
        btn_7 = QPushButton("7 Gün")
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("SecondaryButton")
        btn_3.clicked.connect(lambda: self._choose(3))
        btn_7.clicked.connect(lambda: self._choose(7))
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_3)
        btn_layout.addWidget(btn_7)
        layout.addLayout(btn_layout)
        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

    def _choose(self, days: int):
        self.days = days
        self.accept()


class DestinationPathDialog(QDialog):
    """Kopyala/taşı için hedef klasör prefix'i seçimi."""

    def __init__(self, parent=None, title: str = "Hedef Klasör", current_path: str = '/', hint: str = ''):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setObjectName("ElevatedDialog")
        self.resize(480, 160)
        self._result_path = ''

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        lbl = QLabel(hint or "Hedef klasör yolunu girin (ör. folder/subfolder/):")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        default = current_path if current_path.endswith('/') else current_path + '/'
        if default == '/':
            default = ''
        self.edit_path = QLineEdit(default)
        self.edit_path.setPlaceholderText("boş = bucket kökü")
        layout.addWidget(self.edit_path)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_ok = QPushButton("Tamam")
        btn_ok.setObjectName("PrimaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._accept)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        apply_dialog_elevation(self, dark=(current_theme_mode() == "dark"))

    def _accept(self):
        path = self.edit_path.text().strip().replace('\\', '/')
        if path.startswith('/'):
            path = path[1:]
        if path and not path.endswith('/'):
            path += '/'
        self._result_path = path
        self.accept()

    @property
    def destination_prefix(self) -> str:
        return self._result_path
