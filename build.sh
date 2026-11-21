#!/usr/bin/env bash
# Genera dist/ToledoDiagnosis (ejecutable único para Linux, sin consola).
# Requisitos (Fedora): sudo dnf install python3 python3-tkinter
# Requisitos (Debian/Ubuntu): sudo apt install python3 python3-venv python3-tk
set -euo pipefail
cd "$(dirname "$0")"

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Falta tkinter. Fedora: sudo dnf install python3-tkinter | Debian/Ubuntu: sudo apt install python3-tk"
    exit 1
fi

python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt pyinstaller

.venv/bin/pyinstaller --noconfirm --clean --onefile --windowed \
  --name ToledoDiagnosis \
  --add-data "$PWD/icono.png:." \
  --add-data "$PWD/icono.ico:." \
  --hidden-import simulador \
  --hidden-import serial.tools.list_ports \
  --collect-submodules anthropic \
  --collect-submodules openai \
  --distpath dist --workpath build --specpath build \
  gui.py

echo
echo "Ejecutable: $PWD/dist/ToledoDiagnosis"
echo "Para instalarlo en el menú de aplicaciones: ./linux/instalar.sh"
