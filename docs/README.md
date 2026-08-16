# GitHub Pages yayını

Bu klasör statik tanıtım sitesini içerir.

## İlk kurulum (bir kez)

1. GitHub repo → **Settings** → **Pages**
2. **Build and deployment** → Source: **Deploy from a branch**
3. Branch: `main`, Folder: **`/docs`**
4. Save — site birkaç dakika içinde yayında olur

**URL:** https://bahadirdogru.github.io/S3MANAGER/

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
