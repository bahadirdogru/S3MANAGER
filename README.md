<div align="center">

# S3MANAGER

**DigitalOcean Spaces için cross-platform masaüstü dosya yöneticisi**

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-41CD52?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/)

[Özellikler](#özellikler) · [Kurulum](#kurulum) · [Kullanım](#kullanım) · [Dağıtım](#dağıtım) · [Dökümantasyon](#dökümantasyon)

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

### ⬆️ Yükleme
- Dosya ve klasör yükleme
- Private / Public ACL
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
- WhatsApp-inspired dark theme
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

```bash
git clone <repository-url>
cd S3MANAGER
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS
pip install -r requirements.txt
python src/main.py
```

İlk çalıştırmada **Bağlan** ile Key, Secret, Bölge, Endpoint ve Bucket girin. Bilgiler `~/.s3manager/config.ini` dosyasına kaydedilir.

> **Not:** Daha önce eski sürüm kullandıysanız `~/.pydamlaspace/` klasöründeki ayarlar ilk çalıştırmada otomatik olarak `~/.s3manager/` konumuna taşınır.

## Dağıtım

PyInstaller **onedir** ile hedef platformda yerel derleme gerekir (cross-compile yok).

| Platform | Komut | Çıktı |
|----------|-------|-------|
| Windows | `.\scripts\build.ps1` | `dist\S3MANAGER\` klasörü + `dist\S3MANAGER.zip` |
| Linux / macOS | `chmod +x scripts/build.sh && ./scripts/build.sh` | `dist/S3MANAGER/` klasörü + `dist/S3MANAGER.zip` |

Script'ler venv oluşturur, `requirements.txt` + `requirements-dev.txt` kurar ve `s3manager.spec` ile derler. Dağıtım için tüm `S3MANAGER/` klasörünü veya zip arşivini paylaşın; yalnızca exe/binary dosyası yeterli değildir (`_internal/` içindeki DLL ve kütüphaneler gerekir).

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

`~/.s3manager/app.log`: RotatingFileHandler, 10MB, 5 yedek. Detaylar için [ARCHITECTURE.md](ARCHITECTURE.md).

## Konfigürasyon

`~/.s3manager/config.ini` — örnek: [config.example.ini](config.example.ini)

## Desteklenen bölgeler

`nyc3` · `sfo3` · `sgp1` · `ams3` · `fra1` · `blr1`

## Geliştirme notu

Bu projenin kodlama sürecinde büyük ölçüde **LLM (Large Language Model)** araçları kullanılmıştır. Mimari kararlar, kod yapısı ve geliştirme kısıtları [LLM.md](LLM.md) dosyasında belgelenmiştir.

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
