"""Versiones nuevas: Aurora mira la última Release de GitHub (como mucho una vez al día) y se actualiza con un clic.

  • Windows (instalado con el instalador): descarga Aurora-Setup-x.y.exe, comprueba su SHA-256 con el
    SHA256SUMS.txt de la Release, lo ejecuta en silencio y el instalador vuelve a abrir Aurora.
  • Linux (instalado con instalar-fedora.sh): descarga Aurora-x.y-Linux.zip, lo comprueba, lo descomprime y
    ejecuta «instalar-fedora.sh --sin-preguntas»; luego ofrece reiniciar.
  • Desde el código (git, iniciar.bat…): solo avisa y abre la página de la Release.
Solo se descarga por HTTPS desde GitHub y nada se ejecuta si la huella no coincide. Los archivos se piden por la
API («releases/assets/<id>»): la dirección normal de descarga la cachea GitHub y, si se sustituye un archivo con el
mismo nombre, sigue dando el viejo durante un rato.
"""
import hashlib
import tempfile
import time
import zipfile

from PyQt6.QtCore import QProcess
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from .comun import *  # noqa: F401,F403
from . import __version__

REPO = "Nestro08/aurora-navegador"
URL_ULTIMA = f"https://api.github.com/repos/{REPO}/releases/latest"
URL_RELEASES = f"https://github.com/{REPO}/releases"
URL_ARCHIVOS = f"https://api.github.com/repos/{REPO}/releases/assets/"
INTERVALO = 20 * 3600  # entre consultas automáticas
CARPETA_APP = Path.home() / ".local" / "share" / "aurora-app"  # donde instala instalar-fedora.sh
LANZADOR = Path.home() / ".local" / "bin" / "aurora"
ARCHIVOS = {"windows": r"Aurora-Setup-\d+(\.\d+)*\.exe", "linux": r"Aurora-\d+(\.\d+)*-Linux\.zip"}
MAX_DESCARGA = 600 * 1024 * 1024


def tupla(version):
    """«v4.10.1» → (4, 10, 1): para comparar versiones como números, no como texto."""
    numeros = [int(x) for x in re.findall(r"\d+", str(version))][:4]
    return tuple(numeros + [0] * (4 - len(numeros)))


def mas_nueva(remota, local=__version__):
    return tupla(remota) > tupla(local)


def como_se_instala():
    """«windows», «linux» o None (si se ejecuta desde el código: se actualiza con git)."""
    if sys.platform == "win32" and getattr(sys, "frozen", False):
        return "windows"
    if sys.platform.startswith("linux"):
        try:
            if Path(__file__).resolve().is_relative_to(CARPETA_APP.resolve()):
                return "linux"
        except OSError:
            pass
    return None


def de_github(archivo):
    """True si el archivo de la Release se descarga de este repositorio de GitHub (por su API)."""
    return isinstance(archivo, dict) and str(archivo.get("url", "")).startswith(URL_ARCHIVOS)


def archivo_para(release, modo):
    """El archivo de la Release para este sistema (dict de la API de GitHub: name, url…)."""
    for a in release.get("assets") or []:
        if de_github(a) and re.fullmatch(ARCHIVOS[modo], str(a.get("name", ""))):
            return a
    return None


def huella_de(sumas, nombre):
    """Busca la línea de «sha256sum» de un archivo: «<64 hex>  nombre» (o « *nombre»)."""
    for linea in sumas.splitlines():
        m = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", linea.strip())
        if m and m.group(2).strip() == nombre:
            return m.group(1).lower()
    return None


def extraer_seguro(zip_ruta, destino):
    """Descomprime sin dejar que ninguna ruta salga de la carpeta (zip slip). Devuelve la carpeta «Aurora»."""
    destino = Path(destino).resolve()
    with zipfile.ZipFile(zip_ruta) as z:
        for m in z.infolist():
            ruta = (destino / m.filename).resolve()
            if not ruta.is_relative_to(destino):
                raise ValueError(f"ruta peligrosa en el paquete: {m.filename}")
        z.extractall(destino)
        for m in z.infolist():  # zipfile no conserva el permiso de ejecución
            if (m.external_attr >> 16) & 0o111:
                os.chmod(destino / m.filename, 0o755)
    carpeta = destino / "Aurora"
    if not (carpeta / "instalar-fedora.sh").is_file():
        raise ValueError("el paquete no trae instalar-fedora.sh")
    return carpeta


