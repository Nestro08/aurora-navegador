# -*- mode: python ; coding: utf-8 -*-
# Receta de PyInstaller para crear dist\Aurora\Aurora.exe   (uso: pyinstaller --noconfirm Aurora.spec)
# QtWebEngine necesita el modo "carpeta" (onedir): el .exe va acompañado de sus librerías.

a = Analysis(
    ["Aurora.pyw"],
    pathex=[],
    binaries=[],
    datas=[("recursos/aurora.png", "recursos"), ("LICENSE", ".")],
    hiddenimports=["PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtNetwork", "PyQt6.QtMultimedia",
                   "cryptography.fernet", "importlib.util"],
    excludes=["tkinter", "PyQt6.QtQuick3D", "PyQt6.QtBluetooth"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Aurora",
    icon="recursos/aurora.ico",
    console=False,
    version="herramientas/version.txt",
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Aurora")
