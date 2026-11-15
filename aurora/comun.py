"""Constantes, configuración, scripts inyectados y utilidades compartidas."""
import base64
import csv
import functools
import html
import json
import os
import re
import secrets
import sys
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote_plus

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
                      "--enable-smooth-scrolling --enable-features=OverlayScrollbar")

from PyQt6.QtCore import (QEasingCurve, QEvent, QFileSystemWatcher, QObject, QPoint, QPointF,
                          QPropertyAnimation, QRect, QRectF, QSize, QSizeF, QStandardPaths,
                          QStringListModel, Qt, QTimer, QUrl, QVariantAnimation, pyqtSignal, qVersion)
from PyQt6.QtGui import (QCursor, QPainterPath, QSyntaxHighlighter, QTextCharFormat, QTextDocument,
                         QColor, QDesktopServices, QFont, QFontDatabase, QFontMetrics, QIcon,
                         QKeySequence, QLinearGradient, QPainter, QPalette, QPen, QPixmap,
                         QShortcut)
from PyQt6.QtWebEngineCore import (QWebEngineDownloadRequest, QWebEnginePage, QWebEngineProfile,
                                   QWebEngineScript, QWebEngineSettings,
                                   QWebEngineUrlRequestInterceptor)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import (QInputDialog, QSizeGrip, QSplitter, QTextBrowser,
                             QAbstractButton, QAbstractItemView, QApplication, QCheckBox, QComboBox,
                             QDialog, QMessageBox,
                             QCompleter, QFileDialog, QFrame, QGraphicsDropShadowEffect,
                             QGraphicsOpacityEffect, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                             QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMenu,
                             QPlainTextEdit, QPushButton, QScrollArea, QStackedWidget, QStyle,
                             QStyledItemDelegate, QTableWidget, QTableWidgetItem, QTabWidget,
                             QVBoxLayout, QWidget)

# ═════════════════════════════ configuración

NOMBRE = "Aurora"
DATOS = Path.home() / ".aurora"
DATOS.mkdir(exist_ok=True)
if os.name == "posix":  # historial, contraseñas y ajustes: solo los puede leer tu usuario
    os.chmod(DATOS, 0o700)
# Secreto de esta sesión para los mensajes de los scripts de Aurora (las webs no pueden falsificarlos)
TOKEN_PUENTE = secrets.token_hex(12)
NUEVA = DATOS / "nueva.html"
NUEVA_URL = QUrl.fromLocalFile(str(NUEVA)).toString()

C = {
    "fondo": "#0d0f14", "barra": "#12151c", "chip": "#1a1e27", "chip_hover": "#212633",
    "chip_activo": "#262b38", "texto": "#e6e8ee", "tenue": "#8a90a2", "borde": "#2a2f3c",
}
class Tema:
    """Colores de acento actuales (se cambian en caliente desde Ajustes)."""
    a1, a2 = "#7c5cff", "#22d3ee"


T = Tema()

