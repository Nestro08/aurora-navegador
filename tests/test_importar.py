"""Importar desde un perfil de Chrome falso, cifrado como lo hace Chrome en Linux."""
import hashlib
import json
import sqlite3
import sys
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtNetwork import QNetworkCookie
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile

from aurora.comun import AJUSTES_DEFECTO, Almacen
from aurora.contrasenas import Contrasenas
from aurora.importar import PerfilNavegador, detectar, fecha_webkit, importar

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="cifrado de Chrome en Linux")
SECRETO = b"secreto-del-llavero"


def cifrar_chrome(texto, version=b"v11", dominio=None):
    secreto = b"peanuts" if version == b"v10" else SECRETO
    clave = PBKDF2HMAC(hashes.SHA1(), 16, b"saltysalt", 1).derive(secreto)
    datos = (hashlib.sha256(dominio.encode()).digest() if dominio else b"") + texto.encode()
    r = padding.PKCS7(128).padder()
    datos = r.update(datos) + r.finalize()
    c = Cipher(algorithms.AES(clave), modes.CBC(b" " * 16)).encryptor()
    return version + c.update(datos) + c.finalize()


def webkit(dt):
    return int((dt - datetime(1601, 1, 1)).total_seconds() * 1_000_000)


@pytest.fixture
def chrome(tmp_path):
    base = tmp_path / "google-chrome"
    d = base / "Default"
    (d / "Network").mkdir(parents=True)
    (base / "Local State").write_text(json.dumps({"profile": {"info_cache": {"Default": {"name": "Persona 1"}}}}))
    (d / "Preferences").write_text(json.dumps({"default_search_provider_data": {
        "template_url_data": {"keyword": "google.com", "short_name": "Google"}}}))
    (d / "Bookmarks").write_text(json.dumps({"roots": {
        "bookmark_bar": {"type": "folder", "children": [
            {"type": "url", "name": "GitHub", "url": "https://github.com/", "date_added": str(webkit(datetime(2026, 1, 1)))},
            {"type": "folder", "name": "Uni", "children": [
                {"type": "url", "name": "Campus", "url": "https://campus.uni.es/"}]}]},
        "other": {"type": "folder", "children": [{"type": "url", "name": "x", "url": "javascript:alert(1)"}]}}}))
    h = sqlite3.connect(d / "History")
    h.execute("CREATE TABLE urls (url TEXT, title TEXT, last_visit_time INTEGER, hidden INTEGER)")
    h.executemany("INSERT INTO urls VALUES (?,?,?,?)", [
        ("https://wikipedia.org/", "Wikipedia", webkit(datetime(2026, 11, 10, 12, 0)), 0),
        ("chrome://settings/", "Ajustes", webkit(datetime(2026, 11, 10, 13, 0)), 0),
        ("https://oculto.com/", "", webkit(datetime(2026, 11, 10, 14, 0)), 1)])
    h.commit()
    h.close()
    for nombre, filas in (("Login Data", [
            ("https://banco.com/login", "ana", cifrar_chrome("s3cr3to"), 0),
            ("https://viejo.com/", "ana", cifrar_chrome("antigua", b"v10"), 0),
            ("https://nunca.com/", "", b"", 1),
            ("android://abc@com.app/", "ana", cifrar_chrome("x"), 0),
            ("https://roto.com/", "ana", b"v11" + b"\0" * 32, 0)]),
            ("Login Data For Account", [("https://cuenta.com/", "ana@gmail.com", cifrar_chrome("de-la-cuenta"), 0)])):
        bd = sqlite3.connect(d / nombre)
        bd.execute("CREATE TABLE logins (origin_url TEXT, username_value TEXT, password_value BLOB, "
                   "blacklisted_by_user INTEGER)")
        bd.executemany("INSERT INTO logins VALUES (?,?,?,?)", filas)
        bd.commit()
        bd.close()
    ck = sqlite3.connect(d / "Network" / "Cookies")
    ck.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    ck.execute("INSERT INTO meta VALUES ('version', '24')")
    ck.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, value TEXT, encrypted_value BLOB, path TEXT, "
               "expires_utc INTEGER, is_secure INTEGER, is_httponly INTEGER, samesite INTEGER, has_expires INTEGER)")
    futuro, pasado = webkit(datetime(2030, 1, 1)), webkit(datetime(2020, 1, 1))
    ck.executemany("INSERT INTO cookies VALUES (?,?,?,?,?,?,?,?,?,?)", [
        (".ejemplo.com", "sesion", "", cifrar_chrome("abc123", dominio=".ejemplo.com"), "/", futuro, 1, 1, 1, 1),
        ("otra.com", "tema", "oscuro", b"", "/", 0, 0, 0, -1, 0),
        ("caducada.com", "vieja", "", cifrar_chrome("x", dominio="caducada.com"), "/", pasado, 0, 0, 0, 1)])
    ck.commit()
    ck.close()
    return PerfilNavegador("Google Chrome", base, "Default", "Persona 1", "Chrome")


