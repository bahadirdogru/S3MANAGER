<div align="center">

# S3MANAGER

**DigitalOcean Spaces ve diğer S3 destekli depolama servisleri için cross-platform masaüstü dosya yöneticisi**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/bahadirdogru/S3MANAGER?label=release)](https://github.com/bahadirdogru/S3MANAGER/releases)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/bahadirdogru/S3MANAGER/releases)

[Özellikler](#özellikler) · [Kurulum](#kurulum) · [Roadmap](#roadmap) · [Kullanım](#kullanım) · [Dağıtım](#dağıtım) · [Dökümantasyon](#dökümantasyon)

</div>

---

> **Doc Map** — Proje dökümantasyon rehberi
>
> | Dosya | Ne için okunur |
> |-------|----------------|
> | [README.md](README.md) | Kurulum, kullanım, proje tanıtımı (GitHub/GitLab anasayfa) |
> | [UI.md](UI.md) | Renk, font, widget, QSS tasarım standartları |
> | [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, veri akışı, threading (insan okuması) |
> | [LLM.md](LLM.md) | Güncel kod yapısı, dosya haritası, geliştirme kısıtları (LLM) |
> | [PROCESS.md](PROCESS.md) | Kronolojik değişiklik kayıtları (LLM changelog) |

## Hakkında

**S3MANAGER**, DigitalOcean Spaces üzerindeki dosyalarınızı yerel bir masaüstü uygulaması deneyimiyle yönetmenizi sağlar. Yükleme, indirme, paylaşım ve klasör yönetimi tek bir modern arayüzde bir araya gelir.

Bu proje [Bahadır Doğru](https://bahadirdogru.com) tarafından **S3MANAGER** adıyla geliştirilmiş ve **GPL-3.0** lisansı altında açık kaynak olarak yayınlanmaktadır.

## Özellikler

<table>
<tr>
<td width="50%" valign="top">

### 📁 Dosya Gezgini
- Klasör yapısıyla görüntüleme
- Sayfalı lazy loading
- Breadcrumb navigasyon
- Sütun sıralama, çoklu seçim
- Kopyala / taşı / yeniden adlandır (F2, Ctrl+C/X)
- Toolbar arama (prefix filtre)
- Sağ panel dosya önizleme (görsel, metin)

### ⬆️ Yükleme
- Dosya ve klasör yükleme
- Ana pencereye sürükle-bırak
- Private / Public ACL
- Otomatik Content-Type ve Content-Disposition (html, zip, css, js vb.)
- Multipart (>100 MB)
- Paralel yükleme (max 3)

</td>
<td width="50%" valign="top">

### ⬇️ İndirme & Paylaşım
- Tekli / çoklu indirme
- Klasör indirme
- 3 veya 7 gün presigned URL
- Panoya otomatik kopyalama

### 🎨 Modern UI
- PySide6 (Qt 6)
- WhatsApp-inspired dark/light theme
- Qt standart toolbar ikonları
- Transfer geçmişi paneli
- Detaylar: [UI.md](UI.md)

</td>
</tr>
</table>

### Ekran Görüntüsü

> 📷 Ekran görüntüsü yakında eklenecek.

<!-- docs/screenshots/main.png -->

## Gereksinimler

- Python 3.10+
- DigitalOcean Spaces hesabı ve erişim anahtarları

## Kurulum

### Kaynak koddan (geliştirme)

**Hızlı başlangıç** (Linux/macOS/Git Bash):

```bash
git clone https://github.com/bahadirdogru/S3MANAGER.git
cd S3MANAGER
./start.sh
```

`start.sh` venv oluşturur, bağımlılıkları kurar ve uygulamayı başlatır. Windows'ta Git Bash veya WSL kullanın.

**Manuel kurulum:**

```bash
git clone https://github.com/bahadirdogru/S3MANAGER.git
cd S3MANAGER
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
python src/main.py
```

İlk çalıştırmada **Bağlan** ile Key, Secret, Bölge, Endpoint ve Bucket girin. Bilgiler `~/.s3manager/config.ini` dosyasına kaydedilir.

> **Not:** Daha önce eski sürüm kullandıysanız `~/.pydamlaspace/` klasöründeki ayarlar ilk çalıştırmada otomatik olarak `~/.s3manager/` konumuna taşınır.

### Binary (son kullanıcı)

Python kurmadan kullanmak için [Releases](https://github.com/bahadirdogru/S3MANAGER/releases) sayfasından platformunuza uygun dosyayı indirin (aşağıdaki [Releases](#releases) bölümüne bakın).

## Roadmap

S3 uyumlu depolama (boto3) için önceliklendirilmiş geliştirme planı. Maddeler mevcut kod tabanındaki eksiklere göre sıralanmıştır; katkılar ve öneriler [Issues](https://github.com/bahadirdogru/S3MANAGER/issues) üzerinden değerlendirilir.

### Yakın vade — temel S3 işlemleri

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Çoklu bağlantı profili** | Birden fazla bucket/endpoint kaydı; hızlı geçiş | Planlandı |
| **Kimlik bilgisi güvenliği** | OS keyring veya şifreli credential depolama | Planlandı |

### Orta vade — üretkenlik ve görünürlük

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Nesne metadata paneli** | `Content-Type`, `Cache-Control`, özel `x-amz-meta-*` görüntüleme/düzenleme | Planlandı |
| **Yükleme devam ettirme** | Kesilen multipart upload'ların resume edilmesi | Planlandı |

### Geç vade — sonra

| Özellik | Açıklama | Not |
|---------|----------|-----|
| **Dosya önizleme (gelişmiş)** | PDF viewer, daha fazla format, düzenleme | Temel split-view önizleme eklendi; PDF ve gelişmiş tipler sonraya |

### Tamamlanan (v0.0.7+)

- **Yeniden adlandırma / taşıma / kopyalama** — context menu, toolbar, F2/Ctrl+C/Ctrl+X
- **Prefix arama ve filtre** — toolbar arama kutusu (mevcut klasör)
- **Sürükle-bırak yükleme** — ana pencereye dosya bırakma
- **Transfer geçmişi** — alt panelde yükleme/indirme kayıtları
- **Toolbar ikonları** — Qt standart ikon seti
- **Dosya önizleme (MVP)** — split-view sağ panel; görsel ve metin dosyaları

### Bilinçli olarak kapsam dışı (şimdilik)

- Tam IAM/STS yönetim konsolu
- Glacier / derin arşiv storage class geçişleri
- Sunucu tarafı şifreleme (SSE-KMS) yapılandırma sihirbazı

## Releases

En son sürüm: **[v0.0.7](https://github.com/bahadirdogru/S3MANAGER/releases/tag/v0.0.7)** — [GitHub Releases](https://github.com/bahadirdogru/S3MANAGER/releases) sayfasından indirebilirsiniz.

| Platform | Dosya |
|----------|-------|
| Windows | `S3MANAGER-0.0.7-windows-setup.exe` (NSIS installer) veya `S3MANAGER-0.0.7-windows-portable.zip` |
| macOS (Apple Silicon) | `S3MANAGER-0.0.7-macos-arm64.dmg` |
| Linux x86_64 | `S3MANAGER-0.0.7-linux-x86_64.tar.gz` veya `S3MANAGER-0.0.7-linux-x86_64.AppImage` |

Uygulama açılışında GitHub Releases üzerinden otomatik güncelleme kontrolü yapılır. **Yardım → Güncellemeleri Kontrol Et** ile manuel kontrol de mümkündür. Yeni sürüm bulunursa indirme sayfası tarayıcıda açılır.

> **Not:** Binary'ler kod imzalı değildir; Windows Defender / macOS Gatekeeper uyarısı verebilir.

### Geliştiriciler için release

```bash
# src/version.py sürümünü güncelle, commit et
git tag v0.0.7
git push origin main
git push origin v0.0.7
```

`v*.*.*` tag push edildiğinde GitHub Actions otomatik olarak Windows, macOS ve Linux'ta build alır ve [GitHub Release](https://github.com/bahadirdogru/S3MANAGER/releases) oluşturur.

## Dağıtım (yerel derleme)

PyInstaller **onedir** ile hedef platformda yerel derleme gerekir (cross-compile yok).

| Platform | Komut | Çıktı |
|----------|-------|-------|
| Windows | `.\scripts\package-windows.ps1 -Version 0.0.7` | NSIS installer + portable zip |
| macOS | `./scripts/package-macos.sh 0.0.7` | `.dmg` |
| Linux | `./scripts/package-linux.sh 0.0.7` | `.tar.gz` + `.AppImage` |
| Tümü (sadece build) | `.\scripts\build.ps1` / `./scripts/build.sh` | `dist/S3MANAGER/` |

Windows paketleme için [NSIS](https://nsis.sourceforge.io/) kurulu olmalıdır (`makensis` PATH'te veya Chocolatey ile `choco install nsis`). CI ortamında NSIS Chocolatey üzerinden kurulur. İkon üretimi: `python scripts/generate_icons.py` (Pillow gerekir).

`s3manager.spec` yalnızca QtWidgets için gerekli PySide6 modüllerini paketler (`collect_all` kullanılmaz). Script'ler venv oluşturur, `requirements.txt` + `requirements-dev.txt` kurar ve PyInstaller ile derler.

**Bilinen kısıtlar:** Windows Defender / macOS Gatekeeper imzasız binary uyarısı verebilir.

## Kullanım

### Bağlantı

1. **Bağlan** → kimlik bilgilerini girin (bağlantı doğrulanır)
2. Kayıtlı bilgiler varsa uygulama otomatik bağlanır

### Dosya gezgini

- Klasöre çift tıklayın; üstte breadcrumb ile gezinin (geri dönüşte liste önbelleği kullanılır)
- **← Geri**, **Yenile**, sütun başlığına tıklayarak sıralama
- Ctrl/Shift ile çoklu seçim; sağ tık menüsü

### Yükleme

1. **Yükle** → Dosya veya Klasör Seç (her seçim listeyi değiştirir)
2. Private/Public seçin → **Yüklemeyi Başlat**
3. İlerleme: yüzde, hız, multipart bilgisi

Dosya uzantısına göre **Content-Type** ve **Content-Disposition** otomatik atanır (ör. `.html` tarayıcıda açılır, `.zip` indirilir). Kurallar **Ayarlar → Yükleme Metadata...** veya yükleme dialogundaki **Ayarlar...** ile özelleştirilebilir (`~/.s3manager/config.ini` `[upload_metadata]`).

### İndirme

1. Dosya/klasör seçin → **İndir** veya sağ tık **Seçilenleri İndir**
2. Hedef klasörü seçin

### Paylaşım

1. Tek dosya seçin → **Paylaş** (3/7 gün seçimi) veya sağ tık menüsü
2. Link otomatik panoya kopyalanır

### Diğer

- Boş alana sağ tık → **Yeni Klasör**, **Dosya Yükle**
- Toolbar sağ üstteki **🌙/☀️** switch ile koyu/açık tema
- **Del** silme, **F5** yenile, **Ctrl+A** tümünü seç

## Loglama

`~/.s3manager/app.log`: RotatingFileHandler, 10MB, 5 yedek. Detaylar için [ARCHITECTURE.md](ARCHITECTURE.md).

## Konfigürasyon

`~/.s3manager/config.ini` — örnek: [config.example.ini](config.example.ini)

## Desteklenen bölgeler

`nyc3` · `sfo3` · `sgp1` · `ams3` · `fra1` · `blr1`

## Geliştirme

### Testler

```bash
pip install -r requirements-dev.txt
pytest                                    # tüm testler
pytest tests/unit -v                      # yalnızca unit
pytest --cov=src --cov-report=html        # HTML rapor → htmlcov/
./scripts/test.sh                         # venv + pytest (Git Bash)
```

Yapılandırma: [`pyproject.toml`](pyproject.toml). CI'da `ubuntu-latest` üzerinde `pytest` job'ı çalışır; build matrix yalnızca testler geçince başlar.

| Katman | Araç | Dizin |
|--------|------|-------|
| Unit | pytest | `tests/unit/` |
| Servis (S3 mock) | pytest + moto | `tests/services/` |

GUI (PySide6) testleri kapsam dışıdır.

## Geliştirme notu

Bu projenin kodlama sürecinde **LLM (Large Language Model)** araçları kullanılmıştır. Mimari kararlar, kod yapısı ve geliştirme kısıtları [LLM.md](LLM.md) dosyasında belgelenmiştir.

## Dökümantasyon

| Dosya | İçerik |
|-------|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari ve veri akışı |
| [UI.md](UI.md) | Tasarım sistemi |
| [LLM.md](LLM.md) | LLM geliştirme rehberi |
| [PROCESS.md](PROCESS.md) | Değişiklik geçmişi |

---

<div align="center">

## Yazar & Lisans

**S3MANAGER** — Copyright © 2026 [Bahadır Doğru](https://bahadirdogru.com)

Bu proje [GNU General Public License v3.0](LICENSE) altında açık kaynak olarak yayınlanmaktadır.

</div>
