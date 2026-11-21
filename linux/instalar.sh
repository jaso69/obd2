#!/usr/bin/env bash
# Instala Toledo Diagnosis para el usuario actual (sin sudo):
#   ~/.local/bin/ToledoDiagnosis, icono y lanzador en el menú de aplicaciones.
# Uso: ./instalar.sh [ruta/al/ejecutable]   instala (por defecto el ejecutable junto a
#                                           este script o, en el repositorio, dist/ToledoDiagnosis)
#      ./instalar.sh --desinstalar          lo quita (no borra la configuración ni los CSV)
# Funciona desde el repositorio (linux/instalar.sh) y desde el paquete .tar.gz descomprimido.
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"

BIN="$HOME/.local/bin/ToledoDiagnosis"
ICONO="$HOME/.local/share/icons/hicolor/256x256/apps/toledo-diagnosis.png"
LANZADOR="$HOME/.local/share/applications/toledo-diagnosis.desktop"

if [ "${1:-}" = "--desinstalar" ]; then
    rm -f "$BIN" "$ICONO" "$LANZADOR"
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    echo "Desinstalado. La configuración sigue en ~/.config/ToledoDiagnosis (bórrala si quieres)."
    exit 0
fi

primero() { for f in "$@"; do [ -f "$f" ] && { echo "$f"; return; }; done; echo "$1"; }
EXE="${1:-$(primero "$D/ToledoDiagnosis" "$D/../dist/ToledoDiagnosis")}"
PNG="$(primero "$D/icono.png" "$D/../icono.png")"
if [ ! -f "$EXE" ]; then
    echo "No encuentro el ejecutable ($EXE). Compílalo con ./build.sh o indica su ruta."
    exit 1
fi

install -Dm755 "$EXE" "$BIN"
install -Dm644 "$PNG" "$ICONO"
install -Dm644 "$D/toledo-diagnosis.desktop" "$LANZADOR"
sed -i "s|^Exec=.*|Exec=$BIN|" "$LANZADOR"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
touch "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Instalado. Aparecerá en el menú como «Toledo Diagnosis» (o ejecuta $BIN)."

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
    echo "IMPORTANTE: para usar el cable o el ELM327 tu usuario debe estar en el grupo $GRUPO:"
    echo "    sudo usermod -aG $GRUPO \$USER"
    echo "y después cerrar sesión y volver a entrar."
fi

# En Ubuntu/Mint, brltty (lector braille) se apodera de muchos adaptadores USB-serie
if systemctl is-enabled brltty-udev.service >/dev/null 2>&1 || \
   { command -v dpkg >/dev/null && dpkg -s brltty >/dev/null 2>&1; }; then
    echo
    echo "AVISO: está instalado brltty, que suele capturar los adaptadores USB-serie (CH340, FTDI)"
    echo "y hace que /dev/ttyUSB0 desaparezca al conectarlo. Si no usas una línea braille:"
    echo "    sudo apt remove brltty"
fi
