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

## MCP (`odoo-kesi19`)

| Setting | Value |
|---|---|
| Server name | `odoo-kesi19` |
| Wrapper | `~/.grok/bin/mcp-odoo-kesi19.sh` |
| Credentials | Bitwarden `ODOO_KESI19_USERNAME`, `ODOO_KESI19_API_KEY` |
| Writes | **Enabled** — module-scoped allowlist only |

### MCP write allowlist

| Model | Allowed operations |
|---|---|
| `vehicle.scanner.config` | `write` (password, api_base_url, toggles) |
| `vehicle.scanner.panel.mapping` | `create`, `write` |
| `vehicle.scanner.field.mapping` | `create`, `write` (only if user requests) |
| `vehicle.scanner.parser.rule` | `create`, `write` (only if user requests) |
| `ir.module.module` | `execute_method` → `button_immediate_install` for `vehicle_scanner_connector` only |

### MCP write flow (mandatory)

1. `preview_write`
2. `validate_write`
3. `execute_approved_write` with `confirm=true`

### MCP forbidden (even with write permission)

- `res.partner`, `sale.order`, `fleet.vehicle`, `account.move`, `res.users`
- `chatter_post`
- `execute_method` on models outside allowlist
- Installing/upgrading modules other than `vehicle_scanner_connector`
- `unlink` except rollback explicitly approved by user

### MCP read tools (always safe)

`health_check`, `get_odoo_profile`, `search_records`, `read_record`, `list_models`,
`get_model_fields`, `diagnose_access`, `diagnose_odoo_call`, `scan_addons_source`

## Webhook endpoints (after install)

| Path | Purpose |
|---|---|
| `/budha` | BUHDA Flask-compatible |
| `/vehicle_scanner/budha` | BUHDA namespaced |
| `/vehicle_scanner/receive` | Generic scanner |
| `/vehicle_scanner/inbound` | Auto-detect |

## Default credentials (change on install)

| Field | Default |
|---|---|
| Username | `ai_scanner` |
| Password | `change-me-on-install` → set via MCP `vehicle.scanner.config` write |

## Isolation guarantee

Adds only Vehicle Scanner models, security groups, HTTP routes, and Fleet submenu.
Does not patch core Odoo models or existing business data.