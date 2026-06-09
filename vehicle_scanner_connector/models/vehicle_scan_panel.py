from odoo import fields, models


class VehicleScanPanel(models.Model):
    _name = 'vehicle.scan.panel'
    _description = 'Vehicle Scan Panel Damage'
    _order = 'panel_index'

    scan_log_id = fields.Many2one(
        'vehicle.scan.log',
        string='Scan Log',
        required=True,
        ondelete='cascade',
        index=True,
    )
    panel_index = fields.Integer(string='Panel #', required=True)
    panel_name = fields.Char(string='Panel Name', required=True)
    budha_name = fields.Char(string='BUHDA Part Name')
    amount_small = fields.Integer(string='Small Dents', default=0)
    amount_medium = fields.Integer(string='Medium Dents', default=0)
    amount_large = fields.Integer(string='Large Dents', default=0)
    amount_oversize = fields.Integer(string='Oversize Dents', default=0)
    amount_total = fields.Integer(string='Total Dents', default=0)
    average_size = fields.Char(string='Average Size')
    amount_10 = fields.Integer(string='Dents 1-10mm', default=0)
    amount_20 = fields.Integer(string='Dents 11-20mm', default=0)
    amount_30 = fields.Integer(string='Dents 21-30mm', default=0)
    amount_40 = fields.Integer(string='Dents 31-40mm', default=0)
    amount_50 = fields.Integer(string='Dents 41-80mm', default=0)
    is_aluminum = fields.Boolean(string='Aluminum')
    is_glue = fields.Boolean(string='Glue')
    is_ptp = fields.Boolean(string='PTP')
    market_format = fields.Char(string='Market Format')