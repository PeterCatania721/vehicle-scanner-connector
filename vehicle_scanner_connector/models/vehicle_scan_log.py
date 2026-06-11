from odoo import api, fields, models


class VehicleScanLog(models.Model):
    _name = 'vehicle.scan.log'
    _description = 'Vehicle Scan Log'
    _order = 'received_at desc'

    name = fields.Char(string='Reference', required=True, index=True)
    config_id = fields.Many2one('vehicle.scanner.config', string='Configuration', index=True)
    source = fields.Selection(
        [
            ('budha', 'BUHDA'),
            ('generic', 'Generic API'),
        ],
        string='Source',
        required=True,
        default='generic',
    )
    market_code = fields.Selection(
        related='config_id.market_code',
        store=True,
        readonly=True,
    )
    license_plate = fields.Char(string='License Plate', index=True)
    client_code = fields.Char(
        string='Client Code',
        index=True,
        help='Codice Cartella / client reference used to match preventivi.',
    )
    scan_id = fields.Char(string='External Scan ID', index=True)
    case_number = fields.Char(string='Case Number', index=True)
    claim_number = fields.Char(string='Claim Number')
    vehicle_description = fields.Char(string='Vehicle Description')
    chassis_number = fields.Char(string='Chassis Number')
    mileage = fields.Char(string='Mileage')
    insured_name = fields.Char(string='Insured Name')
    examiner = fields.Char(string='Examiner')
    first_registration = fields.Char(string='First Registration')
    remarks = fields.Text(string='Remarks')
    soft_pressing_labor = fields.Char(string='Soft Pressing Labor')
    bodywork_labor = fields.Char(string='Bodywork Labor')
    painting_labor = fields.Char(string='Painting Labor')
    vehicle_type = fields.Char(string='Vehicle Type')
    vehicle_color = fields.Char(string='Vehicle Color')
    vehicle_external_id = fields.Char(string='Vehicle External ID')
    is_scanned = fields.Boolean(string='Scanned')
    replacement_parts_json = fields.Text(string='Replacement Parts (JSON)')
    repairs_json = fields.Text(string='Repairs (JSON)')
    scan_data = fields.Text(string='Raw JSON')
    received_at = fields.Datetime(
        string='Received At',
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    status = fields.Selection(
        [
            ('received', 'Received'),
            ('processed', 'Processed'),
            ('error', 'Error'),
        ],
        string='Status',
        default='received',
        required=True,
        index=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Preventivo',
        index=True,
        ondelete='set null',
    )
    preventivi_action = fields.Selection(
        [
            ('created', 'Created'),
            ('updated', 'Updated'),
            ('skipped', 'Skipped'),
        ],
        string='Preventivi Action',
        readonly=True,
    )
    error_message = fields.Text(string='Error Message')
    panel_ids = fields.One2many('vehicle.scan.panel', 'scan_log_id', string='Panels')
    attachment_count = fields.Integer(compute='_compute_attachment_count')
    total_dents = fields.Integer(compute='_compute_total_dents', store=True)

    @api.depends(
        'panel_ids.amount_small',
        'panel_ids.amount_medium',
        'panel_ids.amount_large',
        'panel_ids.amount_oversize',
        'panel_ids.amount_total',
        'panel_ids.amount_10',
        'panel_ids.amount_20',
        'panel_ids.amount_30',
        'panel_ids.amount_40',
        'panel_ids.amount_50',
    )
    def _compute_total_dents(self):
        for record in self:
            total = 0
            for panel in record.panel_ids:
                total += (
                    panel.amount_small
                    + panel.amount_medium
                    + panel.amount_large
                    + panel.amount_oversize
                    + panel.amount_total
                    + panel.amount_10
                    + panel.amount_20
                    + panel.amount_30
                    + panel.amount_40
                    + panel.amount_50
                )
            record.total_dents = total

    def _compute_attachment_count(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)],
            ['res_id'],
            ['res_id'],
        )
        counts = {item['res_id']: item['res_id_count'] for item in attachment_data}
        for record in self:
            record.attachment_count = counts.get(record.id, 0)

    def action_view_attachments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachments',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'default_res_model': self._name, 'default_res_id': self.id},
        }

    def action_open_preventivo(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Preventivo',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
        }