@pytest.fixture
def aurora(tmp_path, app, con_llavero):
    c = tmp_path / "aurora"
    c.mkdir()
    return SimpleNamespace(ajustes=Almacen("ajustes", dict(AJUSTES_DEFECTO), c), claves=Contrasenas(c),
                           marcadores=Almacen("marcadores", [{"url": "https://github.com/", "titulo": "Ya", "ts": 1}], c),
                           historial=Almacen("historial", [], c), web=QWebEngineProfile())


def test_fecha_webkit():
    assert fecha_webkit(webkit(datetime(2026, 5, 4, 3, 2, 1))) == datetime(2026, 5, 4, 3, 2, 1)
    assert fecha_webkit(0) is None


def test_detecta_perfiles(chrome, monkeypatch, tmp_path):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path / "casa")
    (tmp_path / "casa" / ".config").mkdir(parents=True)
    (tmp_path / "casa" / ".config" / "google-chrome").symlink_to(chrome.base)
    perfiles = detectar()
    assert [str(p) for p in perfiles] == ["Google Chrome"] and perfiles[0].llavero == "Chrome"


def test_importa_todo(chrome, aurora):
    resumen = importar(aurora, chrome, {"marcadores", "historial", "contrasenas", "buscador"}, SECRETO)
    assert [m["url"] for m in aurora.marcadores.datos] == ["https://github.com/", "https://campus.uni.es/"]
    assert [h["url"] for h in aurora.historial.datos] == ["https://wikipedia.org/"]
    c = aurora.claves
    assert c.clave(c.de("https://banco.com")[0]) == "s3cr3to"
    assert c.clave(c.de("https://viejo.com")[0]) == "antigua"            # formato v10
    assert c.clave(c.de("https://cuenta.com")[0]) == "de-la-cuenta"      # guardadas en la cuenta de Google
    assert not c.sin_cifrar()
    assert "https://nunca.com" in c.datos["nunca"]
    assert len(c.datos["cuentas"]) == 3                                   # sin android:// ni la rota
    assert aurora.ajustes.datos["buscador"] == "Google"
    assert any("1 no se pudieron descifrar" in r for r in resumen)
    # repetir no duplica nada
    importar(aurora, chrome, {"marcadores", "historial", "contrasenas"}, SECRETO)
    assert len(aurora.marcadores.datos) == 2 and len(aurora.historial.datos) == 1 and len(c.datos["cuentas"]) == 3


def test_secreto_incorrecto_no_rompe(chrome, aurora):
    resumen = importar(aurora, chrome, {"contrasenas"}, b"otro")
    assert {x["origen"] for x in aurora.claves.datos["cuentas"]} == {"https://viejo.com"}  # solo la v10
    assert any("3 no se pudieron descifrar" in r for r in resumen)  # android:// ni se intenta


def test_cookies(chrome, aurora):
    pagina = QWebEnginePage(aurora.web)  # como en Aurora: el almacén de cookies vive con alguna página abierta
    pagina.setHtml("<p>")
    recibidas, bucle = [], QEventLoop()
    # la señal pasa una referencia temporal: hay que copiarla
    aurora.web.cookieStore().cookieAdded.connect(lambda c: recibidas.append(QNetworkCookie(c)))
    resumen = importar(aurora, chrome, {"cookies"}, SECRETO)
    QTimer.singleShot(1500, bucle.quit)
    bucle.exec()
    por_nombre = {bytes(c.name()).decode(): c for c in recibidas}
    assert set(por_nombre) == {"sesion", "tema"}                        # la caducada no
    s = por_nombre["sesion"]
    assert bytes(s.value()) == b"abc123"                                  # sin el prefijo SHA-256
    assert s.domain() == ".ejemplo.com" and s.isSecure() and s.isHttpOnly()
    # Chromium limita la caducidad a 400 días (RFC 6265bis): 2030 se queda en «dentro de ~400 días»
    dias = (s.expirationDate().toSecsSinceEpoch() - datetime.now(timezone.utc).timestamp()) / 86400
    assert 399 < dias <= 400
    assert por_nombre["tema"].isSessionCookie()
    assert resumen == ["🍪  2 cookies (sesiones iniciadas)"]
