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
            fondo = QColor(255, 255, 255, int(20 * self._h + (14 if self.isDown() else 0)))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fondo)
        p.drawRoundedRect(r, 9, 9)
        if not self.isEnabled():
            color = QColor("#4a5060")
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
        p.setBrush(mezcla("#343a48", T.a1, self._p))
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
