"""El puente de contraseñas en un Chromium real (sin pantalla): la web no puede falsificarlo ni espiarlo."""
import json

import pytest
from PyQt6.QtCore import QEventLoop, QTimer, QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineScript

from aurora.contrasenas import JS_CAPTURA, JS_RELLENAR, MSG_GEN, MSG_PW, MUNDO_AURORA

FORMULARIO = """<html><body><form onsubmit="return false">
<input type=text id=u><input type=password id=p><button id=b>Entrar</button></form>
<script>window.visto=[];
// una web maliciosa intenta fingir los mensajes de Aurora y espiar el relleno
console.log('__aurora_pw__'+JSON.stringify({u:'falso',p:'falso'}));console.log('__aurora_gen__');
document.getElementById('p').addEventListener('input',e=>window.visto.push(typeof window.__aurora_pw));
</script></body></html>"""


class Pagina(QWebEnginePage):
    def __init__(self, perfil):
        super().__init__(perfil)
        self.mensajes = []

    def javaScriptConsoleMessage(self, nivel, mensaje, linea, origen):
        self.mensajes.append(mensaje)


def esperar(ms=400):
    bucle = QEventLoop()
    QTimer.singleShot(ms, bucle.quit)
    bucle.exec()


def js(pagina, codigo, mundo=QWebEngineScript.ScriptWorldId.MainWorld):
    res, bucle = [], QEventLoop()
    pagina.runJavaScript(codigo, mundo, lambda r: (res.append(r), bucle.quit()))
    QTimer.singleShot(5000, bucle.quit)
    bucle.exec()
    return res[0] if res else None


@pytest.fixture
def pagina(app):
    perfil = QWebEngineProfile()
    s = QWebEngineScript()
    s.setSourceCode(JS_CAPTURA)
    s.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
    s.setWorldId(MUNDO_AURORA)
    perfil.scripts().insert(s)
    p = Pagina(perfil)
    bucle = QEventLoop()
    p.loadFinished.connect(lambda _: bucle.quit())
    QTimer.singleShot(15000, bucle.quit)
    p.setHtml(FORMULARIO, QUrl("https://ejemplo.com/login"))
    bucle.exec()
    esperar()
    yield p
    p.deleteLater()


def test_la_web_no_puede_fingir_mensajes(pagina):
    assert not any(m.startswith(MSG_PW) or m == MSG_GEN for m in pagina.mensajes)


def test_captura_real_llega_con_token(pagina):
    js(pagina, "document.getElementById('u').value='ana';document.getElementById('p').value='clave1';"
               "document.getElementById('b').click()")
    esperar()
    reales = [m for m in pagina.mensajes if m.startswith(MSG_PW)]
    assert reales and json.loads(reales[-1][len(MSG_PW):]) == {"u": "ana", "p": "clave1"}


def test_la_web_no_ve_el_script_de_aurora(pagina):
    assert js(pagina, "typeof window.__aurora_pw") == "undefined"
    assert js(pagina, "typeof window.__aurora_pw", MUNDO_AURORA) == "number"


def test_relleno_en_mundo_aislado(pagina):
    codigo = JS_RELLENAR.replace("%%A_RGB%%", "0,0,0") % (json.dumps("ana"), json.dumps("s3cr3to"),
                                                          json.dumps("https://ejemplo.com"))
    assert js(pagina, codigo, MUNDO_AURORA) == 1
    assert js(pagina, "document.getElementById('p').value") == "s3cr3to"
    assert js(pagina, "document.getElementById('u').value") == "ana"
    assert js(pagina, "JSON.stringify(window.visto)") == '["undefined"]'  # el evento llega, el script no se ve


def test_no_rellena_si_la_pagina_es_de_otro_sitio(pagina):
    codigo = JS_RELLENAR.replace("%%A_RGB%%", "0,0,0") % (json.dumps("ana"), json.dumps("s3cr3to"),
                                                          json.dumps("https://otro-sitio.com"))
    assert js(pagina, codigo, MUNDO_AURORA) == -1
    assert js(pagina, "document.getElementById('p').value") == ""
