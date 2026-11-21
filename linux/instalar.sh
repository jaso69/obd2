#!/usr/bin/env bash
# Instala Toledo Diagnosis para el usuario actual (sin sudo):
#   ~/.local/bin/ToledoDiagnosis, icono y lanzador en el menú de aplicaciones.
# Uso: ./linux/instalar.sh [ruta/al/ejecutable]   (por defecto dist/ToledoDiagnosis)
set -euo pipefail
cd "$(dirname "$0")/.."

EXE="${1:-dist/ToledoDiagnosis}"
if [ ! -f "$EXE" ]; then
    echo "No encuentro $EXE. Compílalo con ./build.sh o indica la ruta del ejecutable descargado."
    exit 1
fi

install -Dm755 "$EXE" "$HOME/.local/bin/ToledoDiagnosis"
install -Dm644 icono.png "$HOME/.local/share/icons/hicolor/256x256/apps/toledo-diagnosis.png"
install -Dm644 linux/toledo-diagnosis.desktop "$HOME/.local/share/applications/toledo-diagnosis.desktop"
sed -i "s|^Exec=.*|Exec=$HOME/.local/bin/ToledoDiagnosis|" "$HOME/.local/share/applications/toledo-diagnosis.desktop"
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo "Instalado. Aparecerá en el menú como «Toledo Diagnosis»."
if ! id -nG "$USER" | grep -qw dialout; then
    echo
    echo "IMPORTANTE: para usar el cable o el ELM327 tu usuario debe estar en el grupo dialout:"
    echo "    sudo usermod -aG dialout \$USER"
    echo "y después cerrar sesión y volver a entrar."
fi
