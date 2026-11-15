"""Herramientas extra para desarrolladores: cliente de API, auditoría, cuentagotas/medidor y captura completa."""
import ssl
import threading
import time
import urllib.error
import urllib.request

from .widgets import *  # noqa: F401,F403

# ═════════════════════════════ resaltado de JSON
class ResaltadoJSON(QSyntaxHighlighter):
    REGLAS = [(r'"(\\.|[^"\\])*"(?=\s*:)', "#7cc4ff"), (r':\s*"(\\.|[^"\\])*"', "#a5e88a"),
              (r"\b-?\d+(\.\d+)?([eE][+-]?\d+)?\b", "#ffb86b"), (r"\b(true|false)\b", "#c792ea"),
              (r"\bnull\b", "#7a8094")]

    def __init__(self, documento):
        super().__init__(documento)
        self.reglas = []
        for patron, color in self.REGLAS:
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            self.reglas.append((re.compile(patron), f))

    def highlightBlock(self, texto):
        for patron, formato in self.reglas:
            for m in patron.finditer(texto):
                inicio = m.start() + (m.group(0).index('"') if m.group(0).startswith(":") else 0)
                self.setFormat(inicio, m.end() - inicio, formato)


# ═════════════════════════════ cliente de API
class _Peticion(QObject):
    hecho = pyqtSignal(dict)

    def lanzar(self, metodo, url, cabeceras, cuerpo):
        threading.Thread(target=self._hilo, args=(metodo, url, cabeceras, cuerpo), daemon=True).start()

    def _hilo(self, metodo, url, cabeceras, cuerpo):
        inicio = time.perf_counter()
        res = {"metodo": metodo, "url": url}
        try:
            req = urllib.request.Request(url, data=cuerpo.encode("utf-8") if cuerpo else None,
                                         headers=cabeceras, method=metodo)
            with urllib.request.urlopen(req, timeout=30, context=ssl.create_default_context()) as r:
                datos = r.read()
                res.update(estado=r.status, razon=r.reason, cabeceras=dict(r.headers.items()), datos=datos)
        except urllib.error.HTTPError as e:
            res.update(estado=e.code, razon=e.reason, cabeceras=dict(e.headers.items()), datos=e.read())
        except Exception as e:
            res.update(estado=0, razon=str(e), cabeceras={}, datos=b"")
        res["ms"] = round((time.perf_counter() - inicio) * 1000)
        self.hecho.emit(res)


