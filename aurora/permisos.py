"""Permisos de las webs (cámara, micrófono, ubicación, notificaciones, compartir pantalla…) y notificaciones.

Aurora pregunta con una tarjeta y guarda la respuesta por sitio en permisos.json del perfil (en incógnito, solo
en memoria). No basta con lo que recuerda QtWebEngine: cámara y micrófono los olvida al cerrar la página.
Compartir pantalla se pregunta siempre, como en Chrome. Todo se ve y se olvida en Ajustes → Privacidad.
"""
import shutil
import subprocess

from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403

try:
    from PyQt6.QtWebEngineCore import QWebEnginePermission
    TIPO = QWebEnginePermission.PermissionType
    ESTADO = QWebEnginePermission.State
except ImportError:  # Qt < 6.8: se usa la API antigua (featurePermissionRequested)
    QWebEnginePermission = TIPO = ESTADO = None

# nombre interno → (qué pide la web, nombre corto para la lista de Ajustes)
DESCRIPCIONES = {
    "MediaAudioCapture": ("usar tu micrófono", "Micrófono"),
    "MediaVideoCapture": ("usar tu cámara", "Cámara"),
    "MediaAudioVideoCapture": ("usar tu cámara y tu micrófono", "Cámara y micrófono"),
    "DesktopVideoCapture": ("ver tu pantalla", "Compartir pantalla"),
    "DesktopAudioVideoCapture": ("ver tu pantalla y oír su sonido", "Compartir pantalla y sonido"),
    "Notifications": ("enviarte notificaciones", "Notificaciones"),
    "Geolocation": ("saber dónde estás", "Ubicación"),
    "ClipboardReadWrite": ("leer y escribir tu portapapeles", "Portapapeles"),
    "LocalFontsAccess": ("ver las fuentes instaladas en tu PC", "Fuentes"),
}
SIN_PREGUNTAR = {"MouseLock"}  # juegos y visores 3D: Chromium lo concede sin preguntar (se sale con Esc)
SIEMPRE_PREGUNTAR = {"DesktopVideoCapture", "DesktopAudioVideoCapture"}  # ver tu pantalla: cada vez


def origen_de(url):
    """«https://meet.google.com» (con el puerto si no es el normal)."""
    url = QUrl(url)
    puerto = f":{url.port()}" if url.port() != -1 else ""
    return f"{url.scheme()}://{url.host()}{puerto}" if url.host() else url.toString()


def nombre_tipo(tipo):
    return getattr(tipo, "name", str(tipo))


def descripcion(tipo):
    return DESCRIPCIONES.get(nombre_tipo(tipo), ("usar una función de tu equipo", nombre_tipo(tipo)))


def permisos_guardados(perfil):
    """[(origen, tipo, permitido)] de lo que has respondido en este perfil, ordenado por sitio."""
    return sorted((origen, tipo, bool(valor)) for origen, tipos in perfil.permisos.datos.items()
                  if isinstance(tipos, dict) for tipo, valor in tipos.items())


def olvidar_permiso(perfil, origen, tipo):
    """Borra la respuesta guardada (también la que recuerda QtWebEngine): la próxima vez se pregunta."""
    tipos = perfil.permisos.datos.get(origen, {})
    tipos.pop(tipo, None)
    if not tipos:
        perfil.permisos.datos.pop(origen, None)
    perfil.permisos.guardar()
    if hasattr(perfil.web, "queryPermission") and hasattr(TIPO, tipo):
        perfil.web.queryPermission(QUrl(origen), getattr(TIPO, tipo)).reset()


# ─────────────────────────────── notificaciones de las webs

_BANDEJA = None


def _bandeja():
    """Icono en la bandeja de Windows para enseñar notificaciones del sistema."""
    global _BANDEJA
    from PyQt6.QtWidgets import QSystemTrayIcon
    if not QSystemTrayIcon.isSystemTrayAvailable() or not QSystemTrayIcon.supportsMessages():
        return None
    if _BANDEJA is None:
        _BANDEJA = QSystemTrayIcon(crear_icono_app(), QApplication.instance())
        _BANDEJA.setToolTip(NOMBRE)
        _BANDEJA.ocultar = QTimer(_BANDEJA, singleShot=True, interval=12000)
        _BANDEJA.ocultar.timeout.connect(_BANDEJA.hide)
    return _BANDEJA


