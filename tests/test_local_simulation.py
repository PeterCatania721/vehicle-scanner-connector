#!/usr/bin/env python3
"""Local simulation tests for vehicle_scanner_connector (no Odoo runtime)."""

import base64
import hmac
import json
import re
import sys
import unittest
from datetime import datetime


# ---------------------------------------------------------------------------
# Pure-logic mirrors of vehicle_scan_service / scanner_config (no Odoo deps)
# ---------------------------------------------------------------------------


def normalize_license_plate(plate):
    if not plate:
        return False
    return re.sub(r'\s+', ' ', str(plate).strip().upper())


def extract_json_path(data, path):
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


def apply_transform(value, transform):
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


def get_value_from_sources(data, *keys):
    for key in keys:
        if not key:
            continue
        value = extract_json_path(data, key) if '.' in key else data.get(key)
        if value not in (None, '', False):
            return value
    return False


def normalize_budha_payload(payload, wrapper_key='CaseData'):
    wrapper = (wrapper_key or '').strip()
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


def safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def panel_line_from_dent(panel_index, dent, market_code):
    line = {
        'panel_index': panel_index,
        'is_aluminum': bool(dent.get('alu')),
        'is_glue': bool(dent.get('glue')),
        'is_ptp': bool(dent.get('ptp')),
        'market_format': market_code,
    }
    if market_code in ('CH', 'AT', 'SL'):
        line.update({
            'amount_small': safe_int(dent.get('amountSmall')),
            'amount_medium': safe_int(dent.get('amountMedium')),
            'amount_large': safe_int(dent.get('amountLarge')),
            'amount_oversize': safe_int(dent.get('oversizeAmount')),
        })
    elif market_code in ('DE', 'NL'):
        line.update({
            'amount_total': safe_int(dent.get('amount')),
            'average_size': str(dent.get('avarageSize') or dent.get('averageSize') or ''),
        })
    elif market_code == 'FR':
        line.update({
            'amount_10': safe_int(dent.get('amount10')),
            'amount_20': safe_int(dent.get('amount20')),
            'amount_30': safe_int(dent.get('amount30')),
            'amount_40': safe_int(dent.get('amount40')),
            'amount_50': safe_int(dent.get('amount50')),
        })
    elif market_code == 'US':
        line.update({
            'amount_total': safe_int(dent.get('amount')),
            'average_size': str(dent.get('avarageSize') or dent.get('averageSize') or ''),
            'amount_oversize': safe_int(dent.get('oversizeAmount')),
        })
    else:
        line.update({
            'amount_small': safe_int(dent.get('amountSmall')),
            'amount_medium': safe_int(dent.get('amountMedium')),
            'amount_large': safe_int(dent.get('amountLarge')),
        })
    return line


def check_basic_auth(auth_header, username, password):
    if not auth_header or not auth_header.startswith('Basic '):
        return False
    try:
        encoded = auth_header[6:].strip()
        decoded = base64.b64decode(encoded).decode('utf-8')
        user, pwd = decoded.split(':', 1)
    except Exception:
        return False
    return (
        hmac.compare_digest(user, username)
        and hmac.compare_digest(pwd, password)
    )


def detect_inbound_format(payload, wrapper_key='CaseData'):
    if normalize_budha_payload(payload, wrapper_key):
        return 'budha'
    if isinstance(payload, dict) and (
        payload.get('plate') or payload.get('targa') or payload.get('scan_id')
    ):
        return 'generic'
    return None


def build_budha_log_vals(case_data, index, strip_pdf=True):
    case_number = case_data.get('Vorgangsnummer') or f'case_{index}'
    license_plate = get_value_from_sources(case_data, 'Kennzeichen', 'plate', 'targa')
    clean_data = dict(case_data)
    if strip_pdf:
        clean_data.pop('overviewPDF', None)
        clean_data.pop('attachmentsPDF', None)
    return {
        'name': f'BUHDA {case_number}',
        'case_number': case_number,
        'license_plate': normalize_license_plate(license_plate),
        'scan_data': json.dumps(clean_data, ensure_ascii=False, indent=2),
    }


# ---------------------------------------------------------------------------
# Simulated payloads (synthetic — no live/production data)
# ---------------------------------------------------------------------------

SAMPLE_BUHDA_CASE = {
    'Vorgangsnummer': 'SIM-2026-001',
    'Kennzeichen': 'ti 12345',
    'Fahrzeug': 'BMW 320d (simulated)',
    'Scanned': True,
    'Dents': {
        '1': {
            'amountSmall': 3,
            'amountMedium': 1,
            'amountLarge': 0,
            'oversizeAmount': 0,
            'alu': False,
            'glue': True,
            'ptp': False,
        },
        '6': {
            'amountSmall': 2,
            'amountMedium': 0,
            'amountLarge': 1,
            'oversizeAmount': 0,
            'alu': True,
            'glue': False,
            'ptp': True,
        },
    },
    'overviewPDF': 'c2ltdWxhdGVkX3BkZl9kYXRh',
    'attachmentsPDF': {'report': 'c2ltdWxhdGVkX2F0dGFjaA=='},
}

