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
> **Bu dosya:** Mimari dokümantasyon — katmanlar, veri akışı, threading ve güvenlik.

# Mimari Dokümantasyon

## Genel Bakış

S3MANAGER, DigitalOcean Spaces ile etkileşim için PySide6 tabanlı bir masaüstü uygulamasıdır. UI, servis ve config katmanları ayrılmıştır; ağ işlemleri worker thread'lerde çalışır.

## Mimari Katmanlar

```
┌─────────────────────────────────────┐
│         UI Layer (PySide6)          │
│  MainWindow, FileModel, Dialogs     │
│  QTreeView, Breadcrumb, Workers     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Service Layer                    │
│  SpacesClient, UploadService          │
│  ShareService, ListingCache           │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Config + Utils                   │
│  Settings, CredentialsManager         │
│  helpers, validators, logging         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      DigitalOcean Spaces (boto3)      │
└─────────────────────────────────────┘
```

## UI Katmanı

### MainWindow (`src/ui/qt/main_window.py`)

Ana pencere; iki satır toolbar, breadcrumb, arama, split-view (liste + önizleme), transfer paneli ve tüm worker'ları koordine eder.

Navigasyon (`navigate_to`, breadcrumb, geri) sırasında önceki `SpacesWorker` durdurulur ve sinyalleri koparılır (`_stop_list_worker`, `_detach_list_worker`). Cache hit'te stale callback'lerin modeli bozmaması için `on_page_loaded` / `on_list_finished` içinde `sender() is _list_worker` kontrolü yapılır.

**Worker sınıfları (aynı dosyada):**

| Worker | Görev |
|--------|-------|
| `SpacesWorker` | Sayfalı dosya listeleme |
| `AttributeWorker` | Görünür satırlar için ACL lazy load |
| `ActionWorker` | Silme, klasör oluşturma |
| `DownloadWorker` | Dosya/klasör indirme |
| `ParallelUploadWorker` | Paralel yükleme (max 3 thread) |

### FileModel (`src/ui/qt/models.py`)

`QAbstractItemModel` tabanlı liste modeli. Sanal scrolling ile binlerce satır desteklenir. Sayfalı yükleme için `append_items()` kullanılır; `canFetchMore` / `fetchMore` scroll ile sonraki sayfayı tetikler.

### PreviewPanel (`src/ui/qt/preview_panel.py`)

Split-view sağ panel. Tek dosya seçildiğinde metadata + görsel/metin önizleme. **Özellikler** → `ObjectPropertiesDialog`.

### SettingsDialog (`src/ui/qt/settings_dialog.py`)

Toolbar **Ayarlar** — 6 sekme: Bağlantı, Yükleme Metadata, Görünüm, Günlük, **Bakım** (`IncompleteUploadsPanel`), Yardım. Görünüm sekmesi toolbar `ThemeSwitch` ile senkron.

### ObjectPropertiesDialog (`src/ui/qt/object_properties_dialog.py`)

Mevcut nesnede Content-Type, Cache-Control, `x-amz-meta-*`, ACL düzenleme → `SpacesClient.update_object_metadata`, `put_object_acl`.

### Dialogs (`src/ui/qt/dialogs.py`)

- **LoginDialog** — Kimlik bilgisi, validators, `test_connection()`
- **UploadDialog** — Üç fazlı: seçim (drop zone + dosya listesi), yükleme (genel progress), özet
- **ShareDialog** — 3/7 gün paylaşım süresi seçimi

### Styles (`src/ui/qt/styles.py`)

WhatsApp-inspired dark/light QSS — `ThemePalette`, `apply_app_theme()`, `apply_item_view_palette()` (Windows tablo viewport). Detaylar [UI.md](UI.md).

## Servis Katmanı

### SpacesClient (`src/services/spaces_client.py`)

Boto3 S3 client wrapper (DigitalOcean Spaces endpoint).

- `list_objects_page()` — Tek API sayfası (lazy loading)
- `list_objects()` — Tam liste (indirme/silme için)
- `upload_file`, `download_file`, `delete_object`, `delete_objects_batch`, `delete_folder_recursive`
- `get_object_acl`, `head_object` — Lazy attribute / önizleme
- `put_object_acl`, `update_object_metadata` — Nesne özellikleri dialogu
- `list_incomplete_multipart_uploads`, `abort_multipart_upload` — Bakım sekmesi
- `create_presigned_url`, `create_folder`, `test_connection`

### UploadService (`src/services/upload_service.py`)

Multipart upload (100MB eşik), thread-safe progress. **Deadlock önleme:** `progress.lock` içinde `get_progress()` çağrılmaz.

### ShareService (`src/services/share_service.py`)

Presigned URL (3/7 gün) ve panoya kopyalama.

### ListingCache (`src/services/listing_cache.py`)

Prefix bazlı klasör listesi cache (TTL 60 saniye). Upload/silme/yenile sonrası invalidate.

