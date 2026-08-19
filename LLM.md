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
> **Bu dosya:** LLM için token-optimize proje yapısı ve geliştirme kısıtları.

# S3MANAGER — LLM Rehberi

DigitalOcean Spaces masaüstü dosya yöneticisi. Python 3.10+, PySide6, boto3, pyperclip. Sürüm: **0.0.9** (`src/version.py`). **pytest** — 93 test (`tests/`).

## Dizin yapısı

```
S3MANAGER/
├── docs/                        # Tanıtım sitesi (GitHub Pages → s3manager.bahadirdogru.com)
│   ├── index.html, css/, js/, assets/, screenshots/, CNAME
├── release-notes/               # GitHub Release body (v0.0.8.md …)
├── tests/
│   ├── conftest.py              # mock_config_dir, spaces_client (moto)
│   ├── unit/                    # helpers, validators, metadata, cache, settings
│   └── services/                # SpacesClient (moto mock S3)
├── pyproject.toml               # pytest + coverage yapılandırması
├── src/
│   ├── main.py
│   ├── version.py               # __version__, GITHUB_REPO
│   ├── config/
│   │   ├── settings.py          # ~/.s3manager/config.ini (+ updates dismissed)
│   │   └── credentials.py
│   ├── ui/qt/
│   │   ├── main_window.py       # Workers, MainWindow, iki satır toolbar, btn_settings
│   │   ├── models.py
│   │   ├── dialogs.py
│   │   ├── settings_dialog.py   # Tab'lı Ayarlar (Bağlantı, Metadata, Görünüm, Günlük, Bakım, Yardım)
│   │   ├── object_properties_dialog.py  # Nesne metadata / ACL
│   │   ├── incomplete_uploads_panel.py  # Yarım multipart (Bakım sekmesi)
│   │   ├── upload_metadata_panel.py  # Metadata form widget
│   │   ├── styles.py            # ThemePalette, build_stylesheet, apply_app_theme, apply_item_view_palette
│   │   ├── theme_switch.py      # Toolbar tema toggle
│   │   ├── connection_indicator.py  # Bağlantı göstergesi (yeşil/kırmızı)
│   │   ├── preview_panel.py
│   │   ├── transfer_panel.py
│   │   └── file_tree_view.py
│   ├── services/
│   │   ├── spaces_client.py
│   │   ├── upload_service.py
│   │   ├── share_service.py
│   │   ├── listing_cache.py
│   │   └── update_service.py    # GitHub Releases API
│   └── utils/
│       ├── helpers.py
│       ├── log_viewer.py        # read_log_tail (günlük sekmesi)
│       └── object_metadata.py   # MIME tespiti, upload ExtraArgs
├── assets/                      # icon.png, icon.ico, icon.icns (macOS build)
├── build/macos_x86_64/          # Intel macOS release only: PySide6 shim + legacy_entry.py
├── requirements-macos-x86_64.txt  # PySide2 (release Intel DMG; dev'de gerekmez)
├── .github/workflows/
│   ├── ci.yml                   # PR/main: test → matrix build
│   └── release.yml              # tag → build + release-notes/vX.Y.Z.md body
├── scripts/
│   ├── build.ps1 / build.sh
│   ├── test.sh                  # venv + pytest + coverage
│   ├── capture_screenshots.py   # docs/screenshots/ UI görüntüleri
│   ├── generate_og_image.py     # docs/assets/og-image.png
│   ├── package-windows.ps1      # NSIS installer (makensis otomatik bulunur)
│   ├── package-macos.sh         # DMG (arm64 PySide6 / x86_64 legacy)
│   ├── setup-macos-legacy-python.sh  # python-build-standalone 3.10 (Intel release)
│   ├── verify-macos-legacy-binary.sh # macOS 10.13 dylib uyumluluk kontrolü
│   ├── package-linux.sh         # tar.gz + AppImage (--appimage-extract-and-run CI)
│   ├── generate_icons.py
│   └── installer/windows.nsi
├── start.sh                     # venv + pip + python src/main.py (Git Bash/WSL)
├── s3manager.spec               # PySide6 collect_all YOK; QtWidgets only
├── s3manager-macos-x86_64.spec  # Intel macOS release: PySide2 + shim (min 10.13)
```

**macOS kuralı:** UI kodu `PySide6` import kullanır. Intel legacy build shim + **python-build-standalone** 3.10 ile release'te çözülür — `src/` değiştirilmez. Günlük dev/CI yalnızca PySide6 (`setup-python` Intel release'te kullanılmaz).

Release artifact'ları (6): Windows setup + portable, macOS arm64 dmg, macOS x86_64 dmg, Linux tar.gz + AppImage.

## Kritik dosyalar

