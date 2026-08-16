> **Doc Map** — Proje dökümantasyon rehberi
>
> | Dosya | Ne için okunur |
> |-------|----------------|
> | [README.md](README.md) | Kurulum, kullanım, proje tanıtımı (GitHub/GitLab anasayfa) |
> | [docs/](docs/) | Tanıtım web sitesi ([GitHub Pages](https://bahadirdogru.github.io/S3MANAGER/)) |
> | [UI.md](UI.md) | Renk, font, widget, QSS tasarım standartları |
> | [ARCHITECTURE.md](ARCHITECTURE.md) | Mimari katmanlar, veri akışı, threading (insan okuması) |
> | [LLM.md](LLM.md) | Güncel kod yapısı, dosya haritası, geliştirme kısıtları (LLM) |
> | [PROCESS.md](PROCESS.md) | Kronolojik değişiklik kayıtları (LLM changelog) |
>
> **Bu dosya:** Tasarım sistemi — renk, font, widget, QSS ve UX kuralları.

# Kullanıcı Arayüzü Standartları ve Stil Yönergeleri

## Tasarım Prensipleri

### Genel Yaklaşım - WhatsApp Inspired (PySide6/Qt 6)

- **Modern ve Minimal**: Temiz, sade, zarif tasarım
- **WhatsApp Aesthetic**: Koyu veya açık arka plan, yeşil vurgular, yüksek kontrast metin
- **Native Performance**: Qt 6 ile GPU hızlandırmalı rendering
- **Kullanıcı Dostu**: Sezgisel navigasyon ve işlemler
- **Bilgilendirici**: Kullanıcıya her zaman durum bilgisi
- **Tutarlı**: Tüm ekranlarda aynı stil ve davranış
- **Elegant Spacing**: Generous padding ve margin'ler
- **Subtle Effects**: Yumuşak gölgeler ve hover efektleri

## Renk Paleti - WhatsApp Inspired (QSS)

Kaynak: `src/ui/qt/styles.py` — `ThemePalette`, `build_stylesheet()`, `apply_app_theme()`.

Pazarlama sitesi (`docs/css/style.css`) aynı WhatsApp-inspired paleti CSS custom properties ile kullanır; renk değişikliklerinde her iki dosyayı senkron tutun.

### Qt Style Sheets (QSS) Tema

- **Appearance Mode**: Dark (varsayılan) veya Light — toolbar `ThemeSwitch` (🌙/☀️) ile geçiş; tercih `~/.s3manager/config.ini` `[appearance] theme`
- **QSS Theme**: WhatsApp-inspired palet; yeşil vurgular her iki modda aynı
- **Semantik Renkler**:
  - Başarı: `#25D366` (`WA_SUCCESS`)
  - Hata: `#EA0038` (`WA_ERROR`)
  - Uyarı: `#FFB800` (`WA_WARNING`)
  - Birincil vurgu: `#00A884` (`WA_GREEN`)
  - Parlak vurgu: `#25D366` (`WA_GREEN_BRIGHT`)

### Widget Renkleri (Dark)

- **Primary Buttons**: `#00A884` (`WA_GREEN`)
- **Secondary Buttons**: `#2A3942` (`WA_BG_HOVER`)
- **Selected Items**: `#075E54` (`WA_GREEN_DARK`)
- **Background (ana pencere)**: `#0B141A`
- **Panel Background**: `#151F26`
- **Dialog Background**: `#1A252D`
- **Elevated / Kart**: `#243038`
- **Border**: `#3A4A54`
- **Border Subtle**: `#2A3942`
- **Text Primary**: `#E9EDEF`
- **Text Secondary**: `#AEBAC1`
- **Text Muted**: `#A0ADB4`

### Widget Renkleri (Light)

- **Background (ana pencere)**: `#F0F2F5`
- **Panel / Dialog**: `#FFFFFF`
- **Elevated / Kart**: `#F5F6F6`
- **Hover**: `#E9EDEF`
- **Text Primary**: `#111B21`
- **Text Secondary**: `#667781`
- **Text Muted**: `#8696A0`
- **Border**: `#D1D7DB`
- **Border Subtle**: `#E9EDEF`

### Tema tutarlılığı kuralları

- Tüm arka plan ve metin renkleri `ThemePalette` üzerinden `build_stylesheet()` ile uygulanır; widget’larda hardcode hex kullanılmaz (semantik `WA_ERROR` / `WA_SUCCESS` istisna).
- Yeni bileşen: `objectName` ata → kural ekle [`styles.py`](src/ui/qt/styles.py).
- Zorunlu global kurallar: `QScrollArea::viewport`, `QLineEdit:read-only`, genel `QTextEdit` / `QPlainTextEdit` fallback.
- Kartlar: `QFrame#FormFrame` → `bg_panel` + `border_subtle` (light/dark palet değişkenleri).
- Dialog tipografi: `DialogTitle`, `DialogTitleLarge`, `DialogSubtitle`, `UploadPhaseStatus`, `DialogSummaryResult`, `StatusSuccess`, `StatusError`.
- Tema geçişi: `apply_app_theme()` → `app.setStyleSheet` + `_repolish_top_levels()` + açık `ElevatedDialog` gölge güncelleme (`update_dialog_elevation`).
- **İstisna:** `QMessageBox` native Windows/macOS görünümü — tema ile tam uyum beklenmez.

**Manuel test matrisi (Dark + Light):** ana liste/önizleme, Ayarlar (5 sekme), Bağlan, Yükle/İndir (3 faz), Paylaş/Hedef yol; dialog açıkken toolbar tema switch.

### ThemeSwitch (toolbar satır 1, sağ uç)

Kaynak: `src/ui/qt/theme_switch.py` — `ConnectionIndicator` yanında.

| Özellik | Değer |
|---------|-------|
| Boyut | 64×32 px |
| objectName | `ThemeSwitch` |
| Thumb | `ThemeSwitchThumb` (28×24 px, yeşil pill) |
| İkonlar | `ThemeSwitchIcon` — sol 🌙 (koyu), sağ ☀️ (açık) |
| Davranış | Sol/sağ yarı tıklama; `theme_changed` signal |

### ConnectionIndicator (toolbar satır 1)

Kaynak: `src/ui/qt/connection_indicator.py` — tema switch solunda.

| Özellik | Değer |
|---------|-------|
| objectName | `ConnectionIndicator`, alt nokta `ConnectionIndicatorDot` |
| Yeşil | Bağlı (`connectionState=connected`) |
| Kırmızı | Bağlı değil / hata (`disconnected`) |
| Sarı | Bağlanıyor (`connecting`, isteğe bağlı) |
| Hover | Tooltip (bucket, bölge, endpoint) |
| Tıklama | Bağlan dialogu |

### İki satır Toolbar (`ToolbarFrame`)

`QMenuBar` kaldırıldı; tüm üst navigasyon tek `ToolbarFrame` içinde:

```
Satır 1: [Bağlan][Yükle]…[Yeniden Adlandır]  stretch  [Ayarlar][●][ThemeSwitch]
Satır 2: [Breadcrumb …]  [SearchEdit — kalan genişlik]  [← Geri]
```

| objectName | Bileşen |
|------------|---------|
| `ToolbarButton` | Satır 1 aksiyon `QPushButton` (Ayarlar dahil) |
| `ToolbarBreadcrumbHost` | Satır 2 breadcrumb konteyneri |
| `SearchEdit` | Arama — kalan tüm genişlik; breadcrumb uzadığında küçülür (min ~120px) |
| `SecondaryButton` | Geri butonu |

### Ayarlar dialogu (`SettingsDialog`)

Toolbar **Ayarlar** butonu → modal `QDialog#ElevatedDialog` (~640×520), `QTabWidget#SettingsTabWidget`:

| Sekme | İçerik |
|-------|--------|
| Bağlantı | Config yolu, bucket/bölge/endpoint, maskeli key/secret, güvenlik notu; Bağlantıyı düzenle → `LoginDialog`; Config klasörünü aç |
| Yükleme Metadata | `UploadMetadataPanel` — otomatik Content-Type / Disposition / Cache-Control kuralları |
| Görünüm | Koyu / Açık tema; önizleme anında; Kaydet ile persist; toolbar `ThemeSwitch` ile çift yönlü senkron |
| Günlük | `app.log` yolu, `QPlainTextEdit#LogViewer` (son ~400 satır), Yenile / klasör aç / panoya kopyala |
| Yardım | Sürüm, GitHub Releases, güncelleme kontrolü, GPL-3.0 notu |

Alt: **Kaydet** / **İptal** — metadata ve görünüm değişiklikleri Kaydet ile `config.ini`'ye yazılır.

Eski toolbar **Yardım** menüsü ve **Metadata** butonu kaldırıldı; işlevleri bu dialoga taşındı.

### Katman Hiyerarşisi (derinlik)

Ana pencere (en koyu) → Dialog (`WA_BG_DIALOG` + border + `apply_dialog_elevation()` gölge) → Kart (`UploadProgressCard`, `FormFrame`).

- `QDialog#ElevatedDialog` — login, upload, share
- `QWidget#UploadProgressCard` — dosya başına progress kartı
- `QScrollArea#UploadScroll` — upload listesi alanı
- `QLabel#ProgressMeta` — boyut, hız, durum metinleri (secondary kontrast)

## Tipografi

### Font Boyutları

- **Başlıklar**: 22pt, semibold (SF Pro Display style)
- **Alt Başlıklar**: 17pt, semibold
- **Normal Metin**: 15pt, regular
- **Küçük Metin**: 13pt, regular
- **Status Metinleri**: 13pt, regular
- **Caption**: 11pt, regular

### Font Kullanımı (QSS)

```css
/* Başlık */
QLabel#Title {
    font-size: 22px;
    font-weight: bold;
}

/* Alt başlık */
QLabel#Subtitle {
    font-size: 17px;
    font-weight: bold;
}

/* Normal metin */
QLabel {
    font-size: 15px;
}

/* Küçük metin */
QLabel#Small {
    font-size: 13px;
}

/* Caption */
QLabel#Caption {
    font-size: 11px;
}
```

## Widget Standartları - PySide6/Qt

### Butonlar (QPushButton)

**Boyutlar**:
- Standart: `width=130, height=32`
- Büyük: `width=200, height=36`
- Küçük: `width=90, height=28`
- Compact: `width=70, height=24`

**Stiller** (QSS):
```css
QPushButton {
    background-color: #00A884;
    color: white;
    border-radius: 6px;
    padding: 6px 15px;
    font-size: 13px;
    font-weight: bold;
    border: none;
}

QPushButton:hover {
    background-color: #06CF9C;
}

QPushButton:disabled {
    background-color: #2A3942;
    color: #8696A0;
}

QPushButton#SecondaryButton {
    background-color: #2A3942;
    color: #E9EDEF;
}

QPushButton#SecondaryButton:hover {
    background-color: #2A3942;
}

QPushButton#BreadcrumbButton {
    background-color: transparent;
    color: #25D366;
    border: none;
    padding: 2px 6px;
    font-weight: normal;
}
```

### Giriş Alanları (QLineEdit)

**Boyutlar**:
- Standart: `width=300, height=36`
- Geniş: `setMinimumWidth(400)`

**QSS Stil**:
```css
QLineEdit {
    background-color: #202C33;
    color: #E9EDEF;
    border: 1px solid #2A3942;
    border-radius: 6px;
    padding: 8px;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #00A884;
}
```

**Özel Durumlar**:
- Şifre alanları: `setEchoMode(QLineEdit.Password)`

### Açılır Menüler (QComboBox)

**QSS Stil**:
```css
QComboBox {
    background-color: #202C33;
    color: #E9EDEF;
    border: 1px solid #2A3942;
    border-radius: 6px;
    padding: 8px;
    font-size: 14px;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #202C33;
    color: #E9EDEF;
    selection-background-color: #075E54;
}
```

### Çerçeveler (QFrame)

**Padding**:
- Standart: `setContentsMargins(24, 16, 24, 16)`
- Kompakt: `setContentsMargins(12, 8, 12, 8)`
- Geniş: `setContentsMargins(32, 24, 32, 24)`

**QSS Stil**:
```css
QFrame#FormFrame {
    background-color: #202C33;
    border-radius: 12px;
}

QFrame#ToolbarFrame {
    background-color: #111B21;
    border-bottom: 1px solid #2A3942;
}

QFrame#BreadcrumbFrame {
    background-color: #111B21;
    border-bottom: 1px solid #2A3942;
}
```

### Dosya Listesi (QTreeView)

**QSS Stil**:
```css
QTreeView {
    background-color: #0B141A;
    color: #E9EDEF;
    border: none;
    outline: none;
}

QTreeView::item {
    height: 38px;
    border-bottom: 1px solid #111B21;
}

QTreeView::item:selected {
    background-color: #075E54;
    color: #FFFFFF;
}

QTreeView::item:hover {
    background-color: #2A3942;
}

QHeaderView::section {
    background-color: #202C33;
    color: #E9EDEF;
    padding: 8px 5px;
    border: none;
    border-bottom: 2px solid #075E54;
    font-weight: bold;
}
```

## Layout Standartları - Qt

### Pencere Boyutları

- **Ana Pencere**: `1100x750`
- **Dialog'lar**: 
  - Login: `520x520`
  - Upload: `720x640`
  - Download: `720x640`
  - Share: `420x240`

### Padding ve Spacing (Qt Layouts)

- **Widget'lar arası**: `setSpacing(8-12)`
- **Bölümler arası**: `setSpacing(24)`
- **Form elemanları**: `setContentsMargins(16, 12, 16, 12)`
- **List items**: `setSpacing(4)`

### Layout Types

- **Form'lar**: `QVBoxLayout`, `QHBoxLayout` (düzenli hizalama için)
- **Grid'ler**: `QGridLayout` (tablo benzeri yapılar için)
- **Scroll Areas**: `QScrollArea` (uzun içerik için)

## İkonlar

### Dosya Türü İkonları (Qt Standard Icons)

- 📁 Klasör: `QStyle.SP_DirIcon`
- 📄 Dosya: `QStyle.SP_FileIcon`

### Aksiyon İkonları (Emoji)

- 🔌 Bağlan
- 📤 Yükle
- 🔄 Yenile
- 🔗 Paylaş
- 📥 İndir
- 🔒 Private
- 🔓 Public
- ← Geri
- ✓ Başarılı
- ✗ Hata

## Kullanıcı Deneyimi Kuralları

### Geri Bildirim (Qt)

1. **Her Aksiyon İçin**:
   - Başarı: `QMessageBox.information()`
   - Hata: `QMessageBox.critical()`
   - Bilgi: `QMessageBox.information()`

2. **Progress Gösterimi**:
   - Upload işlemleri için `QProgressBar` ve detaylı bilgi (yüzde, yüklenen boyut, hız MB/s)
   - Genel ilerleme çubuğu: tüm dosyaların byte toplamına göre ağırlıklı yüzde
   - Büyük dosyalarda multipart bilgisi (part sayısı / tamamlanan)
   - Status mesajları (upload_service callback zincirinde deadlock düzeltildi; büyük dosyalarda da güncellenir)
   - Yeni dosya/klasör seçiminde progress alanı temizlenir; sadece seçilen dosyalar yüklenir (liste extend değil replace)

### Upload Dialog (`UploadDialog`)

Üç fazlı akış (`QStackedWidget`):

1. **Seçim** — `DropZoneFrame` (sürükle-bırak + Dosya/Klasör Seç), `UploadFileList` (liste veya klasör ağacı), özet satırı (adet · boyut · ACL), ACL radio
2. **Yükleme** — genel progress bar, dosya başına `UploadProgressBar`, İptal / Kapat
3. **Özet** — başarı/hata sayısı veya iptal mesajı; Yeni Yükleme ile Faz 1'e dönüş

- Klasör modunda `QTreeWidget` ile relative path önizlemesi (max 200 dosya + truncate uyarısı)
- Tekil silme: liste satırındaki ✕ veya ağaç sütunundaki ✕
- İptal: `cancel_requested` → worker interruption + `UploadService` yeniden oluşturma
- Dialog boyutu: `720x640`, non-blocking `show()`

### Download Dialog (`DownloadDialog`)

Upload ile simetrik üç fazlı akış:

1. **Onay** — seçili uzak öğe listesi (`DownloadItemList`), hedef klasör seçimi, özet satırı (adet · boyut · hedef)
2. **İndirme** — başlık satırında toplam hız, genel progress bar, dosya başına `UploadProgressBar`, İptal / Kapat
3. **Özet** — başarı/hata/iptal sayısı; Kapat ile dialog kapanır (yeni indirme ana pencereden)

- Öğeler ana pencereden seçilir; dialog `show_download()` ile açılır
- Klasör seçiminde iç dosyalar `build_download_tasks()` ile genişletilir
- Paralel indirme: max 3 (`ParallelDownloadWorker`)
- İptal: `cancel_requested` → HTTP kesme + worker interruption
- Dialog boyutu: `720x640`, non-blocking `show()`

3. **Loading Durumları**:
   - \"Yükleniyor...\" status mesajı
   - Disable edilmiş butonlar: `setEnabled(False)`
   - Progress bar'lar

### Modal Dialog'lar (QDialog)

- **Centered**: `move(parent.geometry().center() - self.rect().center())`
- **Modal**: `setModal(True)` veya `exec()`
- **Parent**: `QDialog(parent)`
- **Kapatma**: Cancel butonu veya X

### Context Menüler (QMenu)

- Sağ tık ile açılır
- Dosya türüne göre farklı seçenekler
- `QMenu` ve `QAction` kullanımı

### Navigasyon

- **Breadcrumb**: Üst kısımda, path gösterimi
- **Geri Butonu**: Sol üstte, sadece root'ta değilken aktif
- **Çift Tık**: Klasöre girmek için (QTreeView double-click)

## Qt Model/View Architecture

### FileModel (QAbstractItemModel)

- **Virtual Scrolling**: Sadece görünen satırlar çizilir
- **Yüksek Performans**: Binlerce dosya ile %0 kayıp
- **Otomatik Güncelleme**: Model değişince view otomatik güncellenir

### QTreeView

- **Sütunlar**: İsim, Boyut, Tarih, İzin
- **Sıralama**: Header'a tıklayarak
- **Seçim**: Single selection mode

## Threading (QThread)

### Worker Threads

```python
class SpacesWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)
    
    def run(self):
        try:
            # Network işlemi
            result = self.spaces_client.list_objects()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### Signals/Slots

```python
# Worker oluştur
worker = SpacesWorker()
worker.finished.connect(self.on_list_finished)
worker.error.connect(self.on_error)
worker.start()

@Slot(dict)
def on_list_finished(self, result):
    # UI güncelleme
    self.file_model.set_items(result['items'])
```

## Hata Yönetimi UI (Qt)

### Hata Mesajları

```python
QMessageBox.critical(
    self,
    "Hata",
    "Bağlantı kurulamadı. Lütfen bilgilerinizi kontrol edin."
)
```

### Logging Entegrasyonu

Tüm UI işlemleri logger ile kaydedilir:

```python
from src.utils.logging_config import get_logger

logger = get_logger('main_window')

# UI işlemlerinde
logger.info("Upload başlatıldı")
logger.error("Upload hatası", exc_info=True)
logger.debug("Signal emit edildi")
```

### Validasyon

- **Real-time**: Input alanlarında
- **Hata Gösterimi**: Kırmızı label altında
- **Buton Durumu**: Geçersiz input'ta `setEnabled(False)`

## Tutarlılık Kontrol Listesi

- [x] Tüm butonlar aynı boyut standardında (QSS)
- [x] Tüm mesajlar Türkçe
- [x] Hata mesajları kırmızı
- [x] Başarı mesajları yeşil
- [x] Dialog'lar ortalanmış
- [x] Progress bar'lar tutarlı stil
- [x] İkonlar anlamlı ve tutarlı
- [x] Padding ve spacing standartlara uygun (Qt layouts)
- [x] Qt Model/View mimarisi kullanılıyor
- [x] QThread ile async işlemler
- [x] QSS ile tutarlı tema

## Görsel Özellikler (Qt ile)

### Visual Hierarchy

- **Clear Hierarchy**: Başlıklar, alt başlıklar, body text arasında net hiyerarşi
- **Visual Breathing Room**: Generous spacing, her element'in nefes alacak alanı
- **Subtle Separators**: İnce, yumuşak ayırıcılar
- **Rounded Corners**: Tüm köşeler yuvarlatılmış (`border-radius: 6-12px`)

### Interaction Design

- **Smooth Hover**: Yumuşak hover efektleri (QSS `:hover`)
- **Clear Feedback**: Her etkileşimde net geri bildirim (Signals/Slots)
- **Minimal Icons**: Sade, minimal ikon kullanımı (Qt Standard Icons)
- **Clean Typography**: Okunabilir, modern font kullanımı

### Color Usage

- **WhatsApp Palette**: `styles.py` içindeki `WA_*` sabitleri; inline stillerde de bunlar kullanılır
- **Green Accents**: Butonlar, breadcrumb, progress bar ve seçim vurgusu
- **High Contrast Text**: Sütun başlıkları ve durum metni açık renk (`#E9EDEF` / `#AEBAC1`)
- **Background Layers**: `WA_BG` → `WA_BG_PANEL` → `WA_BG_ELEVATED` derinlik katmanları

## Performans (Qt Avantajları)

- **GPU Rendering**: Qt 6 ile donanım hızlandırmalı çizim
- **Virtual Scrolling**: QAbstractItemModel ile sadece görünen satırlar
- **Native Look**: İşletim sisteminin native widget'ları
- **Smooth Animations**: Qt'nin built-in animasyon desteği

## Breadcrumb ve navigasyon

- Breadcrumb: `ToolbarFrame` 2. satırında `ToolbarBreadcrumbHost` içinde
- Segment butonları: `QPushButton#BreadcrumbButton` — şeffaf arka plan, `#25D366` metin
- Ayırıcı: `QLabel#BreadcrumbSep` — `#8696A0`
- Bağlantı durumu: `ConnectionIndicator` (yeşil/kırmızı nokta + tooltip); işlem mesajları tooltip üzerinden
- Geri butonu: 2. satır sağ; root'ta disabled

## Klavye kısayolları

- **F5** — Yenile
- **Del** — Seçilenleri sil
- **Ctrl+A** — Tümünü seç
- **Escape** — Seçimi bırak
