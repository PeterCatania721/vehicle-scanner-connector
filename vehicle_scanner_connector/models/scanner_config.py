import base64
import hmac

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..constants import (
    BUDHA_PATH_SELECTION,
    GENERIC_PATH_SELECTION,
    INBOUND_PATH_SELECTION,
)


class VehicleScannerConfig(models.Model):
    _name = 'vehicle.scanner.config'
    _description = 'Vehicle Scanner API Configuration'
    _rec_name = 'name'

    name = fields.Char(default='Vehicle Scanner API', required=True)
    active = fields.Boolean(default=True)

    # --- Authentication ---
    username = fields.Char(required=True, default='ai_scanner')
    password = fields.Char(
        required=True,
        groups='vehicle_scanner_connector.group_vehicle_scanner_manager',
    )

    # --- Endpoints ---
    enable_budha_endpoint = fields.Boolean(string='Enable BUHDA Endpoint', default=True)
    enable_generic_endpoint = fields.Boolean(string='Enable Generic Endpoint', default=True)
    enable_inbound_endpoint = fields.Boolean(
        string='Enable Universal Inbound Endpoint',
        default=True,
        help='Single endpoint that auto-detects BUHDA vs generic payloads.',
    )
    budha_webhook_path = fields.Selection(
        selection=BUDHA_PATH_SELECTION,
        string='BUHDA Webhook Path',
        default='/budha',
        required=True,
        help='Canonical URL path shown to configure BUHDA. All BUHDA aliases remain active.',
    )
    generic_webhook_path = fields.Selection(
        selection=GENERIC_PATH_SELECTION,
        string='Generic Webhook Path',
        default='/vehicle_scanner/receive',
        required=True,
        help='Canonical URL path for generic scanners. All generic aliases remain active.',
    )
    inbound_webhook_path = fields.Selection(
        selection=INBOUND_PATH_SELECTION,
        string='Inbound Webhook Path',
        default='/vehicle_scanner/inbound',
        required=True,
        help='Canonical URL path for the auto-detect inbound endpoint.',
    )
    api_base_url = fields.Char(
        string='Public Base URL',
        help='Override web.base.url for the URL shown to configure BUHDA (e.g. https://odoo.kesi.ch).',
    )
    budha_api_url = fields.Char(compute='_compute_api_urls', string='BUHDA API URL')
    generic_api_url = fields.Char(compute='_compute_api_urls', string='Generic API URL')
    inbound_api_url = fields.Char(compute='_compute_api_urls', string='Inbound API URL')

    # --- Payload / market ---
    market_code = fields.Selection(
        [
            ('CH', 'Switzerland (CH)'),
            ('DE', 'Germany (DE)'),
            ('NL', 'Netherlands (NL)'),
            ('AT', 'Austria (AT)'),
            ('FR', 'France (FR)'),
            ('US', 'United States (US)'),
            ('SL', 'Slovenia (SL)'),
        ],
        string='BUHDA Market',
        default='CH',
        required=True,
        help='Determines how the Dents object is parsed. See docs/SOFTWAREEN-Custom-API-Documentation.pdf.',
    )
    payload_wrapper_key = fields.Char(
        string='Payload Wrapper Key',
        default='CaseData',
        help='JSON key wrapping case data (e.g. CaseData). Leave empty to accept raw BUHDA objects.',
    )
    strip_pdf_from_json_log = fields.Boolean(
        string='Strip PDF Fields from Raw JSON Log',
        default=True,
        help='Exclude overviewPDF and attachmentsPDF from the stored raw JSON.',
    )

    # --- Behavior ---
    allow_cors = fields.Boolean(
        string='Allow CORS (*)',
        default=False,
        help='Enable only for testing. Disable in production.',
    )
    require_license_plate = fields.Boolean(
        string='Require License Plate',
        default=False,
        help='Reject payloads without a recognizable license plate.',
    )
    auto_process_panels = fields.Boolean(
        string='Auto-parse Panel Dents',
        default=True,
    )

    # --- Preventivi sync ---
    enable_preventivi_sync = fields.Boolean(
        string='Create/Update Preventivi from Scans',
        default=True,
        help='Automatically create or update sale quotations from incoming scans.',
    )
    preventivi_user_id = fields.Many2one(
        'res.users',
        string='Preventivi Owner / Tecnico',
        domain=[('share', '=', False)],
        help='User assigned as owner and technician on scanner-created preventivi.',
    )
    preventivi_partner_id = fields.Many2one(
        'res.partner',
        string='Default Preventivi Customer',
        help='Customer used when creating preventivi from scans.',
    )
    preventivi_product_id = fields.Many2one(
        'product.product',
        string='Default Service Line',
        domain=[('sale_ok', '=', True)],
        help='Service product added to new preventivi created from scans.',
    )
    preventivi_boli_product_ref = fields.Integer(
        string='Default Tabella di calcolo ID',
        help='Database ID of the boli.product used on scanner-created preventivi. '
             'Required for bolli calculation when the Levabolli module is installed.',
    )

    # --- API response (shown in BUHDA UI) ---
    response_success_message = fields.Char(
        string='Success Message',
        default='Scan received successfully',
    )
    response_error_message = fields.Char(
        string='Error Message',
        default='Scan processing failed',
    )
    include_scan_log_id = fields.Boolean(
        string='Include Scan Log ID in Response',
        default=True,
    )

    # --- Custom parsing ---
    panel_mapping_ids = fields.One2many(
        'vehicle.scanner.panel.mapping',
        'config_id',
        string='Panel Mappings',
    )
    field_mapping_ids = fields.One2many(
        'vehicle.scanner.field.mapping',
        'config_id',
        string='Field Mappings',
    )
    parser_rule_ids = fields.One2many(
        'vehicle.scanner.parser.rule',
        'config_id',
        string='Custom Parser Rules',
    )

    @api.depends('api_base_url', 'budha_webhook_path', 'generic_webhook_path', 'inbound_webhook_path')
    def _compute_api_urls(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for record in self:
            root = (record.api_base_url or base_url).rstrip('/')
            record.budha_api_url = f'{root}{record.budha_webhook_path}' if root else record.budha_webhook_path
            record.generic_api_url = f'{root}{record.generic_webhook_path}' if root else record.generic_webhook_path
            record.inbound_api_url = f'{root}{record.inbound_webhook_path}' if root else record.inbound_webhook_path

    @api.model
    def get_active_config(self):
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise ValidationError(
                'No active Vehicle Scanner configuration found. '
                'Configure credentials under Fleet > Vehicle Scanner > Configuration.'
            )
        return config

    def check_basic_auth(self, auth_header):
        """Validate Authorization: Basic header against configured credentials."""
        self.ensure_one()
        if not auth_header or not auth_header.startswith('Basic '):
            return False
        try:
            encoded = auth_header[6:].strip()
            decoded = base64.b64decode(encoded).decode('utf-8')
            username, password = decoded.split(':', 1)
        except Exception:
            return False
        return (
            hmac.compare_digest(username, self.username)
            and hmac.compare_digest(password, self.password)
        )

    def get_panel_name(self, panel_index):
        self.ensure_one()
        mapping = self.panel_mapping_ids.filtered(
            lambda m: m.active and m.panel_index == panel_index
        )[:1]
        if mapping:
            return mapping.kesi_name or mapping.budha_name or f'Panel {panel_index}'
        return f'Panel {panel_index}'

    def get_kesi_bolli_row(self, panel_index):
        self.ensure_one()
        mapping = self.panel_mapping_ids.filtered(
            lambda m: m.active and m.panel_index == panel_index
        )[:1]
        if mapping and mapping.kesi_bolli_row:
            return mapping.kesi_bolli_row
        return self.env['vehicle.scanner.panel.mapping'].default_kesi_bolli_row(panel_index)

    def build_success_response(self, extra=None):
        self.ensure_one()
        payload = {
            'status': 'ok',
            'success': True,
            'message': self.response_success_message,
        }
        if extra:
            payload.update(extra)
        return payload

    def build_error_response(self, error_message, extra=None):
        self.ensure_one()
        payload = {
            'status': 'error',
            'success': False,
            'error': error_message,
            'message': self.response_error_message,
        }
        if extra:
            payload.update(extra)
        return payload

    def action_load_default_panel_mappings(self):
        self.ensure_one()
        defaults = self.env['vehicle.scanner.panel.mapping'].get_default_mappings()
        existing = {m.panel_index: m for m in self.panel_mapping_ids}
        for panel_index, budha_name, kesi_name, kesi_bolli_row in defaults:
            if panel_index in existing:
                existing[panel_index].write({
                    'budha_name': budha_name,
                    'kesi_name': kesi_name,
                    'kesi_bolli_row': kesi_bolli_row,
                    'active': True,
                })
            else:
                self.env['vehicle.scanner.panel.mapping'].create({
                    'config_id': self.id,
                    'panel_index': panel_index,
                    'budha_name': budha_name,
                    'kesi_name': kesi_name,
                    'kesi_bolli_row': kesi_bolli_row,
                    'active': True,
                })
        return True