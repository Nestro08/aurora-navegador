"""Punto de entrada: instancia única, argumentos (URLs y archivos) y primera ventana."""
import getpass

from .ventana import *  # noqa: F401,F403

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
    servidor.listen(SERVIDOR)

    def conexion():
        s = servidor.nextPendingConnection()

        def leer():
            try:
                urls = json.loads(bytes(s.readAll()).decode("utf-8"))
            except ValueError:
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
    if sys.platform == "win32":  # icono propio en la barra de tareas
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Aurora.Navegador")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(NOMBRE)
    app.setApplicationDisplayName(NOMBRE)
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
    paleta = QPalette()
    for rol, color in ((QPalette.ColorRole.Window, C["fondo"]), (QPalette.ColorRole.WindowText, C["texto"]),
                       (QPalette.ColorRole.Base, C["chip"]), (QPalette.ColorRole.Text, C["texto"]),
                       (QPalette.ColorRole.Button, C["chip"]), (QPalette.ColorRole.ButtonText, C["texto"]),
                       (QPalette.ColorRole.Highlight, T.a1), (QPalette.ColorRole.HighlightedText, "#ffffff"),
                       (QPalette.ColorRole.ToolTipBase, "#1b1f29"), (QPalette.ColorRole.ToolTipText, C["texto"]),
                       (QPalette.ColorRole.PlaceholderText, "#6b7184")):
        paleta.setColor(rol, QColor(color))
    app.setPalette(paleta)
    Iconos.iniciar()
    perfil = gestor().perfil()
    fijar_acento(perfil.ajustes.datos["acento"])
    app.setStyleSheet(hoja_estilo())
    servidor = _escuchar(app)  # noqa: F841  (se mantiene vivo mientras dure la app)
    gestor().nueva_ventana(urls=urls, incognito=incognito)
    sys.exit(app.exec())
