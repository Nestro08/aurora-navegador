"""Extensiones de Aurora.

Se instalan en ~/.aurora/extensiones y pueden ser:
  • un archivo .user.js (userscript estilo Greasemonkey/Tampermonkey: @match, @include, @run-at)
  • un archivo .user.css (estilo que se aplica a todas las webs o a las de su comentario @match)
  • una carpeta con manifest.json, que puede traer JavaScript, CSS y/o un módulo de Python:
        {"nombre": "...", "descripcion": "...", "version": "1.0",
         "coincide": ["*://*.youtube.com/*"], "js": ["script.js"], "css": ["estilo.css"],
         "python": "extension.py"}
    El módulo de Python define activar(aurora) y recibe la API de AuroraAPI (más abajo).
"""
import importlib.util
import traceback

from .contrasenas import *  # noqa: F401,F403

CARPETA_EXT = DATOS / "extensiones"

EJEMPLOS = {
    "youtube-sin-shorts/manifest.json": json.dumps({
        "nombre": "YouTube sin Shorts", "version": "1.0",
        "descripcion": "Oculta los Shorts de la portada, las búsquedas y el menú de YouTube.",
        "coincide": ["*://*.youtube.com/*"], "css": ["estilo.css"]}, ensure_ascii=False, indent=2),
    "youtube-sin-shorts/estilo.css": """ytd-reel-shelf-renderer, ytd-rich-shelf-renderer[is-shorts],
ytd-rich-section-renderer:has([is-shorts]), grid-shelf-view-model, ytm-shorts-lockup-view-model,
ytd-guide-entry-renderer:has(a[title="Shorts"]), ytd-mini-guide-entry-renderer[aria-label="Shorts"],
ytd-video-renderer:has(a[href^="/shorts/"]) { display: none !important; }
""",
    "barra-de-lectura.user.js": """// ==UserScript==
// @name         Barra de progreso de lectura
// @description  Muestra arriba una barra fina con lo que llevas leído de la página.
// @version      1.0
// @match        *://*/*
// @run-at       document-end
// ==/UserScript==
(() => {
  if (window.top !== window || document.body.scrollHeight < innerHeight * 2) return;
  const b = document.createElement('div');
  b.style.cssText = 'position:fixed;top:0;left:0;height:3px;width:0;z-index:2147483647;' +
    'background:linear-gradient(90deg,#7c5cff,#22d3ee);transition:width .15s;pointer-events:none';
  document.documentElement.appendChild(b);
  const act = () => { const h = document.documentElement.scrollHeight - innerHeight;
    b.style.width = (h > 0 ? scrollY / h * 100 : 0) + '%'; };
  addEventListener('scroll', act, {passive: true}); act();
})();
""",
    "copiar-markdown/manifest.json": json.dumps({
        "nombre": "Copiar como Markdown", "version": "1.0",
        "descripcion": "Añade a la paleta (Ctrl+K) un comando para copiar el enlace de la página en Markdown. "
                       "Atajo: Ctrl+Shift+K.", "python": "extension.py"}, ensure_ascii=False, indent=2),
    "copiar-markdown/extension.py": '''"""Ejemplo de extensión en Python para Aurora."""


def activar(aurora):
    def copiar():
        aurora.portapapeles(f"[{aurora.titulo_actual()}]({aurora.url_actual()})")
        aurora.aviso("📋  Enlace copiado en Markdown")

    aurora.comando("Copiar enlace en Markdown", copiar, "Ctrl+Shift+K")
''',
    "contador-palabras/manifest.json": json.dumps({
        "nombre": "Contador de palabras", "version": "1.0",
        "descripcion": "Cuenta las palabras de la selección (o de toda la página) y el tiempo de lectura.",
        "python": "extension.py"}, ensure_ascii=False, indent=2),
    "contador-palabras/extension.py": '''"""Ejemplo: usa JavaScript en la página y recibe el resultado en Python."""

JS = "(window.getSelection().toString() || document.body.innerText).trim().split(/\\\\s+/).filter(Boolean).length"


def activar(aurora):
    def contar():
        def mostrar(n):
            n = int(n or 0)
            aurora.aviso(f"📝  {n:,} palabras · {max(1, round(n / 220))} min de lectura".replace(",", "."))
        aurora.ejecutar_js(JS, mostrar)

    aurora.comando("Contar palabras", contar)
''',
}
ACTIVAS_POR_DEFECTO = {"youtube-sin-shorts", "copiar-markdown", "contador-palabras"}


