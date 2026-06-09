"""Shared webhook path constants used by models and controllers."""

BUDHA_ROUTE_PATHS = [
    '/budha',
    '/vehicle_scanner/budha',
]

GENERIC_ROUTE_PATHS = [
    '/api/receive-vehicle-scan',
    '/vehicle_scanner/receive',
]

INBOUND_ROUTE_PATHS = [
    '/vehicle_scanner/inbound',
]

BUDHA_PATH_SELECTION = [
    ('/budha', '/budha (Flask-compatible)'),
    ('/vehicle_scanner/budha', '/vehicle_scanner/budha (namespaced)'),
]

GENERIC_PATH_SELECTION = [
    ('/vehicle_scanner/receive', '/vehicle_scanner/receive'),
    ('/api/receive-vehicle-scan', '/api/receive-vehicle-scan (legacy)'),
]

INBOUND_PATH_SELECTION = [
    ('/vehicle_scanner/inbound', '/vehicle_scanner/inbound'),
]