class ClienteAPI(QWidget):
    METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self.peticion = _Peticion()
        self.peticion.hecho.connect(self.respuesta)
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(8)
        fila = QHBoxLayout()
        self.metodo = QComboBox()
        self.metodo.addItems(self.METODOS)
        self.metodo.setFixedWidth(100)
        self.url = QLineEdit(placeholderText="https://api.ejemplo.com/v1/recurso")
        self.url.setFont(fuente_mono())
        self.url.returnPressed.connect(self.enviar)
        self.b_enviar = QPushButton("Enviar", objectName="primario")
        self.b_enviar.clicked.connect(self.enviar)
        actual = QPushButton("Página actual")
        actual.setToolTip("Usar la URL de la pestaña")
        actual.clicked.connect(lambda: self.url.setText(self.v.vista().url().toString()))
        fila.addWidget(self.metodo)
        fila.addWidget(self.url, 1)
        fila.addWidget(self.b_enviar)
        l.addLayout(fila)
        fila2 = QHBoxLayout()
        self.historial = QComboBox()
        self.historial.setPlaceholderText("Historial de peticiones")
        self.historial.activated.connect(self._desde_historial)
        curl = QPushButton("Copiar como cURL")
        curl.clicked.connect(self.copiar_curl)
        fila2.addWidget(self.historial, 1)
        fila2.addWidget(actual)
        fila2.addWidget(curl)
        l.addLayout(fila2)

        self.pet_tabs = QTabWidget(objectName="tabsPanel")
        self.pet_tabs.setDocumentMode(True)
        self.cabeceras = QPlainTextEdit(placeholderText="Content-Type: application/json\nAuthorization: Bearer …")
        self.cuerpo = QPlainTextEdit(placeholderText='{\n  "nombre": "Aurora"\n}')
        for w in (self.cabeceras, self.cuerpo):
            w.setFont(fuente_mono())
        ResaltadoJSON(self.cuerpo.document())
        self.pet_tabs.addTab(self.cuerpo, "Cuerpo")
        self.pet_tabs.addTab(self.cabeceras, "Cabeceras")
        self.pet_tabs.setMaximumHeight(170)
        l.addWidget(self.pet_tabs)

        self.estado = QLabel("Envía una petición para ver la respuesta.", objectName="tenue")
        l.addWidget(self.estado)
        self.res_tabs = QTabWidget(objectName="tabsPanel")
        self.res_tabs.setDocumentMode(True)
        self.salida = QPlainTextEdit(readOnly=True)
        self.salida_cab = QPlainTextEdit(readOnly=True)
        for w in (self.salida, self.salida_cab):
            w.setFont(fuente_mono())
        ResaltadoJSON(self.salida.document())
        self.res_tabs.addTab(self.salida, "Respuesta")
        self.res_tabs.addTab(self.salida_cab, "Cabeceras")
        l.addWidget(self.res_tabs, 1)
        self.anteriores = []

    def _cabeceras(self):
        cab = {"User-Agent": f"{NOMBRE}-API/1.0"}
        for linea in self.cabeceras.toPlainText().splitlines():
            if ":" in linea:
                k, v = linea.split(":", 1)
                cab[k.strip()] = v.strip()
        if self.cuerpo.toPlainText().strip().startswith(("{", "[")) and not any(k.lower() == "content-type" for k in cab):
            cab["Content-Type"] = "application/json"
        return cab

    def enviar(self):
        url = self.url.text().strip()
        if not url:
            return
        if "://" not in url:
            url = "https://" + url
            self.url.setText(url)
        metodo = self.metodo.currentText()
        cuerpo = self.cuerpo.toPlainText() if metodo not in ("GET", "HEAD") else ""
        self.b_enviar.setEnabled(False)
        self.estado.setText("Enviando…")
        self.peticion.lanzar(metodo, url, self._cabeceras(), cuerpo)
        clave = f"{metodo}  {url}"
        guardado = (metodo, url, self.cabeceras.toPlainText(), self.cuerpo.toPlainText())
        self.anteriores = [a for a in self.anteriores if f"{a[0]}  {a[1]}" != clave][:19]
        self.anteriores.insert(0, guardado)
        self.historial.clear()
        self.historial.addItems([f"{a[0]}  {a[1]}" for a in self.anteriores])
        self.historial.setCurrentIndex(-1)

    def _desde_historial(self, i):
        metodo, url, cab, cuerpo = self.anteriores[i]
        self.metodo.setCurrentText(metodo)
        self.url.setText(url)
        self.cabeceras.setPlainText(cab)
        self.cuerpo.setPlainText(cuerpo)

    def respuesta(self, r):
        self.b_enviar.setEnabled(True)
        estado = r["estado"]
        color = "#6ee7a8" if 200 <= estado < 300 else "#ffc857" if 300 <= estado < 400 else "#ff6b81"
        texto_estado = f"{estado} {r['razon']}" if estado else f"Error: {r['razon']}"
        self.estado.setText(f'<span style="color:{color};font-weight:600">{html.escape(texto_estado)}</span>'
                            f'  ·  {r["ms"]} ms  ·  {len(r["datos"]) / 1024:.1f} KB')
        datos = r["datos"]
        try:
            texto = datos.decode("utf-8")
        except UnicodeDecodeError:
            texto = f"[{len(datos)} bytes binarios]"
        try:
            texto = json.dumps(json.loads(texto), indent=2, ensure_ascii=False)
        except ValueError:
            pass
        self.salida.setPlainText(texto[:500_000])
        self.salida_cab.setPlainText("\n".join(f"{k}: {v}" for k, v in r["cabeceras"].items()))

    def copiar_curl(self):
        partes = [f"curl -X {self.metodo.currentText()} '{self.url.text().strip()}'"]
        for k, v in self._cabeceras().items():
            partes.append(f"-H '{k}: {v}'")
        if self.cuerpo.toPlainText().strip() and self.metodo.currentText() not in ("GET", "HEAD"):
            partes.append("--data '" + self.cuerpo.toPlainText().replace("'", "'\\''") + "'")
        QApplication.clipboard().setText(" \\\n  ".join(partes))
        self.v.aviso.mostrar("Comando cURL copiado")


