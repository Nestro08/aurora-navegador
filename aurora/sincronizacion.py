"""Sincronización entre dispositivos a través de una carpeta compartida.

Cada dispositivo escribe su propio archivo (Aurora-Sync/<perfil>/<dispositivo>.json) en una carpeta que
sincroniza otro programa (OneDrive, Dropbox, Google Drive, Syncthing…). Al sincronizar, Aurora lee los
archivos de los demás dispositivos y mezcla accesos, historial y contraseñas. Con una frase de paso, las
contraseñas y el historial viajan cifrados (AES de la librería `cryptography`), nunca en claro.

Cada dispositivo deriva su clave con su propia sal, que publica en su archivo («sal»), así que dos PCs que
empiezan a la vez no pueden acabar con sales distintas. Si existe el antiguo sal.bin compartido, se adopta
como sal propia para seguir entendiéndose con dispositivos que aún usan la versión 1.

Leer y escribir la carpeta se hace en un hilo aparte (OneDrive con «archivos a petición» puede tardar en
entregar un archivo, y PBKDF2 es lento a propósito); la mezcla, que cambia los datos del perfil, en el hilo
principal. Todo lo que llega de otro dispositivo se valida antes de usarlo.
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
    except (ValueError, TypeError):
        return datetime.min


def _numero(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else 0.0


class Sincronizador(QObject):
    terminado = pyqtSignal(bool, str)
    _leido = pyqtSignal(object, object, bool)  # del hilo de lectura al principal
    _escrito = pyqtSignal(str, bool)
    _fallo = pyqtSignal(str)

    def __init__(self, perfil):
        super().__init__()
        self.p = perfil
        self.estado = Almacen("sync_estado", {"borrados_marcadores": {}, "borrados_claves": {}, "ultima": ""},
                              perfil.carpeta)
        for tipo in ("marcadores", "claves"):
            if not isinstance(self.estado.datos.get(f"borrados_{tipo}"), dict):
                self.estado.datos[f"borrados_{tipo}"] = {}
        self._claves = {}  # (frase, sal) → Fernet: PBKDF2 es lento a propósito, no se repite en cada sync
        self._en_curso = False
        self._leido.connect(self._al_leer)
        self._escrito.connect(self._al_escribir)
        self._fallo.connect(self._al_fallar)
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

    def _fernet(self, frase, sal):
        if not (frase and sal):
            return None
        if (frase, sal) not in self._claves:
            clave = hashlib.pbkdf2_hmac("sha256", frase.encode("utf-8"), sal, 300_000)
            self._claves[(frase, sal)] = Fernet(base64.urlsafe_b64encode(clave))
        return self._claves[(frase, sal)]

    def _fernet_de(self, frase, carpeta, otro):
        """La clave con la que otro dispositivo cifró su archivo."""
        if isinstance(otro.get("sal"), str) and otro["sal"]:
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
            return fernet.decrypt(str(token).encode()).decode("utf-8")
        except InvalidToken:
            raise RuntimeError("la frase de paso no coincide con la de tus otros dispositivos")

    @staticmethod
    def _limpiar(o):
        """Valida el archivo de otro dispositivo: una entrada rara no rompe la sincronización ni se cuela."""
        marcadores = []
        for m in o.get("marcadores") if isinstance(o.get("marcadores"), list) else []:
            if not es_marcador(m):  # también descarta javascript:, data:…
                continue
            limpio = {"url": m["url"], "titulo": str(m.get("titulo") or m["url"])[:200], "ts": _numero(m.get("ts"))}
            if isinstance(m.get("color"), str) and re.fullmatch(r"#[0-9a-fA-F]{6}", m["color"]):
                limpio["color"] = m["color"].lower()
            if isinstance(m.get("icono"), str) and m["icono"].strip():
                limpio["icono"] = m["icono"].strip()[:4]
            pos = m.get("pos")
            if isinstance(pos, dict) and all(isinstance(pos.get(k), (int, float)) for k in ("x", "y")):
                limpio["pos"] = {k: max(0.0, min(1.0, float(pos[k]))) for k in ("x", "y")}
            marcadores.append(limpio)
        historial = [{"url": h["url"], "titulo": h.get("titulo", "")[:500], "fecha": h["fecha"][:16]}
                     for h in (o.get("historial") if isinstance(o.get("historial"), list) else [])
                     if es_visita(h) and h["url"].startswith(("http://", "https://"))]
        bruto = o.get("borrados") if isinstance(o.get("borrados"), dict) else {}
        borrados = {}
        for tipo in ("marcadores", "claves"):
            b = bruto.get(tipo) if isinstance(bruto.get(tipo), dict) else {}
            borrados[tipo] = {str(k): _numero(ts) for k, ts in b.items()}
        claves = [{"origen": c["origen"], "usuario": c["usuario"], "clave": c["clave"], "ts": _numero(c.get("ts"))}
                  for c in (o.get("claves") if isinstance(o.get("claves"), list) else [])
                  if isinstance(c, dict) and all(isinstance(c.get(k), str) for k in ("origen", "usuario", "clave"))
                  and c["origen"].startswith(("http://", "https://"))]
        return {"marcadores": marcadores, "historial": historial, "borrados": borrados, "claves": claves,
                "_fernet": o.get("_fernet")}

    # ── 1. leer la carpeta (puede ir en un hilo: solo lee archivos y deriva claves, no toca el perfil)
    def _preparar(self):
        """Lo que la lectura necesita del perfil, tomado en el hilo principal."""
        sal = self.estado.datos.get("sal")
        return {"carpeta": self.carpeta(), "yo": self.dispositivo(), "frase": self._frase(),
                "sal": base64.b64decode(sal) if sal else None}

    def _leer(self, prep):
        carpeta, yo, frase, sal = prep["carpeta"], prep["yo"], prep["frase"], prep["sal"]
        carpeta.mkdir(parents=True, exist_ok=True)
        if frase and sal is None:
            antigua = carpeta / "sal.bin"
            sal = antigua.read_bytes() if antigua.exists() else secrets.token_bytes(16)
            if not antigua.exists():  # para que los dispositivos con la versión 1 usen la misma
                antigua.write_bytes(sal)
        fernet = self._fernet(frase, sal)
        otros, falta_frase = [], False
        for archivo in sorted(carpeta.glob("*.json")):
            if archivo.stem == yo:
                continue
            try:
                o = json.loads(archivo.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(o, dict):
                continue
            try:
                o["_fernet"] = self._fernet_de(frase, carpeta, o) if frase else None
            except (ValueError, OSError):  # sal mal codificada
                o["_fernet"] = None
            cifrado = o.pop("historial_c", None)
            if isinstance(cifrado, str) and frase:
                try:
                    o["historial"] = json.loads(self._descifrar(o["_fernet"], cifrado))
                except ValueError:  # JSON dañado dentro del cifrado
                    o["historial"] = []
            elif cifrado or o.get("claves"):
                falta_frase = True  # sin frase aquí no se puede leer lo que llega cifrado
            otros.append(self._limpiar(o))
        return {"sal": sal, "fernet": fernet, "otros": otros, "falta_frase": falta_frase}

    # ── 2. mezclar (en el hilo principal: cambia accesos, historial y contraseñas)
    def _mezclar(self, leido, yo):
        otros, fernet, sal = leido["otros"], leido["fernet"], leido["sal"]
        if sal and not self.estado.datos.get("sal"):
            self.estado.datos["sal"] = base64.b64encode(sal).decode()

        # borrados (lápidas): gana el más reciente de todos los dispositivos
        for tipo in ("marcadores", "claves"):
            b = self.estado.datos[f"borrados_{tipo}"]
            for o in otros:
                for k, ts in o["borrados"][tipo].items():
                    b[k] = max(ts, b.get(k, 0))
        borr_m, borr_c = self.estado.datos["borrados_marcadores"], self.estado.datos["borrados_claves"]

        # accesos: por URL, gana la edición más reciente
        locales = {m["url"]: m for m in self.p.marcadores.datos}
        orden = [m["url"] for m in self.p.marcadores.datos]
        for o in otros:
            for m in o["marcadores"]:
                actual = locales.get(m["url"])
                if actual is None:
                    orden.append(m["url"])
                if actual is None or m["ts"] > actual.get("ts", 0):
                    locales[m["url"]] = m
        self.p.marcadores.datos[:] = [locales[u] for u in dict.fromkeys(orden)
                                      if u in locales and borr_m.get(u, 0) <= locales[u].get("ts", 0)]
        self.p.marcadores.guardar()

        # historial: unión sin duplicados, de más nuevo a más viejo
        vistos, historial = set(), []
        for h in self.p.historial.datos + [h for o in otros for h in o["historial"]]:
            clave = (h.get("url"), h.get("fecha"))
            if clave not in vistos:
                vistos.add(clave)
                historial.append(h)
        historial.sort(key=_fecha, reverse=True)
        self.p.historial.datos[:] = historial[:5000]
        self.p.historial.guardar()

        # contraseñas (solo si hay frase de paso y cryptography)
        n_claves = 0
        if fernet:
            for o in otros:
                for c in o["claves"] if o["_fernet"] else []:
                    k = c["origen"] + "\n" + c["usuario"]
                    if borr_c.get(k, 0) >= c["ts"]:
                        continue
                    local = next((x for x in self.p.claves.de(c["origen"]) if x["usuario"] == c["usuario"]), None)
                    if local is None or c["ts"] > local.get("ts", 0):
                        plano = self._descifrar(o["_fernet"], c["clave"])
                        self.p.claves.guardar_cuenta(c["origen"], c["usuario"], plano, ts=c["ts"] or None,
                                                     guardar=False)
                        n_claves += 1
            self.p.claves.datos["cuentas"] = [
                c for c in self.p.claves.datos["cuentas"]
                if borr_c.get(c["origen"] + "\n" + c["usuario"], 0) < c.get("ts", 0)]
            self.p.claves.guardar()
        self.estado.guardar()

        # mi archivo con el resultado de la mezcla (copias: el hilo que lo escribe no comparte nada)
        claves = []
        for c in self.p.claves.datos["cuentas"] if fernet else []:
            plano = self.p.claves.leer_clave(c)
            if plano is not None:  # nunca se envía como vacía una contraseña que no se pudo descifrar
                claves.append({"origen": c["origen"], "usuario": c["usuario"], "ts": c.get("ts", 0),
                               "clave": fernet.encrypt(plano.encode()).decode()})
        mio = {
            "dispositivo": yo, "ts": time.time(), "version": 2,
            "marcadores": [dict(m) for m in self.p.marcadores.datos],
            "borrados": {"marcadores": dict(borr_m), "claves": dict(borr_c)},
            "claves": claves,
        }
        historial = [dict(h) for h in self.p.historial.datos[:3000]]
        if fernet:
            mio["sal"] = base64.b64encode(sal).decode()
            mio["historial_c"] = fernet.encrypt(json.dumps(historial, ensure_ascii=False).encode()).decode()
        else:
            mio["historial"] = historial
        extra = f", {n_claves} contraseñas nuevas" if n_claves else ""
        if leido["falta_frase"]:
            extra += " (pon la frase de paso para recibir historial y contraseñas)"
        return mio, f"⇅  Sincronizado con {len(otros)} dispositivo(s){extra}"

    # ── 3. escribir mi archivo (puede ir en un hilo: la carpeta puede ser de OneDrive y tardar)
    @staticmethod
    def _escribir(carpeta, yo, mio):
        temporal = carpeta / f"{yo}.tmp"
        temporal.write_text(json.dumps(mio, ensure_ascii=False), encoding="utf-8")
        os.replace(temporal, carpeta / f"{yo}.json")

    def _terminar(self):
        self.estado.datos["ultima"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.estado.guardar()
        for v in self.p.ventanas:
            v.generar_nueva()

    def _sincronizar(self):
        """Todo seguido en este hilo (al cerrar la última ventana y en los tests). Devuelve el mensaje."""
        prep = self._preparar()
        mio, mensaje = self._mezclar(self._leer(prep), prep["yo"])
        self._escribir(prep["carpeta"], prep["yo"], mio)
        self._terminar()
        return mensaje

    def sincronizar(self, silencioso=False, bloqueante=False):
        if not self.configurado() or self.p.incognito or self._en_curso:
            return
        if bloqueante:
            try:
                mensaje = self._sincronizar()
                if not silencioso:
                    self.terminado.emit(True, mensaje)
            except Exception as e:
                self.terminado.emit(False, f"No se pudo sincronizar: {e}")
            return
        self._en_curso = True
        try:
            prep = self._preparar()
        except Exception as e:
            self._al_fallar(str(e))
            return

        def hilo():
            try:
                self._leido.emit(self._leer(prep), prep, silencioso)
            except Exception as e:
                self._fallo.emit(str(e))

        threading.Thread(target=hilo, daemon=True).start()

    def _al_leer(self, leido, prep, silencioso):
        try:
            mio, mensaje = self._mezclar(leido, prep["yo"])
        except Exception as e:
            self._al_fallar(str(e))
            return

        def hilo():
            try:
                self._escribir(prep["carpeta"], prep["yo"], mio)
                self._escrito.emit(mensaje, silencioso)
            except Exception as e:
                self._fallo.emit(str(e))

        threading.Thread(target=hilo, daemon=True).start()

    def _al_escribir(self, mensaje, silencioso):
        self._en_curso = False
        try:
            self._terminar()
        except Exception as e:
            self._al_fallar(str(e))
            return
        if not silencioso:
            self.terminado.emit(True, mensaje)

    def _al_fallar(self, error):
        self._en_curso = False
        self.terminado.emit(False, f"No se pudo sincronizar: {error}")
