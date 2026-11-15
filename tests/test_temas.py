"""Temas: validación de lo que llega de fuera, paleta derivada, instalar/exportar y fondo de inicio."""
import io
import json
import zipfile

import pytest

from aurora import temas
from aurora.comun import C, T


def zip_de(archivos):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as zf:
        for nombre, datos in archivos.items():
            zf.writestr(nombre, datos)
    return b.getvalue()


BASE = {"nombre": "Prueba", "autor": "yo", "colores": {"fondo": "#101010", "texto": "#f0f0f0",
                                                         "acento1": "#ff0000", "acento2": "#00ff00"}}


@pytest.fixture(autouse=True)
def limpio(tmp_path, monkeypatch):
    monkeypatch.setattr(temas, "CARPETA_TEMAS", tmp_path / "temas")


def test_integrados_validos_y_aurora_identico():
    for t in temas.INTEGRADOS:
        temas.normalizar(t)
    p = temas.paleta(temas.integrado("aurora"))
    assert p["superficie"] == "#161a22" and p["fondo"] == "#0d0f14"


def test_paleta_derivada_sirve_para_claros():
    claro = temas.paleta(temas.integrado("papel"))
    assert temas.es_oscuro(claro["texto"]) and not temas.es_oscuro(claro["fondo"])
    assert set(temas.DERIVADOS) <= set(claro)


@pytest.mark.parametrize("cambio", [
    {"colores": {"fondo": "red;background:url(x)", "texto": "#fff", "acento1": "#000", "acento2": "#000"}},
    {"colores": {"fondo": "#000000"}},
    {"nombre": ""},
    {"fondo": {"tipo": "imagen", "archivo": "../../etc/passwd.png"}},
    {"fondo": {"tipo": "script", "archivo": "a.png"}},
    {"sonidos": {"abrir": "x.mp3"}},
])
def test_rechaza_temas_malos(cambio):
    with pytest.raises(ValueError):
        temas.normalizar({**BASE, **cambio})


@pytest.mark.parametrize("archivos", [
    {"tema.json": json.dumps(BASE), "../fuera.png": b"x"},
    {"tema.json": json.dumps(BASE), "sub/fondo.png": b"x"},
    {"tema.json": json.dumps(BASE), "script.js": b"alert(1)"},
    {"tema.json": json.dumps(BASE), "otro.json": b"{}"},
    {"tema.json": "no es json"},
    {"fondo.png": b"x"},
])
def test_zip_malo(archivos):
    with pytest.raises(ValueError):
        temas.importar_zip(zip_de(archivos))
    assert not (temas.CARPETA_TEMAS / "prueba").exists()


def test_zip_demasiado_grande(monkeypatch):
    monkeypatch.setattr(temas, "MAX_ARCHIVO", 10)
    with pytest.raises(ValueError, match="grande"):
        temas.importar_zip(zip_de({"tema.json": json.dumps(BASE), "fondo.png": b"x" * 100}))


def test_importar_exportar_ida_y_vuelta(tmp_path):
    datos = {**BASE, "fondo": {"tipo": "imagen", "archivo": "fondo.png", "oscurecer": 0.5},
             "sonidos": {"abrir": "abrir.wav"}}
    t = temas.importar_zip(zip_de({"tema.json": json.dumps(datos), "fondo.png": b"png", "abrir.wav": b"wav"}))
    assert t["id"] == "prueba" and any(x["id"] == "prueba" for x in temas.instalados())
    temas.exportar_zip(t, tmp_path / "x.aurora-tema")
    temas.borrar("prueba")
    t2 = temas.importar_zip(str(tmp_path / "x.aurora-tema"))
    assert t2["fondo"] == t["fondo"] and t2["sonidos"] == {"abrir": "abrir.wav"}


def test_no_pisa_integrados():
    t = temas.importar_zip(zip_de({"tema.json": json.dumps({**BASE, "id": "aurora"})}))
    assert t["id"] == "aurora-2"
    assert temas.integrado("aurora")["nombre"] == "Aurora"