# ═════════════════════════════ auditoría
JS_AUDITORIA = r"""(()=>{const R=[];let n=0;
const marcar=(el)=>{if(!el||!el.setAttribute)return -1;const i=n++;el.setAttribute('data-aurora-aud',i);return i};
const add=(nivel,cat,texto,el)=>R.push({nivel,cat,texto,i:marcar(el)});
document.querySelectorAll('[data-aurora-aud]').forEach(e=>e.removeAttribute('data-aurora-aud'));
// SEO
if(!document.title)add('error','SEO','La página no tiene <title>');else if(document.title.length>65)add('aviso','SEO','El título es largo ('+document.title.length+' caracteres, mejor < 60)');
const md=document.querySelector('meta[name=description]');if(!md||!md.content)add('aviso','SEO','Falta <meta name="description">');
if(!document.documentElement.lang)add('aviso','Accesibilidad','Falta el atributo lang en <html>');
if(!document.querySelector('meta[name=viewport]'))add('aviso','Móvil','Falta <meta name="viewport"> (se verá mal en móviles)');
const h1=document.querySelectorAll('h1');if(!h1.length)add('aviso','SEO','No hay ningún <h1>');else if(h1.length>1)add('info','SEO','Hay '+h1.length+' <h1> (normalmente uno)',h1[1]);
let ant=0;document.querySelectorAll('h1,h2,h3,h4,h5,h6').forEach(h=>{const nv=+h.tagName[1];if(ant&&nv>ant+1)add('info','Accesibilidad','Salto de encabezado: '+h.tagName+' después de H'+ant,h);ant=nv});
// imágenes
let sinAlt=0,grandes=0;document.querySelectorAll('img').forEach(im=>{if(!im.hasAttribute('alt')){sinAlt++;if(sinAlt<=15)add('error','Accesibilidad','Imagen sin texto alternativo (alt): '+(im.currentSrc||im.src).split('/').pop().slice(0,60),im)}
 if(im.naturalWidth>0&&im.clientWidth>0&&im.naturalWidth>im.clientWidth*2.5&&im.naturalWidth>800){grandes++;if(grandes<=8)add('aviso','Rendimiento','Imagen sobredimensionada ('+im.naturalWidth+'px para '+im.clientWidth+'px)',im)}});
if(sinAlt>15)add('error','Accesibilidad','…y '+(sinAlt-15)+' imágenes más sin alt');
// enlaces y botones
document.querySelectorAll('a').forEach(a=>{const t=(a.innerText||a.getAttribute('aria-label')||a.title||(a.querySelector('img[alt]')||{}).alt||'').trim();
 if(!t&&a.offsetParent!==null)add('aviso','Accesibilidad','Enlace sin texto: '+(a.getAttribute('href')||'').slice(0,60),a);
 if(a.target==='_blank'&&!/noopener|noreferrer/.test(a.rel||''))add('info','Seguridad','target="_blank" sin rel="noopener"',a);
 if(/^javascript:/i.test(a.getAttribute('href')||''))add('info','Buenas prácticas','Enlace con href="javascript:…"',a)});
document.querySelectorAll('button,[role=button]').forEach(b=>{if(!(b.innerText||b.getAttribute('aria-label')||b.title||'').trim()&&b.offsetParent!==null)add('aviso','Accesibilidad','Botón sin nombre accesible',b)});
document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea').forEach(i=>{
 const tiene=(i.id&&document.querySelector('label[for="'+CSS.escape(i.id)+'"]'))||i.closest('label')||i.getAttribute('aria-label')||i.getAttribute('aria-labelledby')||i.title;
 if(!tiene&&i.offsetParent!==null)add('aviso','Accesibilidad','Campo de formulario sin etiqueta'+(i.placeholder?' («'+i.placeholder.slice(0,30)+'»)':''),i)});
// contraste
const lum=c=>{const m=c.match(/[\d.]+/g);if(!m)return null;const [r,g,b]=m.slice(0,3).map(x=>{x/=255;return x<=.03928?x/12.92:Math.pow((x+.055)/1.055,2.4)});return .2126*r+.7152*g+.0722*b};
const fondo=el=>{while(el){const c=getComputedStyle(el).backgroundColor;const m=c.match(/[\d.]+/g);if(m&&(m.length<4||+m[3]>.5))return c;el=el.parentElement}return 'rgb(255,255,255)'};
let bajos=0;const vistos=new Set();
[...document.querySelectorAll('p,span,a,li,td,th,label,button,h1,h2,h3,h4,small')].slice(0,700).forEach(el=>{
 if(!el.offsetParent||!el.childNodes.length||![...el.childNodes].some(x=>x.nodeType===3&&x.textContent.trim()))return;
 const s=getComputedStyle(el);const l1=lum(s.color),l2=lum(fondo(el));if(l1==null||l2==null)return;
 const ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);const grande=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.6&&+s.fontWeight>=700);
 if(ratio<(grande?3:4.5)){const k=s.color+fondo(el);if(vistos.has(k))return;vistos.add(k);bajos++;
  if(bajos<=10)add('aviso','Accesibilidad','Contraste bajo ('+ratio.toFixed(2)+':1): «'+el.innerText.trim().slice(0,40)+'»',el)}});
// seguridad y contenido mixto
if(location.protocol==='https:'){[...document.querySelectorAll('img[src^="http:"],script[src^="http:"],link[href^="http:"],iframe[src^="http:"]')].slice(0,5).forEach(e=>add('error','Seguridad','Contenido mixto (HTTP en página HTTPS)',e))}
else if(location.protocol==='http:'&&!/^(localhost|127\.)/.test(location.hostname))add('aviso','Seguridad','La página no usa HTTPS');
// rendimiento
const nav=performance.getEntriesByType('navigation')[0];if(nav&&nav.loadEventEnd>4000)add('aviso','Rendimiento','Carga lenta: '+Math.round(nav.loadEventEnd)+' ms');
const nodos=document.getElementsByTagName('*').length;if(nodos>3000)add('info','Rendimiento','DOM muy grande ('+nodos+' nodos)');
// enlaces rotos (asíncrono, mismo dominio)
window.__aurora_rotos={hecho:false,lista:[]};
const internos=[...new Set([...document.querySelectorAll('a[href]')].map(a=>a.href).filter(h=>h.startsWith(location.origin)&&!h.includes('#')))].slice(0,40);
Promise.all(internos.map(u=>fetch(u,{method:'HEAD'}).then(r=>{if(r.status>=400)window.__aurora_rotos.lista.push([u,r.status])}).catch(()=>{})))
 .then(()=>{window.__aurora_rotos.hecho=true;window.__aurora_rotos.n=internos.length});
return JSON.stringify(R)})()"""