def presentar_notificacion(n):
    """Muestra la notificación de una web como notificación del sistema (o, si no se puede, dentro de Aurora)."""
    origen = n.origin().host() or n.origin().toString()
    titulo = (n.title() or origen)[:120]
    texto = (n.message() or "")[:400]
    presentar_notificacion.vivas = getattr(presentar_notificacion, "vivas", [])[-20:] + [n]  # que no se borre

    def abrir():
        n.click()
        from .perfiles import gestor
        v = gestor().ventana_activa()
        if v:
            v.showNormal() if v.isMinimized() else v.show()
            v.raise_()
            v.activateWindow()

    if sys.platform.startswith("linux") and shutil.which("notify-send"):
        try:  # «--»: un título que empiece por «-» no puede colarse como opción
            subprocess.Popen(["notify-send", "-a", NOMBRE, "-i", "aurora", "--", titulo, f"{texto}\n{origen}".strip()],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            n.show()
            return
        except OSError:
            pass
    if sys.platform == "win32":
        b = _bandeja()
        if b:
            try:
                b.messageClicked.disconnect()
            except TypeError:
                pass
            b.messageClicked.connect(abrir)
            b.show()
            b.showMessage(titulo, f"{texto}\n{origen}".strip(), crear_icono_app(), 8000)
            b.ocultar.start()
            n.show()
            return
    from .perfiles import gestor
    v = gestor().ventana_activa()
    if v:
        v.aviso.mostrar(f"🔔  {titulo}" + (f" · {texto[:90]}" if texto else ""))
        n.show()


# ─────────────────────────────── en la ventana

class MixinPermisos:
    """Lo que la ventana hace cuando una web pide un permiso o compartir la pantalla."""

    def conectar_permisos(self, pagina):
        if hasattr(pagina, "permissionRequested"):
            pagina.permissionRequested.connect(lambda permiso, p=pagina: self.pedir_permiso(p, permiso))
        else:
            pagina.featurePermissionRequested.connect(
                lambda url, funcion, p=pagina: self._pedir_permiso_antiguo(p, url, funcion))
        if hasattr(pagina, "desktopMediaRequested"):
            pagina.desktopMediaRequested.connect(self.elegir_pantalla)

    def pedir_permiso(self, pagina, permiso):
        # el que llega es temporal (como las cookies de cookieAdded): usarlo después de la señal cuelga Aurora
        permiso = QWebEnginePermission(permiso)
        tipo = nombre_tipo(permiso.permissionType())
        if tipo in SIN_PREGUNTAR:
            permiso.grant()
            return
        if tipo == "Unsupported":
            permiso.deny()
            return
        self._preguntar(permiso.origin(), tipo, permiso.grant, permiso.deny)

    def _pedir_permiso_antiguo(self, pagina, url, funcion):
        P = QWebEnginePage.PermissionPolicy
        tipo = nombre_tipo(funcion)
        if tipo == "MouseLock":
            pagina.setFeaturePermission(url, funcion, P.PermissionGrantedByUser)
            return
        self._preguntar(url, tipo, lambda: pagina.setFeaturePermission(url, funcion, P.PermissionGrantedByUser),
                        lambda: pagina.setFeaturePermission(url, funcion, P.PermissionDeniedByUser))

    def _preguntar(self, url, tipo, permitir, bloquear):
        accion = descripcion(tipo)[0]
        origen = origen_de(url)
        sitio = QUrl(url).host() or origen
        recordar = tipo not in SIEMPRE_PREGUNTAR
        guardado = self.p.permisos.datos.get(origen, {}).get(tipo) if recordar else None
        if guardado is not None:  # ya respondiste en este sitio
            (permitir if guardado else bloquear)()
            return
        if not recordar:
            recuerda = "Te lo preguntará cada vez."
        elif self.incognito:
            recuerda = "Lo recordará hasta que cierres el incógnito."
        else:
            recuerda = "Aurora lo recordará para este sitio."

        def hecho(funcion, permitido, texto):
            funcion()
            if recordar:
                self.p.permisos.datos.setdefault(origen, {})[tipo] = permitido
                self.p.permisos.guardar()
            self.aviso.mostrar(texto)

        icono = {"Notifications": "info", "Geolocation": "inicio"}.get(tipo, "ojo")
        self.pregunta.mostrar(f"¿Permitir que {sitio} pueda {accion}?",
                              f"{recuerda} Puedes cambiarlo en Ajustes → Privacidad.",
                              [("Bloquear", lambda: hecho(bloquear, False, f"🚫  Bloqueado: {sitio} no puede {accion}"),
                                False),
                               ("Permitir", lambda: hecho(permitir, True, f"✓  {sitio} puede {accion}"), True)], icono)

    def elegir_pantalla(self, peticion):
        """La web quiere compartir pantalla (Meet, Teams, Discord…): elige qué pantalla o ventana."""
        pantallas, ventanas = peticion.screensModel(), peticion.windowsModel()
        opciones = []
        for modelo, icono, seleccionar in ((pantallas, "🖥", peticion.selectScreen),
                                           (ventanas, "🗔", peticion.selectWindow)):
            for fila in range(modelo.rowCount()):
                indice = modelo.index(fila, 0)
                nombre = modelo.data(indice, Qt.ItemDataRole.DisplayRole) or f"{fila + 1}"
                opciones.append((f"{icono}  {nombre}", seleccionar, indice))
        if not opciones:
            peticion.cancel()
            self.aviso.mostrar("No encuentro ninguna pantalla que compartir")
            return
        if len(opciones) == 1:  # p. ej. en Wayland, donde el propio sistema pregunta qué compartir
            opciones[0][1](opciones[0][2])
            return
        elegida, ok = QInputDialog.getItem(self, "Compartir pantalla", "¿Qué quieres compartir?",
                                           [o[0] for o in opciones], 0, False)
        if not ok:
            peticion.cancel()
            return
        for texto, seleccionar, indice in opciones:
            if texto == elegida:
                seleccionar(indice)
                return

