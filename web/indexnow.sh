#!/usr/bin/env bash
# Avisa a Bing (y a los demás buscadores de IndexNow) de todas las URL del sitemap.
# Usar después de ./web/publicar.sh cuando haya páginas nuevas o cambiadas. No se publica.
set -euo pipefail
cd "$(dirname "$0")"
KEY=373bed750456333d70447ae264980c5f
URLS=$(grep -o '<loc>[^<]*</loc>' sitemap.xml | sed 's/<[^>]*>//g' | python3 -c 'import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')
curl -sS -o /dev/null -w "IndexNow: HTTP %{http_code}\n" -X POST https://api.indexnow.org/indexnow \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d "{\"host\":\"www.obd2desk.com\",\"key\":\"$KEY\",\"keyLocation\":\"https://www.obd2desk.com/$KEY.txt\",\"urlList\":$URLS}"