JS_ROTOS = "JSON.stringify(window.__aurora_rotos||{hecho:true,lista:[]})"
JS_SENALAR = r"""((i)=>{const e=document.querySelector('[data-aurora-aud="'+i+'"]');if(!e)return;
e.scrollIntoView({behavior:'smooth',block:'center'});const o=e.style.outline,s=e.style.boxShadow;
e.style.outline='3px solid %%A%%';e.style.boxShadow='0 0 0 8px rgba(%%A_RGB%%,.25)';e.style.transition='outline .3s';
setTimeout(()=>{e.style.outline=o;e.style.boxShadow=s},2200)})(%s)"""


class Puntuacion(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(76, 76)
        self.valor, self._v = None, 0.0
        self.anim = animacion(self, self._set, 900, QEasingCurve.Type.OutCubic)

    def _set(self, v):
        self._v = v
        self.update()

    def fijar(self, valor):
        self.valor = valor
        animar(self.anim, 0.0, float(valor))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(6, 6, 64, 64)
        p.setPen(QPen(QColor(C["borde"]), 6))
        p.drawEllipse(r)
        if self.valor is None:
            return
        color = "#6ee7a8" if self._v >= 90 else "#ffc857" if self._v >= 60 else "#ff6b81"
        pen = QPen(QColor(color), 6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(r, 90 * 16, int(-360 * 16 * self._v / 100))
        f = QFont(self.font())
        f.setPointSizeF(15)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor(C["texto"]))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, str(round(self._v)))


