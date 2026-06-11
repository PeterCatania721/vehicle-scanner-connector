#!/bin/zsh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
OUT="${ROOT}/dist/vehicle_scanner_connector.zip"
MODULE="${ROOT}/vehicle_scanner_connector"

mkdir -p "${ROOT}/dist"
rm -f "$OUT"

if [[ ! -f "${MODULE}/__manifest__.py" ]]; then
  echo "Error: ${MODULE}/__manifest__.py not found" >&2
  exit 1
fi

cd "$ROOT"
zip -r "$OUT" "$(basename "$MODULE")" \
  -x '*/__pycache__/*' \
  -x '*.pyc' \
  -x '.DS_Store'

echo "Created: $OUT"
echo "Size: $(wc -c < "$OUT") bytes"