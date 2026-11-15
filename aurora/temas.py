"""Temas: colores de toda la interfaz, fondo y animación de la página de inicio, y sonidos.

Un tema instalado es una carpeta ~/.aurora/temas/<id>/ con tema.json y, si quiere, una imagen o un vídeo de
fondo y sonidos .wav. Se comparte como archivo .aurora-tema (un zip con esos archivos, sin subcarpetas).
Los temas integrados están en este archivo; los de la tienda se descargan de un índice JSON en internet con
su SHA-256. Todo lo que llega de fuera se valida igual: colores #rrggbb, nombres de archivo simples, tipos y
tamaños permitidos y nada más dentro del zip.

Un tema solo necesita cuatro colores (fondo, texto y dos de acento): el resto de la paleta se deriva
mezclando fondo y texto, así que sirve igual para temas oscuros y claros. Cualquier color derivado se puede
fijar a mano en «colores».
"""
import hashlib
import io
import math
import shutil
import struct
import tempfile
import wave
import zipfile

from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .comun import *  # noqa: F401,F403

CARPETA_TEMAS = DATOS / "temas"
EXT_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}
EXT_VIDEO = {".webm", ".mp4"}
EXT_SONIDO = {".wav"}
MAX_ARCHIVO = 30 * 1024 * 1024
MAX_TEMA = 40 * 1024 * 1024
MAX_INDICE = 1024 * 1024
RE_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
RE_ARCHIVO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
BASICOS = ("fondo", "texto", "acento1", "acento2")
# color derivado → cuánto texto se mezcla con el fondo
DERIVADOS = {"hoja": 0.015, "barra": 0.025, "tarjeta": 0.04, "superficie": 0.045, "chip": 0.065, "tooltip": 0.07,
             "aviso": 0.08, "chip_hover": 0.10, "chip_activo": 0.14, "borde": 0.15, "scroll": 0.15,
             "interruptor": 0.20, "borde_fuerte": 0.21, "scroll_hover": 0.24, "apagado": 0.30, "marcador": 0.42,
             "tenue": 0.58}
ANIMACIONES = {"manchas": "Manchas de color", "aurora": "Aurora boreal", "particulas": "Partículas",
               "ninguna": "Sin animación"}
EVENTOS = {"abrir": "Abrir pestaña", "cerrar": "Cerrar pestaña", "cambiar": "Cambiar de pestaña",
           "descarga": "Descarga terminada"}
PAQUETES = {"suave": "Suave", "neon": "Neón", "burbujas": "Burbujas"}

INTEGRADOS = [
    {"id": "aurora", "nombre": "Aurora", "autor": "Aurora", "descripcion": "El de siempre: oscuro, violeta y cian.",
     "colores": {"fondo": "#0d0f14", "texto": "#e6e8ee", "acento1": "#7c5cff", "acento2": "#22d3ee",
                 "barra": "#12151c", "chip": "#1a1e27", "chip_hover": "#212633", "chip_activo": "#262b38",
                 "tenue": "#8a90a2", "borde": "#2a2f3c", "superficie": "#161a22", "tarjeta": "#141821",
                 "hoja": "#10131a", "aviso": "#1c2130", "borde_fuerte": "#2d3343", "scroll": "#2c3241",
                 "scroll_hover": "#3c4459", "apagado": "#4a5060", "interruptor": "#343a48", "tooltip": "#1b1f29",
                 "marcador": "#6b7184"},
     "animacion": "manchas"},
    {"id": "medianoche", "nombre": "Medianoche", "autor": "Aurora", "descripcion": "Azul marino profundo y tranquilo.",
     "colores": {"fondo": "#0a1020", "texto": "#dbe4ff", "acento1": "#3b82f6", "acento2": "#06b6d4"},
     "animacion": "aurora"},
    {"id": "bosque", "nombre": "Bosque", "autor": "Aurora", "descripcion": "Verdes de musgo para leer sin cansarse.",
     "colores": {"fondo": "#0c140f", "texto": "#e0eadf", "acento1": "#22c55e", "acento2": "#a3e635"},
     "animacion": "manchas", "sonidos": {"paquete": "suave"}},
    {"id": "atardecer", "nombre": "Atardecer", "autor": "Aurora", "descripcion": "Naranjas y rosas cálidos.",
     "colores": {"fondo": "#160d0d", "texto": "#f5e6e0", "acento1": "#f97316", "acento2": "#f43f5e"},
     "animacion": "manchas"},
    {"id": "neon", "nombre": "Neón", "autor": "Aurora", "descripcion": "Modo gamer: negro, magenta, partículas y "
                                                                      "sonidos sintetizados.",
     "colores": {"fondo": "#07060c", "texto": "#f2eaff", "acento1": "#ff2bd6", "acento2": "#00f0ff"},
     "animacion": "particulas", "sonidos": {"paquete": "neon"}},
    {"id": "papel", "nombre": "Papel", "autor": "Aurora", "descripcion": "Claro y limpio, como una hoja.",
     "colores": {"fondo": "#f6f4ef", "texto": "#1f2328", "acento1": "#2563eb", "acento2": "#0ea5e9"},
     "animacion": "ninguna"},
    {"id": "sakura", "nombre": "Sakura", "autor": "Aurora", "descripcion": "Claro con rosas de cerezo y burbujas.",
     "colores": {"fondo": "#fdf2f6", "texto": "#3b1f2b", "acento1": "#ec4899", "acento2": "#a78bfa"},
     "animacion": "manchas", "sonidos": {"paquete": "burbujas"}},
]
IDS_INTEGRADOS = {t["id"] for t in INTEGRADOS}


