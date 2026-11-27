#!/usr/bin/env bash
# Compila el binario de Linux para distribuir y genera el paquete:
#   dist/OBD2Desk-<versión>-linux-x86_64.tar.gz
# Se compila dentro de un contenedor Debian 11 (glibc 2.31) para que funcione en
# Ubuntu 20.04+, Debian 11+, Mint 20+, Fedora, openSUSE, Arch... (un binario
# compilado en una distro nueva no arranca en las antiguas).
# Requisitos: podman o docker. Uso: ./linux/build-portable.sh [versión]
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGEN=docker.io/library/python:3.13-bullseye
VERSION="${1:-$(git describe --tags --always --dirty 2>/dev/null || echo dev)}"
NOMBRE="OBD2Desk-$VERSION-linux-x86_64"

if command -v podman >/dev/null; then
    MOTOR=(podman run --rm -i --security-opt label=disable)
elif command -v docker >/dev/null; then
    MOTOR=(docker run --rm -i --security-opt label=disable --user "$(id -u):$(id -g)" -e HOME=/tmp)
else
    echo "Hace falta podman o docker. Fedora: sudo dnf install podman | Debian/Ubuntu: sudo apt install podman"
    exit 1
fi

mkdir -p dist
rm -f dist/OBD2Desk
echo "Compilando en $IMAGEN (la primera vez descarga la imagen y las dependencias)..."
# El código se pasa por la entrada estándar: así no se toca el .venv ni el build/ del repositorio
tar -c --exclude=.git --exclude=.venv --exclude=build --exclude=dist --exclude=__pycache__ \
    --exclude='*.pdf' . |
    "${MOTOR[@]}" -v "$PWD/dist:/out" "$IMAGEN" bash -c '
        set -e
        mkdir /tmp/src && tar -x -C /tmp/src && cd /tmp/src
        ./build.sh > /tmp/build.log 2>&1 || { tail -40 /tmp/build.log; exit 1; }
        cp dist/OBD2Desk /out/'

echo "Comprobando el binario..."
salida="$(mktemp)"
dist/OBD2Desk --autotest-ia "$salida"
cat "$salida"; echo
if grep -q FALLO "$salida"; then
    rm -f "$salida"
    echo "La autoprueba de IA ha fallado."
    exit 1
fi
rm -f "$salida"

PAQ="$(mktemp -d)"
mkdir "$PAQ/OBD2Desk"
install -m755 dist/OBD2Desk linux/instalar.sh "$PAQ/OBD2Desk/"
install -m644 linux/obd2desk.desktop linux/LEEME.txt linux/README.txt icono.png LICENSE "$PAQ/OBD2Desk/"
tar -czf "dist/$NOMBRE.tar.gz" -C "$PAQ" --owner=0 --group=0 OBD2Desk
rm -rf "$PAQ"

echo
echo "Paquete: $PWD/dist/$NOMBRE.tar.gz"