class Auditoria(QWidget):
    COLORES = {"error": "#ff6b81", "aviso": "#ffc857", "info": "#7cc4ff"}
    PESOS = {"error": 8, "aviso": 3, "info": 1}

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(10)
        cab = QHBoxLayout()
        self.nota = Puntuacion()
        textos = QVBoxLayout()
        self.titulo = QLabel("Auditoría de la página", objectName="tituloPregunta")
        self.resumen = QLabel("Revisa accesibilidad, SEO, rendimiento, seguridad y enlaces rotos.", objectName="tenue")
        self.resumen.setWordWrap(True)
        textos.addWidget(self.titulo)
        textos.addWidget(self.resumen)
        boton = QPushButton("Auditar", objectName="primario")
        boton.clicked.connect(self.auditar)
        cab.addWidget(self.nota)
        cab.addLayout(textos, 1)
        cab.addWidget(boton)
        l.addLayout(cab)
        self.lista = QListWidget(objectName="listaAuditoria")
        self.lista.setWordWrap(True)
        self.lista.itemDoubleClicked.connect(self.senalar)
        self.lista.setToolTip("Doble clic para ver el elemento en la página")
        l.addWidget(self.lista, 1)
        self.resultados = []

    def auditar(self):
        self.lista.clear()
        self.resumen.setText("Analizando…")
        self.v.vista().page().runJavaScript(JS_AUDITORIA, self._mostrar)

    def _mostrar(self, r):
        try:
            self.resultados = json.loads(r or "[]")
        except ValueError:
            self.resultados = []
        self._pintar()
        self._intentos = 0
        QTimer.singleShot(1500, self._rotos)

    def _rotos(self):
        def leer(r):
            try:
                d = json.loads(r or "{}")
            except ValueError:
                return
            if not d.get("hecho") and self._intentos < 8:
                self._intentos += 1
                QTimer.singleShot(1000, self._rotos)
                return
            for url, estado in d.get("lista", []):
                self.resultados.append({"nivel": "error", "cat": "Enlaces", "texto": f"Enlace roto ({estado}): {url}", "i": -1})
            self._pintar(d.get("n"))
        self.v.vista().page().runJavaScript(JS_ROTOS, leer)

    def _pintar(self, comprobados=None):
        self.lista.clear()
        orden = {"error": 0, "aviso": 1, "info": 2}
        for r in sorted(self.resultados, key=lambda x: (orden[x["nivel"]], x["cat"])):
            item = QListWidgetItem(f"●  {r['cat']} · {r['texto']}")
            item.setForeground(QColor(self.COLORES[r["nivel"]]))
            item.setData(Qt.ItemDataRole.UserRole, r["i"])
            self.lista.addItem(item)
        puntos = max(0, 100 - sum(self.PESOS[r["nivel"]] for r in self.resultados))
        self.nota.fijar(puntos)
        n = {k: sum(1 for r in self.resultados if r["nivel"] == k) for k in self.PESOS}
        extra = f" · {comprobados} enlaces internos comprobados" if comprobados is not None else ""
        self.resumen.setText(f"{n['error']} errores · {n['aviso']} avisos · {n['info']} sugerencias{extra}"
                             if self.resultados else f"¡Todo bien! No hay problemas que señalar{extra}.")

    def senalar(self, item):
        i = item.data(Qt.ItemDataRole.UserRole)
        if i is not None and i >= 0:
            js = JS_SENALAR.replace("%%A_RGB%%", rgb(T.a1)).replace("%%A%%", T.a1) % i
            self.v.vista().page().runJavaScript(js)


