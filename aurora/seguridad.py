"""Seguridad: generador de contraseñas, contraseña maestra y Windows Hello."""
import asyncio
import hashlib
import secrets
import string
import time

from .widgets import *  # noqa: F401,F403

SIMBOLOS = "!@#$%&*-_=+?"


def generar_contrasena(longitud=18):
    """Contraseña aleatoria criptográficamente segura con minúsculas, mayúsculas, números y símbolos."""
    grupos = [string.ascii_lowercase, string.ascii_uppercase, string.digits, SIMBOLOS]
    todos = "".join(grupos)
    while True:
        clave = "".join(secrets.choice(todos) for _ in range(longitud))
        if all(any(c in g for c in clave) for g in grupos):
            return clave


def _verificador_windows():
    """Devuelve la clase UserConsentVerifier de Windows si hay un paquete WinRT instalado."""
    for modulo in ("winrt.windows.security.credentials.ui", "winsdk.windows.security.credentials.ui"):
        try:
            m = __import__(modulo, fromlist=["UserConsentVerifier"])
            return m
        except Exception:
            continue
    return None


_HELLO = None


def hello_disponible():
    global _HELLO
    if _HELLO is None:
        _HELLO = False
        if sys.platform == "win32":
            m = _verificador_windows()
            if m:
                try:
                    estado = asyncio.run(_esperar(m.UserConsentVerifier.check_availability_async()))
                    _HELLO = estado == m.UserConsentVerifierAvailability.AVAILABLE
                except Exception:
                    _HELLO = False
    return _HELLO


async def _esperar(operacion):
    return await operacion


def verificar_hello(motivo):
    m = _verificador_windows()
    try:
        r = asyncio.run(_esperar(m.UserConsentVerifier.request_verification_async(motivo)))
        return r == m.UserConsentVerificationResult.VERIFIED
    except Exception:
        return False


class DialogoMaestra(QDialog):
    def __init__(self, padre, motivo, crear=False):
        super().__init__(padre)
        self.setWindowTitle("Contraseña maestra")
        self.setMinimumWidth(420)
        l = QVBoxLayout(self)
        l.setContentsMargins(24, 22, 24, 20)
        l.setSpacing(10)
        icono = QLabel(Iconos.glifo("llave"))
        icono.setFont(Iconos.fuente(22))
        icono.setStyleSheet(f"color:{T.a1}")
        titulo = QLabel("Crea tu contraseña maestra" if crear else "Confirma que eres tú", objectName="tituloPregunta")
        texto = QLabel(("Protegerá tus contraseñas guardadas. Aurora no puede recuperarla si la olvidas, "
                        "así que elige una que recuerdes.") if crear else f"Escribe tu contraseña maestra para {motivo}.",
                       objectName="tenue")
        texto.setWordWrap(True)
        self.clave = QLineEdit(placeholderText="Contraseña maestra")
        self.clave.setEchoMode(QLineEdit.EchoMode.Password)
        self.repetir = QLineEdit(placeholderText="Repítela")
        self.repetir.setEchoMode(QLineEdit.EchoMode.Password)
        self.repetir.setVisible(crear)
        self.error = QLabel("", objectName="error")
        for w in (icono, titulo, texto, self.clave, self.repetir, self.error):
            l.addWidget(w)
        fila = QHBoxLayout()
        fila.addStretch()
        cancelar = QPushButton("Cancelar")
        aceptar = QPushButton("Crear" if crear else "Desbloquear", objectName="primario")
        cancelar.clicked.connect(self.reject)
        aceptar.clicked.connect(self._aceptar)
        aceptar.setDefault(True)
        fila.addWidget(cancelar)
        fila.addWidget(aceptar)
        l.addLayout(fila)
        self.crear = crear

    def _aceptar(self):
        if self.crear:
            if len(self.clave.text()) < 6:
                self.error.setText("Usa al menos 6 caracteres.")
                return
            if self.clave.text() != self.repetir.text():
                self.error.setText("Las dos contraseñas no coinciden.")
                return
        self.accept()


class Verificador:
    """Pide Windows Hello o la contraseña maestra antes de mostrar contraseñas (válido 5 minutos)."""
    VALIDEZ = 300

    def __init__(self, ajustes):
        self.ajustes = ajustes
        self.hasta = 0.0

    @staticmethod
    def derivar(clave, sal):
        return hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, 300_000)

    def tiene_maestra(self):
        return bool(self.ajustes.datos.get("maestra"))

    def crear_maestra(self, padre):
        d = DialogoMaestra(padre, "", crear=True)
        if not d.exec():
            return False
        sal = secrets.token_bytes(16)
        self.ajustes.datos["maestra"] = {"sal": base64.b64encode(sal).decode(),
                                         "hash": base64.b64encode(self.derivar(d.clave.text(), sal)).decode()}
        self.ajustes.guardar()
        self.hasta = time.time() + self.VALIDEZ
        return True

    def _coincide(self, clave):
        m = self.ajustes.datos["maestra"]
        esperado = base64.b64decode(m["hash"])
        return secrets.compare_digest(self.derivar(clave, base64.b64decode(m["sal"])), esperado)

    def comprobar(self, padre, motivo="ver tus contraseñas"):
        a = self.ajustes.datos
        if not a.get("proteger_pw"):
            return True
        if time.time() < self.hasta:
            return True
        if a.get("usar_hello", True) and hello_disponible():
            if verificar_hello(f"Aurora quiere {motivo}"):
                self.hasta = time.time() + self.VALIDEZ
                return True
            return False
        if not self.tiene_maestra():
            return self.crear_maestra(padre)
        for _ in range(3):
            d = DialogoMaestra(padre, motivo)
            if not d.exec():
                return False
            if self._coincide(d.clave.text()):
                self.hasta = time.time() + self.VALIDEZ
                return True
            QMessageBox.warning(padre, "Contraseña incorrecta", "La contraseña maestra no es correcta.")
        return False

    def bloquear(self):
        self.hasta = 0.0