# ═════════════════════════════ validación y paleta

def es_color(valor):
    return isinstance(valor, str) and bool(RE_COLOR.match(valor))


def es_oscuro(color):
    return QColor(color).lightnessF() < 0.5


def _texto(valor, maximo):
    return str(valor or "").strip()[:maximo]


def _archivo(nombre, extensiones, carpeta):
    if not isinstance(nombre, str) or not RE_ARCHIVO.match(nombre) or Path(nombre).suffix.lower() not in extensiones:
        raise ValueError(f"archivo no válido: {nombre!r}")
    if carpeta is not None and not (Path(carpeta) / nombre).is_file():
        raise ValueError(f"falta el archivo {nombre}")
    return nombre


def normalizar(datos, carpeta=None):
    """Comprueba un tema (de tema.json) y lo devuelve limpio. Lanza ValueError si algo no vale."""
    if not isinstance(datos, dict):
        raise ValueError("tema.json no es un objeto")
    nombre = _texto(datos.get("nombre"), 40)
    if not nombre:
        raise ValueError("el tema no tiene nombre")
    colores = datos.get("colores")
    if not isinstance(colores, dict) or not all(es_color(colores.get(k)) for k in BASICOS):
        raise ValueError("faltan colores básicos (fondo, texto, acento1, acento2) en formato #rrggbb")
    tema = {"id": slug_tema(datos.get("id") or nombre), "nombre": nombre, "autor": _texto(datos.get("autor"), 40),
            "version": _texto(datos.get("version"), 12) or "1.0", "descripcion": _texto(datos.get("descripcion"), 200),
            "colores": {k: v.lower() for k, v in colores.items() if (k in BASICOS or k in DERIVADOS) and es_color(v)},
            "animacion": datos.get("animacion") if datos.get("animacion") in ANIMACIONES else "manchas",
            "fondo": None, "sonidos": None}
    fondo = datos.get("fondo")
    if isinstance(fondo, dict) and fondo.get("archivo"):
        tipo = fondo.get("tipo")
        if tipo not in ("imagen", "video"):
            raise ValueError("el fondo debe ser «imagen» o «video»")
        tema["fondo"] = {"tipo": tipo, "archivo": _archivo(fondo["archivo"], EXT_IMAGEN if tipo == "imagen"
                                                            else EXT_VIDEO, carpeta),
                         "oscurecer": max(0.0, min(0.9, float(fondo.get("oscurecer", 0.35))))}
    sonidos = datos.get("sonidos")
    if isinstance(sonidos, dict):
        if sonidos.get("paquete") in PAQUETES:
            tema["sonidos"] = {"paquete": sonidos["paquete"]}
        else:
            propios = {e: _archivo(sonidos[e], EXT_SONIDO, carpeta) for e in EVENTOS if sonidos.get(e)}
            tema["sonidos"] = propios or None
    return tema


def slug_tema(texto):
    s = re.sub(r"[^a-z0-9]+", "-", str(texto).lower()).strip("-")[:40]
    return s or "tema"


