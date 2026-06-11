import json
import logging
import re
import string

from odoo import _, api, models

_logger = logging.getLogger(__name__)

REVISION_SUFFIX_RE = re.compile(r'^(?P<base>.+?)(?:/(?P<suffix>R[A-Z]?))?$')
IDENTIFIER_PRIORITY = ('license_plate', 'ref', 'chassis')
REVISION_SUFFIX_FIELDS = ('license_plate', 'chassis')
REVISION_PRIMARY_PRIORITY = ('license_plate', 'chassis', 'ref')


class VehicleScanServicePreventivi(models.AbstractModel):
    _inherit = 'vehicle.scan.service'

    @api.model
    def _preventivi_fields_available(self):
        return 'license_plate' in self.env['sale.order']._fields

    @api.model
    def _strip_revision_suffix(self, value):
        if not value:
            return value
        value = str(value).strip()
        match = REVISION_SUFFIX_RE.match(value)
        return match.group('base') if match else value

    @api.model
    def _iter_revision_candidates(self, base):
        yield base
        yield f'{base}/R'
        for letter in string.ascii_uppercase:
            yield f'{base}/R{letter}'

    @api.model
    def _allocate_revision_suffix(self, SaleOrder, field_name, base_value):
        base = self._strip_revision_suffix(base_value)
        for candidate in self._iter_revision_candidates(base):
            if not SaleOrder.search([(field_name, '=', candidate)], limit=1):
                if candidate == base:
                    return ''
                return candidate[len(base):]
        raise ValueError(_('No unique revision suffix available for %s') % base_value)

    @api.model
    def _scan_identifiers(self, scan_log):
        plate = self.normalize_license_plate(scan_log.license_plate) if scan_log.license_plate else False
        client_code = (scan_log.client_code or scan_log.case_number or '').strip() or False
        chassis = (scan_log.chassis_number or '').strip() or False
        return {
            'license_plate': plate,
            'ref': client_code,
            'chassis': chassis,
        }

    @api.model
    def _values_match_identifier(self, order, field_name, value):
        if field_name not in order._fields:
            return False
        order_value = order[field_name]
        if not order_value or not value:
            return False
        if field_name in REVISION_SUFFIX_FIELDS:
            return self._strip_revision_suffix(order_value) == self._strip_revision_suffix(value)
        return str(order_value).strip() == str(value).strip()

    @api.model
    def _search_revision_family(self, SaleOrder, field_name, value):
        base = self._strip_revision_suffix(value)
        if field_name not in SaleOrder._fields or not base:
            return SaleOrder.browse()
        return SaleOrder.search([
            '|', '|',
            (field_name, '=', base),
            (field_name, '=', f'{base}/R'),
            (field_name, '=like', f'{base}/R_'),
        ])

    @api.model
    def _find_preventivo_for_update(self, identifiers):
        SaleOrder = self.env['sale.order'].sudo()
        active = {key: value for key, value in identifiers.items() if value}
        if not active:
            return SaleOrder.browse()

        candidates = SaleOrder.browse()
        if active.get('ref') and 'ref' in SaleOrder._fields:
            candidates = SaleOrder.search([('ref', '=', active['ref'])], limit=20)
        if not candidates and active.get('license_plate'):
            candidates = self._search_revision_family(
                SaleOrder, 'license_plate', active['license_plate'],
            )
        if not candidates and active.get('chassis'):
            candidates = self._search_revision_family(
                SaleOrder, 'chassis', active['chassis'],
            )

        if candidates:
            matched = candidates.filtered(
                lambda order: all(
                    self._values_match_identifier(order, field_name, value)
                    for field_name, value in active.items()
                )
            )
            if len(matched) == 1:
                return matched[:1]
            if len(matched) > 1:
                return matched.sorted('id', reverse=True)[:1]

        candidate_sets = []
        for field_name, value in active.items():
            orders = SaleOrder.search([(field_name, '=', value)])
            if field_name in REVISION_SUFFIX_FIELDS:
                orders |= self._search_revision_family(SaleOrder, field_name, value)
            candidate_sets.append(set(orders.ids))

        if len(active) == 1:
            field_name, value = next(iter(active.items()))
            orders = SaleOrder.search([(field_name, '=', value)], limit=1)
            if not orders and field_name in REVISION_SUFFIX_FIELDS:
                orders = self._search_revision_family(SaleOrder, field_name, value)[:1]
            return orders

        intersection = set.intersection(*candidate_sets) if candidate_sets else set()
        if len(intersection) == 1:
            return SaleOrder.browse(next(iter(intersection)))
        return SaleOrder.browse()

    @api.model
    def _scan_indicates_hail(self, scan_log):
        if scan_log.panel_ids or scan_log.total_dents:
            return True
        try:
            data = json.loads(scan_log.scan_data or '{}')
        except (TypeError, ValueError):
            return False
        damage = data.get('damage') or {}
        return bool(damage.get('hail'))

    @api.model
    def _scan_indicates_parking_damage(self, scan_log):
        try:
            data = json.loads(scan_log.scan_data or '{}')
        except (TypeError, ValueError):
            return False
        damage = data.get('damage') or {}
        return bool(damage.get('panels') or damage.get('parking'))

    @api.model
    def _resolve_partner_by_name(self, name):
        if not name:
            return False
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search([('name', '=ilike', name.strip())], limit=1)
        return partner.id if partner else False

    @api.model
    def _panel_has_damage(self, panel):
        return any([
            panel.amount_small,
            panel.amount_medium,
            panel.amount_large,
            panel.amount_oversize,
            panel.amount_total,
            panel.amount_10,
            panel.amount_20,
            panel.amount_30,
            panel.amount_40,
            panel.amount_50,
            panel.is_glue,
            panel.is_aluminum,
            panel.is_ptp,
        ])

    @api.model
    def _panel_dent_counts(self, panel, market_code):
        if market_code in ('CH', 'AT', 'SL'):
            sotto = panel.amount_small
            sopra = panel.amount_medium + panel.amount_large + panel.amount_oversize
        elif market_code in ('DE', 'NL'):
            sotto = panel.amount_total
            sopra = 0
        elif market_code == 'FR':
            sotto = panel.amount_10 + panel.amount_20
            sopra = panel.amount_30 + panel.amount_40 + panel.amount_50
        elif market_code == 'US':
            sotto = max(panel.amount_total - panel.amount_oversize, 0)
            sopra = panel.amount_oversize
        else:
            sotto = panel.amount_small + panel.amount_medium
            sopra = panel.amount_large + panel.amount_oversize
        return sotto, sopra

    @api.model
    def _resolve_boli_product_id(self, config):
        boli_product = getattr(config, 'preventivi_boli_product_id', False)
        if boli_product:
            return boli_product.id
        if config.preventivi_boli_product_ref:
            return config.preventivi_boli_product_ref
        return False

    @api.model
    def _build_bolli_vals_from_scan(self, scan_log, config):
        SaleOrder = self.env['sale.order']
        available = SaleOrder._fields
        vals = {}
        market_code = config.market_code

        for panel in scan_log.panel_ids:
            row = config.get_kesi_bolli_row(panel.panel_index)
            if not row:
                continue
            sotto, sopra = self._panel_dent_counts(panel, market_code)
            has_damage = self._panel_has_damage(panel)
            if not has_damage:
                continue

            field_map = {
                f'g{row}': panel.is_glue or bool(sotto or sopra),
                f'a{row}': panel.is_aluminum,
                f'p{row}': panel.is_ptp,
                f'mm_{row}': bool(sotto or sopra),
                f'sotto{row}': sotto,
                f'sopra{row}': sopra,
            }
            for field_name, value in field_map.items():
                if field_name not in available:
                    continue
                if field_name.startswith(('sotto', 'sopra')):
                    if value:
                        vals[field_name] = vals.get(field_name, 0) + value
                elif value:
                    vals[field_name] = value
        return vals

    @api.model
    def _resolve_car_brand_model(self, vehicle_description):
        if not vehicle_description or 'brand_id' not in self.env['sale.order']._fields:
            return {}
        parts = str(vehicle_description).strip().split()
        if not parts:
            return {}
        brand_name = parts[0]
        model_name = parts[1] if len(parts) > 1 else False
        vals = {}
        if 'car.brand' in self.env:
            brand = self.env['car.brand'].sudo().search([('name', '=ilike', brand_name)], limit=1)
            if not brand:
                brand = self.env['car.brand'].sudo().create({'name': brand_name})
            vals['brand_id'] = brand.id
            if model_name and 'car.model' in self.env:
                model = self.env['car.model'].sudo().search([
                    ('name', '=ilike', model_name),
                    ('brand_id', '=', brand.id),
                ], limit=1)
                if not model:
                    model = self.env['car.model'].sudo().create({
                        'name': model_name,
                        'brand_id': brand.id,
                    })
                vals['model_id'] = model.id
        return vals

    @api.model
    def _build_preventivi_vals(self, scan_log, config, identifiers, revision_suffix=''):
        SaleOrder = self.env['sale.order']
        available = SaleOrder._fields
        vals = {}

        for field_name in IDENTIFIER_PRIORITY:
            value = identifiers.get(field_name)
            if not value or field_name not in available:
                continue
            base = self._strip_revision_suffix(value)
            if field_name in REVISION_SUFFIX_FIELDS and revision_suffix:
                vals[field_name] = f'{base}{revision_suffix}'
            else:
                vals[field_name] = base

        field_sources = {
            'practice_no': scan_log.claim_number,
            'km': scan_log.mileage,
        }
        for field_name, value in field_sources.items():
            if value and field_name in available:
                vals[field_name] = value

        has_hail = self._scan_indicates_hail(scan_log)
        if 'hail' in available:
            vals['hail'] = has_hail
        if 'dent_remover' in available:
            vals['dent_remover'] = has_hail
        if 'panels' in available:
            vals['panels'] = self._scan_indicates_parking_damage(scan_log)

        vals.update(self._resolve_car_brand_model(scan_log.vehicle_description))

        if 'insurance_id' in available and scan_log.insured_name:
            insurance_id = self._resolve_partner_by_name(scan_log.insured_name)
            if insurance_id:
                vals['insurance_id'] = insurance_id
        if 'expert_id' in available and scan_log.examiner:
            expert_id = self._resolve_partner_by_name(scan_log.examiner)
            if expert_id:
                vals['expert_id'] = expert_id

        if config.preventivi_user_id and 'user_id' in available:
            vals['user_id'] = config.preventivi_user_id.id
        if config.preventivi_partner_id and 'partner_id' in available:
            vals['partner_id'] = config.preventivi_partner_id.id

        if 'billing_status' in available:
            vals['billing_status'] = vals.get('billing_status') or 'not_paid'

        boli_product_id = self._resolve_boli_product_id(config)
        if boli_product_id and 'boli_product_id' in available:
            vals['boli_product_id'] = boli_product_id

        vals.update(self._build_bolli_vals_from_scan(scan_log, config))
        return vals

    @api.model
    def _ensure_preventivi_order_line(self, order, config, is_new):
        if not is_new or not config.preventivi_product_id or order.order_line:
            return
        self.env['sale.order.line'].sudo().create({
            'order_id': order.id,
            'product_id': config.preventivi_product_id.id,
            'product_uom_qty': 1,
        })

    @api.model
    def _copy_scan_attachments_to_order(self, scan_log, order):
        Attachment = self.env['ir.attachment'].sudo()
        attachments = Attachment.search([
            ('res_model', '=', 'vehicle.scan.log'),
            ('res_id', '=', scan_log.id),
        ])
        for attachment in attachments:
            attachment.copy({
                'res_model': 'sale.order',
                'res_id': order.id,
            })

    @api.model
    def sync_preventivi_from_scan(self, scan_log, config):
        if not config.enable_preventivi_sync:
            return {'action': 'skipped', 'reason': 'disabled'}

        if not self._preventivi_fields_available():
            return {'action': 'skipped', 'reason': 'no_preventivi_fields'}

        if not config.preventivi_partner_id:
            raise ValueError(_('Configure a default Preventivi customer on the scanner configuration.'))

        identifiers = self._scan_identifiers(scan_log)
        if not any(identifiers.values()):
            return {'action': 'skipped', 'reason': 'no_identifier'}

        SaleOrder = self.env['sale.order'].sudo()
        order = self._find_preventivo_for_update(identifiers)
        is_new = not order

        if is_new:
            primary_field = next(
                (field_name for field_name in REVISION_PRIMARY_PRIORITY if identifiers.get(field_name)),
                None,
            )
            revision_suffix = self._allocate_revision_suffix(
                SaleOrder,
                primary_field,
                identifiers[primary_field],
            )
            vals = self._build_preventivi_vals(scan_log, config, identifiers, revision_suffix)
            order = SaleOrder.create(vals)
            action = 'created'
        else:
            vals = self._build_preventivi_vals(scan_log, config, identifiers)
            vals.pop('partner_id', None)
            for field_name in IDENTIFIER_PRIORITY:
                vals.pop(field_name, None)
            order.write(vals)
            action = 'updated'

        self._ensure_preventivi_order_line(order, config, is_new)
        self._copy_scan_attachments_to_order(scan_log, order)

        scan_log.write({
            'sale_order_id': order.id,
            'preventivi_action': action,
            'status': 'processed',
        })

        _logger.info(
            'Preventivi %s from scan log %s -> sale.order %s (%s)',
            action,
            scan_log.id,
            order.id,
            order.name,
        )
        return {
            'action': action,
            'sale_order_id': order.id,
            'sale_order_name': order.name,
            'license_plate': order.license_plate if 'license_plate' in order._fields else False,
        }