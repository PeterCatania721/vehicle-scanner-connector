from odoo import fields, models


class CarModel(models.Model):
    _name = 'car.model'
    _description = 'Car Model'
    _order = 'name'

    name = fields.Char(string='Modello', required=True)
    brand_id = fields.Many2one('car.brand', string='Marca', ondelete='restrict')