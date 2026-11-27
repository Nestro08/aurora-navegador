"""Perfiles (Personal, Uni…), modo incógnito y gestor de ventanas."""
from .seguridad import *  # noqa: F401,F403
from .sincronizacion import *  # noqa: F401,F403
from .extensiones import *  # noqa: F401,F403
from PyQt6.QtNetwork import QNetworkCookie

from .motor import Bloqueador
from .permisos import presentar_notificacion

def identidad(perfil_web):
    """User-Agent y pistas de cliente (Sec-CH-UA) de Aurora: Chromium del motor + «Aurora»."""
    from . import __version__
    ua = re.sub(r" QtWebEngine/\S+", "", perfil_web.httpUserAgent())
    ua = re.sub(r" Aurora/\S+", "", ua) + f" Aurora/{__version__}"
    if hasattr(perfil_web, "clientHints"):  # Qt 6.8 o más nuevo: la marca también en navigator.userAgentData
        pistas = perfil_web.clientHints()
        marcas = {k: v for k, v in dict(pistas.fullVersionList()).items() if k != "QtWebEngine"}
        marcas["Aurora"] = ".".join((__version__ + ".0.0.0").split(".")[:4])
        pistas.setFullVersionList(marcas)
    return ua


COLORES_PERFIL = ["#7c5cff", "#22c55e", "#f97316", "#ec4899", "#06b6d4", "#f59e0b", "#ef4444", "#14b8a6"]


