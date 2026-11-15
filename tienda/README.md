# Tienda de temas de Aurora

Cada carpeta de `temas/` es un tema: un `tema.json` y, si quiere, una imagen o un vídeo de fondo
(`fondo.jpg`, `fondo.webm`…) y sonidos `.wav`. El formato completo está explicado al principio de
`aurora/temas.py`.

## Publicar

```bash
QT_QPA_PLATFORM=offscreen python herramientas/publicar_tienda.py
```

Crea `tienda/publicado/` con cada tema empaquetado (`.aurora-tema`), su miniatura y `indice.json`
(con el SHA-256 de cada paquete: Aurora rechaza cualquier archivo que no coincida).

Sube esa carpeta a cualquier sitio con **HTTPS**. Con GitHub, por ejemplo, en un repositorio público:

```
https://raw.githubusercontent.com/<usuario>/<repositorio>/main/tienda/publicado/indice.json
```

Pon esa dirección en *Ajustes → Temas → Dirección de la tienda* (o en `URL_TIENDA_DEFECTO` de
`aurora/tienda_temas.py` para que venga puesta en todas las instalaciones).

## Añadir un tema

Créalo en Aurora (*Ajustes → Temas → Crear tema…*), expórtalo como `.aurora-tema`, descomprímelo en
una carpeta nueva dentro de `temas/` y vuelve a publicar.