class Extension:
    def __init__(self, ident, ruta):
        self.id, self.ruta = ident, ruta
        self.nombre, self.descripcion, self.version = ident, "", ""
        self.coincide, self.js, self.css, self.python = ["*://*/*"], [], [], None
        self.tipos, self.error, self.modulo = [], "", None

    @property
    def carpeta(self):
        return self.ruta if self.ruta.is_dir() else self.ruta.parent


def _cabecera(nombre, coincide, run_at):
    lineas = ["// ==UserScript==", f"// @name ext:{nombre}"]
    lineas += [f"// @match {c}" for c in coincide] or ["// @match *://*/*"]
    lineas += [f"// @run-at {run_at}", "// ==/UserScript=="]
    return "\n".join(lineas) + "\n"


def _css_a_js(css):
    return ("(()=>{const s=document.createElement('style');s.dataset.aurora='ext';s.textContent=%s;"
            "(document.head||document.documentElement).appendChild(s)})();" % json.dumps(css))


class AuroraAPI:
    """Lo que puede usar una extensión de Python."""

    def __init__(self, gestor_ext, ext):
        self._g, self._ext = gestor_ext, ext

    def _ventana(self):
        from .perfiles import gestor
        return gestor().ventana_activa()

    def comando(self, nombre, funcion, atajo=""):
        """Añade un comando a la paleta (Ctrl+K) y, opcionalmente, un atajo de teclado."""
        self._g.comandos.append((self._ext.id, nombre, atajo, funcion))
        for v in self._g.ventanas():
            v.registrar_atajo_extension(atajo, funcion)

    def al_cargar(self, funcion):
        """funcion(url) se llama cada vez que termina de cargar una página."""
        self._g.al_cargar.append((self._ext.id, funcion))

    def aviso(self, texto):
        v = self._ventana()
        if v:
            v.aviso.mostrar(texto)

    def navegar(self, url):
        v = self._ventana()
        if v:
            v.navegar(QUrl.fromUserInput(url))

    def nueva_pestana(self, url):
        v = self._ventana()
        if v:
            v.nueva_pestana(url)

    def ejecutar_js(self, codigo, callback=None):
        v = self._ventana()
        if v:
            if callback:
                v.vista().page().runJavaScript(codigo, callback)
            else:
                v.vista().page().runJavaScript(codigo)

    def url_actual(self):
        v = self._ventana()
        return v.vista().url().toString() if v else ""

    def titulo_actual(self):
        v = self._ventana()
        return v.vista().title() if v else ""

    def portapapeles(self, texto):
        QApplication.clipboard().setText(texto)


