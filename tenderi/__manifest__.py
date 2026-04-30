{
    'name': 'Tenderi',
    'version': '18.0.1.0.0',
    'depends': ['base', 'purchase', 'hr', 'tbili_budget'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/tenderi_excel_import_wizard_views.xml',
        'views/tenderi_views.xml',
        'views/purchase_plan_views.xml',
    ],
    'external_dependencies': {
        'python': ['openpyxl', 'xlrd'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}