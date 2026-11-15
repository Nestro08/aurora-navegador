"""Importar desde Chrome, Chromium, Brave, Edge o Vivaldi: accesos, historial, contraseñas, buscador y cookies.

Se leen los archivos del perfil del otro navegador (copiados antes a una carpeta temporal, porque el
navegador puede tenerlos abiertos). Las contraseñas y cookies vienen cifradas:
  • Linux: AES-128-CBC. Prefijo «v11» = clave del llavero del sistema («Chrome Safe Storage»);
    «v10» = clave fija «peanuts» (cuando el navegador no tenía llavero).
  • Windows: AES-256-GCM con una clave protegida por DPAPI en «Local State». Las «v20» (cifrado ligado a la
    aplicación, Chrome 127+) solo las puede leer el propio Chrome: para esas, exporta un CSV.
Desde el esquema 24 de cookies, el valor descifrado empieza por el SHA-256 del dominio (32 bytes), que se quita.
"""
import hashlib
import shutil
import sqlite3
import tempfile
from datetime import timedelta, timezone

from PyQt6.QtCore import QDateTime
from PyQt6.QtNetwork import QNetworkCookie

from .contrasenas import *  # noqa: F401,F403
from .contrasenas import _dpapi

NAVEGADORES_LINUX = [("Google Chrome", "google-chrome", "Chrome"), ("Chromium", "chromium", "Chromium"),
                     ("Brave", "BraveSoftware/Brave-Browser", "Brave"), ("Microsoft Edge", "microsoft-edge",
                                                                         "Microsoft Edge"),
                     ("Vivaldi", "vivaldi", "Vivaldi")]
NAVEGADORES_WINDOWS = [("Google Chrome", r"Google\Chrome\User Data"), ("Chromium", r"Chromium\User Data"),
                       ("Brave", r"BraveSoftware\Brave-Browser\User Data"), ("Microsoft Edge", r"Microsoft\Edge\User Data"),
                       ("Vivaldi", r"Vivaldi\User Data")]
EPOCA_WEBKIT = datetime(1601, 1, 1)


def fecha_webkit(microsegundos):
    """Chrome guarda las fechas en microsegundos desde 1601 (UTC)."""
    try:
        return EPOCA_WEBKIT + timedelta(microseconds=int(microsegundos)) if microsegundos else None
    except (OverflowError, ValueError):
        return None


class PerfilNavegador:
    """Un perfil de un navegador basado en Chromium instalado en este PC."""

    def __init__(self, navegador, base, carpeta, nombre, llavero=""):
        self.navegador, self.base, self.carpeta, self.nombre, self.llavero = navegador, Path(base), carpeta, nombre, llavero

    @property
    def ruta(self):
        return self.base / self.carpeta

    def __str__(self):
        return self.navegador if self.nombre in ("", "Persona 1", "Person 1") else f"{self.navegador} · {self.nombre}"

    def abierto(self):
        """True si el navegador parece estar en marcha (sus datos más recientes aún no están en disco)."""
        if sys.platform == "win32":
            return (self.ruta / "LOCK").exists() and not _se_puede_abrir(self.ruta / "History")
        return (self.base / "SingletonLock").is_symlink()


def _se_puede_abrir(ruta):
    try:
        with open(ruta, "rb"):
            return True
    except OSError:
        return False


def detectar():
    """Lista los perfiles de navegadores Chromium instalados."""
    if sys.platform == "win32":
        raiz = Path(os.environ.get("LOCALAPPDATA", ""))
        candidatos = [(n, raiz / r, "") for n, r in NAVEGADORES_WINDOWS]
    else:
        raiz = Path.home() / ".config"
        candidatos = [(n, raiz / r, ll) for n, r, ll in NAVEGADORES_LINUX]
    perfiles = []
    for navegador, base, llavero in candidatos:
        try:
            estado = json.loads((base / "Local State").read_text(encoding="utf-8"))
            info = estado.get("profile", {}).get("info_cache", {})
        except (OSError, ValueError):
            info = {}
        carpetas = list(info) or (["Default"] if (base / "Default").is_dir() else [])
        for carpeta in carpetas:
            if (base / carpeta / "Preferences").exists():
                perfiles.append(PerfilNavegador(navegador, base, carpeta, info.get(carpeta, {}).get("name", ""),
                                                llavero))
    return perfiles


