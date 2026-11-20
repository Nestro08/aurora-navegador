"""Punto de entrada: instancia única, argumentos (URLs y archivos) y primera ventana."""
import getpass

from .ventana import *  # noqa: F401,F403
from . import temas
from .temas import Apariencia, aplicar_colores, paleta_qt
from .arranque import PantallaArranque
from . import drm

SERVIDOR = f"aurora-{getpass.getuser()}"


def _urls_de(argumentos):
    urls = []
    for a in argumentos:
        if a.startswith("-"):
            continue
        if os.path.exists(a):
            urls.append(QUrl.fromLocalFile(os.path.abspath(a)).toString())
        else:
            urls.append(QUrl.fromUserInput(a).toString())
    return urls


def _avisar_instancia(urls):
    """Si Aurora ya está abierto, le pasa las URLs y devuelve True."""
    s = QLocalSocket()
    s.connectToServer(SERVIDOR)
    if not s.waitForConnected(400):
        return False
    s.write(json.dumps(urls or ["__ventana__"]).encode("utf-8"))
    s.waitForBytesWritten(1500)
    s.disconnectFromServer()
    return True


def _escuchar(app):
    QLocalServer.removeServer(SERVIDOR)
    servidor = QLocalServer(app)
    servidor.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)  # otros usuarios no pueden conectarse
    servidor.listen(SERVIDOR)

    def conexion():
        s = servidor.nextPendingConnection()
        recibido = bytearray()

        def leer():
            recibido.extend(bytes(s.readAll()))
            try:
                urls = json.loads(recibido.decode("utf-8"))
            except ValueError:  # aún no ha llegado todo el mensaje
                return
            recibido.clear()
            if not isinstance(urls, list) or not all(isinstance(u, str) for u in urls):
                return
            v = gestor().ventana_activa()
            if urls == ["__incognito__"]:
                v = gestor().nueva_ventana(incognito=True)
            elif urls == ["__ventana__"] or v is None:
                v = gestor().nueva_ventana(restaurar=v is None)
            else:
                for u in urls:
                    v.nueva_pestana(u)
            v.showNormal() if v.isMinimized() else v.show()
            v.raise_()
            v.activateWindow()
        s.readyRead.connect(leer)

    servidor.newConnection.connect(conexion)
    return servidor


def main():
    try:
        extra = json.loads((DATOS / "ajustes.json").read_text(encoding="utf-8")).get("flags", "")
        if extra:
            os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] += " " + extra
    except (OSError, ValueError):
        pass
    drm.activar()  # Widevine (Netflix, Spotify…) del Chrome/Edge/Brave instalado, si lo hay
    if sys.platform == "win32":  # icono propio en la barra de tareas
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Aurora.Navegador")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(NOMBRE)
    app.setDesktopFileName("aurora")  # en GNOME/Wayland enlaza la ventana con aurora.desktop (icono del dock)
    app.setWindowIcon(crear_icono_app())
    urls = _urls_de(sys.argv[1:])
    incognito = "--incognito" in sys.argv
    if "--nueva-instancia" not in sys.argv and _avisar_instancia(["__incognito__"] if incognito else urls):
        return
    app.setStyle("Fusion")
    fuente = QFont()
    fuente.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans"])
    fuente.setPointSizeF(9.75)
    app.setFont(fuente)
    Iconos.iniciar()
    perfil = gestor().perfil()
    a = Apariencia.datos()
    if "migrado" not in a:  # antes el acento era del perfil
        acento = perfil.ajustes.datos.get("acento", "")
        Apariencia.guardar(acento="" if acento in ("", "Aurora") else acento, migrado=True)
    aplicar_colores(temas.buscar(a["tema"]), a["acento"])
    app.setPalette(paleta_qt())
    app.setStyleSheet(hoja_estilo())
    servidor = _escuchar(app)  # noqa: F841  (se mantiene vivo mientras dure la app)
    app.aboutToQuit.connect(Almacen.volcar_pendientes)
    if Apariencia.datos().get("arranque", True):
        nombre = perfil.ajustes.datos.get("nombre", "")
        bienvenida = PantallaArranque(f"Hola, {nombre}" if nombre else "")
        bienvenida.mostrar()
        estado = {"ventana": None, "listo": False}

        def acabar():  # cuando terminan la animación y la ventana (lo último de los dos)
            if estado["ventana"] is not None and estado["listo"]:
                estado["ventana"].show()
                bienvenida.cerrar()

        def crear():
            estado["ventana"] = gestor().nueva_ventana(urls=urls, incognito=incognito, mostrar=False)
            acabar()

        bienvenida.terminado.connect(lambda: (estado.update(listo=True), acabar()))
        QTimer.singleShot(350, crear)  # Chromium tarda en arrancar: se hace con el logo ya en pantalla
    else:
        gestor().nueva_ventana(urls=urls, incognito=incognito)
    sys.exit(app.exec())
