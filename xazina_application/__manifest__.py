{
    'name': 'Xazina Application',
    'version': '18.0.1.0.0',
    'depends': ['base', 'analytic', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/xazina_views.xml',
        'wizard/import_xazina_wizard_views.xml',
        'wizard/create_gatareba_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}