BUSCADORES = {
    "DuckDuckGo": "https://duckduckgo.com/?q={}",
    "Google": "https://www.google.com/search?q={}",
    "Bing": "https://www.bing.com/search?q={}",
}
LIBRE = "Libre (sin simulación)"
DISPOSITIVOS = {
    LIBRE: None,
    "iPhone 15": (393, 852), "iPhone SE": (375, 667), "Pixel 8": (412, 915),
    "Galaxy S23": (360, 780), "iPad Air": (820, 1180), "iPad Pro 12.9": (1024, 1366),
    "Portátil 1366×768": (1366, 768), "Full HD 1920×1080": (1920, 1080),
}
UAS = {
    "Por defecto": None,
    "iPhone (Safari)": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
                       "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    "Android (Chrome)": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36",
    "Firefox (Windows)": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Googlebot": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
}
BLOQUEO_BASE = {
    "doubleclick.net", "googlesyndication.com", "googleadservices.com", "google-analytics.com",
    "adservice.google.com", "adnxs.com", "taboola.com", "outbrain.com", "criteo.com",
    "scorecardresearch.com", "facebook.net", "ads.yahoo.com", "amazon-adsystem.com", "hotjar.com",
}
ACENTOS = {
    "Aurora": ("#7c5cff", "#22d3ee"), "Océano": ("#3b82f6", "#06b6d4"), "Bosque": ("#22c55e", "#a3e635"),
    "Atardecer": ("#f97316", "#f43f5e"), "Sakura": ("#ec4899", "#a78bfa"), "Oro": ("#f59e0b", "#fde047"),
    "Menta": ("#14b8a6", "#5eead4"),
}
TAMANOS = {"Pequeño": 14, "Normal": 16, "Grande": 18, "Muy grande": 20}
ZOOMS = ["80 %", "90 %", "100 %", "110 %", "125 %", "150 %"]
AJUSTES_DEFECTO = {
    "buscador": "DuckDuckGo", "bloqueo": True, "sesion": [], "ua": "Por defecto", "inicio": "sesion",
    "nombre": "", "acento": "Aurora", "fondo_animado": True, "mostrar_accesos": True, "tam_fuente": "Normal",
    "zoom": 1.0, "dnt": True, "cookies_terceros": False, "guardar_historial": True, "ofrecer_pw": True,
    "autorrellenar": True, "carpeta_descargas": "", "preguntar_descarga": False, "dev_inicio": False,
    "flags": "", "dormir_min": 30, "sugerir_pw": True, "proteger_pw": False, "usar_hello": True,
    "maestra": None, "grupos": {}, "sync_activa": False, "sync_carpeta": "", "sync_dispositivo": "",
    "sync_frase": "", "ia_proveedor": "Anthropic (Claude)", "ia_modelo": "claude-haiku-5-5",
    "ia_url": "http://localhost:11434/v1", "ia_clave": "", "ia_contexto": True,
}
NUEVA_INCOG = DATOS / "nueva-incognito.html"
NUEVA_INCOG_URL = QUrl.fromLocalFile(str(NUEVA_INCOG)).toString()
C_INCOG = "#150f22"
TIPOS_RECURSO = {
    "MainFrame": "Documento", "SubFrame": "iframe", "Stylesheet": "CSS", "Script": "JS",
    "Image": "Imagen", "FontResource": "Fuente", "Media": "Media", "Xhr": "XHR/fetch",
    "Favicon": "Favicon", "Ping": "Ping", "ServiceWorker": "SW", "Prefetch": "Prefetch",
}
MONO = ["Cascadia Code", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "monospace"]

# ─────────────────────────────────────────────────────────── scripts que se inyectan
JS_EVAL = ("(()=>{try{const r=(0,eval)(%s);if(r===undefined)return 'undefined';"
           "if(typeof r==='function')return r.toString();"
           "try{const j=JSON.stringify(r,null,2);return j===undefined?String(r):j}catch(e){return String(r)}}"
           "catch(e){return '\\u26a0 '+e}})()")

JS_CSS = ("(()=>{let s=document.getElementById('__aurora_css');if(!s){s=document.createElement('style');"
          "s.id='__aurora_css';document.documentElement.appendChild(s)}s.textContent=%s})()")

JS_RENDIMIENTO = r"""(()=>{const n=performance.getEntriesByType('navigation')[0]||{};
const r=performance.getEntriesByType('resource');const kb=r.reduce((a,e)=>a+(e.transferSize||0),0)+(n.transferSize||0);
const pintado=(performance.getEntriesByType('paint').find(p=>p.name==='first-contentful-paint')||{}).startTime;
return JSON.stringify({'Primer pintado (ms)':Math.round(pintado||0),'DOM listo (ms)':Math.round(n.domContentLoadedEventEnd||0),
'Carga completa (ms)':Math.round(n.loadEventEnd||0),'Recursos':r.length,'Transferido (KB)':Math.round(kb/1024),
'Nodos DOM':document.getElementsByTagName('*').length,'Memoria JS (MB)':performance.memory?Math.round(performance.memory.usedJSHeapSize/1048576):'n/d'},null,2)})()"""

