"""Avisos de versión nueva y actualización desde GitHub Releases."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from aurora import __version__, actualizar
from aurora.actualizar import (Actualizador, archivo_para, como_se_instala, extraer_seguro, huella_de, mas_nueva,
                               tupla)

RAIZ = Path(__file__).resolve().parent.parent


def release(etiqueta, **extra):
    api = "https://api.github.com/repos/Nestro08/aurora-navegador/releases/assets/"
    return {"tag_name": etiqueta, "html_url": f"https://github.com/Nestro08/aurora-navegador/releases/tag/{etiqueta}",
            "body": "## Novedades\n- Permisos de cámara\n- Bloqueador ampliado\n", "draft": False, "prerelease": False,
            "assets": [{"name": f"Aurora-Setup-{etiqueta[1:]}.exe", "url": api + "1"},
                       {"name": f"Aurora-{etiqueta[1:]}-Linux.zip", "url": api + "2"},
                       {"name": "SHA256SUMS.txt", "url": api + "3"}], **extra}


def test_compara_versiones_como_numeros():
    assert tupla("v4.10.1") == (4, 10, 1, 0)
    assert mas_nueva("v4.10", "4.9") and mas_nueva("4.0.1", "4.0") and mas_nueva("v5", "4.99")
    assert not mas_nueva("v4.0", "4.0") and not mas_nueva("3.9", "4.0")


def test_elige_el_archivo_de_cada_sistema():
    r = release("v4.1")
    assert archivo_para(r, "windows")["name"] == "Aurora-Setup-4.1.exe"
    assert archivo_para(r, "linux")["name"] == "Aurora-4.1-Linux.zip"
    r["assets"][0]["url"] = "https://otra-web.example/a.exe"  # solo desde este repositorio de GitHub
    assert archivo_para(r, "windows") is None
    r["assets"][0]["url"] = "https://api.github.com/repos/otro/repo/releases/assets/1"
    assert archivo_para(r, "windows") is None


def test_lee_las_huellas_de_sha256sum():
    sumas = "a" * 64 + "  Aurora-Setup-4.1.exe\n" + "B" * 64 + " *Aurora-4.1-Linux.zip\n"
    assert huella_de(sumas, "Aurora-Setup-4.1.exe") == "a" * 64
    assert huella_de(sumas, "Aurora-4.1-Linux.zip") == "b" * 64
    assert huella_de(sumas, "otro.zip") is None and huella_de("basura", "Aurora-Setup-4.1.exe") is None


def test_desde_el_codigo_solo_avisa():
    assert como_se_instala() is None  # los tests corren desde el repositorio, no instalados


def test_respuesta_de_github(app, monkeypatch):
    datos = {}
    monkeypatch.setattr("aurora.temas.Apariencia.datos", classmethod(lambda cls: datos))
    a = Actualizador()
    recibidas = []
    a.disponible.connect(recibidas.append)
    assert a.procesar(json.dumps(release("v999.0")).encode())[0] == "nueva" and recibidas
    assert a.procesar(json.dumps(release("v" + __version__)).encode())[0] == "al_dia"
    assert a.procesar(json.dumps(release("v999.0", prerelease=True)).encode())[0] == "al_dia"
    assert a.procesar(b"no es json")[0] == "error"
    falsa = release("v999.0", html_url="https://malo.example/")
    assert a.procesar(json.dumps(falsa).encode())[0] == "error"
    datos["omitida"] = "v999.0"  # «Omitir»: no vuelve a avisar solo de esa versión, pero sí si lo buscas tú
    assert a.procesar(json.dumps(release("v999.0")).encode())[0] == "al_dia"
    assert a.procesar(json.dumps(release("v999.0")).encode(), manual=True)[0] == "nueva"


def test_zip_seguro(tmp_path):
    bueno = tmp_path / "bueno.zip"
    with zipfile.ZipFile(bueno, "w") as z:
        info = zipfile.ZipInfo("Aurora/instalar-fedora.sh")
        info.external_attr = 0o100755 << 16
        z.writestr(info, "echo hola")
        z.writestr("Aurora/aurora/app.py", "")
    carpeta = extraer_seguro(bueno, tmp_path / "dentro")
    assert (carpeta / "instalar-fedora.sh").is_file()
    malo = tmp_path / "malo.zip"
    with zipfile.ZipFile(malo, "w") as z:
        z.writestr("../../fuera.txt", "x")
        z.writestr("Aurora/instalar-fedora.sh", "")
    with pytest.raises(ValueError):
        extraer_seguro(malo, tmp_path / "dentro2")
    assert not (tmp_path / "fuera.txt").exists()


def test_paquete_de_linux_y_version(tmp_path):
    """El paquete de Linux de la Release trae lo necesario, con los .sh ejecutables."""
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "version.py")], capture_output=True, text=True)
    assert r.stdout.strip() == __version__
    # en una carpeta temporal: nunca en dist, donde puede estar el paquete de una Release a medio subir
    r = subprocess.run([sys.executable, str(RAIZ / "herramientas" / "empaquetar_linux.py"), str(tmp_path / "dist")],
                       capture_output=True, text=True, check=True)
    zip_ruta = Path(r.stdout.strip())
    assert zip_ruta.parent == tmp_path / "dist"
    with zipfile.ZipFile(zip_ruta) as z:
        nombres = set(z.namelist())
        assert {"Aurora/instalar-fedora.sh", "Aurora/Aurora.pyw", "Aurora/aurora/app.py", "Aurora/LICENSE",
                "Aurora/aurora/actualizar.py"} <= nombres
        assert not any("__pycache__" in n or "CLAUDE" in n or n.startswith("Aurora/tests") for n in nombres)
        assert (z.getinfo("Aurora/instalar-fedora.sh").external_attr >> 16) & 0o111
    carpeta = extraer_seguro(zip_ruta, tmp_path / "fuera")
    assert (carpeta / "aurora" / "__init__.py").read_text(encoding="utf-8").count(__version__)


def test_los_archivos_tienen_la_misma_version():
    assert f'#define Version "{__version__}"' in (RAIZ / "instalador" / "aurora.iss").read_text(encoding="utf-8-sig")
    assert f'"ProductVersion", "{".".join((__version__ + ".0.0").split(".")[:3])}"' in \
        (RAIZ / "herramientas" / "version.txt").read_text(encoding="utf-8")
    assert actualizar.REPO == "Nestro08/aurora-navegador"