class Perfil(QObject):
    """Todo lo que comparten las ventanas de un mismo perfil."""

    def __init__(self, nombre, carpeta, color, incognito=False, base=None):
        super().__init__()
        self.nombre, self.color, self.incognito, self.base = nombre, color, incognito, base
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)
        self.ventanas = []
        if incognito:
            self.ajustes, self.marcadores, self.claves = base.ajustes, base.marcadores, base.claves
            self.historial, self.lista_descargas = AlmacenMemoria([]), AlmacenMemoria([])
            self.verificador, self.sync = base.verificador, None
            self.permisos = AlmacenMemoria({})  # lo que permitas en incógnito se olvida al cerrarlo
            self.web = QWebEngineProfile(QApplication.instance())  # sin nombre: no se guarda nada en disco
        else:
            self.ajustes = Almacen("ajustes", dict(AJUSTES_DEFECTO), self.carpeta)
            for clave, valor in AJUSTES_DEFECTO.items():
                self.ajustes.datos.setdefault(clave, valor)
            self.marcadores = Almacen("marcadores", [], self.carpeta)
            self.historial = Almacen("historial", [], self.carpeta)
            # entradas sueltas que no tengan la forma esperada no deben romper la interfaz
            self.marcadores.datos[:] = [m for m in self.marcadores.datos if es_marcador(m)]
            self.historial.datos[:] = [h for h in self.historial.datos if es_visita(h)]
            self.claves = Contrasenas(self.carpeta)
            self.lista_descargas = Almacen("descargas", [], self.carpeta)
            self.permisos = Almacen("permisos", {}, self.carpeta)  # {origen: {tipo: permitido}}
            self.verificador = Verificador(self.ajustes)
            nombre_web = NOMBRE if self.carpeta == DATOS else f"{NOMBRE}-{self.carpeta.name}"
            self.web = QWebEngineProfile(nombre_web, QApplication.instance())
            self.web.setPersistentStoragePath(str(self.carpeta / "perfil"))
            self.web.setCachePath(str(self.carpeta / "cache"))
            self.web.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
            self.sync = Sincronizador(self)
            self.claves.al_borrar = lambda k: self.sync.borrado("claves", k)
        self._configurar_web()
        self.favicons = favicons()

    def _configurar_web(self):
        a = self.ajustes.datos
        # Identidad propia, como hacen los navegadores basados en Chromium (Edge añade «Edg/…», Vivaldi «Vivaldi/…»):
        # el token Chrome/… del motor y, al final, «Aurora/x.y». Sin «QtWebEngine/…», que hace que muchas webs traten
        # a Aurora como una aplicación incrustada y no como un navegador.
        self.ua_original = identidad(self.web)
        self.web.setHttpUserAgent(self.ua_original)
        if UAS.get(a.get("ua")):
            self.web.setHttpUserAgent(UAS[a["ua"]])
        A = QWebEngineSettings.WebAttribute
        s = self.web.settings()
        for atributo in (A.FullScreenSupportEnabled, A.PluginsEnabled, A.PdfViewerEnabled,
                         A.ScrollAnimatorEnabled, A.ScreenCaptureEnabled, A.PlaybackRequiresUserGesture):
            s.setAttribute(atributo, atributo != A.PlaybackRequiresUserGesture)
        s.setFontSize(QWebEngineSettings.FontSize.DefaultFontSize, TAMANOS.get(a["tam_fuente"], 16))
        self.bloqueador = Bloqueador(self._peticion)
        self.bloqueador.activo, self.bloqueador.dnt = a["bloqueo"], a["dnt"]
        self.bloqueador.ampliado = a.get("bloqueo_ampliado", True)
        self.web.setUrlRequestInterceptor(self.bloqueador)
        self.web.cookieStore().setCookieFilter(
            lambda peticion: not (self.ajustes.datos.get("cookies_terceros") and peticion.thirdParty))
        script = QWebEngineScript()
        script.setName("aurora-contrasenas")
        script.setSourceCode(JS_CAPTURA)
        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        script.setWorldId(MUNDO_AURORA)
        script.setRunsOnSubFrames(False)
        self.web.scripts().insert(script)
        self.web.downloadRequested.connect(self._descarga)
        # registro de cookies para poder borrar las de un sitio (Qt no deja preguntar por ellas)
        self.cookies = {}
        tienda = self.web.cookieStore()
        tienda.cookieAdded.connect(self._cookie_anadida)
        tienda.cookieRemoved.connect(self._cookie_quitada)
        tienda.loadAllCookies()
        self.web.setNotificationPresenter(presentar_notificacion)
        if hasattr(self.web, "setPersistentPermissionsPolicy"):  # incógnito: solo en memoria
            P = QWebEngineProfile.PersistentPermissionsPolicy
            self.web.setPersistentPermissionsPolicy(P.StoreInMemory if self.incognito else P.StoreOnDisk)
        extensiones().aplicar(self.web)

    @staticmethod
    def _clave_cookie(c):
        return bytes(c.name()), c.domain().lower(), c.path()

    def _cookie_anadida(self, c):
        c = QNetworkCookie(c)  # la que llega es temporal
        self.cookies[self._clave_cookie(c)] = c

    def _cookie_quitada(self, c):
        self.cookies.pop(self._clave_cookie(QNetworkCookie(c)), None)

    def cookies_de(self, host):
        """Cookies del sitio: las del propio host, las de sus subdominios y las de sus dominios padre."""
        host = host.lower()
        res = []
        for c in self.cookies.values():
            dominio = c.domain().lstrip(".").lower()
            if dominio and (host == dominio or host.endswith("." + dominio) or dominio.endswith("." + host)):
                res.append(c)
        return res

    def _peticion(self, *datos):
        for v in self.ventanas:
            v.registrar_peticion(*datos)

    def ventana_activa(self):
        activa = QApplication.activeWindow()
        if activa in self.ventanas:
            return activa
        return self.ventanas[-1] if self.ventanas else None

    def _descarga(self, d):
        v = self.ventana_activa()
        if v:
            v.descargar(d)
        else:
            d.cancel()

    def marcar_borrado_marcador(self, url):
        if self.sync:
            self.sync.borrado("marcadores", url)
        elif self.base and self.base.sync:
            self.base.sync.borrado("marcadores", url)