# ═════════════════════════════ cuentagotas y medidor
class Cuentagotas(QWidget):
    """Capa sobre la página: lupa con el color bajo el ratón (clic = copiar) y regla al arrastrar."""

    def __init__(self, ventana, pagina):
        super().__init__(pagina)
        self.v, self.pagina = ventana, pagina
        vista = pagina.vista
        self.setGeometry(vista.geometry())
        self.imagen = vista.grab().toImage()
        self.dpr = self.imagen.devicePixelRatio() or 1.0
        self.zoom = vista.zoomFactor() or 1.0
        self.raton = None
        self.inicio = self.fin = None
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.show()
        self.raise_()
        self.setFocus()

    def color(self, pos):
        x, y = int(pos.x() * self.dpr), int(pos.y() * self.dpr)
        if 0 <= x < self.imagen.width() and 0 <= y < self.imagen.height():
            return self.imagen.pixelColor(x, y)
        return QColor(0, 0, 0)

    def mouseMoveEvent(self, e):
        self.raton = e.position()
        if self.inicio is not None:
            self.fin = e.position()
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.salir()
            return
        self.inicio, self.fin = e.position(), None

    def mouseReleaseEvent(self, e):
        if self.inicio is not None and (self.fin is None or (self.fin - self.inicio).manhattanLength() < 4):
            c = self.color(e.position())
            QApplication.clipboard().setText(c.name())
            self.v.aviso.mostrar(f"🎯  Color {c.name()}  ·  rgb({c.red()}, {c.green()}, {c.blue()}) copiado")
            self.inicio = self.fin = None
        elif self.inicio is not None and self.fin is not None:
            w, h = self._medida()
            QApplication.clipboard().setText(f"{w} × {h}")
            self.v.aviso.mostrar(f"📏  {w} × {h} px copiado")
        self.update()

    def _medida(self):
        r = QRectF(self.inicio, self.fin).normalized()
        return round(r.width() / self.zoom), round(r.height() / self.zoom)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.salir()

    def salir(self):
        self.v.cuentagotas_activo = None
        self.deleteLater()
        self.v.enfocar_pagina()

    def paintEvent(self, e):
        p = QPainter(self)
        p.drawImage(QRectF(self.rect()), self.imagen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # instrucciones
        aviso = "Cuentagotas y medidor · clic: copiar color · arrastrar: medir · Esc: salir"
        fm = QFontMetrics(self.font())
        ra = QRectF((self.width() - fm.horizontalAdvance(aviso) - 30) / 2, 14, fm.horizontalAdvance(aviso) + 30, 30)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 23, 31, 230))
        p.drawRoundedRect(ra, 15, 15)
        p.setPen(QColor(C["texto"]))
        p.drawText(ra, Qt.AlignmentFlag.AlignCenter, aviso)
        if self.inicio is not None and self.fin is not None:
            r = QRectF(self.inicio, self.fin).normalized()
            p.setPen(QPen(QColor(T.a2), 1.5, Qt.PenStyle.DashLine))
            p.setBrush(con_alfa(T.a2, 0.12))
            p.drawRect(r)
            w, h = self._medida()
            etiqueta = f"{w} × {h} px"
            caja = QRectF(r.center().x() - 50, r.bottom() + 8, 100, 26)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(T.a1))
            p.drawRoundedRect(caja, 8, 8)
            p.setPen(QColor("white"))
            p.drawText(caja, Qt.AlignmentFlag.AlignCenter, etiqueta)
        if self.raton is None:
            return
        m = self.raton
        p.setPen(QPen(QColor(255, 255, 255, 160), 1))
        p.drawLine(QPointF(m.x(), 0), QPointF(m.x(), self.height()))
        p.drawLine(QPointF(0, m.y()), QPointF(self.width(), m.y()))
        # lupa
        tam, celdas = 130, 13
        lx = m.x() + 24 if m.x() + 24 + tam < self.width() else m.x() - 24 - tam
        ly = m.y() + 24 if m.y() + 24 + tam + 34 < self.height() else m.y() - 24 - tam - 34
        lupa = QRectF(lx, ly, tam, tam)
        origen = QRect(int(m.x() * self.dpr) - celdas // 2, int(m.y() * self.dpr) - celdas // 2, celdas, celdas)
        camino = QPainterPath()
        camino.addEllipse(lupa)
        p.save()
        p.setClipPath(camino)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawImage(lupa, self.imagen, QRectF(origen))
        celda = tam / celdas
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        for i in range(celdas + 1):
            p.drawLine(QPointF(lx + i * celda, ly), QPointF(lx + i * celda, ly + tam))
            p.drawLine(QPointF(lx, ly + i * celda), QPointF(lx + tam, ly + i * celda))
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(lx + celdas // 2 * celda, ly + celdas // 2 * celda, celda, celda))
        p.restore()
        p.setPen(QPen(QColor(255, 255, 255, 220), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(lupa)
        c = self.color(m)
        caja = QRectF(lx + tam / 2 - 58, ly + tam + 6, 116, 26)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 23, 31, 235))
        p.drawRoundedRect(caja, 8, 8)
        p.setBrush(c)
        p.drawRoundedRect(QRectF(caja.left() + 6, caja.top() + 6, 14, 14), 4, 4)
        p.setPen(QColor(C["texto"]))
        p.setFont(fuente_mono(9))
        p.drawText(caja.adjusted(24, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, c.name().upper())


class MixinDev:
    def iniciar_dev(self):
        self.cuentagotas_activo = None

    def cuentagotas(self):
        if self.cuentagotas_activo:
            self.cuentagotas_activo.salir()
            return
        self.cuentagotas_activo = Cuentagotas(self, self.pagina())

    def captura_completa(self):
        """Agranda la vista a la altura de toda la página, la fotografía y la deja como estaba."""
        pagina, vista = self.pagina(), self.vista()

        def medir(r):
            try:
                alto_css, scroll = json.loads(r)
            except (TypeError, ValueError):
                return
            alto = int(min(alto_css * vista.zoomFactor(), 16000))
            self.aviso.mostrar("🧾  Haciendo la captura completa…")
            vista.page().runJavaScript("window.scrollTo(0,0)")
            vista.setGeometry(vista.x(), vista.y(), vista.width(), alto)

            def foto():
                imagen = vista.grab()
                pagina.colocar()
                vista.page().runJavaScript(f"window.scrollTo(0,{scroll})")
                self._guardar_captura(imagen, "completa")
            QTimer.singleShot(900, foto)
        vista.page().runJavaScript("JSON.stringify([Math.max(document.documentElement.scrollHeight,"
                                   "document.body?document.body.scrollHeight:0), scrollY])", medir)

    def _guardar_captura(self, imagen, tipo=""):
        carpeta = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
                       or Path.home()) / NOMBRE
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"captura{'-' + tipo if tipo else ''}-{datetime.now():%Y%m%d-%H%M%S}.png"
        imagen.save(str(ruta))
        QApplication.clipboard().setPixmap(imagen)
        self.aviso.mostrar(f"📸  Captura {tipo + ' ' if tipo else ''}guardada en Imágenes/{NOMBRE} y copiada")
        return ruta
