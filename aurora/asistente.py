"""Asistente con IA en un panel lateral: resume, traduce y explica la página o lo que selecciones.

Dos modos:
  • Con tu cuenta (por defecto): el panel abre la web de tu IA (Claude, ChatGPT, Gemini…) con la sesión de tu
    perfil de Aurora. Las conversaciones quedan en tu cuenta. Los botones rápidos escriben la petición, con el
    texto de la página, en la caja de chat de la web; la envías tú con Enter.
  • Avanzado, con clave de API: Anthropic o cualquier proveedor compatible con OpenAI, incluido Ollama (gratis y
    local: http://localhost:11434/v1). Las respuestas llegan en streaming.
"""
import threading
import urllib.error
import urllib.request

from .contrasenas import *  # noqa: F401,F403
from .desarrollo import Asa

PROVEEDORES = ["Anthropic (Claude)", "Compatible con OpenAI (OpenAI, Ollama, LM Studio…)"]
MODO_API = "api"
IAS_WEB = {  # nombre: (dirección, quién la hace)
    "Claude": ("https://claude.ai/new", "Anthropic"),
    "ChatGPT": ("https://chatgpt.com/", "OpenAI"),
    "Gemini": ("https://gemini.google.com/app", "Google"),
    "Copilot": ("https://copilot.microsoft.com/", "Microsoft"),
    "Perplexity": ("https://www.perplexity.ai/", "Respuestas con fuentes"),
    "Le Chat": ("https://chat.mistral.ai/chat", "Mistral"),
}
# Escribe en la caja de chat de la web de la IA (corre en el mundo aislado de Aurora). Primero como un pegado
# (los editores de Claude, ChatGPT… lo tratan igual que Ctrl+V); si la web no lo recoge, como texto tecleado.
JS_ESCRIBIR = r"""((t)=>{const sel=['div.ProseMirror[contenteditable=true]','#prompt-textarea','rich-textarea [contenteditable=true]',
'[contenteditable=true][role=textbox]','textarea:not([disabled]):not([readonly])','[contenteditable=true]'];
let el=null;for(const s of sel){el=[...document.querySelectorAll(s)].find(e=>e.offsetParent!==null);if(el)break}
if(!el)return 0;el.focus();
if(el instanceof HTMLTextAreaElement){Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(el,t);
 el.dispatchEvent(new Event('input',{bubbles:true}));return 1}
const dt=new DataTransfer();dt.setData('text/plain',t);
const ev=new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true});el.dispatchEvent(ev);
if(!ev.defaultPrevented){document.execCommand('selectAll',false);document.execCommand('insertText',false,t)}
return 1})(%s)"""
ACCIONES = [
    ("Resumir", "Resume esta página en 5-8 puntos clave, en español."),
    ("Puntos clave", "Extrae las ideas, datos y conclusiones más importantes de esta página en una lista."),
    ("Traducir", "Traduce al español el contenido principal de esta página, manteniendo el formato."),
    ("Explicar selección", "Explícame de forma sencilla el texto que he seleccionado. Si es código, "
                           "explica qué hace paso a paso."),
]


