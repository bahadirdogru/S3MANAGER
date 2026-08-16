# Changelog

Tüm önemli değişiklikler bu dosyada kayıt altına alınır. Format [Keep a Changelog](https://keepachangelog.com/) ile uyumludur.

## [0.0.8] - 2026-08-16

### Added

- **Ayarlar menüsü** — Toolbar'da tek `Ayarlar` butonu; tab'lı `SettingsDialog` (Bağlantı, Yükleme Metadata, Görünüm, Günlük, Bakım, Yardım)
- **Nesne özellikleri** — Content-Type, Cache-Control, `x-amz-meta-*` ve ACL düzenleme (`ObjectPropertiesDialog`; context menu ve önizleme paneli)
- **Bakım sekmesi** — Yarım kalan multipart yüklemeleri listeleme ve iptal
- **S3 API** — `put_object_acl`, `update_object_metadata`, `delete_objects_batch`, `list_incomplete_multipart_uploads`, `abort_multipart_upload`
- **ConnectionIndicator** — Toolbar bağlantı durumu (yeşil/kırmızı nokta)
- **Log görüntüleme** — Ayarlar Günlük sekmesi (`read_log_tail`)
- **Tema tutarlılığı** — Global QSS (viewport, read-only input, tablolar); `apply_item_view_palette` (Windows tablo düzeltmesi)

### Changed

- Toolbar iki satır: breadcrumb + arama; Yardım/Metadata toolbar butonları Ayarlar'a taşındı
- Toplu dosya silme `delete_objects` batch API kullanır
- Önizleme metin alanı light/dark paletle uyumlu
- `Transferler` başlık rengi light modda okunabilir
- README roadmap: S3/DO API eksikleri ve CDN purge (DO API token) planlandı

### Tests

- `test_spaces_client.py`: ACL, metadata güncelleme, batch delete, multipart testleri (+4 sınıf, toplam 93 test)

## [0.0.7] - 2026-08-11

### Added

- Kopyala / taşı / yeniden adlandır (toolbar, context menu, F2, Ctrl+C/X)
- Toolbar arama, sürükle-bırak yükleme, transfer geçmişi paneli
- Split-view dosya önizleme (görsel/metin)
- pytest + moto test altyapısı (CI test job)

[0.0.8]: https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.8
[0.0.7]: https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.7
