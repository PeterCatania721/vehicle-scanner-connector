# Vehicle Scanner Connector

Odoo 19+ addon that receives AI vehicle scan data directly in Odoo, replacing the intermediate Flask bridge for BUHDA hail-damage scanners.

Based on the working patterns from [Budha Connection Flask](../Budha%20Connection%20Flask/budha_connect.py).

## Features

- **BUHDA-compatible webhook** — same JSON payload and Basic Auth as the Flask `/budha` endpoint
- **Generic scanner API** — simple JSON format for custom scanners
- **Scan logs** — stores raw JSON, panel-level dent data, and PDF/image attachments
- **Fleet integration** — links scans to `fleet.vehicle` by license plate
- **Configurable credentials** — no hard-coded passwords in code

## Installation

1. Copy `vehicle_scanner_connector/` into your Odoo addons path:

   ```bash
   cp -r vehicle_scanner_connector /path/to/odoo/custom-addons/
   ```

2. Add the addons path to `odoo.conf` if needed:

   ```ini
   addons_path = /usr/lib/python3/dist-packages/odoo/addons,/path/to/custom-addons
   ```

3. Restart Odoo and update the Apps list.

4. Install **Vehicle Scanner Connector**.

5. Open **Fleet → Vehicle Scanner → Configuration** and set username/password.

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

## Module structure

```
vehicle_scanner_connector/
├── controllers/main.py      # HTTP webhooks
├── models/
│   ├── scanner_config.py    # API credentials
│   ├── vehicle_scan_log.py  # Scan records
│   ├── vehicle_scan_panel.py
│   └── vehicle_scan_service.py  # BUHDA parsing (Flask-aligned)
├── security/
├── data/
└── views/
```

## Security notes

- Change the default password immediately after install.
- Keep **Allow CORS** disabled in production.
- Put Odoo behind HTTPS (Nginx/Traefik).
- Consider rate limiting at the reverse proxy.

## License

LGPL-3