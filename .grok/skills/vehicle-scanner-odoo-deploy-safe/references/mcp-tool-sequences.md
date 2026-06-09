# MCP Tool Sequences (odoo-kesi19)

Copy-paste reference for the agent. All calls use server `odoo-kesi19`.

## 1. Health + profile

```
health_check {}
get_odoo_profile { "include_modules": true, "module_limit": 50 }
```

## 2. Check Fleet dependency

```
search_records {
  "model": "ir.module.module",
  "domain": [["name", "=", "fleet"]],
  "fields": ["name", "state"],
  "limit": 1
}
```

## 3. Refresh apps list (required before install)

```
diagnose_odoo_call {
  "model": "ir.module.module",
  "method": "update_list",
  "args": []
}
execute_method {
  "model": "ir.module.module",
  "method": "update_list",
  "args": []
}
```

## 4. Find vehicle_scanner_connector

```
search_records {
  "model": "ir.module.module",
  "domain": [["name", "=", "vehicle_scanner_connector"]],
  "fields": ["name", "state", "id", "latest_version", "summary"],
  "limit": 1
}
```

## 5. Install module

Replace `MODULE_ID` with integer from step 4.

```
diagnose_odoo_call {
  "model": "ir.module.module",
  "method": "button_immediate_install",
  "args": [[MODULE_ID]]
}
execute_method {
  "model": "ir.module.module",
  "method": "button_immediate_install",
  "args": [[MODULE_ID]]
}
```

## 6. Configure scanner (safe write chain)

Replace `CONFIG_ID` from `search_records` on `vehicle.scanner.config`.

```
get_model_fields { "model": "vehicle.scanner.config" }

preview_write {
  "model": "vehicle.scanner.config",
  "operation": "write",
  "record_ids": [CONFIG_ID],
  "values": {
    "password": "<user-password>",
    "api_base_url": "https://kesi19.jcloud.ik-server.com"
  }
}

validate_write {
  "model": "vehicle.scanner.config",
  "operation": "write",
  "record_ids": [CONFIG_ID],
  "values": {
    "password": "<user-password>",
    "api_base_url": "https://kesi19.jcloud.ik-server.com"
  },
  "use_live_metadata": true
}

execute_approved_write {
  "approval": <object returned by preview_write>,
  "confirm": true
}
```

## 7. Load default panels (if empty)

```
execute_method {
  "model": "vehicle.scanner.config",
  "method": "action_load_default_panel_mappings",
  "args": [[CONFIG_ID]]
}
```

## 8. Verify scan log after webhook test

```
search_records {
  "model": "vehicle.scan.log",
  "domain": [["case_number", "=", "MCP-DEPLOY-TEST"]],
  "fields": ["name", "license_plate", "status", "received_at"],
  "limit": 1
}
```

## Zip import fallback (if module not in apps list)

Only when `base_import_module` is `installed`:

1. Run locally: `scripts/build-module-zip.sh`
2. Base64-encode the zip
3. Try:

```
execute_method {
  "model": "ir.module.module",
  "method": "import_module",
  "args": [<base64_zip_string>]
}
```

If `import_module` signature differs, use `diagnose_odoo_call` with `use_live_metadata: true`
to inspect the exact method before calling.

Then repeat steps 3–5 (`update_list` → search → install).

## MCP wrapper requirements

`~/.grok/bin/mcp-odoo-kesi19.sh` must export:

```bash
export ODOO_PASSWORD="$ODOO_KESI19_API_KEY"
export ODOO_MCP_ENABLE_WRITES=1
export ODOO_MCP_ALLOWED_SIDE_EFFECT_METHODS="ir.module.module.update_list,ir.module.module.button_immediate_install,ir.module.module.button_immediate_upgrade,vehicle.scanner.config.action_load_default_panel_mappings"
```

Restart `odoo-kesi19` MCP after changing the wrapper.