JS_JSON = r"""(()=>{if(window.__aurora_json||!/json/.test(document.contentType))return;
let o;try{o=JSON.parse(document.body.innerText)}catch(e){return}window.__aurora_json=1;
const esc=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const j=esc(JSON.stringify(o,null,2)).replace(/("(\\u[a-fA-F0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,m=>{
let c='n';if(/^"/.test(m))c=/:$/.test(m)?'k':'s';else if(/true|false/.test(m))c='b';else if(/null/.test(m))c='z';return '<span class='+c+'>'+m+'</span>'});
document.head.innerHTML='<style>body{background:#0d0f14;color:#e6e8ee;font:13px/1.6 "Cascadia Code",Consolas,monospace;padding:18px 24px;margin:0}'+
'.k{color:#7cc4ff}.s{color:#a5e88a}.n{color:#ffb86b}.b{color:#c792ea}.z{color:#7a8094}'+
'.cab{position:sticky;top:0;background:#0d0f14;color:#8a90a2;padding:0 0 12px;font-family:"Segoe UI",sans-serif}</style>';
document.body.innerHTML='<div class=cab>✨ JSON formateado por Aurora</div><pre>'+j+'</pre>'})()"""

JS_BORRAR_SITIO = ("(()=>{try{localStorage.clear();sessionStorage.clear();"
                   "indexedDB.databases&&indexedDB.databases().then(d=>d.forEach(x=>indexedDB.deleteDatabase(x.name)))}catch(e){}})()")

