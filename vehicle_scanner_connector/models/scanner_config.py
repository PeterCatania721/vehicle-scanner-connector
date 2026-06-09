import base64
import hmac

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class VehicleScannerConfig(models.Model):
    _name = 'vehicle.scanner.config'
    _description = 'Vehicle Scanner API Configuration'
    _rec_name = 'name'

    name = fields.Char(default='Vehicle Scanner API', required=True)
    active = fields.Boolean(default=True)
    username = fields.Char(required=True, default='ai_scanner')
    password = fields.Char(required=True, groups='vehicle_scanner_connector.group_vehicle_scanner_manager')
    allow_cors = fields.Boolean(
        string='Allow CORS (*)',
        default=False,
        help='Enable only for testing. Disable in production.',
    )
    auto_create_vehicle = fields.Boolean(
        string='Auto-create Fleet Vehicle',
        default=False,
        help='Create a fleet.vehicle when no match is found for the license plate.',
    )

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