"""Gestor de contraseñas: cifrado, almacén y tarjeta de «¿Guardar contraseña?»."""
from .comun import *  # noqa: F401,F403
from .widgets import *  # noqa: F401,F403
from .pestanas import *  # noqa: F401,F403
from .omnibox import *  # noqa: F401,F403
from .paleta import *  # noqa: F401,F403
from .motor import *  # noqa: F401,F403
from .desarrollo import *  # noqa: F401,F403


# ═════════════════════════════ contraseñas

CIFRADO_REAL = sys.platform == "win32"  # en Linux se decide al usar el llavero (ver cifrado_disponible)

JS_CAPTURA = r"""(()=>{if(window.__aurora_pw)return;window.__aurora_pw=1;let ultimo='';
const ss=(k,v)=>{try{return v===undefined?sessionStorage.getItem(k):sessionStorage.setItem(k,v)}catch(e){return null}};
const visibles=s=>[...document.querySelectorAll(s)].filter(i=>i.offsetParent!==null||i.type==='hidden');
const usuario=p=>{const ins=[...document.querySelectorAll('input')].filter(i=>/^(text|email|tel)$/.test(i.type)&&i.value);
 const antes=ins.filter(i=>i.compareDocumentPosition(p)&Node.DOCUMENT_POSITION_FOLLOWING);
 const u=((antes.pop()||ins[0]||{}).value||'').trim();if(u)ss('__aurora_u',u);return u||ss('__aurora_u')||''};
const mirar=()=>{const p=[...document.querySelectorAll('input[type=password]')].find(i=>i.value);
 if(!p){const e=visibles('input[type=email],input[autocomplete=username],input[name*=user i],input[name*=login i]').find(i=>i.value);
  if(e)ss('__aurora_u',e.value.trim());return}
 const d=JSON.stringify({u:usuario(p),p:p.value});if(d===ultimo)return;ultimo=d;console.log('__aurora_pw__'+d)};
document.addEventListener('submit',mirar,true);
document.addEventListener('click',e=>{if(e.target.closest&&e.target.closest('button,input[type=submit],input[type=button],[role=button],a'))mirar()},true);
document.addEventListener('keydown',e=>{if(e.key==='Enter')mirar()},true);
window.addEventListener('pagehide',mirar);
document.addEventListener('focusin',e=>{const i=e.target;
 if(!(i instanceof HTMLInputElement)||i.type!=='password'||i.value||i.__aurora_g)return;
 const f=i.form||document;const n=f.querySelectorAll('input[type=password]').length;
 const txt=(((f.innerText||'')+' '+location.href).toLowerCase()).slice(0,4000);
 if(i.autocomplete==='new-password'||n>=2||/regist|sign.?up|crear.{0,12}cuenta|create.{0,12}account|únete|join now|nueva contraseña|new password/.test(txt)){
  i.__aurora_g=1;console.log('__aurora_gen__')}},true);
})()"""

JS_PONER_GENERADA = r"""((p)=>{const a=document.activeElement;const f=(a&&a.form)||document;
const ins=[...f.querySelectorAll('input[type=password]')].filter(i=>i.offsetParent!==null);
const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
ins.forEach(i=>{s.call(i,p);i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));
i.style.transition='background-color .6s';i.style.backgroundColor='rgba(%%A_RGB%%,.16)'});return ins.length})(%s)"""

JS_RELLENAR = r"""((u,p)=>{const vis=i=>i.offsetParent!==null;
const poner=(el,v)=>{const s=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;s.call(el,v);
 el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));
 el.style.transition='background-color .6s';el.style.backgroundColor='rgba(%%A_RGB%%,.16)'};
const pw=[...document.querySelectorAll('input[type=password]')].filter(vis);
const textos=[...document.querySelectorAll('input')].filter(i=>/^(text|email|tel)$/.test(i.type)&&vis(i));
if(pw.length){const p0=pw[0];poner(p0,p);const antes=textos.filter(i=>i.compareDocumentPosition(p0)&Node.DOCUMENT_POSITION_FOLLOWING);
 const uf=antes.pop();if(uf&&u&&(!uf.value||uf.value===u))poner(uf,u);return 1}
const uf=textos.find(i=>/user|mail|login|correo|usuario|identifier/i.test(i.name+i.id+i.autocomplete+i.type));
if(uf&&u&&!uf.value){poner(uf,u);return 2}return 0})(%s,%s)"""


