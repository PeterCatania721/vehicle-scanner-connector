---
name: vehicle-scanner-odoo-deploy-safe
description: >
  Deploy vehicle_scanner_connector to KESI Odoo 19 production using only odoo-kesi19 MCP.
  No SSH. Safe mode: module-scoped writes only via preview/validate/execute flow.
  Use when the user asks to install the custom module on production, deploy vehicle
  scanner safely, MCP-only deploy, or runs /vehicle-scanner-odoo-deploy-safe.
---

# Vehicle Scanner — MCP-Only Safe Deploy (Odoo 19)

Deploy **only** `vehicle_scanner_connector` using **`odoo-kesi19` MCP tools only**.

**No SSH. No docker commands on the server. No systemctl.** The agent must never open
a remote shell session.

Local shell is allowed only for:
- `python3 tests/test_local_simulation.py` (pre-flight)
- `scripts/build-module-zip.sh` (if zip import path is needed)

## MCP server

Use **only** `odoo-kesi19`. Do not use Hostinger MCP, SSH, or manual Odoo UI unless
this skill explicitly says the MCP path failed and tells the user what to click.

Wrapper: `~/.grok/bin/mcp-odoo-kesi19.sh` (must have `ODOO_PASSWORD` + writes enabled).
See `references/mcp-tool-sequences.md` for exact tool payloads.

## What "safe mode" means

| Allowed via MCP | Forbidden |
|---|---|
| `ir.module.module.update_list` | SSH / scp / docker / systemctl on server |
| `ir.module.module.button_immediate_install` for **this module only** | Install/upgrade any other module |
| Writes on `vehicle.scanner.*` models (allowlist) | Writes on `res.partner`, `sale.order`, `fleet.vehicle`, etc. |
| `base_import_module` import (if installed on Odoo) | `-u all`, SQL, `chatter_post` |
| Read tools: `search_records`, `get_odoo_profile`, … | `unlink` outside allowlist |

Every write: `preview_write` → `validate_write` → `execute_approved_write` with
`confirm=true`.

## MCP write allowlist

| Model | Method / operation |
|---|---|
| `ir.module.module` | `execute_method` → `update_list` |
| `ir.module.module` | `execute_method` → `button_immediate_install` (this module only) |
| `ir.module.module` | `execute_method` → `button_immediate_upgrade` (only if user asks to upgrade) |
| `vehicle.scanner.config` | `write` |
| `vehicle.scanner.config` | `execute_method` → `action_load_default_panel_mappings` |
| `vehicle.scanner.panel.mapping` | `create` / `write` |
| `base_import_module` | `execute_method` → import (only if module missing from apps list) |

## Workflow (MCP only — follow in order)

### Phase 0 — Local pre-flight

```bash
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py
```

All tests must pass. Ask user to confirm before any MCP write.

`scan_addons_source` (read-only MCP) with:

```json
{
  "addons_paths": ["/Users/petercatania/Projects/vehicle-scanner-connector"],
  "max_files": 200
}
```

Confirm manifest version `19.0.1.0.1` and `installable: true`.

### Phase 1 — MCP connectivity

1. `health_check` — must succeed. If `write_execution_enabled` is false, stop and tell
   user to restart MCP after enabling writes in `mcp-odoo-kesi19.sh`.
2. `get_odoo_profile` — confirm database `Gestionale_Levabolli`, Odoo 19, json2.

If "No Odoo configuration found": stop. User must restart `odoo-kesi19` MCP (wrapper
needs `ODOO_PASSWORD` exported).

### Phase 2 — Dependency check (read-only)

`search_records` on `ir.module.module`:

```json
{
  "model": "ir.module.module",
  "domain": [["name", "=", "base"]],
  "fields": ["name", "state"],
  "limit": 1
}
```

`base` must be `installed` (always true on a running Odoo). This module does **not**
require Fleet.

### Phase 3 — Refresh apps list (MCP write)

`diagnose_odoo_call` first:

```json
{
  "model": "ir.module.module",
  "method": "update_list"
}
```

Then `execute_method`:

```json
{
  "model": "ir.module.module",
  "method": "update_list",
  "args": []
}
```