class Actualizador(QObject):
    disponible = pyqtSignal(dict)  # la Release (de la API de GitHub) de una versión más nueva

    def __init__(self):
        super().__init__()
        self.red = QNetworkAccessManager(self)
        self.ultima = None
        self.instalando = False
        self.reloj = QTimer(self, interval=6 * 3600 * 1000)  # para quien deja Aurora abierto días
        self.reloj.timeout.connect(self.buscar)

    @staticmethod
    def _ajustes():
        from .temas import Apariencia
        return Apariencia

    def _peticion(self, url, archivo=False):
        """archivo=True: el contenido de un archivo de la Release (la API redirige a la descarga)."""
        p = QNetworkRequest(QUrl(url))
        p.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute,
                       QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        p.setRawHeader(b"User-Agent", f"Aurora/{__version__}".encode())
        p.setRawHeader(b"Accept", b"application/octet-stream" if archivo else b"application/vnd.github+json")
        return p

    # ─────────────── buscar
    def buscar(self, manual=False, al_terminar=None):
        """al_terminar(estado, mensaje) con estado «nueva», «al_dia» o «error»."""
        a = self._ajustes().datos()
        if not manual and (not a.get("buscar_actualizaciones", True)
                           or time.time() - float(a.get("ultima_busqueda") or 0) < INTERVALO):
            return
        r = self.red.get(self._peticion(URL_ULTIMA))

        def fin():
            r.deleteLater()
            if r.error() != QNetworkReply.NetworkError.NoError:
                estado = r.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
                resultado = ("al_dia", "Aún no hay ninguna versión publicada") if estado == 404 else \
                    ("error", f"No se pudo comprobar: {r.errorString()}")
            else:
                self._ajustes().guardar(ultima_busqueda=time.time())
                resultado = self.procesar(bytes(r.readAll())[:1024 * 1024], manual)
            if al_terminar:
                al_terminar(*resultado)

        r.finished.connect(fin)

    def procesar(self, datos, manual=False):
        try:
            release = json.loads(datos.decode("utf-8"))
            etiqueta = str(release["tag_name"])
            if not str(release.get("html_url", "")).startswith(f"https://github.com/{REPO}/"):
                raise ValueError("dirección inesperada")
        except (ValueError, KeyError, TypeError, AttributeError):
            return "error", "La respuesta de GitHub no es válida"
        if release.get("draft") or release.get("prerelease") or not mas_nueva(etiqueta):
            return "al_dia", f"Tienes la última versión ({__version__})"
        if not manual and etiqueta == self._ajustes().datos().get("omitida"):
            return "al_dia", f"Has decidido saltarte la {etiqueta}"
        self.ultima = release
        self.disponible.emit(release)
        return "nueva", f"Aurora {etiqueta.lstrip('v')} ya está disponible"

    # ─────────────── descargar y comprobar
    def descargar(self, release, progreso, terminado):
        """Descarga el archivo de este sistema y comprueba su SHA-256. terminado(ruta o None, error)."""
        modo = como_se_instala()
        archivo = archivo_para(release, modo) if modo else None
        sumas = next((a for a in release.get("assets") or []
                      if de_github(a) and a.get("name") == "SHA256SUMS.txt"), None)
        if not archivo or not sumas:
            terminado(None, "Esta versión no trae el archivo para tu sistema")
            return
        r = self.red.get(self._peticion(sumas["url"], archivo=True))

        def fin_sumas():
            r.deleteLater()
            esperada = huella_de(bytes(r.readAll())[:65536].decode("utf-8", "ignore"), archivo["name"]) \
                if r.error() == QNetworkReply.NetworkError.NoError else None
            if not esperada:
                terminado(None, "No se pudo comprobar la huella de la descarga")
                return
            self._bajar(archivo, esperada, progreso, terminado)

        r.finished.connect(fin_sumas)

    def _bajar(self, archivo, esperada, progreso, terminado):
        carpeta = Path(tempfile.mkdtemp(prefix="aurora-actualizacion-"))
        ruta = carpeta / archivo["name"]
        salida = open(ruta, "wb")
        huella = hashlib.sha256()
        r = self.red.get(self._peticion(archivo["url"], archivo=True))

        def leer():
            trozo = bytes(r.readAll())
            huella.update(trozo)
            salida.write(trozo)

        def avance(recibido, total):
            if max(recibido, total) > MAX_DESCARGA:
                r.abort()
            elif total > 0:
                progreso(recibido / total)

        def fin():
            leer()
            salida.close()
            r.deleteLater()
            if r.error() != QNetworkReply.NetworkError.NoError:
                terminado(None, f"La descarga falló: {r.errorString()}")
            elif huella.hexdigest() != esperada:
                ruta.unlink(missing_ok=True)
                terminado(None, "La descarga no coincide con la huella publicada: no se instala")
            else:
                terminado(ruta, "")

        r.readyRead.connect(leer)
        r.downloadProgress.connect(avance)
        r.finished.connect(fin)

    # ─────────────── instalar
    def instalar(self, ruta, al_terminar):
        """al_terminar(ok, mensaje). En Windows no vuelve: Aurora se cierra y el instalador la reabre."""
        modo = como_se_instala()
        if modo == "windows":
            if not QProcess.startDetached(str(ruta), ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]):
                al_terminar(False, "No se pudo abrir el instalador")
                return
            cerrar_aurora()
            return
        try:
            carpeta = extraer_seguro(ruta, Path(ruta).parent)
        except (ValueError, OSError, zipfile.BadZipFile) as e:
            al_terminar(False, f"El paquete no es válido: {e}")
            return
        proceso = QProcess(self)
        proceso.setWorkingDirectory(str(carpeta))
        proceso.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def fin(codigo, _estado):
            salida = bytes(proceso.readAll()).decode("utf-8", "ignore").strip().splitlines()
            if codigo == 0:
                al_terminar(True, "")
            elif codigo == 3:
                al_terminar(False, "Faltan paquetes del sistema. Abre una terminal y ejecuta: "
                                   f"bash {carpeta / 'instalar-fedora.sh'}")
            else:
                al_terminar(False, "La instalación falló: " + (salida[-1] if salida else f"código {codigo}"))

        proceso.finished.connect(fin)
        proceso.start("bash", ["instalar-fedora.sh", "--sin-preguntas"])


