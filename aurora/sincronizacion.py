"""Sincronización entre dispositivos a través de una carpeta compartida.

Cada dispositivo escribe su propio archivo (Aurora-Sync/<perfil>/<dispositivo>.json) en una carpeta que
sincroniza otro programa (OneDrive, Dropbox, Google Drive, Syncthing…). Al sincronizar, Aurora lee los
archivos de los demás dispositivos y mezcla accesos, historial y contraseñas. Con una frase de paso, las
contraseñas y el historial viajan cifrados (AES de la librería `cryptography`), nunca en claro.

Cada dispositivo deriva su clave con su propia sal, que publica en su archivo («sal»), así que dos PCs que
empiezan a la vez no pueden acabar con sales distintas. Si existe el antiguo sal.bin compartido, se adopta
como sal propia para seguir entendiéndose con dispositivos que aún usan la versión 1.
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
        self._claves = {}  # (frase, sal) → Fernet: PBKDF2 es lento a propósito, no se repite en cada sync
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

    def _frase(self):
        if not (HAY_CRYPTO and self.a.get("sync_frase")):
            return None
        try:
            return descifrar(self.a["sync_frase"]) or None
        except Exception:
            return None

    def _mi_sal(self, carpeta):
        if not self.estado.datos.get("sal"):
            antigua = carpeta / "sal.bin"
            sal = antigua.read_bytes() if antigua.exists() else secrets.token_bytes(16)
            if not antigua.exists():  # para que los dispositivos con la versión 1 usen la misma
                antigua.write_bytes(sal)
            self.estado.datos["sal"] = base64.b64encode(sal).decode()
            self.estado.guardar()
        return base64.b64decode(self.estado.datos["sal"])

    def _fernet(self, frase, sal):
        if not (frase and sal):
            return None
        if (frase, sal) not in self._claves:
            clave = hashlib.pbkdf2_hmac("sha256", frase.encode("utf-8"), sal, 300_000)
            self._claves[(frase, sal)] = Fernet(base64.urlsafe_b64encode(clave))
        return self._claves[(frase, sal)]

    def _fernet_de(self, frase, carpeta, otro):
        """La clave con la que otro dispositivo cifró su archivo."""
        if otro.get("sal"):
            sal = base64.b64decode(otro["sal"])
        else:  # versión 1: sal compartida en sal.bin
            antigua = carpeta / "sal.bin"
            sal = antigua.read_bytes() if antigua.exists() else None
        return self._fernet(frase, sal)

    @staticmethod
    def _descifrar(fernet, token):
        if fernet is None:
            raise RuntimeError("otro dispositivo cifró sus datos con una frase de paso: ponla también aquí")
        try:
            return fernet.decrypt(token.encode()).decode("utf-8")
        except InvalidToken:
            raise RuntimeError("la frase de paso no coincide con la de tus otros dispositivos")

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
        frase = self._frase()
        sal = self._mi_sal(carpeta) if frase else None
        fernet = self._fernet(frase, sal)
        otros, falta_frase = [], False
        for archivo in carpeta.glob("*.json"):
            if archivo.stem != yo:
                try:
                    o = json.loads(archivo.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(o, dict):
                    o["_fernet"] = self._fernet_de(frase, carpeta, o) if frase else None
                    if "historial_c" in o and frase:
                        o["historial"] = json.loads(self._descifrar(o["_fernet"], o["historial_c"]))
                    elif "historial_c" in o or o.get("claves"):
                        falta_frase = True  # sin frase aquí no se puede leer lo que llega cifrado
                    otros.append(o)

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
                    for extra in ("color", "icono"):  # esferas personalizadas
                        if isinstance(m.get(extra), str) and m[extra]:
                            locales[m["url"]][extra] = m[extra][:7 if extra == "color" else 4]
                    pos = m.get("pos")
                    if isinstance(pos, dict) and all(isinstance(pos.get(k), (int, float)) for k in ("x", "y")):
                        locales[m["url"]]["pos"] = {k: max(0.0, min(1.0, float(pos[k]))) for k in ("x", "y")}
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
                for c in o.get("claves", []) if o["_fernet"] else []:
                    k = c["origen"] + "\n" + c["usuario"]
                    if borr_c.get(k, 0) >= c.get("ts", 0):
                        continue
                    local = next((x for x in self.p.claves.de(c["origen"]) if x["usuario"] == c["usuario"]), None)
                    if local is None or c.get("ts", 0) > local.get("ts", 0):
                        plano = self._descifrar(o["_fernet"], c["clave"])
                        self.p.claves.guardar_cuenta(c["origen"], c["usuario"], plano, ts=c.get("ts"), guardar=False)
                        n_claves += 1
            self.p.claves.datos["cuentas"] = [
                c for c in self.p.claves.datos["cuentas"]
                if borr_c.get(c["origen"] + "\n" + c["usuario"], 0) < c.get("ts", 0)]
            self.p.claves.guardar()

        # 5. escribir mi archivo con el resultado de la mezcla
        claves = []
        for c in self.p.claves.datos["cuentas"] if fernet else []:
            plano = self.p.claves.leer_clave(c)
            if plano is not None:  # nunca se envía como vacía una contraseña que no se pudo descifrar
                claves.append({"origen": c["origen"], "usuario": c["usuario"], "ts": c.get("ts", 0),
                               "clave": fernet.encrypt(plano.encode()).decode()})
        historial = self.p.historial.datos[:3000]
        mio = {
            "dispositivo": yo, "ts": time.time(), "version": 2,
            "marcadores": self.p.marcadores.datos,
            "borrados": {"marcadores": borr_m, "claves": borr_c},
            "claves": claves,
        }
        if fernet:
            mio["sal"] = base64.b64encode(sal).decode()
            mio["historial_c"] = fernet.encrypt(json.dumps(historial, ensure_ascii=False).encode()).decode()
        else:
            mio["historial"] = historial
        temporal = carpeta / f"{yo}.tmp"
        temporal.write_text(json.dumps(mio, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, carpeta / f"{yo}.json")
        self.estado.guardar()
        for v in self.p.ventanas:
            v.generar_nueva()
        extra = f", {n_claves} contraseñas nuevas" if n_claves else ""
        if falta_frase:
            extra += " (pon la frase de paso para recibir historial y contraseñas)"
        return f"⇅  Sincronizado con {len(otros)} dispositivo(s){extra}"
