---
name: vehicle-scanner-odoo-deploy-safe
description: >
  Safely deploy the vehicle_scanner_connector Odoo 19 addon to production without
  touching existing business data. Filesystem deploy + isolated module install only.
  MCP odoo-kesi19 may write, but only on module-scoped models via preview/approve flow.
  Use when the user asks to install the custom module on KESI Odoo production,
  deploy vehicle scanner safely, safe mode install, or runs /vehicle-scanner-odoo-deploy-safe.
---

# Vehicle Scanner — Safe Production Deploy (Odoo 19)

Deploy **only** `vehicle_scanner_connector` to production. Do not modify existing
business records, other modules, or unrelated configuration.

**MCP has write permission** — use it only for the allowlisted operations below.
Every write must go through `preview_write` → `validate_write` → `execute_approved_write`
with `confirm=true`. Never skip preview.

## What "safe mode" means

| Allowed | Forbidden |
|---|---|
| Copy/clone module files to server addons path | Writes on `res.partner`, `sale.order`, `fleet.vehicle`, `account.*`, `res.users` |
| Install **only** `vehicle_scanner_connector` (CLI or MCP) | Install/upgrade other modules (`fleet` via MCP, `-u all`, `-u base`) |
| MCP read checks (`get_odoo_profile`, `search_records`) | `unlink` on any model outside allowlist |
| MCP writes on **allowlisted models only** (see below) | `execute_method` on non-allowlisted models/methods |
| `execute_method` → `ir.module.module.button_immediate_install` for this module only | `chatter_post`, broad `execute_method`, SQL |
| New tables for this module (unavoidable on first install) | Change Odoo system settings outside Vehicle Scanner |

The module is isolated: depends only on `base` + `fleet`, adds its own models,
public webhook routes, and Fleet submenu. It does not patch core Odoo models.

## MCP write allowlist (strict)

Only these models and operations may be written via MCP:

| Model | Operation | Purpose |
|---|---|---|
| `vehicle.scanner.config` | `write` | Set password, `api_base_url`, endpoint toggles |
| `vehicle.scanner.panel.mapping` | `create` / `write` | Load default panels if post_init_hook missed |
| `vehicle.scanner.field.mapping` | `create` / `write` | Only when user explicitly requests custom mappings |
| `vehicle.scanner.parser.rule` | `create` / `write` | Only when user explicitly requests parser rules |
| `ir.module.module` | `execute_method` `button_immediate_install` | Install **only** `vehicle_scanner_connector` |

Everything else is **read-only** via MCP, including `fleet.vehicle`, `res.partner`,
`sale.order`, `stock.picking`, `res.users`, `ir.config_parameter`.

## Target (KESI production)

Read `references/kesi-production.md` for URLs, paths, and credentials policy.
Do not hard-code API keys in commands or commits.

## Workflow (follow in order)

### Phase 0 — Pre-flight (local)

1. Confirm repo at `/Users/petercatania/Projects/vehicle-scanner-connector` on `main`.
2. Run local simulation tests — all must pass:

```bash
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py
```

3. Tell the user the plan: filesystem deploy → install this module only → MCP config write.
   Ask explicit confirmation before server commands or MCP writes.

### Phase 1 — MCP pre-flight checks

Use `odoo-kesi19` MCP (reads first):

1. `health_check` — confirm MCP connected; note `write_execution_enabled`.
2. `get_odoo_profile` — confirm Odoo 19, json2, database `Gestionale_Levabolli`.
3. `search_records` `ir.module.module`:
   - `domain`: `[("name", "=", "fleet")]`, `fields`: `["name", "state"]`
   - If `fleet` not `installed`: **stop**. Tell user to install Fleet via Apps UI once.
     Do not install Fleet via MCP.
4. `search_records` `ir.module.module`:
   - `domain`: `[("name", "=", "vehicle_scanner_connector")]`, `fields`: `["name", "state", "id"]`
   - If already `installed`: report version and skip to Phase 4 unless upgrade requested.

### Phase 2 — Filesystem deploy (required — MCP cannot upload files)

SSH to the Odoo server. Discover addons path, then deploy:

```bash
git clone https://github.com/PeterCatania721/vehicle-scanner-connector.git
# or: git pull origin main
```

Verify:

```bash
test -f .../vehicle-scanner-connector/vehicle_scanner_connector/__manifest__.py && echo OK
```

Restart Odoo after any `addons_path` change.

Optional MCP verify (read-only): `scan_addons_source` with local project path on Mac
to confirm manifest version matches before server install.

### Phase 3 — Install only this module

**Option A — SSH (preferred, most reliable):**

```bash
docker compose exec odoo odoo -d Gestionale_Levabolli \
  -i vehicle_scanner_connector --stop-after-init --no-http
docker compose restart odoo
```

**Option B — MCP write (only if SSH install unavailable):**

1. `search_records` `ir.module.module` → get `id` where `name=vehicle_scanner_connector`
2. `diagnose_odoo_call` model `ir.module.module`, method `button_immediate_install`
3. `execute_method` with that record id — **only** for `vehicle_scanner_connector`

Never use MCP to install any other module.

Confirm via MCP:

- `search_records` `ir.module.module` → `state` must be `installed`

### Phase 4 — Post-install via MCP (module-scoped writes)

Configure the scanner using the safe write flow on **allowlisted models only**.

1. `search_records` `vehicle.scanner.config`, `limit=1`, get config `id`.
2. Ask user for production scanner password (or generate a strong one and show it once).
3. Write config:

```
preview_write  → model: vehicle.scanner.config, operation: write
                 record_ids: [config_id]
                 values: {
                   "password": "<user-provided>",
                   "api_base_url": "https://kesi19.jcloud.ik-server.com"
                 }
validate_write → same payload
execute_approved_write → approval from preview, confirm=true
```

4. If `panel_mapping_ids` empty, `execute_method` on config record:
   `action_load_default_panel_mappings` (allowlisted via `vehicle.scanner.config`).

5. Read-only verify:

```bash
curl -X POST https://kesi19.jcloud.ik-server.com/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:PASSWORD' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"CaseData":{"Vorgangsnummer":"SAFE-DEPLOY-TEST","Kennzeichen":"TI00000","Dents":{"1":{"amountSmall":0}}}}'
```

Expect HTTP 200. Check **Fleet → Vehicle Scanner → Scan Logs** via MCP:

- `search_records` `vehicle.scan.log` domain `[("case_number","=","SAFE-DEPLOY-TEST")]`

### Phase 5 — Report

Summarize:

- Module version installed
- Server path for files
- Fleet status (was already installed)
- Config record id and that password was set via MCP
- Confirm **no business records** outside allowlist were written
- Remind user to point BUHDA webhook to `https://kesi19.jcloud.ik-server.com/budha`

## Rollback

1. Uninstall via Apps UI or MCP read + user confirmation for uninstall only.
2. Remove module folder from addons path (optional).
3. Restart Odoo.

Never delete the database.

## Agent discipline

- Execute server commands yourself when SSH is available.
- Every MCP write: preview → validate → execute with confirm. Log what was written.
- If a step needs a model outside the allowlist, stop and ask the user.
- Never print API keys or Bitwarden secrets in chat or commits.

## Trigger phrases

`/vehicle-scanner-odoo-deploy-safe`, safe deploy vehicle scanner, install custom
module production safe mode, deploy vehicle_scanner_connector kesi19