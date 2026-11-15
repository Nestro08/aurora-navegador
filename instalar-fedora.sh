#!/usr/bin/env bash
# Instala Aurora para tu usuario en Fedora (y otras distros con GNOME/KDE).
# Uso:  bash instalar-fedora.sh       (vuelve a ejecutarlo para actualizar)
set -euo pipefail

ORIGEN="$(cd "$(dirname "$0")" && pwd)"
DESTINO="$HOME/.local/share/aurora-app"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONOS="$HOME/.local/share/icons/hicolor"

echo
echo "  ===  Instalando Aurora  ==="
echo

command -v python3 >/dev/null || { echo "Falta Python 3:  sudo dnf install python3"; exit 1; }

# Con dnf se usa el PyQt6 de Fedora: su motor Chromium trae H.264/AAC (vídeos MP4 de Nike, Instagram,
# Twitter…). El PyQt6 de pip viene compilado sin esos códecs y esas webs dicen que el navegador no los soporta.
SISTEMA=0
if command -v dnf >/dev/null && command -v rpm >/dev/null; then
    SISTEMA=1
    faltan=()
    for paquete in python3-pyqt6 python3-pyqt6-webengine python3-cryptography python3-keyring \
                   python3-secretstorage xcb-util-cursor libxkbcommon-x11 nss; do
        rpm -q "$paquete" >/dev/null 2>&1 || faltan+=("$paquete")
    done
    if [ ${#faltan[@]} -gt 0 ]; then
        echo "Instalando paquetes de Fedora: ${faltan[*]} (te pedirá tu contraseña)"
        sudo dnf install -y "${faltan[@]}"
    fi

    # El decodificador H.264 no está en el ffmpeg de Fedora (patentes): lo da RPM Fusion
    if ! rpm -q libavcodec-freeworld >/dev/null 2>&1 && ! rpm -q ffmpeg-libs >/dev/null 2>&1; then
        echo
        echo "Para ver vídeos H.264 (MP4) hace falta «libavcodec-freeworld» del repositorio RPM Fusion."
        read -r -p "¿Instalarlo (y activar RPM Fusion free si no lo está)? [S/n] " respuesta
        if [[ ! "$respuesta" =~ ^[nN]$ ]]; then
            if ! rpm -q rpmfusion-free-release >/dev/null 2>&1; then
                sudo dnf install -y "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm"
            fi
            sudo dnf install -y libavcodec-freeworld
        fi
    fi
fi

mkdir -p "$DESTINO" "$BIN" "$APPS" "$ICONOS/256x256/apps"
rm -rf "$DESTINO/aurora"
cp -r "$ORIGEN/aurora" "$ORIGEN/Aurora.pyw" "$ORIGEN/requirements.txt" "$ORIGEN/recursos" "$DESTINO/"
find "$DESTINO" -name "__pycache__" -type d -prune -exec rm -rf {} +

if [ "$SISTEMA" = 1 ]; then
    # entorno que ve los paquetes de Fedora; se rehace si es uno antiguo con el PyQt6 de pip dentro
    if ! grep -qs "include-system-site-packages = true" "$DESTINO/venv/pyvenv.cfg" \
            || [ -d "$DESTINO"/venv/lib/python3*/site-packages/PyQt6 ]; then
        echo "Preparando el entorno de Python…"
        rm -rf "$DESTINO/venv"
        python3 -m venv --system-site-packages "$DESTINO/venv"
    fi
else
    if [ ! -x "$DESTINO/venv/bin/python" ]; then
        echo "Creando el entorno de Python…"
        python3 -m venv "$DESTINO/venv"
    fi
    echo "Descargando PyQt6 y el motor Chromium (la primera vez tarda unos minutos)…"
    echo "Aviso: el PyQt6 de pip no reproduce vídeos H.264/MP4."
    "$DESTINO/venv/bin/pip" install --upgrade pip -q
    "$DESTINO/venv/bin/pip" install -q -r "$DESTINO/requirements.txt" keyring
fi
# -s: sin ~/.local, donde puede haber un PyQt6 de pip (sin códecs) que taparía el de Fedora
"$DESTINO/venv/bin/python" -s -c "import PyQt6.QtWebEngineWidgets, cryptography, keyring" \
    || { echo "No se pudo preparar PyQt6. Revisa los mensajes de arriba."; exit 1; }

cat > "$BIN/aurora" <<EOF
#!/usr/bin/env bash
exec "$DESTINO/venv/bin/python" -s "$DESTINO/Aurora.pyw" "\$@"
EOF
chmod +x "$BIN/aurora"

cp "$ORIGEN/recursos/aurora.png" "$ICONOS/256x256/apps/aurora.png"

cat > "$APPS/aurora.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Aurora
GenericName=Navegador web
Comment=Navegador rápido y bonito con herramientas para desarrolladores
Exec=$BIN/aurora %U
Icon=aurora
Terminal=false
Categories=Network;WebBrowser;
Keywords=web;navegador;internet;browser;
MimeType=text/html;text/xml;application/xhtml+xml;x-scheme-handler/http;x-scheme-handler/https;application/pdf;image/svg+xml;
StartupNotify=true
StartupWMClass=aurora
Actions=nueva-ventana;incognito;

[Desktop Action nueva-ventana]
Name=Nueva ventana
Exec=$BIN/aurora

[Desktop Action incognito]
Name=Nueva ventana de incógnito
Exec=$BIN/aurora --incognito
EOF

update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache -f -t "$ICONOS" 2>/dev/null || true

echo
echo "  ✓ Aurora instalado. Búscalo en Actividades (tecla Super) o ejecuta:  aurora"
echo
read -r -p "¿Quieres que Aurora sea tu navegador predeterminado? [s/N] " respuesta
if [[ "$respuesta" =~ ^[sS]$ ]]; then
    xdg-settings set default-web-browser aurora.desktop
    echo "  ✓ Hecho. Para volver a Firefox:"
    echo "      xdg-settings set default-web-browser org.mozilla.firefox.desktop"
fi
echo