class ClienteIA(QObject):
    trozo = pyqtSignal(str)
    fin = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._parar = False

    def parar(self):
        self._parar = True

    def enviar(self, cfg, sistema, mensajes):
        self._parar = False
        threading.Thread(target=self._hilo, args=(cfg, sistema, mensajes), daemon=True).start()

    def _hilo(self, cfg, sistema, mensajes):
        anthropic = cfg["proveedor"].startswith("Anthropic")
        try:
            if anthropic:
                if not cfg["clave"]:
                    raise RuntimeError("Falta la clave de API de Anthropic (Ajustes → Asistente IA).")
                url = "https://api.anthropic.com/v1/messages"
                cab = {"x-api-key": cfg["clave"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
                cuerpo = {"model": cfg["modelo"], "max_tokens": 2048, "system": sistema, "messages": mensajes,
                          "stream": True}
            else:
                url = cfg["url"].rstrip("/") + "/chat/completions"
                cab = {"content-type": "application/json"}
                if cfg["clave"]:
                    cab["authorization"] = "Bearer " + cfg["clave"]
                cuerpo = {"model": cfg["modelo"], "stream": True,
                          "messages": [{"role": "system", "content": sistema}] + mensajes}
            req = urllib.request.Request(url, json.dumps(cuerpo).encode("utf-8"), cab, method="POST")
            with urllib.request.urlopen(req, timeout=90) as r:
                for linea in r:
                    if self._parar:
                        break
                    linea = linea.decode("utf-8", "ignore").strip()
                    if not linea.startswith("data:"):
                        continue
                    datos = linea[5:].strip()
                    if datos == "[DONE]":
                        break
                    try:
                        j = json.loads(datos)
                    except ValueError:
                        continue
                    if anthropic:
                        if j.get("type") == "error":
                            raise RuntimeError(j.get("error", {}).get("message", "error"))
                        texto = j.get("delta", {}).get("text", "") if j.get("type") == "content_block_delta" else ""
                    else:
                        texto = ((j.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                    if texto:
                        self.trozo.emit(texto)
            self.fin.emit()
        except urllib.error.HTTPError as e:
            cuerpo = e.read().decode("utf-8", "ignore")
            try:
                j = json.loads(cuerpo)
                mensaje = (j.get("error") or {}).get("message") or cuerpo
            except ValueError:
                mensaje = cuerpo[:300]
            self.error.emit(f"Error {e.code}: {mensaje}")
        except urllib.error.URLError as e:
            self.error.emit(f"No se pudo conectar ({e.reason}). ¿Está bien la dirección del proveedor?")
        except Exception as e:
            self.error.emit(str(e))


def markdown_a_html(md):
    doc = QTextDocument()
    doc.setMarkdown(md)
    h = doc.toHtml()
    m = re.search(r"<body[^>]*>(.*)</body>", h, re.S)
    return m.group(1) if m else html.escape(md)


class VistaIA(QWebEngineView):
    """La web de la IA. Usa el perfil de Aurora: la sesión que inicies se queda guardada."""

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self.setPage(QWebEnginePage(ventana.perfil, self))

    def createWindow(self, tipo):  # ventanas de inicio de sesión (Google, Microsoft…) como pestaña
        return self.v.nueva_pestana(None)


class PanelAsistente(QWidget):
    """Panel lateral: la web de tu IA con tu cuenta, o el chat por clave de API / Ollama (avanzado)."""
    SELECTOR, WEB, API = range(3)

    def __init__(self, ventana):
        super().__init__(objectName="panel")
        self.v, self.abierto = ventana, False
        self.mensajes, self.generando = [], False
        self.ancho = 440
        self.web, self.ia_cargada, self._pendiente = None, None, None
        self.setFixedWidth(0)
        self.hide()
        self.anim = animacion(self, lambda w: self.setFixedWidth(int(w)), 300, QEasingCurve.Type.OutQuart)
        self.anim.finished.connect(lambda: None if self.abierto else self.hide())
        self.cliente = ClienteIA()
        self.cliente.trozo.connect(self._trozo)
        self.cliente.fin.connect(self._terminado)
        self.cliente.error.connect(self._error)
        self.reloj = QTimer(self, singleShot=True, interval=60)
        self.reloj.timeout.connect(self.pintar)

        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(Asa(self))
        cuerpo = QWidget()
        h.addWidget(cuerpo, 1)
        l = QVBoxLayout(cuerpo)
        l.setContentsMargins(12, 4, 10, 10)
        l.setSpacing(8)
        cab = QHBoxLayout()
        cab.addWidget(QLabel("✦  Asistente", objectName="tituloPanel"))
        self.b_ia = QPushButton(objectName="chipIA")
        self.b_ia.setToolTip("Cambiar de IA")
        self.b_ia.clicked.connect(self._menu_ia)
        cab.addWidget(self.b_ia)
        cab.addStretch()
        self.b_nueva = BotonIcono("mas", "Nueva conversación", tam=28)
        self.b_nueva.clicked.connect(self.nueva)
        self.b_pestana = BotonIcono("abrir", "Abrir en una pestaña", tam=28)
        self.b_pestana.clicked.connect(lambda: self.web and self.v.nueva_pestana(self.web.url().toString()))
        config = BotonIcono("ajustes", "Configurar el asistente", tam=28)
        config.clicked.connect(lambda: self.v.abrir_ajustes(Ajustes_SECCION_IA()))
        cerrar = BotonIcono("cerrar", "Cerrar", tam=28)
        cerrar.clicked.connect(self.alternar)
        for b in (self.b_nueva, self.b_pestana, config, cerrar):
            cab.addWidget(b)
        l.addLayout(cab)
        self.rejilla = QWidget()
        g = QGridLayout(self.rejilla)
        g.setContentsMargins(0, 0, 0, 0)
        g.setSpacing(6)
        for i, (texto, peticion) in enumerate(ACCIONES):
            b = QPushButton(texto, objectName="chipIA")
            b.clicked.connect(lambda _, p=peticion, t=texto: self.preguntar(p, etiqueta=t))
            g.addWidget(b, i // 2, i % 2)
        l.addWidget(self.rejilla)
        self.pila = QStackedWidget()
        l.addWidget(self.pila, 1)
        self.pila.addWidget(self._crear_selector())
        self.contenedor_web = QWidget()
        QVBoxLayout(self.contenedor_web).setContentsMargins(0, 0, 0, 0)
        self.pila.addWidget(self.contenedor_web)
        self.pila.addWidget(self._crear_chat_api())
        self.pintar()

    # ─────────────────────────────── páginas del panel
    def _crear_selector(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(4, 18, 4, 4)
        l.setSpacing(10)
        titulo = QLabel("Elige tu IA", objectName="tituloPregunta")
        texto = QLabel("Inicia sesión con tu cuenta, como en su web: tus conversaciones se quedan guardadas en ella "
                       "y las verás también en el móvil. No hace falta ninguna clave.", objectName="tenue")
        texto.setWordWrap(True)
        l.addWidget(titulo)
        l.addWidget(texto)
        g = QGridLayout()
        g.setSpacing(8)
        for i, (nombre, (_, empresa)) in enumerate(IAS_WEB.items()):
            b = QPushButton(f"{nombre}\n{empresa}", objectName="tarjetaIA")
            b.setMinimumHeight(58)
            b.clicked.connect(lambda _, n=nombre: self.elegir(n))
            g.addWidget(b, i // 2, i % 2)
        l.addLayout(g)
        avanzado = QPushButton("Avanzado: clave de API u Ollama (modelo en tu PC)…")
        avanzado.clicked.connect(lambda: self.elegir(MODO_API))
        l.addSpacing(6)
        l.addWidget(avanzado)
        l.addStretch()
        return w

    def _crear_chat_api(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)
        self.chat = QTextBrowser(objectName="chatIA")
        self.chat.setOpenLinks(False)
        self.chat.anchorClicked.connect(self._enlace)
        l.addWidget(self.chat, 1)
        fila = QHBoxLayout()
        self.entrada = QPlainTextEdit(placeholderText="Pregunta lo que quieras sobre esta página…  (Enter envía)")
        self.entrada.setFixedHeight(74)
        self.entrada.installEventFilter(self)
        self.b_enviar = BotonIcono("enviar", "Enviar (Enter)", tam=40)
        self.b_enviar.clicked.connect(self._enviar_o_parar)
        fila.addWidget(self.entrada, 1)
        fila.addWidget(self.b_enviar, 0, Qt.AlignmentFlag.AlignBottom)
        l.addLayout(fila)
        return w

    @property
    def modo(self):
        a = self.v.ajustes.datos  # quien ya tenía una clave de API sigue en ese modo
        return a.get("ia_modo") or (MODO_API if a.get("ia_clave") else "")

    def actualizar(self):
        """Muestra la página que toca según los ajustes (también si se cambian desde Ajustes)."""
        a = self.v.ajustes.datos
        if self.modo == "web" and a.get("ia_web") in IAS_WEB:
            self._cargar_web(a["ia_web"])
            self.pila.setCurrentIndex(self.WEB)
            self.b_ia.setText(f"{a['ia_web']}  ▾")
        elif self.modo == MODO_API:
            self.pila.setCurrentIndex(self.API)
            self.b_ia.setText(f"{a['ia_modelo']}  ▾")
        else:
            self.pila.setCurrentIndex(self.SELECTOR)
        elegido = self.pila.currentIndex() != self.SELECTOR
        self.b_ia.setVisible(elegido)
        self.rejilla.setVisible(elegido)
        self.b_nueva.setVisible(elegido)
        self.b_pestana.setVisible(self.pila.currentIndex() == self.WEB)

    def _cargar_web(self, nombre):
        if self.web is None:
            self.web = VistaIA(self.v)
            self.contenedor_web.layout().addWidget(self.web)
        if self.ia_cargada != nombre:
            self.ia_cargada = nombre
            self.web.setUrl(QUrl(IAS_WEB[nombre][0]))

    def elegir(self, nombre):
        if nombre == MODO_API:
            self.v.set_ajuste("ia_modo", MODO_API)
        else:
            self.v.set_ajuste("ia_modo", "web")
            self.v.set_ajuste("ia_web", nombre)
        self.actualizar()
        if self._pendiente:
            texto, etiqueta = self._pendiente
            self._pendiente = None
            QTimer.singleShot(300, lambda: self.preguntar(texto, etiqueta))

    def _menu_ia(self):
        m = menu_bonito(QMenu(self))
        for nombre in IAS_WEB:
            a = m.addAction(nombre, lambda n=nombre: self.elegir(n))
            a.setCheckable(True)
            a.setChecked(self.modo == "web" and self.v.ajustes.datos.get("ia_web") == nombre)
        m.addSeparator()
        a = m.addAction("Clave de API u Ollama (avanzado)", lambda: self.elegir(MODO_API))
        a.setCheckable(True)
        a.setChecked(self.modo == MODO_API)
        m.exec(self.b_ia.mapToGlobal(QPoint(0, self.b_ia.height() + 4)))

    # ─────────────────────────────── abrir/cerrar
    def alternar(self):
        self.abierto = not self.abierto
        if self.abierto:
            self.show()
            self.actualizar()
            animar(self.anim, self.width(), self.ancho)
            (self.web if self.pila.currentIndex() == self.WEB else self.entrada).setFocus()
        else:
            animar(self.anim, self.width(), 0)
            self.v.enfocar_pagina()
        self.v.b_ia.setChecked(self.abierto)

    def eventFilter(self, obj, e):
        if obj is self.entrada and e.type() == QEvent.Type.KeyPress and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._enviar_o_parar()
                return True
        return False

    def _enlace(self, u):
        if u.scheme() == "aurora":
            self.v.abrir_ajustes(Ajustes_SECCION_IA())
        elif u.scheme() in ("http", "https"):  # nada de file:, javascript:… que venga en una respuesta
            self.v.nueva_pestana(u.toString())

    def nueva(self):
        if self.pila.currentIndex() == self.WEB:
            self.web.setUrl(QUrl(IAS_WEB[self.ia_cargada][0]))
            return
        if self.generando:
            self.cliente.parar()
        self.mensajes = []
        self.generando = False
        self.pintar()

    # ─────────────────────────────── preguntas
    def config(self):
        a = self.v.ajustes.datos
        try:
            clave = descifrar(a["ia_clave"]) if a.get("ia_clave") else ""
        except Exception:
            clave = ""
        return {"proveedor": a["ia_proveedor"], "modelo": a["ia_modelo"], "url": a["ia_url"], "clave": clave}

    def _enviar_o_parar(self):
        if self.generando:
            self.cliente.parar()
            self._terminado()
            return
        texto = self.entrada.toPlainText().strip()
        if texto:
            self.entrada.clear()
            self.preguntar(texto)

    def preguntar(self, texto, etiqueta=None):
        if self.generando:
            return
        if not self.abierto:
            self.alternar()
        if self.modo not in ("web", MODO_API):
            self._pendiente = (texto, etiqueta)  # se hace al elegir IA
            return
        pagina = self.v.vista().page()
        seleccion = pagina.selectedText()
        url, titulo = self.v.vista().url().toString(), self.v.vista().title()
        incluir = self.v.ajustes.datos.get("ia_contexto", True) and not self.v.es_nueva(self.v.vista().url())

        def con_texto(contenido):
            contexto = ""
            if incluir:
                contexto = f"Página actual: «{titulo}» ({url})."
                if seleccion:
                    contexto += f"\n\nTexto seleccionado por el usuario:\n\"\"\"\n{seleccion[:6000]}\n\"\"\""
                if contenido:
                    contexto += f"\n\nContenido de la página (puede estar recortado):\n\"\"\"\n{contenido[:14000]}\n\"\"\""
            if self.modo == "web":
                self._escribir_en_web(texto + ("\n\n" + contexto if contexto else ""), etiqueta)
                return
            sistema = ("Eres el asistente integrado en Aurora, un navegador web. Responde siempre en español, "
                       "de forma clara y concisa, usando Markdown (listas, negritas, bloques de código) cuando ayude.")
            if contexto:
                sistema += "\n\n" + contexto
            self.mensajes.append({"role": "user", "content": texto, "etiqueta": etiqueta})
            self.mensajes.append({"role": "assistant", "content": ""})
            self.generando = True
            self.b_enviar.set_icono("parar")
            self.pintar()
            historial = [{"role": m["role"], "content": m["content"]} for m in self.mensajes[:-1]]
            self.cliente.enviar(self.config(), sistema, historial)

        if incluir and (etiqueta or self.modo == MODO_API):
            pagina.toPlainText(con_texto)
        else:
            con_texto("")

    def _escribir_en_web(self, texto, etiqueta, intento=0):
        """Escribe la petición en la caja de chat de la IA (no la envía: la revisas y pulsas Enter)."""
        ia = self.ia_cargada

        def hecho(r):
            if r == 1:
                self.web.setFocus()
                self.v.aviso.mostrar(f"✦  {etiqueta or 'Pregunta'} escrita en {ia}: pulsa Enter para enviarla")
            elif intento < 8:  # la web aún está cargando
                QTimer.singleShot(700, lambda: self._escribir_en_web(texto, etiqueta, intento + 1))
            else:
                QApplication.clipboard().setText(texto)
                self.v.aviso.mostrar(f"📋  Copiado: pégalo en {ia} con Ctrl+V")

        self.web.page().runJavaScript(JS_ESCRIBIR % json.dumps(texto), MUNDO_AURORA, hecho)

    # ─────────────────────────────── chat por API
    def _trozo(self, t):
        if self.mensajes and self.generando:
            self.mensajes[-1]["content"] += t
            if not self.reloj.isActive():
                self.reloj.start()

    def _terminado(self):
        self.generando = False
        self.b_enviar.set_icono("enviar")
        if self.mensajes and not self.mensajes[-1]["content"]:
            self.mensajes[-1]["content"] = "_(sin respuesta)_"
        self.pintar()

    def _error(self, mensaje):
        if self.mensajes and self.mensajes[-1]["role"] == "assistant":
            self.mensajes.pop()
        self.mensajes.append({"role": "error", "content": mensaje})
        self.generando = False
        self.b_enviar.set_icono("enviar")
        self.pintar()

    def pintar(self):
        c = C
        if not self.mensajes:
            cfg = self.v.ajustes.datos
            falta = cfg["ia_proveedor"].startswith("Anthropic") and not cfg.get("ia_clave")
            aviso = ("<p style='color:#ffc857'>Para empezar, añade tu clave de API en "
                     "<a href='aurora:ajustes-ia' style='color:%s'>Ajustes → Asistente IA</a>, o elige Ollama "
                     "para usar un modelo gratis en tu PC.</p>" % T.a2) if falta else ""
            self.chat.setHtml(f"""<div style='color:{c["tenue"]};text-align:center;margin-top:40px'>
                <p style='font-size:28pt;color:{T.a1}'>✦</p>
                <p style='font-size:12pt;color:{c["texto"]}'><b>¿En qué te ayudo?</b></p>
                <p>Puedo resumir esta página, traducirla, explicarte un texto que selecciones o responder
                cualquier pregunta sobre lo que estás viendo.</p>{aviso}</div>""")
            return
        partes = []
        for m in self.mensajes:
            if m["role"] == "user":
                texto = m.get("etiqueta") or m["content"]
                partes.append(f"""<table width='100%' cellspacing='0' cellpadding='0' style='margin:8px 0'><tr>
                    <td width='15%'></td><td bgcolor='{mezcla(c["chip"], T.a1, 0.35).name()}' style='padding:9px 12px;
                    border-radius:12px;color:#fff'>{html.escape(texto).replace(chr(10), '<br>')}</td></tr></table>""")
            elif m["role"] == "assistant":
                cuerpo = markdown_a_html(m["content"]) if m["content"] else f"<span style='color:{c['tenue']}'>Pensando…</span>"
                if self.generando and m is self.mensajes[-1] and m["content"]:
                    cuerpo += f"<span style='color:{T.a2}'> ▍</span>"
                partes.append(f"<div style='margin:6px 2px 14px 2px;color:{c['texto']}'>{cuerpo}</div>")
            else:
                partes.append(f"<p style='color:#ff8b9c;margin:8px 2px'>⚠ {html.escape(m['content'])}</p>")
        barra = self.chat.verticalScrollBar()
        abajo = barra.value() >= barra.maximum() - 30
        self.chat.setHtml(f"<div style='font-size:10pt'>{''.join(partes)}</div>")
        if abajo or self.generando:
            barra.setValue(barra.maximum())


def Ajustes_SECCION_IA():
    from .ajustes import Ajustes
    return [n for n, _ in Ajustes.SECCIONES].index("Asistente IA")
