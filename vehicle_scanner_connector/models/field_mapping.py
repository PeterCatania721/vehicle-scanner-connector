from odoo import fields, models


class VehicleScannerFieldMapping(models.Model):
    _name = 'vehicle.scanner.field.mapping'
    _description = 'Custom JSON Field Mapping'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'vehicle.scanner.config',
        string='Configuration',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    source_path = fields.Char(
        string='Source JSON Path',
        required=True,
        help='Dot-notation path in incoming JSON, e.g. Kennzeichen, Dents.1.amountSmall, damage.severity.',
    )
    target_field = fields.Selection(
        [
            ('license_plate', 'License Plate'),
            ('case_number', 'Case Number'),
            ('claim_number', 'Claim Number'),
            ('vehicle_description', 'Vehicle Description'),
            ('chassis_number', 'Chassis Number'),
            ('mileage', 'Mileage'),
            ('insured_name', 'Insured Name'),
            ('examiner', 'Examiner'),
            ('first_registration', 'First Registration'),
            ('remarks', 'Remarks'),
            ('soft_pressing_labor', 'Soft Pressing Labor'),
            ('bodywork_labor', 'Bodywork Labor'),
            ('painting_labor', 'Painting Labor'),
            ('vehicle_type', 'Vehicle Type'),
            ('vehicle_color', 'Vehicle Color'),
            ('vehicle_external_id', 'Vehicle External ID'),
            ('scan_id', 'External Scan ID'),
        ],
        string='Target Scan Log Field',
        required=True,
    )
    transform = fields.Selection(
        [
            ('none', 'None'),
            ('upper', 'Uppercase'),
            ('lower', 'Lowercase'),
            ('strip', 'Strip Whitespace'),
            ('int', 'Integer'),
            ('float', 'Float'),
            ('bool', 'Boolean'),
            ('json', 'JSON Serialize'),
        ],
        default='none',
    )
    default_value = fields.Char(
        help='Value used when the source path is missing or empty.',
    )