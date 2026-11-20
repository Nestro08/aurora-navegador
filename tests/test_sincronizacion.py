"""Sincronización entre dos «dispositivos» que comparten carpeta."""
import json
import time
from types import SimpleNamespace

import pytest

from aurora.comun import AJUSTES_DEFECTO, Almacen
from aurora.contrasenas import Contrasenas, cifrar
from aurora.sincronizacion import Sincronizador


def dispositivo(raiz, nombre, nube, frase="frase de prueba"):
    carpeta = raiz / nombre
    carpeta.mkdir()
    ajustes = Almacen("ajustes", dict(AJUSTES_DEFECTO), carpeta)
    ajustes.datos.update(sync_activa=True, sync_carpeta=str(nube), sync_dispositivo=nombre,
                         sync_frase=cifrar(frase) if frase else "")
    p = SimpleNamespace(nombre="Personal", carpeta=carpeta, ajustes=ajustes, incognito=False, ventanas=[],
                        marcadores=Almacen("marcadores", [], carpeta), historial=Almacen("historial", [], carpeta),
                        claves=Contrasenas(carpeta))
    p.sync = Sincronizador(p)
    p.sync.reloj.stop()
    return p


def fijar_sal(p):
    """El dispositivo elige su sal (lo primero que hace al sincronizar con frase de paso)."""
    p.sync._mezclar(p.sync._leer(p.sync._preparar()), p.sync.dispositivo())


@pytest.fixture
def nube(tmp_path):
    n = tmp_path / "nube"
    n.mkdir()
    return n


def test_pasa_contrasenas_historial_y_accesos(tmp_path, nube, app, con_llavero):
    a, b = dispositivo(tmp_path, "pc", nube), dispositivo(tmp_path, "portatil", nube)
    a.claves.guardar_cuenta("https://banco.com", "yo", "s3cr3to")
    a.historial.datos.append({"url": "https://privado.example/", "titulo": "x", "fecha": "01/01/2026 10:00"})
    a.marcadores.datos.append({"url": "https://github.com", "titulo": "GitHub", "ts": 1})
    a.sync._sincronizar()
    b.sync._sincronizar()
    assert b.claves.clave(b.claves.de("https://banco.com")[0]) == "s3cr3to"
    assert b.historial.datos[0]["url"] == "https://privado.example/"
    assert b.marcadores.datos[0]["url"] == "https://github.com"
    # en la nube no hay nada legible
    texto = (nube / "Aurora-Sync" / "personal" / "pc.json").read_text()
    assert "privado.example" not in texto and "s3cr3to" not in texto


def test_sales_distintas_por_carrera_no_rompen(tmp_path, nube, app, con_llavero):
    a, b = dispositivo(tmp_path, "pc", nube), dispositivo(tmp_path, "portatil", nube)
    carpeta = nube / "Aurora-Sync" / "personal"
    carpeta.mkdir(parents=True)
    fijar_sal(a)
    (carpeta / "sal.bin").unlink()  # el otro PC arranca sin ver la sal del primero
    fijar_sal(b)
    assert a.sync.estado.datos["sal"] != b.sync.estado.datos["sal"]
    a.claves.guardar_cuenta("https://x.com", "u", "clave-a")
    b.claves.guardar_cuenta("https://y.com", "u", "clave-b")
    a.sync._sincronizar()
    b.sync._sincronizar()
    a.sync._sincronizar()
    assert a.claves.clave(a.claves.de("https://y.com")[0]) == "clave-b"
    assert b.claves.clave(b.claves.de("https://x.com")[0]) == "clave-a"


def test_compatible_con_version_1(tmp_path, nube, app, con_llavero):
    """Un archivo sin «sal» (versión 1) se lee con el sal.bin compartido."""
    import base64
    import hashlib
    import secrets

    from cryptography.fernet import Fernet
    carpeta = nube / "Aurora-Sync" / "personal"
    carpeta.mkdir(parents=True)
    sal = secrets.token_bytes(16)
    (carpeta / "sal.bin").write_bytes(sal)
    f = Fernet(base64.urlsafe_b64encode(hashlib.pbkdf2_hmac("sha256", b"frase de prueba", sal, 300_000)))
    (carpeta / "viejo.json").write_text(json.dumps({
        "dispositivo": "viejo", "version": 1, "marcadores": [], "historial": [], "borrados": {},
        "claves": [{"origen": "https://v.com", "usuario": "u", "ts": 5, "clave": f.encrypt(b"vieja").decode()}]}))
    b = dispositivo(tmp_path, "nuevo", nube)
    b.sync._sincronizar()
    assert b.claves.clave(b.claves.de("https://v.com")[0]) == "vieja"
    assert base64.b64decode(b.sync.estado.datos["sal"]) == sal  # adopta la sal antigua