SAMPLE_GENERIC = {
    'plate': 'ZH 99999',
    'scan_id': 'sim_scan_001',
    'damage': {'hail': True, 'severity': 'medium'},
    'images': [
        {'filename': 'dent_front.jpg', 'data': 'c2ltdWxhdGVkX2ltYWdl'},
    ],
}


class TestLicensePlate(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_license_plate('ti 12345'), 'TI 12345')
        self.assertEqual(normalize_license_plate('  zh-99999  '), 'ZH-99999')
        self.assertFalse(normalize_license_plate(''))
        self.assertFalse(normalize_license_plate(None))


class TestBudhaNormalization(unittest.TestCase):
    def test_casedata_wrapper(self):
        payload = {'CaseData': SAMPLE_BUHDA_CASE}
        cases = normalize_budha_payload(payload)
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]['Vorgangsnummer'], 'SIM-2026-001')

    def test_raw_case_object(self):
        cases = normalize_budha_payload(SAMPLE_BUHDA_CASE)
        self.assertEqual(len(cases), 1)

    def test_array_of_wrapped_cases(self):
        payload = [
            {'CaseData': {'Vorgangsnummer': 'A'}},
            {'CaseData': {'Vorgangsnummer': 'B'}},
        ]
        cases = normalize_budha_payload(payload)
        self.assertEqual([c['Vorgangsnummer'] for c in cases], ['A', 'B'])

    def test_array_of_raw_cases(self):
        payload = [{'Vorgangsnummer': 'X'}, {'Vorgangsnummer': 'Y'}]
        cases = normalize_budha_payload(payload)
        self.assertEqual(len(cases), 2)

    def test_unrecognized_format(self):
        self.assertIsNone(normalize_budha_payload({'foo': 'bar'}))
        self.assertIsNone(normalize_budha_payload('not json'))

    def test_custom_wrapper_key(self):
        payload = {'ScanCase': {'Vorgangsnummer': 'CUSTOM'}}
        cases = normalize_budha_payload(payload, wrapper_key='ScanCase')
        self.assertEqual(cases[0]['Vorgangsnummer'], 'CUSTOM')


class TestJsonPathAndTransforms(unittest.TestCase):
    def test_nested_path(self):
        data = {'Dents': {'1': {'amountSmall': 5}}}
        self.assertEqual(extract_json_path(data, 'Dents.1.amountSmall'), 5)

    def test_transforms(self):
        self.assertEqual(apply_transform('  abc  ', 'strip'), 'abc')
        self.assertEqual(apply_transform('yes', 'bool'), True)
        self.assertEqual(apply_transform('no', 'bool'), False)
        self.assertEqual(apply_transform('42', 'int'), 42)
        self.assertEqual(apply_transform('bad', 'int'), 0)
        self.assertEqual(apply_transform({'a': 1}, 'json'), '{"a": 1}')

    def test_value_sources_priority(self):
        data = {'plate': '', 'Kennzeichen': 'TI 1', 'targa': 'TI 2'}
        self.assertEqual(get_value_from_sources(data, 'plate', 'Kennzeichen', 'targa'), 'TI 1')


class TestPanelParsing(unittest.TestCase):
    def test_ch_market(self):
        line = panel_line_from_dent(1, SAMPLE_BUHDA_CASE['Dents']['1'], 'CH')
        self.assertEqual(line['amount_small'], 3)
        self.assertEqual(line['amount_medium'], 1)
        self.assertTrue(line['is_glue'])

    def test_de_market(self):
        dent = {'amount': 7, 'averageSize': '12mm'}
        line = panel_line_from_dent(2, dent, 'DE')
        self.assertEqual(line['amount_total'], 7)
        self.assertEqual(line['average_size'], '12mm')

    def test_fr_market(self):
        dent = {'amount10': 1, 'amount20': 2, 'amount30': 0, 'amount40': 0, 'amount50': 1}
        line = panel_line_from_dent(3, dent, 'FR')
        self.assertEqual(line['amount_10'], 1)
        self.assertEqual(line['amount_50'], 1)

    def test_invalid_panel_key_skipped(self):
        dents = {'bad_key': {'amountSmall': 1}, '2': {'amountSmall': 4}}
        lines = []
        for key, dent in dents.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                continue
            lines.append(panel_line_from_dent(idx, dent, 'CH'))
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['amount_small'], 4)


