{
    'name': 'Asset Split',
    'version': '1.0.0',
    'summary': 'Split fixed assets by quantity with recalculated values',
    'description': '''
        Asset Split Module
        ==================
        Allows splitting a fixed asset into two parts based on quantity:
        - Select an asset and specify quantities (raod, raod_new)
        - Creates a new asset copy with recalculated values
        - Updates the original asset with remaining values
        - Automatic recalculation of original_value_new and already_depreciated_amount_import_new
    ''',
    'author': 'Your Company',
    'depends': ['account', 'account_asset'],
    'data': [
        'security/ir.model.access.csv',
        'views/asset_split_views.xml',
    ],
    'installable': True,
    'application': False,
}

