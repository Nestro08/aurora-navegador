"""Los tests usan un HOME temporal y ningún llavero real: nunca tocan tu ~/.aurora ni tus contraseñas."""
import os
import sys
import tempfile
from pathlib import Path

HOME_PRUEBAS = tempfile.mkdtemp(prefix="aurora-tests-")
os.environ["HOME"] = HOME_PRUEBAS
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.fail.Keyring"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")
os.environ["QTWEBENGINE_DISABLE_SANDBOX"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from aurora import comun  # noqa: E402

assert str(comun.DATOS).startswith(HOME_PRUEBAS)

_APP = QApplication.instance() or QApplication(["aurora-tests"])  # Chromium necesita el nombre del programa


@pytest.fixture
def app():
    return _APP


@pytest.fixture
def con_llavero(monkeypatch):
    """Simula un llavero del sistema disponible (clave AES en memoria)."""
    from cryptography.fernet import Fernet

    from aurora import contrasenas
    monkeypatch.setattr(contrasenas, "_FERNET", Fernet(Fernet.generate_key()))
    return contrasenas._FERNET


@pytest.fixture
def sin_llavero(monkeypatch):
    from aurora import contrasenas
    monkeypatch.setattr(contrasenas, "_FERNET", False)
