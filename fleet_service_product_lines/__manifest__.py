{
    'name': 'Fleet Service Product Lines',
    'version': '18.0.1.0.0',
    'summary': 'Add product lines to Fleet Services with auto-filled product data',
    'author': 'DVSport',
    'license': 'LGPL-3',
    'depends': ['fleet', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'views/fleet_service_product_line_views.xml',
    ],
    'installable': True,
    'application': False,
}


