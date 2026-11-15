"""Pantalla de bienvenida al arrancar: logo con animación de carga y «From developer for developers»."""
import math

from PyQt6.QtGui import QBrush, QConicalGradient, QRadialGradient

from .widgets import *  # noqa: F401,F403

FRASE = "From developer for developers"


class PantallaArranque(QWidget):
    terminado = pyqtSignal()
    DURACION = 2300  # ms; la ventana de Aurora se prepara mientras tanto
    TARJETA = QSize(560, 340)

    def __init__(self, saludo=""):
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.saludo, self.t, self.giro = saludo, 0.0, 0.0
        self.logo = crear_icono_app().pixmap(192, 192)
        self.anim = animacion(self, self._paso, self.DURACION, QEasingCurve.Type.Linear)
        self.anim.finished.connect(self.terminado)
        self.reloj = QTimer(self, interval=16)  # el anillo gira aunque la animación principal termine
        self.reloj.timeout.connect(self._girar)
        self.fundido = QPropertyAnimation(self, b"windowOpacity", self)
        self.fundido.setDuration(260)
        self.fundido.finished.connect(self.close)

    def mostrar(self):
        pantalla = QApplication.primaryScreen().geometry()
        if QApplication.platformName().startswith("wayland"):
            self.setGeometry(pantalla)  # Wayland no deja colocar ventanas: se ocupa la pantalla y se centra dentro
            self.showFullScreen()
        else:
            r = QRect(QPoint(0, 0), self.TARJETA)
            r.moveCenter(pantalla.center())
            self.setGeometry(r)
            self.show()
        animar(self.anim, 0.0, 1.0)
        self.reloj.start()

    def cerrar(self):
        self.reloj.stop()
        animar(self.fundido, 1.0, 0.0)

    def _paso(self, t):
        self.t = float(t)
        self.update()

    def _girar(self):
        self.giro = (self.giro + 5.5) % 360
        self.update()

    @staticmethod
    def _entre(t, desde, hasta):
        """0→1 entre dos instantes de la animación, con salida suave."""
        x = max(0.0, min(1.0, (t - desde) / (hasta - desde)))
        return 1 - (1 - x) ** 3

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        caja = QRectF(QPointF(0, 0), QSizeF(self.TARJETA))
        caja.moveCenter(QRectF(self.rect()).center())
        aparece = self._entre(self.t, 0.0, 0.18)
        p.setOpacity(aparece)
        # tarjeta con resplandor de los colores del tema
        p.setPen(QPen(QColor(C["borde_fuerte"]), 1))
        p.setBrush(QColor(C["hoja"]))
        p.drawRoundedRect(caja, 26, 26)
        p.save()
        recorte = QPainterPath()
        recorte.addRoundedRect(caja, 26, 26)
        p.setClipPath(recorte)
        centro = QPointF(caja.center().x(), caja.top() + 118)
        for color, dx, radio in ((T.a1, -70, 220), (T.a2, 80, 200)):
            g = QRadialGradient(centro + QPointF(dx + 18 * math.sin(math.radians(self.giro)), 10), radio)
            g.setColorAt(0, con_alfa(color, 0.32 * aparece))
            g.setColorAt(1, con_alfa(color, 0.0))
            p.fillRect(caja, g)
        p.restore()
        # logo que entra creciendo, con anillo de carga alrededor
        logo = self._entre(self.t, 0.05, 0.4)
        lado = 92 * (0.6 + 0.4 * logo)
        p.setOpacity(aparece * logo)
        p.drawPixmap(QRectF(centro.x() - lado / 2, centro.y() - lado / 2, lado, lado), self.logo, QRectF(self.logo.rect()))
        p.setOpacity(aparece)
        anillo = QRectF(centro.x() - 66, centro.y() - 66, 132, 132)
        p.setPen(QPen(velo(26), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(anillo)
        g = QConicalGradient(centro, -self.giro)
        g.setColorAt(0.0, QColor(T.a1))
        g.setColorAt(0.5, QColor(T.a2))
        g.setColorAt(1.0, con_alfa(T.a1, 0.0))
        pen = QPen(QBrush(g), 3.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(anillo, int(-self.giro * 16), int(-(90 + 200 * self.t) * 16))
        # textos
        titulo = self._entre(self.t, 0.3, 0.6)
        f = QFont(self.font())
        f.setPixelSize(38)
        f.setWeight(QFont.Weight.Light)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(f)
        p.setOpacity(aparece * titulo)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRectF(caja.left(), caja.top() + 196 + 12 * (1 - titulo), caja.width(), 46),
                   Qt.AlignmentFlag.AlignCenter, NOMBRE)
        frase = self._entre(self.t, 0.48, 0.8)
        f.setPixelSize(15)
        f.setWeight(QFont.Weight.Normal)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2.4 + 2 * (1 - frase))
        p.setFont(f)
        p.setOpacity(aparece * frase)
        g = QLinearGradient(caja.center().x() - 150, 0, caja.center().x() + 150, 0)
        g.setColorAt(0, QColor(T.a1).lighter(130))
        g.setColorAt(1, QColor(T.a2).lighter(115))
        p.setPen(QPen(QBrush(g), 1))
        p.drawText(QRectF(caja.left(), caja.top() + 248, caja.width(), 24), Qt.AlignmentFlag.AlignCenter, FRASE)
        if self.saludo:
            f.setPixelSize(13)
            f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.3)
            p.setFont(f)
            p.setOpacity(aparece * self._entre(self.t, 0.62, 0.9))
            p.setPen(QColor(C["tenue"]))
            p.drawText(QRectF(caja.left(), caja.top() + 278, caja.width(), 20), Qt.AlignmentFlag.AlignCenter, self.saludo)
        # barra de progreso
        p.setOpacity(aparece)
        barra = QRectF(caja.center().x() - 90, caja.bottom() - 26, 180, 3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(velo(26))
        p.drawRoundedRect(barra, 1.5, 1.5)
        g = QLinearGradient(barra.left(), 0, barra.right(), 0)
        g.setColorAt(0, QColor(T.a1))
        g.setColorAt(1, QColor(T.a2))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(barra.left(), barra.top(), barra.width() * self._entre(self.t, 0.0, 1.0), 3), 1.5, 1.5)