| Dosya | Amaç |
|-------|------|
| `main_window.py` | UI koordinasyon, QThread workers, `_stop_list_worker` / `_detach_list_worker` |
| `models.py` | `FileModel`: `append_items`, `canFetchMore`, ACL lazy |
| `spaces_client.py` | `list_objects_page`, CRUD, `put_object_acl`, `update_object_metadata`, `delete_objects_batch`, multipart list/abort |
| `upload_service.py` | Multipart upload, progress callbacks, metadata ExtraArgs |
| `object_metadata.py` | `guess_content_type`, `build_upload_extra_args`, `UploadMetadataSettings` |
| `listing_cache.py` | Prefix bazlı liste cache (TTL 60s) |
| `dialogs.py` | Login, Upload, ShareDialog, UploadMetadataSettingsDialog (wrapper) |
| `settings_dialog.py` | SettingsDialog — Bağlantı, Metadata, Görünüm, Günlük, Bakım, Yardım sekmeleri |
| `styles.py` | `ThemePalette`, `apply_app_theme()`, `apply_item_view_palette()` — QApplication seviyesinde tema |
| `theme_switch.py` | Toolbar `ThemeSwitch` widget (🌙/☀️) |
| `settings.py` | config.ini; `[upload_metadata]`, `[appearance] theme` |

## Workers (QThread)

| Worker | Görev |
|--------|-------|
| `SpacesWorker` | Sayfalı listeleme → `page_loaded` signal |
| `AttributeWorker` | Görünür satırlar için ACL lazy load |
| `ActionWorker` | Silme, klasör oluşturma |
| `DownloadWorker` | İndirme |
| `ParallelUploadWorker` | ThreadPoolExecutor max 3 paralel upload |

## Geliştirme kısıtları

1. **Threading:** UI ana thread; ağ IO worker'da. UI güncelleme → Signal/Slot. `thread.terminate()` kullanma → `requestInterruption()`. Liste worker navigasyonda `_detach_list_worker` ile sinyaller koparılır; stale callback guard (`sender() is _list_worker`).
2. **Listeleme:** `list_objects_page()` sayfa sayfa; `FileModel.append_items()` — `beginResetModel` ile binlerce satırı tek seferde yükleme.
3. **Multipart eşiği:** 100 MB (`helpers.MULTIPART_THRESHOLD_MB` ve `TransferConfig`).
4. **ACL listelemede çekilmez** — `AttributeWorker` görünür satırlarda lazy load.
5. **Config:** `~/.s3manager/config.ini` düz metin; log `~/.s3manager/app.log`. Eski `~/.pydamlaspace/` otomatik taşınır. `[upload_metadata]` — yükleme Content-Type/Disposition/Cache-Control. `[appearance] theme` — `dark`/`light`.
6. **Tema:** `apply_app_theme()` → `QApplication.setStyleSheet`; tablolar için `apply_item_view_palette()`; dialog gölge `apply_dialog_elevation(dark=...)`.
7. **Upload progress:** `progress.lock` içinde `get_progress()` çağırma (deadlock).
8. **UploadDialog:** Dosya Seç = liste replace; `clear_progress_area()` yeni seçimde.
9. **Remote key:** Leading `/` olmamalı.
10. **Dökümantasyon:** README, UI, ARCHITECTURE, LLM, PROCESS, docs/ — yeni üst düzey md oluşturma. Changelog yalnızca PROCESS.md.
11. **Changelog:** [PROCESS.md](PROCESS.md).

## Yeni özellik akışı

1. Servis katmanı (`src/services/`)
2. Qt UI (`src/ui/qt/`)
3. MainWindow entegrasyonu + QThread gerekirse
4. Stil → [UI.md](UI.md); mimari → [ARCHITECTURE.md](ARCHITECTURE.md)
5. [PROCESS.md](PROCESS.md) changelog güncelle

## Bağımlılıklar

`boto3`, `PySide6`, `pyperclip` — `requirements.txt`  
Test: `pytest`, `pytest-cov`, `moto[s3]`, `freezegun` — `requirements-dev.txt`

## Test

- `sh scripts/test.sh` veya `pytest` — 93 test; coverage eşiği %60 (`pyproject.toml`)
- `tests/unit/` + `tests/services/` (moto S3); UI (`src/ui/*`) omit
- CI: `.github/workflows/ci.yml` → `test` job → `build` matrix
- GUI testleri yok (`pytest-qt` kullanılmaz)

## Çalıştırma

`./start.sh` (Git Bash/WSL) veya `python src/main.py` (venv aktif)

## Derleme (onedir)

`scripts/build.ps1` (Windows) veya `scripts/build.sh` (Linux/macOS). Çıktı: `dist/S3MANAGER/` klasörü (exe + `_internal/`) ve `dist/S3MANAGER.zip`. `s3manager.spec` içinde `collect_all("PySide6")` kullanılmaz. Frozen'da `paths.is_frozen()` → `sys._MEIPASS`; kullanıcı verisi `~/.s3manager/`.

## Release

`src/version.py` güncelle → commit → `git tag v0.0.8 && git push origin main && git push origin v0.0.8`

`release-notes/vX.Y.Z.md` ekle; `release.yml` tag push'ta binary + release body oluşturur.
