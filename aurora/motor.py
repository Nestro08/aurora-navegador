"""Motor web: bloqueador, páginas, vistas y contenedor de cada pestaña."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403


# ═════════════════════════════ motor y página

class Bloqueador(QWebEngineUrlRequestInterceptor):
    """Bloquea anuncios/rastreadores y avisa de cada petición (para el panel Red)."""

    def __init__(self, receptor):
        super().__init__()
        self.receptor = receptor
        self.activo = self.dnt = True
        self.cargar_lista()

    def cargar_lista(self):
        self.dominios = set(BLOQUEO_BASE)
        extra = DATOS / "bloqueados.txt"
        if extra.exists():
            self.dominios |= {l.strip() for l in extra.read_text(encoding="utf-8").splitlines()
                              if l.strip() and not l.startswith("#")}

    def interceptRequest(self, info):
        url = info.requestUrl()
        if self.dnt:
            info.setHttpHeader(b"DNT", b"1")
            info.setHttpHeader(b"Sec-GPC", b"1")
        bloquear = False
        if self.activo:
            partes = url.host().split(".")
            bloquear = any(".".join(partes[i:]) in self.dominios for i in range(len(partes) - 1))
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
