{
    'name': 'Asset Excel Import',
    'version': '18.0.1.0.0',
    'summary': 'Import assets from Excel with dynamic column-to-field mapping',
    'description': 'Upload Excel, map columns to account.asset fields, match employees and departments by name.',
    'author': 'Tbilservisi',
    'depends': ['account_asset', 'hr'],
    'external_dependencies': {
        'python': ['openpyxl', 'pandas', 'xlrd'],
    },
    'data': [
        'security/ir.model.access.csv',
        'views/asset_import_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
