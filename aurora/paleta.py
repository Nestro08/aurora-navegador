"""Paleta de comandos (Ctrl+K) y buscador en la página (Ctrl+F)."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403


# ═════════════════════════════ paleta de comandos

class DelegadoPaleta(QStyledItemDelegate):
    COLORES = {"Ir": "#22d3ee", "Pestaña": "#7c5cff", "Comando": "#a5e88a", "Marcador": "#ffc857",
               "Historial": "#ff8fb1"}

    def sizeHint(self, opcion, indice):
        return QSize(0, 48)

    def paint(self, p, opcion, indice):
        tipo, titulo, detalle, atajo = indice.data(Qt.ItemDataRole.UserRole)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opcion.rect).adjusted(4, 2, -4, -2)
        if opcion.state & QStyle.StateFlag.State_Selected:
            g = QLinearGradient(r.left(), 0, r.right(), 0)
            g.setColorAt(0, con_alfa(T.a1, 0.30))
            g.setColorAt(1, con_alfa(T.a2, 0.10))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(r, 10, 10)
        pequena = QFont(opcion.font)
        pequena.setPointSizeF(opcion.font.pointSizeF() * 0.82)
        color = QColor(self.COLORES.get(tipo, C["tenue"]))
        etiqueta = QRectF(r.left() + 10, r.center().y() - 10, 74, 20)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(con_alfa(color, 0.14))
        p.drawRoundedRect(etiqueta, 6, 6)
        p.setPen(color)
        p.setFont(pequena)
        p.drawText(etiqueta, Qt.AlignmentFlag.AlignCenter, tipo)
        derecha = r.right() - 12
        if atajo:
            ancho = QFontMetrics(pequena).horizontalAdvance(atajo) + 14
            caja = QRectF(derecha - ancho, r.center().y() - 10, ancho, 20)
            p.setPen(QPen(QColor(C["borde"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(caja, 6, 6)
            p.setPen(QColor(C["tenue"]))
            p.drawText(caja, Qt.AlignmentFlag.AlignCenter, atajo)
            derecha -= ancho + 10
        izq = etiqueta.right() + 12
        ancho_txt = int(derecha - izq)
        p.setFont(opcion.font)
        p.setPen(QColor(C["texto"]))
        fm = QFontMetrics(opcion.font)
        if detalle:
            p.drawText(QRectF(izq, r.top() + 4, ancho_txt, r.height() / 2),
                       Qt.AlignmentFlag.AlignBottom, fm.elidedText(titulo, Qt.TextElideMode.ElideRight, ancho_txt))
            p.setFont(pequena)
            p.setPen(QColor(C["tenue"]))
            p.drawText(QRectF(izq, r.center().y() + 1, ancho_txt, r.height() / 2 - 4),
                       Qt.AlignmentFlag.AlignTop,
                       QFontMetrics(pequena).elidedText(detalle, Qt.TextElideMode.ElideMiddle, ancho_txt))
        else:
            p.drawText(QRectF(izq, r.top(), ancho_txt, r.height()), Qt.AlignmentFlag.AlignVCenter,
                       fm.elidedText(titulo, Qt.TextElideMode.ElideRight, ancho_txt))
        p.restore()


class Paleta(QWidget):
    """Ctrl+K: buscador universal de comandos, pestañas, marcadores e historial."""

    def __init__(self, padre, ventana):
        super().__init__(padre)
        self.v, self.fuente, self._abierta = ventana, None, False
        self.hide()
        self.efecto = QGraphicsOpacityEffect(self)
        self.efecto.setOpacity(0)
        self.setGraphicsEffect(self.efecto)
        self.tarjeta = QFrame(self, objectName="tarjeta")
        l = QVBoxLayout(self.tarjeta)
        l.setContentsMargins(10, 8, 10, 10)
        l.setSpacing(4)
        self.entrada = QLineEdit(objectName="paletaEntrada")
        self.lista = QListWidget(objectName="paletaLista")
        self.lista.setItemDelegate(DelegadoPaleta(self.lista))
        self.lista.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.lista.setUniformItemSizes(True)
        self.lista.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        l.addWidget(self.entrada)
        l.addWidget(self.lista)
        self.entrada.textChanged.connect(self.filtrar)
        self.entrada.installEventFilter(self)
        self.lista.itemClicked.connect(self.ejecutar)
        self.anim_o = QPropertyAnimation(self.efecto, b"opacity", self)
        self.anim_o.setDuration(170)
        self.anim_o.finished.connect(lambda: None if self._abierta else self.hide())
        self.anim_p = QPropertyAnimation(self.tarjeta, b"pos", self)
        self.anim_p.setDuration(260)
        self.anim_p.setEasingCurve(QEasingCurve.Type.OutCubic)

    def abrir(self, fuente, ayuda, texto=""):
        self.fuente = fuente
        self.entrada.setPlaceholderText(ayuda)
        self.setGeometry(self.parentWidget().rect())
        self.colocar()
        destino = self.tarjeta.pos()
        self.show()
        self.raise_()
        self.entrada.blockSignals(True)
        self.entrada.setText(texto)
        self.entrada.blockSignals(False)
        self.filtrar(texto)
        self.entrada.setFocus()
        self._abierta = True
        animar(self.anim_p, destino - QPoint(0, 18), destino)
        animar(self.anim_o, self.efecto.opacity(), 1.0)

    def colocar(self):
        w, h = min(700, self.width() - 40), min(470, self.height() - 120)
        self.tarjeta.setGeometry((self.width() - w) // 2, 70, w, h)

    def cerrar(self):
        if not self._abierta:
            return
        self._abierta = False
        animar(self.anim_o, self.efecto.opacity(), 0.0)
        self.v.enfocar_pagina()

    def filtrar(self, texto):
        self.lista.clear()
        for tipo, titulo, detalle, atajo, accion in (self.fuente(texto) if self.fuente else [])[:80]:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, (tipo, titulo, detalle, atajo))
            item.setData(Qt.ItemDataRole.UserRole + 1, accion)
            self.lista.addItem(item)
        if self.lista.count():
            self.lista.setCurrentRow(0)

    def ejecutar(self, item=None):
        item = item or self.lista.currentItem()
        if not item:
            return
        accion = item.data(Qt.ItemDataRole.UserRole + 1)
        self.cerrar()
        QTimer.singleShot(0, accion)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.KeyPress:
            k = e.key()
            if k in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                n = self.lista.count()
                if n:
                    paso = 1 if k == Qt.Key.Key_Down else -1
                    self.lista.setCurrentRow((self.lista.currentRow() + paso) % n)
                return True
            if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.ejecutar()
                return True
            if k == Qt.Key.Key_Escape:
                self.cerrar()
                return True
        return False

    def mousePressEvent(self, e):
        if not self.tarjeta.geometry().contains(e.position().toPoint()):
            self.cerrar()

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor(4, 5, 9, 150))


class BuscadorFlotante(QFrame):
    """Ctrl+F: buscar en la página con contador de coincidencias."""

    def __init__(self, padre, ventana):
        super().__init__(padre, objectName="buscador")
        self.v, self._abierto = ventana, False
        self.hide()
        self.setFixedSize(400, 46)
        h = QHBoxLayout(self)
        h.setContentsMargins(14, 4, 6, 4)
        h.setSpacing(2)
        self.entrada = QLineEdit(placeholderText="Buscar en la página")
        self.cuenta = QLabel("", objectName="tenue")
        arriba = BotonIcono("arriba", "Anterior (Shift+Enter)", tam=30)
        abajo = BotonIcono("abajo", "Siguiente (Enter)", tam=30)
        cerrar = BotonIcono("cerrar", "Cerrar (Esc)", tam=30)
        for w in (self.entrada, self.cuenta, arriba, abajo, cerrar):
            h.addWidget(w, 1 if w is self.entrada else 0)
        arriba.clicked.connect(lambda: self.buscar(True))
        abajo.clicked.connect(lambda: self.buscar())
        cerrar.clicked.connect(self.cerrar)
        self.entrada.textChanged.connect(lambda: self.buscar())
        self.entrada.installEventFilter(self)
        sombra = QGraphicsDropShadowEffect(self, blurRadius=30, offset=QPointF(0, 8), color=QColor(0, 0, 0, 160))
        self.setGraphicsEffect(sombra)
        self.anim_p = QPropertyAnimation(self, b"pos", self)
        self.anim_p.setDuration(260)
        self.anim_p.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim_out = QPropertyAnimation(self, b"pos", self)
        self.anim_out.setDuration(180)
        self.anim_out.finished.connect(lambda: None if self._abierto else self.hide())

    def destino(self):
        return QPoint(self.v.pila.width() - self.width() - 18, 12)

    def recolocar(self):
        if self._abierto:
            self.move(self.destino())

    def abrir(self):
        self._abierto = True
        d = self.destino()
        if not self.isVisible():
            self.move(d.x(), -self.height())
        self.show()
        self.raise_()
        animar(self.anim_p, self.pos(), d)
        self.entrada.setFocus()
        self.entrada.selectAll()
        if self.entrada.text():
            self.buscar()

    def cerrar(self):
        if not self._abierto:
            return
        self._abierto = False
        animar(self.anim_out, self.pos(), QPoint(self.x(), -self.height() - 10))
        self.v.vista().findText("")
        self.cuenta.setText("")
        self.v.enfocar_pagina()

    def buscar(self, atras=False):
        texto = self.entrada.text()
        pagina = self.v.vista().page()
        if atras:
            pagina.findText(texto, QWebEnginePage.FindFlag.FindBackward)
        else:
            pagina.findText(texto)
        if not texto:
            self.cuenta.setText("")

    def resultado(self, r):
        if not self._abierto or not self.entrada.text():
            return
        n = r.numberOfMatches()
        self.cuenta.setText(f"{r.activeMatch()}/{n}  " if n else "Sin resultados  ")

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.KeyPress:
            if e.key() == Qt.Key.Key_Escape:
                self.cerrar()
                return True
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.buscar(bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier))
                return True
        return False
