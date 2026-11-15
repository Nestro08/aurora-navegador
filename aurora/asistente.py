"""Asistente con IA en un panel lateral: resume, traduce y explica la página o lo que selecciones.

Proveedores:
  • Anthropic (Claude): necesita una clave de API de console.anthropic.com.
  • Compatible con OpenAI: OpenAI, LM Studio, Ollama (gratis y local: http://localhost:11434/v1)…
Las respuestas llegan en streaming (se van escribiendo mientras se generan).
"""
import threading
import urllib.error
import urllib.request

from .contrasenas import *  # noqa: F401,F403
from .desarrollo import Asa

PROVEEDORES = ["Anthropic (Claude)", "Compatible con OpenAI (OpenAI, Ollama, LM Studio…)"]
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


class PanelAsistente(QWidget):
    def __init__(self, ventana):
        super().__init__(objectName="panel")
        self.v, self.abierto = ventana, False
        self.mensajes, self.generando = [], False
        self.ancho = 420
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
        titulo = QLabel("✦  Asistente", objectName="tituloPanel")
        self.modelo = QLabel(objectName="tenue")
        nueva = BotonIcono("mas", "Nueva conversación", tam=28)
        nueva.clicked.connect(self.nueva)
        config = BotonIcono("ajustes", "Configurar el asistente", tam=28)
        config.clicked.connect(lambda: self.v.abrir_ajustes(Ajustes_SECCION_IA()))
        cerrar = BotonIcono("cerrar", "Cerrar", tam=28)
        cerrar.clicked.connect(self.alternar)
        cab.addWidget(titulo)
        cab.addWidget(self.modelo, 1)
        for b in (nueva, config, cerrar):
            cab.addWidget(b)
        l.addLayout(cab)
        rejilla = QGridLayout()
        rejilla.setSpacing(6)
        for i, (texto, peticion) in enumerate(ACCIONES):
            b = QPushButton(texto, objectName="chipIA")
            b.clicked.connect(lambda _, p=peticion, t=texto: self.preguntar(p, etiqueta=t))
            rejilla.addWidget(b, i // 2, i % 2)
        l.addLayout(rejilla)
        self.chat = QTextBrowser(objectName="chatIA")
        self.chat.setOpenLinks(False)
        self.chat.anchorClicked.connect(lambda u: self.v.abrir_ajustes(Ajustes_SECCION_IA()) if u.scheme() == "aurora"
                                        else self.v.nueva_pestana(u.toString()))
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
        self.pintar()

    # ─────────────────────────────── abrir/cerrar
    def alternar(self):
        self.abierto = not self.abierto
        if self.abierto:
            self.show()
            self.actualizar_modelo()
            animar(self.anim, self.width(), self.ancho)
            self.entrada.setFocus()
        else:
            animar(self.anim, self.width(), 0)
            self.v.enfocar_pagina()
        self.v.b_ia.setChecked(self.abierto)

    def actualizar_modelo(self):
        a = self.v.ajustes.datos
        self.modelo.setText(f"  {a['ia_modelo']}")

    def eventFilter(self, obj, e):
        if obj is self.entrada and e.type() == QEvent.Type.KeyPress and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._enviar_o_parar()
                return True
        return False

    def nueva(self):
        if self.generando:
            self.cliente.parar()
        self.mensajes = []
        self.generando = False
        self.pintar()

    # ─────────────────────────────── conversación
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
        pagina = self.v.vista().page()
        seleccion = pagina.selectedText()
        url, titulo = self.v.vista().url().toString(), self.v.vista().title()
        incluir = self.v.ajustes.datos.get("ia_contexto", True) and not self.v.es_nueva(self.v.vista().url())

        def con_texto(contenido):
            sistema = ("Eres el asistente integrado en Aurora, un navegador web. Responde siempre en español, "
                       "de forma clara y concisa, usando Markdown (listas, negritas, bloques de código) cuando ayude.")
            if incluir:
                sistema += f"\n\nPágina actual: «{titulo}» ({url})."
                if seleccion:
                    sistema += f"\n\nTexto seleccionado por el usuario:\n\"\"\"\n{seleccion[:6000]}\n\"\"\""
                if contenido:
                    sistema += f"\n\nContenido de la página (puede estar recortado):\n\"\"\"\n{contenido[:14000]}\n\"\"\""
            self.mensajes.append({"role": "user", "content": texto, "etiqueta": etiqueta})
            self.mensajes.append({"role": "assistant", "content": ""})
            self.generando = True
            self.b_enviar.set_icono("parar")
            self.pintar()
            historial = [{"role": m["role"], "content": m["content"]} for m in self.mensajes[:-1]]
            self.cliente.enviar(self.config(), sistema, historial)

        if incluir:
            pagina.toPlainText(con_texto)
        else:
            con_texto("")

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
