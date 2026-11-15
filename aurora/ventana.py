"""Ventana principal del navegador."""
import time

from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403
from .motor import *  # noqa: F401,F403
from .desarrollo import *  # noqa: F401,F403
from .contrasenas import *  # noqa: F401,F403
from .ajustes import *  # noqa: F401,F403
from .estilo import *  # noqa: F401,F403
from .organizacion import MixinOrganizacion
from .multimedia import MixinMultimedia
from .descargas import MixinDescargas
from .herramientas_dev import MixinDev
from .asistente import PanelAsistente
from . import temas
from .temas import Apariencia, sonidos


# ═════════════════════════════ ventana

class BotonPerfil(QAbstractButton):
    """Círculo con la inicial y el color del perfil (o gafas en incógnito)."""

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self.setFixedSize(34, 34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(5, 5, 24, 24)
        perfil = self.v.p
        if perfil.incognito:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#2a1f44"))
            p.drawEllipse(r)
            p.setPen(QColor("#c4b5fd"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "🕶")
            return
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor(perfil.color))
        g.setColorAt(1, QColor(perfil.color).darker(140))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(r)
        f = QFont(self.font())
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, perfil.nombre[:1].upper())


class Ventana(QMainWindow, MixinOrganizacion, MixinMultimedia, MixinDescargas, MixinDev):
    def __init__(self, perfil=None, urls=None, restaurar=True):
        super().__init__()
        self.p = perfil or gestor().perfil()
        self.p.ventanas.append(self)
        self.incognito = self.p.incognito
        self.setWindowIcon(crear_icono_app())
        self.resize(1380, 880)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.ajustes, self.marcadores, self.historial = self.p.ajustes, self.p.marcadores, self.p.historial
        self.claves, self.lista_descargas = self.p.claves, self.p.lista_descargas
        self.perfil, self.bloqueador, self.ua_original = self.p.web, self.p.bloqueador, self.p.ua_original
        self.descargas = Path(self.ajustes.datos["carpeta_descargas"]
                              or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
                              or Path.home() / "Downloads")
        self.chip_activo, self.cerradas, self.servidores = None, [], []
        self._ultimo_envio = ("", 0)
        self._generadas = {}
        self.vigilante = Vigilante(self)
        self.vigilante.cambio.connect(self.recarga_en_vivo)
        if self.p.sync:
            self.p.sync.terminado.connect(self._sync_terminada)

        # en Linux las pestañas hacen de barra de título (en Windows se oscurece la del sistema)
        self.integrada = sys.platform != "win32"
        if self.integrada:
            self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            self.setMouseTracking(True)
        self.generar_nueva()
        self._regenerar = QTimer(self, singleShot=True, interval=1500)
        self._regenerar.timeout.connect(self.generar_nueva)
        favicons().listo.connect(self._favicon_nuevo)
        self.iniciar_descargas()
        self.iniciar_multimedia()
        self.iniciar_dev()
        self.construir_ui()
        if self.integrada:
            self.controles = ControlesVentana(self)
            self.tira.poner_controles(self.controles)
            self.centralWidget().setCursor(Qt.CursorShape.ArrowCursor)  # que no hereden el cursor de los bordes
            self._ajustar_bordes()
        self.iniciar_organizacion()
        self.registrar_comandos()
        self.actualizar_perfil()

        self.restaurar_sesion() if restaurar else None
        for url in urls or []:
            self.nueva_pestana(url)
        if not self.tira.chips:
            self.nueva_pestana()
        if self.ajustes.datos["dev_inicio"]:
            QTimer.singleShot(400, self.panel.alternar)
        if self.p.sync and len(self.p.ventanas) == 1:
            QTimer.singleShot(3000, lambda: self.p.sync.sincronizar(silencioso=True))
        self.barra_titulo_oscura()

    def restaurar_sesion(self):
        a = self.ajustes.datos
        if a["inicio"] == "nueva":
            return
        self.tira.grupos.update({k: dict(g) for k, g in (a.get("grupos") or {}).items()})
        primero = None
        for entrada in a.get("sesion") or []:
            if isinstance(entrada, str):
                entrada = {"url": entrada}
            self.nueva_pestana(entrada.get("url", ""), enfocar=primero is None)
            chip = self.tira.chips[-1]
            chip.fijada = bool(entrada.get("fijada"))
            chip.grupo = entrada.get("grupo") if entrada.get("grupo") in self.tira.grupos else None
            primero = primero or chip
        self.tira.normalizar()
        self.tira.limpiar_grupos()
        self.tira.recolocar(False)
        if primero:
            self.activar(primero)

    def actualizar_perfil(self):
        nombre = f"{self.p.nombre} · Incógnito" if self.incognito else self.p.nombre
        self.b_perfil.setToolTip(f"Perfil: {nombre}")
        self.b_perfil.update()
        if self.chip_activo:
            self.setWindowTitle(f"{self.chip_activo.titulo} — {self._sufijo_titulo()}")

    def _sufijo_titulo(self):
        if self.incognito:
            return f"{NOMBRE} (Incógnito)"
        return NOMBRE if len(gestor().lista.datos) == 1 else f"{NOMBRE} · {self.p.nombre}"

    def _sync_terminada(self, ok, mensaje):
        if self.isActiveWindow() or self is self.p.ventana_activa():
            self.aviso.mostrar(mensaje)

    # ────────────────────────────────────────────────────────── interfaz
    def construir_ui(self):
        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        self.cabecera = QWidget(objectName="cabecera")
        vc = QVBoxLayout(self.cabecera)
        vc.setContentsMargins(0, 0, 0, 0)
        vc.setSpacing(0)
        self.tira = Tira(self.cabecera)
        if self.incognito:
            self.tira.fondo = C_INCOG
            self.cabecera.setStyleSheet(f"#cabecera, #barra {{ background: {C_INCOG}; }}")
        self.tira.activar_pedido.connect(lambda c: (sonidos().tocar("cambiar") if c is not self.chip_activo else None,
                                                    self.activar(c)))
        self.tira.cerrar_pedido.connect(self.cerrar)
        self.tira.nueva_pedida.connect(lambda: self.nueva_pestana())
        vc.addWidget(self.tira)

        barra = QWidget(objectName="barra")
        hb = QHBoxLayout(barra)
        hb.setContentsMargins(10, 2, 10, 8)
        hb.setSpacing(3)
        self.b_atras = BotonIcono("atras", "Atrás (Alt+←)")
        self.b_adelante = BotonIcono("adelante", "Adelante (Alt+→)")
        self.b_recargar = BotonIcono("recargar", "Recargar (F5)")
        self.b_inicio = BotonIcono("inicio", "Nueva pestaña de inicio")
        self.b_atras.clicked.connect(lambda: self.vista().back())
        self.b_adelante.clicked.connect(lambda: self.vista().forward())
        self.b_recargar.clicked.connect(self.recargar_o_parar)
        self.b_inicio.clicked.connect(self.ir_inicio)
        for b in (self.b_atras, self.b_adelante, self.b_recargar, self.b_inicio):
            hb.addWidget(b)
        hb.addSpacing(6)
        self.omni = Omnibox()
        self.omni.enviado.connect(self.enviar_omni)
        self.omni.proveedor = self.sugerencias
        self.omni.estrella.clicked.connect(self.alternar_marcador)
        self.omni.llave.clicked.connect(self.menu_llave)
        self.omni.lectura = BotonIcono("lectura", "Modo lectura (F9)", tam=30)
        self.omni.lectura.clicked.connect(self.modo_lectura)
        self.omni.layout().insertWidget(self.omni.layout().indexOf(self.omni.llave), self.omni.lectura)
        hb.addWidget(self.omni, 1)
        hb.addSpacing(6)
        if self.incognito:
            insignia = QLabel("🕶  Incógnito", objectName="insignia")
            hb.addWidget(insignia)
            hb.addSpacing(4)
        self.boton_descargas.hide()
        hb.addWidget(self.boton_descargas)
        self.b_ia = BotonIcono("ia", "Asistente IA (Ctrl+Shift+A)")
        self.b_ia.setCheckable(True)
        self.b_ia.clicked.connect(lambda: self.panel_ia.alternar())
        self.b_paleta = BotonIcono("comando", "Paleta de comandos (Ctrl+K)")
        self.b_paleta.clicked.connect(self.abrir_paleta)
        self.b_dev = BotonIcono("dev", "Herramientas de desarrollo (F12)")
        self.b_dev.setCheckable(True)
        self.b_dev.clicked.connect(lambda: self.panel.alternar())
        self.b_ajustes = BotonIcono("ajustes", "Ajustes (Ctrl+,)")
        self.b_ajustes.clicked.connect(lambda: self.abrir_ajustes())
        self.b_menu = BotonIcono("menu", "Menú")
        self.b_menu.clicked.connect(self.mostrar_menu)
        self.b_perfil = BotonPerfil(self)
        self.b_perfil.clicked.connect(self.menu_perfil)
        for b in (self.b_ia, self.b_paleta, self.b_dev, self.b_ajustes, self.b_perfil, self.b_menu):
            hb.addWidget(b)
        vc.addWidget(barra)
        self.progreso = BarraProgreso()
        vc.addWidget(self.progreso)
        v.addWidget(self.cabecera)

        self.cuerpo = QWidget()
        hc = QHBoxLayout(self.cuerpo)
        hc.setContentsMargins(0, 0, 0, 0)
        hc.setSpacing(0)
        self.pila = QStackedWidget()
        self.pila.installEventFilter(self)
        hc.addWidget(self.pila, 1)
        self.panel_ia = PanelAsistente(self)
        hc.addWidget(self.panel_ia)
        self.panel = PanelDev(self)
        self.herr = self.panel.herr
        hc.addWidget(self.panel)
        v.addWidget(self.cuerpo, 1)

        self.paleta = Paleta(central, self)
        self.aviso = Aviso(central)
        self.buscador = BuscadorFlotante(self.cuerpo, self)
        self.pregunta = Pregunta(self.cuerpo, self)
        self.ajustes_ui = Ajustes(central, self)

    def eventFilter(self, obj, e):
        if obj is self.pila and e.type() == QEvent.Type.Resize:
            self.buscador.recolocar()
            self.pregunta.recolocar()
        return False

    def resizeEvent(self, e):
        super().resizeEvent(e)
        for capa in (self.paleta, self.ajustes_ui):
            if capa.isVisible():
                capa.setGeometry(self.centralWidget().rect())
                capa.colocar()

    # ────────────────────────────────────────────────────────── ventana sin marco del sistema
    BORDE = 5

    def _ajustar_bordes(self):
        m = 0 if self.isMaximized() or self.isFullScreen() else self.BORDE
        self.setContentsMargins(m, m, m, m)
        self.controles.actualizar()
        self.update()

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.WindowStateChange and getattr(self, "controles", None):
            self._ajustar_bordes()

    def _bordes_en(self, pos):
        if not self.integrada or self.contentsMargins().left() == 0:
            return None
        m, bordes = self.BORDE + 3, []
        if pos.x() <= m:
            bordes.append(Qt.Edge.LeftEdge)
        elif pos.x() >= self.width() - m:
            bordes.append(Qt.Edge.RightEdge)
        if pos.y() <= m:
            bordes.append(Qt.Edge.TopEdge)
        elif pos.y() >= self.height() - m:
            bordes.append(Qt.Edge.BottomEdge)
        if not bordes:
            return None
        combinados = bordes[0]
        for b in bordes[1:]:
            combinados |= b
        return combinados

    def mouseMoveEvent(self, e):
        bordes = self._bordes_en(e.position().toPoint())
        if bordes is None:
            self.unsetCursor()
            return super().mouseMoveEvent(e)
        izq_arr = (Qt.Edge.LeftEdge | Qt.Edge.TopEdge, Qt.Edge.RightEdge | Qt.Edge.BottomEdge)
        der_arr = (Qt.Edge.RightEdge | Qt.Edge.TopEdge, Qt.Edge.LeftEdge | Qt.Edge.BottomEdge)
        if bordes in izq_arr:
            cursor = Qt.CursorShape.SizeFDiagCursor
        elif bordes in der_arr:
            cursor = Qt.CursorShape.SizeBDiagCursor
        elif bordes in (Qt.Edge.LeftEdge, Qt.Edge.RightEdge):
            cursor = Qt.CursorShape.SizeHorCursor
        else:
            cursor = Qt.CursorShape.SizeVerCursor
        self.setCursor(cursor)

    def mousePressEvent(self, e):
        bordes = self._bordes_en(e.position().toPoint())
        if bordes is not None and e.button() == Qt.MouseButton.LeftButton:
            self.windowHandle().startSystemResize(bordes)
            return
        super().mousePressEvent(e)

    def leaveEvent(self, e):
        if self.integrada:
            self.unsetCursor()
        super().leaveEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        if self.integrada and self.contentsMargins().left():
            p = QPainter(self)
            p.setPen(QColor(C["borde"]))
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))

    def barra_titulo_oscura(self):
        """En Windows 10/11 pone la barra de título oscura y del mismo color que la interfaz."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            hwnd, dwm = int(self.winId()), ctypes.windll.dwmapi
            for atributo, valor in ((20, 1), (35, 0x00140F0D), (36, 0x00EEE8E6)):
                v = ctypes.c_int(valor)
                dwm.DwmSetWindowAttribute(hwnd, atributo, ctypes.byref(v), ctypes.sizeof(v))
        except Exception:
            pass

    def mostrar_menu(self):
        m = menu_bonito(QMenu(self))
        m.addAction("Nueva pestaña\tCtrl+T", lambda: self.nueva_pestana())
        m.addAction("Nueva ventana\tCtrl+N", lambda: gestor().nueva_ventana(self.p.nombre, restaurar=False))
        m.addAction("Nueva ventana de incógnito\tCtrl+Shift+N",
                    lambda: gestor().nueva_ventana(self.p.nombre, incognito=True))
        m.addAction("Reabrir pestaña cerrada\tCtrl+Shift+T", self.reabrir)
        m.addAction("Paleta de comandos\tCtrl+K", self.abrir_paleta)
        m.addSeparator()
        m.addAction("Historial\tCtrl+H", self.ver_historial)
        m.addAction("Descargas\tCtrl+J", self.abrir_descargas)
        sub = menu_bonito(m.addMenu("Buscador"))
        for n in BUSCADORES:
            a = sub.addAction(n, lambda n=n: self.set_buscador(n))
            a.setCheckable(True)
            a.setChecked(self.ajustes.datos["buscador"] == n)
        m.addSeparator()
        m.addAction("Herramientas de desarrollo\tF12", lambda: self.panel.alternar())
        m.addAction("Modo responsive\tCtrl+Shift+M", self.alternar_responsive)
        m.addAction("Captura de pantalla\tCtrl+Shift+S", self.captura)
        m.addAction("Servir carpeta local…", self.servir_carpeta)
        m.addSeparator()
        m.addAction("Modo lectura\tF9", self.modo_lectura)
        m.addAction("Vídeo flotante\tCtrl+Shift+V", self.video_flotante)
        m.addAction("Pantalla dividida\tCtrl+Shift+D", self._alternar_division)
        m.addAction("Asistente IA\tCtrl+Shift+A", lambda: self.panel_ia.alternar())
        m.addAction("Extensiones", lambda: self.abrir_ajustes(Ajustes.indice("Extensiones")))
        m.addSeparator()
        m.addAction("Contraseñas", lambda: self.abrir_ajustes(Ajustes.indice("Contraseñas")))
        m.addAction("Ajustes\tCtrl+,", lambda: self.abrir_ajustes())
        m.adjustSize()
        m.exec(self.b_menu.mapToGlobal(QPoint(self.b_menu.width() - m.width(), self.b_menu.height() + 6)))

    # ────────────────────────────────────────────────────────── comandos y atajos
    def registrar_comandos(self):
        W = QWebEnginePage.WebAction
        self.comandos = [
            ("Nueva pestaña", "Ctrl+T", lambda: self.nueva_pestana()),
            ("Cerrar pestaña", "Ctrl+W", lambda: self.cerrar(self.chip_activo)),
            ("Reabrir pestaña cerrada", "Ctrl+Shift+T", self.reabrir),
            ("Siguiente pestaña", "Ctrl+Tab", lambda: self.saltar_pestana(1)),
            ("Pestaña anterior", "Ctrl+Shift+Tab", lambda: self.saltar_pestana(-1)),
            ("Ir a la barra de direcciones", "Ctrl+L", self.enfocar_omni),
            ("Paleta de comandos", "Ctrl+K", self.abrir_paleta),
            ("Recargar", "F5", lambda: self.vista().reload()),
            ("Recargar sin caché", "Ctrl+F5", self.recargar_sin_cache),
            ("Atrás", "Alt+Left", lambda: self.vista().back()),
            ("Adelante", "Alt+Right", lambda: self.vista().forward()),
            ("Página de inicio", "Alt+Home", self.ir_inicio),
            ("Guardar o quitar de accesos", "Ctrl+D", self.alternar_marcador),
            ("Historial", "Ctrl+H", self.ver_historial),
            ("Buscar en la página", "Ctrl+F", lambda: self.buscador.abrir()),
            ("Acercar", "Ctrl++", lambda: self.zoom(0.1)),
            ("Alejar", "Ctrl+-", lambda: self.zoom(-0.1)),
            ("Zoom normal", "Ctrl+0", lambda: self.zoom(0)),
            ("Pantalla completa", "F11", self.alternar_pantalla_completa),
            ("Herramientas de desarrollo", "F12", lambda: self.panel.alternar()),
            ("Inspector de elementos", "Ctrl+Shift+I", lambda: self.panel.abrir(0)),
            ("Consola JavaScript", "Ctrl+Shift+J", lambda: self.panel.abrir(1)),
            ("Registro de red", "Ctrl+Shift+E", lambda: self.panel.abrir(2)),
            ("Herramientas (responsive, UA, CSS en vivo…)", "", lambda: self.panel.abrir(3)),
            ("Ver código fuente", "Ctrl+U", self.ver_codigo),
            ("Captura de pantalla", "Ctrl+Shift+S", self.captura),
            ("Guardar como PDF", "Ctrl+P", self.guardar_pdf),
            ("Modo responsive (alternar)", "Ctrl+Shift+M", self.alternar_responsive),
            ("Rotar dispositivo", "", self.rotar_dispositivo),
            ("Medir rendimiento", "", self.medir_rendimiento),
            ("Servir carpeta local con recarga en vivo…", "", self.servir_carpeta),
            ("Vigilar carpeta (recarga en vivo)…", "", self.vigilar_carpeta),
            ("Detener recarga en vivo y servidores", "", self.detener_vivo),
            ("Copiar URL", "", self.copiar_url),
            ("Borrar datos del sitio", "", self.borrar_datos_sitio),
            ("Borrar historial", "", self.borrar_historial),
            ("Borrar cookies y caché", "", self.borrar_cookies),
            ("Abrir carpeta de descargas", "Ctrl+J", self.abrir_descargas),
            ("Ajustes", "Ctrl+,", lambda: self.abrir_ajustes()),
            ("Importar desde Chrome u otro navegador…", "", self.importar_navegador),
            ("Nueva ventana", "Ctrl+N", lambda: gestor().nueva_ventana(self.p.nombre, restaurar=False)),
            ("Nueva ventana de incógnito", "Ctrl+Shift+N", lambda: gestor().nueva_ventana(self.p.nombre, incognito=True)),
            ("Modo lectura", "F9", self.modo_lectura),
            ("Vídeo flotante (picture-in-picture)", "Ctrl+Shift+V", self.video_flotante),
            ("Asistente IA", "Ctrl+Shift+A", lambda: self.panel_ia.alternar()),
            ("Resumir la página con IA", "", lambda: self.panel_ia.preguntar(
                "Resume esta página en 5-8 puntos clave, en español.", etiqueta="Resumir")),
            ("Cuentagotas y medidor", "Ctrl+Shift+X", self.cuentagotas),
            ("Captura de página completa", "", self.captura_completa),
            ("Auditar página", "", lambda: (self.panel.abrir(5), self.panel.auditoria.auditar())),
            ("Cliente de API", "", lambda: self.panel.abrir(4)),
            ("Pantalla dividida (alternar)", "Ctrl+Shift+D", self._alternar_division),
            ("Fijar / desfijar pestaña", "", lambda: self.fijar(self.chip_activo, not self.chip_activo.fijada)),
            ("Añadir pestaña a un grupo nuevo", "Ctrl+Shift+G", lambda: self.agrupar(self.chip_activo, None)),
            ("Silenciar / activar sonido de la pestaña", "Ctrl+M", lambda: self.silenciar(self.chip_activo)),
            ("Dormir las demás pestañas", "", lambda: [self.dormir(c) for c in self.tira.chips]),
            ("Generar contraseña segura en el campo actual", "", self.poner_contrasena_generada),
            ("Bloquear contraseñas ahora", "", lambda: (self.p.verificador.bloquear(),
                                                        self.aviso.mostrar("🔒  Contraseñas bloqueadas"))),
            ("Sincronizar ahora", "", lambda: self.p.sync.sincronizar() if self.p.sync else None),
            ("Recargar extensiones", "", lambda: (extensiones().recargar(), self.aviso.mostrar("🧩  Extensiones recargadas"))),
        ]
        self.comandos += [(f"Abrir perfil: {i['nombre']}", "", lambda n=i["nombre"]: gestor().nueva_ventana(n))
                          for i in gestor().lista.datos if i["nombre"] != self.p.nombre]
        self.comandos += [(f"Ajustes: {n}", "", lambda i=i: self.abrir_ajustes(i))
                          for i, (n, _) in enumerate(Ajustes.SECCIONES)]
        self.comandos += [(f"Dispositivo: {n}", "", lambda n=n: self.herr.disp.setCurrentText(n))
                          for n in DISPOSITIVOS]
        self.comandos += [(f"User-Agent: {n}", "", lambda n=n: self.herr.ua.setCurrentText(n)) for n in UAS]
        self.comandos += [(f"Buscador: {n}", "", lambda n=n: self.set_buscador(n)) for n in BUSCADORES]
        for _, atajo, funcion in self.comandos:
            if atajo:
                QShortcut(QKeySequence(atajo), self).activated.connect(funcion)
        for _, _, atajo, funcion in extensiones().comandos:
            self.registrar_atajo_extension(atajo, funcion)
        for atajo, funcion in (("Ctrl+R", lambda: self.vista().reload()), ("Ctrl+=", lambda: self.zoom(0.1)),
                               ("F6", self.enfocar_omni), ("Ctrl+Shift+P", self.abrir_paleta)):
            QShortcut(QKeySequence(atajo), self).activated.connect(funcion)
        self.atajo_esc = QShortcut(QKeySequence("Escape"), self)
        self.atajo_esc.activated.connect(self.salir_pantalla_completa)
        self.atajo_esc.setEnabled(False)

    def registrar_atajo_extension(self, atajo, funcion):
        if atajo:
            QShortcut(QKeySequence(atajo), self).activated.connect(funcion)

    def _alternar_division(self):
        if self.division:
            self.deshacer_division()
        else:
            self.dividir(self.chip_activo, None)

    def menu_perfil(self):
        g = gestor()
        m = menu_bonito(QMenu(self))
        cab = m.addAction(f"{self.p.nombre}{' · Incógnito' if self.incognito else ''}")
        cab.setEnabled(False)
        m.addSeparator()
        for info in g.lista.datos:
            if info["nombre"] != self.p.nombre or self.incognito:
                m.addAction(f"●  Abrir «{info['nombre']}»", lambda n=info["nombre"]: g.nueva_ventana(n))
        m.addAction("🕶  Nueva ventana de incógnito", lambda: g.nueva_ventana(self.p.nombre, incognito=True))
        m.addSeparator()
        m.addAction("Gestionar perfiles…", lambda: self.abrir_ajustes(Ajustes.indice("Perfiles")))
        m.exec(self.b_perfil.mapToGlobal(QPoint(0, self.b_perfil.height() + 6)))

    # ────────────────────────────────────────────────────────── pestañas
    def vista(self):
        return self.chip_activo.pagina.vista

    def pagina(self):
        return self.chip_activo.pagina

    @staticmethod
    def es_nueva(url):
        return url.toString().split("#")[0].split("?")[0] in (NUEVA_URL, NUEVA_INCOG_URL)

    def url_nueva(self):
        return NUEVA_INCOG_URL if self.incognito else NUEVA_URL

    def nueva_pestana(self, url="", enfocar=True):
        """url="" → página de inicio; url=None → en blanco (la rellena la web que la abrió)."""
        if self.isVisible():  # no suena al restaurar la sesión
            sonidos().tocar("abrir")
        pagina = PaginaWeb(self, self.perfil)
        pagina.zoom = float(self.ajustes.datos.get("zoom", 1.0))
        pagina.vista.setZoomFactor(pagina.zoom)
        chip = Chip(self.tira, pagina)
        pagina.chip = chip
        self.pila.addWidget(pagina)
        if url is None and self.chip_activo in self.tira.chips:
            indice = self.tira.chips.index(self.chip_activo) + 1
        else:
            indice = len(self.tira.chips)
        self.tira.agregar(chip, indice)

        v, p = pagina.vista, pagina.vista.page()
        v.titleChanged.connect(lambda _, c=chip: self._titulo(c))
        v.iconChanged.connect(lambda i, c=chip: (setattr(c, "icono", i), c.update(), self._guardar_favicon(c, i)))
        v.urlChanged.connect(lambda _, c=chip: self._url(c))
        v.loadStarted.connect(lambda c=chip: self._carga(c, 5))
        v.loadProgress.connect(lambda n, c=chip: self._carga(c, n) if c.cargando else None)
        v.loadFinished.connect(lambda ok, c=chip: self._fin_carga(c, ok))
        p.findTextFinished.connect(self.buscador.resultado)
        p.fullScreenRequested.connect(self.pantalla_completa_web)
        p.pdfPrintingFinished.connect(
            lambda ruta, ok: self.aviso.mostrar(f"📄  PDF guardado: {Path(ruta).name}" if ok else "No se pudo crear el PDF"))
        p.action(QWebEnginePage.WebAction.InspectElement).triggered.connect(lambda: self.panel.abrir(0))
        p.recentlyAudibleChanged.connect(lambda a, c=chip: (setattr(c, "sonando", a), c.update()))
        p.audioMutedChanged.connect(lambda m, c=chip: (setattr(c, "silenciada", m), c.update()))
        if url is not None:
            v.setUrl(QUrl(url) if url else QUrl(self.url_nueva()))
        if enfocar:
            self.activar(chip)
        return v

    def activar(self, chip, enfocar=True):
        if self.chip_activo and self.chip_activo is not chip:
            self.chip_activo.set_activo(False)
            self.chip_activo.ultimo_uso = time.time()
        if chip.grupo and chip.grupo in self.grupos and self.grupos[chip.grupo]["plegado"]:
            self.grupos[chip.grupo]["plegado"] = False
            self.tira.recolocar()
        self.chip_activo = chip
        chip.ultimo_uso = time.time()
        chip.set_activo(True)
        self.despertar(chip)
        self._mostrar_pagina(chip)
        v = chip.pagina.vista
        self.omni.set_url(v.url(), self.es_nueva(v.url()))
        self.progreso.fijar(chip.cargando, chip.progreso)
        self.b_recargar.set_icono("parar" if chip.cargando else "recargar")
        self._botones_historial()
        self._estrella()
        self._llave()
        self.pregunta.ocultar()
        self.setWindowTitle(f"{chip.titulo} — {self._sufijo_titulo()}")
        v.page().setDevToolsPage(self.panel.devtools.page())
        self.herr.sync(chip.pagina)
        if self.buscador._abierto:
            self.buscador.cerrar()
        if self.es_nueva(v.url()) and enfocar:
            v.setFocus()

    def cerrar(self, chip):
        if chip not in self.tira.chips:
            return
        if self.division and chip in self.division[:2]:
            self.deshacer_division()
        if len(self.tira.chips) == 1:
            self.close()
            return
        sonidos().tocar("cerrar")
        url = chip.pagina.vista.url()
        if not self.es_nueva(url) and not url.isEmpty():
            self.cerradas.append(url.toString())
        i = self.tira.chips.index(chip)
        if chip is self.chip_activo:
            vecino = self.tira.chips[i + 1] if i + 1 < len(self.tira.chips) else self.tira.chips[i - 1]
            self.activar(vecino)
        self.tira.quitar(chip)
        self.pila.removeWidget(chip.pagina)
        chip.pagina.deleteLater()

    def reabrir(self):
        if self.cerradas:
            self.nueva_pestana(self.cerradas.pop())

    def saltar_pestana(self, paso):
        chips = self.tira.chips
        self.activar(chips[(chips.index(self.chip_activo) + paso) % len(chips)])

    def _titulo(self, chip):
        v = chip.pagina.vista
        chip.titulo = "Nueva pestaña" if self.es_nueva(v.url()) else (v.title() or v.url().toString())
        chip.setToolTip(chip.titulo)
        chip.update()
        if chip is self.chip_activo:
            self.setWindowTitle(f"{chip.titulo} — {self._sufijo_titulo()}")

    def _url(self, chip):
        if chip is self.chip_activo:
            url = chip.pagina.vista.url()
            self.omni.set_url(url, self.es_nueva(url))
            self._botones_historial()
            self._estrella()
            self._llave()

    def _carga(self, chip, progreso):
        if not chip.cargando:
            chip.set_cargando(True)
        chip.progreso = progreso
        if chip is self.chip_activo:
            self.progreso.progreso(progreso)
            self.b_recargar.set_icono("parar")

    def _fin_carga(self, chip, ok):
        chip.set_cargando(False)
        chip.progreso = 100
        pagina = chip.pagina
        pagina.colocar()
        if chip is self.chip_activo:
            self.progreso.progreso(100)
            self.b_recargar.set_icono("recargar")
            self._botones_historial()
        if not ok:
            return
        self.registrar_historial(pagina.vista)
        pagina.vista.page().runJavaScript(JS_JSON)
        # con la protección activada no se rellena solo: hay que pedirlo con la llave (y verificarse)
        if self.ajustes.datos["autorrellenar"] and not self.ajustes.datos["proteger_pw"]:
            self.autorrellenar(pagina.vista.page())
        extensiones().notificar_carga(pagina.vista.url().toString())
        if chip is self.chip_activo and self.herr.css.toPlainText().strip():
            self.aplicar_css()

    def _botones_historial(self):
        h = self.vista().history()
        self.b_atras.setEnabled(h.canGoBack())
        self.b_adelante.setEnabled(h.canGoForward())

    # ────────────────────────────────────────────────────────── navegación
    def interpretar(self, texto):
        t = texto.strip()
        if re.match(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?(/|$)", t) or re.match(r"^[\w.-]+:\d+(/|$)", t):
            return QUrl("http://" + t), False
        if re.match(r"^[a-zA-Z][\w+.-]*://", t) or t.startswith(("about:", "view-source:", "data:", "file:")):
            return QUrl(t), False
        if " " not in t and re.match(r"^[^\s/]+\.[a-zA-Z]{2,}(/.*)?$", t):
            return QUrl.fromUserInput(t), False
        return QUrl(BUSCADORES[self.ajustes.datos["buscador"]].format(quote_plus(t))), True

    def enviar_omni(self, texto):
        ahora = datetime.now().timestamp()
        if not texto.strip() or (texto, ) == self._ultimo_envio[:1] and ahora - self._ultimo_envio[1] < 0.4:
            return
        self._ultimo_envio = (texto, ahora)
        self.navegar(self.interpretar(texto)[0])

    def navegar(self, url):
        self.vista().setUrl(url)
        self.enfocar_pagina()

    def recargar_o_parar(self):
        (self.vista().stop if self.chip_activo.cargando else self.vista().reload)()

    def recargar_sin_cache(self):
        self.vista().triggerPageAction(QWebEnginePage.WebAction.ReloadAndBypassCache)

    def ir_inicio(self):
        self.vista().setUrl(QUrl(self.url_nueva()))

    def enfocar_omni(self):
        self.omni.entrada.setFocus()
        self.omni.entrada.selectAll()

    def enfocar_pagina(self):
        if self.chip_activo:
            self.vista().setFocus()

    def zoom(self, paso):
        p = self.pagina()
        p.zoom = 1.0 if paso == 0 else round(max(0.25, min(5.0, p.zoom + paso)), 2)
        p.colocar()
        self.aviso.mostrar(f"🔍  Zoom {round(p.zoom * 100)} %")

    def alternar_pantalla_completa(self):
        if self.isFullScreen():
            self.salir_pantalla_completa()
        else:
            self._estaba_max = self.isMaximized()
            self.showFullScreen()
            self.atajo_esc.setEnabled(True)
            self.aviso.mostrar("Pantalla completa · pulsa Esc o F11 para salir")

    def salir_pantalla_completa(self):
        if self.cabecera.isHidden():
            self.vista().triggerPageAction(QWebEnginePage.WebAction.ExitFullScreen)
            return
        self.showMaximized() if getattr(self, "_estaba_max", False) else self.showNormal()
        self.atajo_esc.setEnabled(False)

    def pantalla_completa_web(self, peticion):
        peticion.accept()
        if peticion.toggleOn():
            self._estaba_max = self.isMaximized()
            self._panel_abierto = self.panel.abierto
            self.cabecera.hide()
            self.panel.hide()
            self.showFullScreen()
            self.atajo_esc.setEnabled(True)
        else:
            self.cabecera.show()
            if getattr(self, "_panel_abierto", False):
                self.panel.show()
            self.showMaximized() if self._estaba_max else self.showNormal()
            self.atajo_esc.setEnabled(False)

    # ────────────────────────────────────────────────────────── paleta, historial, marcadores
    def abrir_paleta(self):
        self.paleta.abrir(self.fuente_general, "Busca comandos, pestañas, accesos, historial… o escribe una URL")

    def ver_historial(self):
        self.paleta.abrir(self.fuente_historial, "Buscar en el historial…")

    def fuente_general(self, q):
        palabras = q.lower().split()

        def vale(*t):
            s = " ".join(t).lower()
            return all(p in s for p in palabras)

        res = []
        if q.strip():
            url, busqueda = self.interpretar(q)
            res.append(("Ir", f"Buscar «{q.strip()}»" if busqueda else f"Ir a {url.toString()}", "", "Enter",
                        lambda u=url: self.navegar(u)))
        for c in self.tira.chips:
            u = c.pagina.vista.url().toString()
            if vale(c.titulo, u):
                res.append(("Pestaña", c.titulo, "" if self.es_nueva(QUrl(u)) else u, "", lambda c=c: self.activar(c)))
        res += [("Comando", n, "", a, f) for n, a, f in self.comandos if vale(n)]
        res += [("Comando", n, "Extensión", a, f) for _, n, a, f in extensiones().comandos if vale(n)]
        res += [("Marcador", m["titulo"], m["url"], "", lambda u=m["url"]: self.navegar(QUrl(u)))
                for m in self.marcadores.datos if vale(m["titulo"], m["url"])]
        if palabras:
            vistos = set()
            for h in self.historial.datos:
                if h["url"] not in vistos and vale(h.get("titulo", ""), h["url"]):
                    vistos.add(h["url"])
                    res.append(("Historial", h.get("titulo") or h["url"], h["url"], "",
                                lambda u=h["url"]: self.navegar(QUrl(u))))
                    if len(vistos) >= 25:
                        break
        return res

    def fuente_historial(self, q):
        palabras = q.lower().split()
        res = []
        for h in self.historial.datos:
            s = f"{h.get('titulo', '')} {h['url']}".lower()
            if all(p in s for p in palabras):
                res.append(("Historial", h.get("titulo") or h["url"], f"{h['fecha']}  ·  {h['url']}", "",
                            lambda u=h["url"]: self.nueva_pestana(u)))
                if len(res) >= 200:
                    break
        return res

    def sugerencias(self, q):
        """Lo que aparece bajo la barra de direcciones mientras escribes."""
        palabras = q.lower().split()
        if not palabras:
            return []

        def vale(*t):
            s = " ".join(t).lower()
            return all(p in s for p in palabras)

        url, busqueda = self.interpretar(q)
        res = [{"tipo": "buscar", "titulo": q.strip(), "url": url.toString(), "motor": self.ajustes.datos["buscador"]}
               if busqueda else {"tipo": "ir", "titulo": url.toString().split("://", 1)[-1], "url": url.toString()}]
        vistos = set()
        for c in self.tira.chips:
            u = c.pagina.vista.url().toString()
            if c is not self.chip_activo and not self.es_nueva(QUrl(u)) and vale(c.titulo, u) and len(vistos) < 2:
                vistos.add(u)
                res.append({"tipo": "pestana", "titulo": c.titulo, "url": u, "accion": lambda c=c: self.activar(c)})
        for m in self.marcadores.datos:
            if m["url"] not in vistos and vale(m["titulo"], m["url"]) and len(res) < 5:
                vistos.add(m["url"])
                res.append({"tipo": "acceso", "titulo": m["titulo"], "url": m["url"]})
        puntos = {}
        for n, h in enumerate(self.historial.datos[:3000]):  # visitas y lo reciente que es
            if h["url"] not in vistos and vale(h.get("titulo", ""), h["url"]):
                titulo, valor = puntos.get(h["url"], (h.get("titulo", ""), 0))
                puntos[h["url"]] = (titulo or h.get("titulo", ""), valor + 1 + 2 / (1 + n / 50))
        for u, (titulo, _) in sorted(puntos.items(), key=lambda x: -x[1][1])[:8 - len(res)]:
            res.append({"tipo": "historial", "titulo": titulo, "url": u})
        return res

    def registrar_historial(self, vista):
        url = vista.url().toString()
        if not url.startswith("http") or not self.ajustes.datos["guardar_historial"]:
            return
        h = self.historial.datos
        if h and h[0]["url"] == url:
            h[0]["titulo"] = vista.title()
        else:
            h.insert(0, {"url": url, "titulo": vista.title(), "fecha": datetime.now().strftime("%d/%m/%Y %H:%M")})
            del h[5000:]
        self.historial.guardar_luego()

    def _estrella(self):
        url = self.vista().url().toString()
        marcado = any(m["url"] == url for m in self.marcadores.datos)
        self.omni.estrella.setChecked(marcado)
        self.omni.estrella.set_icono("estrella_llena" if marcado else "estrella")
        self.omni.estrella.setVisible(not self.es_nueva(self.vista().url()))

    def alternar_marcador(self):
        v = self.vista()
        url = v.url().toString()
        if self.es_nueva(v.url()):
            return
        existente = [m for m in self.marcadores.datos if m["url"] == url]
        if existente:
            self.marcadores.datos.remove(existente[0])
            self.p.marcar_borrado_marcador(url)
            self.aviso.mostrar("Quitado de accesos")
        else:
            self.marcadores.datos.append({"url": url, "titulo": v.title() or url, "ts": datetime.now().timestamp()})
            self.aviso.mostrar("★  Guardado en accesos de la página de inicio")
        self.marcadores.guardar()
        for ventana in self.p.ventanas:
            ventana.generar_nueva()
        self._estrella()

    MAX_ACCESOS = 30

    def _accesos(self):
        """Los accesos de la página de inicio (los predeterminados si aún no tienes ninguno)."""
        return self.marcadores.datos[:self.MAX_ACCESOS] or [{"titulo": t, "url": u} for t, u in ACCESOS_DEFECTO]

    def generar_nueva(self):
        a = self.ajustes.datos
        lista = self._accesos() if a["mostrar_accesos"] else []
        piezas = []
        for i, m in enumerate(lista):
            titulo, url = m.get("titulo") or m["url"], m["url"]
            host = Favicons.host(url)
            icono_web = favicons().ruta(host) if host else None
            if m.get("icono"):
                clase, contenido = "esfera", html.escape(m["icono"])
            elif icono_web and icono_web.exists() and not m.get("color"):
                clase = "esfera blanca"
                contenido = f'<img src="{html.escape(QUrl.fromLocalFile(str(icono_web)).toString(), True)}" alt="">'
            else:
                clase, contenido = "esfera", html.escape((nombre_sitio(host) if host else titulo)[:1].upper() or "?")
            if m.get("color"):
                c = QColor(m["color"])
                fondo = (f"radial-gradient(circle at 32% 25%,{c.lighter(150).name()},{c.name()} 55%,"
                         f"{c.darker(160).name()})")
                brillo = f"rgba({rgb(m['color'])},.55)"
            else:
                tono = tono_de(nombre_sitio(host) if host else titulo)
                fondo = (f"radial-gradient(circle at 32% 25%,hsl({tono},85%,72%),hsl({tono},72%,52%) 55%,"
                         f"hsl({(tono + 30) % 360},70%,32%))")
                brillo = f"hsla({tono},80%,60%,.55)"
            estilo = "" if "blanca" in clase else f' style="background:{fondo}"'
            pos = m.get("pos")
            sitio = (f"left:calc({pos['x'] * 100:.3f}% - 48px);top:calc({pos['y'] * 100:.3f}% - 52px);"
                     if isinstance(pos, dict) else "")
            piezas.append(
                f'<a class="acc e{" libre" if sitio else ""}" draggable="false" data-i="{i}" '
                f'href="{html.escape(url, True)}" style="{sitio}animation-delay:{0.22 + i * 0.03:.3f}s;--brillo:{brillo}">'
                f'<div class="{clase}"{estilo}>{contenido}</div><span>{html.escape(titulo)}</span>'
                f'<button class="ed e1" data-ed="{i}" title="Editar">✎</button>'
                f'<button class="ed e2" data-del="{i}" title="Quitar">✕</button></a>')
        if a["mostrar_accesos"] and not self.incognito:
            piezas.append(f'<a class="acc e nuevo" href="#" style="animation-delay:{0.22 + len(lista) * 0.03:.3f}s">'
                          '<div class="esfera">+</div><span>Añadir</span></a>')
        datos = [{"titulo": m.get("titulo", ""), "url": m["url"], "color": m.get("color", ""), "icono": m.get("icono", "")}
                 for m in lista]
        tema = Apariencia.tema or temas.buscar("aurora")
        if self.incognito:  # en incógnito, siempre las manchas moradas
            tema = dict(tema, fondo=None, animacion="manchas")
        fondo, extra = temas.fondo_pagina_inicio(tema, a["fondo_animado"])
        def js(valor):  # JSON seguro dentro de <script>
            return json.dumps(valor, ensure_ascii=False).replace("<", "\\u003c")

        contenido = (PLANTILLA_NUEVA.replace("%%ACCESOS%%", "".join(piezas)).replace("%%FONDO%%", fondo)
                     .replace("%%ACC_JSON%%", js(datos)).replace("%%MSG_NT%%", js(MSG_NT))
                     .replace("%%PANEL%%", C["superficie"])
                     .replace("%%FONDO_C%%", C["fondo"]).replace("%%FONDO_RGB%%", rgb(C["fondo"]))
                     .replace("%%TEXTO_RGB%%", rgb(C["texto"])).replace("%%TEXTO%%", C["texto"])
                     .replace("%%TENUE%%", C["tenue"])
                     .replace("%%BUSCADOR%%", json.dumps(BUSCADORES[a["buscador"]]))
                     .replace("%%NOMBRE%%", js(a.get("nombre", "")))
                     .replace("%%CSS_EXTRA%%", extra).replace("%%A_RGB%%", rgb(T.a1))
                     .replace("%%A%%", T.a1).replace("%%B%%", T.a2))
        if self.incognito:
            contenido = contenido.replace('<div class="accesos">', '<div class="incog e">🕶 Estás en una ventana de '
                                          'incógnito: al cerrarla se borran el historial, las cookies y los datos de '
                                          'esta sesión.</div><div class="accesos">').replace(
                ".fondo i:nth-child(1){background:var(--a)", ".incog{margin-top:26px;color:#c4b5fd;max-width:560px;"
                "text-align:center;line-height:1.6;animation-delay:.2s}.fondo i:nth-child(1){background:#6d28d9")
            NUEVA_INCOG.write_text(contenido, encoding="utf-8")
        else:
            NUEVA.write_text(contenido, encoding="utf-8")

    def importar_navegador(self):
        from .importar import DialogoImportar
        DialogoImportar(self).exec()

    def accion_inicio(self, d, pagina=None):
        """Añadir, editar, quitar o mover una esfera desde la página de inicio."""
        m = self.marcadores.datos
        ahora = datetime.now().timestamp()
        if not m:  # editar los predeterminados los convierte en tuyos
            m.extend({"url": u, "titulo": t, "ts": ahora} for t, u in ACCESOS_DEFECTO)
        accion, i = d.get("a"), int(d.get("i", -1))
        if accion == "guardar":
            url = QUrl.fromUserInput(str(d.get("url", "")))
            if url.scheme() not in ("http", "https") or not url.host():
                self.aviso.mostrar("Esa dirección no es válida")
                return
            entrada = {"url": url.toString(), "titulo": str(d.get("titulo") or "").strip()[:60]
                       or nombre_sitio(url.host()).capitalize(), "ts": ahora}
            if re.fullmatch(r"#[0-9a-fA-F]{6}", str(d.get("color", ""))):
                entrada["color"] = d["color"].lower()
            if str(d.get("icono", "")).strip():
                entrada["icono"] = str(d["icono"]).strip()[:4]
            if 0 <= i < len(m):
                if m[i]["url"] != entrada["url"]:
                    self.p.marcar_borrado_marcador(m[i]["url"])
                m[i] = entrada
            else:
                existente = next((n for n, x in enumerate(m) if x["url"] == entrada["url"]), None)
                if existente is None:
                    m.append(entrada)
                else:
                    m[existente] = entrada
            self.aviso.mostrar(f"★  «{entrada['titulo']}» en tu página de inicio")
        elif accion == "borrar" and 0 <= i < len(m):
            self.p.marcar_borrado_marcador(m[i]["url"])
            del m[i]
        elif accion == "colocar" and 0 <= i < len(m):
            x, y = (max(0.02, min(0.98, float(d.get(k, 0.5)))) for k in ("x", "y"))
            m[i]["pos"] = {"x": round(x, 4), "y": round(y, 4)}
            m[i]["ts"] = ahora  # para que la posición viaje a tus otros PCs
        elif accion == "ordenar":
            for x in m:
                x.pop("pos", None)
                x["ts"] = ahora
        else:
            return
        self.marcadores.guardar()
        # al colocar, la página que arrastra ya la muestra en su sitio: no se recarga (se vería un parpadeo)
        excepto = pagina if accion == "colocar" else None
        for ventana in self.p.ventanas:
            ventana.generar_nueva()
            ventana.recargar_nuevas(excepto)
            ventana._estrella()

    def set_buscador(self, nombre):
        self.ajustes.datos["buscador"] = nombre
        self.ajustes.guardar()
        self.generar_nueva()
        self.aviso.mostrar(f"Buscador: {nombre}")

    def _favicon_nuevo(self, host):
        if any(Favicons.host(m["url"]) == host for m in self._accesos()):
            self._regenerar.start()

    def _guardar_favicon(self, chip, icono):
        url = chip.pagina.vista.url()
        if not self.incognito and url.scheme() in ("http", "https"):
            favicons().guardar(url.toString(), icono)

    def borrar_historial(self):
        self.historial.datos.clear()
        self.historial.guardar()
        favicons().borrar_todo()
        self.aviso.mostrar("🧹  Historial borrado")

    def borrar_cookies(self):
        self.perfil.cookieStore().deleteAllCookies()
        self.perfil.clearHttpCache()
        self.aviso.mostrar("🧹  Cookies y caché borradas")

    # ────────────────────────────────────────────────────────── descargas
    def abrir_descargas(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.descargas)))

    # ────────────────────────────────────────────────────────── herramientas de desarrollo
    def consola_pagina(self, pagina, nivel, mensaje, linea, origen):
        if mensaje.startswith(MSG_PW):
            self.contrasena_detectada(pagina, mensaje[len(MSG_PW):])
            return
        if mensaje.startswith(MSG_NT):
            if self.es_nueva(pagina.url()) and not self.incognito:  # solo de la página de inicio de Aurora
                try:
                    self.accion_inicio(json.loads(mensaje[len(MSG_NT):]), pagina)
                except (ValueError, TypeError, KeyError):
                    pass
            return
        if mensaje == MSG_GEN:
            self.sugerir_contrasena(pagina)
            return
        if not self.chip_activo or pagina is not self.vista().page():
            return
        N = QWebEnginePage.JavaScriptConsoleMessageLevel
        tipo = {N.WarningMessageLevel: "warn", N.ErrorMessageLevel: "error"}.get(nivel, "log")
        self.panel.consola.escribir(tipo, mensaje, f"{QUrl(origen).fileName() or QUrl(origen).path() or origen}:{linea}")

    def registrar_peticion(self, metodo, tipo, url, bloqueado):
        if self.panel.abierto:
            self.panel.red.anadir(metodo, tipo, url, bloqueado)

    def set_dispositivo(self, nombre):
        self.pagina().set_dispositivo(nombre)
        if DISPOSITIVOS.get(nombre):
            self.aviso.mostrar(f"📱  Simulando {nombre}")

    def rotar_dispositivo(self):
        self.pagina().rotar()

    def alternar_responsive(self):
        self.herr.disp.setCurrentText(LIBRE if self.pagina().disp else "iPhone 15")

    def set_ua(self, nombre):
        self.perfil.setHttpUserAgent(UAS.get(nombre) or self.ua_original)
        self.ajustes.datos["ua"] = nombre
        self.ajustes.guardar()
        self.vista().reload()
        self.aviso.mostrar(f"User-Agent: {nombre}")

    def set_atributo(self, nombre, valor):
        self.perfil.settings().setAttribute(getattr(QWebEngineSettings.WebAttribute, nombre), valor)
        self.vista().reload()

    def set_cache(self, activa):
        T = QWebEngineProfile.HttpCacheType
        self.perfil.setHttpCacheType(T.DiskHttpCache if activa else T.NoCache)
        self.aviso.mostrar("Caché activada" if activa else "Caché desactivada")

    def set_bloqueo(self, activo):
        if self.bloqueador.activo == activo:
            return
        self.bloqueador.activo = activo
        self.set_ajuste("bloqueo", activo)
        self.herr.sw_bloq.blockSignals(True)
        self.herr.sw_bloq.setChecked(activo)
        self.herr.sw_bloq._set(1.0 if activo else 0.0)
        self.herr.sw_bloq.blockSignals(False)
        self.vista().reload()

    # ────────────────────────────────────────────────────────── ajustes
    def set_ajuste(self, clave, valor):
        self.ajustes.datos[clave] = valor
        self.ajustes.guardar()

    def abrir_ajustes(self, seccion=0):
        self.paleta.cerrar()
        self.ajustes_ui.abrir(seccion)

    def recargar_nuevas(self, excepto=None):
        for c in self.tira.chips:
            if self.es_nueva(c.pagina.vista.url()) and c.pagina.vista.page() is not excepto:
                c.pagina.vista.reload()

    def aplicar_acento(self, nombre):
        """nombre = uno de ACENTOS, o "" para usar el del tema."""
        Apariencia.guardar(acento=nombre)
        self.aplicar_tema(Apariencia.tema)

    def aplicar_tema(self, tema, guardar=True):
        """Cambia el tema en caliente en todas las ventanas."""
        if guardar:
            Apariencia.guardar(tema=tema["id"])
        temas.aplicar_colores(tema, Apariencia.datos()["acento"])
        app = QApplication.instance()
        app.setPalette(temas.paleta_qt())
        app.setStyleSheet(hoja_estilo())
        for w in QApplication.allWidgets():
            w.update()
        for ventana in gestor().todas_las_ventanas():
            ventana.generar_nueva()
            ventana.recargar_nuevas()

    def set_fuente(self, nombre):
        self.set_ajuste("tam_fuente", nombre)
        self.perfil.settings().setFontSize(QWebEngineSettings.FontSize.DefaultFontSize, TAMANOS[nombre])
        self.vista().reload()

    def set_dnt(self, activo):
        self.bloqueador.dnt = activo
        self.set_ajuste("dnt", activo)

    def borrar_datos(self, historial, cookies, cache, descargas):
        hecho = []
        if historial:
            self.historial.datos.clear()
            self.historial.guardar()
            hecho.append("historial")
        if cookies:
            self.perfil.cookieStore().deleteAllCookies()
            self.perfil.clearAllVisitedLinks()
            hecho.append("cookies")
        if cache:
            self.perfil.clearHttpCache()
            hecho.append("caché")
        if descargas:
            self.lista_descargas.datos.clear()
            self.lista_descargas.guardar()
            hecho.append("descargas")
        self.aviso.mostrar("🧹  Borrado: " + ", ".join(hecho) if hecho else "No había nada marcado")

    # ────────────────────────────────────────────────────────── contraseñas
    def sugerir_contrasena(self, pagina):
        if not self.ajustes.datos["sugerir_pw"] or self.incognito or pagina is not self.vista().page():
            return
        clave = generar_contrasena()
        self.pregunta.mostrar("¿Usar una contraseña segura?",
                              f"<span style='font-family:Consolas,monospace;color:{C['texto']}'>{html.escape(clave)}"
                              "</span><br>Se guardará sola cuando envíes el formulario.",
                              [("No, gracias", lambda: None, False),
                               ("Usar contraseña", lambda: self.poner_contrasena_generada(clave), True)])

    def poner_contrasena_generada(self, clave=None):
        clave = clave or generar_contrasena()
        pagina = self.vista().page()
        self._generadas[Contrasenas.origen(pagina.url())] = clave
        QApplication.clipboard().setText(clave)
        js = JS_PONER_GENERADA.replace("%%A_RGB%%", rgb(T.a1)) % json.dumps(clave)
        pagina.runJavaScript(js, MUNDO_AURORA, lambda n: self.aviso.mostrar(
            "🔑  Contraseña segura puesta y copiada" if n else "Haz clic primero en el campo de contraseña"))

    def contrasena_detectada(self, pagina, datos):
        if not self.ajustes.datos["ofrecer_pw"] or self.incognito:
            return
        try:
            d = json.loads(datos)
        except ValueError:
            return
        usuario, clave = str(d.get("u", ""))[:200], str(d.get("p", ""))
        origen = Contrasenas.origen(pagina.url())
        if not clave or not origen.startswith("http") or origen in self.claves.datos["nunca"]:
            return
        estado = self.claves.estado(origen, usuario, clave)
        if estado == "igual":
            return
        if self._generadas.get(origen) == clave:  # contraseña que generamos nosotros: se guarda sin preguntar
            self.claves.guardar_cuenta(origen, usuario, clave)
            self._generadas.pop(origen, None)
            self._aviso_guardada("🔑  Contraseña nueva guardada")
            self._llave()
            return

        def guardar():
            self.claves.guardar_cuenta(origen, usuario, clave)
            self._aviso_guardada("🔑  Contraseña guardada")
            self._llave()

        cambiada = estado == "cambiada"
        self.pregunta.mostrar("¿Actualizar la contraseña?" if cambiada else "¿Guardar la contraseña?",
                              f"{usuario or '(sin usuario)'}  ·  {pagina.url().host()}",
                              [("Nunca aquí", lambda: self.claves.nunca(origen), False),
                               ("Actualizar" if cambiada else "Guardar", guardar, True)])

    def _aviso_guardada(self, texto):
        if cifrado_disponible() is None:
            texto = "⚠  Guardada SIN cifrar: no hay llavero del sistema (mira Ajustes → Contraseñas)"
        self.aviso.mostrar(texto)

    def autorrellenar(self, pagina, cuenta=None, reintento=True, forzar=False):
        origen = Contrasenas.origen(pagina.url())
        cuentas = self.claves.de(origen)
        if not cuentas:
            return
        if not forzar and not origen.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            return  # en http normal la contraseña viajaría sin cifrar: solo se rellena pidiéndolo
        c = cuenta or cuentas[0]
        clave = self.claves.leer_clave(c)
        if clave is None:
            if cuenta:
                self.aviso.mostrar("No se puede descifrar esta contraseña (¿llavero bloqueado?)")
            return
        js = JS_RELLENAR.replace("%%A_RGB%%", rgb(T.a1)) % (json.dumps(c["usuario"]), json.dumps(clave),
                                                               json.dumps(origen))

        def hecho(r):
            if r == 1:
                self.aviso.mostrar(f"🔑  Rellenado como {c['usuario'] or 'cuenta guardada'}")
            elif r == -1:  # la página cambió de sitio mientras tanto: no se rellena nada
                return
            elif reintento and not cuenta:  # webs que pintan el formulario más tarde
                QTimer.singleShot(1500, lambda: self._reintentar_relleno(pagina))
            elif cuenta:
                self.aviso.mostrar("No encuentro el formulario de acceso en esta página")

        pagina.runJavaScript(js, MUNDO_AURORA, hecho)

    def _reintentar_relleno(self, pagina):
        try:
            self.autorrellenar(pagina, None, False)
        except RuntimeError:  # la pestaña se cerró antes del reintento
            pass

    def rellenar_pedido(self, cuenta):
        """Relleno desde el menú de la llave: con la protección activada pide verificación."""
        if self.p.verificador.comprobar(self, "rellenar una contraseña"):
            self.autorrellenar(self.vista().page(), cuenta, forzar=True)

    def _llave(self):
        if self.chip_activo:
            hay = bool(self.claves.de(Contrasenas.origen(self.vista().url())))
            self.omni.llave.setVisible(hay)

    def menu_llave(self):
        cuentas = self.claves.de(Contrasenas.origen(self.vista().url()))
        m = menu_bonito(QMenu(self))
        for c in cuentas:
            m.addAction(f"Rellenar como  {c['usuario'] or '(sin usuario)'}",
                        lambda c=c: self.rellenar_pedido(c))
        m.addSeparator()
        m.addAction("Gestionar contraseñas…", lambda: self.abrir_ajustes(Ajustes.indice("Contraseñas")))
        b = self.omni.llave
        m.exec(b.mapToGlobal(QPoint(0, b.height() + 6)))

    def aplicar_css(self):
        self.vista().page().runJavaScript(JS_CSS % json.dumps(self.herr.css.toPlainText()))

    def ver_codigo(self):
        self.nueva_pestana("view-source:" + self.vista().url().toString())

    def captura(self):
        carpeta = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
                       or Path.home()) / NOMBRE
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"captura-{datetime.now():%Y%m%d-%H%M%S}.png"
        imagen = self.vista().grab()
        imagen.save(str(ruta))
        QApplication.clipboard().setPixmap(imagen)
        self.aviso.mostrar(f"📸  Captura guardada en Imágenes/{NOMBRE} y copiada")

    def guardar_pdf(self):
        nombre = re.sub(r'[\\/:*?"<>|]', "_", self.vista().title() or "pagina")[:80] + ".pdf"
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar como PDF", str(self.descargas / nombre), "PDF (*.pdf)")
        if ruta:
            self.vista().page().printToPdf(ruta)

    def medir_rendimiento(self):
        self.panel.abrir(1)
        self.panel.consola.escribir("entrada", "Rendimiento de " + self.vista().url().host())
        self.vista().page().runJavaScript(JS_RENDIMIENTO, lambda r: self.panel.consola.escribir("resultado", r))

    def copiar_url(self):
        QApplication.clipboard().setText(self.vista().url().toString())
        self.aviso.mostrar("🔗  URL copiada")

    def borrar_datos_sitio(self):
        self.vista().page().runJavaScript(JS_BORRAR_SITIO)
        self.vista().reload()
        self.aviso.mostrar(f"🧹  Datos de {self.vista().url().host()} borrados")

    def servir_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta del proyecto web")
        if not carpeta:
            return
        srv = servir(carpeta)
        self.servidores.append(srv)
        puerto = srv.server_address[1]
        self.vigilante.vigilar(carpeta)
        self.herr.estado.setText(f"Sirviendo {carpeta} en http://localhost:{puerto} · recarga en vivo activa")
        self.nueva_pestana(f"http://localhost:{puerto}/")
        self.aviso.mostrar(f"▶  Servidor en localhost:{puerto} con recarga en vivo")

    def vigilar_carpeta(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta a vigilar")
        if carpeta:
            self.vigilante.vigilar(carpeta)
            self.herr.estado.setText(f"Vigilando {carpeta}: al guardar se recarga la pestaña.")
            self.aviso.mostrar("👁  Recarga en vivo activada")

    def detener_vivo(self):
        self.vigilante.parar()
        for s in self.servidores:
            s.shutdown()
        self.servidores.clear()
        self.herr.estado.setText("Ninguna carpeta vigilada.")
        self.aviso.mostrar("■  Recarga en vivo y servidores detenidos")

    def recarga_en_vivo(self, archivo):
        locales = [c for c in self.tira.chips
                   if c.pagina.vista.url().host() in ("localhost", "127.0.0.1") or c.pagina.vista.url().isLocalFile()]
        objetivo = locales or [self.chip_activo]
        for c in objetivo:
            if not self.es_nueva(c.pagina.vista.url()):
                c.pagina.vista.reload()
        self.aviso.mostrar(f"↻  {archivo} cambió")

    # ────────────────────────────────────────────────────────── cierre
    def closeEvent(self, e):
        ultima = len(self.p.ventanas) == 1
        if not self.incognito and ultima:
            sesion = []
            for c in self.tira.chips:
                u = c.pagina.vista.url()
                sesion.append({"url": "" if self.es_nueva(u) else u.toString(), "fijada": c.fijada, "grupo": c.grupo})
            self.ajustes.datos["sesion"] = sesion
            self.ajustes.datos["grupos"] = {k: dict(g) for k, g in self.grupos.items()}
            self.ajustes.datos["ancho_panel"] = self.panel.ancho
            self.ajustes.guardar()
            if self.p.sync:
                self.p.sync.sincronizar(silencioso=True)
        for f in list(self.flotantes):
            f.close()
        for s in self.servidores:
            s.shutdown()
        if self in self.p.ventanas:
            self.p.ventanas.remove(self)
        if self.p.sync:
            try:
                self.p.sync.terminado.disconnect(self._sync_terminada)
            except TypeError:
                pass
        self.panel_descargas.close()
        super().closeEvent(e)