# ─────────────────────────────── descifrado

def _clave_llavero_linux(nombre):
    """El secreto «<Navegador> Safe Storage» del llavero (GNOME Keyring o KWallet vía Secret Service)."""
    try:
        import secretstorage
        conexion = secretstorage.dbus_init()
        coleccion = secretstorage.get_default_collection(conexion)
        if coleccion.is_locked():
            coleccion.unlock()
        for item in coleccion.get_all_items():
            if item.get_label() == f"{nombre} Safe Storage":
                return item.get_secret()
    except Exception:
        pass
    return None


class Descifrador:
    def __init__(self, perfil, secreto_linux=None):
        self.perfil = perfil
        self._claves = {}
        self._secreto = secreto_linux  # para los tests; si no, se pide al llavero la primera vez que hace falta

    def _linux(self, version):
        if version not in self._claves:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            if version == b"v10":
                secreto = b"peanuts"
            else:
                if self._secreto is None:
                    self._secreto = _clave_llavero_linux(self.perfil.llavero) or b""
                secreto = self._secreto
            self._claves[version] = PBKDF2HMAC(hashes.SHA1(), 16, b"saltysalt", 1).derive(secreto) if secreto else None
        return self._claves[version]

    def _windows(self):
        if "win" not in self._claves:
            estado = json.loads((self.perfil.base / "Local State").read_text(encoding="utf-8"))
            cifrada = base64.b64decode(estado["os_crypt"]["encrypted_key"])
            self._claves["win"] = _dpapi(cifrada[5:], False)  # quita el prefijo «DPAPI»
        return self._claves["win"]

    def descifrar(self, valor):
        """bytes cifrados → bytes en claro. Lanza ValueError si no se puede."""
        if not valor:
            return b""
        version, cuerpo = bytes(valor[:3]), bytes(valor[3:])
        if sys.platform == "win32":
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            if version == b"v20":
                raise ValueError("cifrado ligado a Chrome (v20)")
            if version != b"v10":
                return _dpapi(bytes(valor), False)  # formato antiguo
            return AESGCM(self._windows()).decrypt(cuerpo[:12], cuerpo[12:], None)
        if version not in (b"v10", b"v11"):
            raise ValueError(f"formato desconocido {version!r}")
        clave = self._linux(version)
        if clave is None:
            raise ValueError("no encuentro la clave del navegador en el llavero")
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.padding import PKCS7
        d = Cipher(algorithms.AES(clave), modes.CBC(b" " * 16)).decryptor()
        relleno = d.update(cuerpo) + d.finalize()
        quitar = PKCS7(128).unpadder()
        try:
            return quitar.update(relleno) + quitar.finalize()
        except ValueError:
            raise ValueError("clave incorrecta")


# ─────────────────────────────── lectura

