from odoo import fields, models


class BoliProduct(models.Model):
    _name = 'boli.product'
    _description = 'Tabella di calcolo Levabolli'
    _order = 'name'

    name = fields.Char(string='Boli', required=True)