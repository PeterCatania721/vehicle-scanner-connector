import json
import logging

from odoo import http
from odoo.http import request

from ..constants import (
    BUDHA_ROUTE_PATHS,
    GENERIC_ROUTE_PATHS,
    INBOUND_ROUTE_PATHS,
)

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

    def _build_auth_error(self, config, use_generic=False):
        if use_generic:
            payload = {
                'success': False,
                'error': 'Invalid username or password',
                'message': config.response_error_message,
            }
        else:
            payload = config.build_error_response('Invalid username or password')
        return self._json_response(payload, status=401, cors=config.allow_cors)

    def _authenticate(self, config, use_generic=False):
        auth_header = request.httprequest.headers.get('Authorization')
        if not config.check_basic_auth(auth_header):
            return self._build_auth_error(config, use_generic=use_generic)
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

    def _handle_scan_error(self, config, exc, status=400, use_generic=False):
        if use_generic:
            payload = {'success': False, 'error': str(exc), 'message': config.response_error_message}
        else:
            payload = config.build_error_response(str(exc))
        return self._json_response(payload, status=status, cors=config.allow_cors)

    # ------------------------------------------------------------------
    # BUHDA endpoints
    # ------------------------------------------------------------------

    @http.route(
        BUDHA_ROUTE_PATHS,
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        csrf=False,
    )
    def budha_webhook(self, **kw):
        config = self._get_config()
        if request.httprequest.method == 'OPTIONS':
            return self._handle_options(config)
        if not config.enable_budha_endpoint:
            return self._handle_scan_error(config, 'BUHDA endpoint is disabled', status=403)

        auth_error = self._authenticate(config, use_generic=False)
        if auth_error:
            return auth_error

        data, error = self._read_json_body()
        if error:
            return self._handle_scan_error(config, error)

        try:
            result = request.env['vehicle.scan.service'].sudo().process_budha_cases(data)
            return self._json_response(result, cors=config.allow_cors)
        except ValueError as exc:
            return self._handle_scan_error(config, exc)
        except Exception as exc:
            _logger.exception('BUHDA scan processing failed')
            return self._handle_scan_error(config, exc, status=500)

    # ------------------------------------------------------------------
    # Generic scanner endpoint
    # ------------------------------------------------------------------

    @http.route(
        GENERIC_ROUTE_PATHS,
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        csrf=False,
    )
    def receive_vehicle_scan(self, **kw):
        config = self._get_config()
        if request.httprequest.method == 'OPTIONS':
            return self._handle_options(config)
        if not config.enable_generic_endpoint:
            return self._handle_scan_error(
                config, 'Generic endpoint is disabled', status=403, use_generic=True,
            )

        auth_error = self._authenticate(config, use_generic=True)
        if auth_error:
            return auth_error

        data, error = self._read_json_body()
        if error:
            return self._handle_scan_error(config, error, use_generic=True)

        try:
            result = request.env['vehicle.scan.service'].sudo().process_generic_scan(data)
            return self._json_response(result, cors=config.allow_cors)
        except ValueError as exc:
            return self._handle_scan_error(config, exc, use_generic=True)
        except Exception as exc:
            _logger.exception('Generic vehicle scan processing failed')
            return self._handle_scan_error(config, exc, status=500, use_generic=True)

    # ------------------------------------------------------------------
    # Universal inbound endpoint (auto-detect payload format)
    # ------------------------------------------------------------------

    @http.route(
        INBOUND_ROUTE_PATHS,
        type='http',
        auth='public',
        methods=['POST', 'OPTIONS'],
        csrf=False,
    )
    def inbound_webhook(self, **kw):
        config = self._get_config()
        if request.httprequest.method == 'OPTIONS':
            return self._handle_options(config)
        if not config.enable_inbound_endpoint:
            return self._handle_scan_error(
                config, 'Inbound endpoint is disabled', status=403, use_generic=True,
            )

        auth_error = self._authenticate(config, use_generic=True)
        if auth_error:
            return auth_error

        data, error = self._read_json_body()
        if error:
            return self._handle_scan_error(config, error, use_generic=True)

        try:
            result = request.env['vehicle.scan.service'].sudo().process_inbound_payload(data)
            return self._json_response(result, cors=config.allow_cors)
        except ValueError as exc:
            return self._handle_scan_error(config, exc, use_generic=True)
        except Exception as exc:
            _logger.exception('Inbound scan processing failed')
            return self._handle_scan_error(config, exc, status=500, use_generic=True)