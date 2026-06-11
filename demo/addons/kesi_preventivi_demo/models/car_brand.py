from odoo import fields, models


class CarBrand(models.Model):
    _name = 'car.brand'
    _description = 'Car Brand'
    _order = 'name'

    name = fields.Char(string='Marca', required=True)