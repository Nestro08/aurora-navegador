"""Herramientas de desarrollo: servidor local, recarga en vivo y panel F12."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403
from .motor import *  # noqa: F401,F403
from .herramientas_dev import Auditoria, ClienteAPI


# ═════════════════════════════ desarrollo local

class _Manejador(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def parse_request(self):
        """Solo responde a localhost: una web con «DNS rebinding» no puede leer los archivos de tu proyecto."""
        if not super().parse_request():
            return False
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host not in ("localhost", "127.0.0.1", "::1"):
            self.send_error(403, "Solo desde localhost")
            return False
        return True

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def servir(carpeta):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Manejador, directory=carpeta))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class Vigilante(QObject):
    """Vigila una carpeta y avisa cuando cambia algún archivo (recarga en vivo)."""
    cambio = pyqtSignal(str)
    IGNORAR = {"node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target"}

    def __init__(self, padre):
        super().__init__(padre)
        self.w = QFileSystemWatcher(self)
        self.carpeta, self._ultimo = None, ""
        self.reloj = QTimer(self, singleShot=True, interval=180)
        self.reloj.timeout.connect(lambda: self.cambio.emit(Path(self._ultimo).name))
        self.w.fileChanged.connect(self._tocar)
        self.w.directoryChanged.connect(lambda r: (self._escanear(), self._tocar(r)))

    def vigilar(self, carpeta):
        self.parar()
        self.carpeta = Path(carpeta)
        self._escanear()

    def _escanear(self):
        if not self.carpeta:
            return
        rutas = []
        for raiz, dirs, archivos in os.walk(self.carpeta):
            dirs[:] = [d for d in dirs if d not in self.IGNORAR and not d.startswith(".")]
            rutas.append(raiz)
            rutas += [os.path.join(raiz, a) for a in archivos]
            if len(rutas) > 3000:
                break
        ya = set(self.w.files()) | set(self.w.directories())
        nuevas = [r for r in rutas if r not in ya]
        if nuevas:
            self.w.addPaths(nuevas)

    def _tocar(self, ruta):
        self._ultimo = ruta
        if os.path.isfile(ruta) and ruta not in self.w.files():
            self.w.addPath(ruta)
        self.reloj.start()

    def parar(self):
        rutas = self.w.files() + self.w.directories()
        if rutas:
            self.w.removePaths(rutas)
        self.carpeta = None


# ═════════════════════════════ panel de desarrollo

class Consola(QWidget):
    def __init__(self, ventana):
        super().__init__()
        self.v, self.hist, self.pos = ventana, [], 0
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        self.salida = QPlainTextEdit(readOnly=True)
        self.salida.setFont(fuente_mono())
        self.salida.setMaximumBlockCount(3000)
        fila = QHBoxLayout()
        self.entrada = QLineEdit(placeholderText="› Escribe JavaScript…  (↑↓ historial)")
        self.entrada.setFont(fuente_mono())
        limpiar = QPushButton("Limpiar")
        limpiar.clicked.connect(self.salida.clear)
        fila.addWidget(self.entrada, 1)
        fila.addWidget(limpiar)
        l.addWidget(self.salida, 1)
        l.addLayout(fila)
        self.entrada.returnPressed.connect(self.ejecutar)
        self.entrada.installEventFilter(self)
        self.escribir("info", "Consola lista. Los console.log/warn/error de la página aparecen aquí.")

    def escribir(self, tipo, texto, extra=""):
        colores = {"log": "#d7dae3", "info": "#7cc4ff", "warn": "#ffcc66", "error": "#ff6b81",
                   "entrada": "#a78bfa", "resultado": "#a5e88a"}
        prefijo = {"entrada": "› ", "resultado": "← ", "warn": "⚠ ", "error": "✖ "}.get(tipo, "")
        t = html.escape(prefijo + str(texto)).replace("\n", "<br>").replace("  ", "&nbsp;&nbsp;")
        e = f' <span style="color:#596075">— {html.escape(extra)}</span>' if extra else ""
        self.salida.appendHtml(f'<span style="color:{colores[tipo]}">{t}</span>{e}')

    def ejecutar(self):
        codigo = self.entrada.text().strip()
        if not codigo:
            return
        self.hist.append(codigo)
        self.pos = len(self.hist)
        self.entrada.clear()
        self.escribir("entrada", codigo)
        self.v.vista().page().runJavaScript(
            JS_EVAL % json.dumps(codigo),
            lambda r: self.escribir("error" if str(r).startswith("⚠") else "resultado", r))

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.KeyPress and self.hist and e.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            self.pos = max(0, min(len(self.hist), self.pos + (-1 if e.key() == Qt.Key.Key_Up else 1)))
            self.entrada.setText(self.hist[self.pos] if self.pos < len(self.hist) else "")
            return True
        return False


class Red(QWidget):
    def __init__(self):
        super().__init__()
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        fila = QHBoxLayout()
        self.filtro = QLineEdit(placeholderText="Filtrar por URL o tipo…")
        self.contador = QLabel("", objectName="tenue")
        limpiar = QPushButton("Limpiar")
        fila.addWidget(self.filtro, 1)
        fila.addWidget(self.contador)
        fila.addWidget(limpiar)
        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Tipo", "Método", "URL"])
        cab = self.tabla.horizontalHeader()
        cab.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        cab.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        cab.setStretchLastSection(True)
        self.tabla.verticalHeader().hide()
        self.tabla.verticalHeader().setDefaultSectionSize(24)
        self.tabla.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setShowGrid(False)
        self.tabla.setWordWrap(False)
        self.tabla.setFont(fuente_mono(8.5))
        self.tabla.cellDoubleClicked.connect(
            lambda f, c: QApplication.clipboard().setText(self.tabla.item(f, 2).text()))
        self.tabla.setToolTip("Doble clic para copiar la URL")
        l.addLayout(fila)
        l.addWidget(self.tabla, 1)
        self.total = self.bloqueadas = 0
        limpiar.clicked.connect(self.limpiar)
        self.filtro.textChanged.connect(self.aplicar_filtro)

    def limpiar(self):
        self.tabla.setRowCount(0)
        self.total = self.bloqueadas = 0
        self.contador.setText("")

    def _coincide(self, fila):
        f = self.filtro.text().lower()
        return not f or f in self.tabla.item(fila, 2).text().lower() or f in self.tabla.item(fila, 0).text().lower()

    def aplicar_filtro(self):
        for i in range(self.tabla.rowCount()):
            self.tabla.setRowHidden(i, not self._coincide(i))

    def anadir(self, metodo, tipo, url, bloqueado):
        abajo = self.tabla.verticalScrollBar().value() >= self.tabla.verticalScrollBar().maximum() - 4
        if self.tabla.rowCount() >= 600:
            self.tabla.removeRow(0)
        f = self.tabla.rowCount()
        self.tabla.insertRow(f)
        color = QColor("#ff6b81") if bloqueado else (QColor(T.a2) if tipo == "Documento" else QColor(C["texto"]))
        for c, t in enumerate(("⛔ " + tipo if bloqueado else tipo, metodo, url)):
            item = QTableWidgetItem(t)
            item.setForeground(color if c != 1 else QColor(C["tenue"]))
            self.tabla.setItem(f, c, item)
        self.tabla.setRowHidden(f, not self._coincide(f))
        self.total += 1
        self.bloqueadas += bloqueado
        self.contador.setText(f"{self.total} peticiones · {self.bloqueadas} bloqueadas ")
        if abajo:
            self.tabla.scrollToBottom()


class Herramientas(QWidget):
    def __init__(self, v):
        super().__init__()
        self.v = v
        l = QVBoxLayout(self)
        l.setContentsMargins(2, 0, 8, 16)
        l.setSpacing(8)

        def seccion(t):
            e = QLabel(t.upper(), objectName="seccion")
            l.addWidget(e)

        def boton(t, f, consejo=""):
            b = QPushButton(t)
            b.setToolTip(consejo)
            b.clicked.connect(f)
            return b

        seccion("Vista de dispositivo")
        fila = QHBoxLayout()
        self.disp = QComboBox()
        self.disp.addItems(DISPOSITIVOS)
        self.disp.currentTextChanged.connect(v.set_dispositivo)
        fila.addWidget(self.disp, 1)
        fila.addWidget(boton("⟲  Rotar", v.rotar_dispositivo))
        l.addLayout(fila)

        seccion("User-Agent")
        self.ua = QComboBox()
        self.ua.addItems(UAS)
        self.ua.setCurrentText(v.ajustes.datos.get("ua", "Por defecto"))
        self.ua.currentTextChanged.connect(v.set_ua)
        l.addWidget(self.ua)

        seccion("Página")
        s = v.perfil.settings()
        A = QWebEngineSettings.WebAttribute
        self.sw_js = Interruptor("JavaScript", s.testAttribute(A.JavascriptEnabled))
        self.sw_js.toggled.connect(lambda c: v.set_atributo("JavascriptEnabled", c))
        self.sw_img = Interruptor("Cargar imágenes", s.testAttribute(A.AutoLoadImages))
        self.sw_img.toggled.connect(lambda c: v.set_atributo("AutoLoadImages", c))
        self.sw_cache = Interruptor("Caché HTTP", True)
        self.sw_cache.toggled.connect(v.set_cache)
        self.sw_bloq = Interruptor("Bloquear anuncios y rastreadores", v.bloqueador.activo)
        self.sw_bloq.toggled.connect(v.set_bloqueo)
        for w in (self.sw_js, self.sw_img, self.sw_cache, self.sw_bloq):
            l.addWidget(w)
        if hasattr(A, "ForceDarkMode"):
            oscuro = Interruptor("Forzar modo oscuro en las webs", s.testAttribute(A.ForceDarkMode))
            oscuro.toggled.connect(lambda c: v.set_atributo("ForceDarkMode", c))
            l.addWidget(oscuro)

        seccion("Desarrollo local")
        self.estado = QLabel("Ninguna carpeta vigilada.", objectName="tenue")
        self.estado.setWordWrap(True)
        l.addWidget(self.estado)
        g = QGridLayout()
        g.addWidget(boton("▶  Servir carpeta…", v.servir_carpeta,
                          "Arranca un servidor en localhost con esa carpeta y recarga al guardar"), 0, 0)
        g.addWidget(boton("👁  Vigilar carpeta…", v.vigilar_carpeta,
                          "Recarga la pestaña cuando cambie cualquier archivo de la carpeta"), 0, 1)
        g.addWidget(boton("■  Detener", v.detener_vivo), 1, 0, 1, 2)
        l.addLayout(g)

        seccion("CSS en vivo")
        self.css = QPlainTextEdit(placeholderText="* { outline: 1px solid rgba(124,92,255,.5) }\n"
                                                  "Se aplica a la página mientras escribes.")
        self.css.setFont(fuente_mono())
        self.css.setFixedHeight(110)
        self.reloj_css = QTimer(self, singleShot=True, interval=250)
        self.reloj_css.timeout.connect(v.aplicar_css)
        self.css.textChanged.connect(self.reloj_css.start)
        l.addWidget(self.css)

        seccion("Acciones")
        g = QGridLayout()
        acciones = [("📸  Captura", v.captura, "Ctrl+Shift+S · también se copia al portapapeles"),
                    ("🧾  Captura completa", v.captura_completa, "Toda la página de arriba abajo"),
                    ("🎯  Cuentagotas y medidor", v.cuentagotas, "Ctrl+Shift+X · color bajo el ratón y medir distancias"),
                    ("🩺  Auditar página", lambda: (v.panel.abrir(5), v.panel.auditoria.auditar()), "Accesibilidad, SEO, rendimiento…"),
                    ("📄  Guardar PDF", v.guardar_pdf, "Ctrl+P"),
                    ("</>  Código fuente", v.ver_codigo, "Ctrl+U"),
                    ("⚡  Rendimiento", v.medir_rendimiento, "Tiempos de carga, recursos y DOM"),
                    ("🔗  Copiar URL", v.copiar_url, ""),
                    ("🧹  Borrar datos del sitio", v.borrar_datos_sitio, "localStorage, sessionStorage, IndexedDB"),
                    ("↻  Recargar sin caché", v.recargar_sin_cache, "Ctrl+F5")]
        for i, (t, f, c) in enumerate(acciones):
            g.addWidget(boton(t, f, c), i // 2, i % 2)
        l.addLayout(g)
        l.addStretch()

    def sync(self, pagina):
        self.disp.blockSignals(True)
        self.disp.setCurrentText(pagina.nombre_disp)
        self.disp.blockSignals(False)


class Asa(QWidget):
    """Borde izquierdo del panel para redimensionarlo arrastrando."""

    def __init__(self, panel):
        super().__init__(panel)
        self.panel, self._x0, self._h = panel, None, False
        self.setFixedWidth(6)
        self.setCursor(Qt.CursorShape.SizeHorCursor)

    def enterEvent(self, e):
        self._h = True
        self.update()

    def leaveEvent(self, e):
        self._h = False
        self.update()

    def mousePressEvent(self, e):
        self._x0, self._w0 = e.globalPosition().x(), self.panel.width()

    def mouseMoveEvent(self, e):
        if self._x0 is not None:
            w = int(max(320, min(1100, self._w0 + self._x0 - e.globalPosition().x())))
            self.panel.setFixedWidth(w)
            self.panel.ancho = w

    def mouseReleaseEvent(self, e):
        self._x0 = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(QRectF(0, 0, 1, self.height()), QColor(C["borde"]))
        if self._h:
            p.fillRect(QRectF(0, 0, 2, self.height()), QColor(T.a1))


class PanelDev(QWidget):
    def __init__(self, ventana):
        super().__init__(objectName="panel")
        self.v, self.abierto = ventana, False
        self.ancho = int(ventana.ajustes.datos.get("ancho_panel", 500))
        self.setFixedWidth(0)
        self.hide()
        self.anim = animacion(self, lambda w: self.setFixedWidth(int(w)), 300, QEasingCurve.Type.OutQuart)
        self.anim.finished.connect(lambda: None if self.abierto else self.hide())
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(Asa(self))
        cuerpo = QWidget()
        h.addWidget(cuerpo, 1)
        l = QVBoxLayout(cuerpo)
        l.setContentsMargins(10, 4, 10, 10)
        l.setSpacing(4)
        cab = QHBoxLayout()
        cab.addWidget(QLabel("Herramientas de desarrollo", objectName="tituloPanel"), 1)
        cerrar = BotonIcono("cerrar", "Cerrar (F12)", tam=28)
        cerrar.clicked.connect(self.alternar)
        cab.addWidget(cerrar)
        l.addLayout(cab)
        self.tabs = QTabWidget(objectName="tabsPanel")
        self.tabs.setDocumentMode(True)
        self.devtools = QWebEngineView()
        self.consola = Consola(ventana)
        self.red = Red()
        self.herr = Herramientas(ventana)
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setWidget(self.herr)
        self.tabs.addTab(self.devtools, "Inspector")
        self.tabs.addTab(self.consola, "Consola")
        self.tabs.addTab(self.red, "Red")
        self.tabs.addTab(desplazable, "Herramientas")
        self.api = ClienteAPI(ventana)
        self.auditoria = Auditoria(ventana)
        self.tabs.addTab(self.api, "API")
        self.tabs.addTab(self.auditoria, "Auditoría")
        l.addWidget(self.tabs, 1)

    def alternar(self):
        self.abierto = not self.abierto
        if self.abierto:
            self.show()
            animar(self.anim, self.width(), self.ancho)
        else:
            animar(self.anim, self.width(), 0)
            self.v.enfocar_pagina()
        self.v.b_dev.setChecked(self.abierto)

    def abrir(self, pestana=None):
        if pestana is not None:
            self.tabs.setCurrentIndex(pestana)
        if not self.abierto:
            self.alternar()