def paleta(tema):
    """Todos los colores de la interfaz para un tema."""
    c = tema["colores"]
    res = {k: c[k] for k in BASICOS}
    for clave, t in DERIVADOS.items():
        res[clave] = c.get(clave) or mezcla(c["fondo"], c["texto"], t).name()
    return res


# ═════════════════════════════ temas instalados

def integrado(ident):
    return next((normalizar(t) for t in INTEGRADOS if t["id"] == ident), None)


def carpeta_de(ident):
    return None if ident in IDS_INTEGRADOS else CARPETA_TEMAS / ident


def instalados():
    """Integrados y luego los instalados por el usuario o desde la tienda."""
    res = [normalizar(t) for t in INTEGRADOS]
    if CARPETA_TEMAS.is_dir():
        for d in sorted(CARPETA_TEMAS.iterdir()):
            if d.is_dir() and not d.name.startswith("_") and (d / "tema.json").is_file():
                try:
                    tema = normalizar(json.loads((d / "tema.json").read_text(encoding="utf-8")), d)
                    tema["id"] = d.name
                    res.append(tema)
                except (OSError, ValueError):
                    continue
    return res


def buscar(ident):
    return next((t for t in instalados() if t["id"] == ident), None) or integrado("aurora")


def _id_libre(ident):
    if ident not in IDS_INTEGRADOS:
        return ident
    n = 2
    while f"{ident}-{n}" in IDS_INTEGRADOS:
        n += 1
    return f"{ident}-{n}"


