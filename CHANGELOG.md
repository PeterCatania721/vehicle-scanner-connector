# Changelog

All notable changes to the Vehicle Scanner Connector Odoo 19 module.

## [19.0.1.0.1] — 2026-06-09

### Added

- `constants.py` — shared webhook path registry used by controllers and config
- `hooks.py` — post-install hook: single active config, default KESI panel mappings (1–18)
- `panel_mapping.py`, `field_mapping.py`, `parser_rule.py` — configurable parsing layer
- Universal inbound endpoint: `POST /vehicle_scanner/inbound` (auto-detect BUHDA vs generic)
- Full configuration UI: endpoints, market code, API URLs, panel/field mappings, parser rules
- Access rights for panel mappings, field mappings, and parser rules (user read / manager CRUD)
- Odoo `TransactionCase` tests in `vehicle_scanner_connector/tests/`
- Local simulation tests in `tests/test_local_simulation.py` (no Odoo runtime required)
- BUHDA API reference PDF in `docs/SOFTWAREEN-Custom-API-Documentation.pdf`

### Changed

- Removed unused `repair` dependency — module now depends only on `base` and `fleet`
- Webhook paths use `Selection` fields synced with registered route constants
- Generic/inbound endpoints return consistent `{success: false, ...}` auth error format
- BUHDA response no longer duplicates `scan_log_id` in case details
- README rewritten with Odoo 19 install steps, endpoint table, and test instructions

### Fixed

- Missing ACLs that blocked managers from editing mapping and parser rule models
- Configurable webhook path fields that were not wired to HTTP route registration
- Incomplete configuration form that hid most module features after install

## [19.0.1.0.0] — 2026-06-09

### Added

- Initial release: BUHDA webhook (`/budha`), generic scanner API, scan logs, fleet integration
- Basic Auth with configurable credentials
- Panel-level dent parsing (CH market)
- PDF and image attachment storage