"""Barra de direcciones."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403


# ═════════════════════════════ barra de direcciones

class Omnibox(QWidget):
    enviado = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setFixedHeight(40)
        self._f = 0.0
        self.anim = animacion(self, self._set, 220)
        self.proveedor = None
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 0, 6, 0)
        h.setSpacing(8)
        self.icono = QLabel()
        self.icono.setFont(Iconos.fuente(9.5))
        self.icono.setFixedWidth(18)
        self.entrada = QLineEdit(objectName="omniEntrada")
        self.entrada.setFrame(False)
        self.entrada.setPlaceholderText("Busca o escribe una dirección")
        self.estrella = BotonIcono("estrella", "Guardar en accesos (Ctrl+D)", tam=30, color_marcado="#ffc857")
        self.estrella.setCheckable(True)
        self.llave = BotonIcono("llave", "Contraseñas guardadas para este sitio", tam=30)
        self.llave.hide()
        h.addWidget(self.icono)
        h.addWidget(self.entrada, 1)
        h.addWidget(self.llave)
        h.addWidget(self.estrella)
        self.entrada.installEventFilter(self)
        self.entrada.returnPressed.connect(lambda: self.enviado.emit(self.entrada.text()))
        self.modelo = QStringListModel(self)
        self.comp = QCompleter(self.modelo, self)
        self.comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self.comp.setMaxVisibleItems(8)
        self.comp.popup().setObjectName("popupOmni")
        self.entrada.setCompleter(self.comp)

    def _set(self, v):
        self._f = v
        self.update()

    def eventFilter(self, obj, e):
        if obj is self.entrada:
            if e.type() == QEvent.Type.FocusIn:
                animar(self.anim, self._f, 1.0)
                QTimer.singleShot(0, self.entrada.selectAll)
                if self.proveedor:
                    self.modelo.setStringList(self.proveedor())
            elif e.type() == QEvent.Type.FocusOut:
                animar(self.anim, self._f, 0.0)
        return False

    def set_url(self, url, nueva):
        if self.entrada.hasFocus():
            return
        self.entrada.setText("" if nueva else url.toString())
        self.entrada.setCursorPosition(0)
        if nueva:
            glifo, color, consejo = "buscar", C["tenue"], ""
        elif url.scheme() == "https":
            glifo, color, consejo = "candado", "#6ee7a8", "Conexión segura (HTTPS)"
        elif url.host() in ("localhost", "127.0.0.1"):
            glifo, color, consejo = "dev", T.a2, "Servidor local"
        elif url.scheme() == "http":
            glifo, color, consejo = "info", "#ffc857", "Conexión no segura (HTTP)"
        else:
            glifo, color, consejo = "info", C["tenue"], ""
        self.icono.setText(Iconos.glifo(glifo))
        self.icono.setStyleSheet(f"color:{color}")
        self.icono.setToolTip(consejo)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(3, 3, -3, -3)
        radio = r.height() / 2
        if self._f > 0.01:
            p.setPen(QPen(con_alfa(T.a1, 0.22 * self._f), 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-1, -1, 1, 1), radio + 1, radio + 1)
        p.setPen(QPen(mezcla(C["borde"], T.a1, self._f), 1.2))
        p.setBrush(mezcla(C["chip"], "#1c2130", self._f))
        p.drawRoundedRect(r, radio, radio)
