import base64
import json

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestVehicleScanner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env['vehicle.scanner.config'].sudo().get_active_config()
        cls.config.write({
            'password': 'test-secret',
            'require_license_plate': False,
            'strip_pdf_from_json_log': True,
            'auto_process_panels': True,
            'market_code': 'CH',
        })
        cls.service = cls.env['vehicle.scan.service'].sudo()

    def _auth_header(self, username=None, password=None):
        user = username or self.config.username
        pwd = password or self.config.password
        token = base64.b64encode(f'{user}:{pwd}'.encode()).decode()
        return f'Basic {token}'

    def test_basic_auth_valid_and_invalid(self):
        self.assertTrue(self.config.check_basic_auth(self._auth_header()))
        self.assertFalse(self.config.check_basic_auth(self._auth_header(password='wrong')))

    def test_normalize_budha_payload_shapes(self):
        case = {'Vorgangsnummer': 'TEST-001', 'Kennzeichen': 'TI 100'}
        wrapped = self.service.normalize_budha_payload({'CaseData': case}, self.config)
        self.assertEqual(len(wrapped), 1)
        self.assertEqual(wrapped[0]['Vorgangsnummer'], 'TEST-001')

        raw = self.service.normalize_budha_payload(case, self.config)
        self.assertEqual(len(raw), 1)

        array = self.service.normalize_budha_payload([
            {'CaseData': {'Vorgangsnummer': 'A'}},
            {'Vorgangsnummer': 'B'},
        ], self.config)
        self.assertEqual([c['Vorgangsnummer'] for c in array], ['A', 'B'])

    def test_process_budha_case_creates_log_and_panels(self):
        payload = {
            'CaseData': {
                'Vorgangsnummer': 'SIM-001',
                'Kennzeichen': 'ti 200',
                'Fahrzeug': 'Test Car',
                'Dents': {
                    '1': {
                        'amountSmall': 2,
                        'amountMedium': 1,
                        'amountLarge': 0,
                        'oversizeAmount': 0,
                    },
                },
                'overviewPDF': base64.b64encode(b'%PDF-simulated').decode(),
            },
        }
        result = self.service.process_budha_cases(payload)
        self.assertTrue(result['success'])
        self.assertEqual(result['cases_received'], 1)

        log = self.env['vehicle.scan.log'].browse(result['details'][0]['scan_log_id'])
        self.assertEqual(log.license_plate, 'TI 200')
        self.assertEqual(log.source, 'budha')
        self.assertEqual(len(log.panel_ids), 1)
        self.assertEqual(log.panel_ids.amount_small, 2)
        self.assertNotIn('overviewPDF', log.scan_data)

    def test_process_generic_scan_creates_log(self):
        payload = {
            'plate': 'ZH 300',
            'scan_id': 'generic-001',
            'images': [{
                'filename': 'dent.jpg',
                'data': base64.b64encode(b'fake-image').decode(),
            }],
        }
        result = self.service.process_generic_scan(payload)
        self.assertTrue(result['success'])
        log = self.env['vehicle.scan.log'].browse(result['scan_log_id'])
        self.assertEqual(log.source, 'generic')
        self.assertEqual(log.license_plate, 'ZH 300')
        self.assertEqual(log.attachment_count, 1)

    def test_process_inbound_detects_budha(self):
        payload = {'CaseData': {'Vorgangsnummer': 'INB-001', 'Kennzeichen': 'TI 400'}}
        result = self.service.process_inbound_payload(payload)
        self.assertTrue(result['success'])
        self.assertEqual(result['cases_received'], 1)

    def test_require_license_plate_rejects_empty(self):
        self.config.require_license_plate = True
        payload = {'CaseData': {'Vorgangsnummer': 'NO-PLATE'}}
        with self.assertRaises(ValueError):
            self.service.process_budha_cases(payload)

    def test_panel_mapping_models_accessible(self):
        mapping = self.env['vehicle.scanner.panel.mapping'].sudo().create({
            'config_id': self.config.id,
            'panel_index': 99,
            'budha_name': 'test-panel',
            'kesi_name': 'Test Panel',
        })
        field_map = self.env['vehicle.scanner.field.mapping'].sudo().create({
            'config_id': self.config.id,
            'name': 'Plate override',
            'source_path': 'plate',
            'target_field': 'license_plate',
        })
        self.assertEqual(mapping.kesi_name, 'Test Panel')
        self.assertEqual(field_map.target_field, 'license_plate')

    def test_api_urls_use_selected_paths(self):
        self.config.budha_webhook_path = '/vehicle_scanner/budha'
        self.config.generic_webhook_path = '/api/receive-vehicle-scan'
        self.assertTrue(self.config.budha_api_url.endswith('/vehicle_scanner/budha'))
        self.assertTrue(self.config.generic_api_url.endswith('/api/receive-vehicle-scan'))