# No-op hook for PySide6 compatibility shim (real Qt: PySide2).
# Prevents PyInstaller from registering PySide6 as a Qt bindings package.

hiddenimports = []
binaries = []
datas = []
