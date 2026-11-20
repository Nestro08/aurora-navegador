"""Permisos de las webs: Aurora recuerda la respuesta por sitio (Qt olvida la cámara y el micrófono)."""
from types import SimpleNamespace

from PyQt6.QtCore import QUrl

from aurora.comun import Almacen, AlmacenMemoria
from aurora import permisos


class Tarjeta:
    def __init__(self):
        self.botones = None

    def mostrar(self, titulo, detalle, botones, icono="llave"):
        self.titulo, self.detalle, self.botones = titulo, detalle, {b[0]: b[1] for b in botones}


def ventana(perfil, incognito=False):
    v = permisos.MixinPermisos()
    v.p, v.incognito, v.pregunta = perfil, incognito, Tarjeta()
    v.aviso = SimpleNamespace(mostrar=lambda texto: None)
    return v


def perfil(tmp_path):
    return SimpleNamespace(permisos=Almacen("permisos", {}, tmp_path), web=None)


def test_pregunta_y_recuerda_por_sitio(tmp_path):
    p = perfil(tmp_path)
    v = ventana(p)
    hecho = []
    url = QUrl("https://meet.google.com/abc-defg")
    v._preguntar(url, "MediaVideoCapture", lambda: hecho.append("si"), lambda: hecho.append("no"))
    assert "meet.google.com" in v.pregunta.titulo and "cámara" in v.pregunta.titulo
    v.pregunta.botones["Permitir"]()
    assert hecho == ["si"]
    assert Almacen("permisos", {}, tmp_path).datos == {"https://meet.google.com": {"MediaVideoCapture": True}}
    # la segunda vez responde solo, sin tarjeta
    v2 = ventana(p)
    v2._preguntar(url, "MediaVideoCapture", lambda: hecho.append("si"), lambda: hecho.append("no"))
    assert v2.pregunta.botones is None and hecho == ["si", "si"]
    # otro sitio sí pregunta
    v2._preguntar(QUrl("https://otro.example"), "MediaVideoCapture", lambda: None, lambda: None)
    assert v2.pregunta.botones is not None


def test_bloquear_tambien_se_recuerda_y_se_puede_olvidar(tmp_path):
    p = perfil(tmp_path)
    v = ventana(p)
    hecho = []
    url = QUrl("https://ejemplo.com")
    v._preguntar(url, "Geolocation", lambda: hecho.append("si"), lambda: hecho.append("no"))
    v.pregunta.botones["Bloquear"]()
    assert permisos.permisos_guardados(p) == [("https://ejemplo.com", "Geolocation", False)]
    permisos.olvidar_permiso(p, "https://ejemplo.com", "Geolocation")
    assert permisos.permisos_guardados(p) == [] and Almacen("permisos", {}, tmp_path).datos == {}


def test_compartir_pantalla_se_pregunta_siempre(tmp_path):
    p = perfil(tmp_path)
    v = ventana(p)
    url = QUrl("https://meet.google.com")
    v._preguntar(url, "DesktopVideoCapture", lambda: None, lambda: None)
    v.pregunta.botones["Permitir"]()
    v.pregunta.botones = None
    v._preguntar(url, "DesktopVideoCapture", lambda: None, lambda: None)
    assert v.pregunta.botones is not None and permisos.permisos_guardados(p) == []


def test_incognito_no_escribe_en_disco(tmp_path):
    p = SimpleNamespace(permisos=AlmacenMemoria({}), web=None)
    v = ventana(p, incognito=True)
    v._preguntar(QUrl("https://a.com"), "MediaAudioCapture", lambda: None, lambda: None)
    assert "incógnito" in v.pregunta.detalle
    v.pregunta.botones["Permitir"]()
    assert p.permisos.datos and not list(tmp_path.iterdir())


def test_origen_con_puerto():
    assert permisos.origen_de(QUrl("http://localhost:8000/x?y")) == "http://localhost:8000"
    assert permisos.origen_de(QUrl("https://a.com/b")) == "https://a.com"