PLANTILLA_NUEVA = r"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Nueva pestaña</title>
<style>
:root{--a:%%A%%;--b:%%B%%}*{box-sizing:border-box;margin:0}html,body{height:100%}
body{background:#0d0f14;color:#e6e8ee;font-family:"Segoe UI Variable Display","Segoe UI",Inter,system-ui,sans-serif;
display:flex;flex-direction:column;align-items:center;justify-content:center;overflow:hidden;user-select:none}
.fondo{position:fixed;inset:-25%;z-index:-1;filter:blur(90px);opacity:.5}
.fondo i{position:absolute;width:42vmax;height:42vmax;border-radius:50%;animation:flotar 24s ease-in-out infinite alternate}
.fondo i:nth-child(1){background:var(--a);left:12%;top:8%}
.fondo i:nth-child(2){background:var(--b);right:8%;top:28%;animation-duration:30s;animation-delay:-8s}
.fondo i:nth-child(3){background:#ff4fa3;left:38%;bottom:2%;animation-duration:36s;animation-delay:-15s;opacity:.55}
@keyframes flotar{0%{transform:translate(0,0) scale(1)}50%{transform:translate(9vmax,-7vmax) scale(1.18)}100%{transform:translate(-7vmax,6vmax) scale(.88)}}
@keyframes entrar{from{opacity:0;transform:translateY(16px) scale(.98)}to{opacity:1;transform:none}}
.e{animation:entrar .8s cubic-bezier(.2,.8,.2,1) both}
#hora{font-size:96px;font-weight:200;letter-spacing:-3px;line-height:1}
#saludo{color:#aab0c0;font-size:17px;margin:10px 0 36px;animation-delay:.08s}
form{width:min(640px,86vw);animation-delay:.16s}
input{width:100%;padding:18px 26px;border-radius:999px;border:1px solid rgba(255,255,255,.12);background:rgba(18,21,28,.55);
backdrop-filter:blur(24px);color:#fff;font:inherit;font-size:17px;outline:none;transition:border-color .3s,box-shadow .3s,transform .3s}
input::placeholder{color:#7d8396}
input:focus{border-color:rgba(%%A_RGB%%,.9);box-shadow:0 0 0 5px rgba(%%A_RGB%%,.2),0 24px 70px rgba(0,0,0,.45);transform:translateY(-2px)}
.accesos{display:grid;grid-template-columns:repeat(auto-fill,100px);gap:12px;justify-content:center;width:min(780px,90vw);margin-top:40px}
a.acc{display:flex;flex-direction:column;align-items:center;gap:9px;padding:14px 6px;border-radius:20px;color:#cfd3de;
text-decoration:none;font-size:12px;transition:background .25s,transform .25s cubic-bezier(.2,.8,.2,1)}
a.acc:hover{background:rgba(255,255,255,.07);transform:translateY(-5px)}
a.acc b{width:52px;height:52px;border-radius:16px;display:grid;place-items:center;font-size:21px;font-weight:600;color:#fff;
box-shadow:0 10px 28px rgba(0,0,0,.35);transition:transform .25s}
a.acc:hover b{transform:scale(1.07)}
a.acc span{max-width:90px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pista{position:fixed;bottom:22px;color:#646a7d;font-size:12px;animation-delay:.5s}
kbd{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);border-radius:6px;padding:1px 7px;font-family:inherit}
%%CSS_EXTRA%%
</style></head><body>
<div class="fondo"><i></i><i></i><i></i></div>
<div id="hora" class="e"></div><div id="saludo" class="e"></div>
<form id="f" class="e"><input id="q" placeholder="Busca o escribe una dirección" autofocus autocomplete="off" spellcheck="false"></form>
<div class="accesos">%%ACCESOS%%</div>
<div class="pista e"><kbd>Ctrl</kbd> <kbd>K</kbd> paleta de comandos &nbsp;·&nbsp; <kbd>F12</kbd> herramientas de desarrollo &nbsp;·&nbsp; <kbd>Ctrl</kbd> <kbd>D</kbd> guardar en accesos</div>
<script>
const B=%%BUSCADOR%%,N=%%NOMBRE%%;
function t(){const d=new Date(),h=d.getHours();hora.textContent=d.toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'});
saludo.textContent=(h<6?'Buenas noches':h<13?'Buenos días':h<21?'Buenas tardes':'Buenas noches')+(N?', '+N:'')+' · '+
d.toLocaleDateString('es-ES',{weekday:'long',day:'numeric',month:'long'})}
t();setInterval(t,1000);
f.onsubmit=e=>{e.preventDefault();const v=q.value.trim();if(!v)return;let u;
if(/^[a-z][\w+.-]*:\/\//i.test(v))u=v;else if(/^(localhost|127\.0\.0\.1)(:\d+)?/.test(v))u='http://'+v;
else if(/^[^\s]+\.[^\s]{2,}$/.test(v))u='https://'+v;else u=B.replace('{}',encodeURIComponent(v));location.href=u};
</script></body></html>"""

ACCESOS_DEFECTO = [
    ("GitHub", "https://github.com"), ("YouTube", "https://www.youtube.com"),
    ("Stack Overflow", "https://stackoverflow.com"), ("MDN", "https://developer.mozilla.org/es/"),
    ("Wikipedia", "https://es.wikipedia.org"), ("Gmail", "https://mail.google.com"),
]


# ═════════════════════════════ utilidades

def fijar_acento(nombre):
    T.a1, T.a2 = ACENTOS.get(nombre, ACENTOS["Aurora"])


def rgb(color):
    c = QColor(color)
    return f"{c.red()},{c.green()},{c.blue()}"


def mezcla(a, b, t):
    a, b, t = QColor(a), QColor(b), max(0.0, min(1.0, float(t)))
    return QColor(int(a.red() + (b.red() - a.red()) * t), int(a.green() + (b.green() - a.green()) * t),
                  int(a.blue() + (b.blue() - a.blue()) * t), int(a.alpha() + (b.alpha() - a.alpha()) * t))


def con_alfa(color, alfa):
    c = QColor(color)
    c.setAlphaF(max(0.0, min(1.0, alfa)))
    return c


def animacion(padre, al_cambiar, ms=180, curva=QEasingCurve.Type.OutCubic):
    a = QVariantAnimation(padre)
    a.setDuration(ms)
    a.setEasingCurve(curva)
    a.valueChanged.connect(al_cambiar)
    return a


def animar(anim, desde, hasta):
    anim.stop()
    anim.setStartValue(desde)
    anim.setEndValue(hasta)
    anim.start()


def fuente_mono(tam=9.5):
    f = QFont()
    f.setFamilies(MONO)
    f.setPointSizeF(tam)
    return f


def menu_bonito(menu):
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                        | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    return menu


def crear_icono_app():
    pm = QPixmap(256, 256)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    g = QLinearGradient(0, 0, 256, 256)
    g.setColorAt(0, QColor(T.a1))
    g.setColorAt(1, QColor(T.a2))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(g)
    p.drawEllipse(12, 12, 232, 232)
    pen = QPen(QColor(255, 255, 255, 235), 20)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawArc(QRectF(64, 64, 128, 128), 200 * 16, -220 * 16)
    p.drawPoint(128, 170)
    p.end()
    return QIcon(pm)


class Iconos:
    """Usa la fuente de iconos de Windows (Segoe Fluent / MDL2) y, si no existe, símbolos Unicode."""
    familia = None
    MAPA = {
        "atras": ("", "←"), "adelante": ("", "→"), "recargar": ("", "↻"),
        "parar": ("", "✕"), "inicio": ("", "⌂"), "estrella": ("", "☆"),
        "estrella_llena": ("", "★"), "menu": ("", "⋯"), "mas": ("", "+"),
        "cerrar": ("", "✕"), "candado": ("", "🔒"), "buscar": ("", "⌕"),
        "info": ("", "ⓘ"), "dev": ("", "</>"), "arriba": ("", "˄"),
        "abajo": ("", "˅"), "comando": ("", "⌘"), "ajustes": ("", "⚙"),
        "llave": ("", "🔑"), "pincel": ("", "🎨"), "escudo": ("", "🛡"),
        "reloj": ("", "🕘"), "descarga": ("", "⬇"), "ojo": ("", "👁"),
        "copiar": ("", "⧉"), "borrar": ("", "🗑"), "editar": ("", "✎"),
        "lectura": ("", "📖"), "ia": ("", "✨"), "fijar": ("", "📌"),
        "sonido": ("", "🔊"), "silencio": ("", "🔇"), "perfil": ("", "👤"),
        "pausa": ("", "⏸"), "play": ("", "▶"), "carpeta": ("", "📁"),
        "abrir": ("", "↗"), "sync": ("", "⇅"), "extension": ("", "🧩"),
        "enviar": ("", "➤"),
    }

    @classmethod
    def iniciar(cls):
        familias = set(QFontDatabase.families())
        for f in ("Segoe Fluent Icons", "Segoe MDL2 Assets"):
            if f in familias:
                cls.familia = f
                return

    @classmethod
    def glifo(cls, nombre):
        par = cls.MAPA[nombre]
        return par[0] if cls.familia else par[1]

    @classmethod
    def fuente(cls, tam=10.5):
        f = QFont(cls.familia) if cls.familia else QFont()
        f.setPointSizeF(tam if cls.familia else tam + 1.5)
        return f


class Almacen:
    """JSON en ~/.aurora para marcadores, historial y ajustes."""

    def __init__(self, nombre, defecto, carpeta=None):
        self.ruta = Path(carpeta or DATOS) / f"{nombre}.json"
        try:
            self.datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.datos = defecto

    pendientes = set()

    def guardar(self):
        Almacen.pendientes.discard(self)
        temporal = self.ruta.with_suffix(".tmp")
        temporal.write_text(json.dumps(self.datos, ensure_ascii=False, indent=1), encoding="utf-8")
        if os.name == "posix":
            os.chmod(temporal, 0o600)
        os.replace(temporal, self.ruta)  # escritura atómica: nunca queda un JSON a medias

    def guardar_luego(self, ms=2000):
        """Agrupa escrituras frecuentes (p. ej. el historial en cada carga) en una sola."""
        if self not in Almacen.pendientes:
            Almacen.pendientes.add(self)
            QTimer.singleShot(ms, lambda: self.guardar() if self in Almacen.pendientes else None)

    @classmethod
    def volcar_pendientes(cls):
        for almacen in list(cls.pendientes):
            almacen.guardar()


class AlmacenMemoria(Almacen):
    """Igual que Almacen pero solo en memoria (modo incógnito)."""

    def __init__(self, defecto):
        self.ruta, self.datos = None, defecto

    def guardar(self):
        pass

    def guardar_luego(self, ms=2000):
        pass
