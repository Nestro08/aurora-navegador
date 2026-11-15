"""Gestor de descargas: botón con anillo de progreso y panel con pausar, reanudar y cancelar."""
import time

from .widgets import *  # noqa: F401,F403

EMOJIS = {("pdf",): "📕", ("zip", "rar", "7z", "tar", "gz"): "🗜", ("exe", "msi"): "⚙",
          ("png", "jpg", "jpeg", "gif", "webp", "svg"): "🖼", ("mp4", "mkv", "avi", "mov", "webm"): "🎬",
          ("mp3", "wav", "flac", "ogg", "m4a"): "🎵", ("doc", "docx", "odt"): "📄", ("xls", "xlsx", "csv"): "📊",
          ("ppt", "pptx"): "📽", ("py", "java", "c", "js", "html", "css", "json"): "🧾"}
D = QWebEngineDownloadRequest.DownloadState


def tamano(b):
    b = float(b or 0)
    for u in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}".replace(".", ",")
        b /= 1024
    return f"{b:.1f} TB".replace(".", ",")


def duracion(s):
    s = int(s)
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s // 3600} h {s % 3600 // 60:02d} min"


def emoji(nombre):
    ext = nombre.rsplit(".", 1)[-1].lower() if "." in nombre else ""
    return next((e for exts, e in EMOJIS.items() if ext in exts), "📦")


class BarraFina(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(4)
        self.valor, self.pausada, self.error = 0.0, False, False
        self._v = 0.0
        self.anim = animacion(self, self._set, 300)

    def _set(self, v):
        self._v = v
        self.update()

    def fijar(self, valor):
        self.valor = valor
        animar(self.anim, self._v, valor)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect())
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C["borde"]))
        p.drawRoundedRect(r, 2, 2)
        if self._v > 0:
            g = QLinearGradient(0, 0, r.width(), 0)
            if self.error:
                g.setColorAt(0, QColor("#ff6b81"))
                g.setColorAt(1, QColor("#ff6b81"))
            elif self.pausada:
                g.setColorAt(0, QColor(C["tenue"]))
                g.setColorAt(1, QColor(C["tenue"]))
            else:
                g.setColorAt(0, QColor(T.a1))
                g.setColorAt(1, QColor(T.a2))
            p.setBrush(g)
            p.drawRoundedRect(QRectF(0, 0, r.width() * min(1.0, self._v), r.height()), 2, 2)


