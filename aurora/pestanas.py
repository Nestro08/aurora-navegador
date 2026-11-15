"""Barra de pestañas propia: pestañas animadas, fijadas, grupos de colores, sonido y arrastre."""
import time

from .widgets import *  # noqa: F401,F403

ANCHO_FIJADA = 42
COLORES_GRUPO = {
    "Gris": "#8a90a2", "Azul": "#3b82f6", "Rojo": "#f43f5e", "Amarillo": "#f59e0b", "Verde": "#22c55e",
    "Rosa": "#ec4899", "Morado": "#8b5cf6", "Cian": "#06b6d4", "Naranja": "#f97316",
}


class Chip(QWidget):
    """Una pestaña: icono (o spinner al cargar), sonido, título y botón cerrar."""

    def __init__(self, tira, pagina):
        super().__init__(tira)
        self.tira, self.pagina = tira, pagina
        self.titulo, self.icono = "Nueva pestaña", QIcon()
        self.activo = self.cargando = False
        self.fijada = self.dormida = self.sonando = self.silenciada = self.dividida = False
        self.grupo = None
        self.progreso = 0
        self.ultimo_uso = time.time()
        self._h = self._a = self._giro = 0.0
        self._sobre_x = self._sobre_audio = self._arrastrando = False
        self._pulsado = None
        self.setMouseTracking(True)
        self.anim_h = animacion(self, self._set_h, 150)
        self.anim_a = animacion(self, self._set_a, 260)
        self.anim_geo = QPropertyAnimation(self, b"geometry", self)
        self.anim_geo.setDuration(260)
        self.anim_geo.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.reloj = QTimer(self, interval=16)
        self.reloj.timeout.connect(self._girar)

    def _set_h(self, v):
        self._h = v
        self.update()

    def _set_a(self, v):
        self._a = v
        self.update()

    def _girar(self):
        self._giro = (self._giro + 8) % 360
        self.update()

    def set_activo(self, a):
        self.activo = a
        animar(self.anim_a, self._a, 1.0 if a else 0.0)

    def set_cargando(self, c):
        self.cargando = c
        self.reloj.start() if c else self.reloj.stop()
        self.update()

    # zonas clicables
    def rect_x(self):
        return QRectF(self.width() - 28, (self.height() - 20) / 2, 20, 20)

    def rect_audio(self):
        if self.fijada:
            return QRectF(self.width() - 15, 3, 13, 13)
        return QRectF(32, (self.height() - 18) / 2, 18, 18)

    def muestra_x(self):
        return not self.fijada and (self.width() > 100 or self.activo)

    def muestra_audio(self):
        return self.sonando or self.silenciada

    def enterEvent(self, e):
        animar(self.anim_h, self._h, 1.0)

    def leaveEvent(self, e):
        self._sobre_x = self._sobre_audio = False
        animar(self.anim_h, self._h, 0.0)

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.MouseButton.MiddleButton:
            self.tira.cerrar_pedido.emit(self)
        elif e.button() == Qt.MouseButton.RightButton:
            self.tira.menu_pedido.emit(self, e.globalPosition().toPoint())
        elif e.button() == Qt.MouseButton.LeftButton:
            self._pulsado, self._arrastrando = pos, False
            if self.muestra_audio() and self.rect_audio().contains(pos):
                self.tira.silenciar_pedido.emit(self)
                self._pulsado = None
            elif not (self.muestra_x() and self.rect_x().contains(pos)):
                self.tira.activar_pedido.emit(self)

    def mouseMoveEvent(self, e):
        pos = e.position()
        sobre_x = self.muestra_x() and self.rect_x().contains(pos)
        sobre_audio = self.muestra_audio() and self.rect_audio().contains(pos)
        if (sobre_x, sobre_audio) != (self._sobre_x, self._sobre_audio):
            self._sobre_x, self._sobre_audio = sobre_x, sobre_audio
            self.update()
        if self._pulsado is not None and e.buttons() & Qt.MouseButton.LeftButton:
            if not self._arrastrando and abs(pos.x() - self._pulsado.x()) > 6:
                self._arrastrando = True
                self.raise_()
            if self._arrastrando:
                x = self.mapToParent(pos.toPoint()).x() - int(self._pulsado.x())
                self.tira.arrastrar(self, x)

    def mouseReleaseEvent(self, e):
        if self._arrastrando:
            self.tira.soltar(self)
        elif self._pulsado is not None and self.muestra_x() and self.rect_x().contains(e.position()):
            self.tira.cerrar_pedido.emit(self)
        self._pulsado, self._arrastrando = None, False

    def mouseDoubleClickEvent(self, e):
        pass  # que el doble clic en una pestaña no abra otra

    def paintEvent(self, e):
        if self.width() < 10:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        fondo_tira = self.tira.fondo or C["fondo"]
        fondo = mezcla(fondo_tira, C["chip_activo"], self._a)
        fondo = mezcla(fondo, C["chip_hover"], self._h * (1 - self._a) * 0.9)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(fondo)
        p.drawRoundedRect(r, 10, 10)
        color_grupo = self.tira.color_grupo(self.grupo)
        if color_grupo:  # línea del color del grupo
            p.setBrush(con_alfa(color_grupo, 0.85))
            p.drawRoundedRect(QRectF(r.left() + 8, r.bottom() - 2.5, r.width() - 16, 2), 1, 1)
        if self._a > 0.01:  # subrayado con degradado que crece desde el centro
            ancho = (r.width() - (12 if self.fijada else 26)) * self._a
            g = QLinearGradient(r.center().x() - ancho / 2, 0, r.center().x() + ancho / 2, 0)
            g.setColorAt(0, QColor(color_grupo or T.a1))
            g.setColorAt(1, QColor(T.a2))
            p.setBrush(g)
            p.drawRoundedRect(QRectF(r.center().x() - ancho / 2, r.bottom() - 3, ancho, 2.5), 1.2, 1.2)
        if self.dormida:
            p.setOpacity(0.45)

        x = (r.width() - 16) / 2 if self.fijada else 12
        cy = r.center().y()
        if self.cargando:
            pen = QPen(QColor(T.a2), 2)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(QRectF(x + 1, cy - 7, 14, 14), int(-self._giro * 16), 260 * 16)
        elif not self.icono.isNull():
            self.icono.paint(p, QRect(int(x), int(cy - 8), 16, 16))
        else:
            g = QLinearGradient(x, cy - 7, x + 14, cy + 7)
            g.setColorAt(0, QColor(T.a1))
            g.setColorAt(1, QColor(T.a2))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawEllipse(QRectF(x + 1, cy - 7, 14, 14))

        izq = x + 24
        if self.muestra_audio():  # altavoz: clic para silenciar
            ra = self.rect_audio()
            if self._sobre_audio:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(velo(28))
                p.drawRoundedRect(ra.adjusted(-2, -2, 2, 2), 5, 5)
            p.setPen(QColor("#ff8b9c") if self.silenciada else QColor(T.a2))
            p.setFont(Iconos.fuente(7.5 if self.fijada else 8.5))
            p.drawText(ra, Qt.AlignmentFlag.AlignCenter, Iconos.glifo("silencio" if self.silenciada else "sonido"))
            izq = ra.right() + 6
        if self.fijada:
            return
        muestra_x = self.muestra_x()
        rx = self.rect_x()
        derecha = rx.left() - 4 if muestra_x else r.right() - 10
        if derecha - izq > 8:
            p.setPen(mezcla(C["tenue"], C["texto"], max(self._a, self._h * 0.7)))
            p.setFont(self.font())
            texto = QFontMetrics(self.font()).elidedText(self.titulo, Qt.TextElideMode.ElideRight, int(derecha - izq))
            p.drawText(QRectF(izq, r.top(), derecha - izq, r.height()),
                       Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, texto)
        p.setOpacity(1.0)
        alfa = max(self._a, self._h)
        if muestra_x and alfa > 0.02:
            if self._sobre_x:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(velo(28))
                p.drawRoundedRect(rx, 6, 6)
            pen = QPen(con_alfa(C["texto"], 0.85 * alfa), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(pen)
            c, d = rx.center(), 3.6
            p.drawLine(QPointF(c.x() - d, c.y() - d), QPointF(c.x() + d, c.y() + d))
            p.drawLine(QPointF(c.x() + d, c.y() - d), QPointF(c.x() - d, c.y() + d))


class EtiquetaGrupo(QWidget):
    """Píldora con el nombre y color del grupo. Clic: plegar/desplegar. Clic derecho: opciones."""

    def __init__(self, tira, gid):
        super().__init__(tira)
        self.tira, self.gid = tira, gid
        self._h = 0.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.anim_h = animacion(self, self._set, 150)
        self.anim_geo = QPropertyAnimation(self, b"geometry", self)
        self.anim_geo.setDuration(260)
        self.anim_geo.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _set(self, v):
        self._h = v
        self.update()

    def datos(self):
        return self.tira.grupos.get(self.gid, {"nombre": "", "color": "#8a90a2", "plegado": False})

    def texto(self):
        d = self.datos()
        n = sum(1 for c in self.tira.chips if c.grupo == self.gid)
        return f"{d['nombre'] or ' '}  ·  {n}" if d["plegado"] else (d["nombre"] or " ")

    def ancho(self):
        return QFontMetrics(self.font()).horizontalAdvance(self.texto()) + 26

    def enterEvent(self, e):
        animar(self.anim_h, self._h, 1.0)

    def leaveEvent(self, e):
        animar(self.anim_h, self._h, 0.0)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.tira.plegar_pedido.emit(self.gid)
        elif e.button() == Qt.MouseButton.RightButton:
            self.tira.menu_grupo_pedido.emit(self.gid, e.globalPosition().toPoint())

    def paintEvent(self, e):
        if self.width() < 8:
            return
        d = self.datos()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 5, -1, -5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(con_alfa(d["color"], 0.22 + 0.12 * self._h))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        p.setPen(mezcla(d["color"], "#ffffff", 0.35))
        f = QFont(self.font())
        f.setWeight(QFont.Weight.DemiBold)
        p.setFont(f)
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.texto())


