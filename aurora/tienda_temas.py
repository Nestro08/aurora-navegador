"""Tienda de temas (sección de Ajustes) y editor para crear los tuyos."""
import getpass

from PyQt6.QtGui import QRadialGradient
from PyQt6.QtWidgets import QColorDialog, QSlider

from .widgets import *  # noqa: F401,F403
from . import temas
from .temas import ANIMACIONES, EVENTOS, PAQUETES, Apariencia

URL_TIENDA_DEFECTO = ""  # se rellena cuando la tienda esté publicada (ver tienda/README.md)


class Miniatura(QWidget):
    """Aurora en pequeño con los colores, el fondo y la animación de un tema."""

    def __init__(self, tema, ancho=264, alto=148):
        super().__init__()
        self.setFixedSize(ancho, alto)
        self.tema, self.imagen = tema, None
        self.cargar_fondo()

    def fijar(self, tema, imagen=None):
        self.tema = tema
        self.imagen = imagen
        if imagen is None:
            self.cargar_fondo()
        self.update()

    def cargar_fondo(self):
        f = self.tema.get("fondo")
        carpeta = temas.carpeta_de(self.tema["id"])
        self.imagen = None
        if f and f["tipo"] == "imagen":
            ruta = (carpeta / f["archivo"]) if carpeta else None
            if self.tema.get("_origen_fondo"):  # en el editor, antes de guardar
                ruta = Path(self.tema["_origen_fondo"])
            if ruta and ruta.exists():
                pm = QPixmap(str(ruta))
                if not pm.isNull():
                    self.imagen = pm.scaled(self.size() * 2, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                            Qt.TransformationMode.SmoothTransformation)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        recorte = QPainterPath()
        recorte.addRoundedRect(QRectF(0, 0, w, h), 10, 10)
        p.setClipPath(recorte)
        if self.tema.get("_captura") is not None:  # miniatura descargada de la tienda
            p.drawPixmap(self.rect(), self.tema["_captura"])
            return
        c = temas.paleta(self.tema)
        a1, a2 = c["acento1"], c["acento2"]
        p.fillRect(self.rect(), QColor(c["fondo"]))
        cuerpo = QRectF(0, 40, w, h - 40)
        if self.imagen is not None:
            fuente = QRectF(0, 0, self.imagen.width(), self.imagen.height() * cuerpo.height() / h)
            p.drawPixmap(cuerpo, self.imagen, fuente)
            p.fillRect(cuerpo, con_alfa(c["fondo"], (self.tema.get("fondo") or {}).get("oscurecer", 0.35)))
        elif (self.tema.get("fondo") or {}).get("tipo") == "video":
            g = QLinearGradient(0, cuerpo.top(), w, h)
            g.setColorAt(0, con_alfa(a1, 0.55))
            g.setColorAt(1, con_alfa(a2, 0.35))
            p.fillRect(cuerpo, g)
            p.setPen(QColor(c["texto"]))
            p.drawText(cuerpo.adjusted(0, 0, -8, -6), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, "▶ vídeo")
        else:
            anim = self.tema.get("animacion", "manchas")
            if anim == "manchas":
                for (cx, cy, r), color in zip(((0.25, 0.55, 0.42), (0.75, 0.7, 0.38), (0.5, 1.0, 0.32)),
                                              (a1, a2, "#ff4fa3")):
                    g = QRadialGradient(QPointF(cx * w, cy * h), r * w)
                    g.setColorAt(0, con_alfa(color, 0.55))
                    g.setColorAt(1, con_alfa(color, 0.0))
                    p.fillRect(cuerpo, g)
            elif anim == "aurora":
                for i, (color, y) in enumerate(((a1, 0.38), (a2, 0.55), (a1, 0.72))):
                    g = QLinearGradient(0, 0, w, 0)
                    g.setColorAt(0, con_alfa(color, 0.0))
                    g.setColorAt(0.5, con_alfa(color, 0.5 - i * 0.1))
                    g.setColorAt(1, con_alfa(color, 0.0))
                    p.fillRect(QRectF(0, y * h - 12, w, 24), g)
            elif anim == "particulas":
                import random
                azar = random.Random(self.tema["id"])
                p.setPen(Qt.PenStyle.NoPen)
                for _ in range(60):
                    p.setBrush(con_alfa(azar.choice((a1, a2)), azar.uniform(0.3, 0.9)))
                    r = azar.uniform(0.6, 1.8)
                    p.drawEllipse(QPointF(azar.uniform(0, w), azar.uniform(cuerpo.top(), h)), r, r)
        # cabecera: pestañas y barra de direcciones
        p.fillRect(QRectF(0, 0, w, 40), QColor(c["fondo"]))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(c["chip_activo"]))
        p.drawRoundedRect(QRectF(8, 5, 70, 13), 4, 4)
        p.setBrush(QColor(c["chip"]))
        p.drawRoundedRect(QRectF(82, 5, 60, 13), 4, 4)
        g = QLinearGradient(12, 0, 74, 0)
        g.setColorAt(0, QColor(a1))
        g.setColorAt(1, QColor(a2))
        p.setBrush(g)
        p.drawRoundedRect(QRectF(12, 16, 62, 1.6), 1, 1)
        p.setPen(QPen(QColor(c["borde"]), 1))
        p.setBrush(QColor(c["chip"]))
        p.drawRoundedRect(QRectF(30, 22, w - 60, 13), 6.5, 6.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(a1))
        p.drawEllipse(QRectF(w - 22, 24, 9, 9))
        # página de inicio
        f = QFont(self.font())
        f.setPointSizeF(15)
        f.setWeight(QFont.Weight.Light)
        p.setFont(f)
        p.setPen(QColor(c["texto"]))
        p.drawText(QRectF(0, 52, w, 26), Qt.AlignmentFlag.AlignCenter, "12:30")
        p.setPen(QPen(con_alfa(c["texto"], 0.25), 1))
        p.setBrush(con_alfa(c["fondo"], 0.6))
        p.drawRoundedRect(QRectF(w * 0.2, 86, w * 0.6, 14), 7, 7)
        for i in range(5):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(mezcla(a1, a2, i / 4))
            p.drawRoundedRect(QRectF(w / 2 - 62 + i * 26, 112, 18, 18), 5, 5)


