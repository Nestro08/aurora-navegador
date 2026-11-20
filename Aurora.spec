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
    excludes=["tkinter", "PyQt6.QtQuick3D", "PyQt6.QtBluetooth", "PyQt6.QtQuickWidgets", "PyQt6.QtWebEngineQuick",
              "PyQt6.QtDesigner", "PyQt6.QtSql", "PyQt6.QtTest", "PyQt6.QtHelp"],
    noarchive=False,
)
# Aurora no usa QML: fuera los plugins y estilos de QtQuick y lo que arrastran (Quick 3D, Quick Controls…: cientos
# de MB y rutas tan largas que Windows no las acepta). Qt6Quick y Qt6Qml se quedan: QtWebEngine los usa por dentro.
# De las traducciones de Chromium solo hacen falta español e inglés.
import re

SOBRA = re.compile(r"Qt6(Quick3D|QuickControls2|QuickDialogs2|QuickParticles|QuickEffects|QuickLayouts|"
                   r"QuickNativeStyle|QuickShapes|QuickTimeline|QuickVectorImage|MultimediaQuick|PositioningQuick|"
                   r"QuickTest|LabsAnimation|LabsFolderListModel|LabsQmlModels|LabsSettings|LabsSharedImage|"
                   r"LabsWavefrontMesh|ShaderTools|3D)", re.I)


def sirve(entrada):
    ruta = entrada[0].replace("\\", "/")
    nombre = ruta.rsplit("/", 1)[-1]
    if "/qml/" in "/" + ruta or SOBRA.match(nombre) or ".debug." in nombre:  # *.debug.pak: solo para depurar Qt
        return False
    if "/qtwebengine_locales/" in ruta and not nombre.startswith(("es", "en")):
        return False
    return True


a.binaries = [b for b in a.binaries if sirve(b)]
a.datas = [d for d in a.datas if sirve(d)]
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
