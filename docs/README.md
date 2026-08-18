# GitHub Pages yayını

Bu klasör statik tanıtım sitesini içerir.

## İlk kurulum (bir kez)

1. GitHub repo → **Settings** → **Pages**
2. **Build and deployment** → Source: **Deploy from a branch**
3. Branch: `main`, Folder: **`/docs`**
4. Save — site birkaç dakika içinde yayında olur

**URL:** https://s3manager.bahadirdogru.com/

Özel domain: `docs/CNAME` dosyasında tanımlı. GitHub Pages ayarlarında **Custom domain** alanına aynı adresi girin.

## Yerel önizleme

`docs/index.html` dosyasını tarayıcıda açın veya:

```bash
python -m http.server 8080 --directory docs
```

## Ekran görüntülerini yenileme

```bash
python scripts/capture_screenshots.py
python scripts/generate_og_image.py
```

## İndirme tablosu

Kullanıcıya dönük platform/DMG tablosu `docs/index.html` içindedir (README Releases bölümü ile senkron tutulmalı). macOS için arm64 (13+) ve Intel x86_64 (10.13+) satırları ayrı gösterilir.