class ItemDescarga(QFrame):
    def __init__(self, ventana, d):
        super().__init__(objectName="itemDescarga")
        self.v, self.d = ventana, d
        self._inicio, self._ultimo = time.time(), (time.time(), 0)
        self._velocidad = 0.0
        h = QHBoxLayout(self)
        h.setContentsMargins(12, 10, 8, 10)
        h.setSpacing(10)
        icono = QLabel(emoji(d.downloadFileName()))
        icono.setStyleSheet("font-size:20pt")
        h.addWidget(icono)
        cuerpo = QVBoxLayout()
        cuerpo.setSpacing(5)
        self.nombre = QLabel()
        self.barra = BarraFina()
        self.estado = QLabel(objectName="tenue")
        cuerpo.addWidget(self.nombre)
        cuerpo.addWidget(self.barra)
        cuerpo.addWidget(self.estado)
        h.addLayout(cuerpo, 1)
        self.b_pausa = BotonIcono("pausa", "Pausar", tam=30)
        self.b_cancelar = BotonIcono("cerrar", "Cancelar", tam=30)
        self.b_abrir = BotonIcono("abrir", "Abrir", tam=30)
        self.b_carpeta = BotonIcono("carpeta", "Mostrar en la carpeta", tam=30)
        for b in (self.b_pausa, self.b_cancelar, self.b_abrir, self.b_carpeta):
            h.addWidget(b)
        self.b_pausa.clicked.connect(lambda: d.resume() if d.isPaused() else d.pause())
        self.b_cancelar.clicked.connect(d.cancel)
        self.b_abrir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.ruta())))
        self.b_carpeta.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(d.downloadDirectory())))
        d.receivedBytesChanged.connect(self.actualizar)
        d.totalBytesChanged.connect(self.actualizar)
        d.stateChanged.connect(self.actualizar)
        d.isPausedChanged.connect(self.actualizar)
        self.actualizar()

    def ruta(self):
        return str(Path(self.d.downloadDirectory()) / self.d.downloadFileName())

    def progreso(self):
        total = self.d.totalBytes()
        return self.d.receivedBytes() / total if total > 0 else None

    def activa(self):
        return self.d.state() in (D.DownloadInProgress, D.DownloadRequested)

    def actualizar(self, *_):
        d = self.d
        ancho = 230
        self.nombre.setText(QFontMetrics(self.font()).elidedText(d.downloadFileName(), Qt.TextElideMode.ElideMiddle, ancho))
        self.nombre.setToolTip(d.downloadFileName())
        recibido, total = d.receivedBytes(), d.totalBytes()
        ahora = time.time()
        t0, b0 = self._ultimo
        if ahora - t0 >= 0.7:
            instantanea = (recibido - b0) / (ahora - t0)
            self._velocidad = instantanea if not self._velocidad else 0.7 * self._velocidad + 0.3 * instantanea
            self._ultimo = (ahora, recibido)
        estado = d.state()
        self.barra.pausada, self.barra.error = d.isPaused(), estado in (D.DownloadInterrupted, D.DownloadCancelled)
        en_curso = estado == D.DownloadInProgress
        if estado == D.DownloadCompleted:
            self.barra.fijar(1.0)
            self.estado.setText(f"✓  {tamano(total or recibido)} · completada")
        elif estado == D.DownloadCancelled:
            self.estado.setText("Cancelada")
        elif estado == D.DownloadInterrupted:
            self.estado.setText(f"Interrumpida: {d.interruptReasonString()}")
        elif d.isPaused():
            self.estado.setText(f"⏸  En pausa · {tamano(recibido)}" + (f" de {tamano(total)}" if total > 0 else ""))
        else:
            texto = tamano(recibido) + (f" de {tamano(total)}" if total > 0 else "")
            if self._velocidad > 0:
                texto += f" · {tamano(self._velocidad)}/s"
                if total > 0:
                    texto += f" · quedan {duracion((total - recibido) / self._velocidad)}"
            self.estado.setText(texto)
        if total > 0 and estado != D.DownloadCompleted:
            self.barra.fijar(recibido / total)
        self.b_pausa.setVisible(en_curso)
        self.b_pausa.set_icono("play" if d.isPaused() else "pausa")
        self.b_pausa.setToolTip("Reanudar" if d.isPaused() else "Pausar")
        self.b_cancelar.setVisible(en_curso)
        self.b_abrir.setVisible(estado == D.DownloadCompleted)
        self.b_carpeta.setVisible(estado == D.DownloadCompleted)
        self.v.boton_descargas.refrescar()


