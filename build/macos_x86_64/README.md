# Intel macOS legacy build (PySide2 + PySide6 shim)

Bu klasör, **yalnızca release pipeline**'ında Intel Mac (`x86_64`) DMG üretimi için kullanılır.
Günlük geliştirme `PySide6` ile devam eder; `src/` dosyalarına dokunulmaz.

## Mimari

```
legacy_entry.py  →  sys.path'e PySide6 shim ekler  →  src/main.py (PySide6 importları)
                              ↓
                    build/macos_x86_64/PySide6/  (sahte PySide6 → PySide2)
```

| Bileşen | Açıklama |
|---------|----------|
| `PySide6/` | PySide2 üzerinde PySide6 API uyumluluk katmanı |
| `pyinstaller_hooks/` | PyInstaller no-op `hook-PySide6*` (yalnızca PySide2 Qt toplansın) |
| `legacy_entry.py` | `s3manager-macos-x86_64.spec` PyInstaller giriş noktası |
| `requirements-macos-x86_64.txt` | PySide2 (PySide6 yok), proje kökünde |

## Yamalanan API farkları

| Konu | PySide6 | PySide2 | Shim |
|------|---------|---------|------|
| `QShortcut` | `QtGui` | `QtWidgets` | `QtGui` shim'den export |
| `QKeySequence.StandardKey` | enum | düz sabitler | `StandardKey` alias |
| `QDialog.exec()` / `QApplication.exec()` / `QMenu.exec()` | `exec()` | `exec_()` | sınıfa `exec` alias |

## Release build (CI)

- Runner: `macos-15-intel`
- Python: 3.10
- `MACOSX_DEPLOYMENT_TARGET=10.13`
- Spec: `s3manager-macos-x86_64.spec`
- Çıktı: `dist/S3MANAGER-{version}-macos-x86_64.dmg`

## Manuel test (Intel Mac veya CI runner)

```bash
export MACOSX_DEPLOYMENT_TARGET=10.13
python3.10 -m venv venv-legacy
source venv-legacy/bin/activate
pip install -r requirements-macos-x86_64.txt -r requirements-dev.txt
SPEC=s3manager-macos-x86_64.spec bash scripts/build.sh
bash scripts/package-macos.sh 0.0.8
```

## Yeni PySide6 API kullanımı

`src/` içinde PySide6'ya özgü yeni bir API kullanırsanız, Intel release build kırılabilir.
Gerekirse `PySide6/QtGui.py` veya `PySide6/QtWidgets.py` içine yama ekleyin.
Release CI (`build-macos-x86_64`) hatayı tag sırasında yakalar.

## Minimum macOS

Intel DMG: **10.13 High Sierra** ve üzeri (PySide2 5.15 wheel etiketi: `macosx_10_13`).
