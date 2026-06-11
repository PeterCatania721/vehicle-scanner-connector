{
    'name': 'Vehicle Scanner Connector',
    'version': '19.0.1.0.5',
    'category': 'Fleet',
    'summary': 'Receive AI vehicle scan data from BUHDA and external scanners',
    'description': """
Vehicle Scanner Connector
=========================
Receives hail-damage scan data from external AI scanners (BUHDA and generic
JSON payloads) via HTTP webhooks with Basic Auth.

Features:
- BUHDA-compatible endpoint (same payload as KESI Flask bridge)
- Generic vehicle scan endpoint for custom scanners
- Universal inbound endpoint with auto-detect payload format
- Scan logs with panel-level dent data
- PDF and image attachments stored on scan records
- License plate stored on each scan log
- Auto create/update preventivi (sale.order) by targa, codice cartella, or telaio
- Configurable API credentials (no hard-coded passwords)
    """,
    'author': 'KESI SA',
    'website': 'https://www.kesi.ch',
    'depends': ['sale'],
    'data': [
        'security/vehicle_scanner_security.xml',
        'security/ir.model.access.csv',
        'data/scanner_config_data.xml',
        'views/scanner_config_views.xml',
        'views/vehicle_scan_log_views.xml',
        'views/menu.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}