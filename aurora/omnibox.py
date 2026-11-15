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
        self.entrada.returnPressed.connect(self._enter)
        self.entrada.textEdited.connect(self._escrito)
        self.popup = PopupSugerencias(self)

    def _set(self, v):
        self._f = v
        self.update()

    def eventFilter(self, obj, e):
        if obj is self.entrada:
            if e.type() == QEvent.Type.FocusIn:
                animar(self.anim, self._f, 1.0)
                QTimer.singleShot(0, self.entrada.selectAll)
            elif e.type() == QEvent.Type.FocusOut:
                animar(self.anim, self._f, 0.0)
                self.popup.ocultar()
            elif e.type() == QEvent.Type.KeyPress and self.popup.isVisible():
                k = e.key()
                if k in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                    self.popup.mover(1 if k == Qt.Key.Key_Down else -1)
                    return True
                if k == Qt.Key.Key_Escape:
                    self.popup.ocultar()
                    return True
                if k == Qt.Key.Key_Tab:
                    d = self.popup.actual()
                    if d and d["tipo"] not in ("buscar", "ir"):
                        self.entrada.setText(d["url"])
                        self._escrito(d["url"])
                    return True
        return False

    def _escrito(self, texto):
        if self.proveedor and texto.strip():
            self.popup.mostrar(self.proveedor(texto), texto)
        else:
            self.popup.ocultar()

    def _enter(self):
        d = self.popup.actual() if self.popup.isVisible() else None
        self.popup.ocultar()
        if d and d.get("accion"):
            d["accion"]()
        elif d and d["tipo"] not in ("buscar", "ir"):
            self.enviado.emit(d["url"])
        else:
            self.enviado.emit(self.entrada.text())

    def elegir(self, d):
        self.popup.ocultar()
        if d.get("accion"):
            d["accion"]()
        else:
            self.enviado.emit(self.entrada.text() if d["tipo"] in ("buscar", "ir") else d["url"])

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
        p.setBrush(mezcla(C["chip"], C["aviso"], self._f))
        p.drawRoundedRect(r, radio, radio)


ETIQUETAS = {"pestana": "Pestaña abierta", "acceso": "★ Acceso", "historial": "Historial"}


