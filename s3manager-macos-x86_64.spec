# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — S3MANAGER Intel macOS (PySide2 + PySide6 shim, min macOS 10.13)."""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH)
shim_root = project_root / "build" / "macos_x86_64"
icon_ico = project_root / "assets" / "icon.ico"
icon_icns = project_root / "assets" / "icon.icns"

block_cipher = None

hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide2.QtCore",
    "PySide2.QtGui",
    "PySide2.QtWidgets",
    "shiboken2",
    "boto3",
    "botocore",
    "pyperclip",
    "packaging",
]

hiddenimports += collect_submodules("botocore")
hiddenimports = list(dict.fromkeys(hiddenimports))

_pyside2_excludes = [
    "PySide2.QtQml",
    "PySide2.QtQuick",
    "PySide2.Qt3DCore",
    "PySide2.Qt3DRender",
    "PySide2.QtWebEngine",
    "PySide2.QtWebEngineWidgets",
    "PySide2.QtMultimedia",
    "PySide2.QtCharts",
]

a = Analysis(
    [str(shim_root / "legacy_entry.py")],
    pathex=[str(project_root), str(shim_root)],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_pyside2_excludes,
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
