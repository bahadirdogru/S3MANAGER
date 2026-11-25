> **Doc Map** — Proje dökümantasyon rehberi
>
> | Dosya | Ne için okunur |
> |-------|----------------|
> | [README.md](README.md) | Kurulum, kullanım, proje tanıtımı (GitHub/GitLab anasayfa) |
> | [docs/](docs/) | Tanıtım web sitesi ([s3manager.bahadirdogru.com](https://s3manager.bahadirdogru.com/)) |
> | [UI.md](UI.md) | Renk, tema token'ları, shadcn-svelte bileşen ve UX kuralları |
> | [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, veri akışı, eşzamanlılık (insan okuması) |
> | [LLM.md](LLM.md) | Güncel kod yapısı, dosya haritası, geliştirme kısıtları (LLM) |
> | [process.md](process.md) | Kronolojik değişiklik kayıtları (changelog) |
>
> **Bu dosya:** LLM için token-optimize proje yapısı ve geliştirme kısıtları.

# S3MANAGER — LLM Rehberi

S3 uyumlu depolama masaüstü dosya yöneticisi. **Tauri 2** — Rust backend (`aws-sdk-s3`, `tokio`) + SvelteKit 3 / Svelte 5 / TypeScript frontend + shadcn-svelte (vega, lucide) + Tailwind 4. Paket yöneticisi **pnpm**. Sürüm: **0.1.0** (`src-tauri/tauri.conf.json`, `src-tauri/Cargo.toml`, `package.json` — üçü aynı tutulur). Python kodu yoktur.

## Dizin yapısı

```
S3MANAGER/
├── src-tauri/
│   ├── Cargo.toml, tauri.conf.json, capabilities/default.json, icons/
│   └── src/
│       ├── main.rs          # s3manager_lib::run()
│       ├── lib.rs           # plugin'ler, invoke_handler (komut listesi), log hedefleri
│       ├── commands.rs      # AppState + tüm #[tauri::command]
│       ├── s3.rs            # Spaces istemcisi + `live` entegrasyon testi
│       ├── transfers.rs     # TransferManager, Sink, expand_local + `live` transfer testi
│       ├── config.rs        # ~/.s3manager/config.ini
│       ├── metadata.rs      # Content-Type / Disposition kuralları
│       └── error.rs         # AppError, s3() hata dönüştürücü
├── src/
│   ├── app.html, routes/(+layout.svelte, +layout.ts, +page.svelte, layout.css)
│   └── lib/
│       ├── api.ts           # invoke() sarmalayıcıları + tipler (Rust struct'larının aynası)
│       ├── actions.ts       # kullanıcı işlemleri
│       ├── format.ts        # boyut/tarih, uniqueCopyName, toPrefix, DO_REGIONS
│       ├── stores/          # explorer, transfers, session, dialogs, ui (*.svelte.ts, runes)
│       └── components/
│           ├── app/         # Explorer, FileTable, PreviewPanel, TransferPanel, LoginView, *Dialog, DialogHost
│           └── ui/          # shadcn-svelte üretimi — elle düzenleme
├── static/                  # favicon
├── docs/                    # Tanıtım sitesi (GitHub Pages)
├── release-notes/           # vX.Y.Z.md → GitHub Release gövdesi
├── assets/                  # kaynak ikon (icon.png → `pnpm tauri icon assets/icon.png`)
├── .github/workflows/       # ci.yml (check + test + MinIO canlı test → build matrisi), release.yml (tauri-action)
├── components.json          # shadcn-svelte ayarları (alias'lar #lib/…)
└── vite.config.ts           # SvelteKit config da burada (Kit 3), adapter-static, port 1420
```

## Kritik kurallar

1. **`#lib` import'ları tam yol ister** (Node subpath imports, Kit 3): `#lib/api.js`, `#lib/stores/explorer.svelte.js`, `#lib/components/ui/button/index.js`. Uzantısız `#lib/api` derlenmez.
2. **Yeni komut:** `commands.rs`'e fonksiyon → `lib.rs` `generate_handler!` listesine ekle → `api.ts`'e tipli sarmalayıcı. Rust parametreleri snake_case, JS tarafında camelCase gönderilir (`dest_dir` ↔ `destDir`). Struct'lar `#[serde(rename_all = "camelCase")]`.
3. **Ağ IO'su yalnızca Rust'ta.** Frontend S3'e `fetch` yapmaz; CSP buna izin vermez.
4. **Anahtarlar:** baştaki `/` her zaman `norm()` ile atılır; klasör önekleri `as_prefix()` ile `/` ile biter (kök = `""`).
5. **ACL korunur:** `CopyObject` ACL'i sıfırlar — kopyala/taşı/metadata güncelle kaynak ACL'ini yeniden uygular. Yeni kopyalama yolu eklerken aynısını yap.
6. **Checksum:** istemci `WhenRequired` ile kurulur; değiştirme (Spaces/MinIO/R2 kırılır).
7. **Transfer:** multipart eşiği `MULTIPART_THRESHOLD` (16 MB), parça ≥ 8 MB, ≤ 10 000 parça, parça eşzamanlılığı 4, dosya eşzamanlılığı 3. Hata/iptalde `abort_multipart`. İndirme `.part` → rename. İlerleme yalnızca `Reporter`/`Sink` üzerinden.
8. **İndirme yolu güvenliği:** anahtar → yerel yol dönüşümü `safe_relative` / `safe_name` ile yapılır; bypass etme.
9. **Listeleme:** sayfa 200; stale yanıtlar `explorer` içindeki nesil sayacıyla atılır. ACL listede çekilmez — görünen satırlar için `wantAcl()`.
10. **Toplu işlem kilidi:** kopyala/taşı/sil/yeniden adlandır `ui.busy` ile tek seferde bir tane.
11. **Diyaloglar:** basit soru için `dialogs.prompt()` / `dialogs.confirm()`; yeni özellik diyaloğu için `ui` store'una durum + `Explorer.svelte` altına bileşen.
12. **Kısayollar** `Explorer.svelte` `onKeydown` içinde; input'ta yazarken ve diyalog açıkken çalışmaz.
13. **Stil:** renkler yalnızca tema token'larından (`bg-primary`, `text-muted-foreground`, `bg-selected`, `text-success`, `text-warning`…) — bkz. [UI.md](UI.md). Hex yazma.
14. **shadcn bileşeni ekleme:** `pnpm dlx shadcn-svelte@latest add <ad>`; `components/ui/` altını elle değiştirme.
15. **Config uyumu:** `config.ini` bölüm/anahtar adlarını değiştirme (eski kurulumlar okunuyor).
16. **Dökümantasyon:** README (EN), readmetr (TR), UI, ARCHITECTURE, LLM, process.md — yeni üst düzey md oluşturma. Changelog yalnızca `process.md`.

## Komutlar (`commands.rs`)

| Grup | Komutlar |
|------|----------|
| Oturum | `get_startup`, `default_endpoint`, `connect`, `disconnect`, `ping` |
| Gezinme | `list_page`, `get_acls`, `set_acl`, `object_info`, `update_metadata`, `preview` |
| Dosya işlemleri | `create_folder`, `delete_items`, `copy_item`, `move_item`, `rename_item`, `share_link` |
| Transfer | `expand_upload`, `start_upload`, `start_download`, `cancel_transfer`, `cancel_all_transfers`, `active_transfers` |
| Bakım | `list_multipart`, `abort_multipart` |
| Ayarlar | `get_upload_metadata`, `save_upload_metadata`, `save_theme`, `check_update`, `dismiss_update`, `read_log` |

Olay: `transfer` → `TransferEvent { id, direction, name, remoteKey, localPath, total, transferred, status, error, speed, multipart }`.

## Test

- `pnpm check` — svelte-check, 0 hata / 0 uyarı tutulur
- `pnpm test:rust` — birim testleri
- `pnpm test:live` — canlı S3 (`S3M_IT_ENDPOINT`, `S3M_IT_KEY`, `S3M_IT_SECRET`, `S3M_IT_BUCKET`, isteğe bağlı `S3M_IT_REGION`, `S3M_IT_PATH_STYLE`, `S3M_IT_ACL`). MinIO ACL'i yok sayar; `max-keys=1` + klasör işaretçisinde `IsTruncated` yanlış döner — testler 2 kullanır.
- Frontend bileşen testi yok.

## Çalıştırma / derleme

`pnpm tauri dev` (HMR) · `pnpm tauri build` (mevcut platform paketleri) · Linux bağımlılıkları (Fedora): `webkit2gtk4.1-devel gtk3-devel libsoup3-devel openssl-devel`.

## Release

Üç dosyada sürümü güncelle → `release-notes/vX.Y.Z.md` → commit → `git tag vX.Y.Z && git push origin main vX.Y.Z`. `release.yml` tauri-action ile Windows (nsis+msi), macOS arm64 + x86_64 (dmg), Linux (AppImage, deb, rpm) üretir.
