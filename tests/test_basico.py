"""Almacén, generador, contraseña maestra y cifrado local."""
import os
import stat
import string
import sys

import pytest

from aurora.comun import Almacen, AlmacenMemoria
from aurora.contrasenas import Contrasenas, cifrado_disponible, cifrar, descifrar
from aurora.seguridad import SIMBOLOS, Verificador, generar_contrasena


def test_almacen_escribe_privado_y_atomico(tmp_path):
    a = Almacen("prueba", {"x": 1}, tmp_path)
    a.datos["x"] = 2
    a.guardar()
    assert Almacen("prueba", {}, tmp_path).datos == {"x": 2}
    assert not list(tmp_path.glob("*.tmp"))
    if os.name == "posix":
        assert stat.S_IMODE(a.ruta.stat().st_mode) == 0o600


def test_guardar_luego_agrupa_y_se_vuelca(tmp_path, app):
    a = Almacen("diferido", [], tmp_path)
    a.datos.append(1)
    a.guardar_luego(60_000)
    a.datos.append(2)
    a.guardar_luego(60_000)
    assert not a.ruta.exists()
    Almacen.volcar_pendientes()
    assert Almacen("diferido", None, tmp_path).datos == [1, 2]
    assert a not in Almacen.pendientes


def test_almacen_memoria_no_queda_pendiente():
    a = AlmacenMemoria([])
    a.guardar_luego()
    assert a not in Almacen.pendientes


def test_generar_contrasena():
    for _ in range(50):
        c = generar_contrasena()
        assert len(c) == 18
        for grupo in (string.ascii_lowercase, string.ascii_uppercase, string.digits, SIMBOLOS):
            assert any(ch in grupo for ch in c)
    assert len({generar_contrasena() for _ in range(20)}) == 20


def test_maestra_comprueba_hash(tmp_path):
    import base64
    import secrets
    ajustes = Almacen("ajustes", {}, tmp_path)
    v = Verificador(ajustes)
    sal = secrets.token_bytes(16)
    ajustes.datos["maestra"] = {"sal": base64.b64encode(sal).decode(),
                                "hash": base64.b64encode(v.derivar("correcta", sal)).decode()}
    assert v._coincide("correcta")
    assert not v._coincide("incorrecta")


@pytest.mark.parametrize("url, origen", [
    ("https://ejemplo.com/login?x=1", "https://ejemplo.com"),
    ("http://localhost:8000/a", "http://localhost:8000"),
    ("ejemplo.com", "https://ejemplo.com"),
])
def test_origen(url, origen):
    assert Contrasenas.origen(url) == origen


SOLO_LINUX = pytest.mark.skipif(sys.platform == "win32", reason="en Windows se cifra con DPAPI, no con el llavero")


@SOLO_LINUX
def test_cifrado_con_llavero(con_llavero):
    assert cifrado_disponible() == "llavero"
    v = cifrar("secreto")
    assert v.startswith("llavero:") and "secreto" not in v
    assert descifrar(v) == "secreto"


@SOLO_LINUX
def test_sin_llavero_se_marca_como_sin_cifrar(tmp_path, sin_llavero):
    assert cifrado_disponible() is None
    c = Contrasenas(tmp_path)
    c.guardar_cuenta("https://a.com", "yo", "clave")
    assert c.sin_cifrar()


def test_migra_a_cifrado_cuando_hay_llavero(tmp_path, sin_llavero, monkeypatch):
    c = Contrasenas(tmp_path)
    c.guardar_cuenta("https://a.com", "yo", "clave")
    from cryptography.fernet import Fernet

    from aurora import contrasenas
    monkeypatch.setattr(contrasenas, "_FERNET", Fernet(Fernet.generate_key()))
    c2 = Contrasenas(tmp_path)
    assert not c2.sin_cifrar()
    assert c2.clave(c2.datos["cuentas"][0]) == "clave"


def test_leer_clave_distingue_fallo_de_vacia(tmp_path, con_llavero):
    c = Contrasenas(tmp_path)
    c.guardar_cuenta("https://a.com", "yo", "")
    c.datos["cuentas"].append({"origen": "https://a.com", "usuario": "otro", "clave": "llavero:basura"})
    assert c.leer_clave(c.datos["cuentas"][0]) == ""
    assert c.leer_clave(c.datos["cuentas"][1]) is None
    assert c.clave(c.datos["cuentas"][1]) == ""


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI solo existe en Windows")
def test_cifrado_dpapi_en_windows():
    assert cifrado_disponible() == "dpapi"
    v = cifrar("secreto")
    assert v.startswith("dpapi:") and "secreto" not in v
    assert descifrar(v) == "secreto"


def test_json_danado_se_aparta_y_no_se_pisa(tmp_path):
    (tmp_path / "marcadores.json").write_text('[{"url": "https://a.com"', encoding="utf-8")  # cortado
    Almacen.recuperados.clear()
    a = Almacen("marcadores", [], tmp_path)
    assert a.datos == []
    copias = list(tmp_path.glob("marcadores.danado-*.json"))
    assert len(copias) == 1 and copias[0].read_text(encoding="utf-8").startswith('[{"url"')
    assert Almacen.recuperados == copias
    a.guardar()  # el siguiente guardado ya no destruye lo que había
    assert copias[0].exists()
    Almacen.recuperados.clear()


def test_json_con_tipo_inesperado_se_aparta(tmp_path):
    (tmp_path / "contrasenas.json").write_text("[1, 2, 3]", encoding="utf-8")
    Almacen.recuperados.clear()
    c = Contrasenas(tmp_path)
    assert c.datos == {"cuentas": [], "nunca": []}
    assert list(tmp_path.glob("contrasenas.danado-*.json"))
    Almacen.recuperados.clear()


def test_cuentas_mal_formadas_se_ignoran(tmp_path):
    (tmp_path / "contrasenas.json").write_text(
        '{"cuentas": [{"origen": "https://a.com", "usuario": "yo", "clave": "b64:eA=="}, {"origen": 3}, "x"]}',
        encoding="utf-8")
    c = Contrasenas(tmp_path)
    assert [x["usuario"] for x in c.datos["cuentas"]] == ["yo"] and c.datos["nunca"] == []
