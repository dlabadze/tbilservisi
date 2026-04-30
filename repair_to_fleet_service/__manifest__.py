{
    'name': 'Repair to Fleet Service',
    'version': '18.0.1.0.0',
    'summary': 'Create Fleet Service and product lines when Repair is ended',
    'author': 'DVSport',
    'license': 'LGPL-3',
    'depends': [
        'repair',
        'stock',
        'fleet',
        'fleet_service_product_lines',
        'product',
    ],
    'data': [
        'security/repair_to_fleet_service_security.xml',
        'views/repair_service_smart_buttons.xml',
    ],
    'installable': True,
    'application': False,
} 


