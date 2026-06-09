# KESI Production — MCP-Only Deploy

## Odoo

| Setting | Value |
|---|---|
| URL | `https://kesi19.jcloud.ik-server.com` |
| Database | `Gestionale_Levabolli` |
| MCP server | `odoo-kesi19` |

## Module

| Setting | Value |
|---|---|
| Technical name | `vehicle_scanner_connector` |
| Version | `19.0.1.0.1` |
| Dependencies | `base`, `fleet` |
| Git repo | `https://github.com/PeterCatania721/vehicle-scanner-connector.git` |

## Deploy method

**MCP only — no SSH.**

1. `update_list` scans server addons path
2. `button_immediate_install` if module visible
3. Zip import via `base_import_module` if module not visible
4. Config writes on `vehicle.scanner.config`

Module files must reach the Odoo server via:
- Already present on server addons path, OR
- `base_import_module` zip import through MCP, OR
- Hosting panel Git deploy (user action — not SSH)

## MCP write allowlist

See `mcp-tool-sequences.md` for exact payloads.

## Forbidden

- SSH, scp, docker exec, systemctl on server
- Writes outside `vehicle.scanner.*` + `ir.module.module` install methods
- Installing modules other than `vehicle_scanner_connector`