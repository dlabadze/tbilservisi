{
    'name': 'Xazina Excel Generate',
    'version': '1.0',
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/salary_and_bulletin_excel_view.xml',
        'views/xazina_dakavebebi_excel_view.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
