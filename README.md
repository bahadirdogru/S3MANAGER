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
> **Bu dosya:** GitHub/GitLab proje anasayfası — kurulum ve kullanım rehberi.

# pyDamlaSpace

DigitalOcean Spaces için cross-platform masaüstü dosya yönetim uygulaması.

## Özellikler

- **Dosya gezgini** — Spaces içeriğini klasör yapısıyla görüntüleme, sayfalı lazy loading
- **Yükleme** — Dosya/klasör, Private/Public ACL, multipart (>100MB), paralel yükleme (max 3)
- **İndirme** — Tek/çoklu dosya ve klasör indirme
- **Paylaşım** — 3 veya 7 gün geçerli presigned URL, panoya kopyalama
- **Yönetim** — Silme, toplu silme, klasör oluşturma, çoklu seçim
- **Modern UI** — PySide6, WhatsApp-inspired dark theme ([UI.md](UI.md))

## Gereksinimler

- Python 3.10+
- DigitalOcean Spaces hesabı ve erişim anahtarları

## Kurulum

```bash
git clone <repository-url>
cd pydamlaspace
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
python src/main.py
```

İlk çalıştırmada **Bağlan** ile Key, Secret, Bölge, Endpoint ve Bucket girin. Bilgiler `~/.pydamlaspace/config.ini` dosyasına kaydedilir.

## Dağıtım (tek klasör)

PyInstaller **onedir** ile hedef platformda yerel derleme gerekir (cross-compile yok).

| Platform | Komut | Çıktı |
|----------|-------|-------|
| Windows | `.\scripts\build.ps1` | `dist\pyDamlaSpace\` klasörü + `dist\pyDamlaSpace.zip` |
| Linux / macOS | `chmod +x scripts/build.sh && ./scripts/build.sh` | `dist/pyDamlaSpace/` klasörü + `dist/pyDamlaSpace.zip` |

Script'ler venv oluşturur, `requirements.txt` + `requirements-dev.txt` kurar ve `pydamlaspace.spec` ile derler. Dağıtım için tüm `pyDamlaSpace/` klasörünü veya zip arşivini paylaşın; yalnızca exe/binary dosyası yeterli değildir (`_internal/` içindeki DLL ve kütüphaneler gerekir).

**Bilinen kısıtlar:** Windows Defender / macOS Gatekeeper imzasız binary uyarısı verebilir.

## Kullanım

### Bağlantı

1. **Bağlan** → kimlik bilgilerini girin (bağlantı doğrulanır)
2. Kayıtlı bilgiler varsa uygulama otomatik bağlanır

### Dosya gezgini

- Klasöre çift tıklayın; üstte breadcrumb ile gezinin
- **← Geri**, **Yenile**, sütun başlığına tıklayarak sıralama
- Ctrl/Shift ile çoklu seçim; sağ tık menüsü

### Yükleme

1. **Yükle** → Dosya veya Klasör Seç (her seçim listeyi değiştirir)
2. Private/Public seçin → **Yüklemeyi Başlat**
3. İlerleme: yüzde, hız, multipart bilgisi

### İndirme

1. Dosya/klasör seçin → **İndir** veya sağ tık **Seçilenleri İndir**
2. Hedef klasörü seçin

### Paylaşım

1. Tek dosya seçin → **Paylaş** (3/7 gün seçimi) veya sağ tık menüsü
2. Link otomatik panoya kopyalanır

### Diğer

- Boş alana sağ tık → **Yeni Klasör**, **Dosya Yükle**
- **Del** silme, **F5** yenile, **Ctrl+A** tümünü seç

## Loglama

`~/.pydamlaspace/app.log`: RotatingFileHandler, 10MB, 5 yedek. Detaylar için [ARCHITECTURE.md](ARCHITECTURE.md).

## Konfigürasyon

`~/.pydamlaspace/config.ini` — örnek: `config.example.ini`

## Desteklenen bölgeler

nyc3, sfo3, sgp1, ams3, fra1, blr1

## Dökümantasyon

| Dosya | İçerik |
|-------|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari ve veri akışı |
| [UI.md](UI.md) | Tasarım sistemi |
| [LLM.md](LLM.md) | LLM geliştirme rehberi |
| [PROCESS.md](PROCESS.md) | Değişiklik geçmişi |

## Lisans

Özel kullanım.