class Gestor(QObject):
    """Crea perfiles y ventanas. Hay uno solo para toda la aplicación."""

    def __init__(self):
        super().__init__()
        self.lista = Almacen("perfiles", [{"nombre": "Personal", "color": COLORES_PERFIL[0], "carpeta": ""}])
        self.perfiles, self.incognitos = {}, {}

    def info(self, nombre):
        return next((p for p in self.lista.datos if p["nombre"] == nombre), self.lista.datos[0])

    def perfil(self, nombre=None):
        info = self.info(nombre or self.lista.datos[0]["nombre"])
        if info["nombre"] not in self.perfiles:
            carpeta = DATOS / "perfiles" / info["carpeta"] if info["carpeta"] else DATOS
            self.perfiles[info["nombre"]] = Perfil(info["nombre"], carpeta, info["color"])
        return self.perfiles[info["nombre"]]

    def incognito(self, nombre=None):
        base = self.perfil(nombre)
        if base.nombre not in self.incognitos or not self.incognitos[base.nombre].ventanas:
            self.incognitos[base.nombre] = Perfil(base.nombre, base.carpeta, base.color, incognito=True, base=base)
        return self.incognitos[base.nombre]

    def nueva_ventana(self, nombre=None, incognito=False, urls=None, restaurar=True, mostrar=True):
        from .ventana import Ventana
        perfil = self.incognito(nombre) if incognito else self.perfil(nombre)
        primera = not perfil.ventanas
        v = Ventana(perfil, urls=urls, restaurar=restaurar and primera and not incognito)
        if mostrar:
            v.show()
        return v

    def todas_las_ventanas(self):
        return [v for p in list(self.perfiles.values()) + list(self.incognitos.values()) for v in p.ventanas]

    def ventana_activa(self):
        activa = QApplication.activeWindow()
        todas = self.todas_las_ventanas()
        if activa in todas:
            return activa
        return todas[-1] if todas else None

    def crear_perfil(self, nombre):
        nombre = nombre.strip()
        if not nombre or any(p["nombre"].lower() == nombre.lower() for p in self.lista.datos):
            return None
        usados = {p["carpeta"] for p in self.lista.datos}
        carpeta, n = slug(nombre), 2
        while carpeta in usados or (DATOS / "perfiles" / carpeta).exists():
            carpeta, n = f"{slug(nombre)}-{n}", n + 1
        color = COLORES_PERFIL[len(self.lista.datos) % len(COLORES_PERFIL)]
        self.lista.datos.append({"nombre": nombre, "color": color, "carpeta": carpeta})
        self.lista.guardar()
        return nombre

    def renombrar(self, viejo, nuevo):
        nuevo = nuevo.strip()
        if not nuevo or any(p["nombre"].lower() == nuevo.lower() for p in self.lista.datos):
            return False
        self.info(viejo)["nombre"] = nuevo
        self.lista.guardar()
        if viejo in self.perfiles:
            p = self.perfiles.pop(viejo)
            p.nombre = nuevo
            self.perfiles[nuevo] = p
            for v in p.ventanas:
                v.actualizar_perfil()
        return True

    def cambiar_color(self, nombre, color):
        self.info(nombre)["color"] = color
        self.lista.guardar()
        if nombre in self.perfiles:
            self.perfiles[nombre].color = color
            for v in self.perfiles[nombre].ventanas:
                v.actualizar_perfil()

    def borrar_perfil(self, nombre):
        info = self.info(nombre)
        if not info["carpeta"] or (nombre in self.perfiles and self.perfiles[nombre].ventanas):
            return False
        self.lista.datos.remove(info)
        self.lista.guardar()
        self.perfiles.pop(nombre, None)
        import shutil
        shutil.rmtree(DATOS / "perfiles" / info["carpeta"], ignore_errors=True)
        return True


_GESTOR = None


def gestor():
    global _GESTOR
    if _GESTOR is None:
        _GESTOR = Gestor()
    return _GESTOR
