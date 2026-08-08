"""Main window and background workers for S3MANAGER."""
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from PySide6.QtCore import Qt, QThread, Signal, Slot, QItemSelectionModel, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTreeView, QHeaderView,
    QFrame, QMenu, QMessageBox, QFileDialog,
)

from src.ui.qt.models import FileModel
from src.ui.qt.styles import get_dark_theme
from src.ui.qt.dialogs import LoginDialog, UploadDialog, DownloadDialog, ShareDialog
from src.services.spaces_client import SpacesClient, UploadCancelled
from src.services.share_service import ShareService
from src.services.upload_service import UploadService
from src.services.listing_cache import ListingCache
from src.config.credentials import CredentialsManager
from src.utils.helpers import join_path
from src.utils.logging_config import get_logger

logger = get_logger('main_window')

LIST_PAGE_SIZE = 200
MAX_ACL_BATCH = 50
MAX_UPLOAD_WORKERS = 3
MAX_DOWNLOAD_WORKERS = 3
WORKER_STOP_TIMEOUT_MS = 60000
SHUTDOWN_WORKER_WAIT_MS = 2500
PROGRESS_EMIT_INTERVAL_S = 0.15


class SpacesWorker(QThread):
    """Paginated folder listing worker."""
    page_loaded = Signal(dict)
    finished_loading = Signal(dict)
    error = Signal(str)

    def __init__(self, client, prefix='', continuation_token=None):
        super().__init__()
        self.client = client
        self.prefix = prefix
        self.continuation_token = continuation_token

    def run(self):
        try:
            token = self.continuation_token
            while not self.isInterruptionRequested():
                page = self.client.list_objects_page(
                    prefix=self.prefix,
                    continuation_token=token,
                    max_keys=LIST_PAGE_SIZE,
                )
                if self.isInterruptionRequested():
                    return
                self.page_loaded.emit(page)
                if not page.get('is_truncated'):
                    break
                token = page.get('next_continuation_token')
            self.finished_loading.emit({'prefix': self.prefix})
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


class AttributeWorker(QThread):
    """Lazy ACL loader for visible file rows."""
    acl_loaded = Signal(str, str)

    def __init__(self, client, paths):
        super().__init__()
        self.client = client
        self.paths = paths[:MAX_ACL_BATCH]

    def run(self):
        for path in self.paths:
            if self.isInterruptionRequested():
                break
            try:
                acl = self.client.get_object_acl(path)
                self.acl_loaded.emit(path, acl)
            except Exception as e:
                logger.debug(f"ACL yüklenemedi {path}: {e}")


class ActionWorker(QThread):
    """Arka planda tek bir callable çalıştırır. QThread.finished ile çakışmaması için action_finished kullanılır."""
    action_finished = Signal()
    error = Signal(str)

    def __init__(self, parent, func, *args, **kwargs):
        super().__init__(parent)
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            if self.isInterruptionRequested():
                return
            self.func(*self.args, **self.kwargs)
            if not self.isInterruptionRequested():
                self.action_finished.emit()
        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))


class ParallelDownloadWorker(QThread):
    file_progress_detailed = Signal(str, float, int, float, str)
    file_completed = Signal(str)
    file_error = Signal(str, str)

    def __init__(self, parent, client, tasks, should_cancel):
        super().__init__(parent)
        self.client = client
        self.tasks = tasks
        self._should_cancel = should_cancel
        self._progress_lock = threading.Lock()
        self._last_emit_time = {}
        self._pending_progress = {}
        self._executor = None

    def _emit_progress(self, local_path, progress_fraction, downloaded_bytes, speed_mbps, info, force=False):
        if self.isInterruptionRequested() or self._should_cancel():
            return
        now = time.monotonic()
        with self._progress_lock:
            self._pending_progress[local_path] = (
                progress_fraction, downloaded_bytes, speed_mbps, info,
            )
            last = self._last_emit_time.get(local_path, 0.0)
            if not force and (now - last) < PROGRESS_EMIT_INTERVAL_S:
                return
            self._last_emit_time[local_path] = now
            pending = self._pending_progress.pop(local_path)

        progress_fraction, downloaded_bytes, speed_mbps, info = pending
        self.file_progress_detailed.emit(
            local_path, progress_fraction, downloaded_bytes, speed_mbps, info,
        )

    def _download_one(self, task):
        if self.isInterruptionRequested() or self._should_cancel():
            return
        remote_key = task['remote_key']
        local_path = os.path.normpath(task['local_path'])
        file_size = task.get('file_size', 0)
        parent = os.path.dirname(local_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        last_bytes = 0
        last_time = time.monotonic()

        def cb(bytes_transferred):
            if self.isInterruptionRequested() or self._should_cancel():
                raise UploadCancelled("İptal edildi")
            nonlocal last_bytes, last_time
            now = time.monotonic()
            speed_mbps = 0.0
            elapsed = now - last_time
            if elapsed > 0.1:
                diff = bytes_transferred - last_bytes
                if diff > 0:
                    speed_mbps = (diff / elapsed) / (1024 * 1024)
                last_bytes = bytes_transferred
                last_time = now
            fraction = (bytes_transferred / file_size) if file_size > 0 else 0.0
            info = f"{bytes_transferred / 1024 / 1024:.1f} MB"
            self._emit_progress(local_path, min(1.0, fraction), int(bytes_transferred), speed_mbps, info)

        try:
            self._emit_progress(local_path, 0.0, 0, 0.0, "Başlıyor...", force=True)
            success = self.client.download_file(
                remote_key, local_path, callback=cb, should_cancel=self._should_cancel,
            )
            if self.isInterruptionRequested() or self._should_cancel():
                return
            if success:
                self.file_completed.emit(local_path)
            elif not self.isInterruptionRequested() and not self._should_cancel():
                self.file_error.emit(local_path, "Bilinmeyen hata")
        except UploadCancelled:
            return
        except Exception as e:
            if not self.isInterruptionRequested() and not self._should_cancel():
                self.file_error.emit(local_path, str(e))

    def run(self):
        executor = None
        try:
            executor = ThreadPoolExecutor(max_workers=MAX_DOWNLOAD_WORKERS)
            self._executor = executor
            futures = {executor.submit(self._download_one, t): t for t in self.tasks}
            pending = set(futures.keys())
            while pending:
                if self.isInterruptionRequested() or self._should_cancel():
                    break
                done, pending = wait(pending, timeout=0.15, return_when=FIRST_COMPLETED)
                for future in done:
                    if self.isInterruptionRequested() or self._should_cancel():
                        break
                    try:
                        future.result()
                    except Exception as e:
                        if not self.isInterruptionRequested() and not self._should_cancel():
                            logger.error(f"Paralel indirme hatası: {e}", exc_info=True)
        except Exception as e:
            if not self.isInterruptionRequested() and not self._should_cancel():
                logger.error(f"ParallelDownloadWorker hatası: {e}", exc_info=True)
        finally:
            self._executor = None
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)


