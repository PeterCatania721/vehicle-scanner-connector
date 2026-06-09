import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class VehicleScanService(models.AbstractModel):
    _name = 'vehicle.scan.service'
    _description = 'Vehicle Scan Processing Service'

    @api.model
    def normalize_license_plate(self, plate):
        if not plate:
            return False
        return re.sub(r'\s+', ' ', str(plate).strip().upper())

    @api.model
    def _extract_json_path(self, data, path):
        current = data
        for part in (path or '').split('.'):
            if not part:
                continue
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    current = current[int(part)]
                except (ValueError, IndexError, TypeError):
                    return None
            else:
                return None
        return current

    @api.model
    def _apply_transform(self, value, transform):
        if value in (None, '', False) and transform != 'bool':
            return False
        if transform == 'upper':
            return str(value).upper()
        if transform == 'lower':
            return str(value).lower()
        if transform == 'strip':
            return str(value).strip()
        if transform == 'int':
            try:
                return int(value or 0)
            except (TypeError, ValueError):
                return 0
        if transform == 'float':
            try:
                return float(value or 0)
            except (TypeError, ValueError):
                return 0.0
        if transform == 'bool':
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('1', 'true', 'yes', 'y', 'on')
        if transform == 'json':
            return json.dumps(value, ensure_ascii=False)
        return value

    @api.model
    def _safe_int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @api.model
    def _get_value_from_sources(self, data, *keys):
        for key in keys:
            if not key:
                continue
            value = self._extract_json_path(data, key) if '.' in key else data.get(key)
            if value not in (None, '', False):
                return value
        return False

    @api.model
    def apply_field_mappings(self, config, data, base_vals):
        vals = dict(base_vals)
        for mapping in config.field_mapping_ids.filtered('active').sorted('sequence'):
            value = self._extract_json_path(data, mapping.source_path)
            if value in (None, '', False):
                if mapping.default_value not in (None, '', False):
                    value = mapping.default_value
                else:
                    continue
            value = self._apply_transform(value, mapping.transform)
            vals[mapping.target_field] = value
        return vals

    @api.model
    def find_vehicle(self, license_plate, config):
        plate = self.normalize_license_plate(license_plate)
        if not plate:
            return self.env['fleet.vehicle']
        Vehicle = self.env['fleet.vehicle'].sudo()
        vehicle = Vehicle.search([('license_plate', '=ilike', plate)], limit=1)
        if not vehicle:
            compact = plate.replace(' ', '')
            vehicle = Vehicle.search([('license_plate', 'ilike', compact)], limit=1)
        if not vehicle and config.auto_create_vehicle:
            vehicle = Vehicle.create({'name': plate, 'license_plate': plate})
        return vehicle

    @api.model
    def normalize_budha_payload(self, payload, config):
        wrapper = (config.payload_wrapper_key or '').strip()
        if wrapper and isinstance(payload, dict) and wrapper in payload:
            return [payload[wrapper]]
        if isinstance(payload, dict) and 'CaseData' in payload:
            return [payload['CaseData']]
        if isinstance(payload, list):
            cases = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                if wrapper and wrapper in item:
                    cases.append(item[wrapper])
                else:
                    cases.append(item.get('CaseData', item))
            return cases or None
        if isinstance(payload, dict) and payload.get('Vorgangsnummer'):
            return [payload]
        return None

    @api.model
    def _panel_line_from_dent(self, panel_index, dent, config, market_code):
        mapping = config.panel_mapping_ids.filtered(
            lambda m: m.active and m.panel_index == panel_index
        )[:1]
        line = {
            'panel_index': panel_index,
            'panel_name': config.get_panel_name(panel_index),
            'budha_name': mapping.budha_name if mapping else False,
            'is_aluminum': bool(dent.get('alu')),
            'is_glue': bool(dent.get('glue')),
            'is_ptp': bool(dent.get('ptp')),
            'market_format': market_code,
        }

        if market_code in ('CH', 'AT', 'SL'):
            line.update({
                'amount_small': self._safe_int(dent.get('amountSmall')),
                'amount_medium': self._safe_int(dent.get('amountMedium')),
                'amount_large': self._safe_int(dent.get('amountLarge')),
                'amount_oversize': self._safe_int(dent.get('oversizeAmount')),
            })
        elif market_code in ('DE', 'NL'):
            line.update({
                'amount_total': self._safe_int(dent.get('amount')),
                'average_size': str(dent.get('avarageSize') or dent.get('averageSize') or ''),
            })
        elif market_code == 'FR':
            line.update({
                'amount_10': self._safe_int(dent.get('amount10')),
                'amount_20': self._safe_int(dent.get('amount20')),
                'amount_30': self._safe_int(dent.get('amount30')),
                'amount_40': self._safe_int(dent.get('amount40')),
                'amount_50': self._safe_int(dent.get('amount50')),
            })
        elif market_code == 'US':
            line.update({
                'amount_total': self._safe_int(dent.get('amount')),
                'average_size': str(dent.get('avarageSize') or dent.get('averageSize') or ''),
                'amount_oversize': self._safe_int(dent.get('oversizeAmount')),
            })
        else:
            line.update({
                'amount_small': self._safe_int(dent.get('amountSmall')),
                'amount_medium': self._safe_int(dent.get('amountMedium')),
                'amount_large': self._safe_int(dent.get('amountLarge')),
            })
        return line

    @api.model
    def _panel_lines_from_dents(self, dents, config):
        lines = []
        if not isinstance(dents, dict) or not config.auto_process_panels:
            return lines
        market_code = config.market_code
        for key, dent in dents.items():
            try:
                panel_index = int(key)
            except (TypeError, ValueError):
                continue
            if not isinstance(dent, dict):
                continue
            lines.append(self._panel_line_from_dent(panel_index, dent, config, market_code))
        return lines

    @api.model
    def _serialize_json_field(self, value):
        if value in (None, '', False):
            return False
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    @api.model
    def _build_budha_log_vals(self, case_data, config, index):
        case_number = case_data.get('Vorgangsnummer') or f'case_{index}'
        license_plate = self._get_value_from_sources(
            case_data, 'Kennzeichen', 'plate', 'targa'
        )
        vehicle = self.find_vehicle(license_plate, config)

        clean_data = dict(case_data)
        if config.strip_pdf_from_json_log:
            clean_data.pop('overviewPDF', None)
            clean_data.pop('attachmentsPDF', None)

        vals = {
            'name': f'BUHDA {case_number}',
            'source': 'budha',
            'config_id': config.id,
            'vehicle_id': vehicle.id if vehicle else False,
            'license_plate': self.normalize_license_plate(license_plate),
            'case_number': case_number,
            'claim_number': case_data.get('Schadennummer'),
            'vehicle_description': case_data.get('Fahrzeug'),
            'chassis_number': case_data.get('Fahrgestellnummer'),
            'mileage': case_data.get('Kilometerstand'),
            'insured_name': case_data.get('Versicherungsnehmer'),
            'examiner': case_data.get('Begutachter'),
            'first_registration': case_data.get('Erstzulassung'),
            'remarks': case_data.get('Bemerkungen'),
            'soft_pressing_labor': case_data.get('Weichdrücklohn'),
            'bodywork_labor': case_data.get('Karosserielohn'),
            'painting_labor': case_data.get('Lackierlohn'),
            'vehicle_type': case_data.get('Fahrzeugart'),
            'vehicle_color': case_data.get('Helligkeit'),
            'vehicle_external_id': case_data.get('idFahrzeug'),
            'is_scanned': bool(case_data.get('Scanned')),
            'replacement_parts_json': self._serialize_json_field(case_data.get('Ersatzteile')),
            'repairs_json': self._serialize_json_field(case_data.get('Instandsetzen')),
            'scan_data': json.dumps(clean_data, ensure_ascii=False, indent=2),
            'received_at': fields.Datetime.now(),
            'status': 'received',
            'panel_ids': [(0, 0, line) for line in self._panel_lines_from_dents(case_data.get('Dents'), config)],
        }
        return vals, license_plate, case_number, vehicle

    @api.model
    def _create_attachments_from_budha_pdfs(self, scan_log, case_data):
        Attachment = self.env['ir.attachment'].sudo()
        saved = []

        overview = case_data.get('overviewPDF')
        if overview:
            attachment = Attachment.create({
                'name': 'overview.pdf',
                'type': 'binary',
                'datas': overview,
                'res_model': 'vehicle.scan.log',
                'res_id': scan_log.id,
                'mimetype': 'application/pdf',
            })
            saved.append(attachment.name)

        for name, content in (case_data.get('attachmentsPDF') or {}).items():
            if not content:
                continue
            attachment = Attachment.create({
                'name': f'{name}.pdf',
                'type': 'binary',
                'datas': content,
                'res_model': 'vehicle.scan.log',
                'res_id': scan_log.id,
                'mimetype': 'application/pdf',
            })
            saved.append(attachment.name)
        return saved

    @api.model
    def _create_attachments_from_images(self, scan_log, images):
        Attachment = self.env['ir.attachment'].sudo()
        saved = []
        for image in images or []:
            filename = image.get('filename')
            data = image.get('data')
            if not filename or not data:
                continue
            lower = filename.lower()
            if lower.endswith(('.jpg', '.jpeg')):
                mimetype = 'image/jpeg'
            elif lower.endswith('.png'):
                mimetype = 'image/png'
            elif lower.endswith('.pdf'):
                mimetype = 'application/pdf'
            else:
                mimetype = 'application/octet-stream'
            attachment = Attachment.create({
                'name': filename,
                'type': 'binary',
                'datas': data,
                'res_model': 'vehicle.scan.log',
                'res_id': scan_log.id,
                'mimetype': mimetype,
            })
            saved.append(attachment.name)
        return saved

    @api.model
    def _validate_license_plate(self, config, license_plate):
        if config.require_license_plate and not license_plate:
            raise ValueError(_('Vehicle plate is required'))

    @api.model
    def process_budha_cases(self, payload):
        config = self.env['vehicle.scanner.config'].sudo().get_active_config()
        if not config.enable_budha_endpoint and not self.env.context.get('inbound_mode'):
            raise ValueError(_('BUHDA endpoint is disabled in configuration'))

        cases = self.normalize_budha_payload(payload, config)
        if not cases:
            raise ValueError(_('Unrecognized BUHDA JSON format'))

        ParserRule = self.env['vehicle.scanner.parser.rule'].sudo()
        ScanLog = self.env['vehicle.scan.log'].sudo()
        results = []

        for index, case_data in enumerate(cases, start=1):
            case_data = ParserRule.run_rules(config, payload, case_data, 'budha')
            vals, license_plate, case_number, vehicle = self._build_budha_log_vals(case_data, config, index)
            vals = self.apply_field_mappings(config, case_data, vals)
            self._validate_license_plate(config, vals.get('license_plate'))

            scan_log = ScanLog.create(vals)
            pdf_saved = self._create_attachments_from_budha_pdfs(scan_log, case_data)
            _logger.info('BUHDA scan received: case=%s plate=%s log_id=%s', case_number, license_plate, scan_log.id)

            detail = {
                'vorgangsnummer': case_number,
                'license_plate': scan_log.license_plate,
                'pdf_saved': pdf_saved,
            }
            if config.include_scan_log_id:
                detail['scan_log_id'] = scan_log.id
            results.append(detail)

        response = config.build_success_response({
            'cases_received': len(results),
            'details': results,
        })
        return response

    @api.model
    def process_generic_scan(self, data):
        config = self.env['vehicle.scanner.config'].sudo().get_active_config()
        if not config.enable_generic_endpoint and not self.env.context.get('inbound_mode'):
            raise ValueError(_('Generic endpoint is disabled in configuration'))

        ParserRule = self.env['vehicle.scanner.parser.rule'].sudo()
        data = ParserRule.run_rules(config, data, data, 'generic')

        license_plate = self._get_value_from_sources(data, 'plate', 'targa', 'Kennzeichen')
        self._validate_license_plate(config, license_plate)

        vehicle = self.find_vehicle(license_plate, config)
        scan_id = data.get('scan_id')

        vals = {
            'name': f'Scan {license_plate or "unknown"} {scan_id or datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'source': 'generic',
            'config_id': config.id,
            'vehicle_id': vehicle.id if vehicle else False,
            'license_plate': self.normalize_license_plate(license_plate),
            'scan_id': scan_id,
            'scan_data': json.dumps(data, ensure_ascii=False, indent=2),
            'received_at': fields.Datetime.now(),
            'status': 'received',
        }
        vals = self.apply_field_mappings(config, data, vals)

        scan_log = self.env['vehicle.scan.log'].sudo().create(vals)
        images_saved = self._create_attachments_from_images(scan_log, data.get('images'))

        _logger.info('Generic scan received: plate=%s log_id=%s', license_plate, scan_log.id)
        response = {
            'success': True,
            'message': config.response_success_message,
            'scan_log_id': scan_log.id,
            'license_plate': scan_log.license_plate,
            'images_saved': images_saved,
            'received_at': fields.Datetime.to_string(scan_log.received_at),
        }
        if not config.include_scan_log_id:
            response.pop('scan_log_id', None)
        return response

    @api.model
    def process_inbound_payload(self, payload):
        config = self.env['vehicle.scanner.config'].sudo().get_active_config()
        if not config.enable_inbound_endpoint:
            raise ValueError(_('Inbound endpoint is disabled in configuration'))

        if self.normalize_budha_payload(payload, config):
            return self.with_context(inbound_mode=True).process_budha_cases(payload)
        if isinstance(payload, dict) and (
            payload.get('plate') or payload.get('targa') or payload.get('scan_id')
        ):
            return self.with_context(inbound_mode=True).process_generic_scan(payload)
        raise ValueError(_('Unable to detect payload format for inbound endpoint'))