def test_guardar_desde_editor_copia_archivos_y_limpia(tmp_path):
    img = tmp_path / "foto.jpg"
    img.write_bytes(b"jpg")
    t = temas.guardar({**BASE, "fondo": {"tipo": "imagen", "archivo": "fondo.jpg"}}, {"fondo.jpg": str(img)})
    carpeta = temas.CARPETA_TEMAS / t["id"]
    assert (carpeta / "fondo.jpg").read_bytes() == b"jpg"
    temas.guardar({**BASE, "id": t["id"]})  # sin fondo: el archivo sobra
    assert not (carpeta / "fondo.jpg").exists()


def test_aplicar_colores_y_acento(app):
    temas.aplicar_colores(temas.integrado("papel"))
    assert C["fondo"] == "#f6f4ef" and T.a1 == "#2563eb"
    temas.aplicar_colores(temas.integrado("papel"), "Bosque")
    assert T.a1 == "#22c55e"
    temas.aplicar_colores(temas.integrado("aurora"))
    assert C["fondo"] == "#0d0f14"


def test_fondo_pagina_inicio():
    html_, _ = temas.fondo_pagina_inicio(temas.integrado("neon"))
    assert "<canvas" in html_
    t = temas.importar_zip(zip_de({"tema.json": json.dumps({**BASE, "fondo": {"tipo": "video", "archivo": "v.webm"}}),
                                   "v.webm": b"v"}))
    html_, _ = temas.fondo_pagina_inicio(t)
    assert "<video" in html_ and "file://" in html_ and "v.webm" in html_
    _, css = temas.fondo_pagina_inicio(temas.integrado("aurora"), animado=False)
    assert "animation:none" in css


def test_sonidos_sintetizados_son_wav():
    import wave
    ruta = temas.ruta_sonido(temas.integrado("neon"), "abrir")
    with wave.open(str(ruta)) as w:
        assert w.getframerate() == 44100 and w.getnframes() > 1000


def test_tienda_indice_sha256_y_rutas(app):
    import hashlib
    paquete = zip_de({"tema.json": json.dumps(BASE)})
    indice = {"temas": [{**BASE, "id": "prueba", "archivo": "temas/prueba.aurora-tema",
                         "sha256": hashlib.sha256(paquete).hexdigest(), "miniatura": "temas/prueba.png"},
                        {**BASE, "id": "sin-sha", "archivo": "x.aurora-tema"}]}
    servidos = {"https://t.example/indice.json": json.dumps(indice).encode(),
                "https://t.example/temas/prueba.aurora-tema": paquete}
    tienda = temas.Tienda()
    tienda._pedir = lambda url, limite, hecho: hecho(servidos.get(str(url)), "" if str(url) in servidos else "404")
    listas, instalados = [], []
    tienda.indice_listo.connect(lambda l, e: listas.append((l, e)))
    tienda.instalado.connect(lambda t, e: instalados.append((t, e)))
    tienda.cargar_indice("https://t.example/indice.json")
    lista, error = listas[0]
    assert not error and [t["id"] for t in lista] == ["prueba"]  # la que no trae SHA-256 se descarta
    assert lista[0]["tienda"]["archivo"] == "https://t.example/temas/prueba.aurora-tema"
    tienda.instalar(lista[0])
    assert instalados[-1][1] == "" and (temas.CARPETA_TEMAS / "prueba" / "tema.json").exists()
    servidos["https://t.example/temas/prueba.aurora-tema"] = paquete + b"manipulado"
    tienda.instalar(lista[0])
    assert "SHA-256" in instalados[-1][1]


def test_tienda_solo_https(app):
    errores = []
    tienda = temas.Tienda()
    tienda.indice_listo.connect(lambda l, e: errores.append(e))
    tienda.cargar_indice("http://t.example/indice.json")
    assert "https" in errores[0]


def test_tienda_publicada_es_valida():
    """Lo que hay en tienda/publicado coincide con su índice y Aurora lo puede instalar."""
    import hashlib
    from pathlib import Path
    carpeta = Path(__file__).resolve().parent.parent / "tienda" / "publicado"
    if not carpeta.exists():
        pytest.skip("tienda sin publicar")
    indice = json.loads((carpeta / "indice.json").read_text(encoding="utf-8"))
    assert indice["temas"]
    for e in indice["temas"]:
        datos = (carpeta / e["archivo"]).read_bytes()
        assert hashlib.sha256(datos).hexdigest() == e["sha256"]
        assert (carpeta / e["miniatura"]).exists()
        assert temas.importar_zip(datos)["id"] == e["id"]
