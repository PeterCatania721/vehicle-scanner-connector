{
    'name': 'KESI Preventivi Demo',
    'version': '19.0.1.0.1',
    'category': 'Sales',
    'summary': 'Preventivi app structure mirroring KESI Odoo (sale.order based)',
    'description': """
Replicates the KESI "Preventivi" application menu structure on top of sale.order,
with simplified car catalog models and Levabolli quotation fields for local demo use.
    """,
    'author': 'KESI SA',
    'website': 'https://www.kesi.ch',
    'depends': ['sale_management', 'vehicle_scanner_connector'],
    'data': [
        'security/ir.model.access.csv',
        'views/car_brand_views.xml',
        'views/car_model_views.xml',
        'views/car_color_views.xml',
        'views/boli_product_views.xml',
        'views/sale_order_views.xml',
        'views/sale_order_bolli_views.xml',
        'views/scanner_config_views.xml',
        'views/preventivi_menus.xml',
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'kesi_preventivi_demo/static/src/scss/kesi_bolli_matrix.scss',
        ],
    },
}