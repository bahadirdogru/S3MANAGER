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
> **Bu dosya:** Tasarım sistemi — renk token'ları, bileşenler, yerleşim ve UX kuralları.

# Kullanıcı Arayüzü Standartları

## Tasarım ilkeleri

- **WhatsApp esinli:** koyu veya açık zemin, yeşil vurgular, yüksek kontrastlı metin.
- **Masaüstü uygulaması gibi davran:** sayfa kaydırmaz (yalnızca paneller kayar), arayüz metni seçilemez (`user-select: none`; input, textarea ve `data-selectable` hariç), sağ tık menüsü ve kısayollar her yerde.
- **Her zaman durum bilgisi:** yükleniyor iskeletleri, toast bildirimleri, durum çubuğu, transfer paneli.
- **Tutarlılık:** yalnızca shadcn-svelte bileşenleri ve tema token'ları; özel bileşenler bunların üzerine kurulur.

Yığın: **shadcn-svelte** (`vega` stili, `bits-ui` tabanlı), **Tailwind CSS 4**, **lucide** ikonları (`@lucide/svelte/icons/<ad>`), **Inter Variable** fontu, tema için **mode-watcher**.

## Renk paleti

Kaynak: `src/routes/layout.css` (`:root` = açık, `.dark` = koyu). Pazarlama sitesi (`docs/css/style.css`) aynı paleti kullanır; değişikliklerde iki dosyayı senkron tutun.

| Token | Açık | Koyu | Kullanım |
|-------|------|------|----------|
| `--background` | `#F0F2F5` | `#0B141A` | Pencere zemini |
| `--card` | `#FFFFFF` | `#151F26` | Araç çubuğu, paneller, durum çubuğu |
| `--popover` | `#FFFFFF` | `#1A252D` | Diyalog, menü, tooltip |
| `--muted` | `#F5F6F6` | `#243038` | Kart içi / tablo başlığı zemini |
| `--secondary`, `--accent` | `#E9EDEF` | `#2A3942` | İkincil buton, hover |
| `--foreground` | `#111B21` | `#E9EDEF` | Birincil metin |
| `--muted-foreground` | `#667781` | `#AEBAC1` | İkincil metin |
| `--border`, `--input` | `#D1D7DB` | `#3A4A54` | Kenarlık |
| `--primary`, `--ring` | `#00A884` | `#00A884` | Birincil buton, klasör ikonu, odak halkası |
| `--selected` | `#D9FDD3` | `#075E54` | Seçili tablo satırı |
| `--success` | `#25D366` | `#25D366` | Bağlı göstergesi, tamamlanan transfer |
| `--warning` | `#FFB800` | `#FFB800` | Herkese açık ACL, üzerine yazma uyarısı |
| `--destructive` | `#EA0038` | `#EA0038` | Silme, hata |

Tailwind sınıfları: `bg-background`, `bg-card`, `bg-muted/40`, `text-muted-foreground`, `bg-primary`, `text-primary`, `bg-selected`, `text-success`, `text-warning`, `text-destructive`, `border` …

### Tema kuralları

- Bileşenlerde **hex veya Tailwind palet rengi yazılmaz** (`bg-[#…]`, `bg-green-500` yok). Tek istisna: indirme oku `text-sky-500`.
- Yeni anlamsal renk gerekiyorsa `layout.css`'te hem `:root` hem `.dark` altına değişken + `@theme inline` içine `--color-<ad>` eklenir.
- Varsayılan tema **koyu**. Tercih `config.ini` `[appearance] theme`; `session.setTheme()` hem `mode-watcher`'ı hem dosyayı günceller.

## Tipografi

| Kullanım | Sınıf |
|----------|-------|
| Gövde, tablo satırı | `text-sm` (14 px) |
| İkincil bilgi, rozet, transfer satırı, durum çubuğu | `text-xs` (12 px) |
| Endpoint alt başlığı | `text-[11px]` |
| Diyalog başlığı | `Dialog.Title` varsayılanı |
| Kod, URL, ETag, günlük | `font-mono text-xs` |
| Sayılar (boyut, tarih, hız) | `tabular-nums` |

## Yerleşim

```
┌ Araç çubuğu (h-12, bg-card) ───────────────────────────────────────────────┐
│ ● bucket/endpoint │ Yükle  Klasör Yükle  Yeni Klasör  İndir  Sil   [Ara] ⧉ ☀ ⚙ ⏻ │
├ Yol çubuğu (h-10) ─────────────────────────────────────────────────────────┤
│ ← ⟳  root / klasör / alt                                                    │
├ İçerik: Resizable.PaneGroup ───────────────────────────┬───────────────────┤
│ FileTable (Ad · Boyut · Değiştirilme · Erişim)         │ PreviewPanel      │
│                                                        │ (açılıp kapanır)  │
├ TransferPanel (yalnızca transfer varsa; katlanır) ─────┴───────────────────┤
├ Durum çubuğu (h-7): n klasör, m dosya · seçim · işlem · sürüm ─────────────┤
```

