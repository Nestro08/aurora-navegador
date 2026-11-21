# Aurora 4.0

*Por NMM* · **[Web y descargas](https://nestro08.github.io/aurora-navegador/)**

Navegador de escritorio con motor Chromium (QtWebEngine), escrito en Python y PyQt6. Animado, oscuro y con
herramientas para desarrolladores, un gestor de contraseñas, perfiles, sincronización, extensiones y un
asistente con IA.

## Descargar

Todas las versiones están en **[Releases](https://github.com/Nestro08/aurora-navegador/releases/latest)**:

| Sistema | Qué descargar |
|---|---|
| **Windows** | `Aurora-Setup-x.y.exe` (instalador) o `Aurora-x.y-Windows-portable.zip` (sin instalar) |
| **Linux (Fedora)** | `Aurora-x.y-Linux.zip` (mira abajo cómo instalarlo) |

**Actualizaciones:** Aurora mira una vez al día si hay una versión nueva y te avisa. Con un clic en
«Actualizar» se descarga, comprueba que el archivo es el publicado (SHA-256) y se instala solo. Se puede
desactivar en *Ajustes → Acerca de*.

## Instalar en Fedora (Linux)

```bash
unzip Aurora-x.y-Linux.zip && cd Aurora
bash instalar-fedora.sh
```

El script instala Aurora para tu usuario. Con `sudo dnf` instala el PyQt6 de Fedora (su motor Chromium sí
trae los códecs H.264 y AAC) y te ofrece `libavcodec-freeworld` de RPM Fusion, el decodificador que necesitan
los vídeos MP4 de webs como Nike, Instagram o Twitter. El PyQt6 de pip no los trae: esas webs dicen
«your browser doesn't support embedded videos». Después:

- Aparece en **Actividades** con su icono, y con clic derecho tiene *Nueva ventana* e *Incógnito*.
- Se abre desde la terminal con `aurora`.
- Al final te pregunta si quieres que sea tu navegador predeterminado. Para volver a Firefox:
  `xdg-settings set default-web-browser org.mozilla.firefox.desktop`.
- Las versiones nuevas se instalan desde el aviso de Aurora (o volviendo a ejecutar `instalar-fedora.sh`).
- Las pestañas hacen de barra de título (arrastra la zona vacía para mover la ventana, doble clic para
  maximizar).
- Para desinstalar: `bash desinstalar-fedora.sh`.

En Linux las contraseñas se cifran con AES. La clave se guarda en el **llavero del sistema** (GNOME
Keyring o KWallet), que se desbloquea al iniciar sesión. Si no hay llavero, Aurora te avisa de que se
guardan **sin cifrar** (*Ajustes → Contraseñas*) hasta que instales `keyring` y `cryptography`.

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
2. Si tienes [Inno Setup 6](https://jrsoftware.org/isdl.php), crea también `dist\Aurora-Setup-x.y.exe`. El
   instalador añade accesos directos y registra Aurora como navegador. Después puedes elegirlo como
   predeterminado en *Configuración de Windows → Aplicaciones predeterminadas*.
3. Deja en `dist` todo lo de una Release: la versión portátil, el paquete de Linux y `SHA256SUMS.txt`.

## Publicar una versión nueva

1. Cambia la versión en todos los archivos: `python herramientas/version.py 4.1`.
2. En Windows, doble clic en `construir.bat`.
3. En GitHub: **Releases → Draft a new release**. Etiqueta `v4.1`, título `Aurora 4.1`, el texto de
   `dist\NOTAS-4.1.md`, y sube los archivos que indica `construir.bat` (también `SHA256SUMS.txt`).
   Los nombres no se cambian: Aurora los busca así para actualizarse.

Aurora es de **instancia única**: si ya está abierto y pulsas un enlace en otra aplicación, se abre como una
pestaña nueva en la ventana que tienes. Acepta URLs y archivos como argumentos (`Aurora.exe pagina.html`) y
`--incognito`.

## Funciones

| Área | Qué hay |
|---|---|
| Pestañas | Animadas, se reordenan arrastrando, **fijadas**, **grupos de colores con nombre** que se pliegan, indicador de sonido y silenciar (Ctrl+M), **dormir pestañas** inactivas para ahorrar memoria, **pantalla dividida** (Ctrl+Shift+D), menú con clic derecho |
| Navegación | Pantalla de bienvenida al arrancar (desactivable en *Apariencia*), sugerencias en la barra de direcciones con iconos, pestañas abiertas, accesos e historial, paleta de comandos (Ctrl+K), página de inicio animada con **esferas** de accesos que se añaden, editan, colorean y se colocan arrastrándolas donde quieras («⊞ Ordenar esferas» las devuelve a la cuadrícula), buscar en la página (Ctrl+F), **modo lectura** (F9), **vídeo flotante** (Ctrl+Shift+V), gestor de **descargas** con progreso, pausa y reanudación |
| Privacidad | Bloqueador de anuncios y rastreadores (lista ampliada de StevenBlack/hosts, unos 75.000 dominios, que se renueva sola cada semana), Do Not Track y GPC, bloquear cookies de terceros, **ventana de incógnito** (Ctrl+Shift+N), **perfiles** separados (Personal, Uni…) |
| Permisos | Cuando una web pide la **cámara, el micrófono, tu ubicación, enviarte notificaciones o compartir la pantalla** (Meet, Teams, Discord…), Aurora te pregunta y recuerda la respuesta para ese sitio. Se revisan y se olvidan en *Ajustes → Privacidad*. Las notificaciones salen como las del sistema |
| Contraseñas | Guarda y rellena; **generador** al registrarte; cifradas (llavero de GNOME/KDE en Linux, DPAPI en Windows); **contraseña maestra** o **Windows Hello** para verlas, copiarlas o rellenarlas (es un bloqueo de la interfaz, como en Chrome: el cifrado lo pone el llavero o DPAPI de tu sesión); importar el CSV de Chrome o Edge. Los scripts de contraseñas corren aislados de la web: ninguna página puede espiarlos ni fingir que has escrito una contraseña |
| Desarrolladores (F12) | Inspector de Chromium, consola JS, registro de red, **cliente de API** tipo Postman, **auditoría** (accesibilidad, SEO, rendimiento, seguridad, enlaces rotos), modo responsive, User-Agent, CSS en vivo, servidor local con recarga en vivo, **cuentagotas y medidor** (Ctrl+Shift+X), **captura de página completa**, visor de JSON |
| Temas (Ajustes → Temas) | Tienda al estilo de Opera: 7 temas integrados (también claros), más desde la tienda en línea. Cambian los colores de toda la interfaz, el fondo de la página de inicio (animación, imagen o vídeo) y los sonidos. **Editor** para crear los tuyos y compartirlos como archivo `.aurora-tema`. Ver `tienda/README.md` |
| Importar | Desde Chrome, Chromium, Brave, Edge o Vivaldi (*Ajustes → General* o Ctrl+K): marcadores, historial, contraseñas (también las de tu cuenta de Google), buscador y sesiones iniciadas. Las contraseñas se descifran con la clave del navegador y se vuelven a cifrar con la de Aurora |
| Sincronización | Accesos, historial y contraseñas entre tus PCs (Windows y Linux) a través de una carpeta de OneDrive, Dropbox, Syncthing… Con una frase de paso, las contraseñas y el historial viajan cifrados con AES. Se hace en segundo plano (la ventana no se congela aunque la nube tarde) y todo lo que llega se valida |
| Extensiones | Userscripts `.user.js` (compatibles con Tampermonkey), estilos `.user.css` y extensiones en Python con API propia (solo se ejecutan si las apruebas). Incluye 4 de ejemplo |
| Asistente IA (Ctrl+Shift+A) | Elige tu IA (Claude, ChatGPT, Gemini, Copilot, Perplexity o Le Chat) e inicia sesión con tu cuenta en el panel lateral: las conversaciones se guardan en ella. Los botones rápidos (resumir, traducir, explicar) escriben la petición con el texto de la página en el chat; la envías tú con Enter. Avanzado: con clave de API de Claude o cualquier proveedor compatible con OpenAI, incluido **Ollama** (gratis y en tu PC) |
| Ajustes (Ctrl+,) | General, Apariencia (7 colores de acento), Privacidad, Contraseñas, Historial, Accesos, Descargas, Perfiles, Sincronización, Extensiones, Asistente IA, Desarrolladores |

## Dónde se guardan tus datos

En la carpeta `.aurora` de tu usuario (`~/.aurora` en Linux, `C:\Users\<tú>\.aurora` en Windows). La carpeta `perfiles\` contiene los perfiles extra y `extensiones\` las
extensiones. No se borra al desinstalar. En Linux la carpeta y sus archivos solo los puede leer tu usuario
(permisos 700/600).

Si un archivo de datos se daña (un corte de luz, un disco lleno…), Aurora no lo pisa: lo aparta como
`nombre.danado-<fecha>.json` y te avisa, para que puedas recuperarlo.

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

Las extensiones con Python ejecutan código con tus permisos, así que **no se activan solas**: la primera vez
que las enciendes en *Ajustes → Extensiones* Aurora te pide permiso y guarda una huella (SHA-256) de su código.
Si el código cambia, vuelve a pedírtelo. Los archivos del manifest (`js`, `css`, `python`) tienen que estar
dentro de la carpeta de la extensión.

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
  permisos.py           cámara, micrófono, ubicación, notificaciones y compartir pantalla
  motor.py              bloqueador, páginas y modo responsive
  desarrollo.py · herramientas_dev.py   panel F12 y sus herramientas
  multimedia.py         modo lectura y vídeo flotante
  descargas.py          gestor de descargas
  contrasenas.py · seguridad.py   contraseñas, cifrado, maestra, Hello y generador
  perfiles.py           perfiles, incógnito y gestor de ventanas
  sincronizacion.py · extensiones.py · asistente.py
  ajustes.py · estilo.py   pantalla de ajustes y hoja de estilo
  temas.py · tienda_temas.py   temas, sonidos, tienda en línea y editor
  arranque.py           pantalla de bienvenida
  drm.py                Widevine (Netflix, Spotify…) de un navegador instalado
  actualizar.py         aviso de versiones nuevas (GitHub Releases) y actualización con un clic
  importar.py           importar desde Chrome, Brave, Edge…
herramientas/           icono, versión (version.py), preparar_release.py y publicar_tienda.py
tienda/                 temas de la tienda en línea (ver tienda/README.md)
instalador/aurora.iss   instalador de Inno Setup
tests/                  pruebas (pytest)
```

## Pruebas

```bash
pip install -r requirements.txt pytest
python -m pytest tests
```

Funcionan en Linux y en Windows, sin pantalla (Qt en modo `offscreen`) y con una carpeta de usuario temporal:
no tocan tu `.aurora` ni tu llavero. Incluyen un Chromium real para comprobar que las webs no pueden
falsificar ni espiar el puente de contraseñas.

## Límites conocidos

- **Actualizaciones de seguridad.** Aurora usa el Chromium que trae QtWebEngine, y QtWebEngine recibe los
  parches de seguridad de Chrome con semanas o meses de retraso. En Fedora, `dnf upgrade` lo mantiene al día;
  con el PyQt6 de pip (Windows) solo se actualiza reinstalando (`pip install -U PyQt6-WebEngine`). Para la
  banca y webs delicadas, mejor un navegador con actualizaciones automáticas.
- Netflix, Disney+, Spotify… necesitan Widevine (DRM). Aurora no puede incluirlo (es de Google), pero usa el de
  un Chrome, Chromium, Edge, Brave o Vivaldi instalado: con Google Chrome instalado funciona sin hacer nada.
  El estado se ve en *Ajustes → Privacidad y seguridad*. En Windows, Netflix exige además navegadores firmados
  por Google (VMP), así que ahí probablemente no funcione.
- Los vídeos H.264/MP4 solo funcionan con el PyQt6 de Fedora y `libavcodec-freeworld` (lo prepara
  `instalar-fedora.sh`). Con el PyQt6 de pip, en Windows incluido, solo se ven WebM, VP9 y AV1.
- No es compatible con las extensiones de la Chrome Web Store (sí con los userscripts).
- El vídeo flotante abre una ventanita propia; no usa el picture-in-picture del sistema.
- Compartir pantalla en Wayland pasa por el portal del escritorio (GNOME te pregunta qué compartir).
- El asistente usa tu cuenta de la IA que elijas, tu propia clave o un modelo local; Aurora no incluye ningún
  servicio de IA. Algunas webs pueden bloquear «Continuar con Google» dentro del panel: usa correo y contraseña.

## Licencia

Aurora es de **NMM** y es software libre bajo la [GNU GPL v3](LICENSE) (la misma licencia que PyQt6, en la
que se basa): puedes usarlo, estudiarlo, modificarlo y compartirlo, siempre que lo que compartas siga siendo
libre.
