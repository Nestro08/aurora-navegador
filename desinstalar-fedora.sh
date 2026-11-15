#!/usr/bin/env bash
# Desinstala Aurora (programa, acceso en el menú e icono). Tus datos se conservan salvo que digas lo contrario.
set -uo pipefail

if [ "$(xdg-settings get default-web-browser 2>/dev/null)" = "aurora.desktop" ]; then
    xdg-settings set default-web-browser org.mozilla.firefox.desktop && echo "Navegador predeterminado: Firefox otra vez"
fi
rm -rf "$HOME/.local/share/aurora-app"
rm -f "$HOME/.local/bin/aurora" "$HOME/.local/share/applications/aurora.desktop" \
      "$HOME/.local/share/icons/hicolor/256x256/apps/aurora.png"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
echo "✓ Aurora desinstalado."

read -r -p "¿Borrar también tus datos (historial, contraseñas, perfiles en ~/.aurora)? [s/N] " respuesta
if [[ "$respuesta" =~ ^[sS]$ ]]; then
    rm -rf "$HOME/.aurora"
    command -v python3 >/dev/null && python3 - <<'EOF' 2>/dev/null
try:
    import keyring
    keyring.delete_password("Aurora", "clave-contrasenas")
except Exception:
    pass
EOF
    echo "✓ Datos borrados."
fi
