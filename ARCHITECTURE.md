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
> **Bu dosya:** Mimari katmanlar, veri akışı ve eşzamanlılık modeli.

# S3MANAGER — Mimari

## Genel bakış

S3MANAGER bir **Tauri 2** uygulamasıdır. Tek bir native süreç içinde iki katman çalışır:

```
┌──────────────────────────── WebView (WebKitGTK / WKWebView / WebView2) ────────────────────────────┐
│  SvelteKit SPA (TypeScript, Svelte 5 runes, shadcn-svelte)                                         │
│                                                                                                    │
│  components/app/*.svelte ──▶ actions.ts ──▶ api.ts ── invoke() ──┐      listen('transfer') ◀──┐    │
│        ▲                          │                             │                            │    │
│        └──── stores/*.svelte.ts ◀─┘  (explorer, transfers, session, dialogs, ui)             │    │
└─────────────────────────────────────────────────────────────────│────────────────────────────│────┘
                                                IPC (JSON)        ▼                            │
┌──────────────────────────────────────── Rust (tokio) ──────────────────────────────────────────────┐
│  commands.rs  (#[tauri::command], AppState)                                                        │
│      │                 │                         │                                                 │
│      ▼                 ▼                         ▼                                                 │
│  s3.rs (Spaces)    transfers.rs (TransferManager) ── emit("transfer", TransferEvent) ──────────────┘
│      │                 │                                                                           │
│      └──── aws-sdk-s3 ─┴──▶ S3 uyumlu endpoint (Spaces, AWS, MinIO, R2…)                           │
│  config.rs ──▶ ~/.s3manager/config.ini      metadata.rs (Content-Type kuralları)                    │
│  tauri-plugin-log ──▶ ~/.s3manager/app.log                                                         │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **Frontend hiçbir zaman S3'e doğrudan bağlanmaz.** Kimlik bilgileri, imzalama ve ağ IO'su yalnızca Rust tarafındadır. CSP `connect-src` yalnızca IPC'ye izin verir.
- Komutlar tek API yüzeyidir: `src-tauri/src/commands.rs` ↔ `src/lib/api.ts`. İkisi birlikte güncellenir.

## Rust katmanı (`src-tauri/src/`)

| Modül | Sorumluluk |
|-------|-----------|
| `lib.rs` | Plugin kayıtları (log, dialog, clipboard, opener), `invoke_handler`, pencere kapanınca transferleri iptal |
| `commands.rs` | `AppState { settings, spaces: RwLock<Option<Arc<Spaces>>>, transfers }`; tüm komutlar `AppResult<T>` döner |
| `s3.rs` | `Spaces` istemcisi: sayfalı listeleme, `list_all`, ACL okuma/yazma, head/metadata, kopyala/taşı/yeniden adlandır, toplu silme, presign, multipart listele/iptal |
| `transfers.rs` | Yükleme/indirme kuyruğu, ilerleme olayları, iptal |
| `config.rs` | `config.ini` okuma/yazma (`[digitalocean]`, `[upload_metadata]`, `[appearance]`, `[updates]`) |
| `metadata.rs` | Uzantı → Content-Type / Content-Disposition / Cache-Control |
| `error.rs` | `AppError` → frontend'e düz Türkçe metin olarak serialize edilir; S3 hata kodu (`AccessDenied` vb.) mesaja eklenir |

### S3 istemcisi

- `aws-sdk-s3` özel endpoint, bölge ve isteğe bağlı path-style ile kurulur.
- `request_checksum_calculation` / `response_checksum_validation` = **WhenRequired**. Yeni SDK varsayılanı olan CRC checksum'ları birçok S3 uyumlu servis reddeder.
- Zaman aşımları: bağlantı 60 s, okuma 300 s; standart retry, 3 deneme.
- Kopyalama `CopyObject` ile yapılır; kaynak anahtar `x-amz-copy-source` için percent-encode edilir. S3 kopyası ACL'i sıfırladığından **kopyala, taşı ve metadata güncellemede kaynak ACL'i okunup aynısı uygulanır**.
- Taşıma = kopyala + sil. Klasör işlemleri önekteki tüm anahtarları (`list_all`) dolaşır.
- Silme 1000'lik `DeleteObjects` partileriyle yapılır; servis bu çağrıyı reddederse tek tek `DeleteObject`'e düşer.

### Transferler

```
start_uploads / start_downloads
   └─ her dosya: uuid + CancellationToken → tokio görevi
        ├─ Semaphore (yükleme 3, indirme 3) — sırada: status=queued
        ├─ status=running
        ├─ yükleme ≤ 16 MB: tek PutObject (ByteStream::from_path)
        │  yükleme > 16 MB: CreateMultipartUpload → parçalar (≥ 8 MB, ≤ 10 000 parça, 4 eşzamanlı)
        │                   → CompleteMultipartUpload; hata/iptalde AbortMultipartUpload
        ├─ indirme: GetObject akışı → <ad>.part → rename; hata/iptalde .part silinir
        └─ status=done | error | cancelled
