"""Widgets básicos animados: botones, interruptores, barra de progreso, avisos."""
from .comun import *  # noqa: F401,F403


# ═════════════════════════════ widgets base

class BotonIcono(QAbstractButton):
    """Botón redondeado con fondo que aparece suavemente al pasar el ratón."""

    def __init__(self, icono, consejo, padre=None, tam=34, color_marcado=None):
        super().__init__(padre)
        self.icono, self.color_marcado = icono, color_marcado
        self.setToolTip(consejo)
        self.setFixedSize(tam, tam)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._h = 0.0
        self.anim = animacion(self, self._set, 160)

    def _set(self, v):
        self._h = v
        self.update()

    def set_icono(self, icono):
        self.icono = icono
        self.update()

    def enterEvent(self, e):
        animar(self.anim, self._h, 1.0)

    def leaveEvent(self, e):
        animar(self.anim, self._h, 0.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        marcado = self.isChecked() and not self.color_marcado
        if marcado:
            fondo = con_alfa(T.a1, 0.30 + 0.15 * self._h)
        else:
            fondo = velo(20 * self._h + (14 if self.isDown() else 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fondo)
        p.drawRoundedRect(r, 9, 9)
        if not self.isEnabled():
            color = QColor(C["apagado"])
        elif self.isChecked() and self.color_marcado:
            color = QColor(self.color_marcado)
        else:
            color = mezcla(C["tenue"], C["texto"], 0.55 + 0.45 * self._h)
        p.setPen(color)
        p.setFont(Iconos.fuente(10.5 if self.width() > 30 else 9))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, Iconos.glifo(self.icono))


class Interruptor(QAbstractButton):
    """Interruptor tipo iOS con la bolita animada."""

    def __init__(self, texto, marcado=False, padre=None):
        super().__init__(padre)
        self.setCheckable(True)
        self.setChecked(marcado)
        self.setText(texto)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if not texto:
            self.setFixedSize(46, 30)
        self._p = 1.0 if marcado else 0.0
        self.anim = animacion(self, self._set, 200)
        self.toggled.connect(lambda c: animar(self.anim, self._p, 1.0 if c else 0.0))

    def _set(self, v):
        self._p = v
        self.update()

    def sizeHint(self):
        return QSize(240, 30)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRectF(0, 0, self.width() - 50, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        pista = QRectF(self.width() - 42, (self.height() - 22) / 2, 40, 22)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(mezcla(C["interruptor"], T.a1, self._p))
        p.drawRoundedRect(pista, 11, 11)
        x = pista.left() + 3 + (pista.width() - 22) * self._p
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QRectF(x, pista.top() + 3, 16, 16))


class BarraProgreso(QWidget):
    """Línea fina con degradado que avanza suave y se desvanece al terminar."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(2)
        self._v, self._o = 0.0, 0.0
        self.anim_v = animacion(self, self._set_v, 350)
        self.anim_o = animacion(self, self._set_o, 450)

    def _set_v(self, v):
        self._v = v
        self.update()

    def _set_o(self, v):
        self._o = v
        self.update()

    def progreso(self, p):
        if p >= 100:
            animar(self.anim_v, self._v, 1.0)
            animar(self.anim_o, self._o, 0.0)
            return
        if self._o < 0.5 and self._v >= 0.99:
            self._v = 0.0
        animar(self.anim_o, self._o, 1.0)
        animar(self.anim_v, self._v, max(p / 100, 0.08))

    def fijar(self, cargando, p):
        self.anim_v.stop()
        self.anim_o.stop()
        self._v = p / 100 if cargando else 0.0
        self._o = 1.0 if cargando else 0.0
        self.update()

    def paintEvent(self, e):
        if self._o <= 0.01:
            return
        p = QPainter(self)
        p.setOpacity(self._o)
        w = self.width() * self._v
        g = QLinearGradient(0, 0, max(w, 1), 0)
        g.setColorAt(0, QColor(T.a1))
        g.setColorAt(1, QColor(T.a2))
        p.fillRect(QRectF(0, 0, w, 2), g)


class Aviso(QLabel):
    """Notificación flotante (toast) que sube y se desvanece."""

    def __init__(self, padre):
        super().__init__(padre)
        self.setObjectName("aviso")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()
        self.efecto = QGraphicsOpacityEffect(self)
        self.efecto.setOpacity(0)
        self.setGraphicsEffect(self.efecto)
        self.anim_o = QPropertyAnimation(self.efecto, b"opacity", self)
        self.anim_o.setDuration(220)
        self.anim_p = QPropertyAnimation(self, b"pos", self)
        self.anim_p.setDuration(320)
        self.anim_p.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim_o.finished.connect(lambda: self.hide() if self.efecto.opacity() < 0.05 else None)
        self.reloj = QTimer(self, singleShot=True, interval=2600)
        self.reloj.timeout.connect(lambda: animar(self.anim_o, self.efecto.opacity(), 0.0))

    def mostrar(self, texto):
        self.setText(texto)
        self.adjustSize()
        padre = self.parentWidget()
        x = (padre.width() - self.width()) // 2
        y = padre.height() - self.height() - 28
        if not self.isVisible() or self.efecto.opacity() < 0.5:
            self.move(x, y + 18)
        self.show()
        self.raise_()
        animar(self.anim_p, self.pos(), QPoint(x, y))
        animar(self.anim_o, self.efecto.opacity(), 1.0)
        self.reloj.start()


# ═════════════════════════════ barra de título propia (Linux)

class BotonVentana(QAbstractButton):
    """Minimizar, maximizar/restaurar o cerrar, dibujados a mano para que encajen con la barra oscura."""

    def __init__(self, tipo, consejo, padre=None):
        super().__init__(padre)
        self.tipo = tipo
        self.setToolTip(consejo)
        self.setFixedSize(40, 32)
        self._h = 0.0
        self.anim = animacion(self, self._set, 140)

    def _set(self, v):
        self._h = v
        self.update()

    def enterEvent(self, e):
        animar(self.anim, self._h, 1.0)

    def leaveEvent(self, e):
        animar(self.anim, self._h, 0.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 2, -4, -2)
        cerrar = self.tipo == "cerrar"
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(con_alfa("#e5484d", 0.9 * self._h) if cerrar else velo(22 * self._h))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(QPen(QColor("#ffffff") if cerrar and self._h > 0.5 else mezcla(C["tenue"], C["texto"], self._h), 1.3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        c, s = r.center(), 5.0
        if self.tipo == "minimizar":
            p.drawLine(QPointF(c.x() - s, c.y()), QPointF(c.x() + s, c.y()))
        elif self.tipo == "maximizar":
            p.drawRoundedRect(QRectF(c.x() - s, c.y() - s, 2 * s, 2 * s), 1.5, 1.5)
        elif self.tipo == "restaurar":
            p.drawRoundedRect(QRectF(c.x() - s, c.y() - s + 2, 2 * s - 2, 2 * s - 2), 1.5, 1.5)
            p.drawPolyline([QPointF(c.x() - s + 2, c.y() - s), QPointF(c.x() + s, c.y() - s),
                            QPointF(c.x() + s, c.y() + s - 2)])
        else:
            p.drawLine(QPointF(c.x() - s, c.y() - s), QPointF(c.x() + s, c.y() + s))
            p.drawLine(QPointF(c.x() - s, c.y() + s), QPointF(c.x() + s, c.y() - s))


class ControlesVentana(QWidget):
    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.minimizar = BotonVentana("minimizar", "Minimizar")
        self.maximizar = BotonVentana("maximizar", "Maximizar")
        self.cerrar = BotonVentana("cerrar", "Cerrar")
        self.minimizar.clicked.connect(ventana.showMinimized)
        self.maximizar.clicked.connect(self.alternar)
        self.cerrar.clicked.connect(ventana.close)
        for b in (self.minimizar, self.maximizar, self.cerrar):
            h.addWidget(b)
        self.setFixedSize(120, 32)

    def alternar(self):
        self.v.showNormal() if self.v.isMaximized() else self.v.showMaximized()

    def actualizar(self):
        maximizada = self.v.isMaximized()
        self.maximizar.tipo = "restaurar" if maximizada else "maximizar"
        self.maximizar.setToolTip("Restaurar" if maximizada else "Maximizar")
        self.maximizar.update()


# ═════════════════════════════ iconos de webs

def tono_de(texto):
    """Un matiz estable por texto (el mismo dominio siempre tiene el mismo color)."""
    return sum(map(ord, texto)) * 37 % 360


class Favicons(QObject):
    """Iconos de las webs visitadas, guardados en ~/.aurora/favicons cuando una pestaña los recibe.

    (No se usa QWebEngineProfile.requestIconForPageURL: en PyQt6 6.11 cuelga el proceso.)"""
    listo = pyqtSignal(str)  # host
    CARPETA = DATOS / "favicons"

    def __init__(self):
        super().__init__()
        self.cache = {}

    @staticmethod
    def host(url):
        return QUrl(url).host().removeprefix("www.")

    def ruta(self, host):
        return self.CARPETA / (re.sub(r"[^a-z0-9.-]", "_", host.lower()) + ".png")

    def icono(self, url):
        """El QIcon de la web, o None si aún no se conoce."""
        h = self.host(url)
        if not h:
            return None
        if h not in self.cache:
            r = self.ruta(h)
            self.cache[h] = QIcon(str(r)) if r.exists() else None
        return self.cache[h]

    def guardar(self, url, icono):
        h = self.host(url)
        if not h or icono is None or icono.isNull():
            return
        pm = icono.pixmap(32, 32)
        if pm.isNull():
            return
        self.CARPETA.mkdir(exist_ok=True)
        pm.save(str(self.ruta(h)), "PNG")
        nuevo = self.cache.get(h) is None
        self.cache[h] = QIcon(pm)
        if nuevo:
            self.listo.emit(h)

    def borrar_todo(self):
        self.cache.clear()
        for f in self.CARPETA.glob("*.png") if self.CARPETA.exists() else []:
            f.unlink()


_FAVICONS = None


def favicons():
    global _FAVICONS
    if _FAVICONS is None:
        _FAVICONS = Favicons()
    return _FAVICONS


def nombre_sitio(host):
    """«es.wikipedia.org» → «wikipedia»; «developer.mozilla.org» → «mozilla»."""
    partes = [x for x in host.lower().split(".") if x]
    if len(partes) >= 3 and partes[-2] in ("co", "com", "org", "gov", "edu", "ac") and len(partes[-1]) == 2:
        return partes[-3]
    return partes[-2] if len(partes) >= 2 else (partes[0] if partes else host)


def pintar_avatar(p, r, texto, icono=None, redondo=True):
    """Favicon sobre un fondo suave, o la inicial sobre un degradado con el color del sitio."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    radio = r.width() / 2 if redondo else r.width() * 0.28
    if icono is not None:
        p.setBrush(velo(22))
        p.drawRoundedRect(r, radio, radio)
        m = r.width() * 0.2
        icono.paint(p, r.adjusted(m, m, -m, -m).toRect())
    else:
        texto = nombre_sitio(texto) if "." in texto and " " not in texto else texto
        tono = tono_de(texto)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor.fromHsl(tono, 190, 135))
        g.setColorAt(1, QColor.fromHsl((tono + 45) % 360, 170, 100))
        p.setBrush(g)
        p.drawRoundedRect(r, radio, radio)
        f = QFont(p.font())
        f.setPixelSize(int(r.height() * 0.46))
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, (texto.strip() or "?")[0].upper())
    p.restore()
