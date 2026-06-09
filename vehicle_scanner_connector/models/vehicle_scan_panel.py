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
    amount_small = fields.Integer(string='Small Dents', default=0)
    amount_medium = fields.Integer(string='Medium Dents', default=0)
    amount_large = fields.Integer(string='Large Dents', default=0)
    is_aluminum = fields.Boolean(string='Aluminum')
    is_glue = fields.Boolean(string='Glue')
    is_ptp = fields.Boolean(string='PTP')