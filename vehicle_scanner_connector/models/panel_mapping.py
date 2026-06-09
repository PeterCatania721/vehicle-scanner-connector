from odoo import api, fields, models


class VehicleScannerPanelMapping(models.Model):
    _name = 'vehicle.scanner.panel.mapping'
    _description = 'BUHDA Panel to KESI Panel Mapping'
    _order = 'panel_index'

    config_id = fields.Many2one(
        'vehicle.scanner.config',
        string='Configuration',
        required=True,
        ondelete='cascade',
    )
    panel_index = fields.Integer(string='Panel #', required=True)
    budha_name = fields.Char(
        string='BUHDA Part Name',
        help='Part name from BUHDA API documentation (e.g. hood, fender left).',
    )
    kesi_name = fields.Char(
        string='KESI Label',
        help='Internal label used in Odoo scan logs and repair workflows.',
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            'panel_index_unique_per_config',
            'unique(config_id, panel_index)',
            'Panel index must be unique per configuration.',
        ),
    ]

    @api.model
    def get_default_mappings(self):
        """BUHDA PDF part IDs with KESI labels from Budha Connection Flask."""
        return [
            (1, 'hood', 'Parafango Ant Sx'),
            (2, 'fender left', 'Porta Ant SX'),
            (3, 'fender right', 'Porta Post SX'),
            (4, 'door front left', 'Paraf Post Sx'),
            (5, 'door rear left', 'Montante Sx'),
            (6, 'door front right', 'Parafango Ant Dx'),
            (7, 'door rear right', 'Porta Ant Dx'),
            (8, 'roof', 'Porta Post Dx'),
            (9, 'quarter left', 'Parafango Post Dx'),
            (10, 'quarter right', 'Montante DX'),
            (11, 'rail left', 'Cofano ANT'),
            (12, 'rail right', 'Tetto'),
            (13, 'hatch upper', 'Portellone/Baule'),
            (14, 'hatch lower', 'Baule Sotto'),
            (15, 'sill left', 'Sottoporta Sx'),
            (16, 'sill right', 'Sottoporta Dx'),
            (17, 'dashboard', 'Torpedo'),
            (18, 'other', 'Altro'),
        ]