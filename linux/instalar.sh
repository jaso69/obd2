#!/usr/bin/env bash
# Instala OBD2Desk para el usuario actual (sin sudo):
#   ~/.local/bin/OBD2Desk, icono y lanzador en el menú de aplicaciones.
# Uso: ./instalar.sh [ruta/al/ejecutable]   instala (por defecto el ejecutable junto a
#                                           este script o, en el repositorio, dist/OBD2Desk)
#      ./instalar.sh --desinstalar          lo quita (no borra la configuración ni los CSV)
# Funciona desde el repositorio (linux/instalar.sh) y desde el paquete .tar.gz descomprimido.
# Si encuentra la versión anterior (Toledo Diagnosis), la quita del menú; la configuración
# la copia el propio programa la primera vez que se abre.
# Mensajes en español si el sistema está en español; si no, en inglés.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"

case "${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}" in
    es*|ca*|gl*|eu*) ES=1 ;;
    *) ES=0 ;;
esac
msg() { if [ "$ES" = 1 ]; then echo "$1"; else echo "$2"; fi; }

BIN="$HOME/.local/bin/OBD2Desk"
ICONO="$HOME/.local/share/icons/hicolor/256x256/apps/obd2desk.png"
LANZADOR="$HOME/.local/share/applications/obd2desk.desktop"
# Versión anterior (hasta la v0.3.0 se llamaba Toledo Diagnosis)
ANTIGUOS=("$HOME/.local/bin/ToledoDiagnosis"
          "$HOME/.local/share/icons/hicolor/256x256/apps/toledo-diagnosis.png"
          "$HOME/.local/share/applications/toledo-diagnosis.desktop")

if [ "${1:-}" = "--desinstalar" ] || [ "${1:-}" = "--uninstall" ]; then
    rm -f "$BIN" "$ICONO" "$LANZADOR" "${ANTIGUOS[@]}"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    msg "Desinstalado. La configuración sigue en ~/.config/OBD2Desk (bórrala si quieres)." \
        "Uninstalled. The settings remain in ~/.config/OBD2Desk (delete it if you want)."
    exit 0
fi

primero() { for f in "$@"; do [ -f "$f" ] && { echo "$f"; return; }; done; echo "$1"; }
EXE="${1:-$(primero "$D/OBD2Desk" "$D/../dist/OBD2Desk")}"
PNG="$(primero "$D/icono.png" "$D/../icono.png")"
if [ ! -f "$EXE" ]; then
    msg "No encuentro el ejecutable ($EXE). Compílalo con ./build.sh o indica su ruta." \
        "Executable not found ($EXE). Build it with ./build.sh or give its path."
    exit 1
fi

install -Dm755 "$EXE" "$BIN"
install -Dm644 "$PNG" "$ICONO"
install -Dm644 "$D/obd2desk.desktop" "$LANZADOR"
sed -i "s|^Exec=.*|Exec=$BIN|" "$LANZADOR"
if [ -e "${ANTIGUOS[0]}" ] || [ -e "${ANTIGUOS[2]}" ]; then
    rm -f "${ANTIGUOS[@]}"
    msg "Quitada la versión anterior (Toledo Diagnosis). Tu configuración se copiará al abrir OBD2Desk." \
        "Removed the previous version (Toledo Diagnosis). Your settings will be copied when OBD2Desk starts."
fi
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
touch "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

msg "Instalado. Aparecerá en el menú como «OBD2Desk» (o ejecuta $BIN)." \
    "Installed. It will appear in the menu as \"OBD2Desk\" (or run $BIN)."

# Permiso para el puerto serie: el grupo del puerto (dialout; uucp en Arch)
GRUPO=dialout
for p in /dev/ttyUSB0 /dev/ttyACM0 /dev/ttyS0; do
    if [ -e "$p" ]; then
        g="$(stat -c %G "$p")"
        [ "$g" != root ] && { GRUPO="$g"; break; }
    fi
done
if ! id -nG "$USER" | grep -qw "$GRUPO"; then
    echo
    msg "IMPORTANTE: para usar el cable o el ELM327 tu usuario debe estar en el grupo $GRUPO:" \
        "IMPORTANT: to use the cable or the ELM327 your user must be in the $GRUPO group:"
    echo "    sudo usermod -aG $GRUPO \$USER"
    msg "y después cerrar sesión y volver a entrar." "then log out and back in."
fi

# En Ubuntu/Mint, brltty (lector braille) se apodera de muchos adaptadores USB-serie
if systemctl is-enabled brltty-udev.service >/dev/null 2>&1 || \
   { command -v dpkg >/dev/null && dpkg -s brltty >/dev/null 2>&1; }; then
    echo
    msg "AVISO: está instalado brltty, que suele capturar los adaptadores USB-serie (CH340, FTDI)" \
        "WARNING: brltty is installed; it often grabs USB-serial adapters (CH340, FTDI)"
    msg "y hace que /dev/ttyUSB0 desaparezca al conectarlo. Si no usas una línea braille:" \
        "and makes /dev/ttyUSB0 disappear when plugged in. If you don't use a braille display:"
    echo "    sudo apt remove brltty"
fi