def build_download_tasks(client, items, local_base_dir):
    """Seçili öğelerden indirme görev listesi oluştur."""
    tasks = []
    local_base = os.path.normpath(local_base_dir)
    for item in items:
        path = item['path'].lstrip('/')
        name = item.get('name') or os.path.basename(path.rstrip('/'))
        if item.get('type') == 'folder':
            keys = client.list_all_keys(path)
            prefix = path if path.endswith('/') else path + '/'
            for obj in keys:
                key = obj['key']
                rel = key[len(prefix):] if key.startswith(prefix) else key
                rel = rel.replace('/', os.sep)
                local_path = os.path.join(local_base, name, rel)
                tasks.append({
                    'remote_key': key,
                    'local_path': local_path,
                    'display_name': rel.replace(os.sep, '/'),
                    'file_size': obj.get('size', 0),
                })
        else:
            tasks.append({
                'remote_key': path,
                'local_path': os.path.join(local_base, name),
                'display_name': name,
                'file_size': item.get('size', 0),
            })
    return tasks


class ParallelUploadWorker(QThread):
    file_progress = Signal(str, float, str)
    file_progress_detailed = Signal(str, float, int, float, bool, int, int, str)
    file_completed = Signal(str)
    file_error = Signal(str, str)

    def __init__(self, parent, service, files_to_upload, acl):
        super().__init__(parent)
        self.service = service
        self.files = files_to_upload
        self.acl = acl
        self._progress_lock = threading.Lock()
        self._last_emit_time = {}
        self._pending_progress = {}
        self._executor = None

    def _emit_progress(
        self, file_path, progress_fraction, uploaded_bytes, speed_mbps,
        is_multipart, multipart_parts, multipart_completed, info, force=False,
    ):
        if self.isInterruptionRequested():
            return
        now = time.monotonic()
        with self._progress_lock:
            self._pending_progress[file_path] = (
                progress_fraction, uploaded_bytes, speed_mbps,
                is_multipart, multipart_parts, multipart_completed, info,
            )
            last = self._last_emit_time.get(file_path, 0.0)
            if not force and (now - last) < PROGRESS_EMIT_INTERVAL_S:
                return
            self._last_emit_time[file_path] = now
            pending = self._pending_progress.pop(file_path)

        progress_fraction, uploaded_bytes, speed_mbps, is_multipart, multipart_parts, multipart_completed, info = pending
        self.file_progress_detailed.emit(
            file_path, progress_fraction, uploaded_bytes, speed_mbps,
            is_multipart, multipart_parts, multipart_completed, info,
        )

    def _flush_progress(self, file_path):
        with self._progress_lock:
            pending = self._pending_progress.pop(file_path, None)
        if not pending:
            return
        progress_fraction, uploaded_bytes, speed_mbps, is_multipart, multipart_parts, multipart_completed, info = pending
        self.file_progress_detailed.emit(
            file_path, progress_fraction, uploaded_bytes, speed_mbps,
            is_multipart, multipart_parts, multipart_completed, info,
        )

    def _upload_one(self, file_info):
        if self.isInterruptionRequested():
            return
        file_path = file_info['local_path']
        remote_key = file_info['remote_key']
        if not os.path.exists(file_path):
            self.file_error.emit(file_path, f"Dosya bulunamadı: {file_path}")
            return

        def local_cb(fname, prog, ubytes, speed_mbps, is_multipart, multipart_parts, multipart_completed):
            if self.isInterruptionRequested():
                return
            progress_fraction = prog / 100.0
            info = f"{ubytes / 1024 / 1024:.1f} MB"
            if is_multipart:
                info += f" (multipart {multipart_completed}/{multipart_parts})"
            self._emit_progress(
                file_path, progress_fraction, int(ubytes), speed_mbps,
                is_multipart, multipart_parts, multipart_completed, info,
            )

        try:
            self._emit_progress(
                file_path, 0.0, 0, 0.0, False, 0, 0, "Başlıyor...", force=True,
            )
            success = self.service.upload_file(file_path, remote_key, self.acl, local_cb)
            self._flush_progress(file_path)
            if self.isInterruptionRequested():
                return
            if success:
                self.file_completed.emit(file_path)
            elif not self.isInterruptionRequested():
                self.file_error.emit(file_path, "Bilinmeyen hata")
        except Exception as e:
            if not self.isInterruptionRequested():
                self.file_error.emit(file_path, str(e))

    def run(self):
        executor = None
        try:
            executor = ThreadPoolExecutor(max_workers=MAX_UPLOAD_WORKERS)
            self._executor = executor
            futures = {executor.submit(self._upload_one, f): f for f in self.files}
            pending = set(futures.keys())
            while pending:
                if self.isInterruptionRequested():
                    break
                done, pending = wait(pending, timeout=0.15, return_when=FIRST_COMPLETED)
                for future in done:
                    if self.isInterruptionRequested():
                        break
                    try:
                        future.result()
                    except Exception as e:
                        if not self.isInterruptionRequested():
                            logger.error(f"Paralel upload hatası: {e}", exc_info=True)
        except Exception as e:
            if not self.isInterruptionRequested():
                logger.error(f"ParallelUploadWorker hatası: {e}", exc_info=True)
        finally:
            self._executor = None
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S3MANAGER - DigitalOcean Spaces")
        self.resize(1100, 750)

        self.credentials_manager = CredentialsManager()
        self.listing_cache = ListingCache()
        self.spaces_client = None
        self.share_service = None
        self.upload_service = None
        self.current_path = '/'

        self._list_worker = None
        self._attr_worker = None
        self._action_worker = None
        self._batch_delete_active = False
        self._download_worker = None
        self._upload_worker = None
        self._linger_workers = []
        self._download_cancelled = threading.Event()
        self._continuation_token = None
        self._loading_folders = []
        self._loading_files = []
        self._list_prefix = ''

        self.init_ui()
        self.apply_styles()
        self.setup_shortcuts()
        self.auto_connect()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        toolbar = QFrame()
        toolbar.setObjectName("ToolbarFrame")
        toolbar.setFixedHeight(60)
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(15, 0, 15, 0)

        self.btn_connect = QPushButton("🔌 Bağlan")
        self.btn_upload = QPushButton("📤 Yükle")
        self.btn_refresh = QPushButton("🔄 Yenile")
        self.btn_share = QPushButton("🔗 Paylaş")
        self.btn_download = QPushButton("📥 İndir")
        for btn in [self.btn_connect, self.btn_upload, self.btn_refresh, self.btn_share, self.btn_download]:
            btn.setFixedHeight(32)
            toolbar_layout.addWidget(btn)

        self.btn_upload.setEnabled(False)
        self.btn_share.setEnabled(False)
        self.btn_download.setEnabled(False)

        toolbar_layout.addSpacing(20)
        self.lbl_status = QLabel("Bağlantı bekleniyor...")
        self.lbl_status.setObjectName("StatusLabel")
        toolbar_layout.addWidget(self.lbl_status)
        toolbar_layout.addStretch()

        self.btn_back = QPushButton("← Geri")
        self.btn_back.setObjectName("SecondaryButton")
        self.btn_back.setFixedWidth(100)
        self.btn_back.setFixedHeight(32)
        self.btn_back.setEnabled(False)
        toolbar_layout.addWidget(self.btn_back)

        main_layout.addWidget(toolbar)

        breadcrumb_frame = QFrame()
        breadcrumb_frame.setObjectName("BreadcrumbFrame")
        breadcrumb_frame.setFixedHeight(36)
        self.breadcrumb_layout = QHBoxLayout(breadcrumb_frame)
        self.breadcrumb_layout.setContentsMargins(15, 0, 15, 0)
        self.breadcrumb_layout.setSpacing(4)
        main_layout.addWidget(breadcrumb_frame)

        self.view = QTreeView()
        self.model = FileModel()
        self.view.setModel(self.model)
        self.view.setAlternatingRowColors(False)
        self.view.setSelectionBehavior(QTreeView.SelectRows)
        self.view.setSelectionMode(QTreeView.ExtendedSelection)
        self.view.setEditTriggers(QTreeView.NoEditTriggers)
        self.view.setIndentation(0)
        self.view.setRootIsDecorated(False)
        self.view.setSortingEnabled(True)
        self.view.sortByColumn(0, Qt.AscendingOrder)
        self.view.doubleClicked.connect(self.on_item_double_click)
        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        self.view.verticalScrollBar().valueChanged.connect(self._on_scroll)

        header = self.view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.Fixed)
        self.view.setColumnWidth(1, 100)
        self.view.setColumnWidth(2, 160)
        self.view.setColumnWidth(3, 50)

        main_layout.addWidget(self.view)

        self.model.request_next_page.connect(self._load_next_page)

        self.btn_connect.clicked.connect(self.show_login)
        self.btn_refresh.clicked.connect(lambda: self.refresh_list(use_cache=False))
        self.btn_share.clicked.connect(self.on_share_clicked)
        self.btn_download.clicked.connect(self.show_download)
        self.btn_upload.clicked.connect(self.show_upload)
        self.btn_back.clicked.connect(self.go_back)

        self.update_breadcrumb()

    def setup_shortcuts(self):
        QShortcut(QKeySequence("F5"), self, lambda: self.refresh_list(use_cache=False))
        QShortcut(QKeySequence("Del"), self, self.delete_selected_items)
        QShortcut(QKeySequence.StandardKey.SelectAll, self, self.select_all)
        QShortcut(QKeySequence("Escape"), self, self.clear_selection)

    def apply_styles(self):
        self.setStyleSheet(get_dark_theme())

    def _prefix_for_api(self) -> str:
        prefix = self.current_path[1:] if self.current_path.startswith('/') else self.current_path
        if prefix.startswith('/'):
            prefix = prefix[1:]
        return prefix

    def update_breadcrumb(self):
        while self.breadcrumb_layout.count():
            item = self.breadcrumb_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        parts = [p for p in self.current_path.split('/') if p]
        root_btn = QPushButton("🏠 root")
        root_btn.setObjectName("BreadcrumbButton")
        root_btn.setCursor(Qt.PointingHandCursor)
        root_btn.clicked.connect(lambda: self.navigate_to('/'))
        self.breadcrumb_layout.addWidget(root_btn)

        path_so_far = ''
        for part in parts:
            sep = QLabel("/")
            sep.setObjectName("BreadcrumbSep")
            self.breadcrumb_layout.addWidget(sep)
            path_so_far += '/' + part
            target = path_so_far + '/'
            btn = QPushButton(part)
            btn.setObjectName("BreadcrumbButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, p=target: self.navigate_to(p))
            self.breadcrumb_layout.addWidget(btn)

        self.breadcrumb_layout.addStretch()

    def navigate_to(self, path: str):
        if not path.endswith('/') and path != '/':
            path += '/'
        self.current_path = path if path.startswith('/') else '/' + path
        if self.current_path != '/' and not self.current_path.endswith('/'):
            self.current_path += '/'
        self.update_breadcrumb()
        self.refresh_list()

    def auto_connect(self):
        creds = self.credentials_manager.get_credentials()
        if creds:
            self.on_connected(creds)

    def on_connected(self, creds):
        try:
            self.spaces_client = SpacesClient(**creds)
            self.share_service = ShareService(self.spaces_client)
            self.upload_service = UploadService(self.spaces_client)
            self.credentials_manager.update_credentials(creds)
            self.lbl_status.setText(f"Bağlı: {creds.get('bucket', 'Spaces')}")
            self.btn_upload.setEnabled(True)
            self.refresh_list()
        except Exception as e:
            self.lbl_status.setText(f"Hata: {str(e)}")

    def _stop_worker(self, worker, timeout_ms=WORKER_STOP_TIMEOUT_MS):
        """Worker'ı güvenle durdur; timeout'ta referansı canlı tut (orphan etme)."""
        if not worker:
            return True
        if worker.isRunning():
            worker.requestInterruption()
            if not worker.wait(timeout_ms):
                logger.warning(
                    "Worker %s %sms içinde durmadı; referans korunuyor",
                    worker.__class__.__name__,
                    timeout_ms,
                )
                if worker not in self._linger_workers:
                    self._linger_workers.append(worker)
                worker.finished.connect(self._on_linger_worker_finished)
                return False
        if worker in self._linger_workers:
            self._linger_workers.remove(worker)
        return True

    def _on_linger_worker_finished(self):
        sender = self.sender()
        if sender in self._linger_workers:
            self._linger_workers.remove(sender)
        sender.deleteLater()

    def _collect_all_workers(self):
        workers = []
        for w in (
            self._upload_worker,
            self._download_worker,
            self._list_worker,
            self._attr_worker,
            self._action_worker,
        ):
            if w:
                workers.append(w)
        workers.extend(self._linger_workers)
        seen = set()
        unique = []
        for w in workers:
            wid = id(w)
            if wid not in seen:
                seen.add(wid)
                unique.append(w)
        return unique

    def _force_shutdown_all_workers(self):
        """Uygulama kapanırken tüm arka plan işlerini zorla durdur."""
        self._halt_all_upload_workers(recreate_service=False)
        self._halt_all_download_workers()

        for worker in self._collect_all_workers():
            if worker.isRunning():
                worker.requestInterruption()

        for worker in self._collect_all_workers():
            if not worker.isRunning():
                continue
            if not worker.wait(SHUTDOWN_WORKER_WAIT_MS):
                logger.warning(
                    "Uygulama kapanıyor, worker zorla sonlandırılıyor: %s",
                    worker.__class__.__name__,
                )
                worker.terminate()
                worker.wait(1000)

        self._upload_worker = None
        self._download_worker = None
        self._list_worker = None
        self._attr_worker = None
        self._action_worker = None
        self._linger_workers.clear()

    def _disconnect_upload_worker_from_dialog(self):
        worker = self._upload_worker
        dlg = getattr(self, 'upload_dlg', None)
        if not worker or not dlg:
            return
        for signal in (
            worker.file_progress_detailed,
            worker.file_progress,
            worker.file_completed,
            worker.file_error,
        ):
            try:
                signal.disconnect(dlg)
            except (TypeError, RuntimeError):
                pass
        try:
            worker.finished.disconnect(self._on_upload_worker_finished)
        except (TypeError, RuntimeError):
            pass

    def refresh_list(self, use_cache: bool = True):
        if not self.spaces_client:
            return

        self._stop_worker(self._list_worker)
        self._stop_worker(self._attr_worker)

        prefix = self._prefix_for_api()
        self._list_prefix = prefix
        self._continuation_token = None
        self._loading_folders = []
        self._loading_files = []

        if use_cache:
            cached = self.listing_cache.get(prefix)
            if cached:
                folders, files = cached
                self.model.set_items(folders, files)
                self.model.set_has_more(False)
                self.lbl_status.setText(f"Hazır - {self.current_path} ({len(folders) + len(files)} öğe)")
                self.btn_back.setEnabled(self.current_path != '/')
                self._schedule_acl_load()
                return

        self.model.begin_loading()
        self._start_list_worker(prefix, None)
        self.lbl_status.setText("Listeleniyor...")
        self.btn_back.setEnabled(self.current_path != '/')

    def _start_list_worker(self, prefix, token):
        if not self._stop_worker(self._list_worker):
            logger.warning("Önceki liste worker durmadı, yeni sayfa başlatılmadı")
            return
        self._list_worker = SpacesWorker(self.spaces_client, prefix, token)
        self._list_worker.setParent(self)
        self._list_worker.page_loaded.connect(self.on_page_loaded)
        self._list_worker.finished_loading.connect(self.on_list_finished)
        self._list_worker.error.connect(self.on_list_error)
        self._list_worker.start()

    def _load_next_page(self):
        if self._continuation_token and self._list_worker and not self._list_worker.isRunning():
            self._start_list_worker(self._list_prefix, self._continuation_token)

    @Slot(dict)
    def on_page_loaded(self, page):
        first = self._continuation_token is None and not self._loading_folders and not self._loading_files
        self._loading_folders.extend(page.get('folders', []))
        self._loading_files.extend(page.get('files', []))
        self.model.append_items(page.get('folders', []), page.get('files', []), first_page=first)
        self._continuation_token = page.get('next_continuation_token') if page.get('is_truncated') else None
        self.model.set_has_more(bool(page.get('is_truncated')))
        total = len(self._loading_folders) + len(self._loading_files)
        self.lbl_status.setText(f"Yükleniyor... ({total} öğe)")

    @Slot(dict)
    def on_list_finished(self, _summary):
        total = len(self._loading_folders) + len(self._loading_files)
        self.listing_cache.put(self._list_prefix, self._loading_folders, self._loading_files)
        self.lbl_status.setText(f"Hazır - {self.current_path} ({total} öğe)")
        self._schedule_acl_load()

    @Slot(str)
    def on_list_error(self, err_msg):
        QMessageBox.critical(self, "Hata", f"Liste yüklenemedi: {err_msg}")
        self.lbl_status.setText("Hata oluştu")

    def _on_scroll(self, _value):
        self._schedule_acl_load()

    def _schedule_acl_load(self):
        if not self.spaces_client:
            return
        self._stop_worker(self._attr_worker)
        rows = sorted({idx.row() for idx in self.view.selectionModel().selectedRows()})
        if not rows:
            top = self.view.indexAt(self.view.viewport().rect().topLeft())
            bottom = self.view.indexAt(self.view.viewport().rect().bottomLeft())
            if top.isValid() and bottom.isValid():
                rows = list(range(top.row(), bottom.row() + 1))
        paths = self.model.file_paths_needing_acl(rows)
        if not paths:
            return
        self.model.mark_acl_pending(paths)
        self._attr_worker = AttributeWorker(self.spaces_client, paths)
        self._attr_worker.setParent(self)
        self._attr_worker.acl_loaded.connect(self.model.set_acl)
        self._attr_worker.start()

    def go_back(self):
        if self.current_path == '/':
            return
        parts = [p for p in self.current_path.split('/') if p]
        new_path = '/' + '/'.join(parts[:-1]) if len(parts) > 1 else '/'
        if new_path != '/' and not new_path.endswith('/'):
            new_path += '/'
        self.navigate_to(new_path)

    def on_item_double_click(self, index):
        item = self.model.get_item(index)
        if item and item['type'] == 'folder':
            self.navigate_to(item['path'])

    def on_selection_changed(self):
        indexes = self.view.selectionModel().selectedRows()
        self.btn_share.setEnabled(len(indexes) == 1 and self._single_is_file(indexes))
        self.btn_download.setEnabled(len(indexes) >= 1)
        self._schedule_acl_load()

    def _single_is_file(self, indexes):
        if len(indexes) != 1:
            return False
        item = self.model.get_item(indexes[0])
        return item and item.get('type') == 'file'

    def get_selected_items(self):
        items = []
        for idx in self.view.selectionModel().selectedRows():
            if idx.isValid():
                item = self.model.get_item(idx)
                if item:
                    items.append(item)
        return items

    def select_all(self):
        sm = self.view.selectionModel()
        for row in range(self.model.rowCount()):
            sm.select(self.model.index(row, 0), QItemSelectionModel.Select | QItemSelectionModel.Rows)

    def clear_selection(self):
        self.view.selectionModel().clearSelection()

    def _start_action_worker(self, func, on_success, on_error=None, *args, **kwargs):
        """ActionWorker'ı güvenli başlat; önceki worker'ı orphan etme."""
        if not self._stop_worker(self._action_worker):
            return False
        worker = ActionWorker(self, func, *args, **kwargs)
        worker.action_finished.connect(on_success)
        worker.error.connect(on_error or self.on_action_error)
        self._action_worker = worker
        worker.start()
        return True

    def delete_selected_items(self):
        if self._batch_delete_active:
            QMessageBox.warning(self, "Uyarı", "Silme işlemi devam ediyor.")
            return
        items = self.get_selected_items()
        if not items:
            QMessageBox.information(self, "Bilgi", "Silinecek öğe seçilmedi.")
            return
        n = len(items)
        names = ", ".join(i["name"] for i in items[:5])
        if n > 5:
            names += f" ... (+{n - 5} öğe)"
        if QMessageBox.question(
            self, "Onay", f"{n} öğe kalıcı olarak silinecek.\n\n{names}\n\nEmin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self._run_batch_delete(items)

    def _run_batch_delete(self, items):
        if self._action_worker and self._action_worker.isRunning():
            QMessageBox.warning(self, "Uyarı", "Başka bir işlem devam ediyor.")
            return
        self._batch_delete_active = True
        self.view.setEnabled(False)
        self._batch_delete_items = list(items)
        self._batch_delete_index = 0
        self._batch_delete_next()

    def _batch_delete_finished(self):
        self._batch_delete_active = False
        self.view.setEnabled(True)
        self.clear_selection()
        self.listing_cache.invalidate(self._prefix_for_api())
        self.refresh_list(use_cache=False)
        self.lbl_status.setText("Silme tamamlandı")

    def _batch_delete_next(self):
        if self._batch_delete_index >= len(self._batch_delete_items):
            self._batch_delete_finished()
            return
        item = self._batch_delete_items[self._batch_delete_index]
        func = (
            self.spaces_client.delete_folder_recursive
            if item.get("type") == "folder"
            else self.spaces_client.delete_object
        )
        self.lbl_status.setText(
            f"Siliniyor ({self._batch_delete_index + 1}/{len(self._batch_delete_items)}): {item['name']}..."
        )
        if not self._start_action_worker(
            func,
            self._on_batch_delete_step,
            self._on_batch_delete_error,
            item["path"],
        ):
            QTimer.singleShot(300, self._batch_delete_next)

    def _on_batch_delete_step(self):
        self._batch_delete_index += 1
        self._batch_delete_next()

    def _on_batch_delete_error(self, msg):
        QMessageBox.critical(self, "Hata", f"Silme hatası: {msg}")
        self._batch_delete_index = len(self._batch_delete_items)
        self._on_batch_delete_step()

    def show_download(self):
        items = self.get_selected_items()
        if not items:
            QMessageBox.information(self, "Bilgi", "İndirilecek öğe seçilmedi.")
            return
        if not self.spaces_client:
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bağlanın.")
            return
        if getattr(self, 'download_dlg', None) and self.download_dlg.isVisible():
            self.download_dlg.raise_()
            self.download_dlg.activateWindow()
            return
        self.download_dlg = DownloadDialog(self, items=items, current_path=self.current_path)
        self.download_dlg.download_started.connect(self.handle_download)
        self.download_dlg.cancel_requested.connect(self.cancel_download)
        self.download_dlg.destroyed.connect(self._disconnect_download_worker_from_dialog)
        self.download_dlg.show()

    def _halt_all_download_workers(self):
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.requestInterruption()
        for worker in list(self._linger_workers):
            if worker.isRunning():
                worker.requestInterruption()
        if self.spaces_client:
            self.spaces_client.cancel_active_transfers()
        self._download_cancelled.set()

    def cancel_download(self):
        self._halt_all_download_workers()
        worker = self._download_worker
        if worker and worker.isRunning():
            self._disconnect_download_worker_from_dialog()
            self._download_worker = None
            if worker not in self._linger_workers:
                self._linger_workers.append(worker)
                worker.finished.connect(self._on_linger_worker_finished)
        self.on_download_cancelled()

    @Slot()
    def _on_download_worker_finished(self):
        worker = self._download_worker
        if not worker or self.sender() is not worker:
            return
        self._download_worker = None
        if worker.isInterruptionRequested() or self._download_cancelled.is_set():
            return
        self.on_download_all_finished()

    @Slot()
    def on_download_cancelled(self):
        if self.download_dlg:
            self.download_dlg.on_download_cancelled()
        self.lbl_status.setText("İndirme iptal edildi")

    def handle_download(self, items, local_dir):
        if not self.spaces_client:
            if self.download_dlg:
                self.download_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bağlanın.")
            return

        if not self._stop_worker(self._download_worker):
            if self.download_dlg:
                self.download_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "Önceki indirme hâlâ sonlandırılıyor, lütfen bekleyin.")
            return

        linger_running = any(
            isinstance(w, ParallelDownloadWorker) and w.isRunning()
            for w in self._linger_workers
        )
        if linger_running:
            self._halt_all_download_workers()
        self._download_cancelled.clear()

        try:
            tasks = build_download_tasks(self.spaces_client, items, local_dir)
        except Exception as e:
            logger.error(f"İndirme görevleri oluşturulamadı: {e}", exc_info=True)
            if self.download_dlg:
                self.download_dlg._enter_select_phase(fresh=False)
            QMessageBox.critical(self, "Hata", f"İndirme hazırlanamadı:\n{e}")
            return

        if not tasks:
            if self.download_dlg:
                self.download_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "İndirilecek dosya bulunamadı.")
            return

        if self.download_dlg:
            self.download_dlg.setup_progress_widgets(tasks)
            self.download_dlg._enter_download_phase()

        self._download_worker = ParallelDownloadWorker(
            self, self.spaces_client, tasks, self._download_cancelled.is_set,
        )
        if self.download_dlg:
            self._download_worker.file_progress_detailed.connect(
                self.download_dlg.update_progress_detailed,
            )
            self._download_worker.file_completed.connect(self.download_dlg.set_completed)
            self._download_worker.file_error.connect(self.download_dlg.set_error)
        self._download_worker.finished.connect(self._on_download_worker_finished)
        self._download_worker.start()
        self.lbl_status.setText(f"İndiriliyor: {len(tasks)} dosya...")

    @Slot()
    def on_download_all_finished(self):
        if self.download_dlg:
            self.download_dlg.on_download_finished()
        self.lbl_status.setText("İndirme tamamlandı")

    def _disconnect_download_worker_from_dialog(self):
        worker = self._download_worker
        dlg = getattr(self, 'download_dlg', None)
        if not worker or not dlg:
            return
        for signal in (
            worker.file_progress_detailed,
            worker.file_completed,
            worker.file_error,
        ):
            try:
                signal.disconnect(dlg)
            except (TypeError, RuntimeError):
                pass
        try:
            worker.finished.disconnect(self._on_download_worker_finished)
        except (TypeError, RuntimeError):
            pass

    def show_context_menu(self, pos):
        from functools import partial
        index = self.view.indexAt(pos)
        menu = QMenu(self)
        selected = self.get_selected_items()

        menu.addAction("Tümünü Seç", self.select_all)
        menu.addAction("Seçimi Bırak", self.clear_selection)
        menu.addSeparator()
        if selected:
            menu.addAction(f"Seçilenleri Sil ({len(selected)} öğe)", self.delete_selected_items)
            menu.addAction("Seçilenleri İndir" if len(selected) > 1 else "İndir", self.show_download)
            menu.addSeparator()
        if index.isValid():
            item = self.model.get_item(index)
            if item and item['type'] == 'file':
                menu.addAction("Paylaş (3 Gün)", partial(self.share_item, item, 3))
                menu.addAction("Paylaş (7 Gün)", partial(self.share_item, item, 7))
            if not selected or len(selected) == 1:
                menu.addAction("Sil", partial(self.delete_item, item))
        else:
            menu.addAction("Yeni Klasör", self.create_folder)
            menu.addAction("Dosya Yükle", self.show_upload)
        menu.exec(self.view.mapToGlobal(pos))

    def share_item(self, item, days):
        try:
            url, expiration = self.share_service.share_to_clipboard(item['path'], days)
            QMessageBox.information(
                self, "Başarılı",
                f"Link panoya kopyalandı!\nSon gün: {expiration.strftime('%Y-%m-%d')}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))

    def on_share_clicked(self):
        indexes = self.view.selectionModel().selectedRows()
        if not indexes:
            return
        item = self.model.get_item(indexes[0])
        if not item or item['type'] != 'file':
            return
        dlg = ShareDialog(self, item['name'])
        if dlg.exec():
            self.share_item(item, dlg.days)

    def delete_item(self, item):
        if self._batch_delete_active:
            QMessageBox.warning(self, "Uyarı", "Toplu silme devam ediyor.")
            return
        if QMessageBox.question(
            self, "Onay", f"'{item['name']}' kalıcı olarak silinecek. Emin misiniz?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        func = (
            self.spaces_client.delete_folder_recursive
            if item['type'] == 'folder'
            else self.spaces_client.delete_object
        )
        self.lbl_status.setText(f"Siliniyor: {item['name']}...")
        self._start_action_worker(func, self._on_delete_finished, self.on_action_error, item['path'])

    def _on_delete_finished(self):
        self.listing_cache.invalidate(self._prefix_for_api())
        self.refresh_list(use_cache=False)

    def create_folder(self):
        if self._batch_delete_active:
            QMessageBox.warning(self, "Uyarı", "Silme işlemi devam ediyor.")
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Yeni Klasör", "Klasör ismi:")
        if not ok or not name:
            return
        path = self._prefix_for_api() + name + '/'
        self._start_action_worker(
            self.spaces_client.create_folder,
            self._on_folder_created,
            self.on_action_error,
            path,
        )

    def _on_folder_created(self):
        self.listing_cache.invalidate(self._prefix_for_api())
        self.refresh_list(use_cache=False)

    @Slot(str)
    def on_action_error(self, msg):
        QMessageBox.critical(self, "Hata", f"İşlem başarısız: {msg}")

    def show_login(self):
        dlg = LoginDialog(self, on_connect=self.on_connected)
        dlg.exec()

    def show_upload(self):
        if getattr(self, 'upload_dlg', None) and self.upload_dlg.isVisible():
            self.upload_dlg.raise_()
            self.upload_dlg.activateWindow()
            return
        self.upload_dlg = UploadDialog(self, current_path=self.current_path)
        self.upload_dlg.upload_started.connect(self.handle_upload)
        self.upload_dlg.cancel_requested.connect(self.cancel_upload)
        self.upload_dlg.destroyed.connect(self._disconnect_upload_worker_from_dialog)
        self.upload_dlg.show()

    def _halt_all_upload_workers(self, *, recreate_service: bool = False):
        """Aktif ve arka plandaki tüm yükleme worker'larını durdur."""
        if self._upload_worker and self._upload_worker.isRunning():
            self._upload_worker.requestInterruption()
        for worker in list(self._linger_workers):
            if worker.isRunning():
                worker.requestInterruption()
        if self.upload_service:
            self.upload_service.shutdown()
        if self.spaces_client:
            self.spaces_client.cancel_active_transfers()
        if recreate_service and self.spaces_client:
            self.upload_service = UploadService(self.spaces_client)

    def cancel_upload(self):
        self._halt_all_upload_workers(recreate_service=True)

        worker = self._upload_worker
        if worker and worker.isRunning():
            self._disconnect_upload_worker_from_dialog()
            self._upload_worker = None
            if worker not in self._linger_workers:
                self._linger_workers.append(worker)
                worker.finished.connect(self._on_linger_worker_finished)

        self.on_upload_cancelled()

    @Slot()
    def _on_upload_worker_finished(self):
        worker = self._upload_worker
        if not worker or self.sender() is not worker:
            return
        self._upload_worker = None
        if worker.isInterruptionRequested():
            return
        self.on_upload_all_finished()

    @Slot()
    def on_upload_cancelled(self):
        if self.upload_dlg:
            self.upload_dlg.on_upload_cancelled()
        self.lbl_status.setText("Yükleme iptal edildi")

    def handle_upload(self, paths, acl):
        if not self.upload_service or not self.spaces_client:
            if self.upload_dlg:
                self.upload_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "Lütfen önce bağlanın.")
            return

        if not self._stop_worker(self._upload_worker):
            if self.upload_dlg:
                self.upload_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "Önceki yükleme hâlâ sonlandırılıyor, lütfen bekleyin.")
            return

        linger_running = any(
            isinstance(w, ParallelUploadWorker) and w.isRunning()
            for w in self._linger_workers
        )
        if linger_running:
            self._halt_all_upload_workers(recreate_service=True)
        elif self.upload_service and self.upload_service._is_cancelled():
            self.upload_service = UploadService(self.spaces_client)

        files_to_upload = []
        base_prefix = self._prefix_for_api()
        selected_folder = getattr(self.upload_dlg, 'selected_folder', None)

        for p in paths:
            if not os.path.exists(p):
                continue
            normalized_path = os.path.normpath(p)
            if selected_folder:
                try:
                    relative_path = os.path.relpath(normalized_path, selected_folder)
                    remote_key = join_path(base_prefix, os.path.basename(selected_folder), relative_path)
                except ValueError:
                    remote_key = join_path(base_prefix, os.path.basename(selected_folder), os.path.basename(normalized_path))
            else:
                remote_key = join_path(base_prefix, os.path.basename(normalized_path))
            remote_key = remote_key.lstrip('/').replace('\\', '/')
            files_to_upload.append({'local_path': normalized_path, 'remote_key': remote_key})

        if not files_to_upload:
            if self.upload_dlg:
                self.upload_dlg._enter_select_phase(fresh=False)
            QMessageBox.warning(self, "Uyarı", "Yüklenecek geçerli dosya bulunamadı.")
            return

        self._upload_worker = ParallelUploadWorker(
            self, self.upload_service, files_to_upload, acl,
        )
        if self.upload_dlg:
            self._upload_worker.file_progress_detailed.connect(
                self.upload_dlg.update_progress_detailed,
            )
            self._upload_worker.file_completed.connect(self.upload_dlg.set_completed)
            self._upload_worker.file_error.connect(self.upload_dlg.set_error)
        self._upload_worker.finished.connect(self._on_upload_worker_finished)
        self._upload_worker.start()

    @Slot()
    def on_upload_all_finished(self):
        if self.upload_dlg:
            self.upload_dlg.on_upload_finished()
        self.listing_cache.invalidate(self._prefix_for_api())
        self.lbl_status.setText("Yükleme tamamlandı")
        self.refresh_list(use_cache=False)

    def closeEvent(self, event):
        if hasattr(self, 'upload_dlg') and self.upload_dlg:
            self.upload_dlg._uploading = False
            self.upload_dlg.close()
        if hasattr(self, 'download_dlg') and self.download_dlg:
            self.download_dlg._downloading = False
            self.download_dlg.close()
        self._force_shutdown_all_workers()
        event.accept()
