"""La versión de Aurora vive en aurora/__init__.py; este script la copia a los demás sitios.

    python herramientas/version.py          → muestra la versión y sincroniza los archivos
    python herramientas/version.py 4.1      → pone la versión 4.1 en todos los sitios

Archivos que actualiza: aurora/__init__.py, herramientas/version.txt (datos del .exe de Windows),
instalador/aurora.iss (instalador) y el título del README.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
INIT = RAIZ / "aurora" / "__init__.py"
RE_VERSION = re.compile(r"^\d+\.\d+(\.\d+)?$")


def leer():
    return re.search(r'__version__ = "([^"]+)"', INIT.read_text(encoding="utf-8")).group(1)


def _cambiar(ruta, patron, nuevo):
    texto = ruta.read_text(encoding="utf-8")
    cambiado, n = re.subn(patron, nuevo, texto, flags=re.M)
    if n == 0:
        raise SystemExit(f"No encuentro dónde poner la versión en {ruta.relative_to(RAIZ)}")
    if cambiado != texto:
        ruta.write_text(cambiado, encoding="utf-8", newline="\n")


def sincronizar(version):
    partes = [int(x) for x in version.split(".")] + [0, 0]
    cuatro = ", ".join(str(x) for x in partes[:3] + [0])
    larga = ".".join(str(x) for x in partes[:3])
    version_txt = RAIZ / "herramientas" / "version.txt"
    _cambiar(version_txt, r"filevers=\([^)]*\)", f"filevers=({cuatro})")
    _cambiar(version_txt, r"prodvers=\([^)]*\)", f"prodvers=({cuatro})")
    _cambiar(version_txt, r'StringStruct\("FileVersion", "[^"]*"\)', f'StringStruct("FileVersion", "{larga}")')
    _cambiar(version_txt, r'StringStruct\("ProductVersion", "[^"]*"\)', f'StringStruct("ProductVersion", "{larga}")')
    _cambiar(RAIZ / "instalador" / "aurora.iss", r'^  #define Version "[^"]*"', f'  #define Version "{version}"')
    _cambiar(RAIZ / "README.md", r"^# Aurora [\d.]+$", f"# Aurora {version}")


def main():
    if len(sys.argv) > 1:
        nueva = sys.argv[1].lstrip("v")
        if not RE_VERSION.match(nueva):
            raise SystemExit(f"Versión no válida: {nueva!r} (usa algo como 4.1 o 4.1.2)")
        _cambiar(INIT, r'^__version__ = "[^"]*"', f'__version__ = "{nueva}"')
    version = leer()
    sincronizar(version)
    print(version)


if __name__ == "__main__":
    main()