```

- İlerleme `Reporter` üzerinden `Sink` callback'ine gider; uygulamada bu `app.emit("transfer", …)`, testlerde bir koleksiyondur. Olaylar en fazla 150 ms'de bir yayınlanır.
- İptal `tokio::select!` ile her ağ adımında kontrol edilir. Multipart iptal edildiğinde parçalar sunucuda bırakılmaz.
- Klasör indirmede anahtar sonekleri güvenli göreli yola çevrilir (`..`, `.`, kök bileşenleri atılır) — kötü niyetli bir anahtar hedef klasörün dışına yazamaz.
- Yerel klasör yüklemede symlink'ler atlanır (döngü ve sürpriz yok).

## Frontend katmanı (`src/`)

SvelteKit `adapter-static` ile SPA olarak derlenir (`ssr = false`), Tauri bunu `build/` klasöründen sunar.

| Dosya | Sorumluluk |
|-------|-----------|
| `lib/api.ts` | Tipli `invoke()` sarmalayıcıları, `onTransfer()` |
| `lib/actions.ts` | Araç çubuğu, sağ tık menüsü ve kısayolların paylaştığı işlemler (yükle, indir, sil, yeniden adlandır, kopyala/taşı, paylaş) |
| `lib/stores/explorer.svelte.ts` | Mevcut önek, sayfalama, sıralama, seçim, 60 s önek cache'i, lazy ACL kuyruğu |
| `lib/stores/transfers.svelte.ts` | `transfer` olaylarından beslenen canlı liste; biten yüklemeden sonra klasörü yeniler |
| `lib/stores/session.svelte.ts` | Bağlanma, otomatik bağlanma, 60 s'de bir bağlantı ping'i, tema, açılış güncelleme kontrolü |
| `lib/stores/dialogs.svelte.ts` | Promise tabanlı `prompt()` / `confirm()` |
| `lib/stores/ui.svelte.ts` | Açık diyaloglar ve yükleri, çalışan toplu işlem kilidi (`busy`) |
| `lib/components/app/` | Ekranlar ve diyaloglar |
| `lib/components/ui/` | shadcn-svelte tarafından üretilir — elle düzenlenmez |

### Veri akışı: klasör açma

1. `explorer.open(prefix)` → nesil sayacı artar, cache'e bakılır (60 s TTL, anahtar: önek + arama).
2. Cache yoksa `list_page(prefix, null, search, 200)`; sonuç geldiğinde nesil değiştiyse (kullanıcı başka klasöre geçtiyse) atılır.
3. Tablo satırları ortak bir `IntersectionObserver` ile izlenir: görünen dosya satırları ACL kuyruğuna girer (120 ms toplanır, `get_acls` 8 eşzamanlı), alttaki gözcü satırı görününce `loadMore()` çağrılır.

### Veri akışı: yükleme

1. Dosya seçici veya sürükle-bırak → `expand_upload(paths, prefix)` (Rust klasörleri dolaşır, anahtarları üretir).
2. `UploadDialog` listeyi ve üzerine yazılacakları gösterir → `start_upload(requests, acl)` → ilk `queued` olayları döner.
3. `transfer` olayları `transfers.map`'i günceller; `done` olan yükleme mevcut klasördeyse liste 600 ms debounce ile yenilenir.

## Yapılandırma ve günlük

- `~/.s3manager/config.ini` — Python sürümüyle aynı dosya ve bölümler; yeni alan: `[digitalocean] path_style`.
- `~/.s3manager/app.log` — `tauri-plugin-log`, 2 MB'da döner; AWS SDK / hyper / rustls gürültüsü `warn` seviyesine indirilir.

## Testler

| Katman | Araç | Konum |
|--------|------|-------|
| Rust birim | `cargo test` | `#[cfg(test)] mod tests` (metadata, önek, encode, parça boyutu, path traversal, klasör genişletme) |
| Rust canlı S3 | `cargo test -- --ignored` + `S3M_IT_*` | `s3::live`, `transfers::live` — CI'da MinIO'ya karşı |
| Frontend tip | `svelte-check` | `pnpm check` |