def cerrar_aurora():
    """Cierra todas las ventanas (guardan la sesión) y sale."""
    app = QApplication.instance()
    app.closeAllWindows()
    Almacen.volcar_pendientes()
    app.quit()


def reiniciar():
    """Linux: abre la versión nueva cuando esta ya se haya cerrado (si no, solo le pasaría una pestaña)."""
    QProcess.startDetached("sh", ["-c", 'sleep 2; exec "$0"', str(LANZADOR)])
    cerrar_aurora()


_ACTUALIZADOR = None


def actualizador():
    global _ACTUALIZADOR
    if _ACTUALIZADOR is None:
        _ACTUALIZADOR = Actualizador()
    return _ACTUALIZADOR


# ─────────────── en la ventana

def ofrecer(ventana, release):
    """Tarjeta «Aurora x.y ya está disponible» con Omitir · Novedades · Actualizar."""
    version = str(release["tag_name"]).lstrip("v")
    modo = como_se_instala()
    from .temas import Apariencia

    def omitir():
        Apariencia.guardar(omitida=release["tag_name"])

    def novedades():
        ventana.nueva_pestana(release["html_url"])

    def actualizar():
        if modo is None:
            ventana.nueva_pestana(release["html_url"])
            ventana.aviso.mostrar("Estás usando Aurora desde el código: actualiza con «git pull»")
            return
        actualizar_ahora(ventana, release)

    detalle = f"Tienes la {__version__}."
    notas = [l.strip("-*# ").strip() for l in str(release.get("body") or "").splitlines()
             if l.strip().startswith(("-", "*")) and len(l.strip()) > 3][:3]
    if notas:
        detalle += "<br>" + "<br>".join("• " + html.escape(n[:90]) for n in notas)
    ventana.pregunta.mostrar(f"Aurora {version} ya está disponible", detalle,
                             [("Omitir", omitir, False), ("Novedades", novedades, False),
                              ("Actualizar" if modo else "Descargar", actualizar, True)], "descarga")


def actualizar_ahora(ventana, release):
    a = actualizador()
    if a.instalando:
        ventana.aviso.mostrar("La actualización ya está en marcha")
        return
    a.instalando = True
    version = str(release["tag_name"]).lstrip("v")
    ultimo = {"pct": -1}

    def progreso(f):
        pct = int(f * 100)
        if pct >= ultimo["pct"] + 5:
            ultimo["pct"] = pct
            ventana.aviso.mostrar(f"⬇  Descargando Aurora {version}… {pct} %")

    def instalado(ok, mensaje):
        a.instalando = False
        if not ok:
            QMessageBox.warning(ventana, "Actualizar Aurora", mensaje)
            return
        ventana.pregunta.mostrar(f"Aurora {version} instalado", "Reinicia para empezar a usarlo. Tus pestañas "
                                 "se volverán a abrir.", [("Más tarde", lambda: None, False),
                                                          ("Reiniciar ahora", reiniciar, True)], "sync")

    def descargado(ruta, error):
        if not ruta:
            a.instalando = False
            QMessageBox.warning(ventana, "Actualizar Aurora", error)
            return
        ventana.aviso.mostrar(f"⚙  Instalando Aurora {version}…")
        a.instalar(ruta, instalado)

    ventana.aviso.mostrar(f"⬇  Descargando Aurora {version}…")
    a.descargar(release, progreso, descargado)