## Config Katmanı

- **Settings** — `~/.s3manager/config.ini` okuma/yazma
- **CredentialsManager** — Oturum içi credential cache

## Veri Akışı

### Bağlantı

```
LoginDialog → validators → SpacesClient.test_connection()
         → Settings.save_credentials() → MainWindow.on_connected()
```

### Sayfalı listeleme (lazy loading)

```
refresh_list → _stop_list_worker (önceki worker sinyalleri kopar)
            → ListingCache.get (hit → model.set_items, return)
            → SpacesWorker (miss)
                  → list_objects_page() [sayfa 1..N]
                  → page_loaded → FileModel.append_items()  [stale guard]
                  → finished → ListingCache.put(worker prefix)  [stale guard]
            → AttributeWorker → get_object_acl (görünür satırlar)
```

### Yükleme

```
UploadDialog.upload_started → ParallelUploadWorker (ThreadPoolExecutor, max 3)
                           → UploadService.upload_file() × N
                           → object_metadata.build_upload_extra_args() (Content-Type, Content-Disposition, Cache-Control)
                           → SpacesClient.upload_file(ExtraArgs=...)
                           → progress signals → UploadDialog
```

Yükleme metadata ayarları `~/.s3manager/config.ini` `[upload_metadata]` bölümünde; **Ayarlar → Yükleme Metadata...** veya Upload dialog'undaki **Ayarlar...** ile düzenlenir.

### İndirme

```
DownloadWorker → list_all_keys (klasör) → download_file (her dosya)
```

### Paylaşım

```
ShareDialog → ShareService.share_to_clipboard() → presigned URL → pyperclip
```

### Nesne özellikleri

```
Context menu / PreviewPanel → ObjectPropertiesDialog
                         → update_object_metadata (copy+replace)
                         → put_object_acl
```

### Toplu silme

```
Çoklu seçim → delete_objects_batch (batch API, ActionWorker yerine doğrudan batch)
```

### Tanıtım sitesi

Statik site `docs/` → GitHub Pages → https://s3manager.bahadirdogru.com/ (`docs/CNAME`). Renkler `docs/css/style.css` ile UI paleti senkron.

## Threading

- **Ana thread:** Tüm Qt widget işlemleri
- **Worker thread'ler:** boto3 ağ çağrıları
- **İptal:** `requestInterruption()` + `isInterruptionRequested()`; `terminate()` kullanılmaz
- **UI güncelleme:** Qt Signal/Slot (thread-safe)

## Güvenlik

1. Credentials `~/.s3manager/config.ini` (düz metin, home dizini)
2. Şifre alanları maskelenir (`QLineEdit.Password`)
3. ACL: yüklemede kullanıcı seçimi (private/public-read)
4. Presigned URL: sadece GET, 3/7 gün

## Performans

1. **Qt Model/View** — Sanal scrolling
2. **Sayfalı listeleme** — İlk sayfa hızlı görünür; scroll ile devam
3. **ListingCache** — Geri navigasyonda anında liste
4. **ACL lazy load** — Listelemede N+1 API çağrısı yok
5. **Multipart upload** — 100MB üzeri, max 3 paralel upload thread

## Hata Yönetimi

- Servislerde try/except; UI'da `QMessageBox`
- Worker'larda `error` signal
- Tüm hatalar `app.log` (RotatingFileHandler, 10MB, 5 yedek)

## Test stratejisi

- **pytest** — unit testler (`tests/unit/`) ve servis testleri (`tests/services/`)
- **moto** — boto3 S3 çağrıları mock'lanır; gerçek DigitalOcean bağlantısı gerekmez
- **Coverage** — `pyproject.toml` ile %60 eşik; Qt UI katmanı (`src/ui/*`) ve ağır upload servisi omit
- **CI** — `test` job (ubuntu) geçmeden PyInstaller build matrix başlamaz
- GUI testleri bilinçli olarak kapsam dışı

## CI / Release

| Workflow | Tetikleyici | Çıktı |
|----------|-------------|-------|
| `ci.yml` | push/PR `main` | `test` (pytest, 93 test) → matrix build, artifact 7 gün |
| `release.yml` | tag `v*.*.*` | Windows (NSIS+zip), macOS (dmg), Linux (tar.gz+AppImage) → GitHub Release (`release-notes/vX.Y.Z.md`) |

PyInstaller `s3manager.spec`: yalnızca QtWidgets; `collect_all("PySide6")` kullanılmaz. Windows NSIS: Chocolatey + `makensis` PATH. Linux AppImage: `--appimage-extract-and-run` (CI'da FUSE gerekmez).

## Bağımlılıklar

`boto3>=1.34.0`, `PySide6>=6.10.0`, `pyperclip>=1.8.2`

## Değişiklik geçmişi

[PROCESS.md](PROCESS.md)
