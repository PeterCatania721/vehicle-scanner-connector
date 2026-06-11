from odoo import fields, models


class VehicleScannerConfig(models.Model):
    _inherit = 'vehicle.scanner.config'

    preventivi_boli_product_id = fields.Many2one(
        'boli.product',
        string='Default Tabella di calcolo',
        help='Default Levabolli pricing table applied to scanner-created preventivi.',
    )