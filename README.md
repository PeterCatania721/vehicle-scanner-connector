# Vehicle Scanner Connector

Odoo 19 addon that receives AI vehicle scan data directly in Odoo, replacing the intermediate Flask bridge for BUHDA hail-damage scanners.

**Project path:** `/Users/petercatania/Projects/vehicle-scanner-connector`

## Quick install (Odoo 19)

### 1. Copy the addon

Copy the inner module folder into your Odoo custom addons directory:

```bash
cp -r /Users/petercatania/Projects/vehicle-scanner-connector/vehicle_scanner_connector \
  /path/to/odoo/custom-addons/
```

The addons path must contain the folder `vehicle_scanner_connector/` (with `__manifest__.py` inside it).

### 2. Configure Odoo

Add the custom addons path to `odoo.conf` if it is not already there:

```ini
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/path/to/custom-addons
```

Restart the Odoo service after changing `addons_path`.

### 3. Install the module

In Odoo:

1. Enable **Developer mode**
2. Go to **Apps** → **Update Apps List**
3. Search for **Vehicle Scanner Connector**
4. Click **Install**

Or from the command line:

```bash
odoo -d your_database -i vehicle_scanner_connector --stop-after-init
```

With tests:

```bash
odoo -d your_database -i vehicle_scanner_connector --test-enable --stop-after-init
```

### 4. Post-install setup

On install, the module automatically:

- Ensures one active scanner configuration exists
- Loads the default KESI panel mappings (1–18)

Then in Odoo:

1. Open **Fleet → Vehicle Scanner → Configuration**
2. Change the default password (`change-me-on-install`)
3. Set **Public Base URL** if `web.base.url` is not your external HTTPS URL
4. Pick the canonical webhook paths shown to scanner vendors

Fleet managers get access automatically via the implied security group.

## Dependencies

- `base`
- `fleet`

No `repair` module required.

## What this module does

Receives hail-damage scan data from external AI scanners (BUHDA and generic JSON payloads) via HTTP webhooks with Basic Auth. Each scan is stored as a log record with panel-level dent data, PDF/image attachments, and optional linkage to a `fleet.vehicle` by license plate.

## API Endpoints

All endpoints use `POST` with `Content-Type: application/json` and `Authorization: Basic <base64(user:pass)>`.

| Endpoint | Purpose |
|---|---|
| `POST /budha` | BUHDA scanner (Flask drop-in replacement) |
| `POST /vehicle_scanner/budha` | BUHDA scanner (namespaced alias) |
| `POST /vehicle_scanner/receive` | Generic scanner format |
| `POST /api/receive-vehicle-scan` | Legacy generic alias |
| `POST /vehicle_scanner/inbound` | Auto-detect BUHDA vs generic |

Canonical URLs are shown in **Fleet → Vehicle Scanner → Configuration**. All alias paths remain active.

### BUHDA example (local simulation)

```bash
curl -X POST http://localhost:8069/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:yourpassword' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"CaseData":{"Vorgangsnummer":"TEST-001","Kennzeichen":"TI12345","Dents":{"1":{"amountSmall":2}}}}'
```

### Generic example

```bash
curl -X POST http://localhost:8069/vehicle_scanner/receive \
  -H "Authorization: Basic $(printf 'ai_scanner:yourpassword' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"plate":"TI12345","scan_id":"scan_001","damage":{"hail":true}}'
```

## UI

- **Fleet → Vehicle Scanner → Scan Logs** — view scans, panels, attachments, and raw JSON
- **Fleet → Vehicle Scanner → Configuration** — credentials, endpoints, market, panel/field mappings, parser rules

## Local tests (no Odoo required)

```bash
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py
```

## Module structure

```
vehicle_scanner_connector/
├── __manifest__.py
├── constants.py                 # Shared webhook path registry
├── hooks.py                     # Post-install: default panels + single active config
├── controllers/main.py          # HTTP webhooks
├── models/
│   ├── scanner_config.py
│   ├── vehicle_scan_log.py
│   ├── vehicle_scan_panel.py
│   ├── vehicle_scan_service.py
│   ├── panel_mapping.py
│   ├── field_mapping.py
│   └── parser_rule.py
├── security/
├── data/
├── views/
└── tests/
    └── test_vehicle_scanner.py  # Odoo TransactionCase tests
```

## Migrating from Flask

Point the BUHDA scanner webhook URL from:

```
http://your-flask-server:7721/budha
```

to:

```
https://your-odoo-server/budha
```

Use the same Basic Auth credentials configured in Odoo.

## Security notes

- Change the default password immediately after install
- Keep **Allow CORS** disabled in production
- Put Odoo behind HTTPS (Nginx/Traefik)
- Consider rate limiting at the reverse proxy
- Credentials are compared with constant-time checks (`hmac.compare_digest`)

## License

LGPL-3