class GestorExtensiones(QObject):
    def __init__(self):
        super().__init__()
        self.lista, self.comandos, self.al_cargar = [], [], []
        self.perfiles_web = []
        self.instalar_ejemplos()
        self.estado = Almacen("estado", {}, CARPETA_EXT)
        self.cargar()

    @staticmethod
    def ventanas():
        from .perfiles import gestor
        return gestor().todas_las_ventanas()

    def instalar_ejemplos(self):
        if CARPETA_EXT.exists():
            return
        for ruta, contenido in EJEMPLOS.items():
            destino = CARPETA_EXT / ruta
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(contenido, encoding="utf-8")
        (CARPETA_EXT / "estado.json").write_text(json.dumps({k: k in ACTIVAS_POR_DEFECTO for k in
                                                             ["youtube-sin-shorts", "barra-de-lectura", "copiar-markdown",
                                                              "contador-palabras"]}), encoding="utf-8")

    def activa(self, ext):
        return self.estado.datos.get(ext.id, True)

    def cargar(self):
        """Lee la carpeta de extensiones."""
        self.lista = []
        CARPETA_EXT.mkdir(parents=True, exist_ok=True)
        for ruta in sorted(CARPETA_EXT.iterdir()):
            try:
                if ruta.is_dir() and (ruta / "manifest.json").exists():
                    ext = Extension(ruta.name, ruta)
                    m = json.loads((ruta / "manifest.json").read_text(encoding="utf-8"))
                    ext.nombre = m.get("nombre", ruta.name)
                    ext.descripcion, ext.version = m.get("descripcion", ""), m.get("version", "")
                    ext.coincide = m.get("coincide", ["*://*/*"])
                    ext.js, ext.css, ext.python = m.get("js", []), m.get("css", []), m.get("python")
                elif ruta.name.endswith(".user.js"):
                    ext = Extension(ruta.name[:-8], ruta)
                    ext.js = [ruta.name]
                    meta = ruta.read_text(encoding="utf-8")
                    for clave, attr in (("name", "nombre"), ("description", "descripcion"), ("version", "version")):
                        r = re.search(rf"//\s*@{clave}\s+(.+)", meta)
                        if r:
                            setattr(ext, attr, r.group(1).strip())
                elif ruta.name.endswith(".user.css"):
                    ext = Extension(ruta.name[:-9], ruta)
                    ext.css = [ruta.name]
                    meta = ruta.read_text(encoding="utf-8")
                    ext.coincide = re.findall(r"@match\s+(\S+)", meta) or ["*://*/*"]
                    r = re.search(r"@name\s+(.+)", meta)
                    ext.nombre = r.group(1).strip().rstrip("*/").strip() if r else ext.id
                else:
                    continue
                ext.tipos = [t for t, x in (("JavaScript", ext.js), ("CSS", ext.css), ("Python", ext.python)) if x]
                self.lista.append(ext)
            except Exception as e:
                ext = Extension(ruta.name, ruta)
                ext.error = f"No se pudo leer: {e}"
                self.lista.append(ext)
        self.activar_python()

    def scripts(self, ext):
        """Convierte la extensión en scripts de QtWebEngine."""
        res = []
        for i, nombre in enumerate(ext.js):
            fuente = (ext.carpeta / nombre).read_text(encoding="utf-8")
            if "==UserScript==" not in fuente:
                fuente = _cabecera(f"{ext.id}-{i}", ext.coincide, "document-end") + fuente
            res.append((f"ext:{ext.id}:js{i}", fuente))
        for i, nombre in enumerate(ext.css):
            css = (ext.carpeta / nombre).read_text(encoding="utf-8")
            res.append((f"ext:{ext.id}:css{i}", _cabecera(f"{ext.id}-css{i}", ext.coincide, "document-start")
                        + _css_a_js(css)))
        return res

    def aplicar(self, perfil_web):
        """Instala (o reinstala) los scripts activos en un perfil web."""
        if perfil_web not in self.perfiles_web:
            self.perfiles_web.append(perfil_web)
        coleccion = perfil_web.scripts()
        for s in list(coleccion.toList()):
            if s.name().startswith("ext:"):
                coleccion.remove(s)
        for ext in self.lista:
            if ext.error or not self.activa(ext):
                continue
            try:
                for nombre, fuente in self.scripts(ext):
                    sc = QWebEngineScript()
                    sc.setSourceCode(fuente)
                    sc.setName(nombre)
                    sc.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
                    sc.setRunsOnSubFrames(False)
                    coleccion.insert(sc)
            except Exception as e:
                ext.error = str(e)

    def activar_python(self):
        for ext in self.lista:
            if not ext.python or ext.modulo or ext.error or not self.activa(ext):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"aurora_ext_{ext.id.replace('-', '_')}",
                                                              ext.carpeta / ext.python)
                modulo = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(modulo)
                modulo.activar(AuroraAPI(self, ext))
                ext.modulo = modulo
            except Exception:
                ext.error = traceback.format_exc(limit=2).strip().splitlines()[-1]

    def desactivar_python(self, ext):
        if ext.modulo and hasattr(ext.modulo, "desactivar"):
            try:
                ext.modulo.desactivar()
            except Exception:
                pass
        ext.modulo = None
        self.comandos = [c for c in self.comandos if c[0] != ext.id]
        self.al_cargar = [c for c in self.al_cargar if c[0] != ext.id]

    def cambiar(self, ext, activa):
        self.estado.datos[ext.id] = activa
        self.estado.guardar()
        if ext.python:
            self.activar_python() if activa else self.desactivar_python(ext)
        for pw in self.perfiles_web:
            self.aplicar(pw)

    def recargar(self):
        for ext in self.lista:
            self.desactivar_python(ext)
        self.cargar()
        for pw in self.perfiles_web:
            self.aplicar(pw)

    def instalar_archivo(self, ruta):
        destino = CARPETA_EXT / Path(ruta).name
        destino.write_bytes(Path(ruta).read_bytes())
        self.recargar()
        return destino

    def notificar_carga(self, url):
        for _, f in list(self.al_cargar):
            try:
                f(url)
            except Exception:
                traceback.print_exc()


_GESTOR_EXT = None


def extensiones():
    global _GESTOR_EXT
    if _GESTOR_EXT is None:
        _GESTOR_EXT = GestorExtensiones()
    return _GESTOR_EXT
