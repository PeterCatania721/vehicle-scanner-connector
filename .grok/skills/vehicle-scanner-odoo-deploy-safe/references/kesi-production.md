# KESI Production Target

Use this reference when deploying `vehicle_scanner_connector` in safe mode.

## Odoo instance

| Setting | Value |
|---|---|
| URL | `https://kesi19.jcloud.ik-server.com` |
| Database | `Gestionale_Levabolli` |
| Odoo version | 19 |
| Transport (MCP) | JSON-2 (`ODOO_TRANSPORT=json2`) |

## Module

| Setting | Value |
|---|---|
| Technical name | `vehicle_scanner_connector` |
| Human name | Vehicle Scanner Connector |
| Version | `19.0.1.0.1` |
| Dependencies | `base`, `fleet` (not `repair`) |
| Git repo | `https://github.com/PeterCatania721/vehicle-scanner-connector.git` |
| Deploy folder | `vehicle_scanner_connector/` (inner folder) |

## MCP (read-only during deploy)

| Setting | Value |
|---|---|
| MCP server name | `odoo-kesi19` |
| Wrapper script | `~/.grok/bin/mcp-odoo-kesi19.sh` |
| Credentials source | Bitwarden via `bws run` (`ODOO_KESI19_USERNAME`, `ODOO_KESI19_API_KEY`) |
| Writes | **Disabled** — never enable `ODOO_MCP_ENABLE_WRITES` for deploy |

Allowed MCP tools: `health_check`, `get_odoo_profile`, `search_records`, `read_record`,
`list_models`, `get_model_fields`, `diagnose_access`, `diagnose_odoo_call`.

Forbidden MCP tools: `execute_approved_write`, `execute_method`, `preview_write`,
`validate_write`, `chatter_post`.

## Webhook endpoints (after install)

| Path | Purpose |
|---|---|
| `/budha` | BUHDA Flask-compatible |
| `/vehicle_scanner/budha` | BUHDA namespaced |
| `/vehicle_scanner/receive` | Generic scanner |
| `/api/receive-vehicle-scan` | Legacy generic |
| `/vehicle_scanner/inbound` | Auto-detect |

## Server paths (discover at deploy time)

These are **not** confirmed — agent must discover on the server:

```bash
# Typical Docker custom addons
/mnt/extra-addons/vehicle-scanner-connector/vehicle_scanner_connector/

# Typical bare metal
/opt/odoo/custom-addons/vehicle-scanner-connector/vehicle_scanner_connector/
```

## Default post-install credentials (change immediately)

| Field | Default |
|---|---|
| Username | `ai_scanner` |
| Password | `change-me-on-install` |

## Isolation guarantee

This module adds only:

- Models: `vehicle.scan.log`, `vehicle.scan.panel`, `vehicle.scanner.config`,
  `vehicle.scanner.panel.mapping`, `vehicle.scanner.field.mapping`,
  `vehicle.scanner.parser.rule`
- Security groups under category "Vehicle Scanner"
- HTTP controllers (public, Basic Auth)
- Fleet submenu: Scan Logs, Configuration

It does **not** inherit or monkey-patch `sale.order`, `account.move`, `res.partner`,
or other core models.