class TarjetaTema(QFrame):
    def __init__(self, tema, activo=False, botones_=()):
        super().__init__(objectName="tarjetaTema")
        self.setProperty("activo", activo)
        l = QVBoxLayout(self)
        l.setContentsMargins(10, 10, 10, 10)
        l.setSpacing(6)
        self.miniatura = Miniatura(tema)
        l.addWidget(self.miniatura, 0, Qt.AlignmentFlag.AlignHCenter)
        titulo = QLabel(f"<b>{html.escape(tema['nombre'])}</b>" + (f"  <span style='color:{C['tenue']}'>"
                                                                   f"de {html.escape(tema['autor'])}</span>"
                                                                   if tema.get("autor") else ""))
        l.addWidget(titulo)
        extras = []
        if tema.get("sonidos"):
            extras.append("🔊 sonidos")
        if tema.get("fondo"):
            extras.append("🖼 fondo propio" if tema["fondo"]["tipo"] == "imagen" else "🎬 vídeo de fondo")
        elif tema.get("animacion") not in (None, "ninguna"):
            extras.append("✨ " + ANIMACIONES[tema["animacion"]].lower())
        desc = QLabel(tema.get("descripcion", "") + ("\n" if tema.get("descripcion") and extras else "")
                      + " · ".join(extras), objectName="tenue")
        desc.setWordWrap(True)
        desc.setFixedWidth(264)
        l.addWidget(desc)
        l.addStretch()
        l.addWidget(botones(*botones_))


class BotonColor(QPushButton):
    def __init__(self, color, al_cambiar):
        super().__init__()
        self.setFixedSize(56, 28)
        self.al_cambiar = al_cambiar
        self.fijar(color)
        self.clicked.connect(self._elegir)

    def fijar(self, color):
        self.color = color
        self.setStyleSheet(f"background:{color};border:1px solid {C['borde_fuerte']};border-radius:8px")

    def _elegir(self):
        c = QColorDialog.getColor(QColor(self.color), self, "Elige un color")
        if c.isValid():
            self.fijar(c.name())
            self.al_cambiar()


