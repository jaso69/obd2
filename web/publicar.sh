#!/usr/bin/env bash
# Publica la web en https://www.obd2desk.com: sustituye el contenido del repositorio
# jaso69/obd2desk (enlazado con Vercel) por esta carpeta y lo sube con un commit normal
# (el contenido anterior queda en el historial). Uso: ./web/publicar.sh ["mensaje"]
set -euo pipefail
cd "$(dirname "$0")"

REPO=https://github.com/jaso69/obd2desk.git
MENSAJE="${1:-Actualizar la web de OBD2Desk}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

git clone -q "$REPO" "$TMP/web"
cd "$TMP/web"
git rm -rq --ignore-unmatch .            # todo fuera; se copia la web encima
cd - >/dev/null
tar -c --exclude=capturas.py --exclude=publicar.sh --exclude=__pycache__ . | tar -x -C "$TMP/web"
cd "$TMP/web"
git add -A
if git diff --cached --quiet; then
    echo "La web publicada ya está al día."
    exit 0
fi
git status --short
git commit -q -m "$MENSAJE"
git push -q origin HEAD:main
echo "Subido a $REPO; Vercel la publicará en https://www.obd2desk.com en un minuto."
