"""Motor web: bloqueador, páginas, vistas y contenedor de cada pestaña."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInfo


# ═════════════════════════════ motor y página

URL_LISTA = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"  # la que usa Pi-hole
LISTA_AMPLIADA = DATOS / "listas" / "anuncios.txt"
DIAS_LISTA = 7
RE_DOMINIO = re.compile(r"^(?:0\.0\.0\.0|127\.0\.0\.1|::1?)?\s*([a-z0-9][a-z0-9.-]*\.[a-z]{2,})\s*(?:#.*)?$")


def leer_dominios(texto):
    """Dominios de un archivo hosts («0.0.0.0 dominio») o de una lista de un dominio por línea."""
    res = set()
    for linea in texto.splitlines():
        m = RE_DOMINIO.match(linea.strip().lower())
        if m and m.group(1) not in ("localhost", "localhost.localdomain", "local", "broadcasthost"):
            res.add(m.group(1).rstrip("."))
    return res


class Listas(QObject):
    """Lista ampliada de anuncios y rastreadores: se descarga por HTTPS y se renueva cada semana.

    Se comparte entre todos los perfiles (son unos 75.000 dominios: no se cargan dos veces)."""
    cambiada = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ampliada = set()
        self.red = None
        self.descargando = False
        self.cargar()

    def cargar(self):
        try:
            self.ampliada = leer_dominios(LISTA_AMPLIADA.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            self.ampliada = set()

    def fecha(self):
        try:
            return datetime.fromtimestamp(LISTA_AMPLIADA.stat().st_mtime)
        except OSError:
            return None

    def toca_actualizar(self):
        f = self.fecha()
        return f is None or (datetime.now() - f).days >= DIAS_LISTA

    def actualizar(self, al_terminar=None):
        """Descarga la lista. al_terminar(ok, mensaje)."""
        if self.descargando:
            return
        from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
        self.descargando = True
        self.red = self.red or QNetworkAccessManager(self)
        peticion = QNetworkRequest(QUrl(URL_LISTA))
        peticion.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                              QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        r = self.red.get(peticion)
        limite = 15 * 1024 * 1024
        r.downloadProgress.connect(lambda recibido, total: r.abort() if max(recibido, total) > limite else None)

        def fin():
            self.descargando = False
            r.deleteLater()
            if r.error() != QNetworkReply.NetworkError.NoError:
                mensaje = f"No se pudo descargar la lista: {r.errorString()}"
                ok = False
            else:
                texto = bytes(r.readAll()).decode("utf-8", "ignore")
                dominios = leer_dominios(texto)
                if len(dominios) < 1000:  # una respuesta rara (página de error, lista vacía…) no se guarda
                    ok, mensaje = False, "La lista descargada no parece válida: se mantiene la anterior"
                else:
                    LISTA_AMPLIADA.parent.mkdir(parents=True, exist_ok=True)
                    temporal = LISTA_AMPLIADA.with_suffix(".tmp")
                    temporal.write_text(texto, encoding="utf-8")
                    os.replace(temporal, LISTA_AMPLIADA)
                    self.ampliada = dominios
                    self.cambiada.emit()
                    ok, mensaje = True, f"🛡  Lista de bloqueo actualizada: {len(dominios):,} dominios".replace(",", ".")
            if al_terminar:
                al_terminar(ok, mensaje)

        r.finished.connect(fin)


_LISTAS = None


def listas():
    global _LISTAS
    if _LISTAS is None:
        _LISTAS = Listas()
    return _LISTAS


class Bloqueador(QWebEngineUrlRequestInterceptor):
    """Bloquea anuncios/rastreadores y avisa de cada petición (para el panel Red)."""

    def __init__(self, receptor):
        super().__init__()
        self.receptor = receptor
        self.activo = self.dnt = self.ampliado = True
        self.cargar_lista()

    def cargar_lista(self):
        self.dominios = set(BLOQUEO_BASE)
        extra = DATOS / "bloqueados.txt"
        if extra.exists():
            self.dominios |= leer_dominios(extra.read_text(encoding="utf-8", errors="ignore"))

    def total(self):
        return len(self.dominios | listas().ampliada) if self.ampliado else len(self.dominios)

    def bloquea(self, host):
        partes = host.lower().split(".")
        ampliada = listas().ampliada if self.ampliado else ()
        for i in range(len(partes) - 1):
            dominio = ".".join(partes[i:])
            if dominio in self.dominios or dominio in ampliada:
                return True
        return False

    def interceptRequest(self, info):
        url = info.requestUrl()
        if self.dnt:
            info.setHttpHeader(b"DNT", b"1")
            info.setHttpHeader(b"Sec-GPC", b"1")
        bloquear = False
        # la página a la que vas tú (escribiéndola o con un clic) nunca se bloquea: solo lo que carga dentro
        if self.activo and info.resourceType() != QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame:
            bloquear = self.bloquea(url.host())
            if bloquear:
                info.block(True)
        tipo = info.resourceType().name.replace("ResourceType", "")
        self.receptor(bytes(info.requestMethod()).decode(), TIPOS_RECURSO.get(tipo, tipo),
                      url.toString(), bloquear)


class PaginaMotor(QWebEnginePage):
    def __init__(self, perfil, padre, ventana):
        super().__init__(perfil, padre)
        self.v = ventana

    def javaScriptConsoleMessage(self, nivel, mensaje, linea, origen):
        self.v.consola_pagina(self, nivel, mensaje, linea, origen)


class Vista(QWebEngineView):
    def __init__(self, ventana, perfil, padre):
        super().__init__(padre)
        self.v = ventana
        self.setPage(PaginaMotor(perfil, self, ventana))

    def createWindow(self, tipo):
        fondo = tipo == QWebEnginePage.WebWindowType.WebBrowserBackgroundTab
        return self.v.nueva_pestana(None, enfocar=not fondo)


class PaginaWeb(QWidget):
    """Contenedor de cada pestaña. Gestiona zoom y el modo responsive animado."""

    def __init__(self, ventana, perfil):
        super().__init__()
        self.chip = None
        self.zoom, self.disp, self.nombre_disp = 1.0, None, LIBRE
        self.dividida = self.resaltada = False
        self._actual, self._esc = None, 1.0
        self.vista = Vista(ventana, perfil, self)
        self.anim = animacion(self, self._paso, 450, QEasingCurve.Type.OutQuart)
        self.anim.finished.connect(self._fin)

    def set_dispositivo(self, nombre):
        self.nombre_disp = nombre
        self._animar_a(DISPOSITIVOS.get(nombre))

    def rotar(self):
        if self.disp:
            self._animar_a((self.disp[1], self.disp[0]))

    def _animar_a(self, tam):
        lleno = QSizeF(self.width(), self.height())
        origen = self._actual if self._actual is not None else lleno
        self.disp = tam
        animar(self.anim, origen, QSizeF(*tam) if tam else lleno)

    def _paso(self, s):
        self._actual = s
        self.colocar()

    def _fin(self):
        if self.disp is None:
            self._actual = None
            self.colocar()

    def colocar(self):
        if self._actual is None:
            self.vista.setGeometry(self.rect().adjusted(0, 3 if self.dividida else 0, 0, 0))
            self._zoom(self.zoom)
            self.update()
            return
        m = 36
        w, h = max(1.0, self._actual.width()), max(1.0, self._actual.height())
        self._esc = max(0.1, min(1.0, (self.width() - 2 * m) / w, (self.height() - 2 * m - 24) / h))
        rw, rh = w * self._esc, h * self._esc
        self.vista.setGeometry(int((self.width() - rw) / 2), int((self.height() - rh) / 2 + 12), int(rw), int(rh))
        self._zoom(self.zoom * self._esc)
        self.update()

    def _zoom(self, z):
        z = max(0.25, min(5.0, z))
        if abs(self.vista.zoomFactor() - z) > 0.001:
            self.vista.setZoomFactor(z)

    def resizeEvent(self, e):
        if self.anim.state() != QVariantAnimation.State.Running:
            if self.disp is None:
                self._actual = None
            self.colocar()

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C["fondo"]))
        if self.dividida:  # en pantalla dividida, una línea marca el lado activo
            g = QLinearGradient(0, 0, self.width(), 0)
            g.setColorAt(0, QColor(T.a1 if self.resaltada else C["borde"]))
            g.setColorAt(1, QColor(T.a2 if self.resaltada else C["borde"]))
            p.fillRect(QRectF(0, 0, self.width(), 3), g)
        if self._actual is None:
            return
        p.setPen(velo(16))
        for x in range(11, self.width(), 22):
            for y in range(11, self.height(), 22):
                p.drawPoint(x, y)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        marco = QRectF(self.vista.geometry()).adjusted(-7, -7, 7, 7)
        p.setPen(QPen(QColor(C["borde_fuerte"]), 1.5))
        p.setBrush(QColor(C["tarjeta"]))
        p.drawRoundedRect(marco, 16, 16)
        if self.disp:
            p.setPen(QColor(C["tenue"]))
            texto = (f"{self.nombre_disp}   ·   {int(self._actual.width())} × {int(self._actual.height())}"
                     f"   ·   {round(self._esc * 100)} %")
            p.drawText(QRectF(0, marco.top() - 28, self.width(), 20), Qt.AlignmentFlag.AlignCenter, texto)
