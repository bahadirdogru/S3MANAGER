# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — S3MANAGER onedir (Windows / Linux / macOS)."""
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

project_root = Path(SPECPATH)
icon_ico = project_root / "assets" / "icon.ico"
icon_icns = project_root / "assets" / "icon.icns"

block_cipher = None

datas = []
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "boto3",
    "botocore",
    "pyperclip",
    "packaging",
]

for package in ("PySide6",):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

hiddenimports += collect_submodules("botocore")
hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    [str(project_root / "src" / "main.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
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
    upx=True,
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
