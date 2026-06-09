# Vehicle Scanner Connector

Odoo 19+ addon that receives AI vehicle scan data directly in Odoo, replacing the intermediate Flask bridge for BUHDA hail-damage scanners.

**Project path:** `/Users/petercatania/Projects/vehicle-scanner-connector`

Based on the working patterns from [Budha Connection Flask](../Budha%20Connection%20Flask/budha_connect.py) — the module mirrors that integration but runs natively inside Odoo, with no separate Flask server required.

## What this module does

The addon receives hail-damage scan data from external AI scanners (BUHDA and generic JSON payloads) via HTTP webhooks with Basic Auth. Each scan is stored as a log record with panel-level dent data, PDF/image attachments, and optional linkage to a `fleet.vehicle` by license plate.

## Design choices (based on what works)

| Aspect | Solution |
|---|---|
| **Transport** | `type='http'` with plain JSON (not Odoo JSON-RPC) — same approach as Flask |
| **BUHDA endpoint** | `POST /budha` — drop-in replacement for Flask on port 7721 |
| **Auth** | Basic Auth via configurable `vehicle.scanner.config` model (no hard-coded passwords) |
| **Payload parsing** | Same normalization as Flask: `CaseData` wrapper, arrays, raw objects |
| **PDFs** | `overviewPDF` + `attachmentsPDF` saved as `ir.attachment` |
| **Panels** | KESI panel map 1–18 (Parafango Ant Sx, etc.) from Flask `PANELS` dict |
| **Fleet link** | Lookup by `license_plate` (`Kennzeichen` / `plate` / `targa`) |

## Features

- **BUHDA-compatible webhook** — same JSON payload and Basic Auth as the Flask `/budha` endpoint
- **Generic scanner API** — simple JSON format for custom scanners
- **Scan logs** — stores raw JSON, panel-level dent data, and PDF/image attachments
- **Fleet integration** — links scans to `fleet.vehicle` by license plate
- **Configurable credentials** — no hard-coded passwords in code

## UI

After installation, use these menus in Odoo:

- **Fleet → Vehicle Scanner → Scan Logs** — view scans, panels, attachments, and raw JSON
- **Fleet → Vehicle Scanner → Configuration** — set API credentials and behavior options

Fleet managers automatically get access via the implied security group.

## Installation

1. Copy `vehicle_scanner_connector/` into your Odoo addons path:

   ```bash
   cp -r /Users/petercatania/Projects/vehicle-scanner-connector/vehicle_scanner_connector \
     /path/to/odoo/custom-addons/
   ```

2. Add the addons path to `odoo.conf` if needed:

   ```ini
   addons_path = /usr/lib/python3/dist-packages/odoo/addons,/path/to/custom-addons
   ```

3. Restart Odoo and update the Apps list.

4. Install **Vehicle Scanner Connector**.

5. Open **Fleet → Vehicle Scanner → Configuration** and set username/password (change the default password immediately).

## API Endpoints

All endpoints use `POST` with `Content-Type: application/json` and `Authorization: Basic <base64(user:pass)>`.

| Endpoint | Purpose |
|---|---|
| `POST /budha` | BUHDA scanner (Flask drop-in replacement) |
| `POST /vehicle_scanner/budha` | BUHDA scanner (namespaced) |
| `POST /vehicle_scanner/receive` | Generic scanner format |
| `POST /api/receive-vehicle-scan` | Legacy generic endpoint |

### BUHDA example

```bash
curl -X POST https://your-odoo.example.com/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:yourpassword' | base64)" \
  -H "Content-Type: application/json" \
  -d @sample_budha.json
```

Accepted payload shapes (same as Flask):

- `{"CaseData": {...}}`
- `[{"CaseData": {...}}, ...]`
- Raw `CaseData` object with `Vorgangsnummer`

### Generic example

```bash
curl -X POST https://your-odoo.example.com/vehicle_scanner/receive \
  -H "Authorization: Basic $(printf 'ai_scanner:yourpassword' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "plate": "TI12345",
    "scan_id": "scan_001",
    "damage": {"hail": true, "severity": "medium"},
    "images": [
      {"filename": "foto1.jpg", "data": "base64string..."}
    ]
  }'
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

Use the same Basic Auth credentials configured in Odoo (**Fleet → Vehicle Scanner → Configuration**).

### Test with existing sample data

You can test against real data from the Budha Connection Flask project:

```bash
curl -X POST https://your-odoo.example.com/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:yourpassword' | base64)" \
  -H "Content-Type: application/json" \
  -d "{\"CaseData\": $(cat '/Users/petercatania/Projects/Budha Connection Flask/ricezioni_buhda/20260505_175804_1_BMW Salvatore di prova/dati.json')}"
```

If the sample file is sent without the `CaseData` wrapper, wrap it as shown above.

## Module structure

```
vehicle_scanner_connector/
├── __manifest__.py
├── controllers/main.py          # HTTP webhooks
├── models/
│   ├── scanner_config.py        # API credentials
│   ├── vehicle_scan_log.py      # Scan records
│   ├── vehicle_scan_panel.py    # Panel-level dent lines
│   └── vehicle_scan_service.py  # BUHDA parsing (Flask-aligned)
├── security/
│   ├── ir.model.access.csv
│   └── vehicle_scanner_security.xml
├── data/
│   └── scanner_config_data.xml
└── views/
    ├── menu.xml
    ├── scanner_config_views.xml
    └── vehicle_scan_log_views.xml
```

## Security notes

- Change the default password immediately after install.
- Keep **Allow CORS** disabled in production (enable only for testing).
- Put Odoo behind HTTPS (Nginx/Traefik).
- Consider rate limiting at the reverse proxy.
- Credentials are compared with constant-time checks (`hmac.compare_digest`).

## Possible next steps

- Auto-create repair orders from scan data
- API key auth instead of Basic Auth
- Multipart upload support for large image payloads

## License

LGPL-3