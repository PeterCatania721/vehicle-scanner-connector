import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

PARSER_RULE_TEMPLATE = """# Available variables:
#   env         - Odoo environment
#   payload     - full incoming JSON payload
#   case_data   - normalized case dict (BUHDA) or scan dict (generic)
#   config      - active vehicle.scanner.config record
#   result      - assign the modified dict to this variable
#
# Example: normalize Swiss license plates
if case_data.get('Kennzeichen'):
    case_data['Kennzeichen'] = case_data['Kennzeichen'].replace('-', ' ').strip()
result = case_data
"""


class VehicleScannerParserRule(models.Model):
    _name = 'vehicle.scanner.parser.rule'
    _description = 'Custom Vehicle Scan Parser Rule'
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
    apply_on = fields.Selection(
        [
            ('budha', 'BUHDA Payloads'),
            ('generic', 'Generic Payloads'),
            ('both', 'All Payloads'),
        ],
        default='both',
        required=True,
    )
    python_code = fields.Text(
        string='Python Code',
        default=PARSER_RULE_TEMPLATE,
        required=True,
        help='Python code executed in a restricted sandbox. Assign the final dict to `result`.',
    )
    notes = fields.Text()

    def _get_safe_globals(self, payload, case_data, config):
        import json
        import re
        from datetime import datetime

        return {
            'env': self.env,
            'payload': payload,
            'case_data': case_data,
            'config': config,
            'result': case_data,
            'json': json,
            're': re,
            'datetime': datetime,
            '_logger': _logger,
            'ValidationError': ValidationError,
            '_': _,
        }

    @api.model
    def run_rules(self, config, payload, case_data, source):
        rules = config.parser_rule_ids.filtered(
            lambda r: r.active and r.apply_on in (source, 'both')
        ).sorted('sequence')
        result = dict(case_data or {})
        for rule in rules:
            localdict = rule._get_safe_globals(payload, result, config)
            try:
                safe_eval(rule.python_code, localdict, mode='exec', nocopy=True)
            except Exception as exc:
                _logger.exception('Parser rule %s failed', rule.name)
                raise ValidationError(
                    _('Custom parser rule "%(name)s" failed: %(error)s', name=rule.name, error=exc)
                ) from exc
            result = localdict.get('result', result)
            if not isinstance(result, dict):
                raise ValidationError(
                    _('Custom parser rule "%(name)s" must assign a dict to `result`.', name=rule.name)
                )
        return result