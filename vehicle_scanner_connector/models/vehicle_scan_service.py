import json
import logging
import re
from datetime import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# KESI panel map (index -> Italian label), aligned with Budha Connection Flask.
PANEL_NAMES = {
    1: 'Parafango Ant Sx',
    2: 'Porta Ant SX',
    3: 'Porta Post SX',
    4: 'Paraf Post Sx',
    5: 'Montante Sx',
    6: 'Parafango Ant Dx',
    7: 'Porta Ant Dx',
    8: 'Porta Post Dx',
    9: 'Parafango Post Dx',
    10: 'Montante DX',
    11: 'Cofano ANT',
    12: 'Tetto',
    13: 'Portellone/Baule',
    14: 'Baule Sotto',
    15: 'Sottoporta Sx',
    16: 'Sottoporta Dx',
    17: 'Torpedo',
    18: 'Altro',
}


class VehicleScanService(models.AbstractModel):
    _name = 'vehicle.scan.service'
    _description = 'Vehicle Scan Processing Service'

    @api.model
    def normalize_license_plate(self, plate):
        if not plate:
            return False
        return re.sub(r'\s+', ' ', str(plate).strip().upper())

    @api.model
    def find_vehicle(self, license_plate, config):
        plate = self.normalize_license_plate(license_plate)
        if not plate:
            return self.env['fleet.vehicle']
        Vehicle = self.env['fleet.vehicle'].sudo()
        vehicle = Vehicle.search([('license_plate', '=ilike', plate)], limit=1)
        if not vehicle:
            compact = plate.replace(' ', '')
            vehicle = Vehicle.search(
                [('license_plate', 'ilike', compact)],
                limit=1,
            )
        if not vehicle and config.auto_create_vehicle:
            vehicle = Vehicle.create({
                'name': plate,
                'license_plate': plate,
            })
        return vehicle

    @api.model
    def normalize_budha_payload(self, payload):
        """Accept the same shapes handled by Budha Connection Flask."""
        if isinstance(payload, dict) and 'CaseData' in payload:
            return [payload['CaseData']]
        if isinstance(payload, list):
            cases = []
            for item in payload:
                if not isinstance(item, dict):
                    continue
                cases.append(item.get('CaseData', item))
            return cases or None
        if isinstance(payload, dict) and payload.get('Vorgangsnummer'):
            return [payload]
        return None

    @api.model
    def _safe_int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @api.model
    def _panel_lines_from_dents(self, dents):
        lines = []
        if not isinstance(dents, dict):
            return lines
        for key, dent in dents.items():
            try:
                panel_index = int(key)
            except (TypeError, ValueError):
                continue
            if not isinstance(dent, dict):
                continue
            lines.append({
                'panel_index': panel_index,
                'panel_name': PANEL_NAMES.get(panel_index, f'Panel {panel_index}'),
                'amount_small': self._safe_int(dent.get('amountSmall')),
                'amount_medium': self._safe_int(dent.get('amountMedium')),
                'amount_large': self._safe_int(dent.get('amountLarge')),
                'is_aluminum': bool(dent.get('alu')),
                'is_glue': bool(dent.get('glue')),
                'is_ptp': bool(dent.get('ptp')),
            })
        return lines

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
    def process_budha_cases(self, payload):
        config = self.env['vehicle.scanner.config'].sudo().get_active_config()
        cases = self.normalize_budha_payload(payload)
        if not cases:
            raise ValueError(_('Unrecognized BUHDA JSON format'))

        ScanLog = self.env['vehicle.scan.log'].sudo()
        results = []
        for index, case_data in enumerate(cases, start=1):
            result = self._process_single_budha_case(case_data, index, config, ScanLog)
            results.append(result)
        return {
            'status': 'ok',
            'cases_received': len(results),
            'details': results,
        }

    @api.model
    def _process_single_budha_case(self, case_data, index, config, ScanLog):
        case_number = case_data.get('Vorgangsnummer') or f'case_{index}'
        license_plate = case_data.get('Kennzeichen') or case_data.get('plate') or case_data.get('targa')
        vehicle = self.find_vehicle(license_plate, config)

        clean_data = {
            key: value
            for key, value in case_data.items()
            if key not in ('attachmentsPDF', 'overviewPDF')
        }

        scan_log = ScanLog.create({
            'name': f'BUHDA {case_number}',
            'source': 'budha',
            'vehicle_id': vehicle.id if vehicle else False,
            'license_plate': self.normalize_license_plate(license_plate),
            'case_number': case_number,
            'claim_number': case_data.get('Schadennummer'),
            'vehicle_description': case_data.get('Fahrzeug'),
            'chassis_number': case_data.get('Fahrgestellnummer'),
            'mileage': case_data.get('Kilometerstand'),
            'scan_data': json.dumps(clean_data, ensure_ascii=False, indent=2),
            'received_at': fields.Datetime.now(),
            'status': 'received',
            'panel_ids': [(0, 0, line) for line in self._panel_lines_from_dents(case_data.get('Dents'))],
        })

        pdf_saved = self._create_attachments_from_budha_pdfs(scan_log, case_data)
        _logger.info('BUHDA scan received: case=%s plate=%s log_id=%s', case_number, license_plate, scan_log.id)

        return {
            'vorgangsnummer': case_number,
            'scan_log_id': scan_log.id,
            'license_plate': scan_log.license_plate,
            'pdf_saved': pdf_saved,
        }

    @api.model
    def process_generic_scan(self, data):
        config = self.env['vehicle.scanner.config'].sudo().get_active_config()
        license_plate = data.get('plate') or data.get('targa')
        if not license_plate:
            raise ValueError(_('Vehicle plate is required'))

        vehicle = self.find_vehicle(license_plate, config)
        scan_id = data.get('scan_id')
        damage = data.get('damage') or {}

        scan_log = self.env['vehicle.scan.log'].sudo().create({
            'name': f'Scan {license_plate} {scan_id or datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'source': 'generic',
            'vehicle_id': vehicle.id if vehicle else False,
            'license_plate': self.normalize_license_plate(license_plate),
            'scan_id': scan_id,
            'scan_data': json.dumps(data, ensure_ascii=False, indent=2),
            'received_at': fields.Datetime.now(),
            'status': 'received',
        })

        images_saved = self._create_attachments_from_images(scan_log, data.get('images'))
        if damage:
            scan_log.write({'scan_data': json.dumps({**data, 'damage': damage}, ensure_ascii=False, indent=2)})

        _logger.info('Generic scan received: plate=%s log_id=%s', license_plate, scan_log.id)
        return {
            'success': True,
            'message': 'Vehicle scan processed successfully',
            'scan_log_id': scan_log.id,
            'license_plate': scan_log.license_plate,
            'images_saved': images_saved,
            'received_at': fields.Datetime.to_string(scan_log.received_at),
        }