Wait for success. This scans the **server's** addons path — no SSH needed.

### Phase 4 — Find or import module

`search_records`:

```json
{
  "model": "ir.module.module",
  "domain": [["name", "=", "vehicle_scanner_connector"]],
  "fields": ["name", "state", "id", "latest_version"],
  "limit": 1
}
```

**If found and `state` = `installed`:** skip to Phase 6 (config only) unless upgrade requested.

**If found and `state` = `uninstalled`:** go to Phase 5 (install).

**If not found — zip import path (still MCP only):**

1. Check `base_import_module` is installed (`search_records` on `ir.module.module`).
2. If yes, build zip locally:

```bash
cd /Users/petercatania/Projects/vehicle-scanner-connector
./.grok/skills/vehicle-scanner-odoo-deploy-safe/scripts/build-module-zip.sh
```

3. Import via MCP `execute_method` on `ir.module.module` (see `references/mcp-tool-sequences.md`
   for `import_module` payload with base64 zip).
4. Run `update_list` again, then re-search.

**If not found and `base_import_module` not installed:** stop. Tell user the module
files are not on the Odoo server yet. Options **without SSH**:
- Hosting panel Git deploy / webhook (clone repo to addons path)
- Odoo Apps → Import Module (if available on their edition)
Do not attempt SSH.

### Phase 5 — Install module (MCP only)

`diagnose_odoo_call`:

```json
{
  "model": "ir.module.module",
  "method": "button_immediate_install",
  "args": [[MODULE_ID]]
}
```

`execute_method`:

```json
{
  "model": "ir.module.module",
  "method": "button_immediate_install",
  "args": [[MODULE_ID]]
}
```

Replace `MODULE_ID` with id from Phase 4. **Only** for `vehicle_scanner_connector`.

Verify:

```json
{
  "model": "ir.module.module",
  "domain": [["name", "=", "vehicle_scanner_connector"]],
  "fields": ["name", "state", "latest_version"],
  "limit": 1
}
```

`state` must be `installed`.

### Phase 6 — Post-install config (MCP writes)

1. `search_records` `vehicle.scanner.config`, `limit=1` → get `id`.
2. Ask user for scanner password (or generate strong password, show once).
3. Safe write chain:

```
preview_write   → vehicle.scanner.config, write, record_ids=[id],
                  values={"password":"…","api_base_url":"https://kesi19.jcloud.ik-server.com"}
validate_write  → same
execute_approved_write → approval from preview, confirm=true
```

4. If no panel mappings: `execute_method` on config id:
   `action_load_default_panel_mappings`.

### Phase 7 — Verify (MCP read)

1. `search_records` `vehicle.scanner.config` — confirm `api_base_url` set.
2. `search_records` `vehicle.scanner.panel.mapping`, `limit=5` — confirm panels exist.
3. Optional webhook test via local curl (not SSH):

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  -X POST https://kesi19.jcloud.ik-server.com/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:PASSWORD' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"CaseData":{"Vorgangsnummer":"MCP-DEPLOY-TEST","Kennzeichen":"TI00000","Dents":{"1":{"amountSmall":0}}}}'
```

4. `search_records` `vehicle.scan.log`:
   `domain=[("case_number","=","MCP-DEPLOY-TEST")]`

### Phase 8 — Report

Tell user:
- Module version installed
- All steps done via MCP (no SSH)
- Config record id, password set
- No business data outside allowlist was modified
- Point BUHDA webhook to `https://kesi19.jcloud.ik-server.com/budha`

## Rollback (MCP only, with user confirmation)

`execute_method` `ir.module.module` `button_immediate_uninstall` on module id — only
after explicit user approval.

## Agent discipline

- **Never SSH.** If tempted to SSH, use zip import or ask user to use hosting panel.
- Every write: preview → validate → execute. Log model + record ids.
- Never print API keys or passwords in commits.
- If MCP tool fails, diagnose with `diagnose_odoo_call` / `diagnose_access` before retry.

## Trigger phrases

`/vehicle-scanner-odoo-deploy-safe`, MCP deploy vehicle scanner, install module
odoo-kesi19 safe mode, no SSH deploy