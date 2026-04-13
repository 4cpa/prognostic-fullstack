#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# export-openapi.sh
# Exportiert das OpenAPI-Schema aus dem laufenden Backend (oder lokal)
# und speichert es als docs/openapi.json.
#
# Verwendung:
#   ./scripts/export-openapi.sh [BASE_URL]
#
# Beispiele:
#   ./scripts/export-openapi.sh                          # lokal :8000
#   ./scripts/export-openapi.sh http://localhost:8000
# ---------------------------------------------------------------------------
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
OUT_DIR="docs"
OUT_FILE="${OUT_DIR}/openapi.json"

mkdir -p "$OUT_DIR"

echo "Exportiere OpenAPI-Schema von ${BASE_URL}/openapi.json ..."
curl -fsSL "${BASE_URL}/openapi.json" | python3 -m json.tool > "$OUT_FILE"

echo "Schema gespeichert: ${OUT_FILE}"
echo "Endpunkte:"
python3 -c "
import json, sys
data = json.load(open('${OUT_FILE}'))
paths = data.get('paths', {})
for path, methods in sorted(paths.items()):
    for method in methods:
        print(f'  {method.upper():<7} {path}')
"
