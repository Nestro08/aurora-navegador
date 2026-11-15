"""Las extensiones de Python solo se ejecutan con permiso y con el código que aprobaste."""
import json

import pytest

from aurora import extensiones as ext_mod
from aurora.comun import DATOS


@pytest.fixture
def carpeta(tmp_path, monkeypatch, app):
    c = tmp_path / "extensiones"
    monkeypatch.setattr(ext_mod, "CARPETA_EXT", c)
    (DATOS / "extensiones_aprobadas.json").unlink(missing_ok=True)
    return c


def crear_ext(carpeta, nombre, codigo, **manifest):
    d = carpeta / nombre
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.json").write_text(json.dumps({"nombre": nombre, "python": "extension.py", **manifest}))
    (d / "extension.py").write_text(codigo)
    return d


CODIGO = "def activar(aurora):\n    aurora.comando('Hola', lambda: None)\n"


def nombres_comandos(g):
    return [c[1] for c in g.comandos]


def test_ejemplos_intactos_se_aprueban_solos(carpeta):
    g = ext_mod.GestorExtensiones()
    por_id = {e.id: e for e in g.lista}
    assert not por_id["copiar-markdown"].sin_permiso
    assert "Copiar enlace en Markdown" in nombres_comandos(g)


def test_python_nueva_no_se_ejecuta_sin_permiso(carpeta):
    carpeta.mkdir()
    crear_ext(carpeta, "mia", CODIGO)
    g = ext_mod.GestorExtensiones()
    e = next(x for x in g.lista if x.id == "mia")
    assert e.sin_permiso and not g.activa(e) and "Hola" not in nombres_comandos(g)
    with pytest.raises(PermissionError):
        g.cambiar(e, True)
    g.aprobar(e)
    g.cambiar(e, True)
    assert "Hola" in nombres_comandos(g)


def test_codigo_cambiado_pide_permiso_otra_vez(carpeta):
    carpeta.mkdir()
    d = crear_ext(carpeta, "mia", CODIGO)
    g = ext_mod.GestorExtensiones()
    e = next(x for x in g.lista if x.id == "mia")
    g.aprobar(e)
    g.recargar()
    assert not next(x for x in g.lista if x.id == "mia").sin_permiso
    (d / "extension.py").write_text(CODIGO + "# cambiado\n")
    g.recargar()
    assert next(x for x in g.lista if x.id == "mia").sin_permiso


@pytest.mark.parametrize("campo", ["js", "css"])
def test_rutas_fuera_de_la_carpeta(carpeta, campo):
    carpeta.mkdir()
    d = carpeta / "mala"
    d.mkdir()
    (d / "manifest.json").write_text(json.dumps({"nombre": "mala", campo: ["../../secreto.txt"]}))
    g = ext_mod.GestorExtensiones()
    e = next(x for x in g.lista if x.id == "mala")
    assert "fuera de la carpeta" in e.error
