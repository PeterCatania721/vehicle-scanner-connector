#!/bin/zsh
set -euo pipefail

# Install vehicle_scanner_connector on KESI Odoo 19 test DB via JSON-2 API.
# Prerequisite: module folder must already exist on the server addons path
# (zip import does NOT work for Python webhook modules).

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
DB="${ODOO_DB:-New_test_database}"
URL="${ODOO_URL:-https://kesi19.jcloud.ik-server.com}"

BWS_PROJECT_ID="${BWS_GROK_PROJECT_ID:-bc60dc7c-2fd6-4368-9cc2-b45e00b30179}"
token=$(security find-generic-password -s bws-access-token -w 2>/dev/null || true)
if [[ -z "$token" ]]; then
  echo "Error: bws token missing (service: bws-access-token)" >&2
  exit 1
fi

export BWS_ACCESS_TOKEN="$token"
export ODOO_URL="$URL"
export ODOO_DB="$DB"

echo "Installing vehicle_scanner_connector on $URL (database=$DB)"
bws run --project-id "$BWS_PROJECT_ID" -- uvx python "$ROOT/.grok/tmp/deploy_test_db.py"