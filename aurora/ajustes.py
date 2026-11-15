"""Pantalla de ajustes."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403
from .motor import *  # noqa: F401,F403
from .desarrollo import *  # noqa: F401,F403
from .contrasenas import *  # noqa: F401,F403
from .perfiles import *  # noqa: F401,F403
from .asistente import PROVEEDORES, ClienteIA


# ═════════════════════════════ pantalla de ajustes

class Muestra(QAbstractButton):
    """Círculo de color para elegir el acento."""

    def __init__(self, nombre, a1, a2):
        super().__init__()
        self.nombre, self.a1, self.a2 = nombre, a1, a2
        self.setCheckable(True)
        self.setFixedSize(42, 42)
        self.setToolTip(nombre)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._h = 0.0
        self.anim = animacion(self, self._set, 160)

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
        if self.isChecked():
            p.setPen(QPen(QColor(255, 255, 255, 220), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(2, 2, 38, 38))
        m = 7 - 1.5 * self._h
        g = QLinearGradient(m, m, 42 - m, 42 - m)
        g.setColorAt(0, QColor(self.a1))
        g.setColorAt(1, QColor(self.a2))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawEllipse(QRectF(m, m, 42 - 2 * m, 42 - 2 * m))


class Fila(QWidget):
    def __init__(self, titulo, descripcion="", control=None):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(18, 12, 16, 12)
        h.setSpacing(16)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addWidget(QLabel(titulo, objectName="filaTitulo"))
        self.desc = QLabel(descripcion, objectName="tenue")
        self.desc.setWordWrap(True)
        self.desc.setVisible(bool(descripcion))
        textos.addWidget(self.desc)
        h.addLayout(textos, 1)
        if control is not None:
            h.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)


class Tarjeta(QFrame):
    def __init__(self):
        super().__init__(objectName="tarjetaAjuste")
        self.l = QVBoxLayout(self)
        self.l.setContentsMargins(0, 4, 0, 4)
        self.l.setSpacing(0)

    def _separar(self):
        if self.l.count():
            s = QFrame(objectName="separador")
            s.setFixedHeight(1)
            self.l.addWidget(s)

    def fila(self, titulo, descripcion="", control=None):
        self._separar()
        f = Fila(titulo, descripcion, control)
        self.l.addWidget(f)
        return f

    def contenido(self, widget, margen=16):
        self._separar()
        caja = QWidget()
        h = QVBoxLayout(caja)
        h.setContentsMargins(margen, 12, margen, 12)
        h.addWidget(widget)
        self.l.addWidget(caja)
        return widget


def interruptor(valor, al_cambiar):
    sw = Interruptor("", bool(valor))
    if al_cambiar:
        sw.toggled.connect(al_cambiar)
    return sw


def desplegable(opciones, actual, al_cambiar, ancho=230):
    c = QComboBox()
    c.addItems(opciones)
    c.setCurrentText(actual)
    c.setFixedWidth(ancho)
    c.currentTextChanged.connect(al_cambiar)
    return c


def botones(*pares):
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(8)
    for par in pares:
        if not par:
            continue
        texto, funcion = par[0], par[1]
        b = QPushButton(texto, objectName=par[2] if len(par) > 2 else "")
        b.clicked.connect(funcion)
        h.addWidget(b)
    return w


def nueva_tabla(columnas, estirar):
    t = QTableWidget(0, len(columnas))
    t.setHorizontalHeaderLabels(columnas)
    cab = t.horizontalHeader()
    for i in range(len(columnas)):
        modo = QHeaderView.ResizeMode.Stretch if i == estirar else QHeaderView.ResizeMode.ResizeToContents
        cab.setSectionResizeMode(i, modo)
    cab.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    t.verticalHeader().hide()
    t.verticalHeader().setDefaultSectionSize(34)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setShowGrid(False)
    t.setWordWrap(False)
    t.setMinimumHeight(380)
    t.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    return t


class DelegadoNav(QStyledItemDelegate):
    def sizeHint(self, opcion, indice):
        return QSize(0, 40)

    def paint(self, p, opcion, indice):
        texto, icono = indice.data(Qt.ItemDataRole.UserRole)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(opcion.rect).adjusted(0, 2, 0, -2)
        seleccionado = bool(opcion.state & QStyle.StateFlag.State_Selected)
        encima = bool(opcion.state & QStyle.StateFlag.State_MouseOver)
        if seleccionado or encima:
            p.setPen(Qt.PenStyle.NoPen)
            if seleccionado:
                g = QLinearGradient(r.left(), 0, r.right(), 0)
                g.setColorAt(0, con_alfa(T.a1, 0.32))
                g.setColorAt(1, con_alfa(T.a2, 0.08))
                p.setBrush(g)
            else:
                p.setBrush(QColor(255, 255, 255, 12))
            p.drawRoundedRect(r, 10, 10)
        if seleccionado:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.a1))
            p.drawRoundedRect(QRectF(r.left(), r.center().y() - 8, 3, 16), 1.5, 1.5)
        p.setPen(QColor(C["texto"]) if seleccionado else QColor(C["tenue"]))
        p.setFont(Iconos.fuente(10.5))
        p.drawText(QRectF(r.left() + 14, r.top(), 22, r.height()), Qt.AlignmentFlag.AlignCenter, Iconos.glifo(icono))
        p.setFont(opcion.font)
        p.setPen(QColor(C["texto"]))
        p.drawText(QRectF(r.left() + 46, r.top(), r.width() - 50, r.height()), Qt.AlignmentFlag.AlignVCenter, texto)
        p.restore()


class DialogoCuenta(QDialog):
    def __init__(self, padre, sitio="", usuario="", clave=""):
        super().__init__(padre)
        self.setWindowTitle("Contraseña")
        self.setMinimumWidth(420)
        g = QGridLayout(self)
        g.setContentsMargins(22, 20, 22, 18)
        g.setVerticalSpacing(10)
        self.sitio = QLineEdit(sitio, placeholderText="https://ejemplo.com")
        self.usuario = QLineEdit(usuario, placeholderText="usuario o correo")
        self.clave = QLineEdit(clave, placeholderText="contraseña")
        self.clave.setEchoMode(QLineEdit.EchoMode.Password)
        for i, (t, w) in enumerate((("Sitio", self.sitio), ("Usuario", self.usuario), ("Contraseña", self.clave))):
            g.addWidget(QLabel(t), i, 0)
            g.addWidget(w, i, 1)
        g.addWidget(botones(("Cancelar", self.reject), ("Guardar", self.accept, "primario")), 3, 1,
                    Qt.AlignmentFlag.AlignRight)


class Ajustes(QWidget):
    """Pantalla de ajustes: hoja flotante con menú lateral y secciones."""
    SECCIONES = [("General", "ajustes"), ("Apariencia", "pincel"), ("Privacidad y seguridad", "escudo"),
                 ("Contraseñas", "llave"), ("Historial", "reloj"), ("Accesos", "estrella"),
                 ("Descargas", "descarga"), ("Perfiles", "perfil"), ("Sincronización", "sync"),
                 ("Extensiones", "extension"), ("Asistente IA", "ia"), ("Desarrolladores", "dev"),
                 ("Acerca de", "info")]

    @classmethod
    def indice(cls, nombre):
        return [n for n, _ in cls.SECCIONES].index(nombre)

    def __init__(self, padre, ventana):
        super().__init__(padre)
        self.v, self._abierta = ventana, False
        self.hide()
        self._anim_o = None
        self.hoja = QFrame(self, objectName="hoja")
        h = QHBoxLayout(self.hoja)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        nav = QWidget(objectName="navAjustes")
        nav.setFixedWidth(250)
        vn = QVBoxLayout(nav)
        vn.setContentsMargins(14, 20, 14, 14)
        vn.addWidget(QLabel("Ajustes", objectName="tituloAjustes"))
        self.lista = QListWidget(objectName="listaAjustes")
        self.lista.setItemDelegate(DelegadoNav(self.lista))
        self.lista.setMouseTracking(True)
        for texto, icono in self.SECCIONES:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, (texto, icono))
            self.lista.addItem(item)
        vn.addWidget(self.lista, 1)
        pie = QLabel(f"{NOMBRE} · Chromium {self._chromium()}", objectName="tenue")
        vn.addWidget(pie)
        h.addWidget(nav)

        derecha = QWidget()
        vd = QVBoxLayout(derecha)
        vd.setContentsMargins(0, 0, 0, 0)
        vd.setSpacing(0)
        cab = QHBoxLayout()
        cab.setContentsMargins(0, 0, 14, 0)
        self.titulo = QLabel(objectName="tituloSeccion")
        cerrar = BotonIcono("cerrar", "Cerrar (Esc)")
        cerrar.clicked.connect(self.cerrar)
        cab.addWidget(self.titulo, 1)
        cab.addWidget(cerrar)
        vd.addLayout(cab)
        self.paginas = QStackedWidget()
        vd.addWidget(self.paginas, 1)
        h.addWidget(derecha, 1)

        self.lista.currentRowChanged.connect(self.ir)
        self.anim_p = QPropertyAnimation(self.hoja, b"pos", self)
        self.anim_p.setDuration(340)
        self.anim_p.setEasingCurve(QEasingCurve.Type.OutCubic)

    @staticmethod
    def _chromium():
        try:
            from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion
            return qWebEngineChromiumVersion()
        except Exception:
            return "?"

    # ─────────────────────────────── abrir / cerrar / navegar
    def abrir(self, seccion=0):
        self.construir()
        self.setGeometry(self.parentWidget().rect())
        self.colocar()
        destino = self.hoja.pos()
        self.show()
        self.raise_()
        self._abierta = True
        self.lista.blockSignals(True)
        self.lista.setCurrentRow(seccion)
        self.lista.blockSignals(False)
        self.ir(seccion, animado=False)
        self.lista.setFocus()
        animar(self.anim_p, destino + QPoint(0, 30), destino)
        self._fundido(0.0, 1.0)

    def _fundido(self, desde, hasta):
        """Fundido de toda la capa. El efecto se quita al acabar para no anidar efectos (más fluido)."""
        if self._anim_o:
            self._anim_o.stop()
        efecto = QGraphicsOpacityEffect(self)
        efecto.setOpacity(desde)
        self.setGraphicsEffect(efecto)
        self._anim_o = QPropertyAnimation(efecto, b"opacity", self)
        self._anim_o.setDuration(200)
        self._anim_o.setStartValue(desde)
        self._anim_o.setEndValue(hasta)

        def fin():
            if not self._abierta:
                self.hide()
            self.setGraphicsEffect(None)
            self._anim_o = None

        self._anim_o.finished.connect(fin)
        self._anim_o.start()

    def colocar(self):
        w, h = min(1120, self.width() - 60), min(820, self.height() - 50)
        self.hoja.setGeometry((self.width() - w) // 2, (self.height() - h) // 2, w, h)

    def cerrar(self):
        if not self._abierta:
            return
        self._abierta = False
        animar(self.anim_p, self.hoja.pos(), self.hoja.pos() + QPoint(0, 24))
        self._fundido(1.0, 0.0)
        self.v.enfocar_pagina()

    def ir(self, i, animado=True):
        if i < 0:
            return
        self.titulo.setText(self.SECCIONES[i][0])
        self.paginas.setCurrentIndex(i)
        if animado and self.graphicsEffect() is None:
            pagina = self.paginas.widget(i)
            efecto = QGraphicsOpacityEffect(pagina)
            pagina.setGraphicsEffect(efecto)
            a = QPropertyAnimation(efecto, b"opacity", pagina)
            a.setDuration(220)
            a.setStartValue(0.0)
            a.setEndValue(1.0)
            a.finished.connect(lambda: pagina.setGraphicsEffect(None))
            a.start()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.cerrar()
        else:
            super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if not self.hoja.geometry().contains(e.position().toPoint()):
            self.cerrar()

    def paintEvent(self, e):
        QPainter(self).fillRect(self.rect(), QColor(4, 5, 9, 165))

    # ─────────────────────────────── construcción de secciones
    def construir(self):
        while self.paginas.count():
            w = self.paginas.widget(0)
            self.paginas.removeWidget(w)
            w.deleteLater()
        for f in (self._general, self._apariencia, self._privacidad, self._contrasenas, self._historial,
                  self._accesos, self._descargas, self._perfiles, self._sincronizacion, self._extensiones,
                  self._asistente, self._desarrolladores, self._acerca):
            self.paginas.addWidget(f())

    def refrescar(self):
        """Reconstruye las secciones sin cerrar la pantalla (tras crear/borrar perfiles, etc.)."""
        i = self.lista.currentRow()
        self.construir()
        self.paginas.setCurrentIndex(i)

    def _pagina(self):
        contenido = QWidget()
        l = QVBoxLayout(contenido)
        l.setContentsMargins(28, 4, 28, 28)
        l.setSpacing(12)
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        sa.setWidget(contenido)
        return sa, l

    @staticmethod
    def _sub(l, texto):
        l.addWidget(QLabel(texto.upper(), objectName="seccion"))

    def _general(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        t = Tarjeta()
        opciones = ["Restaurar las pestañas anteriores", "Abrir una pestaña nueva"]
        t.fila("Al iniciar Aurora", "Qué se abre cuando arrancas el navegador.",
               desplegable(opciones, opciones[a["inicio"] == "nueva"],
                           lambda x: v.set_ajuste("inicio", "nueva" if x.startswith("Abrir") else "sesion")))
        t.fila("Buscador predeterminado", "El que se usa al escribir en la barra de direcciones.",
               desplegable(list(BUSCADORES), a["buscador"], v.set_buscador))
        nombre = QLineEdit(a.get("nombre", ""), placeholderText="Tu nombre")
        nombre.setFixedWidth(230)
        nombre.editingFinished.connect(lambda: (v.set_ajuste("nombre", nombre.text().strip()), v.generar_nueva(),
                                                v.recargar_nuevas()))
        t.fila("Tu nombre", "Para que la página de inicio te salude.", nombre)
        if sys.platform.startswith("linux"):
            def predeterminado():
                import subprocess
                r = subprocess.run(["xdg-settings", "set", "default-web-browser", "aurora.desktop"],
                                   capture_output=True, text=True)
                v.aviso.mostrar("✓  Aurora es ahora tu navegador predeterminado" if r.returncode == 0 else
                                "No se pudo: instala Aurora con instalar-fedora.sh primero")
            t.fila("Navegador predeterminado", "Abre en Aurora los enlaces de otras aplicaciones. Para volver a "
                                               "Firefox: xdg-settings set default-web-browser "
                                               "org.mozilla.firefox.desktop",
                   botones(("Hacer predeterminado", predeterminado)))
        if sys.platform == "win32":
            t.fila("Navegador predeterminado", "Si instalaste Aurora con el instalador, puedes elegirlo en Windows "
                                               "para abrir enlaces y archivos .html y .pdf.",
                   botones(("Abrir ajustes de Windows",
                            lambda: QDesktopServices.openUrl(QUrl("ms-settings:defaultapps")))))
        l.addWidget(t)

        self._sub(l, "Pestañas")
        t = Tarjeta()
        tiempos = {"Nunca": 0, "5 minutos": 5, "15 minutos": 15, "30 minutos": 30, "1 hora": 60, "3 horas": 180}
        actual = next((k for k, m in tiempos.items() if m == a["dormir_min"]), "30 minutos")
        t.fila("Dormir pestañas inactivas", "Las pestañas que no usas se descargan de memoria y se recargan al "
                                            "volver a ellas. No se duermen las que suenan.",
               desplegable(list(tiempos), actual, lambda x: v.set_ajuste("dormir_min", tiempos[x])))
        l.addWidget(t)

        self._sub(l, "Descargas")
        t = Tarjeta()
        fila_carpeta = t.fila("Carpeta de descargas", str(v.descargas))

        def cambiar():
            carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de descargas", str(v.descargas))
            if carpeta:
                v.descargas = Path(carpeta)
                v.set_ajuste("carpeta_descargas", carpeta)
                fila_carpeta.desc.setText(carpeta)

        fila_carpeta.layout().addWidget(botones(("Cambiar…", cambiar)))
        t.fila("Preguntar dónde guardar cada archivo", "Si está apagado, todo va directo a la carpeta de descargas.",
               interruptor(a["preguntar_descarga"], lambda c: v.set_ajuste("preguntar_descarga", c)))
        l.addWidget(t)
        l.addStretch()
        return sa

    def _apariencia(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        t = Tarjeta()
        caja = QWidget()
        hc = QHBoxLayout(caja)
        hc.setContentsMargins(0, 0, 0, 0)
        hc.setSpacing(6)
        muestras = []
        for nombre, (a1, a2) in ACENTOS.items():
            m = Muestra(nombre, a1, a2)
            m.setChecked(nombre == a["acento"])
            muestras.append(m)
            hc.addWidget(m)

        def elegir(nombre):
            for m in muestras:
                m.setChecked(m.nombre == nombre)
            v.aplicar_acento(nombre)

        hc.addStretch()
        for m in muestras:
            m.clicked.connect(lambda _, n=m.nombre: elegir(n))
        t.fila("Color de acento", "Pestañas, botones, brillos y página de inicio.")
        t.contenido(caja, 18)
        l.addWidget(t)

        self._sub(l, "Página de inicio")
        t = Tarjeta()
        t.fila("Fondo animado", "Las manchas de color que se mueven despacio.",
               interruptor(a["fondo_animado"], lambda c: (v.set_ajuste("fondo_animado", c), v.generar_nueva(),
                                                          v.recargar_nuevas())))
        t.fila("Mostrar accesos", "Los atajos a tus webs guardadas (★).",
               interruptor(a["mostrar_accesos"], lambda c: (v.set_ajuste("mostrar_accesos", c), v.generar_nueva(),
                                                            v.recargar_nuevas())))
        l.addWidget(t)

        self._sub(l, "Webs")
        t = Tarjeta()
        t.fila("Tamaño de letra", "Tamaño base del texto en las páginas.",
               desplegable(list(TAMANOS), a["tam_fuente"], v.set_fuente))
        t.fila("Zoom predeterminado", "Se aplica a las pestañas nuevas. Ctrl + / Ctrl − para cada pestaña.",
               desplegable(ZOOMS, f"{round(a['zoom'] * 100)} %",
                           lambda z: v.set_ajuste("zoom", int(z.split()[0]) / 100)))
        l.addWidget(t)
        l.addStretch()
        return sa

    def _privacidad(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        t = Tarjeta()
        t.fila("Bloquear anuncios y rastreadores", "Bloquea las peticiones a dominios de publicidad conocidos.",
               interruptor(v.bloqueador.activo, v.set_bloqueo))
        lista = t.fila("Lista de bloqueo", f"{len(v.bloqueador.dominios)} dominios. Puedes añadir los tuyos en "
                                           f"bloqueados.txt (uno por línea).")

        def editar():
            archivo = DATOS / "bloqueados.txt"
            if not archivo.exists():
                archivo.write_text("# Un dominio por línea, por ejemplo:\n# anuncios.ejemplo.com\n", encoding="utf-8")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(archivo)))

        def recargar():
            v.bloqueador.cargar_lista()
            lista.desc.setText(f"{len(v.bloqueador.dominios)} dominios. Lista recargada.")

        lista.layout().addWidget(botones(("Editar", editar), ("Recargar", recargar)))
        t.fila("Pedir a las webs que no me rastreen", "Envía las cabeceras «Do Not Track» y «Global Privacy Control».",
               interruptor(a["dnt"], v.set_dnt))
        t.fila("Bloquear cookies de terceros", "Evita el seguimiento entre webs. Algún inicio de sesión "
                                               "integrado podría dejar de funcionar.",
               interruptor(a["cookies_terceros"], lambda c: v.set_ajuste("cookies_terceros", c)))
        t.fila("Guardar historial de navegación", "",
               interruptor(a["guardar_historial"], lambda c: v.set_ajuste("guardar_historial", c)))
        l.addWidget(t)

        self._sub(l, "Borrar datos de navegación")
        t = Tarjeta()
        casillas = QWidget()
        g = QGridLayout(casillas)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(30)
        g.setVerticalSpacing(10)
        opciones = {"historial": QCheckBox("Historial"), "cookies": QCheckBox("Cookies y datos de sitios"),
                    "cache": QCheckBox("Imágenes y archivos en caché"), "descargas": QCheckBox("Lista de descargas")}
        for i, (clave, cb) in enumerate(opciones.items()):
            cb.setChecked(clave != "descargas")
            g.addWidget(cb, i // 2, i % 2)
        t.contenido(casillas, 18)
        t.fila("Se borrará lo marcado", "Las contraseñas guardadas no se tocan.",
               botones(("Borrar datos", lambda: v.borrar_datos(**{k: c.isChecked() for k, c in opciones.items()}),
                        "peligro")))
        l.addWidget(t)
        l.addStretch()
        return sa

    def _contrasenas(self):
        sa, l = self._pagina()
        a, v, claves = self.v.ajustes.datos, self.v, self.v.claves
        t = Tarjeta()
        t.fila("Ofrecer guardar contraseñas", "Al iniciar sesión en una web te pregunta si quieres guardarla.",
               interruptor(a["ofrecer_pw"], lambda c: v.set_ajuste("ofrecer_pw", c)))
        t.fila("Rellenar automáticamente", "Escribe tu usuario y contraseña al abrir la página de acceso.",
               interruptor(a["autorrellenar"], lambda c: v.set_ajuste("autorrellenar", c)))
        modo = cifrado_disponible()
        if modo == "dpapi":
            seguridad = "🔒  Cifradas con tu cuenta de Windows (DPAPI): solo tu usuario en este PC puede leerlas."
        elif modo == "llavero":
            seguridad = ("🔒  Cifradas con AES y una clave guardada en el llavero del sistema (GNOME Keyring o KWallet): "
                         "solo tu usuario, con la sesión iniciada, puede leerlas.")
        else:
            seguridad = ("⚠  No encuentro el llavero del sistema: las contraseñas se guardan solo codificadas. "
                         "Instala «keyring» y «cryptography» (pip install keyring cryptography).")
        t.fila("Sugerir contraseñas seguras", "Al registrarte en una web te propone una contraseña fuerte "
                                              "y la guarda sola.",
               interruptor(a["sugerir_pw"], lambda c: v.set_ajuste("sugerir_pw", c)))
        nunca = t.fila("Cifrado", seguridad)
        l.addWidget(t)

        self._sub(l, "Protección")
        t = Tarjeta()
        verif = v.p.verificador
        hello = hello_disponible()
        sw = interruptor(a["proteger_pw"], lambda c: proteger(c))

        def proteger(c):
            if c and not (hello and a["usar_hello"]) and not verif.tiene_maestra():
                if not verif.crear_maestra(self):
                    sw.blockSignals(True)
                    sw.setChecked(False)
                    sw._set(0.0)
                    sw.blockSignals(False)
                    return
            v.set_ajuste("proteger_pw", c)
            verif.bloquear()

        t.fila("Pedir verificación para ver o copiar contraseñas",
               "Con Windows Hello (huella, cara o PIN) si está disponible; si no, con una contraseña maestra. "
               "Dura 5 minutos.", sw)
        t.fila("Usar Windows Hello", "Disponible en este PC." if hello else
               "No disponible. En Windows instala el paquete «winrt-Windows.Security.Credentials.UI» para activarlo.",
               interruptor(a["usar_hello"], lambda c: v.set_ajuste("usar_hello", c)))

        def cambiar_maestra():
            if verif.tiene_maestra():
                d = DialogoMaestra(self, "cambiar la contraseña maestra")
                if not d.exec():
                    return
                if not verif._coincide(d.clave.text()):
                    QMessageBox.warning(self, "Contraseña incorrecta", "La contraseña maestra no es correcta.")
                    return
            if verif.crear_maestra(self):
                v.aviso.mostrar("🔑  Contraseña maestra guardada")
                self.refrescar()

        t.fila("Contraseña maestra", "Configurada." if verif.tiene_maestra() else "Sin configurar.",
               botones(("Cambiar…" if verif.tiene_maestra() else "Crear…", cambiar_maestra)))
        generada = t.fila("Generador de contraseñas", "Crea una contraseña aleatoria segura de 18 caracteres.")

        def generar():
            clave = generar_contrasena()
            QApplication.clipboard().setText(clave)
            generada.desc.setText(f"<span style='font-family:Consolas,monospace;color:{C['texto']}'>"
                                  f"{html.escape(clave)}</span>  · copiada al portapapeles")

        generada.layout().addWidget(botones(("Generar y copiar", generar)))
        l.addWidget(t)

        self._sub(l, f"Contraseñas guardadas ({len(claves.datos['cuentas'])})")
        barra = QHBoxLayout()
        buscar = QLineEdit(placeholderText="Buscar sitio o usuario…")
        barra.addWidget(buscar, 1)
        tabla = nueva_tabla(["Sitio", "Usuario", "Contraseña", ""], 0)

        def rellenar():
            tabla.setRowCount(0)
            q = buscar.text().lower()
            for c in sorted(claves.datos["cuentas"], key=lambda c: c["origen"]):
                if q and q not in (c["origen"] + c["usuario"]).lower():
                    continue
                f = tabla.rowCount()
                tabla.insertRow(f)
                tabla.setItem(f, 0, QTableWidgetItem(c["origen"].split("://")[-1]))
                tabla.setItem(f, 1, QTableWidgetItem(c["usuario"] or "—"))
                celda = QTableWidgetItem("•" * 10)
                tabla.setItem(f, 2, celda)
                acciones = QWidget()
                ha = QHBoxLayout(acciones)
                ha.setContentsMargins(4, 0, 4, 0)
                ha.setSpacing(0)
                ver = BotonIcono("ojo", "Mostrar / ocultar", tam=30)
                copiar = BotonIcono("copiar", "Copiar contraseña", tam=30)
                editar = BotonIcono("editar", "Editar", tam=30)
                borrar = BotonIcono("borrar", "Borrar", tam=30)
                ver.clicked.connect(lambda _, c=c, it=celda: it.setText("•" * 10) if not it.text().startswith("•")
                                    else it.setText(claves.clave(c)) if v.p.verificador.comprobar(
                                        self, "mostrar una contraseña") else None)
                copiar.clicked.connect(lambda _, c=c: (QApplication.clipboard().setText(claves.clave(c)),
                                                       v.aviso.mostrar("🔑  Contraseña copiada"))
                                       if v.p.verificador.comprobar(self, "copiar una contraseña") else None)
                editar.clicked.connect(lambda _, c=c: editar_cuenta(c))
                borrar.clicked.connect(lambda _, c=c: (claves.borrar(c), rellenar(), v._llave()))
                for b in (ver, copiar, editar, borrar):
                    ha.addWidget(b)
                tabla.setCellWidget(f, 3, acciones)

        def editar_cuenta(c=None):
            if c and not v.p.verificador.comprobar(self, "editar una contraseña"):
                return
            d = DialogoCuenta(self, c["origen"] if c else "", c["usuario"] if c else "", claves.clave(c) if c else "")
            if d.exec() and d.sitio.text().strip() and d.clave.text():
                if c:
                    claves.borrar(c)
                claves.guardar_cuenta(Contrasenas.origen(d.sitio.text().strip()), d.usuario.text().strip(), d.clave.text())
                rellenar()
                v._llave()

        def importar():
            ruta, _ = QFileDialog.getOpenFileName(self, "Importar contraseñas (CSV de Chrome, Edge, Firefox…)",
                                                  str(Path.home()), "CSV (*.csv)")
            if not ruta:
                return
            n = 0
            with open(ruta, newline="", encoding="utf-8-sig") as f:
                for fila in csv.DictReader(f):
                    url = fila.get("url") or fila.get("origin") or ""
                    clave = fila.get("password") or ""
                    if url and clave:
                        claves.guardar_cuenta(Contrasenas.origen(url), fila.get("username", ""), clave)
                        n += 1
            rellenar()
            v.aviso.mostrar(f"🔑  {n} contraseñas importadas")

        def exportar():
            if not v.p.verificador.comprobar(self, "exportar tus contraseñas"):
                return
            if QMessageBox.warning(self, "Exportar contraseñas",
                                   "El archivo CSV tendrá tus contraseñas SIN cifrar. Cualquiera que lo abra "
                                   "podrá verlas.\n\n¿Seguro que quieres exportarlas?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                                   ) != QMessageBox.StandardButton.Yes:
                return
            ruta, _ = QFileDialog.getSaveFileName(self, "Exportar contraseñas", str(v.descargas / "contraseñas.csv"),
                                                  "CSV (*.csv)")
            if ruta:
                with open(ruta, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(["name", "url", "username", "password"])
                    for c in claves.datos["cuentas"]:
                        w.writerow([QUrl(c["origen"]).host(), c["origen"], c["usuario"], claves.clave(c)])
                v.aviso.mostrar("Contraseñas exportadas")

        barra.addWidget(botones(("＋  Añadir", lambda: editar_cuenta()), ("Importar CSV…", importar),
                                ("Exportar…", exportar)))
        buscar.textChanged.connect(rellenar)
        l.addLayout(barra)
        l.addWidget(tabla, 1)
        rellenar()
        n_nunca = len(claves.datos["nunca"])
        if n_nunca:
            def vaciar():
                claves.datos["nunca"].clear()
                claves.guardar()
                nunca.desc.setText(seguridad)
                v.aviso.mostrar("Lista «nunca guardar» vaciada")
            nunca.desc.setText(f"{seguridad}\nSitios en «nunca guardar»: {n_nunca}.")
            nunca.layout().addWidget(botones(("Vaciar lista", vaciar)))
        return sa

    def _historial(self):
        sa, l = self._pagina()
        v = self.v
        barra = QHBoxLayout()
        buscar = QLineEdit(placeholderText="Buscar en el historial…")
        contador = QLabel(objectName="tenue")
        barra.addWidget(buscar, 1)
        barra.addWidget(contador)
        tabla = nueva_tabla(["Fecha", "Título", "Dirección"], 1)
        tabla.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        tabla.setMinimumHeight(520)

        def rellenar():
            tabla.setRowCount(0)
            q = buscar.text().lower().split()
            datos = v.historial.datos
            for i, h in enumerate(datos):
                s = f"{h.get('titulo', '')} {h['url']}".lower()
                if q and not all(p in s for p in q):
                    continue
                f = tabla.rowCount()
                tabla.insertRow(f)
                for col, texto in enumerate((h.get("fecha", ""), h.get("titulo") or h["url"], h["url"])):
                    it = QTableWidgetItem(texto)
                    it.setData(Qt.ItemDataRole.UserRole, i)
                    if col != 1:
                        it.setForeground(QColor(C["tenue"]))
                    tabla.setItem(f, col, it)
                if f >= 1500:
                    break
            contador.setText(f"{len(datos)} entradas ")

        def borrar_sel():
            indices = sorted({tabla.item(i.row(), 0).data(Qt.ItemDataRole.UserRole)
                              for i in tabla.selectionModel().selectedRows()}, reverse=True)
            for i in indices:
                del v.historial.datos[i]
            v.historial.guardar()
            rellenar()

        def borrar_todo():
            v.borrar_historial()
            rellenar()

        def abrir(f, _c=None):
            v.nueva_pestana(tabla.item(f, 2).text())
            self.cerrar()

        barra.addWidget(botones(("Borrar seleccionados", borrar_sel), ("Borrar todo", borrar_todo, "peligro")))
        buscar.textChanged.connect(rellenar)
        tabla.cellDoubleClicked.connect(abrir)
        l.addLayout(barra)
        l.addWidget(QLabel("Doble clic para abrir · Ctrl/Shift para seleccionar varias", objectName="tenue"))
        l.addWidget(tabla, 1)
        rellenar()
        return sa

    def _accesos(self):
        sa, l = self._pagina()
        v = self.v
        l.addWidget(QLabel("Son los atajos de la página de inicio. Doble clic en un nombre o dirección para "
                           "editarlo.", objectName="tenue"))
        tabla = nueva_tabla(["Nombre", "Dirección"], 1)
        tabla.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)

        def rellenar(seleccion=None):
            tabla.blockSignals(True)
            tabla.setRowCount(0)
            for m in v.marcadores.datos:
                f = tabla.rowCount()
                tabla.insertRow(f)
                tabla.setItem(f, 0, QTableWidgetItem(m["titulo"]))
                tabla.setItem(f, 1, QTableWidgetItem(m["url"]))
            tabla.blockSignals(False)
            if seleccion is not None and 0 <= seleccion < tabla.rowCount():
                tabla.selectRow(seleccion)

        def cambiado(item):
            m = v.marcadores.datos[item.row()]
            if item.column() == 1 and m["url"] != item.text():
                v.p.marcar_borrado_marcador(m["url"])
            m["titulo" if item.column() == 0 else "url"] = item.text()
            m["ts"] = datetime.now().timestamp()
            guardar()

        def guardar():
            v.marcadores.guardar()
            v.generar_nueva()
            v.recargar_nuevas()

        def mover(paso):
            f = tabla.currentRow()
            datos = v.marcadores.datos
            if 0 <= f < len(datos) and 0 <= f + paso < len(datos):
                datos[f], datos[f + paso] = datos[f + paso], datos[f]
                guardar()
                rellenar(f + paso)

        def borrar():
            f = tabla.currentRow()
            if 0 <= f < len(v.marcadores.datos):
                v.p.marcar_borrado_marcador(v.marcadores.datos[f]["url"])
                del v.marcadores.datos[f]
                guardar()
                rellenar(min(f, len(v.marcadores.datos) - 1))

        def anadir():
            vista = v.vista()
            if not v.es_nueva(vista.url()):
                v.marcadores.datos.append({"url": vista.url().toString(), "titulo": vista.title() or vista.url().host(),
                                           "ts": datetime.now().timestamp()})
                guardar()
                rellenar(len(v.marcadores.datos) - 1)

        tabla.itemChanged.connect(cambiado)
        l.addWidget(botones(("＋  Añadir pestaña actual", anadir), ("↑  Subir", lambda: mover(-1)),
                            ("↓  Bajar", lambda: mover(1)), ("Borrar", borrar, "peligro")))
        l.addWidget(tabla, 1)
        rellenar()
        return sa

    def _descargas(self):
        sa, l = self._pagina()
        v = self.v
        tabla = nueva_tabla(["Archivo", "Tamaño", "Fecha", "Estado"], 0)

        def tam(b):
            for u in ("B", "KB", "MB", "GB"):
                if b < 1024:
                    return f"{b:.0f} {u}" if u == "B" else f"{b:.1f} {u}"
                b /= 1024
            return f"{b:.1f} TB"

        def rellenar():
            tabla.setRowCount(0)
            for d in v.lista_descargas.datos:
                f = tabla.rowCount()
                tabla.insertRow(f)
                existe = Path(d["ruta"]).exists()
                estado = ("✓ Completada" if existe else "Eliminada") if d.get("ok") else "✕ Fallida"
                for col, texto in enumerate((d["nombre"], tam(d.get("tam", 0)), d.get("fecha", ""), estado)):
                    it = QTableWidgetItem(texto)
                    it.setData(Qt.ItemDataRole.UserRole, d["ruta"])
                    if col:
                        it.setForeground(QColor(C["tenue"]))
                    tabla.setItem(f, col, it)

        def abrir(f, _c=None):
            ruta = tabla.item(f, 0).data(Qt.ItemDataRole.UserRole)
            if Path(ruta).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(ruta))

        def limpiar():
            v.lista_descargas.datos.clear()
            v.lista_descargas.guardar()
            rellenar()

        tabla.cellDoubleClicked.connect(abrir)
        l.addWidget(botones(("Abrir carpeta de descargas", v.abrir_descargas), ("Limpiar lista", limpiar)))
        l.addWidget(QLabel("Doble clic para abrir el archivo", objectName="tenue"))
        l.addWidget(tabla, 1)
        rellenar()
        return sa

    def _perfiles(self):
        sa, l = self._pagina()
        g, v = gestor(), self.v
        intro = QLabel("Cada perfil tiene sus propias sesiones iniciadas, historial, accesos, contraseñas y ajustes. "
                       "Por ejemplo, uno para la uni y otro personal.", objectName="tenue")
        intro.setWordWrap(True)
        l.addWidget(intro)
        t = Tarjeta()
        for info in g.lista.datos:
            nombre = info["nombre"]

            def renombrar(n=nombre):
                nuevo, ok = QInputDialog.getText(self, "Renombrar perfil", "Nombre:", text=n)
                if ok and nuevo.strip() and nuevo.strip() != n:
                    if not g.renombrar(n, nuevo):
                        v.aviso.mostrar("Ya hay un perfil con ese nombre")
                    self.refrescar()

            def color(n=nombre):
                m = menu_bonito(QMenu(self))
                for c in COLORES_PERFIL:
                    pm = QPixmap(14, 14)
                    pm.fill(Qt.GlobalColor.transparent)
                    pp = QPainter(pm)
                    pp.setRenderHint(QPainter.RenderHint.Antialiasing)
                    pp.setBrush(QColor(c))
                    pp.setPen(Qt.PenStyle.NoPen)
                    pp.drawEllipse(1, 1, 12, 12)
                    pp.end()
                    m.addAction(QIcon(pm), c, lambda c=c: (g.cambiar_color(n, c), self.refrescar()))
                m.exec(QCursor.pos())

            def borrar(n=nombre):
                if QMessageBox.question(self, "Borrar perfil", f"¿Borrar el perfil «{n}» y todos sus datos "
                                        "(historial, contraseñas, sesiones…)? No se puede deshacer."
                                        ) == QMessageBox.StandardButton.Yes:
                    if not g.borrar_perfil(n):
                        v.aviso.mostrar("Cierra antes las ventanas de ese perfil")
                    self.refrescar()

            este = nombre == v.p.nombre
            carpeta = DATOS / "perfiles" / info["carpeta"] if info["carpeta"] else DATOS
            f = t.fila(f"{nombre}{'   · este perfil' if este else ''}", str(carpeta),
                       botones(None if este else ("Abrir", lambda _=None, n=nombre: g.nueva_ventana(n)),
                               ("Renombrar", renombrar), ("Color", color),
                               ("Borrar", borrar, "peligro") if info["carpeta"] and not este else None))
            punto = QLabel("●")
            punto.setStyleSheet(f"color:{info['color']};font-size:16pt")
            f.layout().insertWidget(0, punto)
        l.addWidget(t)

        def anadir():
            nombre, ok = QInputDialog.getText(self, "Nuevo perfil", "Nombre del perfil (por ejemplo «Uni»):")
            if ok and nombre.strip():
                creado = g.crear_perfil(nombre)
                if creado:
                    g.nueva_ventana(creado)
                    self.refrescar()
                else:
                    v.aviso.mostrar("Ya hay un perfil con ese nombre")

        l.addWidget(botones(("＋  Añadir perfil", anadir),
                            ("🕶  Nueva ventana de incógnito", lambda: g.nueva_ventana(v.p.nombre, incognito=True))))
        l.addStretch()
        return sa

    def _sincronizacion(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        sync = v.p.sync or (v.p.base.sync if v.p.base else None)
        intro = QLabel("Aurora sincroniza tus accesos, historial y contraseñas entre tus ordenadores usando una "
                       "carpeta que ya se sincronice sola: OneDrive, Google Drive, Dropbox, Syncthing… Elige la "
                       "misma carpeta en todos tus dispositivos.", objectName="tenue")
        intro.setWordWrap(True)
        l.addWidget(intro)
        t = Tarjeta()
        t.fila("Sincronizar este perfil", f"Perfil «{v.p.nombre}». Se sincroniza al abrir, cada 10 minutos y al cerrar.",
               interruptor(a["sync_activa"], lambda c: v.set_ajuste("sync_activa", c)))
        fila = t.fila("Carpeta compartida", a["sync_carpeta"] or "Sin elegir.")

        def elegir():
            carpeta = QFileDialog.getExistingDirectory(self, "Carpeta compartida (OneDrive, Dropbox…)",
                                                       a["sync_carpeta"] or str(Path.home()))
            if carpeta:
                v.set_ajuste("sync_carpeta", carpeta)
                fila.desc.setText(carpeta)

        fila.layout().addWidget(botones(("Elegir…", elegir)))
        disp = QLineEdit(a["sync_dispositivo"], placeholderText=sync.dispositivo() if sync else "")
        disp.setFixedWidth(230)
        disp.editingFinished.connect(lambda: v.set_ajuste("sync_dispositivo", disp.text().strip()))
        t.fila("Nombre de este dispositivo", "Para distinguirlo de los demás (por ejemplo «PC» o «Fedora»).", disp)
        frase = QLineEdit(placeholderText="•••••••• (guardada)" if a["sync_frase"] else "Frase de paso")
        frase.setEchoMode(QLineEdit.EchoMode.Password)
        frase.setFixedWidth(230)
        frase.editingFinished.connect(lambda: (v.set_ajuste("sync_frase", cifrar(frase.text())), frase.clear(),
                                               frase.setPlaceholderText("•••••••• (guardada)"))
                                      if frase.text() else None)
        if HAY_CRYPTO:
            desc = ("Las contraseñas y el historial se cifran con AES usando esta frase antes de salir de tu PC. "
                    "Pon la misma en todos tus dispositivos. Sin frase, las contraseñas no se sincronizan y el "
                    "historial viaja sin cifrar.")
        else:
            desc = "⚠ Para sincronizar contraseñas instala la librería: pip install cryptography"
        t.fila("Frase de paso para las contraseñas", desc, frase)
        l.addWidget(t)
        t = Tarjeta()
        ultima = sync.estado.datos.get("ultima") if sync else ""
        estado = t.fila("Estado", f"Última sincronización: {ultima or 'nunca'}.")

        def ahora():
            if not sync:
                return
            if not (a["sync_activa"] and a["sync_carpeta"]):
                v.aviso.mostrar("Activa la sincronización y elige una carpeta")
                return
            sync.sincronizar()
            try:
                estado.desc.setText(f"Última sincronización: {sync.estado.datos.get('ultima') or 'nunca'}.")
            except RuntimeError:
                pass

        estado.layout().addWidget(botones(("⇅  Sincronizar ahora", ahora, "primario")))
        l.addWidget(t)
        l.addStretch()
        return sa

    def _extensiones(self):
        sa, l = self._pagina()
        ge, v = extensiones(), self.v
        intro = QLabel("Añade funciones a Aurora: userscripts (.user.js, compatibles con Tampermonkey), estilos "
                       "(.user.css) o carpetas con manifest.json que pueden incluir código en Python. Los cambios en "
                       "JavaScript y CSS se aplican al recargar la página.", objectName="tenue")
        intro.setWordWrap(True)
        l.addWidget(intro)

        def instalar():
            ruta, _ = QFileDialog.getOpenFileName(self, "Instalar extensión", str(Path.home()),
                                                  "Extensiones (*.user.js *.user.css)")
            if ruta:
                ge.instalar_archivo(ruta)
                v.aviso.mostrar("🧩  Extensión instalada")
                self.refrescar()

        l.addWidget(botones(("Abrir carpeta", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(CARPETA_EXT)))),
                            ("Recargar", lambda: (ge.recargar(), self.refrescar(), v.aviso.mostrar("🧩  Extensiones recargadas"))),
                            ("Instalar archivo…", instalar)))
        def cambiar(ext, sw, activa):
            if activa and ext.sin_permiso:
                cambio = ge.aprobadas.datos.get(ext.id) is not None
                r = QMessageBox.warning(
                    self, "Permitir extensión de Python",
                    (f"El código de «{ext.nombre}» ha cambiado desde que la aprobaste.\n\n" if cambio else "")
                    + f"«{ext.nombre}» ejecuta código Python con los mismos permisos que tú: puede leer tus "
                      f"archivos, tus contraseñas y usar internet.\n\nCarpeta: {ext.carpeta}\n\n"
                      "Actívala solo si la has escrito tú o confías en quien la hizo. ¿Permitirla?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
                if r != QMessageBox.StandardButton.Yes:
                    sw.blockSignals(True)
                    sw.setChecked(False)
                    sw._set(0.0)
                    sw.blockSignals(False)
                    return
                ge.aprobar(ext)
            ge.cambiar(ext, activa)
            if ext.error:
                v.aviso.mostrar(f"⚠  {ext.nombre}: {ext.error}")

        t = Tarjeta()
        for ext in ge.lista:
            desc = ext.descripcion
            if ext.tipos:
                desc += ("\n" if desc else "") + " · ".join(ext.tipos)
            if ext.error:
                desc += f"\n⚠ {ext.error}"
            elif ext.sin_permiso:
                desc += ("\n🔒 Su código cambió: actívala para revisarla y aprobarla de nuevo."
                         if ext.id in ge.aprobadas.datos else "\n🔒 Necesita tu permiso para ejecutar código Python.")
            sw = interruptor(ge.activa(ext), None)
            sw.toggled.connect(lambda c, e=ext, s=sw: cambiar(e, s, c))
            t.fila(f"{ext.nombre}   {ext.version}".strip(), desc, sw)
        if not ge.lista:
            t.fila("No hay extensiones", f"Copia archivos en {CARPETA_EXT} y pulsa Recargar.")
        l.addWidget(t)
        aviso = QLabel("⚠ Las extensiones de Python ejecutan código en tu ordenador: instala solo las que hayas escrito "
                       "tú o entiendas.", objectName="tenue")
        aviso.setWordWrap(True)
        l.addWidget(aviso)
        l.addStretch()
        return sa

    def _asistente(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        t = Tarjeta()
        modelo = QLineEdit(a["ia_modelo"])
        modelo.setFixedWidth(260)
        modelo.editingFinished.connect(lambda: v.set_ajuste("ia_modelo", modelo.text().strip()))
        url = QLineEdit(a["ia_url"])
        url.setFixedWidth(260)
        url.editingFinished.connect(lambda: v.set_ajuste("ia_url", url.text().strip()))
        url.setEnabled(not a["ia_proveedor"].startswith("Anthropic"))

        def proveedor(p):
            v.set_ajuste("ia_proveedor", p)
            nuevo = "claude-haiku-5-5" if p.startswith("Anthropic") else "llama3.2"
            v.set_ajuste("ia_modelo", nuevo)
            modelo.setText(nuevo)
            url.setEnabled(not p.startswith("Anthropic"))

        t.fila("Proveedor", "Claude necesita una clave de API. Con Ollama el modelo funciona gratis en tu PC.",
               desplegable(PROVEEDORES, a["ia_proveedor"], proveedor, 260))
        t.fila("Modelo", "Por ejemplo claude-haiku-5-5, claude-sonnet-5-5, gpt-4o-mini o llama3.2.", modelo)
        t.fila("Dirección del servidor", "Solo para proveedores compatibles con OpenAI. Ollama: "
                                         "http://localhost:11434/v1 · LM Studio: http://localhost:1234/v1", url)
        clave = QLineEdit(placeholderText="•••••••• (guardada)" if a["ia_clave"] else "Clave de API")
        clave.setEchoMode(QLineEdit.EchoMode.Password)
        clave.setFixedWidth(260)
        clave.editingFinished.connect(lambda: (v.set_ajuste("ia_clave", cifrar(clave.text().strip())), clave.clear(),
                                               clave.setPlaceholderText("•••••••• (guardada)"))
                                      if clave.text().strip() else None)
        t.fila("Clave de API", "Se guarda cifrada. Claude: console.anthropic.com → API keys.", clave)
        t.fila("Usar el contenido de la página", "El asistente lee el texto de la pestaña para poder resumirla o "
                                                 "responder sobre ella.",
               interruptor(a["ia_contexto"], lambda c: v.set_ajuste("ia_contexto", c)))
        l.addWidget(t)
        t = Tarjeta()
        prueba = t.fila("Probar la conexión", "Envía un mensaje corto para comprobar que todo funciona.")
        self._cliente_prueba = ClienteIA()
        respuesta = []

        def probar():
            respuesta.clear()
            prueba.desc.setText("Probando…")
            cfg = v.panel_ia.config()
            self._cliente_prueba.enviar(cfg, "Responde solo con: ¡Hola desde Aurora!",
                                        [{"role": "user", "content": "Hola"}])

        def fin():
            try:
                prueba.desc.setText(f"✓ Funciona. Respuesta: {''.join(respuesta)[:120]}")
            except RuntimeError:
                pass

        def error(m):
            try:
                prueba.desc.setText(f"⚠ {m}")
            except RuntimeError:
                pass

        self._cliente_prueba.trozo.connect(respuesta.append)
        self._cliente_prueba.fin.connect(fin)
        self._cliente_prueba.error.connect(error)
        prueba.layout().addWidget(botones(("Probar", probar), ("Abrir el asistente",
                                                                lambda: (self.cerrar(), v.panel_ia.alternar()))))
        l.addWidget(t)
        nota = QLabel("Privacidad: lo que preguntas (y el texto de la página, si lo activas) se envía al proveedor "
                      "elegido. Con Ollama o LM Studio todo se queda en tu ordenador.", objectName="tenue")
        nota.setWordWrap(True)
        l.addWidget(nota)
        l.addStretch()
        return sa

    def _desarrolladores(self):
        sa, l = self._pagina()
        a, v = self.v.ajustes.datos, self.v
        t = Tarjeta()
        t.fila("Abrir las herramientas al iniciar", "El panel F12 aparece abierto al arrancar.",
               interruptor(a["dev_inicio"], lambda c: v.set_ajuste("dev_inicio", c)))
        t.fila("User-Agent", "Cómo se presenta Aurora ante las webs.",
               desplegable(list(UAS), v.herr.ua.currentText(), v.herr.ua.setCurrentText))
        flags = QLineEdit(a["flags"], placeholderText="--ignore-gpu-blocklist")
        flags.setFixedWidth(300)
        flags.editingFinished.connect(lambda: v.set_ajuste("flags", flags.text().strip()))
        t.fila("Opciones de Chromium", "Parámetros extra del motor. Se aplican al reiniciar Aurora.", flags)
        l.addWidget(t)

        self._sub(l, "Datos")
        t = Tarjeta()
        t.fila("Carpeta de datos de Aurora", str(DATOS),
               botones(("Abrir", lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATOS))))))

        def restablecer():
            if QMessageBox.question(self, "Restablecer ajustes",
                                    "¿Volver a los ajustes de fábrica? Historial, accesos y contraseñas se "
                                    "conservan.") == QMessageBox.StandardButton.Yes:
                sesion = a.get("sesion", [])
                v.ajustes.datos = dict(AJUSTES_DEFECTO, sesion=sesion)
                v.ajustes.guardar()
                v.aplicar_acento("Aurora")
                self.abrir(self.indice("Desarrolladores"))
                v.aviso.mostrar("Ajustes restablecidos · algunos cambios se aplican al reiniciar")

        t.fila("Restablecer ajustes", "Vuelve a la configuración inicial.",
               botones(("Restablecer", restablecer, "peligro")))
        l.addWidget(t)
        l.addStretch()
        return sa

    def _acerca(self):
        sa, l = self._pagina()
        cab = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(crear_icono_app().pixmap(84, 84))
        textos = QVBoxLayout()
        textos.addWidget(QLabel(NOMBRE, objectName="tituloAjustes"))
        from PyQt6.QtCore import PYQT_VERSION_STR
        from . import __version__
        info = QLabel(f"Versión {__version__}  ·  Chromium {self._chromium()}  ·  Qt {qVersion()}  ·  PyQt {PYQT_VERSION_STR}"
                      f"  ·  Python {sys.version.split()[0]}", objectName="tenue")
        info.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        textos.addWidget(info)
        cab.addWidget(logo)
        cab.addSpacing(14)
        cab.addLayout(textos, 1)
        l.addLayout(cab)
        self._sub(l, "Atajos de teclado")
        t = Tarjeta()
        rejilla = QWidget()
        g = QGridLayout(rejilla)
        g.setContentsMargins(0, 0, 0, 0)
        g.setHorizontalSpacing(24)
        g.setVerticalSpacing(8)
        atajos = [(n, a) for n, a, _ in self.v.comandos if a]
        mitad = (len(atajos) + 1) // 2
        for i, (nombre, atajo) in enumerate(atajos):
            col = 0 if i < mitad else 2
            fila = i if i < mitad else i - mitad
            g.addWidget(QLabel(nombre), fila, col)
            g.addWidget(QLabel(atajo, objectName="tecla"), fila, col + 1, Qt.AlignmentFlag.AlignLeft)
        t.contenido(rejilla, 18)
        l.addWidget(t)
        l.addStretch()
        return sa