def importar_zip(origen):
    """Instala un .aurora-tema (ruta o bytes). Devuelve el tema. Lanza ValueError si el archivo no es válido."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(origen) if isinstance(origen, (bytes, bytearray)) else origen)
    except (zipfile.BadZipFile, OSError) as e:
        raise ValueError(f"no es un archivo de tema: {e}")
    with zf:
        miembros = zf.infolist()
        if not any(m.filename == "tema.json" for m in miembros):
            raise ValueError("falta tema.json")
        total = 0
        permitidas = EXT_IMAGEN | EXT_VIDEO | EXT_SONIDO | {".json"}
        for m in miembros:
            if m.is_dir() or not RE_ARCHIVO.match(m.filename) or Path(m.filename).suffix.lower() not in permitidas \
                    or (m.filename.endswith(".json") and m.filename != "tema.json"):
                raise ValueError(f"archivo no permitido en el tema: {m.filename!r}")
            if m.file_size > MAX_ARCHIVO:
                raise ValueError(f"{m.filename} es demasiado grande")
            total += m.file_size
        if total > MAX_TEMA:
            raise ValueError("el tema es demasiado grande")
        temporal = Path(tempfile.mkdtemp(prefix="aurora-tema-"))
        try:
            for m in miembros:
                with zf.open(m) as f:  # se lee con límite por si el zip miente sobre el tamaño
                    datos = f.read(MAX_ARCHIVO + 1)
                if len(datos) > MAX_ARCHIVO:
                    raise ValueError(f"{m.filename} es demasiado grande")
                (temporal / m.filename).write_bytes(datos)
            try:
                bruto = json.loads((temporal / "tema.json").read_text(encoding="utf-8"))
            except ValueError:
                raise ValueError("tema.json no es JSON válido")
            tema = normalizar(bruto, temporal)
            tema["id"] = _id_libre(tema["id"])
            bruto["id"] = tema["id"]
            (temporal / "tema.json").write_text(json.dumps(bruto, ensure_ascii=False, indent=1), encoding="utf-8")
            destino = CARPETA_TEMAS / tema["id"]
            CARPETA_TEMAS.mkdir(parents=True, exist_ok=True)
            shutil.rmtree(destino, ignore_errors=True)
            shutil.move(str(temporal), destino)
            return tema
        finally:
            shutil.rmtree(temporal, ignore_errors=True)


def exportar_zip(tema, ruta):
    """Guarda un tema como .aurora-tema."""
    carpeta = carpeta_de(tema["id"])
    datos = {k: v for k, v in tema.items() if v is not None}
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("tema.json", json.dumps(datos, ensure_ascii=False, indent=1))
        for nombre in archivos_de(tema):
            if carpeta and (carpeta / nombre).is_file():
                zf.write(carpeta / nombre, nombre)


def archivos_de(tema):
    res = [tema["fondo"]["archivo"]] if tema.get("fondo") else []
    sonidos = tema.get("sonidos") or {}
    return res + [sonidos[e] for e in EVENTOS if e in sonidos]


def guardar(tema, archivos_nuevos=None):
    """Guarda un tema creado o editado en el editor. archivos_nuevos = {nombre_en_el_tema: ruta_de_origen}."""
    tema = dict(tema)
    tema["id"] = _id_libre(slug_tema(tema.get("id") or tema["nombre"]))
    destino = CARPETA_TEMAS / tema["id"]
    destino.mkdir(parents=True, exist_ok=True)
    for nombre, origen in (archivos_nuevos or {}).items():
        if Path(origen).stat().st_size > MAX_ARCHIVO:
            raise ValueError(f"{Path(origen).name} es demasiado grande (máximo 30 MB)")
        if Path(origen).resolve() != (destino / nombre).resolve():
            shutil.copyfile(origen, destino / nombre)
    limpio = normalizar(tema, destino)
    (destino / "tema.json").write_text(json.dumps({k: v for k, v in limpio.items() if v is not None},
                                                  ensure_ascii=False, indent=1), encoding="utf-8")
    usados = set(archivos_de(limpio)) | {"tema.json"}
    for f in destino.iterdir():  # lo que ya no usa el tema
        if f.is_file() and f.name not in usados:
            f.unlink()
    return limpio


def borrar(ident):
    if ident not in IDS_INTEGRADOS:
        shutil.rmtree(CARPETA_TEMAS / ident, ignore_errors=True)


def url_archivo(tema, nombre):
    carpeta = carpeta_de(tema["id"])
    return QUrl.fromLocalFile(str(carpeta / nombre)).toString() if carpeta else ""


# ═════════════════════════════ aplicar

class Apariencia:
    """Tema y sonidos elegidos: son de toda la aplicación (todas las ventanas y perfiles)."""
    almacen = None
    tema = None

    @classmethod
    def datos(cls):
        if cls.almacen is None:
            cls.almacen = Almacen("apariencia", {})
            for k, v in {"tema": "aurora", "acento": "", "sonidos": True, "volumen": 0.6, "tienda_url": "",
                         "arranque": True}.items():
                cls.almacen.datos.setdefault(k, v)
        return cls.almacen.datos

    @classmethod
    def guardar(cls, **cambios):
        cls.datos().update(cambios)
        cls.almacen.guardar()


def aplicar_colores(tema, acento=""):
    """Cambia los colores globales (C y T). Lo demás (hoja de estilo, páginas) lo refresca quien llama."""
    Apariencia.tema = tema
    pal = paleta(tema)
    C.clear()
    C.update(pal)
    T.a1, T.a2 = ACENTOS[acento] if acento in ACENTOS else (pal["acento1"], pal["acento2"])
    sonidos().cargar(tema)


def paleta_qt():
    p = QPalette()
    for rol, color in ((QPalette.ColorRole.Window, C["fondo"]), (QPalette.ColorRole.WindowText, C["texto"]),
                       (QPalette.ColorRole.Base, C["chip"]), (QPalette.ColorRole.Text, C["texto"]),
                       (QPalette.ColorRole.Button, C["chip"]), (QPalette.ColorRole.ButtonText, C["texto"]),
                       (QPalette.ColorRole.Highlight, T.a1), (QPalette.ColorRole.HighlightedText, "#ffffff"),
                       (QPalette.ColorRole.ToolTipBase, C["tooltip"]), (QPalette.ColorRole.ToolTipText, C["texto"]),
                       (QPalette.ColorRole.PlaceholderText, C["marcador"])):
        p.setColor(rol, QColor(color))
    return p


def fondo_pagina_inicio(tema, animado=True):
    """→ (html, css) del fondo de la página de inicio para el tema."""
    f = tema.get("fondo")
    if f:
        url = html.escape(url_archivo(tema, f["archivo"]), True)
        velo = f'<div class="velo" style="opacity:{f["oscurecer"]:.2f}"></div>'
        if f["tipo"] == "video":
            return (f'<video class="foto" src="{url}" autoplay muted loop playsinline></video>{velo}', "")
        return f'<div class="foto" style="background-image:url(\'{url}\')"></div>{velo}', ""
    anim = tema.get("animacion", "manchas")
    quieto = "" if animado else ".fondo i,.aur i{animation:none!important}"
    if anim == "manchas":
        return '<div class="fondo"><i></i><i></i><i></i></div>', quieto
    if anim == "aurora":
        return '<div class="aur"><i></i><i></i><i></i></div>', quieto
    if anim == "particulas":
        return ('<canvas id="part"></canvas><script>(()=>{const c=document.getElementById("part"),x=c.getContext("2d");'
                f'const quieto={"true" if not animado else "false"};let w,h,ps=[];'
                'function tam(){w=c.width=innerWidth;h=c.height=innerHeight;ps=Array.from({length:Math.round(w*h/9000)},'
                '()=>({x:Math.random()*w,y:Math.random()*h,r:Math.random()*1.8+.4,vx:(Math.random()-.5)*.35,'
                'vy:(Math.random()-.5)*.35,a:Math.random()*.6+.25,c:Math.random()<.5?1:2}))}'
                'const col=n=>getComputedStyle(document.documentElement).getPropertyValue(n===1?"--a":"--b");'
                'function paso(){x.clearRect(0,0,w,h);for(const p of ps){if(!quieto){p.x=(p.x+p.vx+w)%w;p.y=(p.y+p.vy+h)%h}'
                'x.globalAlpha=p.a;x.fillStyle=col(p.c);x.beginPath();x.arc(p.x,p.y,p.r,0,7);x.fill()}'
                'if(!quieto)requestAnimationFrame(paso)}addEventListener("resize",()=>{tam();quieto&&paso()});tam();paso()})()'
                '</script>', "")
    return "", ""


# ═════════════════════════════ sonidos

def _sintetizar(notas, forma="seno", volumen=0.5):
    """WAV de 16 bits a 44,1 kHz con notas (frecuencia_inicial, frecuencia_final, segundos) seguidas."""
    tasa, muestras = 44100, []
    for f0, f1, dur in notas:
        n = int(tasa * dur)
        fase = 0.0
        for i in range(n):
            t = i / n
            f = f0 + (f1 - f0) * t
            fase += 2 * math.pi * f / tasa
            if forma == "cuadrada":
                v = 0.6 if math.sin(fase) >= 0 else -0.6
            elif forma == "triangulo":
                v = 2 / math.pi * math.asin(math.sin(fase))
            else:
                v = math.sin(fase)
            envolvente = min(1.0, i / (tasa * 0.004)) * (1 - t) ** 2
            muestras.append(int(32767 * volumen * v * envolvente))
    salida = io.BytesIO()
    with wave.open(salida, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(tasa)
        w.writeframes(struct.pack(f"<{len(muestras)}h", *muestras))
    return salida.getvalue()


SINTESIS = {
    "suave": {"abrir": ([(660, 880, .09)], "seno"), "cerrar": ([(660, 440, .1)], "seno"),
              "cambiar": ([(990, 990, .04)], "seno"), "descarga": ([(523, 523, .08), (784, 784, .14)], "seno")},
    "neon": {"abrir": ([(220, 1320, .12)], "cuadrada"), "cerrar": ([(1320, 180, .12)], "cuadrada"),
             "cambiar": ([(1760, 1760, .025)], "cuadrada"),
             "descarga": ([(440, 440, .06), (660, 660, .06), (990, 990, .12)], "cuadrada")},
    "burbujas": {"abrir": ([(400, 1200, .07)], "triangulo"), "cerrar": ([(1200, 500, .07)], "triangulo"),
                 "cambiar": ([(1500, 1900, .03)], "triangulo"),
                 "descarga": ([(700, 1400, .06), (900, 1800, .08)], "triangulo")},
}


def ruta_sonido(tema, evento):
    s = tema.get("sonidos") or {}
    if "paquete" in s:
        carpeta = CARPETA_TEMAS / "_sonidos" / s["paquete"]
        ruta = carpeta / f"{evento}.wav"
        if not ruta.exists():
            notas, forma = SINTESIS[s["paquete"]][evento]
            carpeta.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(_sintetizar(notas, forma, 0.35 if forma == "cuadrada" else 0.5))
        return ruta
    if evento in s and carpeta_de(tema["id"]):
        return carpeta_de(tema["id"]) / s[evento]
    return None


class Sonidos:
    def __init__(self):
        self.efectos = {}
        try:
            from PyQt6.QtMultimedia import QSoundEffect
            self._clase = QSoundEffect
        except ImportError:  # sin QtMultimedia, Aurora funciona igual pero en silencio
            self._clase = None

    def cargar(self, tema):
        self.efectos = {}
        if not self._clase:
            return
        for evento in EVENTOS:
            ruta = ruta_sonido(tema, evento)
            if ruta and ruta.exists():
                e = self._clase()
                e.setSource(QUrl.fromLocalFile(str(ruta)))
                self.efectos[evento] = e

    def tocar(self, evento):
        a = Apariencia.datos()
        e = self.efectos.get(evento)
        if e and a["sonidos"]:
            e.setVolume(float(a["volumen"]))
            e.play()


_SONIDOS = None


def sonidos():
    global _SONIDOS
    if _SONIDOS is None:
        _SONIDOS = Sonidos()
    return _SONIDOS


# ═════════════════════════════ tienda en línea

class Tienda(QObject):
    """Lee el índice de la tienda y descarga temas y miniaturas (solo HTTPS, con límites y SHA-256)."""
    indice_listo = pyqtSignal(list, str)  # temas, error
    miniatura_lista = pyqtSignal(str, QPixmap)
    instalado = pyqtSignal(dict, str)  # tema, error

    def __init__(self, padre=None):
        super().__init__(padre)
        self.red = QNetworkAccessManager(self)
        self.base = QUrl()
        self.cache = CARPETA_TEMAS / "_cache"

    def _pedir(self, url, limite, hecho):
        url = QUrl(url)
        if url.scheme() != "https":
            hecho(None, "la tienda solo usa direcciones https://")
            return
        peticion = QNetworkRequest(url)
        peticion.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                              QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        r = self.red.get(peticion)

        def progreso(recibido, total):
            if recibido > limite or total > limite:
                r.abort()

        def fin():
            r.deleteLater()
            if r.error() == QNetworkReply.NetworkError.OperationCanceledError:
                hecho(None, "el archivo es demasiado grande")
            elif r.error() != QNetworkReply.NetworkError.NoError:
                hecho(None, r.errorString())
            else:
                hecho(bytes(r.readAll()), "")

        r.downloadProgress.connect(progreso)
        r.finished.connect(fin)

    def cargar_indice(self, url):
        self.base = QUrl(url)

        def hecho(datos, error):
            if datos is None:
                self.indice_listo.emit([], error)
                return
            try:
                bruto = json.loads(datos.decode("utf-8"))
                temas = [self._entrada(e) for e in bruto.get("temas", [])]
                self.indice_listo.emit([t for t in temas if t], "")
            except (ValueError, AttributeError) as e:
                self.indice_listo.emit([], f"índice no válido: {e}")

        self._pedir(url, MAX_INDICE, hecho)

    def _entrada(self, e):
        try:
            tema = normalizar(e)  # sin carpeta: los archivos aún no están
            archivo = self.base.resolved(QUrl(str(e["archivo"]))).toString()
            if not re.fullmatch(r"[0-9a-f]{64}", str(e.get("sha256", ""))):
                return None
            tema.update(tienda={"archivo": archivo, "sha256": e["sha256"],
                                "miniatura": self.base.resolved(QUrl(str(e["miniatura"]))).toString()
                                if e.get("miniatura") else ""})
            return tema
        except (KeyError, ValueError, TypeError):
            return None

    def miniatura(self, tema):
        url = tema.get("tienda", {}).get("miniatura")
        if not url:
            return
        cacheada = self.cache / f"{tema['tienda']['sha256']}.png"
        if cacheada.exists():
            self.miniatura_lista.emit(tema["id"], QPixmap(str(cacheada)))
            return

        def hecho(datos, error):
            pm = QPixmap()
            if datos and pm.loadFromData(datos):
                self.cache.mkdir(parents=True, exist_ok=True)
                pm.save(str(cacheada), "PNG")
                self.miniatura_lista.emit(tema["id"], pm)

        self._pedir(url, 2 * 1024 * 1024, hecho)

    def instalar(self, tema):
        def hecho(datos, error):
            if datos is None:
                self.instalado.emit(tema, error)
            elif hashlib.sha256(datos).hexdigest() != tema["tienda"]["sha256"]:
                self.instalado.emit(tema, "el archivo descargado no coincide con el de la tienda (SHA-256)")
            else:
                try:
                    self.instalado.emit(importar_zip(datos), "")
                except ValueError as e:
                    self.instalado.emit(tema, str(e))

        self._pedir(tema["tienda"]["archivo"], MAX_TEMA, hecho)
