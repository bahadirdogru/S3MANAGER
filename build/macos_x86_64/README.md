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

## PySide6 kurulumu (önemli)

Intel build (`scripts/build.sh` + `S3MANAGER_LEGACY_MACOS=1`) **`requirements-dev.txt` kurmaz** — o dosya `-r requirements.txt` ile PySide6 çeker. Venv'e gerçek PySide6 kurulursa PyInstaller hem PySide2 hem PySide6 runtime hook'unu paketler ve uygulama şu hatayla açılmaz:

```
RuntimeError: Cannot execute run-time hook for 'PySide6' because run-time hook for 'PySide2' has been run before
```

Legacy build yalnızca `requirements-macos-x86_64.txt` + `pyinstaller` kurar. Build sonrası `scripts/verify-macos-x86_64-bundle.sh` gerçek PySide6/Qt6 binary'lerinin bundle'a girmediğini doğrular.

## Yamalanan API farkları

| Konu | PySide6 | PySide2 | Shim |
|------|---------|---------|------|
| `QShortcut` | `QtGui` | `QtWidgets` | `QtGui` shim'den export |
| `QKeySequence.StandardKey` | enum | düz sabitler | `StandardKey` alias |
| `QDialog.exec()` / `QApplication.exec()` / `QMenu.exec()` | `exec()` | `exec_()` | sınıfa `exec` alias |

## Release build (CI)

- Runner: `macos-15-intel`
- Python: **python.org 3.10.11** (`scripts/setup-macos-legacy-python.sh`) — macOS 10.13+ uyumlu; GitHub `setup-python` kullanılmaz
- `libintl.8.dylib`: Homebrew yerine `scripts/build-macos-legacy-libintl.sh` ile 10.13 hedefli derleme (`fix-macos-legacy-dylibs.sh`)
- `MACOSX_DEPLOYMENT_TARGET=10.13`
- Spec: `s3manager-macos-x86_64.spec`
- Çıktı: `dist/S3MANAGER-{version}-macos-x86_64.dmg`
<<<<<<< Updated upstream
- Build sonrası: `scripts/verify-macos-legacy-binary.sh` (LC_BUILD_VERSION kontrolü), `scripts/verify-macos-x86_64-bundle.sh` (PySide2-only bundle)
=======
- Build sonrası: `fix-macos-legacy-dylibs.sh` + `verify-macos-legacy-binary.sh` (LC_DYLD_CHAINED_FIXUPS / minos kontrolü)
>>>>>>> Stashed changes

## Manuel test (Intel Mac veya CI runner)

```bash
export MACOSX_DEPLOYMENT_TARGET=10.13
export S3MANAGER_LEGACY_MACOS=1
bash scripts/setup-macos-legacy-python.sh
bash scripts/package-macos.sh 0.0.8
```

## Yeni PySide6 API kullanımı

`src/` içinde PySide6'ya özgü yeni bir API kullanırsanız, Intel release build kırılabilir.
Gerekirse `PySide6/QtGui.py` veya `PySide6/QtWidgets.py` içine yama ekleyin.
Release CI (`build-macos-x86_64`) hatayı tag sırasında yakalar.

## Minimum macOS

Intel DMG: **10.13 High Sierra** ve üzeri (PySide2 5.15 wheel etiketi: `macosx_10_13`).
