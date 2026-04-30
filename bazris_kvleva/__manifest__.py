{
    'name': 'Bazris Kvleva',
    'version': '18.0.1.0.0',
    'depends': ['purchase', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/excel_import_wizard_views.xml',
        'views/bazris_kvlevis_tanamshromlebi_views.xml',
        'views/safudzvlis_werilis_tarigebi_views.xml',
        'views/bazris_kvleva_views.xml',
        'views/bazris_kvleva_menu.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

