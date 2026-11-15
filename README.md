# Aurora 4.0

Navegador de escritorio con motor Chromium (QtWebEngine), escrito en Python y PyQt6. Animado, oscuro y con
herramientas para desarrolladores, un gestor de contraseñas, perfiles, sincronización, extensiones y un
asistente con IA.

## Instalar en Fedora (Linux)

```bash
unzip Aurora-4.0.zip && cd Aurora
bash instalar-fedora.sh
```

El script instala Aurora para tu usuario, sin tocar el sistema salvo dos o tres librerías de Qt si faltan
(las pide con `sudo dnf`). Después:

- Aparece en **Actividades** con su icono, y con clic derecho tiene *Nueva ventana* e *Incógnito*.
- Se abre desde la terminal con `aurora`.
- Al final te pregunta si quieres que sea tu navegador predeterminado. Para volver a Firefox:
  `xdg-settings set default-web-browser org.mozilla.firefox.desktop`.
- Para actualizar, vuelve a ejecutar `instalar-fedora.sh` con la versión nueva.
- Para desinstalar: `bash desinstalar-fedora.sh`.

En Linux las contraseñas se cifran con AES. La clave se guarda en el **llavero del sistema** (GNOME
Keyring o KWallet), que se desbloquea al iniciar sesión.

## Empezar en Windows

**Sin instalar nada más (para probar o programar):** doble clic en `iniciar.bat`. La primera vez crea un
entorno virtual e instala las dependencias.

O a mano:

```bat
pip install -r requirements.txt
python Aurora.pyw
```

**Como programa de verdad (.exe + instalador):** doble clic en `construir.bat`.

1. Crea `dist\Aurora\Aurora.exe` con PyInstaller.
2. Si tienes [Inno Setup 6](https://jrsoftware.org/isdl.php), crea también `dist\Aurora-Setup-4.0.exe`. El
   instalador añade accesos directos y registra Aurora como navegador. Después puedes elegirlo como
   predeterminado en *Configuración de Windows → Aplicaciones predeterminadas*.

Aurora es de **instancia única**: si ya está abierto y pulsas un enlace en otra aplicación, se abre como una
pestaña nueva en la ventana que tienes. Acepta URLs y archivos como argumentos (`Aurora.exe pagina.html`) y
`--incognito`.

## Funciones

| Área | Qué hay |
|---|---|
| Pestañas | Animadas, se reordenan arrastrando, **fijadas**, **grupos de colores con nombre** que se pliegan, indicador de sonido y silenciar (Ctrl+M), **dormir pestañas** inactivas para ahorrar memoria, **pantalla dividida** (Ctrl+Shift+D), menú con clic derecho |
| Navegación | Paleta de comandos (Ctrl+K), página de inicio animada con accesos, buscar en la página (Ctrl+F), **modo lectura** (F9), **vídeo flotante** (Ctrl+Shift+V), gestor de **descargas** con progreso, pausa y reanudación |
| Privacidad | Bloqueador de anuncios y rastreadores, Do Not Track y GPC, bloquear cookies de terceros, **ventana de incógnito** (Ctrl+Shift+N), **perfiles** separados (Personal, Uni…) |
| Contraseñas | Guarda y rellena; **generador** al registrarte; cifradas (llavero de GNOME/KDE en Linux, DPAPI en Windows); **contraseña maestra** o **Windows Hello** para verlas; importar el CSV de Chrome o Edge |
| Desarrolladores (F12) | Inspector de Chromium, consola JS, registro de red, **cliente de API** tipo Postman, **auditoría** (accesibilidad, SEO, rendimiento, seguridad, enlaces rotos), modo responsive, User-Agent, CSS en vivo, servidor local con recarga en vivo, **cuentagotas y medidor** (Ctrl+Shift+X), **captura de página completa**, visor de JSON |
| Sincronización | Accesos, historial y contraseñas entre tus PCs (Windows y Linux) a través de una carpeta de OneDrive, Dropbox, Syncthing… Las contraseñas viajan cifradas con AES y una frase de paso |
| Extensiones | Userscripts `.user.js` (compatibles con Tampermonkey), estilos `.user.css` y extensiones en Python con API propia. Incluye 4 de ejemplo |
| Asistente IA (Ctrl+Shift+A) | Resume, traduce y explica la página o lo que selecciones, con respuestas en tiempo real. Funciona con Claude (clave de API) o cualquier proveedor compatible con OpenAI, incluido **Ollama** (gratis y en tu PC) |
| Ajustes (Ctrl+,) | General, Apariencia (7 colores de acento), Privacidad, Contraseñas, Historial, Accesos, Descargas, Perfiles, Sincronización, Extensiones, Asistente IA, Desarrolladores |

## Dónde se guardan tus datos

En la carpeta `.aurora` de tu usuario (`~/.aurora` en Linux, `C:\Users\<tú>\.aurora` en Windows). La carpeta `perfiles\` contiene los perfiles extra y `extensiones\` las
extensiones. No se borra al desinstalar.

## Escribir una extensión

Crea una carpeta en `.aurora\extensiones` con un `manifest.json`:

```json
{ "nombre": "Mi extensión", "version": "1.0", "descripcion": "Qué hace",
  "coincide": ["*://*.ejemplo.com/*"], "js": ["script.js"], "css": ["estilo.css"], "python": "extension.py" }
```

Todo es opcional menos `nombre`. El módulo de Python recibe la API en `activar(aurora)`:

```python
def activar(aurora):
    def saludar():
        aurora.aviso(f"Estás en {aurora.titulo_actual()}")
    aurora.comando("Saludar", saludar, "Ctrl+Alt+S")    # aparece en la paleta (Ctrl+K)
    aurora.al_cargar(lambda url: print("cargada", url))  # cada vez que carga una página
    # también: navegar(url), nueva_pestana(url), ejecutar_js(codigo, callback), url_actual(), portapapeles(texto)
```

También vale copiar un archivo `.user.js` o `.user.css` directamente en la carpeta. Luego pulsa
*Ajustes → Extensiones → Recargar*.

## Estructura del código

```
Aurora.pyw              lanzador (doble clic, sin consola)
aurora/
  app.py                arranque, instancia única y argumentos
  ventana.py            ventana principal (une todo)
  comun.py              constantes, scripts inyectados y utilidades
  widgets.py            botones, interruptores, avisos y barra de progreso animados
  pestanas.py           barra de pestañas, grupos y fijadas
  organizacion.py       grupos, dormir pestañas, pantalla dividida y menús
  omnibox.py · paleta.py  barra de direcciones, paleta de comandos y buscador
  motor.py              bloqueador, páginas y modo responsive
  desarrollo.py · herramientas_dev.py   panel F12 y sus herramientas
  multimedia.py         modo lectura y vídeo flotante
  descargas.py          gestor de descargas
  contrasenas.py · seguridad.py   contraseñas, cifrado, maestra, Hello y generador
  perfiles.py           perfiles, incógnito y gestor de ventanas
  sincronizacion.py · extensiones.py · asistente.py
  ajustes.py · estilo.py   pantalla de ajustes y hoja de estilo
herramientas/           icono y versión del .exe
instalador/aurora.iss   instalador de Inno Setup
```

## Límites conocidos

- Netflix, Disney+ y Spotify Web no reproducen contenido: necesitan Widevine (DRM), que QtWebEngine no trae.
- No es compatible con las extensiones de la Chrome Web Store (sí con los userscripts).
- El vídeo flotante abre una ventanita propia; no usa el picture-in-picture del sistema.
- El asistente usa tu propia clave o un modelo local; Aurora no incluye ningún servicio de IA.
