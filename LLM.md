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
> **Bu dosya:** LLM için token-optimize proje yapısı ve geliştirme kısıtları.

# S3MANAGER — LLM Rehberi

DigitalOcean Spaces masaüstü dosya yöneticisi. Python 3.10+, PySide6, boto3, pyperclip. Sürüm: **0.0.4** (`src/version.py`). **Test yok** — otomatik test kurulmaz.

## Dizin yapısı

```
S3MANAGER/
├── src/
│   ├── main.py
│   ├── version.py               # __version__, GITHUB_REPO
│   ├── config/
│   │   ├── settings.py          # ~/.s3manager/config.ini (+ updates dismissed)
│   │   └── credentials.py
│   ├── ui/qt/
│   │   ├── main_window.py       # Workers, MainWindow, update check, Yardım menüsü
│   │   ├── models.py
│   │   ├── dialogs.py
│   │   └── styles.py
│   ├── services/
│   │   ├── spaces_client.py
│   │   ├── upload_service.py
│   │   ├── share_service.py
│   │   ├── listing_cache.py
│   │   └── update_service.py    # GitHub Releases API
│   └── utils/
│       ├── helpers.py
│       └── object_metadata.py   # MIME tespiti, upload ExtraArgs
├── assets/                      # icon.png, icon.ico, icon.icns (macOS build)
├── .github/workflows/
│   ├── ci.yml                   # PR/main matrix build
│   └── release.yml              # tag → GitHub Release
├── scripts/
│   ├── build.ps1 / build.sh
│   ├── package-windows.ps1      # NSIS installer (makensis otomatik bulunur)
│   ├── package-macos.sh         # DMG
│   ├── package-linux.sh         # tar.gz + AppImage (--appimage-extract-and-run CI)
│   ├── generate_icons.py
│   └── installer/windows.nsi
├── start.sh                     # venv + pip + python src/main.py (Git Bash/WSL)
├── s3manager.spec               # PySide6 collect_all YOK; QtWidgets only
```

## Kritik dosyalar

| Dosya | Amaç |
|-------|------|
| `main_window.py` | UI koordinasyon, QThread workers, `_stop_list_worker` / `_detach_list_worker` |
| `models.py` | `FileModel`: `append_items`, `canFetchMore`, ACL lazy |
| `spaces_client.py` | `list_objects_page`, upload/download/delete |
| `upload_service.py` | Multipart upload, progress callbacks, metadata ExtraArgs |
| `object_metadata.py` | `guess_content_type`, `build_upload_extra_args`, `UploadMetadataSettings` |
| `listing_cache.py` | Prefix bazlı liste cache (TTL 60s) |
| `dialogs.py` | Login, Upload, ShareDialog, UploadMetadataSettingsDialog |
| `settings.py` | config.ini; `[upload_metadata]` okuma/yazma |

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
5. **Config:** `~/.s3manager/config.ini` düz metin; log `~/.s3manager/app.log`. Eski `~/.pydamlaspace/` otomatik taşınır. `[upload_metadata]` — yükleme Content-Type/Disposition/Cache-Control.
6. **Upload progress:** `progress.lock` içinde `get_progress()` çağırma (deadlock).
7. **UploadDialog:** Dosya Seç = liste replace; `clear_progress_area()` yeni seçimde.
8. **Remote key:** Leading `/` olmamalı.
9. **Dökümantasyon:** Sadece 5 md dosyası; yeni md oluşturma.
10. **Changelog:** [PROCESS.md](PROCESS.md).

## Yeni özellik akışı

1. Servis katmanı (`src/services/`)
2. Qt UI (`src/ui/qt/`)
3. MainWindow entegrasyonu + QThread gerekirse
4. Stil → [UI.md](UI.md); mimari → [ARCHITECTURE.md](ARCHITECTURE.md)
5. [PROCESS.md](PROCESS.md) changelog güncelle

## Bağımlılıklar

`boto3`, `PySide6`, `pyperclip` — `requirements.txt`

## Çalıştırma

`./start.sh` (Git Bash/WSL) veya `python src/main.py` (venv aktif)

## Derleme (onedir)

`scripts/build.ps1` (Windows) veya `scripts/build.sh` (Linux/macOS). Çıktı: `dist/S3MANAGER/` klasörü (exe + `_internal/`) ve `dist/S3MANAGER.zip`. `s3manager.spec` içinde `collect_all("PySide6")` kullanılmaz. Frozen'da `paths.is_frozen()` → `sys._MEIPASS`; kullanıcı verisi `~/.s3manager/`.

## Release

`git tag v0.0.4 && git push origin v0.0.4` → `.github/workflows/release.yml` (Windows NSIS/choco, Linux AppImage/FUSE, macOS DMG).