def _dpapi(datos, cifrar_):
    """Cifra/descifra con la API de protección de datos de Windows (ligado a tu usuario de Windows)."""
    import ctypes
    from ctypes import wintypes

    class BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(datos, len(datos))
    entrada = BLOB(len(datos), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    salida = BLOB()
    crypt32 = ctypes.windll.crypt32
    if cifrar_:
        ok = crypt32.CryptProtectData(ctypes.byref(entrada), "Aurora", None, None, None, 0, ctypes.byref(salida))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(salida))
    if not ok:
        raise OSError("DPAPI")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(salida.pbData)


_FERNET = None


def _llavero():
    """En Linux: clave AES guardada en el llavero del sistema (GNOME Keyring o KWallet, vía Secret Service).

    El llavero se desbloquea al iniciar sesión, así que solo tu usuario puede leer las contraseñas."""
    global _FERNET
    if _FERNET is None:
        _FERNET = False
        try:
            import keyring
            from cryptography.fernet import Fernet
            backend = type(keyring.get_keyring()).__name__.lower()
            if any(x in backend for x in ("fail", "plaintext", "null", "chainer")) and \
                    not getattr(keyring.get_keyring(), "backends", None):
                raise RuntimeError("sin llavero seguro")
            clave = keyring.get_password("Aurora", "clave-contrasenas")
            if not clave:
                clave = Fernet.generate_key().decode()
                keyring.set_password("Aurora", "clave-contrasenas", clave)
                if keyring.get_password("Aurora", "clave-contrasenas") != clave:
                    raise RuntimeError("el llavero no guardó la clave")
            _FERNET = Fernet(clave.encode())
        except Exception:
            _FERNET = False
    return _FERNET or None


def cifrado_disponible():
    if sys.platform == "win32":
        return "dpapi"
    return "llavero" if _llavero() else None


def cifrar(texto):
    datos = texto.encode("utf-8")
    if sys.platform == "win32":
        try:
            return "dpapi:" + base64.b64encode(_dpapi(datos, True)).decode()
        except Exception:
            pass
    else:
        f = _llavero()
        if f:
            return "llavero:" + f.encrypt(datos).decode()
    return "b64:" + base64.b64encode(datos).decode()


def descifrar(valor):
    tipo, _, cuerpo = valor.partition(":")
    if tipo == "llavero":
        return _llavero().decrypt(cuerpo.encode()).decode("utf-8")
    datos = base64.b64decode(cuerpo)
    if tipo == "dpapi":
        datos = _dpapi(datos, False)
    return datos.decode("utf-8")


