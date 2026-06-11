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
        cls.partner = cls.env['res.partner'].create({'name': 'Scanner Test Customer'})
        cls.product = cls.env['product.product'].create({
            'name': 'Scanner Repair Service',
            'type': 'service',
            'list_price': 100.0,
        })
        cls.config.write({
            'password': 'test-secret',
            'require_license_plate': False,
            'strip_pdf_from_json_log': True,
            'auto_process_panels': True,
            'market_code': 'CH',
            'enable_preventivi_sync': True,
            'preventivi_user_id': cls.env.user.id,
            'preventivi_partner_id': cls.partner.id,
            'preventivi_product_id': cls.product.id,
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

    def test_budha_panel_maps_to_kesi_bolli_row(self):
        defaults = self.env['vehicle.scanner.panel.mapping'].get_default_mappings()
        by_index = {panel_index: bolli_row for panel_index, _, _, bolli_row in defaults}
        self.assertEqual(by_index[1], 1)
        self.assertEqual(by_index[10], 10)
        self.assertEqual(by_index[11], 12)
        self.assertEqual(by_index[12], 13)
        self.assertEqual(by_index[17], 18)

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

    def test_revision_suffix_allocation(self):
        SaleOrder = self.env['sale.order'].sudo()
        if 'license_plate' not in SaleOrder._fields:
            self.skipTest('Preventivi fields are not installed')
        SaleOrder.create({
            'partner_id': self.partner.id,
            'license_plate': 'TI 12345',
        })
        suffix = self.service._allocate_revision_suffix(SaleOrder, 'license_plate', 'TI 12345')
        self.assertEqual(suffix, '/R')
        SaleOrder.create({
            'partner_id': self.partner.id,
            'license_plate': 'TI 12345/R',
        })
        suffix = self.service._allocate_revision_suffix(SaleOrder, 'license_plate', 'TI 12345')
        self.assertEqual(suffix, '/RA')

    def test_budha_scan_creates_preventivo(self):
        if 'license_plate' not in self.env['sale.order']._fields:
            self.skipTest('Preventivi fields are not installed')
        payload = {
            'CaseData': {
                'Vorgangsnummer': 'PREV-001',
                'Kennzeichen': 'ti 555',
                'Fahrzeug': 'BMW 320d',
                'Fahrgestellnummer': 'CHASSIS-001',
                'Dents': {
                    '1': {
                        'amountSmall': 2,
                        'amountMedium': 1,
                        'glue': True,
                        'alu': True,
                    },
                },
            },
        }
        result = self.service.process_budha_cases(payload)
        log = self.env['vehicle.scan.log'].browse(result['details'][0]['scan_log_id'])
        self.assertEqual(log.preventivi_action, 'created')
        self.assertTrue(log.sale_order_id)
        order = log.sale_order_id
        self.assertEqual(order.license_plate, 'TI 555')
        self.assertEqual(order.ref, 'PREV-001')
        self.assertEqual(order.chassis, 'CHASSIS-001')
        self.assertTrue(order.dent_remover)
        if 'g1' in order._fields:
            self.assertTrue(order.g1)
            self.assertTrue(order.a1)
            self.assertTrue(order.mm_1)
            self.assertEqual(order.sotto1, 2)
            self.assertEqual(order.sopra1, 1)

    def test_rescan_updates_existing_preventivo(self):
        if 'license_plate' not in self.env['sale.order']._fields:
            self.skipTest('Preventivi fields are not installed')
        payload = {
            'CaseData': {
                'Vorgangsnummer': 'PREV-002',
                'Kennzeichen': 'ti 777',
                'Dents': {'2': {'amountSmall': 1}},
            },
        }
        first = self.service.process_budha_cases(payload)
        order = self.env['vehicle.scan.log'].browse(
            first['details'][0]['scan_log_id']
        ).sale_order_id
        second = self.service.process_budha_cases(payload)
        log = self.env['vehicle.scan.log'].browse(second['details'][0]['scan_log_id'])
        self.assertEqual(log.preventivi_action, 'updated')
        self.assertEqual(log.sale_order_id, order)

    def test_duplicate_plate_creates_revision_suffix(self):
        if 'license_plate' not in self.env['sale.order']._fields:
            self.skipTest('Preventivi fields are not installed')
        first = self.service.process_budha_cases({
            'CaseData': {
                'Vorgangsnummer': 'CASE-A',
                'Kennzeichen': 'ti 888',
                'Fahrgestellnummer': 'VIN-888',
            },
        })
        second = self.service.process_budha_cases({
            'CaseData': {
                'Vorgangsnummer': 'CASE-B',
                'Kennzeichen': 'ti 888',
                'Fahrgestellnummer': 'VIN-888',
            },
        })
        order = self.env['vehicle.scan.log'].browse(
            second['details'][0]['scan_log_id']
        ).sale_order_id
        self.assertEqual(order.license_plate, 'TI 888/R')
        self.assertEqual(order.chassis, 'VIN-888/R')
        self.assertEqual(order.ref, 'CASE-B')  # codice cartella stays unsuffixed