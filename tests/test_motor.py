"""Bloqueador de anuncios, servidor local y accesos seguros."""
import http.client

from aurora.comun import es_marcador, url_segura
from aurora.desarrollo import servir
from aurora.motor import Bloqueador, leer_dominios, listas


def test_lee_listas_hosts_y_de_dominios():
    texto = """# comentario
127.0.0.1 localhost
0.0.0.0 anuncios.example.com
0.0.0.0 Rastreo.Example.NET # con comentario
solo-dominio.org
basura sin sentido
::1 localhost
"""
    assert leer_dominios(texto) == {"anuncios.example.com", "rastreo.example.net", "solo-dominio.org"}


def test_bloquea_dominio_y_subdominios(app):
    b = Bloqueador(lambda *datos: None)
    b.ampliado = False
    assert b.bloquea("doubleclick.net") and b.bloquea("ad.g.doubleclick.net")
    assert not b.bloquea("example.com") and not b.bloquea("notdoubleclick.net")


def test_lista_ampliada_solo_si_esta_activa(app):
    b = Bloqueador(lambda *datos: None)
    listas().ampliada = {"solo-en-la-ampliada.example"}
    try:
        b.ampliado = True
        assert b.bloquea("cdn.solo-en-la-ampliada.example")
        b.ampliado = False
        assert not b.bloquea("cdn.solo-en-la-ampliada.example")
    finally:
        listas().ampliada = set()


def test_servidor_local_solo_responde_a_localhost(tmp_path):
    (tmp_path / "index.html").write_text("hola", encoding="utf-8")
    srv = servir(str(tmp_path))
    try:
        puerto = srv.server_address[1]
        for host, esperado in ((f"localhost:{puerto}", 200), (f"127.0.0.1:{puerto}", 200),
                               (f"atacante.example:{puerto}", 403)):  # DNS rebinding
            c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=5)
            c.request("GET", "/index.html", headers={"Host": host})
            r = c.getresponse()
            assert r.status == esperado, host
            r.read()
            c.close()
    finally:
        srv.shutdown()


def test_accesos_solo_con_esquemas_seguros():
    assert url_segura("https://github.com") and url_segura("http://localhost:8000/") and url_segura("file:///tmp/a")
    for mala in ("javascript:alert(1)", "data:text/html,<script>", "JAVASCRIPT:x", "", None, 3):
        assert not url_segura(mala)
    assert es_marcador({"url": "https://a.com", "titulo": "A"})
    assert not es_marcador({"url": "https://a.com", "titulo": 3}) and not es_marcador({"titulo": "x"})