class TestAuth(unittest.TestCase):
    def test_valid_credentials(self):
        token = base64.b64encode(b'ai_scanner:secret').decode()
        header = f'Basic {token}'
        self.assertTrue(check_basic_auth(header, 'ai_scanner', 'secret'))

    def test_invalid_credentials(self):
        token = base64.b64encode(b'ai_scanner:wrong').decode()
        self.assertFalse(check_basic_auth(f'Basic {token}', 'ai_scanner', 'secret'))

    def test_missing_header(self):
        self.assertFalse(check_basic_auth(None, 'ai_scanner', 'secret'))
        self.assertFalse(check_basic_auth('Bearer xyz', 'ai_scanner', 'secret'))


class TestInboundDetection(unittest.TestCase):
    def test_detect_budha(self):
        self.assertEqual(detect_inbound_format({'CaseData': SAMPLE_BUHDA_CASE}), 'budha')

    def test_detect_generic(self):
        self.assertEqual(detect_inbound_format(SAMPLE_GENERIC), 'generic')

    def test_detect_unknown(self):
        self.assertIsNone(detect_inbound_format({'unknown': True}))


class TestBudhaLogBuilding(unittest.TestCase):
    def test_strips_pdf_from_stored_json(self):
        vals = build_budha_log_vals(SAMPLE_BUHDA_CASE, 1, strip_pdf=True)
        stored = json.loads(vals['scan_data'])
        self.assertNotIn('overviewPDF', stored)
        self.assertNotIn('attachmentsPDF', stored)
        self.assertEqual(vals['license_plate'], 'TI 12345')
        self.assertEqual(vals['case_number'], 'SIM-2026-001')

    def test_keeps_pdf_when_disabled(self):
        vals = build_budha_log_vals(SAMPLE_BUHDA_CASE, 1, strip_pdf=False)
        stored = json.loads(vals['scan_data'])
        self.assertIn('overviewPDF', stored)


class TestFlaskParity(unittest.TestCase):
    """Ensure Odoo normalization covers Flask _normalize_budha_payload shapes."""

    def _flask_normalize(self, payload):
        if isinstance(payload, dict) and 'CaseData' in payload:
            return [payload['CaseData']]
        if isinstance(payload, list):
            casi = [
                item['CaseData'] if 'CaseData' in item else item
                for item in payload
                if isinstance(item, dict)
            ]
            return casi or None
        return None

    def test_parity_wrapped_and_list(self):
        shapes = [
            {'CaseData': SAMPLE_BUHDA_CASE},
            [{'CaseData': {'Vorgangsnummer': 'L1'}}, {'Vorgangsnummer': 'L2'}],
        ]
        for shape in shapes:
            flask_result = self._flask_normalize(shape)
            odoo_result = normalize_budha_payload(shape)
            self.assertEqual(
                [c.get('Vorgangsnummer') for c in (flask_result or [])],
                [c.get('Vorgangsnummer') for c in (odoo_result or [])],
            )

    def test_odoo_supports_raw_case_flask_does_not(self):
        """Odoo adds raw Vorgangsnummer dict — intentional enhancement."""
        odoo_result = normalize_budha_payload(SAMPLE_BUHDA_CASE)
        flask_result = self._flask_normalize(SAMPLE_BUHDA_CASE)
        self.assertIsNotNone(odoo_result)
        self.assertIsNone(flask_result)


class TestModuleStructure(unittest.TestCase):
    """Static checks on module files."""

    def test_manifest_declares_odoo_19(self):
        manifest_path = (
            '/Users/petercatania/Projects/vehicle-scanner-connector'
            '/vehicle_scanner_connector/__manifest__.py'
        )
        with open(manifest_path, encoding='utf-8') as f:
            content = f.read()
        self.assertIn("'version': '19.", content)
        self.assertIn("'sale'", content)
        self.assertNotIn("'fleet'", content)
        self.assertIn("'post_init_hook'", content)

    def test_security_access_csv_covers_all_models(self):
        csv_path = (
            '/Users/petercatania/Projects/vehicle-scanner-connector'
            '/vehicle_scanner_connector/security/ir.model.access.csv'
        )
        with open(csv_path, encoding='utf-8') as f:
            content = f.read()
        for model in (
            'vehicle.scan.log',
            'vehicle.scan.panel',
            'vehicle.scanner.config',
            'vehicle.scanner.panel.mapping',
            'vehicle.scanner.field.mapping',
            'vehicle.scanner.parser.rule',
        ):
            self.assertIn(model, content)

    def test_manifest_has_no_fleet_or_repair_dependency(self):
        manifest_path = (
            '/Users/petercatania/Projects/vehicle-scanner-connector'
            '/vehicle_scanner_connector/__manifest__.py'
        )
        with open(manifest_path, encoding='utf-8') as f:
            content = f.read()
        self.assertIn("'sale'", content)
        self.assertNotIn("'fleet'", content)
        self.assertNotIn("'repair'", content)
        self.assertIn("'post_init_hook'", content)


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)