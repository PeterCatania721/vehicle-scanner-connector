from odoo import fields, models


class CarColor(models.Model):
    _name = 'car.color'
    _description = 'Car Color'
    _order = 'name'

    name = fields.Char(string='Colore', required=True)