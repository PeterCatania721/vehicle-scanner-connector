import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class VehicleScannerController(http.Controller):

    def _get_config(self):
        return request.env['vehicle.scanner.config'].sudo().get_active_config()

    def _json_response(self, payload, status=200, cors=False):
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        if cors:
            headers.update({
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Authorization, Content-Type',
            })
        return request.make_response(
            json.dumps(payload, ensure_ascii=False),
            headers=headers,
            status=status,
        )

    def _authenticate(self, config):
        auth_header = request.httprequest.headers.get('Authorization')
        if not config.check_basic_auth(auth_header):
            return self._json_response(
                {'success': False, 'error': 'Invalid username or password'},
                status=401,
                cors=config.allow_cors,
            )
        return None

    def _read_json_body(self):
        try:
            data = request.get_json_data()
        except Exception:
            raw = request.httprequest.get_data(as_text=True)
            if not raw:
                return None, 'Empty payload'
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return None, 'Invalid JSON payload'
        if data is None:
            return None, 'Empty payload'
        return data, None

    def _handle_options(self, config):
        if not config.allow_cors:
            return self._json_response({'error': 'Method not allowed'}, status=405)
        return self._json_response({'status': 'ok'}, cors=True)

    # ------------------------------------------------------------------
    # BUHDA endpoints (compatible with Budha Connection Flask /budha)
    # ------------------------------------------------------------------

    @http.route(
        ['/budha', '/vehicle_scanner/budha'],
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        csrf=False,
    )
    def budha_webhook(self, **kw):
        config = self._get_config()
        if request.httprequest.method == 'OPTIONS':
            return self._handle_options(config)

        auth_error = self._authenticate(config)
        if auth_error:
            return auth_error

        data, error = self._read_json_body()
        if error:
            return self._json_response(
                {'status': 'error', 'error': error},
                status=400,
                cors=config.allow_cors,
            )

        try:
            result = request.env['vehicle.scan.service'].sudo().process_budha_cases(data)
            return self._json_response(result, cors=config.allow_cors)
        except ValueError as exc:
            return self._json_response(
                {'status': 'error', 'error': str(exc)},
                status=400,
                cors=config.allow_cors,
            )
        except Exception as exc:
            _logger.exception('BUHDA scan processing failed')
            return self._json_response(
                {'status': 'error', 'error': str(exc)},
                status=500,
                cors=config.allow_cors,
            )

    # ------------------------------------------------------------------
    # Generic scanner endpoint (from original AI Scanner plan)
    # ------------------------------------------------------------------

    @http.route(
        ['/api/receive-vehicle-scan', '/vehicle_scanner/receive'],
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        csrf=False,
    )
    def receive_vehicle_scan(self, **kw):
        config = self._get_config()
        if request.httprequest.method == 'OPTIONS':
            return self._handle_options(config)

        auth_error = self._authenticate(config)
        if auth_error:
            return auth_error

        data, error = self._read_json_body()
        if error:
            return self._json_response(
                {'success': False, 'error': error},
                status=400,
                cors=config.allow_cors,
            )

        try:
            result = request.env['vehicle.scan.service'].sudo().process_generic_scan(data)
            return self._json_response(result, cors=config.allow_cors)
        except ValueError as exc:
            return self._json_response(
                {'success': False, 'error': str(exc)},
                status=400,
                cors=config.allow_cors,
            )
        except Exception as exc:
            _logger.exception('Generic vehicle scan processing failed')
            return self._json_response(
                {'success': False, 'error': str(exc)},
                status=500,
                cors=config.allow_cors,
            )