# Project State — 2026-06-09

Snapshot of the **Vehicle Scanner Connector** Odoo 19 module at release **19.0.1.0.1**.

## Repository

| | |
|---|---|
| **Path** | `/Users/petercatania/Projects/vehicle-scanner-connector` |
| **Remote** | `https://github.com/PeterCatania721/vehicle-scanner-connector.git` |
| **Branch** | `main` |
| **Odoo target** | 19.0 |
| **Dependencies** | `base`, `fleet` |

## Status

| Area | State |
|---|---|
| Module install | Ready — copy `vehicle_scanner_connector/` to custom addons, install via Apps |
| Post-install | Auto-loads default panel mappings; change default password in Configuration |
| HTTP webhooks | Active on fixed registered paths (see README) |
| Configuration UI | Complete — credentials, endpoints, market, mappings, parser rules |
| Security | Groups + ACLs for all models; Fleet managers implied |
| Tests | 27 local simulation tests pass; Odoo TransactionCase tests included |

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
├── __manifest__.py          # v19.0.1.0.1, post_init_hook
├── constants.py             # Webhook path registry
├── hooks.py                 # Post-install bootstrap
├── controllers/main.py      # HTTP endpoints
├── models/
│   ├── scanner_config.py    # API config + auth
│   ├── vehicle_scan_service.py  # BUHDA/generic/inbound processing
│   ├── vehicle_scan_log.py
│   ├── vehicle_scan_panel.py
│   ├── panel_mapping.py
│   ├── field_mapping.py
│   └── parser_rule.py
├── security/
├── views/
└── tests/
```

## Verification Commands

```bash
# Local (no Odoo)
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py

# Odoo install + tests
odoo -d your_database -i vehicle_scanner_connector --test-enable --stop-after-init
```

## Related Infrastructure

- **Odoo instance:** `https://kesi19.jcloud.ik-server.com` (DB: `Gestionale_Levabolli`)
- **MCP:** `odoo-kesi19` — requires `ODOO_PASSWORD` env alongside `ODOO_API_KEY` (fixed in wrapper script)
- **Flask reference:** `../Budha Connection Flask/budha_connect.py`

## Safe production deploy

Grok skill: `.grok/skills/vehicle-scanner-odoo-deploy-safe/`

Run in Grok Build:

```
/vehicle-scanner-odoo-deploy-safe
```

Safe mode = MCP-only deploy (no SSH). `update_list` → install → config writes.
MCP writes on module-scoped models only (preview → validate → execute).

## Next Steps (optional)

- Deploy to KESI Odoo 19 production via skill above
- Point BUHDA scanner webhook from Flask `:7721/budha` to Odoo `/budha`
- Auto-create repair orders from scan data
- Rate limiting at reverse proxy