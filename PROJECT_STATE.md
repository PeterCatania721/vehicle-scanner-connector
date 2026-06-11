# Project State — 2026-06-11

Snapshot of the **Vehicle Scanner Connector** Odoo 19 module at release **19.0.1.0.5**.

## Repository

| | |
|---|---|
| **Path** | `/Users/petercatania/Projects/vehicle-scanner-connector` |
| **Remote** | `https://github.com/PeterCatania721/vehicle-scanner-connector.git` |
| **Branch** | `main` |
| **Odoo target** | 19.0 |
| **Dependencies** | `sale` (KESI Preventivi fields from `tw_sale_creation` when present) |

## Status

| Area | State |
|---|---|
| Module install | Ready — copy `vehicle_scanner_connector/` to custom addons, or import zip from `dist/` / Desktop |
| Import zip | `dist/vehicle_scanner_connector.zip` (v19.0.1.0.5) — XML/data only; Python webhook modules need addons-path deploy on server |
| Post-install | Auto-loads default panel mappings; set password, customer, and tabella ID in Configuration |
| Preventivi sync | Creates/updates `sale.order` by targa, codice cartella, or telaio; maps BUHDA dents to bolli matrix |
| Bolli mapping | `g*`/`a*`/`p*`/`mm_*`/`sotto*`/`sopra*` from scan panels; BUHDA panel 11 → KESI row 12 |
| HTTP webhooks | Active on fixed registered paths (see README) |
| Configuration UI | Complete — credentials, endpoints, market, preventivi sync, panel/field mappings, parser rules |
| Security | Groups + ACLs for all models |
| Tests | 27 local simulation tests pass; Odoo TransactionCase tests included |
| Local demo | `demo/` Docker Compose on `http://localhost:8069` (DB: `vehicle_scanner_demo`) |

## Distribution

| Artifact | Location |
|---|---|
| Desktop import zip | `~/Desktop/vehicle_scanner_connector.zip` |
| Repo zip | `dist/vehicle_scanner_connector.zip` |
| Build command | `.grok/skills/vehicle-scanner-odoo-deploy-safe/scripts/build-module-zip.sh` |

## API Endpoints

| Path | Type |
|---|---|
| `/budha` | BUHDA (Flask-compatible) |
| `/vehicle_scanner/budha` | BUHDA (namespaced alias) |
| `/vehicle_scanner/receive` | Generic scanner |
| `/api/receive-vehicle-scan` | Generic (legacy alias) |
| `/vehicle_scanner/inbound` | Auto-detect BUHDA or generic |

## Key Files

```
vehicle_scanner_connector/
├── __manifest__.py          # v19.0.1.0.5, post_init_hook
├── constants.py             # Webhook path registry
├── hooks.py                 # Post-install bootstrap
├── controllers/main.py      # HTTP endpoints
├── models/
│   ├── scanner_config.py    # API config + auth + preventivi settings
│   ├── vehicle_scan_service.py  # BUHDA/generic/inbound processing
│   ├── preventivi_sync.py   # sale.order create/update + bolli matrix
│   ├── vehicle_scan_log.py
│   ├── vehicle_scan_panel.py
│   ├── panel_mapping.py     # BUHDA panel → KESI bolli row
│   ├── field_mapping.py
│   └── parser_rule.py
├── security/
├── views/
└── tests/
demo/                        # Local Odoo 19 + kesi_preventivi_demo
dist/                        # Import zip for Apps → Import Module
```

## Verification Commands

```bash
# Local (no Odoo)
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py

# Build desktop/repo zip
./.grok/skills/vehicle-scanner-odoo-deploy-safe/scripts/build-module-zip.sh

# Local Odoo demo (install + upgrade)
cd demo
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d vehicle_scanner_demo \
  -i vehicle_scanner_connector,kesi_preventivi_demo --stop-after-init

# Odoo tests
docker compose run --rm odoo odoo -c /etc/odoo/odoo.conf -d vehicle_scanner_demo \
  --test-tags /vehicle_scanner_connector --stop-after-init
```

## Related Infrastructure

- **Odoo test instance:** `https://kesi19.jcloud.ik-server.com` (DB: `New_test_database`)
- **Odoo production:** `https://kesi19.jcloud.ik-server.com` (DB: `Gestionale_Levabolli`)
- **MCP:** `odoo-kesi19` — test DB default; writes via preview → validate → execute
- **Flask reference:** `../Budha Connection Flask/budha_connect.py`

## Safe production deploy

Grok skill: `.grok/skills/vehicle-scanner-odoo-deploy-safe/`

Run in Grok Build:

```
/vehicle-scanner-odoo-deploy-safe
```

Safe mode = MCP-only deploy (no SSH). `update_list` → install → config writes.
Python webhook modules must exist on the server addons path before install (zip import alone is insufficient).

## Next Steps (optional)

- Deploy module folder to KESI Odoo 19 server addons path, then install on Test DB
- Point BUHDA scanner webhook from Flask `:7721/budha` to Odoo `/budha`
- Rate limiting at reverse proxy