"""Crea dist/Aurora-<versión>-Linux.zip: lo necesario para instalar Aurora con instalar-fedora.sh.

    python herramientas/empaquetar_linux.py [carpeta]   (por defecto, dist; los tests usan una temporal)

Dentro hay una carpeta «Aurora» (unzip Aurora-x.y-Linux.zip && cd Aurora && bash instalar-fedora.sh).
"""
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from version import leer  # noqa: E402

INCLUIR = ["aurora", "recursos", "Aurora.pyw", "requirements.txt", "instalar-fedora.sh", "desinstalar-fedora.sh",
           "LICENSE", "README.md"]


def archivos():
    for nombre in INCLUIR:
        ruta = RAIZ / nombre
        if ruta.is_dir():
            yield from sorted(p for p in ruta.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        else:
            yield ruta


def main():
    version = leer()
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "dist"
    destino = carpeta / f"Aurora-{version}-Linux.zip"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for ruta in archivos():
            info = zipfile.ZipInfo.from_file(ruta, "Aurora/" + ruta.relative_to(RAIZ).as_posix())
            ejecutable = ruta.suffix == ".sh"
            info.external_attr = (0o100755 if ejecutable else 0o100644) << 16  # los .sh, ejecutables
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, ruta.read_bytes())
    print(destino)


if __name__ == "__main__":
    main()
