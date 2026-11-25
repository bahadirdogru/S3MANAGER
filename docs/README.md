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

`docs/index.html` dosyasını tarayıcıda açın veya `npx serve docs` çalıştırın.

## Ekran görüntüleri

`docs/screenshots/` elle güncellenir: uygulamayı `pnpm tauri dev` ile açıp koyu/açık tema ana pencere, önizleme ve ayarlar
ekranlarının görüntüsünü alın (`main-dark.png`, `main-light.png`, `preview.png`, `settings.png`).

## İndirme tablosu

Kullanıcıya dönük platform/DMG tablosu `docs/index.html` içindedir (README Releases bölümü ile senkron tutulmalı). macOS için arm64 ve Intel x86_64 satırları ayrı gösterilir (Tauri sürümlerinde minimum macOS 10.15).