class Tira(QWidget):
    """Barra de pestañas: coloca pestañas y grupos con animación y permite arrastrar."""
    activar_pedido = pyqtSignal(object)
    cerrar_pedido = pyqtSignal(object)
    nueva_pedida = pyqtSignal()
    menu_pedido = pyqtSignal(object, QPoint)
    menu_grupo_pedido = pyqtSignal(str, QPoint)
    plegar_pedido = pyqtSignal(str)
    silenciar_pedido = pyqtSignal(object)

    def __init__(self, padre):
        super().__init__(padre)
        self.setFixedHeight(46)
        self.chips, self.grupos, self.etiquetas = [], {}, {}
        self.fondo = None  # None = el del tema (en incógnito se fija otro)
        self.ancho = 200
        self._destinos = {}
        self.integrada, self.controles, self.reserva = False, None, 0  # barra de título propia
        self._pulsado = None
        self.boton_mas = BotonIcono("mas", "Nueva pestaña (Ctrl+T)", self, 32)
        self.boton_mas.clicked.connect(self.nueva_pedida)
        self.anim_mas = QPropertyAnimation(self.boton_mas, b"pos", self)
        self.anim_mas.setDuration(260)
        self.anim_mas.setEasingCurve(QEasingCurve.Type.OutCubic)

    def poner_controles(self, controles):
        """Convierte la tira en barra de título: botones de ventana a la derecha y arrastrar para mover."""
        self.integrada, self.controles = True, controles
        controles.setParent(self)
        controles.show()
        self.reserva = controles.width() + 16
        self.resizeEvent(None)

    def color_grupo(self, gid):
        return self.grupos[gid]["color"] if gid in self.grupos else None

    def plegada(self, chip):
        return bool(chip.grupo in self.grupos and self.grupos[chip.grupo]["plegado"])

    def agregar(self, chip, indice):
        self.chips.insert(indice, chip)
        self.normalizar()
        self._calcular()
        destino = self._diseno().get(chip, QRect(8, 7, 0, 34))
        chip.setGeometry(destino.x() + destino.width() // 2, 7, 0, 34)
        chip.show()
        self.recolocar()

    def quitar(self, chip):
        self.chips.remove(chip)
        chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        g = chip.geometry()
        chip.anim_geo.stop()
        chip.anim_geo.setDuration(200)
        chip.anim_geo.setStartValue(g)
        chip.anim_geo.setEndValue(QRect(g.x() + g.width() // 2, g.y(), 0, g.height()))
        chip.anim_geo.finished.connect(chip.deleteLater)
        chip.anim_geo.start()
        self.limpiar_grupos()
        self.recolocar()

    def normalizar(self):
        """Fijadas primero y cada grupo con sus pestañas juntas, respetando el orden."""
        fijadas = [c for c in self.chips if c.fijada]
        resto, vistos = [], set()
        for c in self.chips:
            if c.fijada or c in vistos:
                continue
            if c.grupo:
                miembros = [x for x in self.chips if x.grupo == c.grupo and not x.fijada]
                resto += miembros
                vistos.update(miembros)
            else:
                resto.append(c)
                vistos.add(c)
        self.chips[:] = fijadas + resto

    def limpiar_grupos(self):
        usados = {c.grupo for c in self.chips if c.grupo}
        for gid in list(self.grupos):
            if gid not in usados:
                del self.grupos[gid]
        for gid in list(self.etiquetas):
            if gid not in self.grupos:
                self.etiquetas.pop(gid).deleteLater()

    def _calcular(self):
        fijo = 10 + 46
        normales = 0
        previo = None
        for c in self.chips:
            if c.grupo != previo and c.grupo in self.grupos:
                fijo += self._etiqueta(c.grupo).ancho() + 4
            previo = c.grupo
            if c.fijada:
                fijo += ANCHO_FIJADA + 4
            elif not self.plegada(c):
                normales += 1
        self.ancho = int(max(56, min(232, (self.width() - fijo - self.reserva) / max(1, normales))))

    def _etiqueta(self, gid):
        if gid not in self.etiquetas:
            e = EtiquetaGrupo(self, gid)
            e.setGeometry(8, 7, 0, 34)
            e.show()
            self.etiquetas[gid] = e
        return self.etiquetas[gid]

    def _diseno(self):
        destinos = {}
        x, previo = 8, None
        for c in self.chips:
            if c.grupo != previo and c.grupo in self.grupos:
                e = self._etiqueta(c.grupo)
                destinos[e] = QRect(x, 7, e.ancho(), 34)
                x += e.ancho() + 4
            previo = c.grupo
            if c.fijada:
                destinos[c] = QRect(x, 7, ANCHO_FIJADA, 34)
                x += ANCHO_FIJADA + 4
            elif self.plegada(c):
                destinos[c] = QRect(x, 7, 0, 34)
            else:
                destinos[c] = QRect(x, 7, self.ancho - 4, 34)
                x += self.ancho
        destinos[self.boton_mas] = QRect(x + 2, 8, 32, 32)
        return destinos

    def recolocar(self, animado=True, excepto=None):
        self._calcular()
        self._destinos = self._diseno()
        for w, destino in self._destinos.items():
            if w is self.boton_mas:
                pos = destino.topLeft()
                if animado:
                    animar(self.anim_mas, self.boton_mas.pos(), pos)
                elif self.anim_mas.state() == QPropertyAnimation.State.Running:
                    self.anim_mas.setEndValue(pos)
                else:
                    self.boton_mas.move(pos)
                continue
            if w is excepto:
                continue
            w.setVisible(destino.width() > 0 or w.width() > 0)
            if animado:
                w.anim_geo.stop()
                w.anim_geo.setDuration(260)
                w.anim_geo.setStartValue(w.geometry())
                w.anim_geo.setEndValue(destino)
                w.anim_geo.start()
            elif w.anim_geo.state() == QPropertyAnimation.State.Running:
                w.anim_geo.setEndValue(destino)
            else:
                w.setGeometry(destino)
        for e in self.etiquetas.values():
            e.update()

    def arrastrar(self, chip, x):
        chip.anim_geo.stop()
        x = max(4, min(x, self.width() - chip.width() - 46 - self.reserva))
        chip.move(x, chip.y())
        centro = x + chip.width() / 2
        otros = [c for c in self.chips if c is not chip and c.fijada == chip.fijada]
        antes = sum(1 for c in otros if c in self._destinos and self._destinos[c].center().x() < centro)
        zona = [c for c in self.chips if c.fijada == chip.fijada]
        inicio = 0 if chip.fijada else sum(1 for c in self.chips if c.fijada)
        nuevo = inicio + antes
        viejo = self.chips.index(chip)
        if nuevo != viejo and len(zona) > 1:
            self.chips.insert(nuevo, self.chips.pop(viejo))
            self.recolocar(excepto=chip)

    def soltar(self, chip):
        """Al soltar, la pestaña entra o sale del grupo según dónde haya caído."""
        if not chip.fijada:
            i = self.chips.index(chip)
            previo = self.chips[i - 1] if i > 0 else None
            siguiente = self.chips[i + 1] if i + 1 < len(self.chips) else None
            g_prev = previo.grupo if previo else None
            g_sig = siguiente.grupo if siguiente else None
            if chip.grupo and chip.grupo not in (g_prev, g_sig):
                if any(c.grupo == chip.grupo for c in self.chips if c is not chip):
                    chip.grupo = None
            elif not chip.grupo and g_prev and g_prev == g_sig:
                chip.grupo = g_prev
        self.normalizar()
        self.limpiar_grupos()
        self.recolocar()

    def resizeEvent(self, e):
        if self.controles:
            self.controles.move(self.width() - self.controles.width() - 8, (self.height() - self.controles.height()) // 2)
        self.recolocar(False)

    def mousePressEvent(self, e):
        if self.integrada and e.button() == Qt.MouseButton.LeftButton:
            self._pulsado = e.position().toPoint()

    def mouseMoveEvent(self, e):
        # se empieza a mover al arrastrar un poco, para no tragarse el doble clic
        if self._pulsado is not None and (e.position().toPoint() - self._pulsado).manhattanLength() > 4:
            self._pulsado = None
            self.window().windowHandle().startSystemMove()

    def mouseReleaseEvent(self, e):
        self._pulsado = None

    def mouseDoubleClickEvent(self, e):
        if self.integrada:
            self.controles.alternar()
        else:
            self.nueva_pedida.emit()