def test_frase_distinta_da_error_claro(tmp_path, nube, app, con_llavero):
    a = dispositivo(tmp_path, "pc", nube)
    b = dispositivo(tmp_path, "portatil", nube, frase="otra frase")
    a.claves.guardar_cuenta("https://x.com", "u", "c")
    a.sync._sincronizar()
    with pytest.raises(RuntimeError, match="frase de paso no coincide"):
        b.sync._sincronizar()


def test_sin_frase_sincroniza_accesos_y_avisa(tmp_path, nube, app, con_llavero):
    a = dispositivo(tmp_path, "pc", nube)
    b = dispositivo(tmp_path, "portatil", nube, frase=None)
    a.marcadores.datos.append({"url": "https://github.com", "titulo": "GitHub", "ts": 1})
    a.claves.guardar_cuenta("https://x.com", "u", "c")
    a.sync._sincronizar()
    mensaje = b.sync._sincronizar()
    assert "frase de paso" in mensaje
    assert b.marcadores.datos and not b.claves.datos["cuentas"]


def test_borrado_se_propaga(tmp_path, nube, app, con_llavero):
    a, b = dispositivo(tmp_path, "pc", nube), dispositivo(tmp_path, "portatil", nube)
    a.claves.guardar_cuenta("https://x.com", "u", "c")
    a.sync._sincronizar()
    b.sync._sincronizar()
    a.claves.al_borrar = lambda k: a.sync.borrado("claves", k)
    a.claves.borrar(a.claves.datos["cuentas"][0])
    a.sync._sincronizar()
    b.sync._sincronizar()
    assert not b.claves.datos["cuentas"]


def test_no_envia_vacias_las_que_no_se_descifran(tmp_path, nube, app, con_llavero):
    a, b = dispositivo(tmp_path, "pc", nube), dispositivo(tmp_path, "portatil", nube)
    a.claves.datos["cuentas"].append({"origen": "https://x.com", "usuario": "u", "clave": "llavero:basura", "ts": 9})
    a.sync._sincronizar()
    b.sync._sincronizar()
    assert not b.claves.datos["cuentas"]


def test_archivo_raro_de_otro_dispositivo_no_rompe_ni_cuela_nada(tmp_path, nube, app, con_llavero):
    b = dispositivo(tmp_path, "portatil", nube, frase="")
    carpeta = nube / "Aurora-Sync" / "personal"
    carpeta.mkdir(parents=True)
    (carpeta / "malo.json").write_text(json.dumps({
        "marcadores": [{"titulo": "sin url"}, {"url": "javascript:alert(document.cookie)", "titulo": "trampa"},
                       {"url": "https://bueno.example/", "titulo": 7, "ts": "ayer"},
                       {"url": "https://ok.example/", "titulo": "OK", "color": "red;}", "pos": {"x": 9, "y": -1}}],
        "historial": [{"url": "https://h.example/"}, "texto", {"url": "javascript:x", "fecha": "01/01/2026 10:00"},
                      {"url": "https://h.example/", "titulo": "H", "fecha": "01/01/2026 10:00"}],
        "borrados": {"marcadores": "no es un dict"}, "claves": [{"origen": 1}],
    }), encoding="utf-8")
    (carpeta / "roto.json").write_text("{esto no es json", encoding="utf-8")
    b.sync._sincronizar()
    assert [m["url"] for m in b.marcadores.datos] == ["https://ok.example/"]
    ok = b.marcadores.datos[0]
    assert "color" not in ok and ok["pos"] == {"x": 1.0, "y": 0.0}
    assert [h["url"] for h in b.historial.datos] == ["https://h.example/"]


def test_sincronizar_en_segundo_plano(tmp_path, nube, app, con_llavero):
    a, b = dispositivo(tmp_path, "pc", nube), dispositivo(tmp_path, "portatil", nube)
    a.marcadores.datos.append({"url": "https://github.com", "titulo": "GitHub", "ts": 1})
    a.sync._sincronizar()
    resultados = []
    b.sync.terminado.connect(lambda ok, mensaje: resultados.append((ok, mensaje)))
    b.sync.sincronizar()
    assert b.sync._en_curso
    b.sync.sincronizar()  # mientras tanto no se lanza otra
    limite = time.time() + 20
    while not resultados and time.time() < limite:
        app.processEvents()
        time.sleep(0.02)
    assert resultados and resultados[0][0], resultados
    assert not b.sync._en_curso
    assert b.marcadores.datos[0]["url"] == "https://github.com"
    assert (nube / "Aurora-Sync" / "personal" / "portatil.json").exists()
