"""Detección del módulo Widevine de un navegador instalado."""
import json
import sys

import pytest

from aurora import drm

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="rutas de Linux")


def cdm(base, version, interfaces="10"):
    base.mkdir(parents=True)
    (base / "manifest.json").write_text(json.dumps({"version": version, "x-cdm-interface-versions": interfaces}))
    lib = base / "_platform_specific" / "linux_x64" / "libwidevinecdm.so"
    lib.parent.mkdir(parents=True)
    lib.write_bytes(b"\x7fELF")
    return lib


def test_elige_el_mas_reciente_compatible(tmp_path, monkeypatch):
    cdm(tmp_path / "chrome", "4.10.3112.0")
    nuevo = cdm(tmp_path / "brave", "4.10.3200.0")
    cdm(tmp_path / "raro", "9.0.0.0", interfaces="12")  # interfaz que este motor no entiende
    (tmp_path / "vacio").mkdir()
    monkeypatch.setattr(drm, "_candidatos", lambda: (
        [("Google Chrome", tmp_path / "chrome"), ("Brave", tmp_path / "brave"), ("Raro", tmp_path / "raro"),
         ("Nada", tmp_path / "vacio")], "_platform_specific/linux_x64/libwidevinecdm.so"))
    w = drm.buscar()
    assert w == {"ruta": str(nuevo), "version": "4.10.3200.0", "navegador": "Brave"}
    monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "--enable-smooth-scrolling")
    drm.activar()
    import os
    assert os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] == f"--enable-smooth-scrolling --widevine-path={nuevo}"


def test_sin_widevine(tmp_path, monkeypatch):
    monkeypatch.setattr(drm, "_candidatos", lambda: ([], "x"))
    monkeypatch.setenv("QTWEBENGINE_CHROMIUM_FLAGS", "")
    assert drm.buscar() is None and drm.activar() is None
