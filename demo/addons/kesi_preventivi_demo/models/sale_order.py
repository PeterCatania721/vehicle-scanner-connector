from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    license_plate = fields.Char(string='Targa')
    hail = fields.Boolean(string='GRANDINE')
    panels = fields.Boolean(string='Danni da parcheggio')
    dent_remover = fields.Boolean(string='Danni da Grandine')
    chassis = fields.Char(string='Telaio')
    ref = fields.Char(string='Codice Cartella')
    practice_no = fields.Char(string='N°Pratica')
    km = fields.Char(string='Km')
    insurance_id = fields.Many2one('res.partner', string='Assicurazione')
    expert_id = fields.Many2one('res.partner', string='Perito')
    brand_id = fields.Many2one('car.brand', string='Marca')
    model_id = fields.Many2one(
        'car.model',
        string='Modello',
        domain="[('brand_id', '=', brand_id)]",
    )
    color_id = fields.Many2one('car.color', string='Colore')
    billing_status = fields.Selection(
        selection=[
            ('paid', 'Pagato'),
            ('not_paid', 'Non Pagato'),
            ('in_progress', 'In Pagamento'),
        ],
        string='Levabolli',
    )
    boli_product_id = fields.Many2one('boli.product', string='Tabella di calcolo')