class Contrasenas(Almacen):
    def __init__(self, carpeta=None):
        super().__init__("contrasenas", {"cuentas": [], "nunca": []}, carpeta)
        self.al_borrar = None  # lo usa la sincronización para registrar borrados
        self._migrar()

    def _migrar(self):
        """Si había contraseñas solo codificadas y ahora hay cifrado disponible, las cifra."""
        pendientes = [c for c in self.datos["cuentas"] if c["clave"].startswith("b64:")]
        if pendientes and cifrado_disponible():
            for c in pendientes:
                c["clave"] = cifrar(descifrar(c["clave"]))
            self.guardar()

    @staticmethod
    def origen(url):
        if isinstance(url, str):
            url = QUrl(url if "://" in url else "https://" + url)
        puerto = f":{url.port()}" if url.port() != -1 else ""
        return f"{url.scheme()}://{url.host()}{puerto}"

    def de(self, origen):
        return [c for c in self.datos["cuentas"] if c["origen"] == origen]

    def clave(self, cuenta):
        try:
            return descifrar(cuenta["clave"])
        except Exception:
            return ""

    def estado(self, origen, usuario, clave):
        for c in self.de(origen):
            if c["usuario"] == usuario:
                return "igual" if self.clave(c) == clave else "cambiada"
        return "nueva"

    def guardar_cuenta(self, origen, usuario, clave, ts=None, guardar=True):
        fecha = datetime.now().strftime("%d/%m/%Y")
        ahora = datetime.now().timestamp() if ts is None else ts
        for c in self.datos["cuentas"]:
            if c["origen"] == origen and c["usuario"] == usuario:
                c.update(clave=cifrar(clave), fecha=fecha, ts=ahora)
                break
        else:
            self.datos["cuentas"].append({"origen": origen, "usuario": usuario, "clave": cifrar(clave),
                                          "fecha": fecha, "ts": ahora})
        if guardar:
            self.guardar()

    def borrar(self, cuenta):
        self.datos["cuentas"].remove(cuenta)
        self.guardar()
        if self.al_borrar:
            self.al_borrar(cuenta["origen"] + "\n" + cuenta["usuario"])

    def nunca(self, origen):
        if origen not in self.datos["nunca"]:
            self.datos["nunca"].append(origen)
            self.guardar()


class Pregunta(QFrame):
    """Tarjeta flotante con botones, p. ej. «¿Guardar la contraseña?»."""

    def __init__(self, padre, ventana):
        super().__init__(padre, objectName="pregunta")
        self.v, self._abierta = ventana, False
        self.hide()
        self.setFixedWidth(360)
        l = QVBoxLayout(self)
        l.setContentsMargins(18, 14, 12, 14)
        l.setSpacing(6)
        cab = QHBoxLayout()
        self.icono = QLabel(Iconos.glifo("llave"))
        self.icono.setFont(Iconos.fuente(13))
        self.titulo = QLabel(objectName="tituloPregunta")
        cerrar = BotonIcono("cerrar", "Ahora no", tam=28)
        cerrar.clicked.connect(self.ocultar)
        cab.addWidget(self.icono)
        cab.addSpacing(6)
        cab.addWidget(self.titulo, 1)
        cab.addWidget(cerrar)
        self.detalle = QLabel(objectName="tenue")
        self.detalle.setWordWrap(True)
        self.botones = QHBoxLayout()
        self.botones.setSpacing(8)
        l.addLayout(cab)
        l.addWidget(self.detalle)
        l.addSpacing(6)
        l.addLayout(self.botones)
        self.setGraphicsEffect(QGraphicsDropShadowEffect(self, blurRadius=34, offset=QPointF(0, 10),
                                                         color=QColor(0, 0, 0, 170)))
        self.anim = QPropertyAnimation(self, b"pos", self)
        self.anim.setDuration(320)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.finished.connect(lambda: None if self._abierta else self.hide())

    def mostrar(self, titulo, detalle, botones):
        while self.botones.count():
            w = self.botones.takeAt(0).widget()
            if w:
                w.deleteLater()
        self.titulo.setText(titulo)
        self.detalle.setText(detalle)
        self.botones.addStretch()
        for texto, funcion, primario in botones:
            b = QPushButton(texto, objectName="primario" if primario else "")
            b.clicked.connect(lambda _, f=funcion: (f(), self.ocultar()))
            self.botones.addWidget(b)
        self.adjustSize()
        x = self.v.pila.width() - self.width() - 18
        if not self._abierta:
            self.move(x, -self.height() - 10)
        self._abierta = True
        self.show()
        self.raise_()
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        animar(self.anim, self.pos(), QPoint(x, 12))

    def ocultar(self):
        if not self._abierta:
            return
        self._abierta = False
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        animar(self.anim, self.pos(), QPoint(self.x(), -self.height() - 20))

    def recolocar(self):
        if self._abierta:
            self.move(self.v.pila.width() - self.width() - 18, 12)
