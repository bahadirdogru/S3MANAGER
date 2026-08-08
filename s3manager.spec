# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — S3MANAGER onedir (Windows / Linux / macOS)."""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH)
icon_ico = project_root / "assets" / "icon.ico"
icon_icns = project_root / "assets" / "icon.icns"

block_cipher = None

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "boto3",
    "botocore",
    "pyperclip",
    "packaging",
]

hiddenimports += collect_submodules("botocore")
hiddenimports = list(dict.fromkeys(hiddenimports))

# collect_all("PySide6") QML/Qt3D dahil tum modulleri toplar ve CI'da
# eksik QML plugin DLL hatalarina yol acar. QtWidgets icin yerlesik hook'lar yeterli.
_pyside6_excludes = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.QtBluetooth",
    "PySide6.QtWebEngine",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "PySide6.QtMultimedia",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtLocation",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
]

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_pyside6_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_icon = str(icon_ico) if icon_ico.exists() else None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="S3MANAGER",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="S3MANAGER",
)

if sys.platform == "darwin" and icon_icns.exists():
    app = BUNDLE(
        coll,
        name="S3MANAGER.app",
        icon=str(icon_icns),
        bundle_identifier="com.bahadirdogru.s3manager",
    )