class DelegadoSugerencia(QStyledItemDelegate):
    """Fila del desplegable: icono, título con lo buscado resaltado, dirección y tipo."""

    def __init__(self, padre):
        super().__init__(padre)
        self.q = []

    def sizeHint(self, opcion, indice):
        return QSize(0, 48)

    def _resaltado(self, texto, color):
        partes, i, bajo = [], 0, texto.lower()
        tramos = sorted((bajo.find(q), len(q)) for q in self.q if q and bajo.find(q) >= 0)
        for ini, n in tramos:
            if ini < i:
                continue
            partes.append(html.escape(texto[i:ini]))
            partes.append(f"<b style='color:{color}'>{html.escape(texto[ini:ini + n])}</b>")
            i = ini + n
        partes.append(html.escape(texto[i:]))
        return "".join(partes)

    def _texto(self, p, rect, contenido, fuente, color):
        doc = QTextDocument()
        doc.setDefaultFont(fuente)
        doc.setDocumentMargin(0)
        doc.setHtml(f"<span style='color:{color};white-space:pre'>{contenido}</span>")
        p.save()
        p.setClipRect(rect)
        p.translate(rect.left(), rect.center().y() - doc.size().height() / 2)
        doc.drawContents(p)
        p.restore()

    def paint(self, p, opcion, indice):
        d = indice.data(Qt.ItemDataRole.UserRole)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opcion.rect).adjusted(4, 2, -4, -2)
        sel = bool(opcion.state & QStyle.StateFlag.State_Selected)
        if sel or opcion.state & QStyle.StateFlag.State_MouseOver:
            p.setPen(Qt.PenStyle.NoPen)
            if sel:
                g = QLinearGradient(r.left(), 0, r.right(), 0)
                g.setColorAt(0, con_alfa(T.a1, 0.30))
                g.setColorAt(1, con_alfa(T.a2, 0.07))
                p.setBrush(g)
            else:
                p.setBrush(velo(12))
            p.drawRoundedRect(r, 10, 10)
        icono = QRectF(r.left() + 10, r.center().y() - 14, 28, 28)
        if d["tipo"] in ("buscar", "ir"):
            g = QLinearGradient(icono.topLeft(), icono.bottomRight())
            g.setColorAt(0, QColor(T.a1))
            g.setColorAt(1, QColor(T.a2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(icono, 9, 9)
            p.setPen(QColor("white"))
            p.setFont(Iconos.fuente(10))
            p.drawText(icono, Qt.AlignmentFlag.AlignCenter, Iconos.glifo("buscar" if d["tipo"] == "buscar" else "abrir"))
        else:
            pintar_avatar(p, icono, Favicons.host(d["url"]) or d["titulo"], favicons().icono(d["url"]), redondo=False)
        izq = icono.right() + 12
        etiqueta = "↵  Enter" if sel else ETIQUETAS.get(d["tipo"], "")
        fm = QFontMetrics(opcion.font)
        derecha = r.right() - 14 - fm.horizontalAdvance(etiqueta)
        ancho = QRectF(izq, r.top(), derecha - izq - 12, r.height())
        negrita = QFont(opcion.font)
        negrita.setWeight(QFont.Weight.DemiBold)
        if d["tipo"] == "buscar":
            self._texto(p, ancho, f"<b>{html.escape(d['titulo'])}</b> <span style='color:{C['tenue']}'>— Buscar en "
                                  f"{html.escape(d['motor'])}</span>", opcion.font, C["texto"])
        elif d["tipo"] == "ir":
            self._texto(p, ancho, f"<span style='color:{C['tenue']}'>Ir a</span> <b>{html.escape(d['titulo'])}</b>",
                        opcion.font, C["texto"])
        else:
            arriba = QRectF(izq, r.top() + 5, ancho.width(), 20)
            abajo = QRectF(izq, r.top() + 24, ancho.width(), 18)
            titulo = fm.elidedText(d["titulo"] or d["url"], Qt.TextElideMode.ElideRight, int(ancho.width()))
            self._texto(p, arriba, self._resaltado(titulo, T.a2), negrita, C["texto"])
            url = d["url"].split("://", 1)[-1].removeprefix("www.")
            url = fm.elidedText(url, Qt.TextElideMode.ElideMiddle, int(ancho.width()))
            self._texto(p, abajo, self._resaltado(url, T.a2), opcion.font, C["tenue"])
        if etiqueta:
            p.setPen(QColor(T.a2 if sel else C["tenue"]))
            p.setFont(opcion.font)
            p.drawText(QRectF(derecha, r.top(), r.right() - derecha - 10, r.height()),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, etiqueta)
        p.restore()


class PopupSugerencias(QFrame):
    """Desplegable bajo la barra de direcciones. Es una capa dentro de la ventana (no roba el foco)."""

    def __init__(self, omni):
        super().__init__(objectName="popupSugerencias")
        self.omni = omni
        self.hide()
        l = QVBoxLayout(self)
        l.setContentsMargins(6, 6, 6, 6)
        self.lista = QListWidget(objectName="listaSugerencias")
        self.lista.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.lista.setMouseTracking(True)
        self.lista.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.delegado = DelegadoSugerencia(self.lista)
        self.lista.setItemDelegate(self.delegado)
        self.lista.itemClicked.connect(lambda it: self.omni.elegir(it.data(Qt.ItemDataRole.UserRole)))
        l.addWidget(self.lista)
        self.setGraphicsEffect(QGraphicsDropShadowEffect(self, blurRadius=36, offset=QPointF(0, 12),
                                                         color=QColor(0, 0, 0, 150)))
        favicons().listo.connect(lambda _: self.lista.viewport().update())

    def mostrar(self, resultados, texto):
        if not resultados:
            self.ocultar()
            return
        ventana = self.omni.window()
        if self.parent() is not ventana:
            self.setParent(ventana)
        self.delegado.q = texto.lower().split()
        self.lista.clear()
        for d in resultados:
            it = QListWidgetItem()
            it.setData(Qt.ItemDataRole.UserRole, d)
            self.lista.addItem(it)
        self.lista.setCurrentRow(0)
        pos = self.omni.mapTo(ventana, QPoint(0, self.omni.height() + 4))
        self.setGeometry(pos.x(), pos.y(), self.omni.width(), 12 + 48 * len(resultados) + 2)
        self.show()
        self.raise_()

    def ocultar(self):
        self.hide()

    def actual(self):
        it = self.lista.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def mover(self, paso):
        self.lista.setCurrentRow((self.lista.currentRow() + paso) % self.lista.count())
