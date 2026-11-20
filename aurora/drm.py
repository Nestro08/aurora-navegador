"""Contenido protegido (Netflix, Spotify, Disney+…): el módulo Widevine de un navegador ya instalado.

Widevine es de Google y no se puede incluir en Aurora, pero cualquier Chrome, Chromium, Edge, Brave o Vivaldi
instalado trae uno. Aurora busca el más reciente compatible y se lo indica al motor (--widevine-path).
"""
import json
import os
import sys
from pathlib import Path

INTERFACES = {"10", "11"}  # versiones de la interfaz CDM que entiende el Chromium de Qt 6


def _candidatos():
    casa = Path.home()
    if sys.platform == "win32":
        prog = [Path(os.environ.get(v, "")) for v in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        res = []
        for base in prog:
            for nombre, sub in (("Google Chrome", "Google/Chrome/Application"), ("Microsoft Edge", "Microsoft/Edge/Application")):
                res += [(nombre, d) for d in (base / sub).glob("*/WidevineCdm")]
        return res, "_platform_specific/win_x64/widevinecdm.dll"
    res = [("Google Chrome", Path("/opt/google/chrome/WidevineCdm")),
           ("Microsoft Edge", Path("/opt/microsoft/msedge/WidevineCdm")),
           ("Vivaldi", Path("/opt/vivaldi/WidevineCdm")),
           ("Chromium", Path("/usr/lib64/chromium-browser/WidevineCdm")),
           ("Chromium", Path("/usr/lib/chromium/WidevineCdm"))]
    for nombre, carpeta in (("Google Chrome", ".config/google-chrome"), ("Chromium", ".config/chromium"),
                            ("Brave", ".config/BraveSoftware/Brave-Browser")):
        res += [(nombre, d) for d in (casa / carpeta / "WidevineCdm").glob("*") if d.is_dir()]
    return res, "_platform_specific/linux_x64/libwidevinecdm.so"


def _version(texto):
    return tuple(int(x) for x in texto.split(".") if x.isdigit())


def buscar():
    """→ {"ruta", "version", "navegador"} del Widevine más reciente y compatible, o None."""
    candidatos, relativa = _candidatos()
    mejores = []
    for navegador, carpeta in candidatos:
        lib = carpeta / relativa
        try:
            manifiesto = json.loads((carpeta / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        interfaces = set(str(manifiesto.get("x-cdm-interface-versions", "")).split(","))
        if lib.is_file() and interfaces & INTERFACES:
            mejores.append({"ruta": str(lib), "version": str(manifiesto.get("version", "")), "navegador": navegador})
    return max(mejores, key=lambda m: _version(m["version"]), default=None)


def activar():
    """Indica al motor dónde está Widevine. Hay que llamarlo antes de crear la QApplication."""
    w = buscar()
    if w and " " not in w["ruta"]:  # en Windows (rutas con espacios) el propio Qt busca el de Chrome
        actuales = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
        if "--widevine-path" not in actuales:
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = f"{actuales} --widevine-path={w['ruta']}".strip()
    return w
