"""El asistente escribe la petición en la caja de chat de la web de la IA (sin enviarla)."""
import json

import pytest
from PyQt6.QtCore import QEventLoop, QTimer, QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript

from aurora.asistente import IAS_WEB, JS_ESCRIBIR
from aurora.contrasenas import MUNDO_AURORA

TEXTO = "Resume esta página.\n\nContenido:\n\"\"\"\nHola «mundo» & <b>no es html</b>\n\"\"\""

PAGINAS = {
    # como Perplexity y otras: un textarea controlado
    "textarea": "<textarea id=e></textarea><script>window.leido='';e.addEventListener('input',()=>leido=e.value)</script>",
    # como ProseMirror (Claude, ChatGPT): gestiona el pegado él mismo
    "editor": """<div id=e class=ProseMirror contenteditable=true></div><script>window.leido='';
        e.addEventListener('paste',ev=>{ev.preventDefault();leido=ev.clipboardData.getData('text/plain');
        e.textContent=leido})</script>""",
    # contenteditable sin gestor de pegado: se escribe como texto tecleado
    "simple": "<div id=e contenteditable=true role=textbox></div><script>window.leido='';"
              "e.addEventListener('input',()=>leido=e.innerText)</script>",
    "sin_caja": "<p>nada donde escribir</p><script>window.leido=''</script>",
}


def esperar_js(pagina, codigo, mundo=QWebEngineScript.ScriptWorldId.MainWorld):
    res, bucle = [], QEventLoop()
    pagina.runJavaScript(codigo, mundo, lambda r: (res.append(r), bucle.quit()))
    QTimer.singleShot(5000, bucle.quit)
    bucle.exec()
    return res[0] if res else None


@pytest.fixture(scope="module")
def perfil(app):
    return QWebEngineProfile()


@pytest.mark.parametrize("tipo, esperado", [("textarea", 1), ("editor", 1), ("simple", 1), ("sin_caja", 0)])
def test_escribe_en_la_caja(perfil, tipo, esperado):
    p = QWebEnginePage(perfil)
    bucle = QEventLoop()
    p.loadFinished.connect(lambda _: bucle.quit())
    QTimer.singleShot(10000, bucle.quit)
    p.setHtml(PAGINAS[tipo], QUrl("https://ia.example/"))
    bucle.exec()
    assert esperar_js(p, JS_ESCRIBIR % json.dumps(TEXTO), MUNDO_AURORA) == esperado
    leido = esperar_js(p, "window.leido")
    if esperado:
        # en un contenteditable los saltos se convierten en bloques: se comparan las líneas con texto
        lineas = lambda t: [x for x in t.replace("\r", "").split("\n") if x.strip()]  # noqa: E731
        assert lineas(leido) == lineas(TEXTO)
    else:
        assert leido == ""
    p.deleteLater()


def test_ias_web_son_https():
    assert {"Claude", "ChatGPT", "Gemini", "Copilot", "Perplexity", "Le Chat"} == set(IAS_WEB)
    assert all(url.startswith("https://") for url, _ in IAS_WEB.values())