class Importador:
    def __init__(self, perfil, secreto_linux=None):
        self.perfil = perfil
        self.descifrador = Descifrador(perfil, secreto_linux)
        self._tmp = Path(tempfile.mkdtemp(prefix="aurora-importar-"))
        if os.name == "posix":
            os.chmod(self._tmp, 0o700)

    def cerrar(self):
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _bd(self, *nombres):
        """Copia una base de datos SQLite (con su diario) y la abre. None si no existe."""
        for nombre in nombres:
            origen = self.perfil.ruta / nombre
            if origen.exists():
                destino = self._tmp / nombre.replace("/", "_")
                for sufijo in ("", "-wal", "-journal"):
                    if Path(str(origen) + sufijo).exists():
                        shutil.copyfile(str(origen) + sufijo, str(destino) + sufijo)
                return sqlite3.connect(destino)
        return None

    def marcadores(self):
        try:
            datos = json.loads((self.perfil.ruta / "Bookmarks").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        res = []

        def recorrer(nodo):
            if nodo.get("type") == "url" and nodo.get("url", "").startswith(("http://", "https://")):
                fecha = fecha_webkit(nodo.get("date_added"))
                res.append({"url": nodo["url"], "titulo": nodo.get("name") or nodo["url"],
                            "ts": fecha.timestamp() if fecha else 0})
            for hijo in nodo.get("children", []):
                recorrer(hijo)

        for raiz in ("bookmark_bar", "other", "synced"):
            recorrer(datos.get("roots", {}).get(raiz, {}))
        return res

    def historial(self, limite=5000):
        bd = self._bd("History")
        if not bd:
            return []
        try:
            filas = bd.execute("SELECT url, title, last_visit_time FROM urls WHERE hidden = 0 "
                               "ORDER BY last_visit_time DESC LIMIT ?", (limite,)).fetchall()
        finally:
            bd.close()
        res = []
        for url, titulo, visita in filas:
            fecha = fecha_webkit(visita)
            if url.startswith(("http://", "https://")) and fecha:
                local = fecha.replace(tzinfo=timezone.utc).astimezone()
                res.append({"url": url, "titulo": titulo or "", "fecha": local.strftime("%d/%m/%Y %H:%M")})
        return res

    def contrasenas(self):
        """→ (cuentas, nunca, fallos): cuentas = [(origen, usuario, clave)], nunca = [origen]."""
        cuentas, nunca, fallos = {}, set(), 0
        for nombre in ("Login Data", "Login Data For Account"):
            bd = self._bd(nombre)
            if not bd:
                continue
            try:
                filas = bd.execute("SELECT origin_url, username_value, password_value, blacklisted_by_user "
                                   "FROM logins").fetchall()
            finally:
                bd.close()
            for url, usuario, valor, bloqueado in filas:
                if not url.startswith(("http://", "https://")):
                    continue  # android://, chrome://…
                origen = Contrasenas.origen(url)
                if bloqueado:
                    nunca.add(origen)
                    continue
                try:
                    clave = self.descifrador.descifrar(valor).decode("utf-8")
                except (ValueError, UnicodeDecodeError, OSError):
                    fallos += 1
                    continue
                if clave:
                    cuentas[(origen, usuario or "")] = clave
        return [(o, u, c) for (o, u), c in cuentas.items()], sorted(nunca), fallos

    def buscador(self):
        try:
            prefs = json.loads((self.perfil.ruta / "Preferences").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        datos = prefs.get("default_search_provider_data", {}).get("template_url_data", {})
        texto = " ".join(str(datos.get(k, "")) for k in ("keyword", "short_name", "url")).lower()
        if not texto.strip():
            return "Google"  # sin elegir: Chrome usa Google
        for nombre in BUSCADORES:
            if nombre.lower().replace(" ", "") in texto.replace(" ", ""):
                return nombre
        return None

    def cookies(self):
        """→ (cookies, fallos): cookies = lista de QNetworkCookie listas para el almacén de Aurora."""
        bd = self._bd("Network/Cookies", "Cookies")
        if not bd:
            return [], 0
        try:
            fila = bd.execute("SELECT value FROM meta WHERE key = 'version'").fetchone()
            version = int(fila[0]) if fila else 0
            filas = bd.execute("SELECT host_key, name, value, encrypted_value, path, expires_utc, is_secure, "
                               "is_httponly, samesite, has_expires FROM cookies").fetchall()
        finally:
            bd.close()
        ahora = datetime.now(timezone.utc).replace(tzinfo=None)
        res, fallos = [], 0
        politicas = {0: QNetworkCookie.SameSite.None_, 1: QNetworkCookie.SameSite.Lax,
                     2: QNetworkCookie.SameSite.Strict}
        for host, nombre, valor, cifrado, ruta, expira, seguro, solo_http, samesite, tiene_fin in filas:
            fin = fecha_webkit(expira) if tiene_fin else None
            if fin and fin < ahora:
                continue
            if cifrado:
                try:
                    plano = self.descifrador.descifrar(cifrado)
                except (ValueError, OSError):
                    fallos += 1
                    continue
                if version >= 24 and plano[:32] == hashlib.sha256(host.encode()).digest():
                    plano = plano[32:]
                valor = plano
            else:
                valor = (valor or "").encode()
            c = QNetworkCookie(nombre.encode(), bytes(valor))
            c.setDomain(host)
            c.setPath(ruta or "/")
            c.setSecure(bool(seguro))
            c.setHttpOnly(bool(solo_http))
            if samesite in politicas:
                c.setSameSitePolicy(politicas[samesite])
            if fin:
                c.setExpirationDate(QDateTime.fromSecsSinceEpoch(int(fin.replace(tzinfo=timezone.utc).timestamp())))
            res.append(c)
        return res, fallos


# ─────────────────────────────── aplicar en Aurora

def importar(perfil_aurora, perfil_nav, opciones, secreto_linux=None):
    """Importa en un perfil de Aurora. opciones ⊆ {marcadores, historial, contrasenas, buscador, cookies}.

    Devuelve una lista de líneas para el resumen."""
    imp = Importador(perfil_nav, secreto_linux)
    resumen = []
    try:
        if "marcadores" in opciones:
            existentes, nuevos = {m["url"] for m in perfil_aurora.marcadores.datos}, []
            for m in imp.marcadores():
                if m["url"] not in existentes:
                    existentes.add(m["url"])
                    nuevos.append(m)
            perfil_aurora.marcadores.datos.extend(nuevos)
            perfil_aurora.marcadores.guardar()
            resumen.append(f"★  {len(nuevos)} accesos")
        if "historial" in opciones:
            vistos, mezcla_h = set(), []
            for h in perfil_aurora.historial.datos + imp.historial():
                if (h["url"], h.get("fecha")) not in vistos:
                    vistos.add((h["url"], h.get("fecha")))
                    mezcla_h.append(h)

            def orden(h):
                try:
                    return datetime.strptime(h.get("fecha", ""), "%d/%m/%Y %H:%M")
                except ValueError:
                    return datetime.min
            mezcla_h.sort(key=orden, reverse=True)
            antes = len(perfil_aurora.historial.datos)
            perfil_aurora.historial.datos[:] = mezcla_h[:5000]
            perfil_aurora.historial.guardar()
            resumen.append(f"🕘  {max(0, len(perfil_aurora.historial.datos) - antes)} entradas de historial")
        if "contrasenas" in opciones:
            claves = perfil_aurora.claves
            cuentas, nunca, fallos = imp.contrasenas()
            nuevas = cambiadas = 0
            for origen, usuario, clave in cuentas:
                estado = claves.estado(origen, usuario, clave)
                if estado != "igual":
                    claves.guardar_cuenta(origen, usuario, clave, guardar=False)
                    nuevas += estado == "nueva"
                    cambiadas += estado == "cambiada"
            for origen in nunca:
                if origen not in claves.datos["nunca"]:
                    claves.datos["nunca"].append(origen)
            claves.guardar()
            linea = f"🔑  {nuevas} contraseñas nuevas" + (f", {cambiadas} actualizadas" if cambiadas else "")
            if fallos:
                linea += f" · ⚠ {fallos} no se pudieron descifrar"
            resumen.append(linea)
        if "buscador" in opciones:
            nombre = imp.buscador()
            if nombre:
                perfil_aurora.ajustes.datos["buscador"] = nombre
                perfil_aurora.ajustes.guardar()
                resumen.append(f"🔍  Buscador: {nombre}")
            else:
                resumen.append("🔍  El buscador de ese navegador no está en Aurora: no se ha cambiado")
        if "cookies" in opciones:
            cookies, fallos = imp.cookies()
            almacen = perfil_aurora.web.cookieStore()
            for c in cookies:
                almacen.setCookie(c)
            linea = f"🍪  {len(cookies)} cookies (sesiones iniciadas)"
            if fallos:
                linea += f" · ⚠ {fallos} no se pudieron descifrar"
            resumen.append(linea)
    finally:
        imp.cerrar()
    return resumen


class DialogoImportar(QDialog):
    OPCIONES = [("marcadores", "Marcadores", "Pasan a tus accesos."),
                ("historial", "Historial", "Las últimas 5.000 visitas."),
                ("contrasenas", "Contraseñas", "Se descifran con la clave del navegador y se cifran con la de Aurora."),
                ("buscador", "Buscador predeterminado", ""),
                ("cookies", "Sesiones iniciadas (cookies)",
                 "Para seguir dentro en tus webs. Google suele pedir iniciar sesión otra vez.")]

    def __init__(self, ventana):
        super().__init__(ventana)
        self.v = ventana
        self.setWindowTitle("Importar desde otro navegador")
        self.setMinimumWidth(520)
        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 20)
        l.setSpacing(10)
        l.addWidget(QLabel("Importar desde otro navegador", objectName="tituloPregunta"))
        self.perfiles = detectar()
        self.origen = QComboBox()
        self.origen.addItems([str(p) for p in self.perfiles] or ["No encuentro Chrome, Chromium, Brave, Edge ni Vivaldi"])
        self.origen.setEnabled(bool(self.perfiles))
        self.origen.currentIndexChanged.connect(self._revisar)
        l.addWidget(self.origen)
        self.casillas = {}
        for clave, texto, ayuda in self.OPCIONES:
            c = QCheckBox(texto)
            c.setChecked(True)
            c.setEnabled(bool(self.perfiles))
            self.casillas[clave] = c
            l.addWidget(c)
            if ayuda:
                a = QLabel(ayuda, objectName="tenue")
                a.setWordWrap(True)
                a.setContentsMargins(28, 0, 0, 4)
                l.addWidget(a)
        self.aviso = QLabel("", objectName="error")
        self.aviso.setWordWrap(True)
        l.addWidget(self.aviso)
        self.b_importar = QPushButton("Importar", objectName="primario")
        self.b_importar.setEnabled(bool(self.perfiles))
        self.b_importar.clicked.connect(self._importar)
        cerrar = QPushButton("Cerrar")
        cerrar.clicked.connect(self.reject)
        fila = QHBoxLayout()
        fila.addStretch()
        fila.addWidget(cerrar)
        fila.addWidget(self.b_importar)
        l.addLayout(fila)
        self._revisar()

    def _revisar(self):
        p = self.perfiles[self.origen.currentIndex()] if self.perfiles else None
        self.aviso.setText(f"⚠ {p.navegador} está abierto: ciérralo del todo para importar lo más reciente."
                           if p and p.abierto() else "")

    def _importar(self):
        p = self.perfiles[self.origen.currentIndex()]
        opciones = {k for k, c in self.casillas.items() if c.isChecked()}
        if not opciones:
            return
        if "contrasenas" in opciones and not self.v.p.verificador.comprobar(self, "importar contraseñas"):
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            resumen = importar(self.v.p, p, opciones)
        except Exception as e:
            resumen = [f"⚠ No se pudo importar: {e}"]
        finally:
            QApplication.restoreOverrideCursor()
        for ventana in self.v.p.ventanas:
            ventana.generar_nueva()
            ventana.recargar_nuevas()
            ventana._estrella()
            ventana._llave()
        QMessageBox.information(self, "Importación terminada", f"Desde {p}:\n\n" + "\n".join(resumen))
        self.accept()
