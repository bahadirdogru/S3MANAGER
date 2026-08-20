> **Doc Map** — Proje dökümantasyon rehberi
>
> | Dosya | Ne için okunur |
> |-------|----------------|
> | [README.md](README.md) | Kurulum, kullanım, proje tanıtımı (GitHub/GitLab anasayfa) |
> | [docs/](docs/) | Tanıtım web sitesi ([s3manager.bahadirdogru.com](https://s3manager.bahadirdogru.com/)) |
> | [UI.md](UI.md) | Renk, font, widget, QSS tasarım standartları |
> | [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, veri akışı, threading (insan okuması) |
> | [LLM.md](LLM.md) | Güncel kod yapısı, dosya haritası, geliştirme kısıtları (LLM) |
> | [PROCESS.md](PROCESS.md) | Kronolojik değişiklik kayıtları (changelog) |
>
> **Bu dosya:** Kronolojik changelog — ne yapıldı, nasıl yapıldı, neden.

# S3MANAGER — Changelog

Ters kronolojik sıra. Gelecek işler burada tutulmaz.

---

## 2026-08-19 — v0.0.9: Intel macOS PySide2/PySide6 çakışması düzeltmesi

- **Sorun:** Intel `*-macos-x86_64.dmg` açılışta `RuntimeError: Cannot execute run-time hook for 'PySide6' because run-time hook for 'PySide2' has been run before`
- **Kök neden:** `scripts/build.sh` legacy build'de `requirements-dev.txt` kuruyordu; bu dosya `-r requirements.txt` ile gerçek PySide6 wheel'ini venv'e ekliyordu
- **Çözüm:** Legacy build yalnızca `requirements-macos-x86_64.txt` + `pyinstaller`; `scripts/verify-macos-x86_64-bundle.sh` ile bundle doğrulaması
- **Dosyalar:** `scripts/build.sh`, `scripts/verify-macos-x86_64-bundle.sh`, `.github/workflows/release.yml`, `build/macos_x86_64/README.md`

---

## 2026-08-18 — Intel macOS 10.13 uyumluluk düzeltmesi

- **Sorun:** `setup-python` / Homebrew `libintl.8.dylib` macOS 10.13'te `load command 0x80000034` (`LC_DYLD_CHAINED_FIXUPS`) hatası veriyordu
- **Çözüm:** x86_64 release job'da **python.org 3.10.11** (`scripts/setup-macos-legacy-python.sh`); `libintl` 10.13 hedefli derlenir (`build-macos-legacy-libintl.sh` + `fix-macos-legacy-dylibs.sh`); build sonrası `verify-macos-legacy-binary.sh`
- **Dosyalar:** `scripts/setup-macos-legacy-python.sh`, `scripts/build-macos-legacy-libintl.sh`, `scripts/fix-macos-legacy-dylibs.sh`, `scripts/verify-macos-legacy-binary.sh`, `scripts/build.sh`, `.github/workflows/release.yml`

---

## 2026-08-18 — macOS çift DMG (arm64 + Intel x86_64)

- **Ne:** Apple Silicon (`macos-arm64.dmg`, min macOS 13) ve Intel Mac (`macos-x86_64.dmg`, min macOS 10.13) için ayrı release hattı
- **Nasıl:** `release.yml` → `build-macos-arm64` (PySide6) + `build-macos-x86_64` (`macos-15-intel`, PySide2 + `build/macos_x86_64/PySide6` shim)
- **Geliştirme:** Günlük dev süreci değişmedi — `src/` PySide6, `ci.yml` aynı; PySide2 yalnızca Intel release build'de
- **Binary'ler:** `macos-arm64.dmg` + `macos-x86_64.dmg` (Windows/Linux aynı)
- **Dosyalar:** `build/macos_x86_64/`, `s3manager-macos-x86_64.spec`, `requirements-macos-x86_64.txt`, `scripts/package-macos.sh`, `.github/workflows/release.yml`

---

## 2026-08-16 — Dökümantasyon senkronizasyonu

- **Ne:** README, LLM, ARCHITECTURE, UI güncellendi — v0.0.8, tanıtım sitesi, Ayarlar/Bakım, nesne özellikleri, test.sh (93 test); CHANGELOG.md kaldırıldı (changelog yalnızca PROCESS.md)

---

## 2026-08-16 — Tanıtım sitesi özel domain

- **URL:** https://s3manager.bahadirdogru.com/ yayında
- **Dosya:** `docs/CNAME` — GitHub Pages özel domain kaydı

---

## 2026-08-16 — GitHub Pages tanıtım sitesi

- **Ne:** `docs/` altında statik tanıtım sayfası — hero, özellikler, ekran görüntüleri, indirme tablosu
- **URL:** https://s3manager.bahadirdogru.com/ (GitHub Pages, özel domain)
- **Dosyalar:** `docs/index.html`, `docs/css/style.css`, `docs/js/main.js`, `docs/screenshots/`, `scripts/capture_screenshots.py`, `scripts/generate_og_image.py`

---

## 2026-08-16 — v0.0.8 yayınlandı

- **Ne:** Ayarlar merkezi, tema tutarlılığı, S3 API genişletmesi (nesne özellikleri, multipart bakım, batch silme)
- **Binary'ler:** Windows setup/portable, macOS arm64 dmg, Linux tar.gz + AppImage
- **Kaynak:** [v0.0.8 release](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.8), [PROCESS.md](PROCESS.md)

---

## 2026-08-16 — S3 API genişletmesi (metadata, multipart, batch delete)

- **Ne:** boto3 eksikleri — nesne özellikleri dialogu, yarım multipart Bakım sekmesi, toplu silme optimizasyonu
- **Servis:** `put_object_acl`, `update_object_metadata`, `delete_objects_batch`, `list_incomplete_multipart_uploads`, `abort_multipart_upload`
- **UI:** `object_properties_dialog.py`, `incomplete_uploads_panel.py`, Ayarlar Bakım sekmesi, önizleme Özellikler butonu
- **Roadmap:** README — CDN purge (DO API token) ve bucket yönetimi planlandı olarak dokümante
- **Test:** +4 moto integration test sınıfı (19 test `test_spaces_client.py`)

---

## 2026-08-16 — Light/Dark tema tutarlılığı

- **Ne:** Tüm uygulama içi Qt ekranlarında palet tutarlılığı; global QSS (viewport, read-only input, text edit fallback), dialog inline stiller → objectName + QSS
- **Tema geçişi:** `apply_app_theme` repolish + `update_dialog_elevation`; Ayarlar dialogu açıkken toolbar switch
- **FormFrame:** `bg_panel` kart stili; Ayarlar Bağlantı scroll viewport düzeltmesi
- **Dosyalar:** `styles.py`, `settings_dialog.py`, `dialogs.py`, `preview_panel.py`, `UI.md`

---

## 2026-08-16 — Ayarlar menüsü (tab'lı merkez)

- **Ne:** Toolbar'da tek **Ayarlar** butonu; `SettingsDialog` ile 5 sekme (Bağlantı, Yükleme Metadata, Görünüm, Günlük, Yardım)
- **Kaldırıldı:** Toolbar Yardım menüsü ve Metadata butonu
- **Yeni:** `settings_dialog.py`, `upload_metadata_panel.py`, `utils/log_viewer.py` (`read_log_tail`)
- **Tema:** Görünüm sekmesi ↔ toolbar `ThemeSwitch` çift yönlü senkron
- **Dosyalar:** `main_window.py`, `dialogs.py`, `styles.py`, `UI.md`, `LLM.md`

---

## 2026-08-16 — İki satır toolbar revizyonu

- **Ne:** `QMenuBar` ve ayrı `BreadcrumbFrame` kaldırıldı; tek `ToolbarFrame` iki satır
- **Satır 1:** Bağlan, Yükle, Yenile, Paylaş, İndir, Kopyala, Taşı, Yeniden Adlandır, Yardım (menü), Metadata, `ConnectionIndicator`, `ThemeSwitch`
- **Satır 2:** Breadcrumb, arama (min 180px stretch), Geri
- **Bağlantı:** Yeşil/kırmızı nokta + tooltip; tıklayınca Bağlan dialogu
- **Dosyalar:** `main_window.py`, `connection_indicator.py`, `styles.py`, `UI.md`

---

## 2026-08-11 — v0.0.7 yayınlandı

- **Ne:** Dosya yöneticisi tamamlama, önizleme paneli, pytest test altyapısı
- **İçerik:**
  - Kopyala / taşı / yeniden adlandır (toolbar, context menu, F2, Ctrl+C/X)
  - Toolbar arama (prefix filtre), sürükle-bırak yükleme, transfer geçmişi paneli
  - Split-view dosya önizleme (görsel/metin), Qt standart toolbar ikonları
  - pytest + moto test suite (89 test), CI test job
- **Binary'ler:** Windows setup/portable, macOS arm64 dmg, Linux tar.gz + AppImage
- **Kaynak:** [v0.0.7 release](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.7)

---

## 2026-08-11 — Otomatik test altyapısı (pytest)

- **Ne:** pytest tabanlı unit + servis testleri; CI entegrasyonu
- **Nasıl:**
  - `pyproject.toml` — pytest markers, coverage %60 eşiği
  - `tests/unit/` — helpers, validators, object_metadata, listing_cache, update_service, settings, share_service
  - `tests/services/test_spaces_client.py` — moto mock S3 (CRUD, copy/move/rename, ACL)
  - `tests/conftest.py` — `mock_config_dir`, `spaces_client` fixture'ları
  - `.github/workflows/ci.yml` — ayrı `test` job; `build` `needs: test`
  - `scripts/test.sh` — yerel test runner
- **Dosyalar:** `pyproject.toml`, `requirements-dev.txt`, `tests/`, `ci.yml`, `README.md`, `LLM.md`

---

## 2026-08-11 — v0.0.6 yayınlandı

- **Ne:** Koyu / açık tema desteği ile yeni sürüm
- **İçerik:** Toolbar ay/güneş `ThemeSwitch`; `ThemePalette` tabanlı QSS; tercih `~/.s3manager/config.ini` `[appearance]`
- **Binary'ler:** Windows setup/portable, macOS arm64 dmg, Linux tar.gz + AppImage
- **Kaynak:** [v0.0.6 release](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.6)

---

## 2026-08-11 — Koyu / Açık tema (ThemeSwitch)

- **Ne:** Toolbar'da ay/güneş simgeli tema switch; koyu (varsayılan) ve açık mod
- **Nası:**
  - `src/ui/qt/styles.py` — `ThemePalette`, `build_stylesheet()`, `apply_app_theme()`; QApplication seviyesinde QSS
  - `src/ui/qt/theme_switch.py` — `ThemeSwitch` pill toggle widget
  - `Settings.load/save_theme_mode()` — `[appearance] theme` config
  - `main_window.py` — toolbar entegrasyonu; dialog'lardan `setStyleSheet` kaldırıldı
- **Dosyalar:** `styles.py`, `theme_switch.py`, `settings.py`, `main_window.py`, `dialogs.py`, `config.example.ini`, `UI.md`

---

## 2026-08-11 — v0.0.5 yayınlandı

- **Ne:** Yükleme metadata özelliği ile yeni sürüm
- **İçerik:** Content-Type, Content-Disposition ve Cache-Control otomatik tespit; Ayarlar menüsünden özelleştirilebilir kurallar
- **Binary'ler:** Windows setup/portable, macOS arm64 dmg, Linux tar.gz + AppImage
- **Kaynak:** [v0.0.5 release](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.5)

---

## 2026-08-08 — Yükleme metadata otomatik tespit

- **Ne:** Yüklemede Content-Type, Content-Disposition ve isteğe bağlı Cache-Control otomatik atanıyor
- **Nası:**
  - `src/utils/object_metadata.py` — uzantı/MIME tespiti, `build_upload_extra_args`
  - `Settings.load/save_upload_metadata_settings()` — `[upload_metadata]` config bölümü
  - `UploadMetadataSettingsDialog` — Ayarlar menüsü ve Upload dialog entegrasyonu
  - `UploadService` → `SpacesClient.upload_file(extra_args=...)`
- **Dosyalar:** `object_metadata.py`, `settings.py`, `spaces_client.py`, `upload_service.py`, `dialogs.py`, `main_window.py`, `config.example.ini`

---

## 2026-08-08 — v0.0.4 yayınlandı

- **Ne:** İlk başarılı çoklu platform GitHub Release
- **İçerik:** Breadcrumb cache düzeltmesi, `start.sh`, CI/release pipeline düzeltmeleri
- **Binary'ler:** Windows setup/portable, macOS arm64 dmg, Linux tar.gz + AppImage
- **Kaynak:** [v0.0.4 release](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.4)

---

## 2026-08-08 — v0.0.4 Windows NSIS PATH düzeltmesi

- **Ne:** Release Windows job'unda `makensis` bulunamadi hatasi
- **Nasil:** `package-windows.ps1` makensis yolunu otomatik bulur; `release.yml` choco sonrasi NSIS dizinini PATH'e ekler
- **Dosyalar:** `scripts/package-windows.ps1`, `.github/workflows/release.yml`, `src/version.py`

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