- Pencere: 1280×820 varsayılan, en az 900×560.
- Önizleme paneli genişliği `autoSaveId="s3m-main"` ile hatırlanır.
- Araç çubuğu düğmeleri `variant="ghost" size="sm"`, etiket `xl` genişlikten itibaren görünür, her düğmede tooltip + kısayol.
- Tablo satırı `h-8`; `content-visibility: auto` ile binlerce satırda bile hızlı.

## Bileşen kuralları

| Durum | Bileşen |
|-------|---------|
| Basit metin girişi (yeni klasör, yeniden adlandır, hedef klasör) | `dialogs.prompt()` → `DialogHost` |
| Onay (silme, bağlantıyı kesme, multipart iptal) | `dialogs.confirm({ destructive: true })` → `AlertDialog` |
| Özellik diyaloğu | `Dialog.Root` + `ui` store durumu (`UploadDialog`, `ShareDialog`, `PropertiesDialog`, `SettingsDialog`) |
| Kısa geri bildirim | `toast.success / error / info / warning`; uzun işlemde `toast.loading` + aynı `id` ile güncelle |
| Satır menüsü | `ContextMenu` (FileTable) — seçim yoksa yalnızca klasör işlemleri |
| İlerleme | `Progress` (`h-1.5`) |
| Açık/kapalı ayar | `Switch` satırı: `flex justify-between rounded-md border p-3` |
| Yükleniyor | Liste için `Skeleton`, düğme içinde `Loader2Icon animate-spin` |

- Yıkıcı işlemler `variant="destructive"` ve onay ister; onay metni geri alınamazlığı söyler.
- Diyalog altbilgisi: solda `Vazgeç` (`variant="outline"`), sağda birincil işlem.
- Seçilebilir olması gereken her metin (hata mesajı, URL, metadata, günlük) `data-selectable` alır.

## İkonlar

Lucide, `@lucide/svelte/icons/<ad>` ile tek tek import edilir (ağaç sallama için).

| Öğe | İkon |
|-----|------|
| Klasör | `folder` (`text-primary`) |
| Görsel / kod / metin / arşiv / video / ses / diğer | `file-image`, `file-code`, `file-text`, `file-archive`, `file-video`, `file-audio`, `file` |
| ACL | `globe` (herkese açık, `text-warning`), `lock` (özel) |
| Transfer | `arrow-up` (yükleme, `text-primary`), `arrow-down` (indirme) |
| Durum | `check`, `circle-alert`, `ban` |

## UX kuralları

- **Navigasyon:** çift tık / Enter klasörü açar, dosyada özellikleri açar; Backspace ve Alt+← geri; breadcrumb her parçaya tıklanabilir.
- **Seçim:** tıklama tek seçim, Ctrl/⌘ ekle-çıkar, Shift aralık; sağ tık mevcut çoklu seçimi korur; boş alana tıklama seçimi bırakır.
- **Arama:** 300 ms debounce, sunucu tarafı önek; Esc temizler.
- **Yükleme:** seçim/bırakma önce `UploadDialog`'da listelenir; üzerine yazılacak dosyalar `text-warning` ile işaretlenir.
- **Kopyalama aynı klasöre:** `ad (kopya n).uzantı`.
- **Paylaşım:** link oluşturulur oluşturulmaz panoya kopyalanır ve toast gösterilir.
- **Transfer paneli:** yeni transferde açılır; aktifken toplam yüzde, bitince "Bitenleri temizle"; tamamlanan indirmede "Klasörde göster".
- **Hata gösterimi:** S3 hata kodu mesajda görünür (`Silme hatası: AccessDenied`); ayrıntı `app.log`'da.

## Klavye kısayolları

| Tuş | İşlem |
|-----|-------|
| F5 / Ctrl+R | Yenile |
| Del | Sil |
| F2 | Yeniden adlandır |
| Ctrl+A / Esc | Tümünü seç / seçimi bırak |
| Ctrl+C / Ctrl+X | Kopyala… / Taşı… |
| Ctrl+U | Dosya yükle |
| Ctrl+Shift+N | Yeni klasör |
| Ctrl+F | Aramaya odaklan |
| Enter | Aç / Özellikler |
| Backspace, Alt+← | Geri |

Kısayollar input'ta yazarken ve bir diyalog açıkken devre dışıdır.
