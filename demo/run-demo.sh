#!/usr/bin/env bash
# Local Odoo 19 demo for vehicle_scanner_connector.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

DB_NAME="vehicle_scanner_demo"
ODOO_URL="http://localhost:8069"
SCANNER_USER="ai_scanner"
SCANNER_PASS="demo-secret-2026"
COMPOSE="docker compose"

log() { printf '\n==> %s\n' "$*"; }

wait_for_odoo() {
  local attempt=0
  until curl -sf "$ODOO_URL/web/health" >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [[ $attempt -ge 90 ]]; then
      echo "Odoo did not become ready on $ODOO_URL" >&2
      return 1
    fi
    sleep 2
  done
}

module_state() {
  local module_name="$1"
  $COMPOSE exec -T db psql -U odoo -d "$DB_NAME" -tAc \
    "SELECT state FROM ir_module_module WHERE name='${module_name}'" 2>/dev/null || true
}

install_or_upgrade_module() {
  local module_name="$1"
  local state
  state="$(module_state "$module_name")"
  if [[ "$state" == "installed" ]]; then
    log "Module $module_name already installed — upgrading"
    $COMPOSE run --rm odoo odoo \
      -c /etc/odoo/odoo.conf \
      -d "$DB_NAME" \
      -u "$module_name" \
      --without-demo \
      --stop-after-init
  else
    log "Installing $module_name on database $DB_NAME"
    $COMPOSE run --rm odoo odoo \
      -c /etc/odoo/odoo.conf \
      -d "$DB_NAME" \
      -i "$module_name" \
      --without-demo \
      --stop-after-init
  fi
}



configure_scanner() {
  log "Setting scanner password and public base URL"
  $COMPOSE run --rm odoo odoo shell \
    -c /etc/odoo/odoo.conf \
    -d "$DB_NAME" \
    --stop-after-init <<'PY'
config = env['vehicle.scanner.config'].sudo().get_active_config()
partner = env.ref('kesi_preventivi_demo.partner_customer_demo', raise_if_not_found=False)
product = env.ref('kesi_preventivi_demo.product_repair_hail', raise_if_not_found=False)
boli = env.ref('kesi_preventivi_demo.boli_product_standard', raise_if_not_found=False)
vals = {
    'password': 'demo-secret-2026',
    'api_base_url': 'http://localhost:8069',
    'enable_preventivi_sync': True,
    'preventivi_user_id': env.ref('base.user_admin').id,
}
if partner:
    vals['preventivi_partner_id'] = partner.id
if product:
    vals['preventivi_product_id'] = product.id
if boli:
    vals['preventivi_boli_product_id'] = boli.id
config.write(vals)
if not config.panel_mapping_ids:
    config.action_load_default_panel_mappings()
env.cr.commit()
print(f'Config id={config.id} budha_url={config.budha_api_url} preventivi_user={config.preventivi_user_id.name}')
PY
  $COMPOSE restart odoo
  wait_for_odoo
}

post_budha_scan() {
  curl -sS -w "\nHTTP %{http_code}\n" \
    -X POST "$ODOO_URL/budha" \
    -H "Authorization: Basic $(printf '%s:%s' "$SCANNER_USER" "$SCANNER_PASS" | base64)" \
    -H "Content-Type: application/json" \
    -d '{
      "CaseData": {
        "Vorgangsnummer": "DOCKER-DEMO-001",
        "Kennzeichen": "ti 12345",
        "Fahrzeug": "BMW 320d (docker demo)",
        "Dents": {
          "1": {"amountSmall": 3, "amountMedium": 1, "amountLarge": 0, "glue": true},
          "6": {"amountSmall": 2, "amountLarge": 1, "alu": true, "ptp": true}
        }
      }
    }'
}

post_generic_scan() {
  curl -sS -w "\nHTTP %{http_code}\n" \
    -X POST "$ODOO_URL/vehicle_scanner/receive" \
    -H "Authorization: Basic $(printf '%s:%s' "$SCANNER_USER" "$SCANNER_PASS" | base64)" \
    -H "Content-Type: application/json" \
    -d '{
      "plate": "zh 99999",
      "scan_id": "docker-generic-001",
      "damage": {"hail": true, "severity": "medium"}
    }'
}

show_scan_logs() {
  log "Scan logs stored in Odoo"
  $COMPOSE run --rm odoo odoo shell \
    -c /etc/odoo/odoo.conf \
    -d "$DB_NAME" \
    --stop-after-init <<'PY'
logs = env['vehicle.scan.log'].sudo().search([], order='id desc', limit=10)
for log in logs:
    panels = ', '.join(
        f"#{p.panel_index} small={p.amount_small} medium={p.amount_medium} large={p.amount_large}"
        for p in log.panel_ids
    ) or '(no panels)'
    print(f"- id={log.id} source={log.source} plate={log.license_plate} case={log.case_number or '-'} panels=[{panels}]")
PY
}

main() {
  log "Starting Odoo 19 + PostgreSQL"
  $COMPOSE up -d --wait

  wait_for_odoo

  install_or_upgrade_module vehicle_scanner_connector
  install_or_upgrade_module kesi_preventivi_demo

  $COMPOSE up -d odoo
  wait_for_odoo

  configure_scanner

  log "BUHDA webhook demo (POST /budha)"
  post_budha_scan

  log "Generic webhook demo (POST /vehicle_scanner/receive)"
  post_generic_scan

  show_scan_logs

  log "Demo ready"
  echo "  Odoo UI:      $ODOO_URL"
  echo "  Database:     $DB_NAME"
  echo "  Master pwd:   admin"
  echo "  Scanner user: $SCANNER_USER"
  echo "  Scanner pass: $SCANNER_PASS"
  echo "  Menu:         Preventivi (quotations) / Vehicle Scanner → Scan Logs"
  echo
  echo "Stop demo: docker compose -f demo/docker-compose.yml down"
}

main "$@"