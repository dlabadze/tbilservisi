{
    'name': 'ავტოპარკის დაშბორდი',
    'version': '18.0.1.0.0',
    'summary': 'ავტოპარკის სერვისების ანალიტიკა (ავტომობილები, ნაწილები, საამქროები)',
    'category': 'Fleet',
    'author': 'Tbilservisi',
    'depends': ['fleet', 'mail', 'stock', 'product'],
    'data': [
        'security/ir.model.access.csv',
        # 'data/ir_sequence_data.xml',          # disabled — service auto-numbering
        # 'views/fleet_service_views.xml',      # disabled — adds reference field to service form/list/search
        'views/fleet_dashboard_views.xml',
        'wizard/fleet_dashboard_wizard_views.xml',
        'wizard/fleet_cost_per_km_views.xml',
        'views/fleet_dashboard_menus.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
