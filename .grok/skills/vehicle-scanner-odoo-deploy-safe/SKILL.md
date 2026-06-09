---
name: vehicle-scanner-odoo-deploy-safe
description: >
  Safely deploy the vehicle_scanner_connector Odoo 19 addon to production without
  touching existing business data. Filesystem deploy + isolated module install only.
  MCP odoo-kesi19 is read-only (no writes, no execute_method). Use when the user
  asks to install the custom module on KESI Odoo production, deploy vehicle scanner
  safely, safe mode install, or runs /vehicle-scanner-odoo-deploy-safe.
---

# Vehicle Scanner — Safe Production Deploy (Odoo 19)

Deploy **only** `vehicle_scanner_connector` to production. Do not modify existing
business records, other modules, or unrelated configuration.

## What "safe mode" means

| Allowed | Forbidden |
|---|---|
| Copy/clone module files to server addons path | `execute_approved_write`, `execute_method` with side effects |
| Restart Odoo service/container | `ODOO_MCP_ENABLE_WRITES=1` or any MCP write |
| Install **only** `vehicle_scanner_connector` (`-i`, not `-u all`) | Upgrade all modules (`-u base` / mass update) |
| Read-only MCP checks (`get_odoo_profile`, `search_records`) | Create/edit/delete on `res.partner`, `sale.order`, `fleet.vehicle`, etc. |
| New tables for this module (unavoidable on first install) | SQL, shell inside DB, data imports |
| Post-install: change scanner password in **new** config record | Change passwords/users/settings outside Vehicle Scanner |

The module is isolated: depends only on `base` + `fleet`, adds its own models
(`vehicle.scan.log`, `vehicle.scanner.config`, …), public webhook routes, and
Fleet submenu. It does not patch core Odoo models.

## Target (KESI production)

Read `references/kesi-production.md` for URLs, paths, and credentials policy.
Do not hard-code API keys in commands or commits.

## Workflow (follow in order)

### Phase 0 — Pre-flight (local, no server changes)

1. Confirm repo is at `/Users/petercatania/Projects/vehicle-scanner-connector` on `main`.
2. Run local simulation tests:

```bash
cd /Users/petercatania/Projects/vehicle-scanner-connector
python3 tests/test_local_simulation.py
```

All tests must pass before deploying.

3. Tell the user what will happen: filesystem copy + single module install + restart.
   Ask for explicit confirmation before any server command.

### Phase 1 — Read-only MCP checks (optional but recommended)

Use `odoo-kesi19` MCP **read-only only**:

1. `get_odoo_profile` — confirm Odoo 19, transport json2, database name.
2. `search_records` on `ir.module.module`:
   - `domain`: `[("name", "=", "fleet")]`, `fields`: `["name", "state"]`
   - If `fleet` is not `installed`, stop and tell user to install Fleet manually
     via Apps UI first (one-time, separate step). Do not install Fleet via MCP.
3. `search_records` on `ir.module.module`:
   - `domain`: `[("name", "=", "vehicle_scanner_connector")]`
   - If already `installed`, stop — report version and skip reinstall unless user
     explicitly asks to upgrade **only** this module.

If MCP returns "No Odoo configuration found", skip MCP checks and proceed with
SSH/filesystem steps only. Do not attempt to fix MCP during deploy.

### Phase 2 — Filesystem deploy (primary action)

SSH to the Odoo server. Discover the real custom addons path before copying:

```bash
# Docker — find addons mount
docker compose exec odoo ls /mnt/extra-addons 2>/dev/null || true
docker compose exec odoo grep addons_path /etc/odoo/odoo.conf

# Bare metal
grep addons_path /etc/odoo/odoo.conf
```

Deploy the **inner** module folder `vehicle_scanner_connector/` (must contain
`__manifest__.py` at its root).

**Preferred — git pull on server** (if repo already cloned):

```bash
cd /path/to/custom-addons/vehicle-scanner-connector
git pull origin main
```

**First-time clone:**

```bash
cd /path/to/custom-addons
git clone https://github.com/PeterCatania721/vehicle-scanner-connector.git
```

**Verify layout:**

```bash
test -f /path/to/custom-addons/vehicle-scanner-connector/vehicle_scanner_connector/__manifest__.py \
  && echo "OK: module path correct"
```

Ensure `addons_path` in `odoo.conf` includes the parent of `vehicle_scanner_connector/`.
If not, add the path and tell the user — do not edit production config without confirmation.

### Phase 3 — Install only this module

Restart Odoo, then install **only** `vehicle_scanner_connector`:

```bash
# Docker
docker compose restart odoo
docker compose exec odoo odoo \
  -d Gestionale_Levabolli \
  -i vehicle_scanner_connector \
  --stop-after-init \
  --no-http

# Bare metal
sudo systemctl restart odoo
sudo -u odoo odoo \
  -d Gestionale_Levabolli \
  -i vehicle_scanner_connector \
  --stop-after-init \
  --no-http
```

Rules:

- Use `-i vehicle_scanner_connector` only — never `-u all`, never `-u base`.
- Never run `--test-enable` on production unless user explicitly requests it.
- If install fails on missing `fleet`, stop and report — user installs Fleet via Apps.

Restart Odoo again after install:

```bash
docker compose restart odoo
# or: sudo systemctl restart odoo
```

### Phase 4 — Post-install (minimal, module-scoped)

Tell the user to do these two steps in the Odoo UI (do not use MCP writes):

1. **Fleet → Vehicle Scanner → Configuration**
2. Change password from `change-me-on-install`
3. Set **Public Base URL** to `https://kesi19.jcloud.ik-server.com` if needed

Optional read-only MCP verify after user changes password:

```bash
curl -s -o /dev/null -w "%{http_code}" \
  -X POST https://kesi19.jcloud.ik-server.com/budha \
  -H "Authorization: Basic $(printf 'ai_scanner:USER_SET_PASSWORD' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"CaseData":{"Vorgangsnummer":"SAFE-DEPLOY-TEST","Kennzeichen":"TI00000","Dents":{"1":{"amountSmall":0}}}}'
```

Expect HTTP 200. User must supply the new password for the curl test — never use
default password on production after install.

Read-only MCP confirm module installed:

- `search_records` `ir.module.module` domain `[("name","=","vehicle_scanner_connector")]`
  fields `["name","state","latest_version"]`

### Phase 5 — Report

Summarize for the user:

- Module version installed (`19.0.1.0.1` from `__manifest__.py`)
- Server path where files were placed
- Whether Fleet was already installed
- That no business data was modified via MCP
- Remaining manual steps (password, BUHDA webhook URL change)

## Rollback (if install fails or user requests)

1. Uninstall via Odoo UI: Apps → Vehicle Scanner Connector → Uninstall.
2. Remove module folder from addons path (optional, after uninstall).
3. Restart Odoo.

Do not delete the database. Do not restore backups unless user explicitly asks.

## Agent discipline

- Execute all server commands yourself when SSH/access is available — do not
  hand the user a long manual checklist unless access is missing.
- One command at a time; show output before proceeding.
- If any step would touch data outside this module, stop and ask.
- Never store or print API keys, passwords, or Bitwarden secrets in chat or commits.

## Trigger phrases

`/vehicle-scanner-odoo-deploy-safe`, safe deploy vehicle scanner, install custom
module production safe mode, deploy vehicle_scanner_connector kesi19