"""Deja en dist/ todo lo que hay que subir a una Release de GitHub (lo ejecuta construir.bat al final).

    python herramientas/preparar_release.py

Crea (o recoge, si ya existe):
  • Aurora-Setup-<v>.exe               instalador de Windows (lo hace construir.bat con Inno Setup)
  • Aurora-<v>-Windows-portable.zip    la carpeta dist/Aurora comprimida (sin instalar)
  • Aurora-<v>-Linux.zip               para instalar-fedora.sh
  • SHA256SUMS.txt                     huellas: Aurora las comprueba antes de actualizarse
  • NOTAS-<v>.md                       texto para pegar en la descripción de la Release

Los nombres importan: Aurora busca exactamente estos archivos en la última Release para actualizarse sola.
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIST = RAIZ / "dist"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from version import leer, sincronizar  # noqa: E402


def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for trozo in iter(lambda: f.read(1024 * 1024), b""):
            h.update(trozo)
    return h.hexdigest()


def main():
    version = leer()
    sincronizar(version)
    DIST.mkdir(exist_ok=True)
    subirlos = []

    instalador = DIST / f"Aurora-Setup-{version}.exe"
    if instalador.exists():
        subirlos.append(instalador)
    else:
        print(f"⚠ No está {instalador.name}: créalo en Windows con construir.bat (necesita Inno Setup 6).")

    if (DIST / "Aurora" / "Aurora.exe").exists():
        # ojo: no usar with_suffix(), que tomaría «.0-Windows-portable» de «Aurora-4.0-…» como extensión
        portable = shutil.make_archive(str(DIST / f"Aurora-{version}-Windows-portable"), "zip", DIST, "Aurora")
        subirlos.append(Path(portable))

    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "empaquetar_linux.py")],
                       capture_output=True, text=True, check=True)
    subirlos.append(Path(r.stdout.strip()))

    sumas = DIST / "SHA256SUMS.txt"
    sumas.write_text("".join(f"{sha256(a)}  {a.name}\n" for a in subirlos), encoding="utf-8", newline="\n")
    subirlos.append(sumas)

    notas = DIST / f"NOTAS-{version}.md"
    notas.write_text(f"""## Novedades

- (escribe aquí lo nuevo, una línea por cambio empezando con «-»: Aurora enseña las tres primeras en el aviso)

## Descargar

| Sistema | Archivo |
|---|---|
| **Windows** | `Aurora-Setup-{version}.exe` (instalador) o `Aurora-{version}-Windows-portable.zip` (sin instalar) |
| **Linux (Fedora)** | `Aurora-{version}-Linux.zip` → descomprímelo y ejecuta `bash instalar-fedora.sh` |

Si ya tienes Aurora instalado, te avisará de esta versión y se actualizará con un clic.
`SHA256SUMS.txt` tiene las huellas de los archivos.
""", encoding="utf-8")

    print(f"\nRelease de Aurora {version}: sube a GitHub estos archivos de la carpeta dist:")
    for a in subirlos:
        print(f"   {a.name}  ({a.stat().st_size / 1048576:.1f} MB)")
    print(f"\nEtiqueta (tag): v{version}   ·   Título: Aurora {version}   ·   Descripción: {notas.name}")
    print("Pasos: https://github.com/Nestro08/aurora-navegador/releases/new")


if __name__ == "__main__":
    main()