class BotonDescargas(BotonIcono):
    """Botón de la barra con un anillo que muestra el progreso total."""

    def __init__(self, ventana):
        super().__init__("descarga", "Descargas")
        self.v = ventana
        self._giro = 0.0
        self.reloj = QTimer(self, interval=30)
        self.reloj.timeout.connect(self._girar)
        self._pulso = 0.0
        self.anim_pulso = animacion(self, self._set_pulso, 700, QEasingCurve.Type.OutCubic)

    def _set_pulso(self, v):
        self._pulso = v
        self.update()

    def _girar(self):
        self._giro = (self._giro + 6) % 360
        self.update()

    def pulso(self):
        animar(self.anim_pulso, 1.0, 0.0)

    def refrescar(self):
        activas = [i for i in self.v.items_descarga if i.activa()]
        if activas and not self.reloj.isActive():
            self.reloj.start()
        elif not activas:
            self.reloj.stop()
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        activas = [i for i in self.v.items_descarga if i.activa()]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(4, 4, -4, -4)
        if self._pulso > 0.01:
            p.setPen(QPen(con_alfa(T.a2, self._pulso * 0.8), 2 + 4 * (1 - self._pulso)))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(r.adjusted(-2 * (1 - self._pulso), -2 * (1 - self._pulso), 2 * (1 - self._pulso),
                                     2 * (1 - self._pulso)))
        if not activas:
            return
        total = sum(i.d.totalBytes() for i in activas if i.d.totalBytes() > 0)
        recibido = sum(i.d.receivedBytes() for i in activas if i.d.totalBytes() > 0)
        pen = QPen(QColor(T.a2), 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(QPen(QColor(C["borde"]), 2.2))
        p.drawEllipse(r)
        p.setPen(pen)
        if total > 0:
            p.drawArc(r, 90 * 16, int(-360 * 16 * recibido / total))
        else:
            p.drawArc(r, int(-self._giro * 16), 90 * 16)


class PanelDescargas(QFrame):
    """Ventana emergente con las descargas de esta sesión."""

    def __init__(self, ventana):
        super().__init__(ventana, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.v = ventana
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        exterior = QVBoxLayout(self)
        exterior.setContentsMargins(0, 0, 0, 0)
        caja = QFrame(objectName="panelDescargas")
        exterior.addWidget(caja)
        l = QVBoxLayout(caja)
        l.setContentsMargins(10, 12, 10, 10)
        l.setSpacing(8)
        cab = QHBoxLayout()
        cab.addWidget(QLabel("Descargas", objectName="tituloPregunta"), 1)
        b_carpeta = QPushButton("Abrir carpeta")
        b_todas = QPushButton("Ver todas")
        b_carpeta.clicked.connect(lambda: (self.hide(), ventana.abrir_descargas()))
        b_todas.clicked.connect(lambda: (self.hide(), ventana.abrir_ajustes(ventana.ajustes_ui.indice("Descargas"))))
        cab.addWidget(b_carpeta)
        cab.addWidget(b_todas)
        l.addLayout(cab)
        self.lista = QVBoxLayout()
        self.lista.setSpacing(6)
        contenedor = QWidget()
        contenedor.setLayout(self.lista)
        self.vacio = QLabel("Las descargas de esta sesión aparecerán aquí.", objectName="tenue")
        self.vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vacio.setMinimumHeight(70)
        self.lista.addWidget(self.vacio)
        self.lista.addStretch()
        self.desplazable = QScrollArea()
        self.desplazable.setWidgetResizable(True)
        self.desplazable.setWidget(contenedor)
        l.addWidget(self.desplazable, 1)
        self.setFixedWidth(440)
        self.anim = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim.setDuration(160)

    def anadir(self, item):
        self.vacio.hide()
        self.lista.insertWidget(0, item)

    def mostrar(self, boton):
        n = len(self.v.items_descarga)
        self.setFixedHeight(min(520, 96 + max(1, n) * 78))
        pos = boton.mapToGlobal(QPoint(boton.width() - self.width(), boton.height() + 6))
        self.move(pos)
        self.setWindowOpacity(0.0)
        self.show()
        animar(self.anim, 0.0, 1.0)


class MixinDescargas:
    def iniciar_descargas(self):
        self.items_descarga = []
        self.boton_descargas = BotonDescargas(self)
        self.boton_descargas.clicked.connect(lambda: self.panel_descargas.mostrar(self.boton_descargas))
        self.panel_descargas = PanelDescargas(self)

    def descargar(self, d):
        if self.ajustes.datos["preguntar_descarga"]:
            ruta, _ = QFileDialog.getSaveFileName(self, "Guardar archivo", str(self.descargas / d.downloadFileName()))
            if not ruta:
                d.cancel()
                return
            d.setDownloadDirectory(str(Path(ruta).parent))
            d.setDownloadFileName(Path(ruta).name)
        else:
            d.setDownloadDirectory(str(self.descargas))
        d.accept()
        item = ItemDescarga(self, d)
        self.items_descarga.append(item)
        self.panel_descargas.anadir(item)
        self.boton_descargas.show()
        self.boton_descargas.pulso()
        self.boton_descargas.refrescar()
        self.aviso.mostrar(f"⬇  Descargando {d.downloadFileName()}")

        def fin():
            if not d.isFinished():
                return
            ok = d.state() == D.DownloadCompleted
            self.lista_descargas.datos.insert(0, {
                "nombre": d.downloadFileName(), "ruta": str(Path(d.downloadDirectory()) / d.downloadFileName()),
                "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"), "tam": d.receivedBytes(), "ok": ok})
            del self.lista_descargas.datos[500:]
            self.lista_descargas.guardar()
            if ok:
                from .temas import sonidos
                sonidos().tocar("descarga")
                self.boton_descargas.pulso()
                self.aviso.mostrar(f"✓  {d.downloadFileName()} descargado")
            self.boton_descargas.refrescar()

        d.isFinishedChanged.connect(fin)
