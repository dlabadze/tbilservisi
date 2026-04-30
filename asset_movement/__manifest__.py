{
    'name': 'Asset Movement',
    'version': '1.0.0',
    'summary': 'Track movements (deploy, transfer, etc.) of fixed assets with lines per asset',
    'description': 'Master/detail for asset movements. Master: date, operation type, employee. Lines: related assets. Integrates with Accounting assets.',
    'author': 'ChatGPT',
    'depends': ['account','hr','account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'views/asset_movement_views.xml',
    ],
    'installable': True,
    'application': False,
}
