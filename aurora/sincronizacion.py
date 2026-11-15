"""Sincronización entre dispositivos a través de una carpeta compartida.

Cada dispositivo escribe su propio archivo (Aurora-Sync/<perfil>/<dispositivo>.json) en una carpeta que
sincroniza otro programa (OneDrive, Dropbox, Google Drive, Syncthing…). Al sincronizar, Aurora lee los
archivos de los demás dispositivos y mezcla accesos, historial y contraseñas. Las contraseñas viajan
cifradas con una frase de paso (AES de la librería `cryptography`), nunca en claro.
"""
import hashlib
import secrets
import socket
import time

from .contrasenas import *  # noqa: F401,F403

try:
    from cryptography.fernet import Fernet, InvalidToken
    HAY_CRYPTO = True
except ImportError:  # sin la librería se sincroniza todo menos las contraseñas
    HAY_CRYPTO = False


def slug(texto):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", texto.strip().lower()).strip("-")
    return s or "perfil"


def _fecha(h):
    try:
        return datetime.strptime(h.get("fecha", ""), "%d/%m/%Y %H:%M")
    except ValueError:
        return datetime.min


class Sincronizador(QObject):
    terminado = pyqtSignal(bool, str)

    def __init__(self, perfil):
        super().__init__()
        self.p = perfil
        self.estado = Almacen("sync_estado", {"borrados_marcadores": {}, "borrados_claves": {}, "ultima": ""},
                              perfil.carpeta)
        self.reloj = QTimer(self, interval=10 * 60 * 1000)
        self.reloj.timeout.connect(lambda: self.sincronizar(silencioso=True))
        self.reloj.start()

    @property
    def a(self):
        return self.p.ajustes.datos

    def configurado(self):
        return bool(self.a.get("sync_activa") and self.a.get("sync_carpeta"))

    def dispositivo(self):
        return slug(self.a.get("sync_dispositivo") or socket.gethostname())

    def carpeta(self):
        return Path(self.a["sync_carpeta"]) / "Aurora-Sync" / slug(self.p.nombre)

    def borrado(self, tipo, clave):
        self.estado.datos[f"borrados_{tipo}"][clave] = time.time()
        self.estado.guardar()

    def _fernet(self, carpeta):
        if not (HAY_CRYPTO and self.a.get("sync_frase")):
            return None
        try:
            frase = descifrar(self.a["sync_frase"])
        except Exception:
            return None
        archivo_sal = carpeta / "sal.bin"
        if not archivo_sal.exists():
            archivo_sal.write_bytes(secrets.token_bytes(16))
        clave = hashlib.pbkdf2_hmac("sha256", frase.encode("utf-8"), archivo_sal.read_bytes(), 300_000)
        return Fernet(base64.urlsafe_b64encode(clave))

    def sincronizar(self, silencioso=False):
        if not self.configurado() or self.p.incognito:
            return
        try:
            mensaje = self._sincronizar()
            self.estado.datos["ultima"] = datetime.now().strftime("%d/%m/%Y %H:%M")
            self.estado.guardar()
            if not silencioso:
                self.terminado.emit(True, mensaje)
        except Exception as e:
            self.terminado.emit(False, f"No se pudo sincronizar: {e}")

    def _sincronizar(self):
        carpeta = self.carpeta()
        carpeta.mkdir(parents=True, exist_ok=True)
        yo = self.dispositivo()
        fernet = self._fernet(carpeta)
        otros = []
        for archivo in carpeta.glob("*.json"):
            if archivo.stem != yo:
                try:
                    otros.append(json.loads(archivo.read_text(encoding="utf-8")))
                except (OSError, ValueError):
                    pass

        # 1. borrados (lápidas): gana el más reciente de todos los dispositivos
        for tipo in ("marcadores", "claves"):
            b = self.estado.datos[f"borrados_{tipo}"]
            for o in otros:
                for k, ts in o.get("borrados", {}).get(tipo, {}).items():
                    b[k] = max(ts, b.get(k, 0))
        borr_m, borr_c = self.estado.datos["borrados_marcadores"], self.estado.datos["borrados_claves"]

        # 2. accesos: por URL, gana la edición más reciente
        locales = {m["url"]: m for m in self.p.marcadores.datos}
        orden = [m["url"] for m in self.p.marcadores.datos]
        for o in otros:
            for m in o.get("marcadores", []):
                actual = locales.get(m["url"])
                if actual is None:
                    orden.append(m["url"])
                if actual is None or m.get("ts", 0) > actual.get("ts", 0):
                    locales[m["url"]] = {"url": m["url"], "titulo": m.get("titulo", m["url"]), "ts": m.get("ts", 0)}
        self.p.marcadores.datos = [locales[u] for u in orden
                                   if u in locales and borr_m.get(u, 0) <= locales[u].get("ts", 0)]
        self.p.marcadores.guardar()

        # 3. historial: unión sin duplicados, de más nuevo a más viejo
        vistos, historial = set(), []
        for h in self.p.historial.datos + [h for o in otros for h in o.get("historial", [])]:
            clave = (h.get("url"), h.get("fecha"))
            if clave not in vistos:
                vistos.add(clave)
                historial.append(h)
        historial.sort(key=_fecha, reverse=True)
        self.p.historial.datos[:] = historial[:5000]
        self.p.historial.guardar()

        # 4. contraseñas (solo si hay frase de paso y cryptography)
        n_claves = 0
        if fernet:
            for o in otros:
                for c in o.get("claves", []):
                    k = c["origen"] + "\n" + c["usuario"]
                    if borr_c.get(k, 0) >= c.get("ts", 0):
                        continue
                    local = next((x for x in self.p.claves.de(c["origen"]) if x["usuario"] == c["usuario"]), None)
                    if local is None or c.get("ts", 0) > local.get("ts", 0):
                        try:
                            plano = fernet.decrypt(c["clave"].encode()).decode()
                        except InvalidToken:
                            raise RuntimeError("la frase de paso no coincide con la de tus otros dispositivos")
                        self.p.claves.guardar_cuenta(c["origen"], c["usuario"], plano, ts=c.get("ts"), guardar=False)
                        n_claves += 1
            self.p.claves.datos["cuentas"] = [
                c for c in self.p.claves.datos["cuentas"]
                if borr_c.get(c["origen"] + "\n" + c["usuario"], 0) < c.get("ts", 0)]
            self.p.claves.guardar()

        # 5. escribir mi archivo con el resultado de la mezcla
        mio = {
            "dispositivo": yo, "ts": time.time(), "version": 1,
            "marcadores": self.p.marcadores.datos, "historial": self.p.historial.datos[:3000],
            "borrados": {"marcadores": borr_m, "claves": borr_c},
            "claves": [{"origen": c["origen"], "usuario": c["usuario"], "ts": c.get("ts", 0),
                        "clave": fernet.encrypt(self.p.claves.clave(c).encode()).decode()}
                       for c in self.p.claves.datos["cuentas"]] if fernet else [],
        }
        temporal = carpeta / f"{yo}.tmp"
        temporal.write_text(json.dumps(mio, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, carpeta / f"{yo}.json")
        self.estado.guardar()
        for v in self.p.ventanas:
            v.generar_nueva()
        extra = f", {n_claves} contraseñas nuevas" if n_claves else ""
        return f"⇅  Sincronizado con {len(otros)} dispositivo(s){extra}"
