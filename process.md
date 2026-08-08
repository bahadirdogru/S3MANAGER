> **Doc Map** — Proje dökümantasyon rehberi
>
> | Dosya | Ne için okunur |
> |-------|----------------|
> | [README.md](README.md) | Kurulum, kullanım, proje tanıtımı (GitHub/GitLab anasayfa) |
> | [UI.md](UI.md) | Renk, font, widget, QSS tasarım standartları |
> | [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, veri akışı, threading (insan okuması) |
> | [LLM.md](LLM.md) | Güncel kod yapısı, dosya haritası, geliştirme kısıtları (LLM) |
> | [PROCESS.md](PROCESS.md) | Kronolojik değişiklik kayıtları (LLM changelog) |
>
> **Bu dosya:** Kronolojik changelog — ne yapıldı, nasıl yapıldı, neden.

# S3MANAGER — Changelog

Ters kronolojik sıra. Gelecek işler burada tutulmaz.

---

## 2026-08-08 — CI PyInstaller ve NSIS düzeltmesi

- **Ne:** Release/CI build PyInstaller ve Windows NSIS adimlari basarisiz oluyordu
- **Neden:** `collect_all("PySide6")` QML/Qt3D modullerini dahil edip eksik plugin DLL hatasi veriyordu; NSIS SourceForge indirmesi CI'da calismiyordu
- **Nasil:**
  - `s3manager.spec`: `collect_all` kaldirildi, gereksiz Qt modulleri exclude, UPX kapali
  - `release.yml`: NSIS kurulumu `choco install nsis` ile
  - `package-linux.sh`: AppImage CI'da `--appimage-extract-and-run` (FUSE gerektirmez)
  - `release.yml`: Linux job'a `libfuse2` + `wget` kurulumu
- **Dosyalar:** `s3manager.spec`, `.github/workflows/release.yml`, `src/version.py`

---

## 2026-08-08 — v0.0.2 release

- **Ne:** Breadcrumb cache düzeltmesi, `start.sh` geliştirme ortamı scripti
- **Nasıl:** `v0.0.2` tag → GitHub Actions release workflow
- **Dosyalar:** `src/ui/qt/main_window.py`, `src/ui/qt/models.py`, `start.sh`, `src/version.py`

---

## 2026-08-08 — Breadcrumb cache race condition düzeltmesi

- **Ne:** Breadcrumb ile ileri/geri gezinirken klasör içeriği cache'ten yanlış veya karışık geliyordu
- **Neden:** Önceki `SpacesWorker` sinyalleri navigasyon sonrası bağlı kalıyordu; stale `on_page_loaded` / `on_list_finished` callback'leri modeli ve cache'i bozuyordu
- **Nasıl:**
  - `main_window.py`: `_detach_list_worker`, `_stop_list_worker`; stale callback guard; cache put için worker prefix'i
  - `models.py`: `set_items()` ACL cache temizliği
- **Dosyalar:** `src/ui/qt/main_window.py`, `src/ui/qt/models.py`

---

## 2026-08-08 — CI/CD, installer ve güncelleme kontrolü

- **Ne:** GitHub Actions CI/release; Windows NSIS, macOS DMG, Linux tar.gz+AppImage; GitHub Releases güncelleme bildirimi
- **Nasıl:**
  - `.github/workflows/ci.yml` — matrix build (win/linux/mac)
  - `.github/workflows/release.yml` — `v*.*.*` tag → 5 asset GitHub Release
  - `scripts/package-*.ps1/sh`, `scripts/installer/windows.nsi`
  - `src/services/update_service.py` — Releases API; MainWindow Yardım menüsü
  - `src/version.py` — surum + `GITHUB_REPO`
- **Dosyalar:** `.github/`, `scripts/`, `src/version.py`, `src/services/update_service.py`, `assets/`, `README.md`, `LLM.md`

---

## 2026-08-08 — S3MANAGER rebrand ve açık kaynak

- **Ne:** Proje adı pyDamlaSpace → S3MANAGER; GPL-3 lisans, README yenileme, config dizini `~/.s3manager/`
- **Nasıl:**
  - `s3manager.spec` — PyInstaller onedir spec yeniden adlandırıldı
  - `src/utils/paths.py` — `get_config_dir()` ile `~/.pydamlaspace/` → `~/.s3manager/` otomatik taşıma
  - `README.md` — GitHub vitrin tasarımı, yazar/lisans/LLM notları
  - `LICENSE` — telif bloğu eklendi (Bahadır Doğru, GPL-3)
- **Dosyalar:** `README.md`, `LICENSE`, `s3manager.spec`, `scripts/`, `src/`, `ARCHITECTURE.md`, `LLM.md`

---

## 2026-08-08 — Onedir (tek klasör) derleme geçişi

- **Ne:** PyInstaller onefile yerine onedir dağıtımı; exe + `_internal/` DLL'leri tek klasörde; zip arşivi
- **Nasıl:**
  - `pydamlaspace.spec` — `EXE(exclude_binaries=True)` + `COLLECT` onedir yapısı
  - `scripts/build.ps1`, `scripts/build.sh` — klasör doğrulama, `dist/pyDamlaSpace.zip` üretimi
  - `README.md`, `LLM.md` — dağıtım dokümantasyonu güncellendi
- **Dosyalar:** `pydamlaspace.spec`, `scripts/build.ps1`, `scripts/build.sh`, `README.md`, `LLM.md`

---

## 2026-08-07 — Tek dosya (onefile) cross-platform derleme

- **Ne:** PyInstaller onefile ile Windows/Linux/macOS dağıtım paketi; frozen runtime path düzeltmeleri
- **Nasıl:**
  - `src/utils/paths.py` — `is_frozen()`, `app_root()`, `user_data_dir()`, `log_file_path()`
  - `main.py` — `sys.path` yalnızca geliştirme modunda; frozen'da atlanır
  - `logging_config.py` — varsayılan log `~/.pydamlaspace/app.log`
  - `pydamlaspace.spec` — PySide6 `collect_all`, botocore hiddenimports, `console=False`, `onefile=True`
  - `requirements-dev.txt` — PyInstaller (build-only)
  - `scripts/build.ps1`, `scripts/build.sh` — yerel derleme script'leri
- **Dosyalar:** `paths.py`, `main.py`, `logging_config.py`, `pydamlaspace.spec`, `requirements-dev.txt`, `scripts/`, `README.md`, `LLM.md`

---

## 2026-08-07 — İndirme popup dialog

- **Ne:** Upload ile simetrik üç fazlı indirme dialogu (onay → indirme → özet)
- **Nasıl:**
  - `DownloadDialog`, `DownloadItemList` — hedef klasör seçimi, dosya bazlı progress, iptal, özet
  - `ParallelDownloadWorker` — max 3 paralel, progress throttle, `build_download_tasks()`
  - `spaces_client.download_file` → `should_cancel` + `UploadCancelled`
  - `show_download()` / `handle_download()` / `cancel_download()` — toolbar ve context menu
- **Dosyalar:** `src/ui/qt/dialogs.py`, `main_window.py`, `spaces_client.py`, `UI.md`

---

## 2026-08-07 — UI derinlik ve okunabilirlik

- **Ne:** Dialog/kart katmanları, kontrast artışı, progress metin okunabilirliği
- **Nasıl:**
  - Palet: `WA_BG_DIALOG`, `WA_BORDER_SUBTLE`, açık `WA_TEXT_MUTED`
  - `apply_dialog_elevation()` gölge; `UploadProgressCard`, `UploadScroll`, `ProgressMeta`
  - Dialog kenarlığı; ana pencere ile dialog renk ayrımı
- **Dosyalar:** `styles.py`, `dialogs.py`, `UI.md`

---

## 2026-08-07 — Upload dialog yeniden tasarımı

- **Ne:** İki/üç fazlı upload UI: sürükle-bırak, dosya listesi, genel progress, iptal, özet ekranı
- **Nasıl:**
  - `DropZoneFrame`, `UploadFileList`, `QStackedWidget` (seçim / yükleme / özet)
  - Genel byte-ağırlıklı progress; `cancel_requested` + `upload_cancelled` signal
  - `ParallelUploadWorker.upload_cancelled`; iptal sonrası `UploadService` yeniden oluşturma
- **Dosyalar:** `src/ui/qt/dialogs.py`, `main_window.py`, `styles.py`, `UI.md`

---

## 2026-08-07 — WhatsApp teması ve okunabilirlik

- **Ne:** macOS mavi palet → WhatsApp siyah-yeşil tema; okunmayan sütun başlıkları ve breadcrumb düzeltildi
- **Nasıl:**
  - `styles.py`: `WA_*` renk sabitleri, `get_dark_theme()` yeniden yazıldı
  - `main_window.py`: breadcrumb inline stiller kaldırıldı; `BreadcrumbButton` / `BreadcrumbFrame` object name
  - `dialogs.py`: inline renkler `WA_*` sabitlerine taşındı
- **Dosyalar:** `src/ui/qt/styles.py`, `main_window.py`, `dialogs.py`, `UI.md`, `README.md`, `ARCHITECTURE.md`

---

## 2026-08-07 — Plan uygulaması: lazy loading, dokümantasyon, kod temizliği

- **Ne:** Dokümantasyon politikası (5 md), sayfalı listeleme, ACL lazy load, paralel upload düzeltmesi, UX iyileştirmeleri
- **Nasıl:**
  - `list_objects_page()`, `FileModel.append_items()`, `ListingCache`, `AttributeWorker`
  - `ParallelUploadWorker` ThreadPoolExecutor ile gerçek paralel yükleme
  - Breadcrumb, sıralama, paylaş dialogu; `thread.terminate()` → `requestInterruption()`
  - Ölü kod/import temizliği; `validators` + `test_connection` LoginDialog'da
- **Dosyalar:** `src/services/`, `src/ui/qt/`, `README.md`, `LLM.md`, `ARCHITECTURE.md`, `UI.md`, `PROCESS.md`

---

## 2026-08-07 — Dokümantasyon politikası tanımı

- **Ne:** 5 dosyalı doc yapısı; Doc Map bloğu; PROCESS changelog formatı
- **Neden:** LLM/insan için net rol ayrımı, tekrarların önlenmesi

---

## Önceki sürüm — Özet kayıtlar

### PySide6 geçişi ve temel uygulama

- **Ne:** CustomTkinter → PySide6; Spaces entegrasyonu; config.ini kimlik yönetimi
- **Dosyalar:** `src/ui/qt/`, `src/services/spaces_client.py`, `src/config/`

### Loglama

- **Ne:** `logging_config.py`, RotatingFileHandler `app.log`
- **Dosyalar:** `src/utils/logging_config.py`

### Upload: multipart, progress, deadlock düzeltmesi

- **Ne:** 100MB+ multipart; progress UI; büyük dosyada UI donması
- **Nasıl:** `upload_service.py` — `progress.lock` içinde `get_progress()` kaldırıldı (reentrant olmayan lock deadlock)
- **Dosyalar:** `src/services/upload_service.py`, `src/ui/qt/dialogs.py`

### Yükleme listesi davranışı

- **Ne:** "Dosya Seç" listeyi değiştirir (extend değil); progress alanı temizlenir
- **Dosyalar:** `src/ui/qt/dialogs.py`

### Dosya indirme

- **Ne:** Tek/çoklu dosya ve klasör indirme; üç fazlı `DownloadDialog`; max 3 paralel indirme
- **Dosyalar:** `src/ui/qt/dialogs.py` (`DownloadDialog`), `main_window.py` (`ParallelDownloadWorker`), `spaces_client.download_file`

### Dosya gezgini ve yönetim

- **Ne:** QTreeView + FileModel; çift tık; geri; context menu; toplu silme; klasör oluşturma
- **Dosyalar:** `src/ui/qt/main_window.py`, `src/ui/qt/models.py`

### Paylaşım

- **Ne:** Presigned URL 3/7 gün; pyperclip
- **Dosyalar:** `src/services/share_service.py`

### UI / stil

- **Ne:** WhatsApp-inspired dark QSS; LoginDialog, UploadDialog, UploadProgressBar
- **Dosyalar:** `src/ui/qt/styles.py`, `src/ui/qt/dialogs.py`
