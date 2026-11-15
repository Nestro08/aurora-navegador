"""Genera recursos/aurora.ico (varios tamaños) y recursos/aurora.png a partir del icono del programa."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from aurora.comun import crear_icono_app  # noqa: E402  (importa QtWebEngine antes de crear la app)
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)

destino = RAIZ / "recursos"
destino.mkdir(exist_ok=True)
icono = crear_icono_app()
png = destino / "aurora.png"
icono.pixmap(256, 256).save(str(png))
try:
    from PIL import Image
    Image.open(png).save(destino / "aurora.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                        (128, 128), (256, 256)])
except ImportError:  # sin Pillow: icono de un solo tamaño con el escritor de Qt
    icono.pixmap(256, 256).save(str(destino / "aurora.ico"))
print(f"Icono creado en {destino / 'aurora.ico'}")
