"""Prepara la tienda de temas para publicarla: tienda/temas/<id>/ → tienda/publicado/.

Para cada tema valida tema.json igual que Aurora, crea <id>.aurora-tema, su miniatura <id>.png y el
indice.json con el SHA-256 de cada archivo. Las rutas del índice son relativas, así que basta con subir la
carpeta tienda/publicado a cualquier web con HTTPS (por ejemplo un repositorio de GitHub).

Uso:  QT_QPA_PLATFORM=offscreen python herramientas/publicar_tienda.py
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import PyQt6.QtWebEngineWidgets  # noqa: E402,F401  (antes de crear la aplicación)
from PyQt6.QtWidgets import QApplication  # noqa: E402

app = QApplication(["publicar-tienda"])

from aurora import temas  # noqa: E402
from aurora.tienda_temas import Miniatura  # noqa: E402


def main():
    origen, destino = RAIZ / "tienda" / "temas", RAIZ / "tienda" / "publicado"
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    temas.CARPETA_TEMAS = origen  # para que la miniatura encuentre los fondos
    indice = []
    for carpeta in sorted(d for d in origen.iterdir() if d.is_dir()):
        bruto = json.loads((carpeta / "tema.json").read_text(encoding="utf-8"))
        tema = temas.normalizar(bruto, carpeta)
        tema["id"] = carpeta.name
        paquete = destino / f"{tema['id']}.aurora-tema"
        temas.exportar_zip(tema, paquete)
        Miniatura(tema).grab().save(str(destino / f"{tema['id']}.png"), "PNG")
        indice.append({**{k: v for k, v in tema.items() if v is not None},
                       "archivo": paquete.name, "miniatura": f"{tema['id']}.png",
                       "sha256": hashlib.sha256(paquete.read_bytes()).hexdigest(),
                       "tamano": paquete.stat().st_size})
        print(f"✓ {tema['nombre']}  ({paquete.stat().st_size // 1024} KB)")
    (destino / "indice.json").write_text(json.dumps({"version": 1, "temas": indice}, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(f"\nTienda lista en {destino} ({len(indice)} temas)")


if __name__ == "__main__":
    main()