class DialogoTema(QDialog):
    """Editor: colores, fondo (animación, imagen o vídeo) y sonidos, con vista previa en directo."""

    def __init__(self, padre, tema=None):
        super().__init__(padre)
        self.setWindowTitle("Editar tema" if tema and tema["id"] not in temas.IDS_INTEGRADOS else "Crear tema")
        self.setMinimumWidth(640)
        base = tema or temas.buscar(Apariencia.datos()["tema"])
        self.editando = tema["id"] if tema and tema["id"] not in temas.IDS_INTEGRADOS else None
        carpeta = temas.carpeta_de(base["id"])
        # archivos del tema: nombre dentro del tema → ruta de donde se copiará al guardar
        self.archivos = {n: str(carpeta / n) for n in temas.archivos_de(base)} if carpeta else {}
        self.fondo = dict(base["fondo"]) if base.get("fondo") else None
        self.sonidos = dict(base["sonidos"]) if base.get("sonidos") else None

        h = QHBoxLayout(self)
        h.setContentsMargins(22, 20, 22, 18)
        h.setSpacing(20)
        g = QGridLayout()
        g.setVerticalSpacing(9)
        fila = 0

        def poner(etiqueta, w):
            nonlocal fila
            g.addWidget(QLabel(etiqueta), fila, 0)
            g.addWidget(w, fila, 1)
            fila += 1

        self.nombre = QLineEdit(base["nombre"] if self.editando else f"{base['nombre']} (mío)")
        self.autor = QLineEdit(base.get("autor") if self.editando else getpass.getuser())
        self.descripcion = QLineEdit(base.get("descripcion", "") if self.editando else "")
        poner("Nombre", self.nombre)
        poner("Autor", self.autor)
        poner("Descripción", self.descripcion)
        colores = QWidget()
        hc = QHBoxLayout(colores)
        hc.setContentsMargins(0, 0, 0, 0)
        self.colores = {}
        for clave, texto in (("fondo", "Fondo"), ("texto", "Texto"), ("acento1", "Acento"), ("acento2", "Acento 2")):
            caja = QVBoxLayout()
            b = BotonColor(base["colores"][clave], self.previsualizar)
            self.colores[clave] = b
            caja.addWidget(b)
            caja.addWidget(QLabel(texto, objectName="tenue"), 0, Qt.AlignmentFlag.AlignHCenter)
            hc.addLayout(caja)
        poner("Colores", colores)
        self.tipo_fondo = QComboBox()
        self.tipo_fondo.addItems(["Animación", "Imagen", "Vídeo"])
        self.tipo_fondo.setCurrentIndex({None: 0, "imagen": 1, "video": 2}[(self.fondo or {}).get("tipo")])
        self.tipo_fondo.currentIndexChanged.connect(self._cambio_fondo)
        poner("Fondo de inicio", self.tipo_fondo)
        self.animacion = QComboBox()
        self.animacion.addItems(list(ANIMACIONES.values()))
        self.animacion.setCurrentText(ANIMACIONES[base.get("animacion", "manchas")])
        self.animacion.currentIndexChanged.connect(self.previsualizar)
        poner("Animación", self.animacion)
        self.b_archivo = QPushButton("Elegir archivo…")
        self.b_archivo.clicked.connect(self._elegir_fondo)
        poner("Archivo", self.b_archivo)
        self.oscurecer = QSlider(Qt.Orientation.Horizontal)
        self.oscurecer.setRange(0, 90)
        self.oscurecer.setValue(int((self.fondo or {}).get("oscurecer", 0.35) * 100))
        self.oscurecer.valueChanged.connect(self.previsualizar)
        poner("Oscurecer fondo", self.oscurecer)
        self.paquete = QComboBox()
        self.paquete.addItems(["Sin sonidos"] + list(PAQUETES.values()) + ["Mis archivos .wav…"])
        s = self.sonidos or {}
        self.paquete.setCurrentText(PAQUETES[s["paquete"]] if "paquete" in s else
                                    "Mis archivos .wav…" if s else "Sin sonidos")
        self.paquete.currentIndexChanged.connect(self._cambio_sonidos)
        poner("Sonidos", self.paquete)
        self.propios = QWidget()
        hp = QHBoxLayout(self.propios)
        hp.setContentsMargins(0, 0, 0, 0)
        self.b_sonidos = {}
        for evento, texto in EVENTOS.items():
            b = QPushButton(texto.split()[0])
            b.setToolTip(f"Sonido al {texto.lower()} (.wav)")
            b.clicked.connect(lambda _, ev=evento: self._elegir_sonido(ev))
            self.b_sonidos[evento] = b
            hp.addWidget(b)
        poner("", self.propios)
        self.error = QLabel("", objectName="error")
        self.error.setWordWrap(True)
        g.addWidget(self.error, fila, 0, 1, 2)
        izquierda = QVBoxLayout()
        izquierda.addLayout(g)
        izquierda.addStretch()
        izquierda.addWidget(botones(("Cancelar", self.reject), ("Guardar y aplicar", self._guardar, "primario")))
        h.addLayout(izquierda, 1)
        derecha = QVBoxLayout()
        derecha.addWidget(QLabel("Vista previa", objectName="tenue"))
        self.vista = Miniatura(base, 300, 168)
        derecha.addWidget(self.vista)
        derecha.addStretch()
        h.addLayout(derecha)
        self._cambio_fondo()
        self._cambio_sonidos()

    # ─────────────────────────────── controles
    def _cambio_fondo(self):
        tipo = self.tipo_fondo.currentIndex()
        self.animacion.setEnabled(tipo == 0)
        self.b_archivo.setEnabled(tipo > 0)
        self.oscurecer.setEnabled(tipo > 0)
        if self.fondo and ((tipo == 1) != (self.fondo["tipo"] == "imagen") or tipo == 0):
            self.fondo = None
        self.b_archivo.setText(self.fondo["archivo"] if self.fondo else "Elegir archivo…")
        self.previsualizar()

    def _elegir_fondo(self):
        video = self.tipo_fondo.currentIndex() == 2
        filtro = "Vídeos (*.webm *.mp4)" if video else "Imágenes (*.jpg *.jpeg *.png *.webp)"
        ruta, _ = QFileDialog.getOpenFileName(self, "Fondo de la página de inicio", str(Path.home()), filtro)
        if ruta:
            nombre = "fondo" + Path(ruta).suffix.lower()
            self.archivos = {k: v for k, v in self.archivos.items() if not k.startswith("fondo.")}
            self.archivos[nombre] = ruta
            self.fondo = {"tipo": "video" if video else "imagen", "archivo": nombre,
                          "oscurecer": self.oscurecer.value() / 100}
            self.b_archivo.setText(Path(ruta).name)
            self.previsualizar()

    def _cambio_sonidos(self):
        texto = self.paquete.currentText()
        self.propios.setVisible(texto == "Mis archivos .wav…")
        for evento, b in self.b_sonidos.items():
            b.setText(("✓ " if (self.sonidos or {}).get(evento) else "") + EVENTOS[evento].split()[0])

    def _elegir_sonido(self, evento):
        ruta, _ = QFileDialog.getOpenFileName(self, EVENTOS[evento], str(Path.home()), "Sonidos (*.wav)")
        if ruta:
            if not self.sonidos or "paquete" in self.sonidos:
                self.sonidos = {}
            self.archivos[f"{evento}.wav"] = ruta
            self.sonidos[evento] = f"{evento}.wav"
            self._cambio_sonidos()

    def tema(self):
        anim = list(ANIMACIONES)[self.animacion.currentIndex()]
        fondo = dict(self.fondo, oscurecer=self.oscurecer.value() / 100) if self.fondo else None
        texto = self.paquete.currentText()
        paquete = next((k for k, v in PAQUETES.items() if v == texto), None)
        sonidos = {"paquete": paquete} if paquete else (
            {e: a for e, a in (self.sonidos or {}).items() if e in EVENTOS} or None
            if texto == "Mis archivos .wav…" else None)
        return {"id": self.editando or temas.slug_tema(self.nombre.text()), "nombre": self.nombre.text().strip(),
                "autor": self.autor.text().strip(), "descripcion": self.descripcion.text().strip(), "version": "1.0",
                "colores": {k: b.color for k, b in self.colores.items()}, "animacion": anim, "fondo": fondo,
                "sonidos": sonidos}

    def previsualizar(self):
        t = self.tema()
        if t["fondo"] and t["fondo"]["archivo"] in self.archivos:
            t["_origen_fondo"] = self.archivos[t["fondo"]["archivo"]]
        self.vista.fijar(t)

    def _guardar(self):
        t = self.tema()
        if not t["nombre"]:
            self.error.setText("Ponle un nombre al tema.")
            return
        if self.tipo_fondo.currentIndex() > 0 and not t["fondo"]:
            self.error.setText("Elige el archivo de fondo, o vuelve a «Animación».")
            return
        if not self.editando:  # no pisar otro tema tuyo con el mismo nombre
            base, n = t["id"], 2
            while (temas.CARPETA_TEMAS / t["id"]).exists():
                t["id"], n = f"{base}-{n}", n + 1
        usados = set(temas.archivos_de(t))
        try:
            self.resultado = temas.guardar(t, {n: r for n, r in self.archivos.items() if n in usados})
        except (OSError, ValueError) as e:
            self.error.setText(f"No se pudo guardar: {e}")
            return
        self.accept()


