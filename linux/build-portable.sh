#!/usr/bin/env bash
# Compila el binario de Linux para distribuir y genera el paquete:
#   dist/ToledoDiagnosis-<versión>-linux-x86_64.tar.gz
# Se compila dentro de un contenedor Debian 11 (glibc 2.31) para que funcione en
# Ubuntu 20.04+, Debian 11+, Mint 20+, Fedora, openSUSE, Arch... (un binario
# compilado en una distro nueva no arranca en las antiguas).
# Requisitos: podman o docker. Uso: ./linux/build-portable.sh [versión]
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGEN=docker.io/library/python:3.13-bullseye
VERSION="${1:-$(git describe --tags --always --dirty 2>/dev/null || echo dev)}"
NOMBRE="ToledoDiagnosis-$VERSION-linux-x86_64"

if command -v podman >/dev/null; then
    MOTOR=(podman run --rm -i --security-opt label=disable)
elif command -v docker >/dev/null; then
    MOTOR=(docker run --rm -i --security-opt label=disable --user "$(id -u):$(id -g)" -e HOME=/tmp)
else
    echo "Hace falta podman o docker. Fedora: sudo dnf install podman | Debian/Ubuntu: sudo apt install podman"
    exit 1
fi

mkdir -p dist
rm -f dist/ToledoDiagnosis
echo "Compilando en $IMAGEN (la primera vez descarga la imagen y las dependencias)..."
# El código se pasa por la entrada estándar: así no se toca el .venv ni el build/ del repositorio
tar -c --exclude=.git --exclude=.venv --exclude=build --exclude=dist --exclude=__pycache__ \
    --exclude='*.pdf' . |
    "${MOTOR[@]}" -v "$PWD/dist:/out" "$IMAGEN" bash -c '
        set -e
        mkdir /tmp/src && tar -x -C /tmp/src && cd /tmp/src
        ./build.sh > /tmp/build.log 2>&1 || { tail -40 /tmp/build.log; exit 1; }
        cp dist/ToledoDiagnosis /out/'

echo "Comprobando el binario..."
salida="$(mktemp)"
dist/ToledoDiagnosis --autotest-ia "$salida"
cat "$salida"; echo
if grep -q FALLO "$salida"; then
    rm -f "$salida"
    echo "La autoprueba de IA ha fallado."
    exit 1
fi
rm -f "$salida"

PAQ="$(mktemp -d)"
mkdir "$PAQ/ToledoDiagnosis"
install -m755 dist/ToledoDiagnosis linux/instalar.sh "$PAQ/ToledoDiagnosis/"
install -m644 linux/toledo-diagnosis.desktop linux/LEEME.txt icono.png LICENSE "$PAQ/ToledoDiagnosis/"
tar -czf "dist/$NOMBRE.tar.gz" -C "$PAQ" --owner=0 --group=0 ToledoDiagnosis
rm -rf "$PAQ"

echo
echo "Paquete: $PWD/dist/$NOMBRE.tar.gz"
