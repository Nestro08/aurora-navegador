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

# Librerías del sistema que Qt puede necesitar (sobre todo en sesiones X11)
if command -v dnf >/dev/null && command -v rpm >/dev/null; then
    faltan=()
    for paquete in xcb-util-cursor libxkbcommon-x11 nss; do
        rpm -q "$paquete" >/dev/null 2>&1 || faltan+=("$paquete")
    done
    if [ ${#faltan[@]} -gt 0 ]; then
        echo "Instalando librerías del sistema: ${faltan[*]} (te pedirá tu contraseña)"
        sudo dnf install -y "${faltan[@]}"
    fi
fi

mkdir -p "$DESTINO" "$BIN" "$APPS" "$ICONOS/256x256/apps"
rm -rf "$DESTINO/aurora"
cp -r "$ORIGEN/aurora" "$ORIGEN/Aurora.pyw" "$ORIGEN/requirements.txt" "$ORIGEN/recursos" "$DESTINO/"
find "$DESTINO" -name "__pycache__" -type d -prune -exec rm -rf {} +

if [ ! -x "$DESTINO/venv/bin/python" ]; then
    echo "Creando el entorno de Python…"
    python3 -m venv "$DESTINO/venv"
fi
echo "Descargando PyQt6 y el motor Chromium (la primera vez tarda unos minutos)…"
"$DESTINO/venv/bin/pip" install --upgrade pip -q
"$DESTINO/venv/bin/pip" install -q -r "$DESTINO/requirements.txt" keyring

cat > "$BIN/aurora" <<EOF
#!/usr/bin/env bash
exec "$DESTINO/venv/bin/python" "$DESTINO/Aurora.pyw" "\$@"
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