def seccion_temas(ajustes, l):
    """Rellena la sección «Temas» de Ajustes en el layout l."""
    v = ajustes.v
    a = Apariencia.datos()
    activo = a["tema"]
    intro = QLabel("Cambia los colores de todo Aurora, el fondo de la página de inicio y los sonidos. Crea los tuyos "
                   "y compártelos como archivo .aurora-tema.", objectName="tenue")
    intro.setWordWrap(True)
    l.addWidget(intro)

    def aplicar(tema):
        v.aplicar_tema(tema)
        v.aviso.mostrar(f"🎨  Tema «{tema['nombre']}» aplicado")
        ajustes.refrescar()

    def crear(tema=None):
        d = DialogoTema(ajustes, tema)
        if d.exec():
            aplicar(d.resultado)

    def importar():
        ruta, _ = QFileDialog.getOpenFileName(ajustes, "Importar tema", str(Path.home()), "Temas de Aurora (*.aurora-tema)")
        if ruta:
            try:
                aplicar(temas.importar_zip(ruta))
            except ValueError as e:
                QMessageBox.warning(ajustes, "No se pudo importar", str(e))

    def exportar(tema):
        ruta, _ = QFileDialog.getSaveFileName(ajustes, "Exportar tema", str(v.descargas / f"{tema['id']}.aurora-tema"),
                                              "Temas de Aurora (*.aurora-tema)")
        if ruta:
            temas.exportar_zip(tema, ruta if ruta.endswith(".aurora-tema") else ruta + ".aurora-tema")
            v.aviso.mostrar("🎨  Tema exportado")

    def borrar(tema):
        if QMessageBox.question(ajustes, "Eliminar tema", f"¿Eliminar «{tema['nombre']}»?") \
                != QMessageBox.StandardButton.Yes:
            return
        temas.borrar(tema["id"])
        if tema["id"] == activo:
            v.aplicar_tema(temas.buscar("aurora"))
        ajustes.refrescar()

    l.addWidget(botones(("＋  Crear tema…", lambda: crear()), ("Importar .aurora-tema…", importar)))

    def rejilla(tarjetas):
        caja = QWidget()
        g = QGridLayout(caja)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(12)
        for i, t in enumerate(tarjetas):
            g.addWidget(t, i // 2, i % 2)
        g.setColumnStretch(2, 1)
        return caja

    ajustes._sub(l, "Tus temas")
    tarjetas = []
    for t in temas.instalados():
        propio = t["id"] not in temas.IDS_INTEGRADOS
        acciones = [("En uso" if t["id"] == activo else "Aplicar", lambda _, t=t: aplicar(t), "primario"),
                    ("Editar" if propio else "Personalizar", lambda _, t=t: crear(t)),
                    ("Exportar…", lambda _, t=t: exportar(t))]
        if propio:
            acciones.append(("Eliminar", lambda _, t=t: borrar(t), "peligro"))
        tarjetas.append(TarjetaTema(t, t["id"] == activo, acciones))
    l.addWidget(rejilla(tarjetas))

    ajustes._sub(l, "Tienda en línea")
    estado = QLabel("", objectName="tenue")
    estado.setWordWrap(True)
    l.addWidget(estado)
    tienda_caja = QVBoxLayout()
    l.addLayout(tienda_caja)
    url = a.get("tienda_url") or URL_TIENDA_DEFECTO
    campo = QLineEdit(url, placeholderText="https://…/indice.json")
    campo.editingFinished.connect(lambda: (Apariencia.guardar(tienda_url=campo.text().strip()), ajustes.refrescar())
                                  if campo.text().strip() != url else None)
    fila = QHBoxLayout()
    fila.addWidget(QLabel("Dirección de la tienda"))
    fila.addWidget(campo, 1)
    l.addLayout(fila)
    if not url:
        estado.setText("Aún no hay una tienda configurada. Cuando publiques una (mira tienda/README.md en el "
                       "proyecto), pon aquí la dirección de su indice.json.")
    else:
        estado.setText("Cargando la tienda…")
        tienda = temas.Tienda(ajustes)
        ajustes._tienda = tienda  # que no se destruya mientras descarga
        ids = {t["id"] for t in temas.instalados()}

        def instalar(tema, boton):
            boton.setEnabled(False)
            boton.setText("Descargando…")
            tienda.instalar(tema)

        def instalado(tema, error):
            if error:
                QMessageBox.warning(ajustes, "No se pudo instalar", f"{tema['nombre']}: {error}")
                ajustes.refrescar()
            else:
                aplicar(tema)

        def listo(lista, error):
            try:
                if error:
                    estado.setText(f"⚠ No se pudo abrir la tienda: {error}")
                    return
                nuevos = [t for t in lista if t["id"] not in ids]
                estado.setText(f"{len(nuevos)} temas para instalar." if nuevos else
                               "Ya tienes todos los temas de la tienda.")
                tarjetas_t = {}
                for t in nuevos:
                    tarjeta = TarjetaTema(t, False, [])
                    b = QPushButton("Instalar y aplicar", objectName="primario")
                    b.clicked.connect(lambda _, t=t, b=b: instalar(t, b))
                    tarjeta.layout().itemAt(tarjeta.layout().count() - 1).widget().layout().addWidget(b)
                    tarjetas_t[t["id"]] = tarjeta
                    tienda.miniatura(t)
                tienda_caja.addWidget(rejilla(list(tarjetas_t.values())))
                tienda._tarjetas = tarjetas_t
            except RuntimeError:  # se cerró Ajustes mientras cargaba
                pass

        def miniatura(ident, pm):
            try:
                t = tienda._tarjetas.get(ident)
                if t:
                    t.miniatura.tema = dict(t.miniatura.tema, _captura=pm)
                    t.miniatura.update()
            except (RuntimeError, AttributeError):
                pass

        tienda.indice_listo.connect(listo)
        tienda.miniatura_lista.connect(miniatura)
        tienda.instalado.connect(instalado)
        tienda.cargar_indice(url)

    ajustes._sub(l, "Sonidos")
    t = Tarjeta_()
    volumenes = {"Bajo": 0.3, "Medio": 0.6, "Alto": 1.0}
    actual = min(volumenes, key=lambda k: abs(volumenes[k] - a["volumen"]))
    t.fila("Sonidos del tema", "Al abrir, cerrar y cambiar de pestaña y al terminar una descarga (si el tema los trae).",
           interruptor_(a["sonidos"], lambda c: Apariencia.guardar(sonidos=c)))
    vol = desplegable_(list(volumenes), actual, lambda x: (Apariencia.guardar(volumen=volumenes[x]),
                                                            temas.sonidos().tocar("abrir")))
    t.fila("Volumen", "", vol)
    l.addWidget(t)
    l.addStretch()


# los widgets de filas viven en ajustes.py; se inyectan para no crear un import circular
Tarjeta_ = interruptor_ = desplegable_ = botones = None
