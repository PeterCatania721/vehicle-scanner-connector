from odoo import api, fields, models


class VehicleScanLog(models.Model):
    _name = 'vehicle.scan.log'
    _description = 'Vehicle Scan Log'
    _order = 'received_at desc'

    name = fields.Char(string='Reference', required=True, index=True)
    source = fields.Selection(
        [
            ('budha', 'BUHDA'),
            ('generic', 'Generic API'),
        ],
        string='Source',
        required=True,
        default='generic',
    )
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', index=True)
    license_plate = fields.Char(string='License Plate', index=True)
    scan_id = fields.Char(string='External Scan ID', index=True)
    case_number = fields.Char(string='Case Number', index=True)
    claim_number = fields.Char(string='Claim Number')
    vehicle_description = fields.Char(string='Vehicle Description')
    chassis_number = fields.Char(string='Chassis Number')
    mileage = fields.Char(string='Mileage')
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
    error_message = fields.Text(string='Error Message')
    panel_ids = fields.One2many('vehicle.scan.panel', 'scan_log_id', string='Panels')
    attachment_count = fields.Integer(compute='_compute_attachment_count')
    total_dents = fields.Integer(compute='_compute_total_dents', store=True)

    @api.depends('panel_ids.amount_small', 'panel_ids.amount_medium', 'panel_ids.amount_large')
    def _compute_total_dents(self):
        for record in self:
            record.total_dents = sum(
                panel.amount_small + panel.amount_medium + panel.amount_large
                for panel in record.panel_ids
            )

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